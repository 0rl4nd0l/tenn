import importlib.util
import sys
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
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

CLASSIFIER = load_module(str(SCRIPTS_DIR / "statement_classifier.py"), "statement_classifier")


class TestStatementClassifier(unittest.TestCase):
    def test_classify_income_statement_keywords(self):
        result = CLASSIFIER.classify_table_statement(
            [
                ["Item", "FY25", "FY24"],
                ["Revenue", "120", "110"],
                ["Gross profit", "55", "47"],
                ["Operating profit", "21", "18"],
                ["Net profit", "15", "12"],
            ]
        )

        self.assertEqual(result["statement_type"], "income_statement")
        self.assertGreaterEqual(result["confidence"], 0.6)

    def test_classify_balance_sheet_keywords(self):
        result = CLASSIFIER.classify_table_statement(
            [
                ["Item", "2025", "2024"],
                ["Total assets", "250", "220"],
                ["Total liabilities", "140", "125"],
                ["Equity", "110", "95"],
                ["Retained earnings", "60", "51"],
            ]
        )

        self.assertEqual(result["statement_type"], "balance_sheet")
        self.assertGreaterEqual(result["confidence"], 0.6)

    def test_classify_cash_flow_keywords(self):
        result = CLASSIFIER.classify_table_statement(
            [
                ["Item", "FY25", "FY24"],
                ["Operating cash flow", "42", "39"],
                ["Investing activities", "(15)", "(11)"],
                ["Financing activities", "(10)", "(9)"],
                ["Net change in cash", "17", "19"],
            ]
        )

        self.assertEqual(result["statement_type"], "cash_flow_statement")
        self.assertGreaterEqual(result["confidence"], 0.6)

    def test_classify_notes_when_table_looks_like_disclosure(self):
        result = CLASSIFIER.classify_table_statement(
            [
                ["Note", "Description", "Amount"],
                ["12", "Contingent liabilities disclosure", "5"],
                ["13", "Commitments disclosure", "8"],
            ]
        )

        self.assertEqual(result["statement_type"], "notes")
        self.assertGreater(result["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
