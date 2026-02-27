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

    def test_chunked_enrichment_phrase_routes_to_chunked_action(self):
        c = self._controller()
        self.assertEqual(c.detect_action_intent("run asx enrichment chunked for 5 years"), "asx_enrichment_chunked")

    def test_recover_marketindex_phrase_not_shadowed_by_daily_marketindex(self):
        c = self._controller()
        self.assertEqual(c.detect_action_intent("recover marketindex today"), "recover_headed")


if __name__ == "__main__":
    unittest.main()
