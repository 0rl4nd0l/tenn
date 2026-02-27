#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load_module():
    path = REPO_ROOT / "scripts" / "update_ticker_financials.py"
    spec = importlib.util.spec_from_file_location("update_ticker_financials", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parser_stub(args: argparse.Namespace):
    class _Parser:
        def parse_args(self_inner):  # noqa: ANN001
            return args

    return _Parser()


class UpdateTickerFinancialsQualityGateTests(unittest.TestCase):
    def _base_args(self, report_path: Path, *, policy: str) -> argparse.Namespace:
        return argparse.Namespace(
            ticker="BHP",
            years=1,
            max_backfill_retries=1,
            resume_max_retries=1,
            resume_retry_delay_seconds=0.1,
            process_documents=True,
            skip_resume_pending=True,
            report=str(report_path),
            zero_rows_policy=policy,
            python=sys.executable,
        )

    def test_auto_rebuild_fail_marks_status_failed_when_rows_stay_zero(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "update.json"
            args = self._base_args(report_path, policy="auto_rebuild_fail")
            backfill_payload = {
                "ticker": "BHP",
                "found": 1,
                "inserted": 0,
                "processed": 1,
                "processed_ok_count": 1,
                "extraction_failed_count": 0,
                "skipped_download": 0,
                "process_documents": True,
                "importance_classification": None,
                "provider_metrics": {},
                "provider_failures_sample": [],
                "errors": [],
                "error_count": 0,
            }
            with (
                mock.patch.object(mod, "build_parser", return_value=_parser_stub(args)),
                mock.patch.object(mod, "build_run_metadata", return_value={}),
                mock.patch.object(
                    mod,
                    "_query_financial_state",
                    side_effect=[
                        {"ticker": "BHP", "rows": 0, "latest": None},
                        {"ticker": "BHP", "rows": 0, "latest": None},
                        {"ticker": "BHP", "rows": 0, "latest": None},
                    ],
                ),
                mock.patch.object(mod, "_refresh_announcement_context", return_value={"ok": True}),
                mock.patch.object(mod.subprocess, "run", return_value=SimpleNamespace(returncode=0)),
                mock.patch.dict(
                    sys.modules,
                    {"app.services.pipeline": SimpleNamespace(backfill_ticker_sync=lambda **kwargs: backfill_payload)},
                ),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    mod.main()
            self.assertEqual(int(ctx.exception.code), 1)

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["quality_gate"]["policy"], "auto_rebuild_fail")
            self.assertFalse(payload["quality_gate"]["passed"])
            self.assertEqual(payload["quality_gate"]["after_rows"], 0)
            self.assertIsNotNone(payload["quality_gate"]["rebuild"])

    def test_warn_policy_keeps_success_when_rows_zero_and_no_other_errors(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "update_warn.json"
            args = self._base_args(report_path, policy="warn")
            backfill_payload = {
                "ticker": "BHP",
                "found": 1,
                "inserted": 0,
                "processed": 1,
                "processed_ok_count": 1,
                "extraction_failed_count": 0,
                "skipped_download": 0,
                "process_documents": True,
                "importance_classification": None,
                "provider_metrics": {},
                "provider_failures_sample": [],
                "errors": [],
                "error_count": 0,
            }
            with (
                mock.patch.object(mod, "build_parser", return_value=_parser_stub(args)),
                mock.patch.object(mod, "build_run_metadata", return_value={}),
                mock.patch.object(
                    mod,
                    "_query_financial_state",
                    side_effect=[
                        {"ticker": "BHP", "rows": 0, "latest": None},
                        {"ticker": "BHP", "rows": 0, "latest": None},
                    ],
                ),
                mock.patch.object(mod, "_refresh_announcement_context", return_value={"ok": True}),
                mock.patch.dict(
                    sys.modules,
                    {"app.services.pipeline": SimpleNamespace(backfill_ticker_sync=lambda **kwargs: backfill_payload)},
                ),
            ):
                mod.main()

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "success")
            self.assertTrue(payload["quality_gate"]["passed"])
            self.assertIn("warn mode", " ".join(payload["quality_gate"]["reasons"]).lower())

    def test_extraction_failures_force_failed_status(self):
        mod = _load_module()
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "update_extract_failed.json"
            args = self._base_args(report_path, policy="warn")
            backfill_payload = {
                "ticker": "BHP",
                "found": 1,
                "inserted": 0,
                "processed": 1,
                "processed_ok_count": 0,
                "extraction_failed_count": 1,
                "skipped_download": 0,
                "process_documents": True,
                "importance_classification": None,
                "provider_metrics": {},
                "provider_failures_sample": [],
                "errors": [],
                "error_count": 0,
            }
            with (
                mock.patch.object(mod, "build_parser", return_value=_parser_stub(args)),
                mock.patch.object(mod, "build_run_metadata", return_value={}),
                mock.patch.object(
                    mod,
                    "_query_financial_state",
                    side_effect=[
                        {"ticker": "BHP", "rows": 1, "latest": {"period_end": "2025-12-31"}},
                        {"ticker": "BHP", "rows": 1, "latest": {"period_end": "2025-12-31"}},
                    ],
                ),
                mock.patch.object(mod, "_refresh_announcement_context", return_value={"ok": True}),
                mock.patch.dict(
                    sys.modules,
                    {"app.services.pipeline": SimpleNamespace(backfill_ticker_sync=lambda **kwargs: backfill_payload)},
                ),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    mod.main()
            self.assertEqual(int(ctx.exception.code), 1)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["extraction_failures"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
