from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "cockpit_routing_smoke.py"
spec = importlib.util.spec_from_file_location("cockpit_routing_smoke", MODULE_PATH)
assert spec is not None and spec.loader is not None
SMOKE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = SMOKE
spec.loader.exec_module(SMOKE)


def _result():
    return SMOKE.SmokeResult()


def test_request_json_sends_api_key_header(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"ok": True}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["headers"] = {
            key.lower(): value for key, value in request.header_items()
        }
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(SMOKE.urllib.request, "urlopen", fake_urlopen)

    data = SMOKE._request_json(
        "GET",
        "http://127.0.0.1:8000/api/cockpit/config",
        api_key=" local-secret ",
        timeout=3.0,
    )

    assert data == {"ok": True}
    assert captured["headers"]["x-api-key"] == "local-secret"
    assert captured["timeout"] == 3.0


def test_parser_api_key_defaults_from_env(monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_API_KEY", "env-secret")

    args = SMOKE.build_parser().parse_args([])

    assert args.api_key == "env-secret"


def test_validate_generic_prompt_response_accepts_api_with_no_sources() -> None:
    result = _result()

    SMOKE.validate_generic_prompt_response(
        result,
        {
            "text": "ok",
            "source": "api",
            "model": "claude-sonnet-test",
            "sources": [],
            "routing_metadata": {
                "source": "api",
                "model": "claude-sonnet-test",
                "routing_reason": "force:api",
            },
        },
    )

    assert result.ok is True


def test_validate_generic_prompt_response_fails_orchestrator_memory_noise() -> None:
    result = _result()

    SMOKE.validate_generic_prompt_response(
        result,
        {
            "text": "ok\n\nCoverage and Failure Signals:",
            "source": "orchestrator",
            "model": None,
            "sources": [
                {
                    "title": "Australian inflation gauge has cooled",
                    "kind": "context",
                }
            ],
            "routing_metadata": {
                "source": "orchestrator",
                "sources": ["market_memory"],
            },
        },
    )

    failed = {item["name"] for item in result.failures}
    assert {
        "generic_model_present",
        "generic_not_orchestrator",
        "generic_no_visible_sources",
        "generic_no_coverage_noise",
    } <= failed


def test_validate_generic_prompt_response_fails_force_api_local_source() -> None:
    result = _result()

    SMOKE.validate_generic_prompt_response(
        result,
        {
            "text": "ok",
            "source": "local",
            "model": "model:qwen",
            "sources": [],
            "routing_metadata": {
                "source": "local",
                "model": "model:qwen",
                "routing_reason": "force:api",
            },
        },
    )

    assert any(item["name"] == "generic_forced_local_not_local" for item in result.failures)


def test_validate_api_only_config_requires_backend_and_preferences_alignment() -> None:
    result = _result()

    SMOKE.validate_api_only_config(
        result,
        config={"routing_policy": "api_only", "routing_policy_override": "api_only"},
        preferences={
            "api_default_enabled": True,
            "chat_routing_policy_override": "api_only",
        },
        require_api_only=True,
    )

    assert result.ok is True
