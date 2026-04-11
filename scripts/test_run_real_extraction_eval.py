import importlib.util
import os
import sys
import tempfile
import unittest
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


class TestPersistLocalLlmApiKey(unittest.TestCase):
    def test_preserves_existing_llm_api_key(self):
        with mock.patch.dict(os.environ, {"LLM_API_KEY": "configured-key"}, clear=True):
            with mock.patch.object(mod, "_discover_local_llamacpp_api_key") as detect:
                self.assertEqual(mod._persist_local_llm_api_key(), "configured-key")
                self.assertEqual(os.environ["LLM_API_KEY"], "configured-key")
                detect.assert_not_called()

    def test_ignores_openai_api_key_and_uses_detected_local_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}, clear=True):
            with mock.patch.object(
                mod,
                "_discover_local_llamacpp_api_key",
                return_value="detected-key",
            ) as detect:
                self.assertEqual(mod._persist_local_llm_api_key(), "detected-key")
                self.assertEqual(os.environ["LLM_API_KEY"], "detected-key")
                detect.assert_called_once_with()

    def test_ignores_openai_api_key_and_falls_back_to_default_local_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}, clear=True):
            with mock.patch.object(
                mod, "_discover_local_llamacpp_api_key", return_value=""
            ):
                self.assertEqual(
                    mod._persist_local_llm_api_key(),
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )
                self.assertEqual(
                    os.environ["LLM_API_KEY"],
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )

    def test_uses_detected_local_llama_server_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                mod,
                "_discover_local_llamacpp_api_key",
                return_value="detected-key",
            ):
                self.assertEqual(mod._persist_local_llm_api_key(), "detected-key")
                self.assertEqual(os.environ["LLM_API_KEY"], "detected-key")

    def test_falls_back_to_default_local_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                mod, "_discover_local_llamacpp_api_key", return_value=""
            ):
                self.assertEqual(
                    mod._persist_local_llm_api_key(),
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )
                self.assertEqual(
                    os.environ["LLM_API_KEY"],
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )


class TestDiscoverLocalLlamaCppApiKey(unittest.TestCase):
    def test_parses_api_key_from_llama_server_process(self):
        proc = SimpleNamespace(
            stdout=(
                "user 123 0.0 0.0 llama-server --host 0.0.0.0 --port 8001 "
                "--api-key local-openai-key --parallel 1\n"
            )
        )
        with mock.patch.object(mod.subprocess, "run", return_value=proc):
            self.assertEqual(mod._discover_local_llamacpp_api_key(), "local-openai-key")

    def test_returns_empty_string_when_process_scan_fails(self):
        with mock.patch.object(mod.subprocess, "run", side_effect=TimeoutError):
            self.assertEqual(mod._discover_local_llamacpp_api_key(), "")


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

    def test_summarize_includes_failure_and_trigger_counts(self):
        summary = mod._summarize(
            [
                {
                    "trust_outcome": "abstain",
                    "context_correct": True,
                    "trust_matches_expected": False,
                    "trust_triggers": ["net_debt:missing"],
                    "context_mismatches": [],
                    "failed_metric_count": 1,
                    "metric_results": {
                        "net_debt": {"status": "missing"},
                        "revenue": {"status": "correct"},
                    },
                },
                {
                    "trust_outcome": "quarantine",
                    "context_correct": False,
                    "trust_matches_expected": True,
                    "trust_triggers": ["context_mismatch"],
                    "context_mismatches": ["currency"],
                    "failed_metric_count": 0,
                    "metric_results": {
                        "operating_cash_flow": {"status": "correct"},
                    },
                },
            ]
        )

        self.assertEqual(summary["failed_documents"], 2)
        self.assertEqual(summary["context_mismatch_documents"], 1)
        self.assertEqual(summary["context_mismatch_fields"], 1)
        self.assertEqual(summary["trust_distribution"]["abstain"], 1)
        self.assertEqual(summary["trust_distribution"]["quarantine"], 1)
        self.assertEqual(summary["missing_count"], 1)
        self.assertEqual(summary["correct_count"], 2)
        self.assertEqual(summary["trust_matches_expected"], 1)
        self.assertEqual(summary["trust_mismatches_expected"], 1)
        self.assertEqual(summary["trust_trigger_counts"]["context_mismatch"], 1)
        self.assertEqual(summary["trust_trigger_counts"]["net_debt:missing"], 1)

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


if __name__ == "__main__":
    unittest.main()
