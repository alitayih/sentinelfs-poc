from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from .scoring import normalize_signals

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(ttl=300)
def load_mock_signals() -> pd.DataFrame:
    path = ROOT / "data" / "mock_signals.csv"
    df = pd.read_csv(path)
    return normalize_signals(df)


@st.cache_data(ttl=300)
def load_mock_actions_csv() -> pd.DataFrame:
    path = ROOT / "data" / "mock_actions.csv"
    return pd.read_csv(path)
