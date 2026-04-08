from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.models.extractions import ExtractionRun
from app.services import pipeline
from app.services.pipeline_stages import (
    EmbeddingStageStatus,
    ExtractionStageResult,
    ExtractionStageStatus,
    attach_reproducibility_metadata,
    build_reproducibility_metadata,
    run_embedding_stage,
    run_extraction_stage,
)


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


def test_attach_reproducibility_metadata_is_additive() -> None:
    payload = {"metrics": {"revenue": 1000}, "confidence_metrics": 0.9}
    merged = attach_reproducibility_metadata(
        payload,
        {"extractor_version": "docling_multipass_v1", "status": "ok"},
    )

    assert merged["metrics"]["revenue"] == 1000
    assert merged["_reproducibility"]["extractor_version"] == "docling_multipass_v1"


def test_process_document_records_reproducibility_metadata(monkeypatch) -> None:
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

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "skipped"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "skipped"
    assert repro["failure_code"] == "disabled"
    assert repro["document_id"] == str(doc_id)


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
    monkeypatch,
) -> None:
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Low confidence doc"
        pdf_path = "/tmp/test-low.pdf"
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
    monkeypatch.setattr(
        pipeline,
        "run_multipass_extraction",
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

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "ok_low_confidence"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "ok_low_confidence"
    assert repro["failure_code"] is None
    assert repro["non_null_metric_count"] == 3


def test_process_document_records_reproducibility_for_failed_extraction(
    monkeypatch,
) -> None:
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Failed extraction doc"
        pdf_path = "/tmp/test-failed.pdf"
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
    monkeypatch.setattr(
        pipeline,
        "run_multipass_extraction",
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

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "failed"
    run = next(obj for obj in session.added if isinstance(obj, ExtractionRun))
    assert run.structured_json is not None
    repro = run.structured_json["_reproducibility"]
    assert repro["status"] == "failed"
    assert repro["failure_code"] == "parser_timeout"
