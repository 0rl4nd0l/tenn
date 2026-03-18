#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cockpit.integrations.db_reader import DbReader  # noqa: E402


class TestCockpitDbDiagnosticQuery(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = DbReader("sqlite:///:memory:")
        with self.reader.engine.begin() as conn:
            conn.exec_driver_sql("create table t (id integer primary key, name text)")
            conn.exec_driver_sql("insert into t(name) values ('alpha'), ('beta')")

    def test_allowlisted_tables_sqlite(self):
        result = self.reader.run_diagnostic_query("tables_sqlite", limit=10)
        self.assertTrue(result.get("ok"), result)
        self.assertIn("columns", result)
        rows = result.get("rows", [])
        table_names = [r.get("table_name") for r in rows if r.get("table_name")]
        self.assertIn("t", table_names)

    def test_allowlisted_tables_alias(self):
        result = self.reader.run_diagnostic_query("tables", limit=10)
        self.assertTrue(result.get("ok"), result)
        self.assertIn("rows", result)

    def test_unknown_query_name_rejected(self):
        result = self.reader.run_diagnostic_query("update t set name='x' where id=1", limit=1)
        self.assertFalse(result.get("ok"))
        self.assertIn("allowed", result)

    def test_empty_query_name_rejected(self):
        result = self.reader.run_diagnostic_query("", limit=1)
        self.assertFalse(result.get("ok"))
        self.assertIn("required", result.get("error", "").lower())


if __name__ == "__main__":
    unittest.main()
