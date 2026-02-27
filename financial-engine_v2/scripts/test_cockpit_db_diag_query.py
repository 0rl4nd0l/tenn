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

    def test_select_query_allowed_and_limited(self):
        result = self.reader.run_diagnostic_query("select id, name from t order by id", limit=1)
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("row_count"), 1)
        self.assertEqual(result.get("rows")[0]["name"], "alpha")

    def test_mutation_keywords_blocked(self):
        result = self.reader.run_diagnostic_query("update t set name='x' where id=1")
        self.assertFalse(result.get("ok"))
        self.assertIn("allowed", str(result.get("error", "")).lower())

    def test_comments_and_multi_statement_blocked(self):
        result = self.reader.run_diagnostic_query("select * from t; select * from t")
        self.assertFalse(result.get("ok"))
        self.assertIn("single-statement", str(result.get("error", "")).lower())


if __name__ == "__main__":
    unittest.main()
