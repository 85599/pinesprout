"""PineSprout command-line interface.

Run ``pinesprout --help`` (or ``pf --help``) for full usage. Every command
supports ``--json`` for machine-readable output suitable for CI pipelines
and editor integrations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from pinesprout import __version__
from pinesprout.core.analyzer import analyze
from pinesprout.core.explainer import explain_script_summary, explain_source
from pinesprout.core.formatter import FormatOptions, format_source
from pinesprout.core.linter import LintResult, Severity, lint_source
from pinesprout.core.optimizer import optimize_source
from pinesprout.core.upgrader import upgrade_source
from pinesprout.db.database import Database
from pinesprout.generators.ai_generator import GenerationError, GenerationRequest, generate_pine_script
from pinesprout.generators.doc_generator import DocFormat, generate_docs
from pinesprout.generators.readme_generator import generate_readme
from pinesprout.generators.report_generator import generate_report
from pinesprout.generators.template_generator import (
    TemplateKind,
    TemplateSpec,
    available_templates,
    generate_from_template,
)
from pinesprout.plugins.loader import load_plugins
from pinesprout.utils.console import console, error_console
from pinesprout.utils.file_utils import read_text, resolve_pine_files, write_text
from pinesprout.utils.json_output import print_json


class _FormatFileResult(BaseModel):
    file: str
    changed: bool
    formatted: str


app = typer.Typer(
    name="pinesprout",
    help="A production-grade toolkit for TradingView Pine Script developers.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"pinesprout {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show the PineSprout version and exit.",
    ),
) -> None:
    """PineSprout: generate, format, lint, analyze, and document Pine Script."""


def _db() -> Database:
    return Database()


def _load_source(file: Path) -> str:
    if not file.exists():
        error_console.print(f"[pf.error]File not found:[/pf.error] {file}")
        raise typer.Exit(code=1)
    return read_text(file)


def _severity_style(sev: Severity) -> str:
    return {
        Severity.ERROR: "pf.error",
        Severity.WARNING: "pf.warning",
        Severity.INFO: "pf.info",
    }[sev]


# --------------------------------------------------------------------------
# format
# --------------------------------------------------------------------------
@app.command()
def format(
    file: Path = typer.Argument(..., exists=True, help="Pine Script file (or directory) to format."),
    write: bool = typer.Option(False, "--write", "-w", help="Write formatted output back to the file(s)."),
    indent_size: int = typer.Option(4, help="Spaces per indent level."),
    diff: bool = typer.Option(False, help="Print a unified diff instead of the full formatted source."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Format Pine Script source code."""
    files = resolve_pine_files(file)
    if not files:
        files = [file]

    results: list[_FormatFileResult] = []
    for f in files:
        source = _load_source(f)
        formatted = format_source(source, FormatOptions(indent_size=indent_size))
        changed = formatted != source
        results.append(_FormatFileResult(file=str(f), changed=changed, formatted=formatted))

        if write and changed:
            write_text(f, formatted)

    if json_output:
        print_json(results if len(results) > 1 else results[0])
        return

    for r in results:
        if diff:
            import difflib

            original = _load_source(Path(r.file))
            diff_lines = list(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    r.formatted.splitlines(keepends=True),
                    fromfile=f"{r.file} (original)",
                    tofile=f"{r.file} (formatted)",
                )
            )
            if diff_lines:
                console.print("".join(diff_lines))
            else:
                console.print(f"[pf.success]{r.file}: already formatted[/pf.success]")
        elif write:
            status = "reformatted" if r.changed else "unchanged"
            console.print(f"[pf.success]{r.file}: {status}[/pf.success]")
        else:
            console.print(Syntax(r.formatted, "javascript", theme="ansi_dark", line_numbers=True))

    _db().record_run("format", target=str(file), summary=f"{len(files)} file(s) processed")


# --------------------------------------------------------------------------
# lint
# --------------------------------------------------------------------------
@app.command()
def lint(
    file: Path = typer.Argument(..., exists=True, help="Pine Script file (or directory) to lint."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    fail_on_warning: bool = typer.Option(False, help="Exit non-zero if any warnings are found."),
) -> None:
    """Lint Pine Script for unused vars, repaint risk, deprecated syntax, and performance issues."""
    files = resolve_pine_files(file) or [file]
    results: list[LintResult] = []
    loaded_plugins = load_plugins()

    for f in files:
        source = _load_source(f)
        result = lint_source(source, file=str(f))
        for lp in loaded_plugins:
            for rule in lp.plugin.lint_rules():
                try:
                    result.issues.extend(rule.check(source))
                except Exception as exc:  # pragma: no cover - defensive
                    error_console.print(f"[pf.warning]Plugin rule '{rule.name}' failed: {exc}[/pf.warning]")
        result.issues.sort(key=lambda i: (i.line, i.column))
        results.append(result)

    if json_output:
        print_json(results if len(results) > 1 else results[0])
    else:
        for result in results:
            console.rule(f"[pf.accent]{result.file}")
            if not result.issues:
                console.print("[pf.success]No issues found.[/pf.success]")
                continue
            table = Table(show_header=True, header_style="bold")
            table.add_column("Line", justify="right", width=6)
            table.add_column("Severity", width=10)
            table.add_column("Category", width=18)
            table.add_column("Message")
            for issue in result.issues:
                table.add_row(
                    str(issue.line),
                    f"[{_severity_style(issue.severity)}]{issue.severity.value}[/{_severity_style(issue.severity)}]",
                    issue.category.value,
                    issue.message + (f"\n[pf.muted]→ {issue.suggestion}[/pf.muted]" if issue.suggestion else ""),
                )
            console.print(table)
            console.print(
                f"[pf.error]{result.error_count} error(s)[/pf.error], "
                f"[pf.warning]{result.warning_count} warning(s)[/pf.warning], "
                f"[pf.info]{result.info_count} info[/pf.info]"
            )

    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)
    _db().record_run("lint", target=str(file), summary=f"{total_errors} errors, {total_warnings} warnings")

    if total_errors > 0 or (fail_on_warning and total_warnings > 0):
        raise typer.Exit(code=1)


# --------------------------------------------------------------------------
# analyze
# --------------------------------------------------------------------------
def analyze_cmd(
    file: Path = typer.Argument(..., exists=True, help="Pine Script file to analyze."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Analyze an indicator or strategy's structure and complexity."""
    source = _load_source(file)
    report = analyze(source, file=str(file))

    if json_output:
        print_json(report)
        return

    kind = (
        "Strategy" if report.script_kind.is_strategy else ("Library" if report.script_kind.is_library else "Indicator")
    )
    console.print(
        Panel.fit(
            f"[bold]{report.script_kind.title or file.name}[/bold]\n"
            f"Type: {kind}  ·  Pine v{report.pine_version}  ·  Complexity: {report.complexity_score}",
            title="PineSprout Analysis",
        )
    )

    table = Table(show_header=False)
    table.add_row(
        "Lines (code / comment / blank)",
        f"{report.code_line_count} / {report.comment_line_count} / {report.blank_line_count}",
    )
    table.add_row("Variables", str(report.variable_count))
    table.add_row("Functions", str(report.function_count))
    table.add_row("Inputs", str(report.input_count))
    table.add_row("Plots", str(report.plot_count))
    table.add_row("Alerts", str(report.alert_count))
    table.add_row("Strategy entries", str(report.strategy_entry_count))
    table.add_row("Max nesting depth", str(report.max_nesting_depth))
    table.add_row("Uses request.security", str(report.uses_security))
    console.print(table)

    if report.warnings:
        console.print(Panel("\n".join(f"• {w}" for w in report.warnings), title="Warnings", border_style="yellow"))

    _db().record_run("analyze", target=str(file), summary=f"complexity={report.complexity_score}")


app.command(name="analyze")(analyze_cmd)


# --------------------------------------------------------------------------
# optimize
# --------------------------------------------------------------------------
@app.command()
def optimize(
    file: Path = typer.Argument(..., exists=True, help="Pine Script file to optimize."),
    apply: bool = typer.Option(False, "--apply", help="Apply auto-fixable transformations in place."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Suggest (and optionally apply) performance and readability refactors."""
    source = _load_source(file)
    result = optimize_source(source, file=str(file), apply_fixes=apply)

    if json_output:
        print_json(result)
    else:
        if not result.suggestions:
            console.print("[pf.success]No optimization suggestions — looks clean![/pf.success]")
        for s in result.suggestions:
            console.print(
                Panel(
                    f"{s.detail}"
                    + (
                        f"\n\n[pf.muted]Before:[/pf.muted] {s.before}\n[pf.muted]After:[/pf.muted] {s.after}"
                        if s.before
                        else ""
                    ),
                    title=f"Line {s.line}: {s.title}",
                    border_style="magenta",
                )
            )

    if apply and result.optimized_source:
        write_text(file, result.optimized_source)
        console.print(f"[pf.success]Applied fixes to {file}[/pf.success]")

    _db().record_run("optimize", target=str(file), summary=f"{len(result.suggestions)} suggestion(s)")


# --------------------------------------------------------------------------
# explain
# --------------------------------------------------------------------------
@app.command()
def explain(
    file: Path = typer.Argument(..., exists=True, help="Pine Script file to explain."),
    summary_only: bool = typer.Option(False, "--summary", help="Print only the high-level summary."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Explain Pine Script line-by-line in plain English."""
    source = _load_source(file)
    summary = explain_script_summary(source)

    if summary_only:
        if json_output:
            print_json({"summary": summary})
        else:
            console.print(Panel(summary, title="Summary"))
        return

    explanations = explain_source(source)

    if json_output:
        print_json({"summary": summary, "lines": explanations})
        return

    console.print(Panel(summary, title="Summary"))
    table = Table(show_header=True, header_style="bold")
    table.add_column("Line", justify="right", width=6)
    table.add_column("Code")
    table.add_column("Explanation")
    for e in explanations:
        table.add_row(str(e.line), e.code, e.explanation)
    console.print(table)

    _db().record_run("explain", target=str(file))


# --------------------------------------------------------------------------
# upgrade
# --------------------------------------------------------------------------
@app.command()
def upgrade(
    file: Path = typer.Argument(..., exists=True, help="Pine Script file to upgrade."),
    to: int = typer.Option(6, "--to", help="Target Pine version (5 or 6)."),
    write: bool = typer.Option(False, "--write", "-w", help="Write the upgraded source back to the file."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Upgrade Pine Script source across versions (v4 -> v5 -> v6)."""
    source = _load_source(file)
    result = upgrade_source(source, target_version=to, file=str(file))

    if json_output:
        print_json(result)
    else:
        console.print(
            f"Detected version: [bold]{result.original_version or 'unknown (<=v4)'}[/bold] -> "
            f"Target: [bold]{result.target_version}[/bold] -> Final: [bold]{result.final_version}[/bold]"
        )
        if result.applied_migrations:
            table = Table(title="Applied Migrations")
            table.add_column("Change")
            table.add_column("From")
            table.add_column("To")
            table.add_column("Occurrences", justify="right")
            for m in result.applied_migrations:
                table.add_row(m.description, str(m.from_version), str(m.to_version), str(m.occurrences))
            console.print(table)
        else:
            console.print("[pf.muted]No automatic migrations were necessary.[/pf.muted]")

        if result.manual_review_needed:
            console.print(
                Panel(
                    "\n".join(f"• {m}" for m in result.manual_review_needed),
                    title="Manual Review Recommended",
                    border_style="yellow",
                )
            )

        console.print(Syntax(result.upgraded_source, "javascript", theme="ansi_dark", line_numbers=True))

    if write:
        write_text(file, result.upgraded_source)
        console.print(f"[pf.success]Wrote upgraded source to {file}[/pf.success]")

    _db().record_run("upgrade", target=str(file), summary=f"v{result.original_version}->v{result.final_version}")


# --------------------------------------------------------------------------
# generate (AI)
# --------------------------------------------------------------------------
@app.command()
def generate(
    prompt: str = typer.Argument(..., help="Natural-language description of the indicator/strategy to build."),
    script_type: str = typer.Option("indicator", "--type", help="indicator | strategy | library"),
    pine_version: int = typer.Option(6, "--pine-version"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write generated source to this file."),
    api_key: str | None = typer.Option(None, "--api-key", help="Anthropic API key (overrides ANTHROPIC_API_KEY)."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Generate Pine Script from a natural-language prompt using Claude."""
    request = GenerationRequest(prompt=prompt, script_type=script_type, pine_version=pine_version)
    try:
        with console.status("[pf.accent]Generating Pine Script..."):
            result = generate_pine_script(request, api_key=api_key)
    except GenerationError as exc:
        error_console.print(f"[pf.error]{exc}[/pf.error]")
        raise typer.Exit(code=1) from exc

    if json_output:
        print_json(result)
    else:
        console.print(Syntax(result.source, "javascript", theme="ansi_dark", line_numbers=True))
        if result.lint_issues:
            console.print(
                f"[pf.warning]{len(result.lint_issues)} lint issue(s) found in generated code — "
                f"run `pinesprout lint` for details.[/pf.warning]"
            )

    if output:
        write_text(output, result.source)
        console.print(f"[pf.success]Saved to {output}[/pf.success]")

    _db().record_run("generate", target=str(output) if output else None, summary=prompt[:120])


# --------------------------------------------------------------------------
# template
# --------------------------------------------------------------------------
template_app = typer.Typer(help="Generate indicator/strategy scaffolds from built-in templates.")
app.add_typer(template_app, name="template")


@template_app.command("list")
def template_list(json_output: bool = typer.Option(False, "--json")) -> None:
    """List available templates."""
    templates = available_templates()
    if json_output:
        print_json({"templates": templates})
    else:
        for t in templates:
            console.print(f"  • {t}")


@template_app.command("new")
def template_new(
    kind: str = typer.Argument(..., help=f"Template kind. One of: {', '.join(available_templates())}"),
    title: str = typer.Option("My Script", "--title"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    overlay: bool = typer.Option(True, "--overlay/--no-overlay"),
    pine_version: int = typer.Option(6, "--pine-version"),
) -> None:
    """Scaffold a new indicator or strategy from a built-in template."""
    try:
        template_kind = TemplateKind(kind)
    except ValueError:
        error_console.print(
            f"[pf.error]Unknown template '{kind}'. Choices: {', '.join(available_templates())}[/pf.error]"
        )
        raise typer.Exit(code=1) from None

    spec = TemplateSpec(kind=template_kind, title=title, overlay=overlay, pine_version=pine_version)
    source = generate_from_template(spec)

    if output:
        write_text(output, source)
        console.print(f"[pf.success]Wrote {output}[/pf.success]")
    else:
        console.print(Syntax(source, "javascript", theme="ansi_dark", line_numbers=True))

    _db().record_run("template", target=str(output) if output else kind, summary=kind)


# --------------------------------------------------------------------------
# docs / readme / report
# --------------------------------------------------------------------------
@app.command()
def readme(
    file: Path = typer.Argument(..., exists=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Generate a README.md for a Pine Script file."""
    source = _load_source(file)
    content = generate_readme(source, source_filename=file.name, description=description)
    if output:
        write_text(output, content)
        console.print(f"[pf.success]Wrote {output}[/pf.success]")
    else:
        console.print(content)
    _db().record_run("readme", target=str(file))


@app.command()
def docs(
    file: Path = typer.Argument(..., exists=True),
    fmt: str = typer.Option("markdown", "--format", help="markdown | html"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate HTML or Markdown documentation for a Pine Script file."""
    source = _load_source(file)
    doc_format = DocFormat.HTML if fmt.lower() == "html" else DocFormat.MARKDOWN
    content = generate_docs(source, fmt=doc_format, source_filename=file.name)
    if output:
        write_text(output, content)
        console.print(f"[pf.success]Wrote {output}[/pf.success]")
    else:
        console.print(content)
    _db().record_run("docs", target=str(file), summary=fmt)


@app.command()
def report(
    file: Path = typer.Argument(..., exists=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate a comprehensive strategy/indicator analysis report (Markdown)."""
    source = _load_source(file)
    content = generate_report(source, file=file.name)
    if output:
        write_text(output, content)
        console.print(f"[pf.success]Wrote {output}[/pf.success]")
    else:
        console.print(content)
    _db().record_run("report", target=str(file))


# --------------------------------------------------------------------------
# history / plugins
# --------------------------------------------------------------------------
@app.command()
def history(
    limit: int = typer.Option(20, "--limit"),
    command: str | None = typer.Option(None, "--command"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show recent PineSprout command history."""
    runs = _db().recent_runs(limit=limit, command=command)
    if json_output:
        print_json([r.__dict__ for r in runs])
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", width=5)
    table.add_column("Command", width=12)
    table.add_column("Target")
    table.add_column("Summary")
    table.add_column("When")
    for r in runs:
        table.add_row(str(r.id), r.command, r.target or "-", r.summary or "-", r.created_at)
    console.print(table)


plugins_app = typer.Typer(help="Manage PineSprout plugins.")
app.add_typer(plugins_app, name="plugins")


@plugins_app.command("list")
def plugins_list(json_output: bool = typer.Option(False, "--json")) -> None:
    """List currently discoverable/loaded plugins."""
    loaded = load_plugins()
    if json_output:
        print_json([{"name": lp.plugin.name, "version": lp.plugin.version, "source": lp.source} for lp in loaded])
        return
    if not loaded:
        console.print("[pf.muted]No plugins found.[/pf.muted]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Source")
    for lp in loaded:
        table.add_row(lp.plugin.name, lp.plugin.version, lp.source)
    console.print(table)


def run() -> None:
    """Entry point used by the console_scripts / packaging config."""
    try:
        app()
    except Exception as exc:  # pragma: no cover - top-level safety net
        error_console.print(f"[pf.error]Unexpected error:[/pf.error] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app()
