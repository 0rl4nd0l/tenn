#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from textual.widgets import Input, RichLog, Static


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


def _log_text(widget: RichLog) -> str:
    return "\n".join(strip.text for strip in widget.lines)


def _build_config(tmpdir: Path) -> dict[str, object]:
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

            def _slow_response(
                message: str,
                enable_web: bool = False,
                prior_ticker: str | None = None,
                on_chunk=None,
            ) -> ChatResponse:
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

    async def test_input_submit_echoes_and_streams_into_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = CockpitApp(repo_root=REPO_ROOT, config=_build_config(Path(tmp)), read_only=True)

            def _streaming_response(
                message: str,
                enable_web: bool = False,
                prior_ticker: str | None = None,
                on_chunk=None,
            ) -> ChatResponse:
                for chunk in ("First ", "draft", "\nSecond line"):
                    if on_chunk is not None:
                        on_chunk(chunk)
                    time.sleep(0.06)
                return ChatResponse(
                    text="First draft\nSecond line",
                    evidence=[{"details": {"ticker": "BHP"}}],
                )

            app.chat_controller.build_chat_response = _streaming_response

            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.get_screen("chat")
                input_widget = screen.query_one("#chat-input", Input)
                input_widget.value = "analyse bhp"

                await screen.on_input_submitted(SimpleNamespace(value="analyse bhp", input=input_widget))
                self.assertEqual(input_widget.value, "")

                await asyncio.sleep(0.05)
                await pilot.pause()

                log = screen.query_one("#chat-log", RichLog)
                status = screen.query_one("#chat-status", Static)
                live = screen.query_one("#chat-live-response", Static)

                self.assertIn("You: analyse bhp", _log_text(log))
                self.assertIn("Tenn (thinking)", _widget_text(status))
                self.assertIn("Tenn: First", _widget_text(live))

                await asyncio.sleep(0.25)
                await pilot.pause()

                self.assertEqual(_widget_text(status), "")
                self.assertEqual(_widget_text(live), "")
                # Final assistant response is now written to the unified #chat-log.
                log_text = _log_text(log)
                self.assertIn("First draft", log_text)
                self.assertIn("Second line", log_text)


if __name__ == "__main__":
    unittest.main()
