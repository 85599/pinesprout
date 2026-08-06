from __future__ import annotations

from pinesprout.core.upgrader import detect_version, upgrade_source


def test_detect_version_v4():
    assert detect_version("//@version=4\nstudy('x')\n") == 4


def test_detect_version_none_when_absent():
    assert detect_version("indicator('x')\n") is None


def test_upgrade_v4_to_v6_bumps_pragma(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=6)
    assert result.final_version == 6
    assert "//@version=6" in result.upgraded_source
    assert "//@version=4" not in result.upgraded_source


def test_upgrade_replaces_study_with_indicator(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=6)
    assert "indicator(" in result.upgraded_source
    assert "study(" not in result.upgraded_source


def test_upgrade_namespaces_ta_functions(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=6)
    assert "ta.rsi(" in result.upgraded_source
    assert "ta.sma(" in result.upgraded_source
    assert "ta.crossover(" in result.upgraded_source


def test_upgrade_namespaces_security(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=6)
    assert "request.security(" in result.upgraded_source


def test_upgrade_records_applied_migrations(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=6)
    descriptions = [m.description for m in result.applied_migrations]
    assert "study() -> indicator()" in descriptions


def test_upgrade_to_v5_only_stops_at_v5(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=5)
    assert result.final_version == 5
    assert "//@version=5" in result.upgraded_source


def test_upgrade_already_current_version_is_noop(clean_v6_source):
    result = upgrade_source(clean_v6_source, target_version=6)
    assert result.original_version == 6
    assert result.final_version == 6
    assert len(result.applied_migrations) == 0


def test_upgrade_provides_manual_review_notes(messy_v4_source):
    result = upgrade_source(messy_v4_source, target_version=6)
    assert len(result.manual_review_needed) > 0
