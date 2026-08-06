"""A small, dependency-free lexer for Pine Script (v4/v5/v6).

This tokenizer is intentionally forgiving: Pine Script has a fairly
regular, Python-like surface syntax (significant indentation, ``//``
comments, no semicolons), so a single-pass regex tokenizer is sufficient
to support formatting, linting, and analysis without requiring a full
compiler front end.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    COMMENT = auto()
    STRING = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    KEYWORD = auto()
    OPERATOR = auto()
    PUNCTUATION = auto()
    NEWLINE = auto()
    INDENT = auto()
    ANNOTATION = auto()  # //@version=5
    WHITESPACE = auto()
    EOF = auto()


KEYWORDS = {
    "if",
    "else",
    "for",
    "to",
    "while",
    "switch",
    "var",
    "varip",
    "import",
    "export",
    "method",
    "type",
    "true",
    "false",
    "na",
    "and",
    "or",
    "not",
    "in",
    "by",
    "continue",
    "break",
    "return",
    "series",
    "simple",
    "const",
    "input",
    "float",
    "int",
    "bool",
    "string",
    "color",
    "line",
    "label",
    "box",
    "table",
    "array",
    "matrix",
    "map",
}

OPERATORS = sorted(
    [
        "=>",
        "==",
        "!=",
        "<=",
        ">=",
        ":=",
        "?",
        ":",
        "+",
        "-",
        "*",
        "/",
        "%",
        "=",
        "<",
        ">",
        "and",
        "or",
        "not",
        "[",
        "]",
        "(",
        ")",
        ",",
        ".",
    ],
    key=len,
    reverse=True,
)

TOKEN_REGEX = re.compile(
    r"""
    (?P<ANNOTATION>//\s*@[a-zA-Z_]+.*)
  | (?P<COMMENT>//[^\n]*)
  | (?P<STRING>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
  | (?P<NUMBER>\b\d+\.\d+(?:[eE][+-]?\d+)?\b|\b\d+(?:[eE][+-]?\d+)?\b|\.\d+\b)
  | (?P<IDENTIFIER>[A-Za-z_][A-Za-z0-9_.]*)
  | (?P<OP>=>|==|!=|<=|>=|:=|\?|::|[+\-*/%=<>:,.\[\]\(\)])
  | (?P<NEWLINE>\n)
  | (?P<WS>[ \t]+)
    """,
    re.VERBOSE,
)


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int


def tokenize(source: str) -> list[Token]:
    """Tokenize Pine Script source into a flat list of tokens.

    Newlines and leading whitespace are preserved as tokens so that the
    formatter can reconstruct layout faithfully; consumers that only care
    about semantics (linter, analyzer) can filter them out.
    """
    tokens: list[Token] = []
    line_no = 1
    line_start = 0
    pos = 0
    length = len(source)

    while pos < length:
        match = TOKEN_REGEX.match(source, pos)
        if not match:
            # Unknown character: emit as punctuation and advance.
            ch = source[pos]
            tokens.append(Token(TokenType.PUNCTUATION, ch, line_no, pos - line_start))
            pos += 1
            continue

        col = match.start() - line_start
        kind = match.lastgroup
        value = match.group()

        if kind == "ANNOTATION":
            tokens.append(Token(TokenType.ANNOTATION, value, line_no, col))
        elif kind == "COMMENT":
            tokens.append(Token(TokenType.COMMENT, value, line_no, col))
        elif kind == "STRING":
            tokens.append(Token(TokenType.STRING, value, line_no, col))
        elif kind == "NUMBER":
            tokens.append(Token(TokenType.NUMBER, value, line_no, col))
        elif kind == "IDENTIFIER":
            ttype = TokenType.KEYWORD if value in KEYWORDS else TokenType.IDENTIFIER
            tokens.append(Token(ttype, value, line_no, col))
        elif kind == "OP":
            tokens.append(Token(TokenType.OPERATOR, value, line_no, col))
        elif kind == "NEWLINE":
            tokens.append(Token(TokenType.NEWLINE, value, line_no, col))
            line_no += 1
            line_start = match.end()
        elif kind == "WS":
            tokens.append(Token(TokenType.WHITESPACE, value, line_no, col))

        pos = match.end()

    tokens.append(Token(TokenType.EOF, "", line_no, pos - line_start))
    return tokens
