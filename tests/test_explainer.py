from __future__ import annotations

from pinesprout.core.explainer import explain_script_summary, explain_source


def test_explain_source_produces_entry_per_statement(clean_v6_source):
    explanations = explain_source(clean_v6_source)
    assert len(explanations) > 0
    assert all(e.line > 0 for e in explanations)


def test_explain_source_explains_if_statement():
    source = '//@version=6\nindicator("x")\nif close > open\n    x = 1\nplot(close)\n'
    explanations = explain_source(source)
    if_explanation = next(e for e in explanations if e.node_kind == "IF_STATEMENT")
    assert "close > open" in if_explanation.explanation


def test_explain_source_explains_variable_decl():
    source = '//@version=6\nindicator("x")\nlen = 14\nplot(close)\n'
    explanations = explain_source(source)
    var_explanation = next(e for e in explanations if e.node_kind == "VARIABLE_DECL")
    assert "len" in var_explanation.explanation


def test_explain_summary_mentions_script_type(clean_v6_source):
    summary = explain_script_summary(clean_v6_source)
    assert "strategy" in summary.lower()


def test_explain_summary_mentions_title(clean_v6_source):
    summary = explain_script_summary(clean_v6_source)
    assert "Clean EMA Strategy" in summary
