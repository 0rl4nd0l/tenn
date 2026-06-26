from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from app.services.memory_events import emit_memory_read_event, suppress_memory_read_events
from cockpit.storage.state import StateStore


def test_cockpit_chat_stream_emits_only_status_plain_text_chunks_and_done(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            if on_chunk is not None:
                on_chunk("Hello ")
                on_chunk("there.")
            if on_status is not None:
                on_status("Resolving request context")
            if on_thinking is not None:
                on_thinking("internal assessment", "internal plan")
            return SimpleNamespace(
                text="Hello there.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 1234,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "hello", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    chunk_events = [event for event in data_events if event.get("type") == "chunk"]
    assert [event["data"]["text"] for event in chunk_events] == [
        "Hello ",
        "there.",
    ]
    assert all('{"type"' not in event["data"]["text"] for event in chunk_events)
    assert not [event for event in data_events if event.get("type") == "thinking"]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"]["text"] == "Hello there."


def test_cockpit_chat_stream_blocks_substantive_answer_without_sources(monkeypatch) -> None:
    finalize_calls: list[str] = []
    auto_flag_calls: list[str] = []

    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="BHP revenue grew sharply and broker sentiment improved.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            finalize_calls.append(kwargs["response"].text)

        def auto_flag_chat_response(self, **kwargs):
            auto_flag_calls.append(kwargs["response"].text)
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "tell me about BHP", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "can't verify that from current evidence" in done_events[-1]["data"]["text"].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]
    assert finalize_calls == [done_events[-1]["data"]["text"]]
    assert auto_flag_calls == [done_events[-1]["data"]["text"]]


def test_cockpit_chat_non_stream_allows_planning_without_sources(monkeypatch) -> None:
    finalized_metadata: list[dict] = []

    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            **kwargs,
        ):
            return SimpleNamespace(
                text=(
                    "We should check financials, recent announcements, price "
                    "context, and data quality next."
                ),
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            finalized_metadata.append(dict(kwargs["response"].routing_metadata or {}))

        def auto_flag_chat_response(self, **kwargs):
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "what should we check next?", "stream": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["text"].startswith("We should check financials")
    assert finalized_metadata[-1]["response_classification"] == (
        "planning_response"
    )
    assert "grounding_guard" not in finalized_metadata[-1]


def test_cockpit_chat_metadata_marks_price_trend_missing_market_evidence(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            **kwargs,
        ):
            return SimpleNamespace(
                text=(
                    "CSL looks bearish on the current price trend, while the "
                    "filing shows a buy-back notice."
                ),
                evidence=[
                    {
                        "type": "attached_source",
                        "details": {
                            "title": "CSL Appendix 3C buy-back notice",
                            "source_id": "asx:CSL:appendix-3c",
                            "doc_type": "asx_announcement",
                            "snippet": "CSL lodged an on-market buy-back notice.",
                            "evidence_labels": ["context_only"],
                            "claim_verified": False,
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            return None

        def auto_flag_chat_response(self, **kwargs):
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "what is the CSL price trend?", "stream": False},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    metadata = payload["routing_metadata"]
    assert payload["text"].startswith("DATA_MISSING / evidence gaps:")
    assert "market_data_missing: price or technical trend claims" in payload["text"]
    assert "unsupported_or_not_verified: treat unsupported claim families" in payload["text"]
    assert "context_only" in payload["sources"][0]["evidence_labels"]
    assert payload["sources"][0]["claim_verified"] is False
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert "market_data_missing" in metadata["evidence_labels"]
    assert "unsupported_or_not_verified" in metadata["evidence_labels"]
    assert metadata["missing_evidence_categories"] == ["market_data"]
    assert metadata["unsupported_claim_families"] == [
        "market_price_or_technical_trend"
    ]


def test_cockpit_chat_local_news_only_accepts_verified_news_shortcircuit_prompts(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(self, **kwargs):
            return SimpleNamespace(
                text=(
                    "Recent BHP-linked news:\n"
                    "- BHP local news update\n"
                    "  published: 2026-05-24"
                ),
                evidence=[
                    {
                        "type": "news_search",
                        "details": {
                            "ticker": "BHP",
                            "hits": [
                                {
                                    "title": "BHP local news update",
                                    "source_id": "news:bhp-local-news",
                                    "url": "https://news.example.com/bhp-local-news",
                                    "snippet": "BHP was covered in local market news.",
                                    "published_at": "2026-05-24T03:00:00Z",
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    for message in (
        "Use only local_news_context for BHP",
        "latest local news for BHP",
    ):
        response = client.post(
            "/api/cockpit/chat",
            json={
                "message": message,
                "ticker": "BHP",
                "stream": False,
                "rag": True,
                "web_search": False,
                "stateless_smoke": True,
            },
            headers={"X-Tenn-Stateless-Smoke": "1"},
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        metadata = payload["routing_metadata"]
        final_text = payload["text"]
        assert not final_text.startswith("DATA_MISSING")
        assert "BHP local news update" in final_text
        source = payload["sources"][0]
        assert source["source_id"] == "news:bhp-local-news"
        assert source["kind"] == "news"
        assert source["claim_verified"] is True
        assert "claim_verified" in source["evidence_labels"]
        assert "local_news_context" in source["evidence_labels"]
        assert "context_only" not in source["evidence_labels"]
        assert metadata["source_coverage_status"] == "claim_verified"
        assert metadata["claim_verified_source_count"] == 1
        assert metadata["local_news_context_count"] == 1
        assert metadata["claim_verified_local_news_count"] == 1


def test_cockpit_chat_local_news_only_news_shortcircuit_no_hit_stays_data_missing(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(self, **kwargs):
            return SimpleNamespace(
                text=(
                    "I couldn't find recent indexed news for COH. That is not "
                    "evidence there is no news."
                ),
                evidence=[
                    {
                        "type": "news_search",
                        "details": {
                            "ticker": "COH",
                            "hits": [],
                            "data_insufficient": True,
                        },
                    }
                ],
                action_preview={
                    "action_id": "daily_news_ingest",
                    "args": {"tickers": "COH", "since_hours": 24},
                },
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "Use only local_news_context for COH",
            "ticker": "COH",
            "stream": False,
            "rag": True,
            "web_search": False,
            "stateless_smoke": True,
        },
        headers={"X-Tenn-Stateless-Smoke": "1"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    metadata = payload["routing_metadata"]
    final_text = payload["text"]
    assert final_text.startswith("DATA_MISSING / evidence gaps:")
    assert "no relevant local_news_context" in final_text
    assert payload["sources"][0]["source_id"] == "search_news:no_hits:coh"
    assert payload["sources"][0]["claim_verified"] is False
    assert "no_hit" in payload["sources"][0]["evidence_labels"]
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert metadata["claim_verified_source_count"] == 0
    assert metadata["local_news_context_count"] == 0
    assert metadata["claim_verified_local_news_count"] == 0


def test_cockpit_chat_local_news_only_guard_blocks_filing_synthesis(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def chat_stream(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text=(
                    "Here is the latest local news for A2M: the class action "
                    "settlement and dividend update were lodged with the ASX."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "ticker": "A2M",
                            "qual_context_news": {
                                "hits": [
                                    {
                                        "title": "A2M infant formula recall uncertainty",
                                        "source_id": "news:a2m-recall:1",
                                        "snippet": (
                                            "A2M was covered in relation to infant "
                                            "formula recall uncertainty."
                                        ),
                                        "published_at": "2026-05-17T22:01:00Z",
                                        "evidence_labels": [
                                            "context_only",
                                            "local_news_context",
                                        ],
                                        "claim_verified": False,
                                    }
                                ]
                            },
                            "docs": [
                                {
                                    "title": "A2M dividend update",
                                    "source_id": "asx:A2M:dividend",
                                    "doc_type": "asx_announcement",
                                    "snippet": "A2M lodged a dividend update.",
                                    "evidence_labels": ["context_only"],
                                    "claim_verified": False,
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": (
                "What is the latest local news for A2M? Use local news evidence "
                "only. If no relevant local_news_context is available, say "
                "DATA_MISSING."
            ),
            "ticker": "A2M",
            "stream": False,
            "rag": True,
            "web_search": False,
            "stateless_smoke": True,
        },
        headers={"X-Tenn-Stateless-Smoke": "1"},
    )

    assert response.status_code == 200
    assert captured["persist_chat"] is False
    payload = response.json()["data"]
    metadata = payload["routing_metadata"]
    final_text = payload["text"]
    assert final_text.startswith("DATA_MISSING / evidence gaps:")
    assert "context-only and not claim-verified" in final_text
    assert "A2M infant formula recall uncertainty" in final_text
    assert "class action" not in final_text.lower()
    assert "dividend update were lodged" not in final_text.lower()
    news_source = next(
        source for source in payload["sources"] if source["source_id"].startswith("news:")
    )
    assert "local_news_context" in news_source["evidence_labels"]
    assert "context_only" in news_source["evidence_labels"]
    assert news_source["claim_verified"] is False
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert metadata["claim_verified_source_count"] == 0
    assert metadata["local_news_context_count"] == 1
    assert metadata["claim_verified_local_news_count"] == 0
    assert metadata["local_news_only_guard"]["applied"] is True
    assert "insufficient_for_recent_news" in metadata["evidence_labels"]


def test_cockpit_chat_local_news_only_guard_blocks_document_only_control(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(self, **kwargs):
            return SimpleNamespace(
                text=(
                    "COH latest local news includes a substantial holder notice "
                    "and dividend filing."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "ticker": "COH",
                            "docs": [
                                {
                                    "title": "COH substantial holder notice",
                                    "source_id": "asx:COH:holder",
                                    "doc_type": "asx_announcement",
                                    "snippet": "COH lodged a substantial holder notice.",
                                    "evidence_labels": ["context_only"],
                                    "claim_verified": False,
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "What is the latest local news for COH? Use local news evidence only.",
            "ticker": "COH",
            "stream": False,
            "rag": True,
            "web_search": False,
            "stateless_smoke": True,
        },
        headers={"X-Tenn-Stateless-Smoke": "1"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    metadata = payload["routing_metadata"]
    final_text = payload["text"]
    assert final_text.startswith("DATA_MISSING / evidence gaps:")
    assert "no relevant local_news_context" in final_text
    assert "substantial holder" not in final_text.lower()
    assert "dividend filing" not in final_text.lower()
    assert payload["sources"][0]["source_id"] == "asx:COH:holder"
    assert payload["sources"][0]["claim_verified"] is False
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert metadata["claim_verified_source_count"] == 0
    assert metadata["local_news_context_count"] == 0
    assert metadata["local_news_only_guard"]["applied"] is True
    assert "insufficient_for_recent_news" in metadata["evidence_labels"]


def test_cockpit_chat_local_news_only_stream_suppresses_unguarded_chunks(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(self, on_chunk=None, **kwargs):
            if on_chunk is not None:
                on_chunk(
                    "Here is the latest local news for A2M: class action settlement."
                )
            return SimpleNamespace(
                text=(
                    "Here is the latest local news for A2M: class action "
                    "settlement from an ASX filing."
                ),
                evidence=[
                    {
                        "type": "local_context",
                        "details": {
                            "ticker": "A2M",
                            "qual_context_news": {
                                "hits": [
                                    {
                                        "title": "A2M infant formula recall uncertainty",
                                        "source_id": "news:a2m-recall:1",
                                        "snippet": "A2M appeared in a recall context item.",
                                        "evidence_labels": [
                                            "context_only",
                                            "local_news_context",
                                        ],
                                        "claim_verified": False,
                                    }
                                ]
                            },
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={
            "message": "What is the latest local news for A2M? Use local news evidence only.",
            "ticker": "A2M",
            "stream": True,
            "rag": True,
            "web_search": False,
            "stateless_smoke": True,
        },
        headers={"X-Tenn-Stateless-Smoke": "1"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    chunk_events = [event for event in data_events if event.get("type") == "chunk"]
    done_events = [event for event in data_events if event.get("type") == "done"]

    assert chunk_events == []
    assert done_events[-1]["data"]["text"].startswith("DATA_MISSING / evidence gaps:")
    assert "class action" not in done_events[-1]["data"]["text"].lower()
    assert done_events[-1]["data"]["routing_metadata"]["local_news_only_guard"][
        "applied"
    ] is True


def test_cockpit_chat_stream_metadata_marks_price_trend_missing_market_evidence(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            **kwargs,
        ):
            if on_chunk is not None:
                on_chunk("CSL looks bearish on the current price trend.")
            return SimpleNamespace(
                text="CSL looks bearish on the current price trend.",
                evidence=[
                    {
                        "type": "attached_source",
                        "details": {
                            "title": "CSL Appendix 3C buy-back notice",
                            "source_id": "asx:CSL:appendix-3c",
                            "doc_type": "asx_announcement",
                            "snippet": "CSL lodged an on-market buy-back notice.",
                            "evidence_labels": ["context_only"],
                            "claim_verified": False,
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            return None

        def auto_flag_chat_response(self, **kwargs):
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "what is the CSL price trend?", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"]["text"].startswith("DATA_MISSING / evidence gaps:")
    assert (
        "market_data_missing: price or technical trend claims"
        in done_events[-1]["data"]["text"]
    )
    metadata = done_events[-1]["data"]["routing_metadata"]
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert "market_data_missing" in metadata["evidence_labels"]
    assert metadata["unsupported_claim_families"] == [
        "market_price_or_technical_trend"
    ]


def test_cockpit_chat_stateless_smoke_requires_header(monkeypatch) -> None:
    class FakeService:
        def chat_stream(self, **kwargs):
            raise AssertionError("stateless smoke without header should not run chat")

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "tell me about CSL",
            "stream": False,
            "stateless_smoke": True,
        },
    )

    assert response.status_code == 400
    assert "X-Tenn-Stateless-Smoke" in response.json()["detail"]


def test_cockpit_chat_stateless_smoke_non_stream_skips_persistence_and_auto_flag(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def chat_stream(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text="\n".join(
                    [
                        "Facts from financial truth:",
                        "- no canonical financial rows were returned",
                        "Interpretation from company memory:",
                        "- observed fact: CSL's share price dropped amid chaotic "
                        "trading after CEO resignation announcement",
                        "CSL looks bearish on the current price trend, while the "
                        "filing shows a buy-back notice.",
                    ]
                ),
                evidence=[
                    {
                        "type": "attached_source",
                        "details": {
                            "title": "CSL Appendix 3C buy-back notice",
                            "source_id": "asx:CSL:appendix-3c",
                            "doc_type": "asx_announcement",
                            "snippet": "CSL lodged an on-market buy-back notice.",
                            "evidence_labels": ["context_only"],
                            "claim_verified": False,
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                    "chat_persistence": "disabled",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            raise AssertionError("stateless smoke must not finalize chat state")

        def auto_flag_chat_response(self, **kwargs):
            raise AssertionError("stateless smoke must not persist auto flags")

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        headers={"X-Tenn-Stateless-Smoke": "1"},
        json={
            "message": "what is the CSL price trend?",
            "session_id": "real-session-should-not-be-read",
            "stream": False,
            "stateless_smoke": True,
        },
    )

    assert response.status_code == 200
    assert captured["persist_chat"] is False
    assert str(captured["session_id"]).startswith("stateless-smoke-")
    assert captured["session_id"] != "real-session-should-not-be-read"
    payload = response.json()["data"]
    assert payload["stateless_smoke"] is True
    assert payload["stateless_smoke_session_id"] == captured["session_id"]
    assert payload["auto_flag"] is None
    metadata = payload["routing_metadata"]
    assert metadata["stateless_smoke"] is True
    assert metadata["chat_persistence"] == "disabled"
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert "market_data_missing" in metadata["evidence_labels"]
    assert "metric_extraction_missing" in metadata["evidence_labels"]
    assert "insufficient_for_recent_news" in metadata["evidence_labels"]
    assert "unsupported_or_not_verified" in metadata["evidence_labels"]
    assert metadata["missing_evidence_categories"] == [
        "market_data",
        "metric_extraction",
        "recent_news",
    ]
    assert metadata["unsupported_claim_families"] == [
        "market_price_or_technical_trend",
        "recent_news_or_update",
    ]
    assert payload["text"].startswith("DATA_MISSING / evidence gaps:")
    assert "metric_extraction_missing: canonical metric" in payload["text"]
    assert "insufficient_for_recent_news: recent-news or recent-update claims" in payload["text"]
    assert (
        "Context-only company memory (not verified market/technical evidence):"
        in payload["text"]
    )
    assert "context-only company memory note (not market-verified)" in payload["text"]


def test_cockpit_chat_normal_non_stream_keeps_persistence_enabled(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    finalize_calls: list[str] = []
    auto_flag_calls: list[str] = []

    class FakeService:
        def chat_stream(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text="Hello there.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            finalize_calls.append(kwargs["response"].text)

        def auto_flag_chat_response(self, **kwargs):
            auto_flag_calls.append(kwargs["response"].text)
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "hello", "stream": False},
    )

    assert response.status_code == 200
    assert captured["persist_chat"] is True
    assert captured["session_id"] is None
    assert "stateless_smoke" not in response.json()["data"]
    assert finalize_calls == ["Hello there."]
    assert auto_flag_calls == ["Hello there."]


def test_cockpit_chat_stateless_smoke_stream_skips_persistence_and_auto_flag(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def chat_stream(self, on_chunk=None, **kwargs):
            captured.update(kwargs)
            if on_chunk is not None:
                on_chunk("CSL looks bearish on the current price trend.")
            return SimpleNamespace(
                text="CSL looks bearish on the current price trend.",
                evidence=[
                    {
                        "type": "attached_source",
                        "details": {
                            "title": "CSL Appendix 3C buy-back notice",
                            "source_id": "asx:CSL:appendix-3c",
                            "doc_type": "asx_announcement",
                            "snippet": "CSL lodged an on-market buy-back notice.",
                            "evidence_labels": ["context_only"],
                            "claim_verified": False,
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                    "chat_persistence": "disabled",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            raise AssertionError("stateless smoke must not finalize chat state")

        def auto_flag_chat_response(self, **kwargs):
            raise AssertionError("stateless smoke must not persist auto flags")

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        headers={"X-Tenn-Stateless-Smoke": "1"},
        json={
            "message": "what is the CSL price trend?",
            "session_id": "real-session-should-not-be-read",
            "stream": True,
            "stateless_smoke": True,
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert captured["persist_chat"] is False
    assert str(captured["session_id"]).startswith("stateless-smoke-")
    assert captured["session_id"] != "real-session-should-not-be-read"
    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    done = done_events[-1]["data"]
    assert done["stateless_smoke"] is True
    assert done["stateless_smoke_session_id"] == captured["session_id"]
    assert done["auto_flag"] is None
    metadata = done["routing_metadata"]
    assert metadata["stateless_smoke"] is True
    assert metadata["chat_persistence"] == "disabled"
    assert "market_data_missing" in metadata["evidence_labels"]
    assert done["text"].startswith("DATA_MISSING / evidence gaps:")
    assert "unsupported_or_not_verified: treat unsupported claim families" in done["text"]


def test_memory_read_event_suppression_preserves_normal_writes(tmp_path) -> None:
    memory_read_log = tmp_path / "memory_read_events.jsonl"

    normal_event = emit_memory_read_event(
        mode="cockpit_chat",
        query_type="company_analysis",
        query="tell me about CSL",
        entities={"ticker": "CSL"},
        source_plan=["company_memory"],
        considered_counts={"company_memory": 1},
        selected_counts={"company_memory": 1},
        filtered_counts={"company_memory": 0},
        path=memory_read_log,
    )

    assert normal_event.get("suppressed") is None
    assert len(memory_read_log.read_text().splitlines()) == 1

    with suppress_memory_read_events():
        suppressed_event = emit_memory_read_event(
            mode="cockpit_chat",
            query_type="company_analysis",
            query="tell me about CSL",
            entities={"ticker": "CSL"},
            source_plan=["company_memory"],
            considered_counts={"company_memory": 1},
            selected_counts={"company_memory": 1},
            filtered_counts={"company_memory": 0},
            path=memory_read_log,
        )

    assert suppressed_event["suppressed"] is True
    assert suppressed_event["suppression_reason"] == "stateless_chat_smoke"
    assert len(memory_read_log.read_text().splitlines()) == 1


def test_cockpit_service_chat_stream_stateless_smoke_does_not_persist_state(
    tmp_path,
) -> None:
    service = CockpitService.__new__(CockpitService)
    service.llm_client = SimpleNamespace(model="model:test")
    service.chat_runtime_target_preference = lambda: "local"
    service._resolve_chat_runtime_target = lambda runtime_target, **kwargs: (
        "local",
        "test",
    )
    service._resolve_thread_id = (
        lambda session_id: str(session_id or "").strip()[:128] or "global-main"
    )
    service._resolve_continuity_turn = lambda **kwargs: (None, None, {})
    service._apply_api_default_routing = lambda message: (message, False)
    service._seed_recent_youtube_video_options = lambda *args, **kwargs: None

    persisted_messages: list[tuple[str, str, str]] = []
    turn_diagnostics: list[tuple[str, dict]] = []
    remembered_youtube: list[tuple[object, ...]] = []

    service._persist_chat_message = (
        lambda thread_id, role, content: persisted_messages.append(
            (thread_id, role, content)
        )
    )
    service._remember_turn_diagnostics = (
        lambda thread_id, payload: turn_diagnostics.append((thread_id, payload))
    )
    service._remember_recent_youtube_video_options = (
        lambda *args: remembered_youtube.append(args)
    )

    class FakeController:
        _hybrid_router = None

        def build_chat_response(self, **kwargs):
            assert kwargs["message"] == "what is the CSL price trend?"
            emit_memory_read_event(
                mode="cockpit_chat",
                query_type="company_analysis",
                query=kwargs["message"],
                entities={"ticker": "CSL"},
                source_plan=["company_memory"],
                considered_counts={"company_memory": 1},
                selected_counts={"company_memory": 1},
                filtered_counts={"company_memory": 0},
                path=memory_read_log,
            )
            return SimpleNamespace(
                text="CSL looks bearish on the current price trend.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:test",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    service._build_chat_controller = (
        lambda thread_id, llm_client=None: FakeController()
    )
    memory_read_log = tmp_path / "memory_read_events.jsonl"

    stateless_response = CockpitService.chat_stream(
        service,
        message="what is the CSL price trend?",
        session_id="smoke-csl",
        persist_chat=False,
    )

    assert stateless_response.text == "CSL looks bearish on the current price trend."
    assert stateless_response.routing_metadata["chat_persistence"] == "disabled"
    assert persisted_messages == []
    assert turn_diagnostics == []
    assert remembered_youtube == []
    assert not memory_read_log.exists()

    normal_response = CockpitService.chat_stream(
        service,
        message="what is the CSL price trend?",
        session_id="normal-csl",
        persist_chat=True,
    )

    assert normal_response.text == "CSL looks bearish on the current price trend."
    assert normal_response.routing_metadata.get("chat_persistence") is None
    assert len(memory_read_log.read_text().splitlines()) == 1
    assert [row[:2] for row in persisted_messages] == [
        ("normal-csl", "user"),
        ("normal-csl", "assistant"),
    ]


def test_cockpit_chat_metadata_marks_metric_extraction_missing(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="CSL revenue and EBITDA margin improved in the latest period.",
                evidence=[
                    {
                        "type": "attached_source",
                        "details": {
                            "title": "CSL announcement excerpt",
                            "source_id": "asx:CSL:announcement",
                            "doc_type": "asx_announcement",
                            "snippet": "Announcement context only.",
                            "evidence_labels": ["context_only"],
                            "claim_verified": False,
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            return None

        def auto_flag_chat_response(self, **kwargs):
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "summarize CSL revenue", "stream": False},
    )

    assert response.status_code == 200
    metadata = response.json()["data"]["routing_metadata"]
    text = response.json()["data"]["text"]
    assert metadata["source_coverage_status"] == "missing_required_evidence"
    assert "metric_extraction_missing" in metadata["evidence_labels"]
    assert metadata["missing_evidence_categories"] == ["metric_extraction"]
    assert metadata["unsupported_claim_families"] == ["financial_metric"]
    assert text.startswith("DATA_MISSING / evidence gaps:")
    assert "metric_extraction_missing: canonical metric" in text


def test_cockpit_chat_non_stream_allows_control_prompt_ok_without_sources(
    monkeypatch,
) -> None:
    finalized_metadata: list[dict] = []
    auto_flag_calls: list[str] = []

    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="ok",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:test",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            finalized_metadata.append(dict(kwargs["response"].routing_metadata or {}))

        def auto_flag_chat_response(self, **kwargs):
            auto_flag_calls.append(kwargs["response"].text)
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "Reply exactly: ok", "stream": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["text"] == "ok"
    assert "grounding_guard" not in finalized_metadata[-1]
    assert auto_flag_calls == ["ok"]


def test_cockpit_chat_non_stream_preserves_marketplace_draft_without_sources(
    monkeypatch,
) -> None:
    draft_json = (
        '{"assistant_message":"What budget should I use?",'
        '"draft":{},"missing_fields":["budget"],'
        '"ready_to_create":false,"suggested_action":"ask_followup"}'
    )
    finalize_calls: list[str] = []
    auto_flag_calls: list[str] = []

    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            **kwargs,
        ):
            assert kwargs["ui_mode"] == "marketplace"
            return SimpleNamespace(
                text=draft_json,
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "claude-sonnet-test",
                    "latency_ms": 111,
                    "cost_usd": 0.0,
                    "source": "api",
                    "ui_mode": "marketplace",
                },
                tool_traces=[],
            )

        def finalize_chat_response_delivery(self, **kwargs):
            finalize_calls.append(kwargs["response"].text)

        def auto_flag_chat_response(self, **kwargs):
            auto_flag_calls.append(kwargs["response"].text)
            return None

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "/cloud You are the Tenn Marketplace mission assistant.",
            "mode": "marketplace",
            "stream": False,
            "rag": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["text"] == draft_json
    assert "grounding_guard" not in payload["data"]
    assert finalize_calls == [draft_json]
    assert auto_flag_calls == [draft_json]


def test_cockpit_chat_stream_preserves_marketplace_draft_without_sources(
    monkeypatch,
) -> None:
    draft_json = (
        '{"assistant_message":"What budget should I use?",'
        '"draft":{},"missing_fields":["budget"],'
        '"ready_to_create":false,"suggested_action":"ask_followup"}'
    )

    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            assert kwargs["ui_mode"] == "marketplace"
            return SimpleNamespace(
                text=draft_json,
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "claude-sonnet-test",
                    "latency_ms": 111,
                    "cost_usd": 0.0,
                    "source": "api",
                    "ui_mode": "marketplace",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={
            "message": "/cloud You are the Tenn Marketplace mission assistant.",
            "mode": "marketplace",
            "stream": True,
            "rag": False,
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == draft_json
    assert "can't verify that from current evidence" not in done_events[-1]["data"][
        "text"
    ].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_allows_good_morning_without_sources(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Good morning. How can I help?",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 321,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "good morning", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == "Good morning. How can I help?"


def test_cockpit_chat_stream_blocks_market_update_command_phrase_without_sources(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No market-update reports found.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 111,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "market update today?", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "can't verify that from current evidence" in done_events[-1]["data"]["text"].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_blocks_cloud_research_without_sources(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Hydrogen industry demand is accelerating and ASX leaders are gaining share.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "claude-sonnet-test",
                    "latency_ms": 111,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "/cloud tell me about hydrogen industry", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "can't verify that from current evidence" in done_events[-1]["data"]["text"].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_preserves_explicit_unverified_without_claims(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="I can't verify that from current evidence yet.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 111,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "fgr price", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == "I can't verify that from current evidence yet."
    assert "Sources dropdown" not in done_events[-1]["data"]["text"]
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_preserves_watch_youtube_command_result(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Added YouTube channel Kneppy Invests (UCabc123) to the watch list.",
                evidence=[
                    {
                        "tool": "watch_youtube_channel",
                        "arguments": {"channel_name": "Kneppy Invests"},
                        "result": {
                            "ok": True,
                            "channel_id": "UCabc123",
                            "name": "Kneppy Invests",
                            "already_existed": False,
                        },
                    }
                ],
                action_preview=None,
                mode="command",
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 111,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "watch youtube channel kneppy invests", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == (
        "Added YouTube channel Kneppy Invests (UCabc123) to the watch list."
    )
    assert "Sources dropdown" not in done_events[-1]["data"]["text"]
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_preserves_agent_watch_youtube_ack(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Kneppy Invests is already on the YouTube watch list.",
                evidence=[
                    {
                        "tool": "watch_youtube_channel",
                        "arguments": {"channel_name": "Kneppy Invests"},
                        "result": {
                            "ok": True,
                            "channel_id": "UCjQJPzeCJhA4KrETh3FVVHA",
                            "name": "Kneppy Invests",
                            "enabled": True,
                            "already_existed": True,
                        },
                    }
                ],
                action_preview=None,
                mode="agent",
                routing_metadata={
                    "model": "claude-sonnet-4-20250514",
                    "latency_ms": 1929,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "watch kneppy invests", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == (
        "Kneppy Invests is already on the YouTube watch list."
    )
    assert "Sources dropdown" not in done_events[-1]["data"]["text"]
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_blocks_financial_claim_with_only_watch_youtube(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Kneppy Invests reported that BHP revenue will rise.",
                evidence=[
                    {
                        "tool": "watch_youtube_channel",
                        "arguments": {"channel_name": "Kneppy Invests"},
                        "result": {
                            "ok": True,
                            "channel_id": "UCjQJPzeCJhA4KrETh3FVVHA",
                            "name": "Kneppy Invests",
                            "enabled": True,
                            "already_existed": True,
                        },
                    }
                ],
                action_preview=None,
                mode="agent",
                routing_metadata={
                    "model": "claude-sonnet-4-20250514",
                    "latency_ms": 1929,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "watch kneppy invests", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "can't verify that from current evidence" in done_events[-1]["data"][
        "text"
    ].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_preserves_watch_youtube_tool_error(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Could not watch YouTube channel Kneppy Invests: backend down.",
                evidence=[
                    {
                        "tool": "watch_youtube_channel",
                        "arguments": {"channel_name": "Kneppy Invests"},
                        "result": {
                            "ok": False,
                            "error": "backend down",
                        },
                    }
                ],
                action_preview=None,
                mode="agent",
                routing_metadata={
                    "model": "claude-sonnet-4-20250514",
                    "latency_ms": 1929,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "watch kneppy invests", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == (
        "Could not watch YouTube channel Kneppy Invests: backend down."
    )
    assert "Sources dropdown" not in done_events[-1]["data"]["text"]
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_preserves_youtube_ingest_tool_error(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text=(
                    "Could not ingest selected YouTube video(s): "
                    "members-only video cannot be ingested: "
                    "https://www.youtube.com/watch?v=ULVlVUSSSkI"
                ),
                evidence=[
                    {
                        "tool": "ingest_youtube_videos",
                        "arguments": {
                            "urls": ["https://www.youtube.com/watch?v=ULVlVUSSSkI"],
                            "takeaway_limit": 5,
                        },
                        "result": {
                            "ok": False,
                            "count": 0,
                            "error_count": 1,
                            "results": [],
                            "errors": [
                                {
                                    "url": "https://www.youtube.com/watch?v=ULVlVUSSSkI",
                                    "status_code": 403,
                                    "detail": (
                                        "members-only video cannot be ingested: "
                                        "https://www.youtube.com/watch?v=ULVlVUSSSkI"
                                    ),
                                }
                            ],
                            "partial_ok": False,
                        },
                    }
                ],
                action_preview=None,
                mode="command",
                routing_metadata={
                    "model": "claude-sonnet-4-20250514",
                    "latency_ms": 1929,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "ingest 2", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert done_events[-1]["data"]["text"] == (
        "Could not ingest selected YouTube video(s): "
        "members-only video cannot be ingested: "
        "https://www.youtube.com/watch?v=ULVlVUSSSkI"
    )
    assert "Sources dropdown" not in done_events[-1]["data"]["text"]
    assert "grounding_guard" not in done_events[-1]["data"]["routing_metadata"]
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_blocks_financial_claim_with_only_youtube_ingest(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text=(
                    "Could not ingest selected YouTube video(s), but BHP revenue "
                    "rose 9% according to the video."
                ),
                evidence=[
                    {
                        "tool": "ingest_youtube_videos",
                        "arguments": {
                            "urls": ["https://www.youtube.com/watch?v=ULVlVUSSSkI"],
                            "takeaway_limit": 5,
                        },
                        "result": {
                            "ok": False,
                            "count": 0,
                            "error_count": 1,
                            "results": [],
                            "errors": [
                                {
                                    "url": "https://www.youtube.com/watch?v=ULVlVUSSSkI",
                                    "status_code": 403,
                                    "detail": "members-only video cannot be ingested",
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                mode="agent",
                routing_metadata={
                    "model": "claude-sonnet-4-20250514",
                    "latency_ms": 1929,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "ingest 2", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "can't verify that from current evidence" in done_events[-1]["data"][
        "text"
    ].lower()
    assert not [event for event in data_events if event.get("type") == "sources"]


def test_cockpit_chat_stream_preserves_bare_operational_error_reply(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text=(
                    "I need the specific error details or the failing step before "
                    "I can investigate it."
                ),
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "claude-sonnet-4-20250514",
                    "latency_ms": 12,
                    "cost_usd": 0.0,
                    "source": "api",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "/cloud Error", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    assert "specific error details" in done_events[-1]["data"]["text"]
    assert "Sources dropdown" not in done_events[-1]["data"]["text"]


def test_cockpit_chat_stream_emits_sources_when_evidence_is_renderable(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="BHP news is mixed.",
                evidence=[
                    {
                        "tool": "search_news",
                        "result": {
                            "hits": [
                                {
                                    "title": "BHP update",
                                    "url": "https://example.com/bhp-update",
                                    "published_at": "2026-04-16T07:00:00Z",
                                    "snippet": "BHP released an update.",
                                }
                            ]
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "bhp news", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    source_events = [event for event in data_events if event.get("type") == "sources"]
    assert source_events
    items = source_events[-1]["data"]["items"]
    assert items[0]["url"] == "https://example.com/bhp-update"


def test_cockpit_chat_stream_financial_truth_sources_satisfy_source_contract(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="BHP reported revenue in the latest annual period.",
                evidence=[
                    {
                        "type": "orchestrator",
                        "details": {
                            "financial_truth": {
                                "financials": [
                                    {
                                        "ticker": "BHP",
                                        "period_type": "annual",
                                        "period_end": "2025-06-30",
                                        "revenue": 55100,
                                        "source_document_id": "doc-bhp-fy25",
                                    }
                                ]
                            }
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "what did BHP report?", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events[-1]["data"]["text"] == "BHP reported revenue in the latest annual period."
    assert source_events
    assert source_events[-1]["data"]["items"][0]["document_id"] == "doc-bhp-fy25"
    assert source_events[-1]["data"]["items"][0]["evidence_label"] == "financial_truth"
    assert "financial_truth" in done_events[-1]["data"]["routing_metadata"]["evidence_labels"]


def test_cockpit_chat_stream_youtube_recent_videos_emit_sources(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text=(
                    "Recent videos from Kneppy Invests (UCabc123):\n"
                    "1. BHP quarterly results breakdown | 2026-04-28T00:00:00Z\n"
                    "   https://www.youtube.com/watch?v=vid123"
                ),
                evidence=[
                    {
                        "tool": "check_youtube_channel_recent_videos",
                        "arguments": {"channel_name": "Kneppy Invests"},
                        "result": {
                            "ok": True,
                            "name": "Kneppy Invests",
                            "channel_id": "UCabc123",
                            "videos": [
                                {
                                    "video_id": "vid123",
                                    "title": "BHP quarterly results breakdown",
                                    "published_at": "2026-04-28T00:00:00Z",
                                    "webpage_url": "https://www.youtube.com/watch?v=vid123",
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                mode="command",
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "check youtube Kneppy Invests for recent videos", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events[-1]["data"]["text"].startswith("Recent videos from Kneppy Invests")
    assert source_events
    assert source_events[-1]["data"]["items"][0]["source_id"] == "youtube:vid123"


def test_cockpit_chat_stream_search_news_zero_hit_allows_pure_no_hit_response(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No news results were returned for BHP.",
                evidence=[
                    {
                        "tool": "search_news",
                        "result": {
                            "query": "BHP news",
                            "ticker": "BHP",
                            "hit_count": 0,
                            "hits": [],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "BHP news", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events[-1]["data"]["text"] == "No news results were returned for BHP."
    item = source_events[-1]["data"]["items"][0]
    assert item["source_id"] == "search_news:no_hits:bhp news"
    assert item["evidence_label"] == "no_hit"
    assert item["claim_verified"] is False
    routing = done_events[-1]["data"]["routing_metadata"]
    assert routing["source_coverage_status"] == "no_hit"
    assert routing["claim_verified_source_count"] == 0


def test_cockpit_chat_stream_search_news_zero_hit_does_not_support_claims(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No news results were returned for BHP. BHP reported stronger revenue today.",
                evidence=[
                    {
                        "tool": "search_news",
                        "result": {
                            "query": "BHP news",
                            "ticker": "BHP",
                            "hit_count": 0,
                            "hits": [],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "BHP news", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]

    assert "can't verify that from current evidence" in done_events[-1]["data"]["text"].lower()


def test_cockpit_chat_stream_surfaces_degraded_runtime_metadata(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Based on available evidence: search_news returned one article.",
                evidence=[
                    {
                        "tool": "search_news",
                        "result": {
                            "hits": [
                                {
                                    "title": "A2M recall article",
                                    "url": "https://example.com/a2m-recall",
                                }
                            ]
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                    "system_status": "degraded",
                    "runtime_degradation": "synthesis_timeout",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "tell me about A2M", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    routing = done_events[-1]["data"]["routing_metadata"]
    assert routing["source_coverage_status"] == "degraded_runtime"
    assert "degraded_runtime" in routing["evidence_labels"]
    assert routing["claim_verified_source_count"] == 0


def test_cockpit_chat_stream_tv_screener_evidence_satisfies_source_contract(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Top movers include BHP and RIO today.",
                evidence=[
                    {
                        "tool": "tv_screener",
                        "result": {
                            "market": "australia",
                            "results": [
                                {
                                    "symbol": "ASX:BHP",
                                    "change_percent": 2.4,
                                    "close": 45.2,
                                }
                            ],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 121,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "what are some market movers today", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events
    assert done_events[-1]["data"]["text"] == "Top movers include BHP and RIO today."
    assert source_events
    assert source_events[-1]["data"]["items"][0]["source_id"] == "tv_screener:AUSTRALIA:ASX:BHP"


def test_cockpit_chat_stream_tv_screener_empty_result_still_emits_source_item(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No high-conviction movers were returned.",
                evidence=[
                    {
                        "tool": "tv_screener",
                        "result": {
                            "market": "australia",
                            "count": 0,
                            "results": [],
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 121,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "what are some market movers today", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events
    assert done_events[-1]["data"]["text"] == "No high-conviction movers were returned."
    assert source_events
    item = source_events[-1]["data"]["items"][0]
    assert item["source_id"] == "tv_screener:AUSTRALIA"
    assert item["evidence_label"] == "no_hit"
    assert item["claim_verified"] is False
    routing = done_events[-1]["data"]["routing_metadata"]
    assert routing["source_coverage_status"] == "no_hit"
    assert routing["claim_verified_source_count"] == 0


def test_cockpit_chat_stream_financial_truth_missing_rows_surfaces_missing_evidence(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No canonical financial rows were returned for BHP.",
                evidence=[
                    {
                        "tool": "get_financials",
                        "result": {
                            "ok": True,
                            "ticker": "BHP",
                            "financials": [],
                            "data_insufficient": True,
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 121,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "What is BHP revenue?", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events[-1]["data"]["text"].startswith("DATA_MISSING / evidence gaps:")
    assert "metric_extraction_missing: canonical metric" in done_events[-1]["data"]["text"]
    assert "No canonical financial rows were returned for BHP." in done_events[-1]["data"]["text"]
    item = source_events[-1]["data"]["items"][0]
    assert item["source_id"] == "financial_truth:no_hit:bhp"
    assert item["evidence_label"] == "missing_required_evidence"
    assert item["claim_verified"] is False
    routing = done_events[-1]["data"]["routing_metadata"]
    assert routing["source_coverage_status"] == "missing_required_evidence"
    assert routing["claim_verified_source_count"] == 0
    assert "metric_extraction_missing" in routing["evidence_labels"]


def test_cockpit_chat_stream_web_tool_failure_surfaces_degraded_runtime(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Web search failed: search timed out.",
                evidence=[
                    {
                        "tool": "search_web",
                        "result": {
                            "ok": False,
                            "query": "BHP latest announcement",
                            "error": "search timed out",
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 121,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "search web for BHP latest announcement", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    source_events = [event for event in data_events if event.get("type") == "sources"]

    assert done_events[-1]["data"]["text"] == "Web search failed: search timed out."
    item = source_events[-1]["data"]["items"][0]
    assert item["evidence_label"] == "degraded_runtime"
    assert item["claim_verified"] is False
    routing = done_events[-1]["data"]["routing_metadata"]
    assert routing["source_coverage_status"] == "degraded_runtime"
    assert "degraded_runtime" in routing["evidence_labels"]
    assert routing["claim_verified_source_count"] == 0


def test_cockpit_chat_stream_done_event_preserves_model_metadata(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="No evidence available.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:qwen3.5-35b-a3b",
                    "latency_ms": 0,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "tell me about BHP", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]

    assert done_events[-1]["data"]["model"] == "model:qwen3.5-35b-a3b"


def test_cockpit_chat_stream_done_event_preserves_provider_error(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Claude API billing failed.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "claude-sonnet-test",
                    "latency_ms": 222,
                    "cost_usd": 0.0,
                    "source": "api",
                    "provider_error": {
                        "provider": "anthropic",
                        "code": "billing_insufficient_credit",
                        "severity": "action_required",
                        "message": "Top up Anthropic credits in Plans & Billing.",
                    },
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "/cloud hello", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events
    provider_error = done_events[-1]["data"]["provider_error"]
    assert provider_error["provider"] == "anthropic"
    assert provider_error["code"] == "billing_insufficient_credit"
    assert provider_error["severity"] == "action_required"


def test_cockpit_chat_stream_done_event_includes_auto_flag_handoff(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="I cannot verify that from current evidence.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:test",
                    "latency_ms": 90_000,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

        def auto_flag_chat_response(self, **kwargs):
            assert kwargs["session_id"] == "session-auto"
            assert kwargs["ticker"] == "BHP"
            return {
                "report_id": "auto_20260430_abc123",
                "feedback_type": "poor",
                "capture_kind": "auto_diagnostic",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-auto/auto_20260430_abc123",
                "read_api_path": "/api/cockpit/feedback/flags/auto_20260430_abc123",
                "codex_prompt": "Investigate this automatically flagged cockpit diagnostic.",
                "codex_prompt_path": "/tmp/reports/cockpit/flagged_sessions/session-auto/auto_20260430_abc123/codex_prompt.md",
                "investigation_path": "/tmp/reports/cockpit/flagged_sessions/session-auto/auto_20260430_abc123/investigation.json",
                "investigation_status": "queued",
                "codex_cli_command": "python scripts/cockpit_flag_investigator.py --report-id auto_20260430_abc123 --once --apply",
            }

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={
            "message": "tell me about BHP",
            "ticker": "BHP",
            "session_id": "session-auto",
            "stream": True,
        },
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [event for event in data_events if event.get("type") == "done"]
    auto_flag = done_events[-1]["data"]["auto_flag"]
    assert auto_flag["report_id"] == "auto_20260430_abc123"
    assert auto_flag["capture_kind"] == "auto_diagnostic"
    assert auto_flag["investigation_status"] == "queued"
    assert auto_flag["codex_prompt_path"].endswith("/codex_prompt.md")
    assert auto_flag["read_api_path"].endswith("/auto_20260430_abc123")
    assert "codex_prompt" not in auto_flag
    assert "codex_cli_command" not in auto_flag


def test_cockpit_chat_non_stream_uses_to_thread(monkeypatch) -> None:
    class FakeService:
        def chat_stream(self, **kwargs):
            return SimpleNamespace(
                text="Hello there.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:gpt-oss-20b",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                },
                tool_traces=[],
            )

    called: dict[str, object] = {"used": False, "kwargs": None}

    async def _fake_to_thread(func, /, *args, **kwargs):
        called["used"] = True
        called["kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "hello", "stream": False},
    )

    assert response.status_code == 200
    assert called["used"] is True
    assert response.json()["data"]["text"] == "Hello there."


def test_cockpit_chat_forwards_attached_sources(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def chat_stream(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text="Hello there.",
                evidence=[],
                action_preview=None,
                routing_metadata={
                    "model": "model:gpt-oss-20b",
                    "latency_ms": 42,
                    "cost_usd": 0.0,
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "hello",
            "stream": False,
            "attached_sources": [{"source_id": "src-1", "source_kind": "concat"}],
        },
    )

    assert response.status_code == 200
    assert captured["attached_sources"] == [
        {"source_id": "src-1", "source_kind": "concat"}
    ]


def test_cockpit_chat_stream_emits_filestats_chart_event(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Company Data Dump: BHP\nSummary\n- Docs: 1",
                evidence=[
                    {
                        "type": "company_dump",
                        "details": {
                            "ticker": "BHP",
                            "backend": {
                                "ticker": "BHP",
                                "summary": {"doc_count": 1, "price_points_1y": 1},
                                "docs": [
                                    {
                                        "document_id": "doc-1",
                                        "published_at": "2026-04-09",
                                        "doc_class": "quarterly",
                                        "title": "Quarterly",
                                    }
                                ],
                                "financials": [],
                                "risk_notes": [],
                                "price_history_1y": [
                                    {
                                        "timestamp": "2026-04-09T00:00:00Z",
                                        "close": 55.2,
                                    }
                                ],
                                "extraction_failures": [],
                                "low_confidence_financials": [],
                                "company_memory": {"entries": []},
                                "market_memory": {"items": []},
                            },
                            "cockpit_local_memory": {},
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "bhp filestats", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    chart_events = [event for event in data_events if event.get("type") == "chart"]
    assert chart_events, body
    assert chart_events[-1]["data"]["title"].startswith("BHP filestats")
    assert "Filestats Dashboard" in chart_events[-1]["data"]["html"]

    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"].get("chart") is not None


def test_cockpit_chat_stream_emits_holdings_chart_event(monkeypatch) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Portfolio overview (3 holdings)",
                evidence=[
                    {
                        "type": "holdings",
                        "details": [
                            {
                                "holding_id": "h1",
                                "ticker": "BHP",
                                "market_value": 12000.0,
                                "price_currency": "AUD",
                            },
                            {
                                "holding_id": "h2",
                                "ticker": "CBA",
                                "market_value": 8000.0,
                                "price_currency": "AUD",
                            },
                            {
                                "holding_id": "h3",
                                "ticker": "CSL",
                                "market_value": 5000.0,
                                "price_currency": "AUD",
                            },
                        ],
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "what are my holdings", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    chart_events = [event for event in data_events if event.get("type") == "chart"]
    assert chart_events, body
    assert chart_events[-1]["data"]["title"].startswith("Holdings allocation")
    assert "Portfolio Allocation" in chart_events[-1]["data"]["html"]

    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"].get("chart") is not None


def test_cockpit_chat_holdings_sources_do_not_become_source_backed(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Local personal holdings data:\nBHP qty 10.",
                evidence=[
                    {
                        "type": "holdings",
                        "details": [
                            {
                                "holding_id": "h1",
                                "ticker": "BHP",
                                "quantity": 10,
                            }
                        ],
                    }
                ],
                action_preview=None,
                routing_metadata={
                    "model": "gpt-oss-20b",
                    "latency_ms": 123,
                    "cost_usd": 0.0,
                    "source": "local_holdings",
                    "canonical_intent": "holdings",
                    "data_scope": "local_personal_holdings",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/cockpit/chat",
        json={"message": "holdings?", "stream": True},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    data_events = [
        json.loads(line.removeprefix("data: ").strip())
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    assert not [event for event in data_events if event.get("type") == "sources"]
    done_events = [event for event in data_events if event.get("type") == "done"]
    assert done_events, body
    assert done_events[-1]["data"]["sources"] == []
    routing = done_events[-1]["data"]["routing_metadata"]
    assert routing["data_scope"] == "local_personal_holdings"
    assert routing["source_coverage_status"] == "local_personal_data"
    assert "local_personal_data" in routing["evidence_labels"]
    assert "financial_truth" not in routing["evidence_labels"]
    assert "visible_source_count" not in routing


def test_cockpit_chat_holdings_filters_irrelevant_screener_sources(
    monkeypatch,
) -> None:
    class FakeService:
        def chat_stream(
            self,
            message: str,
            ticker: str | None = None,
            session_id: str | None = None,
            on_chunk=None,
            on_status=None,
            on_thinking=None,
            **kwargs,
        ):
            return SimpleNamespace(
                text="Local personal holdings data:\nNo holdings are stored.",
                evidence=[
                    {"type": "holdings", "details": []},
                    {
                        "tool": "tv_screener",
                        "result": {
                            "market": "AUSTRALIA",
                            "results": [],
                            "count": 0,
                        },
                    },
                    {
                        "tool": "screen_tickers",
                        "result": {"results": [], "count": 0},
                    },
                ],
                action_preview=None,
                routing_metadata={
                    "source": "local_holdings",
                    "canonical_intent": "holdings",
                },
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={"message": "what stocks i hold currently", "stream": False},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["sources"] == []
    assert "TradingView" not in json.dumps(payload)
    assert "tv_screener" not in json.dumps(payload)
    assert "screen_tickers" not in json.dumps(payload)


def test_cockpit_feedback_flag_route_returns_saved_artifact_info(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["session_id"] == "session-123"
            assert kwargs["ticker"] == "BHP"
            assert kwargs["feedback_type"] == "poor"
            assert kwargs["capture_kind"] == "chat_feedback"
            assert kwargs["flagged_message"]["content"] == "Bad answer"
            return {
                "ok": True,
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "codex_prompt": "Investigate this flagged cockpit response and fix the underlying bug.\n\nFlag ID: flag_20260409_abc123\nRead API: /api/cockpit/feedback/flags/flag_20260409_abc123",
                "analysis_summary": "The answer appears to have ignored the retrieved evidence.",
            }

        def list_flagged_reports(self, limit, status):
            assert limit == 5
            assert status == "open"
            return [
                {
                    "report_id": "flag_20260409_abc123",
                    "feedback_type": "poor",
                    "session_id": "session-123",
                    "ticker": "BHP",
                    "saved_at": "2026-04-09T07:31:00Z",
                    "note": "Missed cited evidence",
                    "flagged_response_excerpt": "Bad answer",
                    "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                }
            ]

        def get_flagged_report(self, report_id):
            assert report_id == "flag_20260409_abc123"
            return {
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "bundle": {"report_id": "flag_20260409_abc123"},
                "summary_markdown": "# Flagged Cockpit Chat",
                "analysis": {"summary": "Ignored evidence"},
            }

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flag",
        json={
            "session_id": "session-123",
            "ticker": "BHP",
            "flagged_message": {
                "id": "assistant-1",
                "role": "assistant",
                "content": "Bad answer",
            },
            "transcript": [
                {"id": "user-1", "role": "user", "content": "Tell me about BHP"},
                {"id": "assistant-1", "role": "assistant", "content": "Bad answer"},
            ],
            "frontend_context": {"source": "cockpit-ui-chat"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["report_id"] == "flag_20260409_abc123"
    assert payload["feedback_type"] == "poor"
    assert payload["capture_kind"] == "chat_feedback"
    assert (
        payload["read_api_path"] == "/api/cockpit/feedback/flags/flag_20260409_abc123"
    )
    assert "Flag ID: flag_20260409_abc123" in payload["codex_prompt"]
    assert "/api/cockpit/feedback/flags/flag_20260409_abc123" in payload["codex_prompt"]
    assert (
        payload["analysis_summary"]
        == "The answer appears to have ignored the retrieved evidence."
    )
    assert payload["resolution_status"] == "open"
    assert payload["resolution_commit_sha"] is None


def _feedback_flag_request() -> dict:
    return {
        "session_id": "session-123",
        "ticker": "BHP",
        "flagged_message": {
            "id": "assistant-1",
            "role": "assistant",
            "content": "Bad answer",
        },
        "transcript": [
            {"id": "user-1", "role": "user", "content": "Tell me about BHP"},
            {"id": "assistant-1", "role": "assistant", "content": "Bad answer"},
        ],
        "frontend_context": {"source": "cockpit-ui-chat"},
    }


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
@pytest.mark.parametrize(
    ("path", "json_body"),
    [
        ("/api/cockpit/feedback/flag", _feedback_flag_request()),
        (
            "/api/cockpit/feedback/flags/flag_20260409_abc123/resolve",
            {
                "commit_sha": "abc1234",
                "resolved_by": "codex",
                "note": "fixed prompt guard",
            },
        ),
    ],
)
def test_cockpit_feedback_write_routes_require_api_key_before_service(
    monkeypatch,
    headers,
    path,
    json_body,
) -> None:
    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)
    get_instance = Mock(side_effect=AssertionError("service should not initialize"))
    monkeypatch.setattr(
        CockpitService,
        "get_instance",
        classmethod(lambda cls: get_instance()),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(path, headers=headers, json=json_body)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    get_instance.assert_not_called()


def test_cockpit_feedback_flag_route_accepts_matching_api_key(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["session_id"] == "session-123"
            return {
                "ok": True,
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "codex_prompt": "Investigate this flagged cockpit response.",
                "analysis_summary": None,
            }

    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flag",
        headers={"X-API-Key": "local-secret"},
        json=_feedback_flag_request(),
    )

    assert response.status_code == 200
    assert response.json()["report_id"] == "flag_20260409_abc123"


def test_cockpit_feedback_flag_list_route_returns_recent_flags(monkeypatch) -> None:
    class FakeService:
        def list_flagged_reports(self, limit, status):
            assert limit == 5
            assert status == "open"
            return [
                {
                    "report_id": "flag_20260409_abc123",
                    "feedback_type": "poor",
                    "capture_kind": "chat_feedback",
                    "session_id": "session-123",
                    "ticker": "BHP",
                    "saved_at": "2026-04-09T07:31:00Z",
                    "note": "Missed cited evidence",
                    "flagged_response_excerpt": "Bad answer",
                    "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                }
            ]

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/feedback/flags?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["report_id"] == "flag_20260409_abc123"
    assert payload["items"][0]["feedback_type"] == "poor"
    assert payload["items"][0]["capture_kind"] == "chat_feedback"
    assert payload["items"][0]["resolution_status"] == "open"


def test_cockpit_feedback_flag_list_route_accepts_resolved_status_filter(
    monkeypatch,
) -> None:
    class FakeService:
        def list_flagged_reports(self, limit, status):
            assert limit == 5
            assert status == "resolved"
            return []

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/feedback/flags?limit=5&status=resolved")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_cockpit_feedback_flag_read_route_returns_flag_payload(monkeypatch) -> None:
    class FakeService:
        def get_flagged_report(self, report_id):
            assert report_id == "flag_20260409_abc123"
            return {
                "report_id": "flag_20260409_abc123",
                "feedback_type": "poor",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
                "bundle": {"report_id": "flag_20260409_abc123", "ticker": "BHP"},
                "summary_markdown": "# Flagged Cockpit Chat",
                "analysis": {"summary": "Ignored evidence"},
            }

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/feedback/flags/flag_20260409_abc123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "flag_20260409_abc123"
    assert payload["feedback_type"] == "poor"
    assert payload["capture_kind"] == "chat_feedback"
    assert payload["bundle"]["ticker"] == "BHP"
    assert payload["resolution_status"] == "open"


def test_cockpit_feedback_flag_resolve_route_persists_commit_sha(monkeypatch) -> None:
    class FakeService:
        def resolve_flagged_report(self, report_id, *, commit_sha, resolved_by, note):
            assert report_id == "flag_20260409_abc123"
            assert commit_sha == "abc1234"
            assert resolved_by == "codex"
            assert note == "fixed prompt guard"
            return {
                "ok": True,
                "report_id": "flag_20260409_abc123",
                "resolution_status": "resolved",
                "resolved_at": "2026-04-22T10:00:00+00:00",
                "resolution_commit_sha": "abc1234",
                "resolved_by": "codex",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "read_api_path": "/api/cockpit/feedback/flags/flag_20260409_abc123",
            }

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flags/flag_20260409_abc123/resolve",
        json={
            "commit_sha": "abc1234",
            "resolved_by": "codex",
            "note": "fixed prompt guard",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "flag_20260409_abc123"
    assert payload["resolution_status"] == "resolved"
    assert payload["resolution_commit_sha"] == "abc1234"
    assert payload["resolved_by"] == "codex"


def test_cockpit_feedback_flag_resolve_route_accepts_matching_api_key(monkeypatch) -> None:
    class FakeService:
        def resolve_flagged_report(self, report_id, *, commit_sha, resolved_by, note):
            return {
                "ok": True,
                "report_id": report_id,
                "resolution_status": "resolved",
                "resolved_at": "2026-04-22T10:00:00+00:00",
                "resolution_commit_sha": commit_sha,
                "resolved_by": resolved_by,
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/flag_20260409_abc123/summary.md",
                "read_api_path": f"/api/cockpit/feedback/flags/{report_id}",
            }

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(cockpit_api.settings, "local_api_key", "local-secret", raising=False)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flags/flag_20260409_abc123/resolve",
        headers={"X-API-Key": "local-secret"},
        json={
            "commit_sha": "abc1234",
            "resolved_by": "codex",
            "note": "fixed prompt guard",
        },
    )

    assert response.status_code == 200
    assert response.json()["resolution_commit_sha"] == "abc1234"


def test_cockpit_feedback_flag_route_supports_good_feedback(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["feedback_type"] == "good"
            assert kwargs["capture_kind"] == "chat_feedback"
            return {
                "ok": True,
                "report_id": "good_20260410_abc123",
                "feedback_type": "good",
                "capture_kind": "chat_feedback",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/good_20260410_abc123/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/good_20260410_abc123",
                "codex_prompt": "Review this positively rated cockpit response and capture what worked well.",
                "analysis_summary": None,
            }

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flag",
        json={
            "session_id": "session-123",
            "ticker": "BHP",
            "feedback_type": "good",
            "flagged_message": {
                "id": "assistant-1",
                "role": "assistant",
                "content": "Strong answer",
            },
            "transcript": [
                {"id": "user-1", "role": "user", "content": "Tell me about BHP"},
                {"id": "assistant-1", "role": "assistant", "content": "Strong answer"},
            ],
            "frontend_context": {"source": "cockpit-ui-chat"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "good_20260410_abc123"
    assert payload["feedback_type"] == "good"
    assert payload["capture_kind"] == "chat_feedback"


def test_cockpit_feedback_flag_route_supports_ui_issue_capture(monkeypatch) -> None:
    class FakeService:
        def flag_chat_feedback(self, **kwargs):
            assert kwargs["feedback_type"] == "poor"
            assert kwargs["capture_kind"] == "ui_issue"
            assert kwargs["flagged_message"]["content"] == "Toolbar button overlaps status bar"
            assert kwargs["screenshot"]["filename"] == "ui-screenshot.png"
            return {
                "ok": True,
                "report_id": "ui_issue_20260415_deadbeef",
                "feedback_type": "poor",
                "capture_kind": "ui_issue",
                "report_dir": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef",
                "bundle_path": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef/bundle.json",
                "summary_path": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef/summary.md",
                "analysis_path": "/tmp/reports/cockpit/flagged_sessions/session-123/ui_issue_20260415_deadbeef/analysis.json",
                "read_api_path": "/api/cockpit/feedback/flags/ui_issue_20260415_deadbeef",
                "codex_prompt": "Investigate this cockpit UI issue and implement the minimal safe fix.",
                "analysis_summary": None,
            }

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/feedback/flag",
        json={
            "session_id": "session-123",
            "ticker": "BHP",
            "capture_kind": "ui_issue",
            "note": "Happens after resizing the window",
            "flagged_message": {
                "id": "ui-issue-1",
                "role": "system",
                "content": "Toolbar button overlaps status bar",
            },
            "frontend_context": {"source": "cockpit-ui-issue-capture", "pathname": "/verification"},
            "screenshot": {
                "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9p0NvwAAAABJRU5ErkJggg==",
                "mime_type": "image/png",
                "filename": "ui-screenshot.png",
                "width": 1,
                "height": 1,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "ui_issue_20260415_deadbeef"
    assert payload["capture_kind"] == "ui_issue"


def test_flag_chat_feedback_persists_before_background_analysis(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )

    def _resolve_thread_id(session_id):
        return session_id or "global-main"

    service._resolve_thread_id = _resolve_thread_id
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {
        "request": {"message": "bhp 7 day price summary"},
        "routing_metadata": {"model": "model:test"},
        "response_mode": "deep_analysis",
        "prompt": "system prompt excerpt",
        "evidence": [
            {
                "tool": "query_ticker_data",
                "arguments": {"ticker": "BHP"},
                "result": {"ok": True},
            }
        ],
        "tool_traces": [
            {
                "iteration": 2,
                "ok": True,
                "duration_ms": 42.5,
            }
        ],
    }

    scheduled: dict[str, object] = {}

    def _schedule_flagged_report_analysis(**kwargs):
        scheduled.update(kwargs)

    service._schedule_flagged_report_analysis = _schedule_flagged_report_analysis

    result = service.flag_chat_feedback(
        session_id="session-1",
        ticker="BHP",
        feedback_type="poor",
        note="Unsupported claim",
        flagged_message={
            "id": "assistant-1",
            "role": "assistant",
            "content": "Bad answer",
        },
        transcript=[
            {"id": "user-1", "role": "user", "content": "bhp 7 day price summary"}
        ],
        frontend_context={"source": "cockpit-ui-chat"},
    )

    assert result["analysis_summary"] is None
    assert result["analysis_path"].endswith("analysis.json")
    bundle_path = Path(result["bundle_path"])
    summary_path = Path(result["summary_path"])
    analysis_path = Path(result["analysis_path"])
    prompt_path = Path(result["codex_prompt_path"])
    investigation_path = Path(result["investigation_path"])
    assert bundle_path.exists()
    assert summary_path.exists()
    assert not analysis_path.exists()
    assert prompt_path.exists()
    assert investigation_path.exists()
    owner_stat = tmp_path.stat()
    for artifact_path in (bundle_path, summary_path, prompt_path, investigation_path):
        artifact_stat = artifact_path.stat()
        assert artifact_stat.st_uid == owner_stat.st_uid
        assert artifact_stat.st_gid == owner_stat.st_gid
        assert artifact_stat.st_mode & 0o660 == 0o660
    assert bundle_path.parent.stat().st_mode & 0o770 == 0o770
    assert prompt_path.read_text(encoding="utf-8").strip() == result["codex_prompt"]
    investigation = json.loads(investigation_path.read_text(encoding="utf-8"))
    assert result["investigation_status"] == "queued"
    assert investigation["status"] == "queued"
    assert investigation["mode"] == "operator_gated_codex_cli"
    assert investigation["codex_prompt_path"] == str(prompt_path)
    assert result["codex_cli_command"] == (
        f"python scripts/cockpit_flag_investigator.py --report-id {result['report_id']} --once --apply"
    )
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["feedback_type"] == "poor"
    assert bundle["note"] == "Unsupported claim"
    assert bundle["backend_turn"]["response_mode"] == "deep_analysis"
    assert bundle["backend_turn"]["response_prompt"] == "system prompt excerpt"
    assert bundle["backend_turn"]["tool_calls"][0]["tool"] == "query_ticker_data"
    assert bundle["backend_turn"]["tool_calls"][0]["iteration"] == 2
    assert bundle["backend_turn"]["tool_calls"][0]["duration_ms"] == 42.5
    assert "Flag directory: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert "Bundle: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert "Summary: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert (
        f"/api/cockpit/feedback/flags/{result['report_id']}/resolve"
        in result["codex_prompt"]
    )
    assert scheduled["report_id"] == result["report_id"]
    assert scheduled["analysis_path"] == analysis_path


def test_auto_flag_chat_response_persists_auto_diagnostic(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )
    service._feedback_lock = threading.Lock()
    service._recent_auto_flag_fingerprints = set()
    service._resolve_thread_id = lambda session_id: session_id or "global-main"
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {
        "request": {"message": "tell me about PLS", "ticker": "PLS"},
        "routing_metadata": {"model": "model:test", "latency_ms": 90_000},
        "response_mode": "deep_analysis",
        "evidence": [
            {
                "tool": "query_ticker_data",
                "arguments": {"ticker": "PLS"},
                "result": {"ok": True, "_truncated": True},
            }
        ],
        "tool_traces": [
            {
                "tool": "get_financials",
                "ok": False,
                "error": "backend API client not configured",
                "duration_ms": 25_000,
            }
        ],
        "response_text": "I can't verify that from current evidence.",
    }
    scheduled: dict[str, object] = {}
    service._schedule_flagged_report_analysis = lambda **kwargs: scheduled.update(kwargs)

    result = service.auto_flag_chat_response(
        session_id="session-auto",
        ticker="PLS",
        response=SimpleNamespace(
            text="I can't verify that from current evidence.",
            evidence=[],
            tool_traces=[],
            routing_metadata={
                "model": "model:test",
                "latency_ms": 90_000,
                "grounding_guard": "missing_visible_sources",
            },
        ),
    )

    assert result is not None
    assert result["capture_kind"] == "auto_diagnostic"
    assert result["report_id"].startswith("auto_")
    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert bundle["capture_kind"] == "auto_diagnostic"
    assert bundle["frontend_snapshot"]["context"]["source"] == "cockpit-auto-flagger"
    assert bundle["auto_findings"]
    assert {item["category"] for item in bundle["auto_findings"]} >= {
        "missing_sources",
        "information_access",
        "inefficiency",
    }
    summary = Path(result["summary_path"]).read_text(encoding="utf-8")
    investigation = json.loads(Path(result["investigation_path"]).read_text(encoding="utf-8"))
    assert result["investigation_status"] == "queued"
    assert investigation["capture_kind"] == "auto_diagnostic"
    assert result["codex_cli_command"].endswith(
        f"--report-id {result['report_id']} --once --apply"
    )
    assert "# Auto Cockpit Diagnostic" in summary
    assert "Auto Findings" in summary
    assert "Diagnostic directory: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert scheduled["report_id"] == result["report_id"]

    duplicate = service.auto_flag_chat_response(
        session_id="session-auto",
        ticker="PLS",
        response=SimpleNamespace(
            text="I can't verify that from current evidence.",
            evidence=[],
            tool_traces=[],
            routing_metadata={
                "model": "model:test",
                "latency_ms": 90_000,
                "grounding_guard": "missing_visible_sources",
            },
        ),
    )
    assert duplicate is None


def test_finalize_chat_response_delivery_rewrites_guarded_response_state(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.state_store = StateStore(str(tmp_path / "state.db"))
    service._feedback_lock = threading.Lock()
    service._recent_turn_diagnostics = {
        "session-guard": [
            {
                "request": {"message": "tell me about BHP"},
                "response_text": "BHP revenue grew sharply without sources.",
                "routing_metadata": {"model": "model:test"},
                "evidence": [],
                "tool_traces": [],
            }
        ]
    }
    service._resolve_thread_id = lambda session_id: session_id or "global-main"

    service.state_store.add_chat_message(
        "session-guard",
        "user",
        "tell me about BHP",
        "2026-04-30T00:00:00+00:00",
    )
    service.state_store.add_chat_message(
        "session-guard",
        "assistant",
        "BHP revenue grew sharply without sources.",
        "2026-04-30T00:00:01+00:00",
    )

    delivered_text = "I can't verify that from current evidence."
    service.finalize_chat_response_delivery(
        session_id="session-guard",
        response=SimpleNamespace(
            text=delivered_text,
            evidence=[],
            tool_traces=[],
            routing_metadata={
                "model": "model:test",
                "grounding_guard": "missing_visible_sources",
            },
        ),
    )

    messages = service.state_store.get_chat_messages("session-guard")
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == delivered_text
    latest = service._recent_turn_diagnostics["session-guard"][-1]
    assert latest["response_text"] == delivered_text
    assert latest["routing_metadata"]["grounding_guard"] == "missing_visible_sources"


def test_cockpit_workspace_root_env_overrides_flagged_reports_root(
    tmp_path, monkeypatch
) -> None:
    """COCKPIT_WORKSPACE_ROOT env var must route flagged reports to the workspace volume."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("COCKPIT_WORKSPACE_ROOT", str(workspace))

    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path / "app"  # simulates /app inside Docker
    (service.repo_root).mkdir()
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )
    service._resolve_thread_id = lambda sid: sid or "global-main"
    service._resolve_turn_diagnostics = lambda tid, fm: {}
    service._schedule_flagged_report_analysis = lambda **kw: None

    result = service.flag_chat_feedback(
        session_id="env-test",
        ticker="TST",
        feedback_type="poor",
        flagged_message={"id": "a1", "role": "assistant", "content": "bad"},
    )

    bundle_path = Path(result["bundle_path"])
    assert bundle_path.exists()
    # Must be under workspace, not under repo_root (/app)
    assert str(workspace) in str(bundle_path)
    assert str(service.repo_root) not in str(bundle_path)
    flagged_root = workspace / "reports" / "cockpit" / "flagged_sessions"
    assert flagged_root.exists()


def test_good_chat_feedback_persists_without_background_analysis(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )

    def _resolve_thread_id(session_id):
        return session_id or "global-main"

    service._resolve_thread_id = _resolve_thread_id
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {
        "request": {"message": "tell me about bhp"},
        "routing_metadata": {"model": "model:test"},
        "response_mode": "fast",
        "prompt": "good prompt excerpt",
        "evidence": [],
    }

    scheduled: dict[str, object] = {}

    def _schedule_flagged_report_analysis(**kwargs):
        scheduled.update(kwargs)

    service._schedule_flagged_report_analysis = _schedule_flagged_report_analysis

    result = service.flag_chat_feedback(
        session_id="session-1",
        ticker="BHP",
        feedback_type="good",
        note="Well grounded and concise",
        flagged_message={
            "id": "assistant-1",
            "role": "assistant",
            "content": "Strong answer",
        },
        transcript=[{"id": "user-1", "role": "user", "content": "tell me about bhp"}],
        frontend_context={"source": "cockpit-ui-chat"},
    )

    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert result["feedback_type"] == "good"
    assert result["investigation_status"] == "not_requested"
    assert result["codex_cli_command"] is None
    assert bundle["feedback_type"] == "good"
    assert bundle["backend_turn"]["response_mode"] == "fast"
    assert bundle["backend_turn"]["response_prompt"] == "good prompt excerpt"
    assert "Feedback directory: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert result["report_id"].startswith("good_")
    assert scheduled == {}


def test_ui_issue_capture_persists_screenshot_artifact(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )
    service._resolve_thread_id = lambda session_id: session_id or "global-main"
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {}
    scheduled: dict[str, object] = {}
    service._schedule_flagged_report_analysis = lambda **kwargs: scheduled.update(kwargs)

    result = service.flag_chat_feedback(
        session_id="session-ui",
        ticker="BHP",
        feedback_type="poor",
        capture_kind="ui_issue",
        note="Toolbar overlap after resize",
        flagged_message={
            "id": "ui-issue-1",
            "role": "system",
            "content": "Toolbar button overlaps status bar",
        },
        frontend_context={
            "source": "cockpit-ui-issue-capture",
            "pathname": "/verification",
            "debug_bundle": {
                "console": [{"level": "error", "message": "boom"}],
                "network": [{"url": "/api/cockpit/health", "status": 200}],
            },
        },
        screenshot={
            "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9p0NvwAAAABJRU5ErkJggg==",
            "mime_type": "image/png",
            "filename": "ui-screenshot.png",
            "width": 1,
            "height": 1,
            "captured_at": "2026-04-15T07:31:00Z",
        },
    )

    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    assert result["capture_kind"] == "ui_issue"
    assert result["report_id"].startswith("ui_issue_")
    assert scheduled == {}
    assert bundle["capture_kind"] == "ui_issue"
    assert bundle["attachments"][0]["kind"] == "screenshot"
    assert bundle["attachments"][0]["relative_path"] == "ui-screenshot.png"
    assert bundle["attachments"][1]["kind"] == "browser_debug"
    assert bundle["attachments"][1]["relative_path"] == "browser-debug.json"
    assert "data_url" not in json.dumps(bundle)
    assert "debug_bundle" not in json.dumps(bundle)
    screenshot_path = Path(bundle["attachments"][0]["absolute_path"])
    assert screenshot_path.exists()
    assert screenshot_path.read_bytes().startswith(b"\x89PNG")
    debug_path = Path(bundle["attachments"][1]["absolute_path"])
    assert debug_path.exists()
    debug_bundle = json.loads(debug_path.read_text(encoding="utf-8"))
    assert debug_bundle["console"][0]["message"] == "boom"
    summary = Path(result["summary_path"]).read_text(encoding="utf-8")
    investigation = json.loads(Path(result["investigation_path"]).read_text(encoding="utf-8"))
    assert result["investigation_status"] == "queued"
    assert investigation["capture_kind"] == "ui_issue"
    assert result["codex_cli_command"].endswith(
        f"--report-id {result['report_id']} --once --apply"
    )
    assert "# Cockpit UI Issue" in summary
    assert "ui-screenshot.png" in summary
    assert "browser-debug.json" in summary
    assert "Issue directory: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert "Screenshot: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert "Browser debug: reports/cockpit/flagged_sessions/" in result["codex_prompt"]
    assert (
        f"/api/cockpit/feedback/flags/{result['report_id']}/resolve"
        in result["codex_prompt"]
    )


def test_resolve_flagged_report_updates_status_and_filters_open_queue(tmp_path) -> None:
    service = CockpitService.__new__(CockpitService)
    service.repo_root = tmp_path
    service.state_store = None
    service.backend_api_client = None
    service.query_orchestrator = None
    service.llm_client = SimpleNamespace(
        model="model:test", base_url="http://127.0.0.1:8001"
    )
    service._feedback_lock = threading.Lock()
    service._resolve_thread_id = lambda session_id: session_id or "global-main"
    service._resolve_turn_diagnostics = lambda thread_id, flagged_message: {}
    service._schedule_flagged_report_analysis = lambda **kwargs: None

    created = service.flag_chat_feedback(
        session_id="session-1",
        ticker="BHP",
        feedback_type="poor",
        flagged_message={"id": "a1", "role": "assistant", "content": "bad"},
    )
    report_id = created["report_id"]

    open_items_before = service.list_flagged_reports(limit=25, status="open")
    assert any(item["report_id"] == report_id for item in open_items_before)

    resolved = service.resolve_flagged_report(
        report_id,
        commit_sha="abc1234",
        resolved_by="codex",
        note="fixed source contract guard",
    )
    assert resolved["resolution_status"] == "resolved"
    assert resolved["resolution_commit_sha"] == "abc1234"

    open_items_after = service.list_flagged_reports(limit=25, status="open")
    resolved_items = service.list_flagged_reports(limit=25, status="resolved")
    assert all(item["report_id"] != report_id for item in open_items_after)
    assert any(item["report_id"] == report_id for item in resolved_items)

    details = service.get_flagged_report(report_id)
    assert details["resolution_status"] == "resolved"
    assert details["resolution_commit_sha"] == "abc1234"
    assert details["bundle"]["resolution"]["commit_sha"] == "abc1234"
    assert details["investigation"]["status"] == "queued"
    assert details["codex_prompt_path"].endswith("codex_prompt.md")
    assert details["investigation_path"].endswith("investigation.json")
    summary_text = Path(details["summary_path"]).read_text(encoding="utf-8")
    assert "Fix Commit: `abc1234`" in summary_text
