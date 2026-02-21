from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.cache_data(ttl=300)
def build_qatar_geo_figure() -> go.Figure:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")

    points = pd.DataFrame(
        [
            # National hub
            {"name": "Doha (National Command)", "lat": 25.2854, "lon": 51.5310, "category": "National Hub", "note": "Qatar coordination center", "ts": now},
            {"name": "Hamad Port", "lat": 25.1430, "lon": 51.7000, "category": "National Hub", "note": "Inbound maritime logistics", "ts": now},
            # Supplier hubs
            {"name": "Mumbai (India)", "lat": 19.0760, "lon": 72.8777, "category": "Supplier Hub", "note": "Rice/Onions sourcing", "ts": now},
            {"name": "Santos (Brazil)", "lat": -23.9608, "lon": -46.3336, "category": "Supplier Hub", "note": "Frozen protein supply node", "ts": now},
            # Chokepoints
            {"name": "Bab el-Mandeb (Red Sea)", "lat": 12.6, "lon": 43.3, "category": "Maritime Chokepoint", "note": "Red Sea corridor volatility", "ts": now},
            {"name": "Suez Canal", "lat": 30.0, "lon": 32.6, "category": "Maritime Chokepoint", "note": "Transit sensitivity", "ts": now},
            {"name": "Black Sea Transit", "lat": 43.0, "lon": 35.0, "category": "Maritime Chokepoint", "note": "Black Sea disruption risk", "ts": now},
            # Instability cluster
            {"name": "Regional Instability Cluster", "lat": 15.5, "lon": 44.0, "category": "Conflict/Instability", "note": "Elevated conflict spillover risk", "ts": now},
        ]
    )

    color_map = {
        "National Hub": "#C9A227",         # gold
        "Supplier Hub": "#22C55E",         # green
        "Maritime Chokepoint": "#FB923C",  # orange
        "Conflict/Instability": "#EF4444", # red
    }

    fig = go.Figure()

    for cat, grp in points.groupby("category"):
        fig.add_trace(
            go.Scattergeo(
                lon=grp["lon"],
                lat=grp["lat"],
                mode="markers",
                marker=dict(size=10, color=color_map.get(cat, "#93C5FD"), line=dict(width=1, color="rgba(0,0,0,0.35)")),
                name=cat,
                text=grp.apply(lambda r: f"<b>{r['name']}</b><br>{r['note']}<br><span style='opacity:.8'>Last update: {r['ts']}</span>", axis=1),
                hoverinfo="text",
            )
        )

    # route lines: Supplier -> chokepoint -> Doha
    doha = (51.5310, 25.2854)
    routes = [
        # India -> Bab el-Mandeb -> Doha
        ((72.8777, 19.0760), (43.3, 12.6), doha),
        # Brazil -> Suez -> Doha (illustrative)
        ((-46.3336, -23.9608), (32.6, 30.0), doha),
    ]

    for a, b, c in routes:
        for start, end in [(a, b), (b, c)]:
            fig.add_trace(
                go.Scattergeo(
                    lon=[start[0], end[0]],
                    lat=[start[1], end[1]],
                    mode="lines",
                    line=dict(width=2, color="rgba(201,162,39,0.55)"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        geo=dict(
            scope="world",
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(20, 28, 46)",
            showcountries=True,
            countrycolor="rgba(255,255,255,0.10)",
            showocean=True,
            oceancolor="rgb(11, 18, 32)",
            lataxis=dict(range=[-40, 55]),
            lonaxis=dict(range=[-70, 95]),
            center=dict(lat=25.2854, lon=51.5310),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, font=dict(color="#E5E7EB")),
    )

    return fig
