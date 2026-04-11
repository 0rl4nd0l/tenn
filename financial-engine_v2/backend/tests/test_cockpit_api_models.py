from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import cockpit_api
from app.routes.cockpit_api import router


def test_build_ui_sources_includes_rag_hit_metadata_and_doc_fallback() -> None:
    sources = cockpit_api._build_ui_sources(
        [
            {
                "type": "local_context",
                "details": {
                    "qual_context": {
                        "hits": [
                            {
                                "title": "Q4 Appendix 4C",
                                "url": "https://example.com/q4-appendix-4c.pdf",
                                "text": "Operating cash flow was positive and cash closed at $106.9m.",
                                "final_score": 0.92,
                                "document_id": "doc-123",
                                "source_corpus": "filing",
                                "published_at": "2025-10-31T00:00:00Z",
                            }
                        ]
                    },
                    "docs": [
                        {
                            "title": "Quarterly Cashflow",
                            "source_url": "https://example.com/quarterly-cashflow.pdf",
                            "document_id": "doc-456",
                            "doc_class": "results",
                            "published_at": "2025-10-31T00:00:00Z",
                        }
                    ],
                },
            }
        ]
    )

    assert len(sources) == 2
    assert sources[0]["title"] == "Q4 Appendix 4C"
    assert sources[0]["url"] == "https://example.com/q4-appendix-4c.pdf"
    assert sources[0]["document_id"] == "doc-123"
    assert sources[0]["doc_type"] == "filing"
    assert sources[0]["snippet"] == "Operating cash flow was positive and cash closed at $106.9m."
    assert sources[1]["url"] == "https://example.com/quarterly-cashflow.pdf"
    assert sources[1]["doc_type"] == "results"


def test_build_ui_sources_includes_company_dump_documents() -> None:
    sources = cockpit_api._build_ui_sources(
        [
            {
                "type": "company_dump",
                "details": {
                    "backend": {
                        "docs": [
                            {
                                "title": "EOS Appendix 4C",
                                "source_url": "https://example.com/eos-4c.pdf",
                                "document_id": "doc-eos-1",
                                "doc_class": "results",
                                "published_at": "2025-10-31T00:00:00Z",
                            }
                        ]
                    }
                },
            }
        ]
    )

    assert sources == [
        {
            "title": "EOS Appendix 4C",
            "score": 0.0,
            "url": "https://example.com/eos-4c.pdf",
            "snippet": None,
            "published_at": "2025-10-31T00:00:00Z",
            "document_id": "doc-eos-1",
            "source_id": None,
            "doc_type": "results",
            "path": None,
            "kind": "document",
        }
    ]


def test_build_ui_sources_includes_web_and_news_links() -> None:
    sources = cockpit_api._build_ui_sources(
        [
            {
                "type": "news_search",
                "details": {
                    "hits": [
                        {
                            "title": "EOS wins new contract",
                            "url": "https://news.example.com/eos-contract",
                            "snippet": "The company announced a new defence contract.",
                            "score": 0.81,
                        }
                    ]
                },
            },
            {
                "type": "web",
                "details": {
                    "pages": [
                        {
                            "title": "Investor presentation",
                            "url": "https://example.com/presentation",
                            "text": "Latest investor deck covering liquidity and outlook.",
                        }
                    ]
                },
            },
        ]
    )

    assert len(sources) == 2
    assert sources[0]["kind"] == "news"
    assert sources[0]["url"] == "https://news.example.com/eos-contract"
    assert sources[1]["kind"] == "web"
    assert sources[1]["url"] == "https://example.com/presentation"
    assert sources[1]["snippet"] == "Latest investor deck covering liquidity and outlook."


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
    assert [group["location"] for group in payload["groups"]] == ["nvme", "manual_fallback"]

    nvme_models = payload["groups"][0]["models"]
    fb_models = payload["groups"][1]["models"]

    assert {model["id"] for model in nvme_models} == {
        "model:qwen2.5-14b-instruct",
        "model:qwen3.5-35b-a3b",
    }
    assert [model["id"] for model in fb_models] == ["model:gpt-oss-20b"]
    assert all(m.get("manual_fallback") for m in fb_models)
    assert all(model["size_gb"] >= 0.0 for model in nvme_models + fb_models)


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


def test_cockpit_config_prefers_native_model_when_fallback_also_loaded(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_llama_server_models",
        lambda: {
            "model:gpt-oss-20b": {
                "status": "loaded",
                "model_path": "/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf",
                "path_stem": "gpt-oss-20b-mxfp4",
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


def test_cockpit_config_uses_fallback_when_only_fallback_loaded(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_llama_server_models",
        lambda: {
            "model:gpt-oss-20b": {
                "status": "loaded",
                "model_path": "/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf",
                "path_stem": "gpt-oss-20b-mxfp4",
            },
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/config")
    assert response.status_code == 200
    assert response.json()["llm_model"] == "model:gpt-oss-20b"


def test_cockpit_config_reports_extraction_activity_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(cockpit_api, "_fetch_llama_server_models", lambda: {})
    monkeypatch.setattr(
        cockpit_api,
        "get_extraction_activity_snapshot",
        lambda: {
            "active": True,
            "source": "file",
            "expires_in_seconds": 42,
            "active_runs": [
                {
                    "token": "tok-1",
                    "run_id": "run-1",
                    "document_id": "doc-1",
                    "requested_method": "docling",
                    "strict_method": True,
                    "ticker": "BHP",
                    "title": "Quarterly Activities",
                    "expires_at": 123.0,
                    "expires_in_seconds": 42,
                }
            ],
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["extraction_active"] is True
    assert payload["extraction_activity_source"] == "file"
    assert payload["extraction_activity_expires_in_seconds"] == 42
    assert payload["extraction_active_runs"][0]["run_id"] == "run-1"
    assert payload["extraction_active_runs"][0]["document_id"] == "doc-1"


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
    assert payload["active_model"] == "model:gpt-oss-20b"
    assert [group["location"] for group in payload["groups"]] == [
        "nvme",
        "hdd",
        "manual_fallback",
    ]
    fb = payload["groups"][2]["models"][0]
    assert fb["id"] == "model:gpt-oss-20b"
    assert fb["filename"] == "gpt-oss-20b-mxfp4.gguf"
    assert fb["quantization"] == "MXFP4"
    assert fb["available"] is True
    assert fb["manual_fallback"] is True
    assert fb["size_gb"] >= 0.0


def test_cockpit_load_model_noops_when_requested_model_already_loaded(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_runtime_models",
        lambda base_url=None: {
            "model:qwen2.5-14b-instruct": {
                "status": "loaded",
                "model_path": "/models/qwen2.5-14b-instruct-q4_k_m.gguf",
                "path_stem": "qwen2.5-14b-instruct-q4_k_m",
            }
        },
    )
    monkeypatch.setattr(
        cockpit_api,
        "resolve_extraction_runtime_config",
        lambda *args, **kwargs: ("http://127.0.0.1:8001", "model:qwen2.5-14b-instruct"),
        raising=False,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/models/load",
        json={"model_id": "model:qwen2.5-14b-instruct"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["already_loaded"] is True
    assert payload["resolved_model"] == "model:qwen2.5-14b-instruct"


def test_cockpit_load_model_uses_router_api_when_model_is_available(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_runtime_models",
        lambda base_url=None: {
            "model:qwen2.5-14b-instruct": {
                "status": "unloaded",
                "model_path": "/models/qwen2.5-14b-instruct-q4_k_m.gguf",
                "path_stem": "qwen2.5-14b-instruct-q4_k_m",
            },
            "model:gpt-oss-20b": {
                "status": "loaded",
                "model_path": "/models/gpt-oss-20b.gguf",
                "path_stem": "gpt-oss-20b",
            },
        },
    )
    monkeypatch.setattr(
        cockpit_api,
        "resolve_extraction_runtime_config",
        lambda *args, **kwargs: ("http://127.0.0.1:8001", "model:qwen2.5-14b-instruct"),
        raising=False,
    )
    monkeypatch.setattr(
        "cockpit.integrations.llamacpp_manager.load_model_api",
        lambda **kwargs: kwargs["model_name"] == "model:qwen2.5-14b-instruct",
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/models/load",
        json={"model_id": "model:qwen2.5-14b-instruct"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["already_loaded"] is False
    assert payload["resolved_model"] == "model:qwen2.5-14b-instruct"


def test_cockpit_load_model_returns_404_when_model_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_runtime_models",
        lambda base_url=None: {
            "model:gpt-oss-20b": {
                "status": "loaded",
                "model_path": "/models/gpt-oss-20b.gguf",
                "path_stem": "gpt-oss-20b",
            }
        },
    )
    monkeypatch.setattr(
        cockpit_api,
        "resolve_extraction_runtime_config",
        lambda *args, **kwargs: ("http://127.0.0.1:8001", "model:qwen2.5-14b-instruct"),
        raising=False,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/models/load",
        json={"model_id": "model:qwen2.5-14b-instruct"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["requested_model"] == "model:qwen2.5-14b-instruct"
    assert "model:gpt-oss-20b" in detail["available_models"]
