from __future__ import annotations

from pinesprout.core.linter import LintCategory, Severity, lint_source


def test_lint_clean_script_has_no_errors(clean_v6_source):
    result = lint_source(clean_v6_source)
    assert result.error_count == 0
    assert result.passed


def test_lint_missing_version_pragma_is_error():
    result = lint_source('indicator("x")\nplot(close)\n')
    assert any(
        i.category == LintCategory.STRUCTURE and i.severity == Severity.ERROR
        for i in result.issues
    )


def test_lint_missing_declaration_is_error():
    result = lint_source("//@version=6\nx = close\nplot(x)\n")
    assert any(
        "declaration" in i.message.lower() and i.severity == Severity.ERROR
        for i in result.issues
    )


def test_lint_detects_unused_variable():
    source = '//@version=6\nindicator("x")\nunused = close * 2\nplot(close)\n'
    result = lint_source(source)
    unused_issues = [i for i in result.issues if i.category == LintCategory.UNUSED_VARIABLE]
    assert len(unused_issues) == 1
    assert unused_issues[0].symbol == "unused"


def test_lint_does_not_flag_used_variable():
    source = '//@version=6\nindicator("x")\nlen = 14\nplot(ta.sma(close, len))\n'
    result = lint_source(source)
    unused_issues = [i for i in result.issues if i.category == LintCategory.UNUSED_VARIABLE]
    assert len(unused_issues) == 0


def test_lint_ignores_underscore_prefixed_variables():
    source = '//@version=6\nindicator("x")\n_ignored = close\nplot(close)\n'
    result = lint_source(source)
    assert not any(i.symbol == "_ignored" for i in result.issues)


def test_lint_detects_deprecated_study():
    result = lint_source('//@version=4\nstudy("x")\nplot(close)\n')
    deprecated = [i for i in result.issues if i.category == LintCategory.DEPRECATED_SYNTAX]
    assert any(i.symbol == "study" for i in deprecated)


def test_lint_detects_deprecated_bare_rsi():
    result = lint_source('//@version=4\nstudy("x")\nr = rsi(close, 14)\nplot(r)\n')
    deprecated = [i for i in result.issues if i.category == LintCategory.DEPRECATED_SYNTAX]
    assert any(i.symbol == "rsi" for i in deprecated)


def test_lint_does_not_flag_namespaced_rsi():
    result = lint_source('//@version=6\nindicator("x")\nr = ta.rsi(close, 14)\nplot(r)\n')
    deprecated = [i for i in result.issues if i.category == LintCategory.DEPRECATED_SYNTAX and i.symbol == "rsi"]
    assert len(deprecated) == 0


def test_lint_detects_repaint_risk_security_without_lookahead():
    source = '//@version=6\nindicator("x")\ns = request.security(syminfo.tickerid, "D", close)\nplot(s)\n'
    result = lint_source(source)
    repaint_issues = [i for i in result.issues if i.category == LintCategory.REPAINT_RISK]
    assert any(i.severity == Severity.WARNING for i in repaint_issues)


def test_lint_no_repaint_warning_with_lookahead_off():
    source = (
        '//@version=6\nindicator("x")\n'
        's = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_off)\nplot(s)\n'
    )
    result = lint_source(source)
    warnings = [
        i for i in result.issues
        if i.category == LintCategory.REPAINT_RISK and i.severity == Severity.WARNING
    ]
    assert len(warnings) == 0


def test_lint_detects_performance_issue_in_loop():
    source = (
        '//@version=6\nindicator("x")\n'
        "for i = 0 to 10\n    x = ta.sma(close, 14)\nplot(close)\n"
    )
    result = lint_source(source)
    perf_issues = [i for i in result.issues if i.category == LintCategory.PERFORMANCE]
    assert len(perf_issues) >= 1


def test_lint_line_length_style_warning():
    long_line = "x" * 130 + " = close"
    source = f'//@version=6\nindicator("x")\n{long_line}\nplot(close)\n'
    result = lint_source(source)
    style_issues = [i for i in result.issues if i.category == LintCategory.STYLE]
    assert any("120 characters" in i.message or "exceeds" in i.message for i in style_issues)


def test_lint_result_counts_by_severity():
    source = 'x = close\nplot(x)\n'  # missing version + missing declaration = 2 errors
    result = lint_source(source)
    assert result.error_count >= 2
    assert result.passed is False


def test_lint_issues_sorted_by_line():
    result = lint_source('x=close\nplot(x)\n')
    lines = [i.line for i in result.issues]
    assert lines == sorted(lines)
