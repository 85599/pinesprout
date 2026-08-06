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

Run locally:
    streamlit run streamlit_app.py

Deploy on Streamlit Community Cloud: point it at this file as the "Main
file path" for the repo; `requirements.txt` at the repo root installs
PineSprout itself (`-e .`) plus Streamlit.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

import streamlit as st

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


def _set_source(source: str, filename: str) -> None:
    st.session_state.pine_source = source
    st.session_state.pine_filename = filename


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

st.sidebar.divider()
st.sidebar.caption("PineSprout only ever operates on the script text you provide — "
                    "it never fetches or bypasses protected/invite-only TradingView scripts.")

# ---------------------------------------------------------------------------
# Main area: acquisition mode
# ---------------------------------------------------------------------------
st.title("PineSprout Studio")
st.caption(
    "💡 Don't see the sidebar (mode selector, theme toggle)? "
    "Click the **»** arrow at the top-left of the page to expand it — "
    "your browser remembers this setting across visits."
)
render_ticker_banner(DEFAULT_SYMBOLS, theme=get_theme())

if mode == "✨ Describe my strategy (AI)":
    st.subheader("Describe your strategy in plain English")
    st.caption(
        "Example: *\"A daily pivot-point strategy that goes long when price reclaims "
        "the daily PP with RSI above 50, with a stop below S1\"*"
    )

    with st.expander("🔑 Anthropic API Key (required for this mode)", expanded=not api_key):
        main_api_key = st.text_input(
            "ANTHROPIC_API_KEY",
            value=api_key,
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
st.caption("Live ticker & heatmap tools by **Khushal Jain**.")
