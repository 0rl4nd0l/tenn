#!/usr/bin/env python3
"""Focused tests for the certified no-write extraction replay runner."""

from __future__ import annotations

import argparse
import importlib.util
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "extraction_no_write_replay.py"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "extraction_no_write_replay", RUNNER_PATH
    )
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
            Path(
                "financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json"
            )
        )
        self.assertTrue(
            str(resolved).startswith(str(RUNNER.CERTIFIED_MANIFEST_ROOT.resolve()))
        )

    def test_whc_edu_mixed_unit_manifest_is_certified_docling_only(self):
        manifest_path = RUNNER.resolve_manifest_path(
            Path(
                "financial-engine_v2/data/extraction_no_write_cases/whc_edu_mixed_unit_cases_v1.json"
            )
        )
        manifest = RUNNER.load_manifest(manifest_path)
        self.assertFalse(manifest["certification"]["allow_production_writes"])
        self.assertFalse(manifest["certification"]["allow_broad_extraction"])
        self.assertTrue(manifest["certification"]["loopback_llm_only"])

        cases = manifest["cases"]
        self.assertEqual(
            ["WHC_2023_MIXED_UNIT", "EDU_2023_MIXED_UNIT"],
            [case["case_id"] for case in cases],
        )
        self.assertEqual([], RUNNER._docling_incompatible_cases(cases))
        for case in cases:
            self.assertEqual("failed", case["expected_status"])
            self.assertEqual("docling", case["parser_backend"])
            self.assertTrue(case["strict_parser"])
            self.assertTrue(case["skip_narrative"])
            self.assertEqual("mixed_unit_surface", case["source_bound_unit_family"])
            self.assertFalse(Path(case["source_path"]).is_absolute())
            self.assertTrue(case["source_path"].startswith("asx/docs/"))
            self.assertTrue(
                case["expected_error_family"].startswith("validation_gate:")
            )

    def test_llm_url_must_be_loopback(self):
        self.assertEqual(
            "http://127.0.0.1:8001",
            RUNNER.assert_loopback_url("http://127.0.0.1:8001/"),
        )
        self.assertEqual(
            "http://localhost:8001", RUNNER.assert_loopback_url("http://localhost:8001")
        )
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.assert_loopback_url("https://example.com/v1")

    def test_profile_must_be_certified(self):
        self.assertEqual(RUNNER.BASELINE_PROFILE, RUNNER.normalize_profile(""))
        self.assertEqual(
            RUNNER.DOCLING_PROFILE, RUNNER.normalize_profile(RUNNER.DOCLING_PROFILE)
        )
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.normalize_profile("ad-hoc-docling")

    def test_docling_venv_python_must_be_approved_candidate(self):
        approved = RUNNER.resolve_approved_venv_python(
            "financial-engine_v2/.venv/bin/python"
        )
        self.assertTrue(str(approved).endswith("financial-engine_v2/.venv/bin/python"))
        with self.assertRaises(RUNNER.ReplayConfigError):
            RUNNER.resolve_approved_venv_python("/tmp/random-venv/bin/python")

    def test_case_timeout_can_be_disabled_for_debug_runs(self):
        with RUNNER._case_timeout(0):
            self.assertTrue(True)

    def test_case_timeout_raises_timeout_error(self):
        with self.assertRaises(RUNNER.CaseTimeoutError):
            with RUNNER._case_timeout(1):
                time.sleep(2)

    def test_compact_payload_preserves_strong_total_debt_for_benchmark_only(self):
        result = mock.Mock(
            status="ok",
            error=None,
            payload={
                "metrics": {"revenue": 10_000_000},
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
                "field_provenance": {
                    "revenue": {
                        "source_cell": {
                            "raw_value": "10",
                            "scaled_value": 10_000_000,
                            "requested_period_end": "2025-06-30",
                        }
                    }
                },
            },
        )
        multipass = mock.Mock()
        multipass._is_strong_total_debt_evidence.return_value = True
        debug_capture = {
            "pass3a_results": [
                {
                    "_source": "balance_sheet",
                    "_page_number": 12,
                    "_scale": "millions",
                    "_scale_source": "table",
                    "total_debt": 25_000_000,
                    "row_refs": {"total_debt": "Borrowings"},
                    "_period_source_cells": {
                        "total_debt": {
                            "raw_value": "25",
                            "scaled_value": 25_000_000,
                            "requested_period_end": "2025-06-30",
                            "header_cell": "30 June 2025",
                        }
                    },
                }
            ]
        }

        payload = RUNNER._compact_payload(
            result,
            benchmark_internal_metrics=RUNNER._benchmark_internal_metrics(
                multipass, debug_capture
            ),
        )

        self.assertEqual({"revenue": 10_000_000}, payload["non_null_metrics"])
        self.assertNotIn("total_debt", payload["non_null_metrics"])
        self.assertEqual(
            "10",
            payload["benchmark_metric_source_cells"]["revenue"]["raw_value"],
        )
        self.assertEqual(
            {"total_debt": 25_000_000}, payload["benchmark_internal_metrics"]
        )
        self.assertEqual(
            "millions",
            payload["benchmark_internal_metric_source_scales"]["total_debt"],
        )
        self.assertEqual(
            "balance_sheet:page_12:Borrowings",
            payload["benchmark_internal_provenance"]["total_debt"],
        )
        self.assertEqual(
            "25",
            payload["benchmark_internal_source_cells"]["total_debt"]["raw_value"],
        )

    def test_unbound_total_debt_is_not_a_benchmark_observation(self):
        multipass = mock.Mock()
        multipass._is_strong_total_debt_evidence.return_value = True
        debug_capture = {
            "pass3a_results": [
                {
                    "_source": "balance_sheet",
                    "total_debt": 25_000_000,
                    "row_refs": {"total_debt": "Borrowings"},
                }
            ]
        }

        observations = RUNNER._benchmark_internal_metrics(multipass, debug_capture)

        self.assertEqual({}, observations["values"])

    def test_compact_payload_keeps_v1_shape_without_benchmark_internal_fields(self):
        result = mock.Mock(
            status="ok",
            error=None,
            payload={"metrics": {"revenue": 10_000_000}},
        )

        payload = RUNNER._compact_payload(result)

        self.assertEqual({"revenue": 10_000_000}, payload["non_null_metrics"])
        self.assertFalse(any(key.startswith("benchmark_internal_") for key in payload))

    def test_pass3a_failure_capture_keeps_v1_case_row_keys_unchanged(self):
        v1_row = {"case_id": "A", "result": {"status": "ok"}}
        expected_keys = set(v1_row)
        debug_capture = {"pass3a_failures": [{"table_type": "income_statement"}]}

        RUNNER._attach_pass3a_failure_capture(v1_row, debug_capture, enabled=False)

        self.assertEqual(expected_keys, set(v1_row))
        self.assertNotIn("pass3a_failures", v1_row)

        v2_row = dict(v1_row)
        RUNNER._attach_pass3a_failure_capture(v2_row, debug_capture, enabled=True)
        self.assertEqual(debug_capture["pass3a_failures"], v2_row["pass3a_failures"])

    def test_case_timeout_is_infrastructure_failure(self):
        self.assertTrue(
            RUNNER._is_infrastructure_failure(
                {
                    "result": {
                        "status": "exception",
                        "error": "CaseTimeoutError: case_timeout: exceeded 1 seconds",
                    }
                }
            )
        )

    def test_raw_transport_exceptions_are_infrastructure_failures(self):
        for error in (
            "ConnectError: All connection attempts failed",
            "TimeoutException: timed out",
            "ReadError: [Errno 104] Connection reset by peer",
            "RemoteProtocolError: Server disconnected without sending a response",
        ):
            with self.subTest(error=error):
                self.assertTrue(
                    RUNNER._is_infrastructure_failure(
                        {"result": {"status": "exception", "error": error}},
                        include_raw_transport=True,
                    )
                )

    def test_v1_raw_transport_exception_classification_remains_unchanged(self):
        row = {
            "result": {
                "status": "exception",
                "error": "ReadError: [Errno 104] Connection reset by peer",
            }
        }
        self.assertFalse(RUNNER._is_infrastructure_failure(row))

    def test_raw_non_transport_exception_is_not_infrastructure_failure(self):
        self.assertFalse(
            RUNNER._is_infrastructure_failure(
                {
                    "result": {
                        "status": "exception",
                        "error": "ValueError: timeout parsing metric payload",
                    }
                }
            )
        )

    def test_captured_pass3a_transport_and_5xx_failures_are_infrastructure(self):
        for cause in (
            {"exception_type": "ReadError", "status_code": None},
            {"exception_type": "HTTPStatusError", "status_code": 503},
            {"exception_type": "LlamaCppServerUnavailable", "status_code": None},
        ):
            with self.subTest(cause=cause):
                row = {
                    "result": {"status": "ok", "error": None},
                    "pass3a_failures": [
                        {
                            "initial_error_chain": [cause],
                            "retry_error_chain": [cause],
                        }
                    ],
                }
                self.assertTrue(
                    RUNNER._is_infrastructure_failure(row, include_raw_transport=True)
                )

    def test_captured_pass3a_quality_and_4xx_failures_are_not_infrastructure(self):
        for cause in (
            {"exception_type": "ValueError", "status_code": None},
            {"exception_type": "HTTPStatusError", "status_code": 400},
        ):
            with self.subTest(cause=cause):
                row = {
                    "result": {"status": "ok", "error": None},
                    "pass3a_failures": [
                        {
                            "initial_error_chain": [cause],
                            "retry_error_chain": [cause],
                        }
                    ],
                }
                self.assertFalse(
                    RUNNER._is_infrastructure_failure(row, include_raw_transport=True)
                )

    def test_v1_ignores_captured_pass3a_transport_metadata(self):
        row = {
            "result": {"status": "ok", "error": None},
            "pass3a_failures": [
                {
                    "initial_error_chain": [
                        {"exception_type": "ReadError", "status_code": None}
                    ]
                }
            ],
        }
        self.assertFalse(RUNNER._is_infrastructure_failure(row))

    def test_captured_pass3a_outage_survives_later_quality_exception(self):
        row = {
            "result": {
                "status": "exception",
                "error": "ValueError: post-processing failed",
            }
        }
        RUNNER._attach_pass3a_failure_capture(
            row,
            {
                "pass3a_failures": [
                    {
                        "table_type": "income_statement",
                        "initial_error_chain": [
                            {"exception_type": "ReadError", "status_code": None}
                        ],
                        "retry_error_chain": [
                            {"exception_type": "ReadError", "status_code": None}
                        ],
                    }
                ]
            },
            enabled=True,
        )

        self.assertTrue(
            RUNNER._is_infrastructure_failure(row, include_raw_transport=True)
        )
        self.assertEqual(
            "DATA_MISSING",
            RUNNER._derive_replay_status(
                {
                    "forbidden_surface_clean": True,
                    "report_only_durable_writes": True,
                    "isolated_cache_contained": True,
                    "isolated_runtime_contained": True,
                },
                llm_missing=False,
                extraction_exception_count=1,
                infrastructure_failure_count=1,
                expectation_failure_count=0,
            ),
        )

    def test_docling_profile_rejects_non_docling_manifest_cases(self):
        cases = [
            {"case_id": "HUB", "parser_backend": "docling"},
            {"case_id": "WHC", "parser_backend": "pymupdf"},
        ]
        incompatible = RUNNER._docling_incompatible_cases(cases)
        self.assertEqual(
            [{"case_id": "WHC", "parser_backend": "pymupdf"}], incompatible
        )

    def test_docling_profile_forces_strict_docling_cases(self):
        cases = [
            {"case_id": "HUB", "parser_backend": "docling", "strict_parser": False},
            {"case_id": "LBL"},
        ]
        strict_cases = RUNNER._force_docling_profile_cases(cases)
        self.assertEqual(
            ["docling", "docling"], [case["parser_backend"] for case in strict_cases]
        )
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
        self.assertTrue(
            env["MODEL_ROUTING_CONFIG"].endswith(
                "financial-engine_v2/backend/app/config/model_routing.yaml"
            )
        )

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
        report_root = (
            ROOT
            / "reports"
            / "agent_jobs"
            / "extraction_no_write_invalid_selector_test"
        )
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
        report_root = (
            ROOT / "reports" / "agent_jobs" / "extraction_no_write_invalid_llm_url_test"
        )
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

            validation = json.loads(
                (report_dir / "validation.json").read_text(encoding="utf-8")
            )
            audit = json.loads(
                (report_dir / "side_effect_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual("DATA_MISSING", validation["status"])
            self.assertEqual(RUNNER.DOCLING_PROFILE, validation["profile"])
            self.assertTrue(audit["forbidden_surface_clean"])
            self.assertFalse(any(audit["forbidden_surface_mutation"].values()))

    def test_infrastructure_failure_detects_runtime_config_failures(self):
        row = {
            "result": {
                "status": "failed",
                "error": "pass1:OLLAMA_URL must be set when provider is 'ollama'",
            }
        }
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
            item
            for item in results
            if (item.get("result") or {}).get("status") == "exception"
        ]
        infrastructure_failures = [
            item for item in results if RUNNER._is_infrastructure_failure(item)
        ]

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

    def test_surface_audit_fails_on_transient_code_identity_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = RUNNER._surface_audit(
                git_before=[],
                git_after=[],
                source_before={},
                source_after={},
                normal_cache_before={},
                normal_cache_after={},
                report_dir=root / "reports" / "agent_jobs" / "job" / "run",
                report_files=[],
                isolated_cache_root=root / "cache",
                isolated_cache_files=[],
                isolated_runtime_root=root / "runtime",
                isolated_runtime_files=[],
                code_identity_conflict="Git HEAD changed during extractor import",
            )

        self.assertFalse(audit["forbidden_surface_clean"])
        self.assertTrue(audit["forbidden_surface_mutation"]["repo_worktree_write"])
        self.assertEqual(
            "Git HEAD changed during extractor import",
            audit["code_identity_conflict"],
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
            source_dir = (
                root / "data" / "asx" / "docs" / "HUB" / "financial_performance"
            )
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

    def test_v1_manifest_behavior_remains_compatible(self):
        manifest = self.manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")

            loaded = RUNNER.load_manifest(path)

        self.assertEqual(
            "extraction_no_write_case_manifest_v1", loaded["artifact_type"]
        )
        self.assertEqual(
            ["HUB", "LBL"], [row["case_id"] for row in RUNNER.select_cases(loaded, [])]
        )

    def test_v2_receipt_is_bound_to_one_report_and_rejects_reuse(self):
        report_parent = ROOT / "reports" / "agent_jobs"
        report_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=report_parent) as directory:
            job = Path(directory)
            output = job / "output"
            receipt_path = job / "INVOCATION_RECEIPT.json"
            invocation_id = "synthetic-invocation"
            stage = job / f".output.staging-{invocation_id}"
            report_dir = stage / "replay"
            manifest_path = job / "cases.json"
            corpus_path = job / "corpus.json"
            source_root = job / "sources"
            manifest_path.write_text("{}\n", encoding="utf-8")
            corpus_path.write_text("{}\n", encoding="utf-8")
            corpus_sha = RUNNER._sha256(corpus_path)
            command = [
                sys.executable,
                "-I",
                "-B",
                "-S",
                str(RUNNER_PATH),
                "--case-manifest",
                str(manifest_path),
                "--source-contract",
                str(corpus_path),
                "--case",
                "all",
                "--report-dir",
                report_dir.relative_to(ROOT).as_posix(),
                "--invocation-receipt",
                str(receipt_path),
                "--source-root",
                str(source_root),
                "--llm-base-url",
                "http://127.0.0.1:8001",
                "--case-timeout-seconds",
                "900",
                "--profile",
                RUNNER.BASELINE_PROFILE,
                "--expected-git-head",
                "a" * 40,
            ]
            code_identity = {
                "head_sha": "a" * 40,
                "tree_sha": "b" * 40,
                "tracked_files_sha256": {
                    "scripts/extraction_no_write_replay.py": "c" * 64
                },
            }
            receipt = {
                "artifact_type": "broad_extraction_invocation_receipt_v2",
                "invocation_id": invocation_id,
                "receipt_path": str(receipt_path),
                "final_output_root": str(output),
                "staging_root": str(stage),
                "replay_report_dir": str(report_dir),
                "case_manifest_path": str(manifest_path),
                "case_manifest_sha256": RUNNER._sha256(manifest_path),
                "corpus_path": str(corpus_path),
                "corpus_sha256": corpus_sha,
                "case_count": 20,
                "interpreter": {
                    "binary_sha256": RUNNER._sha256(Path(sys.executable).resolve())
                },
                "code_identity": code_identity,
                "launch_environment": {},
                "command": command,
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            with (
                mock.patch.object(RUNNER, "V2_CORPUS_SHA256", corpus_sha),
                mock.patch.object(
                    RUNNER, "inspect_code_identity", return_value=code_identity
                ),
                mock.patch.object(RUNNER, "validate_v2_launch_environment"),
                mock.patch.object(RUNNER, "validate_v2_running_interpreter"),
            ):
                validated = RUNNER.validate_v2_invocation_receipt(
                    receipt_path,
                    manifest_path=manifest_path,
                    corpus_path=corpus_path,
                    report_dir=report_dir,
                    source_root=source_root,
                    llm_url="http://127.0.0.1:8001",
                    case_timeout_seconds=900,
                    profile=RUNNER.BASELINE_PROFILE,
                    requested_git_head="a" * 40,
                )
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "Git HEAD argument mismatch"
                ):
                    RUNNER.validate_v2_invocation_receipt(
                        receipt_path,
                        manifest_path=manifest_path,
                        corpus_path=corpus_path,
                        report_dir=report_dir,
                        source_root=source_root,
                        llm_url="http://127.0.0.1:8001",
                        case_timeout_seconds=900,
                        profile=RUNNER.BASELINE_PROFILE,
                        requested_git_head="d" * 40,
                    )
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "command binding mismatch"
                ):
                    RUNNER.validate_v2_invocation_receipt(
                        receipt_path,
                        manifest_path=manifest_path,
                        corpus_path=corpus_path,
                        report_dir=report_dir,
                        source_root=source_root,
                        llm_url="http://127.0.0.1:8001",
                        case_timeout_seconds=900,
                        profile=RUNNER.DOCLING_PROFILE,
                    )
                receipt["command"][0] = "/usr/bin/not-the-current-python"
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "command binding mismatch"
                ):
                    RUNNER.validate_v2_invocation_receipt(
                        receipt_path,
                        manifest_path=manifest_path,
                        corpus_path=corpus_path,
                        report_dir=report_dir,
                        source_root=source_root,
                        llm_url="http://127.0.0.1:8001",
                        case_timeout_seconds=900,
                        profile=RUNNER.BASELINE_PROFILE,
                    )
                receipt["command"][0] = sys.executable
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "path binding mismatch"
                ):
                    RUNNER.validate_v2_invocation_receipt(
                        receipt_path,
                        manifest_path=manifest_path,
                        corpus_path=corpus_path,
                        report_dir=job / "different-replay",
                        source_root=source_root,
                        llm_url="http://127.0.0.1:8001",
                        case_timeout_seconds=900,
                        profile=RUNNER.BASELINE_PROFILE,
                    )

                report_dir.mkdir(parents=True)
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "staging root already exists"
                ):
                    RUNNER.validate_v2_invocation_receipt(
                        receipt_path,
                        manifest_path=manifest_path,
                        corpus_path=corpus_path,
                        report_dir=report_dir,
                        source_root=source_root,
                        llm_url="http://127.0.0.1:8001",
                        case_timeout_seconds=900,
                        profile=RUNNER.BASELINE_PROFILE,
                    )

                output.mkdir()
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "final output already exists"
                ):
                    RUNNER.validate_v2_invocation_receipt(
                        receipt_path,
                        manifest_path=manifest_path,
                        corpus_path=corpus_path,
                        report_dir=report_dir,
                        source_root=source_root,
                        llm_url="http://127.0.0.1:8001",
                        case_timeout_seconds=900,
                        profile=RUNNER.BASELINE_PROFILE,
                    )

            self.assertEqual(invocation_id, validated["invocation_id"])

    def test_v2_launch_environment_rejects_unbound_startup_code(self):
        bound = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        }
        with mock.patch.dict(os.environ, bound, clear=True):
            RUNNER.validate_v2_launch_environment(bound)
            os.environ["PYTHONPATH"] = "/tmp/unbound-code"
            with self.assertRaisesRegex(
                RUNNER.ReplayConfigError, "launch environment mismatch"
            ):
                RUNNER.validate_v2_launch_environment(bound)

    def test_v2_running_interpreter_revalidates_binary_and_dependencies(self):
        versions = dict(RUNNER.V2_EXPECTED_DEPENDENCY_VERSIONS)
        snapshot_sha = hashlib.sha256(
            json.dumps(versions, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        binding = {
            "binary_sha256": "a" * 64,
            "versions": versions,
            "dependency_snapshot_sha256": snapshot_sha,
            "site_packages": [str(Path(sys.executable).resolve().parent)],
        }
        with (
            mock.patch.object(RUNNER, "_sha256", return_value="a" * 64),
            mock.patch.object(
                RUNNER.importlib.metadata,
                "version",
                side_effect=lambda name: versions[name],
            ),
            mock.patch.object(RUNNER.sys, "path", list(RUNNER.sys.path)),
        ):
            RUNNER.validate_v2_running_interpreter(binding)
            binding["binary_sha256"] = "b" * 64
            with self.assertRaisesRegex(
                RUNNER.ReplayConfigError, "running interpreter SHA-256 mismatch"
            ):
                RUNNER.validate_v2_running_interpreter(binding)

    def test_v2_code_identity_revalidation_rejects_clean_head_switch(self):
        binding = {
            "head_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "tracked_files_sha256": {"file.py": "c" * 64},
        }
        with mock.patch.object(
            RUNNER,
            "inspect_code_identity",
            return_value=binding | {"head_sha": "d" * 40},
        ):
            with self.assertRaisesRegex(
                RUNNER.CodeIdentityConflict, "code identity mismatch"
            ):
                RUNNER.require_v2_code_identity(binding)

    def test_initial_code_identity_conflict_has_distinct_exit_code(self):
        with (
            mock.patch.object(RUNNER, "parse_args", return_value=mock.Mock()),
            mock.patch.object(
                RUNNER,
                "run_replay",
                side_effect=RUNNER.CodeIdentityConflict("changed before child"),
            ),
        ):
            self.assertEqual(RUNNER.CODE_IDENTITY_CONFLICT_EXIT_CODE, RUNNER.main())

    def test_v2_manifest_accepts_only_exact_complete_direct_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            source_root = root / "source"
            corpus_path = repo.joinpath(*RUNNER.V2_CORPUS_REPO_PATH.parts)
            corpus_path.parent.mkdir(parents=True)
            cases = []
            documents = []
            for index in range(20):
                ticker = f"T{index:02d}"
                document_id = f"doc_{index:02d}"
                relative = f"asx/docs/{ticker}/report.pdf"
                source = source_root / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(f"source-{index}".encode())
                cases.append(
                    {
                        "case_id": f"CASE_{index:02d}",
                        "ticker": ticker,
                        "document_id": document_id,
                        "title": ticker,
                        "source_path": relative,
                    }
                )
                documents.append(
                    {
                        "document_id": document_id,
                        "issuer_id": ticker,
                        "admission_status": "admitted",
                        "source_path": relative,
                        "source_sha256": RUNNER._sha256(source),
                    }
                )
            corpus = {
                "artifact_type": "broad_extraction_benchmark_corpus_v2",
                "documents": documents,
            }
            manifest = {
                "artifact_type": RUNNER.V2_MANIFEST_ARTIFACT_TYPE,
                "certification": {
                    "allow_production_writes": False,
                    "loopback_llm_only": True,
                    "source_contract": RUNNER.V2_CORPUS_REPO_PATH.as_posix(),
                },
                "cases": cases,
            }
            corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
            manifest_path = root / "cases.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with (
                mock.patch.object(
                    RUNNER, "V2_CORPUS_SHA256", RUNNER._sha256(corpus_path)
                ),
                mock.patch.object(
                    RUNNER, "V2_MANIFEST_SHA256", RUNNER._sha256(manifest_path)
                ),
            ):
                contract = RUNNER._validate_v2_manifest_contract(
                    manifest_path, manifest, repo_root=repo
                )
                resolved = RUNNER.resolve_v2_case_source_paths(
                    manifest_path,
                    manifest,
                    source_root=source_root,
                    repo_root=repo,
                )
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "complete 20-case"
                ):
                    RUNNER.select_cases(manifest, ["CASE_00"])

                (source_root / cases[0]["source_path"]).write_bytes(b"changed")
                with self.assertRaisesRegex(
                    RUNNER.ReplayConfigError, "source SHA-256 mismatch"
                ):
                    RUNNER.resolve_v2_case_source_paths(
                        manifest_path,
                        manifest,
                        source_root=source_root,
                        repo_root=repo,
                    )

            self.assertEqual(20, len(contract["document_by_id"]))
            self.assertEqual(20, len(resolved))
            self.assertNotIn("source_path_candidates", resolved[0])

    def test_v2_execution_uses_hash_verified_isolated_source_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "shared" / "report.pdf"
            source.parent.mkdir()
            source.write_bytes(b"frozen-source-bytes")
            cases = [
                {
                    "case_id": "CASE_00",
                    "document_id": "doc_00",
                    "source_path": str(source),
                    "source_path_declared": "asx/docs/T00/report.pdf",
                    "source_sha256": RUNNER._sha256(source),
                }
            ]

            isolated = RUNNER._materialize_v2_execution_sources(
                cases, root / "isolated"
            )
            isolated_source = Path(isolated[0]["source_path"])
            source.write_bytes(b"replacement-bytes")

            self.assertEqual(b"frozen-source-bytes", isolated_source.read_bytes())
            self.assertEqual(cases[0]["source_sha256"], RUNNER._sha256(isolated_source))
            self.assertEqual(str(source), isolated[0]["source_path_original"])
            self.assertEqual(
                "asx/docs/T00/report.pdf", isolated[0]["source_path_declared"]
            )

            bad_case = dict(cases[0], source_sha256="0" * 64)
            with self.assertRaisesRegex(
                RUNNER.ReplayConfigError, "isolated source SHA-256 mismatch"
            ):
                RUNNER._materialize_v2_execution_sources(
                    [bad_case], root / "isolated-bad"
                )


if __name__ == "__main__":
    unittest.main()
