#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

try:
    from cockpit.integrations.db_reader import DbReader  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - dependency optional in local test env
    DbReader = None  # type: ignore[assignment]


@unittest.skipIf(DbReader is None, "sqlalchemy is not installed in this environment")
class CockpitDbReaderQualitySignalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = DbReader("sqlite:///:memory:")
        with self.reader.engine.begin() as conn:
            conn.exec_driver_sql(
                """
                create table documents (
                    document_id text primary key,
                    ticker text,
                    published_at text,
                    title text
                )
                """
            )
            conn.exec_driver_sql(
                """
                create table extraction_runs (
                    run_id integer primary key,
                    document_id text,
                    status text,
                    error text,
                    created_at text
                )
                """
            )
            conn.exec_driver_sql(
                """
                create table asx_periodic_financials (
                    ticker text,
                    period_end text,
                    period_type text,
                    confidence_metrics real,
                    source_document_id text
                )
                """
            )
            conn.exec_driver_sql(
                """
                insert into documents(document_id, ticker, published_at, title) values
                ('doc-bhp', 'BHP', '2026-02-18', 'BHP Interim Results'),
                ('doc-rio', 'RIO', '2026-02-17', 'RIO Quarterly Update')
                """
            )
            conn.exec_driver_sql(
                """
                insert into extraction_runs(run_id, document_id, status, error, created_at) values
                (1, 'doc-bhp', 'failed', 'table parse failed', '2026-02-18T10:00:00Z'),
                (2, 'doc-rio', 'failed', 'ocr timeout', '2026-02-17T09:00:00Z'),
                (3, 'doc-bhp', 'completed', '', '2026-02-18T11:00:00Z')
                """
            )
            conn.exec_driver_sql(
                """
                insert into asx_periodic_financials(ticker, period_end, period_type, confidence_metrics, source_document_id) values
                ('BHP', '2025-12-31', 'HY', 0.22, 'doc-bhp'),
                ('RIO', '2025-12-31', 'HY', 0.31, 'doc-rio'),
                ('BHP', '2024-12-31', 'FY', 0.91, 'doc-bhp')
                """
            )

    def test_get_extraction_failures_ticker_filter(self):
        rows = self.reader.get_extraction_failures(limit=10, ticker="BHP")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.get("ticker"), "BHP")
        self.assertEqual(row.get("title"), "BHP Interim Results")
        self.assertEqual(row.get("status"), "failed")

    def test_get_low_confidence_financials_ticker_filter(self):
        rows = self.reader.get_low_confidence_financials(threshold=0.4, limit=10, ticker="RIO")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("ticker"), "RIO")
        self.assertLess(float(rows[0].get("confidence_metrics")), 0.4)

    def test_calls_without_ticker_preserve_legacy_behavior(self):
        failures = self.reader.get_extraction_failures(limit=10)
        low_conf = self.reader.get_low_confidence_financials(threshold=0.4, limit=10)
        self.assertEqual(len(failures), 2)
        self.assertEqual(len(low_conf), 2)


if __name__ == "__main__":
    unittest.main()
