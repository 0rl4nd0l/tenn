#!/usr/bin/env python3
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from scripts.announcement_reaction_report import build_close_series, compute_reaction_for_time  # noqa: E402


class AnnouncementReactionReportTests(unittest.TestCase):
    def test_build_close_series_dedupes_and_orders(self):
        payload = {
            "history": [
                {"timestamp": "2026-02-03T00:00:00+00:00", "close": 102.0},
                {"timestamp": "2026-02-01T00:00:00+00:00", "close": 100.0},
                {"timestamp": "2026-02-02T00:00:00+00:00", "close": 101.0},
                {"timestamp": "2026-02-03T00:00:00+00:00", "close": 103.0},
            ]
        }
        series = build_close_series(payload)
        self.assertEqual(len(series), 3)
        self.assertEqual([round(row[1], 2) for row in series], [100.0, 101.0, 103.0])

    def test_compute_reaction_for_time(self):
        series = [
            (datetime(2026, 2, 1, tzinfo=timezone.utc), 100.0),
            (datetime(2026, 2, 2, tzinfo=timezone.utc), 102.0),
            (datetime(2026, 2, 3, tzinfo=timezone.utc), 104.0),
            (datetime(2026, 2, 4, tzinfo=timezone.utc), 101.0),
            (datetime(2026, 2, 5, tzinfo=timezone.utc), 105.0),
            (datetime(2026, 2, 6, tzinfo=timezone.utc), 107.0),
            (datetime(2026, 2, 7, tzinfo=timezone.utc), 110.0),
        ]
        published = datetime(2026, 2, 2, 12, 0, tzinfo=timezone.utc)
        reaction = compute_reaction_for_time(series, published_at=published)

        self.assertIsNotNone(reaction)
        self.assertAlmostEqual(reaction["anchor_close"], 102.0, places=5)
        # From 102 -> 104
        self.assertAlmostEqual(reaction["ret_1d"], ((104.0 / 102.0) - 1.0) * 100.0, places=5)
        # From 102 -> 110
        self.assertAlmostEqual(reaction["ret_5d"], ((110.0 / 102.0) - 1.0) * 100.0, places=5)
        self.assertIsNone(reaction["ret_20d"])

    def test_compute_reaction_returns_none_when_before_series(self):
        series = [
            (datetime(2026, 2, 5, tzinfo=timezone.utc), 105.0),
            (datetime(2026, 2, 6, tzinfo=timezone.utc), 107.0),
        ]
        published = datetime(2026, 2, 1, tzinfo=timezone.utc)
        self.assertIsNone(compute_reaction_for_time(series, published_at=published))


if __name__ == "__main__":
    unittest.main()
