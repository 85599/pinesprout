"""File discovery and safe read/write helpers used across CLI commands."""

from __future__ import annotations

from pathlib import Path

PINE_EXTENSIONS = (".pine", ".pinescript")


def is_pine_file(path: Path) -> bool:
    return path.suffix.lower() in PINE_EXTENSIONS


def resolve_pine_files(target: Path, recursive: bool = True) -> list[Path]:
    """Resolve a file or directory argument into a sorted list of .pine files."""
    if target.is_file():
        return [target]
    if target.is_dir():
        pattern = "**/*" if recursive else "*"
        files = [p for p in target.glob(pattern) if p.is_file() and is_pine_file(p)]
        return sorted(files)
    return []


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
