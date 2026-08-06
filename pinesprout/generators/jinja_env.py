"""Shared Jinja2 environment configured to read PineSprout's bundled templates."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


def get_templates_dir() -> Path:
    with resources.as_file(resources.files("pinesprout") / "templates") as path:
        return path


def build_env(autoescape_html: bool = False) -> Environment:
    templates_dir = get_templates_dir()
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(enabled_extensions=("html",)) if autoescape_html else False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env
