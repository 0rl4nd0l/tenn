#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.update_status import (  # noqa: E402
    is_successful_update_status,
    normalize_update_status,
)


class CockpitStatusNormalizationTests(unittest.TestCase):
    def test_normalizes_completed_to_success(self):
        self.assertEqual(normalize_update_status("completed"), "success")
        self.assertEqual(normalize_update_status("success"), "success")
        self.assertEqual(normalize_update_status("FAILED"), "failed")

    def test_success_status_check_accepts_legacy_completed(self):
        self.assertTrue(is_successful_update_status("success"))
        self.assertTrue(is_successful_update_status("completed"))
        self.assertFalse(is_successful_update_status("failed"))


if __name__ == "__main__":
    unittest.main()
