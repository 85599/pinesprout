"""
about.py
The "About" section for PineSprout Studio -- developer credit, social
links, and a friendly feature showcase.

Usage in your main app.py:

    from pinesprout.utils.about import render_about_section

    render_about_section()
"""

from __future__ import annotations

from typing import Literal

import streamlit as st

DEVELOPER_NAME = "Khushal Jain"

LINKS: list[tuple[str, str, Literal["primary", "secondary", "tertiary"]]] = [
    ("📈 TradingView", "https://in.tradingview.com/u/khushaljain023/", "primary"),
    ("𝕏 Twitter / X", "https://x.com/khushaljai48011", "secondary"),
    ("💻 GitHub", "https://github.com/85599", "secondary"),
]

FEATURE_CARDS: list[tuple[str, str, str]] = [
    ("✨", "AI Generator", "Describe a strategy in plain English, get working Pine Script back."),
    ("🧪", "Template Builder", "25 indicators × 4 signal patterns — thousands of combos to explore."),
    ("🔍", "Linter", "Unused vars, repaint risk, deprecated syntax, and performance checks."),
    ("🧹", "Formatter", "Deterministic, consistent formatting on every save."),
    ("⬆️", "Version Upgrader", "Migrate Pine v4 → v5 → v6 automatically."),
    ("📊", "Live Heatmap", "TradingView's Stock Heatmap — India, US, Europe, Asia-Pacific."),
    ("📡", "Market Ticker", "Live NIFTY, SENSEX, BANK NIFTY, and commodities banner."),
    ("📄", "Docs & Reports", "One-click README, HTML/Markdown docs, and analysis reports."),
]


def render_about_section() -> None:
    # Custom colors per social link, targeted by href so they're robust
    # regardless of DOM ordering: saffron for TradingView, white for
    # X/Twitter, green for GitHub.
    st.markdown(
        """
        <style>
        a[data-testid="stBaseLinkButton-secondary"][href*="tradingview.com"],
        a[href*="tradingview.com"] {
            background-color: #FF9933 !important;
            border-color: #FF9933 !important;
            color: #FFFFFF !important;
        }
        a[href*="x.com/"], a[href*="twitter.com"] {
            background-color: #FFFFFF !important;
            border-color: #D0D5DB !important;
            color: #14171A !important;
        }
        a[href*="github.com"] {
            background-color: #22A55A !important;
            border-color: #22A55A !important;
            color: #FFFFFF !important;
        }
        a[href*="tradingview.com"]:hover,
        a[href*="x.com/"]:hover, a[href*="twitter.com"]:hover,
        a[href*="github.com"]:hover {
            filter: brightness(1.08);
        }
        a[href*="tradingview.com"] *,
        a[href*="x.com/"] *, a[href*="twitter.com"] *,
        a[href*="github.com"] * {
            color: inherit !important;
            fill: inherit !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="text-align:center; padding: 1.2rem 0 0.4rem 0;">
          <div style="font-size:2.6rem; line-height:1;">🌲🌱</div>
          <div style="font-size:1.8rem; font-weight:800; margin-top:0.3rem;">
            PineSprout Studio
          </div>
          <div style="opacity:0.75; font-size:1.05rem; margin-top:0.2rem;">
            Where Pine Script ideas take root and grow.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, rgba(41,98,255,0.12), rgba(41,98,255,0.02));
            border: 1px solid rgba(41,98,255,0.25);
            border-radius: 14px;
            padding: 1rem 1.3rem;
            margin: 1rem 0 1.4rem 0;
            text-align:center;
        ">
          👨‍💻 Built with care by <b>{DEVELOPER_NAME}</b> — open-source, and free to use.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-header">🔗 Connect</p>', unsafe_allow_html=True)
    cols = st.columns(len(LINKS))
    for col, (label, url, kind) in zip(cols, LINKS, strict=False):
        col.link_button(label, url, width="stretch", type=kind)

    st.markdown('<p class="section-header" style="margin-top:1.6rem;">🧰 What\'s inside</p>', unsafe_allow_html=True)

    for row_start in range(0, len(FEATURE_CARDS), 4):
        row = FEATURE_CARDS[row_start : row_start + 4]
        cols = st.columns(4)
        for col, (icon, title, desc) in zip(cols, row, strict=False):
            with col:
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid var(--kj-border, #2A2F3A);
                        border-radius: 12px;
                        padding: 0.9rem 0.8rem;
                        height: 148px;
                        margin-bottom: 0.8rem;
                        transition: transform 0.15s ease;
                    ">
                      <div style="font-size:1.6rem;">{icon}</div>
                      <div style="font-weight:700; margin-top:0.35rem;">{title}</div>
                      <div style="font-size:0.82rem; opacity:0.75; margin-top:0.25rem;">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.caption("🌱 PineSprout grows with every idea you plant. Happy building!")
