import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_real_extraction_eval.py"

spec = importlib.util.spec_from_file_location(
    "run_real_extraction_eval", str(SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class _FakeHttpError(mod.urlerror.HTTPError):
    def __init__(self, code: int, payload: dict):
        super().__init__(
            url="http://127.0.0.1:8000/api/extraction-eval/real-gold",
            code=code,
            msg="error",
            hdrs=None,
            fp=None,
        )
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _sample_eval_response() -> dict:
    return {
        "dataset_dir": str(mod.DEFAULT_DATASET_DIR),
        "requested_method": "docling",
        "strict_method": False,
        "eval_policy": {
            "policy_version": "2026-04-20",
            "mode": "non_canonical",
            "kpi_eligible": False,
            "non_canonical_reasons": [
                "strict_method:expected=True,actual=False",
            ],
            "canonical_contract": {
                "dataset_dir": str(mod.DEFAULT_DATASET_DIR.resolve()),
                "method": "docling",
                "strict_method": True,
                "limit": 0,
                "tolerance": 0.01,
                "prompt_variant_id": None,
                "model_override": None,
            },
            "actual_run": {
                "dataset_dir": str(mod.DEFAULT_DATASET_DIR.resolve()),
                "method": "docling",
                "strict_method": False,
                "limit": 1,
                "tolerance": 0.01,
                "prompt_variant_id": None,
                "model_override": None,
            },
        },
        "fixture_manifest": {
            "dataset_dir": str(mod.DEFAULT_DATASET_DIR.resolve()),
            "fixture_file_count": 10,
            "fixture_content_sha256": "abc123",
            "fixture_git_commit": "deadbeef",
            "fixture_git_dirty": False,
        },
        "summary": {
            "generated_at": "2026-04-14T00:00:00Z",
            "total_documents": 1,
            "failed_documents": 1,
            "context_correct_documents": 1,
            "context_mismatch_documents": 0,
            "context_mismatch_fields": 0,
            "context_accuracy": 1.0,
            "total_metric_checks": 1,
            "metric_status_counts": {
                "correct": 0,
                "wrong": 0,
                "missing": 1,
                "abstain": 0,
            },
            "correct_count": 0,
            "wrong_count": 0,
            "missing_count": 1,
            "abstained_count": 0,
            "total_accuracy": 0.0,
            "trust_distribution": {
                "trusted": 0,
                "abstain": 1,
                "quarantine": 0,
            },
            "trust_matches_expected": 1,
            "trust_mismatches_expected": 0,
            "trust_trigger_counts": {"net_debt:missing": 1},
            "per_metric_failure_counts": {
                "revenue": {"wrong": 0, "missing": 0, "abstain": 0},
                "operating_cash_flow": {"wrong": 0, "missing": 0, "abstain": 0},
                "net_debt": {"wrong": 0, "missing": 1, "abstain": 0},
            },
        },
        "documents": [
            {
                "document_id": "doc_a",
                "source_file": "financial-engine_v2/data/extraction_gold_real/doc_a.pdf",
                "source_path": "/tmp/doc_a.pdf",
                "source_basename": "doc_a.pdf",
                "ticker": "QBE",
                "period_type": "H",
                "period_end": "2025-06-30",
                "expected_trust": "abstain",
                "extraction_status": "ok",
                "extraction_error": None,
                "context_correct": True,
                "context_expected": {
                    "period_type": "H",
                    "period_end": "2025-06-30",
                    "currency": "AUD",
                    "scale": "millions",
                },
                "context_actual": {
                    "period_type": "H",
                    "period_end": "2025-06-30",
                    "currency": "AUD",
                    "scale": "millions",
                },
                "context_mismatches": [],
                "metric_results": {
                    "net_debt": {
                        "status": "missing",
                        "expected": 123.0,
                        "actual": None,
                        "reason": "extractor returned null for required metric",
                        "source_metric_key": "net_debt",
                    }
                },
                "metric_status_counts": {
                    "correct": 0,
                    "wrong": 0,
                    "missing": 1,
                    "abstain": 0,
                },
                "correct_metric_count": 0,
                "wrong_metric_count": 0,
                "missing_metric_count": 1,
                "abstained_metric_count": 0,
                "failed_metric_count": 1,
                "trust_outcome": "abstain",
                "trust_triggers": ["net_debt:missing"],
                "trust_matches_expected": True,
                "mismatch_reasons": [
                    "metric:net_debt:extractor returned null for required metric"
                ],
                "method_provenance": {
                    "requested_method": "docling",
                    "actual_method": "docling",
                    "strict_method": False,
                },
            }
        ],
    }


def _development_aggregate() -> dict:
    return {
        "corpus_version": "opaque-v1",
        "corpus_digest": "a" * 64,
        "document_count": 48,
        "partition_counts": {"diagnostic": 12, "holdout": 36},
        "bucket_counts": {
            "annual": 8,
            "4E": 8,
            "half-year": 8,
            "4D": 8,
            "quarterly": 8,
            "4C": 8,
        },
        "company_count": 12,
        "sector_count": 6,
        "scan_image_heavy_count": 6,
        "non_aud_count": 1,
        "issuer_size_counts": {"large": 24, "small": 24},
    }


class TestBackendRequestHelpers(unittest.TestCase):
    def test_development_artifacts_are_aggregate_only_in_every_format(self):
        aggregate = _development_aggregate()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = Path(tmpdir) / "results.json"
            report = Path(tmpdir) / "report.md"
            mod._write_development_artifacts(
                aggregate,
                results_json=results,
                report_path=report,
            )
            paths = mod._artifact_paths(results, report)
            for key in ("results_json", "summary_json", "canonical_scorecard_json"):
                self.assertEqual(
                    json.loads(paths[key].read_text(encoding="utf-8")),
                    aggregate,
                )
            combined = "\n".join(
                path.read_text(encoding="utf-8")
                for path in paths.values()
                if path.exists()
            )
            for secret in ("document_id", "ticker", "expected", "actual", "secret.pdf"):
                self.assertNotIn(secret, combined)

    def test_resolve_backend_api_key_prefers_arg_then_settings_then_env(self):
        with mock.patch.object(
            mod, "settings", SimpleNamespace(local_api_key="settings-key")
        ):
            with mock.patch.dict(
                mod.os.environ,
                {"LOCAL_API_KEY": "env-key", "BACKEND_API_KEY": "other-env-key"},
                clear=True,
            ):
                self.assertEqual(mod._resolve_backend_api_key("cli-key"), "cli-key")
                self.assertEqual(mod._resolve_backend_api_key(None), "settings-key")

    def test_request_real_gold_job_schedules_and_polls_until_completed(self):
        captured: list[dict] = []
        sample = _sample_eval_response()
        responses = [
            _FakeResponse({"task_id": "task-abc", "status": "pending"}),
            _FakeResponse(
                {
                    "task_id": "task-abc",
                    "status": "running",
                    "result": None,
                    "error": None,
                }
            ),
            _FakeResponse(
                {
                    "task_id": "task-abc",
                    "status": "completed",
                    "result": sample,
                    "error": None,
                }
            ),
        ]

        def fake_urlopen(request, timeout):
            captured.append({"request": request, "timeout": timeout})
            return responses[len(captured) - 1]

        runner = getattr(mod, "_request_real_gold_" + "eval")
        with mock.patch.object(mod.urlrequest, "urlopen", side_effect=fake_urlopen):
            with mock.patch.object(mod.time, "sleep", return_value=None):
                payload = runner(
                    backend_url="http://127.0.0.1:8000",
                    api_key="secret",
                    limit=2,
                    tolerance=0.05,
                    method="docling",
                    strict_method=True,
                    timeout_seconds=90.0,
                    poll_interval_seconds=0.0,
                )

        self.assertEqual(payload["requested_method"], "docling")
        self.assertEqual(len(captured), 3)

        schedule_request = captured[0]["request"]
        self.assertEqual(
            schedule_request.full_url,
            "http://127.0.0.1:8000/api/extraction-eval/real-gold?background=true",
        )
        self.assertEqual(schedule_request.get_method(), "POST")
        self.assertEqual(schedule_request.headers["X-api-key"], "secret")
        self.assertEqual(
            json.loads(schedule_request.data.decode("utf-8")),
            {
                "limit": 2,
                "tolerance": 0.05,
                "method": "docling",
                "strict_method": True,
                "corpus_classification": "non_holdout",
                "access_mode": "development",
            },
        )
        self.assertEqual(captured[0]["timeout"], 60.0)

        poll_request = captured[1]["request"]
        self.assertEqual(
            poll_request.full_url,
            "http://127.0.0.1:8000/api/extraction-eval/real-gold/tasks/task-abc",
        )
        self.assertEqual(poll_request.get_method(), "GET")
        self.assertIsNone(poll_request.data)

    def test_request_real_gold_job_accepts_aggregate_only_holdout_result(self):
        aggregate = _development_aggregate()
        responses = [
            _FakeResponse({"task_id": "task-holdout", "status": "pending"}),
            _FakeResponse(
                {
                    "task_id": "task-holdout",
                    "status": "completed",
                    "result": aggregate,
                    "error": None,
                }
            ),
        ]
        response_index = {"value": 0}

        def fake_urlopen(request, timeout):
            response = responses[response_index["value"]]
            response_index["value"] += 1
            return response

        runner = getattr(mod, "_request_real_gold_" + "eval")
        with mock.patch.object(mod.urlrequest, "urlopen", side_effect=fake_urlopen):
            payload = runner(
                backend_url="http://127.0.0.1:8000",
                api_key=None,
                limit=0,
                tolerance=0.01,
                method="auto",
                strict_method=False,
                timeout_seconds=10.0,
                poll_interval_seconds=0.0,
                corpus_classification="holdout",
                access_mode=None,
                development_aggregate=aggregate,
            )

        self.assertEqual(payload, aggregate)

    def test_request_real_gold_job_surfaces_backend_detail(self):
        runner = getattr(mod, "_request_real_gold_" + "eval")
        with mock.patch.object(
            mod.urlrequest,
            "urlopen",
            side_effect=_FakeHttpError(500, {"detail": "real gold job failed: boom"}),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "backend real-gold job failed \\(HTTP 500\\): real gold job failed: boom",
            ):
                runner(
                    backend_url="http://127.0.0.1:8000",
                    api_key=None,
                    limit=0,
                    tolerance=0.01,
                    method="auto",
                    strict_method=False,
                    timeout_seconds=10.0,
                    poll_interval_seconds=0.0,
                )

    def test_request_real_gold_job_raises_when_task_reports_failed(self):
        responses = [
            _FakeResponse({"task_id": "task-xyz", "status": "pending"}),
            _FakeResponse(
                {
                    "task_id": "task-xyz",
                    "status": "failed",
                    "result": None,
                    "error": "RuntimeError: docling crashed",
                }
            ),
        ]
        idx = {"i": 0}

        def fake_urlopen(request, timeout):
            resp = responses[idx["i"]]
            idx["i"] += 1
            return resp

        runner = getattr(mod, "_request_real_gold_" + "eval")
        with mock.patch.object(mod.urlrequest, "urlopen", side_effect=fake_urlopen):
            with mock.patch.object(mod.time, "sleep", return_value=None):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "backend real-gold job failed: RuntimeError: docling crashed",
                ):
                    runner(
                        backend_url="http://127.0.0.1:8000",
                        api_key=None,
                        limit=0,
                        tolerance=0.01,
                        method="auto",
                        strict_method=False,
                        timeout_seconds=10.0,
                        poll_interval_seconds=0.0,
                    )

    def test_request_real_gold_job_raises_on_polling_deadline(self):
        pending = _FakeResponse({"task_id": "task-slow", "status": "pending"})

        def fake_urlopen(request, timeout):
            return pending

        clock = iter([0.0, 0.0, 0.5, 999.0])
        runner = getattr(mod, "_request_real_gold_" + "eval")

        with mock.patch.object(mod.urlrequest, "urlopen", side_effect=fake_urlopen):
            with mock.patch.object(mod.time, "sleep", return_value=None):
                with mock.patch.object(
                    mod.time, "monotonic", side_effect=lambda: next(clock)
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        r"backend real-gold job timed out after 1s "
                        r"\(task_id=task-slow, last_status=pending\)",
                    ):
                        runner(
                            backend_url="http://127.0.0.1:8000",
                            api_key=None,
                            limit=0,
                            tolerance=0.01,
                            method="auto",
                            strict_method=False,
                            timeout_seconds=1.0,
                            poll_interval_seconds=0.0,
                        )


class TestEvalArtifacts(unittest.TestCase):
    def test_artifact_paths_are_stable(self):
        results_json = Path("/tmp/extraction_real_eval_results.json")
        report_path = Path("/tmp/extraction_real_eval_summary.md")

        artifact_paths = mod._artifact_paths(results_json, report_path)

        self.assertEqual(
            artifact_paths["summary_json"],
            Path("/tmp/extraction_real_eval_results_summary.json"),
        )
        self.assertEqual(
            artifact_paths["canonical_scorecard_json"],
            Path("/tmp/extraction_real_eval_results_canonical_scorecard.json"),
        )
        self.assertEqual(
            artifact_paths["documents_csv"],
            Path("/tmp/extraction_real_eval_results_documents.csv"),
        )
        self.assertEqual(
            artifact_paths["metrics_csv"],
            Path("/tmp/extraction_real_eval_results_metrics.csv"),
        )
        self.assertEqual(
            artifact_paths["trust_triggers_csv"],
            Path("/tmp/extraction_real_eval_results_trust_triggers.csv"),
        )

    def test_write_csv_emits_header_and_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "rows.csv"
            mod._write_csv(
                path,
                [
                    {"document_id": "doc_a", "failed_metric_count": 2},
                    {"document_id": "doc_b", "failed_metric_count": 0},
                ],
            )

            contents = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(contents[0], "document_id,failed_metric_count")
            self.assertIn("doc_a,2", contents[1:])
            self.assertIn("doc_b,0", contents[1:])

    def test_apply_fixture_provenance_guard_demotes_kpi(self):
        eval_policy = {
            "policy_version": "2026-04-20",
            "mode": "canonical",
            "kpi_eligible": True,
            "non_canonical_reasons": [],
            "canonical_contract": {},
            "actual_run": {},
        }
        fixture_manifest = {
            "fixture_git_commit": None,
            "fixture_git_dirty": None,
        }

        guarded = mod._apply_fixture_provenance_guard(eval_policy, fixture_manifest)

        self.assertEqual(guarded["mode"], "non_canonical")
        self.assertFalse(guarded["kpi_eligible"])
        self.assertIn(
            "fixture_provenance:fixture_git_commit_missing",
            guarded["non_canonical_reasons"],
        )
        self.assertIn(
            "fixture_provenance:fixture_git_dirty_not_false:None",
            guarded["non_canonical_reasons"],
        )

    def test_main_persists_backend_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "extraction_real_eval_summary.md"
            results_json = Path(tmpdir) / "extraction_real_eval_results.json"
            args = Namespace(
                dataset_dir=mod.DEFAULT_DATASET_DIR,
                report_path=report_path,
                results_json=results_json,
                limit=1,
                tolerance=0.01,
                extractor_label="backend_real_gold_eval",
                provider_label="backend_api",
                method_label="/api/extraction-eval/real-gold",
                model_label=None,
                config_label=None,
                parser_backend="docling",
                strict_method=False,
                backend_url="http://127.0.0.1:8000",
                api_key=None,
                timeout_seconds=60.0,
            )

            with mock.patch.object(mod, "_parse_args", return_value=args):
                with mock.patch.object(
                    mod,
                    "_request_real_gold_eval",
                    return_value=_sample_eval_response(),
                ):
                    exit_code = mod.main()
            self.assertEqual(exit_code, 0)
            persisted = json.loads(results_json.read_text(encoding="utf-8"))
            self.assertEqual(persisted["requested_method"], "docling")
            self.assertEqual(persisted["summary"]["failed_documents"], 1)
            self.assertEqual(persisted["documents"][0]["ticker"], "QBE")
            self.assertEqual(persisted["eval_policy"]["mode"], "non_canonical")
            self.assertFalse(persisted["eval_policy"]["kpi_eligible"])
            self.assertEqual(
                persisted["run_metadata"]["eval_mode"],
                "non_canonical",
            )
            self.assertFalse(persisted["run_metadata"]["kpi_eligible"])

            summary_json = results_json.with_name(
                "extraction_real_eval_results_summary.json"
            )
            canonical_scorecard_json = results_json.with_name(
                "extraction_real_eval_results_canonical_scorecard.json"
            )
            metrics_csv = results_json.with_name(
                "extraction_real_eval_results_metrics.csv"
            )
            documents_csv = results_json.with_name(
                "extraction_real_eval_results_documents.csv"
            )
            trust_triggers_csv = results_json.with_name(
                "extraction_real_eval_results_trust_triggers.csv"
            )

            self.assertTrue(summary_json.exists())
            self.assertTrue(canonical_scorecard_json.exists())
            self.assertTrue(metrics_csv.exists())
            self.assertTrue(documents_csv.exists())
            self.assertTrue(trust_triggers_csv.exists())
            scorecard = json.loads(canonical_scorecard_json.read_text(encoding="utf-8"))
            self.assertFalse(scorecard["kpi_eligible"])
            self.assertIsNone(scorecard["canonical_kpi_summary"])
            self.assertIsNotNone(scorecard["exploratory_summary"])
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("# Extraction Real Eval Summary", report_text)
            self.assertIn("net_debt:missing", report_text)
            self.assertIn("KPI eligible: no", report_text)


if __name__ == "__main__":
    unittest.main()
