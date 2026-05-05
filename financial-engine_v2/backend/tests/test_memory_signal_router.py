from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.company_memory import CompanyMemoryStore
from app.services.market_memory import MarketMemoryStore
from app.services.memory_signal_router import (
    route_signals,
    signals_from_commentary_memo,
    signals_from_news_memo,
)


def _tickers_with_statement(
    company_store: CompanyMemoryStore,
    tickers: list[str],
    text: str,
) -> list[str]:
    needle = text.lower()
    return [
        ticker
        for ticker in tickers
        if any(
            needle in entry["statement"].lower()
            for entry in company_store.list_entries(ticker)
        )
    ]


def test_commentary_memo_generates_company_signals_with_required_fields() -> None:
    memo = {
        "source_id": "comm-1",
        "speaker": "Analyst",
        "claims": ["BHP management is prioritising cost-out initiatives."],
        "catalysts": ["Copper expansion could lift group volumes."],
        "risks": ["WA labour tightness remains a risk."],
        "sentiment": "bullish",
        "time_horizon": "medium-term",
        "tickers": ["BHP"],
        "source_type": "youtube_transcript",
        "published_at": "2026-04-09T10:00:00+00:00",
    }

    signals = signals_from_commentary_memo(memo)

    assert len(signals) == 3
    assert {signal["type"] for signal in signals} == {
        "management_guidance",
        "catalyst",
        "risk",
    }
    assert {signal["entity_id"] for signal in signals} == {"BHP"}
    for signal in signals:
        assert signal["statement"]
        assert signal["confidence"] > 0
        assert signal["materiality"] > 0
        assert signal["source"].startswith("commentary:")
        assert signal["source_id"] == "comm-1"
        assert signal["metadata"]["specificity"] >= 0.28


def test_commentary_claims_are_split_into_atomic_signals() -> None:
    memo = {
        "source_id": "comm-atomic",
        "speaker": "Analyst",
        "claims": [
            "BHP management guides FY2026 copper growth higher; rail constraints are easing."
        ],
        "catalysts": [],
        "risks": [],
        "sentiment": "bullish",
        "time_horizon": "medium-term",
        "tickers": ["BHP"],
        "source_type": "podcast_transcript",
        "published_at": "2026-04-09T10:00:00+00:00",
    }

    signals = signals_from_commentary_memo(memo)

    assert [signal["statement"] for signal in signals] == [
        "BHP management guides FY2026 copper growth higher",
        "rail constraints are easing",
    ]
    assert signals[0]["type"] == "management_guidance"
    assert signals[1]["type"] == "operating_context"


def test_low_value_signal_fragments_are_rejected_before_persistence() -> None:
    memo = {
        "source_id": "comm-low-value",
        "speaker": "Analyst",
        "claims": [
            "Things look good.",
            "BHP targets FY2026 copper growth from the expansion plan.",
        ],
        "catalysts": [],
        "risks": [],
        "sentiment": "bullish",
        "time_horizon": "long-term",
        "tickers": ["BHP"],
        "source_type": "youtube_transcript",
        "published_at": "2026-04-09T10:00:00+00:00",
    }

    signals = signals_from_commentary_memo(memo)

    assert len(signals) == 1
    assert (
        signals[0]["statement"]
        == "BHP targets FY2026 copper growth from the expansion plan"
    )


def test_specific_guidance_scores_higher_confidence_and_materiality() -> None:
    memo = {
        "source_id": "news-strong",
        "provider": "afr",
        "key_events": [],
        "sentiment": "bullish",
        "impact_magnitude": "material",
        "tickers": ["BHP"],
        "claims": [
            "BHP management guides FY2026 copper growth higher through the expansion plan."
        ],
        "risks": [],
        "published_at": "2026-04-09T10:00:00+00:00",
    }

    signals = signals_from_news_memo(memo)

    assert len(signals) == 1
    assert signals[0]["type"] == "management_guidance"
    assert signals[0]["confidence"] >= 0.75
    assert signals[0]["materiality"] >= 0.8
    assert signals[0]["metadata"]["themes"] == ["growth"]
    assert "fiscal_year" in signals[0]["metadata"]["time_refs"]


def test_commentary_memo_generates_sector_and_macro_market_signals() -> None:
    memo = {
        "source_id": "comm-2",
        "speaker": "Macro desk",
        "claims": [
            "Iron ore sector supply discipline is improving.",
            "China stimulus could support bulk commodity demand.",
        ],
        "catalysts": [],
        "risks": [],
        "sentiment": "bullish",
        "time_horizon": "near-term",
        "tickers": [],
        "source_type": "market_commentary",
        "published_at": "2026-04-09T10:00:00+00:00",
    }

    signals = signals_from_commentary_memo(memo)

    scopes = {
        (signal["scope"], signal.get("sector") or signal.get("macro_topic"))
        for signal in signals
    }
    assert ("sector", "Materials") in scopes
    assert ("macro", "China stimulus") in scopes


def test_news_memo_generates_company_and_market_signals() -> None:
    memo = {
        "source_id": "news-1",
        "provider": "afr",
        "key_events": ["BHP flagged stronger realised iron ore pricing."],
        "sentiment": "bullish",
        "impact_magnitude": "material",
        "tickers": ["BHP"],
        "claims": ["Iron ore market sentiment is improving."],
        "risks": ["China demand remains uncertain."],
        "published_at": "2026-04-09T10:00:00+00:00",
    }

    signals = signals_from_news_memo(memo)

    company_signals = [signal for signal in signals if signal.get("entity_id") == "BHP"]
    market_signals = [
        signal for signal in signals if signal.get("scope") in {"sector", "macro"}
    ]
    assert company_signals
    assert market_signals
    assert any(signal.get("sector") == "Materials" for signal in market_signals)
    assert any(signal.get("macro_topic") == "China demand" for signal in market_signals)


def test_route_signals_persists_company_and_market_entries(tmp_path: Path) -> None:
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    signals = [
        {
            "type": "claim",
            "statement": "BHP management is prioritising cost-out initiatives.",
            "entity_id": "BHP",
            "confidence": 0.7,
            "materiality": 0.6,
            "persistence": "medium",
            "status": "active",
            "source": "commentary:youtube_transcript",
            "source_id": "comm-3",
        },
        {
            "scope": "sector",
            "sector": "Materials",
            "type": "sector_trend",
            "statement": "Iron ore market sentiment is improving.",
            "confidence": 0.65,
            "materiality": 0.8,
            "persistence": "medium",
            "status": "active",
            "source": "news:afr",
            "source_id": "news-3",
            "linked_tickers": ["BHP"],
        },
    ]

    result = route_signals(
        signals,
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert result["company_memory_count"] == 1
    assert result["market_memory_count"] == 1
    assert len(company_store.list_entries("BHP")) == 1
    assert len(market_store.list_sector_entries("Materials")) == 1


def test_multi_topic_commentary_does_not_fanout_primary_company_signal(
    tmp_path: Path,
) -> None:
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    memo = {
        "source_id": "synthetic:a2m-recall-multi-topic",
        "speaker": "Synthetic Analyst",
        "claims": [
            "A2M share price dropped 10 due to a product recall.",
            "Atlassian share price is up about 30 due to better than expected results.",
            "Pettimed capital raising at 1 cent per share.",
            "Chrysos Corporation share price fell 6.39 despite a positive trading update.",
            "Accent Group share price is down 12.9 after a downgrade announcement.",
            "US non farm payrolls data expected to show job growth of 60,000 jobs in May.",
        ],
        "catalysts": [],
        "risks": ["Inflation and interest rates remain a macro risk for the market."],
        "sentiment": "mixed",
        "time_horizon": "near-term",
        "tickers": ["A2M", "ATLASSIAN", "PETTIMED", "CHRYSOS", "ACC", "BHP", "COH"],
        "source_type": "youtube_transcript",
        "published_at": "2026-05-05T00:00:00+00:00",
    }

    route_signals(
        signals_from_commentary_memo(memo),
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    all_tickers = ["A2M", "ATLASSIAN", "PETTIMED", "CHRYSOS", "ACC", "BHP", "COH"]
    assert _tickers_with_statement(company_store, all_tickers, "product recall") == [
        "A2M"
    ]
    assert _tickers_with_statement(
        company_store, all_tickers, "ATLASSIAN share price"
    ) == ["ATLASSIAN"]
    assert _tickers_with_statement(
        company_store, all_tickers, "PETTIMED capital raising"
    ) == ["PETTIMED"]

    macro_entries = market_store.list_macro_entries("Interest rates")
    assert any(
        "interest rates" in entry["statement"].lower() for entry in macro_entries
    )
    for ticker in all_tickers:
        assert all(
            "interest rates" not in entry["statement"].lower()
            for entry in company_store.list_entries(ticker)
        )


def test_single_company_commentary_still_routes_all_company_statements(
    tmp_path: Path,
) -> None:
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    memo = {
        "source_id": "synthetic:single-company-bhp",
        "speaker": "Synthetic Analyst",
        "claims": [
            "BHP management is prioritising cost-out initiatives.",
            "Copper expansion could lift group volumes.",
        ],
        "catalysts": [],
        "risks": [],
        "sentiment": "bullish",
        "time_horizon": "medium-term",
        "tickers": ["BHP"],
        "source_type": "youtube_transcript",
        "published_at": "2026-05-05T00:00:00+00:00",
    }

    result = route_signals(
        signals_from_commentary_memo(memo),
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    statements = [entry["statement"] for entry in company_store.list_entries("BHP")]
    assert result["company_memory_count"] == 2
    assert statements == [
        "BHP management is prioritising cost-out initiatives",
        "Copper expansion could lift group volumes",
    ]


def test_multi_ticker_memo_without_statement_target_does_not_fanout(
    tmp_path: Path,
) -> None:
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    memo = {
        "source_id": "synthetic:ambiguous-multi-company",
        "speaker": "Synthetic Analyst",
        "claims": [
            "Management guides FY2026 growth higher after the expansion plan.",
        ],
        "catalysts": [],
        "risks": [],
        "sentiment": "bullish",
        "time_horizon": "medium-term",
        "tickers": ["BHP", "RIO"],
        "source_type": "youtube_transcript",
        "published_at": "2026-05-05T00:00:00+00:00",
    }

    result = route_signals(
        signals_from_commentary_memo(memo),
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert result["company_memory_count"] == 0
    assert company_store.list_entries("BHP") == []
    assert company_store.list_entries("RIO") == []


def test_multi_ticker_memo_honors_statement_level_target_ticker(
    tmp_path: Path,
) -> None:
    company_store = CompanyMemoryStore(tmp_path / "company_memory.sqlite")
    market_store = MarketMemoryStore(tmp_path / "market_memory.sqlite")
    memo = {
        "source_id": "synthetic:structured-target",
        "speaker": "Synthetic Analyst",
        "claims": [
            {
                "statement": "Management guides FY2026 copper growth higher through the expansion plan.",
                "target_ticker": "BHP",
            }
        ],
        "catalysts": [],
        "risks": [],
        "sentiment": "bullish",
        "time_horizon": "medium-term",
        "tickers": ["BHP", "RIO"],
        "source_type": "youtube_transcript",
        "published_at": "2026-05-05T00:00:00+00:00",
    }

    result = route_signals(
        signals_from_commentary_memo(memo),
        company_memory_store=company_store,
        market_memory_store=market_store,
    )

    assert result["company_memory_count"] == 1
    assert len(company_store.list_entries("BHP")) == 1
    assert company_store.list_entries("RIO") == []


def test_statement_dict_without_text_is_not_stringified_into_memory() -> None:
    memo = {
        "source_id": "synthetic:dict-without-statement",
        "speaker": "Synthetic Analyst",
        "claims": [{"ticker": "BHP", "metadata": {"raw": "not a statement"}}],
        "catalysts": [],
        "risks": [],
        "sentiment": "mixed",
        "time_horizon": "medium-term",
        "tickers": ["BHP"],
        "source_type": "youtube_transcript",
        "published_at": "2026-05-05T00:00:00+00:00",
    }

    assert signals_from_commentary_memo(memo) == []
