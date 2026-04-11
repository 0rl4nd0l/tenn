from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services import router_state


def test_extraction_activity_file_fallback_tracks_active_state(
    monkeypatch, tmp_path
) -> None:
    state_path = tmp_path / "extraction-active.json"
    lock_path = tmp_path / "extraction-active.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )

    assert router_state.is_extraction_active() is False

    with router_state.extraction_activity():
        assert router_state.is_extraction_active() is True
        assert state_path.exists()

    assert router_state.is_extraction_active() is False
    assert state_path.exists() is False


def test_legacy_set_extraction_active_uses_file_fallback(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "legacy-extraction.json"
    lock_path = tmp_path / "legacy-extraction.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )
    monkeypatch.setattr(router_state, "_legacy_extraction_activity_token", None)

    router_state.set_extraction_active(True)
    assert router_state.is_extraction_active() is True

    router_state.set_extraction_active(False)
    assert router_state.is_extraction_active() is False


def test_extraction_activity_snapshot_preserves_file_metadata(
    monkeypatch, tmp_path
) -> None:
    state_path = tmp_path / "metadata-extraction.json"
    lock_path = tmp_path / "metadata-extraction.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )

    metadata = {
        "run_id": "run-123",
        "document_id": "doc-456",
        "requested_method": "docling",
        "strict_method": True,
        "ticker": "BHP",
        "title": "Quarterly Activities",
    }

    with router_state.extraction_activity(metadata=metadata):
        snapshot = router_state.get_extraction_activity_snapshot()
        assert snapshot["active"] is True
        assert snapshot["source"] == "file"
        assert snapshot["token_count"] == 1
        assert len(snapshot["active_runs"]) == 1
        active_run = snapshot["active_runs"][0]
        assert active_run["run_id"] == "run-123"
        assert active_run["document_id"] == "doc-456"
        assert active_run["requested_method"] == "docling"
        assert active_run["strict_method"] is True
        assert active_run["ticker"] == "BHP"
        assert active_run["title"] == "Quarterly Activities"


def test_is_extraction_active_prunes_expired_file_tokens(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "stale-extraction.json"
    lock_path = tmp_path / "stale-extraction.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )

    expired_payload = {"tokens": {"stale-token": time.time() - 5}}
    state_path.write_text(__import__("json").dumps(expired_payload), encoding="utf-8")

    assert router_state.is_extraction_active() is False
    assert state_path.exists() is False
