from __future__ import annotations

from pinesprout.core.formatter import FormatOptions, format_source


def test_format_trims_trailing_whitespace():
    source = "//@version=6\nindicator('x')   \nplot(close)  \n"
    formatted = format_source(source)
    assert "   \n" not in formatted
    assert not any(line.endswith(" ") for line in formatted.splitlines())


def test_format_collapses_multiple_blank_lines():
    source = "//@version=6\nindicator('x')\n\n\n\nplot(close)\n"
    formatted = format_source(source, FormatOptions(max_blank_lines=1))
    assert "\n\n\n" not in formatted


def test_format_ends_with_single_newline():
    source = "//@version=6\nindicator('x')\nplot(close)"
    formatted = format_source(source)
    assert formatted.endswith("\n")
    assert not formatted.endswith("\n\n")


def test_format_version_pragma_moved_to_top():
    source = "indicator('x')\n//@version=6\nplot(close)\n"
    formatted = format_source(source)
    assert formatted.splitlines()[0] == "//@version=6"


def test_format_keyword_args_stay_tight():
    source = '//@version=6\nindicator(title="X", overlay=true)\n'
    formatted = format_source(source)
    assert 'title="X"' in formatted
    assert 'title = "X"' not in formatted


def test_format_top_level_assignment_gets_spaced():
    source = "//@version=6\nindicator('x')\nlen=14\n"
    formatted = format_source(source)
    assert "len = 14" in formatted


def test_format_comma_spacing():
    source = "//@version=6\nindicator('x')\nplot(close,color=color.red)\n"
    formatted = format_source(source)
    assert "close, color" in formatted


def test_format_is_idempotent(clean_v6_source):
    once = format_source(clean_v6_source)
    twice = format_source(once)
    assert once == twice


def test_format_preserves_string_contents():
    source = '//@version=6\nindicator("A==B  ,  C")\nplot(close)\n'
    formatted = format_source(source)
    assert '"A==B  ,  C"' in formatted


def test_format_does_not_touch_comment_contents():
    source = "//@version=6\nindicator('x') // a==b,c\nplot(close)\n"
    formatted = format_source(source)
    assert "a==b,c" in formatted


def test_format_preserves_arrow_operator():
    source = "//@version=6\nindicator('x')\nf(a, b) =>\n    a + b\nplot(close)\n"
    formatted = format_source(source)
    assert "=>" in formatted
    assert "= >" not in formatted


def test_format_keeps_keyword_args_tight_across_multiline_call():
    source = '//@version=6\nindicator("x")\nplot(close, title="Close",\n     linewidth=2, color=color.blue)\n'
    formatted = format_source(source)
    assert "linewidth=2" in formatted
    assert "linewidth = 2" not in formatted
    assert "color=color.blue" in formatted
