"""Tests for cockpit.core.llm_profile and AgentLoop backend prefixes."""

from __future__ import annotations

import pytest

from cockpit.core.agent_loop import parse_backend_prefix
from cockpit.core.llm_profile import (
    cockpit_llm_profile_label,
    describe_llm_profile,
    format_all_profile_descriptions,
    preview_effective_policy,
    resolve_hybrid_router_policy,
)


def test_resolve_explicit_hybrid_router_policy_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTER_POLICY", "local_only")
    monkeypatch.setenv("COCKPIT_LLM_PROFILE", "advisor")
    assert resolve_hybrid_router_policy(api_available=True) == "local_only"


def test_resolve_ops_default_local_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYBRID_ROUTER_POLICY", raising=False)
    monkeypatch.setenv("COCKPIT_LLM_PROFILE", "ops")
    assert resolve_hybrid_router_policy(api_available=True) == "local_preferred"


def test_resolve_advisor_prefers_api_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYBRID_ROUTER_POLICY", raising=False)
    monkeypatch.setenv("COCKPIT_LLM_PROFILE", "advisor")
    assert resolve_hybrid_router_policy(api_available=True) == "api_preferred"


def test_resolve_advisor_falls_back_without_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYBRID_ROUTER_POLICY", raising=False)
    monkeypatch.setenv("COCKPIT_LLM_PROFILE", "advisor")
    assert resolve_hybrid_router_policy(api_available=False) == "local_preferred"


def test_cockpit_llm_profile_label_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYBRID_ROUTER_POLICY", "api_only")
    monkeypatch.setenv("COCKPIT_LLM_PROFILE", "ops")
    assert cockpit_llm_profile_label() == "override:api_only"


def test_describe_llm_profile_covers_known_ids() -> None:
    for pid in ("ops", "advisor", "local_only", "api_only"):
        assert len(describe_llm_profile(pid)) > 20
    assert "local" in describe_llm_profile("local_only").lower()


def test_format_all_profile_descriptions_lists_each_profile() -> None:
    block = format_all_profile_descriptions()
    assert "Ops" in block and "Advisor" in block
    assert "ops" in block.lower() or "local-first" in block.lower()


def test_preview_effective_policy_matches_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYBRID_ROUTER_POLICY", raising=False)
    monkeypatch.setenv("COCKPIT_LLM_PROFILE", "ops")
    assert preview_effective_policy(profile="ops", explicit_override=None, api_available=True) == "local_preferred"
    assert (
        preview_effective_policy(profile="ops", explicit_override="api_only", api_available=True) == "api_only"
    )


def test_parse_backend_prefix() -> None:
    assert parse_backend_prefix("/advisor compare BHP") == ("api", "compare BHP")
    assert parse_backend_prefix("  /cloud  x") == ("api", "x")
    assert parse_backend_prefix("/local only local") == ("local", "only local")
    assert parse_backend_prefix("/ops run job") == ("local", "run job")
    assert parse_backend_prefix("no prefix") == (None, "no prefix")
