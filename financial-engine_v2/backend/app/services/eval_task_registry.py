"""Thread-safe in-memory task registry for long-running eval jobs.

Scope
-----
The extraction-eval corpus route (``POST /api/extraction-eval/real-gold``) can
take many minutes under ``limit=0``. Before this registry the handler returned
only when the full run completed, which blocked the HTTP caller and made the
CLI wrapper's 1800s timeout the de-facto hang detector.

This module stores one record per scheduled run so the handler can return a
``task_id`` immediately and the caller can poll for status. The registry is
process-local; on restart all state is lost. Persistence is intentionally out
of scope for this slice — the contract here is intentionally thin enough that
a later DB-backed implementation can replace it without changing callers.

Threading
---------
All mutating operations take a single module-level ``threading.Lock`` guarding
the underlying ``dict``. The FastAPI handler runs on the anyio threadpool and
calls :meth:`register`, then spawns a daemon thread that calls
:meth:`set_running` and eventually :meth:`set_completed` or
:meth:`set_failed`. Reads via :meth:`get` are also lock-guarded so a polling
GET never observes a torn record.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED)


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    status: TaskStatus
    created_at: float
    updated_at: float
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    progress: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "progress": list(self.progress),
        }


class TaskRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[str, TaskRecord] = {}

    def register(self) -> TaskRecord:
        task_id = uuid.uuid4().hex
        now = time.time()
        record = TaskRecord(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[task_id] = record
        return record

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def set_running(self, task_id: str) -> None:
        self._update(task_id, status=TaskStatus.RUNNING)

    def set_completed(self, task_id: str, result: dict[str, Any]) -> None:
        self._update(task_id, status=TaskStatus.COMPLETED, result=result)

    def set_failed(self, task_id: str, error: str) -> None:
        self._update(task_id, status=TaskStatus.FAILED, error=error)

    def record_progress(self, task_id: str, event: dict[str, Any]) -> None:
        now = time.time()
        payload = dict(event)
        payload.setdefault("timestamp", now)
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                raise KeyError(f"unknown task_id: {task_id}")
            self._tasks[task_id] = replace(
                current,
                updated_at=now,
                progress=(*current.progress, payload)[-200:],
            )

    def _update(
        self,
        task_id: str,
        *,
        status: TaskStatus,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                raise KeyError(f"unknown task_id: {task_id}")
            self._tasks[task_id] = replace(
                current,
                status=status,
                updated_at=time.time(),
                result=result,
                error=error,
            )


_registry: Optional[TaskRegistry] = None
_registry_lock = threading.Lock()


def get_eval_task_registry() -> TaskRegistry:
    """Return the process-wide singleton registry, constructing it if needed."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = TaskRegistry()
        return _registry


__all__ = [
    "TaskRecord",
    "TaskRegistry",
    "TaskStatus",
    "get_eval_task_registry",
]
