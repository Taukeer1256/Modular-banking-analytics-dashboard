"""
app.py
------
Modular Banking Analytics Dashboard for Small Banks.
Answers: "Which banking module should a small bank launch first?"
Powered by real public data from NPCI and the Reserve Bank of India (RBI).
"""

import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scoring import (
    DEFAULT_WEIGHTS,
    normalize_weights,
    calculate_opportunity_scores,
    generate_recommendation,
)

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Modular Banking Strategy | Small Bank Decision Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "banking.db"
DATA_DIR = BASE_DIR / "data"

# ── Custom CSS for High-Aesthetic Dark Theme ──────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Global reset and font */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Background and containers */
    .stApp {
        background: radial-gradient(circle at 15% 15%, #0d1527 0%, #080c14 100%);
        color: #e2e8f0;
    }

    /* Metric cards with glassmorphism */
    .metric-card {
        background: linear-gradient(135deg, rgba(22, 31, 51, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.36);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.82rem;
        color: #10b981;
        margin-top: 6px;
        font-weight: 500;
    }

    /* Executive recommendation hero callout */
    .rec-box {
        background: linear-gradient(135deg, rgba(30, 41, 75, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-left: 5px solid #6366f1;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 28px;
        box-shadow: 0 10px 40px -10px rgba(99, 102, 241, 0.25);
    }
    .rec-title {
        font-size: 0.95rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #a5b4fc;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .rec-body {
        font-size: 1.05rem;
        line-height: 1.68;
        color: #f1f5f9;
        font-weight: 400;
    }

    /* Badges */
    .badge-real {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 9px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-benchmark {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 3px 9px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-block;
    }

    /* Subheaders and headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Sidebar adjustments */
    [data-testid="stSidebar"] {
        background-color: #0c121e;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    /* Code block font */
    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Database Helpers ──────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_db_data():
    """Loads cleaned tables and views from SQLite database."""
    if not DB_PATH.exists():
        import sys
        sys.path.insert(0, str(DATA_DIR))
        from clean_data import clean_upi, clean_rbi, get_banking_modules_benchmark, build_db
        upi_clean = clean_upi()
        rbi_clean = clean_rbi()
        modules_clean = get_banking_modules_benchmark()
        build_db(upi_clean, rbi_clean, modules_clean)

    conn = sqlite3.connect(DB_PATH)
    upi_monthly = pd.read_sql("SELECT * FROM upi_monthly ORDER BY period ASC", conn)
    upi_yoy = pd.read_sql("SELECT * FROM v_upi_yoy_growth", conn)
    upi_mom = pd.read_sql("SELECT * FROM v_upi_mom_change", conn)
    upi_seasonality = pd.read_sql("SELECT * FROM v_upi_seasonality", conn)
    channel_share = pd.read_sql("SELECT * FROM v_channel_share", conn)
    banking_modules = pd.read_sql("SELECT * FROM banking_modules", conn)
    conn.close()

    upi_monthly["period"] = pd.to_datetime(upi_monthly["period"])
    return {
        "upi_monthly": upi_monthly,
        "upi_yoy": upi_yoy,
        "upi_mom": upi_mom,
        "upi_seasonality": upi_seasonality,
        "channel_share": channel_share,
        "banking_modules": banking_modules,
    }


data_dict = load_db_data()
upi_df = data_dict["upi_monthly"]
modules_df = data_dict["banking_modules"]
channel_df = data_dict["channel_share"]
seasonality_df = data_dict["upi_seasonality"]
yoy_df = data_dict["upi_yoy"]


# ── Sidebar: Assumptions & Decision Weights Panel ─────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Strategy & Assumptions")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.85rem;'>"
        "Adjust criteria weights below to model different banking priorities. "
        "The engine normalizes weights and updates the recommendation in real-time."
        "</p>",
        unsafe_allow_html=True,
    )

    # Strategy Presets
    preset = st.selectbox(
        "Strategic Profile Presets",
        options=[
            "Prudent Small Bank (Balanced)",
            "Speed & Reach First (Acquisition)",
            "High-Yield Margin Chaser (Assets)",
            "Conservative Liquidity (Deposits)",
            "Custom Weights",
        ],
        index=0,
    )

    if preset == "Prudent Small Bank (Balanced)":
        init_growth = 25
        init_scale = 20
        init_ttm = 25
        init_margin = 15
        init_safety = 15
    elif preset == "Speed & Reach First (Acquisition)":
        init_growth = 35
        init_scale = 30
        init_ttm = 25
        init_margin = 5
        init_safety = 5
    elif preset == "High-Yield Margin Chaser (Assets)":
        init_growth = 10
        init_scale = 10
        init_ttm = 10
        init_margin = 55
        init_safety = 15
    elif preset == "Conservative Liquidity (Deposits)":
        init_growth = 15
        init_scale = 15
        init_ttm = 20
        init_margin = 15
        init_safety = 35
    else:
        init_growth = 20
        init_scale = 20
        init_ttm = 20
        init_margin = 20
        init_safety = 20

    st.markdown("---")
    st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#e2e8f0;'>DECISION WEIGHTS (%)</p>", unsafe_allow_html=True)

    w_growth = st.slider("📈 Market Growth Rate", min_value=0, max_value=100, value=init_growth, step=5,
                         help="Annual expansion of the transaction channel or segment.")
    w_scale = st.slider("👥 Adoption Scale / Volume", min_value=0, max_value=100, value=init_scale, step=5,
                        help="Top-of-funnel reach and daily customer transaction frequency.")
    w_ttm = st.slider("⚡ Speed to Market / Low Capex", min_value=0, max_value=100, value=init_ttm, step=5,
                      help="Ease of integration using standard APIs, SaaS switches, and turnkey rails.")
    w_margin = st.slider("💰 Unit Margin Potential (NIM / Fees)", min_value=0, max_value=100, value=init_margin, step=5,
                         help="Direct revenue generation per account or transaction.")
    w_safety = st.slider("🛡️ Credit Risk Safety", min_value=0, max_value=100, value=init_safety, step=5,
                         help="Protection against loan defaults, NPAs, and balance-sheet stress.")

    raw_weights = {
        "growth": w_growth,
        "scale": w_scale,
        "time_to_market": w_ttm,
        "margin": w_margin,
        "safety": w_safety,
    }
    norm_w = normalize_weights(raw_weights)

    st.markdown("---")
    st.markdown(
        f"<div style='font-size:0.75rem; color:#94a3b8; line-height:1.5;'>"
        f"<b>Normalized Weights Applied:</b><br>"
        f"• Growth: <code>{norm_w['growth']*100:.1f}%</code> | Scale: <code>{norm_w['scale']*100:.1f}%</code><br>"
        f"• Speed: <code>{norm_w['time_to_market']*100:.1f}%</code> | Margin: <code>{norm_w['margin']*100:.1f}%</code><br>"
        f"• Safety: <code>{norm_w['safety']*100:.1f}%</code>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.75rem; color:#64748b;'>"
        "Data Sources: NPCI Official UPI Statistics (Jan 2023–Aug 2025) & RBI Payment System Indicators.<br>"
        "Built for Small Finance Banks & Community Banking Executives."
        "</div>",
        unsafe_allow_html=True,
    )


# ── Calculate Opportunity Scores & Dynamic Recommendation ─────────────────────
scored_modules_df = calculate_opportunity_scores(modules_df, raw_weights)
recommendation_text = generate_recommendation(scored_modules_df, raw_weights)
top_module = scored_modules_df.iloc[0]


# ── Main Dashboard Header ─────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("<h1 style='margin-bottom:4px;'>🏦 Modular Banking Strategy Engine</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8; font-size:1.05rem; margin-top:0;'>"
        "Core Question: <b>Which banking module should a small bank launch first?</b>"
        "</p>",
        unsafe_allow_html=True,
    )
with col_h2:
    st.markdown(
        "<div style='text-align:right; padding-top:10px;'>"
        "<span class='badge-real'>REAL NPCI & RBI DATA</span><br>"
        "<span style='font-size:0.75rem; color:#64748b;'>Updated with Oct 2024–2025 releases</span>"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Top Metric KPI Cards ──────────────────────────────────────────────────────
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

# 2024 UPI Volume
upi_2024_vol = upi_df[upi_df["year"] == 2024]["volume_mn"].sum() / 1000.0  # In Billions
upi_2023_vol = upi_df[upi_df["year"] == 2023]["volume_mn"].sum() / 1000.0
vol_growth = ((upi_2024_vol - upi_2023_vol) / upi_2023_vol) * 100.0

# 2024 UPI Value (Lakh Crore)
upi_2024_val = upi_df[upi_df["year"] == 2024]["value_cr"].sum() / 100000.0  # Lakh Cr

# UPI Channel share
upi_share = channel_df[channel_df["system"] == "UPI"]["volume_share_pct"].iloc[0]

with kpi1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">2024 UPI Annual Volume</div>
            <div class="metric-value">{upi_2024_vol:.1f}B</div>
            <div class="metric-sub">↑ {vol_growth:.1f}% YoY Growth (Real NPCI)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">2024 UPI Value Settled</div>
            <div class="metric-value">₹{upi_2024_val:.2f}L Cr</div>
            <div class="metric-sub">↑ 37.7% YoY Value Expansion</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Digital Volume Dominance</div>
            <div class="metric-value">{upi_share:.1f}%</div>
            <div class="metric-sub">UPI share of all retail digital txns</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        f"""
        <div class="metric-card" style="border-color: rgba(99, 102, 241, 0.4);">
            <div class="metric-label">#1 Recommended Module</div>
            <div class="metric-value" style="color: #818cf8; font-size:1.35rem; padding-top:4px;">{top_module['module_name']}</div>
            <div class="metric-sub" style="color: #c7d2fe;">Opportunity Score: {top_module['opportunity_score']:.1f} / 100</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)


# ── Dynamic Executive Recommendation Callout ──────────────────────────────────
st.markdown(
    f"""
    <div class="rec-box">
        <div class="rec-title">
            <span>🎯 Executive Product Recommendation</span>
            <span style="font-size:0.75rem; background:rgba(99,102,241,0.25); color:#c7d2fe; padding:2px 8px; border-radius:12px;">Live MCDA Result</span>
        </div>
        <div class="rec-body">{recommendation_text}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Navigation Tabs ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Module Comparison & Scoring",
    "📈 UPI Growth & Seasonality",
    "🔄 Payment Channel Mix (RBI)",
    "🔍 SQL Engine & Provenance",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Module Comparison & Opportunity Scoring
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🏆 Banking Module Multi-Criteria Evaluation")
    st.markdown(
        "Comparing the 5 modular components a modern small bank (or Small Finance Bank) can prioritize for its initial digital rollout. "
        "Scores dynamically recalculate based on the weights specified in the sidebar."
    )

    col_t1, col_t2 = st.columns([3, 2])

    with col_t1:
        # Visual Bar Chart of Composite Opportunity Scores
        bar_colors = ["#6366f1" if i == 0 else "#3b82f6" if i == 1 else "#64748b" for i in range(len(scored_modules_df))]
        
        fig_score = go.Figure(
            go.Bar(
                x=scored_modules_df["opportunity_score"],
                y=scored_modules_df["module_name"],
                orientation="h",
                marker=dict(
                    color=scored_modules_df["opportunity_score"],
                    colorscale=[[0, "#334155"], [0.5, "#4f46e5"], [1.0, "#06b6d4"]],
                    line=dict(color="rgba(255,255,255,0.15)", width=1),
                ),
                text=scored_modules_df["opportunity_score"].apply(lambda v: f" {v:.1f} pts"),
                textposition="auto",
            )
        )
        fig_score.update_layout(
            title=dict(text="Composite Opportunity Score (0 - 100)", font=dict(color="#ffffff", size=15)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed", color="#cbd5e1"),
            xaxis=dict(range=[0, 100], color="#94a3b8", gridcolor="rgba(255,255,255,0.06)"),
            margin=dict(l=10, r=10, t=40, b=20),
            height=340,
        )
        st.plotly_chart(fig_score, use_container_width=True)

    with col_t2:
        # Radar Chart of Dimensions for Top 2 Modules
        top1 = scored_modules_df.iloc[0]
        top2 = scored_modules_df.iloc[1]

        categories = ["Market Growth", "Volume Scale", "Speed to Market", "Unit Margin", "Credit Safety"]
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[
                min(100, top1["market_growth_pct"] * 2.0),
                top1["volume_scale_score"],
                top1["time_to_market_score"],
                top1["margin_potential_score"],
                top1["credit_risk_safety_score"],
            ],
            theta=categories,
            fill='toself',
            name=f"#1 {top1['module_name']}",
            line=dict(color="#10b981", width=2),
            fillcolor='rgba(16, 185, 129, 0.25)',
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[
                min(100, top2["market_growth_pct"] * 2.0),
                top2["volume_scale_score"],
                top2["time_to_market_score"],
                top2["margin_potential_score"],
                top2["credit_risk_safety_score"],
            ],
            theta=categories,
            fill='toself',
            name=f"#2 {top2['module_name']}",
            line=dict(color="#6366f1", width=2),
            fillcolor='rgba(99, 102, 241, 0.25)',
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], color="#94a3b8", gridcolor="rgba(255,255,255,0.1)"),
                angularaxis=dict(color="#cbd5e1"),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            title=dict(text=f"Trade-off Matrix: #1 vs #2", font=dict(color="#ffffff", size=15)),
            showlegend=True,
            legend=dict(font=dict(color="#cbd5e1", size=10), orientation="h", y=-0.15),
            margin=dict(l=20, r=20, t=40, b=30),
            height=340,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("#### 📋 Detailed Module Comparison Table")

    display_df = scored_modules_df[[
        "rank", "module_name", "opportunity_score", "market_growth_pct",
        "volume_scale_score", "time_to_market_score", "margin_potential_score",
        "credit_risk_safety_score", "data_source"
    ]].rename(columns={
        "rank": "Rank",
        "module_name": "Module",
        "opportunity_score": "Score (0-100)",
        "market_growth_pct": "Growth (% YoY)",
        "volume_scale_score": "Scale (0-100)",
        "time_to_market_score": "Launch Speed (0-100)",
        "margin_potential_score": "Margin Potential (0-100)",
        "credit_risk_safety_score": "Safety (0-100)",
        "data_source": "Data Provenance",
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(format="%d 🥇"),
            "Score (0-100)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "Growth (% YoY)": st.column_config.NumberColumn(format="%.1f%%"),
            "Scale (0-100)": st.column_config.NumberColumn(format="%.0f"),
            "Launch Speed (0-100)": st.column_config.NumberColumn(format="%.0f"),
            "Margin Potential (0-100)": st.column_config.NumberColumn(format="%.0f"),
            "Safety (0-100)": st.column_config.NumberColumn(format="%.0f"),
        }
    )

    st.markdown("#### 🏗️ Architecture & Launch Sequencing Playbook")
    with st.expander("📖 View Strategic Launch Playbook for a Small Bank", expanded=True):
        st.markdown("""
        1. **Phase 1: UPI & Instant Payments (Month 0 - 3)**
           - *Why First:* Connects to NPCI rails via a third-party application provider (TPAP) or certified switch partner. Delivers immediate brand presence, high daily active usage (DAU), and captures transaction telemetry. Zero balance-sheet credit exposure.
        2. **Phase 2: Digital Onboarding & CASA (Month 2 - 5)**
           - *Why Second:* Convert daily transaction users into funded deposit holders using Aadhaar OTP / Video-KYC and Account Aggregator consent flows. Provides sticky, low-cost CASA float to fund future balance sheet expansion.
        3. **Phase 3: Digital Micro-Lending & Overdraft (Month 6 - 12)**
           - *Why Later:* High margin (NIM 8-14%) but requires customer transaction history to underwrite responsibly. Launching lending on day 1 without proprietary behavioral data invites adverse selection and elevated NPAs.
        """)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: UPI Growth Trends & Seasonality
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 📈 NPCI UPI Growth & Seasonality Analytics")
    st.markdown(
        "Monthly time-series analysis based on official NPCI product statistics (32 consecutive months from Jan 2023 to Aug 2025). "
        "Shows structural expansion, average ticket sizes, and monthly surges."
    )

    col_g1, col_g2 = st.columns([3, 2])

    with col_g1:
        # Dual-axis: Volume (Mn) and Value (Cr)
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=upi_df["period"],
            y=upi_df["volume_mn"],
            name="Volume (Mn Txns)",
            marker_color="rgba(99, 102, 241, 0.75)",
            yaxis="y1",
        ))
        fig_trend.add_trace(go.Scatter(
            x=upi_df["period"],
            y=upi_df["value_cr"],
            name="Value (₹ Cr)",
            mode="lines+markers",
            line=dict(color="#10b981", width=3),
            marker=dict(size=6, color="#34d399"),
            yaxis="y2",
        ))

        fig_trend.update_layout(
            title=dict(text="Monthly UPI Transaction Volume (Mn) & Value (₹ Cr)", font=dict(color="#ffffff", size=14)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#94a3b8", gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(
                title=dict(text="Volume (Mn)", font=dict(color="#a5b4fc")),
                color="#a5b4fc",
                gridcolor="rgba(255,255,255,0.06)",
            ),
            yaxis2=dict(
                title=dict(text="Value (₹ Cr)", font=dict(color="#34d399")),
                color="#34d399",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
            legend=dict(font=dict(color="#cbd5e1"), orientation="h", y=1.1, x=0),
            margin=dict(l=10, r=10, t=50, b=20),
            height=380,
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_g2:
        # Average ticket size over time
        fig_ticket = px.line(
            upi_df,
            x="period",
            y="avg_ticket_size_inr",
            title="UPI Average Ticket Size (₹ per Txn)",
            markers=True,
        )
        fig_ticket.update_traces(line_color="#06b6d4", marker=dict(size=5, color="#22d3ee"))
        fig_ticket.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#94a3b8", gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(color="#94a3b8", gridcolor="rgba(255,255,255,0.06)", title="Ticket Size (₹)"),
            font=dict(color="#ffffff"),
            margin=dict(l=10, r=10, t=50, b=20),
            height=380,
        )
        st.plotly_chart(fig_ticket, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🗓️ Calendar Month Seasonality Index")
    st.markdown(
        "Aggregated across 2023–2025 to isolate calendar-month seasonality. "
        "Notice surges in October/December (festive/Diwali shopping) and March (fiscal year-end corporate & tax settlements)."
    )

    fig_season = go.Figure()
    fig_season.add_trace(go.Bar(
        x=seasonality_df["month"],
        y=seasonality_df["seasonality_index_pct"],
        marker=dict(
            color=seasonality_df["seasonality_index_pct"],
            colorscale=[[0, "#ef4444"], [0.5, "#64748b"], [1, "#10b981"]],
            line=dict(color="rgba(255,255,255,0.15)", width=1),
        ),
        text=seasonality_df["seasonality_index_pct"].apply(lambda v: f"{v:+.1f}%"),
        textposition="outside",
    ))
    fig_season.update_layout(
        title=dict(text="UPI Volume Seasonality Index (% variance vs annual baseline average)", font=dict(color="#ffffff", size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(color="#cbd5e1"),
        yaxis=dict(color="#94a3b8", gridcolor="rgba(255,255,255,0.06)", title="Variance vs Mean (%)"),
        margin=dict(l=10, r=10, t=40, b=20),
        height=320,
    )
    st.plotly_chart(fig_season, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Payment Channel Mix (RBI Data)
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🔄 India Payment Systems Channel Mix (RBI Indicators)")
    st.markdown(
        "Demonstrates the fundamental architectural dichotomy between **Retail Transaction Volume** (dominated by UPI) "
        "and **Institutional Settlement Value** (dominated by NEFT & RTGS). Real data from RBI Payment Systems Reports."
    )

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        fig_pie_vol = px.pie(
            channel_df,
            values="volume_mn",
            names="system",
            title="Transaction Volume Share (2024)",
            hole=0.45,
            color_discrete_sequence=["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#8b5cf6"],
        )
        fig_pie_vol.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"),
            legend=dict(orientation="h", y=-0.1),
            margin=dict(l=10, r=10, t=50, b=30),
            height=360,
        )
        st.plotly_chart(fig_pie_vol, use_container_width=True)

    with col_c2:
        fig_pie_val = px.pie(
            channel_df,
            values="value_cr",
            names="system",
            title="Transaction Value Share (2024)",
            hole=0.45,
            color_discrete_sequence=["#3b82f6", "#10b981", "#6366f1", "#f59e0b", "#ec4899"],
        )
        fig_pie_val.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1"),
            legend=dict(orientation="h", y=-0.1),
            margin=dict(l=10, r=10, t=50, b=30),
            height=360,
        )
        st.plotly_chart(fig_pie_val, use_container_width=True)

    st.markdown("#### 💡 Strategic Takeaway for Small Bank Executives")
    st.info(
        "**Volume vs Value Asymmetry:** UPI accounts for **~75% of all digital transaction volume** in India, but only **~3.7% of total value settled**. "
        "Conversely, NEFT and RTGS settle over **96% of value** with less than 20% of volume. "
        "For a small bank, launching UPI is NOT about earning massive interchange on large transfers; "
        "it is about **owning the everyday customer interface**, driving daily active engagement, and preventing churn to larger incumbent banks."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: SQL Engine & Data Provenance
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 🔍 SQLite Analytical Engine & Public Data Provenance")
    st.markdown(
        "All calculations originate from clean SQLite tables and views in `banking.db`. "
        "Select any of the 5 foundational SQL queries below to inspect its SQL code and execute it live."
    )

    query_options = {
        "Query 1: Year-over-Year (YoY) Growth Rate": "01_growth_rate.sql",
        "Query 2: Month-over-Month (MoM) Changes": "02_mom_change.sql",
        "Query 3: Seasonality Analysis across Calendar Months": "03_seasonality.sql",
        "Query 4: Channel Share & Volume/Value Mix": "04_channel_share.sql",
        "Query 5: Opportunity Score MCDA Model": "05_opportunity_score.sql",
    }

    selected_query_title = st.selectbox("Select SQL Query to Inspect & Run", list(query_options.keys()))
    selected_filename = query_options[selected_query_title]
    sql_file_path = BASE_DIR / "queries" / selected_filename

    if sql_file_path.exists():
        sql_content = sql_file_path.read_text(encoding="utf-8")
        st.code(sql_content, language="sql")

        conn = sqlite3.connect(DB_PATH)
        res_df = pd.read_sql(sql_content, conn)
        conn.close()

        st.markdown(f"**Query Results ({len(res_df)} rows returned):**")
        st.dataframe(res_df, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📑 Data Provenance & Cleaning Log")
    col_log1, col_log2 = st.columns(2)

    with col_log1:
        st.markdown("##### Verified Public Data Sources")
        st.markdown("""
        - **NPCI UPI Product Statistics:**
          - Official URL: `https://www.npci.org.in/what-we-do/upi/product-statistics`
          - Cross-verified with Press Information Bureau (PIB Release ID 2085731)
          - Date Retrieved: Oct 2026 / Dec 2024–Aug 2025 releases
        - **RBI Payment System Indicators:**
          - Official URL: `https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/`
          - Annual Report 2023-24 Bulletin Payment System tables
        - **RBI Banking Trends & SFB Benchmarks:**
          - Report on Trend and Progress of Banking in India 2023-24
        """)

    with col_log2:
        st.markdown("##### Cleaning Script Drop Log (`data/clean.log`)")
        log_file = DATA_DIR / "clean.log"
        if log_file.exists():
            log_lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            st.text_area(
                "Recent pipeline log output:",
                value="\n".join(log_lines[-20:]),
                height=180,
                disabled=True,
            )
        else:
            st.write("No log file found.")
