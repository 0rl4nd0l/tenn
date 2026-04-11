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
        self._hybrid_router = None

    def build_chat_response(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=self.text,
            routing_metadata=None,
            action_preview=None,
            tool_traces=[],
            evidence=[],
        )


class _FakeControllerWithMode:
    def __init__(self, text: str, mode: str, prompt: str) -> None:
        self.text = text
        self.mode = mode
        self.prompt = prompt

    def build_chat_response(self, **kwargs):
        return SimpleNamespace(
            text=self.text,
            routing_metadata=None,
            action_preview=None,
            tool_traces=[],
            evidence=[],
            mode=self.mode,
            prompt=self.prompt,
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


def test_chat_stream_uses_last_attempt_route_when_controller_metadata_is_empty() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:qwen3.5-35b-a3b")
    controller = _FakeController(
        "I encountered an error communicating with the language model: Error code: 529"
    )
    controller._hybrid_router = SimpleNamespace(
        last_attempt_metadata=lambda: {
            "source": "api",
            "model": "claude-sonnet-test",
            "latency_ms": 0,
            "cost_usd": 0.0,
            "routing_reason": "force:api",
        }
    )
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="/cloud tell me about AGL",
        session_id="session-last-attempt",
    )

    assert "Error code: 529" in response.text
    assert response.routing_metadata == {
        "source": "api",
        "model": "claude-sonnet-test",
        "latency_ms": 0,
        "cost_usd": 0.0,
        "routing_reason": "force:api",
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


def test_chat_stream_records_response_mode_in_turn_diagnostics() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeControllerWithMode(
        text="Deep answer.",
        mode="deep_analysis",
        prompt="prompt excerpt",
    )
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="deep dive",
        session_id="session-deep",
    )

    assert response.text == "Deep answer."
    saved = service._recent_turn_diagnostics["session-deep"][-1]
    assert saved["response_mode"] == "deep_analysis"
    assert saved["prompt"] == "prompt excerpt"


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
