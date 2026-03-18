from __future__ import annotations

import re
from typing import Any, Callable

import numpy as np

from app.core.config import settings
from app.services.llm import embed_texts


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _default_embedding_fn(texts: list[str], *, ollama_url: str, model: str) -> list[list[float]]:
    return embed_texts(
        texts,
        metadata={
            "task_type": "embedding",
            "component": "reranker",
            "operation": "rerank",
        },
    )


def _tokenize(text: Any) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or ""))]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    if left_vector.shape != right_vector.shape:
        return 0.0
    denominator = float(np.linalg.norm(left_vector) * np.linalg.norm(right_vector))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left_vector, right_vector) / denominator)


def _normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high == low:
        return [1.0 if high > 0.0 else 0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _keyword_overlap(query_tokens: set[str], chunk_tokens: set[str]) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    overlap = len(query_tokens & chunk_tokens)
    if overlap <= 0:
        return 0.0
    return float(overlap) / float(max(1, len(query_tokens)))


class RetrievalReranker:
    def __init__(
        self,
        *,
        embedding_fn: Callable[..., list[list[float]]] | None = None,
        ollama_url: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self.embedding_fn = embedding_fn or _default_embedding_fn
        self.ollama_url = str(ollama_url or settings.ollama_url)
        self.embed_model = str(embed_model or settings.embed_model)

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.embedding_fn(texts, ollama_url=self.ollama_url, model=self.embed_model)

    def rerank(
        self,
        *,
        query: str,
        chunks: list[dict[str, Any]],
        framework_families: list[str] | None,
        top_k: int = 8,
        query_embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        limit = max(0, int(top_k))
        if limit == 0 or not chunks:
            return []

        prepared = [dict(chunk) for chunk in chunks]
        query_tokens = set(_tokenize(query))
        texts = [str(chunk.get("text") or "") for chunk in prepared]
        vector_scores = [float(chunk.get("vector_score") or 0.0) for chunk in prepared]

        embedding_scores: list[float]
        if query_embedding:
            chunk_embeddings = self._embed_texts(texts)
            if len(chunk_embeddings) == len(prepared):
                embedding_scores = [
                    max(_cosine_similarity(query_embedding, chunk_embedding), vector_scores[index])
                    for index, chunk_embedding in enumerate(chunk_embeddings)
                ]
            else:
                embedding_scores = list(vector_scores)
        else:
            vectors = self._embed_texts([str(query or "")] + texts)
            if len(vectors) == len(prepared) + 1:
                query_vector = vectors[0]
                embedding_scores = [
                    max(_cosine_similarity(query_vector, chunk_embedding), vector_scores[index])
                    for index, chunk_embedding in enumerate(vectors[1:])
                ]
            else:
                embedding_scores = list(vector_scores)

        keyword_scores: list[float] = []
        raw_keyword_overlap: list[float] = []
        for chunk in prepared:
            overlap = _keyword_overlap(query_tokens, set(_tokenize(chunk.get("text"))))
            raw_keyword_overlap.append(overlap)
            keyword_scores.append(float(chunk.get("keyword_score") or 0.0) + overlap)

        normalized_embedding = _normalize_scores(embedding_scores)
        normalized_keyword = _normalize_scores(keyword_scores)
        family_set = {
            str(family or "").strip()
            for family in (framework_families or [])
            if str(family or "").strip()
        }

        for index, chunk in enumerate(prepared):
            family_match = 1.0 if str(chunk.get("framework_family") or "").strip() in family_set else 0.0
            rerank_score = (
                (0.55 * normalized_embedding[index])
                + (0.30 * normalized_keyword[index])
                + (0.15 * family_match)
            )
            chunk["embedding_similarity"] = round(float(embedding_scores[index]), 6)
            chunk["keyword_overlap"] = round(float(raw_keyword_overlap[index]), 6)
            chunk["family_match"] = bool(family_match)
            chunk["rerank_score"] = round(float(rerank_score), 6)

        prepared.sort(
            key=lambda chunk: (
                -float(chunk.get("rerank_score") or 0.0),
                -float(chunk.get("embedding_similarity") or 0.0),
                -float(chunk.get("keyword_score") or 0.0),
                str(chunk.get("chunk_id") or ""),
                str(chunk.get("source_file") or ""),
                int(chunk.get("page_start") or 0),
            )
        )
        return prepared[:limit]
