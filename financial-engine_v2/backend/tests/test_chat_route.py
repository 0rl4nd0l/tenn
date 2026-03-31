from __future__ import annotations

from starlette.requests import Request

from app.routes import chat as chat_route


def _request_with_headers(*, session_id: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if session_id is not None:
        headers.append((b"x-session-id", session_id.encode()))
    return Request({"type": "http", "headers": headers})


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

    def _fake_chat_with_tenn(message: str, *, ticker: str | None, session_id: str | None):
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
