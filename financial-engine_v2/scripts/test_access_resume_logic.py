#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.access_resume import (  # noqa: E402
    access_scope_is_enabled,
    build_pending_action_payload,
    resolve_confirm_resume_message,
    resolve_pending_action_alias,
)


class AccessResumeLogicTests(unittest.TestCase):
    def test_build_pending_action_payload_keeps_resume_message_for_access_request(self):
        preview = {"action_id": "__access_request__", "args": {"scope": "web", "enable": True}}
        payload = build_pending_action_payload(preview, "deep analysis analyse MGR")
        self.assertEqual(payload["action_id"], "__access_request__")
        self.assertEqual(payload["args"]["scope"], "web")
        self.assertEqual(payload.get("resume_message"), "deep analysis analyse MGR")

    def test_build_pending_action_payload_does_not_add_resume_for_non_access_actions(self):
        preview = {"action_id": "update_ticker_financials", "args": {"ticker": "MGR"}}
        payload = build_pending_action_payload(preview, "deep analysis analyse MGR")
        self.assertEqual(payload["action_id"], "update_ticker_financials")
        self.assertNotIn("resume_message", payload)

    def test_access_scope_is_enabled(self):
        state = {
            "web_enabled": True,
            "rag_enabled": False,
            "db_diagnostic_query_enabled": True,
        }
        self.assertTrue(access_scope_is_enabled("web", state))
        self.assertFalse(access_scope_is_enabled("rag", state))
        self.assertTrue(access_scope_is_enabled("dbdiag", state))

    def test_resolve_confirm_resume_message_requires_scope_enabled(self):
        action = {
            "action_id": "__access_request__",
            "args": {"scope": "web", "enable": True},
            "resume_message": "deep analysis analyse MGR",
        }
        self.assertIsNone(resolve_confirm_resume_message(action, {"web_enabled": False}))
        self.assertEqual(
            resolve_confirm_resume_message(action, {"web_enabled": True}),
            "deep analysis analyse MGR",
        )

    def test_resolve_confirm_resume_message_ignores_disable_actions(self):
        action = {
            "action_id": "__access_request__",
            "args": {"scope": "web", "enable": False},
            "resume_message": "deep analysis analyse MGR",
        }
        self.assertIsNone(resolve_confirm_resume_message(action, {"web_enabled": False}))

    def test_resolve_confirm_resume_message_ignores_non_access_actions(self):
        action = {
            "action_id": "update_ticker_financials",
            "args": {"ticker": "MGR"},
            "resume_message": "deep analysis analyse MGR",
        }
        self.assertIsNone(resolve_confirm_resume_message(action, {"web_enabled": True}))

    def test_resolve_pending_action_alias_for_confirm_and_cancel(self):
        self.assertEqual(resolve_pending_action_alias("yes", True), "/confirm")
        self.assertEqual(resolve_pending_action_alias("OK", True), "/confirm")
        self.assertEqual(resolve_pending_action_alias("n", True), "/cancel")
        self.assertEqual(resolve_pending_action_alias("cancel", True), "/cancel")
        self.assertEqual(resolve_pending_action_alias("yes", False), "yes")
        self.assertEqual(resolve_pending_action_alias("analyse MGR", True), "analyse MGR")


if __name__ == "__main__":
    unittest.main()
