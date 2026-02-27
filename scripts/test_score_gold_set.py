import csv
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
MOD = load_module(str(ROOT / "scripts" / "score_gold_set.py"), "score_gold_set")


class TestScoreGoldSet(unittest.TestCase):
    def _run_case(self, gold_fields, canonical_rows):
        td_path = Path(tempfile.mkdtemp())
        doc_id = "89d1f8dd-f214-4fbb-94b9-01d223aa4fe1"
        gold_dir = td_path / "gold" / "BHP"
        gold_dir.mkdir(parents=True, exist_ok=True)
        gold_doc = {
            "doc_id": doc_id,
            "ticker": "BHP",
            "pdf_sha256": "abc",
            "published_at": "2025-08-19T00:00:00Z",
            "fields": list(gold_fields),
        }
        (gold_dir / f"{doc_id}.json").write_text(json.dumps(gold_doc, indent=2), encoding="utf-8")

        canonical_csv = td_path / "canonical.csv"
        with canonical_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "file",
                    "metric",
                    "metric_base",
                    "value",
                    "raw_value",
                    "currency",
                    "statement_period_end",
                    "statement_period",
                    "statement_scope",
                    "unit_scale",
                ],
            )
            w.writeheader()
            for row in canonical_rows:
                full_row = {
                    "file": f"/tmp/2025-08-19_bhp_{doc_id}.pdf",
                    "metric": "",
                    "metric_base": "",
                    "value": "",
                    "raw_value": "",
                    "currency": "",
                    "statement_period_end": "",
                    "statement_period": "",
                    "statement_scope": "consolidated_statement",
                    "unit_scale": "1",
                }
                full_row.update(row)
                w.writerow(full_row)

        out_dir = td_path / "score_out"
        result = MOD.score_gold_set(
            gold_dir=td_path / "gold",
            canonical_csv=canonical_csv,
            out_dir=out_dir,
        )
        taxonomy = json.loads((out_dir / "taxonomy_counts.json").read_text(encoding="utf-8"))
        return result, taxonomy, out_dir

    def test_wrong_period_currency_and_scope_taxonomy(self):
        gold = [
            {
                "metric": "revenue",
                "period_end": "2025-06-30",
                "period_type": "FY",
                "value": 100.0,
                "unit_scale": 1,
                "currency": "AUD",
                "scope": "group",
            },
            {
                "metric": "ebitda",
                "period_end": "2025-06-30",
                "period_type": "FY",
                "value": 50.0,
                "unit_scale": 1,
                "currency": "AUD",
                "scope": "group",
            },
            {
                "metric": "eps",
                "period_end": "2025-06-30",
                "period_type": "FY",
                "value": 2.0,
                "unit_scale": 1,
                "currency": "AUD",
                "scope": "group",
            },
        ]
        rows = [
            {
                "metric": "revenue",
                "metric_base": "revenue",
                "value": "100",
                "raw_value": "100",
                "currency": "AUD",
                "statement_period_end": "2024-06-30",
                "statement_period": "FY",
                "statement_scope": "consolidated_statement",
            },
            {
                "metric": "ebitda",
                "metric_base": "ebitda",
                "value": "50",
                "raw_value": "50",
                "currency": "USD",
                "statement_period_end": "2025-06-30",
                "statement_period": "FY",
                "statement_scope": "consolidated_statement",
            },
            {
                "metric": "eps",
                "metric_base": "eps",
                "value": "2.0",
                "raw_value": "2.0",
                "currency": "AUD",
                "statement_period_end": "2025-06-30",
                "statement_period": "FY",
                "statement_scope": "parent",
            },
        ]
        _result, taxonomy, _out_dir = self._run_case(gold, rows)
        self.assertEqual(int(taxonomy.get("wrong_period", 0)), 1)
        self.assertEqual(int(taxonomy.get("wrong_currency", 0)), 1)
        self.assertEqual(int(taxonomy.get("wrong_scope", 0)), 1)

    def test_wrong_unit_scale_taxonomy(self):
        gold = [
            {
                "metric": "revenue",
                "period_end": "2025-06-30",
                "period_type": "FY",
                "value": 1200000000.0,
                "unit_scale": 1,
                "currency": "AUD",
                "scope": "group",
            }
        ]
        rows = [
            {
                "metric": "revenue",
                "metric_base": "revenue",
                "value": "1200",
                "raw_value": "1200",
                "currency": "AUD",
                "statement_period_end": "2025-06-30",
                "statement_period": "FY",
                "statement_scope": "consolidated_statement",
            }
        ]
        _result, taxonomy, _out_dir = self._run_case(gold, rows)
        self.assertEqual(int(taxonomy.get("wrong_unit_scale", 0)), 1)

    def test_duplicate_collision_taxonomy_and_doc_breakdown(self):
        gold = [
            {
                "metric": "net_income",
                "period_end": "2025-06-30",
                "period_type": "FY",
                "value": 100.0,
                "unit_scale": 1,
                "currency": "AUD",
                "scope": "group",
            }
        ]
        rows = [
            {
                "metric": "net_income",
                "metric_base": "net_income",
                "value": "70",
                "raw_value": "70",
                "currency": "AUD",
                "statement_period_end": "2025-06-30",
                "statement_period": "FY",
                "statement_scope": "consolidated_statement",
            },
            {
                "metric": "net_income",
                "metric_base": "net_income",
                "value": "230",
                "raw_value": "230",
                "currency": "AUD",
                "statement_period_end": "2025-06-30",
                "statement_period": "FY",
                "statement_scope": "consolidated_statement",
            },
        ]
        result, taxonomy, out_dir = self._run_case(gold, rows)
        self.assertEqual(int(taxonomy.get("duplicate_collision", 0)), 1)
        self.assertTrue((out_dir / "doc_breakdown.csv").exists())
        self.assertIn("doc_breakdown_csv", result)

    def test_emits_standard_outputs(self):
        gold = [
            {
                "metric": "revenue",
                "period_end": "2025-06-30",
                "period_type": "FY",
                "value": 100.0,
                "unit_scale": 1,
                "currency": "AUD",
                "scope": "group",
            }
        ]
        rows = [
            {
                "metric": "revenue",
                "metric_base": "revenue",
                "value": "100",
                "raw_value": "100",
                "currency": "AUD",
                "statement_period_end": "2025-06-30",
                "statement_period": "FY",
                "statement_scope": "consolidated_statement",
            }
        ]
        _result, _taxonomy, out_dir = self._run_case(gold, rows)
        self.assertTrue((out_dir / "scorecard.json").exists())
        self.assertTrue((out_dir / "scorecard.csv").exists())
        self.assertTrue((out_dir / "doc_breakdown.csv").exists())
        self.assertTrue((out_dir / "taxonomy_counts.json").exists())
        self.assertTrue((out_dir / "failures.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
