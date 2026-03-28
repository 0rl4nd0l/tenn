from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
        latest_meta = {"json_path": "", "markdown_path": "", "thread_id": thread_id}

        class _StateStore:
            def get_chat_messages(self, thread_id: str, limit: int = 200):
                return [{"role": "user", "content": "show chart"}]

            def get_latest_export(self, thread_id: str):
                return latest_meta

        payload: dict = {
            "exported_at": "now",
            "screen": "chat",
            "thread_id": thread_id,
            "runtime": {},
        }

        state_store = _StateStore()
        payload["chat_messages"] = state_store.get_chat_messages(thread_id, limit=200)
        payload["pending_action"] = None
        payload["last_detected_ticker"] = "BHP"
        payload["last_chart_path"] = last_chart_path
        payload["last_snapshot_payload"] = last_snapshot_payload
        payload["last_verification_payload"] = last_verification_payload
        latest = state_store.get_latest_export(thread_id)
        if latest:
            payload["latest_analysis_export_meta"] = latest

        encoded = json.dumps(payload, indent=2, default=str)
        decoded = json.loads(encoded)

        self.assertEqual(decoded["last_chart_path"], last_chart_path)
        self.assertEqual(decoded["last_snapshot_payload"], last_snapshot_payload)
        self.assertEqual(decoded["last_verification_payload"], last_verification_payload)


if __name__ == "__main__":
    unittest.main()
