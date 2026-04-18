"""Tests for shared.session_memory_base.SessionMemoryClient."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# shared/ lives at financial-engine_v2/shared, which is two levels up from tests/.
# conftest.py already adds backend/ to sys.path; we also need financial-engine_v2/.
_FE2_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_FE2_ROOT) not in sys.path:
    sys.path.insert(0, str(_FE2_ROOT))

from shared.session_memory_base import (  # noqa: E402
    SessionMemoryClient,
    _message_content,
    _message_role,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(config_exists: bool = False) -> SessionMemoryClient:
    config_path = Path("/tmp/nonexistent_cockpit.ov.conf")
    if config_exists:
        config_path = Path("/tmp/fake_cockpit.ov.conf")
        config_path.touch()
    return SessionMemoryClient(
        component_name="test",
        config_path=config_path,
        operator_action="run test setup",
    )


# ---------------------------------------------------------------------------
# Unit: _resolve_config_path
# ---------------------------------------------------------------------------


def test_resolve_config_path_returns_none_when_nothing_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENVIKING_CONFIG_FILE", raising=False)
    client = _make_client(config_exists=False)
    assert client._resolve_config_path() is None


def test_resolve_config_path_returns_component_path_when_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENVIKING_CONFIG_FILE", raising=False)
    cfg = tmp_path / "cockpit.ov.conf"
    cfg.touch()
    client = SessionMemoryClient(
        component_name="test",
        config_path=cfg,
        operator_action="n/a",
    )
    assert client._resolve_config_path() == cfg


def test_resolve_config_path_env_override_wins_over_component_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_cfg = tmp_path / "custom-env.ov.conf"
    env_cfg.touch()
    monkeypatch.setenv("OPENVIKING_CONFIG_FILE", str(env_cfg))
    component_cfg = tmp_path / "component.ov.conf"
    component_cfg.touch()
    client = SessionMemoryClient(
        component_name="test",
        config_path=component_cfg,
        operator_action="n/a",
    )
    assert client._resolve_config_path() == env_cfg


def test_resolve_config_path_ignores_other_domain_default_env_when_component_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    openviking_dir = tmp_path / ".openviking"
    openviking_dir.mkdir(parents=True, exist_ok=True)
    env_cfg = openviking_dir / "backend.ov.conf"
    env_cfg.touch()
    component_cfg = openviking_dir / "cockpit.ov.conf"
    component_cfg.touch()
    monkeypatch.setenv("OPENVIKING_CONFIG_FILE", str(env_cfg))
    client = SessionMemoryClient(
        component_name="cockpit",
        config_path=component_cfg,
        operator_action="n/a",
    )
    assert client._resolve_config_path() == component_cfg


def test_resolve_config_path_uses_env_when_component_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_cfg = tmp_path / "env_only.ov.conf"
    env_cfg.touch()
    monkeypatch.setenv("OPENVIKING_CONFIG_FILE", str(env_cfg))
    client = _make_client(config_exists=False)
    assert client._resolve_config_path() == env_cfg


def test_resolve_config_path_env_missing_file_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENVIKING_CONFIG_FILE", str(tmp_path / "does_not_exist.conf"))
    client = _make_client(config_exists=False)
    assert client._resolve_config_path() is None


# ---------------------------------------------------------------------------
# Unit: _get_ov — init behaviour
# ---------------------------------------------------------------------------


def test_get_ov_returns_none_when_no_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENVIKING_CONFIG_FILE", raising=False)
    client = _make_client(config_exists=False)
    assert client._get_ov() is None
    assert client._ov_init_error == "no config file found"


def test_get_ov_returns_none_when_openviking_not_installed(tmp_path: Path) -> None:
    cfg = tmp_path / "test.ov.conf"
    cfg.touch()
    client = SessionMemoryClient(
        component_name="test",
        config_path=cfg,
        operator_action="n/a",
    )
    with patch.dict("sys.modules", {"openviking": None}):
        result = client._get_ov()
    assert result is None
    assert "ModuleNotFoundError" in client._ov_init_error or client._ov_init_error != ""


def test_get_ov_init_attempted_only_once(tmp_path: Path) -> None:
    cfg = tmp_path / "test.ov.conf"
    cfg.touch()
    client = SessionMemoryClient(
        component_name="test",
        config_path=cfg,
        operator_action="n/a",
    )
    call_count = 0

    original_resolve = client._resolve_config_path

    def patched_resolve() -> Path | None:
        nonlocal call_count
        call_count += 1
        return original_resolve()

    client._resolve_config_path = patched_resolve  # type: ignore[method-assign]

    # Mark init as already attempted with an instance.
    client._ov_init_attempted = True
    client._ov_instance = MagicMock()

    # Should return cached instance without calling _resolve_config_path again.
    result = client._get_ov()
    assert result is client._ov_instance
    assert call_count == 0


def test_get_ov_returns_instance_on_successful_init(tmp_path: Path) -> None:
    cfg = tmp_path / "test.ov.conf"
    cfg.touch()
    client = SessionMemoryClient(
        component_name="test",
        config_path=cfg,
        operator_action="n/a",
    )
    mock_ov = MagicMock()
    mock_ov_class = MagicMock(return_value=mock_ov)
    mock_module = MagicMock()
    mock_module.SyncOpenViking = mock_ov_class

    with patch.dict("sys.modules", {"openviking": mock_module}):
        result = client._get_ov()

    assert result is mock_ov
    mock_ov.initialize.assert_called_once()


def test_get_ov_restores_env_after_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "test.ov.conf"
    cfg.touch()
    client = SessionMemoryClient(
        component_name="test",
        config_path=cfg,
        operator_action="n/a",
    )
    monkeypatch.setenv("OPENVIKING_CONFIG_FILE", "/tmp/original.ov.conf")
    mock_ov = MagicMock()
    mock_ov_class = MagicMock(return_value=mock_ov)
    mock_module = MagicMock()
    mock_module.SyncOpenViking = mock_ov_class

    def _initialize() -> None:
        assert os.environ.get("OPENVIKING_CONFIG_FILE") == str(cfg)

    mock_ov.initialize.side_effect = _initialize

    with patch.dict("sys.modules", {"openviking": mock_module}):
        client._get_ov()

    assert os.environ.get("OPENVIKING_CONFIG_FILE") == "/tmp/original.ov.conf"


# ---------------------------------------------------------------------------
# Unit: get_relevant_session_context
# ---------------------------------------------------------------------------


def test_get_relevant_session_context_returns_empty_when_no_ov() -> None:
    client = _make_client(config_exists=False)
    result = client.get_relevant_session_context("sess1", "query")
    assert result == []


def test_get_relevant_session_context_parses_json_results() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    turn = {"query": "what is the revenue?", "answer": "100M"}
    mock_ov.search.return_value = [{"content": json.dumps(turn)}]
    client._ov_instance = mock_ov

    result = client.get_relevant_session_context("sess1", "revenue", limit=2)
    assert result == [turn]


def test_get_relevant_session_context_handles_plain_text_results() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.search.return_value = ["plain text result"]
    client._ov_instance = mock_ov

    result = client.get_relevant_session_context("sess1", "q")
    assert result == [{"text": "plain text result"}]


def test_get_relevant_session_context_skips_empty_content() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.search.return_value = [{"content": ""}, {"text": ""}, ""]
    client._ov_instance = mock_ov

    result = client.get_relevant_session_context("sess1", "q")
    assert result == []


def test_get_relevant_session_context_returns_empty_on_exception() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.search.side_effect = RuntimeError("search failed")
    client._ov_instance = mock_ov

    result = client.get_relevant_session_context("sess1", "q")
    assert result == []


def test_get_relevant_session_context_respects_limit() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.search.return_value = [
        {"content": json.dumps({"turn": i})} for i in range(10)
    ]
    client._ov_instance = mock_ov

    result = client.get_relevant_session_context("sess1", "q", limit=3)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Unit: get_recent_turns
# ---------------------------------------------------------------------------


def _make_msg(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def test_get_recent_turns_returns_empty_when_no_ov() -> None:
    client = _make_client(config_exists=False)
    result = client.get_recent_turns("sess1")
    assert result == []


def test_get_recent_turns_via_get_session(tmp_path: Path) -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True

    turn_payload = {"query": "test", "answer": "42"}
    messages = [
        _make_msg("user", "test"),
        _make_msg("assistant", json.dumps(turn_payload)),
    ]
    mock_session = MagicMock()
    mock_session.messages = messages
    mock_ov = MagicMock()
    mock_ov.get_session.return_value = mock_session
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1", limit=5)
    assert result == [turn_payload]


def test_get_recent_turns_returns_plain_text_when_not_json() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True

    messages = [_make_msg("assistant", "plain answer")]
    mock_session = MagicMock()
    mock_session.messages = messages
    mock_ov = MagicMock()
    mock_ov.get_session.return_value = mock_session
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1")
    assert result == [{"text": "plain answer"}]


def test_get_recent_turns_ignores_user_messages() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True

    messages = [
        _make_msg("user", "this should be ignored"),
        _make_msg("assistant", json.dumps({"answer": "yes"})),
    ]
    mock_session = MagicMock()
    mock_session.messages = messages
    mock_ov = MagicMock()
    mock_ov.get_session.return_value = mock_session
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1", limit=10)
    assert len(result) == 1
    assert result[0] == {"answer": "yes"}


def test_get_recent_turns_respects_limit() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True

    messages = [
        _make_msg("assistant", json.dumps({"turn": i})) for i in range(10)
    ]
    mock_session = MagicMock()
    mock_session.messages = messages
    mock_ov = MagicMock()
    mock_ov.get_session.return_value = mock_session
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1", limit=3)
    assert len(result) == 3
    # Most recent 3: turns 7, 8, 9
    assert result[0] == {"turn": 7}
    assert result[2] == {"turn": 9}


def test_get_recent_turns_falls_back_to_history_attr() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True

    turn = {"answer": "fallback"}
    msg = _make_msg("assistant", json.dumps(turn))

    mock_session = MagicMock(spec=["history"])  # no 'messages' attr
    mock_session.history = [msg]
    mock_ov = MagicMock()
    mock_ov.get_session.return_value = mock_session
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1")
    assert result == [turn]


def test_get_recent_turns_returns_empty_on_exception() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.get_session.side_effect = RuntimeError("network error")
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1")
    assert result == []


def test_get_recent_turns_returns_empty_when_session_is_none() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.get_session.return_value = None
    client._ov_instance = mock_ov

    result = client.get_recent_turns("sess1")
    assert result == []


# ---------------------------------------------------------------------------
# Unit: get_session_context
# ---------------------------------------------------------------------------


def test_get_session_context_prefers_semantic_results() -> None:
    client = _make_client(config_exists=False)
    semantic = [{"query": "q1"}]
    client.get_relevant_session_context = MagicMock(return_value=semantic)  # type: ignore[method-assign]
    client.get_recent_turns = MagicMock(return_value=[{"query": "q2"}])  # type: ignore[method-assign]

    result = client.get_session_context("sess1", "query", semantic_limit=2)

    assert result == semantic
    client.get_recent_turns.assert_not_called()


def test_get_session_context_falls_back_to_recent_turns() -> None:
    client = _make_client(config_exists=False)
    recent = [{"query": "recent"}]
    client.get_relevant_session_context = MagicMock(return_value=[])  # type: ignore[method-assign]
    client.get_recent_turns = MagicMock(return_value=recent)  # type: ignore[method-assign]

    result = client.get_session_context(
        "sess1",
        "query",
        semantic_limit=2,
        recent_limit=1,
    )

    assert result == recent
    client.get_recent_turns.assert_called_once_with("sess1", limit=1)


# ---------------------------------------------------------------------------
# Unit: record_turn
# ---------------------------------------------------------------------------


def test_record_turn_does_nothing_when_no_ov() -> None:
    client = _make_client(config_exists=False)
    # Should not raise.
    client.record_turn("sess1", {"query": "hello", "answer": "world"})


def test_record_turn_writes_user_and_assistant_messages() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    client._ov_instance = mock_ov

    payload = {"query": "test query", "answer": "test answer"}
    client.record_turn("sess1", payload)

    assert mock_ov.add_message.call_count == 2
    user_call = mock_ov.add_message.call_args_list[0]
    assert user_call[0] == ("sess1", "user")
    assert user_call[1]["content"] == "test query"


def test_record_turn_skips_user_message_when_query_empty() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    client._ov_instance = mock_ov

    payload = {"query": "", "answer": "answer only"}
    client.record_turn("sess1", payload)

    # Only the assistant message should be written.
    assert mock_ov.add_message.call_count == 1
    call = mock_ov.add_message.call_args_list[0]
    assert call[0][1] == "assistant"


def test_record_turn_swallows_exceptions() -> None:
    client = _make_client(config_exists=False)
    client._ov_init_attempted = True
    mock_ov = MagicMock()
    mock_ov.add_message.side_effect = OSError("disk full")
    client._ov_instance = mock_ov

    # Should not raise.
    client.record_turn("sess1", {"query": "q", "answer": "a"})


# ---------------------------------------------------------------------------
# Unit: helper functions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "msg,expected",
    [
        ({"role": "user"}, "user"),
        ({"role": "assistant"}, "assistant"),
        ({}, ""),
        ("not a dict", ""),
    ],
)
def test_message_role(msg: Any, expected: str) -> None:
    assert _message_role(msg) == expected


@pytest.mark.parametrize(
    "msg,expected",
    [
        ({"content": "hello"}, "hello"),
        ({"text": "world"}, "world"),
        ({}, ""),
        ("not a dict", ""),
    ],
)
def test_message_content(msg: Any, expected: str) -> None:
    assert _message_content(msg) == expected


# ---------------------------------------------------------------------------
# Integration: log_startup_status
# ---------------------------------------------------------------------------


def test_log_startup_status_emits_once(caplog: pytest.LogCaptureFixture) -> None:
    client = _make_client(config_exists=False)
    import logging

    with caplog.at_level(logging.WARNING):
        client.log_startup_status()
        client.log_startup_status()  # second call — must be a no-op

    # Only one warning about missing config, not two.
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "test.session_memory" in warnings[0].message
