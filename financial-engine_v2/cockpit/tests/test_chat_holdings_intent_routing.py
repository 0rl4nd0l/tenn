from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from cockpit.core.chat import ChatController, ResponseMode
from cockpit.storage.state import StateStore


@pytest.fixture
def controller(tmp_path):
    old_agent_mode = os.environ.get("COCKPIT_AGENT_MODE")
    os.environ["COCKPIT_AGENT_MODE"] = "keyword"
    store = StateStore(str(tmp_path / "state.db"))
    ollama_client = MagicMock()
    ollama_client.chat.return_value = "generic answer"
    tool_router = MagicMock()
    action_registry = MagicMock()
    instance = ChatController(
        ollama_client=ollama_client,
        tool_router=tool_router,
        action_registry=action_registry,
        state_store=store,
    )
    yield instance, store, ollama_client, tool_router
    if old_agent_mode is None:
        os.environ.pop("COCKPIT_AGENT_MODE", None)
    else:
        os.environ["COCKPIT_AGENT_MODE"] = old_agent_mode


def test_holdings_phrase_uses_local_holdings_without_llm_or_screeners(controller) -> None:
    chat, store, ollama_client, tool_router = controller
    store.add_holding(
        "BHP",
        account_label="Broker A",
        quantity=10,
        avg_cost=42.5,
        cost_currency="AUD",
        note="core",
    )

    response = chat.build_chat_response("what stocks i hold currently")

    assert response.mode == ResponseMode.FAST
    assert "Local personal holdings data" in response.text
    assert "BHP" in response.text
    assert "10" in response.text
    assert "core" in response.text
    assert response.routing_metadata["canonical_intent"] == "holdings"
    assert len(response.evidence) == 1
    assert response.evidence[0]["type"] == "holdings"
    assert response.evidence[0]["details"][0]["ticker"] == "BHP"
    assert not response.tool_traces
    assert "screen_tickers" not in str(response.evidence)
    assert "tv_screener" not in str(response.evidence)
    assert "get_strategy" not in str(response.evidence)
    ollama_client.chat.assert_not_called()
    tool_router.gather_local_context.assert_not_called()


def test_empty_holdings_says_not_configured_without_access_denial(controller) -> None:
    chat, _store, ollama_client, _tool_router = controller

    response = chat.build_chat_response("holdings?")

    assert response.mode == ResponseMode.FAST
    assert "No holdings are stored" in response.text
    assert "import" in response.text.lower()
    assert "paste" in response.text.lower()
    assert "lack access" not in response.text.lower()
    assert "do not have access" not in response.text.lower()
    assert response.evidence == []
    ollama_client.chat.assert_not_called()


def test_holdings_response_does_not_render_raw_json_or_thinking(controller) -> None:
    chat, store, _ollama_client, _tool_router = controller
    store.add_holding("CBA", quantity=5)

    response = chat.build_chat_response("my positions")

    forbidden = ["{\"", "tool_call", "thinking", "scratch", "assessment", "plan"]
    assert all(token not in response.text.lower() for token in forbidden)


def test_proposed_route_alias_is_not_active_until_confirmed(controller) -> None:
    chat, store, ollama_client, _tool_router = controller
    store.add_holding("BHP", quantity=1)
    store.propose_route_alias_preference(
        source_utterance="my stonks means my portfolio",
        alias_phrase="my stonks",
        canonical_intent="holdings",
    )

    response = chat.build_chat_response("my stonks")

    assert "Local personal holdings data" not in response.text
    ollama_client.chat.assert_called_once()


def test_confirmed_route_alias_routes_to_holdings(controller) -> None:
    chat, store, ollama_client, _tool_router = controller
    store.add_holding("BHP", quantity=1)
    proposed = store.propose_route_alias_preference(
        source_utterance="my stonks means my portfolio",
        alias_phrase="my stonks",
        canonical_intent="holdings",
    )
    store.confirm_route_alias_preference(proposed["preference_id"])

    response = chat.build_chat_response("my stonks")

    assert "Local personal holdings data" in response.text
    assert "BHP" in response.text
    ollama_client.chat.assert_not_called()


def test_rejected_and_disabled_route_aliases_do_not_route(controller) -> None:
    chat, store, ollama_client, _tool_router = controller
    store.add_holding("BHP", quantity=1)
    rejected = store.propose_route_alias_preference(
        source_utterance="holdies means my portfolio",
        alias_phrase="holdies",
        canonical_intent="holdings",
    )
    disabled = store.propose_route_alias_preference(
        source_utterance="bags means my portfolio",
        alias_phrase="bags",
        canonical_intent="holdings",
    )
    store.reject_route_alias_preference(rejected["preference_id"])
    store.confirm_route_alias_preference(disabled["preference_id"])
    store.disable_route_alias_preference(disabled["preference_id"])

    rejected_response = chat.build_chat_response("holdies")
    disabled_response = chat.build_chat_response("bags")

    assert "Local personal holdings data" not in rejected_response.text
    assert "Local personal holdings data" not in disabled_response.text
    assert not any(item.get("type") == "holdings" for item in rejected_response.evidence)
    assert not any(item.get("type") == "holdings" for item in disabled_response.evidence)


def test_holdings_correction_proposes_confirmation_gated_route_alias(controller) -> None:
    chat, store, ollama_client, _tool_router = controller

    response = chat.build_chat_response("u do have access to my holdings")

    proposals = store.list_route_alias_preferences(canonical_intent="holdings")
    assert len(proposals) == 1
    assert proposals[0]["alias_phrase"] == "holdings"
    assert proposals[0]["confirmation_status"] == "proposed"
    assert proposals[0]["enabled"] is False
    assert proposals[0]["preference_id"] in response.text
    assert "Confirm" in response.text
    ollama_client.chat.assert_not_called()
