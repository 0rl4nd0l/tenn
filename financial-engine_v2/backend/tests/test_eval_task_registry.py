"""Unit tests for the in-memory eval task registry.

The registry is the primitive that backs the background-eval path added to
/api/extraction-eval/real-gold. It must be thread-safe because the FastAPI
handler schedules the eval on a daemon thread and the polling GET endpoint
reads the record from the anyio threadpool.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.eval_task_registry import (  # noqa: E402
    TaskRegistry,
    TaskStatus,
)


@pytest.mark.unit
def test_register_returns_pending_record_with_unique_id():
    registry = TaskRegistry()
    first = registry.register()
    second = registry.register()
    assert first.status is TaskStatus.PENDING
    assert second.status is TaskStatus.PENDING
    assert first.task_id
    assert first.task_id != second.task_id
    assert first.result is None
    assert first.error is None


@pytest.mark.unit
def test_get_unknown_id_returns_none():
    registry = TaskRegistry()
    assert registry.get("does-not-exist") is None


@pytest.mark.unit
def test_set_running_then_completed_transitions_and_persists_result():
    registry = TaskRegistry()
    record = registry.register()

    registry.set_running(record.task_id)
    running = registry.get(record.task_id)
    assert running is not None
    assert running.status is TaskStatus.RUNNING

    payload = {"summary": {"ok": True}, "documents": []}
    registry.set_completed(record.task_id, payload)
    final = registry.get(record.task_id)
    assert final is not None
    assert final.status is TaskStatus.COMPLETED
    assert final.result == payload
    assert final.error is None


@pytest.mark.unit
def test_set_failed_records_error_and_clears_result():
    registry = TaskRegistry()
    record = registry.register()

    registry.set_running(record.task_id)
    registry.set_failed(record.task_id, "RuntimeError: boom")

    final = registry.get(record.task_id)
    assert final is not None
    assert final.status is TaskStatus.FAILED
    assert final.error == "RuntimeError: boom"
    assert final.result is None


@pytest.mark.unit
def test_unknown_id_transition_raises_key_error():
    registry = TaskRegistry()
    with pytest.raises(KeyError):
        registry.set_running("unknown")
    with pytest.raises(KeyError):
        registry.set_completed("unknown", {"x": 1})
    with pytest.raises(KeyError):
        registry.set_failed("unknown", "boom")


@pytest.mark.unit
def test_task_status_terminal_flag():
    assert TaskStatus.COMPLETED.is_terminal is True
    assert TaskStatus.FAILED.is_terminal is True
    assert TaskStatus.PENDING.is_terminal is False
    assert TaskStatus.RUNNING.is_terminal is False


@pytest.mark.unit
def test_concurrent_registrations_produce_unique_ids():
    """32 threads calling register() must produce 32 distinct task_ids.

    This is the thread-safety guarantee the handler relies on — if the
    internal dict assignment raced, two threads could collide on a
    uuid4().hex or the second write could clobber the first record.
    """
    registry = TaskRegistry()
    ids: list[str] = []
    ids_lock = threading.Lock()

    def work() -> None:
        record = registry.register()
        with ids_lock:
            ids.append(record.task_id)

    threads = [threading.Thread(target=work) for _ in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(ids) == 32
    assert len(set(ids)) == 32


@pytest.mark.unit
def test_to_dict_round_trips_serializable_fields():
    registry = TaskRegistry()
    record = registry.register()
    registry.set_running(record.task_id)
    registry.set_completed(record.task_id, {"ok": True})

    payload = registry.get(record.task_id).to_dict()
    assert payload["task_id"] == record.task_id
    assert payload["status"] == "completed"
    assert payload["result"] == {"ok": True}
    assert payload["error"] is None
    assert isinstance(payload["created_at"], float)
    assert isinstance(payload["updated_at"], float)
