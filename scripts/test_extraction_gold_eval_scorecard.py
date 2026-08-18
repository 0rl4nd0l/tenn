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
    def test_holdout_profile_is_exact_development_aggregate(self):
        aggregate = {
            "corpus_version": "opaque-v1",
            "corpus_digest": "a" * 64,
            "document_count": 48,
            "partition_counts": {"diagnostic": 12, "holdout": 36},
            "bucket_counts": {
                "annual": 8,
                "4E": 8,
                "half-year": 8,
                "4D": 8,
                "quarterly": 8,
                "4C": 8,
            },
            "company_count": 12,
            "sector_count": 6,
            "scan_image_heavy_count": 6,
            "non_aud_count": 1,
            "issuer_size_counts": {"large": 24, "small": 24},
        }
        payload = mod._build_profile(
            "expanded_required",
            None,
            corpus_classification="holdout",
            development_aggregate=aggregate,
        )

        self.assertEqual(payload, aggregate)

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
