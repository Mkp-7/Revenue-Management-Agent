"""
dashboard/app.py — ABG Revenue Intelligence Dashboard
Run: streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import asyncio
from datetime import datetime
from agents.agent1_scraper import scrape_all_airports
from agents.agent2_demand import collect_all_demand_signals
from agents.agent3_recommendations import run_all_airports
from config.airports import TOP_50_AIRPORTS
from config.settings import TOP_10_AIRPORTS
from config.database import get_connection, init_db
from config.airports import TOP_50_AIRPORTS, COMPETITORS, CAR_CATEGORIES
from config.settings import TOP_10_AIRPORTS
from agents.agent1_scraper import get_latest_prices, get_anomalies
from agents.agent3_recommendations import get_pending_recommendations

st.set_page_config(
    page_title="ABG Revenue Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 40%, #fff0f9 100%) !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: white !important; border-right: 1px solid #e8eaf6 !important; box-shadow: 4px 0 24px rgba(99,102,241,0.08) !important; }
.main .block-container { padding: 1.5rem 2rem 3rem 2rem !important; max-width: 1400px !important; }
.hero { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%); border-radius: 24px; padding: 2.5rem 3rem; margin-bottom: 2rem; color: white; box-shadow: 0 20px 60px rgba(99,102,241,0.3); }
.hero-title { font-family: 'Space Grotesk', sans-serif !important; font-size: 2.4rem !important; font-weight: 700 !important; margin: 0 !important; }
.hero-sub { font-size: 1rem; opacity: 0.85; margin-top: 0.4rem; }
.hero-badge { display: inline-block; background: rgba(255,255,255,0.2); border-radius: 50px; padding: 0.25rem 1rem; font-size: 0.8rem; font-weight: 600; margin-bottom: 1rem; letter-spacing: 1px; text-transform: uppercase; }
.kpi-card { background: white; border-radius: 20px; padding: 1.5rem; box-shadow: 0 4px 24px rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.08); }
.stTabs [data-baseweb="tab-list"] { background: white !important; border-radius: 16px !important; padding: 0.4rem !important; box-shadow: 0 4px 24px rgba(99,102,241,0.08) !important; margin-bottom: 1.5rem !important; }
.stTabs [data-baseweb="tab"] { border-radius: 12px !important; padding: 0.6rem 1.4rem !important; font-weight: 600 !important; color: #6b7280 !important; border: none !important; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; box-shadow: 0 4px 12px rgba(99,102,241,0.35) !important; }
.rec-card { background: white; border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 0.75rem; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.rec-critical { border-left: 4px solid #ef4444; }
.rec-high     { border-left: 4px solid #f97316; }
.rec-medium   { border-left: 4px solid #eab308; }
.rec-low      { border-left: 4px solid #10b981; }
.badge-critical { background:#fee2e2; color:#dc2626; border-radius:50px; padding:0.2rem 0.75rem; font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
.badge-high     { background:#ffedd5; color:#ea580c; border-radius:50px; padding:0.2rem 0.75rem; font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
.badge-medium   { background:#fef9c3; color:#ca8a04; border-radius:50px; padding:0.2rem 0.75rem; font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
.badge-low      { background:#dcfce7; color:#16a34a; border-radius:50px; padding:0.2rem 0.75rem; font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important; }
.empty-state { text-align: center; padding: 3rem; color: #9ca3af; background: white; border-radius: 20px; box-shadow: 0 4px 24px rgba(99,102,241,0.06); }
</style>
""", unsafe_allow_html=True)

init_db()

CHART_BG = dict(paper_bgcolor="white", plot_bgcolor="#fafafa",
                font=dict(color="#1e1b4b", family="Inter"),
                margin=dict(l=20, r=20, t=40, b=20))

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚗 ABG Intelligence")
    st.markdown("*Revenue Management Platform*")
    st.divider()

    active_airports = [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS]
    airport_options = {f"{a['code']} — {a['city']}": a["code"] for a in active_airports}
    selected_label  = st.selectbox("📍 Airport", list(airport_options.keys()))
    selected_airport = airport_options[selected_label]

    st.divider()
    selected_category    = st.selectbox("Car Category", ["All"] + CAR_CATEGORIES)
    selected_competitors = st.multiselect("Competitors", COMPETITORS, default=COMPETITORS)

    st.divider()
    if st.button("▶ Run Pipeline", use_container_width=True):
        
    airports = [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS]
    with st.spinner("Step 1/3 — Generating prices..."):
        asyncio.run(scrape_all_airports(airports))
    st.toast("✅ Prices done")
    
    with st.spinner("Step 2/3 — Fetching demand signals..."):
        asyncio.run(collect_all_demand_signals(airports))
    st.toast("✅ Demand signals done")
    
    with st.spinner("Step 3/3 — Generating AI recommendations..."):
        run_all_airports(limit=10)
    st.toast("✅ Recommendations done")
    
    st.success("✅ Pipeline complete! Refreshing...")
    st.cache_data.clear()
    st.rerun()

    if st.button("↻ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"🕐 {datetime.now().strftime('%b %d · %H:%M')}")


# ── Load Data ──────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices(code):    return get_latest_prices(code, limit=1000)
@st.cache_data(ttl=60)
def load_recs(code):      return get_pending_recommendations(code)
@st.cache_data(ttl=60)
def load_anomalies():     return get_anomalies(limit=20)
@st.cache_data(ttl=60)
def load_all():           return get_latest_prices(None, limit=5000)

prices_data  = load_prices(selected_airport)
recs_data    = load_recs(selected_airport)
anomalies    = load_anomalies()
all_prices   = load_all()

prices_df    = pd.DataFrame(prices_data) if prices_data else pd.DataFrame()
all_df       = pd.DataFrame(all_prices)  if all_prices  else pd.DataFrame()

airport_info = next((a for a in TOP_50_AIRPORTS if a["code"] == selected_airport), {})
city         = airport_info.get("city", selected_airport)

# ── Hero ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-title">Revenue Intelligence Hub</div>
  <div class="hero-sub">{selected_airport} · {city} &nbsp;·&nbsp; 10 US Airports &nbsp;·&nbsp; 8 Competitors &nbsp;·&nbsp; AI-Powered (Groq)</div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────
comp_count   = prices_df["competitor"].nunique() if not prices_df.empty else 0
price_count  = len(prices_df)
num_recs     = len(recs_data)
critical_n   = sum(1 for r in recs_data if r.get("urgency") == "critical")
anomaly_n    = len(anomalies)
airports_n   = all_df["airport_code"].nunique() if not all_df.empty else 0

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.metric("🏢 Competitors",  comp_count,  delta="Tracked")
with c2: st.metric("💰 Price Records", f"{price_count:,}", delta="Latest")
with c3: st.metric("🤖 AI Recs",      num_recs,    delta=f"{critical_n} critical" if critical_n else None, delta_color="inverse")
with c4: st.metric("⚠️ Anomalies",    anomaly_n,   delta="Needs review" if anomaly_n else "All clear", delta_color="inverse" if anomaly_n else "normal")
with c5: st.metric("🗺️ Airports",     airports_n,  delta="In database")

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Price Heatmap",
    "🤖  AI Recommendations",
    "⚠️  Anomaly Alerts",
    "📈  Competitor Analysis",
    "🗺️  Network Overview",
])

# ── Tab 1: Heatmap ─────────────────────────────────────────────────
with tab1:
    st.markdown("### Competitor Price Matrix")
    if prices_df.empty:
        st.markdown('<div class="empty-state"><div style="font-size:3rem">📭</div><b>No data yet</b><br>Click ▶ Run Pipeline</div>', unsafe_allow_html=True)
    else:
        df = prices_df.copy()
        if selected_category != "All":
            df = df[df["car_category"] == selected_category]
        if selected_competitors:
            df = df[df["competitor"].isin(selected_competitors)]

        pivot = df.pivot_table(index="car_category", columns="competitor",
                               values="daily_rate", aggfunc="mean")
        pivot = pivot.reindex(index=[c for c in CAR_CATEGORIES if c in pivot.index])

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[c.upper() for c in pivot.index.tolist()],
            colorscale=[[0,"#dcfce7"],[0.5,"#fef9c3"],[1,"#fee2e2"]],
            text=[[f"${v:.0f}" if v==v else "—" for v in row] for row in pivot.values],
            texttemplate="%{text}", textfont={"size":14},
            hovertemplate="<b>%{y}</b> — %{x}<br><b>$%{z:.2f}/day</b><extra></extra>",
        ))
        fig.update_layout(title=f"Daily Rates at {selected_airport} ($/day)",
                         height=400, xaxis=dict(side="top"), **CHART_BG)
        st.plotly_chart(fig, use_container_width=True)

        stats = df.groupby("car_category")["daily_rate"].agg(["min","max","mean","count"]).round(2)
        stats.columns = ["Min $/day","Max $/day","Avg $/day","Competitors"]
        stats.index = [i.upper() for i in stats.index]
        st.dataframe(stats.style.format("${:.2f}", subset=["Min $/day","Max $/day","Avg $/day"]),
                    use_container_width=True)


# ── Tab 2: Recommendations ─────────────────────────────────────────
with tab2:
    st.markdown("### 🤖 AI Pricing Recommendations")
    st.caption(f"Groq · llama-3.3-70b-versatile · {selected_airport} · sorted by urgency")

    if not recs_data:
        st.markdown('<div class="empty-state"><div style="font-size:3rem">🤖</div><b>No recommendations yet</b><br>Run the pipeline to generate AI suggestions</div>', unsafe_allow_html=True)
    else:
        urgency_order = {"critical":0,"high":1,"medium":2,"low":3}
        for rec in sorted(recs_data, key=lambda x: urgency_order.get(x.get("urgency","low"),4)):
            urgency = rec.get("urgency","low")
            cat     = rec.get("car_category","unknown").upper()
            action  = rec.get("recommendation","")
            reason  = rec.get("reasoning","")
            delta   = rec.get("price_delta",0) or 0
            emojis  = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}

            if delta > 0:   delta_html = f'<span style="color:#10b981;font-weight:700">↑ +${delta:.0f}/day</span>'
            elif delta < 0: delta_html = f'<span style="color:#ef4444;font-weight:700">↓ −${abs(delta):.0f}/day</span>'
            else:           delta_html = '<span style="color:#94a3b8;font-weight:700">→ Hold</span>'

            st.markdown(f"""
<div class="rec-card rec-{urgency}">
  <div style="display:flex;align-items:center;justify-content:space-between">
    <div><span class="badge-{urgency}">{emojis[urgency]} {urgency}</span>
    &nbsp;<b style="color:#6366f1">{cat}</b></div>
    {delta_html}
  </div>
  <div style="font-weight:600;color:#1e1b4b;margin:0.4rem 0 0.2rem">{action}</div>
  <div style="color:#6b7280;font-size:0.85rem">💡 {reason}</div>
</div>""", unsafe_allow_html=True)

        if st.button("✅ Mark All Applied"):
            conn = get_connection()
            conn.execute("UPDATE recommendations SET status='applied' WHERE airport_code=?", (selected_airport,))
            conn.commit(); conn.close()
            st.cache_data.clear(); st.rerun()


# ── Tab 3: Anomalies ───────────────────────────────────────────────
with tab3:
    st.markdown("### ⚠️ Competitor Anomaly Alerts")
    st.caption("Price changes ≥20% flagged automatically")

    if not anomalies:
        st.success("✅ No anomalies — markets are stable.")
    else:
        for row in anomalies:
            is_spike  = row.get("direction") == "spike"
            pct       = row.get("pct_change", 0)
            old_p     = row.get("old_price", 0)
            new_p     = row.get("new_price", 0)
            pill_cls  = "badge-critical" if is_spike else "badge-low"
            icon      = "🔴 SPIKE ↑" if is_spike else "🟢 DROP ↓"

            st.markdown(f"""
<div class="rec-card" style="display:flex;align-items:center;gap:1rem">
  <span class="{pill_cls}">{icon} {pct:+.1f}%</span>
  <div>
    <b>{row.get('airport_code')} · {str(row.get('competitor','')).upper()} · {row.get('car_category','')}</b><br>
    <span style="color:#6b7280;font-size:0.85rem">${old_p:.0f}/day → ${new_p:.0f}/day · {str(row.get('detected_at',''))[:16]}</span>
  </div>
</div>""", unsafe_allow_html=True)

        if st.button("✅ Acknowledge All"):
            conn = get_connection()
            conn.execute("UPDATE anomalies SET acknowledged=1")
            conn.commit(); conn.close()
            st.cache_data.clear(); st.rerun()


# ── Tab 4: Competitor Analysis ─────────────────────────────────────
with tab4:
    st.markdown(f"### 📈 Competitor Breakdown — {selected_airport}")

    if prices_df.empty:
        st.markdown('<div class="empty-state"><div style="font-size:3rem">📊</div><b>No data</b></div>', unsafe_allow_html=True)
    else:
        df = prices_df.copy()
        if selected_category != "All":
            df = df[df["car_category"] == selected_category]

        col1, col2 = st.columns(2)

        with col1:
            avg_comp = df.groupby("competitor")["daily_rate"].mean().sort_values()
            colors   = ["#6366f1","#8b5cf6","#a78bfa","#c4b5fd","#ddd6fe","#ede9fe","#f5f3ff","#faf5ff"]
            fig = go.Figure(go.Bar(
                x=avg_comp.values, y=avg_comp.index, orientation="h",
                marker_color=colors[:len(avg_comp)],
                text=[f"${v:.0f}" for v in avg_comp.values], textposition="outside",
            ))
            fig.update_layout(title="Avg Rate by Competitor", height=350,
                             xaxis=dict(tickprefix="$"), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            avg_cat = df.groupby("car_category")["daily_rate"].mean().sort_values(ascending=False)
            fig2 = go.Figure(go.Bar(
                x=[c.upper() for c in avg_cat.index], y=avg_cat.values,
                marker_color=colors[:len(avg_cat)],
                text=[f"${v:.0f}" for v in avg_cat.values], textposition="outside",
            ))
            fig2.update_layout(title="Avg Rate by Category", height=350,
                              yaxis=dict(tickprefix="$"), **CHART_BG)
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.box(df, x="car_category", y="daily_rate", color="competitor",
                      title="Price Distribution by Category",
                      labels={"daily_rate":"$/day","car_category":"Category"},
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        fig3.update_layout(height=420, **CHART_BG)
        st.plotly_chart(fig3, use_container_width=True)


# ── Tab 5: Network Overview ────────────────────────────────────────
with tab5:
    st.markdown("### 🗺️ Network Overview — All 10 Airports")

    if all_df.empty:
        st.markdown('<div class="empty-state"><div style="font-size:3rem">🗺️</div><b>No network data</b></div>', unsafe_allow_html=True)
    else:
        econ = all_df[all_df["car_category"]=="economy"].groupby("airport_code")["daily_rate"].mean().reset_index()
        econ.columns = ["code","avg_economy"]
        meta   = pd.DataFrame([a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS])
        merged = econ.merge(meta, on="code", how="inner")

        if not merged.empty:
            fig = px.scatter_geo(
                merged, lat="lat", lon="lon",
                size="avg_economy", color="avg_economy",
                hover_name="code",
                hover_data={"city":True,"state":True,"avg_economy":":.0f","lat":False,"lon":False},
                color_continuous_scale="RdYlGn_r",
                scope="usa",
                title="Average Economy Rate Across 10 Airports ($/day)",
                size_max=30,
            )
            fig.update_layout(
                paper_bgcolor="white",
                geo=dict(bgcolor="#f8faff", landcolor="#eef2ff",
                         lakecolor="#dbeafe", coastlinecolor="#c7d2fe"),
                font=dict(color="#1e1b4b"), height=500,
                margin=dict(l=0,r=0,t=40,b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🔴 Most Expensive**")
                top5 = merged.nlargest(5,"avg_economy")[["code","city","avg_economy"]]
                top5["avg_economy"] = top5["avg_economy"].map("${:.2f}".format)
                top5.columns = ["Airport","City","Avg $/day"]
                st.dataframe(top5, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("**🟢 Most Affordable**")
                bot5 = merged.nsmallest(5,"avg_economy")[["code","city","avg_economy"]]
                bot5["avg_economy"] = bot5["avg_economy"].map("${:.2f}".format)
                bot5.columns = ["Airport","City","Avg $/day"]
                st.dataframe(bot5, use_container_width=True, hide_index=True)
