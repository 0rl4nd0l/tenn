"""Tests for NewsMemoExtractor — schema validation, normalization, and upsert idempotency."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.news_memo_extractor import NewsMemoExtractor, _normalize_list, _normalize_sentiment, _normalize_impact_magnitude, load_news_memos


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_LLM_RESPONSE: dict[str, Any] = {
    "key_events": ["Company XYZ announced a $2B acquisition", "CEO resigned"],
    "sentiment": "bearish",
    "impact_magnitude": "material",
    "tickers": ["XYZ", "ABC"],
    "claims": ["Acquisition expected to close Q3 2026"],
    "risks": ["Regulatory approval uncertain", "Integration risk"],
}


def _make_llm_fn(response: Any = None):
    """Return a callable that mimics generate_json, recording call args."""
    calls: list[dict[str, Any]] = []

    def _fake_llm(**kwargs: Any) -> Any:
        calls.append(kwargs)
        return response if response is not None else GOOD_LLM_RESPONSE

    _fake_llm.calls = calls  # type: ignore[attr-defined]
    return _fake_llm


@pytest.fixture()
def tmp_memos_path(tmp_path: Path) -> Path:
    return tmp_path / "news_memos.jsonl"


# ---------------------------------------------------------------------------
# Test: extract produces valid schema with good LLM data
# ---------------------------------------------------------------------------


def test_extract_valid_schema(tmp_memos_path: Path) -> None:
    llm_fn = _make_llm_fn(GOOD_LLM_RESPONSE)
    extractor = NewsMemoExtractor(llm_fn=llm_fn, memos_path=tmp_memos_path)

    memo = extractor.extract(
        source_id="news-001",
        article_text="Company XYZ announced a major acquisition today...",
        provider="newspaper4k",
        published_at="2026-03-30",
    )

    # Required top-level keys present
    assert memo["source_id"] == "news-001"
    assert memo["provider"] == "newspaper4k"
    assert memo["published_at"] == "2026-03-30"

    # Schema fields from LLM response
    assert memo["key_events"] == ["Company XYZ announced a $2B acquisition", "CEO resigned"]
    assert memo["sentiment"] == "bearish"
    assert memo["impact_magnitude"] == "material"
    assert memo["tickers"] == ["XYZ", "ABC"]
    assert memo["claims"] == ["Acquisition expected to close Q3 2026"]
    assert memo["risks"] == ["Regulatory approval uncertain", "Integration risk"]

    # LLM was called exactly once
    assert len(llm_fn.calls) == 1  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Test: normalize handles missing/empty fields gracefully
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_response",
    [
        {},
        {"key_events": None, "sentiment": None, "impact_magnitude": None, "tickers": None, "claims": None, "risks": None},
        {"key_events": "", "sentiment": "INVALID", "impact_magnitude": "huge", "tickers": "", "claims": "", "risks": ""},
    ],
    ids=["empty-dict", "all-none", "invalid-values"],
)
def test_normalize_handles_missing_fields(tmp_memos_path: Path, raw_response: dict[str, Any]) -> None:
    llm_fn = _make_llm_fn(raw_response)
    extractor = NewsMemoExtractor(llm_fn=llm_fn, memos_path=tmp_memos_path)

    memo = extractor.extract(
        source_id="news-002",
        article_text="Some article text",
        provider="test",
    )

    # All list fields should be empty lists, not None or error
    assert memo["key_events"] == []
    assert memo["tickers"] == []
    assert memo["claims"] == []
    assert memo["risks"] == []

    # Sentiment and impact_magnitude should be empty string for invalid values
    assert memo["sentiment"] == ""
    assert memo["impact_magnitude"] == ""

    # Metadata still present
    assert memo["source_id"] == "news-002"
    assert memo["provider"] == "test"


# ---------------------------------------------------------------------------
# Test: upsert is idempotent (same source_id replaces, not duplicates)
# ---------------------------------------------------------------------------


def test_upsert_idempotent(tmp_memos_path: Path) -> None:
    extractor = NewsMemoExtractor(llm_fn=_make_llm_fn(), memos_path=tmp_memos_path)

    memo_v1 = {
        "source_id": "news-100",
        "provider": "newspaper4k",
        "key_events": ["Event A"],
        "sentiment": "bullish",
        "impact_magnitude": "minor",
        "tickers": ["AAA"],
        "claims": [],
        "risks": [],
        "published_at": "2026-03-01",
    }
    memo_v2 = {
        **memo_v1,
        "key_events": ["Event B", "Event C"],
        "sentiment": "bearish",
    }

    # First upsert — creates the row
    extractor.upsert(memo_v1)
    rows = load_news_memos(tmp_memos_path)
    assert len(rows) == 1
    assert rows[0]["key_events"] == ["Event A"]

    # Second upsert with same source_id — replaces, not appends
    extractor.upsert(memo_v2)
    rows = load_news_memos(tmp_memos_path)
    assert len(rows) == 1
    assert rows[0]["key_events"] == ["Event B", "Event C"]
    assert rows[0]["sentiment"] == "bearish"

    # Third upsert with different source_id — appends
    memo_other = {**memo_v1, "source_id": "news-200"}
    extractor.upsert(memo_other)
    rows = load_news_memos(tmp_memos_path)
    assert len(rows) == 2
    source_ids = [r["source_id"] for r in rows]
    assert "news-100" in source_ids
    assert "news-200" in source_ids


# ---------------------------------------------------------------------------
# Test: upsert rejects memo without source_id
# ---------------------------------------------------------------------------


def test_upsert_requires_source_id(tmp_memos_path: Path) -> None:
    extractor = NewsMemoExtractor(llm_fn=_make_llm_fn(), memos_path=tmp_memos_path)
    with pytest.raises(ValueError, match="source_id is required"):
        extractor.upsert({"provider": "test"})


# ---------------------------------------------------------------------------
# Test: normalize helpers directly
# ---------------------------------------------------------------------------


def test_normalize_list_deduplicates() -> None:
    assert _normalize_list(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_normalize_list_uppercase() -> None:
    assert _normalize_list(["abc", "ABC", "def"], uppercase=True) == ["ABC", "DEF"]


def test_normalize_sentiment_valid() -> None:
    assert _normalize_sentiment("bullish") == "bullish"
    assert _normalize_sentiment("BEARISH") == "bearish"
    assert _normalize_sentiment("mixed") == "mixed"
    assert _normalize_sentiment("neutral") == "neutral"


def test_normalize_sentiment_invalid() -> None:
    assert _normalize_sentiment("positive") == ""
    assert _normalize_sentiment(None) == ""
    assert _normalize_sentiment("") == ""


def test_normalize_impact_magnitude_valid() -> None:
    assert _normalize_impact_magnitude("material") == "material"
    assert _normalize_impact_magnitude("MODERATE") == "moderate"
    assert _normalize_impact_magnitude("minor") == "minor"


def test_normalize_impact_magnitude_invalid() -> None:
    assert _normalize_impact_magnitude("huge") == ""
    assert _normalize_impact_magnitude(None) == ""
