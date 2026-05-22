"""
database.py — SQLite schema and connection manager.
"""

import sqlite3
import os
from pathlib import Path
from loguru import logger

DB_PATH = os.getenv("DB_PATH", "data/pricing.db")


def get_connection() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitor_prices (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            scraped_at    TEXT    NOT NULL,
            airport_code  TEXT    NOT NULL,
            competitor    TEXT    NOT NULL,
            car_category  TEXT    NOT NULL,
            daily_rate    REAL,
            pickup_date   TEXT,
            source_url    TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS flight_demand (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at    TEXT    NOT NULL,
            airport_code  TEXT    NOT NULL,
            flight_date   TEXT    NOT NULL,
            arrivals      INTEGER DEFAULT 0,
            departures    INTEGER DEFAULT 0,
            total_flights INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at           TEXT    NOT NULL,
            airport_code         TEXT    NOT NULL,
            event_name           TEXT,
            event_date           TEXT,
            event_type           TEXT,
            venue                TEXT,
            expected_attendance  INTEGER,
            distance_miles       REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_forecasts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at       TEXT    NOT NULL,
            airport_code     TEXT    NOT NULL,
            forecast_date    TEXT    NOT NULL,
            condition        TEXT,
            precipitation_mm REAL,
            wind_speed_kmh   REAL,
            temp_max_c       REAL,
            temp_min_c       REAL,
            is_severe        INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at    TEXT    NOT NULL,
            airport_code  TEXT    NOT NULL,
            car_category  TEXT,
            recommendation TEXT   NOT NULL,
            reasoning     TEXT,
            urgency       TEXT    CHECK(urgency IN ('low','medium','high','critical')),
            price_delta   REAL,
            status        TEXT    DEFAULT 'pending'
                              CHECK(status IN ('pending','applied','dismissed'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at   TEXT    NOT NULL,
            airport_code  TEXT    NOT NULL,
            competitor    TEXT    NOT NULL,
            car_category  TEXT,
            old_price     REAL,
            new_price     REAL,
            pct_change    REAL,
            direction     TEXT    CHECK(direction IN ('spike','drop')),
            acknowledged  INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Database initialized at {}", DB_PATH)


if __name__ == "__main__":
    init_db()
