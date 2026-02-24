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
DERIVED = load_module(str(ROOT / "scripts" / "derived_metrics.py"), "derived_metrics")


class TestDerivedMetrics(unittest.TestCase):
    def test_build_derived_metrics_gates_on_integrity_and_confidence(self):
        rows = [
            {
                "file": "/tmp/docs/AAA/financial_performance/2024-12-31_report.pdf",
                "statement_period_end": "2024-12-31",
                "metric": "revenue",
                "value_type": "amount",
                "value": 1000.0,
                "canonical_confidence_score": 1,
                "integrity_score": 3,
                "integrity_checks_evaluated": 2,
            }
        ]
        out = DERIVED.build_derived_metrics(
            rows,
            min_canonical_confidence=2,
            min_integrity_score=2,
            min_integrity_checks_evaluated=1,
            default_tax_rate=0.30,
        )
        self.assertEqual(out, [])

    def test_build_derived_metrics_computes_ratios(self):
        rows = [
            {
                "file": "/tmp/docs/AAA/financial_performance/2024-12-31_report.pdf",
                "statement_period_end": "2024-12-31",
                "metric": "net_debt",
                "value_type": "amount",
                "value": 200.0,
                "canonical_confidence_score": 3,
                "integrity_score": 3,
                "integrity_checks_evaluated": 2,
            },
            {
                "file": "/tmp/docs/AAA/financial_performance/2024-12-31_report.pdf",
                "statement_period_end": "2024-12-31",
                "metric": "ebitda",
                "value_type": "amount",
                "value": 100.0,
                "canonical_confidence_score": 3,
                "integrity_score": 3,
                "integrity_checks_evaluated": 2,
            },
            {
                "file": "/tmp/docs/AAA/financial_performance/2024-12-31_report.pdf",
                "statement_period_end": "2024-12-31",
                "metric": "free_cash_flow",
                "value_type": "amount",
                "value": 40.0,
                "canonical_confidence_score": 3,
                "integrity_score": 3,
                "integrity_checks_evaluated": 2,
            },
            {
                "file": "/tmp/docs/AAA/financial_performance/2024-12-31_report.pdf",
                "statement_period_end": "2024-12-31",
                "metric": "npat",
                "value_type": "amount",
                "value": 80.0,
                "canonical_confidence_score": 3,
                "integrity_score": 3,
                "integrity_checks_evaluated": 2,
            },
        ]
        out = DERIVED.build_derived_metrics(
            rows,
            min_canonical_confidence=2,
            min_integrity_score=2,
            min_integrity_checks_evaluated=1,
            default_tax_rate=0.30,
        )
        metrics = {r.get("metric"): float(r.get("value_num", 0.0)) for r in out}
        self.assertAlmostEqual(metrics.get("net_debt_to_ebitda"), 2.0)
        self.assertAlmostEqual(metrics.get("fcf_conversion_pct"), 50.0)

    def test_incremental_margin_not_emitted_when_ebit_missing(self):
        rows = [
            {
                "file": "/tmp/docs/AAA/financial_performance/2023-12-31_report.pdf",
                "statement_period_end": "2023-12-31",
                "metric": "revenue",
                "value_type": "amount",
                "value": 100.0,
                "canonical_confidence_score": 3,
                "integrity_score": 3,
                "integrity_checks_evaluated": 1,
            },
            {
                "file": "/tmp/docs/AAA/financial_performance/2024-12-31_report.pdf",
                "statement_period_end": "2024-12-31",
                "metric": "revenue",
                "value_type": "amount",
                "value": 120.0,
                "canonical_confidence_score": 3,
                "integrity_score": 3,
                "integrity_checks_evaluated": 1,
            },
        ]
        out = DERIVED.build_derived_metrics(
            rows,
            min_canonical_confidence=2,
            min_integrity_score=2,
            min_integrity_checks_evaluated=0,
            default_tax_rate=0.30,
        )
        metrics = [str(r.get("metric", "")) for r in out]
        self.assertNotIn("incremental_margin_pct", metrics)


if __name__ == "__main__":
    unittest.main()
