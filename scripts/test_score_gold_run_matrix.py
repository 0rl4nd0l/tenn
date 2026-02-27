import importlib.util
import json
import tempfile
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
MOD = load_module(str(ROOT / "scripts" / "score_gold_run_matrix.py"), "score_gold_run_matrix")


class TestScoreGoldRunMatrix(unittest.TestCase):
    def test_aggregate_scorecards_outputs_expected_files(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            bhp = td_path / "BHP_scorecard.json"
            rio = td_path / "RIO_scorecard.json"

            bhp_payload = {
                "gold_dir": "/tmp/gold/BHP",
                "totals": {"gold_fields": 10, "predicted": 10, "tp": 9, "fp": 1, "fn": 1},
                "taxonomy_counts": {"wrong_period": 1},
                "per_metric": [
                    {"metric": "revenue", "gold_fields": 4, "predicted": 4, "tp": 4},
                    {"metric": "ebitda", "gold_fields": 6, "predicted": 6, "tp": 5},
                ],
            }
            rio_payload = {
                "gold_dir": "/tmp/gold/RIO",
                "totals": {"gold_fields": 8, "predicted": 8, "tp": 8, "fp": 0, "fn": 0},
                "taxonomy_counts": {"wrong_currency": 1},
                "per_metric": [
                    {"metric": "revenue", "gold_fields": 3, "predicted": 3, "tp": 3},
                    {"metric": "ebitda", "gold_fields": 5, "predicted": 5, "tp": 5},
                ],
            }
            bhp.write_text(json.dumps(bhp_payload), encoding="utf-8")
            rio.write_text(json.dumps(rio_payload), encoding="utf-8")

            out = MOD.aggregate_scorecards([bhp, rio], td_path / "out")
            agg = out["aggregate"]
            self.assertEqual(int(agg["totals"]["gold_fields"]), 18)
            self.assertEqual(int(agg["totals"]["tp"]), 17)
            self.assertIn("precision_gte_0_97", agg["gates"])
            self.assertTrue(Path(out["aggregate_scorecard_json"]).exists())
            self.assertTrue(Path(out["aggregate_metric_family_csv"]).exists())
            self.assertTrue(Path(out["aggregate_taxonomy_csv"]).exists())
            self.assertTrue(Path(out["aggregate_ticker_scores_csv"]).exists())


if __name__ == "__main__":
    unittest.main()
