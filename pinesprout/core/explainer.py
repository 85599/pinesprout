"""Line-by-line plain-English explanations of Pine Script code.

Explanations are generated from the parsed AST using pattern-based rules
covering the vast majority of everyday Pine Script constructs. When an
Anthropic API key is configured (see ``pinesprout.generators.ai_generator``),
callers may optionally enrich explanations with model-generated prose for
lines the heuristic engine can't confidently classify; that enrichment is
handled by the CLI layer, not here, keeping this module fast and offline.
"""

from __future__ import annotations

from pydantic import BaseModel

from pinesprout.core.ast_nodes import Node, NodeKind, ParsedProgram
from pinesprout.core.parser import parse


class LineExplanation(BaseModel):
    line: int
    code: str
    explanation: str
    node_kind: str


def _explain_node(node: Node) -> str:
    kind = node.kind
    meta = node.meta

    if kind == NodeKind.VERSION_ANNOTATION:
        return "Declares which Pine Script compiler version this file targets."
    if kind == NodeKind.COMMENT:
        return "A comment; ignored by the compiler."
    if kind == NodeKind.INDICATOR_DECL:
        return "Declares this script as an indicator (overlay/pane study) and sets its display metadata."
    if kind == NodeKind.STRATEGY_DECL:
        return "Declares this script as a strategy, enabling backtesting and order-placement functions."
    if kind == NodeKind.LIBRARY_DECL:
        return "Declares this script as a reusable library that other scripts can import."
    if kind == NodeKind.IMPORT_STATEMENT:
        module = meta.get("module", "")
        return f"Imports the external library `{module}` for reuse in this script."
    if kind == NodeKind.FUNCTION_DECL:
        name = meta.get("name", "")
        params = meta.get("params", []) or []
        param_str = ", ".join(str(p) for p in params) if params else "no parameters"  # type: ignore[attr-defined]
        return f"Defines a function `{name}` taking {param_str}."
    if kind == NodeKind.IF_STATEMENT:
        cond = meta.get("condition", "")
        return f"Branches based on the condition `{cond}`."
    if kind == NodeKind.FOR_STATEMENT:
        var = meta.get("var", "")
        frm = meta.get("from", "")
        to = meta.get("to", "")
        return f"Loops variable `{var}` from `{frm}` to `{to}`."
    if kind == NodeKind.WHILE_STATEMENT:
        cond = meta.get("condition", "")
        return f"Repeats while the condition `{cond}` holds true."
    if kind == NodeKind.SWITCH_STATEMENT:
        subject = meta.get("subject", "")
        return f"Starts a `switch` over `{subject}`, choosing a branch by matching value."
    if kind == NodeKind.PLOT_STATEMENT:
        fn = node.text.split("(")[0].strip()
        return f"Draws a `{fn}` visual element on the chart."
    if kind == NodeKind.INPUT_STATEMENT:
        return "Defines a user-configurable input shown in the script's settings dialog."
    if kind == NodeKind.VARIABLE_REASSIGN:
        name = meta.get("name", "")
        value = meta.get("value", "")
        return f"Reassigns the existing (mutable) variable `{name}` to `{value}` using `:=`."
    if kind == NodeKind.VARIABLE_DECL:
        name = meta.get("name", "")
        value = meta.get("value", "")
        persistence = "a `var`-persisted" if meta.get("is_var") else "a per-bar"
        return f"Declares {persistence} variable `{name}` initialized to `{value}`."
    if kind == NodeKind.FUNCTION_CALL:
        name = meta.get("name", "")
        return f"Calls the function `{name}`."
    if kind == NodeKind.EXPRESSION_STATEMENT:
        return "Evaluates an expression (its result may be a plotted/return value)."
    return "Executes this statement."


def explain_source(source: str) -> list[LineExplanation]:
    """Produce a plain-English explanation for every meaningful line."""
    program: ParsedProgram = parse(source)
    explanations: list[LineExplanation] = []

    for node in program.root.children:
        if node.kind == NodeKind.SOURCE:
            continue
        explanations.append(
            LineExplanation(
                line=node.start.line,
                code=program.line(node.start.line),
                explanation=_explain_node(node),
                node_kind=node.kind.name,
            )
        )

    explanations.sort(key=lambda e: e.line)
    return explanations


def explain_script_summary(source: str) -> str:
    """One-paragraph, heuristic natural-language summary of the whole script."""
    program = parse(source)
    from pinesprout.core.analyzer import analyze  # local import to avoid cycle

    report = analyze(source)
    kind = "strategy" if report.script_kind.is_strategy else (
        "library" if report.script_kind.is_library else "indicator"
    )
    title = report.script_kind.title or "Untitled"
    pieces = [
        f"This is a Pine Script v{program.pine_version or '?'} {kind} titled \"{title}\".",
        f"It defines {report.variable_count} variable(s) and {report.function_count} function(s),",
        f"reads {report.input_count} user input(s), and produces {report.plot_count} plot(s).",
    ]
    if report.strategy_entry_count:
        pieces.append(f"It places orders via {report.strategy_entry_count} strategy call(s).")
    if report.uses_security:
        pieces.append("It pulls data from another timeframe/symbol using `request.security`.")
    if report.warnings:
        pieces.append("Potential issues: " + "; ".join(report.warnings) + ".")
    return " ".join(pieces)
