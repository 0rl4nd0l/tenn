from __future__ import annotations

from app.services.hybrid_retriever import (
    NEWS_CHUNKS_COLLECTION_NAME,
    _build_ticker_filter,
    _payload_matches_ticker,
)
from app.services.tenn_chat import _filter_news_by_ticker


def test_payload_matches_ticker_scalar_ticker() -> None:
    assert _payload_matches_ticker({"ticker": "a2m"}, "A2M")


def test_payload_matches_ticker_scalar_primary_ticker() -> None:
    assert _payload_matches_ticker({"ticker": "", "primary_ticker": "a2m"}, "A2M")


def test_payload_matches_ticker_list_when_top_level_ticker_is_blank() -> None:
    payload = {"ticker": "", "primary_ticker": "", "tickers": ["BHP", "a2m"]}

    assert _payload_matches_ticker(payload, "A2M")


def test_payload_matches_ticker_list_when_top_level_ticker_is_other_primary() -> None:
    payload = {"ticker": "AEG", "primary_ticker": "AEG", "tickers": ["A2M", "AEG"]}

    assert _payload_matches_ticker(payload, "A2M")


def test_payload_matches_ticker_string_tickers() -> None:
    payload = {"ticker": "", "primary_ticker": "", "tickers": "|BHP|A2M|"}

    assert _payload_matches_ticker(payload, "A2M")


def test_payload_matches_ticker_rejects_unrelated_tickers() -> None:
    payload = {"ticker": "AEG", "primary_ticker": "AEG", "tickers": ["AEG", "BCA"]}

    assert not _payload_matches_ticker(payload, "A2M")


def test_chat_filter_keeps_list_match_when_top_level_ticker_is_blank() -> None:
    chunks = [
        {"chunk_id": "blank-list", "ticker": "", "tickers": ["BHP", "A2M"]},
        {"chunk_id": "unrelated", "ticker": "AEG", "tickers": ["AEG", "BCA"]},
    ]

    assert [
        chunk["chunk_id"] for chunk in _filter_news_by_ticker(chunks, "A2M")
    ] == ["blank-list"]


def test_chat_filter_keeps_list_match_when_top_level_ticker_is_other_primary() -> None:
    chunks = [
        {
            "chunk_id": "linked-secondary",
            "ticker": "AEG",
            "primary_ticker": "AEG",
            "tickers": ["A2M", "AEG"],
        },
        {"chunk_id": "unrelated", "ticker": "BHP", "tickers": ["BHP"]},
    ]

    assert [
        chunk["chunk_id"] for chunk in _filter_news_by_ticker(chunks, "A2M")
    ] == ["linked-secondary"]


def test_chat_filter_keeps_primary_ticker_match() -> None:
    chunks = [
        {"chunk_id": "primary-only", "ticker": "", "primary_ticker": "A2M"},
        {"chunk_id": "unrelated", "ticker": "AEG", "primary_ticker": "AEG"},
    ]

    assert [
        chunk["chunk_id"] for chunk in _filter_news_by_ticker(chunks, "A2M")
    ] == ["primary-only"]


def test_chat_filter_rejects_unrelated_tickers() -> None:
    chunks = [
        {"chunk_id": "unrelated-a", "ticker": "AEG", "tickers": ["AEG", "BCA"]},
        {"chunk_id": "unrelated-b", "primary_ticker": "BHP", "tickers": ["BHP"]},
    ]

    assert _filter_news_by_ticker(chunks, "A2M") == []


def test_news_qdrant_filter_matches_ticker_primary_ticker_or_tickers() -> None:
    query_filter = _build_ticker_filter(NEWS_CHUNKS_COLLECTION_NAME, "a2m")

    assert query_filter is not None
    assert not (query_filter.must or [])
    assert [
        condition.key for condition in (query_filter.should or [])
    ] == ["ticker", "primary_ticker", "tickers"]
    assert all(
        condition.match.value == "A2M" for condition in (query_filter.should or [])
    )
