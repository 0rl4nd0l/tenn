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
    primary_ticker: str | None = None,
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
            "primary_ticker": primary_ticker or ticker,
            "published_at": published_at,
        },
    )


def test_build_news_ticker_filter_matches_primary_or_linked_ticker() -> None:
    query_filter = rag._build_news_ticker_filter("bhp")

    assert query_filter is not None
    assert len(query_filter.should or []) == 3
    keys = [condition.key for condition in query_filter.should or []]
    assert keys == ["ticker", "primary_ticker", "tickers"]
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


def test_normalize_news_results_prefers_primary_ticker_and_recent_hits() -> None:
    hits = [
        _hit(
            0.67,
            article_id="broad-market-wrap",
            title="The ASX 200 rallied as miners and tech recovered",
            ticker="C1X",
            primary_ticker="C1X",
            tickers=["BHP", "CSL", "MIN", "NST", "XRO"] * 8,
            published_at="2026-04-07T07:39:51Z",
        ),
        _hit(
            0.62,
            article_id="linked-recent",
            title="ASX edges lower as miners move",
            ticker="RIO",
            primary_ticker="RIO",
            tickers=["BHP", "RIO"],
            published_at="2026-05-13T21:59:00Z",
        ),
        _hit(
            0.50,
            article_id="primary-recent",
            title="BHP operational update",
            ticker="BHP",
            primary_ticker="BHP",
            published_at="2026-05-12T21:59:00Z",
        ),
    ]

    results = rag._normalize_news_results(hits, ticker="BHP", top_k=3)

    assert [row["payload"]["article_id"] for row in results] == [
        "primary-recent",
        "linked-recent",
        "broad-market-wrap",
    ]


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

    assert client.calls[0]["limit"] == 200
    query_filter = client.calls[0]["query_filter"]
    assert isinstance(query_filter, qmodels.Filter)
    assert len(query_filter.must or []) >= 1
    assert isinstance(result["results"], list)
    assert [row["payload"]["article_id"] for row in result["results"]] == [
        "bhp-news",
        "roundup",
    ]


def test_extract_ticker_handles_cued_lowercase_query() -> None:
    assert rag.extract_ticker("tell me about csl news") == "CSL"


def test_extract_ticker_rejects_plain_language_false_positive() -> None:
    assert rag.extract_ticker("How are things going?") is None


def test_extract_ticker_rejects_ambiguous_multi_ticker_query() -> None:
    assert rag.extract_ticker("Compare BHP and RIO news") is None
