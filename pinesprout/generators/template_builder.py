"""
template_builder.py
A combinatorial Pine Script builder: pick an indicator (or two), a signal
pattern, script type, and risk settings, and get a complete, valid,
lint-clean Pine v6 script back.

Honesty note: this is NOT 10,000 hand-authored template files. It is a
building-block system -- roughly 24 indicators across Trend/Momentum/
Volatility/Volume categories, each combinable with several signal
patterns, freely adjustable numeric parameters (lengths, thresholds,
stop-loss/take-profit %), and both indicator/strategy output. The
combinatorial space this covers is genuinely in the thousands+ of
distinct, working scripts (see `estimate_combination_count()` for the
actual math) -- but the honest framing is "a huge, flexible combination
space", not a literal library of 10,000 pre-written files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IndicatorCategory(str, Enum):
    TREND = "Trend"
    MOMENTUM = "Momentum"
    VOLATILITY = "Volatility"
    VOLUME = "Volume"


@dataclass
class IndicatorSpec:
    id: str
    label: str
    category: IndicatorCategory
    # Pine expression template; {length} etc. filled from params.
    calc_lines: list[str]
    value_var: str  # the primary variable this indicator exposes
    is_overlay_friendly: bool  # can be plotted directly on the price chart
    default_length: int = 14
    supports_threshold: bool = False  # has natural overbought/oversold bounds
    default_overbought: float = 70.0
    default_oversold: float = 30.0
    is_band: bool = False  # exposes upper/lower (value_var_upper/value_var_lower)


INDICATORS: dict[str, IndicatorSpec] = {
    "sma": IndicatorSpec(
        id="sma",
        label="SMA (Simple Moving Average)",
        category=IndicatorCategory.TREND,
        calc_lines=["{var} = ta.sma(close, {length})"],
        value_var="maLine",
        is_overlay_friendly=True,
        default_length=20,
    ),
    "ema": IndicatorSpec(
        id="ema",
        label="EMA (Exponential Moving Average)",
        category=IndicatorCategory.TREND,
        calc_lines=["{var} = ta.ema(close, {length})"],
        value_var="maLine",
        is_overlay_friendly=True,
        default_length=20,
    ),
    "wma": IndicatorSpec(
        id="wma",
        label="WMA (Weighted Moving Average)",
        category=IndicatorCategory.TREND,
        calc_lines=["{var} = ta.wma(close, {length})"],
        value_var="maLine",
        is_overlay_friendly=True,
        default_length=20,
    ),
    "vwma": IndicatorSpec(
        id="vwma",
        label="VWMA (Volume-Weighted MA)",
        category=IndicatorCategory.TREND,
        calc_lines=["{var} = ta.vwma(close, {length})"],
        value_var="maLine",
        is_overlay_friendly=True,
        default_length=20,
    ),
    "hma": IndicatorSpec(
        id="hma",
        label="Hull Moving Average",
        category=IndicatorCategory.TREND,
        calc_lines=["{var} = ta.hma(close, {length})"],
        value_var="maLine",
        is_overlay_friendly=True,
        default_length=20,
    ),
    "supertrend": IndicatorSpec(
        id="supertrend",
        label="SuperTrend",
        category=IndicatorCategory.TREND,
        calc_lines=[
            "[{var}, stDirection] = ta.supertrend({mult}, {length})",
        ],
        value_var="stLine",
        is_overlay_friendly=True,
        default_length=10,
    ),
    "psar": IndicatorSpec(
        id="psar",
        label="Parabolic SAR",
        category=IndicatorCategory.TREND,
        calc_lines=["{var} = ta.sar(0.02, 0.02, 0.2)"],
        value_var="sarLine",
        is_overlay_friendly=True,
        default_length=14,
    ),
    "adx": IndicatorSpec(
        id="adx",
        label="ADX (Trend Strength)",
        category=IndicatorCategory.TREND,
        calc_lines=[
            "[diPlus, diMinus, {var}] = ta.dmi({length}, {length})",
        ],
        value_var="adxLine",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=25.0,
        default_oversold=15.0,
    ),
    "rsi": IndicatorSpec(
        id="rsi",
        label="RSI (Relative Strength Index)",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.rsi(close, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=70.0,
        default_oversold=30.0,
    ),
    "stoch": IndicatorSpec(
        id="stoch",
        label="Stochastic %K",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.stoch(close, high, low, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=80.0,
        default_oversold=20.0,
    ),
    "cci": IndicatorSpec(
        id="cci",
        label="CCI (Commodity Channel Index)",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.cci(close, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=20,
        supports_threshold=True,
        default_overbought=100.0,
        default_oversold=-100.0,
    ),
    "willr": IndicatorSpec(
        id="willr",
        label="Williams %R",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.wpr({length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=-20.0,
        default_oversold=-80.0,
    ),
    "roc": IndicatorSpec(
        id="roc",
        label="ROC (Rate of Change)",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.roc(close, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=12,
        supports_threshold=True,
        default_overbought=5.0,
        default_oversold=-5.0,
    ),
    "mom": IndicatorSpec(
        id="mom",
        label="Momentum",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.mom(close, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=10,
        supports_threshold=True,
        default_overbought=0.0,
        default_oversold=0.0,
    ),
    "ao": IndicatorSpec(
        id="ao",
        label="Awesome Oscillator",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["{var} = ta.sma(hl2, 5) - ta.sma(hl2, 34)"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=5,
        supports_threshold=True,
        default_overbought=0.0,
        default_oversold=0.0,
    ),
    "macd": IndicatorSpec(
        id="macd",
        label="MACD Line",
        category=IndicatorCategory.MOMENTUM,
        calc_lines=["[{var}, macdSignalLine, macdHist] = ta.macd(close, 12, 26, 9)"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=12,
        supports_threshold=True,
        default_overbought=0.0,
        default_oversold=0.0,
    ),
    "bb": IndicatorSpec(
        id="bb",
        label="Bollinger Bands",
        category=IndicatorCategory.VOLATILITY,
        calc_lines=[
            "bbBasis = ta.sma(close, {length})",
            "bbDev = {mult} * ta.stdev(close, {length})",
            "{var}Upper = bbBasis + bbDev",
            "{var}Lower = bbBasis - bbDev",
        ],
        value_var="band",
        is_overlay_friendly=True,
        default_length=20,
        is_band=True,
    ),
    "keltner": IndicatorSpec(
        id="keltner",
        label="Keltner Channel",
        category=IndicatorCategory.VOLATILITY,
        calc_lines=[
            "kcBasis = ta.ema(close, {length})",
            "kcRange = ta.atr({length}) * {mult}",
            "{var}Upper = kcBasis + kcRange",
            "{var}Lower = kcBasis - kcRange",
        ],
        value_var="band",
        is_overlay_friendly=True,
        default_length=20,
        is_band=True,
    ),
    "donchian": IndicatorSpec(
        id="donchian",
        label="Donchian Channel",
        category=IndicatorCategory.VOLATILITY,
        calc_lines=[
            "{var}Upper = ta.highest(high, {length})",
            "{var}Lower = ta.lowest(low, {length})",
        ],
        value_var="band",
        is_overlay_friendly=True,
        default_length=20,
        is_band=True,
    ),
    "atr": IndicatorSpec(
        id="atr",
        label="ATR (Average True Range)",
        category=IndicatorCategory.VOLATILITY,
        calc_lines=["{var} = ta.atr({length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=1.5,
        default_oversold=0.5,
    ),
    "stdev": IndicatorSpec(
        id="stdev",
        label="Standard Deviation",
        category=IndicatorCategory.VOLATILITY,
        calc_lines=["{var} = ta.stdev(close, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=20,
        supports_threshold=True,
        default_overbought=1.0,
        default_oversold=0.2,
    ),
    "obv": IndicatorSpec(
        id="obv",
        label="OBV (On-Balance Volume)",
        category=IndicatorCategory.VOLUME,
        calc_lines=["{var} = ta.obv"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=0.0,
        default_oversold=0.0,
    ),
    "vwap": IndicatorSpec(
        id="vwap",
        label="VWAP",
        category=IndicatorCategory.VOLUME,
        calc_lines=["{var} = ta.vwap(hlc3)"],
        value_var="maLine",
        is_overlay_friendly=True,
        default_length=1,
    ),
    "mfi": IndicatorSpec(
        id="mfi",
        label="MFI (Money Flow Index)",
        category=IndicatorCategory.VOLUME,
        calc_lines=["{var} = ta.mfi(hlc3, {length})"],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=14,
        supports_threshold=True,
        default_overbought=80.0,
        default_oversold=20.0,
    ),
    "cmf": IndicatorSpec(
        id="cmf",
        label="Chaikin Money Flow",
        category=IndicatorCategory.VOLUME,
        calc_lines=[
            "cmfMF = ((close - low) - (high - close)) / (high - low) * volume",
            "{var} = ta.sma(cmfMF, {length}) / ta.sma(volume, {length})",
        ],
        value_var="oscValue",
        is_overlay_friendly=False,
        default_length=20,
        supports_threshold=True,
        default_overbought=0.0,
        default_oversold=0.0,
    ),
}


class SignalPattern(str, Enum):
    PRICE_CROSS_MA = "price_cross_ma"  # single overlay-friendly indicator
    MA_CROSSOVER = "ma_crossover"  # two overlay-friendly indicators
    OSCILLATOR_THRESHOLD = "oscillator_threshold"  # single threshold-capable indicator
    BAND_BREAKOUT = "band_breakout"  # single band indicator


SIGNAL_PATTERN_LABELS = {
    SignalPattern.PRICE_CROSS_MA: "Price crosses the indicator line",
    SignalPattern.MA_CROSSOVER: "Fast indicator crosses slow indicator (needs 2 picks)",
    SignalPattern.OSCILLATOR_THRESHOLD: "Oscillator crosses overbought/oversold",
    SignalPattern.BAND_BREAKOUT: "Price breaks above/below the band",
}


class RiskPreset(str, Enum):
    NONE = "none"
    FIXED_PERCENT = "fixed_percent"
    ATR_BASED = "atr_based"


RISK_PRESET_LABELS = {
    RiskPreset.NONE: "No stop-loss / take-profit",
    RiskPreset.FIXED_PERCENT: "Fixed % stop-loss / take-profit",
    RiskPreset.ATR_BASED: "ATR-multiple stop-loss / take-profit",
}


def indicators_for_pattern(pattern: SignalPattern) -> list[IndicatorSpec]:
    """Which indicators are valid choices for a given signal pattern."""
    if pattern == SignalPattern.PRICE_CROSS_MA:
        return [i for i in INDICATORS.values() if i.is_overlay_friendly and not i.is_band]
    if pattern == SignalPattern.MA_CROSSOVER:
        return [i for i in INDICATORS.values() if i.is_overlay_friendly and not i.is_band]
    if pattern == SignalPattern.OSCILLATOR_THRESHOLD:
        return [i for i in INDICATORS.values() if i.supports_threshold]
    if pattern == SignalPattern.BAND_BREAKOUT:
        return [i for i in INDICATORS.values() if i.is_band]
    return []


@dataclass
class BuilderSpec:
    title: str
    script_type: str  # "indicator" | "strategy"
    pattern: SignalPattern
    primary_indicator: str  # key into INDICATORS
    secondary_indicator: str | None = None  # only for MA_CROSSOVER
    length: int = 14
    length2: int = 21
    overbought: float | None = None
    oversold: float | None = None
    band_mult: float = 2.0
    risk: RiskPreset = RiskPreset.NONE
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 4.0
    atr_stop_mult: float = 2.0
    atr_tp_mult: float = 3.0
    overlay: bool = True
    pine_version: int = 6


def _emit_indicator(spec: IndicatorSpec, var_name: str, length: int, mult: float = 2.0) -> list[str]:
    lines = []
    for tmpl in spec.calc_lines:
        lines.append(tmpl.format(var=var_name, length=length, mult=mult))
    return lines


def build_from_spec(spec: BuilderSpec) -> str:
    """Render a complete Pine v6 script from a BuilderSpec."""
    calc_lines: list[str] = []
    plot_lines: list[str] = []
    long_condition = "false"
    short_condition = "false"

    primary = INDICATORS[spec.primary_indicator]

    if spec.pattern == SignalPattern.PRICE_CROSS_MA:
        var = f"{primary.id}Line"
        calc_lines += _emit_indicator(primary, var, spec.length)
        long_condition = f"ta.crossover(close, {var})"
        short_condition = f"ta.crossunder(close, {var})"
        plot_lines.append(f'plot({var}, title="{primary.label}", color=color.new(color.blue, 0), linewidth=2)')

    elif spec.pattern == SignalPattern.MA_CROSSOVER:
        secondary = INDICATORS[spec.secondary_indicator or spec.primary_indicator]
        fast_var, slow_var = "fastLine", "slowLine"
        calc_lines += _emit_indicator(primary, fast_var, spec.length)
        calc_lines += _emit_indicator(secondary, slow_var, spec.length2)
        long_condition = f"ta.crossover({fast_var}, {slow_var})"
        short_condition = f"ta.crossunder({fast_var}, {slow_var})"
        plot_lines.append(
            f'plot({fast_var}, title="Fast {primary.label}", color=color.new(color.teal, 0), linewidth=2)'
        )
        plot_lines.append(
            f'plot({slow_var}, title="Slow {secondary.label}", color=color.new(color.orange, 0), linewidth=2)'
        )

    elif spec.pattern == SignalPattern.OSCILLATOR_THRESHOLD:
        var = "oscValue"
        calc_lines += _emit_indicator(primary, var, spec.length)
        ob = spec.overbought if spec.overbought is not None else primary.default_overbought
        os_ = spec.oversold if spec.oversold is not None else primary.default_oversold
        calc_lines.append(f"obLevel = {ob}")
        calc_lines.append(f"osLevel = {os_}")
        long_condition = f"ta.crossover({var}, osLevel)"
        short_condition = f"ta.crossunder({var}, obLevel)"
        plot_lines.append(f'plot({var}, title="{primary.label}", color=color.new(color.purple, 0))')
        plot_lines.append('plot(obLevel, title="Overbought", color=color.new(color.red, 40))')
        plot_lines.append('plot(osLevel, title="Oversold", color=color.new(color.green, 40))')

    elif spec.pattern == SignalPattern.BAND_BREAKOUT:
        var = "band"
        calc_lines += _emit_indicator(primary, var, spec.length, spec.band_mult)
        long_condition = f"ta.crossover(close, {var}Upper)"
        short_condition = f"ta.crossunder(close, {var}Lower)"
        plot_lines.append(f'plot({var}Upper, title="Upper Band", color=color.new(color.red, 30))')
        plot_lines.append(f'plot({var}Lower, title="Lower Band", color=color.new(color.green, 30))')

    lines: list[str] = [f"//@version={spec.pine_version}"]

    if spec.script_type == "strategy":
        lines.append(f'strategy(title="{spec.title}", overlay={"true" if spec.overlay else "false"},')
        lines.append("     initial_capital=10000, default_qty_type=strategy.percent_of_equity,")
        lines.append("     default_qty_value=10, commission_type=strategy.commission.percent, commission_value=0.05)")
    else:
        lines.append(f'indicator(title="{spec.title}", overlay={"true" if spec.overlay else "false"})')

    lines.append("")
    lines.append("// ---- Calculations ----")
    lines.extend(calc_lines)
    lines.append("")
    lines.append("// ---- Signal ----")
    lines.append(f"longCondition = {long_condition}")
    lines.append(f"shortCondition = {short_condition}")

    if spec.script_type == "strategy":
        lines.append("")
        lines.append("// ---- Orders ----")
        lines.append("if longCondition")
        lines.append('    strategy.entry("Long", strategy.long)')
        lines.append("")
        lines.append("if shortCondition")
        lines.append('    strategy.entry("Short", strategy.short)')

        if spec.risk == RiskPreset.FIXED_PERCENT:
            lines.append("")
            lines.append("// ---- Risk management (fixed %) ----")
            lines.append(
                f'strategy.exit("Exit Long", from_entry="Long", '
                f"stop=close * (1 - {spec.stop_loss_pct} / 100), "
                f"limit=close * (1 + {spec.take_profit_pct} / 100))"
            )
            lines.append(
                f'strategy.exit("Exit Short", from_entry="Short", '
                f"stop=close * (1 + {spec.stop_loss_pct} / 100), "
                f"limit=close * (1 - {spec.take_profit_pct} / 100))"
            )
        elif spec.risk == RiskPreset.ATR_BASED:
            lines.append("")
            lines.append("// ---- Risk management (ATR-based) ----")
            lines.append("riskAtr = ta.atr(14)")
            lines.append(
                f'strategy.exit("Exit Long", from_entry="Long", '
                f"stop=close - riskAtr * {spec.atr_stop_mult}, "
                f"limit=close + riskAtr * {spec.atr_tp_mult})"
            )
            lines.append(
                f'strategy.exit("Exit Short", from_entry="Short", '
                f"stop=close + riskAtr * {spec.atr_stop_mult}, "
                f"limit=close - riskAtr * {spec.atr_tp_mult})"
            )
    else:
        lines.append("")
        lines.append('alertcondition(longCondition, title="Long Signal", message="Long signal triggered")')
        lines.append('alertcondition(shortCondition, title="Short Signal", message="Short signal triggered")')

    lines.append("")
    lines.append("// ---- Plots ----")
    lines.extend(plot_lines)
    lines.append(
        'plotshape(longCondition, title="Long", location=location.belowbar,\n'
        "     color=color.new(color.green, 0), style=shape.triangleup, size=size.tiny)"
    )
    lines.append(
        'plotshape(shortCondition, title="Short", location=location.abovebar,\n'
        "     color=color.new(color.red, 0), style=shape.triangledown, size=size.tiny)"
    )

    return "\n".join(lines).strip("\n") + "\n"


def estimate_combination_count() -> dict[str, int]:
    """Rough, honest count of the distinct *structural* combinations this
    builder can produce (excludes the effectively unlimited variation from
    freely adjustable numeric parameters like length/thresholds/%)."""
    overlay_friendly = [i for i in INDICATORS.values() if i.is_overlay_friendly and not i.is_band]
    threshold_capable = [i for i in INDICATORS.values() if i.supports_threshold]
    band_indicators = [i for i in INDICATORS.values() if i.is_band]

    n_price_cross = len(overlay_friendly)
    n_ma_crossover = len(overlay_friendly) * len(overlay_friendly)  # fast x slow, order matters
    n_threshold = len(threshold_capable)
    n_band = len(band_indicators)

    structural_patterns = n_price_cross + n_ma_crossover + n_threshold + n_band
    script_types = 2  # indicator, strategy
    risk_presets = len(RiskPreset)  # only meaningful for strategy, counted loosely here

    total_structural = structural_patterns * script_types * risk_presets

    return {
        "indicators": len(INDICATORS),
        "price_cross_combos": n_price_cross,
        "ma_crossover_combos": n_ma_crossover,
        "threshold_combos": n_threshold,
        "band_combos": n_band,
        "structural_patterns": structural_patterns,
        "structural_total_with_type_and_risk": total_structural,
    }
