"""Discover and load PineSprout plugins.

Two discovery mechanisms are supported:

1. **Entry points** — any installed package that declares an entry point
   in the ``pinesprout.plugins`` group is loaded automatically. Example, in
   a plugin package's ``pyproject.toml``::

       [project.entry-points."pinesprout.plugins"]
       my_plugin = "my_package.plugin:PLUGIN"

2. **Local plugin directory** — any ``*.py`` file inside
   ``.pinesprout/plugins/`` relative to the current working directory (or
   a custom directory) is imported directly and its ``PLUGIN`` attribute
   is registered. This is convenient for one-off, project-specific rules
   that don't warrant a full package.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from pinesprout.plugins.base import PineSproutPlugin

ENTRY_POINT_GROUP = "pinesprout.plugins"
DEFAULT_PLUGIN_DIR = Path(".pinesprout") / "plugins"


@dataclass
class LoadedPlugin:
    plugin: PineSproutPlugin
    source: str  # "entry_point" | "local:<path>"


def _load_from_entry_points() -> list[LoadedPlugin]:
    loaded: list[LoadedPlugin] = []
    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except Exception:
        return loaded

    for ep in eps:
        try:
            obj = ep.load()
            plugin = obj() if isinstance(obj, type) else obj
            if isinstance(plugin, PineSproutPlugin):
                loaded.append(LoadedPlugin(plugin=plugin, source="entry_point"))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[pinesprout] Failed to load plugin '{ep.name}': {exc}", file=sys.stderr)
    return loaded


def _load_from_directory(plugin_dir: Path) -> list[LoadedPlugin]:
    loaded: list[LoadedPlugin] = []
    if not plugin_dir.is_dir():
        return loaded

    for py_file in sorted(plugin_dir.glob("*.py")):
        module_name = f"pinesprout_local_plugin_{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            plugin_obj = getattr(module, "PLUGIN", None)
            if isinstance(plugin_obj, PineSproutPlugin):
                loaded.append(LoadedPlugin(plugin=plugin_obj, source=f"local:{py_file}"))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[pinesprout] Failed to load local plugin '{py_file}': {exc}", file=sys.stderr)
    return loaded


def load_plugins(plugin_dir: Path | None = None) -> list[LoadedPlugin]:
    """Load all discoverable plugins and call their ``on_load`` hook."""
    plugin_dir = plugin_dir or DEFAULT_PLUGIN_DIR
    loaded = _load_from_entry_points() + _load_from_directory(plugin_dir)
    for lp in loaded:
        try:
            lp.plugin.on_load()
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[pinesprout] Plugin '{lp.plugin.name}' on_load() failed: {exc}", file=sys.stderr)
    return loaded
