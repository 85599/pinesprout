"""
market_heatmap.py  (improved)
-----------------
- Native India (Nifty 50) heatmap built with yfinance — always works
- TradingView embed kept for global markets (US / Europe / Asia)
- Better defaults for India so the tab is never blank

"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ---------------------------------------------------------------------------
# TradingView config (global markets)
# ---------------------------------------------------------------------------
DATA_SOURCES = {
    "S&P 500 (US)": "SPX500",
    "NASDAQ 100 (US)": "NASDAQ100",
    "Dow Jones (US)": "DOWJONES",
    "Russell 2000 (US)": "RUT2000",
    "All USA Stocks": "AllUSA",
    "ASX 200 (Australia)": "ASX200",
}

EXCHANGES_BY_REGION: dict[str, dict[str, str]] = {
    "🇮🇳 India": {
        "NSE — National Stock Exchange of India": "NSE",
        "BSE — Bombay Stock Exchange": "BSE",
    },
    "🌏 Asia-Pacific": {
        "ASX — Australian Securities Exchange": "ASX",
        "HSI — Hang Seng Indices (Hong Kong)": "HSI",
        "SSE — Shanghai Stock Exchange": "SSE",
        "SZSE — Shenzhen Stock Exchange": "SZSE",
    },
    "🇪🇺 Europe": {
        "FWB/XETR — Frankfurt / Xetra (Germany)": "FWB",
        "MIL — Milan Stock Exchange (Italy)": "MIL",
        "BME — Bolsa de Madrid (Spain)": "BME",
        "SIX — SIX Swiss Exchange": "SIX",
        "OMX — Nasdaq OMX Group": "OMX",
    },
}

GROUPINGS = {
    "No grouping": "no_group",
    "Sector": "sector",
    "Industry": "industry",
}

BLOCK_SIZES = {
    "Market cap": "market_cap_basic",
    "Volume": "volume",
}

BLOCK_COLORS = {
    "1-day change %": "change",
    "1-week performance": "Perf.W",
    "1-month performance": "Perf.1M",
    "3-month performance": "Perf.3M",
    "Year-to-date performance": "Perf.YTD",
    "1-year performance": "Perf.Y",
}

# Nifty 50 constituents (Yahoo .NS symbols)
NIFTY50 = [
    ("RELIANCE.NS", "Reliance"),
    ("TCS.NS", "TCS"),
    ("HDFCBANK.NS", "HDFC Bank"),
    ("INFY.NS", "Infosys"),
    ("ICICIBANK.NS", "ICICI Bank"),
    ("HINDUNILVR.NS", "HUL"),
    ("ITC.NS", "ITC"),
    ("SBIN.NS", "SBI"),
    ("BHARTIARTL.NS", "Airtel"),
    ("KOTAKBANK.NS", "Kotak Bank"),
    ("LT.NS", "L&T"),
    ("AXISBANK.NS", "Axis Bank"),
    ("BAJFINANCE.NS", "Bajaj Fin"),
    ("ASIANPAINT.NS", "Asian Paints"),
    ("MARUTI.NS", "Maruti"),
    ("SUNPHARMA.NS", "Sun Pharma"),
    ("TITAN.NS", "Titan"),
    ("WIPRO.NS", "Wipro"),
    ("ULTRACEMCO.NS", "UltraTech"),
    ("NESTLEIND.NS", "Nestle"),
    ("POWERGRID.NS", "Power Grid"),
    ("NTPC.NS", "NTPC"),
    ("HCLTECH.NS", "HCL Tech"),
    ("TECHM.NS", "Tech Mahindra"),
    ("M&M.NS", "M&M"),
    ("TATAMOTORS.NS", "Tata Motors"),
    ("TATASTEEL.NS", "Tata Steel"),
    ("JSWSTEEL.NS", "JSW Steel"),
    ("ADANIENT.NS", "Adani Ent"),
    ("ADANIPORTS.NS", "Adani Ports"),
    ("ONGC.NS", "ONGC"),
    ("COALINDIA.NS", "Coal India"),
    ("BPCL.NS", "BPCL"),
    ("IOC.NS", "IOC"),
    ("INDUSINDBK.NS", "IndusInd"),
    ("BAJAJFINSV.NS", "Bajaj Finserv"),
    ("HDFCLIFE.NS", "HDFC Life"),
    ("SBILIFE.NS", "SBI Life"),
    ("GRASIM.NS", "Grasim"),
    ("CIPLA.NS", "Cipla"),
    ("DRREDDY.NS", "Dr Reddy"),
    ("APOLLOHOSP.NS", "Apollo Hosp"),
    ("EICHERMOT.NS", "Eicher"),
    ("HEROMOTOCO.NS", "Hero Moto"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto"),
    ("BRITANNIA.NS", "Britannia"),
    ("DIVISLAB.NS", "Divi's Lab"),
    ("UPL.NS", "UPL"),
    ("TATACONSUM.NS", "Tata Cons."),
    ("SHREECEM.NS", "Shree Cem"),
]


def _fetch_one(symbol: str, name: str) -> dict:
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose")
        change_pct = None
        if price is not None and prev:
            change_pct = ((price - prev) / prev) * 100
        return {
            "symbol": symbol,
            "name": name,
            "price": price,
            "change_pct": change_pct,
            "ok": price is not None,
        }
    except Exception:
        return {"symbol": symbol, "name": name, "price": None, "change_pct": None, "ok": False}


@st.cache_data(ttl=120)
def _load_nifty50_data() -> list[dict]:
    if not HAS_YF:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(_fetch_one, sym, name): (sym, name) for sym, name in NIFTY50}
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda x: abs(x["change_pct"] or 0), reverse=True)
    return results


def _color_for_change(pct: float | None) -> str:
    if pct is None:
        return "#555555"
    if pct >= 3:
        return "#006400"
    if pct >= 1.5:
        return "#228B22"
    if pct >= 0.3:
        return "#2E8B57"
    if pct > -0.3:
        return "#6B7280"
    if pct > -1.5:
        return "#B22222"
    if pct > -3:
        return "#8B0000"
    return "#5C0000"


def render_india_nifty_heatmap(theme: str = "dark") -> None:
    """Native Nifty 50 heatmap — works reliably, no TradingView dependency."""
    st.subheader("🇮🇳 Nifty 50 Heatmap (Live)")
    st.caption("Built with live Yahoo Finance data • Sorted by |change %|")

    if not HAS_YF:
        st.error("Install yfinance: `pip install yfinance`")
        return

    with st.spinner("Loading Nifty 50 prices..."):
        data = _load_nifty50_data()

    if not data:
        st.warning("Could not load data. Check internet / try again.")
        return

    ups = sum(1 for d in data if (d["change_pct"] or 0) > 0)
    downs = sum(1 for d in data if (d["change_pct"] or 0) < 0)
    flat = len(data) - ups - downs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stocks", len(data))
    c2.metric("▲ Advancing", ups)
    c3.metric("▼ Declining", downs)
    c4.metric("Unchanged", flat)

    st.markdown("")

    cols_per_row = 5
    for i in range(0, len(data), cols_per_row):
        row = data[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, item in zip(cols, row):
            pct = item["change_pct"]
            bg = _color_for_change(pct)
            price_str = f"₹{item['price']:,.2f}" if item["price"] is not None else "—"
            pct_str = f"{pct:+.2f}%" if pct is not None else "—"
            html = f"""
            <div style="
                background:{bg};
                color:#FFFFFF;
                border-radius:10px;
                padding:12px 10px;
                margin:4px 0;
                text-align:center;
                min-height:90px;
                box-shadow:0 2px 6px rgba(0,0,0,0.25);
            ">
                <div style="font-size:0.75rem;opacity:0.9;">{item['name']}</div>
                <div style="font-size:1.05rem;font-weight:700;margin:4px 0;">{price_str}</div>
                <div style="font-size:0.9rem;font-weight:600;">{pct_str}</div>
            </div>
            """
            col.markdown(html, unsafe_allow_html=True)

    if st.button("🔄 Refresh Nifty data", key="nifty_refresh"):
        st.cache_data.clear()
        st.rerun()


def _build_widget_html(config: dict[str, object], height: int) -> str:
    config = dict(config)
    inner_height = max(height - 8, 400)
    config["width"] = "100%"
    config["height"] = str(inner_height)
    config_json = json.dumps(config)
    return f"""<!DOCTYPE html>
<html>
<head>
<style>
  html, body {{ margin:0; padding:0; height:100%; width:100%; overflow:hidden; background:transparent; }}
</style>
</head>
<body>
  <div class="tradingview-widget-container" style="height:{inner_height}px;width:100%;">
    <div class="tradingview-widget-container__widget" style="height:{inner_height}px;width:100%;"></div>
    <script type="text/javascript"
            src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js"
            async>
    {config_json}
    </script>
  </div>
</body>
</html>
"""


def _render_html(html: str, height: int) -> None:
    if hasattr(st, "iframe"):
        st.iframe(html, height=height, width="stretch")
    else:
        st.components.v1.html(html, height=height, scrolling=True)


def render_tradingview_heatmap(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    """TradingView widget — best for US / global."""
    st.subheader("🌍 TradingView Global Heatmap")
    st.caption(
        "Official TradingView widget. **Tip:** For India use the Nifty 50 tab above — "
        "TradingView free embed often returns empty for NSE/BSE exchanges."
    )

    market_mode = st.radio(
        "Market selection mode",
        [
            "Preset index (S&P 500, NASDAQ, ...)",
            "Pick exchanges",
            "Custom dataSource",
        ],
        horizontal=True,
        key=f"{key_prefix}_mode",
        index=0,
    )

    data_source: str | None = None
    exchange_codes: list[str] = []

    if market_mode.startswith("Preset"):
        source_label = st.selectbox("Index / universe", list(DATA_SOURCES.keys()), key=f"{key_prefix}_source")
        data_source = DATA_SOURCES[source_label]

    elif market_mode.startswith("Pick"):
        col_region, col_pick = st.columns([1, 2])
        with col_region:
            region = st.selectbox("Region", list(EXCHANGES_BY_REGION.keys()), key=f"{key_prefix}_region")
        with col_pick:
            options = list(EXCHANGES_BY_REGION[region].keys())
            picked = st.multiselect(
                "Exchange(s)", options, default=options[:1], key=f"{key_prefix}_exchanges_{region}"
            )
            exchange_codes = [EXCHANGES_BY_REGION[region][p] for p in picked]
        if region.startswith("🇮🇳"):
            st.warning(
                "⚠️ TradingView free heatmap often shows **blank** for NSE/BSE. "
                "Use the **Nifty 50 Heatmap** tab for reliable India data."
            )
        if not exchange_codes:
            st.warning("Pick at least one exchange.")
            return
    else:
        data_source = st.text_input(
            "Custom dataSource",
            value="SPX500",
            key=f"{key_prefix}_custom_source",
        )

    col2, col3, col4 = st.columns(3)
    with col2:
        grouping_label = st.selectbox("Group by", list(GROUPINGS.keys()), key=f"{key_prefix}_group")
    with col3:
        size_label = st.selectbox("Block size", list(BLOCK_SIZES.keys()), key=f"{key_prefix}_size")
    with col4:
        color_label = st.selectbox("Color by", list(BLOCK_COLORS.keys()), index=0, key=f"{key_prefix}_color")

    col5, col6, col7 = st.columns(3)
    with col5:
        show_top_bar = st.checkbox("Show top bar", value=True, key=f"{key_prefix}_topbar")
    with col6:
        zoom_enabled = st.checkbox("Allow zoom", value=True, key=f"{key_prefix}_zoom")
    with col7:
        height = st.slider("Widget height (px)", 500, 1600, 900, 50, key=f"{key_prefix}_height")

    config: dict[str, object] = {
        "grouping": GROUPINGS[grouping_label],
        "blockSize": BLOCK_SIZES[size_label],
        "blockColor": BLOCK_COLORS[color_label],
        "locale": "en",
        "symbolUrl": "",
        "colorTheme": "dark" if theme == "dark" else "light",
        "hasTopBar": show_top_bar,
        "isDataSetEnabled": False,
        "isZoomEnabled": zoom_enabled,
        "hasSymbolTooltip": True,
    }
    if exchange_codes:
        config["exchanges"] = exchange_codes
    if data_source:
        config["dataSource"] = data_source

    _render_html(_build_widget_html(config, height), height + 40)


def render_heatmap_tab(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    """Main entry used by streamlit_app.py"""
    tab_india, tab_tv = st.tabs(["🇮🇳 Nifty 50 Heatmap (Recommended)", "🌍 TradingView Global"])

    with tab_india:
        render_india_nifty_heatmap(theme=theme)

    with tab_tv:
        render_tradingview_heatmap(theme=theme, key_prefix=key_prefix)
