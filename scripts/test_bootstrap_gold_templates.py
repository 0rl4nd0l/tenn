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
MOD = load_module(str(ROOT / "scripts" / "bootstrap_gold_templates.py"), "bootstrap_gold_templates")


class TestBootstrapGoldTemplates(unittest.TestCase):
    def test_bootstrap_creates_template(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            canonical = td_path / "canonical.csv"
            rows = [
                {
                    "file": "/tmp/data/asx/docs/BHP/financial_performance/2025-08-19_doc_89d1f8dd-f214-4fbb-94b9-01d223aa4fe1.pdf",
                    "metric": "revenue",
                    "metric_base": "revenue",
                    "value": "100",
                    "currency": "AUD",
                    "statement_period_end": "2025-06-30",
                    "statement_period": "FY2025",
                    "statement_scope": "consolidated_statement",
                    "statement_family": "income_statement",
                    "page_number": "1",
                    "table_page": "1",
                    "table_id": "t1",
                }
            ]
            with canonical.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)

            out_dir = td_path / "gold"
            result = MOD.bootstrap_templates(
                canonical_csv=canonical,
                out_dir=out_dir,
                tickers=["BHP"],
                docs_per_ticker=12,
                overwrite=False,
            )

            self.assertEqual(int(result["created"]), 1)
            target = out_dir / "BHP" / "89d1f8dd-f214-4fbb-94b9-01d223aa4fe1.json"
            self.assertTrue(target.exists())
            obj = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(obj["ticker"], "BHP")
            self.assertEqual(obj["fields"][0]["metric"], "revenue")

    def test_bootstrap_infers_single_ticker_for_pdf_subset_paths(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            canonical = td_path / "canonical.csv"
            rows = [
                {
                    "file": "/tmp/reports/expansion_runs/run_1/NST/pdf_subset/2025-08-21_annual-report_2ea617f2-46dd-45c6-8c1c-56b8a99eedb4.pdf",
                    "metric": "total_assets",
                    "metric_base": "total_assets",
                    "value": "1000",
                    "currency": "AUD",
                    "statement_period_end": "2025-06-30",
                    "statement_period": "FY2025",
                    "statement_scope": "consolidated_statement",
                    "statement_family": "balance_sheet",
                    "page_number": "10",
                    "table_page": "10",
                    "table_id": "t10",
                }
            ]
            with canonical.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)

            out_dir = td_path / "gold"
            result = MOD.bootstrap_templates(
                canonical_csv=canonical,
                out_dir=out_dir,
                tickers=["NST"],
                docs_per_ticker=12,
                overwrite=False,
            )

            self.assertEqual(int(result["created"]), 1)
            target = out_dir / "NST" / "2ea617f2-46dd-45c6-8c1c-56b8a99eedb4.json"
            self.assertTrue(target.exists())
            obj = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(obj["ticker"], "NST")
            self.assertEqual(obj["fields"][0]["metric"], "total_assets")


if __name__ == "__main__":
    unittest.main()
