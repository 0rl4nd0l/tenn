from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.memory_signal_router as memory_signal_router
from app.services.commentary_memo_extractor import CommentaryMemoExtractor
from app.services.company_memory import CompanyMemoryStore
from app.services.market_memory import MarketMemoryStore
from app.services.news_memo_extractor import NewsMemoExtractor


def test_commentary_extractor_can_store_and_route_signals(tmp_path: Path) -> None:
    extractor = CommentaryMemoExtractor(
        llm_fn=lambda **_: {
            "speaker": "Analyst",
            "claims": ["BHP management is prioritising cost-out initiatives."],
            "catalysts": ["Iron ore market sentiment is improving."],
            "risks": [],
            "sentiment": "bullish",
            "time_horizon": "medium-term",
            "tickers": ["BHP"],
        },
        memos_path=tmp_path / "commentary_memos.jsonl",
    )
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    result = extractor.extract_store_and_route(
        source_id="comm-route-1",
        transcript_text="placeholder",
        speaker="Analyst",
        source_type="youtube_transcript",
        published_at="2026-04-09T10:00:00+00:00",
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert result["signals"]
    assert len(company_store.list_entries("BHP")) == 2
    assert len(market_store.list_sector_entries("Materials")) == 1


def test_commentary_extract_and_store_routes_signals_by_default(tmp_path: Path) -> None:
    extractor = CommentaryMemoExtractor(
        llm_fn=lambda **_: {
            "speaker": "Analyst",
            "claims": ["BHP management is prioritising cost-out initiatives."],
            "catalysts": ["Iron ore market sentiment is improving."],
            "risks": [],
            "sentiment": "bullish",
            "time_horizon": "medium-term",
            "tickers": ["BHP"],
        },
        memos_path=tmp_path / "commentary_memos.jsonl",
    )
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    memo = extractor.extract_and_store(
        source_id="comm-route-2",
        transcript_text="placeholder",
        speaker="Analyst",
        source_type="youtube_transcript",
        published_at="2026-04-09T10:00:00+00:00",
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert memo["source_id"] == "comm-route-2"
    assert memo["signal_routing"]["status"] == "ok"
    assert memo["signal_routing"]["company_memory_count"] == 2
    assert memo["signal_routing"]["market_memory_count"] == 1
    assert len(company_store.list_entries("BHP")) == 2
    assert len(market_store.list_sector_entries("Materials")) == 1


def test_commentary_extract_and_store_reports_routing_failure(
    monkeypatch, tmp_path: Path
) -> None:
    extractor = CommentaryMemoExtractor(
        llm_fn=lambda **_: {
            "speaker": "Analyst",
            "claims": ["BHP management is prioritising cost-out initiatives."],
            "catalysts": ["Iron ore market sentiment is improving."],
            "risks": [],
            "sentiment": "bullish",
            "time_horizon": "medium-term",
            "tickers": ["BHP"],
        },
        memos_path=tmp_path / "commentary_memos.jsonl",
    )

    def _raise(*args, **kwargs):
        raise RuntimeError("routing unavailable")

    monkeypatch.setattr(memory_signal_router, "route_signals", _raise)

    memo = extractor.extract_and_store(
        source_id="comm-route-error",
        transcript_text="placeholder",
        speaker="Analyst",
        source_type="youtube_transcript",
        published_at="2026-04-09T10:00:00+00:00",
    )

    assert memo["source_id"] == "comm-route-error"
    assert memo["signal_routing"] == {
        "status": "error",
        "error": "routing unavailable",
    }


def test_news_extractor_can_store_and_route_signals(tmp_path: Path) -> None:
    extractor = NewsMemoExtractor(
        llm_fn=lambda **_: {
            "key_events": ["BHP flagged stronger realised iron ore pricing."],
            "sentiment": "bullish",
            "impact_magnitude": "material",
            "tickers": ["BHP"],
            "claims": ["China demand remains supportive for iron ore markets."],
            "risks": [],
        },
        memos_path=tmp_path / "news_memos.jsonl",
    )
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    result = extractor.extract_store_and_route(
        source_id="news-route-1",
        article_text="placeholder",
        provider="afr",
        published_at="2026-04-09T10:00:00+00:00",
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert result["routing"]["company_memory_count"] >= 1
    assert result["routing"]["market_memory_count"] >= 1
    assert len(company_store.list_entries("BHP")) >= 1
    assert len(market_store.list_macro_entries("China demand")) == 1


def test_news_extract_and_store_routes_signals_by_default(tmp_path: Path) -> None:
    extractor = NewsMemoExtractor(
        llm_fn=lambda **_: {
            "key_events": ["BHP flagged stronger realised iron ore pricing."],
            "sentiment": "bullish",
            "impact_magnitude": "material",
            "tickers": ["BHP"],
            "claims": ["China demand remains supportive for iron ore markets."],
            "risks": [],
        },
        memos_path=tmp_path / "news_memos.jsonl",
    )
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")

    memo = extractor.extract_and_store(
        source_id="news-route-2",
        article_text="placeholder",
        provider="afr",
        published_at="2026-04-09T10:00:00+00:00",
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert memo["source_id"] == "news-route-2"
    assert memo["signal_routing"]["status"] == "ok"
    assert memo["signal_routing"]["company_memory_count"] >= 1
    assert memo["signal_routing"]["market_memory_count"] >= 1
    assert len(company_store.list_entries("BHP")) >= 1
    assert len(market_store.list_macro_entries("China demand")) == 1


def test_news_extract_and_store_reports_routing_failure(
    monkeypatch, tmp_path: Path
) -> None:
    extractor = NewsMemoExtractor(
        llm_fn=lambda **_: {
            "key_events": ["BHP flagged stronger realised iron ore pricing."],
            "sentiment": "bullish",
            "impact_magnitude": "material",
            "tickers": ["BHP"],
            "claims": ["China demand remains supportive for iron ore markets."],
            "risks": [],
        },
        memos_path=tmp_path / "news_memos.jsonl",
    )

    def _raise(*args, **kwargs):
        raise RuntimeError("routing unavailable")

    monkeypatch.setattr(memory_signal_router, "route_signals", _raise)

    memo = extractor.extract_and_store(
        source_id="news-route-error",
        article_text="placeholder",
        provider="afr",
        published_at="2026-04-09T10:00:00+00:00",
    )

    assert memo["source_id"] == "news-route-error"
    assert memo["signal_routing"] == {
        "status": "error",
        "error": "routing unavailable",
    }
