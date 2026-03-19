from __future__ import annotations

import pytest

from openclaw import nl_router
from openclaw.nl_router import parse_user_message, route_user_message


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("run next task", "run"),
        ("continue working", "run"),
        ("what is the system status", "status"),
        ("show the last report", "latest"),
        ("show gates", "gates"),
        ("list runs", "runs"),
        ("start daemon", "start"),
        ("stop daemon", "stop"),
    ],
)
def test_parse_user_message_examples(message: str, expected: str) -> None:
    assert parse_user_message(message) == expected


def test_parse_user_message_unknown() -> None:
    assert parse_user_message("launch shell and run ls") == "unknown"


def test_route_user_message_accepts_llm_task(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nl_router,
        "_route_with_llm",
        lambda text: {"action": "task", "task_text": "Optimize PDF parser", "source": "llm"},
    )
    routed = route_user_message("please optimize parser")
    assert routed["action"] == "task"
    assert routed["task_text"] == "Optimize PDF parser"


def test_parse_user_message_filters_non_command_action(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nl_router,
        "_route_with_llm",
        lambda text: {"action": "task", "task_text": "Improve tests", "source": "llm"},
    )
    assert parse_user_message("improve tests") == "unknown"


def test_openai_base_url_prefers_router_specific(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("OPENCLAW_ROUTER_OPENAI_BASE_URL", "http://localhost:9000/v1")
    assert nl_router._openai_base_url() == "http://localhost:9000/v1"


def test_openai_api_key_allows_local_endpoint_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    base_url = "http://localhost:8000/v1"
    assert nl_router._openai_api_key(base_url) == "local-openai-key"


def test_openai_api_key_requires_key_for_remote_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    base_url = "https://api.openai.com/v1"
    assert nl_router._openai_api_key(base_url) == ""
