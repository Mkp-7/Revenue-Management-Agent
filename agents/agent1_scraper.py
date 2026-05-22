"""
agent1_scraper.py — Competitor Price Intelligence Engine
=========================================================
Generates market-calibrated competitor pricing data based on:
  - Real market rate ranges (economy $32-68, SUV $72-165 etc.)
  - Competitor positioning (Hertz +14% premium, Thrifty -16% discount)
  - Airport market multipliers (JFK +38%, LAS -8%)
  - Day-of-week patterns (weekends +20%)
  - Seasonal demand (July peak +25%, January slow -12%)
  - Random market noise (±8%) for realistic variance
  - Demand spikes (15% probability per run)

In production: replace with Amadeus, OAG, or ATPCO data feeds.
ABG already has enterprise contracts with these providers.
"""

import os
import random
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.airports import TOP_50_AIRPORTS
from config.settings import TOP_10_AIRPORTS, PICKUP_DAYS_AHEAD
from config.database import get_connection, init_db

# ── Market Data ────────────────────────────────────────────────────

BASE_RATES = {
    "economy":     {"min": 32,  "max": 68,  "avg": 48},
    "compact":     {"min": 38,  "max": 78,  "avg": 56},
    "midsize":     {"min": 48,  "max": 95,  "avg": 68},
    "fullsize":    {"min": 58,  "max": 115, "avg": 82},
    "suv":         {"min": 72,  "max": 165, "avg": 108},
    "luxury":      {"min": 110, "max": 295, "avg": 175},
    "van":         {"min": 85,  "max": 155, "avg": 115},
    "convertible": {"min": 95,  "max": 225, "avg": 148},
}

AIRPORT_MULTIPLIERS = {
    "ATL": 1.00, "LAX": 1.28, "ORD": 1.12, "DFW": 1.05, "DEN": 1.02,
    "JFK": 1.38, "SFO": 1.32, "LAS": 0.92, "MCO": 0.88, "MIA": 1.18,
}

COMPETITOR_STRATEGY = {
    "hertz":      {"offset": +0.14, "categories": ["economy","compact","midsize","fullsize","suv","luxury"]},
    "avis":       {"offset": +0.09, "categories": ["economy","compact","midsize","fullsize","suv","luxury","convertible"]},
    "enterprise": {"offset": +0.04, "categories": ["economy","compact","midsize","fullsize","suv","van"]},
    "national":   {"offset": +0.06, "categories": ["compact","midsize","fullsize","suv","luxury"]},
    "alamo":      {"offset": -0.04, "categories": ["economy","compact","midsize","suv","van"]},
    "budget":     {"offset": -0.11, "categories": ["economy","compact","midsize","fullsize","suv","van"]},
    "dollar":     {"offset": -0.13, "categories": ["economy","compact","midsize","fullsize"]},
    "thrifty":    {"offset": -0.16, "categories": ["economy","compact","midsize","fullsize","suv"]},
}

SEASONAL_MULTIPLIERS = {
    1: 0.88, 2: 0.90, 3: 1.05, 4: 1.08,  5: 1.10,
    6: 1.22, 7: 1.25, 8: 1.20, 9: 1.02, 10: 1.05,
    11: 0.95, 12: 1.12,
}


def generate_market_prices(airport_code: str, pickup_date: str) -> list[dict]:
    """Generate realistic competitor prices for one airport."""
    results      = []
    airport_mult = AIRPORT_MULTIPLIERS.get(airport_code, 1.0)
    pickup_dt    = datetime.strptime(pickup_date, "%Y-%m-%d")
    seasonal_m   = SEASONAL_MULTIPLIERS.get(pickup_dt.month, 1.0)
    weekend_m    = 1.20 if pickup_dt.weekday() >= 4 else 1.0
    demand_spike = random.uniform(1.15, 1.35) if random.random() < 0.15 else 1.0

    for comp, strategy in COMPETITOR_STRATEGY.items():
        for cat in strategy["categories"]:
            base  = BASE_RATES[cat]
            price = (
                base["avg"]
                * airport_mult
                * seasonal_m
                * weekend_m
                * demand_spike
                * (1 + strategy["offset"])
                * (1 + random.uniform(-0.08, 0.08))
            )
            price = round(price) - 0.01 if random.random() > 0.3 else round(price)
            price = max(float(price), base["min"] * 0.75)

            results.append({
                "competitor":   comp,
                "car_category": cat,
                "daily_rate":   round(price, 2),
                "airport_code": airport_code,
            })

    return results


def detect_and_store_anomalies(conn, airport_code, new_prices):
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    for p in new_prices:
        cur.execute("""
            SELECT daily_rate FROM competitor_prices
            WHERE airport_code=? AND competitor=? AND car_category=?
            ORDER BY scraped_at DESC LIMIT 1
        """, (airport_code, p["competitor"], p["car_category"]))
        last = cur.fetchone()
        if not last or not last["daily_rate"] or last["daily_rate"] == 0:
            continue
        pct = (p["daily_rate"] - last["daily_rate"]) / last["daily_rate"] * 100
        if abs(pct) >= 20:
            cur.execute("""
                INSERT INTO anomalies
                    (detected_at, airport_code, competitor, car_category,
                     old_price, new_price, pct_change, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, airport_code, p["competitor"], p["car_category"],
                  last["daily_rate"], p["daily_rate"], round(pct, 2),
                  "spike" if pct > 0 else "drop"))
            logger.warning("⚠️ ANOMALY: {} {} {} {:+.1f}%",
                           airport_code, p["competitor"], p["car_category"], pct)
    conn.commit()


def store_prices(conn, prices, pickup_date):
    if not prices:
        return
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.executemany("""
        INSERT INTO competitor_prices
            (scraped_at, airport_code, competitor, car_category, daily_rate, pickup_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [(now, p["airport_code"], p["competitor"], p["car_category"],
           p["daily_rate"], pickup_date) for p in prices])
    conn.commit()


async def scrape_all_airports(target_airports=None):
    airports    = target_airports or [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS]
    pickup_date = (datetime.now() + timedelta(days=PICKUP_DAYS_AHEAD)).strftime("%Y-%m-%d")
    conn        = get_connection()
    init_db()

    logger.info("🚀 Price Intelligence Engine — {} airports — pickup: {}", len(airports), pickup_date)

    for i, airport in enumerate(airports):
        logger.info("[{}/{}] {} — {}", i+1, len(airports), airport["code"], airport["city"])
        prices = generate_market_prices(airport["code"], pickup_date)
        detect_and_store_anomalies(conn, airport["code"], prices)
        store_prices(conn, prices, pickup_date)
        comps = sorted(set(p["competitor"] for p in prices))
        logger.success("✅ {} → {} records | {}", airport["code"], len(prices), comps)

    conn.close()
    logger.success("🏁 Price engine complete — {} airports", len(airports))


def get_latest_prices(airport_code=None, limit=500):
    conn = get_connection()
    cur  = conn.cursor()
    if airport_code:
        cur.execute("""
            SELECT cp.* FROM competitor_prices cp
            INNER JOIN (
                SELECT airport_code, competitor, car_category, MAX(scraped_at) as latest
                FROM competitor_prices WHERE airport_code=?
                GROUP BY airport_code, competitor, car_category
            ) l ON cp.airport_code=l.airport_code
               AND cp.competitor=l.competitor
               AND cp.car_category=l.car_category
               AND cp.scraped_at=l.latest
            LIMIT ?
        """, (airport_code, limit))
    else:
        cur.execute("""
            SELECT cp.* FROM competitor_prices cp
            INNER JOIN (
                SELECT airport_code, competitor, car_category, MAX(scraped_at) as latest
                FROM competitor_prices
                GROUP BY airport_code, competitor, car_category
            ) l ON cp.airport_code=l.airport_code
               AND cp.competitor=l.competitor
               AND cp.car_category=l.car_category
               AND cp.scraped_at=l.latest
            LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_anomalies(unacknowledged_only=True, limit=50):
    conn  = get_connection()
    cur   = conn.cursor()
    where = "WHERE acknowledged=0" if unacknowledged_only else ""
    cur.execute(f"SELECT * FROM anomalies {where} ORDER BY detected_at DESC LIMIT ?", (limit,))
    rows  = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--airports", nargs="+")
    args = parser.parse_args()
    filtered = [a for a in TOP_50_AIRPORTS if a["code"] in args.airports] if args.airports else None
    asyncio.run(scrape_all_airports(filtered))
