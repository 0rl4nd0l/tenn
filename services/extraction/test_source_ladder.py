#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from services.extraction import source_ladder as sl


class TestSourceLadder(unittest.TestCase):
    def test_detect_signals_ixbrl_and_xbrl_scores(self) -> None:
        text = "This annual report uses Inline XBRL (iXBRL) tagging for ix:nonfraction elements."
        out = sl.detect_structured_reporting_signals("/tmp/missing.pdf", text, "report_ixbrl.pdf")
        self.assertTrue(out["ixbrl_hint"])
        self.assertGreater(out["ixbrl_score"], 0.2)
        self.assertGreater(out["combined_structured_score"], 0.3)

    def test_detect_signals_esef_filename(self) -> None:
        out = sl.detect_structured_reporting_signals(
            "/tmp/missing.pdf",
            "Consolidated financial statements.",
            "acme_esef_2024.pdf",
        )
        self.assertTrue(out["esef_hint"] or out["esef_score"] > 0.2)

    def test_detect_signals_sec_like(self) -> None:
        text = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. Form 10-K"
        out = sl.detect_structured_reporting_signals("/tmp/missing.pdf", text, "filing.pdf")
        self.assertGreater(out["sec_like_score"], 0.2)
        self.assertTrue(out["sec_like_hint"])

    def test_choose_tier_structured_from_signals(self) -> None:
        sig = sl.detect_structured_reporting_signals(
            "/tmp/missing.pdf",
            "inline xbrl taxonomy linkbase xbrl instance",
            "xbrl_notes.pdf",
        )
        tier, reason = sl.choose_source_tier(
            structured_signals=sig,
            raw_text_len=80,
            probe_row_count=5,
            verification_ratio=0.9,
            classifier={"complexity_score": 0.2},
        )
        self.assertEqual(tier, sl.TIER_STRUCTURED_SOURCE)
        self.assertTrue(reason)

    def test_choose_tier_scanned_minimal_text(self) -> None:
        sig = sl.detect_structured_reporting_signals("/tmp/missing.pdf", "", "scan.pdf")
        tier, reason = sl.choose_source_tier(
            structured_signals=sig,
            raw_text_len=20,
            probe_row_count=0,
            verification_ratio=0.0,
            classifier={"complexity_score": 0.1},
        )
        self.assertEqual(tier, sl.TIER_SCANNED_PDF_LAYOUT)
        self.assertIn("minimal", reason)

    def test_choose_tier_constrained_repair_low_verification(self) -> None:
        sig = sl.detect_structured_reporting_signals("/tmp/missing.pdf", "ordinary narrative", "a.pdf")
        tier, reason = sl.choose_source_tier(
            structured_signals=sig,
            raw_text_len=2000,
            probe_row_count=20,
            verification_ratio=0.2,
            classifier={"complexity_score": 0.3},
        )
        self.assertEqual(tier, sl.TIER_CONSTRAINED_REPAIR)
        self.assertIn("verification", reason)

    def test_choose_tier_native_default(self) -> None:
        sig = sl.detect_structured_reporting_signals("/tmp/missing.pdf", "Revenue was strong in Q4.", "b.pdf")
        tier, reason = sl.choose_source_tier(
            structured_signals=sig,
            raw_text_len=800,
            probe_row_count=12,
            verification_ratio=0.95,
            classifier={"complexity_score": 0.25},
        )
        self.assertEqual(tier, sl.TIER_NATIVE_PDF_LAYOUT)
        self.assertIn("default", reason)

    def test_detect_signals_nonexistent_pdf_graceful(self) -> None:
        p = Path("/nonexistent/path/ghost.pdf")
        out = sl.detect_structured_reporting_signals(p, "XBRL taxonomy", "ghost.pdf")
        self.assertEqual(out["pdf_binary_hits"], [])
        self.assertTrue(out["xbrl_hint"])


if __name__ == "__main__":
    unittest.main()
