"""Deterministic template-based scaffold generation for indicators and strategies.

Unlike ``ai_generator`` (which calls out to Claude), this module produces
Pine Script from Jinja2 templates with sensible, well-known defaults
(e.g. an EMA-crossover indicator, an RSI mean-reversion strategy). It
requires no network access or API key, so it always works.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from pinesprout.generators.jinja_env import build_env


class InputSpec(BaseModel):
    name: str
    type: str
    default: str
    label: str
    extra: str | None = None


class PlotSpec(BaseModel):
    expr: str
    title: str
    color: str = "color.blue"
    linewidth: int | None = None


class AlertSpec(BaseModel):
    condition: str
    title: str
    message: str


class TemplateKind(str, Enum):
    EMA_CROSS_INDICATOR = "ema-cross-indicator"
    RSI_INDICATOR = "rsi-indicator"
    BLANK_INDICATOR = "blank-indicator"
    RSI_STRATEGY = "rsi-strategy"
    EMA_CROSS_STRATEGY = "ema-cross-strategy"
    BLANK_STRATEGY = "blank-strategy"
    PIVOT_CONFLUENCE = "pivot-confluence-levels"


class TemplateSpec(BaseModel):
    kind: TemplateKind
    title: str
    shorttitle: str = Field(default="")
    overlay: bool = True
    pine_version: int = 6


_PRESETS: dict[TemplateKind, dict[str, object]] = {
    TemplateKind.EMA_CROSS_INDICATOR: {
        "template": "indicator.pine.j2",
        "overlay": True,
        "inputs": [
            InputSpec(name="fastLen", type="int", default="9", label="Fast EMA Length"),
            InputSpec(name="slowLen", type="int", default="21", label="Slow EMA Length"),
        ],
        "calc_lines": [
            "fastEma = ta.ema(close, fastLen)",
            "slowEma = ta.ema(close, slowLen)",
            "bullish = ta.crossover(fastEma, slowEma)",
            "bearish = ta.crossunder(fastEma, slowEma)",
        ],
        "plots": [
            PlotSpec(expr="fastEma", title="Fast EMA", color="color.new(color.teal, 0)"),
            PlotSpec(expr="slowEma", title="Slow EMA", color="color.new(color.orange, 0)"),
        ],
        "alerts": [
            AlertSpec(condition="bullish", title="Bullish Cross", message="Fast EMA crossed above Slow EMA"),
            AlertSpec(condition="bearish", title="Bearish Cross", message="Fast EMA crossed below Slow EMA"),
        ],
    },
    TemplateKind.RSI_INDICATOR: {
        "template": "indicator.pine.j2",
        "overlay": False,
        "inputs": [
            InputSpec(name="rsiLen", type="int", default="14", label="RSI Length"),
            InputSpec(name="obLevel", type="int", default="70", label="Overbought Level"),
            InputSpec(name="osLevel", type="int", default="30", label="Oversold Level"),
        ],
        "calc_lines": [
            "rsiValue = ta.rsi(close, rsiLen)",
        ],
        "plots": [
            PlotSpec(expr="rsiValue", title="RSI", color="color.purple"),
            PlotSpec(expr="obLevel", title="Overbought", color="color.red"),
            PlotSpec(expr="osLevel", title="Oversold", color="color.green"),
        ],
        "alerts": [
            AlertSpec(
                condition="ta.crossover(rsiValue, obLevel)",
                title="RSI Overbought",
                message="RSI crossed above overbought level",
            ),
            AlertSpec(
                condition="ta.crossunder(rsiValue, osLevel)",
                title="RSI Oversold",
                message="RSI crossed below oversold level",
            ),
        ],
    },
    TemplateKind.BLANK_INDICATOR: {
        "template": "indicator.pine.j2",
        "overlay": True,
        "inputs": [InputSpec(name="length", type="int", default="14", label="Length")],
        "calc_lines": ["value = ta.sma(close, length)"],
        "plots": [PlotSpec(expr="value", title="Value", color="color.blue")],
        "alerts": [],
    },
}

_STRATEGY_PRESETS: dict[TemplateKind, dict[str, object]] = {
    TemplateKind.RSI_STRATEGY: {
        "template": "strategy.pine.j2",
        "overlay": False,
        "inputs": [
            InputSpec(name="rsiLen", type="int", default="14", label="RSI Length"),
            InputSpec(name="obLevel", type="int", default="70", label="Overbought Level"),
            InputSpec(name="osLevel", type="int", default="30", label="Oversold Level"),
        ],
        "calc_lines": ["rsiValue = ta.rsi(close, rsiLen)"],
        "long_condition": "ta.crossover(rsiValue, osLevel)",
        "short_condition": "ta.crossunder(rsiValue, obLevel)",
        "plots": [PlotSpec(expr="rsiValue", title="RSI", color="color.purple")],
        "use_stop_loss": True,
        "stop_loss_pct": 2.0,
        "take_profit_pct": 4.0,
        "initial_capital": 10000,
        "default_qty_value": 10,
        "commission_value": 0.05,
    },
    TemplateKind.EMA_CROSS_STRATEGY: {
        "template": "strategy.pine.j2",
        "overlay": True,
        "inputs": [
            InputSpec(name="fastLen", type="int", default="9", label="Fast EMA Length"),
            InputSpec(name="slowLen", type="int", default="21", label="Slow EMA Length"),
        ],
        "calc_lines": [
            "fastEma = ta.ema(close, fastLen)",
            "slowEma = ta.ema(close, slowLen)",
        ],
        "long_condition": "ta.crossover(fastEma, slowEma)",
        "short_condition": "ta.crossunder(fastEma, slowEma)",
        "plots": [
            PlotSpec(expr="fastEma", title="Fast EMA", color="color.teal"),
            PlotSpec(expr="slowEma", title="Slow EMA", color="color.orange"),
        ],
        "use_stop_loss": True,
        "stop_loss_pct": 3.0,
        "take_profit_pct": 6.0,
        "initial_capital": 10000,
        "default_qty_value": 10,
        "commission_value": 0.05,
    },
    TemplateKind.BLANK_STRATEGY: {
        "template": "strategy.pine.j2",
        "overlay": True,
        "inputs": [InputSpec(name="length", type="int", default="14", label="Length")],
        "calc_lines": ["value = ta.sma(close, length)"],
        "long_condition": "ta.crossover(close, value)",
        "short_condition": "ta.crossunder(close, value)",
        "plots": [PlotSpec(expr="value", title="Value", color="color.blue")],
        "use_stop_loss": False,
        "stop_loss_pct": 2.0,
        "take_profit_pct": 4.0,
        "initial_capital": 10000,
        "default_qty_value": 10,
        "commission_value": 0.05,
    },
}


def available_templates() -> list[str]:
    return [k.value for k in TemplateKind]


def generate_from_template(spec: TemplateSpec) -> str:
    """Render a full Pine Script file for the requested template kind."""
    env = build_env()

    if spec.kind == TemplateKind.PIVOT_CONFLUENCE:
        template = env.get_template("pivot_confluence.pine.j2")
        rendered = template.render(
            pine_version=spec.pine_version,
            title=spec.title,
            shorttitle=spec.shorttitle or spec.title[:10],
        )
        lines = [ln.rstrip() for ln in rendered.splitlines()]
        return "\n".join(lines).strip("\n") + "\n"

    if spec.kind in _PRESETS:
        preset = _PRESETS[spec.kind]
    elif spec.kind in _STRATEGY_PRESETS:
        preset = _STRATEGY_PRESETS[spec.kind]
    else:
        raise ValueError(f"Unknown template kind: {spec.kind}")

    template = env.get_template(str(preset["template"]))
    context = {
        "pine_version": spec.pine_version,
        "title": spec.title,
        "shorttitle": spec.shorttitle or spec.title[:10],
        "overlay": spec.overlay if spec.overlay is not None else preset.get("overlay", True),
        "inputs": preset.get("inputs", []),
        "calc_lines": preset.get("calc_lines", []),
        "plots": preset.get("plots", []),
        "alerts": preset.get("alerts", []),
    }
    if preset["template"] == "strategy.pine.j2":
        context.update(
            long_condition=preset["long_condition"],
            short_condition=preset["short_condition"],
            use_stop_loss=preset["use_stop_loss"],
            stop_loss_pct=preset["stop_loss_pct"],
            take_profit_pct=preset["take_profit_pct"],
            initial_capital=preset["initial_capital"],
            default_qty_value=preset["default_qty_value"],
            commission_value=preset["commission_value"],
        )

    rendered = template.render(**context)
    # Collapse excessive blank lines produced by conditional Jinja blocks.
    lines = [ln.rstrip() for ln in rendered.splitlines()]
    cleaned: list[str] = []
    blank_streak = 0
    for ln in lines:
        if ln == "":
            blank_streak += 1
            if blank_streak > 1:
                continue
        else:
            blank_streak = 0
        cleaned.append(ln)
    return "\n".join(cleaned).strip("\n") + "\n"
