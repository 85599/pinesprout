"""
streamlit_ticker.py
Live scrolling ticker banner for Streamlit -- stock-exchange style.

This reuses the same quote-fetching approach as your original ticker.py
(yfinance `fast_info`, background refresh thread), but renders the
result as a CSS-animated horizontal marquee instead of a `rich` terminal
Live display, since terminal ANSI rendering doesn't work inside a
Streamlit page.

Requires your existing `markets.py` (same one ticker.py imports --
`COMMODITIES` dict + `quiet()` context manager). If you don't have one
yet, a minimal fallback is used automatically so this still runs.

Usage in your main app.py:

    from streamlit_ticker import render_ticker_banner, DEFAULT_SYMBOLS

    render_ticker_banner(DEFAULT_SYMBOLS)   # call near the top of the page,
                                             # e.g. right under st.title(...)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import streamlit as st
import yfinance as yf

# See the matching comment in index_watch.py -- silences yfinance's
# per-attempt "possibly delisted" console spam for expected failures.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

try:
    import markets
    from markets import COMMODITIES
except ImportError:  # pragma: no cover - fallback if markets.py isn't present yet
    from collections.abc import Iterator
    from contextlib import contextmanager

    COMMODITIES = {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE OIL": "CL=F"}

    class _MarketsFallback:
        @staticmethod
        @contextmanager
        def quiet() -> Iterator[None]:
            yield

    markets = _MarketsFallback()

REFRESH_SECONDS = 20
SEPARATOR = "     |     "


@dataclass
class Quote:
    label: str
    price: float | None = None
    change_pct: float | None = None
    ok: bool = False


DEFAULT_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "USD/INR": "INR=X",
}


def _fetch_quotes(symbol_map: dict[str, str]) -> list[Quote]:
    """Fetch one quote per symbol. Returns a list of Quote objects so the
    caller can render however it likes (HTML marquee here, but reusable
    for anything else)."""
    quotes: list[Quote] = []
    for label, symbol in symbol_map.items():
        entry = Quote(label=label)
        try:
            with markets.quiet():
                t = yf.Ticker(symbol)
                fast = t.fast_info
                price = fast.get("lastPrice") or fast.get("last_price")
                prev_close = fast.get("previousClose") or fast.get("previous_close")
            if price is not None:
                entry.price = float(price)
                entry.ok = True
                if prev_close:
                    entry.change_pct = (float(price) - float(prev_close)) / float(prev_close) * 100
        except Exception:
            pass
        quotes.append(entry)
    return quotes


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def _cached_quotes(symbol_map_items: tuple[tuple[str, str], ...], include_commodities: bool) -> list[Quote]:
    """Cached wrapper -- Streamlit reruns constantly (every widget
    interaction), so we cache the actual network calls for
    REFRESH_SECONDS and let the CSS animation handle the visual motion
    independent of Python reruns."""
    symbol_map = dict(symbol_map_items)
    if include_commodities:
        symbol_map.update(COMMODITIES)
    return _fetch_quotes(symbol_map)


def _quotes_to_html(quotes: list[Quote]) -> str:
    spans = []
    for q in quotes:
        if not q.ok or q.price is None:
            spans.append(f'<span class="kj-tick-label">{q.label}</span> <span class="kj-tick-na">N/A</span>')
        else:
            price_str = f"{q.price:,.2f}"
            if q.change_pct is not None:
                arrow = "▲" if q.change_pct >= 0 else "▼"
                cls = "kj-tick-up" if q.change_pct >= 0 else "kj-tick-down"
                spans.append(
                    f'<span class="kj-tick-label">{q.label}</span> '
                    f'<span class="kj-tick-price">{price_str}</span> '
                    f'<span class="{cls}">{arrow}{abs(q.change_pct):.2f}%</span>'
                )
            else:
                spans.append(
                    f'<span class="kj-tick-label">{q.label}</span> <span class="kj-tick-price">{price_str}</span>'
                )
    return '<span class="kj-tick-sep">&nbsp;&nbsp;|&nbsp;&nbsp;</span>'.join(spans)


_TICKER_CSS_TEMPLATE = """
<style>
.kj-ticker-wrap {{
    width: 100%;
    overflow: hidden;
    background: {bg};
    border-top: 1px solid {border};
    border-bottom: 1px solid {border};
    padding: 8px 0;
    box-sizing: border-box;
}}
.kj-ticker-move {{
    display: inline-block;
    white-space: nowrap;
    padding-left: 100%;
    animation: kj-scroll {duration}s linear infinite;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 15px;
}}
.kj-tick-label {{ color: {text}; font-weight: 700; }}
.kj-tick-price {{ color: {text}; }}
.kj-tick-up {{ color: #26A65B; font-weight: 700; }}
.kj-tick-down {{ color: #E5484D; font-weight: 700; }}
.kj-tick-na {{ color: {muted}; }}
.kj-tick-sep {{ color: {muted}; }}
@keyframes kj-scroll {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-100%); }}
}}
</style>
"""


def _render_html(html: str, height: int) -> None:
    """st.iframe (Streamlit >= 1.4x) with a fallback to the older
    st.components.v1.html for projects pinned to an earlier Streamlit."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:  # pragma: no cover - only hit on older Streamlit installs
        st.components.v1.html(html, height=height, scrolling=False)


def render_ticker_banner(
    symbol_map: dict[str, str] | None = None,
    include_commodities: bool = True,
    theme: str = "dark",
    speed_seconds: int = 40,
) -> None:
    """Renders the live scrolling ticker banner. Call once near the top
    of your page. `speed_seconds` controls how long one full loop takes
    (lower = faster scroll)."""
    symbol_map = symbol_map or DEFAULT_SYMBOLS
    quotes = _cached_quotes(tuple(symbol_map.items()), include_commodities)
    content_html = _quotes_to_html(quotes)

    if theme == "dark":
        css = _TICKER_CSS_TEMPLATE.format(
            bg="#0E1117", border="#2A2F3A", text="#FAFAFA", muted="#9AA4B2", duration=speed_seconds
        )
    else:
        css = _TICKER_CSS_TEMPLATE.format(
            bg="#F5F7FA", border="#E1E5EA", text="#1A1C1E", muted="#5B6572", duration=speed_seconds
        )

    html = f"""
    {css}
    <div class="kj-ticker-wrap">
      <div class="kj-ticker-move">{content_html}&nbsp;&nbsp;|&nbsp;&nbsp;{content_html}</div>
    </div>
    """
    _render_html(html, 48)
