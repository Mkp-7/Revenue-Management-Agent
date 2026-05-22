"""
orchestrator.py — Master Pipeline Runner
Runs all 3 agents for the same 10 airports consistently.
"""

import os
import sys
import asyncio
import argparse
import schedule
import time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from config.database import init_db
from config.airports import TOP_50_AIRPORTS
from config.settings import TOP_10_AIRPORTS, SCRAPE_INTERVAL_HRS
from agents.agent1_scraper import scrape_all_airports
from agents.agent2_demand import collect_all_demand_signals
from agents.agent3_recommendations import run_all_airports

load_dotenv()

logger.remove()
logger.add(sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True)
logger.add("logs/orchestrator.log", rotation="10 MB", retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

AIRPORTS = [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS]


async def run_pipeline():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 ABG PRICING INTELLIGENCE PIPELINE")
    logger.info("   Time: {} | Airports: {}", start.isoformat(), len(AIRPORTS))
    logger.info("=" * 60)

    logger.info("\n📦 STEP 1/3 — Competitor Price Engine")
    await scrape_all_airports(AIRPORTS)

    logger.info("\n📡 STEP 2/3 — Demand Signal Monitor")
    await collect_all_demand_signals(AIRPORTS)

    logger.info("\n🤖 STEP 3/3 — AI Pricing Recommendations")
    run_all_airports(limit=10)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.success("✅ PIPELINE COMPLETE in {:.0f}s", elapsed)
    logger.info("   Next run in {} hours", SCRAPE_INTERVAL_HRS)
    logger.info("=" * 60)


def run_pipeline_sync():
    asyncio.run(run_pipeline())


def run_scheduled():
    init_db()
    logger.info("⏰ Scheduler — every {} hours", SCRAPE_INTERVAL_HRS)
    run_pipeline_sync()
    schedule.every(SCRAPE_INTERVAL_HRS).hours.do(run_pipeline_sync)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    init_db()
    if args.once:
        run_pipeline_sync()
    else:
        run_scheduled()
