import importlib.util
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
AUDIT = load_module(str(ROOT / "scripts" / "audit_financial_metric_quality.py"), "audit_financial_metric_quality")


class TestAuditFinancialMetricQuality(unittest.TestCase):
    def test_balance_sheet_identity_mismatch_detected(self):
        rows = [
            {"file": "a.pdf", "statement_period_end": "2024-12-31", "metric": "total_assets", "value": 1000.0},
            {"file": "a.pdf", "statement_period_end": "2024-12-31", "metric": "total_liabilities", "value": 700.0},
            {"file": "a.pdf", "statement_period_end": "2024-12-31", "metric": "total_equity", "value": 200.0},
        ]
        issues, stats = AUDIT.gather_integrity_issues(rows, balance_sheet_tolerance_pct=0.01)
        self.assertEqual(stats["balance_sheet_identity_evaluated"], 1)
        self.assertEqual(len(issues["balance_sheet_identity_mismatch"]), 1)

    def test_cash_flow_bridge_mismatch_detected(self):
        rows = [
            {
                "file": "b.pdf",
                "statement_period_end": "2025-03-31",
                "metric": "cash_and_equivalents_opening",
                "value": 100.0,
                "row_label": "Cash and cash equivalents at beginning of period",
            },
            {
                "file": "b.pdf",
                "statement_period_end": "2025-03-31",
                "metric": "cash_and_equivalents_closing",
                "value": 170.0,
                "row_label": "Cash and cash equivalents at end of period",
            },
            {
                "file": "b.pdf",
                "statement_period_end": "2025-03-31",
                "metric": "cash_and_equivalents",
                "value": 10.0,
                "row_label": "Net increase / (decrease) in cash and cash equivalents for the period",
            },
        ]
        issues, stats = AUDIT.gather_integrity_issues(rows, cash_bridge_tolerance_pct=0.01)
        self.assertEqual(stats["cash_flow_bridge_evaluated"], 1)
        self.assertEqual(len(issues["cash_flow_bridge_mismatch"]), 1)

    def test_retained_earnings_roll_handles_signed_dividends(self):
        rows = [
            {
                "file": "c.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "total_equity",
                "value": 100.0,
                "row_label": "Retained earnings at beginning of period",
            },
            {
                "file": "c.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "npat",
                "value": 30.0,
                "row_label": "NPAT",
            },
            {
                "file": "c.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "total_equity",
                "value": -10.0,
                "row_label": "Dividends paid",
            },
            {
                "file": "c.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "total_equity",
                "value": 120.0,
                "row_label": "Retained earnings at end of period",
            },
        ]
        issues, stats = AUDIT.gather_integrity_issues(rows, retained_earnings_tolerance_pct=0.01)
        self.assertEqual(stats["retained_earnings_roll_evaluated"], 1)
        self.assertEqual(len(issues["retained_earnings_roll_mismatch"]), 0)

    def test_integrity_score_counts_not_evaluated_checks(self):
        rows = [
            {
                "file": "d.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "revenue",
                "value": 100.0,
            }
        ]
        idx = AUDIT.build_integrity_index(rows)
        meta = idx.get(("d.pdf", "2025-12-31"), {})
        self.assertEqual(meta.get("integrity_checks_evaluated"), 0)
        self.assertEqual(meta.get("integrity_score"), 4)

    def test_non_cash_label_allows_profit_from_operations_for_ebit(self):
        rows = [
            {
                "file": "e.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "ebit",
                "value": 12520.0,
                "row_label": "Profit from operations",
                "statement_scope": "consolidated_statement",
                "inside_table": True,
            }
        ]
        issues = AUDIT.gather_issues(rows)
        self.assertEqual(len(issues["non_cash_label_metric_mismatch"]), 0)

    def test_non_cash_label_allows_attributable_net_income_wording(self):
        rows = [
            {
                "file": "f.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "net_income",
                "value": 2140.0,
                "row_label": "Profit attributable to owners of the parent",
                "statement_scope": "consolidated_statement",
                "inside_table": True,
            }
        ]
        issues = AUDIT.gather_issues(rows)
        self.assertEqual(len(issues["non_cash_label_metric_mismatch"]), 0)

    def test_non_cash_label_allows_after_taxation_attributable_wording(self):
        rows = [
            {
                "file": "g.pdf",
                "statement_period_end": "2025-12-31",
                "metric": "net_income",
                "value": 9019.0,
                "row_label": "Profit after taxation attributable to BHP shareholders",
                "statement_scope": "consolidated_statement",
                "inside_table": True,
            }
        ]
        issues = AUDIT.gather_issues(rows)
        self.assertEqual(len(issues["non_cash_label_metric_mismatch"]), 0)


if __name__ == "__main__":
    unittest.main()
