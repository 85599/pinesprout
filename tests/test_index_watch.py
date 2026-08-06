"""Tests for pinesprout.utils.index_watch -- the NSE-style Index Watch
card grid (native Streamlit, no iframe)."""

from __future__ import annotations

import pytest

pytest.importorskip("yfinance")

from pinesprout.utils.index_watch import (  # noqa: E402
    CATEGORIES,
    IndexQuote,
    _tile_html,
)


def test_categories_nonempty():
    assert len(CATEGORIES) >= 3
    for symbols in CATEGORIES.values():
        assert len(symbols) > 0


def test_broad_market_includes_flagship_indices():
    broad = CATEGORIES["Broad Market Indices"]
    assert broad["NIFTY 50"] == "^NSEI"
    assert broad["SENSEX"] == "^BSESN"


def test_broken_nifty_pvt_bank_ticker_removed():
    all_symbols = {sym for cat in CATEGORIES.values() for sym in cat.values()}
    assert "NIFTYPVTBANK.NS" not in all_symbols


def test_thematic_indices_use_verified_tickers():
    thematic = CATEGORIES["Thematic Indices"]
    assert thematic["NIFTY PSU BANK"] == "^CNXPSUBANK"
    assert thematic["NIFTY CONSUMPTION"] == "^CNXCONSUM"


def test_tile_html_na_for_unavailable_quote():
    q = IndexQuote(label="TEST INDEX", ok=False)
    html = _tile_html(q, "#161B22", "#2A2F3A", "#FAFAFA")
    assert "N/A" in html
    assert "TEST INDEX" in html


def test_tile_html_green_for_positive_change():
    q = IndexQuote(label="NIFTY 50", price=24500.0, change_pct=0.75, ok=True)
    html = _tile_html(q, "#161B22", "#2A2F3A", "#FAFAFA")
    assert "+0.75%" in html
    assert "#178A4C" in html  # green border for advancing


def test_tile_html_red_for_negative_change():
    q = IndexQuote(label="NIFTY 50", price=24500.0, change_pct=-1.25, ok=True)
    html = _tile_html(q, "#161B22", "#2A2F3A", "#FAFAFA")
    assert "-1.25%" in html
    assert "#C6303E" in html  # red border for declining


def test_tile_html_formats_price_with_commas():
    q = IndexQuote(label="SENSEX", price=80234.567, change_pct=0.1, ok=True)
    html = _tile_html(q, "#161B22", "#2A2F3A", "#FAFAFA")
    assert "80,234.57" in html
