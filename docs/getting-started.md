# Getting Started with PineSprout

## Installation

```bash
pip install pinesprout
```

Requires Python 3.12 or newer. Verify the install:

```bash
pinesprout --version
```

Both `pinesprout` and the shorter alias `psp` are installed as console
scripts, and `python -m pinesprout` works too.

## Your first indicator

Scaffold a ready-to-use EMA-crossover indicator:

```bash
pinesprout template new ema-cross-indicator --title "My First Indicator" -o my_indicator.pine
```

Check it for issues:

```bash
pinesprout lint my_indicator.pine
```

Format it (PineSprout formats in place with `--write`, or prints to
stdout by default):

```bash
pinesprout format my_indicator.pine --write
```

See a structural breakdown:

```bash
pinesprout analyze my_indicator.pine
```

## Working with an existing script

Point any command at a file you already have:

```bash
pinesprout lint path/to/your_script.pine
pinesprout explain path/to/your_script.pine
pinesprout optimize path/to/your_script.pine
```

## Upgrading old scripts

If you have a Pine v4 script, PineSprout can migrate it toward v5/v6
automatically:

```bash
pinesprout upgrade legacy.pine --to 6 --write
```

This rewrites deprecated global functions (`study()`, bare `rsi()`,
`sma()`, `security()`, etc.) into their namespaced v5/v6 equivalents and
bumps the `//@version=` pragma. Review the "Manual Review Recommended"
notes it prints — a few behavioral nuances (e.g. `request.security`
argument defaults) can't be auto-verified and are worth a second look.

## Generating new scripts with AI

Set your Anthropic API key once:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Then describe what you want:

```bash
pinesprout generate "A Bollinger Band squeeze breakout strategy with volume confirmation" \
  --type strategy \
  --output squeeze_strategy.pine
```

Generated code is automatically linted before being returned so you can
see any issues immediately.

## Documenting a script

```bash
pinesprout readme my_indicator.pine -o README.md
pinesprout docs my_indicator.pine --format html -o docs.html
pinesprout report my_indicator.pine -o analysis_report.md
```

## Machine-readable output

Every command accepts `--json` for use in scripts, CI pipelines, or
editor integrations:

```bash
pinesprout lint my_indicator.pine --json | jq '.issues | length'
```

`pinesprout lint` also exits with a non-zero status code if any errors
are found (and optionally on warnings with `--fail-on-warning`), so it
plugs directly into CI.

## Next steps

- [CLI Reference](cli-reference.md) — every command, flag, and example
- [Plugin Development](plugin-development.md) — write custom lint rules
- [Architecture](architecture.md) — how PineSprout is put together
