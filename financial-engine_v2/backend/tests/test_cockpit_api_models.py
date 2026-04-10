from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import cockpit_api
from app.routes.cockpit_api import router


def test_cockpit_models_falls_back_to_llama_registry_when_local_dirs_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cockpit_api, "_scan_model_directory", lambda _dir: [])
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_llama_server_models",
        lambda: {
            "Qwen3.5-35B-A3B-Q4_K_M": {
                "status": "unloaded",
                "model_path": "/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf",
                "path_stem": "Qwen3.5-35B-A3B-Q4_K_M",
            },
            "model:qwen3.5-35b-a3b": {
                "status": "loaded",
                "model_path": "/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf",
                "path_stem": "Qwen3.5-35B-A3B-Q4_K_M",
            },
            "gpt-oss-20b-mxfp4": {
                "status": "unloaded",
                "model_path": "/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf",
                "path_stem": "gpt-oss-20b-mxfp4",
            },
            "model:gpt-oss-20b": {
                "status": "unloaded",
                "model_path": "/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf",
                "path_stem": "gpt-oss-20b-mxfp4",
            },
            "qwen2.5-14b-instruct-q4_k_m": {
                "status": "unloaded",
                "model_path": "/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf",
                "path_stem": "qwen2.5-14b-instruct-q4_k_m",
            },
            "model:qwen2.5-14b-instruct": {
                "status": "unloaded",
                "model_path": "",
                "path_stem": "",
            },
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/models")
    assert response.status_code == 200

    payload = response.json()
    assert payload["active_model"] == "model:qwen3.5-35b-a3b"
    assert [group["location"] for group in payload["groups"]] == ["nvme", "ssd"]

    nvme_models = payload["groups"][0]["models"]
    ssd_models = payload["groups"][1]["models"]

    assert {model["id"] for model in nvme_models} == {
        "model:qwen2.5-14b-instruct",
        "model:qwen3.5-35b-a3b",
    }
    assert [model["id"] for model in ssd_models] == ["model:gpt-oss-20b"]
    assert all(model["size_gb"] >= 0.0 for model in nvme_models + ssd_models)


def test_cockpit_config_prefers_loaded_model_from_llama_registry(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_llama_server_models",
        lambda: {
            "model:gpt-oss-20b": {
                "status": "unloaded",
                "model_path": "",
                "path_stem": "",
            },
            "model:qwen3.5-35b-a3b": {
                "status": "loaded",
                "model_path": "/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf",
                "path_stem": "Qwen3.5-35B-A3B-Q4_K_M",
            },
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/config")
    assert response.status_code == 200
    assert response.json()["llm_model"] == "model:qwen3.5-35b-a3b"


def test_cockpit_config_reports_anthropic_key_from_effective_config(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cockpit_api, "_fetch_llama_server_models", lambda: {})
    monkeypatch.setattr(
        cockpit_api,
        "compute_effective_cockpit_config",
        lambda *args, **kwargs: {
            "cockpit_llm": {
                "defaults": {
                    "anthropic_api_key": "test-config-key",
                    "anthropic_model": "claude-sonnet-4-20250514",
                }
            }
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/config")
    assert response.status_code == 200
    assert response.json()["anthropic_key_configured"] is True


def test_cockpit_models_fills_missing_ssd_group_from_llama_registry(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COCKPIT_MODELS_NVME_DIR", "/models/nvme")
    monkeypatch.setenv("COCKPIT_MODELS_SSD_DIR", "/models/ssd")
    monkeypatch.setenv("COCKPIT_MODELS_HDD_DIR", "/models/hdd")

    def fake_scan(dir_path: str):
        if dir_path == "/models/nvme":
            return [
                cockpit_api.ModelInfo(
                    id="qwen2.5-14b-instruct-q4_k_m",
                    filename="qwen2.5-14b-instruct-q4_k_m.gguf",
                    size_gb=8.4,
                    quantization="Q4_K_M",
                    available=True,
                )
            ]
        if dir_path == "/models/hdd":
            return [
                cockpit_api.ModelInfo(
                    id="qwen3-14b-q4_k_m",
                    filename="qwen3-14b-q4_k_m.gguf",
                    size_gb=8.4,
                    quantization="Q4_K_M",
                    available=True,
                )
            ]
        return []

    monkeypatch.setattr(cockpit_api, "_scan_model_directory", fake_scan)
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_llama_server_models",
        lambda: {
            "model:qwen2.5-14b-instruct": {
                "status": "unloaded",
                "model_path": "/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf",
                "path_stem": "qwen2.5-14b-instruct-q4_k_m",
            },
            "model:gpt-oss-20b": {
                "status": "loaded",
                "model_path": "/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf",
                "path_stem": "gpt-oss-20b-mxfp4",
            },
            "model:qwen3-14b": {
                "status": "unloaded",
                "model_path": "/mnt/hdd-cold/tenn/models/qwen3-14b-q4_k_m.gguf",
                "path_stem": "qwen3-14b-q4_k_m",
            },
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/models")
    assert response.status_code == 200

    payload = response.json()
    assert [group["location"] for group in payload["groups"]] == ["nvme", "ssd", "hdd"]
    assert payload["groups"][1]["models"][0]["id"] == "model:gpt-oss-20b"
    assert payload["groups"][1]["models"][0]["filename"] == "gpt-oss-20b-mxfp4.gguf"
    assert payload["groups"][1]["models"][0]["quantization"] == "MXFP4"
    assert payload["groups"][1]["models"][0]["available"] is True
    assert payload["groups"][1]["models"][0]["size_gb"] >= 0.0
