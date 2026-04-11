"""Tests for the OpsStore SQLite data layer."""

from __future__ import annotations

import json
import threading

from app.services.ops_store import OpsStore


def _make_store(tmp_path) -> OpsStore:
    return OpsStore(tmp_path / "ops.db")


def test_create_and_get_job_run(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="j1",
        job_type="extraction",
        job_family="pipeline",
        title="Extract doc-42",
        ticker="BHP",
        total_items=3,
        metadata={"doc_id": "doc-42"},
    )
    run = store.get_job_run("j1")
    assert run is not None
    assert run["job_id"] == "j1"
    assert run["job_type"] == "extraction"
    assert run["ticker"] == "BHP"
    assert run["total_items"] == 3
    assert run["status"] == "pending"
    assert run["metadata"] == {"doc_id": "doc-42"}


def test_get_missing_job_run_returns_none(tmp_path) -> None:
    store = _make_store(tmp_path)
    assert store.get_job_run("nonexistent") is None


def test_update_job_run(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="j2",
        job_type="backfill",
        job_family="celery",
        title="Backfill CBA",
    )
    updated = store.update_job_run("j2", status="running", phase="downloading")
    assert updated is True
    run = store.get_job_run("j2")
    assert run is not None
    assert run["status"] == "running"
    assert run["phase"] == "downloading"


def test_update_nonexistent_job_returns_false(tmp_path) -> None:
    store = _make_store(tmp_path)
    assert store.update_job_run("ghost", status="running") is False


def test_list_job_runs_with_filters(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="a", job_type="extraction", job_family="pipeline", title="A"
    )
    store.create_job_run(
        job_id="b",
        job_type="backfill",
        job_family="celery",
        title="B",
        ticker="CBA",
    )
    store.update_job_run("a", status="running")

    runs_all, total_all = store.list_job_runs()
    assert total_all == 2

    runs_running, total_running = store.list_job_runs(status="running")
    assert total_running == 1
    assert runs_running[0]["job_id"] == "a"

    runs_type, total_type = store.list_job_runs(job_type="backfill")
    assert total_type == 1

    runs_ticker, total_ticker = store.list_job_runs(ticker="cba")
    assert total_ticker == 1
    assert runs_ticker[0]["ticker"] == "CBA"


def test_list_job_runs_pagination(tmp_path) -> None:
    store = _make_store(tmp_path)
    for i in range(5):
        store.create_job_run(
            job_id=f"p{i}",
            job_type="extraction",
            job_family="pipeline",
            title=f"Job {i}",
        )
    runs, total = store.list_job_runs(limit=2, offset=0)
    assert total == 5
    assert len(runs) == 2

    runs2, _ = store.list_job_runs(limit=2, offset=2)
    assert len(runs2) == 2
    # Ensure no overlap
    ids1 = {r["job_id"] for r in runs}
    ids2 = {r["job_id"] for r in runs2}
    assert not ids1 & ids2


def test_list_job_runs_comma_separated_status(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="s1", job_type="extraction", job_family="pipeline", title="S1"
    )
    store.create_job_run(
        job_id="s2", job_type="extraction", job_family="pipeline", title="S2"
    )
    store.update_job_run("s1", status="running")
    store.update_job_run("s2", status="succeeded")

    runs, total = store.list_job_runs(status="running,pending")
    assert total == 1
    assert runs[0]["job_id"] == "s1"


def test_add_and_list_job_events(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="e1", job_type="extraction", job_family="pipeline", title="E1"
    )
    store.add_job_event(
        job_id="e1",
        event_type="job.started",
        message="Starting extraction",
        phase="parser",
    )
    store.add_job_event(
        job_id="e1",
        event_type="job.progress",
        message="50%",
        progress_current=1,
        progress_total=2,
        progress_pct=50.0,
    )
    events = store.list_job_events("e1")
    assert len(events) == 2
    assert events[0]["event_type"] == "job.started"
    assert events[1]["progress_pct"] == 50.0


def test_add_and_list_job_artifacts(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="art1", job_type="extraction", job_family="pipeline", title="Art"
    )
    store.add_job_artifact(
        job_id="art1",
        artifact_type="report",
        artifact_label="Extraction summary",
        artifact_path="/tmp/report.json",
        metadata={"format": "json"},
    )
    artifacts = store.list_job_artifacts("art1")
    assert len(artifacts) == 1
    assert artifacts[0]["artifact_type"] == "report"
    assert artifacts[0]["metadata"] == {"format": "json"}


def test_cleanup_removes_old_jobs(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="old1", job_type="extraction", job_family="pipeline", title="Old"
    )
    # Manually backdate the queued_at
    store.conn.execute(
        "UPDATE job_runs SET queued_at = '2020-01-01T00:00:00+00:00' WHERE job_id = 'old1'"
    )
    store.conn.commit()
    store.add_job_event(
        job_id="old1", event_type="job.created", message="Created"
    )
    store.add_job_artifact(
        job_id="old1",
        artifact_type="log",
        artifact_label="Log",
    )

    removed = store.cleanup(max_age_days=1)
    assert removed == 1
    assert store.get_job_run("old1") is None
    assert store.list_job_events("old1") == []
    assert store.list_job_artifacts("old1") == []


def test_concurrent_writes(tmp_path) -> None:
    store = _make_store(tmp_path)
    errors: list[Exception] = []

    def create_jobs(prefix: str) -> None:
        try:
            for i in range(10):
                store.create_job_run(
                    job_id=f"{prefix}-{i}",
                    job_type="extraction",
                    job_family="pipeline",
                    title=f"Job {prefix}-{i}",
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=create_jobs, args=(f"t{t}",)) for t in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent write errors: {errors}"
    runs, total = store.list_job_runs(limit=100)
    assert total == 30


def test_metadata_json_roundtrip(tmp_path) -> None:
    store = _make_store(tmp_path)
    meta = {"nested": {"key": [1, 2, 3]}, "flag": True}
    store.create_job_run(
        job_id="meta1",
        job_type="extraction",
        job_family="pipeline",
        title="Meta test",
        metadata=meta,
    )
    run = store.get_job_run("meta1")
    assert run is not None
    assert run["metadata"] == meta


def test_update_metadata(tmp_path) -> None:
    store = _make_store(tmp_path)
    store.create_job_run(
        job_id="m2",
        job_type="extraction",
        job_family="pipeline",
        title="M2",
        metadata={"v": 1},
    )
    store.update_job_run("m2", metadata={"v": 2, "extra": True})
    run = store.get_job_run("m2")
    assert run is not None
    assert run["metadata"] == {"v": 2, "extra": True}
