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
    def test_development_input_produces_aggregate_only_markdown(self):
        aggregate = {
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
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "secret-name.json"
            summary_path = Path(tmpdir) / "summary.md"
            artifact.write_text(json.dumps(aggregate), encoding="utf-8")
            with mock.patch.object(
                sys,
                "argv",
                [
                    str(SCRIPT_PATH),
                    str(artifact),
                    "--summary-path",
                    str(summary_path),
                    "--corpus-classification",
                    "non_holdout",
                    "--access-mode",
                    "development",
                ],
            ):
                self.assertEqual(mod.main(), 0)
            contents = summary_path.read_text(encoding="utf-8")
            self.assertIn("document_count: 48", contents)
            self.assertNotIn("secret-name", contents)
            self.assertNotIn("document_id", contents)

    def test_holdout_classification_ignores_detailed_analysis_input(self):
        aggregate = {
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
        with tempfile.TemporaryDirectory() as tmpdir:
            detailed = Path(tmpdir) / "detailed.json"
            aggregate_path = Path(tmpdir) / "aggregate.json"
            summary_path = Path(tmpdir) / "summary.md"
            detailed.write_text(
                json.dumps({"documents": [{"document_id": "secret"}]}),
                encoding="utf-8",
            )
            aggregate_path.write_text(json.dumps(aggregate), encoding="utf-8")
            with mock.patch.object(
                sys,
                "argv",
                [
                    str(SCRIPT_PATH),
                    str(detailed),
                    "--summary-path",
                    str(summary_path),
                    "--corpus-classification",
                    "holdout",
                    "--access-mode",
                    "development",
                    "--development-aggregate-json",
                    str(aggregate_path),
                ],
            ):
                self.assertEqual(mod.main(), 0)
            self.assertNotIn("secret", summary_path.read_text(encoding="utf-8"))

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
                    "--corpus-classification",
                    "non_holdout",
                    "--access-mode",
                    "development",
                ],
            ):
                exit_code = mod.main()

            self.assertEqual(exit_code, 0)
            contents = summary_path.read_text(encoding="utf-8")
            self.assertIn("## Most Failed Documents", contents)
            self.assertIn("## Failure Clusters By Ticker And Form", contents)
            self.assertIn("## Trust Trigger Summary", contents)
            self.assertIn("QBE", contents)

    def test_cli_requires_explicit_confidentiality_contract(self):
        with mock.patch.object(
            sys,
            "argv",
            [str(SCRIPT_PATH), "results.json"],
        ):
            with self.assertRaises(SystemExit):
                mod._parse_args()


if __name__ == "__main__":
    unittest.main()
