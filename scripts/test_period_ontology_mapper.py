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
MOD = _load_module(str(ROOT / "scripts" / "period_ontology_mapper.py"), "period_ontology_mapper")


class TestPeriodOntologyMapper(unittest.TestCase):
    def test_fy_label_is_canonicalized(self):
        self.assertEqual(MOD.canonicalize_period_label("FY25"), "FY2025")

    def test_h1_fy_label_maps_to_december_period_end(self):
        end, sort = MOD.normalize_period_label("H1 FY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2024-12-31")
        self.assertEqual(sort, "2024-12-31")

    def test_h2_fy_label_maps_to_june_period_end(self):
        end, sort = MOD.normalize_period_label("H2 FY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2025-06-30")
        self.assertEqual(sort, "2025-06-30")

    def test_fiscal_quarter_maps_to_fiscal_period_end(self):
        end, sort = MOD.normalize_period_label("Q3 FY25", allow_doc_date_fallback=False)
        self.assertEqual(end, "2025-03-31")
        self.assertEqual(sort, "2025-03-31")


if __name__ == "__main__":
    unittest.main()
