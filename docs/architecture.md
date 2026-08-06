# Architecture

## Design goals

1. **Deterministic core, optional AI.** Formatting, linting, analysis,
   optimization, explanation, and version upgrades are all pure,
   offline, deterministic Python — no network access or API key
   required. AI is used only where it adds genuine value (generating
   new code from a prompt), and its output is always re-validated by
   the deterministic linter before being returned.
2. **One AST, many consumers.** A single parse produces a lightweight
   AST that the formatter, linter, analyzer, optimizer, and explainer
   all consume, so improvements to parsing accuracy benefit every
   feature at once.
3. **Everything is data.** Lint issues, analysis reports, optimization
   suggestions, and upgrade results are all Pydantic models. This is
   what makes `--json` output trivial and consistent across every
   command — there is no separate "human output" vs. "machine output"
   code path with different information.

## Pipeline

```
source text
    |
    v
core/lexer.py         tokenize()      -> flat list of Tokens
    |  (used directly by the formatter for string/comment-safe spacing)
    v
core/parser.py         parse()        -> ParsedProgram (lightweight AST)
    |
    +--> core/formatter.py   -> formatted source
    +--> core/linter.py      -> LintResult (list[LintIssue])
    +--> core/analyzer.py    -> AnalysisReport
    +--> core/optimizer.py   -> OptimizationResult
    +--> core/explainer.py   -> list[LineExplanation] + summary
    +--> core/upgrader.py    -> UpgradeResult (regex migrations, not AST-based)
              |
              v
    generators/*.py   -> README.md / docs.html / docs.md / report.md
    (Jinja2 templates in pinesprout/templates/, fed by analyzer + linter + optimizer output)
```

The `upgrader` works at the regex/text level rather than through the AST
because version migrations are simple, well-defined token substitutions
(`rsi(` -> `ta.rsi(`) where a full AST round-trip would add complexity
without adding safety — the same guarantee (compilable output) is
already provided by re-linting the result.

## Why a custom parser, not tree-sitter/ANTLR

TradingView does not publish or maintain an official tree-sitter or
ANTLR grammar for Pine Script. Rather than depend on an unofficial,
potentially incomplete or stale third-party grammar, PineSprout ships a
small, dependency-free lexer/parser (`core/lexer.py`, `core/parser.py`)
whose output shape deliberately mirrors what a tree-sitter concrete
syntax tree looks like: typed nodes (`NodeKind` enum), line/column
spans (`Position`), a `children` list, and a `meta` dict for
per-node-kind structured data. This means:

- No dependency on an unofficial, potentially incomplete or stale
  third-party grammar.
- The parser is forgiving of real-world Pine Script's many edge cases
  (Pine has evolved across v1-v6 with different syntax quirks at each
  version) because it classifies each logical line independently rather
  than requiring a single unified grammar to accept every version.
- A real tree-sitter/ANTLR grammar could be swapped in later behind the
  same `ParsedProgram` interface without touching the formatter, linter,
  analyzer, optimizer, or explainer — they only depend on the AST shape,
  not the parsing strategy.

The parser handles **multi-line statements** (e.g. a `strategy(...)`
call whose named arguments span several lines, a very common real-world
style) via a pre-pass (`_join_continuations`) that tracks bracket depth
— ignoring string/comment content — and merges physical lines into one
logical line before classification.

## Module map

| Module | Responsibility |
|---|---|
| `core/lexer.py` | Regex-based tokenizer (strings, numbers, identifiers, operators, comments, the `//@version=` annotation) |
| `core/parser.py` | Builds the lightweight AST; handles multi-line statement joining |
| `core/ast_nodes.py` | `NodeKind`, `Node`, `Position`, `ParsedProgram` — the shared data model |
| `core/formatter.py` | Re-indentation by structural nesting, operator/comma spacing (string/comment-safe, depth-aware for `=` so keyword args stay tight), blank-line collapsing |
| `core/linter.py` | The rule engine: unused vars, repaint risk, deprecated syntax, performance, structure, style |
| `core/analyzer.py` | Structural/complexity metrics, script-type detection, input/plot/alert counting |
| `core/optimizer.py` | Repeated-call detection, magic-number detection, redundant-boolean detection, loop-performance cross-reference |
| `core/explainer.py` | Per-node plain-English explanation rules + whole-script summary |
| `core/upgrader.py` | Version-pragma bump + regex-based v4->v5->v6 migrations |
| `core/version_rules.py` | The data tables (`DEPRECATED_SYMBOLS`, `MIGRATIONS_V4_TO_V5`, etc.) everything above is driven by |
| `generators/ai_generator.py` | Anthropic API call + code-block extraction + re-lint of the result |
| `generators/template_generator.py` | Jinja2-based deterministic scaffolds (no network) |
| `generators/readme_generator.py`, `doc_generator.py`, `report_generator.py` | Render `AnalysisReport` / `LintResult` / `OptimizationResult` into Markdown/HTML via Jinja2 |
| `plugins/` | `PineSproutPlugin` / `LintRule` base classes + entry-point and local-directory discovery |
| `db/database.py` | SQLite-backed run history (`~/.pinesprout/pinesprout.db`) |
| `utils/` | Rich console theme, JSON serialization helpers, file discovery |
| `cli.py` | Typer app wiring all of the above together, with `--json` on every command |

## Testing strategy

- **Unit tests** for every `core/` module, exercising both "clean" and
  intentionally messy fixtures (`tests/fixtures/clean_v6.pine`,
  `tests/fixtures/messy_v4.pine`).
- **Generator tests** verify every built-in template produces code that
  parses correctly *and* lints with zero errors (a regression guard
  against templates drifting out of sync with linter rules).
- **AI generator tests** mock the HTTP transport (`httpx.MockTransport`)
  — no real network calls or API key are needed to run the suite.
- **CLI integration tests** use `typer.testing.CliRunner` to exercise
  every command's exit code and output, including error paths (missing
  file, missing API key, lint failures).
- **Plugin tests** cover both successful loading and graceful failure
  (a plugin file with a syntax error is skipped with a warning, not a
  crash).
