import importlib.util
import sys
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
MOD = _load_module(str(ROOT / "scripts" / "extractor_fallback_policy.py"), "extractor_fallback_policy_threshold")


class TestFallbackPolicy(unittest.TestCase):
    def _row(self, metric: str, value: float, *, currency: str = "AUD"):
        return {
            "file": "/tmp/demo.pdf",
            "statement_period_end": "2025-06-30",
            "currency": currency,
            "metric": metric,
            "metric_base": metric,
            "value": value,
            "value_type": "amount",
        }

    def test_critical_metrics_missing_does_not_trigger_fallback_when_docling_rows_are_sufficient(self):
        split = {
            "canonical_rows": [self._row("cash_and_equivalents", 50.0)],
            "context_rows": [self._row("revenue", 120.0)],
            "diagnostics": {"docling_row_count_before_filtering": 10, "tsr_tables_processed": 1},
        }

        decision = MOD.evaluate_docling_fallback(split)

        self.assertFalse(decision["should_fallback"])
        self.assertEqual(decision["fallback_reason"], None)
        self.assertEqual(decision["reasons"], [])
        self.assertTrue(decision["fallback_suppressed"])
        self.assertEqual(decision["fallback_suppression_reason"], "sufficient_docling_rows")

    def test_critical_metrics_missing_triggers_fallback_when_docling_rows_are_below_threshold(self):
        split = {
            "canonical_rows": [self._row("cash_and_equivalents", 50.0)],
            "diagnostics": {"docling_row_count_before_filtering": 9},
        }

        decision = MOD.evaluate_docling_fallback(split)

        self.assertTrue(decision["should_fallback"])
        self.assertEqual(decision["fallback_reason"], "critical_metrics_missing")
        self.assertIn("critical_metrics_missing", decision["reasons"])
        self.assertFalse(decision["fallback_suppressed"])
        self.assertIsNone(decision["fallback_suppression_reason"])

    def test_financial_consistency_failure_still_triggers_fallback(self):
        split = {
            "canonical_rows": [
                self._row("total_assets", 300.0),
                self._row("total_liabilities", 180.0),
                self._row("total_equity", 100.0),
            ],
            "diagnostics": {"docling_row_count_before_filtering": 99},
        }

        decision = MOD.evaluate_docling_fallback(split)

        self.assertTrue(decision["should_fallback"])
        self.assertEqual(decision["fallback_reason"], "financial_consistency_failed")
        self.assertIn("financial_consistency_failed", decision["reasons"])
        self.assertFalse(decision["fallback_suppressed"])
        self.assertIsNone(decision["fallback_suppression_reason"])


if __name__ == "__main__":
    unittest.main()
