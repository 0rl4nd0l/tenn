from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _BackendCall:
    query: str
    ticker: str | None
    top_k: int


class QualContextReader:
    """Backend-only qualitative context adapter for Cockpit.

    Cockpit intentionally does not embed or query local vector stores. Instead it calls the
    backend RAG endpoint via `backend_api_client.rag_query(...)` and normalizes the response
    into a stable "hits" shape for downstream use.
    """

    def __init__(
        self,
        *,
        repo_root: Path,
        backend_api_client: Any,
        embed_backend: str = "ollama",
        embed_model: str = "nomic-embed-text",
        corpus_filter: str = "",
        ticker_match_mode: str = "soft",
        top_k: int = 8,
        timeout: float = 12.0,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.backend_api_client = backend_api_client
        self.embed_backend = str(embed_backend or "").strip().lower() or "ollama"
        self.embed_model = str(embed_model or "").strip() or "nomic-embed-text"
        self.corpus_filter = str(corpus_filter or "").strip()
        self.ticker_match_mode = str(ticker_match_mode or "").strip().lower() or "soft"
        self.top_k = int(max(1, int(top_k)))
        self.timeout = float(timeout)
        self._last_backend_call: _BackendCall | None = None

    def validate_runtime(self) -> None:
        if self.embed_backend != "ollama":
            raise RuntimeError("Cockpit RAG must use backend API. Local embeddings disabled.")
        if not hasattr(self.backend_api_client, "rag_query"):
            raise RuntimeError("backend_api_client.rag_query is required for Cockpit RAG.")

    def query(
        self,
        *,
        query: str,
        company: str = "",  # kept for backward compatibility with older callers
        deep_mode: bool = False,  # noqa: ARG002 - backend decides truncation
        top_k: int | None = None,
        ticker_filter: str = "",
        source_filter: str = "",  # noqa: ARG002 - backend handles source filtering
    ) -> dict[str, Any]:
        q = str(query or "").strip()
        limit = int(max(1, int(top_k) if top_k is not None else self.top_k))
        ticker = str(ticker_filter or "").strip().upper() or None

        if not q:
            return {"ok": False, "hits": [], "error": "query is required"}

        # Enforce policy before any backend call.
        try:
            self.validate_runtime()
        except Exception as exc:
            return {"ok": False, "hits": [], "error": str(exc)}

        self._last_backend_call = _BackendCall(query=q, ticker=ticker, top_k=limit)
        try:
            result = self.backend_api_client.rag_query(q=q, ticker=ticker, top_k=limit, timeout=self.timeout)
        except Exception as exc:
            return {"ok": False, "hits": [], "error": str(exc)[:400]}

        if not isinstance(result, dict):
            return {"ok": False, "hits": [], "error": "backend unavailable"}

        # rag_query() returns {"results": [{"score": float, "payload": {...}}, ...]} directly.
        raw_results = result.get("results")
        if not isinstance(raw_results, list):
            return {"ok": False, "hits": [], "error": "unexpected backend response shape"}

        hits: list[dict[str, Any]] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            score = float(item.get("score") or 0.0)
            item_payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            corpus = str(item_payload.get("corpus") or "")
            if self.corpus_filter and corpus and corpus != self.corpus_filter:
                continue
            hit = dict(item_payload)
            hit.setdefault("semantic_score", score)
            hit.setdefault("final_score", float(hit.get("semantic_score") or score))
            hits.append(hit)

        return {
            "ok": True,
            "query": q,
            "company": str(company or "").strip().upper(),
            "ticker_filter": ticker_filter,
            "top_k": limit,
            "candidate_count": len(raw_results),
            "filtered_count": len(hits),
            "hits": hits,
        }

