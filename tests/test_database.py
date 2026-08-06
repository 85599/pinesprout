from __future__ import annotations

from pathlib import Path

from pinesprout.db.database import Database


def test_database_creates_schema(tmp_path: Path):
    Database(path=tmp_path / "test.db")
    assert (tmp_path / "test.db").exists()


def test_record_and_retrieve_run(tmp_path: Path):
    db = Database(path=tmp_path / "test.db")
    run_id = db.record_run("lint", target="my_script.pine", summary="0 errors")
    assert run_id > 0

    runs = db.recent_runs(limit=10)
    assert len(runs) == 1
    assert runs[0].command == "lint"
    assert runs[0].target == "my_script.pine"


def test_recent_runs_filters_by_command(tmp_path: Path):
    db = Database(path=tmp_path / "test.db")
    db.record_run("lint", target="a.pine")
    db.record_run("format", target="b.pine")
    db.record_run("lint", target="c.pine")

    lint_runs = db.recent_runs(command="lint")
    assert len(lint_runs) == 2
    assert all(r.command == "lint" for r in lint_runs)


def test_recent_runs_respects_limit(tmp_path: Path):
    db = Database(path=tmp_path / "test.db")
    for i in range(5):
        db.record_run("lint", target=f"file{i}.pine")
    runs = db.recent_runs(limit=2)
    assert len(runs) == 2


def test_recent_runs_ordered_newest_first(tmp_path: Path):
    db = Database(path=tmp_path / "test.db")
    db.record_run("lint", target="first.pine")
    db.record_run("lint", target="second.pine")
    runs = db.recent_runs(limit=10)
    assert runs[0].target == "second.pine"


def test_clear_removes_all_runs(tmp_path: Path):
    db = Database(path=tmp_path / "test.db")
    db.record_run("lint", target="a.pine")
    db.clear()
    assert db.recent_runs() == []


def test_run_details_json_round_trips(tmp_path: Path):
    db = Database(path=tmp_path / "test.db")
    db.record_run("lint", target="a.pine", details={"errors": 2, "warnings": ["x", "y"]})
    runs = db.recent_runs()
    assert runs[0].details["errors"] == 2
    assert runs[0].details["warnings"] == ["x", "y"]
