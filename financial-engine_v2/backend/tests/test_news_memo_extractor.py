"""Tests for NewsMemoExtractor — schema validation, normalization, and upsert idempotency."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.services.news_memo_extractor import (
    NewsMemoExtractor,
    _normalize_impact_magnitude,
    _normalize_list,
    _normalize_sentiment,
    load_news_memos,
)


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
        candidate_tickers=["XYZ", "ABC"],
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
    assert memo["extraction_provenance"]["component"] == "news_memo_extractor"
    assert memo["extraction_provenance"]["llm_model"]
    assert memo["extraction_provenance"]["max_article_chars"] == 5000

    # LLM was called exactly once
    assert len(llm_fn.calls) == 1  # type: ignore[attr-defined]


def test_extract_prompt_includes_current_date_anchor(tmp_memos_path: Path) -> None:
    llm_fn = _make_llm_fn(GOOD_LLM_RESPONSE)
    extractor = NewsMemoExtractor(llm_fn=llm_fn, memos_path=tmp_memos_path)

    extractor.extract(
        source_id="news-anchored",
        article_text="Company XYZ announced a major acquisition today...",
        provider="newspaper4k",
        published_at="2026-03-30",
    )

    prompt = llm_fn.calls[0]["prompt"]  # type: ignore[attr-defined]
    today_iso = datetime.now(timezone.utc).date().isoformat()
    assert today_iso in prompt
    assert "historical context" in prompt.lower()


def test_extract_prompt_honors_article_char_cap(tmp_memos_path: Path) -> None:
    llm_fn = _make_llm_fn(GOOD_LLM_RESPONSE)
    extractor = NewsMemoExtractor(
        llm_fn=llm_fn,
        memos_path=tmp_memos_path,
        max_article_chars=12,
    )

    extractor.extract(
        source_id="news-capped",
        article_text="A" * 40,
        provider="newspaper4k",
        published_at="2026-03-30",
    )

    prompt = llm_fn.calls[0]["prompt"]  # type: ignore[attr-defined]
    assert "A" * 12 in prompt
    assert "A" * 13 not in prompt


def test_extract_routes_configured_llm_runtime_in_metadata(
    tmp_memos_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def llm_fn(*, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
        calls.append({"prompt": prompt, "metadata": metadata})
        return GOOD_LLM_RESPONSE

    extractor = NewsMemoExtractor(
        llm_fn=llm_fn,
        llm_url="http://127.0.0.1:8001",
        llm_model="model:qwen3.5-35b-a3b-apex",
        memos_path=tmp_memos_path,
    )

    extractor.extract(
        source_id="news-model",
        article_text="Company XYZ announced a major acquisition today.",
        provider="newspaper4k",
        published_at="2026-03-30",
    )

    metadata = calls[0]["metadata"]
    assert metadata["component"] == "news_memo_extractor"
    assert metadata["llm_url"] == "http://127.0.0.1:8001"
    assert metadata["llm_model"] == "model:qwen3.5-35b-a3b-apex"


def test_extract_records_effective_anthropic_route_in_provenance(
    tmp_memos_path: Path,
) -> None:
    def llm_fn(*, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
        metadata.update(
            {
                "effective_provider": "anthropic",
                "effective_model": "claude-sonnet-test",
                "effective_base_url": "https://api.anthropic.com",
                "routing_reason": "metric_extraction_active",
            }
        )
        return GOOD_LLM_RESPONSE

    extractor = NewsMemoExtractor(llm_fn=llm_fn, memos_path=tmp_memos_path)

    memo = extractor.extract(
        source_id="news-api-route",
        article_text="NYSE:XYZ announced a supported update.",
        provider="newspaper4k",
        published_at="2026-07-15",
    )

    provenance = memo["extraction_provenance"]
    assert provenance["llm_provider"] == "anthropic"
    assert provenance["llm_model"] == "claude-sonnet-test"
    assert provenance["llm_url"] == "https://api.anthropic.com"
    assert provenance["routing_reason"] == "metric_extraction_active"


def test_extract_prompt_cleans_html_and_lists_candidate_tickers(
    tmp_memos_path: Path,
) -> None:
    llm_fn = _make_llm_fn(GOOD_LLM_RESPONSE)
    extractor = NewsMemoExtractor(llm_fn=llm_fn, memos_path=tmp_memos_path)

    extractor.extract(
        source_id="news-html",
        article_text=(
            "<p>Company update for NYSE:XYZ.</p>"
            "<script>alert('ignore me')</script>"
        ),
        provider="newspaper4k",
        published_at="2026-03-30",
    )

    prompt = llm_fn.calls[0]["prompt"]  # type: ignore[attr-defined]
    assert "<p>" not in prompt
    assert "<script>" not in prompt
    assert "ignore me" not in prompt
    assert "CANDIDATE_TICKERS: XYZ" in prompt
    assert "arrays of plain strings, not objects" in prompt


def test_normalize_drops_dictlike_items_and_outside_candidate_tickers(
    tmp_memos_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    raw_response = {
        "key_events": [
            {"date": "2026-03-30", "description": "dict should not persist"},
            "{'date': '2026-03-30', 'description': 'stringified dict'}",
            "Plain supported event",
        ],
        "sentiment": "bullish",
        "impact_magnitude": "moderate",
        "tickers": ["XYZ", "M&G PLC", "ASX:ABC"],
        "claims": ["Grounded claim"],
        "risks": [],
    }
    extractor = NewsMemoExtractor(
        llm_fn=_make_llm_fn(raw_response),
        memos_path=tmp_memos_path,
    )

    with caplog.at_level(logging.WARNING, logger="app.services.news_memo_extractor"):
        memo = extractor.extract(
            source_id="news-strict",
            article_text="Company XYZ update.",
            provider="newspaper4k",
            candidate_tickers=["XYZ"],
        )

    assert memo["key_events"] == ["Plain supported event"]
    assert memo["tickers"] == ["XYZ"]
    assert memo["claims"] == ["Grounded claim"]
    assert any("dropped non-scalar list item" in r.message for r in caplog.records)
    assert any("dropped dictlike string item" in r.message for r in caplog.records)
    assert any("outside candidate allowlist" in r.message for r in caplog.records)


def test_empty_candidate_list_drops_freeform_tickers(tmp_memos_path: Path) -> None:
    llm_fn = _make_llm_fn({**GOOD_LLM_RESPONSE, "tickers": ["M&G PLC"]})
    extractor = NewsMemoExtractor(llm_fn=llm_fn, memos_path=tmp_memos_path)

    memo = extractor.extract(
        source_id="news-no-ticker",
        article_text="M&G reported net inflows.",
        provider="newspaper4k",
        candidate_tickers=[],
    )

    assert memo["tickers"] == []


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


def test_upsert_preserves_extraction_provenance(tmp_memos_path: Path) -> None:
    extractor = NewsMemoExtractor(
        llm_fn=_make_llm_fn(GOOD_LLM_RESPONSE),
        llm_model="model:qwen3.5-35b-a3b-apex",
        memos_path=tmp_memos_path,
        max_article_chars=2500,
    )

    stored = extractor.extract_and_store(
        source_id="news-provenance",
        article_text="NYSE:XYZ announced a transaction.",
        provider="newspaper4k",
        candidate_tickers=["XYZ"],
        route_signals=False,
    )

    rows = load_news_memos(tmp_memos_path)
    assert rows == [stored]
    provenance = rows[0]["extraction_provenance"]
    assert provenance["component"] == "news_memo_extractor"
    assert provenance["llm_model"] == "model:qwen3.5-35b-a3b-apex"
    assert provenance["llm_url"]
    assert provenance["max_article_chars"] == 2500


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


# ---------------------------------------------------------------------------
# Regression: malformed LLM JSON emits a warning (LATENT-1)
# ---------------------------------------------------------------------------


def test_normalize_list_warns_on_non_list_value(caplog: pytest.LogCaptureFixture) -> None:
    """_normalize_list must emit a WARNING when coercing a non-list, non-null value.

    Regression for audit finding LATENT-1: garbage LLM JSON was silently coerced
    to a list, making it impossible to distinguish from a legitimate empty result.
    """
    import logging

    with caplog.at_level(logging.WARNING, logger="app.services.news_memo_extractor"):
        result = _normalize_list("not a list", field_name="key_events")

    assert result == ["not a list"]
    assert any("coerced non-list" in record.message for record in caplog.records), (
        "Expected a WARNING about non-list coercion, got: "
        + str([r.message for r in caplog.records])
    )
    assert any("key_events" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Regression: all-empty extraction emits a warning (LATENT-2)
# ---------------------------------------------------------------------------


def test_empty_extraction_emits_warning(
    tmp_memos_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """NewsMemoExtractor must emit a WARNING when all extracted fields are empty.

    Regression for audit finding LATENT-2: an empty memo was written to disk
    silently, preventing re-extraction and making garbage indistinguishable from
    a legitimate 'no events' article.
    """
    import logging

    empty_response: dict[str, Any] = {
        "key_events": [],
        "sentiment": "",
        "impact_magnitude": "",
        "tickers": [],
        "claims": [],
        "risks": [],
    }
    extractor = NewsMemoExtractor(
        llm_fn=_make_llm_fn(empty_response),
        memos_path=tmp_memos_path,
    )
    with caplog.at_level(logging.WARNING, logger="app.services.news_memo_extractor"):
        extractor.extract(
            source_id="test-src-001",
            article_text="Some article text.",
            provider="TestProvider",
            published_at="2026-04-15",
        )

    assert any(
        "all extracted fields are empty" in record.message for record in caplog.records
    ), (
        "Expected a WARNING about all-empty extraction, got: "
        + str([r.message for r in caplog.records])
    )
