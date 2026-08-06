"""Static knowledge base of Pine Script version differences.

Used by the linter (deprecated-syntax warnings) and the upgrader
(v4 -> v5 -> v6 migrations). Kept as plain data so it is easy to extend.
"""

from __future__ import annotations

from pydantic import BaseModel


class Migration(BaseModel):
    pattern: str          # regex pattern to match (old syntax)
    replacement: str      # regex replacement (new syntax)
    description: str
    from_version: int
    to_version: int


class DeprecatedSymbol(BaseModel):
    symbol: str
    since_version: int
    replacement: str
    message: str


# Functions/keywords renamed or namespaced between v4 -> v5 -> v6.
DEPRECATED_SYMBOLS: list[DeprecatedSymbol] = [
    DeprecatedSymbol(symbol="study(", since_version=5, replacement="indicator(",
                      message="`study()` was renamed to `indicator()` in Pine v5."),
    DeprecatedSymbol(symbol="security(", since_version=5, replacement="request.security(",
                      message="`security()` moved to the `request.*` namespace in v5."),
    DeprecatedSymbol(symbol="tickerid(", since_version=5, replacement="ticker.new(",
                      message="`tickerid()` moved to `ticker.new()` in v5."),
    DeprecatedSymbol(symbol="rsi(", since_version=5, replacement="ta.rsi(",
                      message="Built-in technical analysis functions moved to the `ta.*` "
                              "namespace in v5 (e.g. `rsi` -> `ta.rsi`)."),
    DeprecatedSymbol(symbol="sma(", since_version=5, replacement="ta.sma(",
                      message="`sma()` moved to `ta.sma()` in v5."),
    DeprecatedSymbol(symbol="ema(", since_version=5, replacement="ta.ema(",
                      message="`ema()` moved to `ta.ema()` in v5."),
    DeprecatedSymbol(symbol="macd(", since_version=5, replacement="ta.macd(",
                      message="`macd()` moved to `ta.macd()` in v5."),
    DeprecatedSymbol(symbol="stoch(", since_version=5, replacement="ta.stoch(",
                      message="`stoch()` moved to `ta.stoch()` in v5."),
    DeprecatedSymbol(symbol="atr(", since_version=5, replacement="ta.atr(",
                      message="`atr()` moved to `ta.atr()` in v5."),
    DeprecatedSymbol(symbol="highest(", since_version=5, replacement="ta.highest(",
                      message="`highest()` moved to `ta.highest()` in v5."),
    DeprecatedSymbol(symbol="lowest(", since_version=5, replacement="ta.lowest(",
                      message="`lowest()` moved to `ta.lowest()` in v5."),
    DeprecatedSymbol(symbol="crossover(", since_version=5, replacement="ta.crossover(",
                      message="`crossover()` moved to `ta.crossover()` in v5."),
    DeprecatedSymbol(symbol="crossunder(", since_version=5, replacement="ta.crossunder(",
                      message="`crossunder()` moved to `ta.crossunder()` in v5."),
    DeprecatedSymbol(symbol="valuewhen(", since_version=5, replacement="ta.valuewhen(",
                      message="`valuewhen()` moved to `ta.valuewhen()` in v5."),
    DeprecatedSymbol(symbol="barssince(", since_version=5, replacement="ta.barssince(",
                      message="`barssince()` moved to `ta.barssince()` in v5."),
    DeprecatedSymbol(symbol="strategy.performance", since_version=6, replacement="strategy.closedtrades",
                      message="Consider `strategy.closedtrades.*` accessors introduced in v6 for "
                              "richer per-trade statistics."),
]

# Ordered regex migrations applied by the upgrader, keyed by the version
# transition they apply to. Applied in list order.
MIGRATIONS_V4_TO_V5: list[Migration] = [
    Migration(pattern=r"//\s*@version\s*=\s*4", replacement="//@version=5",
               description="Bump version pragma to 5", from_version=4, to_version=5),
    Migration(pattern=r"\bstudy\s*\(", replacement="indicator(",
               description="study() -> indicator()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])security\s*\(", replacement="request.security(",
               description="security() -> request.security()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])rsi\s*\(", replacement="ta.rsi(",
               description="rsi() -> ta.rsi()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])sma\s*\(", replacement="ta.sma(",
               description="sma() -> ta.sma()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])ema\s*\(", replacement="ta.ema(",
               description="ema() -> ta.ema()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])wma\s*\(", replacement="ta.wma(",
               description="wma() -> ta.wma()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])vwma\s*\(", replacement="ta.vwma(",
               description="vwma() -> ta.vwma()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])macd\s*\(", replacement="ta.macd(",
               description="macd() -> ta.macd()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])stoch\s*\(", replacement="ta.stoch(",
               description="stoch() -> ta.stoch()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])atr\s*\(", replacement="ta.atr(",
               description="atr() -> ta.atr()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])highest\s*\(", replacement="ta.highest(",
               description="highest() -> ta.highest()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])lowest\s*\(", replacement="ta.lowest(",
               description="lowest() -> ta.lowest()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])crossover\s*\(", replacement="ta.crossover(",
               description="crossover() -> ta.crossover()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])crossunder\s*\(", replacement="ta.crossunder(",
               description="crossunder() -> ta.crossunder()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])valuewhen\s*\(", replacement="ta.valuewhen(",
               description="valuewhen() -> ta.valuewhen()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])barssince\s*\(", replacement="ta.barssince(",
               description="barssince() -> ta.barssince()", from_version=4, to_version=5),
    Migration(pattern=r"(?<![.\w])tickerid\s*\(", replacement="ticker.new(",
               description="tickerid() -> ticker.new()", from_version=4, to_version=5),
    Migration(pattern=r"\btranspIn\b", replacement="transp",
               description="transpIn -> transp (cosmetic)", from_version=4, to_version=5),
]

MIGRATIONS_V5_TO_V6: list[Migration] = [
    Migration(pattern=r"//\s*@version\s*=\s*5", replacement="//@version=6",
               description="Bump version pragma to 6", from_version=5, to_version=6),
    # v6 is largely backward compatible with v5; most changes are additive
    # (new namespaces, new built-ins). No mandatory renames are applied
    # here beyond the version pragma, but the list is easy to extend.
]

REPAINT_PRONE_FUNCTIONS = {
    "request.security", "security", "ta.valuewhen", "ta.barssince",
    "input.source",
}

PERFORMANCE_SENSITIVE_FUNCTIONS = {
    "ta.sma", "ta.ema", "ta.rsi", "ta.atr", "ta.stoch", "ta.macd",
    "ta.highest", "ta.lowest", "sma", "ema", "rsi", "atr",
}
