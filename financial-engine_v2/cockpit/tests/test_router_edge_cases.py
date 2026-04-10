"""Edge case tests for HybridRouter.

Covers all four policies × all client configurations, force_backend overrides,
cost tracking, API client interfaces (complete vs chat fallback), timeout
passthrough, and input edge cases (empty / single-message lists).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cockpit.core.agent.hybrid_router import HybridRouter, RouterResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _local_client(
    model: str = "local-model", response: str = "local response"
) -> MagicMock:
    """Minimal local client stub: exposes chat()."""
    client = MagicMock()
    client.model = model
    client.chat.return_value = response
    return client


def _api_client_chat_only(
    model: str = "api-model", response: str = "api response"
) -> MagicMock:
    """API client with only chat() — no complete() attribute."""
    client = MagicMock(spec=["chat", "model"])
    client.model = model
    client.chat.return_value = response
    return client


def _api_client_with_complete(
    text: str = "api response",
    cost: float = 0.01,
    model: str = "claude-3-haiku",
) -> MagicMock:
    """API client with the richer complete() interface."""
    client = MagicMock()
    client.model = model
    client.complete.return_value = {
        "text": text,
        "model": model,
        "cost_usd": cost,
        "tool_calls": [],
    }
    return client


_MSG1 = [{"role": "user", "content": "hello"}]
_MSG2 = [
    {"role": "user", "content": "first"},
    {"role": "user", "content": "second"},
]


# ---------------------------------------------------------------------------
# 1. All four policies × all four client availability combinations
# ---------------------------------------------------------------------------


class TestAllFourPoliciesWithBothClients:
    """For each policy: (a) both clients, (b) local only, (c) API only, (d) neither."""

    # --- local_only ---

    def test_local_only__both_clients__uses_local(self):
        local = _local_client()
        api = _api_client_chat_only()
        router = HybridRouter(llm_client=local, api_client=api, policy="local_only")
        resp = router.complete(_MSG1)
        assert resp.source == "local"
        local.chat.assert_called_once()
        api.chat.assert_not_called()

    def test_local_only__local_only__uses_local(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        assert router.complete(_MSG1).source == "local"

    def test_local_only__api_only__raises(self):
        router = HybridRouter(api_client=_api_client_chat_only(), policy="local_only")
        with pytest.raises(RuntimeError, match="No local LLM client"):
            router.complete(_MSG1)

    def test_local_only__neither__raises(self):
        router = HybridRouter(policy="local_only")
        with pytest.raises(RuntimeError, match="No local LLM client"):
            router.complete(_MSG1)

    # --- local_preferred ---

    def test_local_preferred__both_clients__uses_local(self):
        local = _local_client()
        api = _api_client_chat_only()
        router = HybridRouter(
            llm_client=local, api_client=api, policy="local_preferred"
        )
        resp = router.complete(_MSG1)
        assert resp.source == "local"
        api.chat.assert_not_called()

    def test_local_preferred__local_only__uses_local(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_preferred")
        assert router.complete(_MSG1).source == "local"

    def test_local_preferred__api_only__falls_back_to_api(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="local_preferred")
        assert router.complete(_MSG1).source == "api"

    def test_local_preferred__neither__raises(self):
        """No local and no API → falls back to local path → RuntimeError."""
        router = HybridRouter(policy="local_preferred")
        with pytest.raises(RuntimeError, match="No local LLM client"):
            router.complete(_MSG1)

    # --- api_preferred ---

    def test_api_preferred__both_clients__uses_api(self):
        local = _local_client()
        api = _api_client_chat_only()
        router = HybridRouter(llm_client=local, api_client=api, policy="api_preferred")
        resp = router.complete(_MSG1)
        assert resp.source == "api"
        local.chat.assert_not_called()

    def test_api_preferred__local_only__falls_back_to_local(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="api_preferred")
        assert router.complete(_MSG1).source == "local"

    def test_api_preferred__api_only__uses_api(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_preferred")
        assert router.complete(_MSG1).source == "api"

    def test_api_preferred__neither__raises(self):
        """No API → falls back to local path → RuntimeError because no local either."""
        router = HybridRouter(policy="api_preferred")
        with pytest.raises(RuntimeError, match="No local LLM client"):
            router.complete(_MSG1)

    # --- api_only ---

    def test_api_only__both_clients__uses_api(self):
        local = _local_client()
        api = _api_client_chat_only()
        router = HybridRouter(llm_client=local, api_client=api, policy="api_only")
        resp = router.complete(_MSG1)
        assert resp.source == "api"
        local.chat.assert_not_called()

    def test_api_only__local_only__raises(self):
        router = HybridRouter(llm_client=_local_client(), policy="api_only")
        with pytest.raises(RuntimeError, match="No API client"):
            router.complete(_MSG1)

    def test_api_only__api_only__uses_api(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        assert router.complete(_MSG1).source == "api"

    def test_api_only__neither__raises(self):
        router = HybridRouter(policy="api_only")
        with pytest.raises(RuntimeError, match="No API client"):
            router.complete(_MSG1)


# ---------------------------------------------------------------------------
# 2. force_backend overrides policy
# ---------------------------------------------------------------------------


class TestForceBackendOverridesPolicy:
    def test_force_local_with_api_only_policy_uses_local(self):
        local = _local_client()
        api = _api_client_chat_only()
        router = HybridRouter(llm_client=local, api_client=api, policy="api_only")
        resp = router.complete(_MSG1, force_backend="local")
        assert resp.source == "local"
        local.chat.assert_called_once()
        api.chat.assert_not_called()

    def test_force_api_with_local_only_policy_uses_api(self):
        local = _local_client()
        api = _api_client_chat_only()
        router = HybridRouter(llm_client=local, api_client=api, policy="local_only")
        resp = router.complete(_MSG1, force_backend="api")
        assert resp.source == "api"
        local.chat.assert_not_called()

    def test_force_api_local_only_policy_no_api_client_raises(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        with pytest.raises(RuntimeError, match="No API client"):
            router.complete(_MSG1, force_backend="api")

    def test_force_local_api_only_policy_no_local_client_raises(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        with pytest.raises(RuntimeError, match="No local LLM client"):
            router.complete(_MSG1, force_backend="local")


# ---------------------------------------------------------------------------
# 3. Invalid force_backend raises ValueError
# ---------------------------------------------------------------------------


class TestInvalidForceBackendRaises:
    def test_invalid_string_raises_value_error(self):
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        with pytest.raises(ValueError, match="force_backend must be"):
            router.complete(_MSG1, force_backend="invalid")

    def test_none_force_backend_is_valid(self):
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        resp = router.complete(_MSG1, force_backend=None)
        assert resp.source == "local"

    @pytest.mark.parametrize("bad", ["LOCAL", "API", "both", "auto", ""])
    def test_various_invalid_values_raise(self, bad: str):
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        with pytest.raises(ValueError):
            router.complete(_MSG1, force_backend=bad)


class TestRoutingReasonValues:
    def test_force_api_sets_force_reason(self):
        router = HybridRouter(
            llm_client=_local_client(),
            api_client=_api_client_chat_only(),
            policy="local_only",
        )
        router.complete(_MSG1, force_backend="api")
        assert router.cost_log()[-1]["routing_reason"] == "force:api"

    def test_api_preferred_policy_sets_policy_reason(self):
        router = HybridRouter(
            api_client=_api_client_chat_only(), policy="api_preferred"
        )
        router.complete(_MSG1)
        assert router.cost_log()[-1]["routing_reason"] == "policy:api_preferred"


# ---------------------------------------------------------------------------
# 4. Cost tracking accumulates correctly
# ---------------------------------------------------------------------------


class TestCostTrackingAccumulates:
    def test_five_local_calls_produce_five_entries(self):
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        for _ in range(5):
            router.complete(_MSG1)
        assert len(router.cost_log()) == 5

    def test_local_calls_accumulate_zero_cost(self):
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        for _ in range(5):
            router.complete(_MSG1)
        assert router.total_cost_usd() == 0.0

    def test_api_cost_accumulates_correctly(self):
        api = _api_client_with_complete(cost=0.03)
        router = HybridRouter(api_client=api, policy="api_only")
        for _ in range(5):
            router.complete(_MSG1)
        assert len(router.cost_log()) == 5
        assert router.total_cost_usd() == pytest.approx(0.15)

    def test_cost_log_entry_has_all_fields(self):
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        router.complete(_MSG1, role="test-role")
        entry = router.cost_log()[0]
        assert entry["source"] == "local"
        assert entry["role"] == "test-role"
        assert "model" in entry
        assert "latency_ms" in entry
        assert "cost_usd" in entry
        assert "routing_reason" in entry
        assert entry["routing_reason"] == "policy:local_only"

    def test_cost_log_returns_independent_copy(self):
        """Mutating the returned list must not affect internal state."""
        router = HybridRouter(llm_client=_local_client(), policy="local_only")
        router.complete(_MSG1)
        log = router.cost_log()
        log.clear()
        assert len(router.cost_log()) == 1


# ---------------------------------------------------------------------------
# 5. API client with complete() method — cost and routing
# ---------------------------------------------------------------------------


class TestApiClientWithCompleteMethod:
    def test_complete_is_called_not_chat(self):
        api = _api_client_with_complete()
        router = HybridRouter(api_client=api, policy="api_only")
        router.complete(_MSG1)
        api.complete.assert_called_once()
        api.chat.assert_not_called()

    def test_complete_propagates_cost_usd(self):
        api = _api_client_with_complete(cost=0.07)
        router = HybridRouter(api_client=api, policy="api_only")
        resp = router.complete(_MSG1)
        assert resp.cost_usd == pytest.approx(0.07)
        assert router.total_cost_usd() == pytest.approx(0.07)

    def test_complete_propagates_model_name(self):
        api = _api_client_with_complete(model="claude-opus-4-5")
        router = HybridRouter(api_client=api, policy="api_only")
        resp = router.complete(_MSG1)
        assert resp.model == "claude-opus-4-5"

    def test_complete_propagates_text(self):
        api = _api_client_with_complete(text="rich answer")
        router = HybridRouter(api_client=api, policy="api_only")
        resp = router.complete(_MSG1)
        assert resp.text == "rich answer"

    def test_complete_receives_correct_prompt_and_prior(self):
        api = _api_client_with_complete()
        router = HybridRouter(api_client=api, policy="api_only")
        messages = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "final prompt"},
        ]
        router.complete(messages)
        kw = api.complete.call_args.kwargs
        assert kw["prompt"] == "final prompt"
        assert len(kw["prior_messages"]) == 2

    def test_complete_source_is_api(self):
        api = _api_client_with_complete()
        router = HybridRouter(api_client=api, policy="api_only")
        assert router.complete(_MSG1).source == "api"


# ---------------------------------------------------------------------------
# 6. API client without complete() falls back to chat()
# ---------------------------------------------------------------------------


class TestApiClientWithoutCompleteFallback:
    def test_chat_fallback_is_invoked(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        router.complete(_MSG1)
        api.chat.assert_called_once()

    def test_chat_fallback_returns_correct_text(self):
        api = _api_client_chat_only(response="fallback text")
        router = HybridRouter(api_client=api, policy="api_only")
        assert router.complete(_MSG1).text == "fallback text"

    def test_chat_fallback_cost_is_zero(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        assert router.complete(_MSG1).cost_usd == 0.0

    def test_chat_fallback_uses_model_attribute(self):
        api = _api_client_chat_only(model="custom-api-model")
        router = HybridRouter(api_client=api, policy="api_only")
        assert router.complete(_MSG1).model == "custom-api-model"


# ---------------------------------------------------------------------------
# 7. Timeout passthrough to llm_client.chat()
# ---------------------------------------------------------------------------


class TestLocalClientTimeoutPassthrough:
    def test_custom_timeout_passed_to_local_chat(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only", llm_timeout=42.0)
        router.complete(_MSG1)
        kw = local.chat.call_args.kwargs
        assert kw.get("timeout") == 42.0

    def test_default_timeout_is_120(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        router.complete(_MSG1)
        kw = local.chat.call_args.kwargs
        assert kw.get("timeout") == 120.0

    def test_custom_timeout_passed_to_api_chat_fallback(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only", llm_timeout=30.0)
        router.complete(_MSG1)
        kw = api.chat.call_args.kwargs
        assert kw.get("timeout") == 30.0

    def test_custom_timeout_passed_to_api_complete(self):
        api = _api_client_with_complete()
        router = HybridRouter(api_client=api, policy="api_only", llm_timeout=55.0)
        router.complete(_MSG1)
        kw = api.complete.call_args.kwargs
        assert kw.get("timeout") == 55.0


# ---------------------------------------------------------------------------
# 8. on_chunk passthrough for chat() adapter
# ---------------------------------------------------------------------------


class TestChatOnChunkPassthrough:
    def test_chat_passes_on_chunk_to_local_client(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        callback = MagicMock()

        router.chat(prompt="hello", on_chunk=callback)

        kw = local.chat.call_args.kwargs
        assert kw.get("on_chunk") is callback

    def test_chat_passes_on_chunk_to_api_chat_fallback(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        callback = MagicMock()

        router.chat(prompt="hello", on_chunk=callback)

        kw = api.chat.call_args.kwargs
        assert kw.get("on_chunk") is callback


# ---------------------------------------------------------------------------
# 9. Empty messages list — should not crash
# ---------------------------------------------------------------------------


class TestEmptyMessagesList:
    def test_empty_list_local_does_not_raise(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        resp = router.complete([])
        assert isinstance(resp, RouterResponse)

    def test_empty_list_sends_empty_prompt(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        router.complete([])
        kw = local.chat.call_args.kwargs
        assert kw.get("prompt") == ""

    def test_empty_list_prior_is_none(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        router.complete([])
        kw = local.chat.call_args.kwargs
        assert kw.get("prior_messages") is None

    def test_empty_list_api_does_not_raise(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        resp = router.complete([])
        assert isinstance(resp, RouterResponse)

    def test_empty_list_api_sends_empty_prompt(self):
        api = _api_client_chat_only()
        router = HybridRouter(api_client=api, policy="api_only")
        router.complete([])
        kw = api.chat.call_args.kwargs
        assert kw.get("prompt") == ""


# ---------------------------------------------------------------------------
# 10. Single message — no prior_messages
# ---------------------------------------------------------------------------


class TestSingleMessageNoPrior:
    def test_single_message_prior_is_none(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        router.complete([{"role": "user", "content": "only one"}])
        kw = local.chat.call_args.kwargs
        assert kw.get("prior_messages") is None

    def test_single_message_prompt_is_content(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        router.complete([{"role": "user", "content": "only one"}])
        kw = local.chat.call_args.kwargs
        assert kw.get("prompt") == "only one"

    def test_single_message_returns_router_response(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        resp = router.complete([{"role": "user", "content": "only one"}])
        assert isinstance(resp, RouterResponse)
        assert resp.source == "local"

    def test_two_messages_prior_is_first_message(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        messages = [
            {"role": "user", "content": "first"},
            {"role": "user", "content": "second"},
        ]
        router.complete(messages)
        kw = local.chat.call_args.kwargs
        assert kw.get("prior_messages") == [{"role": "user", "content": "first"}]
        assert kw.get("prompt") == "second"

    def test_many_messages_prior_excludes_last(self):
        local = _local_client()
        router = HybridRouter(llm_client=local, policy="local_only")
        messages = [{"role": "user", "content": str(i)} for i in range(5)]
        router.complete(messages)
        kw = local.chat.call_args.kwargs
        assert len(kw.get("prior_messages", [])) == 4
        assert kw.get("prompt") == "4"


# ---------------------------------------------------------------------------
# 11. Invalid policy raises ValueError at construction time
# ---------------------------------------------------------------------------


class TestInvalidPolicyRaises:
    def test_bogus_policy_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown HybridRouter policy"):
            HybridRouter(policy="bogus")

    @pytest.mark.parametrize(
        "bad_policy",
        ["LOCAL_ONLY", "Local_Only", "all", "none", "yolo", "local-only"],
    )
    def test_various_invalid_policies_raise(self, bad_policy: str):
        with pytest.raises(ValueError):
            HybridRouter(policy=bad_policy)

    def test_all_four_valid_policies_do_not_raise(self):
        for policy in ("local_only", "local_preferred", "api_preferred", "api_only"):
            HybridRouter(policy=policy)  # must not raise

    def test_env_var_invalid_policy_raises(self, monkeypatch):
        monkeypatch.setenv("HYBRID_ROUTER_POLICY", "invalid_from_env")
        with pytest.raises(ValueError, match="Unknown HybridRouter policy"):
            HybridRouter()

    def test_env_var_valid_policy_is_used(self, monkeypatch):
        local = _local_client()
        monkeypatch.setenv("HYBRID_ROUTER_POLICY", "local_only")
        router = HybridRouter(llm_client=local)
        resp = router.complete(_MSG1)
        assert resp.source == "local"

    def test_explicit_policy_overrides_env_var(self, monkeypatch):
        local = _local_client()
        api = _api_client_chat_only()
        monkeypatch.setenv("HYBRID_ROUTER_POLICY", "local_only")
        router = HybridRouter(llm_client=local, api_client=api, policy="api_preferred")
        resp = router.complete(_MSG1)
        assert resp.source == "api"
