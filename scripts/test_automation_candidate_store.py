from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import automation_candidate_store as store
from scripts import system_brief as brief


UTC = timezone.utc
NOW = datetime(2026, 7, 9, 6, 0, tzinfo=UTC)


class CandidateStoreTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_changes_with_evidence_hash(self) -> None:
        base = {
            "job": "bug-regression",
            "lane": "reporting",
            "evidence_path": "reports/demo.md",
            "root_cause": "same finding",
        }

        first = store.fingerprint_for(**base, evidence_hash="aaa")
        second = store.fingerprint_for(**base, evidence_hash="aaa")
        changed = store.fingerprint_for(**base, evidence_hash="bbb")

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_default_suppression_ttls(self) -> None:
        self.assertEqual("2026-08-08T06:00:00Z", store.default_suppress_until("deferred", NOW))
        self.assertEqual("2026-07-23T06:00:00Z", store.default_suppress_until("DATA_MISSING", NOW))
        self.assertEqual("2026-10-07T06:00:00Z", store.default_suppress_until("rejected", NOW))
        self.assertIsNone(store.default_suppress_until("duplicate", NOW))

    def test_latest_record_wins_by_updated_at(self) -> None:
        old = store.build_record(
            job="demo",
            lane="reporting",
            evidence_path="reports/demo.md",
            root_cause="same",
            status="deferred",
            title="Old",
            now=NOW,
        )
        new = dict(old)
        new["status"] = "needs_review"
        new["title"] = "New"
        new["updated_at"] = store.format_time(NOW + timedelta(days=1))

        latest = store.latest_by_fingerprint([old, new])

        self.assertEqual(1, len(latest))
        self.assertEqual("needs_review", latest[0]["status"])
        self.assertEqual("New", latest[0]["title"])

    def test_suppressed_record_resurfaces_on_ttl_or_evidence_change(self) -> None:
        record = store.build_record(
            job="demo",
            lane="reporting",
            evidence_path="reports/demo.md",
            root_cause="same",
            status="deferred",
            title="Deferred",
            evidence_hash="aaa",
            now=NOW,
        )

        visible, reason = store.should_resurface(record, now=NOW + timedelta(days=1))
        self.assertFalse(visible)
        self.assertIsNone(reason)

        visible, reason = store.should_resurface(record, now=NOW + timedelta(days=31))
        self.assertTrue(visible)
        self.assertEqual("ttl_expired", reason)

        visible, reason = store.should_resurface(record, now=NOW + timedelta(days=1), current_evidence_hash="bbb")
        self.assertTrue(visible)
        self.assertEqual("evidence_hash_changed", reason)

    def test_candidate_items_for_brief_hides_suppressed_and_shows_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "candidates.jsonl"
            suppressed = store.build_record(
                job="demo",
                lane="reporting",
                evidence_path="reports/suppressed.md",
                root_cause="deferred",
                status="deferred",
                title="Suppressed",
                now=NOW,
            )
            visible = store.build_record(
                job="demo",
                lane="reporting",
                evidence_path="reports/visible.md",
                root_cause="review",
                status="needs_review",
                title="Visible",
                now=NOW,
            )
            store.append_record(path, suppressed)
            store.append_record(path, visible)

            items, summary = store.candidate_items_for_brief(path, now=NOW + timedelta(days=1))

        self.assertEqual(["Visible"], [item["title"] for item in items])
        self.assertEqual(1, summary["suppressed"])
        self.assertEqual(1, summary["visible"])

    def test_cli_upsert_and_list_with_temp_state_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state" / "candidates.jsonl"
            upsert = subprocess.run(
                [
                    sys.executable,
                    "scripts/automation_candidate_store.py",
                    "--state-path",
                    str(path),
                    "upsert",
                    "--job",
                    "demo",
                    "--lane",
                    "reporting",
                    "--evidence-path",
                    "reports/demo.md",
                    "--root-cause",
                    "review me",
                    "--status",
                    "needs_review",
                    "--title",
                    "Review me",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            listed = subprocess.run(
                [
                    sys.executable,
                    "scripts/automation_candidate_store.py",
                    "--state-path",
                    str(path),
                    "list",
                    "--include-summary",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, upsert.returncode, upsert.stderr)
        self.assertEqual(0, listed.returncode, listed.stderr)
        payload = json.loads(listed.stdout)
        self.assertEqual("Review me", payload["items"][0]["title"])
        self.assertEqual(1, payload["summary"]["visible"])

    def test_system_brief_uses_candidate_store_suppression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            automation_root = Path(temp_dir) / "automation"
            state_path = automation_root / "state" / "candidates.jsonl"
            state_path.parent.mkdir(parents=True)
            store.append_record(
                state_path,
                store.build_record(
                    job="demo",
                    lane="reporting",
                    evidence_path="reports/visible.md",
                    root_cause="review",
                    status="needs_review",
                    title="Visible candidate",
                    now=NOW,
                ),
            )
            store.append_record(
                state_path,
                store.build_record(
                    job="demo",
                    lane="reporting",
                    evidence_path="reports/suppressed.md",
                    root_cause="deferred",
                    status="deferred",
                    title="Suppressed candidate",
                    now=NOW,
                ),
            )

            items, status = brief.collect_candidate_items(automation_root)

        self.assertEqual("ok", status)
        self.assertEqual(["Visible candidate"], [item.title for item in items])


if __name__ == "__main__":
    unittest.main()
