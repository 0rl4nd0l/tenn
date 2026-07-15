from __future__ import annotations

from unittest.mock import MagicMock, patch

from cockpit.core.chat import ChatController


def test_keyword_chat_uses_configured_api_router_instead_of_local_llm() -> None:
    local_client = MagicMock()
    local_client.chat.side_effect = AssertionError("local llama.cpp must not be called")
    api_client = MagicMock(spec=["chat", "complete", "model"])
    api_client.complete.return_value = {
        "text": "Claude routed answer",
        "model": "claude-sonnet-test",
        "cost_usd": 0.001,
        "tool_calls": [],
    }
    api_client.model = "claude-sonnet-test"

    with (
        patch.dict(
            "os.environ",
            {
                "COCKPIT_AGENT_MODE": "keyword",
                "ANTHROPIC_API_KEY": "sk-test",
            },
            clear=False,
        ),
        patch(
            "cockpit.core.agent.anthropic_client.AnthropicClient",
            return_value=api_client,
        ),
    ):
        controller = ChatController(
            ollama_client=local_client,
            tool_router=MagicMock(),
            action_registry=MagicMock(),
            cockpit_llm={"hybrid_router_policy": "api_preferred"},
        )

    answer, metadata = controller._complete_keyword_llm(
        user_message="news today?",
        prior_messages=[],
        prompt_fallback="news today?",
        force_backend=None,
        on_chunk=None,
        on_status=None,
    )

    assert answer == "Claude routed answer"
    assert metadata is not None
    assert metadata["source"] == "api"
    api_client.complete.assert_called_once()
    local_client.chat.assert_not_called()
