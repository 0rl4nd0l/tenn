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
            server_parallel=2,
            api_key="local-openai-key",
            disable_prompt_cache=True,
        )

        env = mod._runtime_launch_env(args, "http://127.0.0.1:8002")

        self.assertEqual(env["LLAMA_ARG_CACHE_RAM"], "0")
        self.assertEqual(env["LLAMA_ARG_CACHE_PROMPT"], "false")
        self.assertEqual(env["EXTRACTION_SERVER_PARALLEL"], "2")

    def test_runtime_parallel_parser_handles_split_and_equals_forms(self):
        status = {
            "cmdlines": {
                "1": "llama-server --port 8002 --parallel 2",
                "2": "llama-server --port 8002 --parallel=2",
            }
        }

        self.assertEqual(mod._server_parallel_values(status), {"1": 2, "2": 2})
        self.assertTrue(mod._runtime_has_server_parallel(status, 2))
        self.assertFalse(mod._runtime_has_server_parallel(status, 1))

    def test_pids_for_port_ignores_non_llama_processes(self):
        original_run = mod._run
        try:
            mod._run = lambda cmd, **kwargs: type(
                "Result",
                (),
                {
                    "returncode": 0,
                    "stdout": "\n".join(
                        [
                            "101 /usr/bin/pgrep -af llama-server.*--port 8002",
                            "102 /opt/bin/llama-server --port 8002 --parallel 2",
                            "103 python script.py --runtime-log llama-server --port 8002",
                            "104 /opt/bin/llama-server --port=8002 --parallel=2",
                        ]
                    ),
                },
            )()

            self.assertEqual(mod._pids_for_port(8002), [102, 104])
        finally:
            mod._run = original_run

    def test_ensure_runtime_refuses_parallel_mismatch(self):
        args = Namespace(
            api_key="local-openai-key",
            disable_prompt_cache=True,
            server_parallel=2,
            start_runtime=False,
        )
        original_runtime_status = mod._runtime_status
        try:
            mod._runtime_status = lambda endpoint, *, api_key: {
                "endpoint": endpoint,
                "port": 8002,
                "healthy": True,
                "cmdlines": {"123": "llama-server --port 8002 --parallel 1"},
                "prompt_cache_controls": {
                    "123": {"disabled_by_runtime_config": True}
                },
            }
            with self.assertRaisesRegex(RuntimeError, "server --parallel"):
                mod._ensure_runtime(args, "http://127.0.0.1:8002")
        finally:
            mod._runtime_status = original_runtime_status

    def test_cmdline_redaction_removes_api_key_value(self):
        redacted = mod._redact_cmdline("llama-server --api-key secret --port 8002")

        self.assertEqual(redacted, "llama-server --api-key <redacted> --port 8002")

        redacted_inline = mod._redact_cmdline("llama-server --api-key=secret --port 8002")

        self.assertEqual(redacted_inline, "llama-server --api-key=<redacted> --port 8002")

    def test_in_memory_observer_records_stage_wall_time(self):
        observer = mod._InMemoryStageObserver(
            document_id="doc-1",
            requested_method="docling",
            strict_method=True,
        )

        observer.emit("parser", "running", "start")
        observer._stage_started_at["parser"] -= 1.25
        observer.emit("parser", "succeeded", "done")
        timings = mod._observer_stage_timings(observer)

        self.assertGreaterEqual(timings["docling_parse_layout"], 1.0)
        self.assertEqual(observer.events[-1]["stage"], "parser")

    def test_capture_llm_request_timings_wraps_and_restores_generate_json(self):
        from app.services import llm as llm_service

        original = llm_service.generate_json

        def fake_generate_json(prompt, *args, **kwargs):
            return {"ok": True, "prompt": prompt}

        llm_service.generate_json = fake_generate_json
        try:
            with mod._capture_llm_request_timings("doc-1") as rows:
                result = llm_service.generate_json(
                    "hello",
                    metadata={"component": "multipass_extraction", "task_type": "reasoning"},
                )
            self.assertEqual(result["ok"], True)
            self.assertEqual(llm_service.generate_json, fake_generate_json)
        finally:
            llm_service.generate_json = original

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["document_id"], "doc-1")
        self.assertEqual(rows[0]["component"], "multipass_extraction")
        self.assertEqual(rows[0]["prompt_chars"], 5)
        self.assertIn("started_epoch", rows[0])
        self.assertIn("ended_epoch", rows[0])
        self.assertGreaterEqual(rows[0]["elapsed_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
