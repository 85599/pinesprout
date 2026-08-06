from __future__ import annotations

import pytest

from pinesprout.core.linter import lint_source
from pinesprout.core.parser import parse
from pinesprout.generators.template_generator import (
    TemplateKind,
    TemplateSpec,
    available_templates,
    generate_from_template,
)


def test_available_templates_nonempty():
    assert len(available_templates()) >= 6


@pytest.mark.parametrize("kind", list(TemplateKind))
def test_every_template_produces_valid_pine_structure(kind):
    spec = TemplateSpec(kind=kind, title="Test Script")
    source = generate_from_template(spec)
    program = parse(source)
    assert program.pine_version == 6
    assert len(program.declarations) > 0


@pytest.mark.parametrize("kind", list(TemplateKind))
def test_every_template_lints_without_errors(kind):
    spec = TemplateSpec(kind=kind, title="Test Script")
    source = generate_from_template(spec)
    result = lint_source(source)
    assert result.error_count == 0, result.issues


def test_ema_cross_indicator_has_expected_inputs():
    spec = TemplateSpec(kind=TemplateKind.EMA_CROSS_INDICATOR, title="EMA")
    source = generate_from_template(spec)
    assert "fastLen" in source
    assert "slowLen" in source
    assert "ta.crossover" in source


def test_rsi_strategy_has_stop_loss_logic():
    spec = TemplateSpec(kind=TemplateKind.RSI_STRATEGY, title="RSI Strat")
    source = generate_from_template(spec)
    assert "strategy.exit" in source


def test_template_title_and_overlay_applied():
    spec = TemplateSpec(kind=TemplateKind.BLANK_INDICATOR, title="Custom Title", overlay=False)
    source = generate_from_template(spec)
    assert "Custom Title" in source
    assert "overlay=false" in source


def test_pivot_confluence_template_has_expected_structure():
    spec = TemplateSpec(kind=TemplateKind.PIVOT_CONFLUENCE, title="Pivots")
    source = generate_from_template(spec)
    assert "request.security" in source
    assert "pivotSet" in source
    assert "Confluence" in source


def test_pivot_confluence_template_formats_idempotently():
    from pinesprout.core.formatter import format_source

    spec = TemplateSpec(kind=TemplateKind.PIVOT_CONFLUENCE, title="Pivots")
    source = generate_from_template(spec)
    once = format_source(source)
    twice = format_source(once)
    assert once == twice
    assert "= >" not in once
