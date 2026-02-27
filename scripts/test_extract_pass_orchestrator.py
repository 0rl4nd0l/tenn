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
MOD = load_module(str(ROOT / "scripts" / "extract_pass_orchestrator.py"), "extract_pass_orchestrator")


class TestExtractPassOrchestrator(unittest.TestCase):
    def _base_row(self):
        return {
            "file": "/tmp/2025-08-19_bhp_89d1f8dd-f214-4fbb-94b9-01d223aa4fe1.pdf",
            "metric": "revenue",
            "metric_base": "revenue",
            "value": 100.0,
            "raw_value": "100",
            "currency": "AUD",
            "statement_period_end": "2025-06-30",
            "statement_period": "FY2025",
            "statement_scope": "consolidated_statement",
            "statement_family": "income_statement",
            "page_number": 5,
            "confidence": 3.0,
            "canonical_confidence_score": 3,
            "row_label": "Revenue",
            "line": "Revenue 100",
        }

    def test_gate_blocks_unknown_currency(self):
        row = self._base_row()
        row["currency"] = ""
        out = MOD.select_canonical_candidates([row])
        self.assertEqual(out["stats"]["rows_canonical"], 0)
        self.assertEqual(out["stats"]["rows_context"], 1)

    def test_tie_break_prefers_native_table_over_stream(self):
        a = self._base_row()
        a["source_mode"] = "camelot_stream"
        b = self._base_row()
        b["source_mode"] = "table_bbox"
        b["confidence"] = 3.0
        out = MOD.select_canonical_candidates([a, b])
        self.assertEqual(out["stats"]["rows_canonical"], 1)
        winner = out["canonical_rows"][0]
        self.assertEqual(str(winner.get("orchestrator_pass_name")), "bbox_layout")

    def test_unresolved_collision_is_quarantined(self):
        a = self._base_row()
        b = self._base_row()
        a["table_id"] = "t1"
        b["table_id"] = "t2"
        b["value"] = 101.0
        out = MOD.select_canonical_candidates([a, b])
        self.assertEqual(out["stats"]["rows_canonical"], 0)
        self.assertEqual(out["stats"]["rows_collision_quarantined"], 2)

    def test_collision_resolves_with_unit_evidence(self):
        a = self._base_row()
        b = self._base_row()
        a["metric"] = "cash_and_equivalents"
        a["metric_base"] = "cash_and_equivalents"
        b["metric"] = "cash_and_equivalents"
        b["metric_base"] = "cash_and_equivalents"
        a["table_id"] = "t1"
        b["table_id"] = "t2"
        a["raw_value"] = "15,613"
        b["raw_value"] = "15,613"
        a["value"] = 15613.0
        b["value"] = 15613000000.0
        a["table_header_text"] = "2021 US$M 2020 US$M 2019 US$M"
        b["table_header_text"] = "2021 US$M 2020 US$M 2019 US$M"
        out = MOD.select_canonical_candidates([a, b])
        self.assertEqual(out["stats"]["rows_canonical"], 1)
        self.assertEqual(out["stats"]["rows_collision_quarantined"], 0)
        winner = out["canonical_rows"][0]
        self.assertEqual(float(winner.get("value", 0.0)), 15613000000.0)
        self.assertEqual(str(winner.get("orchestrator_reason")), "collision_resolved_unit_evidence")


if __name__ == "__main__":
    unittest.main()
