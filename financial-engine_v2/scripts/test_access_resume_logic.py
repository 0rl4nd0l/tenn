#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.access_resume import (  # noqa: E402
    build_pending_action_payload,
    resolve_pending_action_alias,
)


class AccessResumeLogicTests(unittest.TestCase):
    def test_build_pending_action_payload_keeps_resume_message_for_backend_access_proposal(self):
        preview = {"action_id": "__backend_proposal__", "args": {"proposal_id": "enable_web_access"}}
        payload = build_pending_action_payload(preview, "deep analysis analyse MGR")
        self.assertEqual(payload["action_id"], "__backend_proposal__")
        self.assertEqual(payload["args"]["proposal_id"], "enable_web_access")
        self.assertEqual(payload["args"].get("resume_message"), "deep analysis analyse MGR")

    def test_build_pending_action_payload_does_not_add_resume_for_non_access_actions(self):
        preview = {"action_id": "update_ticker_financials", "args": {"ticker": "MGR"}}
        payload = build_pending_action_payload(preview, "deep analysis analyse MGR")
        self.assertEqual(payload["action_id"], "update_ticker_financials")
        self.assertNotIn("resume_message", payload)

    def test_build_pending_action_payload_preserves_existing_backend_resume_message(self):
        preview = {
            "action_id": "__backend_proposal__",
            "args": {"proposal_id": "enable_rag_access", "resume_message": "keep me"},
        }
        payload = build_pending_action_payload(preview, "new text")
        self.assertEqual(payload["args"].get("resume_message"), "keep me")

    def test_resolve_pending_action_alias_for_confirm_and_cancel(self):
        self.assertEqual(resolve_pending_action_alias("yes", True), "/confirm")
        self.assertEqual(resolve_pending_action_alias("OK", True), "/confirm")
        self.assertEqual(resolve_pending_action_alias("n", True), "/cancel")
        self.assertEqual(resolve_pending_action_alias("cancel", True), "/cancel")
        self.assertEqual(resolve_pending_action_alias("yes", False), "yes")
        self.assertEqual(resolve_pending_action_alias("analyse MGR", True), "analyse MGR")


if __name__ == "__main__":
    unittest.main()
