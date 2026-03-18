from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.framework_classifier import FrameworkClassifier  # noqa: E402
from app.services.framework_retriever import FrameworkRetriever  # noqa: E402
from app.services.hybrid_retriever import HybridRetriever  # noqa: E402
from app.services.reranker import RetrievalReranker  # noqa: E402
from app.services.retrieval_orchestrator import RetrievalOrchestrator  # noqa: E402


class FakeScoredPoint:
    def __init__(self, payload: dict, score: float):
        self.payload = payload
        self.score = score


class FakeRecord:
    def __init__(self, payload: dict):
        self.payload = payload


class FakeQdrantClient:
    def __init__(self, payloads: list[dict]):
        self._payloads = list(payloads)
        self.search_calls: list[dict] = []
        self.scroll_calls: list[dict] = []

    def search(self, *, collection_name: str, query_vector: list[float], query_filter=None, limit: int = 10, **kwargs):
        self.search_calls.append(
            {
                "collection_name": collection_name,
                "query_vector": list(query_vector),
                "query_filter": query_filter,
                "limit": limit,
            }
        )
        payloads = self._apply_filter(self._payloads, query_filter)
        scored = []
        for payload in payloads:
            vector = payload.get("_vector", [0.0, 0.0, 0.0])
            score = sum(float(left) * float(right) for left, right in zip(query_vector, vector))
            scored.append(FakeScoredPoint(payload=payload, score=score))
        scored.sort(key=lambda item: (-float(item.score), str(item.payload.get("chunk_id") or "")))
        return scored[:limit]

    def scroll(self, *, collection_name: str, scroll_filter=None, limit: int = 10, offset=None, **kwargs):
        self.scroll_calls.append(
            {
                "collection_name": collection_name,
                "scroll_filter": scroll_filter,
                "limit": limit,
                "offset": offset,
            }
        )
        payloads = self._apply_filter(self._payloads, scroll_filter)
        start = int(offset or 0)
        batch = payloads[start : start + limit]
        next_offset = start + limit if start + limit < len(payloads) else None
        return [FakeRecord(payload) for payload in batch], next_offset

    @staticmethod
    def _apply_filter(payloads: list[dict], query_filter) -> list[dict]:
        if query_filter is None:
            return list(payloads)

        conditions = []
        if getattr(query_filter, "must", None):
            must = query_filter.must
            conditions.extend(must if isinstance(must, list) else [must])
        if getattr(query_filter, "should", None):
            should = query_filter.should
            conditions.extend(should if isinstance(should, list) else [should])
        if getattr(query_filter, "min_should", None):
            conditions.extend(getattr(query_filter.min_should, "conditions", []))

        allowed: set[str] = set()
        for condition in conditions:
            key = getattr(condition, "key", None)
            match = getattr(condition, "match", None)
            value = getattr(match, "value", None)
            if key == "framework_family" and value is not None:
                allowed.add(str(value))

        if not allowed:
            return list(payloads)
        return [payload for payload in payloads if str(payload.get("framework_family") or "") in allowed]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _fake_embed(texts: list[str], **_: object) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        lowered = str(text).lower()
        if any(token in lowered for token in ("moat", "five forces", "rivalry", "supplier", "buyer", "barriers")):
            vectors.append([1.0, 0.1, 0.0])
        elif any(token in lowered for token in ("valuation", "cash flow", "intrinsic value", "margin of safety")):
            vectors.append([0.1, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return vectors


def _framework_rows() -> list[dict]:
    return [
        {
            "framework_id": "f-porters-1",
            "framework_family": "porters_five_forces",
            "title": "Porter's Five Forces",
            "principles": [
                "Assess rivalry, supplier power, buyer power, substitution risk, and barriers to entry.",
                "Durable moats weaken competitive forces.",
            ],
            "signals_or_indicators": ["Rivalry intensity", "Switching costs"],
            "decision_rules": ["Prefer industries where competitive forces are structurally weak."],
            "risk_notes": ["Moats can erode when suppliers or buyers gain leverage."],
            "source_pages": [1, 2],
            "evidence_chunk_ids": ["chunk-1", "chunk-2"],
        },
        {
            "framework_id": "f-valuation-1",
            "framework_family": "valuation",
            "title": "Discounted Cash Flow",
            "principles": [
                "Estimate future cash flows conservatively.",
                "Compare intrinsic value to market price.",
            ],
            "signals_or_indicators": ["Free cash flow", "Discount rate"],
            "decision_rules": ["Require a margin of safety before entry."],
            "risk_notes": ["Aggressive assumptions overstate intrinsic value."],
            "source_pages": [3, 4],
            "evidence_chunk_ids": ["chunk-3"],
        },
    ]


def _chunk_payloads() -> list[dict]:
    return [
        {
            "chunk_id": "chunk-1",
            "source_file": "moat_playbook.pdf",
            "page_start": 1,
            "page_end": 1,
            "framework_family": "porters_five_forces",
            "section": "overview",
            "text": "A strong moat depends on rivalry, supplier power, and buyer power staying contained.",
            "_vector": [1.0, 0.1, 0.0],
        },
        {
            "chunk_id": "chunk-2",
            "source_file": "moat_playbook.pdf",
            "page_start": 2,
            "page_end": 2,
            "framework_family": "porters_five_forces",
            "section": "decision_rules",
            "text": "Barriers to entry and low substitution risk support durable competitive advantage.",
            "_vector": [0.95, 0.1, 0.0],
        },
        {
            "chunk_id": "chunk-3",
            "source_file": "valuation_playbook.pdf",
            "page_start": 3,
            "page_end": 3,
            "framework_family": "valuation",
            "section": "overview",
            "text": "Discounted cash flow estimates intrinsic value from future free cash flow.",
            "_vector": [0.1, 1.0, 0.0],
        },
        {
            "chunk_id": "chunk-4",
            "source_file": "misc_notes.pdf",
            "page_start": 4,
            "page_end": 4,
            "framework_family": "porters_five_forces",
            "section": "risks",
            "text": "Buyer concentration can compress pricing power even with a nominal moat.",
            "_vector": [0.85, 0.1, 0.0],
        },
    ]


def test_framework_classification_selects_moat_family(tmp_path: Path) -> None:
    frameworks_path = tmp_path / "framework_records" / "frameworks.jsonl"
    _write_jsonl(frameworks_path, _framework_rows())

    classifier = FrameworkClassifier(
        frameworks_path=frameworks_path,
        embedding_fn=_fake_embed,
    )

    result = classifier.classify("analyze company moat", top_k=1)

    assert result == ["porters_five_forces"]


def test_hybrid_retrieval_filters_by_framework_family_and_deduplicates(tmp_path: Path) -> None:
    frameworks_path = tmp_path / "framework_records" / "frameworks.jsonl"
    _write_jsonl(frameworks_path, _framework_rows())
    qdrant_client = FakeQdrantClient(_chunk_payloads())

    retriever = HybridRetriever(
        qdrant_client=qdrant_client,
        embedding_fn=_fake_embed,
        collection_name="methodology_chunks",
    )

    result = retriever.retrieve(
        query="analyze company moat",
        framework_families=["porters_five_forces"],
        top_k_vector=3,
        top_k_keyword=3,
    )

    chunk_ids = [chunk["chunk_id"] for chunk in result["chunks"]]

    assert qdrant_client.search_calls
    assert qdrant_client.search_calls[0]["query_filter"] is not None
    assert chunk_ids
    assert len(chunk_ids) == len(set(chunk_ids))
    assert "chunk-3" not in chunk_ids
    assert all(chunk["framework_family"] == "porters_five_forces" for chunk in result["chunks"])


def test_reranker_reduces_result_set_and_preserves_best_match() -> None:
    reranker = RetrievalReranker(embedding_fn=_fake_embed)
    chunks = [
        {
            "chunk_id": "chunk-1",
            "framework_family": "porters_five_forces",
            "text": "A strong moat depends on rivalry, supplier power, and buyer power staying contained.",
            "vector_score": 0.98,
            "keyword_score": 2.0,
        },
        {
            "chunk_id": "chunk-2",
            "framework_family": "porters_five_forces",
            "text": "Barriers to entry support durable competitive advantage.",
            "vector_score": 0.92,
            "keyword_score": 1.5,
        },
        {
            "chunk_id": "chunk-3",
            "framework_family": "valuation",
            "text": "Discounted cash flow estimates intrinsic value.",
            "vector_score": 0.15,
            "keyword_score": 0.2,
        },
    ]

    ranked = reranker.rerank(
        query="analyze company moat",
        chunks=chunks,
        framework_families=["porters_five_forces"],
        top_k=2,
    )

    assert len(ranked) == 2
    assert ranked[0]["chunk_id"] == "chunk-1"
    assert all("rerank_score" in chunk for chunk in ranked)


def test_orchestrator_builds_structured_context(tmp_path: Path) -> None:
    frameworks_path = tmp_path / "framework_records" / "frameworks.jsonl"
    _write_jsonl(frameworks_path, _framework_rows())
    qdrant_client = FakeQdrantClient(_chunk_payloads())

    classifier = FrameworkClassifier(frameworks_path=frameworks_path, embedding_fn=_fake_embed)
    framework_retriever = FrameworkRetriever(frameworks_path=frameworks_path)
    hybrid_retriever = HybridRetriever(
        qdrant_client=qdrant_client,
        embedding_fn=_fake_embed,
        collection_name="methodology_chunks",
    )
    reranker = RetrievalReranker(embedding_fn=_fake_embed)
    orchestrator = RetrievalOrchestrator(
        classifier=classifier,
        framework_retriever=framework_retriever,
        hybrid_retriever=hybrid_retriever,
        reranker=reranker,
    )

    result = orchestrator.retrieve("analyze company moat")

    assert list(result.keys())[:3] == ["frameworks", "chunks", "sources"]
    assert result["frameworks"]
    assert result["frameworks"][0]["framework_family"] == "porters_five_forces"
    assert result["chunks"]
    assert result["chunks"][0]["text"]
    assert result["chunks"][0]["source_file"] == "moat_playbook.pdf"
    assert result["methodology_chunks"] == result["chunks"]
    assert result["commentary_chunks"] == []
    assert result["commentary_memos"] == []
    assert result["sources"] == [
        {
            "source_file": "misc_notes.pdf",
            "page_ranges": ["4-4"],
        },
        {
            "source_file": "moat_playbook.pdf",
            "page_ranges": ["1-1", "2-2"],
        },
    ]
