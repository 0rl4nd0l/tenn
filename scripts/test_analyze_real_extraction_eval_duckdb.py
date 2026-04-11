import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "analyze_real_extraction_eval_duckdb.py"

spec = importlib.util.spec_from_file_location(
    "analyze_real_extraction_eval_duckdb", str(SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestDuckDbAnalysis(unittest.TestCase):
    def test_load_rows_captures_tickers_and_trust_triggers(self):
        payload = {
            "summary": {"generated_at": "2026-04-10T00:00:00+00:00"},
            "documents": [
                {
                    "document_id": "rio_a_2024-12-31",
                    "ticker": "RIO",
                    "period_type": "A",
                    "period_end": "2024-12-31",
                    "trust_outcome": "abstain",
                    "expected_trust": "trusted",
                    "context_correct": True,
                    "extraction_status": "completed",
                    "context_mismatches": [],
                    "trust_triggers": ["net_debt:missing"],
                    "metric_results": {
                        "revenue": {"status": "wrong", "reason": "delta"},
                        "net_debt": {"status": "missing", "reason": "null"},
                    },
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "results.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")

            document_rows, metric_rows, trigger_rows = mod._load_rows([artifact])

            self.assertEqual(document_rows[0][1], "rio_a_2024-12-31")
            self.assertEqual(document_rows[0][2], "RIO")
            self.assertEqual(document_rows[0][9], 1)
            self.assertEqual(document_rows[0][10], 1)
            self.assertEqual(document_rows[0][12], 2)
            self.assertEqual(metric_rows[0][2], "RIO")
            self.assertEqual(trigger_rows[0][-1], "net_debt:missing")

    def test_main_writes_expected_sections(self):
        payload = {
            "summary": {"generated_at": "2026-04-10T00:00:00+00:00"},
            "documents": [
                {
                    "document_id": "qbe_h_2025-06-30",
                    "ticker": "QBE",
                    "period_type": "H",
                    "period_end": "2025-06-30",
                    "trust_outcome": "quarantine",
                    "expected_trust": "trusted",
                    "context_correct": False,
                    "extraction_status": "failed",
                    "context_mismatches": ["currency"],
                    "trust_triggers": ["context_mismatch"],
                    "metric_results": {
                        "operating_cash_flow": {
                            "status": "missing",
                            "reason": "null",
                        }
                    },
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "results.json"
            summary_path = Path(tmpdir) / "summary.md"
            artifact.write_text(json.dumps(payload), encoding="utf-8")

            with mock.patch.object(
                sys,
                "argv",
                [
                    str(SCRIPT_PATH),
                    str(artifact),
                    "--summary-path",
                    str(summary_path),
                ],
            ):
                exit_code = mod.main()

            self.assertEqual(exit_code, 0)
            contents = summary_path.read_text(encoding="utf-8")
            self.assertIn("## Most Failed Documents", contents)
            self.assertIn("## Failure Clusters By Ticker And Form", contents)
            self.assertIn("## Trust Trigger Summary", contents)
            self.assertIn("QBE", contents)


if __name__ == "__main__":
    unittest.main()
