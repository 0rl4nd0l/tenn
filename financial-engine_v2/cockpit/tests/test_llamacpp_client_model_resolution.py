from __future__ import annotations

from cockpit.integrations.llamacpp_client import LlamaCppClient


def test_resolve_model_id_maps_broken_alias_to_usable_stem(monkeypatch) -> None:
    client = LlamaCppClient("http://127.0.0.1:8001", "model:gpt-oss-20b")
    monkeypatch.setattr(
        client,
        "_fetch_model_registry",
        lambda: {
            "model:qwen2.5-14b-instruct": {
                "status": "unloaded",
                "model_path": "",
                "path_stem": "",
            },
            "qwen2.5-14b-instruct-q4_k_m": {
                "status": "unloaded",
                "model_path": "/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf",
                "path_stem": "qwen2.5-14b-instruct-q4_k_m",
            },
        },
    )

    assert (
        client._resolve_model_id("model:qwen2.5-14b-instruct")
        == "qwen2.5-14b-instruct-q4_k_m"
    )


def test_resolve_model_id_falls_back_to_loaded_model_when_requested_missing(
    monkeypatch,
) -> None:
    client = LlamaCppClient("http://127.0.0.1:8001", "model:gpt-oss-20b")
    monkeypatch.setattr(
        client,
        "_fetch_model_registry",
        lambda: {
            "model:qwen3.5-35b-a3b": {
                "status": "loaded",
                "model_path": "/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf",
                "path_stem": "Qwen3.5-35B-A3B-Q4_K_M",
            },
            "model:gpt-oss-20b": {
                "status": "unloaded",
                "model_path": "/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf",
                "path_stem": "gpt-oss-20b-mxfp4",
            },
        },
    )

    assert client._resolve_model_id("model:missing") == "model:qwen3.5-35b-a3b"
