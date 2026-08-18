import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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

    def test_news_actions_respect_shared_scripts_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            scripts_root = workspace_root / "scripts"
            news_root = workspace_root / "reports" / "qual_context"
            scripts_root.mkdir(parents=True)
            news_root.mkdir(parents=True)
            for script_name in (
                "fetch_daily_news.py",
                "backfill_news.py",
                "load_news_to_qdrant.py",
            ):
                (scripts_root / script_name).write_text("# stub\n", encoding="utf-8")

            prev = os.environ.get("COCKPIT_SHARED_SCRIPTS_ROOT")
            prev_workspace = os.environ.get("COCKPIT_WORKSPACE_ROOT")
            prev_news_root = os.environ.get("TENN_NEWS_ARTIFACT_ROOT")
            os.environ["COCKPIT_SHARED_SCRIPTS_ROOT"] = str(scripts_root)
            os.environ["COCKPIT_WORKSPACE_ROOT"] = str(workspace_root)
            os.environ["TENN_NEWS_ARTIFACT_ROOT"] = str(news_root)
            try:
                reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
            finally:
                if prev is None:
                    os.environ.pop("COCKPIT_SHARED_SCRIPTS_ROOT", None)
                else:
                    os.environ["COCKPIT_SHARED_SCRIPTS_ROOT"] = prev
                if prev_workspace is None:
                    os.environ.pop("COCKPIT_WORKSPACE_ROOT", None)
                else:
                    os.environ["COCKPIT_WORKSPACE_ROOT"] = prev_workspace
                if prev_news_root is None:
                    os.environ.pop("TENN_NEWS_ARTIFACT_ROOT", None)
                else:
                    os.environ["TENN_NEWS_ARTIFACT_ROOT"] = prev_news_root

            for action_id, script_name in (
                ("daily_news_ingest", "fetch_daily_news.py"),
                ("historical_news_ingest", "backfill_news.py"),
                ("load_news_to_qdrant", "load_news_to_qdrant.py"),
            ):
                spec = reg.get(action_id)
                self.assertEqual(
                    str(spec.command_template[1]), str(scripts_root / script_name)
                )

            preview = reg.preview("daily_news_ingest", {})
            self.assertIn("--news-articles-db", preview.command)
            self.assertIn(str(news_root / "news_articles.sqlite"), preview.command)
            self.assertIn(
                str(news_root / "news_runs"),
                preview.command,
            )
            sync_preview = reg.preview("load_news_to_qdrant", {})
            self.assertIn("--db-path", sync_preview.command)
            self.assertIn(str(news_root / "news_articles.sqlite"), sync_preview.command)
            self.assertIn("--news-context-db", sync_preview.command)
            self.assertIn(str(news_root / "news.sqlite"), sync_preview.command)

    def test_daily_news_ingest_defaults_to_newspaper4k(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        preview = reg.preview("daily_news_ingest", {})
        self.assertIn("newspaper4k", preview.command)
        self.assertNotIn("eodhd,gdelt", preview.command)
        idx = preview.command.index("--since-hours")
        self.assertEqual(preview.command[idx + 1], "24")
        profile_idx = preview.command.index("--newspaper4k-source-profile")
        self.assertEqual(preview.command[profile_idx + 1], "daily")
        total_idx = preview.command.index("--newspaper4k-max-total-articles")
        self.assertEqual(preview.command[total_idx + 1], "60")
        timeout_idx = preview.command.index("--newspaper4k-request-timeout-seconds")
        self.assertEqual(preview.command[timeout_idx + 1], "10")
        self.assertIn("--newspaper4k-no-playwright", preview.command)

    def test_daily_news_ingest_broad_profile_keeps_browser_crawl_explicit(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        preview = reg.preview(
            "daily_news_ingest", {"newspaper4k_source_profile": "broad"}
        )
        profile_idx = preview.command.index("--newspaper4k-source-profile")
        self.assertEqual(preview.command[profile_idx + 1], "broad")
        self.assertNotIn("--newspaper4k-no-playwright", preview.command)

    def test_build_preview_does_not_crash(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        preview = reg.preview("full_history", {"ticker": "BHP", "years": 1})
        self.assertEqual(preview.action_id, "full_history")
        self.assertTrue(preview.command)

    def test_run_analysis_preview_builds_executable_command(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        preview = reg.preview("run_analysis", {"ticker": "NST", "modules": "risk,moat"})
        self.assertEqual(preview.action_id, "run_analysis")
        self.assertIn("scripts/run_analysis_action.py", preview.command)
        self.assertIn("--ticker", preview.command)
        self.assertIn("NST", preview.command)
        self.assertIn("--modules", preview.command)
        self.assertIn("risk,moat", preview.command)

    def test_daily_announcement_ingest_normalizes_today_alias(self):
        reg = ActionRegistry(repo_root=ROOT, confirm_required=True)
        preview = reg.preview("daily_announcement_ingest", {"date": "today"})
        idx = preview.command.index("--date")
        self.assertEqual(
            preview.command[idx + 1],
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )

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
