"""Operational job-status SQLite store.

Provides structured persistence for job runs, events, and artifacts.
Follows the same SQLite/WAL/threading pattern as cockpit StateStore.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


class OpsStore:
    """SQLite-backed operational store for job_runs, job_events, job_artifacts."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS job_runs (
                job_id          TEXT PRIMARY KEY,
                job_type        TEXT NOT NULL,
                job_family      TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                phase           TEXT,
                title           TEXT NOT NULL,
                summary         TEXT,
                trigger_source  TEXT,
                entity_scope    TEXT,
                ticker          TEXT,
                total_items     INTEGER DEFAULT 0,
                succeeded_items INTEGER DEFAULT 0,
                failed_items    INTEGER DEFAULT 0,
                skipped_items   INTEGER DEFAULT 0,
                warning_count   INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                current_item_label TEXT,
                queued_at       TEXT NOT NULL,
                started_at      TEXT,
                updated_at      TEXT NOT NULL,
                completed_at    TEXT,
                elapsed_ms      INTEGER DEFAULT 0,
                metadata_json   TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_job_runs_status ON job_runs(status);
            CREATE INDEX IF NOT EXISTS idx_job_runs_type ON job_runs(job_type);
            CREATE INDEX IF NOT EXISTS idx_job_runs_ticker ON job_runs(ticker);
            CREATE INDEX IF NOT EXISTS idx_job_runs_queued ON job_runs(queued_at);

            CREATE TABLE IF NOT EXISTS job_events (
                event_id         TEXT PRIMARY KEY,
                job_id           TEXT NOT NULL REFERENCES job_runs(job_id),
                event_type       TEXT NOT NULL,
                phase            TEXT,
                message          TEXT NOT NULL,
                progress_current INTEGER,
                progress_total   INTEGER,
                progress_pct     REAL,
                timestamp        TEXT NOT NULL,
                payload_json     TEXT DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);
            CREATE INDEX IF NOT EXISTS idx_job_events_ts ON job_events(timestamp);

            CREATE TABLE IF NOT EXISTS job_artifacts (
                artifact_id    TEXT PRIMARY KEY,
                job_id         TEXT NOT NULL REFERENCES job_runs(job_id),
                artifact_type  TEXT NOT NULL,
                artifact_path  TEXT,
                artifact_label TEXT NOT NULL,
                metadata_json  TEXT DEFAULT '{}',
                created_at     TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_job_artifacts_job ON job_artifacts(job_id);
            """
        )
        self.conn.commit()

    # ── job_runs CRUD ──────────────────────────────────────────────────────

    def create_job_run(
        self,
        *,
        job_id: str,
        job_type: str,
        job_family: str,
        title: str,
        trigger_source: str | None = None,
        entity_scope: str | None = None,
        ticker: str | None = None,
        total_items: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now_iso()
        row = {
            "job_id": job_id,
            "job_type": job_type,
            "job_family": job_family,
            "status": "pending",
            "phase": None,
            "title": title,
            "summary": None,
            "trigger_source": trigger_source,
            "entity_scope": entity_scope,
            "ticker": ticker.upper() if ticker else None,
            "total_items": total_items,
            "succeeded_items": 0,
            "failed_items": 0,
            "skipped_items": 0,
            "warning_count": 0,
            "error_count": 0,
            "current_item_label": None,
            "queued_at": now,
            "started_at": None,
            "updated_at": now,
            "completed_at": None,
            "elapsed_ms": 0,
            "metadata_json": json.dumps(metadata or {}),
        }
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO job_runs (
                    job_id, job_type, job_family, status, phase, title, summary,
                    trigger_source, entity_scope, ticker,
                    total_items, succeeded_items, failed_items, skipped_items,
                    warning_count, error_count, current_item_label,
                    queued_at, started_at, updated_at, completed_at,
                    elapsed_ms, metadata_json
                ) VALUES (
                    :job_id, :job_type, :job_family, :status, :phase, :title, :summary,
                    :trigger_source, :entity_scope, :ticker,
                    :total_items, :succeeded_items, :failed_items, :skipped_items,
                    :warning_count, :error_count, :current_item_label,
                    :queued_at, :started_at, :updated_at, :completed_at,
                    :elapsed_ms, :metadata_json
                )
                """,
                row,
            )
            self.conn.commit()
        return {**row, "metadata": metadata or {}}

    def update_job_run(self, job_id: str, **fields: Any) -> bool:
        if not fields:
            return False
        fields["updated_at"] = _now_iso()
        if "metadata" in fields:
            fields["metadata_json"] = json.dumps(fields.pop("metadata"))
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        fields["job_id"] = job_id
        with self._lock:
            cur = self.conn.execute(
                f"UPDATE job_runs SET {set_clause} WHERE job_id = :job_id",  # noqa: S608
                fields,
            )
            self.conn.commit()
            return cur.rowcount > 0

    def get_job_run(self, job_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM job_runs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return self._parse_job_row(row)

    def list_job_runs(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        ticker: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            statuses = [s.strip() for s in status.split(",")]
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            params.extend(statuses)
        if job_type:
            clauses.append("job_type = ?")
            params.append(job_type)
        if ticker:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        count_row = self.conn.execute(
            f"SELECT COUNT(*) FROM job_runs {where}", params  # noqa: S608
        ).fetchone()
        total = int(count_row[0]) if count_row else 0
        rows = self.conn.execute(
            f"SELECT * FROM job_runs {where} ORDER BY queued_at DESC LIMIT ? OFFSET ?",  # noqa: S608
            [*params, limit, offset],
        ).fetchall()
        return [self._parse_job_row(r) for r in rows], total

    # ── job_events CRUD ────────────────────────────────────────────────────

    def add_job_event(
        self,
        *,
        job_id: str,
        event_type: str,
        message: str,
        phase: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        progress_pct: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = _new_id()
        now = _now_iso()
        row = {
            "event_id": event_id,
            "job_id": job_id,
            "event_type": event_type,
            "phase": phase,
            "message": message,
            "progress_current": progress_current,
            "progress_total": progress_total,
            "progress_pct": progress_pct,
            "timestamp": now,
            "payload_json": json.dumps(payload or {}),
        }
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO job_events (
                    event_id, job_id, event_type, phase, message,
                    progress_current, progress_total, progress_pct,
                    timestamp, payload_json
                ) VALUES (
                    :event_id, :job_id, :event_type, :phase, :message,
                    :progress_current, :progress_total, :progress_pct,
                    :timestamp, :payload_json
                )
                """,
                row,
            )
            self.conn.commit()
        return {**row, "payload": payload or {}}

    def list_job_events(
        self, job_id: str, *, limit: int = 200
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY timestamp ASC LIMIT ?",
            (job_id, limit),
        ).fetchall()
        return [self._parse_event_row(r) for r in rows]

    # ── job_artifacts CRUD ─────────────────────────────────────────────────

    def add_job_artifact(
        self,
        *,
        job_id: str,
        artifact_type: str,
        artifact_label: str,
        artifact_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        artifact_id = _new_id()
        now = _now_iso()
        row = {
            "artifact_id": artifact_id,
            "job_id": job_id,
            "artifact_type": artifact_type,
            "artifact_path": artifact_path,
            "artifact_label": artifact_label,
            "metadata_json": json.dumps(metadata or {}),
            "created_at": now,
        }
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO job_artifacts (
                    artifact_id, job_id, artifact_type, artifact_path,
                    artifact_label, metadata_json, created_at
                ) VALUES (
                    :artifact_id, :job_id, :artifact_type, :artifact_path,
                    :artifact_label, :metadata_json, :created_at
                )
                """,
                row,
            )
            self.conn.commit()
        return {**row, "metadata": metadata or {}}

    def list_job_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM job_artifacts WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
        return [self._parse_artifact_row(r) for r in rows]

    # ── Cleanup ────────────────────────────────────────────────────────────

    def cleanup(self, *, max_age_days: int = 90) -> int:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=max_age_days)
        ).isoformat()
        with self._lock:
            old_jobs = self.conn.execute(
                "SELECT job_id FROM job_runs WHERE queued_at < ?", (cutoff,)
            ).fetchall()
            job_ids = [r[0] for r in old_jobs]
            if not job_ids:
                return 0
            placeholders = ",".join("?" for _ in job_ids)
            self.conn.execute(
                f"DELETE FROM job_artifacts WHERE job_id IN ({placeholders})",  # noqa: S608
                job_ids,
            )
            self.conn.execute(
                f"DELETE FROM job_events WHERE job_id IN ({placeholders})",  # noqa: S608
                job_ids,
            )
            cur = self.conn.execute(
                f"DELETE FROM job_runs WHERE job_id IN ({placeholders})",  # noqa: S608
                job_ids,
            )
            self.conn.commit()
            removed = cur.rowcount
            if removed:
                logger.info(
                    "ops_store cleanup: removed %d jobs older than %d days",
                    removed,
                    max_age_days,
                )
            return removed

    # ── Row parsers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_job_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json", "{}"))
        return item

    @staticmethod
    def _parse_event_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json", "{}"))
        return item

    @staticmethod
    def _parse_artifact_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json", "{}"))
        return item
