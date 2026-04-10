#!/usr/bin/env python3
import os
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.actions import ActionRegistry, VISIBLE_ACTION_IDS  # noqa: E402
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
        self.assertEqual(
            c.detect_action_intent("run news ingestion"), "daily_news_ingest"
        )

    def test_news_ingestion_common_typo_routes_to_daily_news_ingest(self):
        c = self._controller()
        self.assertEqual(
            c.detect_action_intent("run news ingewstion"), "daily_news_ingest"
        )

    def test_pull_news_phrase_does_not_route_to_announcements_update(self):
        c = self._controller()
        self.assertIsNone(c.detect_action_intent("pull news for bhp"))

    def test_load_news_qdrant_phrase_routes_to_action(self):
        c = self._controller()
        self.assertEqual(
            c.detect_action_intent("load news to qdrant"), "load_news_to_qdrant"
        )

    def test_sync_news_chunks_phrase_routes_to_load_news_qdrant(self):
        c = self._controller()
        self.assertEqual(
            c.detect_action_intent("sync news chunks to qdrant"), "load_news_to_qdrant"
        )

    def test_ingest_ticker_shortcut_routes_to_single_ticker_backfill(self):
        os.environ["COCKPIT_AGENT_MODE"] = "keyword"

        class _FakeActionRegistry:
            @staticmethod
            def preview(action_id: str, args: dict[str, object]) -> SimpleNamespace:
                return SimpleNamespace(
                    command=[
                        "python",
                        "scripts/full_history_ticker_sync.py",
                        "--ticker",
                        str(args["ticker"]),
                    ],
                    estimated_impact="mutates local data and reports",
                    timeout_seconds=14400,
                )

        controller = ChatController(
            ollama_client=None,
            tool_router=None,
            action_registry=_FakeActionRegistry(),
        )

        response = controller.build_chat_response("ingest eos")

        self.assertEqual(
            response.action_preview["action_id"], "single_ticker_announcement_backfill"
        )
        self.assertEqual(response.action_preview["args"]["ticker"], "EOS")


class CockpitLoadNewsQdrantActionTests(unittest.TestCase):
    def setUp(self):
        self.registry = ActionRegistry(repo_root=REPO_ROOT, confirm_required=False)

    def test_load_news_to_qdrant_is_in_visible_actions(self):
        self.assertIn("load_news_to_qdrant", VISIBLE_ACTION_IDS)

    def test_load_news_to_qdrant_action_exists_in_registry(self):
        spec = self.registry.get("load_news_to_qdrant")
        self.assertEqual(spec.id, "load_news_to_qdrant")

    def test_load_news_to_qdrant_command_references_correct_script(self):
        spec = self.registry.get("load_news_to_qdrant")
        cmd_str = " ".join(spec.command_template)
        self.assertIn("load_news_to_qdrant.py", cmd_str)

    def test_load_news_to_qdrant_is_mutating(self):
        spec = self.registry.get("load_news_to_qdrant")
        self.assertTrue(spec.is_mutating)

    def test_load_news_to_qdrant_build_command_succeeds_with_defaults(self):
        command = self.registry.build_command("load_news_to_qdrant", {})
        self.assertTrue(any("load_news_to_qdrant.py" in part for part in command))

    def test_load_news_to_qdrant_since_hours_defaults_to_zero(self):
        command = self.registry.build_command("load_news_to_qdrant", {})
        idx = command.index("--since-hours")
        self.assertEqual(
            command[idx + 1],
            "0",
            "since_hours must default to 0 (sync all) for load_news_to_qdrant",
        )


if __name__ == "__main__":
    unittest.main()
