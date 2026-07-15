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

from app.services import llm as llm_service
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


@pytest.mark.unit
def test_news_memo_routes_to_anthropic_before_local_while_extraction_active(
    monkeypatch,
):
    monkeypatch.setattr(llm_service.router_state, "is_extraction_active", lambda: True)
    monkeypatch.setattr(llm_service, "_anthropic_api_key", lambda: "sk-test")
    monkeypatch.setattr(
        llm_service,
        "_execute_generate_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("local generation must not start during metric extraction")
        ),
    )
    monkeypatch.setattr(
        llm_service,
        "_anthropic_fallback_generate_json",
        lambda prompt, **kwargs: {"sentiment": "neutral"},
    )
    metadata = {
        "task_type": "reasoning",
        "component": "news_memo_extractor",
    }

    result = llm_service.generate_json("Return JSON", metadata=metadata)

    assert result == {"sentiment": "neutral"}
    assert metadata["effective_provider"] == "anthropic"
    assert metadata["routing_reason"] == "metric_extraction_active"


@pytest.mark.unit
def test_metric_extraction_remains_on_local_instruct_model_when_registered_active(
    monkeypatch,
):
    decision = _reasoning_decision()
    local_calls: list[dict] = []
    monkeypatch.setattr(llm_service.router_state, "is_extraction_active", lambda: True)
    monkeypatch.setattr(llm_service, "route_request", lambda prompt, metadata: decision)
    monkeypatch.setattr(
        llm_service,
        "_execute_generate_json",
        lambda active_decision, **kwargs: (
            local_calls.append({"decision": active_decision, **kwargs})
            or ({"metrics": []}, {}, "qwen2.5-14b-instruct")
        ),
    )
    monkeypatch.setattr(
        llm_service,
        "_anthropic_fallback_generate_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("metric extraction must remain local")
        ),
    )

    result = llm_service.generate_json(
        "Extract canonical metrics as JSON",
        metadata={
            "task_type": "reasoning",
            "component": "multipass_extraction",
        },
    )

    assert result == {"metrics": []}
    assert len(local_calls) == 1
    assert local_calls[0]["decision"].model_name == "qwen2.5-14b-instruct"


@pytest.mark.unit
def test_other_nonmetric_json_tool_work_uses_api_during_metric_extraction(
    monkeypatch,
):
    api_calls: list[str] = []
    monkeypatch.setattr(llm_service.router_state, "is_extraction_active", lambda: True)
    monkeypatch.setattr(llm_service, "_anthropic_api_key", lambda: "sk-test")
    monkeypatch.setattr(
        llm_service,
        "_anthropic_fallback_generate_json",
        lambda prompt, **kwargs: api_calls.append(prompt) or {"answer": "api"},
    )
    monkeypatch.setattr(
        llm_service,
        "route_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("local routing must not start")
        ),
    )

    result = llm_service.generate_json(
        "Use a tool and return JSON",
        metadata={"task_type": "reasoning", "component": "tenn_chat"},
    )

    assert result == {"answer": "api"}
    assert api_calls == ["Use a tool and return JSON"]


@pytest.mark.unit
def test_nonmetric_json_work_fails_fast_without_api_during_metric_extraction(
    monkeypatch,
):
    monkeypatch.setattr(llm_service.router_state, "is_extraction_active", lambda: True)
    monkeypatch.setattr(llm_service, "_anthropic_api_key", lambda: "")
    monkeypatch.setattr(
        llm_service,
        "route_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("local routing must not start")
        ),
    )

    with pytest.raises(RuntimeError, match="refusing to contend"):
        llm_service.generate_json(
            "Return JSON",
            metadata={"task_type": "reasoning", "component": "news_memo_extractor"},
        )
