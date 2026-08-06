"""Generate a README.md for a Pine Script file from its static analysis."""

from __future__ import annotations

from pinesprout.core.analyzer import AnalysisReport, analyze
from pinesprout.core.explainer import explain_script_summary
from pinesprout.generators.jinja_env import build_env
from pinesprout.generators.template_generator import InputSpec


def _guess_inputs(report: AnalysisReport) -> list[InputSpec]:
    specs: list[InputSpec] = []
    for type_name, count in report.inputs_by_type.items():
        specs.append(
            InputSpec(
                name=f"({count} input{'s' if count != 1 else ''} of this type)",
                type=type_name,
                default="—",
                label="See source for exact parameters",
            )
        )
    return specs


def generate_readme(
    source: str,
    source_filename: str = "script.pine",
    description: str | None = None,
    license_name: str = "MIT",
) -> str:
    report = analyze(source, file=source_filename)
    summary = explain_script_summary(source)

    script_type = (
        "Strategy" if report.script_kind.is_strategy else "Library" if report.script_kind.is_library else "Indicator"
    )

    env = build_env()
    template = env.get_template("readme.md.j2")
    rendered = template.render(
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
        source_filename=source_filename,
        license=license_name,
    )
    return rendered.strip("\n") + "\n"
