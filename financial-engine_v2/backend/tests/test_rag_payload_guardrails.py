from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import embeddings, pipeline, rag


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cleanup_asx_docs_payloads.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("cleanup_asx_docs_payloads", SCRIPT_PATH)
cleanup_script = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
SCRIPT_SPEC.loader.exec_module(cleanup_script)


class _FakeSearchClient:
    def __init__(self, points):
        self._points = list(points)
        self.calls: list[dict] = []

    def search(self, **kwargs):
        self.calls.append(dict(kwargs))
        return list(self._points)


def test_query_rag_skips_malformed_payloads_and_keeps_valid_hits(monkeypatch, caplog):
    valid_document_id = "11111111-1111-1111-1111-111111111111"
    points = [
        SimpleNamespace(
            id="bad-1",
            score=0.91,
            payload={"document_id": None, "ticker": "ABC", "chunk_index": 0, "title": "Broken"},
        ),
        SimpleNamespace(
            id=f"{valid_document_id}:1",
            score=0.73,
            payload={
                "document_id": valid_document_id,
                "ticker": "ABC",
                "chunk_index": 1,
                "title": "Valid chunk",
                "doc_class": "announcement",
                "doc_subtype": "periodic",
            },
        ),
    ]

    monkeypatch.setattr(rag.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(rag.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(rag.settings, "qdrant_collection", "asx_docs", raising=False)
    monkeypatch.setattr(rag, "get_routing_decision", lambda *args, **kwargs: SimpleNamespace(model_name="embed-model"))
    monkeypatch.setattr(rag, "embed_texts", lambda *args, **kwargs: [[0.1, 0.2]])
    monkeypatch.setattr(rag, "_build_qdrant_client", lambda: _FakeSearchClient(points))
    monkeypatch.setattr(rag, "ensure_collection", lambda client, collection, dim: collection)
    monkeypatch.setattr(rag, "_build_research_context", lambda query, evidence_hits: {"evidence_count": len(evidence_hits)})

    with caplog.at_level("WARNING"):
        result = rag.query_rag(query="capital raise", ticker="ABC", top_k=2, debug=True)

    assert result["ok"] is True
    assert result["candidate_count"] == 2
    assert result["filtered_count"] == 1
    assert result["hits"] == [
        {
            "score": pytest.approx(0.73),
            "ticker": "ABC",
            "title": "Valid chunk",
            "document_id": valid_document_id,
            "doc_class": "announcement",
            "doc_subtype": "periodic",
            "chunk_index": 1,
        }
    ]
    assert result["debug"]["skipped_invalid_payloads"] == 1
    warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert warning_records
    assert warning_records[0].point_id == "bad-1"
    assert warning_records[0].ticker == "ABC"
    assert warning_records[0].title == "Broken"
    assert warning_records[0].reason == "payload field document_id is None"


def test_query_rag_extracts_ticker_applies_filter_and_retries_without_filter(monkeypatch):
    filtered_hit = SimpleNamespace(
        id="bhp-1",
        score=0.81,
        payload={
            "document_id": "22222222-2222-2222-2222-222222222222",
            "ticker": "BHP",
            "chunk_index": 2,
            "title": "BHP cash flow update",
            "doc_class": "announcement",
            "doc_subtype": "operating",
        },
    )

    class RetryClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def search(self, **kwargs):
            self.calls.append(dict(kwargs))
            if len(self.calls) == 1:
                return []
            return [filtered_hit]

    client = RetryClient()

    monkeypatch.setattr(rag.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(rag.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(rag.settings, "qdrant_collection", "asx_docs", raising=False)
    monkeypatch.setattr(rag, "get_routing_decision", lambda *args, **kwargs: SimpleNamespace(model_name="embed-model"))
    monkeypatch.setattr(rag, "embed_texts", lambda *args, **kwargs: [[0.1, 0.2]])
    monkeypatch.setattr(rag, "_build_qdrant_client", lambda: client)
    monkeypatch.setattr(rag, "ensure_collection", lambda client, collection, dim: collection)
    monkeypatch.setattr(
        rag,
        "_build_research_context",
        lambda query, evidence_hits, **kwargs: {"evidence_count": len(evidence_hits)},
    )

    result = rag.query_rag(query="What were BHP operating cash flows?", ticker=None, top_k=3)

    assert result["ok"] is True
    assert result["filtered_count"] == 1
    assert result["hits"][0]["ticker"] == "BHP"
    assert len(client.calls) == 2
    assert client.calls[0]["query_filter"].must[0].key == "ticker"
    assert client.calls[0]["query_filter"].must[0].match.value == "BHP"
    assert "query_filter" not in client.calls[1]


def test_query_rag_reranks_ticker_matches_ahead_of_mismatches(monkeypatch):
    points = [
        SimpleNamespace(
            id="csl-1",
            score=0.92,
            payload={
                "document_id": "33333333-3333-3333-3333-333333333333",
                "ticker": "CSL",
                "chunk_index": 0,
                "title": "CSL update",
                "doc_class": "announcement",
                "doc_subtype": "periodic",
            },
        ),
        SimpleNamespace(
            id="bhp-1",
            score=0.84,
            payload={
                "document_id": "44444444-4444-4444-4444-444444444444",
                "ticker": "BHP",
                "chunk_index": 1,
                "title": "BHP operating cash flows",
                "doc_class": "announcement",
                "doc_subtype": "periodic",
            },
        ),
    ]

    monkeypatch.setattr(rag.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(rag.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(rag.settings, "qdrant_collection", "asx_docs", raising=False)
    monkeypatch.setattr(rag, "get_routing_decision", lambda *args, **kwargs: SimpleNamespace(model_name="embed-model"))
    monkeypatch.setattr(rag, "embed_texts", lambda *args, **kwargs: [[0.1, 0.2]])
    monkeypatch.setattr(rag, "_build_qdrant_client", lambda: _FakeSearchClient(points))
    monkeypatch.setattr(rag, "ensure_collection", lambda client, collection, dim: collection)
    monkeypatch.setattr(
        rag,
        "_build_research_context",
        lambda query, evidence_hits, **kwargs: {"evidence_count": len(evidence_hits)},
    )

    result = rag.query_rag(query="What were BHP operating cash flows?", ticker="BHP", top_k=2)

    assert result["hits"][0]["ticker"] == "BHP"
    assert result["hits"][1]["ticker"] == "CSL"


def test_upsert_points_skips_invalid_asx_docs_payloads_before_write(monkeypatch, caplog):
    writes: list[tuple[str, list]] = []

    class DummyClient:
        def upsert(self, *, collection_name, points, wait=True):
            writes.append((collection_name, list(points)))

    monkeypatch.setattr(embeddings.settings, "qdrant_collection", "asx_docs", raising=False)

    valid_document_id = str(uuid.uuid4())
    points = [
        {
            "id": "bad:0",
            "vector": [0.1, 0.2],
            "payload": {
                "document_id": valid_document_id,
                "ticker": "",
                "chunk_index": 0,
                "title": "Missing ticker",
            },
        },
        {
            "id": f"{valid_document_id}:1",
            "vector": [0.3, 0.4],
            "payload": {
                "document_id": valid_document_id,
                "ticker": "ABC",
                "chunk_index": 1,
                "title": "Valid write",
            },
        },
    ]

    with caplog.at_level("WARNING"):
        result = embeddings.upsert_points(DummyClient(), "asx_docs", points)

    assert len(writes) == 1
    assert writes[0][0] == "asx_docs"
    assert len(writes[0][1]) == 1
    assert writes[0][1][0].payload["ticker"] == "ABC"
    assert result == {"written_points": 1, "rejected_payloads": 1}
    warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any(record.action == "skipped_write" for record in warning_records)
    assert any(record.reason == "payload field ticker is missing" for record in warning_records)


def test_delete_points_for_document_filters_by_document_id():
    calls: list[dict] = []

    class DummyClient:
        def delete(self, **kwargs):
            calls.append(kwargs)

    document_id = str(uuid.uuid4())
    embeddings.delete_points_for_document(DummyClient(), "asx_docs", document_id)

    assert len(calls) == 1
    call = calls[0]
    assert call["collection_name"] == "asx_docs"
    assert call["wait"] is True
    selector = call["points_selector"]
    assert selector.filter.must[0].key == "document_id"
    assert selector.filter.must[0].match.value == document_id


def test_process_document_deletes_existing_points_before_upsert(monkeypatch):
    call_order: list[tuple] = []
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Valid doc"
        pdf_path = "/tmp/valid.pdf"
        source_url = "https://example.com/doc.pdf"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def query(self, model):
            return DummyQuery()

        def add(self, obj):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(pipeline, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(pipeline, "chunk_prose_sections", lambda doc: ["chunk-0", "chunk-1"])
    monkeypatch.setattr(pipeline, "_embed_chunks", lambda chunks, ollama_client=None: [[0.1, 0.2], [0.3, 0.4]])
    monkeypatch.setattr(pipeline, "QdrantClient", lambda url: None)
    monkeypatch.setattr(pipeline, "ensure_collection", lambda client, collection, dim: collection)
    monkeypatch.setattr(
        pipeline,
        "delete_points_for_document",
        lambda client, collection, document_id: call_order.append(("delete", collection, document_id)),
    )

    def fake_upsert_points(client, collection, points):
        call_order.append(("upsert", collection, [point["id"] for point in points]))
        return {"written_points": len(points), "rejected_payloads": 0}

    monkeypatch.setattr(pipeline, "upsert_points", fake_upsert_points)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "qdrant_collection", "asx_docs", raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", False, raising=False)

    result = pipeline.process_document(str(doc_id))

    expected_document_id = str(doc_id).lower()
    assert result["written_points"] == 2
    assert call_order[0] == ("delete", "asx_docs", expected_document_id)
    assert call_order[1][0] == "upsert"


def test_process_document_skips_invalid_chunk_payloads(monkeypatch):
    captured_points: list[dict] = []
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = ""
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Invalid ticker doc"
        pdf_path = "/tmp/invalid.pdf"
        source_url = "https://example.com/doc.pdf"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def query(self, model):
            return DummyQuery()

        def add(self, obj):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(pipeline, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(pipeline, "chunk_prose_sections", lambda doc: ["chunk-0", "chunk-1"])
    monkeypatch.setattr(pipeline, "_embed_chunks", lambda chunks, ollama_client=None: [[0.1, 0.2], [0.3, 0.4]])
    monkeypatch.setattr(pipeline, "QdrantClient", lambda url: None)
    monkeypatch.setattr(pipeline, "ensure_collection", lambda client, collection, dim: collection)
    monkeypatch.setattr(
        pipeline,
        "upsert_points",
        lambda client, collection, points: captured_points.extend(points) or {"written_points": len(points), "rejected_payloads": 0},
    )
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", False, raising=False)

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "skipped"
    assert result["skipped_invalid_vectors"] == 2
    assert result["invalid_payloads"] == 2
    assert captured_points == []


def test_process_document_upserts_financial_rows_for_ok_low_confidence(monkeypatch):
    doc_id = uuid.uuid4()
    upsert_calls: list[tuple[object, object, dict]] = []

    class DummyDoc:
        document_id = doc_id
        ticker = "ABC"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Low confidence periodic"
        pdf_path = "/tmp/low_confidence.pdf"
        source_url = "https://example.com/low_confidence.pdf"

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return DummyDoc()

    class DummySession:
        def __init__(self):
            self.added: list[object] = []

        def query(self, model):
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
    structured_payload = {
        "period_type": "H",
        "period_end": "2024-12-31",
        "confidence_metrics": 0.65,
        "confidence_narrative": 0.5,
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
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "provenance": {},
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
    }

    monkeypatch.setattr(pipeline, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        pipeline,
        "run_multipass_extraction",
        lambda *args, **kwargs: SimpleNamespace(
            status="ok_low_confidence",
            payload=structured_payload,
            sections=[{"text": "Narrative section", "page": 1}],
            error=None,
        ),
    )
    monkeypatch.setattr(pipeline, "chunk_prose_sections", lambda doc: [])
    monkeypatch.setattr(
        pipeline,
        "_upsert_financial_rows",
        lambda db, doc, structured: upsert_calls.append((db, doc, structured)),
    )
    monkeypatch.setattr(pipeline.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", False, raising=False)

    result = pipeline.process_document(str(doc_id))

    assert result["extraction_status"] == "ok_low_confidence"
    assert len(upsert_calls) == 1
    assert upsert_calls[0][0] is session
    assert upsert_calls[0][1].document_id == doc_id
    assert upsert_calls[0][2] is structured_payload


def test_query_rag_logs_when_ticker_results_are_missing_after_fallback(monkeypatch, caplog):
    class EmptyClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def search(self, **kwargs):
            self.calls.append(dict(kwargs))
            return []

    client = EmptyClient()

    monkeypatch.setattr(rag.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(rag.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(rag.settings, "qdrant_collection", "asx_docs", raising=False)
    monkeypatch.setattr(rag, "get_routing_decision", lambda *args, **kwargs: SimpleNamespace(model_name="embed-model"))
    monkeypatch.setattr(rag, "embed_texts", lambda *args, **kwargs: [[0.1, 0.2]])
    monkeypatch.setattr(rag, "_build_qdrant_client", lambda: client)
    monkeypatch.setattr(rag, "ensure_collection", lambda client, collection, dim: collection)
    monkeypatch.setattr(rag, "_build_research_context", lambda query, evidence_hits, **kwargs: {"evidence_count": 0})

    with caplog.at_level("INFO"):
        result = rag.query_rag(query="What were BHP earnings?", ticker=None, top_k=3, debug=True)

    assert result["hits"] == []
    assert result["debug"]["detected_ticker"] == "BHP"
    assert result["debug"]["fallback_used"] is True
    assert "No documents found" in caplog.text


def test_cleanup_asx_docs_payloads_reports_invalid_points_only():
    class DummyClient:
        def scroll(self, *, collection_name, limit, offset, with_payload, with_vectors):
            assert collection_name == "asx_docs"
            points = [
                SimpleNamespace(
                    id="bad-1",
                    payload={"document_id": None, "ticker": "ABC", "chunk_index": 0, "title": "Broken"},
                ),
                SimpleNamespace(
                    id="good-1",
                    payload={
                        "document_id": str(uuid.uuid4()),
                        "ticker": "ABC",
                        "chunk_index": 1,
                        "title": "Good",
                    },
                ),
            ]
            return points, None

    report = cleanup_script.cleanup_asx_docs_payloads(DummyClient(), collection_name="asx_docs")

    assert report["invalid_count"] == 1
    assert report["deleted_count"] == 0
    assert report["delete_requested"] is False
    assert report["invalid_points"] == [
        {
            "point_id": "bad-1",
            "document_id": None,
            "ticker": "ABC",
            "title": "Broken",
            "reason": "payload field document_id is None",
        }
    ]


def test_cleanup_asx_docs_payloads_deletes_only_invalid_points_when_requested():
    deleted_payloads: list[list[str]] = []

    class DummyClient:
        def scroll(self, *, collection_name, limit, offset, with_payload, with_vectors):
            points = [
                SimpleNamespace(
                    id="bad-1",
                    payload={"document_id": None, "ticker": "ABC", "chunk_index": 0, "title": "Broken"},
                ),
                SimpleNamespace(
                    id="good-1",
                    payload={
                        "document_id": str(uuid.uuid4()),
                        "ticker": "ABC",
                        "chunk_index": 1,
                        "title": "Good",
                    },
                ),
                SimpleNamespace(
                    id="bad-2",
                    payload={"document_id": str(uuid.uuid4()), "ticker": "", "chunk_index": 2, "title": "No ticker"},
                ),
            ]
            return points, None

        def delete(self, *, collection_name, points_selector, wait):
            assert collection_name == "asx_docs"
            assert wait is True
            deleted_payloads.append(list(points_selector.points))

    report = cleanup_script.cleanup_asx_docs_payloads(
        DummyClient(),
        collection_name="asx_docs",
        delete=True,
    )

    assert deleted_payloads == [["bad-1", "bad-2"]]
    assert report["invalid_count"] == 2
    assert report["deleted_count"] == 2
    assert report["delete_requested"] is True
