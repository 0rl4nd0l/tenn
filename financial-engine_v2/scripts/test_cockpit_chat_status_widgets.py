#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from textual.widgets import Static


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatResponse  # noqa: E402
from cockpit.ui.app import CockpitApp  # noqa: E402


def _widget_text(widget: Static) -> str:
    renderable = widget.renderable
    if hasattr(renderable, "plain"):
        return str(renderable.plain)
    return str(renderable)


def _build_config(tmpdir: Path) -> dict[str, object]:
    return {
        "exports": {"dir": str(tmpdir / "exports")},
        "reports": {"dir": str(tmpdir / "reports")},
        "memory": {"state_db": str(tmpdir / "state.db")},
        "db": {"database_url": f"sqlite:///{tmpdir / 'cockpit.sqlite'}"},
        "paths": {"allow_roots": [str(REPO_ROOT)]},
        "llm": {
            "ollama_url": "http://localhost:11434",
            "model": "test-model",
            "timeout_seconds": 5,
        },
        "actions": {"confirm_required": False},
        "backend": {"api_base_url": ""},
        "rag": {},
        "web": {"enabled_default": False},
        "runtime": {},
    }


class CockpitChatStatusWidgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_panel_and_thinking_status_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = CockpitApp(repo_root=REPO_ROOT, config=_build_config(Path(tmp)), read_only=True)
            app.ollama_client.health = lambda timeout=2.0: {
                "ok": True,
                "url": "http://localhost:11434",
                "models": ["test-model"],
            }
            app._collect_system_metrics = lambda: {
                "gpus": [
                    {
                        "name": "RTX Test",
                        "util_percent": 42.0,
                        "mem_used_mib": 1024.0,
                        "mem_total_mib": 8192.0,
                    }
                ],
                "gpu_error": None,
            }

            def _slow_response(message: str, enable_web: bool = False, prior_ticker: str | None = None) -> ChatResponse:
                time.sleep(0.25)
                return ChatResponse(
                    text="Done",
                    evidence=[{"details": {"ticker": "BHP"}}],
                )

            app.chat_controller.build_chat_response = _slow_response

            async with app.run_test() as pilot:
                await pilot.pause()
                await app._refresh_model_status_widget()
                await pilot.pause()

                screen = app.get_screen("chat")
                panel = screen.query_one("#chat-model-status", Static)
                panel_text = _widget_text(panel)
                self.assertIn("Model Runtime: test-model", panel_text)
                self.assertIn("GPU: RTX Test 42% 1024/8192 MiB", panel_text)

                task = asyncio.create_task(app.handle_chat_message("analyse bhp"))
                await asyncio.sleep(0.05)
                await pilot.pause()

                status = screen.query_one("#chat-status", Static)
                self.assertIn("Tenn (thinking)", _widget_text(status))

                await task
                await pilot.pause()
                self.assertEqual(_widget_text(status), "")


if __name__ == "__main__":
    unittest.main()
