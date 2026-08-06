"""Deterministic Pine Script formatter.

Rules applied (configurable via :class:`FormatOptions`):
  * Normalize indentation to a fixed number of spaces per level.
  * Collapse multiple blank lines to at most one.
  * Trim trailing whitespace.
  * Ensure exactly one space around binary operators (best-effort, string
    literal aware).
  * Ensure a single space after commas.
  * Normalize the ``//@version=`` pragma to the top of the file.
  * Ensure the file ends with exactly one trailing newline.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class FormatOptions(BaseModel):
    indent_size: int = Field(default=4, ge=1, le=8)
    max_blank_lines: int = Field(default=1, ge=0, le=5)
    space_around_operators: bool = True
    space_after_comma: bool = True
    align_trailing_comments: bool = False


_COMMA_RE = re.compile(r",(?!\s)")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)
_VERSION_RE = re.compile(r"^\s*//\s*@version\s*=\s*\d+\s*$")
_OPERATOR_RE = re.compile(
    r"(?<![=!<>:+\-*/])\s*(==|!=|<=|>=|:=|=>|[+\-*/%<>])\s*(?!=)"
)
_INDENT_UNIT = "    "


def _space_bare_equals(content: str, start_depth: int = 0) -> tuple[str, int]:
    """Add spaces around top-level `=` (assignment) but keep `name=value`
    tight inside function-call parentheses (Pine's keyword-argument style,
    matching Python's PEP 8 convention for `f(x=1)`).

    Accepts and returns the paren/bracket depth so callers can thread it
    across multiple physical lines belonging to the same logical
    (multi-line) statement -- otherwise a continuation line that opens
    with a keyword argument would be mistaken for a top-level assignment.
    """
    depth = start_depth
    out: list[str] = []
    i = 0
    n = len(content)
    while i < n:
        ch = content[i]
        if ch in "([":
            depth += 1
            out.append(ch)
            i += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
            out.append(ch)
            i += 1
        elif (
            ch == "="
            and (i == 0 or content[i - 1] not in "=!<>:+-*/")
            and (i + 1 >= n or content[i + 1] not in "=>")
        ):
            while out and out[-1] == " ":
                out.pop()
            out.append("=" if depth > 0 else " = ")
            i += 1
            while i < n and content[i] == " ":
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out), depth


def _line_paren_delta(content: str) -> int:
    """Net bracket-depth change contributed by a single (already
    string/comment-masked) line, ignoring the placeholder tokens."""
    depth = 0
    for ch in content:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
    return depth


def _protect_strings_and_comments(line: str) -> tuple[str, dict[str, str]]:
    """Replace string/comment spans with placeholders so operator spacing
    rules don't corrupt their contents; returns (masked_line, restore_map)."""
    restore: dict[str, str] = {}
    out = []
    i = 0
    n = len(line)
    token_idx = 0
    while i < n:
        ch = line[i]
        if ch in ("'", '"'):
            j = i + 1
            while j < n and line[j] != ch:
                if line[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            key = f"\x00S{token_idx}\x00"
            restore[key] = line[i:j]
            out.append(key)
            token_idx += 1
            i = j
        elif ch == "/" and i + 1 < n and line[i + 1] == "/":
            key = f"\x00C{token_idx}\x00"
            restore[key] = line[i:]
            out.append(key)
            token_idx += 1
            i = n
        else:
            out.append(ch)
            i += 1
    return "".join(out), restore


def _restore(line: str, restore: dict[str, str]) -> str:
    for key, value in restore.items():
        line = line.replace(key, value)
    return line


def _reindent(lines: list[str], indent_size: int) -> list[str]:
    """Recompute indentation from bracket/keyword nesting depth.

    Pine Script uses indentation to delimit blocks (no braces), so we
    track depth based on trailing ``=>``/``if``/``for``/``while``/``switch``
    that open a block, combined with the *original* relative indentation
    to detect dedents, since Pine allows multi-statement blocks at the
    same depth.
    """
    result: list[str] = []
    # Track a stack of original-indentation -> normalized-indentation.
    indent_stack: list[tuple[int, int]] = [(0, 0)]

    for raw in lines:
        if not raw.strip():
            result.append("")
            continue

        original_indent = len(raw) - len(raw.lstrip(" \t"))
        stripped = raw.strip()

        while indent_stack and original_indent < indent_stack[-1][0]:
            indent_stack.pop()

        if indent_stack and original_indent == indent_stack[-1][0]:
            normalized = indent_stack[-1][1]
        elif indent_stack and original_indent > indent_stack[-1][0]:
            normalized = indent_stack[-1][1] + indent_size
            indent_stack.append((original_indent, normalized))
        else:
            normalized = 0
            indent_stack = [(0, 0)]

        result.append(" " * normalized + stripped)

    return result


def format_source(source: str, options: FormatOptions | None = None) -> str:
    """Format Pine Script source code and return the formatted text."""
    options = options or FormatOptions()

    lines = source.splitlines()

    # Pull the version pragma (if any) to the very first line.
    version_line: str | None = None
    body_lines: list[str] = []
    for line in lines:
        if version_line is None and _VERSION_RE.match(line):
            version_line = line.strip()
        else:
            body_lines.append(line)

    # Trim trailing whitespace per line.
    body_lines = [line.rstrip() for line in body_lines]

    # Reindent based on structural nesting.
    if options.indent_size:
        body_lines = _reindent(body_lines, options.indent_size)

    # Operator / comma spacing (string & comment aware).
    normalized_lines: list[str] = []
    running_depth = 0
    for line in body_lines:
        if not line.strip():
            normalized_lines.append("")
            continue
        leading_ws = len(line) - len(line.lstrip(" "))
        indent = line[:leading_ws]
        content = line[leading_ws:]

        masked, restore = _protect_strings_and_comments(content)

        if options.space_after_comma:
            masked = _COMMA_RE.sub(", ", masked)
            masked = re.sub(r"\s+,", ",", masked)

        if options.space_around_operators:
            def _op_sub(m: re.Match[str]) -> str:
                return f" {m.group(1)} "

            masked = _OPERATOR_RE.sub(_op_sub, masked)
            masked, running_depth = _space_bare_equals(masked, running_depth)
            masked = re.sub(r"[ \t]{2,}", " ", masked)
            masked = re.sub(r"\(\s+", "(", masked)
            masked = re.sub(r"\s+\)", ")", masked)
            masked = re.sub(r"\[\s+", "[", masked)
            masked = re.sub(r"\s+\]", "]", masked)
        else:
            running_depth += _line_paren_delta(masked)

        restored = _restore(masked, restore)
        normalized_lines.append(indent + restored.rstrip())

    body = "\n".join(normalized_lines)
    body = _MULTI_BLANK_RE.sub("\n" * (options.max_blank_lines + 1), body)
    body = _TRAILING_WS_RE.sub("", body)

    parts = []
    if version_line:
        parts.append(version_line)
    parts.append(body.strip("\n"))
    formatted = "\n".join(p for p in parts if p != "")

    return formatted.rstrip("\n") + "\n"
