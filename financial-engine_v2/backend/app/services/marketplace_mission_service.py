from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from cockpit.storage.state import StateStore


MISSION_STATUSES = {"active", "paused", "archived"}
MATCH_STATUSES = {"new", "reviewed", "dismissed", "contacted", "won", "lost"}
ALERT_STATUSES = {"new", "acknowledged", "dismissed"}
DECISION_BANDS = {"candidate", "strong_match", "reject"}

DEFAULT_HARD_FILTERS = {
    "include_keywords": [],
    "exclude_keywords": [],
    "price_min": None,
    "price_max": None,
    "location_names": [],
    "radius_km": None,
    "condition_required": [],
    "required_terms": [],
    "forbidden_terms": [],
}

DEFAULT_SOFT_PREFERENCES = {
    "preferred_brands": [],
    "preferred_suburbs": [],
    "preferred_condition_terms": [],
    "nice_to_have_terms": [],
    "urgency": "normal",
    "price_aggressiveness": "balanced",
    "negotiation_expected": False,
}

DEFAULT_SEARCH_CONFIG = {
    "query_variants_enabled": True,
    "broadening_enabled": True,
    "max_queries_per_run": 6,
}

DEFAULT_SCAN_CONFIG = {
    "scan_interval_minutes": 15,
    "candidate_card_target": 300,
    "detail_open_target": 100,
    "run_time_budget_minutes": 20,
    "strong_match_threshold": 85,
    "candidate_threshold": 70,
    "aggressive_alerting": False,
}

_MEANINGFUL_WORD_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, tuple):
        raw_items = list(value)
    elif isinstance(value, str):
        raw_items = re.split(r"[,;\n]", value)
    elif value is None:
        raw_items = []
    else:
        raw_items = [value]

    out: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _optional_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _meaningful_brief(brief: str) -> bool:
    return len(_MEANINGFUL_WORD_RE.findall(brief)) >= 2


class MarketplaceMissionError(ValueError):
    pass


class MarketplaceMissionNotFound(KeyError):
    pass


class MarketplaceMissionService:
    """Backend-owned Marketplace mission and persistence surface."""

    def __init__(self, state_store: StateStore) -> None:
        self.state_store = state_store
        self._lock: threading.Lock = state_store._lock
        self._conn = state_store.conn

    # ------------------------------------------------------------------ #
    # Mission CRUD                                                        #
    # ------------------------------------------------------------------ #

    def create_mission(self, payload: dict[str, Any]) -> dict[str, Any]:
        mission = self._normalize_mission_payload(payload)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO marketplace_missions (
                    mission_id, name, status, brief, category_hint,
                    hard_filters_json, soft_preferences_json, search_config_json,
                    scan_config_json, created_at, updated_at, last_scan_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission["mission_id"],
                    mission["name"],
                    mission["status"],
                    mission["brief"],
                    mission["category_hint"],
                    json.dumps(mission["hard_filters"]),
                    json.dumps(mission["soft_preferences"]),
                    json.dumps(mission["search_config"]),
                    json.dumps(mission["scan_config"]),
                    mission["created_at"],
                    mission["updated_at"],
                    mission["last_scan_at"],
                ),
            )
            self._conn.commit()
        return mission

    def list_missions(self, *, statuses: list[str] | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if statuses:
            normalized = [status for status in statuses if status in MISSION_STATUSES]
            if normalized:
                clauses.append(
                    f"status IN ({','.join('?' for _ in normalized)})"
                )
                params.extend(normalized)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            f"""
            SELECT *
            FROM marketplace_missions
            {where}
            ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,
                     updated_at DESC
            """,
            params,
        )
        return [self._parse_mission_row(row) for row in rows]

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            "SELECT * FROM marketplace_missions WHERE mission_id = ? LIMIT 1",
            (mission_id,),
        )
        return self._parse_mission_row(row) if row else None

    def update_mission(self, mission_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_mission(mission_id)
        if existing is None:
            raise MarketplaceMissionNotFound(mission_id)

        merged = dict(existing)
        for key in (
            "name",
            "status",
            "brief",
            "category_hint",
            "hard_filters",
            "soft_preferences",
            "search_config",
            "scan_config",
        ):
            if key in changes:
                merged[key] = changes[key]

        mission = self._normalize_mission_payload(merged, existing=existing)
        with self._lock:
            self._conn.execute(
                """
                UPDATE marketplace_missions
                SET name = ?, status = ?, brief = ?, category_hint = ?,
                    hard_filters_json = ?, soft_preferences_json = ?,
                    search_config_json = ?, scan_config_json = ?,
                    updated_at = ?, last_scan_at = ?
                WHERE mission_id = ?
                """,
                (
                    mission["name"],
                    mission["status"],
                    mission["brief"],
                    mission["category_hint"],
                    json.dumps(mission["hard_filters"]),
                    json.dumps(mission["soft_preferences"]),
                    json.dumps(mission["search_config"]),
                    json.dumps(mission["scan_config"]),
                    mission["updated_at"],
                    mission["last_scan_at"],
                    mission_id,
                ),
            )
            self._conn.commit()
        return mission

    def mark_last_scan(self, mission_id: str, when: str | None = None) -> None:
        timestamp = _clean_text(when) or _now_iso()
        with self._lock:
            self._conn.execute(
                """
                UPDATE marketplace_missions
                SET last_scan_at = ?, updated_at = ?
                WHERE mission_id = ?
                """,
                (timestamp, timestamp, mission_id),
            )
            self._conn.commit()

    def due_missions(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        current = now or datetime.now(timezone.utc)
        due: list[dict[str, Any]] = []
        for mission in self.list_missions(statuses=["active"]):
            interval_minutes = int(mission["scan_config"]["scan_interval_minutes"])
            last_scan_at = _clean_text(mission.get("last_scan_at"))
            if not last_scan_at:
                due.append(mission)
                continue
            try:
                scanned = datetime.fromisoformat(last_scan_at.replace("Z", "+00:00"))
            except ValueError:
                due.append(mission)
                continue
            if current - scanned >= timedelta(minutes=interval_minutes):
                due.append(mission)
        return due

    # ------------------------------------------------------------------ #
    # Seen listings                                                       #
    # ------------------------------------------------------------------ #

    def get_seen_listing(self, mission_id: str, listing_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT *
            FROM marketplace_seen_listings
            WHERE mission_id = ? AND listing_id = ?
            LIMIT 1
            """,
            (mission_id, listing_id),
        )
        return self._parse_seen_row(row) if row else None

    def upsert_seen_listing(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        listing_id = _clean_text(payload.get("listing_id"))
        listing_url = _clean_text(payload.get("listing_url"))
        if not listing_id or not listing_url:
            raise MarketplaceMissionError("listing_id and listing_url are required")

        existing = self.get_seen_listing(mission_id, listing_id)
        now_iso = _clean_text(payload.get("last_seen_at")) or _now_iso()
        first_seen_at = (
            existing["first_seen_at"]
            if existing is not None
            else _clean_text(payload.get("first_seen_at")) or now_iso
        )
        row = {
            "mission_id": mission_id,
            "listing_id": listing_id,
            "listing_url": listing_url,
            "title": _clean_text(payload.get("title")) or None,
            "price_text": _clean_text(payload.get("price_text")) or None,
            "price_value": _optional_float(payload.get("price_value")),
            "location": _clean_text(payload.get("location")) or None,
            "seller_name": _clean_text(payload.get("seller_name")) or None,
            "query_text": _clean_text(payload.get("query_text")) or None,
            "first_seen_at": first_seen_at,
            "last_seen_at": now_iso,
            "detail_hash": _clean_text(payload.get("detail_hash")) or None,
            "raw_snapshot_json": json.dumps(payload.get("raw_snapshot") or {}),
            "last_status": _clean_text(payload.get("last_status")) or "seen",
            "last_score": _positive_int(payload.get("last_score"), 0)
            if payload.get("last_score") is not None
            else None,
            "last_decision_band": _clean_text(payload.get("last_decision_band")) or None,
            "last_error": _clean_text(payload.get("last_error")) or None,
            "match_id": _clean_text(payload.get("match_id")) or None,
        }

        with self._lock:
            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO marketplace_seen_listings (
                        mission_id, listing_id, listing_url, title, price_text, price_value,
                        location, seller_name, query_text, first_seen_at, last_seen_at,
                        detail_hash, raw_snapshot_json, last_status, last_score,
                        last_decision_band, last_error, match_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["mission_id"],
                        row["listing_id"],
                        row["listing_url"],
                        row["title"],
                        row["price_text"],
                        row["price_value"],
                        row["location"],
                        row["seller_name"],
                        row["query_text"],
                        row["first_seen_at"],
                        row["last_seen_at"],
                        row["detail_hash"],
                        row["raw_snapshot_json"],
                        row["last_status"],
                        row["last_score"],
                        row["last_decision_band"],
                        row["last_error"],
                        row["match_id"],
                    ),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE marketplace_seen_listings
                    SET listing_url = ?, title = ?, price_text = ?, price_value = ?,
                        location = ?, seller_name = ?, query_text = ?, last_seen_at = ?,
                        detail_hash = ?, raw_snapshot_json = ?, last_status = ?,
                        last_score = ?, last_decision_band = ?, last_error = ?, match_id = ?
                    WHERE mission_id = ? AND listing_id = ?
                    """,
                    (
                        row["listing_url"],
                        row["title"],
                        row["price_text"],
                        row["price_value"],
                        row["location"],
                        row["seller_name"],
                        row["query_text"],
                        row["last_seen_at"],
                        row["detail_hash"],
                        row["raw_snapshot_json"],
                        row["last_status"],
                        row["last_score"],
                        row["last_decision_band"],
                        row["last_error"],
                        row["match_id"],
                        mission_id,
                        listing_id,
                    ),
                )
            self._conn.commit()

        result = self.get_seen_listing(mission_id, listing_id)
        if result is None:
            raise MarketplaceMissionError("failed to persist seen listing")
        return result

    def list_seen_prices(self, mission_id: str, *, limit: int = 200) -> list[float]:
        rows = self._fetchall(
            """
            SELECT price_value
            FROM marketplace_seen_listings
            WHERE mission_id = ? AND price_value IS NOT NULL
            ORDER BY last_seen_at DESC
            LIMIT ?
            """,
            (mission_id, limit),
        )
        return [float(row["price_value"]) for row in rows if row["price_value"] is not None]

    def price_band(self, mission_id: str) -> dict[str, float] | None:
        prices = self.list_seen_prices(mission_id)
        if not prices:
            return None
        ordered = sorted(prices)
        return {
            "min": float(ordered[0]),
            "median": float(median(ordered)),
            "max": float(ordered[-1]),
        }

    # ------------------------------------------------------------------ #
    # Matches                                                             #
    # ------------------------------------------------------------------ #

    def list_matches(
        self,
        *,
        mission_id: str | None = None,
        status: str | None = None,
        decision_band: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if mission_id:
            clauses.append("m.mission_id = ?")
            params.append(mission_id)
        if status:
            clauses.append("m.status = ?")
            params.append(status)
        if decision_band:
            clauses.append("m.decision_band = ?")
            params.append(decision_band)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            f"""
            SELECT m.*, mission.name AS mission_name
            FROM marketplace_matches m
            LEFT JOIN marketplace_missions mission
                ON mission.mission_id = m.mission_id
            {where}
            ORDER BY m.captured_at DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        return [self._parse_match_row(row) for row in rows]

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT m.*, mission.name AS mission_name
            FROM marketplace_matches m
            LEFT JOIN marketplace_missions mission
                ON mission.mission_id = m.mission_id
            WHERE m.match_id = ?
            LIMIT 1
            """,
            (match_id,),
        )
        return self._parse_match_row(row) if row else None

    def upsert_match(self, payload: dict[str, Any]) -> dict[str, Any]:
        mission_id = _clean_text(payload.get("mission_id"))
        listing_id = _clean_text(payload.get("listing_id"))
        listing_url = _clean_text(payload.get("listing_url"))
        title = _clean_text(payload.get("title"))
        if not mission_id or not listing_id or not listing_url or not title:
            raise MarketplaceMissionError(
                "mission_id, listing_id, listing_url, and title are required"
            )

        band = _clean_text(payload.get("decision_band")) or "candidate"
        if band not in DECISION_BANDS:
            raise MarketplaceMissionError(f"invalid decision_band: {band}")

        existing = self._fetchone(
            """
            SELECT match_id
            FROM marketplace_matches
            WHERE mission_id = ? AND listing_id = ?
            LIMIT 1
            """,
            (mission_id, listing_id),
        )
        now_iso = _now_iso()
        match_id = (
            _clean_text(existing.get("match_id")) if existing else _new_id("mp_match_")
        )
        row = {
            "match_id": match_id,
            "mission_id": mission_id,
            "listing_id": listing_id,
            "listing_url": listing_url,
            "title": title,
            "price": _clean_text(payload.get("price")) or None,
            "price_value": _optional_float(payload.get("price_value")),
            "location": _clean_text(payload.get("location")) or None,
            "seller_name": _clean_text(payload.get("seller_name")) or None,
            "captured_at": _clean_text(payload.get("captured_at")) or now_iso,
            "score": _positive_int(payload.get("score"), 0),
            "decision_band": band,
            "reasons_for_json": json.dumps(_string_list(payload.get("reasons_for"))),
            "reasons_against_json": json.dumps(
                _string_list(payload.get("reasons_against"))
            ),
            "confidence": _optional_float(payload.get("confidence")),
            "raw_text_snapshot": _clean_text(payload.get("raw_text_snapshot")),
            "screenshot_path": _clean_text(payload.get("screenshot_path")) or None,
            "status": _clean_text(payload.get("status")) or "new",
            "metadata_json": json.dumps(payload.get("metadata") or {}),
            "updated_at": now_iso,
        }
        if row["status"] not in MATCH_STATUSES:
            raise MarketplaceMissionError(f"invalid match status: {row['status']}")
        if not row["raw_text_snapshot"]:
            raise MarketplaceMissionError("raw_text_snapshot is required")

        with self._lock:
            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO marketplace_matches (
                        match_id, mission_id, listing_id, listing_url, title, price,
                        price_value, location, seller_name, captured_at, score,
                        decision_band, reasons_for_json, reasons_against_json,
                        confidence, raw_text_snapshot, screenshot_path, status,
                        metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["match_id"],
                        row["mission_id"],
                        row["listing_id"],
                        row["listing_url"],
                        row["title"],
                        row["price"],
                        row["price_value"],
                        row["location"],
                        row["seller_name"],
                        row["captured_at"],
                        row["score"],
                        row["decision_band"],
                        row["reasons_for_json"],
                        row["reasons_against_json"],
                        row["confidence"],
                        row["raw_text_snapshot"],
                        row["screenshot_path"],
                        row["status"],
                        row["metadata_json"],
                        row["updated_at"],
                    ),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE marketplace_matches
                    SET listing_url = ?, title = ?, price = ?, price_value = ?, location = ?,
                        seller_name = ?, captured_at = ?, score = ?, decision_band = ?,
                        reasons_for_json = ?, reasons_against_json = ?, confidence = ?,
                        raw_text_snapshot = ?, screenshot_path = ?, status = ?,
                        metadata_json = ?, updated_at = ?
                    WHERE match_id = ?
                    """,
                    (
                        row["listing_url"],
                        row["title"],
                        row["price"],
                        row["price_value"],
                        row["location"],
                        row["seller_name"],
                        row["captured_at"],
                        row["score"],
                        row["decision_band"],
                        row["reasons_for_json"],
                        row["reasons_against_json"],
                        row["confidence"],
                        row["raw_text_snapshot"],
                        row["screenshot_path"],
                        row["status"],
                        row["metadata_json"],
                        row["updated_at"],
                        row["match_id"],
                    ),
                )
            self._conn.commit()

        result = self.get_match(match_id)
        if result is None:
            raise MarketplaceMissionError("failed to persist marketplace match")
        return result

    def update_match_status(self, match_id: str, status: str) -> dict[str, Any]:
        normalized = _clean_text(status).lower()
        if normalized not in MATCH_STATUSES:
            raise MarketplaceMissionError(f"invalid match status: {status}")
        with self._lock:
            cur = self._conn.execute(
                """
                UPDATE marketplace_matches
                SET status = ?, updated_at = ?
                WHERE match_id = ?
                """,
                (normalized, _now_iso(), match_id),
            )
            self._conn.commit()
        if cur.rowcount != 1:
            raise MarketplaceMissionNotFound(match_id)
        result = self.get_match(match_id)
        if result is None:
            raise MarketplaceMissionNotFound(match_id)
        return result

    # ------------------------------------------------------------------ #
    # Alerts                                                              #
    # ------------------------------------------------------------------ #

    def create_alert(
        self,
        *,
        mission_id: str,
        match_id: str,
        trigger_reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now_iso = _now_iso()
        alert_id = _new_id("mp_alert_")
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO marketplace_alerts (
                    alert_id, mission_id, match_id, status, created_at,
                    updated_at, trigger_reason, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_id,
                    mission_id,
                    match_id,
                    "new",
                    now_iso,
                    now_iso,
                    _clean_text(trigger_reason) or "strong_match",
                    json.dumps(metadata or {}),
                ),
            )
            self._conn.commit()
        result = self.get_alert(alert_id)
        if result is None:
            raise MarketplaceMissionError("failed to persist marketplace alert")
        return result

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT a.*, m.title AS match_title, m.listing_url, m.price, m.location,
                   m.decision_band, mission.name AS mission_name
            FROM marketplace_alerts a
            JOIN marketplace_matches m ON m.match_id = a.match_id
            LEFT JOIN marketplace_missions mission
                ON mission.mission_id = a.mission_id
            WHERE a.alert_id = ?
            LIMIT 1
            """,
            (alert_id,),
        )
        return self._parse_alert_row(row) if row else None

    def latest_alert_for_match(self, match_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT a.*, m.title AS match_title, m.listing_url, m.price, m.location,
                   m.decision_band, mission.name AS mission_name
            FROM marketplace_alerts a
            JOIN marketplace_matches m ON m.match_id = a.match_id
            LEFT JOIN marketplace_missions mission
                ON mission.mission_id = a.mission_id
            WHERE a.match_id = ?
            ORDER BY a.created_at DESC
            LIMIT 1
            """,
            (match_id,),
        )
        return self._parse_alert_row(row) if row else None

    def list_alerts(
        self,
        *,
        mission_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if mission_id:
            clauses.append("a.mission_id = ?")
            params.append(mission_id)
        if status:
            clauses.append("a.status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            f"""
            SELECT a.*, m.title AS match_title, m.listing_url, m.price, m.location,
                   m.decision_band, mission.name AS mission_name
            FROM marketplace_alerts a
            JOIN marketplace_matches m ON m.match_id = a.match_id
            LEFT JOIN marketplace_missions mission
                ON mission.mission_id = a.mission_id
            {where}
            ORDER BY a.created_at DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        return [self._parse_alert_row(row) for row in rows]

    def update_alert_status(self, alert_id: str, status: str) -> dict[str, Any]:
        normalized = _clean_text(status).lower()
        if normalized not in ALERT_STATUSES:
            raise MarketplaceMissionError(f"invalid alert status: {status}")
        with self._lock:
            cur = self._conn.execute(
                """
                UPDATE marketplace_alerts
                SET status = ?, updated_at = ?
                WHERE alert_id = ?
                """,
                (normalized, _now_iso(), alert_id),
            )
            self._conn.commit()
        if cur.rowcount != 1:
            raise MarketplaceMissionNotFound(alert_id)
        result = self.get_alert(alert_id)
        if result is None:
            raise MarketplaceMissionNotFound(alert_id)
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _normalize_mission_payload(
        self,
        payload: dict[str, Any],
        *,
        existing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now_iso = _now_iso()
        name = _clean_text(payload.get("name"))
        brief = _clean_text(payload.get("brief"))
        status = _clean_text(payload.get("status")).lower() or "active"
        category_hint = _clean_text(payload.get("category_hint")) or None

        if not name:
            raise MarketplaceMissionError("name is required")
        if not brief:
            raise MarketplaceMissionError("brief is required")
        if status not in MISSION_STATUSES:
            raise MarketplaceMissionError(f"invalid mission status: {status}")
        if not _meaningful_brief(brief):
            raise MarketplaceMissionError("brief must include meaningful search intent")

        hard_source = payload.get("hard_filters") or {}
        soft_source = payload.get("soft_preferences") or {}
        search_source = payload.get("search_config") or {}
        scan_source = payload.get("scan_config") or {}

        hard_filters = {
            **DEFAULT_HARD_FILTERS,
            **({k: hard_source.get(k) for k in DEFAULT_HARD_FILTERS} if isinstance(hard_source, dict) else {}),
        }
        soft_preferences = {
            **DEFAULT_SOFT_PREFERENCES,
            **({k: soft_source.get(k) for k in DEFAULT_SOFT_PREFERENCES} if isinstance(soft_source, dict) else {}),
        }
        search_config = {
            **DEFAULT_SEARCH_CONFIG,
            **({k: search_source.get(k) for k in DEFAULT_SEARCH_CONFIG} if isinstance(search_source, dict) else {}),
        }
        scan_config = {
            **DEFAULT_SCAN_CONFIG,
            **({k: scan_source.get(k) for k in DEFAULT_SCAN_CONFIG} if isinstance(scan_source, dict) else {}),
        }

        hard_filters["include_keywords"] = _string_list(hard_filters.get("include_keywords"))
        hard_filters["exclude_keywords"] = _string_list(hard_filters.get("exclude_keywords"))
        hard_filters["location_names"] = _string_list(hard_filters.get("location_names"))
        hard_filters["condition_required"] = _string_list(hard_filters.get("condition_required"))
        hard_filters["required_terms"] = _string_list(hard_filters.get("required_terms"))
        hard_filters["forbidden_terms"] = _string_list(hard_filters.get("forbidden_terms"))
        hard_filters["price_min"] = _optional_float(hard_filters.get("price_min"))
        hard_filters["price_max"] = _optional_float(hard_filters.get("price_max"))
        hard_filters["radius_km"] = _optional_float(hard_filters.get("radius_km"))

        soft_preferences["preferred_brands"] = _string_list(
            soft_preferences.get("preferred_brands")
        )
        soft_preferences["preferred_suburbs"] = _string_list(
            soft_preferences.get("preferred_suburbs")
        )
        soft_preferences["preferred_condition_terms"] = _string_list(
            soft_preferences.get("preferred_condition_terms")
        )
        soft_preferences["nice_to_have_terms"] = _string_list(
            soft_preferences.get("nice_to_have_terms")
        )
        soft_preferences["negotiation_expected"] = _bool(
            soft_preferences.get("negotiation_expected")
        )

        urgency = _clean_text(soft_preferences.get("urgency")).lower() or "normal"
        if urgency not in {"low", "normal", "high"}:
            raise MarketplaceMissionError(f"invalid urgency: {urgency}")
        soft_preferences["urgency"] = urgency

        aggressiveness = (
            _clean_text(soft_preferences.get("price_aggressiveness")).lower()
            or "balanced"
        )
        if aggressiveness not in {"conservative", "balanced", "aggressive"}:
            raise MarketplaceMissionError(
                f"invalid price_aggressiveness: {aggressiveness}"
            )
        soft_preferences["price_aggressiveness"] = aggressiveness

        search_config["query_variants_enabled"] = _bool(
            search_config.get("query_variants_enabled")
        )
        search_config["broadening_enabled"] = _bool(
            search_config.get("broadening_enabled")
        )
        search_config["max_queries_per_run"] = _positive_int(
            search_config.get("max_queries_per_run"),
            DEFAULT_SEARCH_CONFIG["max_queries_per_run"],
        )

        scan_config["scan_interval_minutes"] = _positive_int(
            scan_config.get("scan_interval_minutes"),
            DEFAULT_SCAN_CONFIG["scan_interval_minutes"],
        )
        scan_config["candidate_card_target"] = _positive_int(
            scan_config.get("candidate_card_target"),
            DEFAULT_SCAN_CONFIG["candidate_card_target"],
        )
        scan_config["detail_open_target"] = _positive_int(
            scan_config.get("detail_open_target"),
            DEFAULT_SCAN_CONFIG["detail_open_target"],
        )
        scan_config["run_time_budget_minutes"] = _positive_int(
            scan_config.get("run_time_budget_minutes"),
            DEFAULT_SCAN_CONFIG["run_time_budget_minutes"],
        )
        scan_config["strong_match_threshold"] = _positive_int(
            scan_config.get("strong_match_threshold"),
            DEFAULT_SCAN_CONFIG["strong_match_threshold"],
        )
        scan_config["candidate_threshold"] = _positive_int(
            scan_config.get("candidate_threshold"),
            DEFAULT_SCAN_CONFIG["candidate_threshold"],
        )
        scan_config["aggressive_alerting"] = _bool(
            scan_config.get("aggressive_alerting")
        )

        if (
            hard_filters["price_min"] is not None
            and hard_filters["price_max"] is not None
            and hard_filters["price_min"] > hard_filters["price_max"]
        ):
            raise MarketplaceMissionError("price_min cannot exceed price_max")
        if scan_config["candidate_threshold"] >= scan_config["strong_match_threshold"]:
            raise MarketplaceMissionError(
                "candidate_threshold must be lower than strong_match_threshold"
            )
        if not hard_filters["include_keywords"] and not _meaningful_brief(brief):
            raise MarketplaceMissionError(
                "mission requires include_keywords or a meaningful brief"
            )

        return {
            "mission_id": _clean_text(payload.get("mission_id"))
            or (existing or {}).get("mission_id")
            or _new_id("mp_mission_"),
            "name": name,
            "status": status,
            "brief": brief,
            "category_hint": category_hint,
            "hard_filters": hard_filters,
            "soft_preferences": soft_preferences,
            "search_config": search_config,
            "scan_config": scan_config,
            "created_at": (existing or {}).get("created_at") or now_iso,
            "updated_at": now_iso,
            "last_scan_at": (existing or {}).get("last_scan_at"),
        }

    def _fetchone(self, sql: str, params: tuple[Any, ...] | list[Any]) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _fetchall(self, sql: str, params: tuple[Any, ...] | list[Any]) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _parse_mission_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "hard_filters": json.loads(row.pop("hard_filters_json")),
            "soft_preferences": json.loads(row.pop("soft_preferences_json")),
            "search_config": json.loads(row.pop("search_config_json")),
            "scan_config": json.loads(row.pop("scan_config_json")),
        }

    @staticmethod
    def _parse_seen_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "raw_snapshot": json.loads(row.pop("raw_snapshot_json")),
        }

    @staticmethod
    def _parse_match_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "reasons_for": json.loads(row.pop("reasons_for_json")),
            "reasons_against": json.loads(row.pop("reasons_against_json")),
            "metadata": json.loads(row.pop("metadata_json")),
        }

    @staticmethod
    def _parse_alert_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "metadata": json.loads(row.pop("metadata_json")),
        }
