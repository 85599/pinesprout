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

import streamlit as st

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

DATA_SOURCES = {
    "S&P 500 (US)": "SPX500",
    "NASDAQ 100 (US)": "NASDAQ100",
    "Dow Jones (US)": "DOWJONES",
    "Russell 2000 (US)": "RUT2000",
    "All USA Stocks": "AllUSA",
    "ASX 200 (Australia)": "ASX200",
}

EXCHANGES_BY_REGION = {
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

NIFTY50 = [
    ("RELIANCE.NS", "Reliance"), ("TCS.NS", "TCS"), ("HDFCBANK.NS", "HDFC Bank"),
    ("INFY.NS", "Infosys"), ("ICICIBANK.NS", "ICICI Bank"), ("HINDUNILVR.NS", "HUL"),
    ("ITC.NS", "ITC"), ("SBIN.NS", "SBI"), ("BHARTIARTL.NS", "Airtel"),
    ("KOTAKBANK.NS", "Kotak Bank"), ("LT.NS", "L&T"), ("AXISBANK.NS", "Axis Bank"),
    ("BAJFINANCE.NS", "Bajaj Fin"), ("ASIANPAINT.NS", "Asian Paints"), ("MARUTI.NS", "Maruti"),
    ("SUNPHARMA.NS", "Sun Pharma"), ("TITAN.NS", "Titan"), ("WIPRO.NS", "Wipro"),
    ("ULTRACEMCO.NS", "UltraTech"), ("NESTLEIND.NS", "Nestle"), ("POWERGRID.NS", "Power Grid"),
    ("NTPC.NS", "NTPC"), ("HCLTECH.NS", "HCL Tech"), ("TECHM.NS", "Tech Mahindra"),
    ("M&M.NS", "M&M"), ("TATAMOTORS.NS", "Tata Motors"), ("TATASTEEL.NS", "Tata Steel"),
    ("JSWSTEEL.NS", "JSW Steel"), ("ADANIENT.NS", "Adani Ent"), ("ADANIPORTS.NS", "Adani Ports"),
    ("ONGC.NS", "ONGC"), ("COALINDIA.NS", "Coal India"), ("BPCL.NS", "BPCL"),
    ("IOC.NS", "IOC"), ("INDUSINDBK.NS", "IndusInd"), ("BAJAJFINSV.NS", "Bajaj Finserv"),
    ("HDFCLIFE.NS", "HDFC Life"), ("SBILIFE.NS", "SBI Life"), ("GRASIM.NS", "Grasim"),
    ("CIPLA.NS", "Cipla"), ("DRREDDY.NS", "Dr Reddy"), ("APOLLOHOSP.NS", "Apollo Hosp"),
    ("EICHERMOT.NS", "Eicher"), ("HEROMOTOCO.NS", "Hero Moto"), ("BAJAJ-AUTO.NS", "Bajaj Auto"),
    ("BRITANNIA.NS", "Britannia"), ("DIVISLAB.NS", "Divi's Lab"), ("UPL.NS", "UPL"),
    ("TATACONSUM.NS", "Tata Cons."), ("SHREECEM.NS", "Shree Cem"),
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
        return {"symbol": symbol, "name": name, "price": price, "change_pct": change_pct}
    except Exception:
        return {"symbol": symbol, "name": name, "price": None, "change_pct": None}


@st.cache_data(ttl=120)
def _load_nifty50_data() -> list[dict]:
    if not HAS_YF:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(_fetch_one, sym, name) for sym, name in NIFTY50]
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda x: abs(x["change_pct"] or 0), reverse=True)
    return results


def _color_for_change(pct):
    if pct is None:
        return "#555555"
    if pct >= 3: return "#006400"
    if pct >= 1.5: return "#228B22"
    if pct >= 0.3: return "#2E8B57"
    if pct > -0.3: return "#6B7280"
    if pct > -1.5: return "#B22222"
    if pct > -3: return "#8B0000"
    return "#5C0000"


def render_india_nifty_heatmap(theme: str = "dark") -> None:
    st.subheader("🇮🇳 Nifty 50 Live Heatmap")
    st.caption("Yahoo Finance live data • Green = up, Red = down • Sorted by biggest movers")

    if not HAS_YF:
        st.error("yfinance not installed")
        return

    with st.spinner("Loading Nifty 50..."):
        data = _load_nifty50_data()

    if not data:
        st.warning("Data load failed. Try again.")
        return

    ups = sum(1 for d in data if (d["change_pct"] or 0) > 0)
    downs = sum(1 for d in data if (d["change_pct"] or 0) < 0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stocks", len(data))
    c2.metric("▲ Advancing", ups)
    c3.metric("▼ Declining", downs)
    c4.metric("Unchanged", len(data) - ups - downs)

    st.markdown("")
    cols_per_row = 5
    for i in range(0, len(data), cols_per_row):
        row = data[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, item in zip(cols, row):
            pct = item["change_pct"]
            bg = _color_for_change(pct)
            price_str = f"₹{item['price']:,.2f}" if item["price"] is not None else "—"
            pct_str = f"{pct:+.2f}%" if pct is not None else "—"
            col.markdown(
                f"""
                <div style="background:{bg};color:#fff;border-radius:10px;padding:12px 8px;
                            margin:4px 0;text-align:center;min-height:88px;
                            box-shadow:0 2px 6px rgba(0,0,0,0.25);">
                    <div style="font-size:0.72rem;opacity:0.9;">{item['name']}</div>
                    <div style="font-size:1.05rem;font-weight:700;margin:4px 0;">{price_str}</div>
                    <div style="font-size:0.9rem;font-weight:600;">{pct_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.button("🔄 Refresh", key="nifty_refresh"):
        st.cache_data.clear()
        st.rerun()


def _build_widget_html(config: dict, height: int) -> str:
    config = dict(config)
    inner = max(height - 8, 400)
    config["width"] = "100%"
    config["height"] = str(inner)
    cfg = json.dumps(config)
    return f"""<!DOCTYPE html><html><head>
<style>html,body{{margin:0;padding:0;height:100%;width:100%;overflow:hidden;background:transparent}}</style>
</head><body>
<div class="tradingview-widget-container" style="height:{inner}px;width:100%;">
<div class="tradingview-widget-container__widget" style="height:{inner}px;width:100%;"></div>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
{cfg}
</script></div></body></html>"""


def _render_html(html: str, height: int) -> None:
    if hasattr(st, "iframe"):
        st.iframe(html, height=height, width="stretch")
    else:
        st.components.v1.html(html, height=height, scrolling=True)


def render_tradingview_heatmap(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    st.subheader("🌍 TradingView Global Heatmap")
    st.info(
        "**India (NSE/BSE) ke liye upar wala Nifty 50 tab use karo.** "
        "TradingView free widget India exchanges pe aksar blank aata hai — yeh unki limitation hai."
    )

    market_mode = st.radio(
        "Market selection",
        ["Preset index (S&P 500, NASDAQ...)", "Pick exchanges", "Custom dataSource"],
        horizontal=True,
        key=f"{key_prefix}_mode",
        index=0,
    )

    data_source = None
    exchange_codes = []

    if market_mode.startswith("Preset"):
        label = st.selectbox("Index", list(DATA_SOURCES.keys()), key=f"{key_prefix}_src")
        data_source = DATA_SOURCES[label]
    elif market_mode.startswith("Pick"):
        c1, c2 = st.columns([1, 2])
        with c1:
            region = st.selectbox("Region", list(EXCHANGES_BY_REGION.keys()), key=f"{key_prefix}_reg")
        with c2:
            opts = list(EXCHANGES_BY_REGION[region].keys())
            picked = st.multiselect("Exchange(s)", opts, default=opts[:1], key=f"{key_prefix}_ex")
            exchange_codes = [EXCHANGES_BY_REGION[region][p] for p in picked]
        if region.startswith("🇮🇳"):
            st.warning("⚠️ NSE/BSE pe TradingView blank ho sakta hai. Nifty 50 tab use karo.")
        if not exchange_codes:
            st.warning("Kam se kam 1 exchange select karo.")
            return
    else:
        data_source = st.text_input("dataSource", value="SPX500", key=f"{key_prefix}_custom")

    c1, c2, c3 = st.columns(3)
    with c1:
        grp = st.selectbox("Group by", list(GROUPINGS.keys()), key=f"{key_prefix}_grp")
    with c2:
        size = st.selectbox("Block size", list(BLOCK_SIZES.keys()), key=f"{key_prefix}_sz")
    with c3:
        color = st.selectbox("Color by", list(BLOCK_COLORS.keys()), key=f"{key_prefix}_col")

    c4, c5, c6 = st.columns(3)
    with c4:
        topbar = st.checkbox("Show top bar", True, key=f"{key_prefix}_tb")
    with c5:
        zoom = st.checkbox("Allow zoom", True, key=f"{key_prefix}_zm")
    with c6:
        height = st.slider("Height (px)", 500, 1600, 900, 50, key=f"{key_prefix}_ht")

    config = {
        "grouping": GROUPINGS[grp],
        "blockSize": BLOCK_SIZES[size],
        "blockColor": BLOCK_COLORS[color],
        "locale": "en",
        "symbolUrl": "",
        "colorTheme": "dark" if theme == "dark" else "light",
        "hasTopBar": topbar,
        "isDataSetEnabled": False,
        "isZoomEnabled": zoom,
        "hasSymbolTooltip": True,
    }
    if exchange_codes:
        config["exchanges"] = exchange_codes
    if data_source:
        config["dataSource"] = data_source

    _render_html(_build_widget_html(config, height), height + 40)


def render_heatmap_tab(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    """Called from streamlit_app.py — shows India first, then TradingView."""
    tab_india, tab_tv = st.tabs([
        "🇮🇳 Nifty 50 Heatmap (Recommended)",
        "🌍 TradingView Global (US/Europe/Asia)",
    ])
    with tab_india:
        render_india_nifty_heatmap(theme=theme)
    with tab_tv:
        render_tradingview_heatmap(theme=theme, key_prefix=key_prefix)
