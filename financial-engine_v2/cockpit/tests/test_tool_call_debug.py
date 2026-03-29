"""Tests for tool_call_debug helpers."""

from __future__ import annotations

import pytest

from cockpit.core.tool_call_debug import (
    build_tool_trace_entry,
    cockpit_tool_chat_debug_mode,
    extract_error_message,
    format_failure_block,
    initial_tool_debug_choice_from_env,
    summarize_arguments_for_log,
    tool_result_succeeded,
)


def test_summarize_arguments_redacts_sensitive() -> None:
    s = summarize_arguments_for_log({"ticker": "BHP", "api_key": "secret"})
    assert "BHP" in s
    assert "secret" not in s
    assert "redacted" in s.lower()


def test_tool_result_succeeded() -> None:
    assert tool_result_succeeded({"ok": True, "data": 1}) is True
    assert tool_result_succeeded({"ok": False, "error": "x"}) is False
    assert tool_result_succeeded({"error": "boom"}) is False
    assert tool_result_succeeded({"result": "ok"}) is True


def test_build_tool_trace_entry_failed() -> None:
    entry = build_tool_trace_entry(
        iteration=2,
        tool_name="query_ticker_data",
        arguments={"ticker": "ZZZ"},
        result={"ok": False, "error": "no data"},
        duration_ms=12.3,
    )
    assert entry["ok"] is False
    assert entry["iteration"] == 2
    assert "no data" in entry["error"]
    assert entry["hint"]


def test_format_failure_block() -> None:
    traces = [
        {
            "iteration": 1,
            "tool": "foo",
            "arguments_summary": "{}",
            "ok": True,
            "error": "",
            "duration_ms": 1.0,
            "hint": "",
        },
        {
            "iteration": 1,
            "tool": "bar",
            "arguments_summary": "{}",
            "ok": False,
            "error": "nope",
            "duration_ms": 2.0,
            "hint": "check backend",
        },
    ]
    fail_only = format_failure_block(traces, include_success=False)
    assert "foo" not in fail_only
    assert "FAILED" in fail_only
    full = format_failure_block(traces, include_success=True)
    assert "foo" in full
    assert "ok in" in full


@pytest.mark.parametrize(
    ("env", "expect_fail", "expect_full"),
    [
        ("", True, False),
        ("failures", True, False),
        ("1", True, True),
        ("off", False, False),
    ],
)
def test_cockpit_tool_chat_debug_mode(
    monkeypatch: pytest.MonkeyPatch,
    env: str,
    expect_fail: bool,
    expect_full: bool,
) -> None:
    monkeypatch.delenv("COCKPIT_TOOL_DEBUG", raising=False)
    if env:
        monkeypatch.setenv("COCKPIT_TOOL_DEBUG", env)
    a, b = cockpit_tool_chat_debug_mode()
    assert a is expect_fail
    assert b is expect_full


@pytest.mark.parametrize(
    ("env", "choice"),
    [
        ("", "failures"),
        ("failures", "failures"),
        ("1", "full"),
        ("off", "off"),
        ("full", "full"),
    ],
)
def test_initial_tool_debug_choice_from_env(
    monkeypatch: pytest.MonkeyPatch,
    env: str,
    choice: str,
) -> None:
    monkeypatch.delenv("COCKPIT_TOOL_DEBUG", raising=False)
    if env:
        monkeypatch.setenv("COCKPIT_TOOL_DEBUG", env)
    assert initial_tool_debug_choice_from_env() == choice


def test_extract_error_message() -> None:
    assert "x" in extract_error_message({"error": "x"})
