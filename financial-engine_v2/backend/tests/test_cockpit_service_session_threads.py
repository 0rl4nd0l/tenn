from __future__ import annotations

import sys
import threading
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.cockpit_service import CockpitService


def _prime_service(service: CockpitService) -> None:
    service._feedback_lock = threading.Lock()  # type: ignore[attr-defined]
    service._recent_turn_diagnostics = {}  # type: ignore[attr-defined]


class _FakeStateStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def add_chat_message(
        self, thread_id: str, role: str, content: str, created_at: str
    ) -> None:
        self.calls.append((thread_id, role, content))


class _FakeController:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []

    def build_chat_response(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=self.text,
            routing_metadata=None,
            action_preview=None,
            tool_traces=[],
            evidence=[],
        )


class _FakeLlmClient:
    def __init__(self, model: str) -> None:
        self.model = model

    def switch_model(self, new_model: str) -> None:
        self.model = new_model


def test_chat_stream_uses_session_thread_and_persists_turns() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.chat_controller = _FakeController("ignored")

    captured: dict[str, object] = {}
    controller = _FakeController("Here is the summary.")

    def _build_chat_controller(thread_id: str):
        captured["thread_id"] = thread_id
        return controller

    service._build_chat_controller = _build_chat_controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="ok",
        ticker="BHP",
        session_id="session-123",
        enable_web=False,
        rag=True,
        db_diagnostics=False,
    )

    assert captured["thread_id"] == "session-123"
    assert controller.calls[0]["prior_ticker"] == "BHP"
    assert response.text == "Here is the summary."
    assert service.state_store.calls == [
        ("session-123", "user", "ok"),
        ("session-123", "assistant", "Here is the summary."),
    ]


def test_chat_stream_defaults_blank_session_to_global_thread() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeController("Hello")
    service.chat_controller = controller
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="hello",
        session_id="  ",
    )

    assert response.text == "Hello"
    assert service.state_store.calls == [
        ("global-main", "user", "hello"),
        ("global-main", "assistant", "Hello"),
    ]


def test_chat_stream_populates_model_metadata_even_when_controller_omits_it() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:gpt-oss-20b")
    controller = _FakeController("No evidence available.")
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="tell me about BHP",
        session_id="session-model-meta",
        model="model:qwen3.5-35b-a3b",
    )

    assert service.llm_client.model == "model:qwen3.5-35b-a3b"
    assert response.routing_metadata == {
        "model": "model:qwen3.5-35b-a3b",
        "source": "local",
        "latency_ms": 0,
        "cost_usd": 0.0,
    }


def test_chat_stream_emits_model_switch_status_events() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:gpt-oss-20b")
    controller = _FakeController("Switch completed.")
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    statuses: list[str] = []
    response = CockpitService.chat_stream(
        service,
        message="switch model",
        session_id="session-switch",
        model="model:qwen3.5-35b-a3b",
        on_status=statuses.append,
    )

    assert response.text == "Switch completed."
    assert service.llm_client.model == "model:qwen3.5-35b-a3b"
    assert statuses[0] == "Switching model: model:gpt-oss-20b -> model:qwen3.5-35b-a3b"
    assert "Model ready: model:qwen3.5-35b-a3b" in statuses


def test_preload_preferred_model_skips_during_active_extraction(monkeypatch) -> None:
    service = CockpitService.__new__(CockpitService)
    service.llm_client = SimpleNamespace(
        base_url="http://127.0.0.1:8001",
        model="model:gpt-oss-20b",
        switch_model=lambda new_model: None,
    )

    class _Response:
        content = b'{"data": []}'

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": [
                    {
                        "id": "model:qwen2.5-14b-instruct",
                        "status": {"value": "loaded"},
                    }
                ]
            }

    monkeypatch.setattr(
        "app.services.cockpit_service.httpx.get",
        lambda *args, **kwargs: _Response(),
    )
    monkeypatch.setattr("app.services.router_state.is_extraction_active", lambda: True)

    called = {"load": False}
    monkeypatch.setattr(
        "cockpit.integrations.llamacpp_manager.load_model_api",
        lambda **kwargs: called.__setitem__("load", True),
    )

    CockpitService._preload_preferred_model(
        service,
        preferred_model="model:qwen3.5-35b-a3b",
        api_key="local-openai-key",
    )

    assert called["load"] is False
