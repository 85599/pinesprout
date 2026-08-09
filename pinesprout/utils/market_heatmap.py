"""
market_heatmap.py
-----------------
India: Native Nifty 50 cards + Plotly Treemap heatmap (yfinance)
Global: TradingView widget only for US/preset indices (works reliably)

No dependency on TradingView for Indian data.
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

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

DATA_SOURCES = {
    "S&P 500 (US)": "SPX500",
    "NASDAQ 100 (US)": "NASDAQ100",
    "Dow Jones (US)": "DOWJONES",
    "Russell 2000 (US)": "RUT2000",
    "All USA Stocks": "AllUSA",
    "ASX 200 (Australia)": "ASX200",
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
    "Year-to-date performance": "Perf.YTD",
}

NIFTY50 = [
    ("RELIANCE.NS", "Reliance", "Energy"),
    ("TCS.NS", "TCS", "IT"),
    ("HDFCBANK.NS", "HDFC Bank", "Banking"),
    ("INFY.NS", "Infosys", "IT"),
    ("ICICIBANK.NS", "ICICI Bank", "Banking"),
    ("HINDUNILVR.NS", "HUL", "FMCG"),
    ("ITC.NS", "ITC", "FMCG"),
    ("SBIN.NS", "SBI", "Banking"),
    ("BHARTIARTL.NS", "Airtel", "Telecom"),
    ("KOTAKBANK.NS", "Kotak Bank", "Banking"),
    ("LT.NS", "L&T", "Industrial"),
    ("AXISBANK.NS", "Axis Bank", "Banking"),
    ("BAJFINANCE.NS", "Bajaj Fin", "Finance"),
    ("ASIANPAINT.NS", "Asian Paints", "Consumer"),
    ("MARUTI.NS", "Maruti", "Auto"),
    ("SUNPHARMA.NS", "Sun Pharma", "Pharma"),
    ("TITAN.NS", "Titan", "Consumer"),
    ("WIPRO.NS", "Wipro", "IT"),
    ("ULTRACEMCO.NS", "UltraTech", "Cement"),
    ("NESTLEIND.NS", "Nestle", "FMCG"),
    ("POWERGRID.NS", "Power Grid", "Energy"),
    ("NTPC.NS", "NTPC", "Energy"),
    ("HCLTECH.NS", "HCL Tech", "IT"),
    ("TECHM.NS", "Tech Mahindra", "IT"),
    ("M&M.NS", "M&M", "Auto"),
    ("TATAMOTORS.NS", "Tata Motors", "Auto"),
    ("TATASTEEL.NS", "Tata Steel", "Metal"),
    ("JSWSTEEL.NS", "JSW Steel", "Metal"),
    ("ADANIENT.NS", "Adani Ent", "Conglomerate"),
    ("ADANIPORTS.NS", "Adani Ports", "Industrial"),
    ("ONGC.NS", "ONGC", "Energy"),
    ("COALINDIA.NS", "Coal India", "Energy"),
    ("BPCL.NS", "BPCL", "Energy"),
    ("IOC.NS", "IOC", "Energy"),
    ("INDUSINDBK.NS", "IndusInd", "Banking"),
    ("BAJAJFINSV.NS", "Bajaj Finserv", "Finance"),
    ("HDFCLIFE.NS", "HDFC Life", "Finance"),
    ("SBILIFE.NS", "SBI Life", "Finance"),
    ("GRASIM.NS", "Grasim", "Cement"),
    ("CIPLA.NS", "Cipla", "Pharma"),
    ("DRREDDY.NS", "Dr Reddy", "Pharma"),
    ("APOLLOHOSP.NS", "Apollo Hosp", "Healthcare"),
    ("EICHERMOT.NS", "Eicher", "Auto"),
    ("HEROMOTOCO.NS", "Hero Moto", "Auto"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto", "Auto"),
    ("BRITANNIA.NS", "Britannia", "FMCG"),
    ("DIVISLAB.NS", "Divi's Lab", "Pharma"),
    ("UPL.NS", "UPL", "Chemicals"),
    ("TATACONSUM.NS", "Tata Cons.", "FMCG"),
    ("SHREECEM.NS", "Shree Cem", "Cement"),
]


def _fetch_one(symbol: str, name: str, sector: str) -> dict:
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose")
        mcap = info.get("marketCap") or 0
        change_pct = None
        if price is not None and prev:
            change_pct = ((price - prev) / prev) * 100
        return {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "price": price,
            "change_pct": change_pct,
            "market_cap": mcap if mcap else 1,
        }
    except Exception:  # noqa: BLE001
        return {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "price": None,
            "change_pct": None,
            "market_cap": 1,
        }


@st.cache_data(ttl=120)
def _load_nifty50_data() -> list[dict]:
    if not HAS_YF:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(_fetch_one, s, n, sec) for s, n, sec in NIFTY50]
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda x: abs(x["change_pct"] or 0), reverse=True)
    return results


def _color_for_change(pct):
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


def _render_cards(data: list[dict]) -> None:
    cols_per_row = 5
    for i in range(0, len(data), cols_per_row):
        row = data[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, item in zip(cols, row, strict=False):
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


def _render_treemap(data: list[dict], theme: str) -> None:
    if not HAS_PLOTLY:
        st.warning("plotly not installed — pip install plotly")
        return

    import pandas as pd

    rows = [d for d in data if d["price"] is not None]
    if not rows:
        st.warning("No price data for treemap.")
        return

    df = pd.DataFrame(rows)
    df["change_pct"] = df["change_pct"].fillna(0)
    df["market_cap"] = df["market_cap"].clip(lower=1)

    fig = px.treemap(
        df,
        path=["sector", "name"],
        values="market_cap",
        color="change_pct",
        color_continuous_scale=["#8B0000", "#B22222", "#6B7280", "#2E8B57", "#006400"],
        color_continuous_midpoint=0,
        hover_data={"price": ":.2f", "change_pct": ":.2f", "market_cap": ":,.0f"},
        title="Nifty 50 Treemap — box size = Market Cap, color = 1D Change %",
    )
    fig.update_layout(
        margin={"t": 40, "l": 10, "r": 10, "b": 10},
        height=650,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0e0e0" if theme == "dark" else "#222"},
        coloraxis_colorbar={"title": "Change %"},
    )
    fig.update_traces(
        textinfo="label",
        textfont_size=12,
        marker={"line": {"width": 1, "color": "#111" if theme == "dark" else "#fff"}},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_india_heatmap(theme: str = "dark") -> None:
    st.subheader("India Nifty 50 Market Heatmap")
    st.caption(
        "Live Yahoo Finance data • Treemap = size by market cap, color by % change • Cards = quick view"
    )

    if not HAS_YF:
        st.error("Install yfinance: pip install yfinance")
        return

    with st.spinner("Loading Nifty 50 live data..."):
        data = _load_nifty50_data()

    if not data:
        st.warning("Could not load data. Check internet and try Refresh.")
        return

    ups = sum(1 for d in data if (d["change_pct"] or 0) > 0)
    downs = sum(1 for d in data if (d["change_pct"] or 0) < 0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stocks", len(data))
    c2.metric("Advancing", ups)
    c3.metric("Declining", downs)
    c4.metric("Unchanged", len(data) - ups - downs)

    view = st.radio(
        "View",
        ["Treemap Heatmap", "Color Cards", "Both"],
        horizontal=True,
        key="india_hm_view",
        index=0,
    )

    if view in ("Treemap Heatmap", "Both"):
        st.markdown("#### Treemap (sector to stock)")
        _render_treemap(data, theme)

    if view in ("Color Cards", "Both"):
        st.markdown("#### Stock cards (sorted by biggest movers)")
        _render_cards(data)

    if st.button("Refresh data", key="nifty_refresh"):
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


def render_tradingview_global(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    st.subheader("Global Heatmap (TradingView)")
    st.caption("Best for US indices (S&P 500, NASDAQ). For India use the first tab.")

    source_label = st.selectbox(
        "Index / universe",
        list(DATA_SOURCES.keys()),
        key=f"{key_prefix}_src",
    )
    data_source = DATA_SOURCES[source_label]

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
        "dataSource": data_source,
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
    _render_html(_build_widget_html(config, height), height + 40)


def render_heatmap_tab(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    """Entry point used by streamlit_app.py"""
    tab_india, tab_global = st.tabs([
        "India Nifty 50 Heatmap",
        "Global (TradingView US/AU)",
    ])
    with tab_india:
        render_india_heatmap(theme=theme)
    with tab_global:
        render_tradingview_global(theme=theme, key_prefix=key_prefix)
