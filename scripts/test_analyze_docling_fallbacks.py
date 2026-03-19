import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

ANALYZE = _load_module(str(ROOT / "scripts" / "analyze_docling_fallbacks.py"), "analyze_docling_fallbacks")


class TestAnalyzeDoclingFallbacks(unittest.TestCase):
    def _payload(self):
        return {
            "documents": [
                {
                    "ticker": "AAA",
                    "document": "/tmp/aaa.pdf",
                    "fallback_triggered": True,
                    "fallback_reason": "critical_metrics_missing",
                    "docling_row_count_before_filtering": 10,
                    "rejection_reasons": {
                        "missing_statement_period_end": 2,
                        "canonical_conflict_same_period": 5,
                    },
                    "context_rows": 3,
                    "rejected_rows": 1,
                    "tsr_tables_processed": 4,
                },
                {
                    "ticker": "BBB",
                    "document": "/tmp/bbb.pdf",
                    "fallback_triggered": True,
                    "fallback_reason": "financial_consistency_failed",
                    "docling_row_count_before_filtering": 20,
                    "rejection_reasons": {
                        "canonical_conflict_same_period": 12,
                    },
                    "context_rows": 2,
                    "rejected_rows": 2,
                    "tsr_tables_processed": 7,
                },
                {
                    "ticker": "CCC",
                    "document": "/tmp/ccc.pdf",
                    "fallback_triggered": True,
                    "fallback_reason": "unexpected_reason",
                    "docling_row_count_before_filtering": 0,
                    "rejection_reasons": {},
                    "context_rows": 0,
                    "rejected_rows": 0,
                    "tsr_tables_processed": 0,
                },
                {
                    "ticker": "DDD",
                    "document": "/tmp/ddd.pdf",
                    "fallback_triggered": False,
                    "fallback_suppressed": True,
                    "fallback_suppression_reason": "sufficient_docling_rows",
                    "fallback_reason": None,
                    "docling_row_count_before_filtering": 99,
                    "rejection_reasons": {"canonical_conflict_same_period": 99},
                    "context_rows": 0,
                    "rejected_rows": 0,
                    "tsr_tables_processed": 0,
                },
            ]
        }

    def test_build_docling_fallback_analysis_counts_fallback_documents(self):
        analysis = ANALYZE.build_docling_fallback_analysis(self._payload())

        self.assertEqual(analysis["fallback_documents_total"], 3)
        self.assertEqual(
            analysis["fallback_reason_counts"],
            {
                "no_rows": 1,
                "no_context_rows": 0,
                "financial_consistency_failed": 1,
                "other": 0,
                "no_fallback": 1,
            },
        )
        self.assertEqual(analysis["fallback_suppressed_count"], 1)
        self.assertEqual(
            analysis["fallback_suppression_reason_counts"],
            {
                "sufficient_docling_rows": 1,
            },
        )
        self.assertEqual(analysis["documents_with_consistency_failure"], 1)
        self.assertEqual(analysis["documents_with_metric_missing"], 1)
        self.assertEqual(analysis["documents_with_high_conflicts"], 1)
        self.assertEqual(analysis["top_rejection_reasons"]["canonical_conflict_same_period"], 17)
        self.assertEqual(analysis["average_docling_row_count_before_filtering"], 10.0)
        self.assertEqual(len(analysis["documents"]), 3)
        self.assertIn("rejection_reasons", analysis["documents"][0])
        self.assertEqual(analysis["documents"][0]["reported_fallback_reason"], "critical_metrics_missing")

    def test_main_writes_valid_json_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = Path(tmpdir) / "pipeline_diagnostics.json"
            out_path = Path(tmpdir) / "docling_fallback_analysis.json"
            in_path.write_text(json.dumps(self._payload()), encoding="utf-8")

            rc = ANALYZE.main(
                [
                    "--input",
                    str(in_path),
                    "--output",
                    str(out_path),
                ]
            )

            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())
            written = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(written["fallback_documents_total"], 3)
            self.assertEqual(written["documents_with_metric_missing"], 1)

    def test_build_docling_fallback_analysis_handles_empty_fallback_set(self):
        analysis = ANALYZE.build_docling_fallback_analysis(
            {
                "documents": [
                    {
                        "ticker": "ZZZ",
                        "document": "/tmp/zzz.pdf",
                        "fallback_triggered": False,
                    }
                ]
            }
        )

        self.assertEqual(analysis["fallback_documents_total"], 0)
        self.assertEqual(
            analysis["fallback_reason_counts"],
            {
                "no_rows": 0,
                "no_context_rows": 0,
                "financial_consistency_failed": 0,
                "other": 0,
                "no_fallback": 0,
            },
        )
        self.assertEqual(analysis["fallback_suppressed_count"], 0)
        self.assertEqual(analysis["fallback_suppression_reason_counts"], {})
        self.assertEqual(analysis["top_rejection_reasons"], {})
        self.assertEqual(analysis["average_docling_row_count_before_filtering"], 0.0)
        self.assertEqual(analysis["documents"], [])


if __name__ == "__main__":
    unittest.main()
