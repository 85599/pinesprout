"""Static analysis linter for Pine Script.

Detects:
  * Unused variable declarations.
  * Repaint-prone function usage (e.g. ``request.security`` without
    ``lookahead`` guard, ``ta.valuewhen``/``ta.barssince`` in realtime
    contexts).
  * Deprecated syntax (pre-v5 global functions, ``study()``, etc.)
  * Performance concerns (heavy TA calls inside ``for``/``while`` loops).
  * Missing version pragma / declaration statement.
  * Naming and style nits.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel

from pinesprout.core.ast_nodes import NodeKind, ParsedProgram
from pinesprout.core.parser import parse
from pinesprout.core.version_rules import (
    DEPRECATED_SYMBOLS,
    PERFORMANCE_SENSITIVE_FUNCTIONS,
    REPAINT_PRONE_FUNCTIONS,
)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintCategory(str, Enum):
    UNUSED_VARIABLE = "unused-variable"
    REPAINT_RISK = "repaint-risk"
    DEPRECATED_SYNTAX = "deprecated-syntax"
    PERFORMANCE = "performance"
    STYLE = "style"
    STRUCTURE = "structure"


class LintIssue(BaseModel):
    line: int
    column: int = 0
    severity: Severity
    category: LintCategory
    message: str
    symbol: str | None = None
    suggestion: str | None = None

    def rich_severity_style(self) -> str:
        return {
            Severity.ERROR: "bold red",
            Severity.WARNING: "yellow",
            Severity.INFO: "cyan",
        }[self.severity]


class LintResult(BaseModel):
    file: str
    issues: list[LintIssue]

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.INFO)

    @property
    def passed(self) -> bool:
        return self.error_count == 0


_IDENTIFIER_USE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
_BUILTIN_PREFIXES = ("ta.", "math.", "request.", "str.", "array.", "matrix.",
                     "map.", "color.", "input.", "strategy.", "ticker.",
                     "syminfo.", "chart.", "line.", "label.", "box.", "table.",
                     "runtime.", "timeframe.", "session.", "log.")


def _is_exported_or_special(name: str) -> bool:
    return name in {"_", "close", "open", "high", "low", "volume", "time", "bar_index"}


class Linter:
    """Runs the full PineSprout rule set over a parsed program."""

    def __init__(self, program: ParsedProgram, source: str) -> None:
        self.program = program
        self.source = source
        self.issues: list[LintIssue] = []

    @classmethod
    def from_source(cls, source: str) -> Linter:
        return cls(parse(source), source)

    def run(self) -> list[LintIssue]:
        self.issues = []
        self._check_version_pragma()
        self._check_declaration_present()
        self._check_unused_variables()
        self._check_deprecated_syntax()
        self._check_repaint_risk()
        self._check_performance()
        self._check_style()
        return sorted(self.issues, key=lambda i: (i.line, i.column))

    # -- individual checks -------------------------------------------------

    def _check_version_pragma(self) -> None:
        if self.program.pine_version is None:
            self.issues.append(
                LintIssue(
                    line=1,
                    severity=Severity.ERROR,
                    category=LintCategory.STRUCTURE,
                    message="Missing `//@version=N` pragma; Pine Script compiles as v1 without it.",
                    suggestion="Add `//@version=6` as the first line of the script.",
                )
            )

    def _check_declaration_present(self) -> None:
        has_decl = any(
            n.kind in (NodeKind.INDICATOR_DECL, NodeKind.STRATEGY_DECL, NodeKind.LIBRARY_DECL)
            for n in self.program.declarations
        )
        # Legacy v4 scripts declare via `study(...)` instead of `indicator(...)`;
        # that's already flagged separately as deprecated syntax, so it counts
        # as a valid declaration here to avoid a redundant/misleading error.
        if not has_decl:
            has_decl = any(
                re.match(r"^\s*study\s*\(", line)
                for line in self.program.source_lines
            )
        if not has_decl:
            self.issues.append(
                LintIssue(
                    line=1,
                    severity=Severity.ERROR,
                    category=LintCategory.STRUCTURE,
                    message="No `indicator()`, `strategy()`, or `library()` declaration found.",
                    suggestion="Every Pine Script script/library must declare its type.",
                )
            )

    def _check_unused_variables(self) -> None:
        declared: dict[str, int] = {}
        for node in self.program.variable_assignments:
            if node.kind != NodeKind.VARIABLE_DECL:
                continue
            name = str(node.meta.get("name"))
            if _is_exported_or_special(name) or name.startswith("_"):
                continue
            declared.setdefault(name, node.start.line)

        if not declared:
            return

        full_text = self.program.raw_source
        for name, decl_line in declared.items():
            # Count occurrences of the identifier anywhere other than its
            # own declaration line's LHS.
            uses = 0
            for lineno, line in enumerate(self.program.source_lines, start=1):
                for m in _IDENTIFIER_USE_RE.finditer(line):
                    if m.group(1) != name:
                        continue
                    if lineno == decl_line:
                        # Skip the LHS occurrence itself (first match on decl line).
                        lhs_pos = line.find(name)
                        if m.start() == lhs_pos:
                            continue
                    uses += 1
            if uses == 0:
                self.issues.append(
                    LintIssue(
                        line=decl_line,
                        severity=Severity.WARNING,
                        category=LintCategory.UNUSED_VARIABLE,
                        message=f"Variable `{name}` is declared but never used.",
                        symbol=name,
                        suggestion=f"Remove `{name}` or prefix it with `_` if intentionally unused.",
                    )
                )
        del full_text

    def _check_deprecated_syntax(self) -> None:
        for lineno, line in enumerate(self.program.source_lines, start=1):
            if line.strip().startswith("//"):
                continue
            for dep in DEPRECATED_SYMBOLS:
                idx = line.find(dep.symbol)
                if idx == -1:
                    continue
                # Avoid matching e.g. "ta.rsi(" as "rsi(" via the bare form.
                if idx > 0 and (line[idx - 1].isalnum() or line[idx - 1] in "._"):
                    continue
                self.issues.append(
                    LintIssue(
                        line=lineno,
                        column=idx,
                        severity=Severity.WARNING,
                        category=LintCategory.DEPRECATED_SYNTAX,
                        message=dep.message,
                        symbol=dep.symbol.rstrip("("),
                        suggestion=f"Use `{dep.replacement}` instead.",
                    )
                )

    def _check_repaint_risk(self) -> None:
        for lineno, line in enumerate(self.program.source_lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            for fn in REPAINT_PRONE_FUNCTIONS:
                if fn + "(" not in line:
                    continue
                if fn in ("request.security", "security"):
                    if "lookahead" not in line and "barmerge.lookahead_off" not in line:
                        self.issues.append(
                            LintIssue(
                                line=lineno,
                                severity=Severity.WARNING,
                                category=LintCategory.REPAINT_RISK,
                                message=(
                                    f"`{fn}()` call without an explicit `lookahead` argument can "
                                    "repaint historical values on lower timeframes."
                                ),
                                symbol=fn,
                                suggestion=(
                                    "Pass `lookahead=barmerge.lookahead_off` explicitly, or confirm "
                                    "the repaint behavior is intentional."
                                ),
                            )
                        )
                else:
                    self.issues.append(
                        LintIssue(
                            line=lineno,
                            severity=Severity.INFO,
                            category=LintCategory.REPAINT_RISK,
                            message=f"`{fn}()` can behave differently on historical vs. realtime bars.",
                            symbol=fn,
                            suggestion="Verify behavior matches expectations on the last (realtime) bar.",
                        )
                    )

    def _check_performance(self) -> None:
        in_loop_depth = 0
        loop_indent: list[int] = []
        for node in self.program.root.children:
            indent = int(node.meta.get("indent", 0)) if node.meta else 0  # type: ignore[call-overload]

            while loop_indent and indent <= loop_indent[-1]:
                loop_indent.pop()
                in_loop_depth -= 1

            if node.kind in (NodeKind.FOR_STATEMENT, NodeKind.WHILE_STATEMENT):
                loop_indent.append(indent)
                in_loop_depth += 1
                continue

            if in_loop_depth > 0:
                for fn in PERFORMANCE_SENSITIVE_FUNCTIONS:
                    if fn + "(" in node.text:
                        self.issues.append(
                            LintIssue(
                                line=node.start.line,
                                severity=Severity.WARNING,
                                category=LintCategory.PERFORMANCE,
                                message=(
                                    f"Calling `{fn}()` inside a loop recomputes it every bar for "
                                    "every iteration; this can be a significant performance cost."
                                ),
                                symbol=fn,
                                suggestion="Hoist the call outside the loop if the inputs don't vary per-iteration.",
                            )
                        )

    def _check_style(self) -> None:
        for lineno, line in enumerate(self.program.source_lines, start=1):
            if len(line) > 120:
                self.issues.append(
                    LintIssue(
                        line=lineno,
                        severity=Severity.INFO,
                        category=LintCategory.STYLE,
                        message=f"Line exceeds 120 characters ({len(line)}).",
                        suggestion="Consider breaking the expression across multiple lines.",
                    )
                )
            if "\t" in line:
                self.issues.append(
                    LintIssue(
                        line=lineno,
                        severity=Severity.INFO,
                        category=LintCategory.STYLE,
                        message="Line uses tabs for indentation; spaces are recommended.",
                    )
                )


def lint_source(source: str, file: str = "<memory>") -> LintResult:
    linter = Linter.from_source(source)
    issues = linter.run()
    return LintResult(file=file, issues=issues)
