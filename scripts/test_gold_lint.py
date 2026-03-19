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
MOD = load_module(str(ROOT / "scripts" / "gold_lint.py"), "gold_lint")


class TestGoldLint(unittest.TestCase):
    def test_lint_flags_unknown_currency_and_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            target = td_path / "gold" / "BHP"
            target.mkdir(parents=True, exist_ok=True)
            doc_id = "89d1f8dd-f214-4fbb-94b9-01d223aa4fe1"
            payload = {
                "doc_id": doc_id,
                "ticker": "BHP",
                "pdf_sha256": "abc",
                "published_at": "2025-08-19",
                "fields": [
                    {
                        "metric": "revenue",
                        "period_end": "2025-06-30",
                        "period_type": "FY",
                        "value": 100,
                        "unit_scale": 1,
                        "currency": "UNKNOWN",
                        "scope": "group",
                    },
                    {
                        "metric": "revenue",
                        "period_end": "2025-06-30",
                        "period_type": "FY",
                        "value": 101,
                        "unit_scale": 1,
                        "currency": "AUD",
                        "scope": "group",
                    },
                ],
            }
            (target / f"{doc_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            report = MOD.lint_gold_dir(td_path / "gold")
            self.assertFalse(bool(report["ok"]))
            types = {issue["type"] for issue in report["issues"]}
            self.assertIn("unknown_currency", types)
            self.assertIn("duplicate_metric_period_scope", types)

    def test_lint_passes_clean_file(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            target = td_path / "gold" / "BHP"
            target.mkdir(parents=True, exist_ok=True)
            doc_id = "89d1f8dd-f214-4fbb-94b9-01d223aa4fe1"
            payload = {
                "doc_id": doc_id,
                "ticker": "BHP",
                "pdf_sha256": "abc",
                "published_at": "2025-08-19",
                "fields": [
                    {
                        "metric": "revenue",
                        "period_end": "2025-06-30",
                        "period_type": "FY",
                        "value": 100,
                        "unit_scale": 1,
                        "currency": "AUD",
                        "scope": "group",
                    }
                ],
            }
            (target / f"{doc_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            report = MOD.lint_gold_dir(td_path / "gold")
            self.assertTrue(bool(report["ok"]))
            self.assertEqual(int(report["issues_count"]), 0)


if __name__ == "__main__":
    unittest.main()
