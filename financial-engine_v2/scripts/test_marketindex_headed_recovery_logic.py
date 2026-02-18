#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.marketindex_headed_recovery import (  # noqa: E402
    MARKER_403,
    MARKER_HEADED_ERROR,
    MARKER_NO_CANDIDATE,
    build_candidate_links,
    map_failure_marker,
    parse_identifier_from_link,
)


class ParseIdentifierTests(unittest.TestCase):
    def test_parse_identifier_from_api_link(self):
        link = "https://data-api.marketindex.com.au/api/v1/announcements/XASX:ABC:1A2B3C4D/pdf/inline/sample"
        self.assertEqual(parse_identifier_from_link(link), "XASX:ABC:1A2B3C4D")

    def test_parse_identifier_from_announcement_url(self):
        link = "https://www.marketindex.com.au/asx/xyz/announcements/half-year-results-1A2B3C4D"
        self.assertEqual(parse_identifier_from_link(link), "XASX:XYZ:1A2B3C4D")


class CandidateBuildTests(unittest.TestCase):
    def test_build_candidate_links_from_announcement_url(self):
        links = build_candidate_links(
            source_url="https://www.marketindex.com.au/asx/abc/announcements/half-year-results-1A2B3C4D",
            ticker="ABC",
            heading="Half Year Results",
        )
        self.assertEqual(
            links,
            [
                "https://data-api.marketindex.com.au/api/v1/announcements/XASX:ABC:1A2B3C4D/pdf/inline/half-year-results",
            ],
        )


class StatusMapTests(unittest.TestCase):
    def test_map_status_403_to_blocked_403(self):
        marker = map_failure_marker(
            {
                "status": "failed_fetch",
                "fetch_failures": [{"http_status": 403, "link": "https://example.com"}],
            }
        )
        self.assertEqual(marker, MARKER_403)

    def test_map_status_generic_to_headed_error(self):
        marker = map_failure_marker(
            {
                "status": "failed_invalid_pdf_response",
                "fetch_failures": [{"http_status": 500, "link": "https://example.com"}],
            }
        )
        self.assertEqual(marker, MARKER_HEADED_ERROR)

    def test_no_candidate_marker_constant(self):
        self.assertEqual(MARKER_NO_CANDIDATE, "blocked_marketindex_no_candidate")


if __name__ == "__main__":
    unittest.main()
