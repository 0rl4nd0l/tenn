from __future__ import annotations

from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.core.config as config
import app.main as main_app
from app.api import routes
from app.routes import chat as chat_route


def _request_with_headers(*, session_id: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if session_id is not None:
        headers.append((b"x-session-id", session_id.encode()))
    return Request({"type": "http", "headers": headers})


def _mounted_route(path: str, method: str) -> APIRoute:
    for candidate in main_app.app.routes:
        if (
            isinstance(candidate, APIRoute)
            and candidate.path == path
            and method in candidate.methods
        ):
            return candidate
    raise AssertionError(f"route not found: {method} {path}")


def _has_api_key_dependency(route: APIRoute) -> bool:
    return any(
        dependency.call is routes.require_api_key
        for dependency in route.dependant.dependencies
    )


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


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
def test_legacy_chat_routes_register_api_key_dependency(path: str) -> None:
    assert _has_api_key_dependency(_mounted_route(path, "POST"))


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
def test_legacy_chat_analysis_rejects_missing_or_wrong_key_before_side_effects(
    monkeypatch,
    path: str,
    headers: dict[str, str],
) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    called = {"chat_with_tenn": False, "record_turn": False}

    def fake_chat_with_tenn(*_: Any, **__: Any) -> dict[str, Any]:
        called["chat_with_tenn"] = True
        return {
            "answer": "should not run",
            "insights": [],
            "supporting_evidence": [],
            "confidence": 0.5,
            "sources": [],
        }

    def fake_record_turn(*_: Any, **__: Any) -> None:
        called["record_turn"] = True

    monkeypatch.setattr(chat_route, "chat_with_tenn", fake_chat_with_tenn)
    monkeypatch.setattr(chat_route, "record_turn", fake_record_turn)

    response = TestClient(main_app.app).post(
        path,
        json={
            "message": "What changed for BHP?",
            "mode": "analysis",
            "ticker": "BHP",
            "session_id": "session-1",
        },
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}
    assert called == {"chat_with_tenn": False, "record_turn": False}


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-secret"}])
@pytest.mark.parametrize(
    ("message", "expected_call"),
    [
        ("tighten thesis risk wording", "propose_change"),
        ("confirm proposal-1", "confirm_change"),
        ("apply proposal-1", "apply_change"),
    ],
)
def test_legacy_chat_strategy_rejects_missing_or_wrong_key_before_side_effects(
    monkeypatch,
    path: str,
    headers: dict[str, str],
    message: str,
    expected_call: str,
) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    called = {
        "propose_change": False,
        "confirm_change": False,
        "apply_change": False,
    }

    def mark_called(name: str):
        def inner(*_: Any, **__: Any) -> dict[str, str]:
            called[name] = True
            return {"proposal_id": "proposal-1"}

        return inner

    monkeypatch.setattr(chat_route, "propose_change", mark_called("propose_change"))
    monkeypatch.setattr(chat_route, "confirm_change", mark_called("confirm_change"))
    monkeypatch.setattr(chat_route, "apply_change", mark_called("apply_change"))

    response = TestClient(main_app.app).post(
        path,
        json={"message": message, "mode": "strategy"},
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}
    assert called == {
        "propose_change": False,
        "confirm_change": False,
        "apply_change": False,
    }
    assert called[expected_call] is False


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
def test_legacy_chat_accepts_matching_key_for_analysis(monkeypatch, path: str) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    captured: dict[str, str | None] = {}

    def fake_chat_with_tenn(
        message: str,
        *,
        ticker: str | None,
        session_id: str | None,
    ) -> dict[str, Any]:
        captured.update(
            {
                "message": message,
                "ticker": ticker,
                "session_id": session_id,
            }
        )
        return {
            "answer": "ok",
            "insights": [],
            "supporting_evidence": [],
            "confidence": 0.5,
            "sources": [],
        }

    monkeypatch.setattr(chat_route, "chat_with_tenn", fake_chat_with_tenn)

    response = TestClient(main_app.app).post(
        path,
        json={"message": "hello", "mode": "analysis", "ticker": "BHP"},
        headers={"X-API-Key": "local-secret", "X-Session-ID": "header-session"},
    )

    assert response.status_code == 200
    assert response.json()["type"] == "analysis"
    assert captured == {
        "message": "hello",
        "ticker": "BHP",
        "session_id": "header-session",
    }


@pytest.mark.parametrize("path", ["/chat", "/api/chat"])
def test_legacy_chat_accepts_matching_key_for_strategy(monkeypatch, path: str) -> None:
    monkeypatch.setattr(config.settings, "local_api_key", "local-secret", raising=False)
    captured: dict[str, str] = {}

    def fake_propose_change(message: str) -> dict[str, str]:
        captured["message"] = message
        return {"proposal_id": "proposal-1"}

    monkeypatch.setattr(chat_route, "propose_change", fake_propose_change)

    response = TestClient(main_app.app).post(
        path,
        json={"message": "tighten thesis risk wording", "mode": "strategy"},
        headers={"X-API-Key": "local-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "type": "proposal",
        "content": {"proposal_id": "proposal-1"},
    }
    assert captured == {"message": "tighten thesis risk wording"}
