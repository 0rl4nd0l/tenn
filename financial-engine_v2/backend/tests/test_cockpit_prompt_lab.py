from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService


PROMPT_LAB_HEADERS = {"X-Cockpit-Prompt-Lab-Intent": "inspect-prompts"}


class _FakeHybridRouter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat(self, prompt: str, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return "dry run response"

    def last_attempt_metadata(self):
        return {"source": "api", "model": "fake-model"}


class _FakeAgentLoop:
    def _build_system_prompt(self) -> str:
        return "AGENT SYSTEM PROMPT\nNever fabricate financial data."


class _FakeChatController:
    llm_timeout_seconds = 30.0

    def __init__(self) -> None:
        self._hybrid_router = _FakeHybridRouter()
        self._agent_loop = _FakeAgentLoop()
        self.ollama_client = None

    def _build_system_instruction(self, mode, ticker, local_payload) -> str:
        return (
            f"You are Tenn. mode={mode} ticker={ticker or 'none'}.\n"
            "Every factual claim must be grounded in the current response payload."
        )


def _client(monkeypatch) -> tuple[TestClient, SimpleNamespace]:
    fake_service = SimpleNamespace(chat_controller=_FakeChatController())
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    return TestClient(app), fake_service


def test_prompt_lab_routes_include_locked_no_llm_path(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", "1")
    client, _service = _client(monkeypatch)

    response = client.get("/api/cockpit/prompts/routes", headers=PROMPT_LAB_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    route_ids = {item["route_id"] for item in payload["routes"]}
    assert "structured_agent" in route_ids
    assert "slash_control" in route_ids
    slash = next(item for item in payload["routes"] if item["route_id"] == "slash_control")
    assert slash["editable"] is False
    assert slash["supports_dry_run"] is False


def test_prompt_lab_preview_includes_sample_message_and_locked_blocks(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", "1")
    client, _service = _client(monkeypatch)

    response = client.post(
        "/api/cockpit/prompts/preview",
        headers=PROMPT_LAB_HEADERS,
        json={
            "route_id": "structured_agent",
            "message": "Analyse BHP",
            "ticker": "BHP",
            "draft_override": "Use terse headings.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"]["route_id"] == "structured_agent"
    assert payload["messages"][-1]["role"] == "user"
    assert "Analyse BHP" in payload["messages"][-1]["content"]
    assert any(block["locked"] for block in payload["blocks"])
    draft = next(block for block in payload["blocks"] if block["block_id"] == "operator_draft")
    assert draft["locked"] is False
    assert "Use terse headings" in draft["content"]


def test_prompt_lab_slash_preview_has_no_messages(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", "1")
    client, _service = _client(monkeypatch)

    response = client.post(
        "/api/cockpit/prompts/preview",
        headers=PROMPT_LAB_HEADERS,
        json={"route_id": "slash_control", "message": "/prompt"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"] == []
    assert payload["blocks"][0]["kind"] == "no_llm"


def test_prompt_lab_dry_run_uses_llm_client_without_chat_history(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", "1")
    client, service = _client(monkeypatch)

    response = client.post(
        "/api/cockpit/prompts/dry-run",
        headers=PROMPT_LAB_HEADERS,
        json={"route_id": "structured_agent", "message": "Analyse BHP", "ticker": "BHP"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "dry run response"
    assert payload["routing_metadata"]["model"] == "fake-model"
    calls = service.chat_controller._hybrid_router.calls
    assert len(calls) == 1
    assert "Current ticker context: BHP" in calls[0]["prompt"]


def test_prompt_lab_dry_run_rejects_no_llm_route(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", "1")
    client, _service = _client(monkeypatch)

    response = client.post(
        "/api/cockpit/prompts/dry-run",
        headers=PROMPT_LAB_HEADERS,
        json={"route_id": "slash_control", "message": "/prompt"},
    )

    assert response.status_code == 400
    assert "does not support LLM dry-run" in response.json()["detail"]


def test_prompt_lab_routes_reject_when_operator_access_disabled(monkeypatch) -> None:
    monkeypatch.delenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", raising=False)
    client, _service = _client(monkeypatch)

    response = client.get("/api/cockpit/prompts/routes", headers=PROMPT_LAB_HEADERS)

    assert response.status_code == 403
    assert response.json()["detail"] == "Prompt Lab operator access is disabled"


def test_prompt_lab_dry_run_requires_operator_intent_before_llm(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_PROMPT_LAB_OPERATOR_ACCESS", "1")
    client, service = _client(monkeypatch)

    response = client.post(
        "/api/cockpit/prompts/dry-run",
        json={"route_id": "structured_agent", "message": "Analyse BHP", "ticker": "BHP"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Prompt Lab operator intent header is required"
    assert service.chat_controller._hybrid_router.calls == []
