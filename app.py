from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ---- Cloud-safe sys.path setup (NON-NEGOTIABLE) ----
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_sources import load_mock_signals, load_mock_actions_csv
from src.scoring import generate_alerts, normalize_signals, severity_from_composite
from src.ui import severity_badge, bordered_card
from src.geo import build_qatar_geo_figure
from src.db import (
    init_db,
    add_action,
    list_actions,
    update_action,
    delete_action,
    add_decision_log,
    list_decision_logs,
)


# -------------------- Time helpers --------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


# -------------------- Session State --------------------
def init_state() -> None:
    # Signals: single source of truth (do not load twice)
    if "signals" not in st.session_state:
        st.session_state.signals = load_mock_signals()

    # Selected commodity (used for drilldown)
    if "selected_commodity" not in st.session_state:
        st.session_state.selected_commodity = st.session_state.signals["commodity"].iloc[0]

    # Navigation state
    if "screen" not in st.session_state:
        st.session_state.screen = "Qatar Food Security Overview"

    # Live intelligence feed (notifications)
    if "notifications" not in st.session_state:
        st.session_state.notifications = []
        seed = [
            ("High", "Export restriction mention detected impacting Qatar supply basket (Wheat)"),
            ("High", "Red Sea corridor freight volatility elevated – Qatar inbound risk"),
            ("Medium", "Black Sea transit disruption risk – potential import delays to Qatar"),
            ("Medium", "Hamad Port throughput anomaly – monitoring"),
        ]
        for sev, msg in seed:
            st.session_state.notifications.append({"ts": _utc_now(), "severity": sev, "msg": msg})

    # DB init (seed actions on first run)
    if "db_inited" not in st.session_state:
        seed_actions = load_mock_actions_csv()
        init_db(seed_actions)
        st.session_state.db_inited = True


def get_alerts() -> pd.DataFrame:
    # Derived dynamically from signals (no static alerts CSV)
    return generate_alerts(st.session_state.signals)


def push_notification(severity: str, msg: str) -> None:
    st.session_state.notifications.append({"ts": _utc_now(), "severity": severity, "msg": msg})


# -------------------- UI helpers --------------------
def kpi_card(label: str, value: str) -> None:
    with st.container(border=True):
        st.markdown(f"<div style='font-size:12px; opacity:.85'>{label}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:22px; font-weight:900'>{value}</div>", unsafe_allow_html=True)


def driver_badge(driver: str) -> str:
    driver = (driver or "").strip()
    color = "#93C5FD"
    if driver == "Supply":
        color = "#22C55E"
    elif driver == "Logistics":
        color = "#F59E0B"
    elif driver == "Climate":
        color = "#60A5FA"
    elif driver == "Geopolitical":
        color = "#EF4444"
    return f"""
    <span style="
      padding:2px 10px; border-radius:999px;
      border:1px solid rgba(255,255,255,0.15);
      background:rgba(255,255,255,0.04);
      font-size:12px; font-weight:800;
      color:{color};">
      {driver}
    </span>
    """


# -------------------- Screen 1 --------------------
def screen_overview() -> None:
    st.title("Qatar Food Security Overview")
    st.caption("Executive Command View — intelligence-cycle posture, alerts, and geo-routing context.")

    alerts = get_alerts()

    # KPIs
    risk_index = float(st.session_state.signals["composite_risk_score"].mean())
    active_alerts_count = int(len(alerts))
    reserve_days = 43
    wheat_exposure = "82%"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Qatar Food Risk Index (mean composite)", f"{risk_index:.1f}")
    with c2:
        kpi_card("Strategic Reserve Coverage (Days) – Qatar", str(reserve_days))
    with c3:
        kpi_card("Wheat Import Exposure – Qatar", wheat_exposure)
    with c4:
        kpi_card("Active Alerts Count", str(active_alerts_count))

    st.write("")
    left, right = st.columns([0.45, 0.55], gap="large")

    # Alerts panel (left)
    with left:
        st.subheader("Active Alerts")
        with st.container(border=True):
            if alerts.empty:
                st.info("No active alerts based on current signal rules.")
            else:
                for _, r in alerts.head(12).iterrows():
                    sev = str(r["severity"])
                    row = st.columns([0.34, 0.30, 0.16, 0.20])
                    with row[0]:
                        st.markdown(f"**{r['commodity']}**", help=str(r["trigger_reason"]))
                        st.caption(str(r["market"]))
                    with row[1]:
                        st.markdown(severity_badge(sev), unsafe_allow_html=True)
                    with row[2]:
                        st.markdown(f"**{float(r['composite_risk_score']):.1f}**")
                        st.caption("risk")
                    with row[3]:
                        st.markdown(f"**{float(r['chg_7d']):.1f}%**")
                        st.caption("chg_7d")

                    btn_key = f"open_{r['commodity']}_{r['market']}_{r['date']}"
                    if st.button("Open details", key=btn_key, use_container_width=True):
                        st.session_state.selected_commodity = str(r["commodity"])
                        st.session_state.screen = "AI Issue Breakdown"
                        st.rerun()

                    st.divider()

    # Right side: Risk by commodity + live feed
    with right:
        st.subheader("Risk by Commodity")
        with st.container(border=True):
            byc = (
                st.session_state.signals.groupby("commodity", as_index=False)["composite_risk_score"]
                .mean()
                .sort_values("composite_risk_score", ascending=False)
            )
            fig = px.bar(byc, x="commodity", y="composite_risk_score")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Live Intelligence Feed")
        with st.container(border=True):
            feed = st.session_state.notifications[-8:][::-1]
            if not feed:
                st.caption("No notifications yet.")
            for item in feed:
                st.markdown(
                    f"{severity_badge(item['severity'])} &nbsp; <span style='opacity:.85'>{item['ts']}</span><br>"
                    f"<span style='font-weight:700'>{item['msg']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Geo map
    st.write("")
    st.subheader("Live Geo Map — Qatar Inbound Risk Topology")
    with st.container(border=True):
        geo_fig = build_qatar_geo_figure()
        st.plotly_chart(geo_fig, use_container_width=True)

    # Signals table (render once)
    st.write("")
    st.subheader("Signals (latest observations)")
    with st.container(border=True):
        latest = (
            st.session_state.signals.sort_values("date")
            .groupby(["commodity", "market"], as_index=False)
            .tail(1)
            .sort_values("composite_risk_score", ascending=False)
        )
        show_cols = [
            "commodity",
            "market",
            "date",
            "price",
            "chg_7d",
            "chg_30d",
            "supply_risk_score",
            "logistics_risk_score",
            "climate_risk_score",
            "geopolitical_risk_score",
            "composite_risk_score",
            "main_driver",
            "confidence",
        ]
        st.dataframe(latest[show_cols], use_container_width=True, hide_index=True)


# -------------------- Screen 2 --------------------
def screen_drilldown() -> None:
    st.title("AI Issue Breakdown")
    st.caption("Alert drilldown with root-cause drivers, trends, and one-click scenario shock simulation (Qatar).")

    df = st.session_state.signals
    commodity_list = sorted(df["commodity"].unique().tolist())

    default_idx = 0
    if st.session_state.selected_commodity in commodity_list:
        default_idx = commodity_list.index(st.session_state.selected_commodity)

    commodity = st.selectbox("Commodity", commodity_list, index=default_idx)
    st.session_state.selected_commodity = commodity

    sub = df[df["commodity"] == commodity].copy()
    sub = sub.sort_values("date")

    # IMPORTANT: no stray indentation below (this is where your error came from)
    latest = sub.iloc[-1]
    comp = float(latest["composite_risk_score"])
    sev = severity_from_composite(comp)
    conf = float(latest["confidence"])
    alerts = get_alerts()
    hit = alerts[alerts["commodity"] == commodity]
    trigger_str = hit.iloc[0]["trigger_reason"] if not hit.empty else "No active alert trigger (informational view)."
    primary_driver = str(latest["main_driver"])

    body = f"""
<div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
  <div style="font-size:18px; font-weight:900;">{commodity}</div>
  <div>{severity_badge(sev)}</div>
  <div style="opacity:.85;">Confidence: <b>{conf:.2f}</b></div>
  <div style="opacity:.85;">Trigger: <b>{trigger_str}</b></div>
</div>
<div style="margin-top:10px;">Primary Risk Driver: {driver_badge(primary_driver)}</div>
"""
    st.markdown(bordered_card("Alert Context", body, "#C9A227"), unsafe_allow_html=True)

    # Root cause drivers
    st.subheader("Root Cause Drivers")
    with st.container(border=True):
        drivers = pd.DataFrame(
            {
                "driver": ["Supply", "Logistics", "Climate", "Geopolitical"],
                "score": [
                    float(latest["supply_risk_score"]),
                    float(latest["logistics_risk_score"]),
                    float(latest["climate_risk_score"]),
                    float(latest["geopolitical_risk_score"]),
                ],
            }
        )
        fig = px.bar(drivers, x="driver", y="score")
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Trend
    st.subheader("Trend — Price & Composite Risk")
    with st.container(border=True):
        t = sub.copy()
        t["date"] = pd.to_datetime(t["date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t["date"], y=t["price"], name="Price", mode="lines+markers"))
        fig.add_trace(
            go.Scatter(
                x=t["date"],
                y=t["composite_risk_score"],
                name="Composite Risk",
                mode="lines+markers",
                yaxis="y2",
            )
        )
        fig.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="Price"),
            yaxis2=dict(title="Composite Risk", overlaying="y", side="right", range=[0, 100]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Impact projection
    st.subheader("Impact Projection (mock, consistent)")
    with st.container(border=True):
        impact_html = f"""
<ul style="margin:0 0 0 18px;">
  <li>Retail sensitivity: <b>moderate</b> (Qatar import basket exposure)</li>
  <li>Supply continuity risk: <b>{primary_driver}</b> as dominant driver</li>
  <li>Projected 14-day risk band: <b>{max(0, comp-6):.0f}–{min(100, comp+10):.0f}</b></li>
</ul>
"""
        st.markdown(impact_html, unsafe_allow_html=True)

    # Scenario table
    st.subheader("Scenario Modeling (Best/Base/Worst)")
    with st.container(border=True):
        scen = pd.DataFrame(
            [
                {
                    "Scenario": "Best",
                    "Probability": 0.20,
                    "Assumption": "Freight normalizes; no new export restrictions",
                    "Projected Risk": max(0, comp - 10),
                },
                {
                    "Scenario": "Base",
                    "Probability": 0.55,
                    "Assumption": "Status quo volatility persists",
                    "Projected Risk": min(100, comp + 2),
                },
                {
                    "Scenario": "Worst",
                    "Probability": 0.25,
                    "Assumption": "Chokepoint disruption + policy shocks",
                    "Projected Risk": min(100, comp + 14),
                },
            ]
        )
        st.dataframe(scen, use_container_width=True, hide_index=True)

    # Recommended interventions
    st.subheader("Recommended Interventions")
    with st.container(border=True):
        recs = [
            "Increase Hamad Port inbound monitoring cadence and exception reporting.",
            "Pre-position alternative supplier options for key staples (wheat/rice) with short lead time.",
            "Trigger strategic reserve review if composite risk sustains > 70 for 2 consecutive reads.",
        ]
        st.markdown("\n".join([f"- {r}" for r in recs]))

    # Shock simulation
    st.write("")
    if st.button("Simulate Red Sea Disruption (Qatar)", use_container_width=True):
        shock_df = st.session_state.signals.copy()
        mask = shock_df["commodity"] == commodity

        shock_df.loc[mask, "logistics_risk_score"] = (shock_df.loc[mask, "logistics_risk_score"] + 20).clip(0, 100)
        shock_df.loc[mask, "geopolitical_risk_score"] = (
            shock_df.loc[mask, "geopolitical_risk_score"] + 15
        ).clip(0, 100)
        shock_df.loc[mask, "chg_7d"] = shock_df.loc[mask, "chg_7d"] + 8

        shock_df = normalize_signals(shock_df)
        st.session_state.signals = shock_df

        new_comp = float(shock_df[mask].sort_values("date").iloc[-1]["composite_risk_score"])
        new_sev = severity_from_composite(new_comp)

        push_notification(new_sev, f"Shock simulated: Red Sea disruption applied to {commodity} (Qatar inbound risk updated).")
        add_decision_log(f"Simulated Red Sea disruption triggered for {commodity}")

        st.rerun()


# -------------------- Screen 3 --------------------
def screen_operations() -> None:
    st.title("Action & Intervention Tracking")
    st.caption("Operations layer with SQLite-backed actions and decision logs (feedback loop).")

    # Anticipatory KPIs (mock)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("14-day escalation probability", "28%")
    with k2:
        kpi_card("Conflict intensity trend", "Rising")
    with k3:
        kpi_card("Freight volatility indicator", "Elevated")
    with k4:
        kpi_card("Export restriction sentiment", "Mixed")

    st.write("")
    st.subheader("Add Action")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            title = st.text_input("Title", placeholder="e.g., Supplier diversification plan")
            owner = st.text_input("Owner", value="Ops")

        with c2:
            due = st.date_input("Due date")
            status = st.selectbox("Status", ["Open", "In Progress", "Blocked", "Done"], index=0)

        with c3:
            commodity = st.selectbox(
                "Commodity", ["All"] + sorted(st.session_state.signals["commodity"].unique().tolist())
            )
            expected = st.text_input("Expected risk impact", placeholder="e.g., reduce logistics risk by 5–10")

        notes = st.text_area("Notes", height=90, placeholder="Add operational notes / dependencies / constraints")

        if st.button("Add action", use_container_width=True):
            if not title.strip():
                st.error("Title is required.")
            else:
                add_action(
                    title=title.strip(),
                    owner=owner.strip() or "Ops",
                    due_date=str(due),
                    status=status,
                    notes=notes.strip(),
                    expected_risk_impact=expected.strip(),
                    commodity=commodity,
                )
                push_notification("Medium", f"Action added: {title.strip()} (owner: {owner.strip() or 'Ops'})")
                st.success("Action added.")
                st.rerun()

    st.write("")
    st.subheader("Active Actions")
    with st.container(border=True):
        actions = list_actions()
        if actions.empty:
            st.info("No actions yet.")
        else:
            for _, r in actions.iterrows():
                with st.container(border=True):
                    top = st.columns([0.60, 0.20, 0.20])

                    with top[0]:
                        st.markdown(f"**{r['title']}**")
                        st.caption(f"Owner: {r['owner']} • Commodity: {r['commodity']} • Due: {r['due_date']}")

                    with top[1]:
                        statuses = ["Open", "In Progress", "Blocked", "Done"]
                        idx = statuses.index(r["status"]) if r["status"] in statuses else 0
                        new_status = st.selectbox("Status", statuses, index=idx, key=f"status_{r['id']}")

                    with top[2]:
                        if st.button("Delete", key=f"del_{r['id']}", use_container_width=True):
                            delete_action(int(r["id"]))
                            push_notification("Low", f"Action deleted: {r['title']}")
                            st.rerun()

                    new_notes = st.text_area("Notes", value=r["notes"] or "", height=70, key=f"notes_{r['id']}")
                    if st.button("Save updates", key=f"save_{r['id']}", use_container_width=True):
                        update_action(int(r["id"]), new_status, new_notes)
                        push_notification("Low", f"Action updated: {r['title']} → {new_status}")
                        st.success("Saved.")
                        st.rerun()

    st.write("")
    st.subheader("Decision Log (latest first)")
    with st.container(border=True):
        logs = list_decision_logs(50)
        if logs.empty:
            st.caption("No decision logs yet.")
        else:
            for _, r in logs.iterrows():
                st.markdown(f"- **{r['ts']}** — {r['message']}")


# -------------------- Main --------------------
st.set_page_config(page_title="SentinelFS – Qatar Food Security PoC", layout="wide")
init_state()

screen = st.sidebar.radio(
    "Navigation",
    ["Qatar Food Security Overview", "AI Issue Breakdown", "Action & Intervention Tracking"],
    index=["Qatar Food Security Overview", "AI Issue Breakdown", "Action & Intervention Tracking"].index(
        st.session_state.screen
    )
    if st.session_state.screen in [
        "Qatar Food Security Overview",
        "AI Issue Breakdown",
        "Action & Intervention Tracking",
    ]
    else 0,
)
st.session_state.screen = screen

if screen == "Qatar Food Security Overview":
    screen_overview()
elif screen == "AI Issue Breakdown":
    screen_drilldown()
else:
    screen_operations()