from __future__ import annotations

from pathlib import Path
import sqlite3
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "actions.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(seed_actions: pd.DataFrame | None = None) -> None:
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            owner TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            expected_risk_impact TEXT,
            commodity TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """
    )

    # seed only if empty
    cur.execute("SELECT COUNT(1) FROM actions")
    count = cur.fetchone()[0]
    if count == 0 and seed_actions is not None and len(seed_actions) > 0:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        rows = []
        for _, r in seed_actions.iterrows():
            rows.append(
                (
                    str(r.get("title", "")).strip(),
                    str(r.get("owner", "Ops")).strip(),
                    str(r.get("due_date", "2026-03-01")).strip(),
                    str(r.get("status", "Open")).strip(),
                    str(r.get("notes", "")).strip(),
                    str(r.get("expected_risk_impact", "")).strip(),
                    str(r.get("commodity", "")).strip(),
                    now,
                )
            )

        cur.executemany(
            """
            INSERT INTO actions(title, owner, due_date, status, notes, expected_risk_impact, commodity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()

    conn.commit()
    conn.close()


def add_decision_log(message: str) -> None:
    conn = _connect()
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn.execute("INSERT INTO decision_log(ts, message) VALUES (?, ?)", (ts, message))
    conn.commit()
    conn.close()


def add_action(
    title: str,
    owner: str,
    due_date: str,
    status: str,
    notes: str,
    expected_risk_impact: str,
    commodity: str,
) -> None:
    conn = _connect()
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn.execute(
        """
        INSERT INTO actions(title, owner, due_date, status, notes, expected_risk_impact, commodity, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, owner, due_date, status, notes, expected_risk_impact, commodity, created_at),
    )
    conn.commit()
    conn.close()


def list_actions() -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT id, title, owner, due_date, status, notes, expected_risk_impact, commodity, created_at
        FROM actions
        ORDER BY due_date ASC, id DESC
        """,
        conn,
    )
    conn.close()
    return df


def update_action(action_id: int, status: str, notes: str) -> None:
    conn = _connect()
    conn.execute("UPDATE actions SET status=?, notes=? WHERE id=?", (status, notes, action_id))
    conn.commit()
    conn.close()


def delete_action(action_id: int) -> None:
    conn = _connect()
    conn.execute("DELETE FROM actions WHERE id=?", (action_id,))
    conn.commit()
    conn.close()


def list_decision_logs(limit: int = 50) -> pd.DataFrame:
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT id, ts, message
        FROM decision_log
        ORDER BY id DESC
        LIMIT ?
        """,
        conn,
        params=(limit,),
    )
    conn.close()
    return df
