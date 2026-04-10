from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.source_registry import RESEARCH_MEMORY_ROOT

DEFAULT_MARKET_MEMORY_PATH = RESEARCH_MEMORY_ROOT / "market_memory.sqlite"

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
_VALID_INPUT_STATUSES = {"active", "expired"}
_TYPE_WEIGHT = {
    "sector_risk": 0.08,
    "macro_risk": 0.08,
    "sector_trend": 0.05,
    "macro_theme": 0.05,
}
_INTENT_TYPE_PRIORITY = {
    "market": ("sector_trend", "macro_theme", "sector_risk", "macro_risk"),
    "risk_catalyst": ("sector_risk", "macro_risk", "sector_trend", "macro_theme"),
    "mixed": ("sector_trend", "macro_theme", "sector_risk", "macro_risk"),
    "financial_interpretation": (
        "sector_trend",
        "macro_theme",
        "sector_risk",
        "macro_risk",
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_statement(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _normalize_list(values: Any, *, uppercase: bool = False) -> list[str]:
    items = values if isinstance(values, list) else [values]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        candidate = text.upper() if uppercase else text
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


class MarketMemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_MARKET_MEMORY_PATH).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS market_memory (
                    scope TEXT PRIMARY KEY,
                    active_entry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sector_states (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sector TEXT NOT NULL,
                    type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    normalized_statement TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    materiality REAL NOT NULL,
                    persistence TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    linked_tickers_json TEXT NOT NULL DEFAULT '[]',
                    reinforcement_count INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    closed_at TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_sector_states_lookup
                    ON sector_states(sector, status, type, normalized_statement);

                CREATE TABLE IF NOT EXISTS macro_state (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    macro_topic TEXT NOT NULL,
                    type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    normalized_statement TEXT NOT NULL,
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
                CREATE INDEX IF NOT EXISTS idx_macro_state_lookup
                    ON macro_state(macro_topic, status, type, normalized_statement);

                CREATE TABLE IF NOT EXISTS change_log (
                    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    entity_key TEXT NOT NULL,
                    entry_id INTEGER,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_market_change_log
                    ON change_log(scope, entity_key, created_at);
                """
            )

    def update_market_memory(self, signal: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_signal(signal)
        scope = str(payload["scope"])
        table = "sector_states" if scope == "sector" else "macro_state"
        key_column = "sector" if scope == "sector" else "macro_topic"
        entity_key = str(payload[key_column])
        now = _utc_now()

        with self._connect() as conn:
            self._ensure_scope_row(conn, scope, now)

            if payload["status"] == "expired":
                expired_entry = self._expire_matching_entry(
                    conn,
                    table=table,
                    key_column=key_column,
                    entity_key=entity_key,
                    payload=payload,
                    scope=scope,
                    now=now,
                )
                self._sync_scope_summary(conn, scope, now)
                return {"rule": "expire", "entry": expired_entry}

            existing = self._find_matching_active_entry(
                conn,
                table=table,
                key_column=key_column,
                entity_key=entity_key,
                payload=payload,
            )
            if existing is not None:
                if existing["source_id"] == payload["source_id"]:
                    self._insert_change_log(
                        conn,
                        scope,
                        entity_key,
                        int(existing["entry_id"]),
                        "dedupe",
                        {"source_id": payload["source_id"]},
                        now,
                    )
                    return {"rule": "dedupe", "entry": existing}
                reinforced = self._reinforce_entry(
                    conn,
                    table=table,
                    existing=existing,
                    payload=payload,
                    scope=scope,
                    entity_key=entity_key,
                    now=now,
                )
                self._sync_scope_summary(conn, scope, now)
                return {"rule": "reinforce", "entry": reinforced}

            superseded = self._transition_targets(
                conn,
                table=table,
                key_column=key_column,
                scope=scope,
                entity_key=entity_key,
                targets=payload.get("supersedes") or [],
                new_status="superseded",
                event_type="supersede",
                now=now,
            )
            contradicted = self._transition_targets(
                conn,
                table=table,
                key_column=key_column,
                scope=scope,
                entity_key=entity_key,
                targets=payload.get("contradicts") or [],
                new_status="contradicted",
                event_type="contradict",
                now=now,
            )
            payload["metadata"] = {
                **payload["metadata"],
                "superseded_entry_ids": superseded,
                "contradicted_entry_ids": contradicted,
            }

            if scope == "sector":
                entry_id = conn.execute(
                    f"""
                    INSERT INTO {table} (
                        {key_column}, type, statement, normalized_statement,
                        confidence, materiality, persistence, status, source, source_id,
                        linked_tickers_json, reinforcement_count, first_seen_at, last_seen_at,
                        metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_key,
                        payload["type"],
                        payload["statement"],
                        payload["normalized_statement"],
                        payload["confidence"],
                        payload["materiality"],
                        payload["persistence"],
                        "active",
                        payload["source"],
                        payload["source_id"],
                        json.dumps(payload["linked_tickers"], sort_keys=True),
                        0,
                        now,
                        now,
                        json.dumps(payload["metadata"], sort_keys=True),
                    ),
                ).lastrowid
            else:
                entry_id = conn.execute(
                    f"""
                    INSERT INTO {table} (
                        {key_column}, type, statement, normalized_statement,
                        confidence, materiality, persistence, status, source, source_id,
                        reinforcement_count, first_seen_at, last_seen_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_key,
                        payload["type"],
                        payload["statement"],
                        payload["normalized_statement"],
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
                scope,
                entity_key,
                int(entry_id),
                event_type,
                {
                    "source_id": payload["source_id"],
                    "superseded_entry_ids": superseded,
                    "contradicted_entry_ids": contradicted,
                },
                now,
            )
            self._sync_scope_summary(conn, scope, now)
            entry = self._get_entry_by_id(conn, table, int(entry_id))
            return {"rule": event_type, "entry": entry}

    def list_sector_entries(
        self, sector: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        return self._list_entries("sector_states", "sector", sector, status)

    def list_macro_entries(
        self, macro_topic: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        return self._list_entries("macro_state", "macro_topic", macro_topic, status)

    def list_change_log(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM change_log ORDER BY change_id ASC"
            ).fetchall()
        return [self._change_row_to_dict(row) for row in rows]

    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]:
        sector = self._resolve_relevant_sector(query=query, entities=entities)
        sector_items = self._rank_active_entries(
            self.list_sector_entries(sector, status="active") if sector else [],
            query=query,
            intent=intent,
        )
        macro_items = self._rank_active_entries(
            self._list_entries("macro_state", None, None, "active"),
            query=query,
            intent=intent,
        )
        return {
            "source": "market_memory",
            "status": "ok",
            "sector": sector,
            "sector_items": sector_items,
            "macro_items": macro_items,
            "items": sector_items + macro_items,
            "query": query,
            "intent": intent,
        }

    def _normalize_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        payload = dict(signal or {})
        scope = str(payload.get("scope") or "").strip().lower()
        if scope not in {"sector", "macro"}:
            raise ValueError("market memory signal scope must be 'sector' or 'macro'")

        signal_type = str(payload.get("type") or "").strip().lower()
        if not signal_type:
            raise ValueError("signal type is required")
        if signal_type in _FORBIDDEN_SIGNAL_TYPES:
            raise ValueError(
                "financial metric signals must not be written to market memory"
            )

        statement = str(payload.get("statement") or "").strip()
        if not statement:
            raise ValueError("signal statement is required")

        status = str(payload.get("status") or "active").strip().lower()
        if status not in _VALID_INPUT_STATUSES:
            raise ValueError(f"unsupported market memory status: {status}")

        entity_key_field = "sector" if scope == "sector" else "macro_topic"
        entity_key = str(payload.get(entity_key_field) or "").strip()
        if not entity_key:
            raise ValueError(f"{entity_key_field} is required")

        source_id = str(payload.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("signal source_id is required")

        return {
            "scope": scope,
            entity_key_field: entity_key,
            "type": signal_type,
            "statement": statement,
            "normalized_statement": _normalize_statement(statement),
            "confidence": float(
                payload.get("confidence")
                if payload.get("confidence") not in (None, "")
                else 0.0
            ),
            "materiality": float(
                payload.get("materiality")
                if payload.get("materiality") not in (None, "")
                else 0.0
            ),
            "persistence": str(payload.get("persistence") or "medium").strip().lower(),
            "status": status,
            "source": str(payload.get("source") or "unknown").strip(),
            "source_id": source_id,
            "linked_tickers": _normalize_list(
                payload.get("linked_tickers") or [], uppercase=True
            ),
            "supersedes": list(payload.get("supersedes") or []),
            "contradicts": list(payload.get("contradicts") or []),
            "metadata": dict(payload.get("metadata") or {}),
        }

    def _ensure_scope_row(self, conn: sqlite3.Connection, scope: str, now: str) -> None:
        conn.execute(
            """
            INSERT INTO market_memory (scope, active_entry_count, created_at, updated_at)
            VALUES (?, 0, ?, ?)
            ON CONFLICT(scope) DO NOTHING
            """,
            (scope, now, now),
        )

    def _list_entries(
        self,
        table: str,
        key_column: str | None,
        entity_key: str | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        query = f"SELECT * FROM {table}"
        params: list[Any] = []
        clauses: list[str] = []
        if key_column is not None and entity_key is not None:
            clauses.append(f"{key_column} = ?")
            params.append(entity_key)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY entry_id ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _find_matching_active_entry(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        key_column: str,
        entity_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        row = conn.execute(
            f"""
            SELECT * FROM {table}
            WHERE {key_column} = ? AND type = ? AND normalized_statement = ? AND status = 'active'
            ORDER BY entry_id ASC
            LIMIT 1
            """,
            (entity_key, payload["type"], payload["normalized_statement"]),
        ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def _reinforce_entry(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        existing: dict[str, Any],
        payload: dict[str, Any],
        scope: str,
        entity_key: str,
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
        for key in ("theme_key", "replaceable"):
            if key in payload["metadata"] and not metadata.get(key):
                metadata[key] = payload["metadata"][key]
        updates = {
            "confidence": max(
                float(existing["confidence"]), float(payload["confidence"])
            ),
            "materiality": max(
                float(existing["materiality"]), float(payload["materiality"])
            ),
            "reinforcement_count": int(existing["reinforcement_count"]) + 1,
            "last_seen_at": now,
            "metadata_json": json.dumps(metadata, sort_keys=True),
        }
        if scope == "sector":
            linked = _normalize_list(
                existing.get("linked_tickers") or [], uppercase=True
            )
            for ticker in payload.get("linked_tickers") or []:
                if ticker not in linked:
                    linked.append(ticker)
            updates["linked_tickers_json"] = json.dumps(linked, sort_keys=True)
            conn.execute(
                f"""
                UPDATE {table}
                SET confidence = ?, materiality = ?, reinforcement_count = ?, last_seen_at = ?,
                    metadata_json = ?, linked_tickers_json = ?
                WHERE entry_id = ?
                """,
                (
                    updates["confidence"],
                    updates["materiality"],
                    updates["reinforcement_count"],
                    updates["last_seen_at"],
                    updates["metadata_json"],
                    updates["linked_tickers_json"],
                    existing["entry_id"],
                ),
            )
        else:
            conn.execute(
                f"""
                UPDATE {table}
                SET confidence = ?, materiality = ?, reinforcement_count = ?, last_seen_at = ?,
                    metadata_json = ?
                WHERE entry_id = ?
                """,
                (
                    updates["confidence"],
                    updates["materiality"],
                    updates["reinforcement_count"],
                    updates["last_seen_at"],
                    updates["metadata_json"],
                    existing["entry_id"],
                ),
            )
        self._insert_change_log(
            conn,
            scope,
            entity_key,
            int(existing["entry_id"]),
            "reinforce",
            {"source_id": payload["source_id"]},
            now,
        )
        return self._get_entry_by_id(conn, table, int(existing["entry_id"]))

    def _expire_matching_entry(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        key_column: str,
        entity_key: str,
        payload: dict[str, Any],
        scope: str,
        now: str,
    ) -> dict[str, Any]:
        existing = self._find_matching_active_entry(
            conn,
            table=table,
            key_column=key_column,
            entity_key=entity_key,
            payload=payload,
        )
        if existing is None:
            raise ValueError("no active market memory entry matches the expiry signal")
        conn.execute(
            f"UPDATE {table} SET status = 'expired', closed_at = ?, last_seen_at = ? WHERE entry_id = ?",
            (now, now, existing["entry_id"]),
        )
        self._insert_change_log(
            conn,
            scope,
            entity_key,
            int(existing["entry_id"]),
            "expire",
            {"source_id": payload["source_id"]},
            now,
        )
        return self._get_entry_by_id(conn, table, int(existing["entry_id"]))

    def _transition_targets(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        key_column: str,
        scope: str,
        entity_key: str,
        targets: list[Any],
        new_status: str,
        event_type: str,
        now: str,
    ) -> list[int]:
        transitioned: list[int] = []
        for target in targets:
            row = self._resolve_target_row(conn, table, key_column, entity_key, target)
            if row is None:
                continue
            conn.execute(
                f"UPDATE {table} SET status = ?, closed_at = ?, last_seen_at = ? WHERE entry_id = ?",
                (new_status, now, now, row["entry_id"]),
            )
            transitioned.append(int(row["entry_id"]))
            self._insert_change_log(
                conn,
                scope,
                entity_key,
                int(row["entry_id"]),
                event_type,
                {"target": target},
                now,
            )
        return transitioned

    def _resolve_target_row(
        self,
        conn: sqlite3.Connection,
        table: str,
        key_column: str,
        entity_key: str,
        target: Any,
    ) -> dict[str, Any] | None:
        if isinstance(target, int) or (
            isinstance(target, str) and str(target).isdigit()
        ):
            row = conn.execute(
                f"SELECT * FROM {table} WHERE {key_column} = ? AND entry_id = ? LIMIT 1",
                (entity_key, int(target)),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE {key_column} = ? AND normalized_statement = ? AND status = 'active' LIMIT 1",
                (entity_key, _normalize_statement(str(target))),
            ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def _sync_scope_summary(
        self, conn: sqlite3.Connection, scope: str, now: str
    ) -> None:
        table = "sector_states" if scope == "sector" else "macro_state"
        count_row = conn.execute(
            f"SELECT COUNT(*) AS count FROM {table} WHERE status = 'active'"
        ).fetchone()
        active_count = int(count_row["count"] if count_row is not None else 0)
        conn.execute(
            "UPDATE market_memory SET active_entry_count = ?, updated_at = ? WHERE scope = ?",
            (active_count, now, scope),
        )

    def _insert_change_log(
        self,
        conn: sqlite3.Connection,
        scope: str,
        entity_key: str,
        entry_id: int | None,
        event_type: str,
        details: dict[str, Any],
        now: str,
    ) -> None:
        conn.execute(
            "INSERT INTO change_log (scope, entity_key, entry_id, event_type, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                scope,
                entity_key,
                entry_id,
                event_type,
                json.dumps(details, sort_keys=True),
                now,
            ),
        )

    def _get_entry_by_id(
        self, conn: sqlite3.Connection, table: str, entry_id: int
    ) -> dict[str, Any]:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE entry_id = ? LIMIT 1", (entry_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"market memory entry not found: {entry_id}")
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

        raw_linked_tickers = data.get("linked_tickers_json")
        if raw_linked_tickers is not None:
            try:
                data["linked_tickers"] = json.loads(raw_linked_tickers)
            except json.JSONDecodeError:
                data["linked_tickers"] = []
            data.pop("linked_tickers_json", None)
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

    @staticmethod
    def _resolve_relevant_sector(query: str, entities: dict[str, Any]) -> str | None:
        from app.services.analysis.sector_comparison import (
            SECTOR_TICKERS,
            get_sector_for_ticker,
        )

        primary_ticker = str(entities.get("primary_ticker") or "").strip().upper()
        if primary_ticker:
            sector = get_sector_for_ticker(primary_ticker)
            if sector:
                return sector

        lowered = str(query or "").lower()
        for sector_name in SECTOR_TICKERS:
            if sector_name.lower() in lowered:
                return sector_name
        return None


def update_market_memory(
    signal: dict[str, Any],
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    return MarketMemoryStore(path).update_market_memory(signal)


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
    persistence = str(item.get("persistence") or "medium").strip().lower()
    signal_type = str(item.get("type") or "").strip().lower()
    base_days = {"short": 75, "medium": 240, "long": 450}.get(persistence, 240)
    type_days = {
        "sector_risk": 180,
        "macro_risk": 210,
        "sector_trend": 240,
        "macro_theme": 300,
    }.get(signal_type, base_days)
    if persistence == "short":
        return min(type_days, 90)
    if persistence == "long":
        return max(type_days, 450)
    return type_days


def _expiry_state(item: dict[str, Any]) -> str:
    last_seen = _parse_timestamp(item.get("last_seen_at"))
    if last_seen is None:
        return "fresh"
    age_days = max(
        (datetime.now(timezone.utc) - last_seen).total_seconds() / 86400,
        0.0,
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
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        metadata = dict(item.get("metadata") or {})
        signal_type = str(item.get("type") or "").strip().lower()
        scope_key = (
            str(item.get("sector") or item.get("macro_topic") or "").strip().lower()
        )
        theme_key = str(metadata.get("theme_key") or "").strip().lower()
        key = (signal_type, scope_key, theme_key)
        if bool(metadata.get("replaceable")) and scope_key and theme_key:
            if key in seen:
                continue
            seen.add(key)
        collapsed.append(item)
    return collapsed
