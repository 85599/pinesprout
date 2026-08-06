from __future__ import annotations

from pinesprout.core.optimizer import optimize_source


def test_optimize_detects_repeated_ta_calls():
    source = '//@version=6\nindicator("x")\na = ta.rsi(close, 14) + 1\nb = ta.rsi(close, 14) - 1\nplot(a)\nplot(b)\n'
    result = optimize_source(source)
    assert any("ta.rsi" in s.title for s in result.suggestions)


def test_optimize_detects_magic_numbers():
    source = '//@version=6\nindicator("x")\nx = close > 12345\nplot(close)\n'
    result = optimize_source(source)
    assert any("Magic number" in s.title for s in result.suggestions)


def test_optimize_detects_redundant_boolean():
    source = '//@version=6\nindicator("x")\nif close > open == true\n    x = 1\nplot(close)\n'
    result = optimize_source(source)
    assert any("boolean" in s.title.lower() for s in result.suggestions)


def test_optimize_clean_script_has_minimal_suggestions(clean_v6_source):
    result = optimize_source(clean_v6_source)
    # A well-written script shouldn't trigger magic-number or boolean noise.
    assert not any("boolean" in s.title.lower() for s in result.suggestions)


def test_optimize_apply_fixes_removes_redundant_true():
    source = '//@version=6\nindicator("x")\nif close > open == true\n    x = 1\nplot(close)\n'
    result = optimize_source(source, apply_fixes=True)
    assert result.optimized_source is not None
    assert "== true" not in result.optimized_source


def test_optimize_surfaces_loop_performance_issue():
    source = '//@version=6\nindicator("x")\nfor i = 0 to 5\n    v = ta.ema(close, 10)\nplot(close)\n'
    result = optimize_source(source)
    assert any("performance" in s.title.lower() or "loop" in s.title.lower() for s in result.suggestions)
