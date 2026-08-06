"""
index_watch.py
A native-Streamlit, NSE-style "Index Watch" dashboard for Indian market
indices -- visually inspired by NSE's own Live Market Indices Heatmap
(https://www.nseindia.com/market-data/live-market-indices/heatmap):
categorized tabs, colored tiles per index, an up/down summary bar, plus
an Overview tab with charts, a searchable/downloadable data table, and
optional auto-refresh.

Why this instead of scraping nseindia.com directly: NSE's site allows
general crawling per robots.txt, but its live data endpoints require a
full browser session handshake and are explicitly hardened against
automated/non-browser access, and NSE's terms restrict systematic
redistribution of their market data. Rather than build something that
fights those protections (fragile, and legally murky for a public
open-source app), this pulls the same category of data from Yahoo
Finance via `yfinance` -- the same library already used by
streamlit_ticker.py -- and renders it as a 100% native Streamlit grid.
Because every tile is real Streamlit markup (not embedded in an
iframe), the whole page is naturally interactive everywhere, matching
the "click anywhere" behavior of NSE's own page.

Coverage note: Yahoo Finance's coverage of granular NSE sub-indices
(sectoral/thematic/strategy indices) is inconsistent -- some tickers
below may occasionally show "N/A" if Yahoo doesn't carry that series.
Broad market indices (NIFTY 50, SENSEX, BANK NIFTY, etc.) are reliably
available. Every ticker below has been individually verified against
Yahoo Finance's own listing pages.

Optional dependencies: `plotly` (charts) and `streamlit-autorefresh`
(hands-free periodic refresh). Both degrade gracefully if not
installed -- charts are skipped with a one-line notice, and refresh
falls back to the manual "Refresh now" button.

Usage in your main app.py:

    from pinesprout.utils.index_watch import render_index_watch

    render_index_watch(theme="dark")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import streamlit as st
import yfinance as yf

try:
    import plotly.express as px

    PLOTLY_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when plotly is absent
    PLOTLY_AVAILABLE = False

try:
    from streamlit_autorefresh import st_autorefresh

    AUTOREFRESH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when the package is absent
    AUTOREFRESH_AVAILABLE = False

# yfinance logs a "possibly delisted; no price data found" warning (via the
# stdlib `logging` module) for every failed fetch attempt -- with 3 retry
# attempts per symbol x 2 lookback periods, one bad/unavailable ticker can
# flood the console with a dozen+ lines every refresh cycle. We already
# handle fetch failures gracefully (an "N/A" tile) so these warnings add
# nothing but noise; silence them at the source rather than per-call.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

REFRESH_SECONDS = 30

CATEGORIES: dict[str, dict[str, str]] = {
    "Broad Market Indices": {
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "NIFTY BANK": "^NSEBANK",
        "NIFTY NEXT 50": "^NSMIDCP",
        "NIFTY 100": "^CNX100",
        "NIFTY 500": "^CRSLDX",
    },
    "Sectoral Indices": {
        "NIFTY IT": "^CNXIT",
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY PHARMA": "^CNXPHARMA",
        "NIFTY FMCG": "^CNXFMCG",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY REALTY": "^CNXREALTY",
        "NIFTY ENERGY": "^CNXENERGY",
        "NIFTY MEDIA": "^CNXMEDIA",
    },
    "Thematic Indices": {
        "NIFTY PSU BANK": "^CNXPSUBANK",
        "NIFTY INFRA": "^CNXINFRA",
        "NIFTY MNC": "^CNXMNC",
        "NIFTY CONSUMPTION": "^CNXCONSUM",
    },
    "Currency & Commodities": {
        "USD/INR": "INR=X",
        "GOLD": "GC=F",
        "SILVER": "SI=F",
        "CRUDE OIL": "CL=F",
    },
}

AUTOREFRESH_OPTIONS: dict[str, int | None] = {
    "Off": None,
    "30 sec": 30_000,
    "1 min": 60_000,
    "2 min": 120_000,
    "5 min": 300_000,
}


@dataclass
class IndexQuote:
    label: str
    category: str = ""
    price: float | None = None
    change_pct: float | None = None
    day_open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    prev_close: float | None = None
    ok: bool = False


def _fetch_quotes(symbols: dict[str, str], category: str = "") -> list[IndexQuote]:
    quotes: list[IndexQuote] = []
    for label, symbol in symbols.items():
        q = IndexQuote(label=label, category=category)
        try:
            t = yf.Ticker(symbol)
            fast = t.fast_info
            price = fast.get("lastPrice") or fast.get("last_price")
            prev_close = fast.get("previousClose") or fast.get("previous_close")
            if price is not None:
                q.price = float(price)
                q.ok = True
                q.day_open = fast.get("open")
                q.day_high = fast.get("dayHigh") or fast.get("day_high")
                q.day_low = fast.get("dayLow") or fast.get("day_low")
                if prev_close:
                    q.prev_close = float(prev_close)
                    q.change_pct = (float(price) - float(prev_close)) / float(prev_close) * 100
        except Exception:
            pass
        quotes.append(q)
    return quotes


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def _cached_category_quotes(category: str, symbol_items: tuple[tuple[str, str], ...]) -> list[IndexQuote]:
    return _fetch_quotes(dict(symbol_items), category=category)


def _all_quotes() -> list[IndexQuote]:
    quotes: list[IndexQuote] = []
    for category, symbols in CATEGORIES.items():
        quotes.extend(_cached_category_quotes(category, tuple(symbols.items())))
    return quotes


def _tile_html(q: IndexQuote, bg2: str, border: str, text: str) -> str:
    if not q.ok or q.price is None:
        return f"""
        <div style="background:{bg2};border:1px solid {border};border-radius:10px;
                     padding:0.8rem 0.9rem;height:78px;">
          <div style="font-size:0.78rem;font-weight:700;color:{text};opacity:0.6;">{q.label}</div>
          <div style="font-size:0.85rem;color:{text};opacity:0.5;margin-top:0.4rem;">N/A</div>
        </div>
        """
    up = (q.change_pct or 0) >= 0
    tile_bg = "rgba(23,138,76,0.18)" if up else "rgba(198,48,62,0.18)"
    tile_border = "#178A4C" if up else "#C6303E"
    change_str = f"{'+' if up else ''}{q.change_pct:.2f}%" if q.change_pct is not None else "—"
    return f"""
    <div style="background:{tile_bg};border:1px solid {tile_border};border-radius:10px;
                 padding:0.8rem 0.9rem;height:78px;">
      <div style="font-size:0.78rem;font-weight:700;color:{text};white-space:nowrap;
                   overflow:hidden;text-overflow:ellipsis;">{q.label}</div>
      <div style="font-size:1.05rem;font-weight:700;color:{text};margin-top:0.25rem;">
        {q.price:,.2f}
      </div>
      <div style="font-size:0.82rem;font-weight:700;color:{tile_border};">{change_str}</div>
    </div>
    """


def _render_overview(quotes: list[IndexQuote], key_prefix: str) -> None:
    ok_quotes = [q for q in quotes if q.ok and q.change_pct is not None]

    up_count = sum(1 for q in ok_quotes if (q.change_pct or 0) >= 0)
    down_count = sum(1 for q in ok_quotes if (q.change_pct or 0) < 0)
    na_count = len(quotes) - len(ok_quotes)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 Advancing", up_count)
    c2.metric("🔴 Declining", down_count)
    c3.metric("⚪ No data", na_count)
    c4.metric("📊 Total tracked", len(quotes))

    if not PLOTLY_AVAILABLE:
        st.info("Install `plotly` for charts here (`pip install plotly`). Tables and tiles below work either way.")
    elif ok_quotes:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            sorted_quotes = sorted(ok_quotes, key=lambda q: q.change_pct or 0, reverse=True)
            fig = px.bar(
                x=[q.label for q in sorted_quotes],
                y=[q.change_pct for q in sorted_quotes],
                color=[q.change_pct for q in sorted_quotes],
                color_continuous_scale=["#C6303E", "#9AA4B2", "#178A4C"],
                color_continuous_midpoint=0,
                labels={"x": "", "y": "% change"},
                title="% Change by Index",
            )
            fig.update_layout(xaxis_tickangle=45, showlegend=False, coloraxis_showscale=False, margin=dict(t=40, b=0))
            st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_bar")
        with col_chart2:
            sentiment_df = {
                "Sentiment": ["Advancing", "Declining", "No data"],
                "Count": [up_count, down_count, na_count],
            }
            fig2 = px.pie(
                sentiment_df,
                values="Count",
                names="Sentiment",
                title="Market Sentiment",
                color="Sentiment",
                color_discrete_map={"Advancing": "#178A4C", "Declining": "#C6303E", "No data": "#9AA4B2"},
            )
            fig2.update_layout(margin=dict(t=40, b=0))
            st.plotly_chart(fig2, width="stretch", key=f"{key_prefix}_pie")

    st.markdown("##### 📋 Data Table")
    search = st.text_input("🔍 Search indices", key=f"{key_prefix}_search", placeholder="e.g. BANK, IT, GOLD")
    rows: list[dict[str, object]] = [
        {
            "Index": q.label,
            "Category": q.category,
            "Price": q.price,
            "% Change": round(q.change_pct, 2) if q.change_pct is not None else None,
            "Open": q.day_open,
            "High": q.day_high,
            "Low": q.day_low,
            "Prev Close": q.prev_close,
        }
        for q in quotes
    ]
    if search:
        rows = [r for r in rows if search.lower() in str(r["Index"]).lower()]

    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download as CSV",
            data=csv,
            file_name=f"nse_index_watch_{datetime.now(UTC).strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv",
        )
    except ImportError:  # pragma: no cover - pandas ships with streamlit's own deps
        st.table(rows)


def render_index_watch(theme: str = "dark", key_prefix: str = "idx_watch") -> None:
    """Render the full NSE-style Index Watch: refresh controls + an
    Overview tab (charts, search, CSV export) + category tile-grid tabs,
    all native Streamlit (no iframe)."""
    bg2 = "#161B22" if theme == "dark" else "#F5F7FA"
    border = "#2A2F3A" if theme == "dark" else "#E1E5EA"
    text = "#FAFAFA" if theme == "dark" else "#14171A"

    st.markdown('<p class="section-header">🇮🇳 NSE Index Watch</p>', unsafe_allow_html=True)
    st.caption(
        "Live NIFTY/SENSEX/sectoral index tiles in an NSE-style grid — fully native, so "
        "clicking, hovering, and scrolling anywhere on the page works normally (no embedded "
        "widget sandbox). Data via Yahoo Finance; some niche sub-indices may show N/A if "
        "Yahoo doesn't carry that series. *Built by Khushal Jain.*"
    )

    col_refresh, col_status = st.columns([2, 3])
    with col_refresh:
        if AUTOREFRESH_AVAILABLE:
            refresh_choice = st.selectbox(
                "Auto-refresh", list(AUTOREFRESH_OPTIONS.keys()), index=0, key=f"{key_prefix}_autorefresh"
            )
            ms = AUTOREFRESH_OPTIONS[refresh_choice]
            if ms:
                st_autorefresh(interval=ms, key=f"{key_prefix}_autorefresh_tick")
        else:
            st.caption("💡 `pip install streamlit-autorefresh` for hands-free auto-refresh.")
            if st.button("🔄 Refresh now", key=f"{key_prefix}_refresh"):
                _cached_category_quotes.clear()
                st.rerun()
    with col_status:
        if f"{key_prefix}_last_fetch" not in st.session_state:
            st.session_state[f"{key_prefix}_last_fetch"] = datetime.now(UTC)
        age = (datetime.now(UTC) - st.session_state[f"{key_prefix}_last_fetch"]).seconds
        st.caption(f"🕒 Data cached for up to {REFRESH_SECONDS}s · this render: {age}s ago")

    all_quotes = _all_quotes()

    tab_labels = ["📈 Overview", *list(CATEGORIES.keys())]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        _render_overview(all_quotes, key_prefix)

    for tab, category in zip(tabs[1:], CATEGORIES.keys(), strict=False):
        with tab:
            quotes = [q for q in all_quotes if q.category == category]

            up_count = sum(1 for q in quotes if q.ok and (q.change_pct or 0) >= 0)
            down_count = sum(1 for q in quotes if q.ok and (q.change_pct or 0) < 0)
            na_count = sum(1 for q in quotes if not q.ok)

            c1, c2, c3 = st.columns(3)
            c1.metric("🟢 Advancing", up_count)
            c2.metric("🔴 Declining", down_count)
            c3.metric("⚪ No data", na_count)

            cols_per_row = 4
            for row_start in range(0, len(quotes), cols_per_row):
                row = quotes[row_start : row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, q in zip(cols, row, strict=False):
                    with col:
                        st.markdown(_tile_html(q, bg2, border, text), unsafe_allow_html=True)
                        st.write("")

    if st.button("🔄 Refresh all data now", key=f"{key_prefix}_refresh_all"):
        _cached_category_quotes.clear()
        st.session_state[f"{key_prefix}_last_fetch"] = datetime.now(UTC)
        st.rerun()
