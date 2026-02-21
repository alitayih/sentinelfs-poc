from __future__ import annotations

import html


def severity_badge(severity: str) -> str:
    sev = (severity or "").strip().lower()
    # colors are tuned for dark gov theme
    if sev == "low":
        bg = "#14532D"   # green
        fg = "#DCFCE7"
        br = "#22C55E"
    elif sev == "medium":
        bg = "#78350F"   # amber
        fg = "#FEF3C7"
        br = "#F59E0B"
    elif sev == "high":
        bg = "#7C2D12"   # orange
        fg = "#FFEDD5"
        br = "#FB923C"
    else:  # critical
        bg = "#7F1D1D"   # red
        fg = "#FEE2E2"
        br = "#EF4444"

    label = html.escape(severity.title() if severity else "Unknown")
    return f"""
    <span style="
        display:inline-flex; align-items:center; gap:6px;
        padding:2px 10px; border-radius:999px;
        background:{bg}; color:{fg}; border:1px solid {br};
        font-size:12px; font-weight:700; letter-spacing:.3px;">
        {label}
    </span>
    """


def bordered_card(title: str, body_html: str, accent_color: str = "#C9A227") -> str:
    t = html.escape(title or "")
    return f"""
    <div style="
        border:1px solid rgba(255,255,255,0.10);
        border-left:4px solid {accent_color};
        background:rgba(255,255,255,0.03);
        padding:14px 14px;
        border-radius:12px;
        margin:0 0 10px 0;">
        <div style=\"font-weight:800; font-size:14px; margin-bottom:8px; color:#E5E7EB;\">
            {t}
        </div>
        <div style=\"font-size:13px; color:#E5E7EB; line-height:1.45;\">
            {body_html}
        </div>
    </div>
    """
