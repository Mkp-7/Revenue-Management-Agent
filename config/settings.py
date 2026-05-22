"""
settings.py — Single source of truth for all agents.
Change airports here and every agent updates automatically.
"""

TOP_10_AIRPORTS = [
    "ATL", "LAX", "ORD", "DFW", "DEN",
    "JFK", "SFO", "LAS", "MCO", "MIA",
]

PICKUP_DAYS_AHEAD   = 7
SCRAPE_INTERVAL_HRS = 6
