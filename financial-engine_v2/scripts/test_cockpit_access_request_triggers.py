#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


class _DummyToolRouter:
    def __init__(self, *, rag_available: bool, rag_enabled: bool) -> None:
        self.qual_context_reader = object() if rag_available else None
        self.qual_context_enabled = rag_enabled
        self.web_enrich_calls = 0
        self.last_web_query = None
        self.db_reader = SimpleNamespace(last_error=None)

    def gather_local_context(self, ticker: str | None, query: str, deep_mode: bool = False):
        payload = {
            "ticker": ticker,
            "query": query,
            "docs": [{"title": "Quarterly update", "published_at": "2026-02-01T00:00:00+00:00"}],
            "financials": [{"period_end": "2025-12-31"}],
            "price_state": {"ok": True},
            "price": {},
            "matches": [],
            "reports": [],
        }
        return SimpleNamespace(payload=payload)

    def web_enrich(
        self,
        query: str,
        *,
        enabled: bool,
        max_results: int = 3,
        max_chars_per_page: int = 3000,
        preferred_domains: list[str] | None = None,  # noqa: ARG002
        strict_official: bool = False,  # noqa: ARG002
    ):
        self.web_enrich_calls += 1
        self.last_web_query = query
        payload = {
            "ok": True,
            "query": query,
            "pages": [{"url": "https://example.com", "content": "Sample external evidence"}],
        }
        return SimpleNamespace(ok=True, payload=payload)


class _DummyOllama:
    def chat(self, prompt: str, timeout: float = 300.0, on_chunk=None) -> str:
        return "Deep analysis answer."


class CockpitAccessRequestTriggerTests(unittest.TestCase):
    def test_web_access_request_preview_when_url_and_web_disabled(self):
        controller = ChatController(
            ollama_client=None,
            tool_router=_DummyToolRouter(rag_available=False, rag_enabled=False),
            action_registry=None,
        )
        response = controller.build_chat_response(
            "deep analysis analyse BHP using https://example.com/source",
            enable_web=False,
            prior_ticker=None,
            analysis_mode="deep",
        )
        self.assertIsNotNone(response.action_preview)
        self.assertEqual(response.action_preview.get("action_id"), "__access_request__")
        self.assertEqual((response.action_preview.get("args") or {}).get("scope"), "web")

    def test_rag_access_request_preview_when_deep_analysis_and_rag_disabled(self):
        controller = ChatController(
            ollama_client=None,
            tool_router=_DummyToolRouter(rag_available=True, rag_enabled=False),
            action_registry=None,
        )
        response = controller.build_chat_response(
            "deep analysis analyse BHP",
            enable_web=True,
            prior_ticker=None,
            analysis_mode="deep",
        )
        self.assertIsNotNone(response.action_preview)
        self.assertEqual(response.action_preview.get("action_id"), "__access_request__")
        self.assertEqual((response.action_preview.get("args") or {}).get("scope"), "rag")

    def test_deep_mode_auto_web_enrichment_when_enabled(self):
        router = _DummyToolRouter(rag_available=False, rag_enabled=False)
        controller = ChatController(
            ollama_client=_DummyOllama(),
            tool_router=router,
            action_registry=None,
        )
        response = controller.build_chat_response(
            "deep analysis analyse BHP",
            enable_web=True,
            prior_ticker=None,
            analysis_mode="deep",
        )
        self.assertEqual(router.web_enrich_calls, 1)
        self.assertIn("BHP", str(router.last_web_query or ""))
        self.assertTrue(any((ev or {}).get("type") == "web" for ev in response.evidence))


if __name__ == "__main__":
    unittest.main()
