"""
agent3_recommendations.py — AI Pricing Recommendation Engine
Uses Google Gemini 2.0 Flash (free tier: 1500 requests/day)
Generates specific, data-driven pricing recommendations per airport.
"""

import os
import json
import time
import re
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.airports import TOP_50_AIRPORTS
from config.settings import TOP_10_AIRPORTS
from config.database import get_connection, init_db
from agents.agent1_scraper import get_latest_prices
from agents.agent2_demand import get_demand_summary

load_dotenv()

GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You are a senior revenue analyst for a major US car rental company.
Analyze the competitor pricing data and demand signals provided.
Output ONLY a JSON array of exactly 3 pricing recommendations.

Each recommendation must follow this exact format:
{
  "car_category": "economy|compact|midsize|fullsize|suv|luxury|van|convertible",
  "recommendation": "Specific action with exact dollar amount e.g. Raise economy rates by $8/day to $71",
  "reasoning": "Data-driven reason referencing specific numbers e.g. Braves game (45,000 attendees) on May 28 drives 23% demand spike",
  "urgency": "low|medium|high|critical",
  "price_delta": 8.00
}

STRICT RULES:
- Exactly 3 recommendations, each for a DIFFERENT car_category
- price_delta is always a dollar amount (not percentage). e.g. 8.00 not 0.08
- If holding price, set price_delta = 0 and urgency = "low"
- Reference actual event names, attendance figures, flight counts, or weather conditions
- Return ONLY the JSON array — no markdown, no explanation"""


def build_prompt(airport_code: str) -> str:
    prices = get_latest_prices(airport_code)
    demand = get_demand_summary(airport_code)

    # Build price stats per category
    price_by_cat = {}
    for row in prices:
        cat  = row["car_category"]
        comp = row["competitor"]
        rate = row["daily_rate"]
        price_by_cat.setdefault(cat, {})[comp] = rate

    stats_lines = []
    for cat, comps in price_by_cat.items():
        if comps:
            avg = sum(comps.values()) / len(comps)
            mn  = min(comps.values())
            mx  = max(comps.values())
            comp_str = ", ".join(f"{k}=${v:.0f}" for k,v in sorted(comps.items()))
            stats_lines.append(f"  {cat}: avg=${avg:.0f} min=${mn:.0f} max=${mx:.0f} | {comp_str}")

    # Build events with attendance
    events_lines = []
    for e in demand.get("upcoming_events", [])[:5]:
        attendance = e.get("expected_attendance")
        att_str    = f"{attendance:,} attendees" if attendance else "attendance unknown"
        events_lines.append(
            f"  - {e['event_name']} on {e.get('event_date','?')} "
            f"at {e.get('venue','unknown venue')} ({att_str})"
        )

    # Build weather alerts
    weather_lines = []
    for w in demand.get("severe_weather_days", [])[:3]:
        weather_lines.append(f"  - {w['forecast_date']}: {w['condition']} "
                            f"({w.get('precipitation_mm',0):.0f}mm rain, "
                            f"{w.get('wind_speed_kmh',0):.0f}km/h wind)")

    # Peak flights
    flights    = demand.get("flights_by_day", [])
    peak_day   = max(flights, key=lambda x: x["flights"], default={})
    peak_str   = f"{peak_day.get('flights',0)} flights on {peak_day.get('flight_date','?')}" if peak_day else "no data"

    return f"""Airport: {airport_code}

COMPETITOR PRICES ($/day):
{chr(10).join(stats_lines) or "  No price data"}

UPCOMING EVENTS:
{chr(10).join(events_lines) or "  No events found"}

SEVERE WEATHER:
{chr(10).join(weather_lines) or "  No severe weather forecast"}

FLIGHT DEMAND:
  Peak: {peak_str}

Generate exactly 3 pricing recommendations for this airport.
Each must target a different car category and reference specific data points above."""

def call_groq(prompt: str) -> list[dict]:
    """Fallback to Groq if Gemini fails."""
    if not GROQ_API_KEY:
        return []
    try:
        from groq import Groq
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*",     "", raw)
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        logger.error("Groq error: {}", str(e)[:100])
        return []


def generate_fallback(airport_code: str) -> list[dict]:
    """Rule-based fallback when both AI providers fail."""
    prices = get_latest_prices(airport_code)
    demand = get_demand_summary(airport_code)

    has_events  = len(demand.get("upcoming_events", [])) > 0
    has_weather = len(demand.get("severe_weather_days", [])) > 0

    # Get market averages
    price_by_cat = {}
    for row in prices:
        price_by_cat.setdefault(row["car_category"], []).append(row["daily_rate"])
    avgs = {cat: sum(v)/len(v) for cat, v in price_by_cat.items() if v}

    suv_avg  = avgs.get("suv", 108)
    eco_avg  = avgs.get("economy", 48)
    mid_avg  = avgs.get("midsize", 68)

    recs = []

    if has_events:
        event = demand["upcoming_events"][0]
        att   = event.get("expected_attendance")
        att_str = f"{att:,} attendees" if att else "large attendance"
        recs.append({
            "car_category":  "suv",
            "recommendation": f"Raise SUV rates by $15/day to ${suv_avg+15:.0f} at {airport_code} ahead of {event['event_name']}.",
            "reasoning":     f"{event['event_name']} on {event.get('event_date','?')} ({att_str}) drives strong demand for larger vehicles.",
            "urgency":       "high",
            "price_delta":   15.0,
        })
    else:
        recs.append({
            "car_category":  "suv",
            "recommendation": f"Hold SUV rates at ${suv_avg:.0f}/day at {airport_code} — market stable.",
            "reasoning":     "No major demand triggers. Current pricing aligned with market average.",
            "urgency":       "low",
            "price_delta":   0.0,
        })

    if has_weather:
        weather = demand["severe_weather_days"][0]
        recs.append({
            "car_category":  "fullsize",
            "recommendation": f"Raise fullsize rates by $20/day at {airport_code} — storm demand incoming.",
            "reasoning":     f"{weather['condition']} forecast on {weather['forecast_date']} will drive last-minute rental demand surge.",
            "urgency":       "critical",
            "price_delta":   20.0,
        })
    else:
        recs.append({
            "car_category":  "economy",
            "recommendation": f"Hold economy rates at ${eco_avg:.0f}/day — within 5% of market average.",
            "reasoning":     "Economy segment drives volume. Competitive pricing protects market share.",
            "urgency":       "medium",
            "price_delta":   0.0,
        })

    recs.append({
        "car_category":  "midsize",
        "recommendation": f"Raise midsize rates by $8/day to ${mid_avg+8:.0f} at {airport_code}.",
        "reasoning":     "Midsize has highest margin opportunity with room to grow vs competitors.",
        "urgency":       "medium",
        "price_delta":   8.0,
    })

    return recs


def validate_recs(recs: list) -> list[dict]:
    """Ensure recommendations are valid before storing."""
    valid_cats  = {"economy","compact","midsize","fullsize","suv","luxury","van","convertible"}
    valid_urgency = {"low","medium","high","critical"}
    seen_cats   = set()
    cleaned     = []

    for rec in recs:
        cat     = str(rec.get("car_category","")).lower().strip()
        urgency = str(rec.get("urgency","low")).lower().strip()
        delta   = rec.get("price_delta", 0)

        if cat not in valid_cats:
            continue
        if cat in seen_cats:
            continue
        if urgency not in valid_urgency:
            urgency = "medium"
        try:
            delta = float(delta)
        except Exception:
            delta = 0.0

        # If delta is suspiciously small (percentage not dollars), scale up
        if 0 < abs(delta) < 1:
            delta = round(delta * 100, 2)

        seen_cats.add(cat)
        cleaned.append({
            "car_category":   cat,
            "recommendation": str(rec.get("recommendation", "")),
            "reasoning":      str(rec.get("reasoning", "")),
            "urgency":        urgency,
            "price_delta":    delta,
        })

    return cleaned[:3]


def store_recommendations(airport_code: str, recs: list[dict]):
    conn = get_connection()
    cur  = conn.cursor()
    now  = datetime.now().isoformat()
    # Delete previous recs for this airport
    cur.execute("DELETE FROM recommendations WHERE airport_code=?", (airport_code,))
    for rec in recs:
        cur.execute("""
            INSERT INTO recommendations
                (created_at, airport_code, car_category, recommendation,
                 reasoning, urgency, price_delta, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (now, airport_code, rec["car_category"], rec["recommendation"],
              rec["reasoning"], rec["urgency"], rec["price_delta"]))
    conn.commit()
    conn.close()
    logger.success("💾 Stored {} recommendations for {}", len(recs), airport_code)


def generate_for_airport(airport_code: str) -> list[dict]:
    logger.info("🤖 Generating recommendations for {}...", airport_code)

    prices = get_latest_prices(airport_code)
    if not prices:
        logger.warning("No price data for {} — using fallback", airport_code)
        recs = generate_fallback(airport_code)
        store_recommendations(airport_code, recs)
        return recs

    prompt = build_prompt(airport_code)

    recs = call_groq(prompt)
    if recs:
        recs = validate_recs(recs)
        if recs:
            logger.success("✅ {} → {} recs from Groq", airport_code, len(recs))
            store_recommendations(airport_code, recs)
            return recs

    # Final fallback
    logger.warning("Both AI providers failed for {} — using rule-based fallback", airport_code)
    recs = generate_fallback(airport_code)
    store_recommendations(airport_code, recs)
    return recs


def run_all_airports(limit: int = 10):
    init_db()
    airports = [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS][:limit]
    logger.info("🚀 AI recommendations — {} airports (Gemini → Groq fallback)", len(airports))
    all_recs = []
    for airport in airports:
        recs = generate_for_airport(airport["code"])
        all_recs.extend(recs)
        time.sleep(2)
    logger.success("🏁 Complete — {} recommendations", len(all_recs))
    return all_recs


def get_pending_recommendations(airport_code=None, limit=100):
    conn = get_connection()
    cur  = conn.cursor()
    if airport_code:
        cur.execute("""
            SELECT * FROM recommendations WHERE airport_code=? AND status='pending'
            ORDER BY CASE urgency WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT ?
        """, (airport_code, limit))
    else:
        cur.execute("""
            SELECT * FROM recommendations WHERE status='pending'
            ORDER BY CASE urgency WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--airport", help="Single airport e.g. ATL")
    parser.add_argument("--limit",   type=int, default=10)
    args = parser.parse_args()
    if args.airport:
        recs = generate_for_airport(args.airport)
        for r in recs:
            delta = r.get("price_delta", 0) or 0
            print(f"\n[{r['urgency'].upper()}] {r['car_category']} {'↑' if delta>0 else '↓' if delta<0 else '→'} ${abs(delta):.0f}/day")
            print(f"  {r['recommendation']}")
            print(f"  💡 {r['reasoning']}")
    else:
        run_all_airports(args.limit)    
