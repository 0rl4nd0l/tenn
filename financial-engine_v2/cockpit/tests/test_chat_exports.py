from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cockpit.core.export_utils import extract_ticker_from_payload
from cockpit.storage.artifacts import ArtifactStore

try:
    from cockpit.ui.app import CockpitApp
except ModuleNotFoundError:
    CockpitApp = None


class ChatExportTests(unittest.TestCase):
    @staticmethod
    def _build_chat_export_payload(
        latest_meta: dict[str, str] | None,
        *,
        last_detected_ticker: str | None = None,
    ) -> dict:
        payload: dict = {
            "exported_at": "now",
            "screen": "chat",
            "thread_id": "thread-a",
            "runtime": {},
            "chat_messages": [{"role": "user", "content": f"message {idx}"} for idx in range(5)],
            "chat_messages_export_limit": 80,
            "chat_messages_total_in_thread": 5,
            "chat_messages_truncated": False,
            "pending_action": None,
            "last_chart_path": None,
            "last_snapshot_payload": None,
            "last_verification_payload": None,
        }
        latest_export_payload: dict | None = None
        effective_ticker = last_detected_ticker
        if latest_meta:
            payload["latest_analysis_export_meta"] = latest_meta
            try:
                json_path = Path(str(latest_meta.get("json_path", ""))).expanduser()
                if json_path.exists() and json_path.is_file():
                    latest_export_payload = json.loads(json_path.read_text(encoding="utf-8"))
                    payload["latest_analysis_export"] = latest_export_payload
            except (OSError, json.JSONDecodeError) as exc:
                payload["latest_analysis_export_error"] = str(exc)
        if not effective_ticker:
            effective_ticker = extract_ticker_from_payload(latest_export_payload)
        payload["last_detected_ticker"] = effective_ticker
        return payload

    @unittest.skipIf(CockpitApp is None, "textual/cockpit UI deps unavailable in this environment")
    def test_export_copy_bundle_redacts_settings_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            notifications: list[str] = []

            class _FakeApp:
                def __init__(self):
                    self.thread_id = "thread-a"
                    self.config = {
                        "runtime": {"mode": "test"},
                        "llm": {
                            "llamacpp_api_key": "super-secret",
                            "llamacpp_url": "http://user:pass@localhost:8001/v1",
                        },
                    }
                    self.screen = SimpleNamespace(name="settings")
                    self.state_store = SimpleNamespace()
                    self.pending_action = None
                    self.last_chart_path = None
                    self.last_snapshot_payload = None
                    self.last_verification_payload = None
                    self.last_detected_ticker = None
                    self.repo_root = repo_root

                def timestamp(self):
                    return "20260329_000001"

                def _copy_to_clipboard(self, text: str) -> bool:
                    return False

                def _write_log(self, log_target: str, notice: str) -> None:
                    return None

                def notify(self, notice: str) -> None:
                    notifications.append(notice)

                _sanitize_export_payload = classmethod(CockpitApp._sanitize_export_payload.__func__)
                _export_log_target = staticmethod(CockpitApp._export_log_target)

            app = _FakeApp()

            CockpitApp.action_export_copy_bundle(app)

            bundle_path = repo_root / "reports" / "cockpit" / "exports" / "claude_context.json"
            payload = json.loads(bundle_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["settings"]["llm"]["llamacpp_api_key"], CockpitApp._REDACTED_EXPORT_VALUE)
            self.assertEqual(payload["settings"]["llm"]["llamacpp_url"], "http://localhost:8001/v1")
            self.assertTrue(notifications)

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

    def test_export_copy_bundle_records_corrupt_latest_export_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            export_dir = repo_root / "reports" / "analysis" / "thread-a"
            export_dir.mkdir(parents=True, exist_ok=True)
            broken_json = export_dir / "latest.json"
            broken_json.write_text("{not valid json", encoding="utf-8")

            payload = self._build_chat_export_payload(
                {
                    "json_path": str(broken_json),
                    "markdown_path": str(export_dir / "latest.md"),
                    "thread_id": "thread-a",
                },
            )

            self.assertIn("latest_analysis_export_meta", payload)
            self.assertIn("latest_analysis_export_error", payload)
            self.assertNotIn("latest_analysis_export", payload)

    def test_export_copy_bundle_extracts_ticker_from_latest_export_action_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            export_dir = repo_root / "reports" / "analysis" / "thread-a"
            export_dir.mkdir(parents=True, exist_ok=True)
            latest_json = export_dir / "latest.json"
            latest_json.write_text(
                json.dumps(
                    {
                        "question": "update financials",
                        "answer": "ready",
                        "action_preview": {
                            "action_id": "update_ticker_financials",
                            "args": {"ticker": "csl"},
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = self._build_chat_export_payload(
                {
                    "json_path": str(latest_json),
                    "markdown_path": str(export_dir / "latest.md"),
                    "thread_id": "thread-a",
                },
            )

            self.assertEqual(payload["last_detected_ticker"], "CSL")
            self.assertEqual(payload["latest_analysis_export"]["action_preview"]["args"]["ticker"], "csl")

    def test_write_analysis_renders_price_state_markdown_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            store = ArtifactStore(
                repo_root=repo_root,
                exports_dir="reports/analysis",
                reports_dir="reports",
            )

            md_path, _json_path = store.write_analysis(
                "thread-a",
                "What is the setup?",
                "Here is the answer.",
                {
                    "evidence": [
                        {
                            "details": {
                                "price_state": {
                                    "ok": True,
                                    "ticker": "BHP",
                                    "currency": "AUD",
                                    "last_close": 45.12,
                                    "ret_1d": 1.25,
                                    "ret_20d": -2.5,
                                    "trend_regime": "uptrend",
                                    "vol_20d_ann": 22.4,
                                    "drawdown_from_63d_high": 5.1,
                                    "market_time_utc": "2026-03-29T00:00:00Z",
                                    "data_age_hours": 2.0,
                                    "stale_data": False,
                                    "history_points": 252,
                                }
                            }
                        }
                    ]
                },
            )

            markdown = Path(md_path).read_text(encoding="utf-8")

            self.assertIn("## Price State", markdown)
            self.assertIn("ticker `BHP`", markdown)
            self.assertIn("Last close: 45.12 AUD", markdown)
            self.assertIn("Returns: 1D +1.25%, 20D -2.50%", markdown)
            self.assertIn("Freshness: fresh, market_time=2026-03-29T00:00:00Z, age=2.0h, history_points=252", markdown)


if __name__ == "__main__":
    unittest.main()
