from __future__ import annotations

from pathlib import Path

import pytest

import app.main as main


def test_system_capabilities_snapshot_reports_feature_blockers(monkeypatch):
    monkeypatch.setattr(main.settings, "enable_extraction", True, raising=False)
    monkeypatch.setattr(main.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(main.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(main.settings, "task_mode", "celery", raising=False)
    monkeypatch.setattr(main.settings, "qdrant_collection", "asx_docs", raising=False)

    monkeypatch.setattr(
        main,
        "_system_status_snapshot",
        lambda: {
            "redis_connected": False,
            "qdrant_connected": True,
            "collections_present": ["asx_docs"],
            "document_count_estimate": 12,
            "last_ingestion_activity": "2026-03-29T00:00:00Z",
        },
    )
    monkeypatch.setattr(
        main,
        "_database_state_snapshot",
        lambda: {"reachable": True, "document_count": 12, "extraction_count": 6},
    )
    monkeypatch.setattr(main, "resolve_llm_runtime_config", lambda: ("http://127.0.0.1:8001", "chat-model"))
    monkeypatch.setattr(
        main,
        "resolve_extraction_runtime_config",
        lambda: ("http://127.0.0.1:8002", "extract-model"),
    )
    monkeypatch.setattr(
        main,
        "resolve_embedding_runtime_config",
        lambda: ("http://127.0.0.1:11434", "embed-model"),
    )
    monkeypatch.setattr(
        main,
        "_probe_llamacpp_runtime",
        lambda base_url, expected_model, timeout=5.0: {
            "base_url": base_url,
            "expected_model": expected_model,
            "reachable": base_url.endswith(":8001"),
            "loaded_models": [expected_model] if base_url.endswith(":8001") else [],
            "model_available": base_url.endswith(":8001"),
        },
    )
    monkeypatch.setattr(
        main,
        "_probe_embedding_runtime",
        lambda base_url, expected_model, timeout=5.0: {
            "base_url": base_url,
            "expected_model": expected_model,
            "reachable": True,
            "dimension": 768,
        },
    )
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": "embed-model",
            "configured_model": "embed-model",
            "document_count": 12,
            "extraction_count": 6,
            "qdrant_collection_exists": True,
            "qdrant_points_count": 33,
        },
    )

    payload = main.system_capabilities()
    features = payload["features"]

    assert payload["authority"] == "backend"
    assert features["ingestion"]["status"] == "blocked"
    assert "celery_broker_unreachable" in features["ingestion"]["blockers"]
    assert features["extraction"]["status"] == "blocked"
    assert "extraction_runtime_unreachable" in features["extraction"]["blockers"]
    assert features["embeddings"]["status"] == "available"
    assert features["rag"]["status"] == "available"
    assert any(p["id"] == "start_extraction_runtime" for p in payload["proposals"])


def test_system_capabilities_snapshot_marks_disabled_features(monkeypatch):
    monkeypatch.setattr(main.settings, "enable_extraction", False, raising=False)
    monkeypatch.setattr(main.settings, "enable_embeddings", False, raising=False)
    monkeypatch.setattr(main.settings, "enable_qdrant", False, raising=False)
    monkeypatch.setattr(main.settings, "task_mode", "sync", raising=False)

    monkeypatch.setattr(
        main,
        "_system_status_snapshot",
        lambda: {
            "redis_connected": False,
            "qdrant_connected": False,
            "collections_present": [],
            "document_count_estimate": 0,
            "last_ingestion_activity": None,
        },
    )
    monkeypatch.setattr(
        main,
        "_database_state_snapshot",
        lambda: {"reachable": True, "document_count": 0, "extraction_count": 0},
    )
    monkeypatch.setattr(main, "resolve_llm_runtime_config", lambda: ("http://127.0.0.1:8001", "chat-model"))
    monkeypatch.setattr(main, "resolve_extraction_runtime_config", lambda: ("http://127.0.0.1:8002", "extract-model"))
    monkeypatch.setattr(main, "resolve_embedding_runtime_config", lambda: ("http://127.0.0.1:11434", "embed-model"))
    monkeypatch.setattr(
        main,
        "_probe_llamacpp_runtime",
        lambda base_url, expected_model, timeout=5.0: {"base_url": base_url, "expected_model": expected_model, "reachable": False},
    )
    monkeypatch.setattr(
        main,
        "_probe_embedding_runtime",
        lambda base_url, expected_model, timeout=5.0: {"base_url": base_url, "expected_model": expected_model, "reachable": False},
    )
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": None,
            "configured_model": "embed-model",
            "document_count": 0,
            "extraction_count": 0,
            "qdrant_collection_exists": False,
            "qdrant_points_count": 0,
        },
    )

    payload = main.system_capabilities()
    features = payload["features"]

    assert features["extraction"]["status"] == "disabled"
    assert features["embeddings"]["status"] == "disabled"
    assert features["rag"]["status"] == "disabled"
    assert payload["proposals"] == []


def test_apply_capability_proposal_starts_extraction_runtime(monkeypatch):
    launched = []
    monkeypatch.setattr(main, "PROJECT_ROOT", Path("/tmp/financial-engine_v2"))
    monkeypatch.setattr(Path, "exists", lambda self: True)
    monkeypatch.setattr(
        main.subprocess,
        "Popen",
        lambda *args, **kwargs: launched.append((args, kwargs)),
    )
    monkeypatch.setattr(
        main,
        "resolve_extraction_runtime_config",
        lambda: ("http://127.0.0.1:8002", "extract-model"),
    )

    probes = iter([
        {"reachable": False, "error": "not ready"},
        {"reachable": True, "loaded_models": ["extract-model"], "model_available": True},
    ])
    monkeypatch.setattr(main, "_probe_llamacpp_runtime", lambda *args, **kwargs: next(probes))
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)

    payload = main.apply_system_proposal(main.CapabilityProposalApplyRequest(proposal_id="start_extraction_runtime"))

    assert payload["ok"] is True
    assert payload["status"] == "applied"
    assert launched


def test_apply_capability_proposal_rejects_unknown():
    with pytest.raises(main.HTTPException, match="unknown or unsupported proposal"):
        main.apply_system_proposal(main.CapabilityProposalApplyRequest(proposal_id="unknown"))


def test_apply_capability_proposal_updates_access_state(monkeypatch):
    stored = {}

    monkeypatch.setattr(main, "_load_access_state", lambda: {"web_enabled": False, "rag_enabled": False, "db_diagnostic_query_enabled": False})
    monkeypatch.setattr(main, "_write_access_state", lambda state: stored.setdefault("value", dict(state)))

    payload = main.apply_system_proposal(main.CapabilityProposalApplyRequest(proposal_id="enable_web_access"))

    assert payload["ok"] is True
    assert payload["status"] == "applied"
    assert payload["access"]["web_enabled"] is True
    assert stored["value"]["web_enabled"] is True
