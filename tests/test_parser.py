from __future__ import annotations

from pinesprout.core.ast_nodes import NodeKind
from pinesprout.core.parser import parse


def test_parse_detects_version(clean_v6_source):
    program = parse(clean_v6_source)
    assert program.pine_version == 6


def test_parse_detects_no_version_when_absent():
    program = parse("indicator('x')\nplot(close)\n")
    assert program.pine_version is None


def test_parse_finds_strategy_declaration(clean_v6_source):
    program = parse(clean_v6_source)
    kinds = [d.kind for d in program.declarations]
    assert NodeKind.STRATEGY_DECL in kinds


def test_parse_finds_indicator_declaration():
    program = parse('//@version=6\nindicator("Test")\nplot(close)\n')
    kinds = [d.kind for d in program.declarations]
    assert NodeKind.INDICATOR_DECL in kinds


def test_parse_legacy_study_is_indicator_decl():
    program = parse('//@version=4\nstudy("Test")\nplot(close)\n')
    indicator_decls = [d for d in program.declarations if d.kind == NodeKind.INDICATOR_DECL]
    assert len(indicator_decls) == 1
    assert indicator_decls[0].meta["legacy"] is True


def test_parse_variable_declaration():
    program = parse('//@version=6\nindicator("x")\nlen = 14\n')
    var_decls = [v for v in program.variable_assignments if v.kind == NodeKind.VARIABLE_DECL]
    assert any(v.meta["name"] == "len" for v in var_decls)


def test_parse_var_keyword_flags_is_var():
    program = parse('//@version=6\nindicator("x")\nvar count = 0\n')
    var_decls = [v for v in program.variable_assignments if v.kind == NodeKind.VARIABLE_DECL]
    assert var_decls[0].meta["name"] == "count"
    assert var_decls[0].meta["is_var"] is True


def test_parse_reassignment():
    program = parse('//@version=6\nindicator("x")\nvar count = 0\ncount := count + 1\n')
    reassigns = [v for v in program.variable_assignments if v.kind == NodeKind.VARIABLE_REASSIGN]
    assert len(reassigns) == 1
    assert reassigns[0].meta["name"] == "count"


def test_parse_if_statement():
    program = parse('//@version=6\nindicator("x")\nif close > open\n    x = 1\n')
    if_nodes = [n for n in program.root.children if n.kind == NodeKind.IF_STATEMENT]
    assert len(if_nodes) == 1
    assert if_nodes[0].meta["condition"] == "close > open"


def test_parse_for_statement():
    program = parse('//@version=6\nindicator("x")\nfor i = 0 to 10\n    x = i\n')
    for_nodes = [n for n in program.root.children if n.kind == NodeKind.FOR_STATEMENT]
    assert for_nodes[0].meta["var"] == "i"
    assert for_nodes[0].meta["to"] == "10"


def test_parse_function_decl():
    program = parse('//@version=6\nindicator("x")\nf(a, b) => a + b\n')
    fn_decls = [d for d in program.declarations if d.kind == NodeKind.FUNCTION_DECL]
    assert fn_decls[0].meta["name"] == "f"
    assert fn_decls[0].meta["params"] == ["a", "b"]


def test_parse_comments_collected():
    program = parse("//@version=6\n// this is a comment\nindicator('x')\n")
    assert len(program.comments) == 1


def test_parse_plot_statement_recognized():
    program = parse('//@version=6\nindicator("x")\nplot(close, title="Close")\n')
    plot_nodes = [n for n in program.root.children if n.kind == NodeKind.PLOT_STATEMENT]
    assert len(plot_nodes) == 1


def test_parse_input_statement_recognized():
    program = parse('//@version=6\nindicator("x")\nlen = input.int(14)\n')
    input_nodes = [n for n in program.root.children if n.kind == NodeKind.INPUT_STATEMENT]
    assert len(input_nodes) == 1


def test_split_inline_comment_respects_strings():
    from pinesprout.core.parser import _split_inline_comment

    code, sep, comment = _split_inline_comment('x = "http://example.com" // real comment')
    assert code == 'x = "http://example.com" '
    assert comment == "// real comment"
