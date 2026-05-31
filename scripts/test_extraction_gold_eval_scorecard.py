import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "extraction_gold_eval_scorecard.py"

spec = importlib.util.spec_from_file_location(
    "extraction_gold_eval_scorecard", str(SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestExtractionGoldEvalScorecardScript(unittest.TestCase):
    def test_canonical_core_profile_filters_to_ten_doc_anchor(self):
        scorecard = mod._build_canonical_core_scorecard(mod.DEFAULT_FIXTURES_DIR)

        self.assertEqual(scorecard["total_fixture_count"], 10)
        self.assertEqual(scorecard["total_metric_expectations"], 24)

    def test_confirmed_metric_coverage_profile_is_dry_run_inventory(self):
        payload = mod._build_profile("confirmed_metric_coverage", None)

        self.assertEqual(payload["profile"], "confirmed_metric_coverage")
        self.assertEqual(payload["total_fixture_count"], 15)
        self.assertFalse(
            payload["canonical_trust_semantics"]["mutates_canonical_trust"]
        )

    def test_confirmed_metric_payload_profile_requires_actuals(self):
        with self.assertRaisesRegex(ValueError, "--actuals-json"):
            mod._build_profile("confirmed_metric_payload", None)

    def test_confirmed_metric_payload_profile_emits_pre_persistence_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixtures_dir = tmp_path / "fixtures"
            fixtures_dir.mkdir()
            pdf_path = tmp_path / "report.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            fixture = {
                "_source": "Hand-verified from source PDF page 1.",
                "_verification": "hand-verified",
                "_verification_confidence": "high",
                "document_id": "confirmed_doc",
                "pdf_path": str(pdf_path),
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
                "expected_nulls": [],
            }
            (fixtures_dir / "confirmed.json").write_text(
                json.dumps(fixture), encoding="utf-8"
            )
            actuals_json = tmp_path / "actuals.json"
            actuals_json.write_text(
                json.dumps(
                    {
                        "confirmed_doc": {
                            "period_type": "H",
                            "period_end": "2025-12-31",
                            "currency": "AUD",
                            "scale": "millions",
                            "metrics": {"revenue": 90.0},
                            "evidence": {"revenue": {"page": 1}},
                        }
                    }
                ),
                encoding="utf-8",
            )

            payload = mod._build_profile(
                "confirmed_metric_payload",
                fixtures_dir,
                actuals_json=actuals_json,
                include_pre_persistence_gate=True,
            )

        self.assertEqual(payload["profile"], "confirmed_metric_payload")
        scorecard = payload["payload_scorecard"]
        gate = payload["pre_persistence_gate"]
        self.assertEqual(scorecard["actual_payload_document_count"], 1)
        self.assertEqual(gate["gate_status"], "fail")
        self.assertEqual(gate["decision"], "blocked")
        self.assertFalse(gate["canonical_write_allowed"])
        self.assertFalse(gate["broad_backfill_authorized"])
        self.assertEqual(
            gate["blocking_result_class_summary"]["present_wrong_value"], 1
        )


if __name__ == "__main__":
    unittest.main()
