import importlib.util
import sys
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
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

MOD = load_module(str(SCRIPTS_DIR / "financial_identity_resolver.py"), "financial_identity_resolver")


class TestFinancialIdentityResolver(unittest.TestCase):
    def _base(
        self,
        metric: str,
        value: float,
        *,
        file: str = "/tmp/demo.pdf",
        period: str = "2025-06-30",
        family: str = "income_statement",
        line_no: int = 1,
    ):
        return {
            "file": file,
            "metric": metric,
            "metric_base": metric,
            "statement_period_end": period,
            "statement_family": family,
            "statement_scope": "consolidated_statement",
            "value_type": "amount",
            "value": value,
            "raw_value": str(value),
            "currency": "$",
            "line_no": line_no,
            "row_label": metric.replace("_", " "),
            "table_header_text": "",
            "statement_title": "",
        }

    def test_duplicate_depreciation_resolution(self):
        rows = [
            self._base("ebitda", 100.0, line_no=1),
            self._base("ebit", 80.0, line_no=2),
            self._base("depreciation_and_amortisation", 20.0, line_no=3),
            self._base("depreciation_and_amortisation", 15.0, line_no=4),
        ]

        resolved, demoted, diagnostics = MOD.resolve_duplicate_metrics(rows)

        dep_values = sorted(r["value"] for r in resolved if r["metric"] == "depreciation_and_amortisation")
        self.assertEqual(dep_values, [20.0])
        self.assertEqual(len(demoted), 1)
        self.assertEqual(demoted[0].get("context_reason"), "identity_resolved_same_period")
        self.assertTrue(diagnostics["identity_resolution_applied"])
        self.assertEqual(diagnostics["identity_resolution_conflicts"], 1)

    def test_balance_sheet_identity_resolution(self):
        rows = [
            self._base("total_liabilities", 60.0, family="balance_sheet", line_no=1),
            self._base("total_equity", 40.0, family="balance_sheet", line_no=2),
            self._base("total_assets", 100.0, family="balance_sheet", line_no=3),
            self._base("total_assets", 105.0, family="balance_sheet", line_no=4),
        ]

        resolved, demoted, diagnostics = MOD.resolve_duplicate_metrics(rows)

        asset_values = sorted(r["value"] for r in resolved if r["metric"] == "total_assets")
        self.assertEqual(asset_values, [100.0])
        self.assertEqual(len(demoted), 1)
        self.assertTrue(diagnostics["identity_resolution_applied"])
        self.assertEqual(diagnostics["identity_resolution_conflicts"], 1)

    def test_cash_flow_identity_resolution(self):
        rows = [
            self._base("operating_cash_flow", 50.0, family="cash_flow", line_no=1),
            self._base("investing_cash_flow", -20.0, family="cash_flow", line_no=2),
            self._base("financing_cash_flow", -5.0, family="cash_flow", line_no=3),
            self._base("net_change_in_cash", 25.0, family="cash_flow", line_no=4),
            self._base("net_change_in_cash", 30.0, family="cash_flow", line_no=5),
        ]

        resolved, demoted, diagnostics = MOD.resolve_duplicate_metrics(rows)

        net_change_values = sorted(r["value"] for r in resolved if r["metric"] == "net_change_in_cash")
        self.assertEqual(net_change_values, [25.0])
        self.assertEqual(len(demoted), 1)
        self.assertTrue(diagnostics["identity_resolution_applied"])
        self.assertEqual(diagnostics["identity_resolution_conflicts"], 1)

    def test_no_changes_when_duplicates_absent(self):
        rows = [
            self._base("ebitda", 100.0, line_no=1),
            self._base("ebit", 80.0, line_no=2),
            self._base("depreciation_and_amortisation", 20.0, line_no=3),
        ]

        resolved, demoted, diagnostics = MOD.resolve_duplicate_metrics(rows)

        self.assertEqual(resolved, rows)
        self.assertEqual(demoted, [])
        self.assertFalse(diagnostics["identity_resolution_applied"])
        self.assertEqual(diagnostics["identity_resolution_conflicts"], 0)


if __name__ == "__main__":
    unittest.main()
