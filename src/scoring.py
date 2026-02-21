from __future__ import annotations

import pandas as pd


DRIVERS = ["supply_risk_score", "logistics_risk_score", "climate_risk_score", "geopolitical_risk_score"]


def compute_composite(df: pd.DataFrame) -> pd.Series:
    return (
        0.35 * df["supply_risk_score"]
        + 0.25 * df["logistics_risk_score"]
        + 0.20 * df["climate_risk_score"]
        + 0.20 * df["geopolitical_risk_score"]
    )


def compute_main_driver(df: pd.DataFrame) -> pd.Series:
    idx = df[DRIVERS].astype(float).idxmax(axis=1)
    mapping = {
        "supply_risk_score": "Supply",
        "logistics_risk_score": "Logistics",
        "climate_risk_score": "Climate",
        "geopolitical_risk_score": "Geopolitical",
    }
    return idx.map(mapping)


def severity_from_composite(composite: float) -> str:
    if composite < 50:
        return "Low"
    if composite < 70:
        return "Medium"
    if composite < 85:
        return "High"
    return "Critical"


def generate_alerts(signals: pd.DataFrame) -> pd.DataFrame:
    df = signals.copy()
    df["severity"] = df["composite_risk_score"].apply(severity_from_composite)

    trigger_risk = df["composite_risk_score"] >= 70
    trigger_price = df["chg_7d"].abs() >= 10
    df["triggered"] = trigger_risk | trigger_price
    df["trigger_reason"] = ""
    df.loc[trigger_risk & trigger_price, "trigger_reason"] = "Composite >= 70 AND |7D change| >= 10"
    df.loc[trigger_risk & ~trigger_price, "trigger_reason"] = "Composite >= 70"
    df.loc[~trigger_risk & trigger_price, "trigger_reason"] = "|7D change| >= 10"

    alerts = df[df["triggered"]].copy()
    alerts = alerts.sort_values(["composite_risk_score", "chg_7d"], ascending=[False, False])
    return alerts


def normalize_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["date"] = pd.to_datetime(out["date"]).dt.date

    # numeric conversion
    num_cols = ["price", "chg_7d", "chg_30d"] + DRIVERS + ["confidence"]
    for c in num_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # recompute composite if missing/NaN
    if "composite_risk_score" not in out.columns:
        out["composite_risk_score"] = compute_composite(out)
    else:
        out["composite_risk_score"] = pd.to_numeric(out["composite_risk_score"], errors="coerce")
        missing = out["composite_risk_score"].isna()
        if missing.any():
            out.loc[missing, "composite_risk_score"] = compute_composite(out.loc[missing])

    # ALWAYS recompute main_driver
    out["main_driver"] = compute_main_driver(out)

    # clamp scores
    for c in DRIVERS:
        out[c] = out[c].clip(0, 100)
    out["composite_risk_score"] = out["composite_risk_score"].clip(0, 100)
    out["confidence"] = out["confidence"].clip(0, 1)

    return out
