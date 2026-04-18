from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from app.services.source_registry import RESEARCH_MEMORY_ROOT

DEFAULT_COMPANY_MEMORY_PATH = RESEARCH_MEMORY_ROOT / "company_memory.sqlite"
_MANUAL_SOURCE = "backend_manual"
_SQLITE_TIMEOUT_SECONDS = 5.0
_SQLITE_BUSY_TIMEOUT_MS = int(_SQLITE_TIMEOUT_SECONDS * 1000)
_SQLITE_BUSY_RETRIES = 2
_SQLITE_BUSY_RETRY_SLEEP_SECONDS = 0.05
_WriteResultT = TypeVar("_WriteResultT")

_FORBIDDEN_SIGNAL_TYPES = {
    "revenue",
    "ebit",
    "ebitda",
    "npat",
    "profit",
    "cash_flow",
    "cashflow",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "net_debt",
    "shares_outstanding",
    "capex",
    "dividend",
    "financial_fact",
    "financial_metric",
}
_VALID_STATUSES = {"active", "expired"}
_TYPE_WEIGHT = {
    "management_guidance": 0.08,
    "strategic_initiative": 0.08,
    "catalyst": 0.07,
    "risk": 0.07,
    "observed_fact": 0.05,
    "operating_context": 0.04,
    "interpretation": -0.03,
}
_INTENT_TYPE_PRIORITY = {
    "strategy": (
        "strategic_initiative",
        "management_guidance",
        "observed_fact",
        "operating_context",
        "catalyst",
        "interpretation",
    ),
    "risk_catalyst": (
        "risk",
        "catalyst",
        "operating_context",
        "management_guidance",
        "observed_fact",
        "interpretation",
    ),
    "financial_interpretation": (
        "observed_fact",
        "management_guidance",
        "interpretation",
        "operating_context",
        "risk",
        "catalyst",
        "strategic_initiative",
    ),
    "mixed": (
        "observed_fact",
        "management_guidance",
        "risk",
        "catalyst",
        "strategic_initiative",
        "operating_context",
        "interpretation",
    ),
}
_REPLACEABLE_TYPES = {
    "management_guidance",
    "strategic_initiative",
    "observed_fact",
    "operating_context",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_statement(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _manual_source_id(prefix: str) -> str:
    return f"{prefix}:{time.time_ns()}"


def _is_transient_sqlite_busy(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "locked" in message or "busy" in message


class CompanyMemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_COMPANY_MEMORY_PATH).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=_SQLITE_TIMEOUT_SECONDS)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _run_write_transaction(
        self, operation: Callable[[sqlite3.Connection], _WriteResultT]
    ) -> _WriteResultT:
        for attempt in range(_SQLITE_BUSY_RETRIES + 1):
            try:
                with self._connect() as conn:
                    return operation(conn)
            except sqlite3.OperationalError as exc:
                if (
                    not _is_transient_sqlite_busy(exc)
                    or attempt >= _SQLITE_BUSY_RETRIES
                ):
                    raise
                time.sleep(_SQLITE_BUSY_RETRY_SLEEP_SECONDS)
        raise RuntimeError("unreachable sqlite retry state")

    def _ensure_schema(self) -> None:
        def _create(conn: sqlite3.Connection) -> None:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS company_memory (
                    company_id TEXT PRIMARY KEY,
                    active_entry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memory_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    normalized_statement TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    materiality REAL NOT NULL,
                    persistence TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    reinforcement_count INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    closed_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_memory_entries_company_status
                    ON memory_entries(company_id, status);
                CREATE INDEX IF NOT EXISTS idx_memory_entries_company_statement
                    ON memory_entries(company_id, normalized_statement);

                CREATE TABLE IF NOT EXISTS change_log (
                    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    entry_id INTEGER,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_change_log_company
                    ON change_log(company_id, created_at);
                """
            )
            return None

        self._run_write_transaction(_create)

    def update_company_memory(
        self, company_id: str, signal: dict[str, Any]
    ) -> dict[str, Any]:
        normalized_company = str(company_id or "").strip().upper()
        if not normalized_company:
            raise ValueError("company_id is required")
        payload = self._normalize_signal(normalized_company, signal)
        now = _utc_now()

        def _update(conn: sqlite3.Connection) -> dict[str, Any]:
            self._ensure_company_row(conn, normalized_company, now)

            if payload["status"] == "expired":
                expired_entry = self._expire_matching_entry(
                    conn, normalized_company, payload, now
                )
                self._sync_company_summary(conn, normalized_company, now)
                return {"rule": "expire", "entry": expired_entry}

            existing = self._find_matching_active_entry(
                conn, normalized_company, payload
            )
            if existing is not None:
                if existing["source_id"] == payload["source_id"]:
                    self._insert_change_log(
                        conn,
                        normalized_company,
                        existing["entry_id"],
                        "dedupe",
                        {"source_id": payload["source_id"]},
                        now,
                    )
                    return {"rule": "dedupe", "entry": existing}

                reinforced = self._reinforce_entry(conn, existing, payload, now)
                self._sync_company_summary(conn, normalized_company, now)
                return {"rule": "reinforce", "entry": reinforced}

            superseded = self._transition_targets(
                conn,
                normalized_company,
                payload.get("supersedes") or [],
                new_status="superseded",
                event_type="supersede",
                now=now,
            )
            contradicted = self._transition_targets(
                conn,
                normalized_company,
                payload.get("contradicts") or [],
                new_status="contradicted",
                event_type="contradict",
                now=now,
            )
            payload["metadata"] = {
                **payload["metadata"],
                "superseded_entry_ids": superseded,
                "contradicted_entry_ids": contradicted,
            }

            entry_id = conn.execute(
                """
                INSERT INTO memory_entries (
                    company_id, type, statement, normalized_statement, entity_id,
                    confidence, materiality, persistence, status, source, source_id,
                    reinforcement_count, first_seen_at, last_seen_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_company,
                    payload["type"],
                    payload["statement"],
                    payload["normalized_statement"],
                    payload["entity_id"],
                    payload["confidence"],
                    payload["materiality"],
                    payload["persistence"],
                    "active",
                    payload["source"],
                    payload["source_id"],
                    0,
                    now,
                    now,
                    json.dumps(payload["metadata"], sort_keys=True),
                ),
            ).lastrowid
            event_type = "insert"
            if superseded:
                event_type = "supersede"
            elif contradicted:
                event_type = "contradict"
            self._insert_change_log(
                conn,
                normalized_company,
                entry_id,
                event_type,
                {
                    "source_id": payload["source_id"],
                    "superseded_entry_ids": superseded,
                    "contradicted_entry_ids": contradicted,
                },
                now,
            )
            self._sync_company_summary(conn, normalized_company, now)
            entry = self._get_entry_by_id(conn, int(entry_id))
            return {"rule": event_type, "entry": entry}

        return self._run_write_transaction(_update)

    def list_entries(
        self, company_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        normalized_company = str(company_id or "").strip().upper()
        query = "SELECT * FROM memory_entries WHERE company_id = ?"
        params: list[Any] = [normalized_company]
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY entry_id ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_change_log(self, company_id: str) -> list[dict[str, Any]]:
        normalized_company = str(company_id or "").strip().upper()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM change_log WHERE company_id = ? ORDER BY change_id ASC",
                (normalized_company,),
            ).fetchall()
        return [self._change_row_to_dict(row) for row in rows]

    def add_manual_entry(
        self,
        company_id: str,
        *,
        signal_type: str,
        statement: str,
        confidence: float = 0.0,
        materiality: float = 0.0,
        persistence: str = "medium",
        supersedes: list[Any] | None = None,
        contradicts: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload_metadata = dict(metadata or {})
        payload_metadata.setdefault("manual", True)
        return self.update_company_memory(
            company_id,
            {
                "type": signal_type,
                "statement": statement,
                "confidence": confidence,
                "materiality": materiality,
                "persistence": persistence,
                "status": "active",
                "source": _MANUAL_SOURCE,
                "source_id": _manual_source_id("company-manual"),
                "supersedes": list(supersedes or []),
                "contradicts": list(contradicts or []),
                "metadata": payload_metadata,
            },
        )

    def expire_entry(
        self,
        company_id: str,
        entry_id: int,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        normalized_company = str(company_id or "").strip().upper()
        if not normalized_company:
            raise ValueError("company_id is required")
        if int(entry_id) <= 0:
            raise ValueError("entry_id must be positive")
        now = _utc_now()
        source_id = _manual_source_id("company-expire")

        def _expire(conn: sqlite3.Connection) -> dict[str, Any]:
            row = conn.execute(
                """
                SELECT * FROM memory_entries
                WHERE company_id = ? AND entry_id = ?
                LIMIT 1
                """,
                (normalized_company, int(entry_id)),
            ).fetchone()
            if row is None:
                raise ValueError(f"company memory entry not found: {entry_id}")
            existing = self._row_to_dict(row)
            if str(existing.get("status") or "").strip().lower() != "active":
                raise ValueError(
                    f"company memory entry is not active: {int(existing['entry_id'])}"
                )

            conn.execute(
                """
                UPDATE memory_entries
                SET status = 'expired', closed_at = ?, last_seen_at = ?
                WHERE entry_id = ?
                """,
                (now, now, int(entry_id)),
            )
            details = {"source": _MANUAL_SOURCE, "source_id": source_id}
            if reason:
                details["reason"] = str(reason).strip()
            self._insert_change_log(
                conn,
                normalized_company,
                int(entry_id),
                "expire",
                details,
                now,
            )
            self._sync_company_summary(conn, normalized_company, now)
            return {"rule": "expire", "entry": self._get_entry_by_id(conn, int(entry_id))}

        return self._run_write_transaction(_expire)

    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]:
        company_id = str(entities.get("primary_ticker") or "").strip().upper()
        if not company_id:
            return {"source": "company_memory", "status": "no_entity", "items": []}
        items = self._rank_active_entries(
            self.list_entries(company_id, status="active"),
            query=query,
            intent=intent,
        )
        return {
            "source": "company_memory",
            "status": "ok",
            "items": items,
            "query": query,
            "intent": intent,
        }

    def _normalize_signal(
        self, company_id: str, signal: dict[str, Any]
    ) -> dict[str, Any]:
        payload = dict(signal or {})
        signal_type = str(payload.get("type") or "").strip().lower()
        if not signal_type:
            raise ValueError("signal type is required")
        if signal_type in _FORBIDDEN_SIGNAL_TYPES:
            raise ValueError(
                "financial metric signals must not be written to company memory"
            )

        statement = str(payload.get("statement") or "").strip()
        if not statement:
            raise ValueError("signal statement is required")

        status = str(payload.get("status") or "active").strip().lower()
        if status not in _VALID_STATUSES:
            raise ValueError(f"unsupported company memory status: {status}")

        confidence = float(
            payload.get("confidence")
            if payload.get("confidence") not in (None, "")
            else 0.0
        )
        materiality = float(
            payload.get("materiality")
            if payload.get("materiality") not in (None, "")
            else 0.0
        )
        source = str(payload.get("source") or "unknown").strip()
        source_id = str(payload.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("signal source_id is required")

        return {
            "type": signal_type,
            "statement": statement,
            "normalized_statement": _normalize_statement(statement),
            "entity_id": str(payload.get("entity_id") or company_id).strip().upper(),
            "confidence": confidence,
            "materiality": materiality,
            "persistence": str(payload.get("persistence") or "medium").strip().lower(),
            "status": status,
            "source": source,
            "source_id": source_id,
            "supersedes": list(payload.get("supersedes") or []),
            "contradicts": list(payload.get("contradicts") or []),
            "metadata": dict(payload.get("metadata") or {}),
        }

    def _ensure_company_row(
        self, conn: sqlite3.Connection, company_id: str, now: str
    ) -> None:
        conn.execute(
            """
            INSERT INTO company_memory (company_id, active_entry_count, created_at, updated_at)
            VALUES (?, 0, ?, ?)
            ON CONFLICT(company_id) DO NOTHING
            """,
            (company_id, now, now),
        )

    def _find_matching_active_entry(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        row = conn.execute(
            """
            SELECT * FROM memory_entries
            WHERE company_id = ?
              AND type = ?
              AND normalized_statement = ?
              AND status = 'active'
            ORDER BY entry_id ASC
            LIMIT 1
            """,
            (company_id, payload["type"], payload["normalized_statement"]),
        ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def _reinforce_entry(
        self,
        conn: sqlite3.Connection,
        existing: dict[str, Any],
        payload: dict[str, Any],
        now: str,
    ) -> dict[str, Any]:
        metadata = dict(existing.get("metadata") or {})
        for key in ("themes", "time_refs"):
            combined = list(metadata.get(key) or [])
            for value in payload["metadata"].get(key) or []:
                if value not in combined:
                    combined.append(value)
            if combined:
                metadata[key] = combined
        for key in ("theme_key", "signal_kind", "replaceable"):
            if key in payload["metadata"] and not metadata.get(key):
                metadata[key] = payload["metadata"][key]
        source_ids = list(metadata.get("source_ids") or [])
        if payload["source_id"] not in source_ids:
            source_ids.append(payload["source_id"])
        metadata["source_ids"] = source_ids
        conn.execute(
            """
            UPDATE memory_entries
            SET confidence = ?,
                materiality = ?,
                reinforcement_count = reinforcement_count + 1,
                last_seen_at = ?,
                metadata_json = ?
            WHERE entry_id = ?
            """,
            (
                max(float(existing["confidence"]), float(payload["confidence"])),
                max(float(existing["materiality"]), float(payload["materiality"])),
                now,
                json.dumps(metadata, sort_keys=True),
                existing["entry_id"],
            ),
        )
        self._insert_change_log(
            conn,
            str(existing["company_id"]),
            int(existing["entry_id"]),
            "reinforce",
            {"source_id": payload["source_id"]},
            now,
        )
        return self._get_entry_by_id(conn, int(existing["entry_id"]))

    def _expire_matching_entry(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        payload: dict[str, Any],
        now: str,
    ) -> dict[str, Any]:
        existing = self._find_matching_active_entry(conn, company_id, payload)
        if existing is None:
            raise ValueError("no active company memory entry matches the expiry signal")
        conn.execute(
            """
            UPDATE memory_entries
            SET status = 'expired', closed_at = ?, last_seen_at = ?
            WHERE entry_id = ?
            """,
            (now, now, existing["entry_id"]),
        )
        self._insert_change_log(
            conn,
            company_id,
            int(existing["entry_id"]),
            "expire",
            {"source_id": payload["source_id"]},
            now,
        )
        return self._get_entry_by_id(conn, int(existing["entry_id"]))

    def _transition_targets(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        targets: list[Any],
        *,
        new_status: str,
        event_type: str,
        now: str,
    ) -> list[int]:
        transitioned: list[int] = []
        for target in targets:
            row = self._resolve_target_row(conn, company_id, target)
            if row is None:
                continue
            conn.execute(
                """
                UPDATE memory_entries
                SET status = ?, closed_at = ?, last_seen_at = ?
                WHERE entry_id = ?
                """,
                (new_status, now, now, row["entry_id"]),
            )
            entry_id = int(row["entry_id"])
            transitioned.append(entry_id)
            self._insert_change_log(
                conn,
                company_id,
                entry_id,
                event_type,
                {"target": target},
                now,
            )
        return transitioned

    def _resolve_target_row(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        target: Any,
    ) -> dict[str, Any] | None:
        if isinstance(target, int) or (
            isinstance(target, str) and str(target).isdigit()
        ):
            row = conn.execute(
                "SELECT * FROM memory_entries WHERE company_id = ? AND entry_id = ? LIMIT 1",
                (company_id, int(target)),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM memory_entries
                WHERE company_id = ? AND normalized_statement = ? AND status = 'active'
                ORDER BY entry_id ASC
                LIMIT 1
                """,
                (company_id, _normalize_statement(str(target))),
            ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def _sync_company_summary(
        self, conn: sqlite3.Connection, company_id: str, now: str
    ) -> None:
        active_count_row = conn.execute(
            "SELECT COUNT(*) AS count FROM memory_entries WHERE company_id = ? AND status = 'active'",
            (company_id,),
        ).fetchone()
        active_count = int(
            active_count_row["count"] if active_count_row is not None else 0
        )
        conn.execute(
            "UPDATE company_memory SET active_entry_count = ?, updated_at = ? WHERE company_id = ?",
            (active_count, now, company_id),
        )

    def _insert_change_log(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        entry_id: int | None,
        event_type: str,
        details: dict[str, Any],
        now: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO change_log (company_id, entry_id, event_type, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                company_id,
                entry_id,
                event_type,
                json.dumps(details, sort_keys=True),
                now,
            ),
        )

    def _get_entry_by_id(
        self, conn: sqlite3.Connection, entry_id: int
    ) -> dict[str, Any]:
        row = conn.execute(
            "SELECT * FROM memory_entries WHERE entry_id = ? LIMIT 1",
            (entry_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"company memory entry not found: {entry_id}")
        return self._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
        if row is None:
            return {}
        data = dict(row)
        raw_metadata = data.get("metadata_json") or "{}"
        try:
            data["metadata"] = json.loads(raw_metadata)
        except json.JSONDecodeError:
            data["metadata"] = {}
        data.pop("metadata_json", None)
        return data

    @staticmethod
    def _change_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        raw_details = data.get("details_json") or "{}"
        try:
            data["details"] = json.loads(raw_details)
        except json.JSONDecodeError:
            data["details"] = {}
        data.pop("details_json", None)
        return data

    def _rank_active_entries(
        self,
        items: list[dict[str, Any]],
        *,
        query: str,
        intent: str,
    ) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for item in items:
            annotated = dict(item)
            expiry_state = _expiry_state(annotated)
            if expiry_state == "expired":
                continue
            annotated["expiry_state"] = expiry_state
            annotated["active_score"] = _active_score(
                annotated,
                query=query,
                intent=intent,
                expiry_state=expiry_state,
            )
            if annotated["active_score"] < _promotion_threshold(annotated):
                continue
            ranked.append(annotated)
        ranked.sort(
            key=lambda item: (
                float(item.get("active_score") or 0.0),
                str(item.get("last_seen_at") or ""),
                int(item.get("entry_id") or 0),
            ),
            reverse=True,
        )
        return _collapse_replaceable_entries(ranked)


def update_company_memory(
    company_id: str,
    signal: dict[str, Any],
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    return CompanyMemoryStore(path).update_company_memory(company_id, signal)


def add_manual_company_memory_entry(
    company_id: str,
    *,
    signal_type: str,
    statement: str,
    confidence: float = 0.0,
    materiality: float = 0.0,
    persistence: str = "medium",
    supersedes: list[Any] | None = None,
    contradicts: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    return CompanyMemoryStore(path).add_manual_entry(
        company_id,
        signal_type=signal_type,
        statement=statement,
        confidence=confidence,
        materiality=materiality,
        persistence=persistence,
        supersedes=supersedes,
        contradicts=contradicts,
        metadata=metadata,
    )


def expire_company_memory_entry(
    company_id: str,
    entry_id: int,
    *,
    reason: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    return CompanyMemoryStore(path).expire_entry(
        company_id,
        entry_id,
        reason=reason,
    )


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", str(query or "").lower())
        if len(token) > 2
    }


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _signal_expiry_days(item: dict[str, Any]) -> int:
    signal_type = str(item.get("type") or "").strip().lower()
    persistence = str(item.get("persistence") or "medium").strip().lower()
    base_days = {"short": 60, "medium": 180, "long": 365}.get(persistence, 180)
    type_days = {
        "operating_context": 30,
        "interpretation": 60,
        "management_guidance": 120,
        "catalyst": 120,
        "risk": 180,
        "observed_fact": 180,
        "strategic_initiative": 365,
    }.get(signal_type, base_days)
    if persistence == "short":
        return min(type_days, 60)
    if persistence == "long":
        return max(type_days, 365)
    return type_days


def _expiry_state(item: dict[str, Any]) -> str:
    last_seen = _parse_timestamp(item.get("last_seen_at"))
    if last_seen is None:
        return "fresh"
    age_days = max(
        (datetime.now(timezone.utc) - last_seen).total_seconds() / 86400, 0.0
    )
    expiry_days = float(_signal_expiry_days(item))
    if age_days >= expiry_days:
        return "expired"
    if age_days >= expiry_days * 0.75:
        return "aging"
    return "fresh"


def _active_score(
    item: dict[str, Any],
    *,
    query: str,
    intent: str,
    expiry_state: str,
) -> float:
    metadata = dict(item.get("metadata") or {})
    specificity = float(metadata.get("specificity") or 0.0)
    reinforcement_bonus = min(int(item.get("reinforcement_count") or 0) * 0.06, 0.18)
    recency = 1.0
    last_seen = _parse_timestamp(item.get("last_seen_at"))
    if last_seen is not None:
        age_days = max(
            (datetime.now(timezone.utc) - last_seen).total_seconds() / 86400,
            0.0,
        )
        recency = max(0.0, 1.0 - (age_days / float(_signal_expiry_days(item))))
    score = (
        (float(item.get("confidence") or 0.0) * 0.34)
        + (float(item.get("materiality") or 0.0) * 0.34)
        + (recency * 0.18)
        + (specificity * 0.08)
        + reinforcement_bonus
        + _TYPE_WEIGHT.get(str(item.get("type") or "").strip().lower(), 0.0)
        + _intent_bonus(item, intent=intent)
        + _theme_overlap_bonus(item, query=query)
    )
    if expiry_state == "aging":
        score -= 0.12
    if metadata.get("contradicted_entry_ids"):
        score -= 0.1
    if metadata.get("superseded_entry_ids"):
        score += 0.03
    return round(max(0.0, min(1.5, score)), 3)


def _intent_bonus(item: dict[str, Any], *, intent: str) -> float:
    priorities = _INTENT_TYPE_PRIORITY.get(intent) or _INTENT_TYPE_PRIORITY.get("mixed")
    signal_type = str(item.get("type") or "").strip().lower()
    if signal_type not in priorities:
        return 0.0
    return max(0.0, (len(priorities) - priorities.index(signal_type)) * 0.01)


def _theme_overlap_bonus(item: dict[str, Any], *, query: str) -> float:
    metadata = dict(item.get("metadata") or {})
    themes = {str(theme).lower() for theme in metadata.get("themes") or []}
    terms = _query_terms(query)
    if themes & terms:
        return 0.05
    statement_terms = _query_terms(str(item.get("statement") or ""))
    return 0.03 if statement_terms & terms else 0.0


def _promotion_threshold(item: dict[str, Any]) -> float:
    metadata = dict(item.get("metadata") or {})
    specificity = float(metadata.get("specificity") or 0.0)
    if int(item.get("reinforcement_count") or 0) > 0:
        return 0.54
    if float(item.get("materiality") or 0.0) >= 0.8:
        return 0.56
    return 0.62 if specificity < 0.55 else 0.58


def _collapse_replaceable_entries(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        metadata = dict(item.get("metadata") or {})
        signal_type = str(item.get("type") or "").strip().lower()
        theme_key = str(metadata.get("theme_key") or "").strip().lower()
        replaceable = (
            bool(metadata.get("replaceable")) or signal_type in _REPLACEABLE_TYPES
        )
        key = (signal_type, theme_key)
        if replaceable and theme_key:
            if key in seen:
                continue
            seen.add(key)
        collapsed.append(item)
    return collapsed
