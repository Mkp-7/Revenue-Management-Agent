# 🚗 ABG Revenue Intelligence Agent

> *An autonomous AI agent that monitors competitor car rental pricing across 10 major US airports, integrates real-time demand signals, and generates AI-powered pricing recommendations — replacing hours of manual analyst work with a 15-minute automated pipeline.*

[![GitHub Actions](https://img.shields.io/badge/Pipeline-GitHub%20Actions-2088FF?logo=github-actions)](https://github.com/Mkp-7/Revenue-Management-Agent/actions)
[![Groq AI](https://img.shields.io/badge/AI-Groq%20llama--3.3--70b-orange)](https://groq.com)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B)](https://streamlit.io)

---

## 🎯 What It Does

ABG's Revenue Management team manually checks competitor prices across airports every day — opening Expedia, Kayak, Hertz.com, building Excel reports, making gut calls. It takes hours across a 20-person team.

This agent does it automatically in 15 minutes.

```
┌─────────────────────────────────────────────────────┐
│          PIPELINE (runs every 6 hours)              │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
   ┌───────▼──────┐ ┌────▼──────┐ ┌────▼──────────┐
   │  Agent 1     │ │  Agent 2  │ │  Agent 3      │
   │  Competitor  │ │  Demand   │ │  AI Pricing   │
   │  Prices      │ │  Signals  │ │  Recs (Groq)  │
   │              │ │           │ │               │
   │ 8 competitors│ │ • Flights │ │ • llama-3.3   │
   │ 10 airports  │ │ • Events  │ │ • 70b model   │
   │ All categories│ │ • Weather │ │ • Urgency     │
   └──────┬───────┘ └────┬──────┘ └────┬──────────┘
          └──────────────┴──────────────┘
                         │
                  ┌──────▼──────┐
                  │   SQLite    │
                  │  pricing.db │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │  Streamlit  │
                  │  Dashboard  │
                  └─────────────┘
```

---

## 📊 Live Dashboard

5-tab Streamlit dashboard showing:

| Tab | What it shows |
|-----|--------------|
| 📊 Price Heatmap | Competitor rates by category across all airports |
| 🤖 AI Recommendations | Groq-generated pricing actions sorted by urgency |
| ⚠️ Anomaly Alerts | Competitor price changes ≥20% flagged automatically |
| 📈 Competitor Analysis | Bar charts, box plots, rate breakdowns |
| 🗺️ Network Overview | US map of economy rates across all 10 airports |

---

## 🛠️ Tech Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| AI Recommendations | Groq (llama-3.3-70b-versatile) | Free |
| Flight Demand | OpenSky Network API | Free |
| Events Data | Ticketmaster Discovery API | Free |
| Weather Forecasts | Open-Meteo API | Free |
| Dashboard | Streamlit | Free |
| Database | SQLite | Free |
| Scheduler | GitHub Actions | Free |
| Language | Python 3.11 | Free |

**Total monthly cost: $0**

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Mkp-7/Revenue-Management-Agent.git
cd Revenue-Management-Agent
pip install -r requirements.txt
```

### 2. Set Up API Keys

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_key          # console.groq.com — free
TICKETMASTER_API_KEY=your_key  # developer.ticketmaster.com — free
OPENSKY_USERNAME=              # optional — opensky-network.org
OPENSKY_PASSWORD=              # optional
```

### 3. Run Pipeline

```bash
python orchestrator.py --once
```

### 4. Launch Dashboard

```bash
streamlit run dashboard/app.py
```

Open **http://localhost:8501**

---

## 🏗️ Project Structure

```
Revenue-Management-Agent/
├── agents/
│   ├── agent1_scraper.py          # Competitor price engine
│   ├── agent2_demand.py           # Flight + event + weather signals
│   └── agent3_recommendations.py  # Groq AI pricing recommendations
├── config/
│   ├── airports.py                # 50 US airports with ICAO codes
│   ├── database.py                # SQLite schema
│   └── settings.py                # Shared config (airports list etc.)
├── dashboard/
│   └── app.py                     # Streamlit 5-tab dashboard
├── .github/workflows/
│   └── pipeline.yml               # GitHub Actions — runs every 6h
├── orchestrator.py                # Master pipeline runner
├── requirements.txt
└── .env.example
```

---

## ✈️ Airports Covered

| Code | City | Code | City |
|------|------|------|------|
| ATL | Atlanta | JFK | New York |
| LAX | Los Angeles | SFO | San Francisco |
| ORD | Chicago | LAS | Las Vegas |
| DFW | Dallas | MCO | Orlando |
| DEN | Denver | MIA | Miami |

---

## 🏢 Competitors Tracked

Hertz · Avis · Enterprise · National · Alamo · Budget · Dollar · Thrifty

---

## 🤖 AI Recommendations

Groq (llama-3.3-70b-versatile) analyzes competitor prices + demand signals and outputs:

```
[HIGH] ECONOMY ↑ +$8/day
Raise economy rates by $8 at ATL — Braves game (45,000 attendance) driving demand spike.

[CRITICAL] SUV ↑ +$22/day  
Raise SUV rates 20% at MIA — Hurricane warning forecast drives last-minute rental surge.

[MEDIUM] COMPACT ↓ −$5/day
Cut compact rates at ORD — Budget undercutting market by 18%, volume risk.
```

---

## ⚙️ GitHub Actions

Pipeline auto-runs every 6 hours on GitHub's servers — free forever.

To trigger manually: **Actions → ABG Pricing Intelligence Pipeline → Run workflow**

Add these secrets under **Settings → Secrets → Actions**:
- `GROQ_API_KEY`
- `TICKETMASTER_API_KEY`
- `OPENSKY_USERNAME` (optional)
- `OPENSKY_PASSWORD` (optional)

---

## 💼 Built For

# 🚗 ABG Revenue Intelligence Agent

> *An autonomous AI agent that monitors competitor car rental pricing across 10 major US airports, integrates real-time demand signals, and generates AI-powered pricing recommendations — replacing hours of manual analyst work with a 15-minute automated pipeline.*

[![GitHub Actions](https://img.shields.io/badge/Pipeline-GitHub%20Actions-2088FF?logo=github-actions)](https://github.com/Mkp-7/Revenue-Management-Agent/actions)
[![Groq AI](https://img.shields.io/badge/AI-Groq%20llama--3.3--70b-orange)](https://groq.com)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 What It Does

ABG's Revenue Management team manually checks competitor prices across airports every day — opening Expedia, Kayak, Hertz.com, building Excel reports, making gut calls. It takes hours across a 20-person team.

This agent does it automatically in 15 minutes.

```
┌─────────────────────────────────────────────────────┐
│          PIPELINE (runs every 6 hours)              │
└──────────┬──────────────┬──────────────┬────────────┘
           │              │              │
   ┌───────▼──────┐ ┌────▼──────┐ ┌────▼──────────┐
   │  Agent 1     │ │  Agent 2  │ │  Agent 3      │
   │  Competitor  │ │  Demand   │ │  AI Pricing   │
   │  Prices      │ │  Signals  │ │  Recs (Groq)  │
   │              │ │           │ │               │
   │ 8 competitors│ │ • Flights │ │ • llama-3.3   │
   │ 10 airports  │ │ • Events  │ │ • 70b model   │
   │ All categories│ │ • Weather │ │ • Urgency     │
   └──────┬───────┘ └────┬──────┘ └────┬──────────┘
          └──────────────┴──────────────┘
                         │
                  ┌──────▼──────┐
                  │   SQLite    │
                  │  pricing.db │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │  Streamlit  │
                  │  Dashboard  │
                  └─────────────┘
```

---

## 📊 Live Dashboard

5-tab Streamlit dashboard showing:

| Tab | What it shows |
|-----|--------------|
| 📊 Price Heatmap | Competitor rates by category across all airports |
| 🤖 AI Recommendations | Groq-generated pricing actions sorted by urgency |
| ⚠️ Anomaly Alerts | Competitor price changes ≥20% flagged automatically |
| 📈 Competitor Analysis | Bar charts, box plots, rate breakdowns |
| 🗺️ Network Overview | US map of economy rates across all 10 airports |

---

## 🛠️ Tech Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| AI Recommendations | Groq (llama-3.3-70b-versatile) | Free |
| Flight Demand | OpenSky Network API | Free |
| Events Data | Ticketmaster Discovery API | Free |
| Weather Forecasts | Open-Meteo API | Free |
| Dashboard | Streamlit | Free |
| Database | SQLite | Free |
| Scheduler | GitHub Actions | Free |
| Language | Python 3.11 | Free |

**Total monthly cost: $0**

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Mkp-7/Revenue-Management-Agent.git
cd Revenue-Management-Agent
pip install -r requirements.txt
```

### 2. Set Up API Keys

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_key          # console.groq.com — free
TICKETMASTER_API_KEY=your_key  # developer.ticketmaster.com — free
OPENSKY_USERNAME=              # optional — opensky-network.org
OPENSKY_PASSWORD=              # optional
```

### 3. Run Pipeline

```bash
python orchestrator.py --once
```

### 4. Launch Dashboard

```bash
streamlit run dashboard/app.py
```

Open **http://localhost:8501**

---

## 🏗️ Project Structure

```
Revenue-Management-Agent/
├── agents/
│   ├── agent1_scraper.py          # Competitor price engine
│   ├── agent2_demand.py           # Flight + event + weather signals
│   └── agent3_recommendations.py  # Groq AI pricing recommendations
├── config/
│   ├── airports.py                # 50 US airports with ICAO codes
│   ├── database.py                # SQLite schema
│   └── settings.py                # Shared config (airports list etc.)
├── dashboard/
│   └── app.py                     # Streamlit 5-tab dashboard
├── .github/workflows/
│   └── pipeline.yml               # GitHub Actions — runs every 6h
├── orchestrator.py                # Master pipeline runner
├── requirements.txt
└── .env.example
```

---

## ✈️ Airports Covered

| Code | City | Code | City |
|------|------|------|------|
| ATL | Atlanta | JFK | New York |
| LAX | Los Angeles | SFO | San Francisco |
| ORD | Chicago | LAS | Las Vegas |
| DFW | Dallas | MCO | Orlando |
| DEN | Denver | MIA | Miami |

---

## 🏢 Competitors Tracked

Hertz · Avis · Enterprise · National · Alamo · Budget · Dollar · Thrifty

---

## 🤖 AI Recommendations

Groq (llama-3.3-70b-versatile) analyzes competitor prices + demand signals and outputs:

```
[HIGH] ECONOMY ↑ +$8/day
Raise economy rates by $8 at ATL — Braves game (45,000 attendance) driving demand spike.

[CRITICAL] SUV ↑ +$22/day  
Raise SUV rates 20% at MIA — Hurricane warning forecast drives last-minute rental surge.

[MEDIUM] COMPACT ↓ −$5/day
Cut compact rates at ORD — Budget undercutting market by 18%, volume risk.
```

---

## ⚙️ GitHub Actions

Pipeline auto-runs every 6 hours on GitHub's servers — free forever.

To trigger manually: **Actions → ABG Pricing Intelligence Pipeline → Run workflow**

Add these secrets under **Settings → Secrets → Actions**:
- `GROQ_API_KEY`
- `TICKETMASTER_API_KEY`
- `OPENSKY_USERNAME` (optional)
- `OPENSKY_PASSWORD` (optional)

---

## 💼 Use Case

Built to demonstrate how autonomous AI agents can replace manual revenue management workflows in the car rental industry. It demonstrates:

- Autonomous multi-agent AI architecture
- Real-time data pipeline design
- Revenue management domain knowledge
- Full-stack development (Python, SQLite, Streamlit, GitHub Actions)
- Production-ready code quality

> *"The same workflow analysts do manually in 3 hours, this does in 15 minutes."*
