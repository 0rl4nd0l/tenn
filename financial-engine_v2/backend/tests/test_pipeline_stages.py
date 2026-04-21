from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest

from app.models.extractions import ExtractionRun
from app.services.announcement_importance import (
    classify_narrative_extraction_policy,
    classify_title_extraction_skip,
)
from app.services import pipeline
from app.services.pipeline_stages import (
    DocumentProcessResult,
    DownloadProcessAggregate,
    EmbeddingStageStatus,
    ExtractionStageResult,
    ExtractionStageStatus,
    attach_reproducibility_metadata,
    build_reproducibility_metadata,
    normalize_document_process_result,
    run_embedding_stage,
    run_extraction_stage,
)


def test_classify_title_extraction_skip_matches_admin_titles() -> None:
    result = classify_title_extraction_skip(
        title="Notice of cessation of securities",
        doc_class="quarterly",
        doc_subtype="other",
    )

    assert result["skip_extraction"] is True
    assert result["reason"] == "non_financial_admin_title"
    assert "cessation of securities" in result["matched_keywords"]


def test_classify_title_extraction_skip_matches_buyback_admin_titles() -> None:
    result = classify_title_extraction_skip(
        title="Update - Notification of buy-back - VEA",
        doc_class="quarterly",
        doc_subtype="other",
    )

    assert result["skip_extraction"] is True
    assert result["reason"] == "non_financial_admin_title"
    assert "notification of buy-back" in result["matched_keywords"]


def test_classify_title_extraction_skip_preserves_structural_financial_docs() -> None:
    result = classify_title_extraction_skip(
        title="Appendix 4C Quarterly Cash Flow Report",
        doc_class="quarterly",
        doc_subtype="4C",
    )

    assert result["skip_extraction"] is False
    assert result["matched_keywords"] == []


def test_classify_narrative_extraction_policy_selects_ops_titles() -> None:
    result = classify_narrative_extraction_policy(
        title="Quarterly Activities and Trading Update",
        doc_class="quarterly",
        doc_subtype="other",
        policy="selective",
    )

    assert result["extract_narrative"] is True
    assert result["reason"] == "selective_narrative_title_signal"
    assert "trading update" in result["matched_keywords"]


def test_classify_narrative_extraction_policy_keeps_financial_docs_metrics_only() -> None:
    result = classify_narrative_extraction_policy(
        title="Appendix 4C Quarterly Cash Flow Report",
        doc_class="quarterly",
        doc_subtype="4C",
        policy="selective",
    )

    assert result["extract_narrative"] is False
    assert result["reason"] == "metrics_only_financial_doc"


def test_run_extraction_stage_disabled_returns_structured_status() -> None:
    result = run_extraction_stage(
        enable_extraction=False,
        resolved_pdf_path="/tmp/doc.pdf",
        doc_metadata={"document_id": "1", "ticker": "ABC", "title": "Doc"},
        llm_client=None,
        multipass_runner=lambda *_args, **_kwargs: None,
        default_model_name="qwen2.5-32b-instruct",
        failure_classifier=lambda _err, _payload=None: "unknown",
    )

    assert result.status == ExtractionStageStatus.SKIPPED
    assert result.payload["status"] == "skipped_extraction"
    assert result.failure_code == "disabled"


def test_run_extraction_stage_failed_classifies_error() -> None:
    def _boom(*_args, **_kwargs):
        raise TimeoutError("parser timeout during extraction")

    result = run_extraction_stage(
        enable_extraction=True,
        resolved_pdf_path="/tmp/doc.pdf",
        doc_metadata={"document_id": "1", "ticker": "ABC", "title": "Doc"},
        llm_client=None,
        multipass_runner=_boom,
        default_model_name="qwen2.5-32b-instruct",
        failure_classifier=lambda err, _payload=None: (
            "parser_timeout" if "timeout" in str(err).lower() else "unknown"
        ),
    )

    assert result.status == ExtractionStageStatus.FAILED
    assert result.failure_code == "parser_timeout"
    assert "timeout" in str(result.error).lower()


def test_classify_extraction_failure_detects_missing_pdf_file() -> None:
    failure_code = pipeline.classify_extraction_failure(
        "[Errno 2] No such file or directory: '/data/asx/docs/WTC/sample.pdf'"
    )

    assert failure_code == "missing_pdf_file"


def test_classify_extraction_failure_detects_classifier_low_confidence() -> None:
    failure_code = pipeline.classify_extraction_failure(
        "classifier_low_confidence:0.0"
    )

    assert failure_code == "classifier_low_confidence"


def test_resolve_pdf_path_repairs_legacy_absolute_data_root(
    monkeypatch, tmp_path
) -> None:
    docs_root = tmp_path / "runtime-data" / "asx" / "docs"
    pdf_path = docs_root / "WTC" / "sample.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pipeline.settings, "docs_root", str(docs_root), raising=False)

    resolved = pipeline._resolve_pdf_path("/data/asx/docs/WTC/sample.pdf")

    assert resolved == str(pdf_path.resolve())


def test_attach_reproducibility_metadata_is_additive() -> None:
    payload = {"metrics": {"revenue": 1000}, "confidence_metrics": 0.9}
    merged = attach_reproducibility_metadata(
        payload,
        {"extractor_version": "docling_multipass_v1", "status": "ok"},
    )

    assert merged["metrics"]["revenue"] == 1000
    assert merged["_reproducibility"]["extractor_version"] == "docling_multipass_v1"


def test_process_document_records_reproducibility_metadata(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Test document"
        pdf_path = "/tmp/test.pdf"
        source_url = "https://example.com/test.pdf"
        pdf_sha256 = "abc123"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "skipped"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "skipped"
    assert repro["failure_code"] == "disabled"
    assert repro["document_id"] == str(doc_id)


def test_process_document_fails_loudly_when_pdf_missing_under_active_root(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()
    docs_root = tmp_path / "runtime-data" / "asx" / "docs"

    class DummyDoc:
        document_id = doc_id
        ticker = "WTC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "WTC 1H26 Appendix 4D and Financial Report"
        pdf_path = "/data/asx/docs/WTC/2026-02-25_wtc-1h26.pdf"
        source_url = "https://example.com/wtc.pdf"
        pdf_sha256 = "sha-wtc"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []
            self.commits = 0

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            self.commits += 1

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    monkeypatch.setattr(pipeline.settings, "docs_root", str(docs_root), raising=False)
    monkeypatch.setattr(
        pipeline.settings,
        "data_root",
        str(tmp_path / "runtime-data"),
        raising=False,
    )
    monkeypatch.setattr(pipeline.settings, "database_url", "sqlite:////tmp/test.db", raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability
    from app.services import method_isolated_extraction

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )
    monkeypatch.setattr(
        method_isolated_extraction,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("extraction should not run when PDF is missing")
        ),
    )

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "failed"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.status == "failed"
    assert "stored_pdf_path=/data/asx/docs/WTC/2026-02-25_wtc-1h26.pdf" in run.error
    assert f"docs_root={docs_root.resolve()}" in run.error
    assert session.commits == 1


def test_process_document_honors_cancellation_request(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "WTC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "WTC 1H26 Appendix 4D and Financial Report"
        pdf_path = "/data/asx/docs/WTC/2026-02-25_wtc-1h26.pdf"
        source_url = "https://example.com/wtc.pdf"
        pdf_sha256 = "sha-wtc"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.rollbacks = 0

        def query(self, _model):
            return DummyQuery()

        def add(self, _obj):
            raise AssertionError("cancelled extraction should not persist results")

        def commit(self):
            raise AssertionError("cancelled extraction should not commit")

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            pass

    class FakeTracker:
        def __init__(self) -> None:
            self.cancelled: list[tuple[str, str]] = []

        def create_job(self, *args, **kwargs):
            return SimpleNamespace(job_id=kwargs["job_id"])

        def start_job(self, *args, **kwargs):
            return None

        def change_phase(self, *args, **kwargs):
            return None

        def complete_job(self, *args, **kwargs):
            return None

        def fail_job(self, *args, **kwargs):
            return None

        def is_cancellation_requested(self, job_id: str) -> bool:
            return job_id == "run-cancelled-1"

        def cancel_job(self, job_id: str, reason: str = "") -> None:
            self.cancelled.append((job_id, reason))

    session = DummySession()
    tracker = FakeTracker()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)
    monkeypatch.setattr("app.services.job_tracker.get_tracker", lambda: tracker)

    from app.services import extraction_run_observability

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )

    with pytest.raises(pipeline.PipelineJobCancelled):
        pipeline.process_document(str(doc_id), run_id="run-cancelled-1")

    assert tracker.cancelled == [
        ("run-cancelled-1", "Pipeline operation cancelled by user request.")
    ]
    assert session.rollbacks >= 1


def test_process_document_downloads_pending_pdf_before_extraction(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()
    docs_root = tmp_path / "runtime-data" / "asx" / "docs"
    downloaded_pdf = docs_root / "WTC" / "2026-02-25_wtc-1h26.pdf"

    class DummyDoc:
        document_id = doc_id
        ticker = "WTC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "WTC 1H26 Appendix 4D and Financial Report"
        pdf_path = "/data/asx/docs/WTC/2026-02-25_wtc-1h26.pdf"
        source_url = "https://example.com/wtc.pdf"
        pdf_sha256 = ""

    doc = DummyDoc()

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return doc

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    download_calls: list[str] = []
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    monkeypatch.setattr(pipeline.settings, "docs_root", str(docs_root), raising=False)
    monkeypatch.setattr(
        pipeline.settings,
        "data_root",
        str(tmp_path / "runtime-data"),
        raising=False,
    )
    monkeypatch.setattr(pipeline.settings, "database_url", "sqlite:////tmp/test.db", raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability
    from app.services import method_isolated_extraction

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )

    def fake_download_pdf_for_document(db, document_id, http_client=None):
        download_calls.append(str(document_id))
        downloaded_pdf.parent.mkdir(parents=True, exist_ok=True)
        downloaded_pdf.write_bytes(b"%PDF-1.4\n")
        doc.pdf_path = str(downloaded_pdf)
        doc.pdf_sha256 = "sha-wtc"
        return {"document_id": str(document_id), "bytes": downloaded_pdf.stat().st_size}

    monkeypatch.setattr(
        pipeline, "download_pdf_for_document", fake_download_pdf_for_document
    )
    captured_kwargs: dict[str, object] = {}

    def _fake_run_method_isolated_extraction(*_args, **kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            status="skipped",
            payload={"status": "skipped_after_download"},
            sections=[],
            error=None,
        )

    monkeypatch.setattr(
        method_isolated_extraction,
        "run_method_isolated_extraction",
        _fake_run_method_isolated_extraction,
    )

    result = pipeline.process_document(str(doc_id), skip_narrative=True)

    assert result["extraction_status"] == "skipped"
    assert download_calls == [str(doc_id)]
    assert doc.pdf_path == str(downloaded_pdf)
    assert captured_kwargs["skip_narrative"] is True
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.status == "skipped"


def test_process_document_skips_non_financial_admin_titles_before_extraction(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "EOS"
        doc_class = "quarterly"
        doc_subtype = "other"
        title = "Notice of cessation of securities"
        pdf_path = "/tmp/eos-admin.pdf"
        source_url = "https://example.com/eos-admin.pdf"
        pdf_sha256 = "sha-admin"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability
    from app.services import method_isolated_extraction

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )
    monkeypatch.setattr(
        method_isolated_extraction,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("GPU extraction should not run for admin titles")
        ),
    )

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "skipped"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    assert run.structured_json["skip_reason"] == "non_financial_admin_title"
    assert "cessation of securities" in run.structured_json["matched_keywords"]
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "skipped"
    assert repro["failure_code"] == "non_financial_admin_title"

    run_status_path = tmp_path / "run_status" / f"{result['run_id']}.json"
    run_status = json.loads(run_status_path.read_text(encoding="utf-8"))
    assert "extraction_skipped_non_financial_title" in run_status["warning_codes"]
    assert not any(
        code.startswith("missing_stage_event:")
        for code in run_status["warning_codes"]
    )


def test_build_reproducibility_metadata_counts_non_null_metrics() -> None:
    doc = SimpleNamespace(
        document_id=uuid.uuid4(),
        ticker="ABC",
        source_url="https://example.com/doc.pdf",
        pdf_sha256="sha256",
    )
    stage_result = ExtractionStageResult(
        status=ExtractionStageStatus.OK,
        payload={"metrics": {"revenue": 1000, "ebit": None, "operating_cf": 200}},
        sections=[{"text": "Section 1"}],
        model_name="qwen2.5-32b-instruct",
        error=None,
        confidence=0.8,
        failure_code=None,
    )

    metadata = build_reproducibility_metadata(
        doc=doc,
        resolved_pdf_path="/tmp/doc.pdf",
        extractor_version="docling_multipass_v1",
        prompt_hash="abc",
        stage_result=stage_result,
    )

    assert metadata["non_null_metric_count"] == 2
    assert metadata["sections_count"] == 1


def test_run_embedding_stage_skips_when_embeddings_disabled() -> None:
    doc = SimpleNamespace(
        document_id=uuid.uuid4(),
        ticker="ABC",
        doc_class="announcement",
        doc_subtype="periodic",
        title="Doc",
        source_url="https://example.com/doc.pdf",
    )

    result = run_embedding_stage(
        chunks=["a", "b"],
        doc=doc,
        enable_embeddings=False,
        enable_qdrant=True,
        qdrant_client=None,
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection="asx_docs",
        ollama_client=None,
        embed_chunks=lambda *_args, **_kwargs: [[0.1], [0.2]],
        qdrant_client_factory=lambda _url: None,
        ensure_collection_fn=lambda *_args, **_kwargs: None,
        delete_points_for_document_fn=lambda *_args, **_kwargs: None,
        upsert_points_fn=lambda *_args, **_kwargs: {
            "written_points": 2,
            "rejected_payloads": 0,
        },
        validate_payload_fn=lambda _payload: (True, None),
        log_rejected_payload_fn=lambda *_args, **_kwargs: None,
        logger_obj=SimpleNamespace(error=lambda *_args, **_kwargs: None),
    )

    assert result.status == EmbeddingStageStatus.SKIPPED
    assert result.chunks_created == 2
    assert result.written_points == 0


def test_process_document_records_reproducibility_for_ok_low_confidence(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()
    pdf_file = tmp_path / "test-low.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Low confidence doc"
        pdf_path = str(pdf_file)
        source_url = "https://example.com/test-low.pdf"
        pdf_sha256 = "sha-low"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    from app.services import method_isolated_extraction

    monkeypatch.setattr(
        method_isolated_extraction,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="ok_low_confidence",
            payload={
                "period_type": "H",
                "period_end": "2024-12-31",
                "confidence_metrics": 0.65,
                "metrics": {
                    "revenue": 1000,
                    "ebit": None,
                    "np_attributable": None,
                    "operating_cf": 500,
                    "investing_cf": None,
                    "financing_cf": None,
                    "capex": None,
                    "cash_end": 200,
                    "net_debt": None,
                    "shares_outstanding": None,
                },
            },
            sections=[{"text": "Narrative section", "page": 1}],
            error=None,
        ),
    )
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "ok_low_confidence"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "ok_low_confidence"
    assert repro["failure_code"] is None
    assert repro["non_null_metric_count"] == 3


def test_process_document_records_reproducibility_for_failed_extraction(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()
    pdf_file = tmp_path / "test-failed.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Failed extraction doc"
        pdf_path = str(pdf_file)
        source_url = "https://example.com/test-failed.pdf"
        pdf_sha256 = "sha-failed"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    from app.services import method_isolated_extraction

    monkeypatch.setattr(
        method_isolated_extraction,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("parser timeout")),
    )
    monkeypatch.setattr(
        pipeline,
        "_upsert_financial_rows",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not upsert on failed extraction")
        ),
    )
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "failed"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "failed"
    assert repro["failure_code"] == "parser_timeout"

    run_status_path = tmp_path / "run_status" / f"{result['run_id']}.json"
    run_status = json.loads(run_status_path.read_text(encoding="utf-8"))
    assert "parser_timeout" in run_status["error_codes"]
    assert "embedding_skipped" not in run_status["warning_codes"]
    assert not any(
        code.startswith("missing_stage_event:")
        for code in run_status["warning_codes"]
    )


def test_process_document_persists_narrative_for_failed_validation_gate(
    monkeypatch, tmp_path
) -> None:
    doc_id = uuid.uuid4()
    pdf_file = tmp_path / "incident.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    class DummyDoc:
        document_id = doc_id
        ticker = "VEA"
        doc_class = "quarterly"
        doc_subtype = "other"
        title = "Incident at Geelong Refinery"
        pdf_path = str(pdf_file)
        source_url = "https://example.com/incident.pdf"
        pdf_sha256 = "sha-incident"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, _model):
            return DummyQuery()

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session = DummySession()
    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    from app.services import method_isolated_extraction

    monkeypatch.setattr(
        method_isolated_extraction,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="failed",
            payload={
                "risk_summary": "Compressor incident disrupted refinery output.",
                "risk_bullets": ["Compressor drop event", "Refinery downtime risk"],
                "guidance_summary": "Estimated monthly EBITDA impact disclosed.",
                "material_changes": "Production outage expected while repairs complete.",
            },
            sections=[{"text": "Incident details", "page": 1}],
            error="validation_gate:missing_period_end",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_upsert_financial_rows",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("periodic financial rows should not upsert on failed status")
        ),
    )
    risk_upsert_calls: list[bool] = []
    monkeypatch.setattr(
        pipeline,
        "_upsert_risk_note",
        lambda *_args, **kwargs: risk_upsert_calls.append(
            bool(kwargs.get("allow_empty"))
        )
        or 1,
    )
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    from app.services import extraction_run_observability

    monkeypatch.setattr(
        extraction_run_observability, "RUN_STATUS_ROOT", tmp_path / "run_status"
    )

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "failed"
    assert risk_upsert_calls == [False]

    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "failed"

    run_status_path = tmp_path / "run_status" / f"{result['run_id']}.json"
    run_status = json.loads(run_status_path.read_text(encoding="utf-8"))
    summary = run_status["final_summary"]
    assert summary["financial_rows_written"] == 0
    assert summary["risk_note_written"] == 1


def test_normalize_document_process_result_accepts_mapping() -> None:
    result = normalize_document_process_result(
        {
            "processed": 1,
            "skipped_download": 0,
            "error": None,
            "extraction_status": "ok",
            "chunks_created": 3,
            "chunks_skipped": 1,
            "invalid_payloads": 1,
            "written_points": 2,
        }
    )

    assert isinstance(result, DocumentProcessResult)
    assert result.processed == 1
    assert result.extraction_status == "ok"
    assert result.written_points == 2


def test_download_process_aggregate_tracks_failed_extraction_and_errors() -> None:
    agg = DownloadProcessAggregate()
    agg.add(
        "doc-ok",
        DocumentProcessResult(
            processed=1,
            skipped_download=0,
            extraction_status="failed",
            chunks_created=2,
            chunks_skipped=1,
            invalid_payloads=1,
            written_points=1,
        ),
    )
    agg.add(
        "doc-err",
        DocumentProcessResult(
            processed=0,
            skipped_download=0,
            error="network error",
        ),
    )

    processed, skipped, extraction_failed, errors, metrics = agg.to_legacy_tuple()
    assert processed == 1
    assert skipped == 0
    assert extraction_failed == 1
    assert len(errors) == 2
    assert errors[0]["error"] == "extraction_failed"
    assert errors[1]["error"] == "network error"
    assert metrics["chunks_created"] == 2
    assert metrics["chunks_skipped"] == 1
    assert metrics["invalid_payloads"] == 1
    assert metrics["written_points"] == 1
