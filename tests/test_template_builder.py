"""Tests for pinesprout.generators.template_builder — the combinatorial
indicator/strategy builder."""

from __future__ import annotations

import pytest

from pinesprout.core.linter import Linter
from pinesprout.core.parser import parse
from pinesprout.generators.template_builder import (
    INDICATORS,
    BuilderSpec,
    RiskPreset,
    SignalPattern,
    build_from_spec,
    estimate_combination_count,
    indicators_for_pattern,
)


def test_estimate_combination_count_sane():
    counts = estimate_combination_count()
    assert counts["indicators"] >= 20
    assert counts["structural_patterns"] > 0
    assert counts["structural_total_with_type_and_risk"] > counts["structural_patterns"]


def test_indicators_for_pattern_price_cross_only_overlay_friendly():
    candidates = indicators_for_pattern(SignalPattern.PRICE_CROSS_MA)
    assert all(c.is_overlay_friendly and not c.is_band for c in candidates)
    assert len(candidates) > 0


def test_indicators_for_pattern_threshold_only_threshold_capable():
    candidates = indicators_for_pattern(SignalPattern.OSCILLATOR_THRESHOLD)
    assert all(c.supports_threshold for c in candidates)
    assert len(candidates) > 0


def test_indicators_for_pattern_band_only_bands():
    candidates = indicators_for_pattern(SignalPattern.BAND_BREAKOUT)
    assert all(c.is_band for c in candidates)
    assert len(candidates) > 0


def test_build_price_cross_ma_produces_valid_pine():
    spec = BuilderSpec(
        title="Test EMA Cross",
        script_type="indicator",
        pattern=SignalPattern.PRICE_CROSS_MA,
        primary_indicator="ema",
    )
    source = build_from_spec(spec)
    program = parse(source)
    assert program.pine_version == 6
    assert "ta.ema(close" in source
    assert "ta.crossover(close" in source


def test_build_ma_crossover_uses_both_indicators():
    spec = BuilderSpec(
        title="Test Cross",
        script_type="indicator",
        pattern=SignalPattern.MA_CROSSOVER,
        primary_indicator="ema",
        secondary_indicator="sma",
    )
    source = build_from_spec(spec)
    assert "ta.ema(close" in source
    assert "ta.sma(close" in source
    assert "ta.crossover(fastLine, slowLine)" in source


def test_build_oscillator_threshold_uses_custom_levels():
    spec = BuilderSpec(
        title="Test RSI",
        script_type="indicator",
        pattern=SignalPattern.OSCILLATOR_THRESHOLD,
        primary_indicator="rsi",
        overbought=75.0,
        oversold=25.0,
    )
    source = build_from_spec(spec)
    assert "obLevel = 75.0" in source
    assert "osLevel = 25.0" in source


def test_build_band_breakout_produces_upper_lower():
    spec = BuilderSpec(
        title="Test BB",
        script_type="indicator",
        pattern=SignalPattern.BAND_BREAKOUT,
        primary_indicator="bb",
    )
    source = build_from_spec(spec)
    assert "bandUpper" in source
    assert "bandLower" in source


def test_build_strategy_with_fixed_percent_risk():
    spec = BuilderSpec(
        title="Test Strategy",
        script_type="strategy",
        pattern=SignalPattern.PRICE_CROSS_MA,
        primary_indicator="sma",
        risk=RiskPreset.FIXED_PERCENT,
        stop_loss_pct=3.0,
        take_profit_pct=6.0,
    )
    source = build_from_spec(spec)
    assert "strategy(" in source
    assert "strategy.entry" in source
    assert "1 - 3.0 / 100" in source
    assert "1 + 6.0 / 100" in source


def test_build_strategy_with_atr_risk():
    spec = BuilderSpec(
        title="Test Strategy",
        script_type="strategy",
        pattern=SignalPattern.PRICE_CROSS_MA,
        primary_indicator="sma",
        risk=RiskPreset.ATR_BASED,
        atr_stop_mult=1.5,
        atr_tp_mult=2.5,
    )
    source = build_from_spec(spec)
    assert "riskAtr = ta.atr(14)" in source
    assert "riskAtr * 1.5" in source
    assert "riskAtr * 2.5" in source


def test_build_indicator_type_has_alerts_not_strategy_entries():
    spec = BuilderSpec(
        title="Test Ind",
        script_type="indicator",
        pattern=SignalPattern.PRICE_CROSS_MA,
        primary_indicator="sma",
    )
    source = build_from_spec(spec)
    assert "alertcondition(" in source
    assert "strategy.entry" not in source


@pytest.mark.parametrize("indicator_id", list(INDICATORS.keys()))
def test_every_indicator_lints_clean_in_its_simplest_valid_pattern(indicator_id):
    spec_ind = INDICATORS[indicator_id]
    if spec_ind.is_band:
        pattern = SignalPattern.BAND_BREAKOUT
    elif spec_ind.supports_threshold:
        pattern = SignalPattern.OSCILLATOR_THRESHOLD
    elif spec_ind.is_overlay_friendly:
        pattern = SignalPattern.PRICE_CROSS_MA
    else:
        pytest.skip(f"{indicator_id} has no directly testable single-indicator pattern")
        return

    spec = BuilderSpec(
        title="Lint Check",
        script_type="indicator",
        pattern=pattern,
        primary_indicator=indicator_id,
        overlay=spec_ind.is_overlay_friendly,
    )
    source = build_from_spec(spec)
    issues = Linter.from_source(source).run()
    assert not any(i.severity.value == "error" for i in issues), issues


def test_every_indicator_appears_in_at_least_one_pattern():
    all_patterns = list(SignalPattern)
    for indicator_id, _spec_ind in INDICATORS.items():
        found = any(any(c.id == indicator_id for c in indicators_for_pattern(p)) for p in all_patterns)
        assert found, f"{indicator_id} is unreachable from every signal pattern"
