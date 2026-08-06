"""Smoke tests for streamlit_app.py using Streamlit's official AppTest
framework. These run the app in-process (no server/network needed) and
assert no exceptions are raised across the main user flows."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("yfinance")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = str(Path(__file__).parent.parent / "streamlit_app.py")


def _mode_radio(at):
    """The sidebar now has two radios (theme + mode); find the mode one
    by its option values rather than assuming a fixed index."""
    return next(r for r in at.sidebar.radio if "template" in " ".join(r.options).lower())


def test_app_loads_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception


def test_template_mode_generates_pivot_confluence_script():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📋 Use a template").run(timeout=30)
    assert not at.exception

    tpl_select = at.selectbox[0]
    pivot_label = next(o for o in tpl_select.options if "Pivot" in o)
    tpl_select.set_value(pivot_label).run(timeout=30)

    gen_btn = next(b for b in at.button if "Generate from template" in b.label)
    gen_btn.click().run(timeout=30)

    assert not at.exception
    tab_labels = [t.label for t in at.tabs]
    assert "🔍 Lint" in tab_labels
    assert "📊 Analyze" in tab_labels


def test_template_mode_lint_tab_shows_clean_result():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📋 Use a template").run(timeout=30)
    tpl_select = at.selectbox[0]
    pivot_label = next(o for o in tpl_select.options if "Pivot" in o)
    tpl_select.set_value(pivot_label).run(timeout=30)
    gen_btn = next(b for b in at.button if "Generate from template" in b.label)
    gen_btn.click().run(timeout=30)

    lint_tab = next(t for t in at.tabs if "Lint" in t.label)
    assert any("No issues found" in s.value for s in lint_tab.success)


def test_paste_mode_loads_custom_script(clean_v6_source):
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📄 Paste / upload a script").run(timeout=30)
    assert not at.exception

    at.text_area(key="pasted_source").set_value(clean_v6_source)
    load_btn = next(b for b in at.button if "Load pasted script" in b.label)
    load_btn.click().run(timeout=30)

    assert not at.exception
    analyze_tab = next(t for t in at.tabs if "Analyze" in t.label)
    assert any("Clean EMA Strategy" in m.value for m in analyze_tab.markdown)


def test_heatmap_mode_renders_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📊 Live Market Heatmap").run(timeout=30)
    assert not at.exception
    select_labels = [sb.label for sb in at.selectbox]
    assert "Index / universe" in select_labels


def test_heatmap_mode_supports_india_exchange():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📊 Live Market Heatmap").run(timeout=30)
    market_mode_radio = next(r for r in at.radio if "Pick exchanges" in " ".join(r.options))
    market_mode_radio.set_value("Pick exchanges (India, Europe, Asia-Pacific, ...)").run(timeout=30)
    assert not at.exception
    region_select = next(sb for sb in at.selectbox if sb.label == "Region")
    assert "🇮🇳 India" in region_select.options
    region_select.set_value("🇮🇳 India").run(timeout=30)
    exchange_select = next(m for m in at.multiselect if m.label == "Exchange(s)")
    assert any("NSE" in opt for opt in exchange_select.options)
    assert any("BSE" in opt for opt in exchange_select.options)


def test_heatmap_mode_has_nse_index_watch_as_default_tab():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📊 Live Market Heatmap").run(timeout=30)
    assert not at.exception
    tab_labels = [t.label for t in at.tabs]
    assert "🇮🇳 NSE Index Watch" in tab_labels
    assert "🌍 TradingView Heatmap (global)" in tab_labels
    # Index Watch's own category tabs should also be present.
    assert "Broad Market Indices" in tab_labels
    assert "Sectoral Indices" in tab_labels


def test_index_watch_refresh_button_clears_cache_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📊 Live Market Heatmap").run(timeout=30)
    refresh_btn = next(b for b in at.button if "Refresh" in b.label)
    refresh_btn.click().run(timeout=30)
    assert not at.exception


def test_index_watch_overview_tab_has_search_and_csv_download():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📊 Live Market Heatmap").run(timeout=30)
    assert not at.exception
    tab_labels = [t.label for t in at.tabs]
    assert "📈 Overview" in tab_labels
    search_inputs = [ti for ti in at.text_input if "Search indices" in ti.label]
    assert len(search_inputs) == 1


def test_index_watch_overview_search_filters_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("📊 Live Market Heatmap").run(timeout=30)
    search_input = next(ti for ti in at.text_input if "Search indices" in ti.label)
    search_input.set_value("NIFTY BANK").run(timeout=30)
    assert not at.exception


def test_about_mode_renders_developer_and_links():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("ℹ️ About").run(timeout=30)
    assert not at.exception
    assert any("Khushal Jain" in m.value for m in at.markdown)


def test_about_mode_has_custom_link_button_colors():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("ℹ️ About").run(timeout=30)
    assert not at.exception
    css_blocks = [m.value for m in at.markdown if "href*=" in m.value]
    combined = " ".join(css_blocks)
    assert "tradingview.com" in combined and "#FF9933" in combined
    assert "x.com/" in combined and "#FFFFFF" in combined
    assert "github.com" in combined and "#22A55A" in combined
    # Regression guard: text color must cascade to every descendant element
    # (span included, not just p/div) -- a real bug we caught via a visual
    # screenshot where the white Twitter/X button's label was invisible
    # (white text on white background) because the color-inherit override
    # only targeted `p, div` and Streamlit renders button labels in a
    # `span`, leaving the global dark-theme white text color in effect.
    assert "] *" in combined or '"] *' in combined
    assert "github.com" in combined and "#22A55A" in combined


def test_template_builder_mode_builds_clean_script():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value("🧪 Template Builder (huge combo space)").run(timeout=30)
    assert not at.exception
    build_btn = next(b for b in at.button if "Build Pine Script" in b.label)
    build_btn.click().run(timeout=30)
    assert not at.exception
    lint_tab = next(t for t in at.tabs if "Lint" in t.label)
    assert any("No issues found" in s.value for s in lint_tab.success)


def test_theme_toggle_switches_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    theme_radio = next(r for r in at.sidebar.radio if r.value in ("dark", "light"))
    assert theme_radio.value == "dark"
    theme_radio.set_value("light").run(timeout=30)
    assert not at.exception
    assert at.session_state["kj_theme"] == "light"


def test_theme_css_reflects_choice_in_same_pass():
    """Regression test for a real bug caught via manual browser screenshots:
    inject_theme_css() used to run *before* theme_toggle() in script order,
    so a theme change wasn't reflected in the CSS until some unrelated
    later interaction triggered another rerun -- the radio would show
    "Light" selected while the page stayed visually dark. Fixed by moving
    inject_theme_css() to run immediately after theme_toggle()."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    theme_radio = next(r for r in at.sidebar.radio if r.value in ("dark", "light"))
    theme_radio.set_value("light").run(timeout=30)
    assert not at.exception
    css_blocks = [m.value for m in at.markdown if "--kj-bg" in m.value]
    assert len(css_blocks) == 1
    assert "#FFFFFF" in css_blocks[0]  # light background must be the value actually injected


@pytest.mark.parametrize(
    "mode",
    [
        "✨ Describe my strategy (AI)",
        "🧪 Template Builder (huge combo space)",
        "📋 Use a template",
        "📄 Paste / upload a script",
        "📊 Live Market Heatmap",
        "ℹ️ About",
    ],
)
def test_sidebar_mode_selection_survives_theme_toggle(mode):
    """Regression test for a real bug caught via manual browser screenshots
    (not detectable by exception-only checks): theme_toggle() used to call
    st.rerun() unconditionally after a theme change, which truncated the
    current script pass before the sidebar's mode radio was re-declared.
    Streamlit garbage-collects state for widgets skipped in a pass, which
    silently reset navigation to the first sidebar option on every theme
    toggle. See the fix + comment in pinesprout/utils/theme.py."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    _mode_radio(at).set_value(mode).run(timeout=30)

    theme_radio = next(r for r in at.sidebar.radio if r.value in ("dark", "light"))
    theme_radio.set_value("light").run(timeout=30)

    assert not at.exception
    mode_radio_after = _mode_radio(at)
    assert mode_radio_after.value == mode


def test_ai_generate_mode_shows_error_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    # AI generate is the default mode; type a prompt and click generate.
    at.text_area[0].set_value("a simple sma indicator").run(timeout=30)
    gen_btn = next(b for b in at.button if "Generate Pine Script" in b.label)
    gen_btn.click().run(timeout=30)

    assert not at.exception
    assert any("API key" in e.value for e in at.error)


def test_ai_generate_mode_has_api_key_input_in_main_panel():
    """The API key field must be reachable without scrolling the sidebar --
    it should also appear directly in the main panel for this mode."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception
    api_key_inputs = [ti for ti in at.text_input if ti.label == "ANTHROPIC_API_KEY"]
    assert len(api_key_inputs) >= 2  # sidebar + main panel
