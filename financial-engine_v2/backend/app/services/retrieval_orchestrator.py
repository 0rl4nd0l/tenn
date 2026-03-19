from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from app.services.commentary_memo_extractor import load_commentary_memos
from app.services.framework_classifier import FrameworkClassifier
from app.services.framework_retriever import FrameworkRetriever
from app.services.hybrid_retriever import HybridRetriever
from app.services.reranker import RetrievalReranker
from app.services.source_weighting import apply_weighting_to_chunk


def _page_range(page_start: int | None, page_end: int | None) -> str | None:
    if page_start is None and page_end is None:
        return None
    start = int(page_start if page_start is not None else page_end)
    end = int(page_end if page_end is not None else page_start)
    return f"{start}-{end}"


class RetrievalOrchestrator:
    class _NullFrameworkClassifier:
        def classify(self, query: str, top_k: int = 3) -> list[str]:
            return []

    class _NullFrameworkRetriever:
        def retrieve(self, framework_families: list[str] | None) -> list[dict[str, Any]]:
            return []

    class _NullHybridRetriever:
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
            return {"query_embedding": [], "chunks": []}

    class _NullReranker:
        def rerank(
            self,
            *,
            query: str,
            chunks: list[dict[str, Any]],
            framework_families: list[str] | None,
            top_k: int = 8,
            query_embedding: list[float] | None = None,
        ) -> list[dict[str, Any]]:
            return []

    def __init__(
        self,
        *,
        classifier: FrameworkClassifier | None = None,
        framework_retriever: FrameworkRetriever | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        reranker: RetrievalReranker | None = None,
        commentary_retriever: HybridRetriever | None = None,
        commentary_reranker: RetrievalReranker | None = None,
        commentary_memos_path: str | Path | None = None,
    ) -> None:
        self.classifier = classifier or self._build_default_classifier()
        self.framework_retriever = framework_retriever or self._build_default_framework_retriever()
        self.hybrid_retriever = hybrid_retriever or HybridRetriever()
        self.reranker = reranker or RetrievalReranker()
        if commentary_retriever is not None:
            self.commentary_retriever = commentary_retriever
        elif any(dep is not None for dep in (classifier, framework_retriever, hybrid_retriever, reranker)):
            self.commentary_retriever = self._NullHybridRetriever()
        else:
            self.commentary_retriever = HybridRetriever(collection_name="commentary_chunks")
        if commentary_reranker is not None:
            self.commentary_reranker = commentary_reranker
        elif commentary_retriever is None and any(dep is not None for dep in (classifier, framework_retriever, hybrid_retriever, reranker)):
            self.commentary_reranker = self._NullReranker()
        else:
            self.commentary_reranker = RetrievalReranker()
        self.commentary_memos_path = Path(commentary_memos_path).expanduser().resolve() if commentary_memos_path else None

    def _build_default_classifier(self) -> FrameworkClassifier | _NullFrameworkClassifier:
        try:
            return FrameworkClassifier()
        except FileNotFoundError:
            return self._NullFrameworkClassifier()

    def _build_default_framework_retriever(self) -> FrameworkRetriever | _NullFrameworkRetriever:
        try:
            return FrameworkRetriever()
        except FileNotFoundError:
            return self._NullFrameworkRetriever()

    def _assemble_context(
        self,
        *,
        frameworks: list[dict[str, Any]],
        methodology_chunks: list[dict[str, Any]],
        commentary_chunks: list[dict[str, Any]],
        commentary_memos: list[dict[str, Any]],
    ) -> dict[str, Any]:
        source_pages: dict[str, set[str]] = defaultdict(set)
        for chunk in methodology_chunks + commentary_chunks:
            source_file = str(chunk.get("source_file") or "").strip()
            page_range = _page_range(chunk.get("page_start"), chunk.get("page_end"))
            if source_file and page_range:
                source_pages[source_file].add(page_range)

        sources = [
            {
                "source_file": source_file,
                "page_ranges": sorted(page_ranges),
            }
            for source_file, page_ranges in sorted(source_pages.items())
        ]

        return {
            "frameworks": frameworks,
            "chunks": methodology_chunks,
            "sources": sources,
            "methodology_chunks": methodology_chunks,
            "commentary_chunks": commentary_chunks,
            "commentary_memos": commentary_memos,
        }

    @staticmethod
    def _is_optional_collection_missing(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "does not exist",
                "not found",
                "missing collection",
                "vector dimension error",
                "dimension mismatch",
            )
        )

    def _retrieve_commentary_chunks(
        self,
        *,
        query: str,
        ticker: str | None,
        financial_intents: list[str] | None,
        top_k_vector: int,
        top_k_keyword: int,
        top_k_commentary: int,
    ) -> list[dict[str, Any]]:
        try:
            commentary_result = self.commentary_retriever.retrieve(
                query=query,
                framework_families=None,
                ticker=ticker,
                financial_intents=financial_intents,
                top_k_vector=top_k_vector,
                top_k_keyword=top_k_keyword,
            )
        except Exception as exc:
            if self._is_optional_collection_missing(exc):
                return []
            raise

        reranked = self.commentary_reranker.rerank(
            query=query,
            chunks=commentary_result.get("chunks") or [],
            framework_families=None,
            top_k=top_k_commentary,
            query_embedding=commentary_result.get("query_embedding"),
        )
        return [apply_weighting_to_chunk(chunk) for chunk in reranked]

    def _load_commentary_memos(self, commentary_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.commentary_memos_path is None:
            memos = load_commentary_memos()
        else:
            memos = load_commentary_memos(self.commentary_memos_path)
        source_ids = {
            str(chunk.get("source_id") or "").strip()
            for chunk in commentary_chunks
            if str(chunk.get("source_id") or "").strip()
        }
        if not source_ids:
            return []
        return [
            memo
            for memo in memos
            if str(memo.get("source_id") or "").strip() in source_ids
        ]

    def retrieve(
        self,
        query: str,
        *,
        ticker: str | None = None,
        financial_intents: list[str] | None = None,
        top_k_families: int = 3,
        top_k_chunks: int = 8,
        top_k_vector: int = 20,
        top_k_keyword: int = 20,
        top_k_commentary: int = 4,
        top_k_commentary_vector: int = 12,
        top_k_commentary_keyword: int = 12,
    ) -> dict[str, Any]:
        framework_families = self.classifier.classify(query, top_k=top_k_families)
        frameworks = self.framework_retriever.retrieve(framework_families)
        try:
            hybrid_result = self.hybrid_retriever.retrieve(
                query=query,
                framework_families=framework_families,
                ticker=ticker,
                financial_intents=financial_intents,
                top_k_vector=top_k_vector,
                top_k_keyword=top_k_keyword,
            )
            methodology_chunks = self.reranker.rerank(
                query=query,
                chunks=hybrid_result.get("chunks") or [],
                framework_families=framework_families,
                top_k=top_k_chunks,
                query_embedding=hybrid_result.get("query_embedding"),
            )
        except Exception as exc:
            if self._is_optional_collection_missing(exc):
                methodology_chunks = []
            else:
                raise

        commentary_chunks = self._retrieve_commentary_chunks(
            query=query,
            ticker=ticker,
            financial_intents=financial_intents,
            top_k_vector=top_k_commentary_vector,
            top_k_keyword=top_k_commentary_keyword,
            top_k_commentary=top_k_commentary,
        )
        commentary_memos = self._load_commentary_memos(commentary_chunks)
        return self._assemble_context(
            frameworks=frameworks,
            methodology_chunks=methodology_chunks,
            commentary_chunks=commentary_chunks,
            commentary_memos=commentary_memos,
        )
