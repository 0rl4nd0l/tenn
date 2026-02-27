import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
MOD = load_module(str(ROOT / "capital_structure_enhancement.py"), "capital_structure_enhancement")


class TestCapitalStructureEnhancement(unittest.TestCase):
    def test_structural_net_debt_and_fcf_derivation(self):
        canonical_df = pd.DataFrame(
            [
                # Period 1: no net_debt/fcf, derive both
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "cash_and_equivalents", "value": 40.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "total_debt", "value": 100.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "ebitda", "value": 20.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "operating_cash_flow", "value": 30.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "capital_expenditure", "value": 10.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "total_equity", "value": 200.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "total_liabilities", "value": 180.0, "canonical_confidence_score": 3, "integrity_score": 2},
                # Period 2: explicit net_debt/fcf present
                {"file": "/tmp/docs/AAA/financial_performance/p2.pdf", "statement_period_end": "2024-12-31", "metric": "net_debt", "value": 55.0, "canonical_confidence_score": 4, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p2.pdf", "statement_period_end": "2024-12-31", "metric": "free_cash_flow", "value": 12.0, "canonical_confidence_score": 4, "integrity_score": 2},
                {"file": "/tmp/docs/AAA/financial_performance/p2.pdf", "statement_period_end": "2024-12-31", "metric": "ebitda", "value": 22.0, "canonical_confidence_score": 3, "integrity_score": 2},
            ]
        )
        derived_df = pd.DataFrame(
            [
                {"source_file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "net_debt_to_ebitda", "value_num": 2.5},
                {"source_file": "/tmp/docs/AAA/financial_performance/p2.pdf", "statement_period_end": "2024-12-31", "metric": "net_debt_to_ebitda", "value_num": 2.0},
            ]
        )
        risk_df = pd.DataFrame(
            [
                {"file": "/tmp/docs/AAA/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "signal_name": "net_debt_to_ebitda_risk", "risk_level": "MEDIUM"},
                {"file": "/tmp/docs/AAA/financial_performance/p2.pdf", "statement_period_end": "2024-12-31", "signal_name": "net_debt_to_ebitda_risk", "risk_level": "LOW"},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            summary = MOD.run_enhancement(canonical_df, derived_df, risk_df, Path(td))
            self.assertEqual(summary["total_periods"], 2)
            self.assertGreaterEqual(summary["net_debt_coverage_after"], summary["net_debt_coverage_before"])
            self.assertGreaterEqual(summary["fcf_coverage_after"], summary["fcf_coverage_before"])

            nd = pd.read_csv(Path(td) / "derived_net_debt_enhanced.csv")
            p1 = nd[nd["period_end"] == "2024-06-30"].iloc[0]
            self.assertEqual(str(p1["net_debt_source"]), "structural_derivation")
            self.assertAlmostEqual(float(p1["net_debt"]), 60.0)

            fcf = pd.read_csv(Path(td) / "derived_fcf_enhanced.csv")
            p1_fcf = fcf[fcf["period_end"] == "2024-06-30"].iloc[0]
            self.assertEqual(str(p1_fcf["fcf_source"]), "structural_derivation")
            self.assertAlmostEqual(float(p1_fcf["free_cash_flow"]), 20.0)

            stability = json.loads((Path(td) / "capital_structure_enhancement_summary.json").read_text(encoding="utf-8"))
            self.assertIn("leverage_jump_count_before", stability)
            self.assertIn("leverage_jump_count_after", stability)

    def test_leverage_unknown_when_inputs_missing(self):
        canonical_df = pd.DataFrame(
            [
                {"file": "/tmp/docs/BBB/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "cash_and_equivalents", "value": 10.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/BBB/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "total_equity", "value": 50.0, "canonical_confidence_score": 3, "integrity_score": 2},
                {"file": "/tmp/docs/BBB/financial_performance/p1.pdf", "statement_period_end": "2024-06-30", "metric": "total_liabilities", "value": 40.0, "canonical_confidence_score": 3, "integrity_score": 2},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            MOD.run_enhancement(canonical_df, pd.DataFrame(), pd.DataFrame(), Path(td))
            lev = pd.read_csv(Path(td) / "leverage_enhanced.csv")
            row = lev.iloc[0]
            self.assertEqual(str(row["leverage_support"]), "insufficient_inputs")
            self.assertEqual(str(row["leverage_risk_flag"]), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
