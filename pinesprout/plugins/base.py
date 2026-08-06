"""Plugin interface for extending PineSprout with custom commands or rules.

Plugins are discovered via Python entry points under the group
``pinesprout.plugins`` (see ``pyproject.toml`` -> ``[project.entry-points]``
in a plugin package), and also via a local ``.pinesprout/plugins/`` folder
containing standalone ``*.py`` modules for quick, project-local
extensions.

A plugin module must expose a module-level ``PLUGIN`` object that is an
instance of a :class:`PineSproutPlugin` subclass.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pinesprout.core.linter import LintIssue


class LintRule(ABC):
    """A custom lint rule contributed by a plugin."""

    name: str = "custom-rule"

    @abstractmethod
    def check(self, source: str) -> list[LintIssue]:
        """Return any issues found in ``source``."""
        raise NotImplementedError


class PineSproutPlugin(ABC):
    """Base class every PineSprout plugin must implement."""

    #: Unique, human-readable plugin name.
    name: str = "unnamed-plugin"
    #: Semantic version string of the plugin itself.
    version: str = "0.0.0"

    def lint_rules(self) -> list[LintRule]:
        """Return additional lint rules this plugin contributes."""
        return []

    def register_cli(self, app: object) -> None:
        """Optionally register additional Typer subcommands on ``app``.

        Implementations should treat ``app`` as a ``typer.Typer`` instance
        and use ``app.command()`` / ``app.add_typer()`` to extend the CLI.
        """
        return None

    def on_load(self) -> None:
        """Hook called once when the plugin is loaded."""
        return None
