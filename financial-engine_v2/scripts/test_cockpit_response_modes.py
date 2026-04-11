#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController, ResponseMode  # noqa: E402


class _ToolResult:
    def __init__(self, payload: dict, ok: bool = True) -> None:
        self.payload = payload
        self.ok = ok


class _ToolRouterStub:
    def __init__(self) -> None:
        self.gather_calls: list[dict[str, object]] = []
        self.fetch_calls: list[dict[str, object]] = []

    def gather_local_context(self, ticker=None, query=None, deep_mode=False):
        self.gather_calls.append({"ticker": ticker, "query": query, "deep_mode": deep_mode})
        return _ToolResult({"ticker": ticker, "query": query, "deep_mode": deep_mode})

    def fetch_web(self, url: str, enabled: bool, max_chars: int | None = 8000):
        self.fetch_calls.append({"url": url, "enabled": enabled, "max_chars": max_chars})
        return _ToolResult({"url": url, "enabled": enabled})


class _ActionRegistryStub:
    def preview(self, action_id, args):
        return type("Preview", (), {"command": ["echo", action_id], "estimated_impact": "", "timeout_seconds": 30})()


class _OllamaStub:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat(self, prompt: str, timeout=None, on_chunk=None) -> str:
        self.prompts.append(prompt)
        return "OK"


class CockpitResponseModeTests(unittest.TestCase):
    def test_classify_request_detects_modes(self) -> None:
        self.assertEqual(ChatController.classify_request("analyse BHP deeply"), ResponseMode.DEEP_ANALYSIS)
        self.assertEqual(ChatController.classify_request("verify latest BHP run"), ResponseMode.VERIFICATION)
        self.assertEqual(
            ChatController.classify_request("check https://example.com/bhp", enable_web=True),
            ResponseMode.WEB,
        )
        self.assertEqual(ChatController.classify_request("hello there"), ResponseMode.FAST)

    def test_deep_analysis_uses_deep_context(self) -> None:
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response("analyse BHP and give a full report", enable_web=False)

        self.assertEqual(response.mode, ResponseMode.DEEP_ANALYSIS)
        self.assertTrue(router.gather_calls)
        self.assertIs(router.gather_calls[-1]["deep_mode"], True)
        self.assertIn('"response_mode": "deep_analysis"', response.prompt or "")

    def test_verification_uses_deep_context_and_prompt_bias(self) -> None:
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response("verify latest BHP status", enable_web=False)

        self.assertEqual(response.mode, ResponseMode.VERIFICATION)
        self.assertIs(router.gather_calls[-1]["deep_mode"], True)
        self.assertIn("verification request", response.prompt or "")

    def test_web_mode_fetches_before_prompt(self) -> None:
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response("review https://example.com/report", enable_web=True)

        self.assertEqual(response.mode, ResponseMode.WEB)
        self.assertEqual(len(router.fetch_calls), 1)
        self.assertEqual(response.evidence[-1]["type"], "web")
        self.assertIn('"web_requested": true', response.prompt or "")

    def test_action_mode_short_circuits_before_llm(self) -> None:
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response("run news ingestion for bhp", enable_web=False)

        self.assertEqual(response.mode, ResponseMode.ACTION)
        self.assertEqual(llm.prompts, [])
        self.assertIsNotNone(response.action_preview)

    def test_ui_mode_upgrades_fast_to_deep_analysis(self) -> None:
        """When keywords return FAST but the UI says 'strategy', use DEEP_ANALYSIS."""
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response(
            "tell me about CSL", enable_web=False, ui_mode="strategy"
        )

        self.assertEqual(response.mode, ResponseMode.DEEP_ANALYSIS)

    def test_ui_mode_does_not_override_keyword_signal(self) -> None:
        """Keywords win over ui_mode — 'verify' should stay VERIFICATION even with ui_mode='analysis'."""
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response(
            "verify latest BHP status", enable_web=False, ui_mode="analysis"
        )

        self.assertEqual(response.mode, ResponseMode.VERIFICATION)

    def test_ui_mode_ignored_when_none(self) -> None:
        """No ui_mode means classify_request is the sole authority."""
        router = _ToolRouterStub()
        llm = _OllamaStub()
        controller = ChatController(llm, router, _ActionRegistryStub())

        response = controller.build_chat_response(
            "hello there", enable_web=False, ui_mode=None
        )

        self.assertEqual(response.mode, ResponseMode.FAST)


if __name__ == "__main__":
    unittest.main()
