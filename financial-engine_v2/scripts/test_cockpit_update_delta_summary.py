#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.update_delta import (  # noqa: E402
    build_announcement_update_delta_summary,
    build_close_series,
    compute_reaction_for_time,
    doc_delta_key,
    parse_timestamp_utc,
    sync_human,
)


class CockpitUpdateDeltaSummaryTests(unittest.TestCase):
    def test_build_delta_summary_identifies_new_docs(self):
        before = {
            "docs": [
                {"document_id": "d1", "published_at": "2026-02-10T00:00:00+00:00", "title": "Old one", "doc_class": "update"}
            ],
            "sync": {"status": "stale", "age_hours": 240.0},
            "doc_count": 1,
        }
        after = {
            "docs": [
                {"document_id": "d2", "published_at": "2026-02-20T00:00:00+00:00", "title": "New one", "doc_class": "results"},
                {"document_id": "d1", "published_at": "2026-02-10T00:00:00+00:00", "title": "Old one", "doc_class": "update"},
            ],
            "sync": {"status": "fresh", "age_hours": 2.0},
            "doc_count": 2,
        }

        text, payload = build_announcement_update_delta_summary("BHP", before=before, after=after)
        self.assertIn("Update complete for BHP.", text)
        self.assertIn("before stale", text)
        self.assertIn("after fresh", text)
        self.assertIn("New announcements indexed/downloaded: 1", text)
        self.assertIn("New one", text)
        self.assertEqual(payload["doc_counts"]["before"], 1)
        self.assertEqual(payload["doc_counts"]["after"], 2)
        self.assertEqual(payload["doc_counts"]["new"], 1)
        self.assertEqual(payload["new_announcements"][0]["document_id"], "d2")

    def test_doc_delta_key_prefers_document_id(self):
        key = doc_delta_key({"document_id": "abc123", "title": "x"})
        self.assertEqual(key, "id:abc123")

    def test_sync_human_formats_age(self):
        self.assertEqual(sync_human({"status": "fresh", "age_hours": 2.345}), "fresh (2.3h old)")
        self.assertEqual(sync_human({"status": "unknown"}), "unknown")

    def test_reaction_helpers(self):
        payload = {
            "history": [
                {"timestamp": "2026-02-01T00:00:00+00:00", "close": 100.0},
                {"timestamp": "2026-02-02T00:00:00+00:00", "close": 102.0},
                {"timestamp": "2026-02-03T00:00:00+00:00", "close": 104.0},
                {"timestamp": "2026-02-04T00:00:00+00:00", "close": 103.0},
                {"timestamp": "2026-02-05T00:00:00+00:00", "close": 105.0},
                {"timestamp": "2026-02-06T00:00:00+00:00", "close": 107.0},
                {"timestamp": "2026-02-07T00:00:00+00:00", "close": 110.0},
            ]
        }
        series = build_close_series(payload)
        self.assertEqual(len(series), 7)
        published = parse_timestamp_utc("2026-02-02T12:00:00+00:00")
        self.assertIsNotNone(published)
        reaction = compute_reaction_for_time(series, published_at=published)
        self.assertIsNotNone(reaction)
        self.assertAlmostEqual(reaction["ret_1d"], ((104.0 / 102.0) - 1.0) * 100.0, places=5)
        self.assertAlmostEqual(reaction["ret_5d"], ((110.0 / 102.0) - 1.0) * 100.0, places=5)


if __name__ == "__main__":
    unittest.main()
