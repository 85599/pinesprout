"""Lightweight AST node definitions produced by the PineSprout parser.

PineSprout ships its own hand-written lexer/parser (see ``lexer.py`` and
``parser.py``) rather than depending on an external Pine Script grammar,
since no official tree-sitter or ANTLR grammar for Pine Script is
maintained by TradingView. The design intentionally mirrors the shape of
a tree-sitter concrete syntax tree (typed nodes, byte/line spans, a
``children`` list) so that a real grammar can be swapped in later
without changing any downstream consumer (formatter, linter, analyzer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class NodeKind(Enum):
    SOURCE = auto()
    VERSION_ANNOTATION = auto()
    COMMENT = auto()
    IMPORT_STATEMENT = auto()
    INDICATOR_DECL = auto()
    STRATEGY_DECL = auto()
    LIBRARY_DECL = auto()
    VARIABLE_DECL = auto()
    VARIABLE_REASSIGN = auto()
    FUNCTION_DECL = auto()
    FUNCTION_CALL = auto()
    IF_STATEMENT = auto()
    FOR_STATEMENT = auto()
    WHILE_STATEMENT = auto()
    SWITCH_STATEMENT = auto()
    PLOT_STATEMENT = auto()
    INPUT_STATEMENT = auto()
    EXPRESSION_STATEMENT = auto()
    BLOCK = auto()
    RAW_LINE = auto()


@dataclass
class Position:
    line: int
    column: int


@dataclass
class Node:
    kind: NodeKind
    text: str
    start: Position
    end: Position
    children: list[Node] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<{self.kind.name} {self.start.line}:{self.start.column} {self.text[:30]!r}>"


@dataclass
class ParsedProgram:
    """Result of parsing a Pine Script source file."""

    root: Node
    source_lines: list[str]
    pine_version: int | None
    declarations: list[Node]
    variable_assignments: list[Node]
    function_calls: list[Node]
    comments: list[Node]
    raw_source: str

    def line(self, number: int) -> str:
        """Return the 1-indexed source line text."""
        if 1 <= number <= len(self.source_lines):
            return self.source_lines[number - 1]
        return ""
