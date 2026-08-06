from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def messy_v4_source() -> str:
    return (FIXTURES_DIR / "messy_v4.pine").read_text(encoding="utf-8")


@pytest.fixture()
def clean_v6_source() -> str:
    return (FIXTURES_DIR / "clean_v6.pine").read_text(encoding="utf-8")


@pytest.fixture()
def tmp_pinesprout_db(tmp_path, monkeypatch):
    db_path = tmp_path / "pinesprout_test.db"
    monkeypatch.setenv("PINESPROUT_DB", str(db_path))
    return db_path
