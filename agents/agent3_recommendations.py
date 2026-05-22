"""
agent3_recommendations.py — AI Pricing Recommendation Engine
Uses Groq (free) with llama-3.1-8b-instant.
Runs for same 10 airports as other agents.
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
from groq import Groq
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.airports import TOP_50_AIRPORTS
from config.settings import TOP_10_AIRPORTS
from config.database import get_connection, init_db
from agents.agent1_scraper import get_latest_prices
from agents.agent2_demand import get_demand_summary

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a revenue analyst for Avis Budget Group.
Output ONLY a JSON array of exactly 3 recommendations. No duplicates.
Each object:
{
  "car_category": "economy|compact|midsize|fullsize|suv|luxury|van|convertible",
  "recommendation": "one action sentence with specific dollar amount e.g. Raise economy by $8/day",
  "reasoning": "one sentence using specific data e.g. Braves game (45,000 attendance) drives demand",
  "urgency": "low|medium|high|critical",
  "price_delta": 8.50
}
RULES — violations will break the system:
- Exactly 3 items, no more, no less
- Each car_category must be different — no duplicates
- price_delta is always a dollar number, NEVER a percentage
- If holding price, price_delta = 0 and urgency = "low"
- Use real attendance numbers from events in your reasoning
- Return ONLY the JSON array, nothing else"""


def build_prompt(airport_code):
    prices = get_latest_prices(airport_code)
    demand = get_demand_summary(airport_code)

    # Build compact price summary
    price_by_cat = {}
    for row in prices:
        cat  = row["car_category"]
        comp = row["competitor"]
        rate = row["daily_rate"]
        if cat not in price_by_cat:
            price_by_cat[cat] = {}
        price_by_cat[cat][comp] = rate

    stats_str = "; ".join([
        f"{cat}: avg=${sum(v.values())/len(v):.0f} range=${min(v.values()):.0f}-${max(v.values()):.0f}"
        for cat, v in price_by_cat.items() if v
    ])

    events_str = "\n".join([
        f"- {e['event_name']} on {e['event_date']} at {e.get('venue','unknown venue')} "
        f"(type: {e.get('event_type','unknown')}, "
        f"attendance: {e.get('expected_attendance', 'unknown')})"
        for e in demand.get("upcoming_events", [])[:5]
    ]) or "none"

    severe_str = ", ".join([
        f"{w['forecast_date']} {w['condition']}"
        for w in demand.get("severe_weather_days", [])[:2]
    ]) or "none"

    peak = max([f["flights"] for f in demand.get("flights_by_day", [])], default=0)

    return f"""Airport: {airport_code}
Prices: {stats_str}
Upcoming events: {events_str}
Severe weather: {severe_str}
Peak daily flights: {peak}
Give 3 specific pricing recommendations for ABG (Avis/Budget) at {airport_code}."""


def generate_fallback(airport_code, context=None):
    """Rule-based recommendations when Groq is unavailable."""
    return [
        {
            "car_category":  "suv",
            "recommendation": f"Monitor SUV pricing at {airport_code} — market conditions stable.",
            "reasoning":     "No major demand triggers detected. Hold current pricing.",
            "urgency":       "low",
            "price_delta":   0.0,
        },
        {
            "car_category":  "economy",
            "recommendation": f"Economy segment at {airport_code} is price-sensitive — stay within 10% of market avg.",
            "reasoning":     "Economy drives volume. Competitive pricing protects market share.",
            "urgency":       "medium",
            "price_delta":   0.0,
        },
        {
            "car_category":  "midsize",
            "recommendation": f"Midsize rates at {airport_code} have room to grow — consider +$8/day.",
            "reasoning":     "Midsize is the highest-volume category with good margin opportunity.",
            "urgency":       "medium",
            "price_delta":   8.0,
        },
    ]


def store_recommendations(airport_code, recs):
    conn = get_connection()
    cur  = conn.cursor()
    now  = datetime.now().isoformat()
    # Delete previous recommendations for this airport before storing new ones
    cur.execute("DELETE FROM recommendations WHERE airport_code=?", (airport_code,))
    for rec in recs:
        cur.execute("""
            INSERT INTO recommendations
                (created_at, airport_code, car_category, recommendation,
                 reasoning, urgency, price_delta, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (now, airport_code, rec.get("car_category"),
              rec.get("recommendation"), rec.get("reasoning"),
              rec.get("urgency"), rec.get("price_delta")))
    conn.commit()
    conn.close()
    logger.success("💾 Stored {} recommendations for {}", len(recs), airport_code)


def generate_for_airport(airport_code):
    logger.info("🤖 Generating recommendations for {}...", airport_code)

    prices = get_latest_prices(airport_code)
    if not prices:
        logger.warning("No price data for {} — using fallback", airport_code)
        recs = generate_fallback(airport_code)
        store_recommendations(airport_code, recs)
        return recs

    if not GROQ_API_KEY:
        recs = generate_fallback(airport_code)
        store_recommendations(airport_code, recs)
        return recs

    for attempt in range(2):
        try:
            client   = Groq(api_key=GROQ_API_KEY)
            prompt   = build_prompt(airport_code)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )

            raw    = response.choices[0].message.content.strip()
            raw    = raw.replace("```json","").replace("```","").strip()
            parsed = json.loads(raw)
            recs   = parsed if isinstance(parsed, list) else parsed.get("recommendations", [])

            logger.success("✅ {} → {} recommendations from Groq", airport_code, len(recs))
            store_recommendations(airport_code, recs)
            return recs

        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                if attempt == 0:
                    logger.warning("Groq rate limit for {} — waiting 65s", airport_code)
                    time.sleep(65)
                    continue
            logger.error("Groq error for {}: {}", airport_code, str(e)[:100])
            recs = generate_fallback(airport_code)
            store_recommendations(airport_code, recs)
            return recs

    return generate_fallback(airport_code)


def run_all_airports(limit=5):
    init_db()
    airports = [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS][:limit]
    logger.info("🚀 AI recommendations — {} airports via Groq ({})", len(airports), GROQ_MODEL)
    all_recs = []
    for airport in airports:
        recs = generate_for_airport(airport["code"])
        all_recs.extend(recs)
        time.sleep(3)
    logger.success("🏁 Complete — {} recommendations generated", len(all_recs))
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
    else:
        run_all_airports(args.limit)
