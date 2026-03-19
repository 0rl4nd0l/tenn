import importlib.util
import sys
import unittest
from pathlib import Path


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

CLASSIFIER = load_module(str(ROOT / "scripts" / "table_scope_classifier.py"), "table_scope_classifier")
EXTRACT = load_module(str(ROOT / "scripts" / "extract_financial_metrics.py"), "extract_financial_metrics_scope_test")


class BadStringObject:
    def __str__(self):
        raise RuntimeError("string conversion failed")


class TestTableScopeClassifier(unittest.TestCase):
    def test_classify_table_scope_detects_consolidated(self):
        result = CLASSIFIER.classify_table_scope(
            "Consolidated statement of profit or loss",
            "Revenue EBITDA Net profit after tax",
        )
        self.assertEqual(result["table_scope"], "consolidated")
        self.assertGreaterEqual(result["confidence"], 0.8)

    def test_classify_table_scope_detects_segment(self):
        result = CLASSIFIER.classify_table_scope(
            "Operating segment revenue by division",
            "Mining division Energy division Corporate",
        )
        self.assertEqual(result["table_scope"], "segment")
        self.assertGreaterEqual(result["confidence"], 0.8)

    def test_classify_table_scope_detects_geographic(self):
        result = CLASSIFIER.classify_table_scope(
            "Geographic revenue by region",
            "Australia North America Europe",
        )
        self.assertEqual(result["table_scope"], "geographic")
        self.assertGreaterEqual(result["confidence"], 0.8)

    def test_classify_table_scope_handles_none_header(self):
        result = CLASSIFIER.classify_table_scope(None, "Revenue")
        self.assertEqual(result["table_scope"], "unknown")
        self.assertEqual(result["confidence"], 0.0)

    def test_classify_table_scope_handles_none_table_text(self):
        result = CLASSIFIER.classify_table_scope("Revenue", None)
        self.assertEqual(result["table_scope"], "unknown")
        self.assertEqual(result["confidence"], 0.0)

    def test_classify_table_scope_handles_numeric_header(self):
        result = CLASSIFIER.classify_table_scope(123, "Revenue")
        self.assertEqual(result["table_scope"], "unknown")
        self.assertEqual(result["confidence"], 0.0)

    def test_classify_table_scope_handles_object_table_text(self):
        result = CLASSIFIER.classify_table_scope("Revenue", BadStringObject())
        self.assertEqual(result["table_scope"], "unknown")
        self.assertEqual(result["confidence"], 0.0)

    def test_split_rows_by_scope_routes_segment_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "revenue",
                "raw_value": "100",
                "value": 100.0,
                "value_type": "amount",
                "currency": "$",
                "period": "30 June 2025",
                "statement_period": "30 June 2025",
                "statement_period_end": "2025-06-30",
                "line": "Revenue 100",
                "row_label": "Revenue",
                "inside_table": True,
                "source_mode": "docling_table",
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of profit or loss",
                "statement_family": "income_statement",
                "table_statement_type": "income_statement",
                "table_statement_confidence": 0.9,
                "table_scope": "segment",
                "table_scope_confidence": 0.95,
                "table_header_text": "Operating segment revenue by division",
            }
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "non_consolidated_table_scope")
        self.assertEqual(split["context_rows"][0].get("table_scope"), "segment")

    def test_split_rows_by_scope_keeps_canonical_schema_stable(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "revenue",
                "raw_value": "100",
                "value": 100.0,
                "value_type": "amount",
                "currency": "$",
                "period": "30 June 2025",
                "statement_period": "30 June 2025",
                "statement_period_end": "2025-06-30",
                "line": "Revenue 100",
                "row_label": "Revenue",
                "inside_table": True,
                "source_mode": "docling_table",
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of profit or loss",
                "statement_family": "income_statement",
                "table_statement_type": "income_statement",
                "table_statement_confidence": 0.9,
                "table_scope": "consolidated",
                "table_scope_confidence": 0.95,
                "table_header_text": "Consolidated statement of profit or loss",
            }
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertNotIn("table_scope", split["canonical_rows"][0])
        self.assertNotIn("table_scope_confidence", split["canonical_rows"][0])


if __name__ == "__main__":
    unittest.main()
