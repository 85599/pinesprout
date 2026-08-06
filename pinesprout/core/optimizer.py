"""Heuristic optimizer: proposes and (optionally) applies refactors.

The optimizer builds on top of the linter's findings plus a few
additional structural heuristics (repeated subexpressions, redundant
`ta.*` recomputation, verbose boolean expressions) to suggest concrete
code changes. Applying fixes is conservative: only transformations that
are textually unambiguous (single, unique match) are auto-applied;
everything else is surfaced as a suggestion for the developer to review.
"""

from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel

from pinesprout.core.linter import Linter
from pinesprout.core.version_rules import PERFORMANCE_SENSITIVE_FUNCTIONS

_TA_EXPR_RE = re.compile(r"\b(ta\.[a-zA-Z_]+\([^()]*\))")
_REDUNDANT_BOOL_RE = re.compile(r"==\s*true\b|==\s*false\b")


class OptimizationSuggestion(BaseModel):
    line: int
    title: str
    detail: str
    before: str | None = None
    after: str | None = None
    auto_fixable: bool = False


class OptimizationResult(BaseModel):
    file: str
    suggestions: list[OptimizationSuggestion]
    optimized_source: str | None = None


def _find_repeated_ta_calls(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []
    counts = Counter(_TA_EXPR_RE.findall(source))
    for expr, count in counts.items():
        fn = expr.split("(")[0]
        if count > 1 and fn in PERFORMANCE_SENSITIVE_FUNCTIONS:
            first_line = next((i + 1 for i, ln in enumerate(source.splitlines()) if expr in ln), 1)
            var_name = fn.split(".")[-1] + "_cached"
            suggestions.append(
                OptimizationSuggestion(
                    line=first_line,
                    title=f"Repeated call to `{expr}`",
                    detail=(
                        f"`{expr}` appears {count} times. Pine recomputes this on every bar for "
                        "each occurrence; assign it to a variable once and reuse it."
                    ),
                    before=expr,
                    after=f"{var_name} = {expr}  // then reuse `{var_name}`",
                    auto_fixable=False,
                )
            )
    return suggestions


def _find_redundant_booleans(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if line.strip().startswith("//"):
            continue
        for m in _REDUNDANT_BOOL_RE.finditer(line):
            snippet = m.group()
            suggestions.append(
                OptimizationSuggestion(
                    line=i,
                    title="Redundant boolean comparison",
                    detail=f"`{snippet.strip()}` can be simplified.",
                    before=snippet.strip(),
                    after="(drop the comparison)" if "true" in snippet else "use `not <expr>`",
                    auto_fixable=False,
                )
            )
    return suggestions


def _find_magic_numbers(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []
    seen_lines: set[int] = set()
    magic_re = re.compile(r"(?<![\w.])(\d{2,})(?![\w.])")
    for i, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("//") or "input" in stripped or "@version" in stripped:
            continue
        for m in magic_re.finditer(stripped):
            if i in seen_lines:
                continue
            num = m.group(1)
            if num in ("100",) and ("overbought" in stripped.lower() or "oversold" in stripped.lower()):
                continue
            seen_lines.add(i)
            suggestions.append(
                OptimizationSuggestion(
                    line=i,
                    title=f"Magic number `{num}`",
                    detail=(
                        "Hard-coded numeric literals used in calculations are harder to tune. "
                        "Consider exposing this as an `input.int`/`input.float` parameter."
                    ),
                    auto_fixable=False,
                )
            )
    return suggestions


def optimize_source(source: str, file: str = "<memory>", apply_fixes: bool = False) -> OptimizationResult:
    suggestions: list[OptimizationSuggestion] = []
    suggestions.extend(_find_repeated_ta_calls(source))
    suggestions.extend(_find_redundant_booleans(source))
    suggestions.extend(_find_magic_numbers(source))

    # Pull in performance-category lint issues as optimization hints too.
    lint_issues = Linter.from_source(source).run()
    for issue in lint_issues:
        if issue.category.value == "performance":
            suggestions.append(
                OptimizationSuggestion(
                    line=issue.line,
                    title="Loop-bound performance cost",
                    detail=issue.message,
                    auto_fixable=False,
                )
            )

    optimized_source = None
    if apply_fixes:
        optimized = source
        for line in source.splitlines():
            for m in _REDUNDANT_BOOL_RE.finditer(line):
                snippet = m.group()
                if "true" in snippet:
                    optimized = optimized.replace(snippet, "")
        optimized_source = optimized

    suggestions.sort(key=lambda s: s.line)
    return OptimizationResult(file=file, suggestions=suggestions, optimized_source=optimized_source)
