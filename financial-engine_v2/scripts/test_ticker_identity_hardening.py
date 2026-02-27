#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.qual_context import (  # noqa: E402
    compute_news_weighted_score,
    evaluate_ticker_identity_strength,
)


IDENTITY_MAP = {
    "CSL": {
        "canonical_names": ["CSL Limited"],
        "aliases": ["CSL Ltd"],
    },
    "BHP": {
        "canonical_names": ["BHP Group", "BHP Group Limited"],
        "aliases": [],
    },
    "ORCL": {
        "canonical_names": ["Oracle Corporation", "Oracle Corp"],
        "aliases": ["Oracle"],
    },
    "WBC": {
        "canonical_names": ["Westpac Banking Corporation"],
        "aliases": ["Westpac Banking"],
    },
    "GEM": {
        "canonical_names": ["G8 Education Limited"],
        "aliases": ["ARGE"],
    },
    "ORI": {
        "canonical_names": ["Orica Limited"],
        "aliases": ["Orica"],
    },
}


class TickerIdentityHardeningTests(unittest.TestCase):
    def test_csl_canonical_name_is_strong(self):
        strength = evaluate_ticker_identity_strength(
            ticker="CSL",
            title="CSL Limited announces FY26 guidance",
            body="The biotech group reaffirmed outlook.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
            },
        )
        self.assertEqual(strength, "strong")

    def test_csl_acronym_only_is_ambiguous(self):
        strength = evaluate_ticker_identity_strength(
            ticker="CSL",
            title="Communications Sales & Leasing (CSL) reports quarterly update",
            body="A landlord update from the US REIT business.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
            },
        )
        self.assertEqual(strength, "ambiguous")

    def test_bhp_asx_pattern_is_medium(self):
        strength = evaluate_ticker_identity_strength(
            ticker="BHP",
            title="ASX:BHP earnings beat forecasts",
            body="BHP earnings were supported by iron ore volumes.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
            },
        )
        self.assertEqual(strength, "medium")

    def test_orcl_canonical_name_is_strong(self):
        strength = evaluate_ticker_identity_strength(
            ticker="ORCL",
            title="Oracle Corporation raises cloud margin outlook",
            body="Analysts updated estimates.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
            },
        )
        self.assertEqual(strength, "strong")

    def test_csl_collision_remains_ambiguous_when_headline_only_medium_enabled(self):
        strength = evaluate_ticker_identity_strength(
            ticker="CSL",
            title="Communications Sales & Leasing (CSL) updates leasing portfolio",
            body="Leasing portfolio update.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
                "allow_headline_only_medium": True,
                "headline_only_body_chars": 120,
                "_source_domain": "example.com.au",
                "_source_is_au": True,
            },
        )
        self.assertEqual(strength, "ambiguous")

    def test_headline_only_medium_requires_au_source(self):
        au_strength = evaluate_ticker_identity_strength(
            ticker="WBC",
            title="Westpac Banking Corporation updates margin outlook",
            body="Brief update.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
                "allow_headline_only_medium": True,
                "headline_only_body_chars": 120,
                "_source_domain": "publisher.com.au",
                "_source_is_au": True,
            },
        )
        self.assertEqual(au_strength, "medium")

        non_au_strength = evaluate_ticker_identity_strength(
            ticker="WBC",
            title="Westpac Banking Corporation updates margin outlook",
            body="Brief update.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
                "allow_headline_only_medium": True,
                "headline_only_body_chars": 120,
                "_source_domain": "publisher.com",
                "_source_is_au": False,
            },
        )
        self.assertNotEqual(non_au_strength, "medium")

    def test_alias_substring_collision_is_not_counted_as_match(self):
        strength = evaluate_ticker_identity_strength(
            ticker="GEM",
            title="No charges were filed after the hearing",
            body="Regulators confirmed no charges were filed.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
                "allow_headline_only_medium": True,
                "headline_only_body_chars": 120,
                "_source_domain": "publisher.com.au",
                "_source_is_au": True,
            },
        )
        self.assertEqual(strength, "none")

    def test_canonical_substring_collision_is_not_counted_as_match(self):
        strength = evaluate_ticker_identity_strength(
            ticker="ORI",
            title="Historical districts attract new drilling campaigns",
            body="Explorers are revisiting old targets.",
            identity_map=IDENTITY_MAP,
            config={
                "canonical_name_required_for_acronym": True,
                "acronym_min_length": 4,
                "allow_headline_only_medium": True,
                "headline_only_body_chars": 120,
                "_source_domain": "publisher.com.au",
                "_source_is_au": True,
            },
        )
        self.assertEqual(strength, "none")

    def test_disable_identity_hardening_uses_legacy_ticker_boost(self):
        score = compute_news_weighted_score(
            semantic_score=0.5,
            published_at="2026-02-25T00:00:00Z",
            ticker_match_mode="exact",
            title="Generic title",
            source_domain="example.com",
            config={
                "enable_signal_weighting": True,
                "recency_max_boost": 0.0,
                "ticker_match_boosts": {"exact": 0.24, "strong": 0.14, "weak": 0.06},
                "au_domain_boost": 0.0,
                "title_keyword_boost": 0.0,
                "title_keywords": [],
                "ticker_identity": {
                    "enable_identity_hardening": False,
                    "canonical_name_required_for_acronym": True,
                    "acronym_min_length": 4,
                    "downgrade_ambiguous_acronym_boost": 0.02,
                },
                "now_utc": "2026-02-25T01:00:00Z",
            },
            ticker_identity_strength="ambiguous",
        )
        self.assertAlmostEqual(score, 0.74, places=8)


if __name__ == "__main__":
    unittest.main()
