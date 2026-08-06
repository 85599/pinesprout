from __future__ import annotations

from pathlib import Path

from pinesprout.core.linter import LintCategory, LintIssue, Severity
from pinesprout.plugins.base import LintRule, PineSproutPlugin
from pinesprout.plugins.loader import load_plugins


class _DummyRule(LintRule):
    name = "dummy-rule"

    def check(self, source: str) -> list[LintIssue]:
        return [LintIssue(line=1, severity=Severity.INFO, category=LintCategory.STYLE, message="dummy")]


class _DummyPlugin(PineSproutPlugin):
    name = "dummy-plugin"
    version = "0.1.0"

    def lint_rules(self) -> list[LintRule]:
        return [_DummyRule()]


def test_plugin_lint_rule_returns_issues():
    plugin = _DummyPlugin()
    rules = plugin.lint_rules()
    assert len(rules) == 1
    issues = rules[0].check("//@version=6\n")
    assert issues[0].message == "dummy"


def test_load_plugins_from_local_directory(tmp_path: Path):
    plugin_dir = tmp_path / ".pinesprout" / "plugins"
    plugin_dir.mkdir(parents=True)
    plugin_file = plugin_dir / "sample.py"
    plugin_file.write_text(
        "from pinesprout.plugins.base import PineSproutPlugin\n"
        "class SamplePlugin(PineSproutPlugin):\n"
        "    name = 'sample'\n"
        "    version = '1.0.0'\n"
        "PLUGIN = SamplePlugin()\n",
        encoding="utf-8",
    )

    loaded = load_plugins(plugin_dir=plugin_dir)
    names = [lp.plugin.name for lp in loaded]
    assert "sample" in names


def test_load_plugins_empty_dir_returns_empty(tmp_path: Path):
    empty_dir = tmp_path / "nonexistent"
    loaded = load_plugins(plugin_dir=empty_dir)
    assert loaded == []


def test_load_plugins_skips_broken_plugin_gracefully(tmp_path: Path):
    plugin_dir = tmp_path / ".pinesprout" / "plugins"
    plugin_dir.mkdir(parents=True)
    broken_file = plugin_dir / "broken.py"
    broken_file.write_text("this is not valid python syntax !!!\n", encoding="utf-8")

    loaded = load_plugins(plugin_dir=plugin_dir)
    assert loaded == []
