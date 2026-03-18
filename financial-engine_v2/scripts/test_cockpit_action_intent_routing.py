#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


class CockpitActionIntentRoutingTests(unittest.TestCase):
    def _controller(self) -> ChatController:
        return ChatController(
            ollama_client=None,
            tool_router=None,
            action_registry=None,
        )

    def test_chunked_enrichment_phrase_routes_to_universe_backfill_action(self):
        c = self._controller()
        self.assertEqual(
            c.detect_action_intent("run asx enrichment chunked for 5 years"),
            "universe_announcement_enrichment_backfill",
        )

    def test_recover_marketindex_phrase_has_no_streamlined_action_mapping(self):
        c = self._controller()
        self.assertIsNone(c.detect_action_intent("recover marketindex today"))

    def test_news_ingestion_phrase_routes_to_daily_news_ingest(self):
        c = self._controller()
        self.assertEqual(c.detect_action_intent("run news ingestion"), "daily_news_ingest")

    def test_news_ingestion_common_typo_routes_to_daily_news_ingest(self):
        c = self._controller()
        self.assertEqual(c.detect_action_intent("run news ingewstion"), "daily_news_ingest")

    def test_pull_news_phrase_does_not_route_to_announcements_update(self):
        c = self._controller()
        self.assertIsNone(c.detect_action_intent("pull news for bhp"))


if __name__ == "__main__":
    unittest.main()
