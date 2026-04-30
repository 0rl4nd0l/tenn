from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

ALLOWED_REASON_CODES = {
    "wrong_fact",
    "wrong_number",
    "unsupported_claim",
    "weak_evidence",
    "bad_reasoning",
    "incomplete",
    "irrelevant",
    "unclear",
    "poor_structure",
    "other",
}

MAX_REVIEW_TEXT_CHARS = 40_000
MAX_REVIEW_QUERY_CHARS = 10_000
MAX_REVIEW_NOTE_CHARS = 2_000
MAX_REVIEW_LABEL_CHARS = 512
MAX_REVIEW_LIST_ITEMS = 100
MAX_REVIEW_JSON_CHARS = 80_000

_STORE_CACHE: dict[str, "ResponseFeedbackStore"] = {}
_STORE_CACHE_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else None, ensure_ascii=False, default=str)


def _bounded_text(
    value: Any,
    *,
    field: str,
    max_chars: int,
    strip: bool = False,
) -> str | None:
    if value is None:
        return None
    text = str(value)
    if strip:
        text = text.strip()
    if len(text) > max_chars:
        raise ValueError(f"{field} exceeds {max_chars} characters")
    return text


def _bounded_list(value: Any, *, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if len(value) > MAX_REVIEW_LIST_ITEMS:
        raise ValueError(f"{field} exceeds {MAX_REVIEW_LIST_ITEMS} items")
    return value


def _json_dump_bounded(value: Any, *, field: str) -> str:
    dumped = _json_dump(value)
    if len(dumped) > MAX_REVIEW_JSON_CHARS:
        raise ValueError(f"{field} exceeds {MAX_REVIEW_JSON_CHARS} serialized characters")
    return dumped


def _optional_bool(value: Any) -> int | None:
    if value is None:
        return None
    return 1 if bool(value) else 0


def default_response_feedback_path() -> Path:
    data_root = Path(getattr(settings, "data_root", "./data")).expanduser().resolve()
    return data_root / "cockpit" / "review_feedback.sqlite"


class ResponseFeedbackStore:
    """Dedicated local review store for non-authoritative response feedback."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or default_response_feedback_path()).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    session_id TEXT,
                    message_id TEXT,
                    parent_message_id TEXT,
                    user_label TEXT,
                    reason_code TEXT NOT NULL,
                    note TEXT,
                    query_text TEXT,
                    final_answer_text TEXT NOT NULL,
                    ticker TEXT,
                    company_name TEXT,
                    route_type TEXT,
                    model_label TEXT,
                    confidence_label TEXT,
                    trust_label TEXT,
                    sources_present INTEGER NOT NULL DEFAULT 0,
                    source_ids_json TEXT NOT NULL DEFAULT '[]',
                    source_summary_json TEXT NOT NULL DEFAULT '[]',
                    trace_artifact_id TEXT,
                    scratchpad_artifact_id TEXT,
                    evidence_bundle_id TEXT,
                    used_financial_truth INTEGER,
                    used_company_memory INTEGER,
                    used_market_memory INTEGER,
                    used_transcript_context INTEGER,
                    response_latency_ms REAL,
                    extraction_run_ids_json TEXT NOT NULL DEFAULT '[]',
                    document_ids_json TEXT NOT NULL DEFAULT '[]',
                    provenance_status_json TEXT,
                    app_version TEXT,
                    commit_hash TEXT,
                    verifier_result_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_feedback_created "
                "ON response_feedback(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_feedback_reason "
                "ON response_feedback(reason_code)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_feedback_session_message "
                "ON response_feedback(session_id, message_id)"
            )

    def insert(self, payload: dict[str, Any]) -> dict[str, Any]:
        reason_code = str(payload.get("reason_code") or "").strip()
        if reason_code not in ALLOWED_REASON_CODES:
            raise ValueError(f"Invalid reason_code: {reason_code}")

        final_answer_text = _bounded_text(
            payload.get("final_answer_text"),
            field="final_answer_text",
            max_chars=MAX_REVIEW_TEXT_CHARS,
            strip=True,
        ) or ""
        if not final_answer_text:
            raise ValueError("final_answer_text is required")

        feedback_id = str(payload.get("feedback_id") or "").strip() or f"fb_{uuid.uuid4().hex}"
        created_at = str(payload.get("created_at") or "").strip() or _now_iso()
        source_ids = _bounded_list(payload.get("source_ids") or [], field="source_ids")
        source_summary = _bounded_list(
            payload.get("source_summary") or [],
            field="source_summary",
        )
        extraction_run_ids = _bounded_list(
            payload.get("extraction_run_ids") or [],
            field="extraction_run_ids",
        )
        document_ids = _bounded_list(payload.get("document_ids") or [], field="document_ids")

        row = {
            "feedback_id": feedback_id,
            "created_at": created_at,
            "session_id": _bounded_text(
                payload.get("session_id"),
                field="session_id",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "message_id": _bounded_text(
                payload.get("message_id"),
                field="message_id",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "parent_message_id": _bounded_text(
                payload.get("parent_message_id"),
                field="parent_message_id",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "user_label": _bounded_text(
                payload.get("user_label") or "issue_report",
                field="user_label",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "reason_code": reason_code,
            "note": _bounded_text(
                payload.get("note"),
                field="note",
                max_chars=MAX_REVIEW_NOTE_CHARS,
            ),
            "query_text": _bounded_text(
                payload.get("query_text"),
                field="query_text",
                max_chars=MAX_REVIEW_QUERY_CHARS,
            ),
            "final_answer_text": final_answer_text,
            "ticker": str(payload.get("ticker") or "").strip().upper() or None,
            "company_name": _bounded_text(
                payload.get("company_name"),
                field="company_name",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "route_type": _bounded_text(
                payload.get("route_type"),
                field="route_type",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "model_label": _bounded_text(
                payload.get("model_label"),
                field="model_label",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "confidence_label": _bounded_text(
                payload.get("confidence_label"),
                field="confidence_label",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "trust_label": _bounded_text(
                payload.get("trust_label"),
                field="trust_label",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "sources_present": 1 if bool(payload.get("sources_present")) else 0,
            "source_ids_json": _json_dump_bounded(source_ids, field="source_ids"),
            "source_summary_json": _json_dump_bounded(
                source_summary,
                field="source_summary",
            ),
            "trace_artifact_id": _bounded_text(
                payload.get("trace_artifact_id"),
                field="trace_artifact_id",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "scratchpad_artifact_id": _bounded_text(
                payload.get("scratchpad_artifact_id"),
                field="scratchpad_artifact_id",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "evidence_bundle_id": _bounded_text(
                payload.get("evidence_bundle_id"),
                field="evidence_bundle_id",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "used_financial_truth": _optional_bool(payload.get("used_financial_truth")),
            "used_company_memory": _optional_bool(payload.get("used_company_memory")),
            "used_market_memory": _optional_bool(payload.get("used_market_memory")),
            "used_transcript_context": _optional_bool(payload.get("used_transcript_context")),
            "response_latency_ms": payload.get("response_latency_ms"),
            "extraction_run_ids_json": _json_dump_bounded(
                extraction_run_ids,
                field="extraction_run_ids",
            ),
            "document_ids_json": _json_dump_bounded(document_ids, field="document_ids"),
            "provenance_status_json": _json_dump_bounded(
                payload.get("provenance_status"),
                field="provenance_status",
            )
            if payload.get("provenance_status") is not None
            else None,
            "app_version": _bounded_text(
                payload.get("app_version"),
                field="app_version",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "commit_hash": _bounded_text(
                payload.get("commit_hash"),
                field="commit_hash",
                max_chars=MAX_REVIEW_LABEL_CHARS,
            ),
            "verifier_result_json": _json_dump_bounded(
                payload.get("verifier_result"),
                field="verifier_result",
            )
            if payload.get("verifier_result") is not None
            else None,
        }

        columns = list(row)
        placeholders = ", ".join(["?"] * len(columns))
        sql = (
            f"INSERT INTO response_feedback ({', '.join(columns)}) "
            f"VALUES ({placeholders})"
        )
        with self._lock:
            with self._connect() as conn:
                conn.execute(sql, [row[column] for column in columns])

        return {
            "feedback_id": feedback_id,
            "created_at": created_at,
            "storage_path": str(self.db_path),
        }

    def get(self, feedback_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM response_feedback WHERE feedback_id = ?",
                (feedback_id,),
            ).fetchone()
        return dict(row) if row is not None else None


def get_response_feedback_store(db_path: str | Path | None = None) -> ResponseFeedbackStore:
    path = Path(db_path or default_response_feedback_path()).expanduser().resolve()
    cache_key = str(path)
    with _STORE_CACHE_LOCK:
        store = _STORE_CACHE.get(cache_key)
        if store is None:
            store = ResponseFeedbackStore(path)
            _STORE_CACHE[cache_key] = store
        return store
