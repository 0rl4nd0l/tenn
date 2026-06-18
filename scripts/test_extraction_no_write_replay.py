#!/usr/bin/env python3
"""Focused tests for the certified no-write extraction replay runner."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "extraction_no_write_replay.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("extraction_no_write_replay", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load extraction_no_write_replay")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


class TestExtractionNoWriteReplay(unittest.TestCase):
    def manifest(self):
        return {
            "artifact_type": "extraction_no_write_case_manifest_v1",
            "certification": {
                "allow_production_writes": False,
                "loopback_llm_only": True,
            },
            "cases": [
                {
                    "case_id": "HUB",
                    "ticker": "HUB",
                    "document_id": "doc-hub",
                    "title": "hub.pdf",
                    "source_path": "/tmp/hub.pdf",
                },
                {
                    "case_id": "LBL",
                    "ticker": "LBL",
                    "document_id": "doc-lbl",
                    "title": "lbl.pdf",
                    "source_path": "/tmp/lbl.pdf",
                },
            ],
        }

    def test_select_cases_defaults_to_all_when_selector_empty(self):
        selected = RUNNER.select_cases(self.manifest(), [])
        self.assertEqual(["HUB", "LBL"], [case["case_id"] for case in selected])

    def test_select_cases_uses_explicit_selector_without_implicit_all(self):
        selected = RUNNER.select_cases(self.manifest(), ["HUB"])
        self.assertEqual(["HUB"], [case["case_id"] for case in selected])

    def test_select_cases_rejects_unknown_selector(self):
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.select_cases(self.manifest(), ["DXC"])

    def test_report_dir_must_stay_under_agent_jobs(self):
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.resolve_report_dir("../outside")
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.resolve_report_dir("/tmp/outside")
        resolved = RUNNER.resolve_report_dir(
            "reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay"
        )
        self.assertTrue(str(resolved).startswith(str(ROOT / "reports" / "agent_jobs")))

    def test_manifest_must_stay_under_certified_root(self):
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.resolve_manifest_path(Path("/tmp/guard_cases_v1.json"))
        resolved = RUNNER.resolve_manifest_path(
            Path("financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json")
        )
        self.assertTrue(str(resolved).startswith(str(RUNNER.CERTIFIED_MANIFEST_ROOT.resolve())))

    def test_llm_url_must_be_loopback(self):
        self.assertEqual("http://127.0.0.1:8001", RUNNER.assert_loopback_url("http://127.0.0.1:8001/"))
        self.assertEqual("http://localhost:8001", RUNNER.assert_loopback_url("http://localhost:8001"))
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.assert_loopback_url("https://example.com/v1")

    def test_safe_env_forces_no_write_runtime_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = RUNNER.build_safe_env(Path(tmp), "http://127.0.0.1:8001")
        self.assertEqual(str(Path(tmp) / "home"), env["HOME"])
        self.assertEqual(str(Path(tmp) / "tmp"), env["TMPDIR"])
        self.assertEqual(str(Path(tmp) / "xdg" / "cache"), env["XDG_CACHE_HOME"])
        self.assertEqual("sqlite:///:memory:", env["DATABASE_URL"])
        self.assertEqual("sync", env["TASK_MODE"])
        self.assertEqual("false", env["ENABLE_QDRANT"])
        self.assertEqual("false", env["ENABLE_EMBEDDINGS"])
        self.assertEqual("false", env["ENABLE_SESSION_MEMORY"])
        self.assertEqual("false", env["ROUTER_FEEDBACK_ENABLED"])
        self.assertEqual("memory://tenn-no-write", env["REDIS_URL"])
        self.assertEqual("1", env["EXTRACTION_SKIP_NARRATIVE"])
        self.assertEqual("", env["OPENAI_API_KEY"])
        self.assertEqual("", env["ANTHROPIC_API_KEY"])
        self.assertTrue(env["MODEL_ROUTING_CONFIG"].endswith("financial-engine_v2/backend/app/config/model_routing.yaml"))

    def test_reset_report_outputs_only_removes_known_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            keep = report_dir / "keep.txt"
            stale = report_dir / "validation.json"
            stale_log = report_dir / "logs" / "replay.log"
            keep.write_text("keep", encoding="utf-8")
            stale.write_text("stale", encoding="utf-8")
            stale_log.parent.mkdir(parents=True)
            stale_log.write_text("stale", encoding="utf-8")

            RUNNER._reset_report_outputs(report_dir)

            self.assertTrue(keep.exists())
            self.assertFalse(stale.exists())
            self.assertFalse(stale_log.exists())

    def test_infrastructure_failure_detects_runtime_config_failures(self):
        row = {"result": {"status": "failed", "error": "pass1:OLLAMA_URL must be set when provider is 'ollama'"}}
        self.assertTrue(RUNNER._is_infrastructure_failure(row))

    def test_expectation_failures_compare_status_and_period(self):
        rows = [
            {
                "case_id": "HUB",
                "expected_status": "ok",
                "expected_period_type": "H",
                "expected_period_end": "2023-12-31",
                "result": {"status": "failed", "period_type": None, "period_end": None},
            }
        ]
        failures = RUNNER._expectation_failures(rows)
        self.assertEqual("HUB", failures[0]["case_id"])
        self.assertIn("status", failures[0]["mismatches"])

    def test_manifest_requires_no_production_writes_and_loopback_llm(self):
        bad = self.manifest()
        bad["certification"]["allow_production_writes"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(__import__("json").dumps(bad), encoding="utf-8")
            with self.assertRaises(RUNNER.ReplayConfigError):
                RUNNER.load_manifest(path)


if __name__ == "__main__":
    unittest.main()
