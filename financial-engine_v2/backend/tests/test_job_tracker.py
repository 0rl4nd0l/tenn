"""Tests for the JobTracker lifecycle and event bus."""

from __future__ import annotations

import asyncio

import pytest

from app.services.job_tracker import JobHandle, JobTracker, init_tracker, get_tracker
from app.services.ops_store import OpsStore


def _make_tracker(tmp_path) -> JobTracker:
    store = OpsStore(tmp_path / "ops.db")
    return JobTracker(store)


# ── Lifecycle tests ────────────────────────────────────────────────────────


def test_create_job_returns_handle(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction",
        job_family="pipeline",
        title="Extract doc-1",
    )
    assert isinstance(handle, JobHandle)
    assert handle.job_type == "extraction"
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "pending"


def test_start_job_sets_running(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Start test"
    )
    tracker.start_job(handle.job_id)
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "running"
    assert run["started_at"] is not None


def test_complete_job_sets_succeeded(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Complete test"
    )
    tracker.start_job(handle.job_id)
    tracker.complete_job(handle.job_id, summary="All done")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "succeeded"
    assert run["completed_at"] is not None
    assert run["summary"] == "All done"
    assert run["elapsed_ms"] >= 0


def test_fail_job_sets_failed(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Fail test"
    )
    tracker.start_job(handle.job_id)
    tracker.fail_job(handle.job_id, "Parser crash")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "failed"
    assert run["summary"] == "Parser crash"


def test_cancel_job(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Cancel test"
    )
    tracker.cancel_job(handle.job_id, "User cancelled")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "cancelled"


def test_change_phase(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Phase test"
    )
    tracker.start_job(handle.job_id)
    tracker.change_phase(handle.job_id, "parser")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["phase"] == "parser"


def test_record_progress(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="backfill",
        job_family="celery",
        title="Progress test",
        total_items=10,
    )
    tracker.start_job(handle.job_id)
    tracker.record_progress(
        handle.job_id, current=3, total=10, current_item_label="BHP"
    )
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["succeeded_items"] == 3
    assert run["current_item_label"] == "BHP"


def test_record_item_succeeded_increments(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Item test"
    )
    tracker.start_job(handle.job_id)
    tracker.record_item_succeeded(handle.job_id, "doc-1")
    tracker.record_item_succeeded(handle.job_id, "doc-2")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["succeeded_items"] == 2


def test_record_item_failed_increments(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Fail item test"
    )
    tracker.start_job(handle.job_id)
    tracker.record_item_failed(handle.job_id, "doc-3", error="Parse error")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["failed_items"] == 1


def test_record_warning_increments(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Warning test"
    )
    tracker.record_warning(handle.job_id, "Missing optional field")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["warning_count"] == 1


def test_add_artifact(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Artifact test"
    )
    art = tracker.add_artifact(
        handle.job_id,
        artifact_type="report",
        artifact_label="Summary JSON",
        artifact_path="/tmp/out.json",
    )
    assert art["artifact_type"] == "report"
    artifacts = tracker.store.list_job_artifacts(handle.job_id)
    assert len(artifacts) == 1


def test_full_lifecycle_creates_events(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Full lifecycle"
    )
    tracker.start_job(handle.job_id)
    tracker.change_phase(handle.job_id, "parser")
    tracker.record_progress(handle.job_id, current=1, total=2)
    tracker.record_item_succeeded(handle.job_id, "doc-1")
    tracker.record_warning(handle.job_id, "Minor issue")
    tracker.complete_job(handle.job_id, summary="Done")

    events = tracker.store.list_job_events(handle.job_id)
    event_types = [e["event_type"] for e in events]
    assert "job.created" in event_types
    assert "job.started" in event_types
    assert "job.phase_changed" in event_types
    assert "job.progress" in event_types
    assert "job.item_succeeded" in event_types
    assert "job.warning" in event_types
    assert "job.completed" in event_types


# ── Context manager tests ──────────────────────────────────────────────────


def test_tracked_job_success(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    with tracker.tracked_job(
        job_type="download",
        job_family="celery",
        title="Download PDF",
    ) as handle:
        assert isinstance(handle, JobHandle)
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "succeeded"


def test_tracked_job_failure(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    with pytest.raises(ValueError, match="boom"):
        with tracker.tracked_job(
            job_type="download",
            job_family="celery",
            title="Download PDF fail",
        ) as handle:
            raise ValueError("boom")
    run = tracker.store.get_job_run(handle.job_id)
    assert run is not None
    assert run["status"] == "failed"
    assert "boom" in (run["summary"] or "")


# ── Event bus tests ────────────────────────────────────────────────────────


def test_subscriber_receives_events(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    q = tracker.subscribe()
    handle = tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Sub test"
    )
    assert not q.empty()
    event = q.get_nowait()
    assert event["event_type"] == "job.created"
    assert event["job_id"] == handle.job_id
    tracker.unsubscribe(q)


def test_multiple_subscribers(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    q1 = tracker.subscribe()
    q2 = tracker.subscribe()
    tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Multi sub"
    )
    assert not q1.empty()
    assert not q2.empty()
    tracker.unsubscribe(q1)
    tracker.unsubscribe(q2)


def test_unsubscribe_stops_delivery(tmp_path) -> None:
    tracker = _make_tracker(tmp_path)
    q = tracker.subscribe()
    tracker.unsubscribe(q)
    tracker.create_job(
        job_type="extraction", job_family="pipeline", title="Unsub test"
    )
    assert q.empty()


def test_queue_overflow_drops_oldest(tmp_path) -> None:
    store = OpsStore(tmp_path / "ops.db")
    tracker = JobTracker(store)
    q = tracker.subscribe()
    # Fill queue to capacity
    for i in range(1001):
        tracker.create_job(
            job_type="extraction", job_family="pipeline", title=f"Overflow {i}"
        )
    # Queue should still be functional (not deadlocked)
    assert q.qsize() <= 1000


# ── Singleton tests ────────────────────────────────────────────────────────


def test_init_and_get_tracker(tmp_path) -> None:
    store = OpsStore(tmp_path / "ops.db")
    tracker = init_tracker(store)
    assert get_tracker() is tracker
