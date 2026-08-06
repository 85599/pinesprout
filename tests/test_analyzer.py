from __future__ import annotations

from pinesprout.core.analyzer import analyze


def test_analyze_detects_strategy_type(clean_v6_source):
    report = analyze(clean_v6_source)
    assert report.script_kind.is_strategy is True
    assert report.script_kind.is_indicator is False


def test_analyze_detects_title(clean_v6_source):
    report = analyze(clean_v6_source)
    assert report.script_kind.title == "Clean EMA Strategy"


def test_analyze_counts_plots(clean_v6_source):
    report = analyze(clean_v6_source)
    assert report.plot_count == 2


def test_analyze_counts_strategy_entries(clean_v6_source):
    report = analyze(clean_v6_source)
    assert report.strategy_entry_count == 2


def test_analyze_counts_inputs(clean_v6_source):
    report = analyze(clean_v6_source)
    assert report.input_count == 2
    assert report.inputs_by_type.get("int") == 2


def test_analyze_detects_indicator_type():
    source = '//@version=6\nindicator("My Indicator", overlay=true)\nplot(close)\n'
    report = analyze(source)
    assert report.script_kind.is_indicator is True
    assert report.script_kind.overlay is True


def test_analyze_legacy_study_recognized_as_indicator():
    source = '//@version=4\nstudy("Legacy", overlay=false)\nplot(close)\n'
    report = analyze(source)
    assert report.script_kind.is_indicator is True
    assert report.script_kind.title == "Legacy"


def test_analyze_warns_on_strategy_without_entries():
    source = '//@version=6\nstrategy("No Entries")\nplot(close)\n'
    report = analyze(source)
    assert any("strategy.entry" in w for w in report.warnings)


def test_analyze_warns_on_indicator_without_plots():
    source = '//@version=6\nindicator("No Plots")\nx = close\n'
    report = analyze(source)
    assert any("plot" in w.lower() for w in report.warnings)


def test_analyze_detects_security_usage(messy_v4_source):
    report = analyze(messy_v4_source)
    assert report.uses_security is True


def test_analyze_complexity_score_increases_with_branching():
    simple = '//@version=6\nindicator("x")\nplot(close)\n'
    branchy = '//@version=6\nindicator("x")\nif close > open\n    x = 1\nif close < open\n    y = 2\nplot(close)\n'
    simple_score = analyze(simple).complexity_score
    branchy_score = analyze(branchy).complexity_score
    assert branchy_score > simple_score


def test_analyze_ta_function_calls_counted():
    source = '//@version=6\nindicator("x")\na = ta.rsi(close, 14)\nb = ta.sma(close, 20)\nplot(a)\nplot(b)\n'
    report = analyze(source)
    assert report.ta_function_calls.get("ta.rsi") == 1
    assert report.ta_function_calls.get("ta.sma") == 1
