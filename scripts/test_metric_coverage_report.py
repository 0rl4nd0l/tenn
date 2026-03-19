import importlib.util
import sqlite3
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
COVER = load_module(str(ROOT / "scripts" / "metric_coverage_report.py"), "metric_coverage_report")


class TestMetricCoverageReport(unittest.TestCase):
    def _mk_sqlite(self) -> Path:
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        Path(path).unlink(missing_ok=True)
        db_path = Path(path)
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE financial_statement_integrity (
                    file TEXT NOT NULL,
                    statement_period_end TEXT NOT NULL,
                    company TEXT NOT NULL DEFAULT '',
                    integrity_score INTEGER NOT NULL DEFAULT 0,
                    integrity_checks_evaluated INTEGER NOT NULL DEFAULT 0,
                    integrity_checks_passed INTEGER NOT NULL DEFAULT 0,
                    integrity_score_max INTEGER NOT NULL DEFAULT 4,
                    data_anomaly_level TEXT NOT NULL DEFAULT 'UNKNOWN',
                    PRIMARY KEY (file, statement_period_end)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE derived_metrics (
                    company TEXT NOT NULL DEFAULT '',
                    statement_period_end TEXT NOT NULL DEFAULT '',
                    metric TEXT NOT NULL,
                    source_file TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE financial_risk_signals (
                    file TEXT NOT NULL,
                    statement_period_end TEXT NOT NULL,
                    company TEXT NOT NULL DEFAULT '',
                    signal_name TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        return db_path

    def test_build_period_matrix_uses_metric_base_and_sqlite_indexes(self):
        db_path = self._mk_sqlite()
        try:
            rows = [
                {
                    "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                    "company": "",
                    "statement_period_end": "2024-06-30",
                    "metric": "cash_and_equivalents_closing",
                    "metric_base": "cash_and_equivalents",
                },
                {
                    "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                    "company": "",
                    "statement_period_end": "2024-06-30",
                    "metric": "revenue",
                    "metric_base": "revenue",
                },
                {
                    "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                    "company": "",
                    "statement_period_end": "2024-06-30",
                    "metric": "ebit",
                    "metric_base": "ebit",
                },
                {
                    "file": "/tmp/docs/BHP/financial_performance/b.pdf",
                    "company": "",
                    "statement_period_end": "2024-12-31",
                    "metric": "revenue",
                    "metric_base": "revenue",
                },
            ]
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO financial_statement_integrity "
                    "(file, statement_period_end, company, integrity_score, integrity_checks_evaluated, integrity_checks_passed, integrity_score_max, data_anomaly_level) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/tmp/docs/BHP/financial_performance/a.pdf", "2024-06-30", "BHP", 3, 2, 2, 4, "LOW"),
                )
                cur.execute(
                    "INSERT INTO financial_statement_integrity "
                    "(file, statement_period_end, company, integrity_score, integrity_checks_evaluated, integrity_checks_passed, integrity_score_max, data_anomaly_level) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/tmp/docs/BHP/financial_performance/b.pdf", "2024-12-31", "BHP", 1, 0, 0, 4, "UNKNOWN"),
                )
                cur.execute(
                    "INSERT INTO derived_metrics (company, statement_period_end, metric, source_file) VALUES (?, ?, ?, ?)",
                    ("BHP", "2024-06-30", "ebit_margin_pct", "/tmp/docs/BHP/financial_performance/a.pdf"),
                )
                cur.execute(
                    "INSERT INTO derived_metrics (company, statement_period_end, metric, source_file) VALUES (?, ?, ?, ?)",
                    ("BHP", "2024-06-30", "net_debt_to_ebitda", "/tmp/docs/BHP/financial_performance/a.pdf"),
                )
                cur.execute(
                    "INSERT INTO financial_risk_signals (file, statement_period_end, company, signal_name) VALUES (?, ?, ?, ?)",
                    ("/tmp/docs/BHP/financial_performance/a.pdf", "2024-06-30", "BHP", "net_debt_to_ebitda_risk"),
                )
                conn.commit()
            finally:
                conn.close()

            metrics = ["revenue", "ebit", "cash_and_equivalents", "total_debt"]
            period_rows = COVER.build_period_matrix(rows, metrics=metrics, company_filter=set(), sqlite_path=db_path)
            self.assertEqual(len(period_rows), 2)

            by_period = {r["statement_period_end"]: r for r in period_rows}
            p1 = by_period["2024-06-30"]
            self.assertEqual(p1["company"], "BHP")
            self.assertEqual(p1["has_revenue"], 1)
            self.assertEqual(p1["has_ebit"], 1)
            self.assertEqual(p1["has_cash_and_equivalents"], 1)
            self.assertEqual(p1["has_total_debt"], 0)
            self.assertEqual(p1["integrity_evaluable"], 1)
            self.assertEqual(p1["derived_ready"], 1)
            self.assertEqual(p1["risk_ready"], 1)
            self.assertEqual(p1["risk_signaled"], 1)

            p2 = by_period["2024-12-31"]
            self.assertEqual(p2["has_revenue"], 1)
            self.assertEqual(p2["has_ebit"], 0)
            self.assertEqual(p2["integrity_evaluable"], 0)
            self.assertEqual(p2["derived_ready"], 0)
            self.assertEqual(p2["risk_ready"], 0)
            self.assertEqual(p2["risk_signaled"], 0)
        finally:
            db_path.unlink(missing_ok=True)

    def test_build_company_summary_computes_percentages(self):
        period_rows = [
            {
                "company": "BHP",
                "statement_period_end": "2024-06-30",
                "period_sort_key": 20240630,
                "has_revenue": 1,
                "has_ebit": 1,
                "integrity_evaluable": 1,
                "derived_ready": 1,
                "risk_ready": 1,
                "risk_signaled": 0,
            },
            {
                "company": "BHP",
                "statement_period_end": "2024-12-31",
                "period_sort_key": 20241231,
                "has_revenue": 1,
                "has_ebit": 0,
                "integrity_evaluable": 0,
                "derived_ready": 0,
                "risk_ready": 0,
                "risk_signaled": 1,
            },
        ]
        summaries = COVER.build_company_summary(period_rows, ["revenue", "ebit"])
        self.assertEqual(len(summaries), 1)
        s = summaries[0]
        self.assertEqual(s["company"], "BHP")
        self.assertEqual(s["total_periods"], 2)
        self.assertEqual(s["revenue__periods"], 2)
        self.assertEqual(s["ebit__periods"], 1)
        self.assertEqual(s["revenue__pct"], 100.0)
        self.assertEqual(s["ebit__pct"], 50.0)
        self.assertEqual(s["integrity_evaluable_pct"], 50.0)
        self.assertEqual(s["derived_ready_pct"], 50.0)
        self.assertEqual(s["risk_ready_pct"], 50.0)
        self.assertEqual(s["risk_signaled_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()

