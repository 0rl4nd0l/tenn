import importlib.util
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
MOD = load_module(str(ROOT / "scripts" / "provenance_contract.py"), "provenance_contract")


class TestProvenanceContract(unittest.TestCase):
    def test_normalize_candidate_row_infers_doc_id_and_camelot_provenance(self):
        row = {
            "file": "/tmp/2025-08-19_bhp-annual_89d1f8dd-f214-4fbb-94b9-01d223aa4fe1.pdf",
            "metric_base": "capital_expenditure",
            "value": -9398.0,
            "currency": "US$",
            "statement_period_end": "2025-06-30",
            "statement_period": "for year ended 30 June 2025",
            "statement_scope": "consolidated_statement",
            "statement_family": "cash_flow",
            "page_number": 124,
            "source_mode": "camelot_stream",
            "table_id": "camelot:stream:p124:t0",
            "table_row_idx": 2,
            "row_label": "Purchases of property, plant and equipment",
            "raw_value": "(9,398)",
            "confidence": 0.9,
            "canonical_confidence_score": 2,
        }
        out = MOD.normalize_candidate_row(row)
        self.assertEqual(out["doc_id"], "89d1f8dd-f214-4fbb-94b9-01d223aa4fe1")
        self.assertEqual(out["pass_name"], "stream_table")
        self.assertEqual(out["provenance"]["source_type"], "camelot_table")
        self.assertEqual(out["provenance"]["table_id"], "camelot:stream:p124:t0")
        self.assertEqual(out["unit_scale"], 1.0)
        ok, issues = MOD.validate_candidate_contract(out)
        self.assertTrue(ok, msg=str(issues))

    def test_normalize_candidate_row_infers_unit_scale_from_value_ratio(self):
        row = {
            "file": "/tmp/2024-08-27_bhp_5675698f-abb6-4772-a363-f27aca6a9907.pdf",
            "metric_base": "cash_and_equivalents",
            "value": 17236000000,
            "raw_value": "17,236",
            "currency": "US$",
            "statement_period_end": "2022-06-30",
            "statement_scope": "consolidated_statement",
            "statement_family": "cash_flow",
            "page_number": 173,
            "source_mode": "table_bbox",
        }
        out = MOD.normalize_candidate_row(row)
        self.assertEqual(out["unit_scale"], 1_000_000.0)

    def test_validate_provenance_flags_missing_required_fields(self):
        ok, issues = MOD.validate_provenance({"source_type": "camelot_table", "page": 0})
        self.assertFalse(ok)
        self.assertIn("missing_page", issues)
        self.assertIn("camelot_missing_table_id", issues)

    def test_provenance_depth_score_prefers_table_anchors(self):
        weak = {
            "source_type": "native_text",
            "page": 5,
            "raw_snippet": "Revenue 100",
        }
        strong = {
            "source_type": "camelot_table",
            "page": 5,
            "bbox": [0, 0, 10, 10],
            "table_id": "t1",
            "row_index": 2,
            "col_index": 1,
            "raw_snippet": "Revenue",
            "row_text_raw": "Revenue",
            "cell_text_raw": "100",
        }
        self.assertGreater(MOD.provenance_depth_score(strong), MOD.provenance_depth_score(weak))


if __name__ == "__main__":
    unittest.main()
