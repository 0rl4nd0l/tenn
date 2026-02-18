import unittest

import download_marketindex_pdfs as dmp


class ParseIdentifierTests(unittest.TestCase):
    def test_parse_identifier_from_api_link(self):
        link = "https://data-api.marketindex.com.au/api/v1/announcements/XASX:ABC:1A2B3C4D/pdf/inline/sample"
        self.assertEqual(dmp.parse_identifier_from_link(link), "XASX:ABC:1A2B3C4D")

    def test_parse_identifier_from_announcement_url(self):
        link = "https://www.marketindex.com.au/asx/xyz/announcements/half-year-results-1A2B3C4D"
        self.assertEqual(dmp.parse_identifier_from_link(link), "XASX:XYZ:1A2B3C4D")


class CandidateRebuildTests(unittest.TestCase):
    def test_build_candidate_links_from_recovered_announcement_url(self):
        announcement = {
            "ticker": "ABC",
            "heading": "Half Year Results",
            "link": "https://www.marketindex.com.au/asx/abc/announcements/half-year-results-1A2B3C4D",
        }
        links = dmp.build_candidate_links(announcement)
        self.assertEqual(
            links,
            [
                "https://data-api.marketindex.com.au/api/v1/announcements/XASX:ABC:1A2B3C4D/pdf/inline/half-year-results",
            ],
        )


class QualityGateTests(unittest.TestCase):
    def test_quality_gate_passes_when_both_thresholds_met(self):
        success_ratio, gate, gate_failed = dmp.evaluate_quality_gate(
            downloaded=6,
            candidate_total=10,
            min_download_count=5,
            min_success_ratio=0.35,
        )
        self.assertFalse(gate_failed)
        self.assertTrue(gate["passed"])
        self.assertAlmostEqual(success_ratio, 0.6)

    def test_quality_gate_passes_when_only_ratio_met(self):
        success_ratio, gate, gate_failed = dmp.evaluate_quality_gate(
            downloaded=3,
            candidate_total=6,
            min_download_count=5,
            min_success_ratio=0.35,
        )
        self.assertFalse(gate_failed)
        self.assertTrue(gate["passed"])
        self.assertAlmostEqual(success_ratio, 0.5)

    def test_quality_gate_passes_when_only_count_met(self):
        success_ratio, gate, gate_failed = dmp.evaluate_quality_gate(
            downloaded=5,
            candidate_total=20,
            min_download_count=5,
            min_success_ratio=0.35,
        )
        self.assertFalse(gate_failed)
        self.assertTrue(gate["passed"])
        self.assertAlmostEqual(success_ratio, 0.25)

    def test_quality_gate_fails_only_when_both_below(self):
        success_ratio, gate, gate_failed = dmp.evaluate_quality_gate(
            downloaded=2,
            candidate_total=10,
            min_download_count=5,
            min_success_ratio=0.35,
        )
        self.assertTrue(gate_failed)
        self.assertFalse(gate["passed"])
        self.assertIn("downloaded=2 < min_download_count=5", gate["reason"])
        self.assertAlmostEqual(success_ratio, 0.2)


if __name__ == "__main__":
    unittest.main()
