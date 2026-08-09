"""PineSprout Studio — a Streamlit front-end for the PineSprout toolkit.

Lets you:
  * Describe your own strategy in plain English and have Claude generate
    a complete Pine Script file for it (e.g. "pivot point breakout with
    RSI confirmation"), OR
  * Pick a ready-made template (EMA cross, RSI, daily/weekly/monthly
    Pivot Points + Confluence zones, blank scaffolds), OR
  * Paste / upload a script you already have.

Every generated/uploaded script can then be linted, formatted, analyzed,
optimized, explained, and documented -- all in the browser, with
one-click downloads for each artifact.

Also includes a full **Indian Stock Market Dashboard** (NSE/BSE) with
Yahoo Finance style quotes, charts, financials, news & statistics.

Run locally:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd

# Optional market libs (for Indian Stock Dashboard)
try:
    import yfinance as yf
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_MARKET_LIBS = True
except ImportError:
    HAS_MARKET_LIBS = False

# PineSprout core (optional — app still works for market mode without it)
try:
    from pinesprout.core.analyzer import analyze
    from pinesprout.core.explainer import explain_script_summary, explain_source
    from pinesprout.core.formatter import FormatOptions, format_source
    from pinesprout.core.linter import Severity, lint_source
    from pinesprout.core.optimizer import optimize_source
    from pinesprout.core.upgrader import detect_version, upgrade_source
    from pinesprout.generators.ai_generator import (
        GenerationError,
        GenerationRequest,
        generate_pine_script,
    )
    from pinesprout.generators.doc_generator import DocFormat, generate_docs
    from pinesprout.generators.readme_generator import generate_readme
    from pinesprout.generators.report_generator import generate_report
    from pinesprout.generators.template_generator import (
        TemplateKind,
        TemplateSpec,
        generate_from_template,
    )
    from pinesprout.generators.template_builder import (
        INDICATORS,
        RiskPreset,
        RISK_PRESET_LABELS,
        SignalPattern,
        SIGNAL_PATTERN_LABELS,
        BuilderSpec,
        build_from_spec,
        estimate_combination_count,
        indicators_for_pattern,
    )
    from pinesprout.utils.about import render_about_section
    from pinesprout.utils.index_watch import render_index_watch
    from pinesprout.utils.market_heatmap import render_heatmap_tab
    from pinesprout.utils.streamlit_ticker import DEFAULT_SYMBOLS, render_ticker_banner
    from pinesprout.utils.theme import get_theme, init_theme, inject_theme_css, theme_toggle
    HAS_PINESPROUT = True
except ImportError:
    HAS_PINESPROUT = False
    # Minimal stubs so the file can still run the stock dashboard alone
    class Severity:
        ERROR = "error"
        WARNING = "warning"
        INFO = "info"
    def init_theme(default="dark"): pass
    def inject_theme_css(): pass
    def theme_toggle(**kwargs): pass
    def get_theme(): return "dark"
    def render_ticker_banner(*args, **kwargs): pass
    def render_index_watch(*args, **kwargs): st.info("PineSprout index watch not available.")
    def render_heatmap_tab(*args, **kwargs): st.info("PineSprout heatmap not available.")
    def render_about_section(): st.info("PineSprout about section not available.")
    DEFAULT_SYMBOLS = []

st.set_page_config(
    page_title="PineSprout Studio",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_theme(default="dark")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "pine_source" not in st.session_state:
    st.session_state.pine_source = ""
if "pine_filename" not in st.session_state:
    st.session_state.pine_filename = "script.pine"

if HAS_PINESPROUT:
    TEMPLATE_LABELS: dict[TemplateKind, str] = {
        TemplateKind.PIVOT_CONFLUENCE: "📐 Daily/Weekly/Monthly Pivot Points + Confluence Zones",
        TemplateKind.EMA_CROSS_INDICATOR: "📈 EMA Crossover Indicator",
        TemplateKind.RSI_INDICATOR: "📊 RSI Indicator",
        TemplateKind.EMA_CROSS_STRATEGY: "💰 EMA Crossover Strategy",
        TemplateKind.RSI_STRATEGY: "💰 RSI Mean-Reversion Strategy",
        TemplateKind.BLANK_INDICATOR: "⬜ Blank Indicator Scaffold",
        TemplateKind.BLANK_STRATEGY: "⬜ Blank Strategy Scaffold",
    }
    SEVERITY_ICON = {Severity.ERROR: "🔴", Severity.WARNING: "🟡", Severity.INFO: "🔵"}
else:
    TEMPLATE_LABELS = {}
    SEVERITY_ICON = {}


def _set_source(source: str, filename: str) -> None:
    st.session_state.pine_source = source
    st.session_state.pine_filename = filename


# ===========================================================================
# INDIAN STOCK MARKET DASHBOARD (Yahoo Finance style)
# ===========================================================================

POPULAR_STOCKS = {
    "Reliance Industries": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "SBI": "SBIN.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro": "LT.NS",
    "Axis Bank": "AXISBANK.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Maruti Suzuki": "MARUTI.NS",
    "Sun Pharma": "SUNPHARMA.NS",
    "Titan": "TITAN.NS",
    "Wipro": "WIPRO.NS",
    "UltraTech Cement": "ULTRACEMCO.NS",
    "Nestle India": "NESTLEIND.NS",
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Bank Nifty": "^NSEBANK",
}


@st.cache_data(ttl=300)
def get_ticker_info(symbol: str):
    if not HAS_MARKET_LIBS:
        return {}
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return info if info else {}
    except Exception:
        return {}


@st.cache_data(ttl=300)
def get_history(symbol: str, period: str = "1y", interval: str = "1d"):
    if not HAS_MARKET_LIBS:
        return pd.DataFrame()
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        return hist
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_financials(symbol: str):
    if not HAS_MARKET_LIBS:
        return {}
    try:
        ticker = yf.Ticker(symbol)
        return {
            "income": ticker.financials,
            "balance": ticker.balance_sheet,
            "cashflow": ticker.cashflow,
            "quarterly_income": ticker.quarterly_financials,
            "quarterly_balance": ticker.quarterly_balance_sheet,
            "quarterly_cashflow": ticker.quarterly_cashflow,
        }
    except Exception:
        return {}


@st.cache_data(ttl=300)
def get_news(symbol: str):
    if not HAS_MARKET_LIBS:
        return []
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        return news if news else []
    except Exception:
        return []


def format_number(num):
    if num is None or (isinstance(num, float) and pd.isna(num)):
        return "N/A"
    try:
        num = float(num)
        if abs(num) >= 1e7:
            return f"₹{num/1e7:.2f} Cr"
        elif abs(num) >= 1e5:
            return f"₹{num/1e5:.2f} L"
        else:
            return f"₹{num:,.2f}"
    except Exception:
        return str(num)


def format_pct(val, already_percent: bool = False):
    """Format ratio/percent fields.
    - already_percent=True  → value is already in percent points (e.g. div yield 0.45 → 0.45%)
    - already_percent=False → value is a fraction (e.g. ROE 0.15 → 15.00%)
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        v = float(val)
        if already_percent:
            return f"{v:.2f}%"
        # fraction → percent
        if abs(v) <= 1:
            return f"{v * 100:.2f}%"
        return f"{v:.2f}%"
    except Exception:
        return "—"


def _fmt_price(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        return f"₹{float(val):,.2f}"
    except Exception:
        return "—"


def create_candlestick_chart(hist: pd.DataFrame, symbol: str):
    if hist.empty or not HAS_MARKET_LIBS:
        return None
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.7, 0.3], subplot_titles=(f"{symbol} Price", "Volume")
    )
    fig.add_trace(
        go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"], name="Price",
            increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
        ), row=1, col=1
    )
    colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(hist["Close"], hist["Open"])]
    fig.add_trace(
        go.Bar(x=hist.index, y=hist["Volume"], name="Volume", marker_color=colors, opacity=0.7),
        row=2, col=1
    )
    fig.update_layout(
        title=None, xaxis_rangeslider_visible=False, height=600,
        template="plotly_dark" if get_theme() == "dark" else "plotly_white",
        showlegend=False, margin=dict(l=40, r=40, t=40, b=40)
    )
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


def create_line_chart(hist: pd.DataFrame, symbol: str):
    if hist.empty or not HAS_MARKET_LIBS:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"], mode="lines", name="Close",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy", fillcolor="rgba(31, 119, 180, 0.1)"
    ))
    fig.update_layout(
        title=f"{symbol} Closing Price", height=400,
        template="plotly_dark" if get_theme() == "dark" else "plotly_white",
        xaxis_title="Date", yaxis_title="Price (₹)",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig


def render_indian_stock_dashboard():
    """Full Yahoo Finance style Indian stock dashboard."""
    if not HAS_MARKET_LIBS:
        st.error("Please install `yfinance` and `plotly` to use the Indian Stock Dashboard:\n\n`pip install yfinance plotly`")
        return

    st.markdown("## 🇮🇳 Indian Stock Market Dashboard")
    st.caption("Yahoo Finance style data for NSE & BSE stocks  •  Data via yfinance")

    # ---- Controls ----
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        selection_mode = st.radio("Select", ["Popular Stocks", "Search by Symbol"], horizontal=True, key="ind_sel_mode")
    with c2:
        if selection_mode == "Popular Stocks":
            selected_name = st.selectbox("Stock / Index", list(POPULAR_STOCKS.keys()), key="ind_popular")
            symbol = POPULAR_STOCKS[selected_name]
        else:
            user_input = st.text_input("Symbol (e.g. RELIANCE.NS)", value="RELIANCE.NS", key="ind_symbol").strip().upper()
            if user_input and not user_input.startswith("^") and "." not in user_input:
                user_input = user_input + ".NS"
            symbol = user_input
    with c3:
        period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=5, key="ind_period")

    interval_map = {
        "1d": "5m", "5d": "15m", "1mo": "1h", "3mo": "1d", "6mo": "1d",
        "1y": "1d", "2y": "1d", "5y": "1wk", "max": "1mo"
    }
    interval = interval_map.get(period, "1d")

    if not symbol:
        st.warning("Enter a valid symbol.")
        return

    with st.spinner(f"Loading {symbol}..."):
        info = get_ticker_info(symbol)
        hist = get_history(symbol, period=period, interval=interval)

    if not info and hist.empty:
        st.error(f"Could not fetch data for **{symbol}**. Try adding `.NS` (NSE) or `.BO` (BSE).")
        return

    # ---- Header ----
    name = info.get("shortName") or info.get("longName") or symbol
    sector = info.get("sector") or info.get("sectorDisp") or "—"
    industry = info.get("industry") or info.get("industryDisp") or "—"

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    prev = info.get("previousClose")
    change = pct = None
    if price is not None and prev:
        change = price - prev
        pct = (change / prev) * 100

    # Big price header (no truncation)
    change_html = ""
    if change is not None and pct is not None:
        color = "#26a69a" if change >= 0 else "#ef5350"
        arrow = "▲" if change >= 0 else "▼"
        change_html = f'<span style="color:{color};font-size:1.1rem;margin-left:12px;">{arrow} {change:+.2f} ({pct:+.2f}%)</span>'

    vol_str = f"{hist['Volume'].iloc[-1]:,.0f}" if not hist.empty else "—"
    price_str = f"₹{price:,.2f}" if price is not None else "—"

    st.markdown(f"### {name}")
    st.caption(f"{symbol}  •  {sector}  •  {industry}")
    st.markdown(
        f"""
        <div style="display:flex;align-items:baseline;gap:24px;flex-wrap:wrap;margin:8px 0 16px 0;">
          <div style="font-size:2.2rem;font-weight:700;">{price_str}{change_html}</div>
          <div style="font-size:0.95rem;opacity:0.8;">Volume: <b>{vol_str}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Key metrics as HTML cards (never truncate) ----
    def _card(label: str, value: str) -> str:
        return f"""
        <div style="
            background:rgba(128,128,128,0.12);
            border:1px solid rgba(128,128,128,0.25);
            border-radius:10px;
            padding:12px 10px;
            text-align:center;
            min-height:72px;
        ">
            <div style="font-size:0.75rem;opacity:0.7;margin-bottom:4px;">{label}</div>
            <div style="font-size:1.05rem;font-weight:600;word-break:break-all;">{value}</div>
        </div>
        """

    pe = info.get("trailingPE")
    mcap = info.get("marketCap")
    beta = info.get("beta")
    row1 = [
        ("Open", _fmt_price(info.get("open") or info.get("regularMarketOpen"))),
        ("Day High", _fmt_price(info.get("dayHigh") or info.get("regularMarketDayHigh"))),
        ("Day Low", _fmt_price(info.get("dayLow") or info.get("regularMarketDayLow"))),
        ("52W High", _fmt_price(info.get("fiftyTwoWeekHigh"))),
        ("52W Low", _fmt_price(info.get("fiftyTwoWeekLow"))),
        ("P/E (TTM)", f"{pe:.2f}" if pe else "—"),
    ]
    row2 = [
        ("Market Cap", format_number(mcap) if mcap else "—"),
        ("Div Yield", format_pct(info.get("dividendYield"), already_percent=True)),
        ("Beta", f"{beta:.2f}" if beta else "—"),
        ("EPS (TTM)", _fmt_price(info.get("trailingEps"))),
        ("Book Value", _fmt_price(info.get("bookValue"))),
        ("ROE", format_pct(info.get("returnOnEquity"))),
    ]

    cols = st.columns(6)
    for col, (lab, val) in zip(cols, row1):
        col.markdown(_card(lab, val), unsafe_allow_html=True)

    st.markdown("")  # small gap
    cols = st.columns(6)
    for col, (lab, val) in zip(cols, row2):
        col.markdown(_card(lab, val), unsafe_allow_html=True)

    st.markdown("---")

    # ---- Tabs ----
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Chart", "📋 Summary", "💰 Financials", "📰 News", "📈 Statistics", "ℹ️ About"
    ])

    with tab1:
        st.subheader("Price Chart")
        chart_type = st.radio("Chart Type", ["Candlestick", "Line"], horizontal=True, key="ind_chart_type")
        if not hist.empty:
            fig = create_candlestick_chart(hist, symbol) if chart_type == "Candlestick" else create_line_chart(hist, symbol)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            with st.expander("Recent OHLC Data"):
                display_hist = hist.tail(30).copy()
                display_hist.index = display_hist.index.strftime("%Y-%m-%d %H:%M")
                st.dataframe(
                    display_hist[["Open", "High", "Low", "Close", "Volume"]].style.format({
                        "Open": "₹{:.2f}", "High": "₹{:.2f}", "Low": "₹{:.2f}",
                        "Close": "₹{:.2f}", "Volume": "{:,.0f}"
                    }),
                    use_container_width=True
                )
        else:
            st.warning("No historical data for this period.")

    with tab2:
        st.subheader("Company Summary")
        summary = info.get("longBusinessSummary")
        if summary:
            st.write(summary)
        else:
            st.info("Business summary not available.")
        st.markdown("### Key Details")
        details = {
            "Symbol": symbol,
            "Exchange": info.get("exchange") or info.get("fullExchangeName") or "—",
            "Currency": info.get("currency") or "INR",
            "Country": info.get("country") or "India",
            "Website": info.get("website") or "—",
            "Employees": f"{info.get('fullTimeEmployees'):,}" if info.get("fullTimeEmployees") else "—",
            "Industry": industry,
            "Sector": sector,
        }
        for k, v in details.items():
            st.write(f"**{k}:** {v}")

    with tab3:
        st.subheader("Financial Statements")
        fin = get_financials(symbol)
        if not any(v is not None and not (isinstance(v, pd.DataFrame) and v.empty) for v in fin.values()):
            st.info("Financial statements not available (common for indices).")
        else:
            fin_type = st.radio("Statement", ["Income Statement", "Balance Sheet", "Cash Flow"], horizontal=True, key="ind_fin_type")
            period_type = st.radio("Period", ["Annual", "Quarterly"], horizontal=True, key="ind_fin_period")
            key_map = {
                ("Income Statement", "Annual"): "income",
                ("Income Statement", "Quarterly"): "quarterly_income",
                ("Balance Sheet", "Annual"): "balance",
                ("Balance Sheet", "Quarterly"): "quarterly_balance",
                ("Cash Flow", "Annual"): "cashflow",
                ("Cash Flow", "Quarterly"): "quarterly_cashflow",
            }
            df = fin.get(key_map[(fin_type, period_type)])
            if df is not None and not df.empty:
                display_df = df.copy()
                display_df.columns = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in display_df.columns]
                st.dataframe(display_df.style.format("{:,.0f}"), use_container_width=True, height=500)
            else:
                st.info(f"No {period_type.lower()} {fin_type.lower()} data available.")

    with tab4:
        st.subheader("Latest News")
        news_list = get_news(symbol)
        if news_list:
            for item in news_list[:12]:
                content = item.get("content") or item
                title = content.get("title") or item.get("title") or "No title"
                publisher = (
                    content.get("provider", {}).get("displayName")
                    if isinstance(content.get("provider"), dict)
                    else (item.get("publisher") or "Unknown")
                )
                link = (
                    content.get("canonicalUrl", {}).get("url")
                    if isinstance(content.get("canonicalUrl"), dict)
                    else (item.get("link") or "#")
                )
                pub_date = content.get("pubDate") or item.get("providerPublishTime")
                if pub_date:
                    try:
                        if isinstance(pub_date, (int, float)):
                            pub_date = datetime.fromtimestamp(pub_date).strftime("%Y-%m-%d %H:%M")
                        else:
                            pub_date = str(pub_date)[:16]
                    except Exception:
                        pub_date = ""
                st.markdown(f"**[{title}]({link})**")
                st.caption(f"{publisher}  •  {pub_date}")
                st.markdown("---")
        else:
            st.info("No recent news found.")

    with tab5:
        st.subheader("Valuation & Statistics")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Valuation Measures")
            val_data = {
                "Market Cap": format_number(info.get("marketCap")),
                "Enterprise Value": format_number(info.get("enterpriseValue")),
                "Trailing P/E": f"{info.get('trailingPE'):.2f}" if info.get("trailingPE") else "N/A",
                "Forward P/E": f"{info.get('forwardPE'):.2f}" if info.get("forwardPE") else "N/A",
                "PEG Ratio": f"{info.get('pegRatio'):.2f}" if info.get("pegRatio") else "N/A",
                "Price/Sales (TTM)": f"{info.get('priceToSalesTrailing12Months'):.2f}" if info.get("priceToSalesTrailing12Months") else "N/A",
                "Price/Book": f"{info.get('priceToBook'):.2f}" if info.get("priceToBook") else "N/A",
                "EV/Revenue": f"{info.get('enterpriseToRevenue'):.2f}" if info.get("enterpriseToRevenue") else "N/A",
                "EV/EBITDA": f"{info.get('enterpriseToEbitda'):.2f}" if info.get("enterpriseToEbitda") else "N/A",
            }
            for k, v in val_data.items():
                st.write(f"**{k}:** {v}")
        with col_b:
            st.markdown("#### Financial Highlights")
            fin_data = {
                "Profit Margin": format_pct(info.get("profitMargins")),
                "Operating Margin": format_pct(info.get("operatingMargins")),
                "Return on Assets": format_pct(info.get("returnOnAssets")),
                "Return on Equity": format_pct(info.get("returnOnEquity")),
                "Revenue (TTM)": format_number(info.get("totalRevenue")),
                "Revenue Per Share": f"₹{info.get('revenuePerShare'):.2f}" if info.get("revenuePerShare") else "N/A",
                "Gross Profit": format_number(info.get("grossProfits")),
                "EBITDA": format_number(info.get("ebitda")),
                "Net Income": format_number(info.get("netIncomeToCommon")),
                "Diluted EPS": f"₹{info.get('trailingEps'):.2f}" if info.get("trailingEps") else "N/A",
            }
            for k, v in fin_data.items():
                st.write(f"**{k}:** {v}")

        st.markdown("---")
        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown("#### Trading Information")
            trade_data = {
                "Beta (5Y)": f"{info.get('beta'):.2f}" if info.get("beta") else "N/A",
                "52-Week Change": format_pct(info.get("52WeekChange")),
                "Avg Volume (10d)": f"{info.get('averageVolume10days'):,.0f}" if info.get("averageVolume10days") else "N/A",
                "Avg Volume (3m)": f"{info.get('averageVolume'):,.0f}" if info.get("averageVolume") else "N/A",
                "Shares Outstanding": f"{info.get('sharesOutstanding'):,.0f}" if info.get("sharesOutstanding") else "N/A",
                "Float Shares": f"{info.get('floatShares'):,.0f}" if info.get("floatShares") else "N/A",
                "% Held by Insiders": format_pct(info.get("heldPercentInsiders")),
                "% Held by Institutions": format_pct(info.get("heldPercentInstitutions")),
            }
            for k, v in trade_data.items():
                st.write(f"**{k}:** {v}")
        with col_d:
            st.markdown("#### Dividends & Splits")
            div_data = {
                "Forward Dividend & Yield": (
                    f"₹{info.get('dividendRate'):.2f} ({format_pct(info.get('dividendYield'), already_percent=True)})"
                    if info.get("dividendRate") else "—"
                ),
                "Trailing Annual Dividend": f"₹{info.get('trailingAnnualDividendRate'):.2f}" if info.get("trailingAnnualDividendRate") else "—",
                "Ex-Dividend Date": str(info.get("exDividendDate"))[:10] if info.get("exDividendDate") else "—",
                "Payout Ratio": format_pct(info.get("payoutRatio")),
                "5 Year Avg Dividend Yield": format_pct(info.get("fiveYearAvgDividendYield"), already_percent=True),
                "Last Split Factor": info.get("lastSplitFactor") or "N/A",
                "Last Split Date": str(info.get("lastSplitDate"))[:10] if info.get("lastSplitDate") else "N/A",
            }
            for k, v in div_data.items():
                st.write(f"**{k}:** {v}")

    with tab6:
        st.subheader("About Indian Stock Dashboard")
        st.markdown("""
        Full **Yahoo Finance style** dashboard for **Indian stocks** (NSE & BSE).

        **Features:** Quotes, interactive charts, company profile, financial statements,
        news, valuation ratios, dividends & more.

        **Symbols:**
        - NSE → `RELIANCE.NS`, `TCS.NS`
        - BSE → `RELIANCE.BO`
        - Indices → `^NSEI` (Nifty 50), `^BSESN` (Sensex), `^NSEBANK`

        Data source: Yahoo Finance via `yfinance`. Not financial advice.
        """)
        st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST")


# ---------------------------------------------------------------------------
# Sidebar: how do you want to get a script?
# ---------------------------------------------------------------------------
st.sidebar.title("🌲 PineSprout Studio")
st.sidebar.caption("Generate, analyze, and document TradingView Pine Script.")
st.sidebar.caption("Market tools by **Khushal Jain**.")

st.sidebar.markdown("**Theme**")
theme_toggle(location=st.sidebar, key="pf_theme_toggle_sidebar")
inject_theme_css()
st.sidebar.divider()

mode = st.sidebar.radio(
    "How would you like to start?",
    [
        "✨ Describe my strategy (AI)",
        "🧪 Template Builder (huge combo space)",
        "📋 Use a template",
        "📄 Paste / upload a script",
        "📈 Indian Stock Dashboard",   # ← NEW
        "📊 Live Market Heatmap",
        "ℹ️ About",
    ],
)

st.sidebar.divider()

if mode == "✨ Describe my strategy (AI)":
    st.sidebar.subheader("Anthropic API Key")
    api_key = st.sidebar.text_input(
        "ANTHROPIC_API_KEY",
        type="password",
        help="Required only for AI generation. Get one at console.anthropic.com. "
        "Never stored -- only held in this browser session.",
    )
    st.sidebar.caption(
        "Prefer not to paste a key here? Set the `ANTHROPIC_API_KEY` environment "
        "variable on the machine/host running this app instead."
    )
else:
    api_key = None

st.sidebar.divider()
st.sidebar.caption(
    "PineSprout only ever operates on the script text you provide — "
    "it never fetches or bypasses protected/invite-only TradingView scripts."
)

# ---------------------------------------------------------------------------
# Main area: acquisition mode
# ---------------------------------------------------------------------------
st.title("PineSprout Studio")
st.caption(
    "💡 Don't see the sidebar (mode selector, theme toggle)? "
    "Click the **»** arrow at the top-left of the page to expand it — "
    "your browser remembers this setting across visits."
)
if HAS_PINESPROUT:
    render_ticker_banner(DEFAULT_SYMBOLS, theme=get_theme())

# ========== NEW: Indian Stock Dashboard mode ==========
if mode == "📈 Indian Stock Dashboard":
    render_indian_stock_dashboard()
    st.stop()

if mode == "✨ Describe my strategy (AI)":
    if not HAS_PINESPROUT:
        st.error("PineSprout package not installed. AI generation is unavailable.")
        st.stop()
    st.subheader("Describe your strategy in plain English")
    st.caption(
        "Example: *\"A daily pivot-point strategy that goes long when price reclaims "
        "the daily PP with RSI above 50, with a stop below S1\"*"
    )

    with st.expander("🔑 Anthropic API Key (required for this mode)", expanded=not api_key):
        main_api_key = st.text_input(
            "ANTHROPIC_API_KEY",
            value=api_key or "",
            type="password",
            help="Get one at console.anthropic.com. Never stored -- only held in this "
                 "browser session. You can also set the ANTHROPIC_API_KEY environment "
                 "variable on the machine/host running this app instead of pasting it here.",
            key="main_panel_api_key",
        )
        st.caption("This is the same field as the sidebar's — either one works.")
    api_key = main_api_key or api_key

    col1, col2 = st.columns([3, 1])
    with col1:
        prompt = st.text_area(
            "Strategy description",
            height=140,
            placeholder="Describe indicators, entry/exit rules, risk management, timeframe, etc.",
            label_visibility="collapsed",
        )
    with col2:
        script_type = st.selectbox("Script type", ["indicator", "strategy", "library"])
        pine_version = st.selectbox("Pine version", [6, 5], index=0)

    if st.button("🚀 Generate Pine Script", type="primary", width="stretch"):
        if not prompt.strip():
            st.warning("Please describe your strategy first.")
        else:
            with st.spinner("Asking Claude to write your Pine Script..."):
                try:
                    request = GenerationRequest(
                        prompt=prompt, script_type=script_type, pine_version=pine_version
                    )
                    result = generate_pine_script(request, api_key=api_key or None)
                    _set_source(result.source, f"{script_type}_generated.pine")
                    if result.lint_issues:
                        st.warning(
                            f"Generated, but {len(result.lint_issues)} lint issue(s) were "
                            "found — see the Lint tab below."
                        )
                    else:
                        st.success("Generated cleanly — no lint issues found!")
                except GenerationError as exc:
                    st.error(str(exc))

elif mode == "🧪 Template Builder (huge combo space)":
    if not HAS_PINESPROUT:
        st.error("PineSprout package not installed. Template Builder is unavailable.")
        st.stop()
    st.subheader("Build a custom indicator or strategy")
    counts = estimate_combination_count()
    st.caption(
        f"Mix and match **{counts['indicators']} indicators** (trend, momentum, volatility, "
        f"volume) across **{counts['structural_patterns']} signal patterns**, indicator or "
        f"strategy output, and 3 risk-management styles — that's "
        f"**{counts['structural_total_with_type_and_risk']:,} structural combinations**, and "
        "every length, threshold, and stop-loss/take-profit % is freely adjustable on top of "
        "that, so the realistic number of genuinely distinct scripts you can generate runs into "
        "the thousands. Have fun exploring! *Builder by Khushal Jain.*"
    )

    col1, col2 = st.columns(2)
    with col1:
        builder_title = st.text_input("Title", value="My Custom Script", key="builder_title")
        builder_script_type = st.selectbox("Output type", ["indicator", "strategy"], key="builder_script_type")
    with col2:
        pattern_label = st.selectbox(
            "Signal pattern", list(SIGNAL_PATTERN_LABELS.values()), key="builder_pattern"
        )
        pattern = next(p for p, lbl in SIGNAL_PATTERN_LABELS.items() if lbl == pattern_label)

    candidates = indicators_for_pattern(pattern)
    candidate_labels = {c.label: c.id for c in candidates}

    col3, col4 = st.columns(2)
    with col3:
        primary_label = st.selectbox("Indicator", list(candidate_labels.keys()), key="builder_primary")
        primary_id = candidate_labels[primary_label]
        primary_spec = INDICATORS[primary_id]
        length = st.number_input("Length", min_value=1, max_value=500, value=primary_spec.default_length,
                                  key="builder_length")
    with col4:
        secondary_id = None
        length2 = 21
        if pattern == SignalPattern.MA_CROSSOVER:
            secondary_label = st.selectbox("Second indicator (slow)", list(candidate_labels.keys()),
                                            index=min(1, len(candidate_labels) - 1), key="builder_secondary")
            secondary_id = candidate_labels[secondary_label]
            length2 = st.number_input("Second length", min_value=1, max_value=500, value=21, key="builder_length2")

        overbought = oversold = None
        if pattern == SignalPattern.OSCILLATOR_THRESHOLD:
            overbought = st.number_input("Overbought level", value=primary_spec.default_overbought,
                                          key="builder_ob")
            oversold = st.number_input("Oversold level", value=primary_spec.default_oversold,
                                        key="builder_os")

        band_mult = 2.0
        if pattern == SignalPattern.BAND_BREAKOUT:
            band_mult = st.number_input("Band multiplier", min_value=0.5, max_value=5.0, value=2.0, step=0.1,
                                         key="builder_mult")

    overlay_default = primary_spec.is_overlay_friendly
    overlay = st.checkbox("Overlay on price chart", value=overlay_default, key="builder_overlay")

    risk = RiskPreset.NONE
    stop_loss_pct, take_profit_pct, atr_stop_mult, atr_tp_mult = 2.0, 4.0, 2.0, 3.0
    if builder_script_type == "strategy":
        risk_label = st.selectbox("Risk management", list(RISK_PRESET_LABELS.values()), key="builder_risk")
        risk = next(r for r, lbl in RISK_PRESET_LABELS.items() if lbl == risk_label)
        if risk == RiskPreset.FIXED_PERCENT:
            rc1, rc2 = st.columns(2)
            with rc1:
                stop_loss_pct = st.number_input("Stop-loss %", min_value=0.1, max_value=50.0, value=2.0,
                                                 key="builder_sl")
            with rc2:
                take_profit_pct = st.number_input("Take-profit %", min_value=0.1, max_value=100.0, value=4.0,
                                                   key="builder_tp")
        elif risk == RiskPreset.ATR_BASED:
            rc1, rc2 = st.columns(2)
            with rc1:
                atr_stop_mult = st.number_input("ATR stop multiple", min_value=0.5, max_value=10.0, value=2.0,
                                                 key="builder_atr_sl")
            with rc2:
                atr_tp_mult = st.number_input("ATR take-profit multiple", min_value=0.5, max_value=10.0, value=3.0,
                                               key="builder_atr_tp")

    if st.button("🧪 Build Pine Script", type="primary", width="stretch"):
        spec = BuilderSpec(
            title=builder_title, script_type=builder_script_type, pattern=pattern,
            primary_indicator=primary_id, secondary_indicator=secondary_id,
            length=int(length), length2=int(length2),
            overbought=overbought, oversold=oversold, band_mult=band_mult,
            risk=risk, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
            atr_stop_mult=atr_stop_mult, atr_tp_mult=atr_tp_mult, overlay=overlay,
        )
        source = build_from_spec(spec)
        safe_name = "".join(c if c.isalnum() else "_" for c in builder_title).strip("_") or "script"
        _set_source(source, f"{safe_name}.pine")
        st.success("Built! Scroll down to lint, format, analyze, or download it.")

elif mode == "📋 Use a template":
    if not HAS_PINESPROUT:
        st.error("PineSprout package not installed. Templates are unavailable.")
        st.stop()
    st.subheader("Pick a ready-made template")
    kind_label = st.selectbox("Template", list(TEMPLATE_LABELS.values()))
    kind = next(k for k, v in TEMPLATE_LABELS.items() if v == kind_label)

    col1, col2, col3 = st.columns(3)
    with col1:
        title = st.text_input("Title", value="My Script")
    with col2:
        overlay = st.checkbox("Overlay on price chart", value=True)
    with col3:
        pine_version = st.selectbox("Pine version", [6, 5], index=0, key="tpl_version")

    if kind == TemplateKind.PIVOT_CONFLUENCE:
        st.info(
            "This template plots **Daily / Weekly / Monthly classic pivot points** "
            "(PP, R1–R3, S1–S3) via `request.security` with `lookahead` explicitly off "
            "(repaint-safe), plus a **confluence detector**: when levels from different "
            "timeframes land within your chosen tolerance of each other, it draws a "
            "highlighted zone and labels which levels are stacking there."
        )

    if st.button("🧩 Generate from template", type="primary", width="stretch"):
        spec = TemplateSpec(kind=kind, title=title, overlay=overlay, pine_version=pine_version)
        source = generate_from_template(spec)
        safe_name = "".join(c if c.isalnum() else "_" for c in title).strip("_") or "script"
        _set_source(source, f"{safe_name}.pine")
        st.success("Template generated!")

elif mode == "📄 Paste / upload a script":
    st.subheader("Bring your own script")
    tab_paste, tab_upload = st.tabs(["✍️ Paste code", "📁 Upload .pine file"])
    with tab_paste:
        pasted = st.text_area("Pine Script source", height=300, key="pasted_source")
        if st.button("Load pasted script", width="stretch"):
            if pasted.strip():
                _set_source(pasted, "pasted_script.pine")
                st.success("Loaded.")
            else:
                st.warning("Paste some code first.")
    with tab_upload:
        uploaded = st.file_uploader("Choose a .pine file", type=["pine", "pinescript", "txt"])
        if uploaded is not None:
            content = uploaded.read().decode("utf-8", errors="replace")
            _set_source(content, uploaded.name)
            st.success(f"Loaded {uploaded.name}")

elif mode == "📊 Live Market Heatmap":
    tab_nse, tab_tv = st.tabs(["🇮🇳 NSE Index Watch", "🌍 TradingView Heatmap (global)"])
    with tab_nse:
        render_index_watch(theme=get_theme(), key_prefix="pf_index_watch")
    with tab_tv:
        render_heatmap_tab(theme=get_theme(), key_prefix="pf_heatmap")
        st.caption("Heatmap powered by TradingView's free public widget.")
    st.divider()
    st.caption("Pick a script mode in the sidebar to use the Pine Script toolchain.")
    st.stop()

else:  # ℹ️ About
    render_about_section()
    st.stop()

# ---------------------------------------------------------------------------
# Workbench: once we have source, show the full PineSprout toolchain
# ---------------------------------------------------------------------------
if not HAS_PINESPROUT:
    st.info("PineSprout package not installed — script workbench disabled. Use Indian Stock Dashboard mode.")
    st.stop()

source = st.session_state.pine_source

if not source.strip():
    st.info("👆 Generate, pick a template, or load a script above to start working with it.")
    st.stop()

st.divider()
st.subheader(f"Working with: `{st.session_state.pine_filename}`")

(
    tab_code,
    tab_lint,
    tab_format,
    tab_analyze,
    tab_optimize,
    tab_explain,
    tab_upgrade,
    tab_docs,
) = st.tabs(
    ["Code", "🔍 Lint", "🧹 Format", "📊 Analyze", "⚡ Optimize", "💬 Explain", "⬆️ Upgrade", "📄 Docs"]
)

with tab_code:
    st.code(source, language="javascript", line_numbers=True)
    st.download_button(
        "⬇️ Download .pine file",
        data=source,
        file_name=st.session_state.pine_filename,
        mime="text/plain",
        width="stretch",
    )

with tab_lint:
    result = lint_source(source, file=st.session_state.pine_filename)
    c1, c2, c3 = st.columns(3)
    c1.metric("Errors", result.error_count)
    c2.metric("Warnings", result.warning_count)
    c3.metric("Info", result.info_count)

    if not result.issues:
        st.success("No issues found — clean script! ✅")
    else:
        for issue in result.issues:
            icon = SEVERITY_ICON[issue.severity]
            with st.expander(f"{icon} Line {issue.line} — {issue.category.value} — {issue.message[:70]}"):
                st.write(f"**{issue.message}**")
                if issue.suggestion:
                    st.caption(f"💡 {issue.suggestion}")
                if 1 <= issue.line <= len(source.splitlines()):
                    st.code(source.splitlines()[issue.line - 1], language="javascript")

with tab_format:
    formatted = format_source(source, FormatOptions())
    if formatted == source:
        st.success("Already formatted — nothing to change. ✅")
        st.code(source, language="javascript")
    else:
        st.info("Formatting would make the following changes:")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Original")
            st.code(source, language="javascript")
        with col2:
            st.caption("Formatted")
            st.code(formatted, language="javascript")
        if st.button("✅ Apply formatting to working copy"):
            _set_source(formatted, st.session_state.pine_filename)
            st.rerun()
    st.download_button(
        "⬇️ Download formatted .pine",
        data=formatted,
        file_name=f"formatted_{st.session_state.pine_filename}",
        mime="text/plain",
    )

with tab_analyze:
    report = analyze(source, file=st.session_state.pine_filename)
    kind_str = (
        "Strategy" if report.script_kind.is_strategy
        else "Library" if report.script_kind.is_library
        else "Indicator"
    )
    st.markdown(f"**{report.script_kind.title or st.session_state.pine_filename}** "
                f"· Pine v{report.pine_version} · {kind_str}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Complexity score", report.complexity_score)
    c2.metric("Variables", report.variable_count)
    c3.metric("Functions", report.function_count)
    c4.metric("Plots", report.plot_count)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Inputs", report.input_count)
    c6.metric("Alerts", report.alert_count)
    c7.metric("Max nesting depth", report.max_nesting_depth)
    c8.metric("Strategy entries", report.strategy_entry_count)

    if report.ta_function_calls:
        st.caption("Technical analysis functions used:")
        st.json(report.ta_function_calls)

    if report.warnings:
        for w in report.warnings:
            st.warning(w)

with tab_optimize:
    opt = optimize_source(source, file=st.session_state.pine_filename)
    if not opt.suggestions:
        st.success("No optimization suggestions — looks clean! ✅")
    else:
        for s in opt.suggestions:
            with st.expander(f"Line {s.line} — {s.title}"):
                st.write(s.detail)
                if s.before:
                    st.caption(f"Before: `{s.before}`")
                    st.caption(f"After: `{s.after}`")

with tab_explain:
    st.info(explain_script_summary(source))
    explanations = explain_source(source)
    st.caption(f"{len(explanations)} annotated lines")
    for e in explanations:
        st.markdown(f"**L{e.line}** `{e.code.strip()[:60]}` — {e.explanation}")

with tab_upgrade:
    detected = detect_version(source)
    st.write(f"Detected version: **{detected or 'unknown (assumed ≤ v4)'}**")
    target = st.selectbox("Upgrade to", [6, 5], index=0)
    if st.button("⬆️ Run upgrade"):
        result = upgrade_source(source, target_version=target, file=st.session_state.pine_filename)
        st.write(f"Final version: **v{result.final_version}**")
        if result.applied_migrations:
            for m in result.applied_migrations:
                st.write(f"- {m.description} ({m.occurrences}x)")
        else:
            st.caption("No automatic migrations were necessary.")
        if result.manual_review_needed:
            for note in result.manual_review_needed:
                st.warning(note)
        st.code(result.upgraded_source, language="javascript")
        if st.button("✅ Apply upgrade to working copy"):
            _set_source(result.upgraded_source, st.session_state.pine_filename)
            st.rerun()

with tab_docs:
    doc_kind = st.radio("Generate", ["README.md", "Docs (Markdown)", "Docs (HTML)", "Full Report"], horizontal=True)
    if doc_kind == "README.md":
        content = generate_readme(source, source_filename=st.session_state.pine_filename)
        st.markdown(content)
        st.download_button("⬇️ Download README.md", content, file_name="README.md")
    elif doc_kind == "Docs (Markdown)":
        content = generate_docs(source, fmt=DocFormat.MARKDOWN, source_filename=st.session_state.pine_filename)
        st.markdown(content)
        st.download_button("⬇️ Download docs.md", content, file_name="docs.md")
    elif doc_kind == "Docs (HTML)":
        content = generate_docs(source, fmt=DocFormat.HTML, source_filename=st.session_state.pine_filename)
        st.download_button("⬇️ Download docs.html", content, file_name="docs.html")
        if hasattr(st, "iframe"):
            st.iframe(content, height=600)
        else:
            st.components.v1.html(content, height=600, scrolling=True)
    else:
        content = generate_report(source, file=st.session_state.pine_filename)
        st.markdown(content)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M")
        st.download_button("⬇️ Download report.md", content, file_name=f"report_{ts}.md")

st.divider()
st.caption("Built with PineSprout — the deterministic core (parse/format/lint/analyze) "
           "runs fully offline; only the '✨ Describe my strategy' mode calls the Anthropic API.")
st.caption("Live ticker & heatmap tools by **Khushal Jain**. Indian Stock Dashboard integrated.")
