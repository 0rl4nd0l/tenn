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
    def preview(self, action_id: str, args: dict) -> _Preview:
        return _Preview(
            command=["python3", "scripts/update_ticker_financials.py", "--ticker", args.get("ticker", "BHP")],
            estimated_impact="updates ticker data",
            timeout_seconds=7200,
        )


class _ToolRouterStub:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def gather_local_context(self, ticker: str | None, query: str, deep_mode: bool = False):  # noqa: ARG002
        class _Result:
            def __init__(self, payload):
                self.payload = payload

        payload = {
            "query": query,
            "ticker": ticker,
            "docs": list(self._docs),
            "reports": [],
            "matches": [],
            "price": {"ok": False, "error": "not configured"},
            "price_state": {"ok": False, "error": "not configured"},
        }
        return _Result(payload)


class CockpitAnnouncementSyncOfferTests(unittest.TestCase):
    def _controller(self, tool_router=None) -> ChatController:
        return ChatController(
            ollama_client=None,
            tool_router=tool_router,
            action_registry=_ActionRegistryStub(),
        )

    def test_missing_docs_marks_stale_and_offers_update(self):
        c = self._controller()
        sync = c._compute_announcement_sync_status("BHP", docs=[], message="analyse bhp")
        self.assertEqual(sync["status"], "missing")
        self.assertTrue(sync["needs_update_offer"])

        offer = c._build_ticker_update_offer("BHP", sync)
        self.assertIsNotNone(offer)
        self.assertIn("Announcement sync check for BHP", offer["note"])
        self.assertEqual(offer["action_preview"]["action_id"], "update_ticker_financials")

    def test_fresh_docs_returns_up_to_date_note_without_action(self):
        c = self._controller()
        fresh = datetime.now(timezone.utc) - timedelta(hours=12)
        docs = [{"published_at": fresh.isoformat(), "title": "Recent announcement"}]
        sync = c._compute_announcement_sync_status("BHP", docs=docs, message="analyse bhp")
        self.assertEqual(sync["status"], "fresh")
        self.assertFalse(sync["needs_update_offer"])
        offer = c._build_ticker_update_offer("BHP", sync)
        self.assertIsNotNone(offer)
        self.assertIn("up to date", str(offer.get("note", "")).lower())
        self.assertIsNone(offer.get("action_preview"))

    def test_stale_docs_offer(self):
        c = self._controller()
        stale = datetime.now(timezone.utc) - timedelta(hours=240)
        docs = [{"published_at": stale.isoformat(), "title": "Old announcement"}]
        sync = c._compute_announcement_sync_status("BHP", docs=docs, message="latest bhp announcements")
        self.assertEqual(sync["status"], "stale")
        self.assertTrue(sync["needs_update_offer"])
        offer = c._build_ticker_update_offer("BHP", sync)
        self.assertIsNotNone(offer)
        self.assertIn("/confirm", offer["note"])
        self.assertIn("--ticker", " ".join(offer["action_preview"]["command"]))

    def test_build_chat_response_sets_action_preview_when_stale(self):
        stale = datetime.now(timezone.utc) - timedelta(hours=240)
        tool_router = _ToolRouterStub(docs=[{"published_at": stale.isoformat(), "title": "Old announcement"}])
        c = self._controller(tool_router=tool_router)

        response = c.build_chat_response("bhp announcements", enable_web=False)
        self.assertIsNotNone(response.action_preview)
        self.assertEqual(response.action_preview["action_id"], "update_ticker_financials")
        self.assertIn("/confirm", response.text)

    def test_build_chat_response_shows_up_to_date_note_when_fresh(self):
        fresh = datetime.now(timezone.utc) - timedelta(hours=6)
        tool_router = _ToolRouterStub(docs=[{"published_at": fresh.isoformat(), "title": "Recent announcement"}])
        c = self._controller(tool_router=tool_router)

        response = c.build_chat_response("bhp announcements", enable_web=False)
        self.assertIsNone(response.action_preview)
        self.assertIn("announcement sync check for bhp: up to date", response.text.lower())

    def test_conversational_update_shortcut_prepares_update_action(self):
        tool_router = _ToolRouterStub(docs=[])
        c = self._controller(tool_router=tool_router)

        response = c.build_chat_response("update bhp announcements now", enable_web=False)
        self.assertIsNotNone(response.action_preview)
        self.assertEqual(response.action_preview["action_id"], "update_ticker_financials")
        self.assertEqual(response.action_preview["args"]["ticker"], "BHP")
        self.assertEqual(response.action_preview["args"]["years"], 1)
        self.assertTrue(response.action_preview["args"]["process_documents"])


if __name__ == "__main__":
    unittest.main()
