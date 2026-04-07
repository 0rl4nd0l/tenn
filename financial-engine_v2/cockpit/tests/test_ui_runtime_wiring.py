from __future__ import annotations

import types
import asyncio
from pathlib import Path

from cockpit.ui.app import CockpitApp


class _FakeProbeClient:
    def __init__(self, url: str, model: str, api_key: str = "") -> None:
        self.url = url
        self.model = model
        self.api_key = api_key

    def health(self, timeout: float = 2.0):
        return {"ok": True, "url": self.url}


def test_start_extraction_runtime_uses_endpoint_env_precedence(monkeypatch):
    app = object.__new__(CockpitApp)
    app.repo_root = Path("/workspace/tenn")
    app.ollama_client = types.SimpleNamespace(model="qwen2.5-14b-instruct")
    async def _fake_sleep(_seconds: float) -> None:
        return None

    scenarios = [
        ({"EXTRACTION_LLAMACPP_URL": "http://127.0.0.1:8002", "LLAMACPP_URL": "http://127.0.0.1:8001"}, "http://127.0.0.1:8002"),
        ({"LLAMACPP_URL": "http://127.0.0.1:8011"}, "http://127.0.0.1:8011"),
        ({}, "http://localhost:8001"),
    ]
    for env_vars, expected_url in scenarios:
        logs: list[str] = []
        app._write_log = lambda _target, message: logs.append(message)
        for key in ("EXTRACTION_LLAMACPP_URL", "LLAMACPP_URL"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        popen_calls: list[list[str]] = []
        monkeypatch.setattr("cockpit.ui.app.subprocess.Popen", lambda cmd, **kwargs: popen_calls.append(cmd))
        monkeypatch.setattr("cockpit.ui.app.LlamaCppClient", _FakeProbeClient)
        monkeypatch.setattr("cockpit.ui.app.asyncio.sleep", _fake_sleep)

        ok = asyncio.run(CockpitApp._start_extraction_runtime(app, "chat-log"))

        assert ok is True
        assert popen_calls == [["bash", "scripts/run_extraction_server.sh"]]
        assert any(f"Probing extraction runtime endpoint: {expected_url}" in message for message in logs)
