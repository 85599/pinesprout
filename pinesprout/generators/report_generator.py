"""Generate a comprehensive Markdown analysis report combining analyzer,
linter, and optimizer output."""

from __future__ import annotations

from datetime import UTC, datetime

from pinesprout.core.analyzer import analyze
from pinesprout.core.linter import Linter
from pinesprout.core.optimizer import optimize_source
from pinesprout.generators.jinja_env import build_env


def generate_report(source: str, file: str = "script.pine") -> str:
    report = analyze(source, file=file)
    lint_issues = Linter.from_source(source).run()
    optimization = optimize_source(source, file=file)

    script_type = (
        "Strategy" if report.script_kind.is_strategy else "Library" if report.script_kind.is_library else "Indicator"
    )

    env = build_env()
    template = env.get_template("report.md.j2")
    rendered = template.render(
        file=file,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        pine_version=report.pine_version or "?",
        script_type=script_type,
        line_count=report.line_count,
        code_line_count=report.code_line_count,
        comment_line_count=report.comment_line_count,
        blank_line_count=report.blank_line_count,
        variable_count=report.variable_count,
        function_count=report.function_count,
        max_nesting_depth=report.max_nesting_depth,
        complexity_score=report.complexity_score,
        input_count=report.input_count,
        inputs_by_type=report.inputs_by_type,
        plot_count=report.plot_count,
        alert_count=report.alert_count,
        strategy_entry_count=report.strategy_entry_count,
        uses_security=report.uses_security,
        uses_arrays=report.uses_arrays,
        uses_matrices=report.uses_matrices,
        uses_maps=report.uses_maps,
        ta_function_calls=report.ta_function_calls,
        lint_errors=sum(1 for i in lint_issues if i.severity.value == "error"),
        lint_warnings=sum(1 for i in lint_issues if i.severity.value == "warning"),
        lint_info=sum(1 for i in lint_issues if i.severity.value == "info"),
        lint_issues=[i.model_dump() for i in lint_issues],
        optimization_suggestions=[s.model_dump() for s in optimization.suggestions],
        warnings=report.warnings,
    )
    return rendered.strip("\n") + "\n"
