"""AnthropicClient — adapter for the Anthropic Messages API.

Reads ANTHROPIC_API_KEY from environment. Normalizes responses to the
dict format expected by HybridRouter._call_api().
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Pricing per million tokens (as of 2025-05)
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
}
_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_DEFAULT_FALLBACK_PRICING = {"input": 3.0, "output": 15.0}


class AnthropicClient:
    """Adapter for the Anthropic Messages API.

    Can be used as ``api_client`` in HybridRouter.  Supports both the
    simple ``chat()`` interface (backward-compatible with LlamaCppClient)
    and the richer ``complete()`` interface that returns cost and
    tool-call data.

    Usage::

        client = AnthropicClient()
        router = HybridRouter(api_client=client, policy="api_preferred")
    """

    def __init__(self, model: str = _DEFAULT_MODEL, max_tokens: int = 4096) -> None:
        self.model = model
        self._max_tokens = max_tokens
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — API calls will fail")
            return
        try:
            import anthropic  # noqa: PLC0415  (deferred import intentional)

            self._client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            logger.warning("anthropic SDK not installed — run: pip install anthropic")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(
        self,
        prompt: str,
        timeout: float = 120.0,
        prior_messages: list[dict] | None = None,
    ) -> str:
        """Return the text reply as a plain string.

        Compatible with ``LlamaCppClient.chat()`` so that the same code
        path works for both local and cloud backends.
        """
        result = self.complete(prompt=prompt, timeout=timeout, prior_messages=prior_messages)
        return result["text"]

    def complete(
        self,
        prompt: str,
        timeout: float = 120.0,
        prior_messages: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Call the API and return a rich response dict.

        Returns a dict with keys:
            text        (str)   — concatenated text blocks
            model       (str)   — model ID echoed from the API response
            cost_usd    (float) — computed from usage + _PRICING table
            tool_calls  (list)  — list of tool-use dicts (may be empty)
            usage       (dict)  — raw token counts {input_tokens, output_tokens}
        """
        if self._client is None:
            raise RuntimeError(
                "AnthropicClient not initialized. "
                "Check that ANTHROPIC_API_KEY is set and the anthropic SDK is installed."
            )

        messages: list[dict] = []
        system_msg: str | None = None

        if prior_messages:
            for msg in prior_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    # Anthropic uses a top-level system parameter, not a message.
                    system_msg = content
                else:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "timeout": timeout,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = self._client.messages.create(**kwargs)

        text = ""
        tool_calls: list[dict] = []
        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "tool": block.name,
                        "arguments": block.input,
                    }
                )

        usage = response.usage
        pricing = _PRICING.get(response.model, _DEFAULT_FALLBACK_PRICING)
        cost_usd = round(
            (usage.input_tokens * pricing["input"] / 1_000_000)
            + (usage.output_tokens * pricing["output"] / 1_000_000),
            6,
        )

        return {
            "text": text,
            "model": response.model,
            "cost_usd": cost_usd,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
        }
