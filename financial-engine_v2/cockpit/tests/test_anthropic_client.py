"""Tests for AnthropicClient — Anthropic Messages API adapter."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_block(id: str, name: str, input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = id
    block.name = name
    block.input = input
    return block


def _make_response(
    content: list,
    model: str = "claude-sonnet-4-20250514",
    input_tokens: int = 10,
    output_tokens: int = 20,
) -> MagicMock:
    response = MagicMock()
    response.content = content
    response.model = model
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response.usage = usage
    return response


def _make_client_with_mock_sdk(response: MagicMock) -> tuple:
    """Return (AnthropicClient instance, mock_sdk_client)."""
    from cockpit.core.agent.anthropic_client import AnthropicClient

    mock_sdk = MagicMock()
    mock_sdk.messages.create.return_value = response

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch("anthropic.Anthropic", return_value=mock_sdk):
            client = AnthropicClient()

    return client, mock_sdk


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_model(self):
        from cockpit.core.agent.anthropic_client import AnthropicClient, _DEFAULT_MODEL

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("anthropic.Anthropic"):
                client = AnthropicClient()

        assert client.model == _DEFAULT_MODEL

    def test_custom_model(self):
        from cockpit.core.agent.anthropic_client import AnthropicClient

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("anthropic.Anthropic"):
                client = AnthropicClient(model="claude-haiku-4-5-20251001")

        assert client.model == "claude-haiku-4-5-20251001"

    def test_missing_api_key_logs_warning(self, caplog):
        import logging
        from cockpit.core.agent.anthropic_client import AnthropicClient

        with patch.dict("os.environ", {}, clear=True):
            # Ensure key is absent
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with caplog.at_level(logging.WARNING, logger="cockpit.core.agent.anthropic_client"):
                client = AnthropicClient()

        assert client._client is None
        assert "ANTHROPIC_API_KEY" in caplog.text

    def test_missing_sdk_logs_warning(self, caplog):
        import logging
        from cockpit.core.agent.anthropic_client import AnthropicClient
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return real_import(name, *args, **kwargs)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("builtins.__import__", side_effect=mock_import):
                with caplog.at_level(logging.WARNING, logger="cockpit.core.agent.anthropic_client"):
                    client = AnthropicClient()

        assert client._client is None
        assert "anthropic" in caplog.text.lower()


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------

class TestComplete:
    def test_returns_required_keys(self):
        response = _make_response([_make_text_block("Hello")])
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("Say hi")

        assert {"text", "model", "cost_usd", "tool_calls", "usage"} <= result.keys()

    def test_text_concatenated(self):
        response = _make_response([_make_text_block("Hello "), _make_text_block("world")])
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("Say hi")
        assert result["text"] == "Hello world"

    def test_model_echoed_from_response(self):
        response = _make_response([_make_text_block("Hi")], model="claude-haiku-4-5-20251001")
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("Hi")
        assert result["model"] == "claude-haiku-4-5-20251001"

    def test_cost_calculation_known_model(self):
        # 1000 input tokens at $3/M  = $0.003
        # 2000 output tokens at $15/M = $0.030
        # total = $0.033
        response = _make_response(
            [_make_text_block("hi")],
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=2000,
        )
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("hi")
        assert result["cost_usd"] == pytest.approx(0.033, rel=1e-4)

    def test_cost_calculation_unknown_model_uses_fallback(self):
        # Falls back to {input: 3.0, output: 15.0}
        response = _make_response(
            [_make_text_block("hi")],
            model="claude-future-model-99",
            input_tokens=1000,
            output_tokens=1000,
        )
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("hi")
        expected = (1000 * 3.0 / 1_000_000) + (1000 * 15.0 / 1_000_000)
        assert result["cost_usd"] == pytest.approx(expected, rel=1e-4)

    def test_tool_calls_extracted(self):
        tool_block = _make_tool_block(
            id="tool_abc",
            name="search_financials",
            input={"query": "BHP revenue"},
        )
        response = _make_response([_make_text_block(""), tool_block])
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("Search for BHP")
        assert len(result["tool_calls"]) == 1
        tc = result["tool_calls"][0]
        assert tc["id"] == "tool_abc"
        assert tc["tool"] == "search_financials"
        assert tc["arguments"] == {"query": "BHP revenue"}

    def test_empty_tool_calls_when_no_tools(self):
        response = _make_response([_make_text_block("Answer")])
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("hi")
        assert result["tool_calls"] == []

    def test_usage_tokens_present(self):
        response = _make_response(
            [_make_text_block("hi")], input_tokens=50, output_tokens=100
        )
        client, _ = _make_client_with_mock_sdk(response)

        result = client.complete("hi")
        assert result["usage"]["input_tokens"] == 50
        assert result["usage"]["output_tokens"] == 100

    def test_system_message_extracted_from_prior(self):
        response = _make_response([_make_text_block("Hi")])
        client, mock_sdk = _make_client_with_mock_sdk(response)

        prior = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Previous message"},
        ]
        client.complete("New prompt", prior_messages=prior)

        call_kwargs = mock_sdk.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are a helpful assistant."
        # System message must NOT appear in the messages list
        for msg in call_kwargs["messages"]:
            assert msg.get("role") != "system"

    def test_no_system_kwarg_when_no_system_message(self):
        response = _make_response([_make_text_block("Hi")])
        client, mock_sdk = _make_client_with_mock_sdk(response)

        prior = [{"role": "user", "content": "Previous message"}]
        client.complete("New prompt", prior_messages=prior)

        call_kwargs = mock_sdk.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_raises_when_client_not_initialized(self):
        from cockpit.core.agent.anthropic_client import AnthropicClient

        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)
            client = AnthropicClient()

        with pytest.raises(RuntimeError, match="not initialized"):
            client.complete("hi")

    def test_prompt_appended_as_user_message(self):
        response = _make_response([_make_text_block("Hi")])
        client, mock_sdk = _make_client_with_mock_sdk(response)

        client.complete("My prompt")

        call_kwargs = mock_sdk.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[-1] == {"role": "user", "content": "My prompt"}

    def test_timeout_passed_to_sdk(self):
        response = _make_response([_make_text_block("Hi")])
        client, mock_sdk = _make_client_with_mock_sdk(response)

        client.complete("hi", timeout=30.0)

        call_kwargs = mock_sdk.messages.create.call_args[1]
        assert call_kwargs["timeout"] == 30.0


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------

class TestChat:
    def test_returns_string(self):
        response = _make_response([_make_text_block("Hello there")])
        client, _ = _make_client_with_mock_sdk(response)

        result = client.chat("hi")
        assert isinstance(result, str)
        assert result == "Hello there"

    def test_delegates_to_complete(self):
        from cockpit.core.agent.anthropic_client import AnthropicClient

        response = _make_response([_make_text_block("delegated")])
        client, _ = _make_client_with_mock_sdk(response)

        with patch.object(client, "complete", wraps=client.complete) as mock_complete:
            result = client.chat("prompt", timeout=45.0, prior_messages=[])
            mock_complete.assert_called_once_with(
                prompt="prompt", timeout=45.0, prior_messages=[]
            )

        assert result == "delegated"


# ---------------------------------------------------------------------------
# HybridRouter integration
# ---------------------------------------------------------------------------

class TestHybridRouterIntegration:
    """Verify that HybridRouter uses complete() when available."""

    def test_hybrid_router_calls_complete(self):
        from cockpit.core.agent.hybrid_router import HybridRouter

        mock_api = MagicMock()
        mock_api.complete.return_value = {
            "text": "api response",
            "model": "claude-sonnet-4-20250514",
            "cost_usd": 0.000033,
            "tool_calls": [],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        router = HybridRouter(api_client=mock_api, policy="api_only")
        result = router.complete([{"role": "user", "content": "hi"}])

        mock_api.complete.assert_called_once()
        mock_api.chat.assert_not_called()
        assert result.text == "api response"
        assert result.cost_usd == pytest.approx(0.000033)

    def test_hybrid_router_falls_back_to_chat(self):
        """Client without complete() should use chat() interface."""
        from cockpit.core.agent.hybrid_router import HybridRouter

        mock_api = MagicMock(spec=["chat", "model"])
        mock_api.chat.return_value = "plain text"
        mock_api.model = "legacy-model"

        router = HybridRouter(api_client=mock_api, policy="api_only")
        result = router.complete([{"role": "user", "content": "hi"}])

        mock_api.chat.assert_called_once()
        assert result.text == "plain text"
        assert result.cost_usd == 0.0
