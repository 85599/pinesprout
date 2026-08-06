"""
market_heatmap.py
Customizable TradingView Stock Heatmap widget, embedded via the official
TradingView widget embed script (no API key / scraping needed -- this is
TradingView's own public, free embeddable widget):

    https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/

Usage in your main app.py:

    from market_heatmap import render_heatmap_tab

    with tab_heatmap:
        render_heatmap_tab(theme="dark")   # or theme="light" -- wire to
                                            # your theme.get_theme() value
"""

from __future__ import annotations

import json

import streamlit as st

# US/Australia index universes confirmed via TradingView's own official
# widget demo pages (dataSource field).
DATA_SOURCES = {
    "S&P 500 (US)": "SPX500",
    "NASDAQ 100 (US)": "NASDAQ100",
    "Dow Jones (US)": "DOWJONES",
    "Russell 2000 (US)": "RUT2000",
    "All USA Stocks": "AllUSA",
    "ASX 200 (Australia)": "ASX200",
}

# Exchange codes for the widget's `exchanges` filter. NSE and BSE are
# TradingView's own primary Indian data sources (the same exchanges used
# in symbol search, e.g. NSE:RELIANCE, NSE:NIFTY); MSEI/NCDEX are the
# additional India-region providers confirmed via TradingView's official
# "Available Markets" documentation: https://www.tradingview.com/widget-docs/markets/
EXCHANGES_BY_REGION: dict[str, dict[str, str]] = {
    "🇮🇳 India": {
        "NSE — National Stock Exchange of India": "NSE",
        "BSE — Bombay Stock Exchange": "BSE",
        "MSEI — Metropolitan Stock Exchange": "MSEI",
        "NCDEX — Nat'l Commodity & Derivatives Exchange": "NCDEX",
    },
    "🌏 Asia-Pacific": {
        "ASX — Australian Securities Exchange": "ASX",
        "HSI — Hang Seng Indices (Hong Kong)": "HSI",
        "SSE — Shanghai Stock Exchange": "SSE",
        "SZSE — Shenzhen Stock Exchange": "SZSE",
        "IDX — Indonesia Stock Exchange": "IDX",
        "TPEX — Taipei Exchange": "TPEX",
        "TOCOM — Tokyo Commodity Exchange": "TOCOM",
        "CSE — Colombo Stock Exchange (Sri Lanka)": "CSE",
        "HNX — Hanoi Stock Exchange (Vietnam)": "HNX",
    },
    "🇪🇺 Europe": {
        "FWB/XETR — Frankfurt / Xetra (Germany)": "FWB",
        "MIL — Milan Stock Exchange (Italy)": "MIL",
        "BME — Bolsa de Madrid (Spain)": "BME",
        "SIX — SIX Swiss Exchange": "SIX",
        "GPW — Warsaw Stock Exchange (Poland)": "GPW",
        "OMX — Nasdaq OMX Group": "OMX",
        "ATHEX — Athens Stock Exchange (Greece)": "ATHEX",
        "BET — Budapest Stock Exchange (Hungary)": "BET",
        "VIE — Vienna Stock Exchange (Austria)": "VIE",
    },
}

GROUPINGS = {
    "No grouping": "no_group",
    "Sector": "sector",
    "Industry": "industry",
    "Asset class": "asset_class",
    "Country": "country",
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
    "6-month performance": "Perf.6M",
    "Year-to-date performance": "Perf.YTD",
    "1-year performance": "Perf.Y",
    "Relative volume (10d)": "relative_volume_10d_calc",
}

MODE_PRESET_INDEX = "Preset index (S&P 500, NASDAQ, ASX 200, ...)"
MODE_EXCHANGES = "Pick exchanges (India, Europe, Asia-Pacific, ...)"
MODE_CUSTOM = "Custom dataSource value"


def _build_widget_html(config: dict[str, object], height: int) -> str:
    """Build the TradingView widget embed fragment.

    Two defensive fixes vs. a naive embed, both aimed at a widget that
    renders tiny/blank inside Streamlit's sandboxed iframe:
      1. An explicit html/body CSS reset with height:100% -- percentage
         heights inside an iframe's auto-generated <html>/<body> don't
         resolve unless those elements themselves have a defined height.
      2. A literal pixel height passed to the widget config instead of
         "100%" -- percentage resolution inside a dynamically-injected,
         cross-origin srcdoc iframe can race the async widget script and
         resolve against zero before layout settles.
    """
    config = dict(config)
    inner_height = max(height - 8, 300)
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
    """st.iframe (Streamlit >= 1.4x) with a fallback to the older
    st.components.v1.html for projects pinned to an earlier Streamlit."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height, width="stretch")
    else:  # pragma: no cover - only hit on older Streamlit installs
        st.components.v1.html(html, height=height, scrolling=True)


def render_heatmap_tab(theme: str = "dark", key_prefix: str = "kj_heatmap") -> None:
    """Renders the full heatmap tab: user controls + the live widget.

    `theme` should be "dark" or "light" -- pass your app's current theme
    (e.g. from theme.get_theme()) so the widget visually matches the rest
    of the app.
    """
    st.markdown('<p class="section-header">📊 Live Stock Heatmap</p>', unsafe_allow_html=True)
    st.caption(
        "Powered by TradingView's free Stock Heatmap widget — fully interactive "
        "(hover for details, click to zoom into a sector). Covers US, India (NSE/BSE), "
        "Europe, and Asia-Pacific markets. Market tools by **Khushal Jain**."
    )

    market_mode = st.radio(
        "Market selection mode",
        [MODE_PRESET_INDEX, MODE_EXCHANGES, MODE_CUSTOM],
        horizontal=True,
        key=f"{key_prefix}_mode",
    )

    data_source: str | None = None
    exchange_codes: list[str] = []

    if market_mode == MODE_PRESET_INDEX:
        source_label = st.selectbox("Index / universe", list(DATA_SOURCES.keys()), key=f"{key_prefix}_source")
        data_source = DATA_SOURCES[source_label]

    elif market_mode == MODE_EXCHANGES:
        col_region, col_pick = st.columns([1, 2])
        with col_region:
            region = st.selectbox("Region", list(EXCHANGES_BY_REGION.keys()), key=f"{key_prefix}_region")
        with col_pick:
            options = list(EXCHANGES_BY_REGION[region].keys())
            picked = st.multiselect("Exchange(s)", options, default=options[:1], key=f"{key_prefix}_exchanges_{region}")
            exchange_codes = [EXCHANGES_BY_REGION[region][p] for p in picked]
        if not exchange_codes:
            st.warning("Pick at least one exchange, or switch to a preset index.")

    else:  # MODE_CUSTOM
        data_source = st.text_input(
            "Custom dataSource value",
            value="SPX500",
            help="Exact TradingView dataSource string for an index not listed above. "
            "Look this up via the live configurator on TradingView's widget-docs page: "
            "https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/",
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
        height = st.slider(
            "Widget height (px)", min_value=500, max_value=1800, value=1000, step=50, key=f"{key_prefix}_height"
        )

    if market_mode == MODE_EXCHANGES and not exchange_codes:
        st.info("Select an exchange above to load the heatmap.")
        return

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
    # Only send whichever selector is actually in use -- sending an empty
    # "dataSource": "" alongside a populated "exchanges" list (or vice
    # versa) can make the widget return zero matches.
    if exchange_codes:
        config["exchanges"] = exchange_codes
    if data_source:
        config["dataSource"] = data_source

    _render_html(_build_widget_html(config, height), height + 30)
