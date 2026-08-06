from __future__ import annotations

from pinesprout.core.lexer import TokenType, tokenize


def test_tokenize_version_annotation():
    tokens = tokenize("//@version=6\n")
    assert tokens[0].type == TokenType.ANNOTATION
    assert "@version=6" in tokens[0].value


def test_tokenize_comment_vs_annotation():
    tokens = tokenize("// just a comment\n")
    assert tokens[0].type == TokenType.COMMENT


def test_tokenize_string_literal():
    tokens = tokenize('title = "Hello World"\n')
    string_tokens = [t for t in tokens if t.type == TokenType.STRING]
    assert len(string_tokens) == 1
    assert string_tokens[0].value == '"Hello World"'


def test_tokenize_numbers():
    tokens = tokenize("x = 3.14\ny = 42\n")
    numbers = [t.value for t in tokens if t.type == TokenType.NUMBER]
    assert "3.14" in numbers
    assert "42" in numbers


def test_tokenize_keywords_vs_identifiers():
    tokens = tokenize("if close > open\n")
    kinds = {t.value: t.type for t in tokens if t.type in (TokenType.KEYWORD, TokenType.IDENTIFIER)}
    assert kinds["if"] == TokenType.KEYWORD
    assert kinds["close"] == TokenType.IDENTIFIER


def test_tokenize_operators():
    tokens = tokenize("a := b\nc == d\n")
    ops = [t.value for t in tokens if t.type == TokenType.OPERATOR]
    assert ":=" in ops
    assert "==" in ops


def test_tokenize_ends_with_eof():
    tokens = tokenize("x = 1\n")
    assert tokens[-1].type == TokenType.EOF


def test_tokenize_preserves_line_numbers():
    tokens = tokenize("a = 1\nb = 2\n")
    b_tokens = [t for t in tokens if t.value == "b"]
    assert b_tokens[0].line == 2
