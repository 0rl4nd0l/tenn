#!/usr/bin/env python3
"""
Unit tests for cockpit LLM response quality: prompt construction, post-processing
classifiers, sanitization, and message-length cap. See plan: Cockpit LLM Response
Function Quality Analysis (Deliverable 3 Test Harness).
"""
import os
import sys
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


class _ToolResult:
    def __init__(self, payload: dict, ok: bool = True) -> None:
        self.payload = payload
        self.ok = ok


class _ToolRouterStub:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.qual_context_enabled = False

    def gather_local_context(self, ticker=None, query=None, deep_mode=False):
        p = dict(self.payload)
        p["ticker"] = ticker
        p["query"] = query
        return _ToolResult(p)


class _ActionRegistryStub:
    def preview(self, action_id, args):
        return type("Preview", (), {"command": ["echo", action_id], "estimated_impact": "", "timeout_seconds": 30})()


class _OllamaStub:
    def __init__(self, response: str = "Test response.") -> None:
        self.response = response

    def chat(self, prompt: str, timeout=None, on_chunk=None) -> str:
        return self.response


class TestMessageCap(unittest.TestCase):
    """Fix 1: user message is capped to avoid blowing prompt size."""

    def test_long_message_is_capped(self) -> None:
        os.environ.pop("COCKPIT_MAX_USER_MESSAGE_CHARS", None)
        long_msg = "analyse BHP " + "x" * 15_000  # Over default 8000 cap
        controller = ChatController(
            ollama_client=_OllamaStub("BHP is a diversified miner."),
            tool_router=_ToolRouterStub({"query": "", "ticker": "BHP", "docs": [], "financials": []}),
            action_registry=_ActionRegistryStub(),
        )
        # Should not crash; message is capped internally (default 8000)
        response = controller.build_chat_response(long_msg, enable_web=False, analysis_mode="operational")
        self.assertIsNotNone(response.text)
        self.assertIn("BHP", response.text)

    def test_message_cap_env_respected(self) -> None:
        os.environ["COCKPIT_MAX_USER_MESSAGE_CHARS"] = "10"
        try:
            controller = ChatController(
                ollama_client=_OllamaStub("OK"),
                tool_router=_ToolRouterStub({"query": "", "ticker": None, "docs": [], "reports": [], "matches": []}),
                action_registry=_ActionRegistryStub(),
            )
            response = controller.build_chat_response("analyse BHP and give a full report", enable_web=False)
            # With cap 10 the user message becomes "analyse BHP" (first 10 chars) or similar
            self.assertIsNotNone(response.text)
        finally:
            os.environ.pop("COCKPIT_MAX_USER_MESSAGE_CHARS", None)


class TestPromptEchoDetection(unittest.TestCase):
    """Post-processing: _looks_like_prompt_echo."""

    def test_starts_with_final_context_prompt_is_echo(self) -> None:
        self.assertTrue(
            ChatController._looks_like_prompt_echo("final context prompt for custom gpt something")
        )

    def test_two_markers_is_echo(self) -> None:
        # PROMPT_ECHO_MARKERS include "cockpit context", "as of my last update"
        self.assertTrue(
            ChatController._looks_like_prompt_echo(
                "cockpit context and as of my last update I cannot access real-time data."
            )
        )

    def test_normal_answer_is_not_echo(self) -> None:
        self.assertFalse(
            ChatController._looks_like_prompt_echo("BHP closed at $42.50. Revenue grew 5% in FY24.")
        )


class TestVerificationDisclaimer(unittest.TestCase):
    """Post-processing: _has_verification_disclaimer."""

    def test_contains_phrase_returns_true(self) -> None:
        self.assertTrue(
            ChatController._has_verification_disclaimer(
                "This cannot be verified based on available data."
            )
        )

    def test_case_insensitive(self) -> None:
        self.assertTrue(
            ChatController._has_verification_disclaimer(
                "THIS CANNOT BE VERIFIED BASED ON AVAILABLE DATA."
            )
        )

    def test_absent_returns_false(self) -> None:
        self.assertFalse(
            ChatController._has_verification_disclaimer("BHP revenue was $65bn in FY24.")
        )


class TestSanitizePromptPayload(unittest.TestCase):
    """Sanitization: _sanitize_prompt_local_payload trims docs/snippets."""

    def test_docs_trimmed_in_operational_mode(self) -> None:
        payload = {
            "query": "analyse BHP",
            "ticker": "BHP",
            "docs": [{"document_id": f"doc-{i}", "title": f"Doc {i}"} for i in range(30)],
        }
        out = ChatController._sanitize_prompt_local_payload(payload, deep_mode=False)
        self.assertEqual(len(out["docs"]), 10)

    def test_docs_trimmed_in_deep_mode(self) -> None:
        payload = {
            "query": "analyse BHP",
            "ticker": "BHP",
            "docs": [{"document_id": f"doc-{i}", "title": f"Doc {i}"} for i in range(30)],
        }
        out = ChatController._sanitize_prompt_local_payload(payload, deep_mode=True)
        self.assertEqual(len(out["docs"]), 20)

    def test_snippet_excerpt_trimmed(self) -> None:
        payload = {
            "query": "q",
            "ticker": "BHP",
            "doc_snippets": [
                {"excerpt": "a" * 3000, "title": "T1", "document_id": "d1", "published_at": None, "pdf_path": None}
            ],
        }
        out = ChatController._sanitize_prompt_local_payload(payload, deep_mode=False)
        self.assertEqual(len(out["doc_snippets"]), 1)
        self.assertLessEqual(len(out["doc_snippets"][0]["excerpt"]), 1200)

    def test_non_dict_payload_returns_empty(self) -> None:
        self.assertEqual(ChatController._sanitize_prompt_local_payload(None, deep_mode=False), {})
        self.assertEqual(ChatController._sanitize_prompt_local_payload([], deep_mode=False), {})


class TestPromptConstruction(unittest.TestCase):
    """Prompt contains system prompt, user question, and local evidence JSON."""

    def test_response_prompt_contains_user_question_and_local_json(self) -> None:
        # Use a message that reaches the LLM path (analysis intent + ticker), not financials/smalltalk short-circuit.
        user_msg = "analyse BHP"
        payload = {
            "query": user_msg,
            "ticker": "BHP",
            "docs": [{"document_id": "d1", "title": "BHP 2024 Annual Report"}],
            "financials": [],
            "price_state": {"ok": False},
        }
        controller = ChatController(
            ollama_client=_OllamaStub("BHP is a diversified miner."),
            tool_router=_ToolRouterStub(payload),
            action_registry=_ActionRegistryStub(),
        )
        response = controller.build_chat_response(
            user_msg, enable_web=False, prior_ticker="BHP", analysis_mode="operational"
        )
        self.assertIsNotNone(response.prompt)
        self.assertIn(user_msg, response.prompt)
        self.assertIn("Local evidence JSON", response.prompt)
        self.assertIn("Runtime settings JSON", response.prompt)
        self.assertIn("\"context_profile\": \"balanced\"", response.prompt)
        self.assertIn("/context-profile", response.prompt)
        self.assertIn("BHP", response.prompt)


class TestGatherContextTimeout(unittest.TestCase):
    """Fix 4: _gather_local_context_with_timeout returns fallback on timeout."""

    def test_timeout_returns_fallback_payload(self) -> None:
        class SlowRouter:
            def gather_local_context(self, ticker=None, query=None, deep_mode=False):
                import time
                time.sleep(5)  # Longer than timeout so result(timeout=1) raises
                return _ToolResult({"docs": []})

        controller = ChatController(
            ollama_client=None,
            tool_router=SlowRouter(),
            action_registry=_ActionRegistryStub(),
        )
        prev = os.environ.get("COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS")
        os.environ["COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS"] = "1"
        try:
            started_at = time.perf_counter()
            result = controller._gather_local_context_with_timeout("BHP", "analyse BHP", False)
            elapsed = time.perf_counter() - started_at
            self.assertFalse(result.ok)
            self.assertIn("context_gather_timeout", result.payload.get("note", ""))
            self.assertEqual(result.payload.get("ticker"), "BHP")
            self.assertLess(elapsed, 2.5)
        finally:
            if prev is not None:
                os.environ["COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS"] = prev
            else:
                os.environ.pop("COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS", None)

    def test_exception_returns_fallback_payload(self) -> None:
        class ErrorRouter:
            def gather_local_context(self, ticker=None, query=None, deep_mode=False):
                raise RuntimeError("boom")

        controller = ChatController(
            ollama_client=None,
            tool_router=ErrorRouter(),
            action_registry=_ActionRegistryStub(),
        )
        result = controller._gather_local_context_with_timeout("BHP", "analyse BHP", False)
        self.assertFalse(result.ok)
        self.assertIn("context_gather_error", result.payload.get("note", ""))
        self.assertEqual(result.payload.get("ticker"), "BHP")
        self.assertIn("boom", str(result.payload.get("db_error", "")))

    def test_second_request_while_worker_busy_returns_busy_fallback(self) -> None:
        class SlowRouter:
            def gather_local_context(self, ticker=None, query=None, deep_mode=False):
                import time
                time.sleep(2)
                return _ToolResult({"docs": []})

        controller = ChatController(
            ollama_client=None,
            tool_router=SlowRouter(),
            action_registry=_ActionRegistryStub(),
        )
        prev = os.environ.get("COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS")
        os.environ["COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS"] = "1"
        try:
            first = controller._gather_local_context_with_timeout("BHP", "analyse BHP", False)
            self.assertIn("context_gather_timeout", first.payload.get("note", ""))
            started_at = time.perf_counter()
            second = controller._gather_local_context_with_timeout("BHP", "analyse BHP", False)
            elapsed = time.perf_counter() - started_at
            self.assertIn("context_gather_busy", second.payload.get("note", ""))
            self.assertLess(elapsed, 0.5)
        finally:
            if prev is not None:
                os.environ["COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS"] = prev
            else:
                os.environ.pop("COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS", None)


if __name__ == "__main__":
    unittest.main()
