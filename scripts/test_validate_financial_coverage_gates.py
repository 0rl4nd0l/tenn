import importlib.util
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
MOD = _load_module(str(ROOT / "scripts" / "validate_financial_coverage_gates.py"), "validate_financial_coverage_gates")


class TestValidateFinancialCoverageGates(unittest.TestCase):
    @staticmethod
    def _row(
        period_end: str,
        metric: str,
        period_type: str = "annual",
        company: str = "BHP",
        file_date: str = "2025-08-19",
    ):
        return {
            "company": company,
            "file": f"/tmp/{file_date}_sample.pdf",
            "statement_period_end": period_end,
            "period_type": period_type,
            "metric": metric,
            "metric_base": metric,
            "value": 1.0,
        }

    def test_required_metric_anchor_ignores_guidance_only_future_periods(self):
        rows = [
            self._row("2025-06-30", "revenue"),
            self._row("2025-06-30", "net_income"),
            self._row("2025-06-30", "total_assets"),
            self._row("2025-06-30", "total_liabilities"),
            self._row("2024-06-30", "revenue", file_date="2024-08-20"),
            self._row("2024-06-30", "net_income", file_date="2024-08-20"),
            self._row("2024-06-30", "total_assets", file_date="2024-08-20"),
            self._row("2024-06-30", "total_liabilities", file_date="2024-08-20"),
            self._row("2032-12-31", "guidance", file_date="2022-08-16"),
            self._row("2030-12-31", "revenue", file_date="2022-08-16"),
        ]
        report = MOD.build_report(rows, required_metrics=[], period_types=["annual"], recent_periods=2, coverage_profile="resources")
        checked_periods = [c["statement_period_end"] for c in report["all_checks"]]
        self.assertEqual(checked_periods, ["2025-06-30", "2024-06-30"])
        self.assertTrue(all(c.get("period_selection_source") == "required_metric_anchor_min_count" for c in report["all_checks"]))
        self.assertTrue(report["gate_pass"])

    def test_all_metrics_fallback_when_no_anchor_period_exists(self):
        rows = [
            self._row("2032-12-31", "guidance"),
            self._row("2027-12-31", "capex"),
        ]
        report = MOD.build_report(rows, required_metrics=[], period_types=["annual"], recent_periods=1, coverage_profile="resources")
        self.assertEqual(report["checks_total"], 1)
        check = report["all_checks"][0]
        self.assertEqual(check["statement_period_end"], "2032-12-31")
        self.assertEqual(check.get("period_selection_source"), "all_metrics_fallback")
        self.assertFalse(check["check_pass"])
        self.assertFalse(report["gate_pass"])

    def test_merge_point_in_time_stock_metrics_for_flow_period_checks(self):
        rows = [
            self._row("2024-06-30", "revenue", period_type="annual", file_date="2024-08-20"),
            self._row("2024-06-30", "net_income", period_type="annual", file_date="2024-08-20"),
            self._row("2024-06-30", "total_assets", period_type="point_in_time", file_date="2024-08-20"),
            self._row("2024-06-30", "total_liabilities", period_type="point_in_time", file_date="2024-08-20"),
        ]
        report = MOD.build_report(rows, required_metrics=[], period_types=["annual"], recent_periods=1, coverage_profile="resources")
        self.assertEqual(report["checks_total"], 1)
        check = report["all_checks"][0]
        self.assertEqual(check["statement_period_end"], "2024-06-30")
        self.assertEqual(check["missing_metrics"], [])
        self.assertTrue(check["check_pass"])
        self.assertTrue(report["gate_pass"])

    def test_anchor_requires_min_required_metric_count(self):
        rows = [
            self._row("2025-06-30", "revenue", period_type="annual", file_date="2025-08-20"),
            self._row("2024-06-30", "revenue", period_type="annual", file_date="2024-08-20"),
            self._row("2024-06-30", "net_income", period_type="annual", file_date="2024-08-20"),
        ]
        report = MOD.build_report(rows, required_metrics=[], period_types=["annual"], recent_periods=1, coverage_profile="resources")
        self.assertEqual(report["checks_total"], 1)
        check = report["all_checks"][0]
        self.assertEqual(check["statement_period_end"], "2024-06-30")
        self.assertEqual(check.get("period_selection_source"), "required_metric_anchor_min_count")


if __name__ == "__main__":
    unittest.main()
