"""Structural and complexity analysis for Pine Script indicators/strategies."""

from __future__ import annotations

import re

from pydantic import BaseModel

from pinesprout.core.ast_nodes import NodeKind, ParsedProgram
from pinesprout.core.parser import parse

_INPUT_TYPE_RE = re.compile(r"input\.([a-z]+)\s*\(")
_STRATEGY_ENTRY_RE = re.compile(r"\bstrategy\.(entry|order|close|close_all|exit)\s*\(")
_PLOT_RE = re.compile(r"\bplot(?:shape|char|arrow|candle|bar)?\s*\(")
_ALERT_RE = re.compile(r"\balert(?:condition)?\s*\(")
_TA_CALL_RE = re.compile(r"\bta\.[a-zA-Z_]+\s*\(")


class ScriptKind(BaseModel):
    is_indicator: bool = False
    is_strategy: bool = False
    is_library: bool = False
    overlay: bool | None = None
    title: str | None = None
    shorttitle: str | None = None


class AnalysisReport(BaseModel):
    file: str
    pine_version: int | None
    script_kind: ScriptKind
    line_count: int
    code_line_count: int
    comment_line_count: int
    blank_line_count: int
    variable_count: int
    function_count: int
    input_count: int
    inputs_by_type: dict[str, int]
    plot_count: int
    alert_count: int
    ta_function_calls: dict[str, int]
    strategy_entry_count: int
    max_nesting_depth: int
    complexity_score: float
    uses_security: bool
    uses_arrays: bool
    uses_matrices: bool
    uses_maps: bool
    uses_libraries: list[str]
    warnings: list[str]


_FIRST_STRING_ARG_RE = re.compile(r"\(\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')")


def _extract_decl_arg(decl_text: str, arg_name: str) -> str | None:
    pattern = re.compile(arg_name + r"\s*=\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|true|false)")
    m = pattern.search(decl_text)
    if m:
        return m.group(1).strip("'\"")
    if arg_name == "title":
        # `indicator("My Title", ...)` / `study("My Title")`: title is often
        # the first positional (unnamed) argument.
        m = _FIRST_STRING_ARG_RE.search(decl_text)
        if m:
            return m.group(1).strip("'\"")
    return None


def analyze(source: str, file: str = "<memory>") -> AnalysisReport:
    program: ParsedProgram = parse(source)
    lines = program.source_lines

    code_lines = [ln for ln in lines if ln.strip() and not ln.strip().startswith("//")]
    comment_lines = [ln for ln in lines if ln.strip().startswith("//")]
    blank_lines = [ln for ln in lines if not ln.strip()]

    kind = ScriptKind()
    for decl in program.declarations:
        if decl.kind == NodeKind.INDICATOR_DECL:
            kind.is_indicator = True
            text = str(decl.meta.get("call", decl.text))
            kind.title = _extract_decl_arg(text, "title")
            kind.shorttitle = _extract_decl_arg(text, "shorttitle")
            overlay_raw = _extract_decl_arg(text, "overlay")
            kind.overlay = overlay_raw == "true" if overlay_raw else None
        elif decl.kind == NodeKind.STRATEGY_DECL:
            kind.is_strategy = True
            text = str(decl.meta.get("call", decl.text))
            kind.title = _extract_decl_arg(text, "title")
        elif decl.kind == NodeKind.LIBRARY_DECL:
            kind.is_library = True

    inputs_by_type: dict[str, int] = {}
    for m in _INPUT_TYPE_RE.finditer(source):
        inputs_by_type[m.group(1)] = inputs_by_type.get(m.group(1), 0) + 1
    generic_inputs = len(re.findall(r"\binput\s*\(", source))
    if generic_inputs:
        inputs_by_type["generic"] = inputs_by_type.get("generic", 0) + generic_inputs

    ta_calls: dict[str, int] = {}
    for m in _TA_CALL_RE.finditer(source):
        name = m.group().split("(")[0]
        ta_calls[name] = ta_calls.get(name, 0) + 1

    max_depth = 0
    for node in program.root.children:
        indent = int(node.meta.get("indent", 0)) if node.meta else 0  # type: ignore[call-overload]
        depth = indent // 4 if indent else 0
        max_depth = max(max_depth, depth)

    function_count = sum(1 for d in program.declarations if d.kind == NodeKind.FUNCTION_DECL)
    variable_count = sum(1 for v in program.variable_assignments if v.kind == NodeKind.VARIABLE_DECL)
    plot_count = len(_PLOT_RE.findall(source))
    alert_count = len(_ALERT_RE.findall(source))
    strategy_entries = len(_STRATEGY_ENTRY_RE.findall(source))

    branching = len(re.findall(r"^\s*if\b", source, re.MULTILINE))
    loops = len(re.findall(r"^\s*(for|while)\b", source, re.MULTILINE))
    complexity_score = round(
        1.0
        + 0.15 * branching
        + 0.25 * loops
        + 0.05 * len(code_lines) / max(1, 10)
        + 0.3 * max_depth,
        2,
    )

    libraries = re.findall(r'import\s+([A-Za-z0-9_/]+)', source)

    warnings: list[str] = []
    if not kind.is_indicator and not kind.is_strategy and not kind.is_library:
        warnings.append("Could not determine script type (missing indicator/strategy/library declaration).")
    if kind.is_strategy and strategy_entries == 0:
        warnings.append("Strategy declared but no `strategy.entry/order` calls were found.")
    if plot_count == 0 and kind.is_indicator:
        warnings.append("Indicator has no `plot()`-family calls; nothing will be drawn on the chart.")
    if max_depth >= 4:
        warnings.append(f"Deep nesting detected (depth {max_depth}); consider extracting functions.")

    return AnalysisReport(
        file=file,
        pine_version=program.pine_version,
        script_kind=kind,
        line_count=len(lines),
        code_line_count=len(code_lines),
        comment_line_count=len(comment_lines),
        blank_line_count=len(blank_lines),
        variable_count=variable_count,
        function_count=function_count,
        input_count=sum(inputs_by_type.values()),
        inputs_by_type=inputs_by_type,
        plot_count=plot_count,
        alert_count=alert_count,
        ta_function_calls=ta_calls,
        strategy_entry_count=strategy_entries,
        max_nesting_depth=max_depth,
        complexity_score=complexity_score,
        uses_security="request.security(" in source or "security(" in source,
        uses_arrays="array.new" in source or re.search(r"\barray<", source) is not None,
        uses_matrices="matrix.new" in source or re.search(r"\bmatrix<", source) is not None,
        uses_maps="map.new" in source or re.search(r"\bmap<", source) is not None,
        uses_libraries=libraries,
        warnings=warnings,
    )
