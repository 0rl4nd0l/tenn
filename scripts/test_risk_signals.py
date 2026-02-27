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
RISK = load_module(str(ROOT / "scripts" / "risk_signals.py"), "risk_signals")


def mk_row(company: str, period: str, sort_key: int, metric: str, value: float, file_path: str) -> dict:
    return {
        "company": company,
        "statement_period_end": period,
        "period_sort_key": sort_key,
        "metric": metric,
        "value_num": value,
        "source_file": file_path,
        "canonical_confidence_floor": 3,
        "integrity_score": 3,
        "integrity_checks_evaluated": 1,
        "data_anomaly_level": "LOW",
    }


class TestRiskSignals(unittest.TestCase):
    def test_leverage_thresholds_and_critical_non_positive_ebitda(self):
        th = RISK.thresholds_for_profile("institutional")
        rows = [
            mk_row("AAA", "2023-12-31", 20231231, "net_debt_to_ebitda", 1.8, "f1.pdf"),
            mk_row("AAA", "2024-06-30", 20240630, "net_debt_to_ebitda", 2.4, "f2.pdf"),
            mk_row("AAA", "2024-12-31", 20241231, "net_debt_to_ebitda", 4.2, "f3.pdf"),
            mk_row("AAA", "2025-06-30", 20250630, "ebitda_amount", -5.0, "f4.pdf"),
        ]
        signals = RISK.build_risk_signals(rows, th)
        lev = {
            (s["statement_period_end"], s["signal_name"]): s["risk_level"]
            for s in signals
            if s.get("signal_name") == "net_debt_to_ebitda_risk"
        }
        self.assertEqual(lev[("2023-12-31", "net_debt_to_ebitda_risk")], "LOW")
        self.assertEqual(lev[("2024-06-30", "net_debt_to_ebitda_risk")], "MEDIUM")
        self.assertEqual(lev[("2024-12-31", "net_debt_to_ebitda_risk")], "HIGH")
        self.assertEqual(lev[("2025-06-30", "net_debt_to_ebitda_risk")], "CRITICAL")

    def test_cash_runway_thresholds(self):
        th = RISK.thresholds_for_profile("institutional")
        rows = [
            mk_row("BBB", "2024-03-31", 20240331, "cash_runway_periods", 1.5, "r1.pdf"),
            mk_row("BBB", "2024-06-30", 20240630, "cash_runway_periods", 3.0, "r2.pdf"),
            mk_row("BBB", "2024-09-30", 20240930, "cash_runway_periods", 5.5, "r3.pdf"),
        ]
        signals = RISK.build_risk_signals(rows, th)
        runway = {
            s["statement_period_end"]: s["risk_level"]
            for s in signals
            if s.get("signal_name") == "cash_runway_risk"
        }
        self.assertEqual(runway["2024-03-31"], "CRITICAL")
        self.assertEqual(runway["2024-06-30"], "HIGH")
        self.assertEqual(runway["2024-09-30"], "LOW")

    def test_margin_compression_and_structural_decline(self):
        th = RISK.thresholds_for_profile("institutional")
        rows = [
            mk_row("CCC", "2023-12-31", 20231231, "ebit_margin_pct", 30.0, "m1.pdf"),
            mk_row("CCC", "2024-06-30", 20240630, "ebit_margin_pct", 25.0, "m2.pdf"),
            mk_row("CCC", "2024-12-31", 20241231, "ebit_margin_pct", 21.0, "m3.pdf"),
        ]
        signals = RISK.build_risk_signals(rows, th)
        names_by_period = {}
        for s in signals:
            names_by_period.setdefault(s["statement_period_end"], set()).add(s["signal_name"])
        self.assertIn("ebit_margin_compression", names_by_period.get("2024-06-30", set()))
        self.assertIn("ebit_margin_compression", names_by_period.get("2024-12-31", set()))
        self.assertIn("ebit_margin_structural_compression", names_by_period.get("2024-12-31", set()))

    def test_margin_compression_skips_implausible_unit_mismatch(self):
        th = RISK.thresholds_for_profile("institutional")
        rows = [
            mk_row("DDD", "2023-12-31", 20231231, "ebit_margin_pct", 25.0, "u1.pdf"),
            mk_row("DDD", "2024-12-31", 20241231, "ebit_margin_pct", -1000000.0, "u2.pdf"),
        ]
        signals = RISK.build_risk_signals(rows, th)
        names = [str(s.get("signal_name", "")) for s in signals]
        self.assertNotIn("ebit_margin_compression", names)
        self.assertNotIn("ebit_margin_structural_compression", names)


if __name__ == "__main__":
    unittest.main()
