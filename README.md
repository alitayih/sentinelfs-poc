# sentinelfs-poc

A Qatar-focused **Food Security Intelligence Cycle** Proof-of-Concept (PoC) built in Streamlit.

This is **not** a traditional dashboard. It follows an intelligence-cycle workflow:
**Data ingestion → signal detection → risk scoring → alerting → intervention tracking → feedback loop**

## Features
- 3-screen workflow:
  1) **Qatar Food Security Overview** (Executive Command View)
  2) **AI Issue Breakdown** (Alert Drilldown + Shock Simulation)
  3) **Action & Intervention Tracking** (Operations Layer, SQLite-backed)
- Dynamic alert generation from signals
- One-click shock simulation: **Simulate Red Sea Disruption (Qatar)**
- Live Plotly Geo Map centered on Doha with hubs, chokepoints, and routes

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud
1) Push repo to GitHub
2) Streamlit Cloud → **New app**
3) Select repo `sentinelfs-poc` and branch `main`
4) Main file path: `app.py`
5) Deploy

> Notes: Alerts are generated dynamically from signals. Shock simulation updates signals in-session and writes a decision log to SQLite.
