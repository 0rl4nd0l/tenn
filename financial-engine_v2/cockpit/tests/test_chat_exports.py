from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cockpit.core.export_utils import extract_ticker_from_payload
from cockpit.storage.artifacts import ArtifactStore


class ChatExportTests(unittest.TestCase):
    def test_write_analysis_uses_unique_paths_for_fast_successive_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            store = ArtifactStore(
                repo_root=repo_root,
                exports_dir="reports/analysis",
                reports_dir="reports",
            )

            first_md, first_json = store.write_analysis(
                "thread-a",
                "q1",
                "a1",
                {"evidence": []},
            )
            second_md, second_json = store.write_analysis(
                "thread-a",
                "q2",
                "a2",
                {"evidence": []},
            )

            self.assertNotEqual(first_md, second_md)
            self.assertNotEqual(first_json, second_json)
            self.assertTrue(Path(first_md).exists())
            self.assertTrue(Path(second_md).exists())

    def test_chat_export_bundle_includes_recent_artifact_pointers(self) -> None:
        thread_id = "global-main"
        last_chart_path = "/tmp/chart.html"
        last_snapshot_payload = {"ticker": "BHP", "kind": "snapshot"}
        last_verification_payload = {"ticker": "BHP", "kind": "verification"}
        latest_export = {
            "question": "yes",
            "answer": "This will download and process 2 years of ARR announcements.",
            "evidence": [
                {
                    "tool": "run_backfill",
                    "arguments": {"ticker": "ARR", "years": 2},
                    "result": {"arguments": {"ticker": "ARR", "years": 2}},
                }
            ],
            "actions_taken": [
                {
                    "tool": "run_backfill",
                    "arguments": {"ticker": "ARR", "years": 2},
                }
            ],
        }

        class _StateStore:
            def get_chat_messages(self, thread_id: str, limit: int = 200):
                return [{"role": "user", "content": f"message {idx}"} for idx in range(limit)]

            def count_chat_messages(self, thread_id: str) -> int:
                return 250

            def get_latest_export(self, thread_id: str):
                return {"json_path": "", "markdown_path": "", "thread_id": thread_id}

        payload: dict = {
            "exported_at": "now",
            "screen": "chat",
            "thread_id": thread_id,
            "runtime": {},
        }

        state_store = _StateStore()
        payload["chat_messages"] = state_store.get_chat_messages(thread_id, limit=80)
        payload["chat_messages_export_limit"] = 80
        payload["chat_messages_total_in_thread"] = state_store.count_chat_messages(thread_id)
        payload["chat_messages_truncated"] = True
        payload["pending_action"] = None
        payload["last_chart_path"] = last_chart_path
        payload["last_snapshot_payload"] = last_snapshot_payload
        payload["last_verification_payload"] = last_verification_payload
        latest = state_store.get_latest_export(thread_id)
        if latest:
            payload["latest_analysis_export_meta"] = latest
        payload["latest_analysis_export"] = latest_export
        payload["last_detected_ticker"] = extract_ticker_from_payload(latest_export)

        encoded = json.dumps(payload, indent=2, default=str)
        decoded = json.loads(encoded)

        self.assertEqual(len(decoded["chat_messages"]), 80)
        self.assertEqual(decoded["chat_messages_export_limit"], 80)
        self.assertEqual(decoded["chat_messages_total_in_thread"], 250)
        self.assertTrue(decoded["chat_messages_truncated"])
        self.assertEqual(decoded["last_detected_ticker"], "ARR")
        self.assertEqual(decoded["last_chart_path"], last_chart_path)
        self.assertEqual(decoded["last_snapshot_payload"], last_snapshot_payload)
        self.assertEqual(decoded["last_verification_payload"], last_verification_payload)

    def test_extract_ticker_from_payload_prefers_action_and_export_arguments(self) -> None:
        payload = {
            "evidence": [
                {
                    "tool": "run_backfill",
                    "arguments": {"ticker": "arr"},
                    "result": {"arguments": {"ticker": "arr"}},
                }
            ],
            "actions_taken": [{"arguments": {"ticker": "arr"}}],
        }

        self.assertEqual(extract_ticker_from_payload(payload), "ARR")


if __name__ == "__main__":
    unittest.main()
