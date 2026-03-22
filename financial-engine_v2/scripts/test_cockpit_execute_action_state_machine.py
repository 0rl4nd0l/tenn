#!/usr/bin/env python3
"""
Tests for the execute_action / pending_action state machine in CockpitApp.

Pattern mirrors test_cockpit_chat_status_widgets.py:
  - unittest.IsolatedAsyncioTestCase
  - CockpitApp instantiated with a minimal config dict
  - async with app.run_test() as pilot
  - Widget state asserted via query_one()

All tests use read_only=True by default unless the test specifically needs
to exercise a mutating action path.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from textual.widgets import RichLog, Static

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.ui.app import CockpitApp  # noqa: E402


def _build_config(tmpdir: Path) -> dict:
    return {
        "exports": {"dir": str(tmpdir / "exports")},
        "reports": {"dir": str(tmpdir / "reports")},
        "memory": {"state_db": str(tmpdir / "state.db")},
        "db": {"database_url": f"sqlite:///{tmpdir / 'cockpit.sqlite'}"},
        "paths": {"allow_roots": [str(REPO_ROOT)]},
        "llm": {
            "provider": "llamacpp",
            "llamacpp_url": "http://localhost:8001",
            "model": "test-model",
            "timeout_seconds": 5,
        },
        "actions": {"confirm_required": False},
        "backend": {"api_base_url": ""},
        "rag": {},
        "web": {"enabled_default": False},
        "runtime": {},
    }


def _log_text(widget: RichLog) -> str:
    return "\n".join(strip.text for strip in widget.lines)


def _widget_text(widget: Static) -> str:
    renderable = widget.renderable
    if hasattr(renderable, "plain"):
        return str(renderable.plain)
    return str(renderable)


class ExecuteActionStateMachineTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------
    # 1. Double-run guard — active_job_task blocks a second execute_action call
    # ------------------------------------------------------------------
    async def test_double_run_guard_blocks_second_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = CockpitApp(
                repo_root=REPO_ROOT,
                config=_build_config(Path(tmp)),
                read_only=False,
            )
            async with app.run_test() as pilot:
                await pilot.pause()

                # Simulate an already-running task by planting a never-finishing Task.
                loop = asyncio.get_running_loop()
                blocker: asyncio.Future = loop.create_future()
                dummy_task = asyncio.ensure_future(asyncio.shield(blocker))
                app.active_job_task = dummy_task
                app.active_job_id = "sentinel-job-id"

                # Try to execute another action — should be blocked.
                await app.execute_action(
                    "full_history",
                    {"ticker": "BHP", "years": 1},
                    log_target="chat-log",
                )
                await pilot.pause()

                screen = app.get_screen("chat")
                log_text = _log_text(screen.query_one("#chat-log", RichLog))
                self.assertIn("sentinel-job-id", log_text)

                # Cleanup: cancel the blocker task so teardown is clean.
                blocker.set_result(None)
                dummy_task.cancel()
                try:
                    await dummy_task
                except (asyncio.CancelledError, Exception):
                    pass
                app.active_job_task = None
                app.active_job_id = None

    # ------------------------------------------------------------------
    # 2. read-only mode blocks mutating action
    # ------------------------------------------------------------------
    async def test_read_only_blocks_mutating_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = CockpitApp(
                repo_root=REPO_ROOT,
                config=_build_config(Path(tmp)),
                read_only=True,
            )
            async with app.run_test() as pilot:
                await pilot.pause()

                # full_history is is_mutating=True
                await app.execute_action(
                    "full_history",
                    {"ticker": "ANZ", "years": 1},
                    log_target="chat-log",
                )
                await pilot.pause()

                screen = app.get_screen("chat")
                log_text = _log_text(screen.query_one("#chat-log", RichLog))
                self.assertIn("read-only", log_text.lower())

    # ------------------------------------------------------------------
    # 3. /confirm with no pending action writes "No pending action"
    # ------------------------------------------------------------------
    async def test_confirm_with_no_pending_action_writes_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = CockpitApp(
                repo_root=REPO_ROOT,
                config=_build_config(Path(tmp)),
                read_only=True,
            )
            async with app.run_test() as pilot:
                await pilot.pause()

                # Ensure no pending action
                app.pending_action = None

                await app.handle_chat_message("/confirm")
                await pilot.pause()

                screen = app.get_screen("chat")
                log_text = _log_text(screen.query_one("#chat-log", RichLog))
                self.assertIn("No pending action", log_text)

    # ------------------------------------------------------------------
    # 4. /cancel clears pending_action and updates the pending widget
    # ------------------------------------------------------------------
    async def test_cancel_clears_pending_action_and_updates_widget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = CockpitApp(
                repo_root=REPO_ROOT,
                config=_build_config(Path(tmp)),
                read_only=True,
            )
            async with app.run_test() as pilot:
                await pilot.pause()

                # Plant a pending action
                app.pending_action = {
                    "action_id": "full_history",
                    "args": {"ticker": "CBA", "years": 1},
                }

                # Send /cancel
                await app.handle_chat_message("/cancel")
                await pilot.pause()

                # pending_action should be cleared
                self.assertIsNone(app.pending_action)

                # The #chat-pending widget should reflect "No pending action"
                screen = app.get_screen("chat")
                pending_widget = screen.query_one("#chat-pending")
                pending_text = _widget_text(pending_widget)
                self.assertIn("No pending action", pending_text)

                # The chat log should mention the cancellation
                log_text = _log_text(screen.query_one("#chat-log", RichLog))
                self.assertIn("canceled", log_text.lower())


if __name__ == "__main__":
    unittest.main()
