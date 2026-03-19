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
MOD = _load_module(str(ROOT / "scripts" / "extractor_fallback_policy.py"), "extractor_fallback_policy")


class TestExtractorFallbackPolicy(unittest.TestCase):
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

    def test_no_fallback_when_currency_metrics_and_consistency_are_present(self):
        split = {
            "canonical_rows": [
                self._row("total_assets", 300.0),
                self._row("total_liabilities", 180.0),
                self._row("total_equity", 120.0),
            ],
            "context_rows": [self._row("revenue", 90.0)],
            "diagnostics": {"docling_row_count_before_filtering": 8, "tsr_tables_processed": 1},
        }
        decision = MOD.evaluate_docling_fallback(split)
        self.assertFalse(decision["should_fallback"])
        self.assertEqual(decision["reasons"], [])

    def test_currency_detection_failure_triggers_fallback(self):
        split = {"canonical_rows": [self._row("revenue", 100.0, currency="")]}
        decision = MOD.evaluate_docling_fallback(split)
        self.assertTrue(decision["should_fallback"])
        self.assertIn("currency_detection_failed", decision["reasons"])

    def test_consistency_failure_triggers_fallback(self):
        split = {
            "canonical_rows": [
                self._row("total_assets", 300.0),
                self._row("total_liabilities", 180.0),
                self._row("total_equity", 100.0),
            ]
        }
        decision = MOD.evaluate_docling_fallback(split)
        self.assertTrue(decision["should_fallback"])
        self.assertIn("financial_consistency_failed", decision["reasons"])

    def test_missing_critical_metrics_triggers_fallback(self):
        split = {"canonical_rows": [self._row("cash_and_equivalents", 50.0)]}
        # Missing critical metrics should not force fallback when Docling signal is still usable.
        split["context_rows"] = [self._row("revenue", 120.0)]
        split["diagnostics"] = {"docling_row_count_before_filtering": 12, "tsr_tables_processed": 1}
        decision = MOD.evaluate_docling_fallback(split)
        self.assertFalse(decision["should_fallback"])
        self.assertEqual(decision["fallback_reason"], None)
        self.assertEqual(decision["reasons"], [])


if __name__ == "__main__":
    unittest.main()
