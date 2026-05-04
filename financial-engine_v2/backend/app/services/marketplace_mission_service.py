from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from cockpit.storage.state import StateStore

from app.services.marketplace_requirement_resolver import build_requirement_profile


MISSION_STATUSES = {"active", "paused", "archived"}
MISSION_TYPES = {
    "find_good_deals",
    "benchmark_listings",
    "refresh_retail_benchmarks",
    "review_uncertain_matches",
}
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
_LOCATION_CLAUSE_RE = re.compile(
    r"\blocations?\s*(?:i\s*(?:want|prefer)|to\s*use)?\s*:\s*([^.;\n]+)",
    re.IGNORECASE,
)
_LOCATION_INLINE_RE = re.compile(
    r"\b(?:around|near|in)\s+([a-z][a-z0-9\s,\-/]{2,})",
    re.IGNORECASE,
)
_LOCATION_STOP_RE = re.compile(
    r"\b(?:under|over|with|for|budget|max(?:imum)?|ideally|deal-breakers?|must-have|nice-to-have|brands?)\b",
    re.IGNORECASE,
)
_CANONICAL_LOCATION_MAP = {
    "victoria": "Victoria, Australia",
    "vic": "Victoria, Australia",
}


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


def _media_url_list(value: Any) -> list[str]:
    urls = _string_list(value)
    out: list[str] = []
    seen: set[str] = set()
    for item in urls:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        if not re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= 12:
            break
    return out


def _safe_json_loads(raw: Any, fallback: Any) -> Any:
    if not isinstance(raw, str) or not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


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


def _brief_location_names(brief: str) -> list[str]:
    text = _clean_text(brief)
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()

    def _append_location(candidate: str) -> None:
        cleaned = _clean_text(candidate)
        if not cleaned:
            return
        cleaned = _LOCATION_STOP_RE.split(cleaned, maxsplit=1)[0].strip(" ,.-")
        if not cleaned or re.search(r"\d", cleaned):
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(cleaned)

    for match in _LOCATION_CLAUSE_RE.finditer(text):
        clause = _clean_text(match.group(1))
        parts = re.split(r",|/|\band\b", clause, flags=re.IGNORECASE)
        for part in parts:
            _append_location(part)

    for match in _LOCATION_INLINE_RE.finditer(text):
        _append_location(match.group(1))

    return normalize_marketplace_location_names(out[:4])


def normalize_marketplace_location_names(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        canonical = _CANONICAL_LOCATION_MAP.get(cleaned.lower(), cleaned)
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(canonical)
    if len(out) > 1:
        out = [item for item in out if item.lower() != "australia"] or out
    return out


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
                    scan_config_json, mission_type, user_goal,
                    benchmark_sources_json, deployment_args_json, last_error,
                    created_from_chat_message_id, created_at, updated_at, last_scan_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    mission["mission_type"],
                    mission["user_goal"],
                    json.dumps(mission["benchmark_sources"]),
                    json.dumps(mission["deployment_args"]),
                    mission["last_error"],
                    mission["created_from_chat_message_id"],
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
            "mission_type",
            "brief",
            "user_goal",
            "category_hint",
            "hard_filters",
            "soft_preferences",
            "search_config",
            "scan_config",
            "benchmark_sources",
            "deployment_args",
            "last_error",
            "created_from_chat_message_id",
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
                    mission_type = ?, user_goal = ?, benchmark_sources_json = ?,
                    deployment_args_json = ?, last_error = ?, created_from_chat_message_id = ?,
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
                    mission["mission_type"],
                    mission["user_goal"],
                    json.dumps(mission["benchmark_sources"]),
                    json.dumps(mission["deployment_args"]),
                    mission["last_error"],
                    mission["created_from_chat_message_id"],
                    mission["updated_at"],
                    mission["last_scan_at"],
                    mission_id,
                ),
            )
            self._conn.commit()
        return mission

    def get_primary_tracked_product_link(self, mission_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT mission_id, tracked_product_id, link_type, created_at, updated_at
            FROM marketplace_mission_product_links
            WHERE mission_id = ? AND link_type = 'primary'
            LIMIT 1
            """,
            (mission_id,),
        )
        return row

    def link_primary_tracked_product(
        self, mission_id: str, tracked_product_id: str
    ) -> dict[str, Any]:
        if self.get_mission(mission_id) is None:
            raise MarketplaceMissionNotFound(mission_id)
        product_id = _clean_text(tracked_product_id)
        if not product_id:
            raise MarketplaceMissionError("tracked_product_id is required")
        now_iso = _now_iso()
        with self._lock:
            existing = self._conn.execute(
                """
                SELECT created_at
                FROM marketplace_mission_product_links
                WHERE mission_id = ? AND link_type = 'primary'
                LIMIT 1
                """,
                (mission_id,),
            ).fetchone()
            self._conn.execute(
                """
                INSERT OR REPLACE INTO marketplace_mission_product_links (
                    mission_id, tracked_product_id, link_type, created_at, updated_at
                )
                VALUES (?, ?, 'primary', ?, ?)
                """,
                (
                    mission_id,
                    product_id,
                    str(existing["created_at"]) if existing else now_iso,
                    now_iso,
                ),
            )
            self._conn.commit()
        link = self.get_primary_tracked_product_link(mission_id)
        if link is None:
            raise MarketplaceMissionError("failed to persist mission product link")
        return link

    def unlink_primary_tracked_product(self, mission_id: str) -> dict[str, Any] | None:
        if self.get_mission(mission_id) is None:
            raise MarketplaceMissionNotFound(mission_id)
        existing = self.get_primary_tracked_product_link(mission_id)
        with self._lock:
            self._conn.execute(
                """
                DELETE FROM marketplace_mission_product_links
                WHERE mission_id = ? AND link_type = 'primary'
                """,
                (mission_id,),
            )
            self._conn.commit()
        return existing

    def replace_mission_candidate_products(
        self,
        mission_id: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if self.get_mission(mission_id) is None:
            raise MarketplaceMissionNotFound(mission_id)
        now_iso = _now_iso()
        with self._lock:
            self._conn.execute(
                "DELETE FROM marketplace_mission_candidate_products WHERE mission_id = ?",
                (mission_id,),
            )
            for index, candidate in enumerate(candidates):
                tracked_product_id = _clean_text(candidate.get("tracked_product_id"))
                candidate_key = _clean_text(candidate.get("candidate_key"))
                category = _clean_text(candidate.get("category")).lower()
                if not tracked_product_id or not candidate_key or not category:
                    continue
                self._conn.execute(
                    """
                    INSERT INTO marketplace_mission_candidate_products (
                        mission_id, tracked_product_id, candidate_key, category,
                        candidate_rank, fit_score, fit_label, hard_constraints_json,
                        soft_preferences_json, explanation, created_at, updated_at
                    )
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        mission_id,
                        tracked_product_id,
                        candidate_key,
                        category,
                        int(candidate.get("candidate_rank") or index + 1),
                        float(candidate.get("fit_score") or 0.0),
                        _clean_text(candidate.get("fit_label")) or "fit",
                        json.dumps(candidate.get("hard_constraints_met") or []),
                        json.dumps(candidate.get("soft_preferences_met") or []),
                        _clean_text(candidate.get("explanation")) or None,
                        now_iso,
                        now_iso,
                    ),
                )
            self._conn.commit()
        return self.list_mission_candidate_products(mission_id)

    def list_mission_candidate_products(self, mission_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            """
            SELECT *
            FROM marketplace_mission_candidate_products
            WHERE mission_id = ?
            ORDER BY candidate_rank ASC, updated_at DESC
            """,
            (mission_id,),
        )
        return [self._parse_candidate_product_row(row) for row in rows]

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

    def delete_mission(self, mission_id: str) -> dict[str, Any]:
        existing = self.get_mission(mission_id)
        if existing is None:
            raise MarketplaceMissionNotFound(mission_id)

        with self._lock:
            match_rows = self._conn.execute(
                """
                SELECT match_id
                FROM marketplace_matches
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchall()
            match_ids = [str(row["match_id"]) for row in match_rows if row["match_id"]]

            deleted_benchmark_scores = 0
            deleted_listing_matches = 0
            deleted_value_assessments = 0
            deleted_match_feedback = 0
            if match_ids:
                placeholders = ",".join("?" for _ in match_ids)
                cur_scores = self._conn.execute(
                    f"""
                    DELETE FROM listing_benchmark_scores
                    WHERE match_id IN ({placeholders})
                    """,
                    match_ids,
                )
                deleted_benchmark_scores = max(cur_scores.rowcount, 0)
                cur_listing_matches = self._conn.execute(
                    f"""
                    DELETE FROM listing_product_matches
                    WHERE match_id IN ({placeholders})
                    """,
                    match_ids,
                )
                deleted_listing_matches = max(cur_listing_matches.rowcount, 0)
                cur_value_assessments = self._conn.execute(
                    f"""
                    DELETE FROM marketplace_match_value_assessments
                    WHERE match_id IN ({placeholders})
                    """,
                    match_ids,
                )
                deleted_value_assessments = max(cur_value_assessments.rowcount, 0)
                cur_match_feedback = self._conn.execute(
                    f"""
                    DELETE FROM marketplace_match_feedback
                    WHERE match_id IN ({placeholders})
                    """,
                    match_ids,
                )
                deleted_match_feedback = max(cur_match_feedback.rowcount, 0)

            cur_alerts = self._conn.execute(
                "DELETE FROM marketplace_alerts WHERE mission_id = ?",
                (mission_id,),
            )
            deleted_alerts = max(cur_alerts.rowcount, 0)
            cur_links = self._conn.execute(
                "DELETE FROM marketplace_mission_product_links WHERE mission_id = ?",
                (mission_id,),
            )
            deleted_links = max(cur_links.rowcount, 0)
            cur_candidates = self._conn.execute(
                "DELETE FROM marketplace_mission_candidate_products WHERE mission_id = ?",
                (mission_id,),
            )
            deleted_candidates = max(cur_candidates.rowcount, 0)
            cur_matches = self._conn.execute(
                "DELETE FROM marketplace_matches WHERE mission_id = ?",
                (mission_id,),
            )
            deleted_matches = max(cur_matches.rowcount, 0)
            cur_seen = self._conn.execute(
                "DELETE FROM marketplace_seen_listings WHERE mission_id = ?",
                (mission_id,),
            )
            deleted_seen = max(cur_seen.rowcount, 0)
            cur_missions = self._conn.execute(
                "DELETE FROM marketplace_missions WHERE mission_id = ?",
                (mission_id,),
            )
            if cur_missions.rowcount != 1:
                self._conn.rollback()
                raise MarketplaceMissionNotFound(mission_id)
            self._conn.commit()

        return {
            "mission_id": mission_id,
            "deleted_missions": 1,
            "deleted_seen_listings": deleted_seen,
            "deleted_matches": deleted_matches,
            "deleted_alerts": deleted_alerts,
            "deleted_listing_product_matches": deleted_listing_matches,
            "deleted_listing_benchmark_scores": deleted_benchmark_scores,
            "deleted_mission_product_links": deleted_links,
            "deleted_mission_candidate_products": deleted_candidates,
            "deleted_match_value_assessments": deleted_value_assessments,
            "deleted_match_feedback": deleted_match_feedback,
        }

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
            SELECT s.price_value
            FROM marketplace_seen_listings s
            JOIN marketplace_matches m ON m.match_id = s.match_id
            WHERE s.mission_id = ?
              AND s.price_value IS NOT NULL
              AND m.status != 'dismissed'
              AND m.decision_band IN ('candidate', 'strong_match')
            ORDER BY s.last_seen_at DESC
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
        else:
            clauses.append("m.status != ?")
            params.append("dismissed")
        if decision_band:
            clauses.append("m.decision_band = ?")
            params.append(decision_band)
        else:
            clauses.append("m.decision_band != ?")
            params.append("reject")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._fetchall(
            f"""
            SELECT m.*, mission.name AS mission_name, mission.category_hint AS mission_category_hint
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
            SELECT m.*, mission.name AS mission_name, mission.category_hint AS mission_category_hint
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
            SELECT match_id, listing_media_json
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
        listing_media_payload = (
            payload.get("listing_media")
            if "listing_media" in payload
            else payload.get("listing_photo_urls")
            if "listing_photo_urls" in payload
            else payload.get("listing_images")
            if "listing_images" in payload
            else None
        )
        if listing_media_payload is None and existing:
            listing_media_payload = _safe_json_loads(
                existing.get("listing_media_json"),
                [],
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
            "listing_media_json": json.dumps(
                _media_url_list(listing_media_payload)
            ),
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
                        confidence, raw_text_snapshot, screenshot_path, listing_media_json,
                        status, metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        row["listing_media_json"],
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
                        raw_text_snapshot = ?, screenshot_path = ?, listing_media_json = ?,
                        status = ?, metadata_json = ?, updated_at = ?
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
                        row["listing_media_json"],
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

    def list_not_interested_feedback_notes(self, mission_id: str) -> list[str]:
        rows = self._fetchall(
            """
            SELECT f.note
            FROM marketplace_match_feedback f
            JOIN marketplace_matches m ON m.match_id = f.match_id
            WHERE m.mission_id = ?
              AND f.feedback = 'not_interested'
              AND f.note IS NOT NULL
              AND trim(f.note) != ''
            ORDER BY f.updated_at DESC
            LIMIT 50
            """,
            (str(mission_id or "").strip(),),
        )
        return [str(row["note"]).strip() for row in rows if row.get("note")]

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
        mission_type = _clean_text(payload.get("mission_type")).lower() or "find_good_deals"
        category_hint = _clean_text(payload.get("category_hint")) or None
        user_goal = _clean_text(payload.get("user_goal")) or brief
        benchmark_sources = _string_list(payload.get("benchmark_sources")) or ["centre_com"]
        deployment_args = (
            payload.get("deployment_args")
            if isinstance(payload.get("deployment_args"), dict)
            else {}
        )
        last_error = _clean_text(payload.get("last_error")) or None
        created_from_chat_message_id = (
            _clean_text(payload.get("created_from_chat_message_id")) or None
        )

        if not name:
            raise MarketplaceMissionError("name is required")
        if not brief:
            raise MarketplaceMissionError("brief is required")
        if status not in MISSION_STATUSES:
            raise MarketplaceMissionError(f"invalid mission status: {status}")
        if mission_type not in MISSION_TYPES:
            raise MarketplaceMissionError(f"invalid mission_type: {mission_type}")
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
        hard_filters["location_names"] = normalize_marketplace_location_names(
            _string_list(hard_filters.get("location_names"))
        )
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

        if not hard_filters["location_names"]:
            hard_filters["location_names"] = (
                _string_list(soft_preferences.get("preferred_suburbs"))
                or _brief_location_names(brief)
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
        if not hard_filters["location_names"]:
            raise MarketplaceMissionError(
                "mission requires at least one location (hard_filters.location_names)"
            )

        requirement_profile = build_requirement_profile(
            {
                "name": name,
                "brief": brief,
                "user_goal": user_goal,
                "category_hint": category_hint,
                "hard_filters": hard_filters,
                "soft_preferences": soft_preferences,
            }
        )
        deployment_args = {
            **deployment_args,
            "requirement_profile": requirement_profile,
        }

        return {
            "mission_id": _clean_text(payload.get("mission_id"))
            or (existing or {}).get("mission_id")
            or _new_id("mp_mission_"),
            "name": name,
            "status": status,
            "mission_type": mission_type,
            "brief": brief,
            "user_goal": user_goal,
            "category_hint": category_hint,
            "hard_filters": hard_filters,
            "soft_preferences": soft_preferences,
            "search_config": search_config,
            "scan_config": scan_config,
            "benchmark_sources": benchmark_sources,
            "deployment_args": deployment_args,
            "last_error": last_error,
            "created_from_chat_message_id": created_from_chat_message_id,
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
        deployment_args = json.loads(row.pop("deployment_args_json") or "{}")
        requirement_profile = (
            deployment_args.get("requirement_profile")
            if isinstance(deployment_args, dict)
            else None
        )
        return {
            **row,
            "hard_filters": json.loads(row.pop("hard_filters_json")),
            "soft_preferences": json.loads(row.pop("soft_preferences_json")),
            "search_config": json.loads(row.pop("search_config_json")),
            "scan_config": json.loads(row.pop("scan_config_json")),
            "benchmark_sources": json.loads(
                row.pop("benchmark_sources_json") or "[\"centre_com\"]"
            ),
            "deployment_args": deployment_args,
            "requirement_profile": requirement_profile,
        }

    @staticmethod
    def _parse_candidate_product_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "hard_constraints_met": json.loads(row.pop("hard_constraints_json") or "[]"),
            "soft_preferences_met": json.loads(row.pop("soft_preferences_json") or "[]"),
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
            "listing_media": json.loads(row.pop("listing_media_json", "[]") or "[]"),
            "metadata": json.loads(row.pop("metadata_json")),
        }

    @staticmethod
    def _parse_alert_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "metadata": json.loads(row.pop("metadata_json")),
        }
