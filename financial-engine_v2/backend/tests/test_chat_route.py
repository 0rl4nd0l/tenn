from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.core.config as config
from app.routes import chat as chat_route


def _request_with_headers(*, session_id: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if session_id is not None:
        headers.append((b"x-session-id", session_id.encode()))
    return Request({"type": "http", "headers": headers})


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(chat_route.router)
    app.include_router(chat_route.router, prefix="/api")
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
@pytest.mark.parametrize(
    "payload",
    [
        {
            "message": "summarise BHP",
            "mode": "analysis",
            "ticker": "BHP",
            "session_id": "session-1",
        },
        {
            "message": "confirm proposal-1",
            "mode": "strategy",
        },
    ],
)
def test_legacy_chat_routes_reject_missing_or_wrong_api_key_before_side_effects(
    monkeypatch,
    path,
    headers,
    payload,
):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    blocked_calls = {
        "chat_with_tenn": Mock(
            side_effect=AssertionError("chat_with_tenn should not run")
        ),
        "record_turn": Mock(side_effect=AssertionError("record_turn should not run")),
        "propose_change": Mock(
            side_effect=AssertionError("propose_change should not run")
        ),
        "confirm_change": Mock(
            side_effect=AssertionError("confirm_change should not run")
        ),
        "apply_change": Mock(side_effect=AssertionError("apply_change should not run")),
    }
    for name, mock in blocked_calls.items():
        monkeypatch.setattr(chat_route, name, mock)

    response = _client().post(
        path,
        json=payload,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    for mock in blocked_calls.values():
        mock.assert_not_called()


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
def test_legacy_chat_routes_accept_matching_api_key(monkeypatch, path):
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    chat_with_tenn = Mock(
        return_value={
            "answer": "ok",
            "insights": [],
            "supporting_evidence": [],
            "confidence": 0.5,
            "sources": [],
        }
    )
    monkeypatch.setattr(chat_route, "chat_with_tenn", chat_with_tenn)

    response = _client().post(
        path,
        json={"message": "hello", "mode": "analysis", "ticker": "BHP"},
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "type": "analysis",
        "content": {
            "answer": "ok",
            "insights": [],
            "supporting_evidence": [],
            "confidence": 0.5,
            "sources": [],
        },
    }
    chat_with_tenn.assert_called_once_with("hello", ticker="BHP", session_id=None)


def test_analysis_route_degrades_on_chat_exception(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("explode")

    monkeypatch.setattr(chat_route, "chat_with_tenn", _boom)

    payload = chat_route.ChatRequest(message="hi", mode="analysis", ticker="BHP")
    result = chat_route.chat(payload, _request_with_headers())

    assert result["type"] == "analysis"
    assert result["content"]["system_status"] == "degraded"
    assert result["content"]["error"] == "explode"


def test_analysis_route_sanitizes_non_finite_payload(monkeypatch):
    monkeypatch.setattr(
        chat_route,
        "chat_with_tenn",
        lambda *args, **kwargs: {
            "answer": "ok",
            "insights": [],
            "supporting_evidence": [{"score": float("nan")}],
            "confidence": 0.5,
            "sources": [{"final_score": float("inf")}],
        },
    )

    payload = chat_route.ChatRequest(message="hi", mode="analysis")
    result = chat_route.chat(payload, _request_with_headers(session_id="session-1"))

    assert result == {
        "type": "analysis",
        "content": {
            "answer": "ok",
            "insights": [],
            "supporting_evidence": [{"score": None}],
            "confidence": 0.5,
            "sources": [{"final_score": None}],
        },
    }


def test_analysis_route_uses_header_session_id(monkeypatch):
    captured: dict[str, str | None] = {}

    def _fake_chat_with_tenn(message: str, *, ticker: str | None, session_id: str | None, model: str | None = None):
        captured["message"] = message
        captured["ticker"] = ticker
        captured["session_id"] = session_id
        return {"answer": "ok", "insights": [], "supporting_evidence": [], "confidence": 0.1, "sources": []}

    monkeypatch.setattr(chat_route, "chat_with_tenn", _fake_chat_with_tenn)

    payload = chat_route.ChatRequest(message="hello", mode="analysis", ticker="BHP")
    result = chat_route.chat(payload, _request_with_headers(session_id="header-session"))

    assert result["type"] == "analysis"
    assert captured == {
        "message": "hello",
        "ticker": "BHP",
        "session_id": "header-session",
    }
