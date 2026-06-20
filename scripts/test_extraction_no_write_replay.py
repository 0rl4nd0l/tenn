#!/usr/bin/env python3
"""Focused tests for the certified no-write extraction replay runner."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
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

    def test_profile_must_be_certified(self):
        self.assertEqual(RUNNER.BASELINE_PROFILE, RUNNER.normalize_profile(""))
        self.assertEqual(RUNNER.DOCLING_PROFILE, RUNNER.normalize_profile(RUNNER.DOCLING_PROFILE))
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.normalize_profile("ad-hoc-docling")

    def test_docling_venv_python_must_be_approved_candidate(self):
        approved = RUNNER.resolve_approved_venv_python("financial-engine_v2/.venv/bin/python")
        self.assertTrue(str(approved).endswith("financial-engine_v2/.venv/bin/python"))
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.resolve_approved_venv_python("/tmp/random-venv/bin/python")

    def test_docling_profile_rejects_non_docling_manifest_cases(self):
        cases = [
            {"case_id": "HUB", "parser_backend": "docling"},
            {"case_id": "WHC", "parser_backend": "pymupdf"},
        ]
        incompatible = RUNNER._docling_incompatible_cases(cases)
        self.assertEqual([{"case_id": "WHC", "parser_backend": "pymupdf"}], incompatible)

    def test_docling_profile_forces_strict_docling_cases(self):
        cases = [
            {"case_id": "HUB", "parser_backend": "docling", "strict_parser": False},
            {"case_id": "LBL"},
        ]
        strict_cases = RUNNER._force_docling_profile_cases(cases)
        self.assertEqual(["docling", "docling"], [case["parser_backend"] for case in strict_cases])
        self.assertEqual([True, True], [case["strict_parser"] for case in strict_cases])
        self.assertFalse(cases[0]["strict_parser"])

    def test_docling_reexec_preserves_source_root_env(self):
        old_data_root = os.environ.get("DATA_ROOT")
        old_docs_root = os.environ.get("DOCS_ROOT")
        old_execve = RUNNER.os.execve
        captured = {}

        def fake_execve(path, argv, env):
            captured["path"] = path
            captured["argv"] = argv
            captured["env"] = env
            raise RuntimeError("captured-execve")

        try:
            os.environ["DATA_ROOT"] = "/tmp/source-data"
            os.environ["DOCS_ROOT"] = "/tmp/source-docs"
            RUNNER.os.execve = fake_execve
            args = argparse.Namespace(venv_python=None, _profile_reexeced=False)
            with self.assertRaisesRegex(RuntimeError, "captured-execve"):
                RUNNER._reexec_for_docling_profile(Path(sys.executable), args)
            self.assertEqual("/tmp/source-data", captured["env"]["DATA_ROOT"])
            self.assertEqual("/tmp/source-docs", captured["env"]["DOCS_ROOT"])
        finally:
            RUNNER.os.execve = old_execve
            if old_data_root is None:
                os.environ.pop("DATA_ROOT", None)
            else:
                os.environ["DATA_ROOT"] = old_data_root
            if old_docs_root is None:
                os.environ.pop("DOCS_ROOT", None)
            else:
                os.environ["DOCS_ROOT"] = old_docs_root

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

    def test_safe_env_report_redacts_secret_values(self):
        report = RUNNER._safe_env_report(
            {
                "DATA_ROOT": "/tmp/no-write",
                "LLM_API_KEY": "secret-local-key",
                "OPENAI_API_KEY": "",
                "ANTHROPIC_API_KEY": "secret-anthropic-key",
            }
        )
        self.assertEqual("/tmp/no-write", report["DATA_ROOT"])
        self.assertEqual("<redacted>", report["LLM_API_KEY"])
        self.assertEqual("", report["OPENAI_API_KEY"])
        self.assertEqual("<redacted>", report["ANTHROPIC_API_KEY"])
        self.assertNotIn("secret-local-key", str(report))
        self.assertNotIn("secret-anthropic-key", str(report))

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

    def test_run_replay_validates_case_selector_before_resetting_reports(self):
        report_rel = "reports/agent_jobs/extraction_no_write_invalid_selector_test/run"
        report_root = ROOT / "reports" / "agent_jobs" / "extraction_no_write_invalid_selector_test"
        report_dir = ROOT / report_rel
        stale = report_dir / "validation.json"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale validation", encoding="utf-8")

        args = argparse.Namespace(
            profile=RUNNER.BASELINE_PROFILE,
            venv_python=None,
            case_manifest=str(RUNNER.DEFAULT_MANIFEST),
            report_dir=report_rel,
            case=["DXC"],
            llm_url="http://127.0.0.1:8001",
            preflight_only=True,
            _profile_reexeced=False,
        )
        try:
            with self.assertRaises(RUNNER.ReplayConfigError):
                RUNNER.run_replay(args)
            self.assertEqual("stale validation", stale.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(report_root, ignore_errors=True)

    def test_run_replay_validates_llm_url_before_resetting_reports(self):
        report_rel = "reports/agent_jobs/extraction_no_write_invalid_llm_url_test/run"
        report_root = ROOT / "reports" / "agent_jobs" / "extraction_no_write_invalid_llm_url_test"
        report_dir = ROOT / report_rel
        stale = report_dir / "validation.json"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale validation", encoding="utf-8")

        args = argparse.Namespace(
            profile=RUNNER.BASELINE_PROFILE,
            venv_python=None,
            case_manifest=str(RUNNER.DEFAULT_MANIFEST),
            report_dir=report_rel,
            case=["WHC"],
            llm_base_url="https://example.com/v1",
            preflight_only=True,
            _profile_reexeced=False,
        )
        try:
            with self.assertRaises(RUNNER.ReplayConfigError):
                RUNNER.run_replay(args)
            self.assertEqual("stale validation", stale.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(report_root, ignore_errors=True)

    def test_portable_source_path_resolves_against_data_root(self):
        old_data_root = os.environ.get("DATA_ROOT")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                data_root = Path(tmp) / "data"
                source = (
                    data_root
                    / "asx"
                    / "docs"
                    / "HUB"
                    / "financial_performance"
                    / "hub.pdf"
                )
                source.parent.mkdir(parents=True)
                source.write_text("pdf", encoding="utf-8")
                os.environ["DATA_ROOT"] = str(data_root)

                resolved, candidates = RUNNER.resolve_source_path(
                    "asx/docs/HUB/financial_performance/hub.pdf"
                )

                self.assertEqual(source.resolve(), resolved)
                self.assertIn(source.resolve(), candidates)
        finally:
            if old_data_root is None:
                os.environ.pop("DATA_ROOT", None)
            else:
                os.environ["DATA_ROOT"] = old_data_root

    def test_no_run_artifacts_record_data_missing_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            manifest_path = report_dir / "manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            RUNNER._write_no_run_artifacts(
                report_dir=report_dir,
                manifest_path=manifest_path,
                cases=[{"case_id": "HUB"}],
                profile=RUNNER.DOCLING_PROFILE,
                profile_info={"profile": RUNNER.DOCLING_PROFILE},
                llm_url="http://127.0.0.1:8001",
                data_root=report_dir / "tmp",
                safe_env={"DATA_ROOT": str(report_dir / "tmp")},
                status="DATA_MISSING",
                reason="docling_import_failed",
            )

            validation = __import__("json").loads((report_dir / "validation.json").read_text(encoding="utf-8"))
            audit = __import__("json").loads((report_dir / "side_effect_audit.json").read_text(encoding="utf-8"))
            self.assertEqual("DATA_MISSING", validation["status"])
            self.assertEqual(RUNNER.DOCLING_PROFILE, validation["profile"])
            self.assertTrue(audit["forbidden_surface_clean"])
            self.assertFalse(any(audit["forbidden_surface_mutation"].values()))

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

    def test_replay_status_fails_when_isolated_containment_fails(self):
        side_effect_audit = {
            "forbidden_surface_clean": True,
            "report_only_durable_writes": True,
            "isolated_cache_contained": False,
            "isolated_runtime_contained": True,
        }
        self.assertFalse(RUNNER._side_effect_pass(side_effect_audit))
        self.assertEqual(
            "FAIL",
            RUNNER._derive_replay_status(
                side_effect_audit,
                llm_missing=False,
                extraction_exception_count=0,
                infrastructure_failure_count=0,
                expectation_failure_count=0,
            ),
        )

    def test_replay_status_fails_unexpected_extraction_exception(self):
        side_effect_audit = {
            "forbidden_surface_clean": True,
            "report_only_durable_writes": True,
            "isolated_cache_contained": True,
            "isolated_runtime_contained": True,
        }
        self.assertEqual(
            "FAIL",
            RUNNER._derive_replay_status(
                side_effect_audit,
                llm_missing=False,
                extraction_exception_count=1,
                infrastructure_failure_count=0,
                expectation_failure_count=0,
            ),
        )

    def test_exception_rows_are_not_classified_as_infrastructure_data_missing(self):
        row = {
            "case_id": "HUB",
            "result": {
                "status": "exception",
                "error": "ValueError: unexpected parser failure",
            },
        }
        side_effect_audit = {
            "forbidden_surface_clean": True,
            "report_only_durable_writes": True,
            "isolated_cache_contained": True,
            "isolated_runtime_contained": True,
        }
        results = [row]
        extraction_exceptions = [
            item for item in results if (item.get("result") or {}).get("status") == "exception"
        ]
        infrastructure_failures = [item for item in results if RUNNER._is_infrastructure_failure(item)]

        self.assertEqual([row], extraction_exceptions)
        self.assertEqual([], infrastructure_failures)
        self.assertEqual(
            "FAIL",
            RUNNER._derive_replay_status(
                side_effect_audit,
                llm_missing=False,
                extraction_exception_count=len(extraction_exceptions),
                infrastructure_failure_count=len(infrastructure_failures),
                expectation_failure_count=0,
            ),
        )

    def test_runner_value_error_payload_fails_replay_status(self):
        try:
            raise ValueError("unexpected runner bug")
        except ValueError as exc:
            results, llm_info = RUNNER._runner_exception_payload(exc)

        side_effect_audit = {
            "forbidden_surface_clean": True,
            "report_only_durable_writes": True,
            "isolated_cache_contained": True,
            "isolated_runtime_contained": True,
        }

        self.assertEqual("exception", llm_info["status"])
        self.assertEqual("unexpected_runner_exception", llm_info["classification"])
        self.assertEqual("__runner__", results[0]["case_id"])
        self.assertEqual("exception", results[0]["result"]["status"])
        self.assertEqual(
            "FAIL",
            RUNNER._derive_replay_status(
                side_effect_audit,
                llm_missing=llm_info.get("status") == "DATA_MISSING",
                extraction_exception_count=len(results),
                infrastructure_failure_count=0,
                expectation_failure_count=0,
            ),
        )

    def test_runner_module_missing_payload_stays_data_missing(self):
        try:
            raise ModuleNotFoundError("No module named 'httpx'")
        except ModuleNotFoundError as exc:
            results, llm_info = RUNNER._runner_exception_payload(exc)

        self.assertEqual([], results)
        self.assertEqual("DATA_MISSING", llm_info["status"])
        self.assertEqual("infrastructure", llm_info["classification"])

    def test_surface_audit_fails_on_new_non_report_git_status_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports" / "agent_jobs" / "job" / "run"
            audit = RUNNER._surface_audit(
                git_before=[],
                git_after=[" M financial-engine_v2/backend/app/prompts/example.txt"],
                source_before={},
                source_after={},
                normal_cache_before={},
                normal_cache_after={},
                report_dir=report_dir,
                report_files=[],
                isolated_cache_root=root / "cache",
                isolated_cache_files=[],
                isolated_runtime_root=root / "runtime",
                isolated_runtime_files=[],
            )

        self.assertFalse(audit["forbidden_surface_clean"])
        self.assertTrue(audit["forbidden_surface_mutation"]["repo_worktree_write"])
        self.assertEqual(
            [" M financial-engine_v2/backend/app/prompts/example.txt"],
            audit["unexpected_git_status_changes"],
        )
        self.assertFalse(RUNNER._side_effect_pass(audit))

    def test_surface_audit_allows_new_report_local_git_status_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports" / "agent_jobs" / "job" / "run"
            audit = RUNNER._surface_audit(
                git_before=[],
                git_after=[" M reports/agent_jobs/job/run/validation.json"],
                source_before={},
                source_after={},
                normal_cache_before={},
                normal_cache_after={},
                report_dir=report_dir,
                report_files=[],
                isolated_cache_root=root / "cache",
                isolated_cache_files=[],
                isolated_runtime_root=root / "runtime",
                isolated_runtime_files=[],
            )

        self.assertTrue(audit["forbidden_surface_clean"])
        self.assertFalse(audit["forbidden_surface_mutation"]["repo_worktree_write"])
        self.assertEqual([], audit["unexpected_git_status_changes"])

    def test_surface_audit_fails_on_preexisting_dirty_file_content_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports" / "agent_jobs" / "job" / "run"
            audit = RUNNER._surface_audit(
                git_before=[" M financial-engine_v2/backend/app/prompts/example.txt"],
                git_after=[" M financial-engine_v2/backend/app/prompts/example.txt"],
                source_before={},
                source_after={},
                normal_cache_before={},
                normal_cache_after={},
                report_dir=report_dir,
                report_files=[],
                isolated_cache_root=root / "cache",
                isolated_cache_files=[],
                isolated_runtime_root=root / "runtime",
                isolated_runtime_files=[],
                dirty_repo_before={
                    "financial-engine_v2/backend/app/prompts/example.txt": {
                        "exists": True,
                        "sha256": "before",
                    }
                },
                dirty_repo_after={
                    "financial-engine_v2/backend/app/prompts/example.txt": {
                        "exists": True,
                        "sha256": "after",
                    }
                },
            )

        self.assertFalse(audit["forbidden_surface_clean"])
        self.assertTrue(audit["forbidden_surface_mutation"]["repo_worktree_write"])
        self.assertTrue(audit["dirty_repo_file_mutations"])
        self.assertEqual([], audit["unexpected_git_status_changes"])

    def test_surface_audit_fails_on_source_sidecar_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "data" / "asx" / "docs" / "HUB" / "financial_performance"
            source_dir.mkdir(parents=True)
            source_pdf = source_dir / "hub.pdf"
            source_pdf.write_bytes(b"%PDF-1.4\n")
            cases = [{"case_id": "HUB", "source_path": str(source_pdf)}]

            source_before = RUNNER._source_snapshot(cases)
            (source_dir / "hub.pdf.ocr.tmp").write_text("sidecar", encoding="utf-8")
            source_after = RUNNER._source_snapshot(cases)

            audit = RUNNER._surface_audit(
                git_before=[],
                git_after=[],
                source_before=source_before,
                source_after=source_after,
                normal_cache_before={},
                normal_cache_after={},
                report_dir=root / "reports" / "agent_jobs" / "job" / "run",
                report_files=[],
                isolated_cache_root=root / "cache",
                isolated_cache_files=[],
                isolated_runtime_root=root / "runtime",
                isolated_runtime_files=[],
            )

        self.assertFalse(audit["forbidden_surface_clean"])
        self.assertTrue(audit["forbidden_surface_mutation"]["source_pdf_write"])
        self.assertTrue(audit["forbidden_surface_mutation"]["source_tree_write"])
        self.assertFalse(RUNNER._side_effect_pass(audit))

    def test_normal_cache_snapshot_tracks_unpredicted_cache_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cache"
            root.mkdir()
            before = RUNNER._normal_cache_snapshot([], [root])
            extra = root / "unexpected.tmp"
            extra.write_text("cache", encoding="utf-8")
            after = RUNNER._normal_cache_snapshot([], [root])

        self.assertNotEqual(before, after)
        self.assertEqual("unexpected.tmp", after[str(root)][0]["relative_path"])
        self.assertIn("sha256", after[str(root)][0])

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
