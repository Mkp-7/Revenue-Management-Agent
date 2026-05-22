"""
agent2_demand.py — Demand Signal Monitor
=========================================
Real data from 3 free APIs:
  1. OpenSky Network — real ADS-B flight data (no key needed)
  2. Ticketmaster Discovery API — real events near airports
  3. Open-Meteo — real 14-day weather forecast (no key needed)
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.airports import TOP_50_AIRPORTS
from config.settings import TOP_10_AIRPORTS
from config.database import get_connection, init_db

load_dotenv()

AVIATIONSTACK_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")
TICKETMASTER_KEY = os.getenv("TICKETMASTER_API_KEY", "")
OPENSKY_USER     = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASS     = os.getenv("OPENSKY_PASSWORD", "")

SEVERE_CODES = {65, 67, 75, 77, 82, 85, 86, 95, 96, 99}
WMO_LABELS   = {
    0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
    95: "Thunderstorm", 99: "Severe Thunderstorm",
}


# ── OpenSky Flights ────────────────────────────────────────────────

async def fetch_flight_demand(session, airport):
    iata = airport["code"]
    
    # Try AviationStack first (100 calls/month — used once per day max)
    if AVIATIONSTACK_KEY:
        try:
            async with session.get(
                "http://api.aviationstack.com/v1/flights",
                params={
                    "access_key": AVIATIONSTACK_KEY,
                    "arr_iata":   iata,
                    "flight_status": "scheduled",
                    "limit":      100,
                },
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 200:
                    data    = await resp.json()
                    flights = data.get("data", [])
                    by_date = {}
                    for f in flights:
                        dep = f.get("departure", {}).get("scheduled", "")
                        if dep:
                            date = dep[:10]
                            by_date.setdefault(date, {"arrivals":0,"departures":0})
                            by_date[date]["arrivals"] += 1
                    logger.debug("AviationStack ✅ {}: {} flights", iata, len(flights))
                    return {"airport_code": iata, "by_date": by_date, "source": "aviationstack"}
                else:
                    logger.warning("AviationStack {} HTTP {}", iata, resp.status)
        except Exception as e:
            logger.warning("AviationStack {}: {}", iata, str(e)[:60])

    # Fallback: OpenSky (no key needed)
    icao = airport["icao"]
    end_time = int(datetime.utcnow().timestamp())
    begin    = end_time - (12 * 3600)
    auth     = aiohttp.BasicAuth(OPENSKY_USER, OPENSKY_PASS) if OPENSKY_USER else None

    try:
        async with session.get(
            "https://opensky-network.org/api/flights/arrival",
            params={"airport": icao, "begin": begin, "end": end_time},
            auth=auth,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                flights   = await resp.json()
                count     = len(flights) if isinstance(flights, list) else 0
                daily_est = count * 2
                by_date   = {}
                for i in range(14):
                    date = (datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d")
                    dow  = (datetime.utcnow() + timedelta(days=i)).weekday()
                    proj = int(daily_est * (1.15 if dow >= 4 else 1.0))
                    by_date[date] = {"arrivals": proj//2, "departures": proj//2}
                logger.debug("OpenSky ✅ {}: {} arrivals/12h", iata, count)
                return {"airport_code": iata, "by_date": by_date, "source": "opensky"}
            else:
                logger.warning("OpenSky {} HTTP {}", iata, resp.status)
                return {"airport_code": iata, "by_date": {}, "source": f"error_{resp.status}"}
    except Exception as e:
        logger.warning("OpenSky {}: {}", iata, str(e)[:60])
        return {"airport_code": iata, "by_date": {}, "source": "error"}

def store_flight_demand(airport_code, demand):
    if not demand["by_date"]:
        return
    conn = get_connection()
    cur  = conn.cursor()
    now  = datetime.utcnow().isoformat()
    for date, counts in demand["by_date"].items():
        cur.execute("""
            INSERT INTO flight_demand
                (fetched_at, airport_code, flight_date, arrivals, departures, total_flights)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now, airport_code, date,
              counts["arrivals"], counts["departures"],
              counts["arrivals"] + counts["departures"]))
    conn.commit()
    conn.close()


# ── Ticketmaster Events ────────────────────────────────────────────

async def fetch_events(session, airport):
    if not TICKETMASTER_KEY:
        return []
    try:
        async with session.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params={
                "apikey":             TICKETMASTER_KEY,
                "latlong":            f"{airport['lat']},{airport['lon']}",
                "radius":             "50",
                "unit":               "miles",
                "classificationName": "sports,music,arts",
                "size":               20,
                "startDateTime":      datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endDateTime":        (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                data   = await resp.json()
                events = data.get("_embedded", {}).get("events", [])
                results = []
                for ev in events:
                    dates  = ev.get("dates", {}).get("start", {})
                    venues = ev.get("_embedded", {}).get("venues", [{}])
                    clsf   = ev.get("classifications", [{}])
                    results.append({
                        "airport_code": airport["code"],
                        "event_name":   ev.get("name", "Unknown"),
                        "event_date":   dates.get("localDate", ""),
                        "event_type":   clsf[0].get("segment", {}).get("name", "Other") if clsf else "Other",
                        "venue":        venues[0].get("name", "") if venues else "",
                        "expected_attendance": None,
                        "distance_miles":      None,
                    })
                return results
            return []
    except Exception as e:
        logger.error("Ticketmaster {}: {}", airport["code"], str(e)[:60])
        return []


def store_events(events):
    if not events:
        return
    conn = get_connection()
    cur  = conn.cursor()
    now  = datetime.utcnow().isoformat()
    for ev in events:
        cur.execute("""
            INSERT INTO events
                (fetched_at, airport_code, event_name, event_date, event_type,
                 venue, expected_attendance, distance_miles)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (now, ev["airport_code"], ev["event_name"], ev["event_date"],
              ev["event_type"], ev["venue"], ev["expected_attendance"], ev["distance_miles"]))
    conn.commit()
    conn.close()


# ── Open-Meteo Weather ─────────────────────────────────────────────

async def fetch_weather(session, airport):
    try:
        async with session.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":      airport["lat"],
                "longitude":     airport["lon"],
                "daily":         "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "timezone":      "America/New_York",
                "forecast_days": 14,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                data  = await resp.json()
                daily = data.get("daily", {})
                dates = daily.get("time", [])
                results = []
                for i, date in enumerate(dates):
                    code   = daily.get("weathercode",       [0]  * len(dates))[i] or 0
                    precip = daily.get("precipitation_sum", [0]  * len(dates))[i] or 0
                    wind   = daily.get("windspeed_10m_max", [0]  * len(dates))[i] or 0
                    tmax   = daily.get("temperature_2m_max",[20] * len(dates))[i] or 20
                    tmin   = daily.get("temperature_2m_min",[10] * len(dates))[i] or 10
                    results.append({
                        "airport_code":     airport["code"],
                        "forecast_date":    date,
                        "condition":        WMO_LABELS.get(code, f"Code {code}"),
                        "precipitation_mm": precip,
                        "wind_speed_kmh":   wind,
                        "temp_max_c":       tmax,
                        "temp_min_c":       tmin,
                        "is_severe":        1 if code in SEVERE_CODES or precip > 30 else 0,
                    })
                return results
            return []
    except Exception as e:
        logger.error("Open-Meteo {}: {}", airport["code"], str(e)[:60])
        return []


def store_weather(forecasts):
    if not forecasts:
        return
    conn = get_connection()
    cur  = conn.cursor()
    now  = datetime.utcnow().isoformat()
    for f in forecasts:
        cur.execute("""
            INSERT INTO weather_forecasts
                (fetched_at, airport_code, forecast_date, condition,
                 precipitation_mm, wind_speed_kmh, temp_max_c, temp_min_c, is_severe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (now, f["airport_code"], f["forecast_date"], f["condition"],
              f["precipitation_mm"], f["wind_speed_kmh"],
              f["temp_max_c"], f["temp_min_c"], f["is_severe"]))
    conn.commit()
    conn.close()


# ── Main Loop ──────────────────────────────────────────────────────

async def collect_all_demand_signals(target_airports=None):
    airports = target_airports or [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS]
    init_db()

    logger.info("📡 Demand signals — {} airports", len(airports))
    logger.info("   ✈️  OpenSky | 🎟️  Ticketmaster ({}) | 🌧️  Open-Meteo",
                "✅" if TICKETMASTER_KEY else "❌ no key")

    async with aiohttp.ClientSession() as session:
        for i, airport in enumerate(airports):
            logger.info("[{}/{}] {} — {}", i+1, len(airports), airport["code"], airport["city"])

            flights, events, weather = await asyncio.gather(
                fetch_flight_demand(session, airport),
                fetch_events(session, airport),
                fetch_weather(session, airport),
            )

            store_flight_demand(airport["code"], flights)
            store_events(events)
            store_weather(weather)

            severe = sum(1 for w in weather if w.get("is_severe"))
            logger.success("✅ {} — flights:{} [{}] events:{} weather:{} ({}⚡)",
                           airport["code"],
                           len(flights.get("by_date", {})),
                           flights.get("source", "none"),
                           len(events), len(weather), severe)

            await asyncio.sleep(10)  # respect OpenSky rate limits

    logger.success("🏁 Demand signals complete.")


def get_demand_summary(airport_code, days_ahead=14):
    conn     = get_connection()
    cur      = conn.cursor()
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    today    = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        SELECT flight_date, SUM(total_flights) as flights
        FROM flight_demand WHERE airport_code=? AND flight_date BETWEEN ? AND ?
        GROUP BY flight_date ORDER BY flight_date
    """, (airport_code, today, end_date))
    flights = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT event_name, event_date, event_type, expected_attendance
        FROM events WHERE airport_code=? AND event_date BETWEEN ? AND ?
        ORDER BY event_date
    """, (airport_code, today, end_date))
    events = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT forecast_date, condition, precipitation_mm, wind_speed_kmh, is_severe
        FROM weather_forecasts
        WHERE airport_code=? AND forecast_date BETWEEN ? AND ? AND is_severe=1
        ORDER BY forecast_date
    """, (airport_code, today, end_date))
    severe_weather = [dict(r) for r in cur.fetchall()]

    conn.close()
    return {
        "airport_code":        airport_code,
        "flights_by_day":      flights,
        "upcoming_events":     events,
        "severe_weather_days": severe_weather,
    }


if __name__ == "__main__":
    asyncio.run(collect_all_demand_signals())
