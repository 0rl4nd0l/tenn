#!/usr/bin/env python3
import os
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


@dataclass
class _Preview:
    command: list[str]
    estimated_impact: str
    timeout_seconds: int


class _ActionRegistryStub:
    def preview(self, action_id: str, args: dict) -> _Preview:  # noqa: ARG002
        return _Preview(
            command=["python3", "scripts/update_ticker_financials.py", "--ticker", args.get("ticker", "BHP")],
            estimated_impact="updates ticker data",
            timeout_seconds=7200,
        )


class _ToolResult:
    def __init__(self, payload: dict, ok: bool = True) -> None:
        self.payload = payload
        self.ok = ok


class _ToolRouterStub:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.qual_context_reader = None
        self.qual_context_enabled = True

    def gather_local_context(self, ticker: str | None, query: str, deep_mode: bool = False):  # noqa: ARG002
        payload = dict(self.payload)
        payload["ticker"] = ticker
        payload["query"] = query
        return _ToolResult(payload)

    def fetch_web(self, url: str, enabled: bool, max_chars: int | None = None):  # noqa: ARG002
        return _ToolResult({"url": url, "error": "web unavailable in unit test"}, ok=False)

    def web_enrich(
        self,
        query: str,
        enabled: bool,
        max_results: int = 4,  # noqa: ARG002
        max_chars_per_page: int = 3500,  # noqa: ARG002
        preferred_domains: list[str] | None = None,  # noqa: ARG002
        strict_official: bool = False,  # noqa: ARG002
    ):
        return _ToolResult({"query": query, "pages": [], "error": "web unavailable in unit test"}, ok=False)


class _OllamaShouldNotRun:
    def chat(self, prompt: str, timeout: float = 120.0, on_chunk=None) -> str:  # noqa: ARG002
        raise AssertionError("LLM should not run when answer-readiness evidence is absent")


class _OllamaFrameworkOnly:
    def chat(self, prompt: str, timeout: float = 120.0, on_chunk=None) -> str:  # noqa: ARG002
        return (
            "To conduct a deep analysis of BHP, we need to carefully examine the data.\n"
            "Here is a structured approach:\n"
            "### 1. Moat\n"
            "### 2. Valuation\n"
            "### 3. Risks\n"
        )


class CockpitAnswerReadinessTests(unittest.TestCase):
    def _controller(self, payload: dict, ollama_client=None) -> ChatController:
        return ChatController(
            ollama_client=ollama_client,
            tool_router=_ToolRouterStub(payload),
            action_registry=_ActionRegistryStub(),
        )

    def test_deep_analysis_without_local_or_web_evidence_returns_data_missing(self):
        controller = self._controller(
            {
                "docs": [],
                "financials": [],
                "qual_context": {"ok": False, "hits": []},
                "price": {"ok": False, "error": "not configured"},
                "price_state": {"ok": False, "error": "not configured"},
            },
            ollama_client=_OllamaShouldNotRun(),
        )

        response = controller.build_chat_response("deep analysis analyse BHP", enable_web=True, analysis_mode="deep")

        self.assertIn("This cannot be verified based on available data.", response.text)
        self.assertIn("Announcement sync check for BHP", response.text)
        self.assertEqual(response.analysis_mode, "deep")
        self.assertIsNotNone(response.action_preview)

    def test_stale_announcements_keep_answer_but_offer_update(self):
        stale = datetime.now(timezone.utc) - timedelta(hours=240)
        controller = self._controller(
            {
                "docs": [{"published_at": stale.isoformat(), "title": "Old announcement"}],
                "financials": [],
                "qual_context": {"ok": False, "hits": []},
                "price": {"ok": False, "error": "not configured"},
                "price_state": {"ok": False, "error": "not configured"},
            },
            ollama_client=_OllamaShouldNotRun(),
        )

        response = controller.build_chat_response("bhp announcements", enable_web=False)

        self.assertIn("Latest indexed announcements for BHP", response.text)
        self.assertIn("Announcement sync check for BHP", response.text)
        self.assertEqual(response.action_preview["action_id"], "update_ticker_financials")

    def test_framework_only_deep_output_is_replaced_with_grounded_brief(self):
        controller = self._controller(
            {
                "docs": [{"published_at": "2026-02-18", "title": "BHP 1H26 results presentation"}],
                "financials": [],
                "qual_context": {
                    "ok": True,
                    "hits": [
                        {
                            "score": 0.72,
                            "published_at": "2026-02-18",
                            "title": "BHP operating review",
                            "text": "Liquidity remains strong and operating cash flow supported balance sheet strength.",
                        }
                    ],
                },
                "price": {"ok": False, "error": "not configured"},
                "price_state": {"ok": False, "error": "not configured"},
            },
            ollama_client=_OllamaFrameworkOnly(),
        )

        response = controller.build_chat_response("deep analysis analyse BHP", enable_web=True, analysis_mode="deep")

        self.assertIn("Verdict:", response.text)
        self.assertIn("Evidence:", response.text)
        self.assertIn("[source:", response.text.lower())
        self.assertNotIn("structured approach", response.text.lower())

    def test_price_request_with_unavailable_feed_is_data_missing(self):
        controller = self._controller(
            {
                "docs": [],
                "financials": [],
                "qual_context": {"ok": False, "hits": []},
                "price": {"ok": False, "error": "market price provider returned HTTP 404"},
                "price_state": {"ok": False, "error": "market price provider returned HTTP 404"},
            },
            ollama_client=_OllamaShouldNotRun(),
        )

        response = controller.build_chat_response("bhp price", enable_web=False)

        self.assertIn("This cannot be verified based on available data.", response.text)
        self.assertIn("Price feed error: market price provider returned HTTP 404", response.text)


if __name__ == "__main__":
    unittest.main()
