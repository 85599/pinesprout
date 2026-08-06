"""Parser that turns tokenized Pine Script into a lightweight AST.

Pine Script's grammar is significant-indentation based (like Python) with
a small set of top-level declaration forms (``indicator``, ``strategy``,
``library``) and statement forms (``if``, ``for``, ``while``, ``switch``,
assignments, and function calls). Rather than build a full expression
grammar (unnecessary for formatting/linting/analysis), PineSprout parses
line-by-line, classifying each logical line into a node kind and keeping
the original text for anything it doesn't need to deeply understand. This
keeps the parser robust against the many syntax edge cases in real-world
Pine Script while still giving structured data to every other module.
"""

from __future__ import annotations

import re

from pinesprout.core.ast_nodes import Node, NodeKind, ParsedProgram, Position

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)")
_DECL_RE = re.compile(r"^(indicator|strategy|library|study)\s*\(")
_VAR_DECL_RE = re.compile(r"^(var\s+|varip\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)\s*(.+)$")
_VAR_REASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\[\]]*)\s*:=\s*(.+)$")
_FUNC_DECL_RE = re.compile(r"^(?:export\s+)?(?:method\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*=>\s*(.*)$")
_IF_RE = re.compile(r"^if\s+(.+)$")
_FOR_RE = re.compile(r"^for\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s+to\s+(.+)$")
_WHILE_RE = re.compile(r"^while\s+(.+)$")
_SWITCH_RE = re.compile(r"^switch\b(.*)$")
_IMPORT_RE = re.compile(r"^import\s+(.+)$")
_PLOT_CALL_RE = re.compile(r"^(plot|plotshape|plotchar|plotarrow|plotcandle|plotbar|hline|fill|bgcolor)\s*\(")
_INPUT_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*\s*=\s*)?input(?:\.[a-z]+)?\s*\(")
_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*\(")


def _indent_of(line: str) -> int:
    stripped = line.lstrip(" ")
    return len(line) - len(stripped)


def _paren_delta(code: str) -> int:
    """Net change in bracket depth for a line of code, ignoring string/comment content."""
    masked_code, _, _ = _split_inline_comment(code)
    depth = 0
    in_string: str | None = None
    escape = False
    for ch in masked_code:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_string:
            if ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
    return depth


def _join_continuations(lines: list[str]) -> list[tuple[int, str]]:
    """Merge physical lines that are part of an unbalanced-paren statement
    (e.g. a multi-line ``strategy(...)`` call) into single logical lines.

    Returns a list of (starting_line_number, joined_text) pairs, one per
    logical line, preserving the original 1-indexed line number of the
    first physical line for downstream position tracking. Lines ending in
    a trailing comma/operator with balanced parens are left as-is; only
    genuinely unbalanced bracket depth triggers a join, so this is safe
    for ordinary single-line statements.
    """
    logical: list[tuple[int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        start_line_no = i + 1
        current = lines[i]
        depth = _paren_delta(current)
        buffer = [current]
        while depth > 0 and i + 1 < n:
            i += 1
            buffer.append(lines[i])
            depth += _paren_delta(lines[i])
        joined = " ".join(seg.strip() for seg in buffer) if len(buffer) > 1 else current
        # Preserve original leading indentation of the first physical line.
        if len(buffer) > 1:
            leading_ws = len(current) - len(current.lstrip(" "))
            joined = (" " * leading_ws) + joined.lstrip()
        logical.append((start_line_no, joined))
        i += 1
    return logical


def parse(source: str) -> ParsedProgram:
    """Parse Pine Script source text into a :class:`ParsedProgram`."""
    lines = source.splitlines()
    root = Node(
        kind=NodeKind.SOURCE,
        text=source,
        start=Position(1, 0),
        end=Position(max(len(lines), 1), 0),
    )

    declarations: list[Node] = []
    variable_assignments: list[Node] = []
    function_calls: list[Node] = []
    comments: list[Node] = []
    pine_version: int | None = None

    for idx, raw_line in _join_continuations(lines):
        stripped = raw_line.strip()
        indent = _indent_of(raw_line)
        pos = Position(idx, indent)

        if not stripped:
            continue

        version_match = _VERSION_RE.search(raw_line)
        if version_match:
            pine_version = int(version_match.group(1))
            version_node = Node(NodeKind.VERSION_ANNOTATION, raw_line, pos, pos)
            root.children.append(version_node)
            continue

        if stripped.startswith("//"):
            comment_node = Node(NodeKind.COMMENT, stripped, pos, pos)
            comments.append(comment_node)
            root.children.append(comment_node)
            continue

        # Strip trailing inline comment for classification purposes only.
        code_part, _, inline_comment = _split_inline_comment(stripped)
        code_part = code_part.rstrip()

        if not code_part:
            continue

        node: Node | None = None

        if m := _DECL_RE.match(code_part):
            kind = {
                "indicator": NodeKind.INDICATOR_DECL,
                "study": NodeKind.INDICATOR_DECL,
                "strategy": NodeKind.STRATEGY_DECL,
                "library": NodeKind.LIBRARY_DECL,
            }[m.group(1)]
            node = Node(kind, stripped, pos, pos, meta={"call": code_part, "legacy": m.group(1) == "study"})
            declarations.append(node)

        elif m := _IMPORT_RE.match(code_part):
            node = Node(NodeKind.IMPORT_STATEMENT, stripped, pos, pos, meta={"module": m.group(1)})

        elif m := _FUNC_DECL_RE.match(code_part):
            node = Node(
                NodeKind.FUNCTION_DECL,
                stripped,
                pos,
                pos,
                meta={
                    "name": m.group(1),
                    "params": [p.strip() for p in m.group(2).split(",") if p.strip()],
                    "indent": indent,
                    "single_line_body": m.group(3).strip() or None,
                },
            )
            declarations.append(node)

        elif m := _IF_RE.match(code_part):
            node = Node(NodeKind.IF_STATEMENT, stripped, pos, pos, meta={"condition": m.group(1), "indent": indent})

        elif m := _FOR_RE.match(code_part):
            node = Node(
                NodeKind.FOR_STATEMENT,
                stripped,
                pos,
                pos,
                meta={"var": m.group(1), "from": m.group(2), "to": m.group(3), "indent": indent},
            )

        elif m := _WHILE_RE.match(code_part):
            node = Node(NodeKind.WHILE_STATEMENT, stripped, pos, pos, meta={"condition": m.group(1), "indent": indent})

        elif m := _SWITCH_RE.match(code_part):
            node = Node(
                NodeKind.SWITCH_STATEMENT, stripped, pos, pos, meta={"subject": m.group(1).strip(), "indent": indent}
            )

        elif _PLOT_CALL_RE.match(code_part):
            node = Node(NodeKind.PLOT_STATEMENT, stripped, pos, pos)
            function_calls.append(node)

        elif _INPUT_CALL_RE.match(code_part):
            node = Node(NodeKind.INPUT_STATEMENT, stripped, pos, pos)
            function_calls.append(node)

        elif m := _VAR_REASSIGN_RE.match(code_part):
            node = Node(
                NodeKind.VARIABLE_REASSIGN,
                stripped,
                pos,
                pos,
                meta={"name": m.group(1), "value": m.group(2), "indent": indent},
            )
            variable_assignments.append(node)

        elif m := _VAR_DECL_RE.match(code_part):
            is_var = bool(m.group(1))
            node = Node(
                NodeKind.VARIABLE_DECL,
                stripped,
                pos,
                pos,
                meta={
                    "name": m.group(2),
                    "value": m.group(3),
                    "is_var": is_var,
                    "indent": indent,
                },
            )
            variable_assignments.append(node)
            declarations.append(node)

        else:
            node = Node(NodeKind.EXPRESSION_STATEMENT, stripped, pos, pos, meta={"indent": indent})
            if call_match := _CALL_RE.match(code_part):
                fn_node = Node(NodeKind.FUNCTION_CALL, stripped, pos, pos, meta={"name": call_match.group(1)})
                function_calls.append(fn_node)

        if node is not None:
            node.meta.setdefault("indent", indent)
            if inline_comment:
                node.meta["inline_comment"] = inline_comment
            root.children.append(node)

    return ParsedProgram(
        root=root,
        source_lines=lines,
        pine_version=pine_version,
        declarations=declarations,
        variable_assignments=variable_assignments,
        function_calls=function_calls,
        comments=comments,
        raw_source=source,
    )


def _split_inline_comment(line: str) -> tuple[str, str, str]:
    """Split a line into (code, separator, comment), respecting string literals."""
    in_string: str | None = None
    escape = False
    for i, ch in enumerate(line):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_string:
            if ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
            continue
        if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            return line[:i], "//", line[i:]
    return line, "", ""
