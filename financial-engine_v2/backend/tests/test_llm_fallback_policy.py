"""Fallback-policy tests for app.services.llm._should_retry_with_fallback.

Why this exists: extraction (multipass_extraction) sets ``task_type="reasoning"``
so a 500 from the extraction model would otherwise trigger a fallback to the
router role. In the current deployment the configured router model
(Qwen3-30B-A3B-Instruct-2507-Q3_K_M) is not on disk and the llama-server
fuzzy-matcher resolves it to a harmony-format APEX GGUF. APEX emits
``<|start|>assistant<|channel|>final<|message|>{...}`` prelude tokens which
collide with ``response_format: json_object`` and produce parser 500s —
amplifying the original failure rather than recovering from it.

The fix is to exclude ``component == "multipass_extraction"`` from the
reasoning fallback. Extraction must stay pinned to qwen2.5-14b-instruct and
surface 500s to the caller instead of escalating to a reasoning model that
is incompatible with JSON grammar.
"""

from __future__ import annotations

import httpx
import pytest

from app.services.llm import _should_retry_with_fallback
from app.services.router import RoutingDecision


def _reasoning_decision() -> RoutingDecision:
    return RoutingDecision(
        selected_role="reasoning",
        policy_name="light",
        model_name="qwen2.5-14b-instruct",
        execution_queue="llm_cpu",
        task_type="reasoning",
        provider="llamacpp",
        base_url="http://127.0.0.1:8001",
    )


def _http_500_error() -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://127.0.0.1:8001/v1/chat/completions")
    response = httpx.Response(500, request=request, text="boom")
    return httpx.HTTPStatusError("500", request=request, response=response)


@pytest.mark.unit
def test_multipass_extraction_does_not_escalate_on_http_500():
    """500s from the extraction path must NOT fall back to the router model.

    The router model resolves to a harmony-format APEX GGUF in this deployment,
    which causes parser 500s of its own and masks the original failure.
    """
    decision = _reasoning_decision()
    exc = _http_500_error()
    metadata = {
        "task_type": "reasoning",
        "component": "multipass_extraction",
    }

    assert (
        _should_retry_with_fallback(
            decision, metadata, exc, attempted_fallback=False
        )
        is False
    )


@pytest.mark.unit
def test_non_extraction_reasoning_still_falls_back_on_http_500():
    """Control: other reasoning-role callers (e.g. chat) should still fall back."""
    decision = _reasoning_decision()
    exc = _http_500_error()
    metadata = {
        "task_type": "reasoning",
        "component": "chat",
    }

    assert (
        _should_retry_with_fallback(
            decision, metadata, exc, attempted_fallback=False
        )
        is True
    )


@pytest.mark.unit
def test_extraction_still_blocked_after_attempted_fallback():
    """The attempted_fallback guard already returns False; must keep that."""
    decision = _reasoning_decision()
    exc = _http_500_error()
    metadata = {
        "task_type": "reasoning",
        "component": "multipass_extraction",
    }

    assert (
        _should_retry_with_fallback(
            decision, metadata, exc, attempted_fallback=True
        )
        is False
    )
