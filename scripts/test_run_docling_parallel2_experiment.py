import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_docling_parallel2_experiment.py"

spec = importlib.util.spec_from_file_location(
    "run_docling_parallel2_experiment", str(SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _passing_payload() -> dict:
    return {
        "acceptance": {
            "passed": True,
            "runtime_ids": ["http://127.0.0.1:8002"],
            "shared_runtime_avoided": True,
            "cache_hit": False,
            "fallback_used": False,
            "timeout_event": False,
        },
        "control": {
            "summary": {
                "total_documents": 1,
                "context_correct_documents": 1,
                "total_metric_checks": 1,
                "metric_status_counts": {"correct": 1},
                "trust_distribution": {"trusted": 1},
                "trust_matches_expected": 1,
            },
            "documents": [
                {
                    "document_id": "qbe_h_2025-06-30",
                    "extraction_error": None,
                    "llm_request_timings": [],
                }
            ],
        },
    }


class RunDoclingParallel2ExperimentTests(unittest.TestCase):
    def test_cell_gate_fails_on_captured_llm_request_timeout(self):
        payload = _passing_payload()
        payload["control"]["documents"][0]["llm_request_timings"] = [
            {
                "call_index": 4,
                "elapsed_seconds": 120.24,
                "error": (
                    "llama.cpp JSON generation failed at "
                    "http://127.0.0.1:8002/v1/chat/completions: timed out"
                ),
            }
        ]

        gate = mod._cell_gate(payload)

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["status"], "fail")
        self.assertIn(
            "failure_mode_classified_request_timeout",
            gate["failure_classes"],
        )
        self.assertTrue(gate["acceptance_passed_before_runtime_health_gate"])
        self.assertFalse(gate["no_timeout"])
        self.assertEqual(gate["request_timeouts"]["count"], 1)
        self.assertEqual(
            gate["request_timeouts"]["documents"],
            ["qbe_h_2025-06-30"],
        )

    def test_cell_gate_passes_without_runtime_timeout(self):
        gate = mod._cell_gate(_passing_payload())

        self.assertTrue(gate["passed"])
        self.assertEqual(gate["status"], "pass")
        self.assertTrue(gate["no_timeout"])
        self.assertEqual(gate["request_timeouts"]["count"], 0)

    def test_cell_gate_fails_on_active_runtime_health_false(self):
        payload = _passing_payload()
        payload["request_health_timeline"] = [
            {
                "active": True,
                "port_open": True,
                "health_ok": False,
                "slots_probe_state": "ok",
                "iso_utc": "2026-05-04T00:00:00+00:00",
            }
        ]

        gate = mod._cell_gate(payload)

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["runtime_health"]["status"], "fail")
        self.assertEqual(gate["runtime_health"]["port_open_health_false_count"], 1)
        self.assertIn(
            "failure_mode_classified_runtime_health",
            gate["failure_classes"],
        )

    def test_cell_gate_fails_on_active_slots_timeout(self):
        payload = _passing_payload()
        payload["request_health_timeline"] = [
            {
                "active": True,
                "port_open": True,
                "health_ok": True,
                "slots_probe_state": "timeout",
                "iso_utc": "2026-05-04T00:00:01+00:00",
            }
        ]

        gate = mod._cell_gate(payload)

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["runtime_health"]["slots_timeout_count"], 1)
        self.assertIn(
            "failure_mode_classified_slots_timeout",
            gate["failure_classes"],
        )

    def test_partial_payload_after_llm_timeout_invalidates_candidate(self):
        payload = _passing_payload()
        doc = payload["control"]["documents"][0]
        doc["llm_request_timings"] = [
            {
                "call_index": 2,
                "elapsed_seconds": 120.0,
                "error": "llama.cpp JSON generation failed: timed out",
            }
        ]
        doc["metric_results"] = {"net_debt": {"status": "missing"}}
        doc["trust_outcome"] = "abstain"

        gate = mod._cell_gate(payload)

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["partial_payload_after_timeout"]["count"], 1)
        self.assertEqual(
            gate["partial_payload_after_timeout"]["documents"],
            ["qbe_h_2025-06-30"],
        )
        self.assertIn(
            "failure_mode_classified_partial_payload",
            gate["failure_classes"],
        )

    def test_matrix_invalidates_speed_verdict_when_health_gate_fails(self):
        payload = _passing_payload()
        payload["control"]["wall_time_seconds"] = 1.0
        payload["request_health_timeline"] = [
            {
                "active": True,
                "port_open": True,
                "health_ok": False,
                "slots_probe_state": "ok",
            }
        ]

        matrix = mod._build_matrix(
            baseline_dir=ROOT / "missing-baseline",
            cell_a=None,
            cell_b=None,
            cell_c=payload,
            concurrency_rows=[],
        )

        self.assertEqual(
            matrix["cells"]["server_parallel_2_two_doc_concurrent_client"]["verdict"],
            "candidate_invalidated_by_health_failfast",
        )

    def test_per_doc_timeout_hit_reads_llm_request_timings(self):
        payload = _passing_payload()
        payload["control"]["documents"][0]["llm_request_timings"] = [
            {"error": "deadline exceeded while waiting for llama.cpp"}
        ]

        rows = mod._per_doc_rows("cell", payload)

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["timeout_hit"])

    def test_doc_ids_accepts_selected_docs(self):
        args = argparse.Namespace(doc_ids=["bhp_a_2025-06-30", "qbe_h_2025-06-30"])

        self.assertEqual(
            mod._doc_ids(args),
            ("bhp_a_2025-06-30", "qbe_h_2025-06-30"),
        )

    def test_control_cmd_uses_selected_docs_and_parallel_override(self):
        args = argparse.Namespace(
            extraction_url="http://127.0.0.1:8002",
            shared_url="http://127.0.0.1:8001",
            server_parallel=2,
        )

        cmd = mod._control_cmd(
            args=args,
            results_json=ROOT / "tmp" / "results.json",
            report_path=ROOT / "tmp" / "report.md",
            runtime_log=ROOT / "tmp" / "runtime.log",
            doc_ids=("bhp_a_2025-06-30", "qbe_h_2025-06-30"),
            server_parallel=1,
            start_runtime=True,
        )

        self.assertIn("--start-runtime", cmd)
        parallel_index = cmd.index("--server-parallel")
        self.assertEqual(cmd[parallel_index + 1], "1")
        doc_args = [
            cmd[index + 1]
            for index, item in enumerate(cmd)
            if item == "--doc-id"
        ]
        self.assertEqual(doc_args, ["bhp_a_2025-06-30", "qbe_h_2025-06-30"])

    def test_validation_verdict_invalidates_unsafe_cell_c_after_clean_controls(self):
        control_gate = mod._cell_gate(_passing_payload())
        c_cell = {"verdict": "candidate_invalidated_by_health_failfast"}
        c_gate = mod._cell_gate(_passing_payload())

        self.assertEqual(
            mod._validation_verdict(control_gate, control_gate, c_cell, c_gate),
            "failfast_validation_passed_invalidated_unsafe_candidate",
        )

    def test_write_reports_emits_request_health_csv_when_samples_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            baseline_dir = temp_root / "baseline"
            baseline_dir.mkdir()
            (baseline_dir / "correctness_gate.json").write_text("{}", encoding="utf-8")
            report_dir = temp_root / "report"
            payload = _passing_payload()
            payload["runtime"] = {"endpoint": "http://127.0.0.1:8002"}
            payload["runtime_after"] = {"endpoint": "http://127.0.0.1:8002"}
            payload["control"]["wall_time_seconds"] = 1.0
            payload["request_health_timeline"] = [
                {
                    "cell": "server_parallel_2_two_doc_concurrent_client",
                    "epoch": 1.0,
                    "iso_utc": "2026-05-04T00:00:00+00:00",
                    "event": "poll",
                    "doc_id": "qbe_h_2025-06-30",
                    "active": True,
                    "active_doc_ids": "[\"qbe_h_2025-06-30\"]",
                    "port_open": True,
                    "health_ok": True,
                    "health_http_status": 200,
                    "health_probe_state": "ok",
                    "runtime_pids": "[123]",
                    "slots_http_status": 200,
                    "slots_probe_state": "ok",
                    "slots_snapshot": "[]",
                }
            ]
            args = argparse.Namespace(
                doc_ids=["qbe_h_2025-06-30"],
                max_client_concurrency=2,
            )

            mod._write_reports(
                args=args,
                report_dir=report_dir,
                baseline_dir=baseline_dir,
                audit={},
                cell_a=payload,
                cell_b=None,
                cell_c=None,
                commands=[],
            )

            rows = (report_dir / "request_health_timeline.csv").read_text(
                encoding="utf-8"
            )
            self.assertIn("server_parallel_2_two_doc_concurrent_client", rows)


if __name__ == "__main__":
    unittest.main()
