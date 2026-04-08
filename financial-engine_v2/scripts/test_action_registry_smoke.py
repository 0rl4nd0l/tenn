import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cockpit.core.actions import ActionRegistry


class TestActionRegistrySmoke(unittest.TestCase):
    def test_news_ingest_actions_use_absolute_shared_script_paths(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        for action_id, script_name in (
            ("daily_news_ingest", "fetch_daily_news.py"),
            ("historical_news_ingest", "backfill_news.py"),
            ("load_news_to_qdrant", "load_news_to_qdrant.py"),
        ):
            spec = reg.get(action_id)
            script_path = Path(str(spec.command_template[1]))
            self.assertTrue(script_path.is_absolute())
            self.assertEqual(script_path.name, script_name)
            self.assertTrue(script_path.exists())

    def test_visible_actions_use_streamlined_surface(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        ids = [spec.id for spec in reg.list_actions()]
        self.assertEqual(
            ids,
            [
                "daily_news_ingest",
                "historical_news_ingest",
                "daily_announcement_ingest",
                "single_ticker_announcement_backfill",
                "universe_announcement_enrichment_backfill",
                "metric_extraction",
            ],
        )

    def test_build_preview_does_not_crash(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        preview = reg.preview("full_history", {"ticker": "BHP", "years": 1})
        self.assertEqual(preview.action_id, "full_history")
        self.assertTrue(preview.command)

    def test_update_ticker_financials_supports_no_process_documents_flag(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        cmd = reg.build_command(
            "update_ticker_financials",
            {"ticker": "BHP", "years": 1, "process_documents": False},
        )
        self.assertIn("--no-process-documents", cmd)
        self.assertNotIn("--process-documents", cmd)

    def test_asx_chunked_supports_no_download_existing_missing_flag(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        cmd = reg.build_command(
            "asx_enrichment_chunked",
            {"download_existing_missing": False},
        )
        self.assertIn("--no-download-existing-missing", cmd)
        self.assertNotIn("--download-existing-missing", cmd)

    def test_extract_control_args_dry_run_aliases(self):
        clean, control = ActionRegistry.extract_control_args(
            {"ticker": "BHP", "dry_run": "true", "preview-only": "false"},
        )
        self.assertEqual(clean, {"ticker": "BHP"})
        self.assertTrue(control["dry_run"])

    def test_doctor_quick_single_action(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        report = reg.doctor(check_help=False, action_id="daily_news_ingest")
        self.assertEqual(report["counts"]["total"], 1)
        self.assertEqual(report["counts"]["failed"], 0)
        self.assertTrue(report["checks"][0]["ok"])


if __name__ == "__main__":
    unittest.main()
