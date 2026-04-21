from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.memory_events import emit_memory_write_event
from app.services.source_registry import RESEARCH_MEMORY_ROOT

DEFAULT_USER_THESIS_MEMORY_PATH = RESEARCH_MEMORY_ROOT / "user_thesis_memory.sqlite"

_VALID_PROPOSAL_TYPES = {"create_thesis", "add_evidence", "invalidate"}
_VALID_PROPOSAL_STATUS = {"pending", "confirmed", "rejected", "applied"}
_VALID_SIGNALS = {"BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL"}



def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()



def _normalize_ticker(value: str) -> str:
    ticker = str(value or "").strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    return ticker



def _normalize_signal(value: Any) -> str | None:
    if value in (None, ""):
        return None
    signal = str(value).strip().upper()
    if signal not in _VALID_SIGNALS:
        raise ValueError(f"unsupported signal: {signal}")
    return signal


class UserThesisMemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_USER_THESIS_MEMORY_PATH).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS thesis_entries (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    signal TEXT,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL DEFAULT 'active',
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_thesis_entries_ticker_status
                    ON thesis_entries(ticker, status, entry_type);

                CREATE TABLE IF NOT EXISTS thesis_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    proposal_type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    signal TEXT,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT,
                    confirmation_note TEXT,
                    created_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    applied_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_thesis_proposals_ticker_status
                    ON thesis_proposals(ticker, status, created_at DESC);
                """
            )

    def create_proposal(
        self,
        *,
        ticker: str,
        proposal_type: str,
        statement: str,
        signal: str | None = None,
        confidence: float = 0.6,
        metadata: dict[str, Any] | None = None,
        requested_by: str | None = None,
    ) -> dict[str, Any]:
        normalized_ticker = _normalize_ticker(ticker)
        normalized_type = str(proposal_type or "").strip().lower()
        if normalized_type not in _VALID_PROPOSAL_TYPES:
            raise ValueError(f"unsupported proposal_type: {proposal_type}")
        normalized_statement = str(statement or "").strip()
        if not normalized_statement:
            raise ValueError("statement is required")
        normalized_signal = _normalize_signal(signal)

        payload = {
            "ticker": normalized_ticker,
            "proposal_type": normalized_type,
            "statement": normalized_statement,
            "signal": normalized_signal,
            "confidence": float(max(0.0, min(1.0, confidence))),
            "metadata": dict(metadata or {}),
        }
        proposal_id = f"thp_{uuid.uuid4().hex[:16]}"
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO thesis_proposals (
                    proposal_id, ticker, proposal_type, statement, signal, confidence,
                    payload_json, status, requested_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    proposal_id,
                    normalized_ticker,
                    normalized_type,
                    normalized_statement,
                    normalized_signal,
                    payload["confidence"],
                    json.dumps(payload, sort_keys=True),
                    str(requested_by or "").strip() or None,
                    now,
                ),
            )
        return self.get_proposal(proposal_id)

    def list_proposals(
        self,
        *,
        ticker: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if ticker:
            clauses.append("ticker = ?")
            params.append(_normalize_ticker(ticker))
        if status:
            normalized_status = str(status or "").strip().lower()
            if normalized_status not in _VALID_PROPOSAL_STATUS:
                raise ValueError(f"unsupported proposal status: {status}")
            clauses.append("status = ?")
            params.append(normalized_status)
        query = "SELECT * FROM thesis_proposals"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._proposal_row_to_dict(row) for row in rows]

    def get_proposal(self, proposal_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM thesis_proposals WHERE proposal_id = ? LIMIT 1",
                (str(proposal_id or "").strip(),),
            ).fetchone()
        if row is None:
            raise ValueError(f"thesis proposal not found: {proposal_id}")
        return self._proposal_row_to_dict(row)

    def confirm_proposal(
        self,
        proposal_id: str,
        *,
        note: str | None = None,
    ) -> dict[str, Any]:
        proposal = self.get_proposal(proposal_id)
        if proposal["status"] != "pending":
            raise ValueError(
                f"proposal {proposal_id} is not pending (status={proposal['status']})"
            )
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE thesis_proposals
                SET status = 'confirmed', confirmation_note = ?, confirmed_at = ?
                WHERE proposal_id = ?
                """,
                (str(note or "").strip() or None, now, proposal_id),
            )
        return self.get_proposal(proposal_id)

    def reject_proposal(
        self,
        proposal_id: str,
        *,
        note: str | None = None,
    ) -> dict[str, Any]:
        proposal = self.get_proposal(proposal_id)
        if proposal["status"] not in {"pending", "confirmed"}:
            raise ValueError(
                f"proposal {proposal_id} cannot be rejected from status={proposal['status']}"
            )
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE thesis_proposals
                SET status = 'rejected', confirmation_note = ?
                WHERE proposal_id = ?
                """,
                (str(note or "").strip() or None, proposal_id),
            )
        return self.get_proposal(proposal_id)

    def apply_confirmed_proposal(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.get_proposal(proposal_id)
        if proposal["status"] != "confirmed":
            raise ValueError(
                f"proposal {proposal_id} is not confirmed (status={proposal['status']})"
            )
        payload = dict(proposal.get("payload") or {})
        ticker = _normalize_ticker(str(payload.get("ticker") or proposal.get("ticker") or ""))
        proposal_type = str(payload.get("proposal_type") or proposal.get("proposal_type") or "").strip().lower()
        statement = str(payload.get("statement") or proposal.get("statement") or "").strip()
        signal = _normalize_signal(payload.get("signal") or proposal.get("signal"))
        confidence = float(payload.get("confidence") or proposal.get("confidence") or 0.0)
        metadata = dict(payload.get("metadata") or {})
        now = _utc_now()

        inserted_entry: dict[str, Any] | None = None
        with self._connect() as conn:
            if proposal_type == "create_thesis":
                entry_id = conn.execute(
                    """
                    INSERT INTO thesis_entries (
                        ticker, entry_type, statement, signal, confidence, status,
                        source, source_id, metadata_json, created_at, updated_at
                    ) VALUES (?, 'thesis', ?, ?, ?, 'active', 'user_confirmed', ?, ?, ?, ?)
                    """,
                    (
                        ticker,
                        statement,
                        signal,
                        confidence,
                        f"thesis:{proposal_id}",
                        json.dumps(metadata, sort_keys=True),
                        now,
                        now,
                    ),
                ).lastrowid
                inserted_entry = self._get_entry_by_id(conn, int(entry_id))
            elif proposal_type == "add_evidence":
                evidence_type = (
                    "supporting_evidence"
                    if bool(metadata.get("is_supporting", True))
                    else "disconfirming_evidence"
                )
                entry_id = conn.execute(
                    """
                    INSERT INTO thesis_entries (
                        ticker, entry_type, statement, signal, confidence, status,
                        source, source_id, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, NULL, ?, 'active', 'user_confirmed', ?, ?, ?, ?)
                    """,
                    (
                        ticker,
                        evidence_type,
                        statement,
                        confidence,
                        f"thesis:{proposal_id}",
                        json.dumps(metadata, sort_keys=True),
                        now,
                        now,
                    ),
                ).lastrowid
                inserted_entry = self._get_entry_by_id(conn, int(entry_id))
            elif proposal_type == "invalidate":
                conn.execute(
                    """
                    UPDATE thesis_entries
                    SET status = 'invalidated', updated_at = ?
                    WHERE ticker = ? AND status = 'active' AND entry_type = 'thesis'
                    """,
                    (now, ticker),
                )
            else:
                raise ValueError(f"unsupported proposal_type: {proposal_type}")

            conn.execute(
                """
                UPDATE thesis_proposals
                SET status = 'applied', applied_at = ?
                WHERE proposal_id = ?
                """,
                (now, proposal_id),
            )

        emit_memory_write_event(
            memory_class="user_thesis_memory",
            event_type=f"proposal_{proposal_type}_applied",
            payload={
                "proposal_id": proposal_id,
                "ticker": ticker,
                "proposal_type": proposal_type,
                "entry_id": inserted_entry.get("entry_id") if inserted_entry else None,
                "status": "applied",
            },
        )

        return {
            "proposal": self.get_proposal(proposal_id),
            "entry": inserted_entry,
        }

    def list_entries(
        self,
        ticker: str,
        *,
        status: str | None = "active",
    ) -> list[dict[str, Any]]:
        normalized_ticker = _normalize_ticker(ticker)
        query = "SELECT * FROM thesis_entries WHERE ticker = ?"
        params: list[Any] = [normalized_ticker]
        if status:
            query += " AND status = ?"
            params.append(str(status or "").strip().lower())
        query += " ORDER BY entry_id ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._entry_row_to_dict(row) for row in rows]

    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]:
        ticker = str(entities.get("primary_ticker") or "").strip().upper()
        if not ticker:
            return {"source": "user_thesis_memory", "status": "no_entity", "items": []}
        entries = self.list_entries(ticker, status="active")
        items: list[dict[str, Any]] = []
        for entry in entries:
            item = dict(entry)
            item["active_score"] = float(item.get("confidence") or 0.0)
            items.append(item)
        return {
            "source": "user_thesis_memory",
            "status": "ok",
            "items": items,
            "query": query,
            "intent": intent,
        }

    @staticmethod
    def _entry_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        raw_metadata = data.get("metadata_json") or "{}"
        try:
            data["metadata"] = json.loads(raw_metadata)
        except json.JSONDecodeError:
            data["metadata"] = {}
        data.pop("metadata_json", None)
        return data

    @staticmethod
    def _proposal_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        raw_payload = data.get("payload_json") or "{}"
        try:
            data["payload"] = json.loads(raw_payload)
        except json.JSONDecodeError:
            data["payload"] = {}
        data.pop("payload_json", None)
        return data

    def _get_entry_by_id(self, conn: sqlite3.Connection, entry_id: int) -> dict[str, Any]:
        row = conn.execute(
            "SELECT * FROM thesis_entries WHERE entry_id = ? LIMIT 1",
            (int(entry_id),),
        ).fetchone()
        if row is None:
            raise ValueError(f"thesis entry not found: {entry_id}")
        return self._entry_row_to_dict(row)
