from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from cockpit.storage.state import StateStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fake_service(tmp_path: Path) -> SimpleNamespace:
    state_store = StateStore(str(tmp_path / "state.db"))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        state_store=state_store,
        artifact_store=SimpleNamespace(logs_dir=logs_dir),
    )


def test_chat_sessions_list_get_delete_round_trip(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    fake_service.state_store.add_chat_message(
        "session-1", "user", "How is BHP going?", _now_iso()
    )
    fake_service.state_store.add_chat_message(
        "session-1", "assistant", "BHP is stable.", _now_iso()
    )
    fake_service.state_store.add_chat_message(
        "session-2", "user", "Tell me about RIO", _now_iso()
    )
    fake_service.state_store.add_chat_message(
        "session-2", "assistant", "RIO had mixed results.", _now_iso()
    )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    list_response = client.get("/api/cockpit/chat/sessions?limit=10")
    assert list_response.status_code == 200
    sessions = list_response.json()["items"]
    assert len(sessions) == 2
    assert {item["session_id"] for item in sessions} == {"session-1", "session-2"}
    assert all(int(item["message_count"]) >= 2 for item in sessions)

    get_response = client.get("/api/cockpit/chat/sessions/session-1?limit=50")
    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["session_id"] == "session-1"
    assert payload["message_count"] == 2
    assert payload["items"][0]["role"] == "user"
    assert payload["items"][1]["role"] == "assistant"

    delete_response = client.delete("/api/cockpit/chat/sessions/session-1")
    assert delete_response.status_code == 200
    deleted_payload = delete_response.json()
    assert deleted_payload["ok"] is True
    assert deleted_payload["session_id"] == "session-1"
    assert deleted_payload["deleted_count"] == 2

    after_delete = client.get("/api/cockpit/chat/sessions/session-1")
    assert after_delete.status_code == 200
    assert after_delete.json()["items"] == []


def test_chat_session_reload_preserves_saved_source_labels(tmp_path, monkeypatch) -> None:
    state_store = StateStore(str(tmp_path / "state.db"))

    class FakeService:
        def __init__(self) -> None:
            self.state_store = state_store

        @staticmethod
        def _resolve_thread_id(session_id: str | None) -> str:
            return str(session_id or "").strip() or "global-main"

        def chat_stream(self, message: str, session_id: str | None = None, **kwargs):
            thread_id = self._resolve_thread_id(session_id)
            self.state_store.add_chat_message(thread_id, "user", message, _now_iso())
            self.state_store.add_chat_message(
                thread_id,
                "assistant",
                "A2M recall coverage is visible in local news.",
                _now_iso(),
            )
            return SimpleNamespace(
                text="A2M recall coverage is visible in local news.",
                evidence=[
                    {
                        "type": "news_search",
                        "details": {
                            "hits": [
                                {
                                    "title": "A2M recall article",
                                    "url": "https://example.com/a2m-recall",
                                    "evidence_labels": [
                                        "claim_verified",
                                        "local_news_context",
                                    ],
                                    "claim_verified": True,
                                }
                            ]
                        },
                    }
                ],
                action_preview=None,
                routing_metadata={"source": "local", "model": "model:test"},
                tool_traces=[],
            )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: FakeService())
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/chat",
        json={
            "message": "what happened to A2M?",
            "session_id": "session-labels",
            "stream": False,
        },
    )
    assert response.status_code == 200

    reload_response = client.get("/api/cockpit/chat/sessions/session-labels?limit=20")
    assert reload_response.status_code == 200
    assistant = [
        item for item in reload_response.json()["items"] if item["role"] == "assistant"
    ][-1]
    assert assistant["routing_metadata"]["source_coverage_status"] == "claim_verified"
    assert assistant["routing_metadata"]["claim_verified_source_count"] == 1
    assert assistant["sources"][0]["evidence_labels"] == [
        "claim_verified",
        "local_news_context",
    ]


def test_legacy_chat_session_reload_uses_unclassified_safe_fallback(
    tmp_path, monkeypatch
) -> None:
    fake_service = _fake_service(tmp_path)
    fake_service.state_store.add_chat_message(
        "session-legacy", "assistant", "Legacy answer without source metadata.", _now_iso()
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/chat/sessions/session-legacy?limit=20")

    assert response.status_code == 200
    assistant = response.json()["items"][0]
    assert assistant["routing_metadata"]["evidence_labels"] == ["unknown_unclassified"]
    assert assistant["routing_metadata"]["claim_verified_source_count"] == 0
    assert assistant["sources"] == []


def test_chat_session_create_lists_and_deletes_empty_session(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/chat/sessions",
        json={"session_id": "session-empty"},
    )
    assert create_response.status_code == 200
    created_payload = create_response.json()
    assert created_payload["ok"] is True
    assert created_payload["session_id"] == "session-empty"
    assert created_payload["created"] is True

    list_response = client.get("/api/cockpit/chat/sessions?limit=10")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["session_id"] == "session-empty"
    assert items[0]["message_count"] == 0

    delete_response = client.delete("/api/cockpit/chat/sessions/session-empty")
    assert delete_response.status_code == 200
    deleted_payload = delete_response.json()
    assert deleted_payload["ok"] is True
    assert deleted_payload["deleted_count"] == 0


def test_chat_session_requires_non_empty_id(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/chat/sessions/%20%20%20")
    assert response.status_code == 400
