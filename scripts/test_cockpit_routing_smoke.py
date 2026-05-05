from __future__ import annotations

import importlib.util
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
