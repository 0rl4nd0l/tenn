import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
MOD = load_module(str(ROOT / "scripts" / "validation_gates.py"), "validation_gates")


class TestValidationGates(unittest.TestCase):
    def _base(self, metric: str, value: float, family: str = "balance_sheet"):
        return {
            "file": "/tmp/demo.pdf",
            "statement_period_end": "2025-06-30",
            "statement_scope": "consolidated_statement",
            "statement_family": family,
            "metric": metric,
            "metric_base": metric,
            "value": value,
        }

    def test_balance_sheet_equation_pass(self):
        rows = [
            self._base("total_assets", 1000.0),
            self._base("total_liabilities", 600.0),
            self._base("total_equity", 400.0),
        ]
        failures = MOD.evaluate_balance_sheet_equation(rows)
        self.assertEqual(failures, [])

    def test_balance_sheet_equation_pass_with_negative_liabilities_convention(self):
        rows = [
            self._base("total_assets", 1000.0),
            self._base("total_liabilities", -600.0),
            self._base("total_equity", 400.0),
        ]
        failures = MOD.evaluate_balance_sheet_equation(rows)
        self.assertEqual(failures, [])

    def test_statement_level_quarantine_demotes_only_balance_rows(self):
        rows = [
            self._base("total_assets", 1000.0, "balance_sheet"),
            self._base("total_liabilities", 500.0, "balance_sheet"),
            self._base("total_equity", 400.0, "balance_sheet"),  # mismatch: 100
            self._base("revenue", 300.0, "income_statement"),
        ]
        with tempfile.TemporaryDirectory() as td:
            out = MOD.apply_statement_level_quarantine(rows, out_dir=Path(td))
        self.assertEqual(int(out["summary"]["rows_input"]), 4)
        self.assertEqual(int(out["summary"]["rows_quarantined"]), 3)
        kept_metrics = {str(r.get("metric")) for r in out["kept_rows"]}
        self.assertEqual(kept_metrics, {"revenue"})

    def test_cash_reconciliation_quarantine(self):
        rows = [
            self._base("cash_and_equivalents_opening", 100.0, "cash_flow"),
            self._base("operating_cash_flow", 40.0, "cash_flow"),
            self._base("investing_cash_flow", -10.0, "cash_flow"),
            self._base("financing_cash_flow", 0.0, "cash_flow"),
            self._base("cash_and_equivalents_closing", 200.0, "cash_flow"),
            self._base("revenue", 1000.0, "income_statement"),
        ]
        out = MOD.apply_statement_level_quarantine(rows)
        quarantined_metrics = {str(r.get("metric")) for r in out["quarantined_rows"]}
        self.assertIn("cash_and_equivalents_opening", quarantined_metrics)
        self.assertIn("cash_and_equivalents_closing", quarantined_metrics)
        kept_metrics = {str(r.get("metric")) for r in out["kept_rows"]}
        self.assertIn("revenue", kept_metrics)


if __name__ == "__main__":
    unittest.main()
