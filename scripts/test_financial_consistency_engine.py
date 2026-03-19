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
MOD = _load_module(str(ROOT / "scripts" / "financial_consistency_engine.py"), "financial_consistency_engine")


class TestFinancialConsistencyEngine(unittest.TestCase):
    def _base_row(self, metric: str, value: float):
        return {
            "file": "/tmp/demo.pdf",
            "statement_period_end": "2025-06-30",
            "currency": "AUD",
            "metric": metric,
            "metric_base": metric,
            "value": value,
        }

    def test_consistency_checks_pass_for_balanced_rows(self):
        rows = [
            self._base_row("ebitda", 100.0),
            self._base_row("depreciation_and_amortisation", -20.0),
            self._base_row("ebit", 80.0),
            self._base_row("total_assets", 300.0),
            self._base_row("total_liabilities", 180.0),
            self._base_row("total_equity", 120.0),
            self._base_row("operating_cash_flow", 90.0),
            self._base_row("capital_expenditure", 30.0),
            self._base_row("free_cash_flow", 60.0),
        ]
        report = MOD.evaluate_financial_consistency(rows)
        self.assertTrue(report["passed"])
        self.assertEqual(report["checks_evaluated"], 3)
        self.assertEqual(report["failed_checks"], [])

    def test_consistency_checks_fail_when_identity_breaks(self):
        rows = [
            self._base_row("total_assets", 300.0),
            self._base_row("total_liabilities", 180.0),
            self._base_row("total_equity", 100.0),
        ]
        report = MOD.evaluate_financial_consistency(rows)
        self.assertFalse(report["passed"])
        self.assertEqual(report["failed_reasons"], ["assets_equals_liabilities_plus_equity"])


if __name__ == "__main__":
    unittest.main()
