from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pinesprout.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PINESPROUT_DB", str(tmp_path / "cli_test.db"))
    monkeypatch.chdir(tmp_path)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "pinesprout" in result.stdout


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "PineSprout" in result.stdout or "pinesprout" in result.stdout.lower()


def test_cli_lint_clean_file(tmp_path, clean_v6_source):
    f = _write(tmp_path / "clean.pine", clean_v6_source)
    result = runner.invoke(app, ["lint", str(f)])
    assert result.exit_code == 0
    assert "No issues found" in result.stdout


def test_cli_lint_json_output(tmp_path, clean_v6_source):
    f = _write(tmp_path / "clean.pine", clean_v6_source)
    result = runner.invoke(app, ["lint", str(f), "--json"])
    assert result.exit_code == 0
    assert '"issues"' in result.stdout


def test_cli_lint_errors_exit_nonzero(tmp_path):
    f = _write(tmp_path / "broken.pine", "x = close\nplot(x)\n")
    result = runner.invoke(app, ["lint", str(f)])
    assert result.exit_code == 1


def test_cli_format_write(tmp_path):
    f = _write(tmp_path / "messy.pine", "//@version=6\nindicator('x')\nlen=14\nplot(close)\n")
    result = runner.invoke(app, ["format", str(f), "--write"])
    assert result.exit_code == 0
    formatted = f.read_text(encoding="utf-8")
    assert "len = 14" in formatted


def test_cli_analyze(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    result = runner.invoke(app, ["analyze", str(f)])
    assert result.exit_code == 0
    assert "Analysis" in result.stdout


def test_cli_analyze_json(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    result = runner.invoke(app, ["analyze", str(f), "--json"])
    assert result.exit_code == 0
    assert '"complexity_score"' in result.stdout


def test_cli_optimize(tmp_path, messy_v4_source):
    f = _write(tmp_path / "messy.pine", messy_v4_source)
    result = runner.invoke(app, ["optimize", str(f)])
    assert result.exit_code == 0


def test_cli_explain_summary(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    result = runner.invoke(app, ["explain", str(f), "--summary"])
    assert result.exit_code == 0
    assert "strategy" in result.stdout.lower()


def test_cli_upgrade(tmp_path, messy_v4_source):
    f = _write(tmp_path / "messy.pine", messy_v4_source)
    result = runner.invoke(app, ["upgrade", str(f), "--to", "6"])
    assert result.exit_code == 0
    assert "6" in result.stdout


def test_cli_upgrade_write(tmp_path, messy_v4_source):
    f = _write(tmp_path / "messy.pine", messy_v4_source)
    result = runner.invoke(app, ["upgrade", str(f), "--to", "6", "--write"])
    assert result.exit_code == 0
    upgraded = f.read_text(encoding="utf-8")
    assert "//@version=6" in upgraded


def test_cli_template_list():
    result = runner.invoke(app, ["template", "list"])
    assert result.exit_code == 0
    assert "ema-cross-indicator" in result.stdout


def test_cli_template_new(tmp_path):
    out = tmp_path / "out.pine"
    result = runner.invoke(app, ["template", "new", "rsi-indicator", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert "ta.rsi" in out.read_text(encoding="utf-8")


def test_cli_template_new_unknown_kind():
    result = runner.invoke(app, ["template", "new", "not-a-real-template"])
    assert result.exit_code == 1


def test_cli_readme(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    result = runner.invoke(app, ["readme", str(f)])
    assert result.exit_code == 0
    assert "Clean EMA Strategy" in result.stdout


def test_cli_docs_markdown(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    result = runner.invoke(app, ["docs", str(f), "--format", "markdown"])
    assert result.exit_code == 0


def test_cli_report(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    result = runner.invoke(app, ["report", str(f)])
    assert result.exit_code == 0
    assert "Analysis Report" in result.stdout


def test_cli_history_empty():
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0


def test_cli_history_after_lint(tmp_path, clean_v6_source):
    f = _write(tmp_path / "strat.pine", clean_v6_source)
    runner.invoke(app, ["lint", str(f)])
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "lint" in result.stdout


def test_cli_plugins_list_empty():
    result = runner.invoke(app, ["plugins", "list"])
    assert result.exit_code == 0


def test_cli_generate_without_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["generate", "a simple sma indicator"])
    assert result.exit_code == 1
    assert "API key" in result.output


def test_cli_file_not_found():
    result = runner.invoke(app, ["lint", "/nonexistent/path/file.pine"])
    assert result.exit_code != 0
