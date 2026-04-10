from __future__ import annotations

from types import SimpleNamespace

from qdrant_client.http import models as qmodels

from app.services import rag


def _hit(
    score: float,
    *,
    article_id: str,
    title: str,
    ticker: str,
    tickers: list[str] | None = None,
    published_at: str = "2026-04-08T00:00:00Z",
):
    return SimpleNamespace(
        score=score,
        payload={
            "article_id": article_id,
            "chunk_id": f"news:{article_id}:0",
            "title": title,
            "ticker": ticker,
            "tickers": tickers or ([ticker] if ticker else []),
            "published_at": published_at,
        },
    )


def test_build_news_ticker_filter_matches_primary_or_linked_ticker() -> None:
    query_filter = rag._build_news_ticker_filter("bhp")

    assert query_filter is not None
    assert len(query_filter.should or []) == 2
    keys = [condition.key for condition in query_filter.should or []]
    assert keys == ["ticker", "tickers"]
    assert all(
        condition.match.value == "BHP" for condition in query_filter.should or []
    )


def test_normalize_news_results_dedupes_by_article_and_prefers_title_match() -> None:
    hits = [
        _hit(
            0.56,
            article_id="roundup",
            title="Market News and Updates on NZX Stocks",
            ticker="BHP",
        ),
        _hit(
            0.54,
            article_id="roundup",
            title="Market News and Updates on NZX Stocks",
            ticker="BHP",
            published_at="2026-04-08T01:00:00Z",
        ),
        _hit(
            0.45,
            article_id="bhp-news",
            title="BHP copper expansion update",
            ticker="SFR",
            tickers=["SFR", "BHP"],
        ),
    ]

    results = rag._normalize_news_results(hits, ticker="BHP", top_k=5)

    assert [row["payload"]["article_id"] for row in results] == ["bhp-news", "roundup"]
    assert len(results) == 2


def test_query_news_chunks_expands_candidate_limit_and_dedupes(monkeypatch) -> None:
    class _Client:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def search(self, **kwargs):
            self.calls.append(kwargs)
            return [
                _hit(
                    0.60,
                    article_id="roundup",
                    title="Market News and Updates on NZX Stocks",
                    ticker="BHP",
                ),
                _hit(
                    0.59,
                    article_id="roundup",
                    title="Market News and Updates on NZX Stocks",
                    ticker="BHP",
                    published_at="2026-04-08T01:00:00Z",
                ),
                _hit(
                    0.48,
                    article_id="bhp-news",
                    title="BHP output update",
                    ticker="SFR",
                    tickers=["SFR", "BHP"],
                ),
            ]

    client = _Client()
    monkeypatch.setattr(
        rag, "embed_texts", lambda texts, metadata=None: [[0.1, 0.2, 0.3]]
    )
    monkeypatch.setattr(rag, "_build_qdrant_client", lambda: client)
    monkeypatch.setattr(rag.settings, "enable_qdrant", True)

    result = rag.query_news_chunks(query="BHP", ticker="BHP", top_k=2)

    assert client.calls[0]["limit"] == 12
    query_filter = client.calls[0]["query_filter"]
    assert isinstance(query_filter, qmodels.Filter)
    assert len(query_filter.must or []) >= 1
    assert isinstance(result["results"], list)
    assert [row["payload"]["article_id"] for row in result["results"]] == [
        "bhp-news",
        "roundup",
    ]
