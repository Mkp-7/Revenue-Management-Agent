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
from datetime import datetime
from config.database import get_connection, init_db
from config.airports import TOP_50_AIRPORTS, COMPETITORS, CAR_CATEGORIES
from config.settings import TOP_10_AIRPORTS
from agents.agent1_scraper import get_latest_prices, get_anomalies
from agents.agent3_recommendations import get_pending_recommendations

st.set_page_config(
    page_title="Revenue Intelligence Hub",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

/* ── Page background ── */
[data-testid="stAppViewContainer"] {
    background: #f8f9fe !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1e1b4b !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #e0e7ff !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label { color: #a5b4fc !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div {
    background: #2d2a6e !important;
    border: 1px solid #4338ca !important;
    border-radius: 10px !important;
    color: white !important;
}
[data-testid="stSidebar"] hr { border-color: #3730a3 !important; }

/* ── Main content ── */
.main .block-container { padding: 1.5rem 2rem 3rem 2rem !important; max-width: 1400px !important; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    color: white;
    box-shadow: 0 8px 32px rgba(67,56,202,0.25);
}
.hero-badge {
    display: inline-block;
    background: rgba(165,180,252,0.2);
    border: 1px solid rgba(165,180,252,0.4);
    border-radius: 50px;
    padding: 0.2rem 0.9rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.8rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #a5b4fc;
}
.hero-title {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.3rem 0 !important;
    color: white !important;
}
.hero-sub { font-size: 0.95rem; color: #a5b4fc; margin: 0; }

/* ── KPI Cards ── */
.kpi-row { display: grid; grid-template-columns: repeat(5,1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi { background: white; border-radius: 16px; padding: 1.25rem 1.5rem; box-shadow: 0 2px 12px rgba(67,56,202,0.07); border: 1px solid #e0e7ff; }
.kpi-icon { font-size: 1.4rem; margin-bottom: 0.4rem; }
.kpi-val { font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700; color: #1e1b4b; line-height: 1; }
.kpi-lbl { font-size: 0.72rem; color: #6366f1; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 0.25rem; }
.kpi-sub { font-size: 0.72rem; color: #94a3b8; margin-top: 0.2rem; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: white !important;
    border-radius: 14px !important;
    padding: 0.35rem !important;
    box-shadow: 0 2px 12px rgba(67,56,202,0.07) !important;
    border: 1px solid #e0e7ff !important;
    gap: 0.2rem !important;
    margin-bottom: 1.25rem !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 0.55rem 1.2rem !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    color: #6b7280 !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #1e1b4b !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(30,27,75,0.25) !important;
}

/* ── Rec Cards ── */
.rec { background: white; border-radius: 14px; padding: 1.1rem 1.4rem; margin-bottom: 0.6rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #e5e7eb; }
.rec.critical { border-left-color: #dc2626; background: linear-gradient(135deg,#fff5f5,white); }
.rec.high     { border-left-color: #ea580c; background: linear-gradient(135deg,#fff8f0,white); }
.rec.medium   { border-left-color: #ca8a04; background: linear-gradient(135deg,#fefce8,white); }
.rec.low      { border-left-color: #16a34a; background: linear-gradient(135deg,#f0fdf4,white); }
.badge { border-radius: 50px; padding: 0.18rem 0.7rem; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
.badge.critical { background:#fee2e2; color:#dc2626; }
.badge.high     { background:#ffedd5; color:#ea580c; }
.badge.medium   { background:#fef9c3; color:#ca8a04; }
.badge.low      { background:#dcfce7; color:#16a34a; }
.rec-action { font-size: 0.95rem; font-weight: 600; color: #1e1b4b; margin: 0.35rem 0 0.2rem; }
.rec-reason { font-size: 0.82rem; color: #6b7280; }

/* ── Anomaly ── */
.anomaly { background: white; border-radius: 14px; padding: 1rem 1.4rem; margin-bottom: 0.6rem; display: flex; align-items: center; gap: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

/* ── Buttons ── */
.stButton > button {
    background: #4338ca !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 1.2rem !important;
    box-shadow: 0 4px 12px rgba(67,56,202,0.25) !important;
}
.stButton > button:hover { background: #3730a3 !important; }

/* ── Empty state ── */
.empty { text-align:center; padding:3rem; color:#9ca3af; background:white; border-radius:16px; box-shadow:0 2px 12px rgba(67,56,202,0.07); }

/* ── Sidebar title ── */
.sidebar-brand { font-family:'Space Grotesk',sans-serif; font-size:1.1rem; font-weight:700; color:white; margin-bottom:0.1rem; }
.sidebar-sub { font-size:0.72rem; color:#a5b4fc; margin-bottom:1.2rem; }

/* ── Last updated ── */
.last-updated { font-size:0.72rem; color:#a5b4fc; text-align:center; padding-top:0.5rem; }
</style>
""", unsafe_allow_html=True)

init_db()

CHART_BG = dict(
    paper_bgcolor="white",
    plot_bgcolor="#fafafe",
    font=dict(color="#1e1b4b", family="Inter"),
    margin=dict(l=20, r=20, t=40, b=20),
)

INDIGO_SCALE = [
    "#eef2ff", "#e0e7ff", "#c7d2fe", "#a5b4fc",
    "#818cf8", "#6366f1", "#4f46e5", "#4338ca",
    "#3730a3", "#312e81",
]

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🚗 Revenue Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Competitor Pricing Platform</div>', unsafe_allow_html=True)
    st.divider()

    active   = [a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS]
    opts     = {f"{a['code']} — {a['city']}": a["code"] for a in active}
    label    = st.selectbox("Airport", list(opts.keys()))
    selected = opts[label]

    st.divider()
    sel_cat  = st.selectbox("Category", ["All"] + CAR_CATEGORIES)
    sel_comp = st.multiselect("Competitors", COMPETITORS, default=COMPETITORS)

    st.divider()
    if st.button("↻ Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f'<div class="last-updated">Updated: {datetime.now().strftime("%b %d · %H:%M")}</div>',
                unsafe_allow_html=True)


# ── Load Data ──────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices(code):  return get_latest_prices(code, limit=1000)
@st.cache_data(ttl=60)
def load_recs(code):    return get_pending_recommendations(code)
@st.cache_data(ttl=60)
def load_anomalies():   return get_anomalies(limit=20)
@st.cache_data(ttl=60)
def load_all():         return get_latest_prices(None, limit=5000)

prices_data = load_prices(selected)
recs_data   = load_recs(selected)
anomalies   = load_anomalies()
all_prices  = load_all()

prices_df   = pd.DataFrame(prices_data) if prices_data else pd.DataFrame()
all_df      = pd.DataFrame(all_prices)  if all_prices  else pd.DataFrame()
airport_info = next((a for a in TOP_50_AIRPORTS if a["code"] == selected), {})
city         = airport_info.get("city", selected)


# ── Hero ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-badge">&#9889; Live Intelligence</div>
  <div class="hero-title">Revenue Intelligence Hub</div>
  <div class="hero-sub">{selected} &nbsp;&middot;&nbsp; {city} &nbsp;&middot;&nbsp;
    10 US Airports &nbsp;&middot;&nbsp; 8 Competitors &nbsp;&middot;&nbsp; AI by Groq</div>
</div>
""", unsafe_allow_html=True)


# ── KPIs ───────────────────────────────────────────────────────────
comp_n    = prices_df["competitor"].nunique() if not prices_df.empty else 0
price_n   = len(prices_df)
rec_n     = len(recs_data)
critical_n = sum(1 for r in recs_data if r.get("urgency") == "critical")
anomaly_n = len(anomalies)
airport_n = all_df["airport_code"].nunique() if not all_df.empty else 0

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi"><div class="kpi-icon">&#127970;</div>
    <div class="kpi-val">{comp_n}</div>
    <div class="kpi-lbl">Competitors</div>
    <div class="kpi-sub">Tracked at {selected}</div></div>
  <div class="kpi"><div class="kpi-icon">&#128176;</div>
    <div class="kpi-val">{price_n:,}</div>
    <div class="kpi-lbl">Price Records</div>
    <div class="kpi-sub">Latest scrape</div></div>
  <div class="kpi"><div class="kpi-icon">&#129302;</div>
    <div class="kpi-val">{rec_n}</div>
    <div class="kpi-lbl">AI Recs</div>
    <div class="kpi-sub">{critical_n} critical</div></div>
  <div class="kpi"><div class="kpi-icon">&#9888;</div>
    <div class="kpi-val">{anomaly_n}</div>
    <div class="kpi-lbl">Anomalies</div>
    <div class="kpi-sub">{'Needs review' if anomaly_n else 'All clear'}</div></div>
  <div class="kpi"><div class="kpi-icon">&#128205;</div>
    <div class="kpi-val">{airport_n}</div>
    <div class="kpi-lbl">Airports</div>
    <div class="kpi-sub">In database</div></div>
</div>
""", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "&#128202;  Price Heatmap",
    "&#129302;  AI Recommendations",
    "&#9888;  Anomaly Alerts",
    "&#128200;  Competitor Analysis",
    "&#128205;  Network Overview",
])


# ── Tab 1: Heatmap ─────────────────────────────────────────────────
with tab1:
    st.markdown("### Competitor Price Matrix")
    st.caption(f"Daily rental rates by category at {selected} — darker = more expensive")

    if prices_df.empty:
        st.markdown('<div class="empty"><div style="font-size:2.5rem">&#128235;</div><b>No data yet</b><br><small>Run the GitHub Actions pipeline first</small></div>', unsafe_allow_html=True)
    else:
        df = prices_df.copy()
        if sel_cat != "All":
            df = df[df["car_category"] == sel_cat]
        if sel_comp:
            df = df[df["competitor"].isin(sel_comp)]

        pivot = df.pivot_table(index="car_category", columns="competitor",
                               values="daily_rate", aggfunc="mean")
        pivot = pivot.reindex(index=[c for c in CAR_CATEGORIES if c in pivot.index])

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[c.upper() for c in pivot.index.tolist()],
            colorscale=[
                [0.0,  "#eef2ff"],
                [0.15, "#c7d2fe"],
                [0.3,  "#a5b4fc"],
                [0.45, "#818cf8"],
                [0.6,  "#6366f1"],
                [0.75, "#4f46e5"],
                [0.9,  "#4338ca"],
                [1.0,  "#312e81"],
            ],
            text=[[f"${v:.0f}" if v==v else "—" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont={"size": 13, "color": "white"},
            hovertemplate="<b>%{y}</b> — %{x}<br><b>$%{z:.2f}/day</b><extra></extra>",
            colorbar=dict(title="$/day", tickprefix="$",
                         tickfont=dict(color="#1e1b4b")),
        ))
        fig.update_layout(
            title=dict(text=f"Daily Rates — {selected}", font=dict(size=15, color="#1e1b4b")),
            height=420, xaxis=dict(side="top", tickfont=dict(size=12)),
            yaxis=dict(tickfont=dict(size=12)), **CHART_BG,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Market Stats")
        stats = df.groupby("car_category")["daily_rate"].agg(["min","max","mean","count"]).round(2)
        stats.columns = ["Min $/day","Max $/day","Avg $/day","Competitors"]
        stats.index   = [i.upper() for i in stats.index]
        st.dataframe(
            stats.style
                .format("${:.2f}", subset=["Min $/day","Max $/day","Avg $/day"])
            use_container_width=True,
        )


# ── Tab 2: Recommendations ─────────────────────────────────────────
with tab2:
    st.markdown("### AI Pricing Recommendations")
    st.caption(f"Groq · llama-3.1-8b-instant · {selected} · sorted by urgency")

    if not recs_data:
        st.markdown('<div class="empty"><div style="font-size:2.5rem">&#129302;</div><b>No recommendations yet</b><br><small>Run the GitHub Actions pipeline to generate AI suggestions</small></div>', unsafe_allow_html=True)
    else:
        urgency_order = {"critical":0,"high":1,"medium":2,"low":3}
        for rec in sorted(recs_data, key=lambda x: urgency_order.get(x.get("urgency","low"),4)):
            urgency = rec.get("urgency","low")
            cat     = rec.get("car_category","unknown").upper()
            action  = rec.get("recommendation","")
            reason  = rec.get("reasoning","")
            delta   = rec.get("price_delta",0) or 0
            emojis  = {"critical":"&#128308;","high":"&#128992;","medium":"&#128993;","low":"&#128994;"}

            if delta > 0:
                delta_html = f'<span style="color:#16a34a;font-weight:700;font-size:1rem">&#8679; +${delta:.0f}/day</span>'
            elif delta < 0:
                delta_html = f'<span style="color:#dc2626;font-weight:700;font-size:1rem">&#8681; -${abs(delta):.0f}/day</span>'
            else:
                delta_html = '<span style="color:#94a3b8;font-weight:700;font-size:1rem">&#8212; Hold</span>'

            st.markdown(f"""
<div class="rec {urgency}">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
    <div>
      <span class="badge {urgency}">{emojis.get(urgency,'')} {urgency.upper()}</span>
      &nbsp;<b style="color:#4338ca;font-size:0.9rem">{cat}</b>
    </div>
    {delta_html}
  </div>
  <div class="rec-action">{action}</div>
  <div class="rec-reason">&#128161; {reason}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("&#10003; Mark All Applied"):
            conn = get_connection()
            conn.execute("UPDATE recommendations SET status='applied' WHERE airport_code=?", (selected,))
            conn.commit(); conn.close()
            st.cache_data.clear(); st.rerun()


# ── Tab 3: Anomalies ───────────────────────────────────────────────
with tab3:
    st.markdown("### Competitor Anomaly Alerts")
    st.caption("Price changes ≥20% flagged automatically across all airports")

    if not anomalies:
        st.success("&#10003; No anomalies detected — markets are stable.")
    else:
        for row in anomalies:
            is_spike = row.get("direction") == "spike"
            pct      = row.get("pct_change", 0)
            old_p    = row.get("old_price", 0)
            new_p    = row.get("new_price", 0)
            pill_bg  = "#fee2e2" if is_spike else "#dcfce7"
            pill_col = "#dc2626" if is_spike else "#16a34a"
            icon     = "&#8679; SPIKE" if is_spike else "&#8681; DROP"

            st.markdown(f"""
<div class="anomaly">
  <span style="background:{pill_bg};color:{pill_col};border-radius:50px;padding:0.3rem 0.9rem;font-weight:700;font-size:0.85rem;white-space:nowrap">
    {icon} {pct:+.1f}%
  </span>
  <div>
    <b style="color:#1e1b4b">{row.get('airport_code')} &middot; {str(row.get('competitor','')).upper()} &middot; {row.get('car_category','')}</b><br>
    <span style="color:#6b7280;font-size:0.82rem">${old_p:.0f}/day &rarr; ${new_p:.0f}/day &nbsp;&middot;&nbsp; {str(row.get('detected_at',''))[:16]}</span>
  </div>
</div>""", unsafe_allow_html=True)

        if st.button("&#10003; Acknowledge All"):
            conn = get_connection()
            conn.execute("UPDATE anomalies SET acknowledged=1")
            conn.commit(); conn.close()
            st.cache_data.clear(); st.rerun()


# ── Tab 4: Competitor Analysis ─────────────────────────────────────
with tab4:
    st.markdown(f"### Competitor Breakdown — {selected}")

    if prices_df.empty:
        st.markdown('<div class="empty"><div style="font-size:2.5rem">&#128200;</div><b>No data</b></div>', unsafe_allow_html=True)
    else:
        df = prices_df.copy()
        if sel_cat != "All":
            df = df[df["car_category"] == sel_cat]

        col1, col2 = st.columns(2)

        with col1:
            avg_comp = df.groupby("competitor")["daily_rate"].mean().sort_values()
            colors   = INDIGO_SCALE[:len(avg_comp)]
            fig = go.Figure(go.Bar(
                x=avg_comp.values, y=avg_comp.index, orientation="h",
                marker_color=colors,
                text=[f"${v:.0f}" for v in avg_comp.values],
                textposition="outside",
                textfont=dict(color="#1e1b4b", size=12),
            ))
            fig.update_layout(title="Avg Rate by Competitor", height=380,
                             xaxis=dict(tickprefix="$"), **CHART_BG)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            avg_cat = df.groupby("car_category")["daily_rate"].mean().sort_values(ascending=False)
            fig2 = go.Figure(go.Bar(
                x=[c.upper() for c in avg_cat.index],
                y=avg_cat.values,
                marker_color=INDIGO_SCALE[:len(avg_cat)],
                text=[f"${v:.0f}" for v in avg_cat.values],
                textposition="outside",
                textfont=dict(color="#1e1b4b", size=12),
            ))
            fig2.update_layout(title="Avg Rate by Category", height=380,
                              yaxis=dict(tickprefix="$"), **CHART_BG)
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.box(
            df, x="car_category", y="daily_rate", color="competitor",
            title="Price Distribution by Category",
            labels={"daily_rate":"$/day","car_category":"Category"},
            color_discrete_sequence=[
                "#312e81","#3730a3","#4338ca","#4f46e5",
                "#6366f1","#818cf8","#a5b4fc","#c7d2fe",
            ],
        )
        fig3.update_layout(height=420, **CHART_BG)
        st.plotly_chart(fig3, use_container_width=True)


# ── Tab 5: Network Overview ────────────────────────────────────────
with tab5:
    st.markdown("### Network Overview — All 10 Airports")
    st.caption("Average economy car rate per airport")

    if all_df.empty:
        st.markdown('<div class="empty"><div style="font-size:2.5rem">&#128205;</div><b>No network data</b></div>', unsafe_allow_html=True)
    else:
        econ   = all_df[all_df["car_category"]=="economy"].groupby("airport_code")["daily_rate"].mean().reset_index()
        econ.columns = ["code","avg_economy"]
        meta   = pd.DataFrame([a for a in TOP_50_AIRPORTS if a["code"] in TOP_10_AIRPORTS])
        merged = econ.merge(meta, on="code", how="inner")

        if not merged.empty:
            fig = px.scatter_geo(
                merged, lat="lat", lon="lon",
                size="avg_economy", color="avg_economy",
                hover_name="code",
                hover_data={"city":True,"state":True,"avg_economy":":.0f","lat":False,"lon":False},
                color_continuous_scale=[
                    [0,"#c7d2fe"],[0.3,"#818cf8"],
                    [0.6,"#4f46e5"],[1.0,"#1e1b4b"],
                ],
                scope="usa",
                title="Average Economy Rate Across 10 Airports ($/day)",
                size_max=35,
            )
            fig.update_layout(
                paper_bgcolor="white",
                geo=dict(
                    bgcolor="#f8f9fe",
                    landcolor="#eef2ff",
                    lakecolor="#c7d2fe",
                    coastlinecolor="#a5b4fc",
                    showland=True, showlakes=True,
                ),
                font=dict(color="#1e1b4b"),
                height=500,
                margin=dict(l=0,r=0,t=40,b=0),
                coloraxis_colorbar=dict(title="$/day", tickprefix="$"),
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Most Expensive Markets**")
                top5 = merged.nlargest(5,"avg_economy")[["code","city","avg_economy"]]
                top5["avg_economy"] = top5["avg_economy"].map("${:.2f}".format)
                top5.columns = ["Airport","City","Avg $/day"]
                st.dataframe(top5, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("**Most Affordable Markets**")
                bot5 = merged.nsmallest(5,"avg_economy")[["code","city","avg_economy"]]
                bot5["avg_economy"] = bot5["avg_economy"].map("${:.2f}".format)
                bot5.columns = ["Airport","City","Avg $/day"]
                st.dataframe(bot5, use_container_width=True, hide_index=True)
