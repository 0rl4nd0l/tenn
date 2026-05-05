import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
