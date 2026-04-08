#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import httpx


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.llamacpp_client import LlamaCppClient  # noqa: E402
from cockpit.integrations.ollama_client import OllamaClient  # noqa: E402


class _StreamingErrorResponse:
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self._body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        raise httpx.HTTPStatusError(
            "http error",
            request=httpx.Request("POST", "http://example.test"),
            response=self,
        )

    def read(self) -> bytes:
        return self._body

    @property
    def text(self) -> str:
        raise RuntimeError("Attempted to access streaming response content, without having called `read()`.")


class _FakeClient:
    def __init__(self, response: _StreamingErrorResponse) -> None:
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self._response


class _HealthResponse:
    def __init__(self, payload: dict) -> None:
        self.content = b"{}"
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _HeaderCaptureClient:
    def __init__(self, capture: dict[str, dict]) -> None:
        self.capture = capture

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url, headers=None, timeout=None):  # noqa: ANN001
        self.capture["get"] = {"url": url, "headers": dict(headers or {})}
        return _HealthResponse({"data": [{"id": "qwen"}]})

    def stream(self, method, url, headers=None, json=None, timeout=None):  # noqa: ANN001
        self.capture["stream"] = {
            "method": method,
            "url": url,
            "headers": dict(headers or {}),
            "json": dict(json or {}),
        }
        return _StreamingErrorResponse(401, "Invalid or missing API key")


class _EmptyStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        return iter(())


class _NonStreamingSuccessResponse:
    def __init__(self, payload: dict) -> None:
        self.content = str(payload).encode("utf-8")
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _EmptyStreamFallbackClient:
    def stream(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return _EmptyStreamingResponse()

    def post(self, url, headers=None, timeout=None, json=None):  # noqa: ANN001
        return _NonStreamingSuccessResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"type":"response","content":"fallback answer"}',
                        }
                    }
                ]
            }
        )


class StreamingClientErrorTests(unittest.TestCase):
    def test_ollama_streaming_http_error_uses_response_body(self) -> None:
        import cockpit.integrations.ollama_client as ollama_module

        original_client = ollama_module.httpx.Client
        ollama_module.httpx.Client = lambda *args, **kwargs: _FakeClient(  # type: ignore[assignment]
            _StreamingErrorResponse(503, "upstream unavailable")
        )
        try:
            client = OllamaClient("http://localhost:11434", "phi3:mini")
            with self.assertRaises(RuntimeError) as ctx:
                client.chat("hello")
        finally:
            ollama_module.httpx.Client = original_client  # type: ignore[assignment]

        message = str(ctx.exception)
        self.assertIn("upstream unavailable", message)
        self.assertNotIn("Attempted to access streaming response content", message)

    def test_llamacpp_streaming_http_error_uses_response_body(self) -> None:
        import cockpit.integrations.llamacpp_client as llamacpp_module

        original_client = llamacpp_module.httpx.Client
        llamacpp_module.httpx.Client = lambda *args, **kwargs: _FakeClient(  # type: ignore[assignment]
            _StreamingErrorResponse(502, "gateway failure")
        )
        try:
            client = LlamaCppClient("http://localhost:8001", "model")
            with self.assertRaises(RuntimeError) as ctx:
                client.chat("hello")
        finally:
            llamacpp_module.httpx.Client = original_client  # type: ignore[assignment]

        message = str(ctx.exception)
        self.assertIn("gateway failure", message)
        self.assertNotIn("Attempted to access streaming response content", message)

    def test_llamacpp_client_attaches_runtime_auth_headers(self) -> None:
        import cockpit.integrations.llamacpp_client as llamacpp_module

        capture: dict[str, dict] = {}
        original_client = llamacpp_module.httpx.Client
        llamacpp_module.httpx.Client = lambda *args, **kwargs: _HeaderCaptureClient(capture)  # type: ignore[assignment]
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "LLM_API_KEY": "llm-token",
                    "LLM_AUTH_HEADER": "X-LLM-Auth: extra-value",
                },
                clear=False,
            ):
                client = LlamaCppClient("http://localhost:8001", "model")
                health = client.health()
                self.assertTrue(health["ok"])
                with self.assertRaises(RuntimeError) as ctx:
                    client.chat("hello")
        finally:
            llamacpp_module.httpx.Client = original_client  # type: ignore[assignment]

        self.assertEqual(capture["get"]["headers"]["Authorization"], "Bearer llm-token")
        self.assertEqual(capture["get"]["headers"]["X-LLM-Auth"], "extra-value")
        self.assertEqual(capture["stream"]["headers"]["Authorization"], "Bearer llm-token")
        self.assertEqual(capture["stream"]["headers"]["X-LLM-Auth"], "extra-value")
        self.assertIn("Verify LLM_API_KEY / LLM_AUTH_HEADER", str(ctx.exception))

    def test_llamacpp_empty_stream_retries_non_stream_completion(self) -> None:
        import cockpit.integrations.llamacpp_client as llamacpp_module

        original_client = llamacpp_module.httpx.Client
        llamacpp_module.httpx.Client = lambda timeout=None, limits=None: _EmptyStreamFallbackClient()  # type: ignore[assignment]
        try:
            client = LlamaCppClient("http://localhost:8001", "model")
            result = client.chat("hello")
        finally:
            llamacpp_module.httpx.Client = original_client  # type: ignore[assignment]

        self.assertEqual(result, '{"type":"response","content":"fallback answer"}')


if __name__ == "__main__":
    unittest.main()
