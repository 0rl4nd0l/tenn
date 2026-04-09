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
    assert all(model["size_gb"] == 0.0 for model in nvme_models + ssd_models)


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
