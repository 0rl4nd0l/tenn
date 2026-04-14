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


class TestBackendRequestHelpers(unittest.TestCase):
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

    def test_request_real_gold_eval_posts_expected_body_and_header(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeResponse(_sample_eval_response())

        with mock.patch.object(mod.urlrequest, "urlopen", side_effect=fake_urlopen):
            payload = mod._request_real_gold_eval(
                backend_url="http://127.0.0.1:8000",
                api_key="secret",
                limit=2,
                tolerance=0.05,
                method="docling",
                strict_method=True,
                timeout_seconds=90.0,
            )

        self.assertEqual(payload["requested_method"], "docling")
        self.assertEqual(captured["timeout"], 90.0)
        self.assertEqual(
            captured["request"].full_url,
            "http://127.0.0.1:8000/api/extraction-eval/real-gold",
        )
        self.assertEqual(captured["request"].headers["X-api-key"], "secret")
        self.assertEqual(
            json.loads(captured["request"].data.decode("utf-8")),
            {
                "limit": 2,
                "tolerance": 0.05,
                "method": "docling",
                "strict_method": True,
            },
        )

    def test_request_real_gold_eval_surfaces_backend_detail(self):
        with mock.patch.object(
            mod.urlrequest,
            "urlopen",
            side_effect=_FakeHttpError(500, {"detail": "real gold eval failed: boom"}),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "backend real-gold eval failed \\(HTTP 500\\): real gold eval failed: boom",
            ):
                mod._request_real_gold_eval(
                    backend_url="http://127.0.0.1:8000",
                    api_key=None,
                    limit=0,
                    tolerance=0.01,
                    method="auto",
                    strict_method=False,
                    timeout_seconds=10.0,
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

            summary_json = results_json.with_name(
                "extraction_real_eval_results_summary.json"
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
            self.assertTrue(metrics_csv.exists())
            self.assertTrue(documents_csv.exists())
            self.assertTrue(trust_triggers_csv.exists())
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("# Extraction Real Eval Summary", report_text)
            self.assertIn("net_debt:missing", report_text)


if __name__ == "__main__":
    unittest.main()
