"""Helpers for emitting machine-readable JSON output from CLI commands."""

from __future__ import annotations

import json
import sys
from typing import Any

from pydantic import BaseModel


def to_jsonable(obj: Any) -> Any:
    """Recursively convert Pydantic models / common containers to plain JSON types."""
    if isinstance(obj, BaseModel):
        return json.loads(obj.model_dump_json())
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def print_json(obj: Any, indent: int = 2) -> None:
    """Print ``obj`` as JSON to stdout, converting Pydantic models automatically."""
    payload = to_jsonable(obj)
    sys.stdout.write(json.dumps(payload, indent=indent, default=str))
    sys.stdout.write("\n")
