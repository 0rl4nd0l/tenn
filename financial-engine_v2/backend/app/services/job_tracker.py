"""Unified job lifecycle tracker with SSE event bus.

Wraps OpsStore with higher-level methods for job lifecycle management
and broadcasts events to SSE subscribers.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Generator

from app.services.ops_store import OpsStore

logger = logging.getLogger(__name__)

# Valid event types
EVENT_TYPES = frozenset(
    {
        "job.created",
        "job.started",
        "job.phase_changed",
        "job.progress",
        "job.item_started",
        "job.item_succeeded",
        "job.item_failed",
        "job.warning",
        "job.metric_snapshot",
        "job.completed",
        "job.failed",
        "job.cancelled",
    }
)

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class JobHandle:
    """Lightweight reference returned to callers after job creation."""

    job_id: str
    job_type: str
    title: str


class JobTracker:
    """Manages job lifecycle and broadcasts events to SSE subscribers."""

    def __init__(self, store: OpsStore) -> None:
        self._store = store
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._sub_lock = threading.Lock()

    @property
    def store(self) -> OpsStore:
        return self._store

    # ── Job lifecycle ──────────────────────────────────────────────────────

    def create_job(
        self,
        *,
        job_type: str,
        job_family: str,
        title: str,
        trigger_source: str | None = None,
        entity_scope: str | None = None,
        ticker: str | None = None,
        total_items: int = 0,
        metadata: dict[str, Any] | None = None,
        job_id: str | None = None,
    ) -> JobHandle:
        jid = job_id or uuid.uuid4().hex[:16]
        self._store.create_job_run(
            job_id=jid,
            job_type=job_type,
            job_family=job_family,
            title=title,
            trigger_source=trigger_source,
            entity_scope=entity_scope,
            ticker=ticker,
            total_items=total_items,
            metadata=metadata,
        )
        self._emit_event(jid, "job.created", f"Job created: {title}")
        return JobHandle(job_id=jid, job_type=job_type, title=title)

    def start_job(self, job_id: str) -> None:
        now = _now_iso()
        self._store.update_job_run(job_id, status="running", started_at=now)
        self._emit_event(job_id, "job.started", "Job started")

    def change_phase(self, job_id: str, phase: str, message: str = "") -> None:
        self._store.update_job_run(job_id, phase=phase)
        self._emit_event(
            job_id,
            "job.phase_changed",
            message or f"Phase: {phase}",
            phase=phase,
        )

    def record_progress(
        self,
        job_id: str,
        *,
        current: int,
        total: int,
        message: str = "",
        current_item_label: str | None = None,
    ) -> None:
        pct = round((current / total) * 100, 1) if total > 0 else 0.0
        updates: dict[str, Any] = {
            "succeeded_items": current,
            "total_items": total,
        }
        if current_item_label is not None:
            updates["current_item_label"] = current_item_label
        self._store.update_job_run(job_id, **updates)
        self._emit_event(
            job_id,
            "job.progress",
            message or f"Progress: {current}/{total}",
            progress_current=current,
            progress_total=total,
            progress_pct=pct,
        )

    def record_item_started(
        self, job_id: str, label: str, index: int | None = None
    ) -> None:
        self._store.update_job_run(job_id, current_item_label=label)
        self._emit_event(
            job_id,
            "job.item_started",
            f"Started: {label}",
            payload={"label": label, "index": index},
        )

    def record_item_succeeded(self, job_id: str, label: str) -> None:
        run = self._store.get_job_run(job_id)
        if run:
            self._store.update_job_run(
                job_id, succeeded_items=run["succeeded_items"] + 1
            )
        self._emit_event(
            job_id,
            "job.item_succeeded",
            f"Succeeded: {label}",
            payload={"label": label},
        )

    def record_item_failed(
        self, job_id: str, label: str, error: str = ""
    ) -> None:
        run = self._store.get_job_run(job_id)
        if run:
            self._store.update_job_run(
                job_id, failed_items=run["failed_items"] + 1
            )
        self._emit_event(
            job_id,
            "job.item_failed",
            f"Failed: {label}",
            payload={"label": label, "error": error},
        )

    def record_warning(self, job_id: str, message: str) -> None:
        run = self._store.get_job_run(job_id)
        if run:
            self._store.update_job_run(
                job_id, warning_count=run["warning_count"] + 1
            )
        self._emit_event(job_id, "job.warning", message)

    def complete_job(
        self, job_id: str, summary: str | None = None
    ) -> None:
        now = _now_iso()
        run = self._store.get_job_run(job_id)
        elapsed = 0
        if run and run.get("started_at"):
            started = datetime.fromisoformat(run["started_at"])
            elapsed = max(
                0,
                int(
                    (datetime.now(timezone.utc) - started).total_seconds()
                    * 1000
                ),
            )
        self._store.update_job_run(
            job_id,
            status="succeeded",
            completed_at=now,
            elapsed_ms=elapsed,
            summary=summary,
        )
        self._emit_event(
            job_id, "job.completed", summary or "Job completed successfully"
        )

    def fail_job(self, job_id: str, error: str) -> None:
        now = _now_iso()
        run = self._store.get_job_run(job_id)
        elapsed = 0
        if run and run.get("started_at"):
            started = datetime.fromisoformat(run["started_at"])
            elapsed = max(
                0,
                int(
                    (datetime.now(timezone.utc) - started).total_seconds()
                    * 1000
                ),
            )
        self._store.update_job_run(
            job_id,
            status="failed",
            completed_at=now,
            elapsed_ms=elapsed,
            summary=error,
        )
        self._emit_event(job_id, "job.failed", error)

    def cancel_job(self, job_id: str, reason: str = "") -> None:
        now = _now_iso()
        self._store.update_job_run(
            job_id, status="cancelled", completed_at=now
        )
        self._emit_event(
            job_id, "job.cancelled", reason or "Job cancelled"
        )

    def add_artifact(
        self,
        job_id: str,
        *,
        artifact_type: str,
        artifact_label: str,
        artifact_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._store.add_job_artifact(
            job_id=job_id,
            artifact_type=artifact_type,
            artifact_label=artifact_label,
            artifact_path=artifact_path,
            metadata=metadata,
        )

    # ── Context manager for tracked tasks ──────────────────────────────────

    @contextmanager
    def tracked_job(
        self,
        *,
        job_type: str,
        job_family: str,
        title: str,
        trigger_source: str | None = None,
        entity_scope: str | None = None,
        ticker: str | None = None,
        total_items: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Generator[JobHandle, None, None]:
        handle = self.create_job(
            job_type=job_type,
            job_family=job_family,
            title=title,
            trigger_source=trigger_source,
            entity_scope=entity_scope,
            ticker=ticker,
            total_items=total_items,
            metadata=metadata,
        )
        self.start_job(handle.job_id)
        try:
            yield handle
            self.complete_job(handle.job_id)
        except Exception as exc:
            self.fail_job(handle.job_id, str(exc))
            raise

    # ── SSE event bus ──────────────────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._sub_lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    async def iter_events(
        self, *, job_id: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        q = self.subscribe()
        try:
            while True:
                event = await q.get()
                if job_id and event.get("job_id") != job_id:
                    continue
                yield event
        finally:
            self.unsubscribe(q)

    # ── Internal event emission ────────────────────────────────────────────

    def _emit_event(
        self,
        job_id: str,
        event_type: str,
        message: str,
        *,
        phase: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        progress_pct: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event_record = self._store.add_job_event(
            job_id=job_id,
            event_type=event_type,
            message=message,
            phase=phase,
            progress_current=progress_current,
            progress_total=progress_total,
            progress_pct=progress_pct,
            payload=payload,
        )
        broadcast = {
            "event_type": event_type,
            "job_id": job_id,
            "timestamp": event_record["timestamp"],
            "data": {
                "message": message,
                "phase": phase,
                "progress_current": progress_current,
                "progress_total": progress_total,
                "progress_pct": progress_pct,
                **(payload or {}),
            },
        }
        self._broadcast(broadcast)

    def _broadcast(self, event: dict[str, Any]) -> None:
        with self._sub_lock:
            dead: list[asyncio.Queue[dict[str, Any]]] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop oldest event to make room
                    try:
                        q.get_nowait()
                        q.put_nowait(event)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        dead.append(q)
            for q in dead:
                try:
                    self._subscribers.remove(q)
                except ValueError:
                    pass


# ── Module-level singleton ─────────────────────────────────────────────────

_tracker: JobTracker | None = None
_tracker_lock = threading.Lock()


def init_tracker(store: OpsStore) -> JobTracker:
    """Initialize the module-level JobTracker singleton."""
    global _tracker  # noqa: PLW0603
    with _tracker_lock:
        _tracker = JobTracker(store)
    return _tracker


def get_tracker() -> JobTracker | None:
    """Return the global JobTracker, or None if not initialized."""
    return _tracker
