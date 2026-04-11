from __future__ import annotations

from app.services import llamacpp_runtime


def test_build_llm_headers_discovers_local_key_for_local_runtime(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)
    monkeypatch.setattr(
        llamacpp_runtime,
        "_discover_local_llamacpp_api_key",
        lambda: "detected-local-key",
    )

    headers = llamacpp_runtime.build_llm_headers(base_url="http://127.0.0.1:8001")

    assert headers["Authorization"] == "Bearer detected-local-key"


def test_build_llm_headers_prefers_local_key_over_legacy_ollama_token(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_API_KEY", "wrong-legacy-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)
    monkeypatch.setattr(
        llamacpp_runtime,
        "_discover_local_llamacpp_api_key",
        lambda: "detected-local-key",
    )

    headers = llamacpp_runtime.build_llm_headers(base_url="http://127.0.0.1:8001")

    assert headers["Authorization"] == "Bearer detected-local-key"


def test_build_llm_headers_falls_back_to_default_local_key(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)
    monkeypatch.setattr(
        llamacpp_runtime,
        "_discover_local_llamacpp_api_key",
        lambda: "",
    )

    headers = llamacpp_runtime.build_llm_headers(base_url="http://localhost:8001")

    assert (
        headers["Authorization"]
        == f"Bearer {llamacpp_runtime.DEFAULT_LOCAL_LLAMACPP_API_KEY}"
    )


def test_build_llm_headers_does_not_inject_local_key_for_remote_runtime(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)
    monkeypatch.setattr(
        llamacpp_runtime,
        "_discover_local_llamacpp_api_key",
        lambda: "detected-local-key",
    )

    headers = llamacpp_runtime.build_llm_headers(base_url="https://remote-llm.example")

    assert "Authorization" not in headers
