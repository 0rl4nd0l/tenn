import importlib.util
import json
import subprocess
import sys
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
SCRIPTS_DIR = ROOT / "scripts"
VAL = load_module(str(SCRIPTS_DIR / "validation_quality_cycle.py"), "validation_quality_cycle")


class TestValidationQualityCycle(unittest.TestCase):
    def test_canonical_only_outputs_and_scores(self):
        canonical_df = pd.DataFrame(
            [
                {"statement_period_end": "2024-06-30", "metric": "revenue", "value": 1000.0},
                {"statement_period_end": "2024-06-30", "metric": "ebit", "value": 120.0},
                {"statement_period_end": "2024-06-30", "metric": "npat", "value": 90.0},
                {"statement_period_end": "2024-06-30", "metric": "cash_and_equivalents", "value": 80.0},
                {"statement_period_end": "2024-06-30", "metric": "total_assets", "value": 900.0},
                {"statement_period_end": "2024-06-30", "metric": "total_liabilities", "value": 500.0},
                {"statement_period_end": "2024-06-30", "metric": "total_equity", "value": 400.0},
                {"statement_period_end": "2024-12-31", "metric": "revenue", "value": 1100.0},
                {"statement_period_end": "2024-12-31", "metric": "ebit", "value": 140.0},
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            VAL.run_validation(canonical_df, pd.DataFrame(), pd.DataFrame(), out_dir)

            expected = [
                "validation_period_completeness.csv",
                "validation_metric_presence_matrix.csv",
                "validation_metric_coverage.csv",
                "validation_coverage_flags.csv",
                "validation_economic_flags.csv",
                "validation_risk_stability.csv",
                "validation_summary.json",
            ]
            for name in expected:
                self.assertTrue((out_dir / name).exists(), name)

            completeness = pd.read_csv(out_dir / "validation_period_completeness.csv")
            row_202406 = completeness[completeness["period_end"] == "2024-06-30"].iloc[0]
            self.assertAlmostEqual(float(row_202406["IS_score"]), 1.0)
            self.assertAlmostEqual(float(row_202406["BS_score"]), 1.0)
            self.assertAlmostEqual(float(row_202406["CF_score"]), 0.0)

            flags = pd.read_csv(out_dir / "validation_coverage_flags.csv")
            row_202412 = flags[flags["period_end"] == "2024-12-31"].iloc[0]
            self.assertEqual(int(row_202412["ebit_present_npat_missing"]), 1)

    def test_long_derived_and_long_risk_flags(self):
        canonical_df = pd.DataFrame(
            [
                {"statement_period_end": "2024-03-31", "metric": "ebit", "value": 100.0},
                {"statement_period_end": "2024-03-31", "metric": "net_income", "value": 80.0},
                {"statement_period_end": "2024-06-30", "metric": "ebit", "value": -50.0},
                {"statement_period_end": "2024-06-30", "metric": "net_income", "value": 30.0},
                {"statement_period_end": "2024-09-30", "metric": "ebit", "value": 120.0},
                {"statement_period_end": "2024-09-30", "metric": "net_income", "value": 100.0},
            ]
        )
        derived_df = pd.DataFrame(
            [
                {"statement_period_end": "2024-03-31", "metric": "net_debt_to_ebitda", "value_num": 1.0},
                {"statement_period_end": "2024-06-30", "metric": "net_debt_to_ebitda", "value_num": 5.5},
                {"statement_period_end": "2024-09-30", "metric": "net_debt_to_ebitda", "value_num": 2.0},
                {"statement_period_end": "2024-03-31", "metric": "ebit_margin_pct", "value_num": 40.0},
                {"statement_period_end": "2024-06-30", "metric": "ebit_margin_pct", "value_num": 10.0},
                {"statement_period_end": "2024-09-30", "metric": "ebit_margin_pct", "value_num": 35.0},
            ]
        )
        risk_df = pd.DataFrame(
            [
                {"statement_period_end": "2024-03-31", "signal_name": "leverage_risk_flag", "risk_level": "LOW"},
                {"statement_period_end": "2024-06-30", "signal_name": "leverage_risk_flag", "risk_level": "HIGH"},
                {"statement_period_end": "2024-09-30", "signal_name": "leverage_risk_flag", "risk_level": "LOW"},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            VAL.run_validation(canonical_df, derived_df, risk_df, out_dir)

            economic = pd.read_csv(out_dir / "validation_economic_flags.csv")
            self.assertGreaterEqual(int(economic["ebit_npat_sign_mismatch"].sum()), 1)
            self.assertGreaterEqual(int(economic["leverage_jump_flag"].sum()), 1)
            self.assertGreaterEqual(int(economic["margin_jump_flag"].sum()), 1)

            risk_stability = pd.read_csv(out_dir / "validation_risk_stability.csv")
            row = risk_stability[risk_stability["risk_signal"] == "leverage_risk_flag"].iloc[0]
            self.assertEqual(int(row["high_flicker"]), 1)
            self.assertEqual(int(row["isolated_high"]), 1)

            summary = json.loads((out_dir / "validation_summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["risk_flicker_detected"])

    def test_wide_risk_state_table_supported(self):
        canonical_df = pd.DataFrame(
            [
                {"statement_period_end": "2024-03-31", "metric": "revenue", "value": 1.0},
                {"statement_period_end": "2024-06-30", "metric": "revenue", "value": 1.0},
                {"statement_period_end": "2024-09-30", "metric": "revenue", "value": 1.0},
            ]
        )
        risk_df = pd.DataFrame(
            [
                {"statement_period_end": "2024-03-31", "leverage_risk_flag": 0, "margin_compression_flag": 0},
                {"statement_period_end": "2024-06-30", "leverage_risk_flag": 1, "margin_compression_flag": 0},
                {"statement_period_end": "2024-09-30", "leverage_risk_flag": 0, "margin_compression_flag": 1},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            VAL.run_validation(canonical_df, pd.DataFrame(), risk_df, out_dir)
            risk_stability = pd.read_csv(out_dir / "validation_risk_stability.csv")
            self.assertIn("leverage_risk_flag", set(risk_stability["risk_signal"].tolist()))
            self.assertIn("margin_compression_flag", set(risk_stability["risk_signal"].tolist()))

    def test_cli_alias_columns_and_missing_optional_files(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            canonical_path = td_path / "canonical_alias.csv"
            out_dir = td_path / "out"

            pd.DataFrame(
                [
                    {"period_end": "2024-06-30", "metric_name": "cash_and_equivalents_closing", "value_num": 10.0},
                    {"period_end": "2024-06-30", "metric_name": "npat", "value_num": 5.0},
                    {"period_end": "2024-06-30", "metric_name": "ebit", "value_num": 8.0},
                    {"period_end": "2024-06-30", "metric_name": "revenue", "value_num": 20.0},
                ]
            ).to_csv(canonical_path, index=False)

            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "validation_quality_cycle.py"),
                "--input",
                str(canonical_path),
                "--derived",
                str(td_path / "missing_derived.csv"),
                "--risk",
                str(td_path / "missing_risk.csv"),
                "--out-dir",
                str(out_dir),
            ]
            cp = subprocess.run(cmd, cwd=str(SCRIPTS_DIR), capture_output=True, text=True, check=False)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertTrue((out_dir / "validation_summary.json").exists())

            completeness = pd.read_csv(out_dir / "validation_period_completeness.csv")
            row = completeness.iloc[0]
            self.assertAlmostEqual(float(row["IS_score"]), 1.0)
            self.assertIn("cash", str(row["missing_core_metrics"]))


if __name__ == "__main__":
    unittest.main()
