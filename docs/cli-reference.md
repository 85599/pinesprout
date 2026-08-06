# CLI Reference

Run `pinesprout <command> --help` for the full flag list of any command.
`psp` is a shorter alias for `pinesprout`; both are installed automatically.

## Global options

| Flag | Description |
|---|---|
| `--version`, `-v` | Print the PineSprout version and exit |
| `--install-completion` | Install shell tab-completion |
| `--show-completion` | Print the shell completion script |
| `--help` | Show help for any command or subcommand |

Every subcommand below also accepts `--json` to emit machine-readable
output on stdout instead of the Rich-formatted terminal view.

---

## `format`

```
pinesprout format <file-or-dir> [--write] [--diff] [--indent-size N] [--json]
```

Deterministically formats Pine Script: normalizes indentation to
structural nesting, spaces operators and commas consistently (while
keeping `name=value` keyword arguments tight, matching Pine/Python
convention), collapses excess blank lines, and trims trailing
whitespace.

- `--write` / `-w`: write the formatted output back to disk
- `--diff`: print a unified diff instead of the full source
- Without `--write` or `--diff`: prints the formatted source to stdout

## `lint`

```
pinesprout lint <file-or-dir> [--fail-on-warning] [--json]
```

Runs the full rule set:

- **unused-variable** — declared but never referenced
- **repaint-risk** — `request.security()` without explicit `lookahead`, and other historical/realtime-sensitive calls
- **deprecated-syntax** — pre-v5 global functions (`study`, `rsi`, `sma`, `security`, ...)
- **performance** — expensive `ta.*` calls inside `for`/`while` loops
- **structure** — missing `//@version=` pragma or missing `indicator`/`strategy`/`library` declaration
- **style** — line length, tabs vs. spaces

Exit code is non-zero if any **error**-level issue is found (missing
version pragma / declaration), or if `--fail-on-warning` is set and any
warning is found. This makes `pinesprout lint` a natural CI gate.

Plugin-contributed lint rules (see [Plugin Development](plugin-development.md))
are merged into the output automatically.

## `analyze`

```
pinesprout analyze <file> [--json]
```

Structural and complexity analysis: script type (indicator / strategy /
library), line/variable/function/input/plot counts, nesting depth, a
heuristic complexity score, and warnings (e.g. a strategy with no
`strategy.entry` calls, an indicator with no plots).

## `optimize`

```
pinesprout optimize <file> [--apply] [--json]
```

Surfaces refactor opportunities: repeated `ta.*` calls that should be
cached in a variable, magic numbers that should be inputs, redundant
boolean comparisons (`== true`), and loop-bound performance costs
(cross-referenced from the linter). `--apply` applies the safely
auto-fixable subset (currently: redundant `== true` removal) in place.

## `explain`

```
pinesprout explain <file> [--summary] [--json]
```

Produces a plain-English, line-by-line walkthrough of the script plus a
one-paragraph summary. `--summary` prints only the summary.

## `upgrade`

```
pinesprout upgrade <file> --to {5,6} [--write] [--json]
```

Migrates Pine Script from v4 toward v5/v6: renames `study()` →
`indicator()`, namespaces global TA functions (`rsi` → `ta.rsi`, `sma` →
`ta.sma`, etc.), moves `security()` → `request.security()`, and bumps
the version pragma. Prints a list of applied migrations plus
"manual review" notes for behavioral nuances that can't be auto-verified.

## `generate`

```
pinesprout generate "<prompt>" [--type indicator|strategy|library] \
  [--pine-version 6] [--output file.pine] [--api-key KEY] [--json]
```

Generates a complete Pine Script file from a natural-language prompt
using the Anthropic API. Requires `ANTHROPIC_API_KEY` (or `--api-key`).
Generated code is automatically linted; any issues found are reported
alongside the result.

## `template`

```
pinesprout template list
pinesprout template new <kind> [--title TEXT] [--output FILE] \
  [--overlay/--no-overlay] [--pine-version 6]
```

Deterministic, offline scaffold generation — no API key required.
Available kinds: `ema-cross-indicator`, `rsi-indicator`,
`blank-indicator`, `rsi-strategy`, `ema-cross-strategy`, `blank-strategy`.

## `readme`

```
pinesprout readme <file> [--output README.md] [--description TEXT]
```

Generates a README.md describing the script: title, type, overview,
input table, and key metrics.

## `docs`

```
pinesprout docs <file> [--format markdown|html] [--output FILE]
```

Generates standalone HTML or Markdown documentation, including the full
annotated source in the HTML variant.

## `report`

```
pinesprout report <file> [--output report.md]
```

The most comprehensive single output: combines analyzer metrics, the
full lint result, and optimizer suggestions into one Markdown report —
useful for code review or documenting a strategy's behavior before
deploying it live.

## `history`

```
pinesprout history [--limit N] [--command NAME] [--json]
```

Shows recent PineSprout runs from the local SQLite history database
(`~/.pinesprout/pinesprout.db` by default, override with `PINESPROUT_DB`).

## `plugins`

```
pinesprout plugins list [--json]
```

Lists discovered plugins (installed entry points plus any local
`.pinesprout/plugins/*.py` files) and where each was loaded from.
