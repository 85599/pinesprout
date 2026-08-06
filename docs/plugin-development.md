# Plugin Development

PineSprout can be extended with custom lint rules (and, for packaged
plugins, additional CLI commands) without modifying PineSprout itself.

## Two ways to ship a plugin

### 1. Local, project-specific plugins

Drop a Python file into `.pinesprout/plugins/` in your project root. Every
`*.py` file there is imported automatically and its module-level `PLUGIN`
object is registered. No packaging or installation required — this is
the fastest way to add a rule specific to your team's style guide.

```python
# .pinesprout/plugins/no_hardcoded_colors.py
from pinesprout.core.linter import LintCategory, LintIssue, Severity
from pinesprout.plugins.base import LintRule, PineSproutPlugin


class NoHardcodedColorsRule(LintRule):
    name = "no-hardcoded-colors"

    def check(self, source: str) -> list[LintIssue]:
        issues = []
        for i, line in enumerate(source.splitlines(), start=1):
            if "color=color." in line and "input" not in line:
                issues.append(
                    LintIssue(
                        line=i,
                        severity=Severity.INFO,
                        category=LintCategory.STYLE,
                        message="Hard-coded color; consider exposing via input.color().",
                    )
                )
        return issues


class TeamStylePlugin(PineSproutPlugin):
    name = "team-style-rules"
    version = "1.0.0"

    def lint_rules(self) -> list[LintRule]:
        return [NoHardcodedColorsRule()]


PLUGIN = TeamStylePlugin()
```

Verify it's discovered:

```bash
pinesprout plugins list
```

Then run `pinesprout lint` as usual — your rule's findings are merged
into the normal output automatically.

### 2. Packaged, distributable plugins

For a plugin you want to `pip install` and share across projects,
declare an entry point in the plugin package's own `pyproject.toml`:

```toml
[project.entry-points."pinesprout.plugins"]
my_plugin = "my_package.plugin:PLUGIN"
```

Where `my_package/plugin.py` defines a `PLUGIN` instance the same way as
the local example above. PineSprout discovers it automatically once the
package is installed in the same environment — no configuration needed.

## The `PineSproutPlugin` interface

```python
class PineSproutPlugin(ABC):
    name: str = "unnamed-plugin"
    version: str = "0.0.0"

    def lint_rules(self) -> list[LintRule]:
        """Return additional lint rules this plugin contributes."""
        return []

    def register_cli(self, app: object) -> None:
        """Optionally register additional Typer subcommands on `app`."""
        return None

    def on_load(self) -> None:
        """Called once when the plugin is loaded."""
        return None
```

- Override **`lint_rules()`** to contribute custom static-analysis checks.
- Override **`register_cli()`** to add new Typer subcommands (packaged
  plugins only — this hook receives the live `pinesprout` Typer app).
- Override **`on_load()`** for one-time setup (e.g. validating
  configuration, warming a cache).

## The `LintRule` interface

```python
class LintRule(ABC):
    name: str = "custom-rule"

    @abstractmethod
    def check(self, source: str) -> list[LintIssue]:
        """Return any issues found in `source`."""
```

Return a list of `LintIssue` (the same model PineSprout's built-in rules
use — see `pinesprout.core.linter`), each with a `line`, `severity`
(`error` / `warning` / `info`), `category`, `message`, and optional
`symbol` / `suggestion`.

## Error isolation

If a plugin fails to load, or a lint rule raises an exception while
checking a file, PineSprout prints a warning and continues — a broken
plugin never crashes the CLI or blocks linting from the built-in rules.
