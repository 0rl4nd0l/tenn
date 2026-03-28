from __future__ import annotations

import unittest

from cockpit.core.access_resume import build_pending_action_payload


class AccessResumeTests(unittest.TestCase):
    def test_build_pending_action_payload_normalizes_agent_action_proposal(self) -> None:
        payload = build_pending_action_payload(
            {
                "tool": "run_backfill",
                "arguments": {"ticker": "ARR", "years": 2},
                "explanation": "Propose a backfill for ARR.",
                "requires_confirmation": True,
            },
            "ingest arr",
        )

        self.assertEqual(payload["action_id"], "single_ticker_announcement_backfill")
        self.assertEqual(payload["args"], {"ticker": "ARR", "years": 2})
        self.assertEqual(payload["arguments"], {"ticker": "ARR", "years": 2})


if __name__ == "__main__":
    unittest.main()
