from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any
from urllib.parse import urlparse

from app.services.commentary_decay import compute_recency_decay
from cockpit.storage.state import StateStore


PRODUCT_CATEGORIES = {"gpu", "cpu", "ram", "ssd"}
PRODUCT_STATUSES = {"active", "inactive"}
OBSERVATION_REVIEW_STATES = {"pending_review", "accepted", "rejected"}
CAPTURE_MODES = {"manual", "scanner", "test_seed", "future_adapter"}
VALUE_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _lower(value: Any) -> str:
    return _clean(value).lower()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _json_loads(value: Any, fallback: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", str(value))
    if match is None:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _identity_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if isinstance(value, list | tuple | set):
            tokens.update(_identity_tokens(*value))
            continue
        for token in re.findall(r"[a-z0-9]+", _lower(value)):
            if len(token) <= 1 and not token.isdigit():
                continue
            if token in {"and", "with", "for", "the", "new", "used", "good"}:
                continue
            tokens.add(token)
    return tokens


def _retail_anchor_price(retail_anchor: dict[str, Any]) -> float | None:
    for key in (
        "retail_anchor_price",
        "price",
        "current_price",
        "centre_com_price",
        "amount",
    ):
        parsed = _parse_price(retail_anchor.get(key))
        if parsed is not None:
            return parsed
    return None


def _retail_anchor_label(retail_anchor: dict[str, Any]) -> str | None:
    for key in ("label", "anchor_label", "source", "retailer", "retailer_name"):
        value = _clean(retail_anchor.get(key))
        if value:
            return value
    return None


def _price_delta(listing_price: float | None, anchor_price: float | None) -> dict[str, Any]:
    if listing_price is None or anchor_price is None or anchor_price <= 0:
        return {"amount": None, "percent": None}
    amount = listing_price - anchor_price
    return {
        "amount": round(amount, 2),
        "percent": round((amount / anchor_price) * 100, 1),
    }


def _value_label(score: float | None) -> str:
    if score is None:
        return "unclear"
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 50:
        return "fair"
    return "weak"


def _parse_capacity_gb(text: str) -> int | None:
    tb = re.search(r"\b(\d+(?:\.\d+)?)\s*tb\b", text, flags=re.IGNORECASE)
    if tb:
        return int(float(tb.group(1)) * 1000)
    gb = re.search(r"\b(\d{1,5})\s*gb\b", text, flags=re.IGNORECASE)
    if gb:
        return int(gb.group(1))
    return None


def _parse_observed_at(value: Any) -> datetime:
    text = _clean(value)
    if not text:
        return _now()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return _now()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _to_iso(value: Any) -> str:
    return _parse_observed_at(value).replace(microsecond=0).isoformat()


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return float(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)


def _weighted_percentile(data: list[tuple[float, float]], pct: float) -> float | None:
    """Compute weighted percentile from a list of (value, weight) pairs."""
    if not data:
        return None
    # data is list of (value, weight)
    sorted_data = sorted(data, key=lambda x: x[0])
    total_weight = sum(w for v, w in sorted_data)
    if total_weight <= 0:
        return float(sorted_data[0][0])

    target_weight = total_weight * pct
    current_weight = 0.0
    for value, weight in sorted_data:
        current_weight += weight
        if current_weight >= target_weight:
            return float(value)
    return float(sorted_data[-1][0])


def detect_listing_junk(
    *,
    title: str,
    price: float | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    text = f" {_lower(title)} "
    flags: list[str] = []
    checks = {
        "wanted": r"\b(wanted|wtb|want to buy|looking for)\b",
        "swap_trade": r"\b(swap|trade|trade only|swap only)\b",
        "broken_parts": r"\b(broken|faulty|for parts|parts only|not working|dead gpu|dead cpu)\b",
        "box_only": r"\b(box only|empty box|packaging only|accessory only|bracket only|cable only)\b",
        "bundle_full_build": r"\b(full build|gaming pc|complete pc|bundle|whole setup)\b",
    }
    for name, pattern in checks.items():
        if re.search(pattern, text):
            flags.append(name)

    if price is not None and price <= 5:
        flags.append("placeholder_price")
    if re.search(r"\b(123456|999999|111111)\b", text):
        flags.append("placeholder_price")
    if category in {"gpu", "cpu", "ram", "ssd"} and re.search(
        r"\b(photo|picture|wallpaper|keyring|sticker)\b", text
    ):
        flags.append("accessory_only")

    return {"is_junk": bool(flags), "flags": sorted(set(flags))}


def normalize_product_text(category: str, text: str) -> dict[str, Any]:
    category = _lower(category)
    if category not in PRODUCT_CATEGORIES:
        raise ValueError(f"unsupported product category: {category}")
    cleaned = _clean(text)
    lowered = cleaned.lower()
    attributes: dict[str, Any] = {}

    if category == "gpu":
        if re.search(r"\brtx\b|\bgtx\b|\bnvidia\b|\bgeforce\b", lowered):
            attributes["vendor"] = "NVIDIA"
        elif re.search(r"\bradeon\b|\brx\b|\bamd\b", lowered):
            attributes["vendor"] = "AMD"
        match = re.search(r"\b(rtx|gtx)\s*([2345]0[0-9]{2})\b", lowered)
        if match:
            attributes["generation"] = match.group(2)[0] + "0"
            attributes["chip_model"] = f"{match.group(1).upper()} {match.group(2)}"
            modifiers = re.findall(r"\b(ti|super)\b", lowered)
            if modifiers:
                attributes["suffix"] = " ".join(mod.upper() for mod in modifiers)
        amd = re.search(r"\brx\s*([5679][0-9]{3})(?:\s*(xtx|xt))?\b", lowered)
        if amd:
            attributes["generation"] = amd.group(1)[0] + "000"
            attributes["chip_model"] = f"RX {amd.group(1)}"
            if amd.group(2):
                attributes["suffix"] = amd.group(2).upper()
        vram = re.search(r"\b(\d{1,2})\s*gb\b", lowered)
        if vram:
            attributes["vram_gb"] = int(vram.group(1))

    elif category == "cpu":
        ryzen = re.search(r"\bryzen\s*([3579])\s*([0-9]{4})([a-z0-9]*)\b", lowered)
        intel = re.search(r"\b(?:core\s*)?i([3579])[-\s]*([0-9]{4,5})([a-z]*)\b", lowered)
        if ryzen:
            attributes["vendor"] = "AMD"
            attributes["family"] = f"Ryzen {ryzen.group(1)}"
            attributes["generation"] = ryzen.group(2)[0] + "000"
            attributes["exact_sku"] = f"Ryzen {ryzen.group(1)} {ryzen.group(2)}{ryzen.group(3).upper()}"
            if ryzen.group(3):
                attributes["suffix"] = ryzen.group(3).upper()
        elif intel:
            attributes["vendor"] = "Intel"
            attributes["family"] = f"Core i{intel.group(1)}"
            attributes["generation"] = intel.group(2)[:2] if len(intel.group(2)) == 5 else intel.group(2)[0]
            attributes["exact_sku"] = f"i{intel.group(1)}-{intel.group(2)}{intel.group(3).upper()}"
            if intel.group(3):
                attributes["suffix"] = intel.group(3).upper()

    elif category == "ram":
        ddr = re.search(r"\bddr\s*([345])\b", lowered)
        if ddr:
            attributes["ddr_generation"] = int(ddr.group(1))
        kit = re.search(r"\b(\d)\s*x\s*(\d{1,3})\s*gb\b", lowered)
        if kit:
            attributes["stick_count"] = int(kit.group(1))
            attributes["total_capacity_gb"] = int(kit.group(1)) * int(kit.group(2))
        else:
            capacity = _parse_capacity_gb(lowered)
            if capacity is not None:
                attributes["total_capacity_gb"] = capacity
        speed = re.search(r"\b(?:ddr[345][- ]?)?(\d{4,5})\s*(?:mhz)?\b", lowered)
        if speed:
            attributes["speed_mhz"] = int(speed.group(1))
        cas = re.search(r"\bcl\s*([0-9]{2})\b", lowered)
        if cas:
            attributes["cas_latency"] = int(cas.group(1))

    elif category == "ssd":
        capacity = _parse_capacity_gb(lowered)
        if capacity is not None:
            attributes["capacity_gb"] = capacity
        if re.search(r"\bnvme\b|\bm\.?2\b", lowered):
            attributes["interface"] = "NVMe"
        elif re.search(r"\bsata\b", lowered):
            attributes["interface"] = "SATA"
        gen = re.search(r"\bgen\s*([345])\b|\bpcie\s*([345])(?:\.0)?\b", lowered)
        if gen:
            attributes["pcie_generation"] = int(gen.group(1) or gen.group(2))
        brand = re.search(r"\b(samsung|wd|western digital|crucial|kingston|seagate|lexar|solidigm)\b", lowered)
        if brand:
            attributes["brand"] = "WD" if brand.group(1) == "western digital" else brand.group(1).title()
        model = re.search(r"\b(9[789]0\s*pro|sn[0-9]{3,4}x?|p[0-9]\s*plus|mx500|kc3000|firecuda\s*[0-9]+)\b", lowered)
        if model:
            attributes["model"] = _clean(model.group(1)).upper()

    identity_parts = [
        category,
        str(attributes.get("vendor") or attributes.get("brand") or ""),
        str(attributes.get("chip_model") or attributes.get("exact_sku") or attributes.get("model") or ""),
        str(attributes.get("suffix") or ""),
        str(attributes.get("vram_gb") or attributes.get("total_capacity_gb") or attributes.get("capacity_gb") or ""),
    ]
    canonical_key = re.sub(r"[^a-z0-9]+", "-", " ".join(identity_parts).lower()).strip("-")
    return {
        "category": category,
        "input": cleaned,
        "canonical_key": canonical_key or re.sub(r"[^a-z0-9]+", "-", cleaned.lower()).strip("-"),
        "attributes": attributes,
    }


def listing_fingerprint(
    *,
    source: str,
    source_listing_id: str | None = None,
    url: str | None = None,
    title: str | None = None,
    price: float | None = None,
    location: str | None = None,
) -> str:
    source_key = _lower(source) or "unknown"
    listing_id = _lower(source_listing_id)
    if listing_id:
        basis = f"{source_key}|id|{listing_id}"
    else:
        parsed = urlparse(_clean(url))
        normalized_url = ""
        if parsed.netloc and parsed.path:
            normalized_url = f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
        if normalized_url:
            basis = f"{source_key}|url|{normalized_url}"
        else:
            price_key = "" if price is None else f"{float(price):.2f}"
            basis = f"{source_key}|text|{_lower(title)}|{price_key}|{_lower(location)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class BenchmarkRollup:
    sample_size: int
    median_price: float | None
    fair_range_low: float | None
    fair_range_high: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "median_price": self.median_price,
            "fair_range_low": self.fair_range_low,
            "fair_range_high": self.fair_range_high,
        }


class MarketplacePriceIntelligenceService:
    """Standalone cockpit-local used-market price intelligence foundation."""

    def __init__(self, state_store: StateStore) -> None:
        self._state_store = state_store
        self._conn = state_store.conn
        self._lock = state_store._lock
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_tracked_products (
                    tracked_product_id TEXT PRIMARY KEY,
                    canonical_key TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    brand TEXT,
                    model_family TEXT,
                    variant TEXT,
                    attributes_json TEXT NOT NULL DEFAULT '{}',
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    negative_terms_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_marketplace_tracked_products_category "
                "ON marketplace_tracked_products(category, status)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_price_observations (
                    observation_id TEXT PRIMARY KEY,
                    tracked_product_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    source_listing_id TEXT,
                    listing_fingerprint TEXT NOT NULL,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'AUD',
                    url TEXT,
                    location TEXT,
                    seller_type TEXT,
                    condition_label TEXT,
                    match_confidence REAL,
                    is_transactional INTEGER DEFAULT 0,
                    capture_mode TEXT NOT NULL DEFAULT 'manual',
                    provenance_json TEXT NOT NULL DEFAULT '{}',
                    review_state TEXT NOT NULL DEFAULT 'pending_review',
                    review_reason TEXT,
                    junk_flags_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_marketplace_price_obs_product "
                "ON marketplace_price_observations(tracked_product_id, observed_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_marketplace_price_obs_fingerprint "
                "ON marketplace_price_observations(listing_fingerprint, observed_at DESC)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_listing_timelines (
                    listing_fingerprint TEXT PRIMARY KEY,
                    tracked_product_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    latest_price REAL NOT NULL,
                    price_history_json TEXT NOT NULL DEFAULT '[]',
                    price_change_count INTEGER NOT NULL DEFAULT 0,
                    active_state TEXT NOT NULL DEFAULT 'active',
                    latest_observation_id TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_marketplace_listing_timelines_product "
                "ON marketplace_listing_timelines(tracked_product_id, last_seen DESC)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_benchmark_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    tracked_product_id TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    total_sample_size INTEGER NOT NULL,
                    source_sample_sizes_json TEXT NOT NULL DEFAULT '{}',
                    rollups_json TEXT NOT NULL DEFAULT '{}',
                    fair_range_low REAL,
                    fair_range_high REAL,
                    used_median REAL,
                    retail_anchor_json TEXT NOT NULL DEFAULT '{}',
                    freshness_status TEXT NOT NULL,
                    confidence_label TEXT NOT NULL,
                    notes_json TEXT NOT NULL DEFAULT '[]',
                    warnings_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_marketplace_benchmark_snapshots_product "
                "ON marketplace_benchmark_snapshots(tracked_product_id, generated_at DESC)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_observation_review_history (
                    review_id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT,
                    reviewed_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marketplace_match_value_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    match_id TEXT NOT NULL UNIQUE,
                    mission_id TEXT,
                    tracked_product_id TEXT,
                    benchmark_snapshot_id TEXT,
                    value_state TEXT NOT NULL,
                    value_score REAL,
                    value_label TEXT NOT NULL,
                    value_confidence TEXT NOT NULL,
                    assessment_json TEXT NOT NULL DEFAULT '{}',
                    computed_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_marketplace_match_value_assessments_mission "
                "ON marketplace_match_value_assessments(mission_id, tracked_product_id)"
            )
            self._conn.commit()

    def create_tracked_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        category = _lower(payload.get("category"))
        if category not in PRODUCT_CATEGORIES:
            raise ValueError(f"unsupported product category: {category}")
        brand = _clean(payload.get("brand")) or None
        model_family = _clean(payload.get("model_family")) or None
        variant = _clean(payload.get("variant")) or None
        status = _lower(payload.get("status") or "active")
        if status not in PRODUCT_STATUSES:
            raise ValueError(f"unsupported tracked product status: {status}")
        identity_text = " ".join(part for part in [brand, model_family, variant] if part)
        normalized = normalize_product_text(category, identity_text or _clean(payload.get("canonical_key")))
        attributes = dict(normalized["attributes"])
        attributes.update(payload.get("attributes") or {})
        canonical_key = _clean(payload.get("canonical_key")) or normalized["canonical_key"]
        aliases = [str(item).strip() for item in payload.get("aliases") or [] if str(item).strip()]
        negative_terms = [
            str(item).strip() for item in payload.get("negative_terms") or [] if str(item).strip()
        ]
        now = _now_iso()
        tracked_product_id = _new_id("tp_")
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO marketplace_tracked_products (
                    tracked_product_id, canonical_key, category, brand, model_family,
                    variant, attributes_json, aliases_json, negative_terms_json,
                    status, created_at, updated_at
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    tracked_product_id,
                    canonical_key,
                    category,
                    brand,
                    model_family,
                    variant,
                    _json_dumps(attributes),
                    _json_dumps(aliases),
                    _json_dumps(negative_terms),
                    status,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        product = self.get_tracked_product(tracked_product_id)
        if product is None:
            raise RuntimeError("tracked product insert failed")
        return product

    def list_tracked_products(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[dict[str, Any]]:
        where = []
        args: list[Any] = []
        if status:
            where.append("status = ?")
            args.append(_lower(status))
        if category:
            where.append("category = ?")
            args.append(_lower(category))
        query = "SELECT * FROM marketplace_tracked_products"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY updated_at DESC, created_at DESC"
        rows = self._conn.execute(query, args).fetchall()
        return [self._product_from_row(row) for row in rows]

    def get_tracked_product(self, tracked_product_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM marketplace_tracked_products WHERE tracked_product_id = ?",
            (_clean(tracked_product_id),),
        ).fetchone()
        return self._product_from_row(row) if row else None

    def get_tracked_product_by_canonical_key(self, canonical_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM marketplace_tracked_products WHERE canonical_key = ? LIMIT 1",
            (_clean(canonical_key),),
        ).fetchone()
        return self._product_from_row(row) if row else None

    def get_or_create_tracked_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        canonical_key = _clean(payload.get("canonical_key"))
        if canonical_key:
            existing = self.get_tracked_product_by_canonical_key(canonical_key)
            if existing is not None:
                return existing
        try:
            return self.create_tracked_product(payload)
        except sqlite3.IntegrityError:
            if canonical_key:
                existing = self.get_tracked_product_by_canonical_key(canonical_key)
                if existing is not None:
                    return existing
            raise

    def ingest_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        tracked_product_id = _clean(payload.get("tracked_product_id"))
        product = self.get_tracked_product(tracked_product_id)
        if product is None:
            raise ValueError("tracked_product_id not found")
        source = _lower(payload.get("source")) or "manual"
        title = _clean(payload.get("title"))
        if not title:
            raise ValueError("title is required")
        price = _parse_price(payload.get("price"))
        if price is None:
            raise ValueError("price is required")
        observed_at = _to_iso(payload.get("observed_at"))
        capture_mode = _lower(payload.get("capture_mode") or "manual")
        if capture_mode not in CAPTURE_MODES:
            capture_mode = "manual"
        fingerprint = listing_fingerprint(
            source=source,
            source_listing_id=_clean(payload.get("source_listing_id")) or None,
            url=_clean(payload.get("url")) or None,
            title=title,
            price=price,
            location=_clean(payload.get("location")) or None,
        )
        junk = detect_listing_junk(title=title, price=price, category=product["category"])
        review_state = _lower(payload.get("review_state") or "")
        if not review_state:
            review_state = "rejected" if junk["is_junk"] else "pending_review"
        if review_state not in OBSERVATION_REVIEW_STATES:
            raise ValueError(f"unsupported review_state: {review_state}")
        observation_id = _new_id("obs_")
        created_at = _now_iso()
        is_transactional = 1 if payload.get("is_transactional") else 0
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO marketplace_price_observations (
                    observation_id, tracked_product_id, source, observed_at,
                    source_listing_id, listing_fingerprint, title, price, currency,
                    url, location, seller_type, condition_label, match_confidence,
                    is_transactional, capture_mode, provenance_json, review_state, 
                    review_reason, junk_flags_json, created_at
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    observation_id,
                    tracked_product_id,
                    source,
                    observed_at,
                    _clean(payload.get("source_listing_id")) or None,
                    fingerprint,
                    title,
                    float(price),
                    _clean(payload.get("currency")) or "AUD",
                    _clean(payload.get("url")) or None,
                    _clean(payload.get("location")) or None,
                    _clean(payload.get("seller_type")) or None,
                    _clean(payload.get("condition_label")) or None,
                    payload.get("match_confidence"),
                    is_transactional,
                    capture_mode,
                    _json_dumps(payload.get("provenance") or {}),
                    review_state,
                    _clean(payload.get("review_reason")) or None,
                    _json_dumps(junk["flags"]),
                    created_at,
                ),
            )
            self._upsert_timeline_unlocked(
                tracked_product_id=tracked_product_id,
                source=source,
                observed_at=observed_at,
                price=float(price),
                fingerprint=fingerprint,
                observation_id=observation_id,
            )
            if review_state != "pending_review":
                self._conn.execute(
                    """
                    INSERT INTO marketplace_observation_review_history (
                        review_id, observation_id, from_state, to_state, reason, reviewed_at
                    )
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        _new_id("rev_"),
                        observation_id,
                        None,
                        review_state,
                        _clean(payload.get("review_reason")) or None,
                        created_at,
                    ),
                )
            self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM marketplace_price_observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        return self._observation_from_row(row)

    def latest_observation_for_listing(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        tracked_product_id = _clean(payload.get("tracked_product_id"))
        source = _lower(payload.get("source")) or "manual"
        title = _clean(payload.get("title"))
        price = _parse_price(payload.get("price"))
        if not tracked_product_id or not title or price is None:
            return None
        fingerprint = listing_fingerprint(
            source=source,
            source_listing_id=_clean(payload.get("source_listing_id")) or None,
            url=_clean(payload.get("url")) or None,
            title=title,
            price=price,
            location=_clean(payload.get("location")) or None,
        )
        row = self._conn.execute(
            """
            SELECT *
            FROM marketplace_price_observations
            WHERE tracked_product_id = ?
              AND listing_fingerprint = ?
            ORDER BY observed_at DESC, created_at DESC
            LIMIT 1
            """,
            (tracked_product_id, fingerprint),
        ).fetchone()
        return self._observation_from_row(row) if row else None

    def ingest_observation_if_new_or_changed(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        price = _parse_price(payload.get("price"))
        existing = self.latest_observation_for_listing(payload)
        if existing is not None and price is not None:
            if abs(float(existing["price"]) - float(price)) < 0.01:
                return {**existing, "created": False, "deduped": True}
        observation = self.ingest_observation(payload)
        return {**observation, "created": True, "deduped": False}

    def list_observations(
        self, *, tracked_product_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        if tracked_product_id:
            rows = self._conn.execute(
                """
                SELECT * FROM marketplace_price_observations
                WHERE tracked_product_id = ?
                ORDER BY observed_at DESC, created_at DESC
                LIMIT ?
                """,
                (_clean(tracked_product_id), safe_limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM marketplace_price_observations
                ORDER BY observed_at DESC, created_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [self._observation_from_row(row) for row in rows]

    def list_timelines(self, *, tracked_product_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM marketplace_listing_timelines
            WHERE tracked_product_id = ?
            ORDER BY last_seen DESC
            """,
            (_clean(tracked_product_id),),
        ).fetchall()
        return [self._timeline_from_row(row) for row in rows]

    def rebuild_benchmark_snapshot(
        self, tracked_product_id: str, *, retail_anchor: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        product = self.get_tracked_product(tracked_product_id)
        if product is None:
            raise ValueError("tracked_product_id not found")
        rows = self._conn.execute(
            """
            SELECT *
            FROM marketplace_price_observations
            WHERE tracked_product_id = ?
              AND review_state IN ('pending_review', 'accepted')
            ORDER BY observed_at DESC
            """,
            (_clean(tracked_product_id),),
        ).fetchall()
        observations = [self._observation_from_row(row) for row in rows]
        generated_at_dt = _now()
        generated_at = generated_at_dt.replace(microsecond=0).isoformat()

        # Calculate weights for all observations
        weighted_obs_data = []
        for obs in observations:
            # weight = exp(-0.05 * days_since_observed) -> half_life_days = 1/0.05 = 20
            decay_weight = compute_recency_decay(
                published_at=obs["observed_at"],
                half_life_days=20,
                now=generated_at_dt,
            )
            # Transactional data (sold) is weighted more heavily than asking prices
            multiplier = 2.0 if obs.get("is_transactional") else 1.0
            weight = decay_weight * multiplier
            weighted_obs_data.append({"obs": obs, "weight": weight})

        source_counts: dict[str, int] = {}
        for obs in observations:
            source_counts[obs["source"]] = source_counts.get(obs["source"], 0) + 1

        rollups: dict[str, dict[str, Any]] = {}
        for days in (7, 30, 90):
            cutoff = generated_at_dt - timedelta(days=days)
            pairs = [
                (float(item["obs"]["price"]), item["weight"])
                for item in weighted_obs_data
                if _parse_observed_at(item["obs"]["observed_at"]) >= cutoff
            ]
            rollups[f"{days}d"] = self._build_rollup(pairs).as_dict()

        all_price_weight_pairs = [
            (float(item["obs"]["price"]), item["weight"]) for item in weighted_obs_data
        ]
        total = len(weighted_obs_data)
        latest_seen = (
            max(_parse_observed_at(obs["observed_at"]) for obs in observations)
            if observations
            else None
        )
        warnings: list[str] = []
        notes: list[str] = []
        if total == 0:
            freshness_status = "no_data"
            confidence = "no_data"
            warnings.append("No accepted or pending observations are available.")
        else:
            age_days_val = (
                (generated_at_dt - latest_seen).total_seconds() / 86400 if latest_seen else 999
            )
            if total < 3:
                freshness_status = "low_data"
                confidence = "low"
                warnings.append("Fewer than three samples; benchmark is provisional.")
            elif age_days_val > 30:
                freshness_status = "stale"
                confidence = "low"
                warnings.append("Newest observation is older than 30 days.")
            elif age_days_val <= 7:
                freshness_status = "fresh"
                confidence = "high" if total >= 12 else "medium" if total >= 5 else "low"
            else:
                freshness_status = "aging"
                confidence = "medium" if total >= 5 else "low"
            notes.append("Asking-price benchmark; not mission-linked and not fair-value advice.")

        snapshot = {
            "snapshot_id": _new_id("bench_"),
            "tracked_product_id": tracked_product_id,
            "generated_at": generated_at,
            "total_sample_size": total,
            "source_sample_sizes": source_counts,
            "rollups": rollups,
            "fair_range_low": _weighted_percentile(all_price_weight_pairs, 0.25),
            "fair_range_high": _weighted_percentile(all_price_weight_pairs, 0.75),
            "used_median": _weighted_percentile(all_price_weight_pairs, 0.5),
            "retail_anchor": retail_anchor or {},
            "freshness_status": freshness_status,
            "confidence_label": confidence,
            "notes": notes,
            "warnings": warnings,
        }
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO marketplace_benchmark_snapshots (
                    snapshot_id, tracked_product_id, generated_at, total_sample_size,
                    source_sample_sizes_json, rollups_json, fair_range_low,
                    fair_range_high, used_median, retail_anchor_json,
                    freshness_status, confidence_label, notes_json, warnings_json
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    snapshot["snapshot_id"],
                    snapshot["tracked_product_id"],
                    snapshot["generated_at"],
                    snapshot["total_sample_size"],
                    _json_dumps(snapshot["source_sample_sizes"]),
                    _json_dumps(snapshot["rollups"]),
                    snapshot["fair_range_low"],
                    snapshot["fair_range_high"],
                    snapshot["used_median"],
                    _json_dumps(snapshot["retail_anchor"]),
                    snapshot["freshness_status"],
                    snapshot["confidence_label"],
                    _json_dumps(snapshot["notes"]),
                    _json_dumps(snapshot["warnings"]),
                ),
            )
            self._conn.commit()
        return snapshot

    def list_benchmark_snapshots(
        self, *, tracked_product_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        rows = self._conn.execute(
            """
            SELECT * FROM marketplace_benchmark_snapshots
            WHERE tracked_product_id = ?
            ORDER BY generated_at DESC
            LIMIT ?
            """,
            (_clean(tracked_product_id), safe_limit),
        ).fetchall()
        return [self._snapshot_from_row(row) for row in rows]

    def latest_benchmark_snapshot(self, tracked_product_id: str) -> dict[str, Any] | None:
        snapshots = self.list_benchmark_snapshots(
            tracked_product_id=tracked_product_id,
            limit=1,
        )
        return snapshots[0] if snapshots else None

    def build_benchmark_state(
        self,
        tracked_product: dict[str, Any] | None,
        snapshot: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if tracked_product is None:
            return None
        if snapshot is None:
            return {
                "status": "unavailable",
                "freshness_status": "no_snapshot",
                "confidence_label": "low",
                "sample_size": 0,
                "snapshot_id": None,
                "generated_at": None,
                "fair_low": None,
                "fair_high": None,
                "used_median": None,
                "retail_anchor_price": None,
                "warnings": ["No benchmark snapshot exists for the linked tracked product."],
            }
        retail_anchor = snapshot.get("retail_anchor")
        if not isinstance(retail_anchor, dict):
            retail_anchor = {}
        return {
            "status": snapshot.get("freshness_status") or "unknown",
            "freshness_status": snapshot.get("freshness_status") or "unknown",
            "confidence_label": snapshot.get("confidence_label") or "low",
            "sample_size": int(snapshot.get("total_sample_size") or 0),
            "snapshot_id": snapshot.get("snapshot_id"),
            "generated_at": snapshot.get("generated_at"),
            "fair_low": snapshot.get("fair_range_low"),
            "fair_high": snapshot.get("fair_range_high"),
            "used_median": snapshot.get("used_median"),
            "retail_anchor_price": _retail_anchor_price(retail_anchor),
            "warnings": list(snapshot.get("warnings") or []),
            "notes": list(snapshot.get("notes") or []),
        }

    def assess_match_value(
        self,
        *,
        match: dict[str, Any],
        tracked_product: dict[str, Any] | None,
        snapshot: dict[str, Any] | None,
    ) -> dict[str, Any]:
        now_iso = _now_iso()
        if tracked_product is None:
            return {
                "state": "value_unavailable",
                "value_score": None,
                "value_label": "unclear",
                "value_confidence": "low",
                "benchmark_snapshot_id": None,
                "fair_low": None,
                "fair_high": None,
                "used_median": None,
                "retail_anchor_price": None,
                "price_movement_summary": None,
                "explanation": "Mission is not linked to a tracked product.",
                "warnings": ["Link a primary tracked product to enable value context."],
                "notes": [],
                "computed_at": now_iso,
            }

        if snapshot is None:
            return {
                "state": "value_unavailable",
                "value_score": None,
                "value_label": "unclear",
                "value_confidence": "low",
                "benchmark_snapshot_id": None,
                "fair_low": None,
                "fair_high": None,
                "used_median": None,
                "retail_anchor_price": None,
                "price_movement_summary": None,
                "explanation": "No benchmark snapshot exists for the linked tracked product.",
                "warnings": ["Create or rebuild a benchmark snapshot before scoring value."],
                "notes": [],
                "computed_at": now_iso,
            }

        retail_anchor = snapshot.get("retail_anchor")
        if not isinstance(retail_anchor, dict):
            retail_anchor = {}
        retail_price = _retail_anchor_price(retail_anchor)
        listing_price = _parse_price(match.get("price_value"))
        if listing_price is None:
            listing_price = _parse_price(match.get("price"))

        fair_low = _parse_price(snapshot.get("fair_range_low"))
        fair_high = _parse_price(snapshot.get("fair_range_high"))
        used_median = _parse_price(snapshot.get("used_median"))
        sample_size = int(snapshot.get("total_sample_size") or 0)
        freshness = _clean(snapshot.get("freshness_status")) or "unknown"
        source_sample_sizes = snapshot.get("source_sample_sizes")
        if not isinstance(source_sample_sizes, dict):
            source_sample_sizes = {}
        source_diversity = sum(1 for count in source_sample_sizes.values() if int(count or 0) > 0)
        warnings = list(snapshot.get("warnings") or [])
        notes = list(snapshot.get("notes") or [])
        state = "scored"

        confidence_rank = VALUE_CONFIDENCE_ORDER.get(
            str(snapshot.get("confidence_label") or "low").lower(),
            0,
        )
        if sample_size <= 0:
            state = "value_unavailable"
            confidence_rank = 0
            warnings.append("Benchmark has no used-market observations.")
            if retail_price is not None and listing_price is not None:
                state = "retail_anchor_only"
                warnings.append("Only a retail anchor is available; used-market value is not scored.")
        elif sample_size < 3:
            state = "insufficient_data"
            confidence_rank = min(confidence_rank, 0)
            warnings.append("Fewer than three observations support this benchmark.")
        elif freshness == "stale":
            state = "stale_benchmark"
            confidence_rank = min(confidence_rank, 0)
            warnings.append("Benchmark is stale; value context is low confidence.")
        elif freshness in {"low_data", "no_data"}:
            state = "insufficient_data"
            confidence_rank = min(confidence_rank, 0)

        if source_diversity < 2 and sample_size > 0:
            confidence_rank = max(0, confidence_rank - 1)
            warnings.append("Benchmark currently has weak source diversity.")

        if listing_price is None:
            state = "value_unavailable"
            confidence_rank = 0
            warnings.append("Listing price could not be parsed.")

        variant_confidence = self._variant_match_confidence(match, tracked_product)
        if variant_confidence < 0.35:
            state = "ambiguous_variant"
            confidence_rank = 0
            warnings.append("Listing text does not clearly match the linked tracked product.")
        elif variant_confidence < 0.65:
            confidence_rank = max(0, confidence_rank - 1)
            warnings.append("Listing variant match is plausible but not strong.")

        condition_certainty = self._condition_certainty(match)
        if condition_certainty == "weak":
            confidence_rank = max(0, confidence_rank - 1)
            warnings.append("Listing condition is not explicit enough for high-confidence value context.")
        elif condition_certainty == "risky":
            state = "ambiguous_variant" if state == "scored" else state
            confidence_rank = 0
            warnings.append("Listing condition may indicate broken, parts-only, or incomplete hardware.")

        value_score: float | None = None
        if listing_price is not None and used_median and used_median > 0:
            discount_pct = (used_median - listing_price) / used_median
            value_score = max(0.0, min(100.0, 55.0 + discount_pct * 120.0))
            if fair_low is not None and listing_price <= fair_low:
                value_score = max(value_score, 86.0)
            if fair_high is not None and listing_price > fair_high:
                value_score = min(value_score, 48.0)
        elif state not in {"value_unavailable", "retail_anchor_only"} and retail_price is not None:
            state = "retail_anchor_only"
            confidence_rank = 0
            warnings.append("Only a retail anchor is available; used-market value is not scored.")

        if state == "value_unavailable":
            value_score = None

        value_label = _value_label(value_score if state != "retail_anchor_only" else None)
        value_confidence = ["low", "medium", "high"][max(0, min(2, confidence_rank))]
        explanation = self._value_explanation(
            listing_price=listing_price,
            used_median=used_median,
            fair_low=fair_low,
            fair_high=fair_high,
            state=state,
        )
        return {
            "state": state,
            "value_score": round(value_score, 1) if value_score is not None else None,
            "value_label": value_label,
            "value_confidence": value_confidence,
            "benchmark_snapshot_id": snapshot.get("snapshot_id"),
            "fair_low": fair_low,
            "fair_high": fair_high,
            "used_median": used_median,
            "listing_price": listing_price,
            "retail_anchor_price": retail_price,
            "retail_anchor_label": _retail_anchor_label(retail_anchor),
            "price_movement_summary": self._price_movement_summary(match),
            "explanation": explanation,
            "warnings": warnings,
            "notes": notes,
            "linked_tracked_product_id": tracked_product.get("tracked_product_id"),
            "linked_tracked_product_name": tracked_product.get("canonical_key"),
            "benchmark_freshness_status": freshness,
            "benchmark_sample_size": sample_size,
            "variant_match_confidence": round(variant_confidence, 3),
            "condition_certainty": condition_certainty,
            "computed_at": now_iso,
        }

    def upsert_match_value_assessment(
        self,
        *,
        match: dict[str, Any],
        tracked_product: dict[str, Any],
        snapshot: dict[str, Any] | None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        match_id = _clean(match.get("match_id"))
        if not match_id:
            raise ValueError("match_id is required for value assessment persistence")
        assessment = self.assess_match_value(
            match=match,
            tracked_product=tracked_product,
            snapshot=snapshot,
        )
        if context:
            assessment.update(context)
        now_iso = _now_iso()
        with self._lock:
            existing = self._conn.execute(
                """
                SELECT assessment_id
                FROM marketplace_match_value_assessments
                WHERE match_id = ?
                LIMIT 1
                """,
                (match_id,),
            ).fetchone()
            assessment_id = (
                str(existing["assessment_id"]) if existing else _new_id("value_")
            )
            self._conn.execute(
                """
                INSERT INTO marketplace_match_value_assessments (
                    assessment_id, match_id, mission_id, tracked_product_id,
                    benchmark_snapshot_id, value_state, value_score,
                    value_label, value_confidence, assessment_json,
                    computed_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    mission_id = excluded.mission_id,
                    tracked_product_id = excluded.tracked_product_id,
                    benchmark_snapshot_id = excluded.benchmark_snapshot_id,
                    value_state = excluded.value_state,
                    value_score = excluded.value_score,
                    value_label = excluded.value_label,
                    value_confidence = excluded.value_confidence,
                    assessment_json = excluded.assessment_json,
                    computed_at = excluded.computed_at,
                    updated_at = excluded.updated_at
                """,
                (
                    assessment_id,
                    match_id,
                    _clean(match.get("mission_id")) or None,
                    tracked_product.get("tracked_product_id"),
                    assessment.get("benchmark_snapshot_id"),
                    assessment["state"],
                    assessment.get("value_score"),
                    assessment["value_label"],
                    assessment["value_confidence"],
                    _json_dumps(assessment),
                    assessment["computed_at"],
                    now_iso,
                ),
            )
            self._conn.commit()
        return assessment

    def resolve_match_candidate(
        self,
        match: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
        *,
        min_confidence: float = 0.45,
    ) -> dict[str, Any]:
        best: dict[str, Any] | None = None
        for context in candidate_contexts:
            product = context.get("tracked_product")
            if not isinstance(product, dict):
                continue
            confidence = self._variant_match_confidence(match, product)
            candidate = context.get("candidate") if isinstance(context.get("candidate"), dict) else {}
            score = float(candidate.get("fit_score") or 0.0)
            ranked = {
                **context,
                "candidate_match_confidence": round(confidence, 3),
                "_sort_key": (confidence, score),
            }
            if best is None or ranked["_sort_key"] > best["_sort_key"]:
                best = ranked
        if best is None:
            return {
                "matched": False,
                "candidate_match_confidence": 0.0,
                "warning": "No requirement candidates are available for this mission.",
            }
        if float(best["candidate_match_confidence"]) < min_confidence:
            return {
                "matched": False,
                "candidate_match_confidence": best["candidate_match_confidence"],
                "best_candidate": best.get("candidate"),
                "tracked_product": best.get("tracked_product"),
                "warning": "Listing did not match any requirement candidate strongly enough.",
            }
        best.pop("_sort_key", None)
        return {"matched": True, **best}

    def get_match_value_assessment(self, match_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT assessment_json
            FROM marketplace_match_value_assessments
            WHERE match_id = ?
            LIMIT 1
            """,
            (_clean(match_id),),
        ).fetchone()
        if row is None:
            return None
        parsed = _json_loads(row["assessment_json"], {})
        return parsed if isinstance(parsed, dict) else None

    def build_match_price_comparison(
        self,
        *,
        match: dict[str, Any],
        value_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        listing_price = _parse_price(match.get("price_value"))
        if listing_price is None:
            listing_price = _parse_price(match.get("price"))
        value_context = value_context if isinstance(value_context, dict) else {}
        used_median = _parse_price(value_context.get("used_median"))
        fair_low = _parse_price(value_context.get("fair_low"))
        fair_high = _parse_price(value_context.get("fair_high"))
        retail_anchor_price = _parse_price(value_context.get("retail_anchor_price"))
        retail_anchor_label = _clean(value_context.get("retail_anchor_label")) or None
        benchmark = match.get("benchmark") if isinstance(match.get("benchmark"), dict) else {}
        if retail_anchor_price is None:
            for key in ("current_price", "rrp_price", "rrp", "retail_anchor_price"):
                retail_anchor_price = _parse_price(benchmark.get(key))
                if retail_anchor_price is not None:
                    break
        if retail_anchor_label is None and retail_anchor_price is not None:
            retail_anchor_label = _clean(benchmark.get("source")) or None

        anchor_price = used_median if used_median is not None else retail_anchor_price
        anchor_kind = "used_market_median" if used_median is not None else "retail_anchor"
        if anchor_price is None:
            anchor_kind = "none"

        used_delta = _price_delta(listing_price, used_median)
        retail_delta = _price_delta(listing_price, retail_anchor_price)
        verdict = "unavailable"
        color = "slate"
        comparison_state = "unavailable"
        unavailable_reason: str | None = None
        next_action: str | None = None
        if listing_price is None:
            verdict = "missing_listing_price"
            comparison_state = "missing_listing_price"
            unavailable_reason = "Listing price could not be parsed."
            next_action = "Rescan or inspect the listing to capture a usable listing price."
        elif used_median is not None and used_median > 0:
            comparison_state = "used_market_comparison"
            delta_pct = used_delta["percent"]
            if delta_pct is not None and delta_pct <= -15:
                verdict = "strong_discount"
                color = "green"
            elif delta_pct is not None and delta_pct <= -5:
                verdict = "discount"
                color = "emerald"
            elif delta_pct is not None and delta_pct <= 10:
                verdict = "near_market"
                color = "amber"
            else:
                verdict = "above_market"
                color = "red"
        elif retail_anchor_price is not None and retail_anchor_price > 0:
            comparison_state = "retail_anchor_only"
            delta_pct = retail_delta["percent"]
            if delta_pct is not None and delta_pct <= -35:
                verdict = "below_retail_anchor"
                color = "emerald"
            elif delta_pct is not None and delta_pct <= -10:
                verdict = "modest_retail_discount"
                color = "amber"
            else:
                verdict = "close_to_retail"
                color = "red"
        else:
            comparison_state = "missing_benchmark_anchor"
            unavailable_reason = (
                "Listing price was captured, but no used-market benchmark or retail/RRP "
                "anchor is available for the matched product."
            )
            next_action = (
                "Link or calibrate a tracked product benchmark, then add accepted "
                "marketplace observations or a retail anchor."
            )

        return {
            "listing_price": listing_price,
            "currency": "AUD",
            "used_market_median": used_median,
            "retail_anchor_price": retail_anchor_price,
            "retail_anchor_label": retail_anchor_label,
            "fair_range_low": fair_low,
            "fair_range_high": fair_high,
            "delta_vs_used_median": used_delta,
            "delta_vs_retail_anchor": retail_delta,
            "primary_anchor": {
                "kind": anchor_kind,
                "price": anchor_price,
            },
            "verdict": verdict,
            "color": color,
            "comparison_state": comparison_state,
            "unavailable_reason": unavailable_reason,
            "next_action": next_action,
        }

    def variant_match_confidence(
        self,
        *,
        match: dict[str, Any],
        tracked_product: dict[str, Any],
    ) -> float:
        return self._variant_match_confidence(match, tracked_product)

    def _variant_match_confidence(
        self,
        match: dict[str, Any],
        tracked_product: dict[str, Any],
    ) -> float:
        listing_text = " ".join(
            [
                _clean(match.get("title")),
                _clean(match.get("raw_text_snapshot")),
                _clean(match.get("price")),
            ]
        )
        listing_tokens = _identity_tokens(listing_text)
        aliases = tracked_product.get("aliases")
        identity_values = [
            tracked_product.get("canonical_key"),
            tracked_product.get("brand"),
            tracked_product.get("model_family"),
            tracked_product.get("variant"),
            aliases if isinstance(aliases, list) else [],
        ]
        product_tokens = _identity_tokens(*identity_values)
        if not product_tokens:
            return 0.5
        canonical = _lower(tracked_product.get("canonical_key"))
        if canonical and canonical in _lower(listing_text):
            return 1.0
        overlap = product_tokens.intersection(listing_tokens)
        exact_ratio = len(overlap) / max(len(product_tokens), 1)
        numeric_tokens = {token for token in product_tokens if any(ch.isdigit() for ch in token)}
        numeric_overlap = numeric_tokens.intersection(listing_tokens)
        numeric_ratio = len(numeric_overlap) / max(len(numeric_tokens), 1) if numeric_tokens else 0.5
        return max(0.0, min(1.0, (exact_ratio * 0.7) + (numeric_ratio * 0.3)))

    def _condition_certainty(self, match: dict[str, Any]) -> str:
        metadata = match.get("metadata")
        condition = ""
        if isinstance(metadata, dict):
            condition = _lower(
                metadata.get("condition")
                or metadata.get("condition_label")
                or metadata.get("listing_condition")
            )
        listing_text = _lower(
            " ".join(
                [
                    _clean(match.get("title")),
                    _clean(match.get("raw_text_snapshot")),
                    condition,
                ]
            )
        )
        if re.search(r"\b(broken|not working|for parts|faulty|dead|repair)\b", listing_text):
            return "risky"
        if condition or re.search(r"\b(used|new|near new|excellent|working|sealed)\b", listing_text):
            return "clear"
        return "weak"

    def _price_movement_summary(self, match: dict[str, Any]) -> str | None:
        metadata = match.get("metadata")
        if isinstance(metadata, dict):
            summary = _clean(
                metadata.get("price_movement_summary")
                or metadata.get("price_history_summary")
            )
            if summary:
                return summary
        return "No listing price movement history is available for this match."

    def _value_explanation(
        self,
        *,
        listing_price: float | None,
        used_median: float | None,
        fair_low: float | None,
        fair_high: float | None,
        state: str,
    ) -> str:
        if state == "value_unavailable":
            return "Value context is unavailable from the current benchmark data."
        if state == "retail_anchor_only":
            return "Only a retail anchor is present, so used-market value is not scored."
        if listing_price is None:
            return "Listing price could not be parsed, so value is not scored."
        if used_median is None:
            return "Benchmark has no used-market median, so value is not scored."
        range_text = "fair range unavailable"
        if fair_low is not None and fair_high is not None:
            range_text = f"fair range AUD {fair_low:.0f}-{fair_high:.0f}"
        return (
            f"Listing price AUD {listing_price:.0f} is compared with used median "
            f"AUD {used_median:.0f} and {range_text}."
        )

    def _upsert_timeline_unlocked(
        self,
        *,
        tracked_product_id: str,
        source: str,
        observed_at: str,
        price: float,
        fingerprint: str,
        observation_id: str,
    ) -> None:
        row = self._conn.execute(
            "SELECT * FROM marketplace_listing_timelines WHERE listing_fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        price_entry = {"observed_at": observed_at, "price": float(price)}
        if row is None:
            self._conn.execute(
                """
                INSERT INTO marketplace_listing_timelines (
                    listing_fingerprint, tracked_product_id, source, first_seen,
                    last_seen, latest_price, price_history_json, price_change_count,
                    active_state, latest_observation_id, updated_at
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    fingerprint,
                    tracked_product_id,
                    source,
                    observed_at,
                    observed_at,
                    float(price),
                    _json_dumps([price_entry]),
                    0,
                    "active",
                    observation_id,
                    _now_iso(),
                ),
            )
            return
        history = _json_loads(row["price_history_json"], [])
        if not isinstance(history, list):
            history = []
        previous_price = float(row["latest_price"])
        changed = previous_price != float(price)
        history.append(price_entry)
        self._conn.execute(
            """
            UPDATE marketplace_listing_timelines
            SET last_seen = ?,
                latest_price = ?,
                price_history_json = ?,
                price_change_count = price_change_count + ?,
                active_state = 'active',
                latest_observation_id = ?,
                updated_at = ?
            WHERE listing_fingerprint = ?
            """,
            (
                observed_at,
                float(price),
                _json_dumps(history),
                1 if changed else 0,
                observation_id,
                _now_iso(),
                fingerprint,
            ),
        )

    def _build_rollup(self, price_weight_pairs: list[tuple[float, float]]) -> BenchmarkRollup:
        return BenchmarkRollup(
            sample_size=len(price_weight_pairs),
            median_price=_weighted_percentile(price_weight_pairs, 0.5),
            fair_range_low=_weighted_percentile(price_weight_pairs, 0.25),
            fair_range_high=_weighted_percentile(price_weight_pairs, 0.75),
        )

    def _product_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "tracked_product_id": row["tracked_product_id"],
            "canonical_key": row["canonical_key"],
            "category": row["category"],
            "brand": row["brand"],
            "model_family": row["model_family"],
            "variant": row["variant"],
            "attributes": _json_loads(row["attributes_json"], {}),
            "aliases": _json_loads(row["aliases_json"], []),
            "negative_terms": _json_loads(row["negative_terms_json"], []),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _observation_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "observation_id": row["observation_id"],
            "tracked_product_id": row["tracked_product_id"],
            "source": row["source"],
            "observed_at": row["observed_at"],
            "source_listing_id": row["source_listing_id"],
            "listing_fingerprint": row["listing_fingerprint"],
            "title": row["title"],
            "price": row["price"],
            "currency": row["currency"],
            "url": row["url"],
            "location": row["location"],
            "seller_type": row["seller_type"],
            "condition_label": row["condition_label"],
            "match_confidence": row["match_confidence"],
            "is_transactional": bool(row["is_transactional"]),
            "capture_mode": row["capture_mode"],
            "provenance": _json_loads(row["provenance_json"], {}),
            "review_state": row["review_state"],
            "review_reason": row["review_reason"],
            "junk_flags": _json_loads(row["junk_flags_json"], []),
            "created_at": row["created_at"],
        }

    def _timeline_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "listing_fingerprint": row["listing_fingerprint"],
            "tracked_product_id": row["tracked_product_id"],
            "source": row["source"],
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "latest_price": row["latest_price"],
            "price_history": _json_loads(row["price_history_json"], []),
            "price_change_count": row["price_change_count"],
            "active_state": row["active_state"],
            "latest_observation_id": row["latest_observation_id"],
            "updated_at": row["updated_at"],
        }

    def _snapshot_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "snapshot_id": row["snapshot_id"],
            "tracked_product_id": row["tracked_product_id"],
            "generated_at": row["generated_at"],
            "total_sample_size": row["total_sample_size"],
            "source_sample_sizes": _json_loads(row["source_sample_sizes_json"], {}),
            "rollups": _json_loads(row["rollups_json"], {}),
            "fair_range_low": row["fair_range_low"],
            "fair_range_high": row["fair_range_high"],
            "used_median": row["used_median"],
            "retail_anchor": _json_loads(row["retail_anchor_json"], {}),
            "freshness_status": row["freshness_status"],
            "confidence_label": row["confidence_label"],
            "notes": _json_loads(row["notes_json"], []),
            "warnings": _json_loads(row["warnings_json"], []),
        }
