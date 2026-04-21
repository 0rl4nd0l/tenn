from __future__ import annotations

from app.services import pipeline as pipeline_core
from app.services.job_tracker import get_tracker, init_tracker
from app.services.ops_store import OpsStore
from app.services.pipeline_service import PipelineJobSpec, run_pipeline_sync


def test_run_pipeline_sync_marks_backfill_cancelled(monkeypatch, tmp_path) -> None:
    tracker = init_tracker(OpsStore(tmp_path / "ops.db"))
    created_job_ids: list[str] = []
    original_create_job = tracker.create_job

    def recording_create_job(**kwargs):
        handle = original_create_job(**kwargs)
        created_job_ids.append(handle.job_id)
        return handle

    monkeypatch.setattr(tracker, "create_job", recording_create_job)

    class DummySession:
        def close(self):
            pass

    monkeypatch.setattr("app.services.pipeline_service.SessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        "app.services.pipeline_service.settings.enable_qdrant", False, raising=False
    )
    monkeypatch.setattr(
        "app.services.pipeline_service.settings.enable_importance_classification",
        False,
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.pipeline_service.pipeline_core.discover_and_insert_documents",
        lambda db, ticker, years: {
            "ticker": ticker,
            "found": 1,
            "inserted": 1,
            "new_document_ids": ["doc-1"],
            "provider_metrics": {},
            "provider_failures_sample": [],
        },
    )
    monkeypatch.setattr(
        "app.services.pipeline_service.pipeline_core.download_pdf_for_document",
        lambda db, document_id: None,
    )

    def fake_process_document(document_id, *, parent_job_id=None, **kwargs):
        assert document_id == "doc-1"
        assert parent_job_id in created_job_ids
        active_tracker = get_tracker()
        assert active_tracker is not None
        active_tracker.request_cancellation(
            str(parent_job_id), "Backfill cancelled by user request."
        )
        raise pipeline_core.PipelineJobCancelled(
            "Backfill cancelled by user request."
        )

    monkeypatch.setattr(
        "app.services.pipeline_service.pipeline_core.process_document",
        fake_process_document,
    )

    result = run_pipeline_sync(
        PipelineJobSpec(ticker="BHP", years=1, process_documents=True)
    )

    assert result["cancelled"] is True
    assert created_job_ids
    run = tracker.store.get_job_run(created_job_ids[0])
    assert run is not None
    assert run["status"] == "cancelled"
    assert run["summary"] == "Backfill cancelled by user request."
