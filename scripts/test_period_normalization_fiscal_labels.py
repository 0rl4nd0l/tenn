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
EXTRACT = _load_module(str(ROOT / "scripts" / "extract_financial_metrics.py"), "extract_financial_metrics")


class TestPeriodNormalizationFiscalLabels(unittest.TestCase):
    def test_fy_label_maps_to_june_year_end(self):
        end, sort = EXTRACT.normalize_period_for_db("FY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2025-06-30")
        self.assertEqual(sort, "2025-06-30")

    def test_hy_label_maps_to_prior_december_year_end(self):
        end, sort = EXTRACT.normalize_period_for_db("HY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2024-12-31")
        self.assertEqual(sort, "2024-12-31")

    def test_h1_fy_label_maps_to_prior_december_year_end(self):
        end, sort = EXTRACT.normalize_period_for_db("H1 FY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2024-12-31")
        self.assertEqual(sort, "2024-12-31")

    def test_h2_fy_label_maps_to_june_year_end(self):
        end, sort = EXTRACT.normalize_period_for_db("H2 FY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2025-06-30")
        self.assertEqual(sort, "2025-06-30")


if __name__ == "__main__":
    unittest.main()
