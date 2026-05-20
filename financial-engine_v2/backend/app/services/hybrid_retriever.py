from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.services.embeddings import embed_texts_batched
from app.services.llm import embed_texts


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
DEFAULT_COLLECTION_NAME = "methodology_chunks"
COMMENTARY_COLLECTION_NAME = "commentary_chunks"
COMMENTARY_COLLECTION_V2_NAME = "commentary_chunks_v2"
SCROLL_BATCH_SIZE = 256
ASX_DOCS_COLLECTION_NAME = "asx_docs"
NEWS_CHUNKS_COLLECTION_NAME = "news_chunks"
# Collections that support ticker-based payload filtering
_TICKER_FILTER_COLLECTIONS = frozenset({ASX_DOCS_COLLECTION_NAME, NEWS_CHUNKS_COLLECTION_NAME})
FINANCIAL_TITLE_MARKERS = ("appendix", "results", "financial")
logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    class BM25Okapi:  # type: ignore[override]
        def __init__(self, corpus: list[list[str]], *, k1: float = 1.5, b: float = 0.75) -> None:
            self.corpus = corpus
            self.k1 = float(k1)
            self.b = float(b)
            self.corpus_size = len(corpus)
            self.doc_freqs = [Counter(doc) for doc in corpus]
            self.doc_len = [len(doc) for doc in corpus]
            self.avgdl = float(sum(self.doc_len)) / float(max(1, self.corpus_size))
            frequencies: Counter[str] = Counter()
            for doc in corpus:
                for token in set(doc):
                    frequencies[token] += 1
            self.idf = {
                token: math.log(1.0 + ((self.corpus_size - freq + 0.5) / (freq + 0.5)))
                for token, freq in frequencies.items()
            }

        def get_scores(self, query_tokens: list[str]) -> list[float]:
            scores: list[float] = []
            for freqs, doc_len in zip(self.doc_freqs, self.doc_len):
                score = 0.0
                denominator_bias = self.k1 * (1.0 - self.b + (self.b * float(doc_len) / float(self.avgdl or 1.0)))
                for token in query_tokens:
                    frequency = freqs.get(token, 0)
                    if frequency <= 0:
                        continue
                    idf = self.idf.get(token, 0.0)
                    score += idf * (
                        (float(frequency) * (self.k1 + 1.0))
                        / (float(frequency) + denominator_bias)
                    )
                scores.append(score)
            return scores


def _default_embedding_fn(texts: list[str], *, ollama_url: str, model: str) -> list[list[float]]:
    return embed_texts(
        texts,
        metadata={
            "task_type": "embedding",
            "component": "hybrid_retriever",
            "operation": "hybrid_retrieve",
        },
    )


def _default_secondary_embedding_fn(
    texts: list[str],
    *,
    llm_url: str | None,
    model: str | None,
) -> list[list[float]]:
    return embed_texts_batched(texts, llm_url=llm_url, model=model)


def _tokenize(text: Any) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or ""))]


def _coerce_optional_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _chunk_identity(chunk: dict[str, Any]) -> str:
    chunk_id = str(chunk.get("chunk_id") or "").strip()
    if chunk_id:
        return chunk_id
    source_file = str(chunk.get("source_file") or "").strip()
    page_start = chunk.get("page_start")
    page_end = chunk.get("page_end")
    text = str(chunk.get("text") or "").strip()[:80]
    return f"{source_file}:{page_start}:{page_end}:{text}"


def _chunk_text_hash(chunk: dict[str, Any]) -> str:
    normalized = re.sub(r"\s+", " ", str(chunk.get("text") or "")).strip().lower()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _chunk_dedupe_key(chunk: dict[str, Any]) -> str:
    chunk_id = str(chunk.get("chunk_id") or "").strip()
    if chunk_id:
        return f"chunk_id:{chunk_id}"
    text_hash = _chunk_text_hash(chunk)
    if text_hash:
        return f"text_hash:{text_hash}"
    return f"fallback:{_chunk_identity(chunk)}"


def _build_family_filter(framework_families: list[str] | None) -> qmodels.Filter | None:
    normalized = list(
        dict.fromkeys(
            str(family or "").strip()
            for family in (framework_families or [])
            if str(family or "").strip()
        )
    )
    if not normalized:
        return None
    return qmodels.Filter(
        should=[
            qmodels.FieldCondition(
                key="framework_family",
                match=qmodels.MatchValue(value=family),
            )
            for family in normalized
        ]
    )


def _normalize_ticker_token(value: Any) -> str:
    token = str(value or "").strip().upper()
    if not token:
        return ""
    if token.startswith("ASX:"):
        token = token.split(":", 1)[1].strip()
    return token


def _ticker_values_from_field(value: Any) -> set[str]:
    if value in (None, ""):
        return set()
    if isinstance(value, (list, tuple, set)):
        values: set[str] = set()
        for item in value:
            values.update(_ticker_values_from_field(item))
        return values
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return set()
        if raw.startswith("["):
            try:
                decoded = json.loads(raw)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, list):
                return _ticker_values_from_field(decoded)
        if any(separator in raw for separator in (",", ";", "|", "\n", "\t")):
            return {
                token
                for token in (
                    _normalize_ticker_token(part)
                    for part in re.split(r"[,;|\s]+", raw)
                )
                if token
            }
        token = _normalize_ticker_token(raw)
        return {token} if token else set()
    token = _normalize_ticker_token(value)
    return {token} if token else set()


def _payload_ticker_values(payload: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    values.update(_ticker_values_from_field(payload.get("ticker")))
    values.update(_ticker_values_from_field(payload.get("primary_ticker")))
    values.update(_ticker_values_from_field(payload.get("tickers")))
    return values


def _payload_matches_ticker(payload: dict[str, Any], ticker: str | None) -> bool:
    normalized_ticker = _normalize_ticker_token(ticker)
    if not normalized_ticker:
        return True
    return normalized_ticker in _payload_ticker_values(payload)


def _build_ticker_filter(collection_name: str, ticker: str | None) -> qmodels.Filter | None:
    normalized_ticker = _normalize_ticker_token(ticker)
    if not normalized_ticker or str(collection_name or "").strip() not in _TICKER_FILTER_COLLECTIONS:
        return None
    if str(collection_name or "").strip() == NEWS_CHUNKS_COLLECTION_NAME:
        return qmodels.Filter(
            should=[
                qmodels.FieldCondition(
                    key=key,
                    match=qmodels.MatchValue(value=normalized_ticker),
                )
                for key in ("ticker", "primary_ticker", "tickers")
            ]
        )
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="ticker",
                match=qmodels.MatchValue(value=normalized_ticker),
            )
        ]
    )


def _build_search_filter(
    *,
    collection_name: str,
    framework_families: list[str] | None,
    ticker: str | None,
) -> qmodels.Filter | None:
    family_filter = _build_family_filter(framework_families)
    ticker_filter = _build_ticker_filter(collection_name, ticker)
    if family_filter is None:
        return ticker_filter
    if ticker_filter is None:
        return family_filter
    return qmodels.Filter(must=[ticker_filter, family_filter])


def _boost_retrieval_score(
    *,
    base_score: float,
    payload: dict[str, Any],
    ticker: str | None,
    financial_intents: list[str] | None,
) -> float:
    boosted_score = float(base_score)
    if ticker and _payload_matches_ticker(payload, ticker):
        boosted_score *= 1.25
    if financial_intents:
        doc_class = str(payload.get("doc_class") or "").strip().lower()
        title = str(payload.get("title") or "").strip().lower()
        if doc_class == "financial":
            boosted_score *= 1.15
        if any(marker in title for marker in FINANCIAL_TITLE_MARKERS):
            boosted_score *= 1.10
    return boosted_score


class HybridRetriever:
    def __init__(
        self,
        *,
        qdrant_client: QdrantClient | Any | None = None,
        qdrant_url: str | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_fn: Callable[..., list[list[float]]] | None = None,
        secondary_embedding_fn: Callable[..., list[list[float]]] | None = None,
        ollama_url: str | None = None,
        embed_model: str | None = None,
        secondary_llm_url: str | None = None,
        secondary_embed_model: str | None = None,
    ) -> None:
        self.qdrant_client = qdrant_client or QdrantClient(
            url=str(qdrant_url or settings.qdrant_url),
            timeout=int(getattr(settings, "qdrant_timeout_seconds", 60) or 60),
        )
        self.collection_name = str(collection_name or DEFAULT_COLLECTION_NAME)
        self.embedding_fn = embedding_fn or _default_embedding_fn
        self.secondary_embedding_fn = secondary_embedding_fn or _default_secondary_embedding_fn
        self.ollama_url = str(ollama_url or settings.ollama_url)
        self.embed_model = str(embed_model or settings.embed_model)
        self.secondary_llm_url = secondary_llm_url
        self.secondary_embed_model = secondary_embed_model

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.embedding_fn(texts, ollama_url=self.ollama_url, model=self.embed_model)

    def _embed_secondary_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.secondary_embedding_fn(
            texts,
            llm_url=self.secondary_llm_url,
            model=self.secondary_embed_model,
        )

    def _resolve_collection_names(self) -> list[str]:
        requested = [self.collection_name]
        if self.collection_name == COMMENTARY_COLLECTION_NAME:
            requested = [COMMENTARY_COLLECTION_NAME, COMMENTARY_COLLECTION_V2_NAME]

        try:
            existing = {
                str(collection.name or "").strip()
                for collection in self.qdrant_client.get_collections().collections
                if str(getattr(collection, "name", "") or "").strip()
            }
        except Exception:
            return requested

        available = [collection_name for collection_name in requested if collection_name in existing]
        if available:
            return available
        return requested

    def _collection_vector_size(self, collection_name: str) -> int:
        info = self.qdrant_client.get_collection(collection_name=collection_name)
        params = getattr(info.config, "params", None)
        vectors = getattr(params, "vectors", None) if params is not None else None

        if isinstance(vectors, qmodels.VectorParams):
            return int(vectors.size)
        if isinstance(vectors, dict):
            first = next(iter(vectors.values()), None)
            if isinstance(first, qmodels.VectorParams):
                return int(first.size)

        raise RuntimeError(
            f"Qdrant collection '{collection_name}' has no vector config. "
            "Recreate the collection with the expected vector config."
        )

    def _resolve_query_embeddings(
        self,
        normalized_query: str,
    ) -> tuple[list[float], dict[str, list[float]]]:
        primary_embeddings = self._embed_texts([normalized_query])
        primary_query_embedding = primary_embeddings[0] if primary_embeddings else []

        collection_names = self._resolve_collection_names()
        if collection_names == [self.collection_name]:
            return primary_query_embedding, {self.collection_name: primary_query_embedding}

        secondary_embeddings = self._embed_secondary_texts([normalized_query])
        secondary_query_embedding = secondary_embeddings[0] if secondary_embeddings else []
        candidate_embeddings: dict[int, list[float]] = {}
        for embedding in (primary_query_embedding, secondary_query_embedding):
            if embedding:
                candidate_embeddings.setdefault(len(embedding), embedding)

        collection_query_embeddings: dict[str, list[float]] = {}
        for collection_name in collection_names:
            expected_dim = self._collection_vector_size(collection_name)
            matched_embedding = candidate_embeddings.get(expected_dim)
            if matched_embedding is None:
                raise RuntimeError(
                    f"No query embedding available for collection '{collection_name}' "
                    f"with expected dimension {expected_dim}."
                )
            collection_query_embeddings[collection_name] = matched_embedding

        return collection_query_embeddings.get(COMMENTARY_COLLECTION_NAME, primary_query_embedding), collection_query_embeddings

    def _normalize_chunk_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = {key: value for key, value in dict(payload or {}).items() if not str(key).startswith("_")}
        normalized["chunk_id"] = str(
            normalized.get("chunk_id") or normalized.get("logical_point_id") or ""
        ).strip()
        normalized["source_file"] = str(
            normalized.get("source_file") or normalized.get("source_file_name") or ""
        ).strip()
        normalized["framework_family"] = str(normalized.get("framework_family") or "").strip()
        normalized["section"] = str(normalized.get("section") or "").strip()
        normalized["text"] = str(normalized.get("text") or "").strip()
        normalized["page_start"] = _coerce_optional_int(normalized.get("page_start"))
        normalized["page_end"] = _coerce_optional_int(normalized.get("page_end"))
        return normalized

    def _scroll_chunks(self, framework_families: list[str] | None) -> list[dict[str, Any]]:
        return self._scroll_chunks_for_collection(
            collection_name=self.collection_name,
            framework_families=framework_families,
        )

    def _scroll_chunks_for_collection(
        self,
        *,
        collection_name: str,
        framework_families: list[str] | None,
        ticker: str | None = None,
    ) -> list[dict[str, Any]]:
        scroll_filter = _build_search_filter(
            collection_name=collection_name,
            framework_families=framework_families,
            ticker=ticker,
        )
        chunks: list[dict[str, Any]] = []
        offset: Any = None

        while True:
            records, offset = self.qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=SCROLL_BATCH_SIZE,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not records:
                break
            for record in records:
                payload = dict(getattr(record, "payload", None) or {})
                if not payload:
                    continue
                normalized = self._normalize_chunk_payload(payload)
                if normalized.get("text"):
                    chunks.append(normalized)
            if offset is None:
                break

        if chunks or _build_ticker_filter(collection_name, ticker) is None:
            return chunks

        logger.info(
            "hybrid_retriever_ticker_fallback",
            extra={
                "collection_name": collection_name,
                "ticker": ticker,
                "strategy": "scroll",
            },
        )
        return self._scroll_chunks_for_collection(
            collection_name=collection_name,
            framework_families=framework_families,
            ticker=None,
        )

    def _search_collection_points(
        self,
        *,
        collection_name: str,
        query_embedding: list[float],
        framework_families: list[str] | None,
        ticker: str | None,
        top_k: int,
    ) -> tuple[list[Any], bool]:
        query_filter = _build_search_filter(
            collection_name=collection_name,
            framework_families=framework_families,
            ticker=ticker,
        )
        points = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=int(top_k),
            with_payload=True,
            with_vectors=False,
        )
        if points or _build_ticker_filter(collection_name, ticker) is None:
            return points, False

        logger.info(
            "hybrid_retriever_ticker_fallback",
            extra={
                "collection_name": collection_name,
                "ticker": ticker,
                "strategy": "vector",
            },
        )
        points = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=_build_family_filter(framework_families),
            limit=int(top_k),
            with_payload=True,
            with_vectors=False,
        )
        return points, True

    def _score_chunk(
        self,
        *,
        chunk: dict[str, Any],
        ticker: str | None,
        financial_intents: list[str] | None,
    ) -> None:
        chunk["vector_score"] = _boost_retrieval_score(
            base_score=float(chunk.get("vector_score") or 0.0),
            payload=chunk,
            ticker=ticker,
            financial_intents=financial_intents,
        )
        chunk["keyword_score"] = _boost_retrieval_score(
            base_score=float(chunk.get("keyword_score") or 0.0),
            payload=chunk,
            ticker=ticker,
            financial_intents=financial_intents,
        )

    def _sort_hits(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            hits,
            key=lambda chunk: (
                -float(chunk.get("vector_score") or 0.0),
                -float(chunk.get("keyword_score") or 0.0),
                _chunk_identity(chunk),
            ),
        )

    def _maybe_log_retrieval_context(
        self,
        *,
        ticker: str | None,
        financial_intents: list[str] | None,
        used_ticker_fallback: bool,
    ) -> None:
        if ticker is None and not financial_intents and not used_ticker_fallback:
            return
        logger.info(
            "hybrid_retriever_query_context",
            extra={
                "collection_name": self.collection_name,
                "ticker": ticker,
                "financial_intents": list(financial_intents or []),
                "ticker_filter_applied": bool(_build_ticker_filter(self.collection_name, ticker)),
                "used_ticker_fallback": used_ticker_fallback,
            },
        )

    def _vector_search(
        self,
        *,
        collection_name: str,
        query_embedding: list[float],
        framework_families: list[str] | None,
        ticker: str | None,
        financial_intents: list[str] | None,
        top_k: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        if not query_embedding or top_k <= 0:
            return [], False

        points, used_ticker_fallback = self._search_collection_points(
            collection_name=collection_name,
            query_embedding=query_embedding,
            framework_families=framework_families,
            ticker=ticker,
            top_k=top_k,
        )

        hits: list[dict[str, Any]] = []
        for point in points:
            payload = dict(getattr(point, "payload", None) or {})
            if not payload:
                continue
            normalized = self._normalize_chunk_payload(payload)
            normalized["collection_name"] = collection_name
            normalized["collections"] = [collection_name]
            normalized["vector_score"] = float(getattr(point, "score", 0.0) or 0.0)
            normalized["keyword_score"] = float(normalized.get("keyword_score") or 0.0)
            normalized["retrieval_strategies"] = ["vector"]
            self._score_chunk(
                chunk=normalized,
                ticker=ticker,
                financial_intents=financial_intents,
            )
            hits.append(normalized)
        return self._sort_hits(hits), used_ticker_fallback

    def _keyword_search(
        self,
        *,
        collection_name: str,
        query: str,
        framework_families: list[str] | None,
        ticker: str | None,
        financial_intents: list[str] | None,
        top_k: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        if top_k <= 0:
            return [], False

        query_tokens = _tokenize(query)
        if not query_tokens:
            return [], False

        chunks = self._scroll_chunks_for_collection(
            collection_name=collection_name,
            framework_families=framework_families,
            ticker=ticker,
        )
        if not chunks:
            return [], False

        corpus_tokens = [_tokenize(chunk.get("text")) for chunk in chunks]
        bm25 = BM25Okapi(corpus_tokens)
        raw_scores = [float(score) for score in bm25.get_scores(query_tokens)]

        ranked = sorted(
            zip(chunks, raw_scores),
            key=lambda item: (-item[1], _chunk_identity(item[0])),
        )
        if not ranked or ranked[0][1] <= 0.0:
            return [], False

        hits: list[dict[str, Any]] = []
        for chunk, score in ranked:
            if score <= 0.0:
                break
            normalized = dict(chunk)
            normalized["collection_name"] = collection_name
            normalized["collections"] = [collection_name]
            normalized["vector_score"] = float(normalized.get("vector_score") or 0.0)
            normalized["keyword_score"] = score
            normalized["retrieval_strategies"] = ["keyword"]
            self._score_chunk(
                chunk=normalized,
                ticker=ticker,
                financial_intents=financial_intents,
            )
            hits.append(normalized)
            if len(hits) >= int(top_k):
                break
        return self._sort_hits(hits), False

    def _merge_hits(
        self,
        *,
        vector_hits: list[dict[str, Any]],
        keyword_hits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for hit in vector_hits + keyword_hits:
            identity = _chunk_dedupe_key(hit)
            existing = merged.get(identity)
            if existing is None:
                merged[identity] = dict(hit)
                merged[identity]["collections"] = sorted(
                    {
                        str(collection or "").strip()
                        for collection in (
                            list(hit.get("collections") or [])
                            + [hit.get("collection_name")]
                        )
                        if str(collection or "").strip()
                    }
                )
                continue
            existing["vector_score"] = max(
                float(existing.get("vector_score") or 0.0),
                float(hit.get("vector_score") or 0.0),
            )
            existing["keyword_score"] = max(
                float(existing.get("keyword_score") or 0.0),
                float(hit.get("keyword_score") or 0.0),
            )
            strategies = set(existing.get("retrieval_strategies") or [])
            strategies.update(hit.get("retrieval_strategies") or [])
            existing["retrieval_strategies"] = sorted(strategies)
            collections = {
                str(collection or "").strip()
                for collection in list(existing.get("collections") or [])
                + list(hit.get("collections") or [])
                + [existing.get("collection_name"), hit.get("collection_name")]
                if str(collection or "").strip()
            }
            existing["collections"] = sorted(collections)
            if len(existing["collections"]) == 1:
                existing["collection_name"] = existing["collections"][0]

        return sorted(
            merged.values(),
            key=lambda chunk: (
                -float(chunk.get("vector_score") or 0.0),
                -float(chunk.get("keyword_score") or 0.0),
                _chunk_identity(chunk),
            ),
        )

    def retrieve(
        self,
        *,
        query: str,
        framework_families: list[str] | None,
        ticker: str | None = None,
        financial_intents: list[str] | None = None,
        top_k_vector: int = 20,
        top_k_keyword: int = 20,
    ) -> dict[str, Any]:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            raise ValueError("query is required")

        query_embedding, collection_query_embeddings = self._resolve_query_embeddings(normalized_query)

        vector_hits: list[dict[str, Any]] = []
        keyword_hits: list[dict[str, Any]] = []
        used_ticker_fallback = False
        for collection_name, collection_query_embedding in collection_query_embeddings.items():
            collection_vector_hits, vector_fallback = self._vector_search(
                collection_name=collection_name,
                query_embedding=collection_query_embedding,
                framework_families=framework_families,
                ticker=ticker,
                financial_intents=financial_intents,
                top_k=max(0, int(top_k_vector)),
            )
            vector_hits.extend(collection_vector_hits)
            used_ticker_fallback = used_ticker_fallback or vector_fallback
            collection_keyword_hits, keyword_fallback = self._keyword_search(
                collection_name=collection_name,
                query=normalized_query,
                framework_families=framework_families,
                ticker=ticker,
                financial_intents=financial_intents,
                top_k=max(0, int(top_k_keyword)),
            )
            keyword_hits.extend(collection_keyword_hits)
            used_ticker_fallback = used_ticker_fallback or keyword_fallback
        merged_chunks = self._merge_hits(vector_hits=vector_hits, keyword_hits=keyword_hits)
        self._maybe_log_retrieval_context(
            ticker=ticker,
            financial_intents=financial_intents,
            used_ticker_fallback=used_ticker_fallback,
        )

        return {
            "query_embedding": query_embedding,
            "query_embeddings": collection_query_embeddings,
            "vector_hits": vector_hits,
            "keyword_hits": keyword_hits,
            "chunks": merged_chunks,
        }
