"""Shared Rich console instance and small terminal-UI helpers."""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

PINESPROUT_THEME = Theme(
    {
        "pf.error": "bold red",
        "pf.warning": "yellow",
        "pf.info": "cyan",
        "pf.success": "bold green",
        "pf.muted": "grey58",
        "pf.accent": "bold magenta",
    }
)

console = Console(theme=PINESPROUT_THEME)
error_console = Console(theme=PINESPROUT_THEME, stderr=True)
