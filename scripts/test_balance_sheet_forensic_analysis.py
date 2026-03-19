import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pytest


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "balance_sheet_forensic_analysis.py"
if not MODULE_PATH.exists():
    pytest.skip("balance_sheet_forensic_analysis.py is not available in this checkout.", allow_module_level=True)
MOD = load_module(str(MODULE_PATH), "balance_sheet_forensic_analysis")


class TestBalanceSheetForensicAnalysis(unittest.TestCase):
    def test_classification_outputs_and_required_json_keys(self):
        canonical_df = pd.DataFrame(
            [
                # Full statements period.
                {"statement_period_end": "2024-06-30", "metric": "revenue", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "ebit", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "npat", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "total_assets", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "total_liabilities", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "total_equity", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "cash_and_equivalents", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "total_debt", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "operating_cash_flow", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-06-30", "metric": "capital_expenditure", "canonical_confidence_score": 3},
                # Income only period.
                {"statement_period_end": "2024-12-31", "metric": "revenue", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-12-31", "metric": "ebit", "canonical_confidence_score": 3},
                {"statement_period_end": "2024-12-31", "metric": "net_income", "canonical_confidence_score": 3},
                # Balance sheet partial period.
                {"statement_period_end": "2025-06-30", "metric": "revenue", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-06-30", "metric": "ebit", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-06-30", "metric": "net_income", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-06-30", "metric": "total_assets", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-06-30", "metric": "total_liabilities", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-06-30", "metric": "total_equity", "canonical_confidence_score": 3},
                # Cashflow partial period.
                {"statement_period_end": "2025-12-31", "metric": "revenue", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-12-31", "metric": "ebit", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-12-31", "metric": "net_income", "canonical_confidence_score": 3},
                {"statement_period_end": "2025-12-31", "metric": "operating_cash_flow", "canonical_confidence_score": 3},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            result = MOD.run_forensic(canonical_df, out_dir, min_confidence=3)
            self.assertTrue((out_dir / "balance_sheet_forensic_summary.csv").exists())
            self.assertTrue((out_dir / "balance_sheet_forensic_summary.json").exists())

            summary = json.loads((out_dir / "balance_sheet_forensic_summary.json").read_text(encoding="utf-8"))
            self.assertIn("periods_income_only", summary)
            self.assertIn("periods_balance_sheet_partial", summary)
            self.assertIn("periods_cashflow_partial", summary)
            self.assertIn("periods_full_statements", summary)
            self.assertIn("structural_pattern_detected", summary)
            self.assertIn("2024-12-31", summary["periods_income_only"])
            self.assertIn("2024-06-30", summary["periods_full_statements"])

            csv_df = pd.read_csv(out_dir / "balance_sheet_forensic_summary.csv")
            cls = dict(zip(csv_df["period_end"], csv_df["classification"]))
            self.assertEqual(cls["2024-06-30"], MOD.FULL_STATEMENTS_PRESENT)
            self.assertEqual(cls["2024-12-31"], MOD.INCOME_ONLY)
            self.assertEqual(cls["2025-06-30"], MOD.BALANCE_SHEET_PARTIAL)
            self.assertEqual(cls["2025-12-31"], MOD.CASHFLOW_PARTIAL)

            self.assertEqual(result["counts"]["total_periods"], 4)


if __name__ == "__main__":
    unittest.main()
