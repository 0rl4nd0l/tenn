from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services import router_state


def test_default_extraction_activity_state_file_falls_back_from_unwritable_shared_root(
    monkeypatch, tmp_path
) -> None:
    unwritable_root = tmp_path / "shared-unwritable"
    unwritable_root.mkdir()
    monkeypatch.delenv("TENN_EXTRACTION_ACTIVE_FILE", raising=False)
    monkeypatch.setattr(
        router_state, "_EXTRACTION_ACTIVITY_SHARED_ROOTS", (unwritable_root,)
    )

    real_access = router_state.os.access

    def _fake_access(path, mode):
        if Path(path).resolve() == unwritable_root.resolve():
            return False
        return real_access(path, mode)

    monkeypatch.setattr(router_state.os, "access", _fake_access)

    assert router_state._default_extraction_activity_state_file() == Path(
        "/tmp/tenn_extraction_active.json"
    ).resolve()


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
        assert active_run["started_at"]


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


def _find_unused_pid() -> int:
    import os as _os

    for candidate in (999_997, 999_998, 999_999):
        try:
            _os.kill(candidate, 0)
        except ProcessLookupError:
            return candidate
        except OSError:
            continue
    raise AssertionError("no unused pid available on this host")


class _FakeRedisClient:
    def __init__(self, hashes: dict[str, dict[str, bytes]]) -> None:
        self.hashes = {key: dict(value) for key, value in hashes.items()}

    def hgetall(self, key: str):
        return dict(self.hashes.get(key, {}))

    def hdel(self, key: str, *members: str) -> None:
        bucket = self.hashes.setdefault(key, {})
        for member in members:
            encoded = (
                member if isinstance(member, bytes) else str(member).encode("utf-8")
            )
            bucket.pop(encoded, None)

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.hashes.pop(key, None)


def test_is_extraction_active_prunes_dead_holder_pid(monkeypatch, tmp_path) -> None:
    """Token registered by a since-killed same-host process must be pruned.

    Covers the bug where a Celery child killed via SIGKILL/OOM/time_limit
    never runs `finally`, leaving a ghost token that the UI then renders as
    a phantom 'Running' job until the 30-min TTL expires.
    """
    import json as _json

    state_path = tmp_path / "dead-pid-extraction.json"
    lock_path = tmp_path / "dead-pid-extraction.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )

    dead_pid = _find_unused_pid()
    expiry = time.time() + 600
    payload = {
        "tokens": {"ghost-token": expiry},
        "metadata": {
            "ghost-token": {
                "run_id": "run-ghost",
                "document_id": "doc-ghost",
                "host": router_state._HOST_ID,
                "pid": str(dead_pid),
            }
        },
    }
    state_path.write_text(_json.dumps(payload), encoding="utf-8")

    assert router_state.is_extraction_active() is False
    assert router_state.get_extraction_activity_snapshot()["active"] is False
    assert state_path.exists() is False


def test_is_extraction_active_prunes_prior_process_generation_redis_token(
    monkeypatch, tmp_path
) -> None:
    """A reused same-host pid from an older server instance must be pruned.

    This covers stale redis tokens left behind when the backend process exits
    abruptly and restarts with the same container pid (commonly pid 1).
    """
    import json as _json
    import os as _os

    state_path = tmp_path / "redis-prior-generation.json"
    lock_path = tmp_path / "redis-prior-generation.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)

    token = "redis-ghost"
    expiry = time.time() + 600
    fake_client = _FakeRedisClient(
        {
            router_state._EXTRACTION_ACTIVE_KEY: {
                token.encode("utf-8"): str(expiry).encode("utf-8")
            },
            router_state._EXTRACTION_ACTIVE_META_KEY: {
                token.encode("utf-8"): _json.dumps(
                    {
                        "document_id": "doc-ghost",
                        "host": router_state._HOST_ID,
                        "pid": str(_os.getpid()),
                        "started_at": "2000-01-01T00:00:00+00:00",
                    }
                ).encode("utf-8")
            },
        }
    )
    monkeypatch.setattr(router_state, "_build_redis_client", lambda redis_url=None: fake_client)

    assert router_state.is_extraction_active() is False
    assert fake_client.hgetall(router_state._EXTRACTION_ACTIVE_KEY) == {}
    assert fake_client.hgetall(router_state._EXTRACTION_ACTIVE_META_KEY) == {}


def test_is_extraction_active_trusts_cross_host_tokens(monkeypatch, tmp_path) -> None:
    """Tokens from a different host must not be pruned — we can't verify their PID."""
    import json as _json

    state_path = tmp_path / "cross-host-extraction.json"
    lock_path = tmp_path / "cross-host-extraction.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )

    foreign_host = f"not-{router_state._HOST_ID}"
    expiry = time.time() + 600
    payload = {
        "tokens": {"remote-token": expiry},
        "metadata": {
            "remote-token": {
                "host": foreign_host,
                "pid": "1",  # irrelevant, lives on another host
            }
        },
    }
    state_path.write_text(_json.dumps(payload), encoding="utf-8")

    assert router_state.is_extraction_active() is True
    snapshot = router_state.get_extraction_activity_snapshot()
    assert snapshot["active"] is True
    assert snapshot["active_runs"][0]["host"] == foreign_host


def test_extraction_activity_records_host_and_pid(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "host-pid-extraction.json"
    lock_path = tmp_path / "host-pid-extraction.lock"
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_STATE_FILE", state_path)
    monkeypatch.setattr(router_state, "_EXTRACTION_ACTIVE_LOCK_FILE", lock_path)
    monkeypatch.setattr(
        router_state, "_build_redis_client", lambda redis_url=None: None
    )

    with router_state.extraction_activity():
        snapshot = router_state.get_extraction_activity_snapshot()
        run = snapshot["active_runs"][0]
        assert run["host"] == router_state._HOST_ID
        assert int(run["pid"]) == __import__("os").getpid()
        assert run["boot_id"] == router_state._PROCESS_BOOT_ID
