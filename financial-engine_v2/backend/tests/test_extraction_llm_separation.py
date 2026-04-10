"""Tests for extraction LLM / chat LLM separation.

Verifies that:
- EXTRACTION_LLAMACPP_URL routes extraction calls to a dedicated endpoint
- When unset, extraction falls back to LLAMACPP_URL (backward compatible)
- extract_model defaults to the instruct model, not coder
- Non-extraction calls are unaffected by the new env var
"""

import os

import pytest

from app.core.config import settings
from app.services.llamacpp_runtime import (
    _resolve_model_id,
    resolve_extraction_runtime_config,
    resolve_llm_runtime_config,
)


class TestExtractModelDefault:
    """extract_model code default should be an instruct model.

    Note: .env may override the code default at runtime.  These tests
    verify the code-level default by inspecting the Settings field directly.
    """

    def test_code_default_is_instruct(self):
        field_default = settings.__class__.model_fields["extract_model"].default
        assert "instruct" in field_default.lower(), (
            f"extract_model code default should be instruct, got: {field_default}"
        )

    def test_code_default_is_not_coder(self):
        field_default = settings.__class__.model_fields["extract_model"].default
        assert "coder" not in field_default.lower(), (
            f"extract_model code default should not be coder: {field_default}"
        )


class TestResolveExtractionRuntimeConfig:
    """resolve_extraction_runtime_config uses dedicated URL when available."""

    def test_with_extraction_url_env_var(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
        monkeypatch.setenv("EXTRACT_MODEL", "qwen2.5-14b-instruct")
        url, model = resolve_extraction_runtime_config()
        assert url == "http://127.0.0.1:8002"
        assert model == "qwen2.5-14b-instruct"

    def test_with_extraction_url_strips_v1(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002/v1")
        url, _ = resolve_extraction_runtime_config()
        assert url == "http://127.0.0.1:8002"

    def test_fallback_to_llamacpp_url_when_unset(self, monkeypatch):
        monkeypatch.delenv("EXTRACTION_LLAMACPP_URL", raising=False)
        # Clear settings value too
        monkeypatch.setattr(settings, "extraction_llamacpp_url", "")
        monkeypatch.setenv("LLAMACPP_URL", "http://127.0.0.1:8001")
        url, _ = resolve_extraction_runtime_config()
        assert url == "http://127.0.0.1:8001"

    def test_explicit_base_url_takes_priority(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
        url, _ = resolve_extraction_runtime_config(base_url="http://127.0.0.1:9999")
        assert url == "http://127.0.0.1:9999"

    def test_explicit_model_takes_priority(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
        monkeypatch.setenv("EXTRACT_MODEL", "qwen2.5-14b-instruct")
        _, model = resolve_extraction_runtime_config(model="custom-model")
        assert model == "custom-model"

    def test_does_not_affect_general_resolve(self, monkeypatch):
        """Setting EXTRACTION_LLAMACPP_URL should not change resolve_llm_runtime_config."""
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
        monkeypatch.setenv("LLAMACPP_URL", "http://127.0.0.1:8001")
        url, _ = resolve_llm_runtime_config()
        assert url == "http://127.0.0.1:8001"


class TestLlmRoutingWithExtractionComponent:
    """_resolve_runtime_from_metadata routes extraction to dedicated endpoint."""

    def test_extraction_component_routes_to_extraction_url(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
        monkeypatch.setenv("EXTRACT_MODEL", "qwen2.5-14b-instruct")

        from app.services.llm import _resolve_runtime_from_metadata
        from app.services.router import RoutingDecision

        decision = RoutingDecision(
            selected_role="reasoning",
            policy_name="standard",
            model_name="qwen2.5-coder-14b",
            execution_queue="llm_gpu",
            task_type="reasoning",
            financial_task_type="",
            provider="llamacpp",
            base_url="http://127.0.0.1:8001",
        )
        metadata = {"component": "multipass_extraction", "task_type": "reasoning"}
        url, model = _resolve_runtime_from_metadata(decision, metadata)
        assert url == "http://127.0.0.1:8002"
        assert model == "qwen2.5-14b-instruct"

    def test_commentary_extractor_also_routes_to_extraction(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")

        from app.services.llm import _resolve_runtime_from_metadata
        from app.services.router import RoutingDecision

        decision = RoutingDecision(
            selected_role="reasoning",
            policy_name="standard",
            model_name="qwen2.5-coder-14b",
            execution_queue="llm_gpu",
            task_type="reasoning",
            financial_task_type="",
            provider="llamacpp",
            base_url="http://127.0.0.1:8001",
        )
        metadata = {"component": "commentary_memo_extractor"}
        url, _ = _resolve_runtime_from_metadata(decision, metadata)
        assert url == "http://127.0.0.1:8002"

    def test_non_extraction_component_uses_general_url(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_LLAMACPP_URL", "http://127.0.0.1:8002")
        monkeypatch.setenv("LLAMACPP_URL", "http://127.0.0.1:8001")

        from app.services.llm import _resolve_runtime_from_metadata
        from app.services.router import RoutingDecision

        decision = RoutingDecision(
            selected_role="coding",
            policy_name="standard",
            model_name="qwen2.5-coder-14b",
            execution_queue="llm_gpu",
            task_type="coding",
            financial_task_type="",
            provider="llamacpp",
            base_url="http://127.0.0.1:8001",
        )
        metadata = {"component": "chat", "task_type": "coding"}
        url, _ = _resolve_runtime_from_metadata(decision, metadata)
        assert url == "http://127.0.0.1:8001"


class TestResolveModelId:
    def test_maps_broken_alias_to_usable_extract_model_stem(self):
        models_payload = {
            "data": [
                {
                    "id": "model:qwen2.5-14b-instruct",
                    "status": {"value": "unloaded"},
                },
                {
                    "id": "qwen2.5-14b-instruct-q4_k_m",
                    "status": {
                        "value": "unloaded",
                        "args": [
                            "--model",
                            "/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf",
                        ],
                    },
                },
            ]
        }

        resolved = _resolve_model_id(models_payload, "qwen2.5-14b-instruct")

        assert resolved == "qwen2.5-14b-instruct-q4_k_m"

    def test_preserves_exact_requested_model_when_registry_entry_is_usable(self):
        models_payload = {
            "data": [
                {
                    "id": "model:qwen2.5-14b-instruct",
                    "status": {
                        "value": "loaded",
                    },
                },
            ]
        }

        resolved = _resolve_model_id(models_payload, "model:qwen2.5-14b-instruct")

        assert resolved == "model:qwen2.5-14b-instruct"

    def test_preserves_requested_model_when_registry_has_no_usable_match(self):
        models_payload = {
            "data": [
                {"id": "model:gpt-oss-20b", "status": {"value": "loaded"}},
            ]
        }

        resolved = _resolve_model_id(models_payload, "nonexistent-model")

        assert resolved == "nonexistent-model"
