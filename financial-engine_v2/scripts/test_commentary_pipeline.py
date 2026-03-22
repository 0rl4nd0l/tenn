from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import llm as llm_service  # noqa: E402
from app.services.commentary_decay import compute_recency_decay  # noqa: E402
from app.services.commentary_ingest import ingest_transcript  # noqa: E402
from app.services.commentary_memo_extractor import (  # noqa: E402
    CommentaryMemoExtractor,
    load_commentary_memos,
)
from app.services.hybrid_retriever import HybridRetriever  # noqa: E402
from app.services.research_context_builder import ResearchContextBuilder  # noqa: E402
from app.services.retrieval_orchestrator import RetrievalOrchestrator  # noqa: E402
from app.services.source_registry import SourceRegistry  # noqa: E402
from app.services.source_weighting import (  # noqa: E402
    DEFAULT_SOURCE_WEIGHTS,
    apply_source_weighting,
)
from app.services.router import RoutingDecision  # noqa: E402


class FakeScoredPoint:
    def __init__(self, payload: dict, score: float) -> None:
        self.payload = payload
        self.score = score


class FakeRecord:
    def __init__(self, payload: dict) -> None:
        self.payload = payload


class FakeCollectionInfo:
    def __init__(self, name: str, size: int) -> None:
        from qdrant_client.http import models as qmodels

        self.name = name
        self.config = type(
            "ConfigWrapper",
            (),
            {
                "params": type(
                    "ParamsWrapper",
                    (),
                    {
                        "vectors": qmodels.VectorParams(
                            size=size,
                            distance=qmodels.Distance.COSINE,
                        )
                    },
                )()
            },
        )()


class FakeCollectionList:
    def __init__(self, names: list[str]) -> None:
        self.collections = [type("Collection", (), {"name": name})() for name in names]


class FakeHTTPResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = dict(payload)
        self.status_code = int(status_code)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http error: {self.status_code}")

    def json(self) -> dict:
        return dict(self._payload)


class FakeLLMHTTPClient:
    def __init__(
        self,
        *,
        models_payload: dict | None = None,
        completions_payload: dict | None = None,
        embeddings_payload: dict | None = None,
        embeddings_status_code: int = 200,
    ) -> None:
        self.models_payload = dict(models_payload or {})
        self.completions_payload = dict(completions_payload or {})
        self.embeddings_payload = dict(embeddings_payload or {})
        self.embeddings_status_code = int(embeddings_status_code)
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, timeout=None, headers=None) -> FakeHTTPResponse:
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "json": None,
                "headers": dict(headers or {}),
            }
        )
        return FakeHTTPResponse(self.models_payload)

    def post(self, url: str, json: dict, timeout=None, headers=None) -> FakeHTTPResponse:
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "json": dict(json),
                "headers": dict(headers or {}),
            }
        )
        if url.endswith("/v1/embeddings"):
            return FakeHTTPResponse(self.embeddings_payload, status_code=self.embeddings_status_code)
        return FakeHTTPResponse(self.completions_payload)


class FakeQdrantClient:
    def __init__(self, payloads: dict[str, list[dict]] | None = None) -> None:
        self.payloads = {name: list(rows) for name, rows in (payloads or {}).items()}
        self.created: list[tuple[str, int]] = []
        self.upserts: list[tuple[str, list[dict]]] = []
        self.search_calls: list[dict[str, object]] = []
        self.scroll_calls: list[dict[str, object]] = []

    def get_collections(self):
        return FakeCollectionList(sorted(self.payloads))

    def get_collection(self, collection_name: str):
        payloads = self.payloads.get(collection_name)
        if payloads is None:
            raise RuntimeError(f"missing collection: {collection_name}")
        size = len(payloads[0].get("_vector") or payloads[0].get("vector") or [0.0, 0.0]) if payloads else 2
        return FakeCollectionInfo(collection_name, size)

    def create_collection(self, collection_name: str, vectors_config) -> None:
        self.created.append((collection_name, int(vectors_config.size)))
        self.payloads.setdefault(collection_name, [])

    def upsert(self, *, collection_name: str, points):
        persisted: list[dict] = []
        for point in points:
            payload = dict(point.payload or {})
            vector = list(point.vector or [])
            persisted.append({"id": point.id, **payload, "_vector": vector})
        existing = {
            str(row.get("id")): row
            for row in self.payloads.setdefault(collection_name, [])
        }
        for row in persisted:
            existing[str(row.get("id"))] = row
        rows = sorted(existing.values(), key=lambda row: str(row.get("id") or ""))
        self.payloads[collection_name] = rows
        self.upserts.append((collection_name, rows))

    def search(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        query_filter=None,
        limit: int = 10,
        **kwargs,
    ):
        self.search_calls.append(
            {
                "collection_name": collection_name,
                "query_vector": list(query_vector),
                "query_filter": query_filter,
                "limit": limit,
            }
        )
        payloads = self._apply_filter(self.payloads.get(collection_name, []), query_filter)
        scored: list[FakeScoredPoint] = []
        for payload in payloads:
            vector = payload.get("_vector") or [0.0] * len(query_vector)
            score = sum(float(left) * float(right) for left, right in zip(query_vector, vector))
            scored.append(FakeScoredPoint(payload=payload, score=score))
        scored.sort(
            key=lambda item: (
                -float(item.score),
                str(item.payload.get("chunk_id") or item.payload.get("id") or ""),
            )
        )
        return scored[:limit]

    def scroll(
        self,
        *,
        collection_name: str,
        scroll_filter=None,
        limit: int = 10,
        offset=None,
        **kwargs,
    ):
        self.scroll_calls.append(
            {
                "collection_name": collection_name,
                "scroll_filter": scroll_filter,
                "limit": limit,
                "offset": offset,
            }
        )
        payloads = self._apply_filter(self.payloads.get(collection_name, []), scroll_filter)
        start = int(offset or 0)
        batch = payloads[start : start + limit]
        next_offset = start + limit if start + limit < len(payloads) else None
        return [FakeRecord(payload=row) for row in batch], next_offset

    @staticmethod
    def _apply_filter(payloads: list[dict], query_filter) -> list[dict]:
        if query_filter is None:
            return list(payloads)

        allowed: set[str] = set()
        for attr_name in ("must", "should"):
            conditions = getattr(query_filter, attr_name, None) or []
            if not isinstance(conditions, list):
                conditions = [conditions]
            for condition in conditions:
                key = getattr(condition, "key", None)
                match = getattr(condition, "match", None)
                value = getattr(match, "value", None)
                if key == "framework_family" and value is not None:
                    allowed.add(str(value))
                if key == "ticker" and value is not None:
                    allowed.add(str(value))
        if not allowed:
            return list(payloads)
        filtered = []
        for payload in payloads:
            family = str(payload.get("framework_family") or "")
            ticker = str(payload.get("ticker") or "")
            if family in allowed or ticker in allowed:
                filtered.append(payload)
        return filtered


class StubClassifier:
    def classify(self, query: str, top_k: int = 3) -> list[str]:
        assert query
        assert top_k >= 1
        return ["porters_five_forces"]


class StubFrameworkRetriever:
    def retrieve(self, framework_families: list[str] | None) -> list[dict]:
        assert framework_families == ["porters_five_forces"]
        return [
            {
                "framework_id": "fw-1",
                "framework_family": "porters_five_forces",
                "title": "Porter's Five Forces",
                "principles": ["Assess rivalry and switching costs."],
                "decision_rules": ["Prefer structurally advantaged markets."],
                "risk_notes": ["Moats can fade quickly."],
            }
        ]


class StubHybridRetriever:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def retrieve(
        self,
        *,
        query: str,
        framework_families: list[str] | None,
        ticker: str | None = None,
        financial_intents: list[str] | None = None,
        top_k_vector: int = 20,
        top_k_keyword: int = 20,
    ) -> dict:
        self.calls.append(
            {
                "query": query,
                "framework_families": framework_families,
                "top_k_vector": top_k_vector,
                "top_k_keyword": top_k_keyword,
            }
        )
        return dict(self.response)


class StubReranker:
    def __init__(self, returned: list[dict]) -> None:
        self.returned = returned
        self.calls: list[dict] = []

    def rerank(
        self,
        *,
        query: str,
        chunks: list[dict],
        framework_families: list[str] | None,
        top_k: int = 8,
        query_embedding: list[float] | None = None,
    ) -> list[dict]:
        self.calls.append(
            {
                "query": query,
                "framework_families": framework_families,
                "top_k": top_k,
                "query_embedding": query_embedding,
            }
        )
        return [dict(chunk) for chunk in self.returned[:top_k]]


def _fake_embed(texts: list[str], **_: object) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        lowered = str(text).lower()
        if "moat" in lowered or "rivalry" in lowered:
            vectors.append([1.0, 0.1])
        elif "commentary" in lowered or "catalyst" in lowered:
            vectors.append([0.3, 1.0])
        else:
            vectors.append([0.1, 0.2])
    return vectors


def _make_embedding(seed: int, dim: int = 768) -> list[float]:
    return [float(seed)] + [0.0] * (dim - 1)


def test_commentary_hybrid_retriever_queries_both_collections_and_dedupes_candidates() -> None:
    qdrant = FakeQdrantClient(
        {
            "commentary_chunks": [
                {
                    "chunk_id": "shared-1",
                    "source_id": "youtube_transcript:shared",
                    "text": "Battery materials demand outlook improves as EV sales accelerate.",
                    "_vector": _make_embedding(0.95, dim=768),
                },
                {
                    "text": "Battery materials demand outlook remains tight across converters.",
                    "_vector": _make_embedding(0.75, dim=768),
                },
            ],
            "commentary_chunks_v2": [
                {
                    "chunk_id": "shared-1",
                    "source_id": "youtube_transcript:shared",
                    "text": "Battery materials demand outlook improves as EV sales accelerate.",
                    "_vector": _make_embedding(0.96, dim=5120),
                },
                {
                    "text": "Battery materials demand outlook remains tight across converters.",
                    "_vector": _make_embedding(0.78, dim=5120),
                },
                {
                    "chunk_id": "v2-only",
                    "source_id": "youtube_transcript:v2",
                    "text": "Battery materials demand outlook is strongest for lithium chemical producers.",
                    "_vector": _make_embedding(0.99, dim=5120),
                },
            ],
        }
    )

    retriever = HybridRetriever(
        qdrant_client=qdrant,
        collection_name="commentary_chunks",
        embedding_fn=lambda texts, **_: [_make_embedding(1.0, dim=768) for _ in texts],
        secondary_embedding_fn=lambda texts, **_: [_make_embedding(1.0, dim=5120) for _ in texts],
    )

    result = retriever.retrieve(
        query="battery materials demand outlook",
        framework_families=None,
        top_k_vector=5,
        top_k_keyword=5,
    )

    assert [call["collection_name"] for call in qdrant.search_calls] == [
        "commentary_chunks",
        "commentary_chunks_v2",
    ]
    assert sorted({call["collection_name"] for call in qdrant.scroll_calls}) == [
        "commentary_chunks",
        "commentary_chunks_v2",
    ]
    assert len(result["chunks"]) == 3

    shared = next(chunk for chunk in result["chunks"] if chunk.get("chunk_id") == "shared-1")
    same_text = [
        chunk
        for chunk in result["chunks"]
        if chunk.get("text") == "Battery materials demand outlook remains tight across converters."
    ]

    assert shared["collections"] == ["commentary_chunks", "commentary_chunks_v2"]
    assert len(same_text) == 1
    assert any(chunk.get("chunk_id") == "v2-only" for chunk in result["chunks"])


def test_dual_collection_commentary_retrieval_reranks_merged_candidates(tmp_path: Path) -> None:
    class CapturingReranker:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def rerank(
            self,
            *,
            query: str,
            chunks: list[dict[str, object]],
            framework_families: list[str] | None,
            top_k: int = 8,
            query_embedding: list[float] | None = None,
        ) -> list[dict[str, object]]:
            self.calls.append(
                {
                    "query": query,
                    "chunk_refs": [str(chunk.get("chunk_id") or chunk.get("text") or "") for chunk in chunks],
                    "query_embedding_dim": len(query_embedding or []),
                }
            )
            ranked = sorted(
                [dict(chunk) for chunk in chunks],
                key=lambda chunk: (
                    -float(chunk.get("vector_score") or 0.0),
                    str(chunk.get("chunk_id") or ""),
                ),
            )
            return ranked[:top_k]

    memos_path = tmp_path / "research_memory" / "commentary_memos.jsonl"
    memos_path.parent.mkdir(parents=True, exist_ok=True)
    memos_path.write_text("", encoding="utf-8")

    qdrant = FakeQdrantClient(
        {
            "commentary_chunks": [
                {
                    "chunk_id": "shared-1",
                    "source_id": "youtube_transcript:shared",
                    "source_type": "youtube_transcript",
                    "text": "Battery materials demand outlook improves as EV sales accelerate.",
                    "_vector": _make_embedding(0.95, dim=768),
                },
            ],
            "commentary_chunks_v2": [
                {
                    "chunk_id": "shared-1",
                    "source_id": "youtube_transcript:shared",
                    "source_type": "youtube_transcript",
                    "text": "Battery materials demand outlook improves as EV sales accelerate.",
                    "_vector": _make_embedding(0.96, dim=5120),
                },
                {
                    "chunk_id": "v2-only",
                    "source_id": "youtube_transcript:v2",
                    "source_type": "youtube_transcript",
                    "text": "Battery materials demand outlook is strongest for lithium chemical producers.",
                    "_vector": _make_embedding(0.99, dim=5120),
                },
            ],
        }
    )
    commentary_retriever = HybridRetriever(
        qdrant_client=qdrant,
        collection_name="commentary_chunks",
        embedding_fn=lambda texts, **_: [_make_embedding(1.0, dim=768) for _ in texts],
        secondary_embedding_fn=lambda texts, **_: [_make_embedding(1.0, dim=5120) for _ in texts],
    )
    commentary_reranker = CapturingReranker()

    orchestrator = RetrievalOrchestrator(
        classifier=StubClassifier(),
        framework_retriever=StubFrameworkRetriever(),
        hybrid_retriever=StubHybridRetriever(
            {
                "query_embedding": [1.0, 0.0],
                "chunks": [],
            }
        ),
        reranker=StubReranker([]),
        commentary_retriever=commentary_retriever,
        commentary_reranker=commentary_reranker,
        commentary_memos_path=memos_path,
    )

    retrieval = orchestrator.retrieve(
        "battery materials demand outlook",
        top_k_commentary=2,
        top_k_commentary_vector=5,
        top_k_commentary_keyword=5,
    )

    assert len(commentary_reranker.calls) == 1
    assert sorted(commentary_reranker.calls[0]["chunk_refs"]) == ["shared-1", "v2-only"]
    assert commentary_reranker.calls[0]["query_embedding_dim"] == 768
    assert [chunk["chunk_id"] for chunk in retrieval["commentary_chunks"]] == ["v2-only", "shared-1"]
    assert retrieval["commentary_chunks"][1]["collections"] == ["commentary_chunks", "commentary_chunks_v2"]


def test_generate_json_uses_llamacpp_even_when_router_selects_ollama(monkeypatch) -> None:
    records: list[dict[str, object]] = []
    http_client = FakeLLMHTTPClient(
        models_payload={"data": [{"id": "qwen2.5-coder-14b"}]},
        completions_payload={
            "choices": [
                {
                    "message": {
                        "content": '{"speaker":"","claims":["Demand is improving."],"catalysts":[],"risks":[],"sentiment":"constructive","time_horizon":"","tickers":["SSE"]}'
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 21,
                "completion_tokens": 19,
                "total_tokens": 40,
            },
        },
    )

    monkeypatch.setattr(
        llm_service,
        "route_request",
        lambda prompt, metadata=None: RoutingDecision(
            model_name="llama3:latest",
            execution_queue="llm_gpu",
            task_type="reasoning",
            provider="ollama",
            base_url="http://localhost:11434",
        ),
    )
    monkeypatch.setenv("LLM_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-coder-14b")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLAMACPP_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)
    monkeypatch.setattr(llm_service.router_state, "mark_task_started", lambda queue: None)
    monkeypatch.setattr(llm_service.router_state, "mark_task_finished", lambda queue: None)
    monkeypatch.setattr(llm_service.router_metrics, "record", lambda **kwargs: records.append(dict(kwargs)))

    payload = llm_service.generate_json(
        "Transcript text about improving demand.",
        metadata={"task_type": "reasoning", "component": "commentary_memo_extractor"},
        client=http_client,
    )

    assert payload["claims"] == ["Demand is improving."]
    assert http_client.calls == [
        {
            "method": "GET",
            "url": "http://127.0.0.1:8001/v1/models",
            "json": None,
            "headers": {},
        },
        {
            "method": "POST",
            "url": "http://127.0.0.1:8001/v1/chat/completions",
            "json": {
                "model": "qwen2.5-coder-14b",
                "messages": [
                    {"role": "system", "content": "Extract structured JSON only."},
                    {"role": "user", "content": "Transcript text about improving demand."},
                ],
                "temperature": 0,
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
            },
            "headers": {},
        },
    ]
    assert records[-1]["success"] is True
    assert records[-1]["model_name"] == "qwen2.5-coder-14b"


def test_llamacpp_embed_attaches_auth_headers(monkeypatch) -> None:
    from app.services.llamacpp_embeddings import llamacpp_embed

    http_client = FakeLLMHTTPClient(
        models_payload={"data": [{"id": "qwen2.5-coder-14b"}]},
        embeddings_payload={
            "data": [
                {"embedding": _make_embedding(1)},
            ]
        },
    )

    monkeypatch.setenv("EMBEDDING_URL", "http://127.0.0.1:8101")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("LLM_API_KEY", "token-123")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embed-token-456")
    monkeypatch.setenv("LLM_AUTH_HEADER", "X-LLM-Auth: extra-value")

    vectors = llamacpp_embed(
        "http://127.0.0.1:8101",
        "nomic-embed-text",
        ["alpha"],
        client=http_client,
    )

    assert len(vectors) == 1
    assert http_client.calls == [
        {
            "method": "GET",
            "url": "http://127.0.0.1:8101/v1/models",
            "json": None,
            "headers": {
                "Authorization": "Bearer token-123",
                "Content-Type": "application/json",
                "X-LLM-Auth": "extra-value",
            },
        },
        {
            "method": "POST",
            "url": "http://127.0.0.1:8101/v1/embeddings",
            "json": {
                "model": "nomic-embed-text",
                "input": ["alpha"],
            },
            "headers": {
                "Authorization": "Bearer token-123",
                "Content-Type": "application/json",
                "X-LLM-Auth": "extra-value",
            },
        },
    ]


def test_llamacpp_embed_attaches_embedding_api_key_when_llm_key_missing(monkeypatch) -> None:
    from app.services.llamacpp_embeddings import llamacpp_embed

    http_client = FakeLLMHTTPClient(
        models_payload={"data": [{"id": "qwen2.5-coder-14b"}]},
        embeddings_payload={"data": [{"embedding": [0.1, 0.2]}]},
    )

    monkeypatch.setenv("EMBEDDING_URL", "http://127.0.0.1:8101")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("EMBEDDING_API_KEY", "embed-token-123")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    vectors = llamacpp_embed(
        "http://127.0.0.1:8101",
        "nomic-embed-text",
        ["alpha"],
        client=http_client,
    )

    assert vectors == [[0.1, 0.2]]
    assert http_client.calls == [
        {
            "method": "GET",
            "url": "http://127.0.0.1:8101/v1/models",
            "json": None,
            "headers": {"Authorization": "Bearer embed-token-123", "Content-Type": "application/json"},
        },
        {
            "method": "POST",
            "url": "http://127.0.0.1:8101/v1/embeddings",
            "json": {"model": "nomic-embed-text", "input": ["alpha"]},
            "headers": {"Authorization": "Bearer embed-token-123", "Content-Type": "application/json"},
        },
    ]


def test_embedding_batcher_probes_and_batches_split_runtime(monkeypatch) -> None:
    from app.services.embeddings import embed_texts_batched

    calls: list[dict[str, object]] = []

    def fake_probe_llamacpp_embeddings(base_url: str, model: str, timeout=30.0, client=None):
        calls.append(
            {
                "op": "probe",
                "base_url": base_url,
                "model": model,
                "timeout": timeout,
            }
        )
        return {"base_url": base_url, "model": model, "ok": True, "dimension": 768}

    def fake_llamacpp_embed(
        base_url: str,
        model: str,
        texts: list[str],
        timeout=120.0,
        client=None,
        verify_models=True,
    ):
        calls.append(
            {
                "op": "embed",
                "base_url": base_url,
                "model": model,
                "inputs": list(texts),
                "timeout": timeout,
            }
        )
        return [_make_embedding(idx + 1) for idx, _ in enumerate(texts)]

    monkeypatch.setenv("LLM_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-coder-14b")
    monkeypatch.setenv("EMBEDDING_URL", "http://127.0.0.1:8101")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setattr("app.services.embeddings.probe_llamacpp_embeddings", fake_probe_llamacpp_embeddings)
    monkeypatch.setattr("app.services.embeddings.llamacpp_embed", fake_llamacpp_embed)

    vectors = embed_texts_batched(["alpha", "beta", "gamma"], batch_size=2)

    assert len(vectors) == 3
    assert all(len(vector) == 768 for vector in vectors)
    assert calls == [
        {
            "op": "probe",
            "base_url": "http://127.0.0.1:8101",
            "model": "nomic-embed-text",
            "timeout": 30.0,
        },
        {
            "op": "embed",
            "base_url": "http://127.0.0.1:8101",
            "model": "nomic-embed-text",
            "inputs": ["alpha", "beta"],
            "timeout": 120.0,
        },
        {
            "op": "embed",
            "base_url": "http://127.0.0.1:8101",
            "model": "nomic-embed-text",
            "inputs": ["gamma"],
            "timeout": 120.0,
        },
    ]


def test_embedding_runtime_uses_generation_values_when_embedding_env_missing(monkeypatch) -> None:
    from app.services.embeddings import resolve_llamacpp_embedding_config
    from app.services.llamacpp_runtime import build_embedding_headers

    monkeypatch.setenv("LLM_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-coder-14b")
    monkeypatch.setenv("LLM_API_KEY", "llm-token")
    monkeypatch.delenv("EMBEDDING_URL", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)

    assert resolve_llamacpp_embedding_config() == ("http://127.0.0.1:8001", "qwen2.5-coder-14b")
    assert build_embedding_headers() == {
        "Authorization": "Bearer llm-token",
        "Content-Type": "application/json",
    }


def test_embedding_runtime_defaults_to_local_llamacpp_when_env_missing(monkeypatch) -> None:
    from app.services.embeddings import resolve_llamacpp_embedding_config
    from app.services import llamacpp_runtime

    monkeypatch.delenv("LLM_URL", raising=False)
    monkeypatch.delenv("LLAMACPP_URL", raising=False)
    monkeypatch.delenv("EMBEDDING_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLAMACPP_MODEL", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("EMBED_MODEL", raising=False)
    # settings.embed_model is loaded from .env at import time; patch it out so
    # resolve_embedding_runtime_config falls through to DEFAULT_LLM_MODEL.
    monkeypatch.setattr(llamacpp_runtime.settings, "embed_model", "")

    assert resolve_llamacpp_embedding_config() == ("http://127.0.0.1:8001", "qwen2.5-coder-14b")


def test_embedding_runtime_prefers_non_cpu_model_for_local_cpu_routing(monkeypatch) -> None:
    from app.services.embeddings import resolve_llamacpp_embedding_config

    monkeypatch.setenv("EMBEDDING_URL", "http://127.0.0.1:8101")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    assert resolve_llamacpp_embedding_config(
        llm_url="cpu://sentence-transformers",
        model="sentence-transformers/all-MiniLM-L6-v2",
    ) == ("http://127.0.0.1:8101", "nomic-embed-text")


def test_embedding_probe_raises_clear_error_on_501(monkeypatch) -> None:
    from app.services.llamacpp_embeddings import probe_llamacpp_embeddings

    http_client = FakeLLMHTTPClient(
        models_payload={"data": [{"id": "qwen2.5-coder-14b"}]},
        embeddings_payload={
            "error": {
                "message": "This server does not support embeddings. Start it with --embeddings"
            }
        },
        embeddings_status_code=501,
    )

    monkeypatch.setenv("LLM_API_KEY", "llm-token")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embed-token")
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)

    with pytest.raises(
        RuntimeError,
        match="Embeddings endpoint unavailable\\. Start llama\\.cpp with --embeddings or set EMBEDDING_URL to a working embeddings server\\.",
    ):
        probe_llamacpp_embeddings(
            "http://127.0.0.1:8001",
            "qwen2.5-coder-14b",
            client=http_client,
        )

    assert http_client.calls == [
        {
            "method": "GET",
            "url": "http://127.0.0.1:8001/v1/models",
            "json": None,
            "headers": {
                "Authorization": "Bearer llm-token",
                "Content-Type": "application/json",
            },
        },
        {
            "method": "POST",
            "url": "http://127.0.0.1:8001/v1/embeddings",
            "json": {
                "model": "qwen2.5-coder-14b",
                "input": ["hello"],
            },
            "headers": {
                "Authorization": "Bearer llm-token",
                "Content-Type": "application/json",
            },
        },
    ]


def test_transcript_ingestion_uses_unified_llamacpp_runtime_path(monkeypatch, tmp_path: Path) -> None:
    transcript_path = tmp_path / "transcripts" / "video1.txt"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(
        "00:00 Durable demand is improving.\n"
        "00:15 Management says a margin catalyst is pricing discipline.\n"
        "00:35 The main risk is channel inventory volatility.\n",
        encoding="utf-8",
    )

    embed_calls: list[dict[str, object]] = []

    def fake_embed_texts_batched(texts: list[str], *, llm_url=None, model=None, batch_size=None):
        embed_calls.append(
            {
                "inputs": list(texts),
                "llm_url": llm_url,
                "model": model,
                "batch_size": batch_size,
            }
        )
        return [_make_embedding(idx + 1) for idx, _ in enumerate(texts)]

    queued_payloads: list[dict[str, object]] = []

    class FakeMemoTask:
        def delay(self, payload: dict[str, object]) -> None:
            queued_payloads.append(dict(payload))

    monkeypatch.setenv("LLM_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-coder-14b")
    monkeypatch.setenv("EMBEDDING_URL", "http://127.0.0.1:8101")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setattr("app.services.commentary_ingest.embed_texts_batched", fake_embed_texts_batched)
    monkeypatch.setattr("app.services.commentary_ingest.extract_commentary_memo_task", FakeMemoTask())

    registry_path = tmp_path / "research_memory" / "source_registry.jsonl"
    memos_path = tmp_path / "research_memory" / "commentary_memos.jsonl"
    qdrant = FakeQdrantClient()

    result = ingest_transcript(
        transcript_text=transcript_path.read_text(encoding="utf-8"),
        source_name="Specialist Share Education",
        source_type="youtube_transcript",
        speaker="Specialist Share Education",
        published_at="2026-03-12T00:00:00Z",
        qdrant_client=qdrant,
        registry_path=registry_path,
        memos_path=memos_path,
    )

    stored_chunks = qdrant.payloads["commentary_chunks"]

    assert result["ok"] is True
    assert result["chunks_indexed"] == len(stored_chunks) == 1
    assert stored_chunks[0]["chunk_id"].endswith(":0")
    assert stored_chunks[0]["source_name"] == "Specialist Share Education"
    assert len(stored_chunks[0]["_vector"]) == 768
    assert result["memo"] is None
    assert result["memos_path"] == str(memos_path.expanduser().resolve())
    assert queued_payloads == [
        {
            "source_id": result["source_id"],
            "transcript_text": (
                "Durable demand is improving.\n"
                "Management says a margin catalyst is pricing discipline.\n"
                "The main risk is channel inventory volatility."
            ),
            "speaker": "Specialist Share Education",
            "source_type": "youtube_transcript",
            "published_at": "2026-03-12T00:00:00Z",
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-coder-14b",
            "memos_path": str(memos_path.expanduser().resolve()),
        }
    ]
    assert embed_calls == [
        {
            "batch_size": None,
            "inputs": [stored_chunks[0]["text"]],
            "llm_url": "http://127.0.0.1:8101",
            "model": "nomic-embed-text",
        }
    ]


def test_transcript_ingestion_writes_registry_chunks_and_queues_memo(monkeypatch, tmp_path: Path) -> None:
    queued_payloads: list[dict[str, object]] = []

    class FakeMemoTask:
        def delay(self, payload: dict[str, object]) -> None:
            queued_payloads.append(dict(payload))

    monkeypatch.setattr("app.services.commentary_ingest.extract_commentary_memo_task", FakeMemoTask())

    registry_path = tmp_path / "research_memory" / "source_registry.jsonl"
    memos_path = tmp_path / "research_memory" / "commentary_memos.jsonl"
    qdrant = FakeQdrantClient()

    result = ingest_transcript(
        transcript_text=(
            "00:00 Intro to the company moat.\n"
            "00:10 Demand looks resilient and a catalyst is margin expansion.\n"
            "00:10 Demand looks resilient and a catalyst is margin expansion.\n"
            "00:40 Risks include customer concentration."
        ),
        source_name="Edge Case Capital Interview",
        source_type="youtube_transcript",
        speaker="Jane Analyst",
        published_at="2026-03-01T00:00:00Z",
        topic_tags=["moat", "capital-allocation"],
        qdrant_client=qdrant,
        registry_path=registry_path,
        memos_path=memos_path,
        embed_batch_fn=_fake_embed,
    )

    registry = SourceRegistry(registry_path)
    sources = registry.all()
    stored_chunks = qdrant.payloads["commentary_chunks"]

    assert result["collection"] == "commentary_chunks"
    assert result["memo"] is None
    assert result["chunks_indexed"] == len(stored_chunks)
    assert len(stored_chunks) == 1
    assert stored_chunks[0]["speaker"] == "Jane Analyst"
    assert stored_chunks[0]["source_type"] == "youtube_transcript"
    assert stored_chunks[0]["topic_tags"] == ["capital-allocation", "moat"]
    assert sources[0]["source_name"] == "Edge Case Capital Interview"
    assert sources[0]["credibility_weight"] == DEFAULT_SOURCE_WEIGHTS["youtube_transcript"]
    assert not memos_path.exists()
    assert queued_payloads == [
        {
            "source_id": result["source_id"],
            "transcript_text": (
                "Intro to the company moat.\n"
                "Demand looks resilient and a catalyst is margin expansion.\n"
                "Demand looks resilient and a catalyst is margin expansion.\n"
                "Risks include customer concentration."
            ),
            "speaker": "Jane Analyst",
            "source_type": "youtube_transcript",
            "published_at": "2026-03-01T00:00:00Z",
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-coder-14b",
            "memos_path": str(memos_path.expanduser().resolve()),
        }
    ]


def test_extract_commentary_memo_task_stores_memo(monkeypatch, tmp_path: Path) -> None:
    from app.tasks import commentary_tasks

    records: dict[str, object] = {}

    class FakeMemoExtractor:
        def __init__(self, *, llm_url=None, llm_model=None, memos_path=None) -> None:
            records["init"] = {
                "llm_url": llm_url,
                "llm_model": llm_model,
                "memos_path": Path(memos_path).expanduser().resolve(),
            }

        def extract_and_store(self, **kwargs) -> dict[str, object]:
            records["call"] = dict(kwargs)
            return {"ok": True, "source_id": kwargs["source_id"]}

    monkeypatch.setattr(commentary_tasks, "CommentaryMemoExtractor", FakeMemoExtractor)

    result = commentary_tasks.extract_commentary_memo_task(
        {
            "source_id": "youtube_transcript:test",
            "transcript_text": "Transcript text with one catalyst and one risk.",
            "speaker": "Jane Analyst",
            "source_type": "youtube_transcript",
            "published_at": "2026-03-12T00:00:00Z",
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-coder-14b",
            "memos_path": str((tmp_path / "commentary_memos.jsonl").resolve()),
        }
    )

    assert result == {"ok": True, "source_id": "youtube_transcript:test"}
    assert records["init"] == {
        "llm_url": "http://127.0.0.1:8001",
        "llm_model": "qwen2.5-coder-14b",
        "memos_path": (tmp_path / "commentary_memos.jsonl").resolve(),
    }
    assert records["call"] == {
        "source_id": "youtube_transcript:test",
        "transcript_text": "Transcript text with one catalyst and one risk.",
        "speaker": "Jane Analyst",
        "source_type": "youtube_transcript",
        "published_at": "2026-03-12T00:00:00Z",
    }


def test_transcript_ingestion_keeps_success_when_memo_queueing_fails(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class FailingMemoTask:
        def delay(self, payload: dict[str, object]) -> None:
            raise RuntimeError("memo timeout")

    registry_path = tmp_path / "research_memory" / "source_registry.jsonl"
    memos_path = tmp_path / "research_memory" / "commentary_memos.jsonl"
    qdrant = FakeQdrantClient()
    monkeypatch.setattr("app.services.commentary_ingest.extract_commentary_memo_task", FailingMemoTask())

    result = ingest_transcript(
        transcript_text="Transcript text with a clear thesis and one catalyst.",
        source_name="Timeout Tolerant Channel",
        source_type="youtube_transcript",
        speaker="Jane Analyst",
        published_at="2026-03-12T00:00:00Z",
        qdrant_client=qdrant,
        registry_path=registry_path,
        memos_path=memos_path,
        embed_batch_fn=_fake_embed,
    )

    captured = capsys.readouterr()

    assert result["ok"] is True
    assert result["memo"] is None
    assert result["chunks_indexed"] == len(qdrant.payloads["commentary_chunks"]) == 1
    assert "[WARN] memo extraction queue failed: memo timeout" in captured.out
    assert "[INFO] transcript stored successfully (memo optional)" in captured.out


def test_commentary_memo_extractor_normalizes_llamacpp_payload(tmp_path: Path) -> None:
    extractor = CommentaryMemoExtractor(
        llm_fn=lambda **_: {
            "speaker": " Macro Mike ",
            "claims": "rate cuts help demand",
            "catalysts": None,
            "risks": ["sticky inflation", "", None],
            "sentiment": " bullish ",
            "time_horizon": None,
            "tickers": ["abc", "ABC", " "],
        },
        memos_path=tmp_path / "commentary_memos.jsonl",
    )

    memo = extractor.extract(
        source_id="youtube_transcript:test",
        transcript_text="rate cuts help demand but sticky inflation is still a risk",
        speaker="Macro Mike",
        source_type="youtube_transcript",
        published_at="2026-03-10T00:00:00Z",
    )

    assert memo["speaker"] == "Macro Mike"
    assert memo["claims"] == ["rate cuts help demand"]
    assert memo["catalysts"] == []
    assert memo["risks"] == ["sticky inflation"]
    assert memo["sentiment"] == "bullish"
    assert memo["time_horizon"] == ""
    assert memo["tickers"] == ["ABC"]


def test_decay_and_weighting_penalize_stale_commentary() -> None:
    recency_decay = compute_recency_decay(
        published_at="2026-01-01T00:00:00Z",
        half_life_days=10.0,
        now="2026-03-01T00:00:00Z",
    )

    weighted = apply_source_weighting(
        relevance_score=0.8,
        source_type="market_commentary",
        credibility_weight=0.6,
        recency_decay=recency_decay,
    )

    assert 0.0 < recency_decay < 0.2
    assert weighted["source_weight"] == DEFAULT_SOURCE_WEIGHTS["market_commentary"]
    assert weighted["final_score"] < 0.05


def test_dual_memory_retrieval_caps_commentary_and_builds_context(tmp_path: Path) -> None:
    memos_path = tmp_path / "research_memory" / "commentary_memos.jsonl"
    memos_path.parent.mkdir(parents=True, exist_ok=True)
    memos_path.write_text(
        json.dumps(
            {
                "source_id": "youtube_transcript:abc",
                "speaker": "Jane Analyst",
                "claims": ["Near-term demand inflects."],
                "catalysts": ["Margin expansion."],
                "risks": ["Execution slip."],
                "sentiment": "constructive",
                "time_horizon": "12 months",
                "tickers": ["ABC"],
                "source_type": "youtube_transcript",
                "published_at": "2026-03-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    methodology_chunks = [
        {
            "chunk_id": "m-1",
            "framework_family": "porters_five_forces",
            "text": "Rivalry is manageable and switching costs are rising.",
            "source_file": "moat_playbook.pdf",
            "page_start": 2,
            "page_end": 2,
            "rerank_score": 0.92,
        }
    ]
    commentary_chunks = [
        {
            "chunk_id": "c-1",
            "source_id": "youtube_transcript:abc",
            "source_type": "youtube_transcript",
            "speaker": "Jane Analyst",
            "published_at": "2026-03-01T00:00:00Z",
            "credibility_weight": 0.55,
            "decay_half_life": 14.0,
            "topic_tags": ["abc"],
            "text": "Recent commentary points to demand stabilization and margin recovery.",
            "vector_score": 0.8,
            "keyword_score": 1.1,
            "rerank_score": 0.88,
        }
    ]

    orchestrator = RetrievalOrchestrator(
        classifier=StubClassifier(),
        framework_retriever=StubFrameworkRetriever(),
        hybrid_retriever=StubHybridRetriever(
            {
                "query_embedding": [1.0, 0.0],
                "chunks": methodology_chunks,
            }
        ),
        reranker=StubReranker(methodology_chunks),
        commentary_retriever=StubHybridRetriever(
            {
                "query_embedding": [0.0, 1.0],
                "chunks": commentary_chunks,
            }
        ),
        commentary_reranker=StubReranker(commentary_chunks),
        commentary_memos_path=memos_path,
    )
    builder = ResearchContextBuilder(commentary_weight_max=0.25)

    retrieval = orchestrator.retrieve("analyze company moat and catalysts")
    context = builder.build(
        frameworks=retrieval["frameworks"],
        methodology_chunks=retrieval["methodology_chunks"],
        evidence_chunks=[
            {
                "score": 0.96,
                "ticker": "ABC",
                "title": "FY26 Trading Update",
                "document_id": "11111111-1111-1111-1111-111111111111",
                "chunk_index": 0,
            }
        ],
        commentary_chunks=retrieval["commentary_chunks"],
        commentary_memos=retrieval["commentary_memos"],
    )

    assert retrieval["methodology_chunks"][0]["chunk_id"] == "m-1"
    assert retrieval["commentary_chunks"][0]["final_score"] <= 0.25
    assert list(context.keys()) == [
        "frameworks",
        "evidence_chunks",
        "commentary_chunks",
        "commentary_memos",
    ]
    assert context["frameworks"][0]["supporting_chunks"][0]["chunk_id"] == "m-1"
    assert context["commentary_memos"][0]["speaker"] == "Jane Analyst"


def test_ingest_routes_register_book_and_transcript(monkeypatch, tmp_path: Path) -> None:
    from app.api import routes

    captured: dict[str, dict] = {}

    def fake_ingest_transcript(**kwargs):
        captured["transcript"] = kwargs
        return {"ok": True, "source_id": "youtube_transcript:abc"}

    def fake_ingest_book(**kwargs):
        captured["book"] = kwargs
        return {"ok": True, "source_id": "book:abc"}

    monkeypatch.setattr(routes, "ingest_transcript", fake_ingest_transcript)
    monkeypatch.setattr(routes, "ingest_book", fake_ingest_book)

    transcript_response = routes.ingest_transcript_route(
        routes.TranscriptIngestRequest(
            filename="abc.txt",
            text="Transcript body",
            source_name="ABC CEO interview",
            source_type="youtube_transcript",
            speaker="CEO",
            published_at="2026-03-02T00:00:00Z",
            topic_tags=["abc"],
        )
    )
    book_response = routes.ingest_book_route(
        routes.BookIngestRequest(
            filename="durable.pdf",
            content_base64=base64.b64encode(b"%PDF-1.4 mock").decode("ascii"),
            source_name="Durable Investing",
            source_type="book",
            framework_family="quality",
        )
    )

    assert transcript_response["ok"] is True
    assert book_response["ok"] is True
    assert captured["transcript"]["source_type"] == "youtube_transcript"
    assert captured["book"]["source_type"] == "book"
    assert captured["book"]["filename"] == "durable.pdf"
