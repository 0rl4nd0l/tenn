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
MOD = _load_module(str(ROOT / "scripts" / "financial_normalization.py"), "financial_normalization")


class TestFinancialNormalization(unittest.TestCase):
    def test_parse_accounting_number_parentheses_negative(self):
        self.assertEqual(MOD.parse_accounting_number("(123)"), -123)

    def test_parse_accounting_number_plain_positive(self):
        self.assertEqual(MOD.parse_accounting_number("123"), 123)

    def test_parse_accounting_number_signed_negative(self):
        self.assertEqual(MOD.parse_accounting_number("-123"), -123)

    def test_parse_accounting_number_comma_separators(self):
        self.assertEqual(MOD.parse_accounting_number("1,234"), 1234)

    def test_parse_accounting_number_trims_whitespace(self):
        self.assertEqual(MOD.parse_accounting_number("  1,234  "), 1234)

    def test_parse_accounting_number_parentheses_with_commas(self):
        self.assertEqual(MOD.parse_accounting_number("(1,234)"), -1234)

    def test_normalize_financial_value_expense_metric_positive_input(self):
        self.assertEqual(MOD.normalize_financial_value("depreciation_and_amortisation", "123"), -123)

    def test_normalize_financial_value_expense_metric_parentheses_input(self):
        self.assertEqual(MOD.normalize_financial_value("depreciation_and_amortisation", "(123)"), -123)

    def test_normalize_financial_value_non_expense_metric(self):
        self.assertEqual(MOD.normalize_financial_value("revenue", "123"), 123)


if __name__ == "__main__":
    unittest.main()
