import importlib.util
import sys
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
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

EXTRACT = _load_module(str(ROOT / "scripts" / "extract_financial_metrics.py"), "extract_financial_metrics_tsr_identity")


class TestTsrTableIdentity(unittest.TestCase):
    def _row(
        self,
        *,
        table_scope: str,
        value: float,
        confidence: float,
        file_path: str = "/tmp/demo.pdf",
        line_no: int = 1,
        table_scope_confidence: float = 0.8,
    ):
        return {
            "file": file_path,
            "source_file": file_path,
            "metric": "revenue",
            "metric_base": "revenue",
            "raw_value": str(value),
            "value": value,
            "value_type": "amount",
            "currency": "AUD",
            "period": "30 June 2023",
            "statement_period": "30 June 2023",
            "statement_period_end": "2023-06-30",
            "period_end": "2023-06-30",
            "line": f"Revenue {value}",
            "line_no": line_no,
            "row_label": "Revenue",
            "inside_table": True,
            "source_mode": "docling_table",
            "statement_scope": "consolidated_statement",
            "statement_title": "Consolidated statement of profit or loss",
            "statement_family": "income_statement",
            "table_statement_type": "income_statement",
            "table_statement_confidence": 0.9,
            "table_scope": table_scope,
            "table_scope_confidence": table_scope_confidence,
            "table_header_text": "Revenue FY2023",
            "confidence": confidence,
            "_table_identity": {
                "statement_type": "income_statement",
                "table_scope": table_scope,
                "periods": ["FY2023"],
            },
        }

    def test_consolidated_row_survives_over_segment_table(self):
        rows = [
            self._row(table_scope="consolidated", value=10000.0, confidence=0.5, line_no=1),
            self._row(table_scope="segment", value=4000.0, confidence=0.9, line_no=2),
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertEqual(float(split["canonical_rows"][0]["value"]), 10000.0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertIn(split["context_rows"][0]["context_reason"], {"non_consolidated_table_scope", "duplicate_metric_non_consolidated_table"})

    def test_multiple_segment_tables_are_demoted_to_context(self):
        rows = [
            self._row(table_scope="segment", value=4000.0, confidence=0.8, line_no=1),
            self._row(table_scope="segment", value=6000.0, confidence=0.9, line_no=2),
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 2)
        self.assertTrue(all(row["context_reason"] == "non_consolidated_table_scope" for row in split["context_rows"]))

    def test_consolidated_preferred_over_unknown_duplicate(self):
        rows = [
            self._row(table_scope="consolidated", value=10000.0, confidence=0.4, line_no=1),
            self._row(table_scope="unknown", value=9500.0, confidence=0.9, line_no=2, table_scope_confidence=0.0),
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertEqual(float(split["canonical_rows"][0]["value"]), 10000.0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0]["context_reason"], "duplicate_metric_non_consolidated_table")
        self.assertEqual(split["diagnostics"]["tsr_duplicate_rows_demoted"], 1)
        self.assertNotIn("_table_identity", split["canonical_rows"][0])
        self.assertNotIn("_table_identity", split["context_rows"][0])

    def test_highest_confidence_unknown_row_retained_when_no_consolidated_table_exists(self):
        rows = [
            self._row(table_scope="unknown", value=10000.0, confidence=0.2, line_no=1, table_scope_confidence=0.0),
            self._row(table_scope="unknown", value=12000.0, confidence=0.9, line_no=2, table_scope_confidence=0.0),
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertEqual(float(split["canonical_rows"][0]["value"]), 12000.0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0]["context_reason"], "duplicate_metric_non_consolidated_table")
        self.assertEqual(split["diagnostics"]["tsr_duplicate_rows_demoted"], 1)


if __name__ == "__main__":
    unittest.main()
