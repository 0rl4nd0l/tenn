from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import extraction_run_observability as obs


def test_run_status_tracks_queue_wait_stage_timings_and_missing_stage_warnings(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(obs, "RUN_STATUS_ROOT", tmp_path / "run_status")

    start = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    ticks = iter(start + timedelta(seconds=offset) for offset in range(12))
    monkeypatch.setattr(obs, "_now", lambda: next(ticks))

    obs.initialize_run_status(
        run_id="run-1",
        document_id="doc-1",
        requested_method="docling",
        strict_method=True,
        details={"trigger": "api_process_document"},
    )
    obs.emit_run_event(
        run_id="run-1",
        document_id="doc-1",
        requested_method="docling",
        actual_method="docling",
        strict_method=True,
        stage="starting",
        status="running",
        message="Worker started.",
    )
    obs.emit_run_event(
        run_id="run-1",
        document_id="doc-1",
        requested_method="docling",
        actual_method="docling",
        strict_method=True,
        stage="parser",
        status="running",
        message="Parser started.",
    )
    obs.emit_run_event(
        run_id="run-1",
        document_id="doc-1",
        requested_method="docling",
        actual_method="docling",
        strict_method=True,
        stage="parser",
        status="succeeded",
        message="Parser completed.",
    )
    payload = obs.emit_run_event(
        run_id="run-1",
        document_id="doc-1",
        requested_method="docling",
        actual_method="docling",
        strict_method=True,
        stage="completed",
        status="succeeded",
        message="Extraction completed.",
    )

    assert payload["queued_at"] == "2026-04-10T12:00:00+00:00"
    assert payload["worker_started_at"] is not None
    assert payload["queue_wait_ms"] > 0
    assert payload["stage_timings_ms"]["parser"] > 0
    assert any(
        warning["code"] == "missing_stage_event:pass1_classifier"
        for warning in payload["warnings"]
    )


def test_initialize_run_status_preserves_original_queue_timestamp(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(obs, "RUN_STATUS_ROOT", tmp_path / "run_status")

    start = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    ticks = iter(start + timedelta(seconds=offset) for offset in range(6))
    monkeypatch.setattr(obs, "_now", lambda: next(ticks))

    first = obs.initialize_run_status(
        run_id="run-2",
        document_id="doc-2",
        requested_method="auto",
        strict_method=False,
    )
    second = obs.initialize_run_status(
        run_id="run-2",
        document_id="doc-2",
        requested_method="auto",
        strict_method=False,
    )

    assert first["queued_at"] == second["queued_at"]


def test_failed_run_does_not_add_missing_stage_warnings(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(obs, "RUN_STATUS_ROOT", tmp_path / "run_status")

    start = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    ticks = iter(start + timedelta(seconds=offset) for offset in range(6))
    monkeypatch.setattr(obs, "_now", lambda: next(ticks))

    obs.initialize_run_status(
        run_id="run-3",
        document_id="doc-3",
        requested_method="auto",
        strict_method=False,
    )
    payload = obs.emit_run_event(
        run_id="run-3",
        document_id="doc-3",
        requested_method="auto",
        actual_method=None,
        strict_method=False,
        stage="failed",
        status="failed",
        message="Extraction failed.",
        error_code="parser_failed",
    )

    assert payload["completed_at"] is not None
    assert not any(
        warning["code"].startswith("missing_stage_event:")
        for warning in payload["warnings"]
    )
