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
MOD = _load_module(str(ROOT / "scripts" / "table_structure_reconciliation.py"), "table_structure_reconciliation")


class TestTableStructureReconciliation(unittest.TestCase):
    def test_detect_year_columns_recognizes_fiscal_headers(self):
        columns = ["Metric", "FY24", "FY25"]
        self.assertEqual(MOD.detect_year_columns(columns), [1, 2])

    def test_repair_column_shifts_left_shifts_year_values(self):
        rows = [
            ["Revenue", "", "100", "90"],
            ["EBITDA", "", "40", "35"],
        ]
        repaired_rows, repaired_count = MOD.repair_column_shifts(rows, [1, 2, 3])
        self.assertEqual(repaired_count, 2)
        self.assertEqual(repaired_rows[0], ["Revenue", "100", "90", ""])
        self.assertEqual(repaired_rows[1], ["EBITDA", "40", "35", ""])


if __name__ == "__main__":
    unittest.main()
