"""Global PineSprout configuration, loaded from environment variables and
an optional ``pinesprout.toml`` / ``.pinesproutrc`` file in the project root."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PineSproutSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PINESPROUT_", extra="ignore")

    default_pine_version: int = Field(default=6, ge=1, le=6)
    indent_size: int = Field(default=4, ge=1, le=8)
    max_line_length: int = Field(default=120, ge=40)
    plugin_dir: str = ".pinesprout/plugins"
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str | None = None


def load_project_config(root: Path | None = None) -> PineSproutSettings:
    """Load settings, layering a ``pinesprout.toml`` file over env vars if present."""
    root = root or Path.cwd()
    config_path = root / "pinesprout.toml"
    overrides: dict[str, object] = {}
    if config_path.is_file():
        with config_path.open("rb") as f:
            data = tomllib.load(f)
        overrides = data.get("pinesprout", data)
    return PineSproutSettings(**overrides)  # type: ignore[arg-type]
