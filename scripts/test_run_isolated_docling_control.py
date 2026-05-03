import importlib.util
import sys
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_isolated_docling_control.py"

spec = importlib.util.spec_from_file_location(
    "run_isolated_docling_control", str(SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _doc(doc_id: str, *, runtime_id: str = "http://127.0.0.1:8002") -> dict:
    return {
        "document_id": doc_id,
        "extraction_error": None,
        "method_provenance": {
            "requested_method": "docling",
            "strict_method": True,
            "actual_method": "docling_gpu",
            "fallback_used": False,
            "runtime_id": runtime_id,
        },
        "metric_results": {
            "revenue": {"status": "correct"},
            "operating_cash_flow": {"status": "correct"},
            "net_debt": {"status": "correct"},
        },
    }


class RunIsolatedDoclingControlTests(unittest.TestCase):
    def test_canonical_10_acceptance_passes_full_gate(self):
        payload = {
            "runtime": {"endpoint": "http://127.0.0.1:8002"},
            "isolation": {"shared_runtime_avoided": True},
            "control": {
                "doc_ids": list(mod.CANONICAL_10_DOC_IDS),
                "cache_hit": False,
                "summary": {
                    "total_documents": 10,
                    "failed_documents": 0,
                    "context_correct_documents": 10,
                    "total_metric_checks": 24,
                    "metric_status_counts": {
                        "correct": 24,
                        "wrong": 0,
                        "missing": 0,
                        "abstain": 0,
                    },
                    "trust_distribution": {"trusted": 10},
                    "trust_matches_expected": 10,
                },
                "documents": [_doc(doc_id) for doc_id in mod.CANONICAL_10_DOC_IDS],
            },
        }

        acceptance = mod._derive_acceptance(payload)

        self.assertTrue(acceptance["passed"])
        self.assertEqual(acceptance["acceptance_profile"], "canonical10")
        self.assertTrue(acceptance["metric_gate_passed"])

    def test_strict_4_acceptance_preserves_smoke_gate(self):
        payload = {
            "runtime": {"endpoint": "http://127.0.0.1:8002"},
            "isolation": {"shared_runtime_avoided": True},
            "control": {
                "doc_ids": list(mod.DEFAULT_DOC_IDS),
                "cache_hit": False,
                "summary": {
                    "total_documents": 4,
                    "failed_documents": 0,
                    "context_correct_documents": 4,
                    "total_metric_checks": 10,
                    "metric_status_counts": {
                        "correct": 10,
                        "wrong": 0,
                        "missing": 0,
                        "abstain": 0,
                    },
                    "trust_distribution": {"trusted": 4},
                    "trust_matches_expected": 4,
                },
                "documents": [_doc(doc_id) for doc_id in mod.DEFAULT_DOC_IDS],
            },
        }

        acceptance = mod._derive_acceptance(payload)

        self.assertTrue(acceptance["passed"])
        self.assertEqual(acceptance["acceptance_profile"], "strict4")

    def test_disable_prompt_cache_sets_llamacpp_env_knobs(self):
        args = Namespace(
            model_path="/tmp/model.gguf",
            model_alias="qwen",
            ctx_size=16384,
            api_key="local-openai-key",
            disable_prompt_cache=True,
        )

        env = mod._runtime_launch_env(args, "http://127.0.0.1:8002")

        self.assertEqual(env["LLAMA_ARG_CACHE_RAM"], "0")
        self.assertEqual(env["LLAMA_ARG_CACHE_PROMPT"], "false")

    def test_cmdline_redaction_removes_api_key_value(self):
        redacted = mod._redact_cmdline("llama-server --api-key secret --port 8002")

        self.assertEqual(redacted, "llama-server --api-key <redacted> --port 8002")

        redacted_inline = mod._redact_cmdline("llama-server --api-key=secret --port 8002")

        self.assertEqual(redacted_inline, "llama-server --api-key=<redacted> --port 8002")


if __name__ == "__main__":
    unittest.main()
