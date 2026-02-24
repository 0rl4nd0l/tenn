#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.conversation_commands import derive_conversational_command  # noqa: E402


class CockpitConversationCommandTests(unittest.TestCase):
    def test_watchlist_add_phrases(self):
        self.assertEqual(derive_conversational_command("add bhp to watchlist"), "/watch add BHP")
        self.assertEqual(derive_conversational_command("watch csl"), "/watch add CSL")
        self.assertEqual(derive_conversational_command("track rio"), "/watch add RIO")

    def test_watchlist_remove_list_clear_phrases(self):
        self.assertEqual(derive_conversational_command("remove bhp from watchlist"), "/watch remove BHP")
        self.assertEqual(derive_conversational_command("show my watchlist"), "/watch list")
        self.assertEqual(derive_conversational_command("clear watchlist"), "/watch clear")
        self.assertEqual(derive_conversational_command("sync my watchlist"), "/watch sync")

    def test_alert_phrases(self):
        self.assertEqual(derive_conversational_command("check alerts"), "/alerts")
        self.assertEqual(derive_conversational_command("check alerts for bhp"), "/alerts BHP")
        self.assertEqual(derive_conversational_command("bhp alerts"), "/alerts BHP")
        self.assertEqual(derive_conversational_command("show alert thresholds"), "/alerts thresholds")

    def test_changes_phrases(self):
        self.assertEqual(derive_conversational_command("what changed for bhp"), "/changes BHP")
        self.assertEqual(derive_conversational_command("bhp changes"), "/changes BHP")
        self.assertEqual(derive_conversational_command("what changed"), "/changes")

    def test_access_control_phrases(self):
        self.assertEqual(derive_conversational_command("what access do you have"), "/access")
        self.assertEqual(derive_conversational_command("enable web access"), "/request-access web")
        self.assertEqual(derive_conversational_command("disable web access"), "/web off")
        self.assertEqual(derive_conversational_command("turn on rag"), "/request-access rag")
        self.assertEqual(derive_conversational_command("turn off rag"), "/rag off")
        self.assertEqual(derive_conversational_command("enable sql diagnostics"), "/request-access dbdiag")
        self.assertEqual(derive_conversational_command("disable dbdiag"), "/dbdiag off")

    def test_non_control_messages(self):
        self.assertIsNone(derive_conversational_command("analyse bhp"))
        self.assertIsNone(derive_conversational_command("price bhp"))
        self.assertIsNone(derive_conversational_command("/watch add bhp"))


if __name__ == "__main__":
    unittest.main()
