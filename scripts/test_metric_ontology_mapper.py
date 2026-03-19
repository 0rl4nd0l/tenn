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
MOD = _load_module(str(ROOT / "scripts" / "metric_ontology_mapper.py"), "metric_ontology_mapper")


class TestMetricOntologyMapper(unittest.TestCase):
    def test_turnover_maps_to_revenue(self):
        self.assertEqual(MOD.canonicalize_metric_name("Turnover"), "revenue")

    def test_capex_maps_to_capital_expenditure(self):
        row = {"metric": "capex", "metric_base": "capex"}
        MOD.canonicalize_metric_row(row)
        self.assertEqual(str(row.get("metric")), "capital_expenditure")
        self.assertEqual(str(row.get("metric_base")), "capital_expenditure")

    def test_canonical_metric_is_preserved(self):
        self.assertEqual(MOD.canonicalize_metric_name("ebitda"), "ebitda")


if __name__ == "__main__":
    unittest.main()
