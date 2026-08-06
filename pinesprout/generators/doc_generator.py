"""Generate HTML or Markdown documentation for a Pine Script file."""

from __future__ import annotations

import html
from enum import Enum

from pinesprout.core.analyzer import analyze
from pinesprout.core.explainer import explain_script_summary
from pinesprout.generators.jinja_env import build_env
from pinesprout.generators.readme_generator import _guess_inputs


class DocFormat(str, Enum):
    HTML = "html"
    MARKDOWN = "markdown"


def generate_docs(
    source: str,
    fmt: DocFormat = DocFormat.MARKDOWN,
    source_filename: str = "script.pine",
    description: str | None = None,
) -> str:
    report = analyze(source, file=source_filename)
    summary = explain_script_summary(source)
    script_type = (
        "Strategy" if report.script_kind.is_strategy else "Library" if report.script_kind.is_library else "Indicator"
    )

    env = build_env(autoescape_html=(fmt == DocFormat.HTML))
    template_name = "doc.html.j2" if fmt == DocFormat.HTML else "doc.md.j2"
    template = env.get_template(template_name)

    context = dict(
        title=report.script_kind.title or source_filename,
        description=description or f"A Pine Script v{report.pine_version} {script_type.lower()}.",
        pine_version=report.pine_version or "?",
        script_type=script_type,
        overlay=report.script_kind.overlay,
        summary=summary,
        inputs=_guess_inputs(report),
        line_count=report.line_count,
        variable_count=report.variable_count,
        function_count=report.function_count,
        plot_count=report.plot_count,
        complexity_score=report.complexity_score,
        warnings=report.warnings,
    )
    if fmt == DocFormat.HTML:
        context["source_escaped"] = html.escape(source)

    rendered = template.render(**context)
    return rendered.strip("\n") + "\n"
