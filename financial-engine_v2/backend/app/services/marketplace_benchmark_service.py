from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cockpit.storage.state import StateStore


CENTRE_COM_RETAILER = "centre_com"
LOW_CONFIDENCE_THRESHOLD = 0.72
UNMATCHED_THRESHOLD = 0.35
REVIEW_STATUSES = {"pending_review", "accepted", "rejected", "auto_accepted"}
SUPPORTED_CATEGORIES = {"gpu", "nvme_m2", "cpu", "ram_kit"}
MANUAL_SNAPSHOT_ENV = "CENTRE_COM_MANUAL_SNAPSHOT_FILE"
OBS_SOURCE_LIVE_HTTP = "live_http"
OBS_SOURCE_LIVE_BROWSER = "live_browser"
OBS_SOURCE_MANUAL_SNAPSHOT = "manual_snapshot"
OBS_SOURCE_SEED_FALLBACK = "seed_fallback"
OBSERVATION_SOURCE_VALUES = {
    OBS_SOURCE_LIVE_HTTP,
    OBS_SOURCE_LIVE_BROWSER,
    OBS_SOURCE_MANUAL_SNAPSHOT,
    OBS_SOURCE_SEED_FALLBACK,
}
JSON_LD_RE = re.compile(
    r"<script[^>]+type=[\"']application/ld\\+json[\"'][^>]*>(.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)

# Bounded Centre Com catalog for live page ingest. Each entry keeps a fallback
# price to preserve deterministic operation if the retailer page cannot be fetched.
# These entries are explicitly treated as "new retail benchmark" comparators, not fair value.
CENTRE_COM_SEED_PRODUCTS: list[dict[str, Any]] = [
    {
        "category": "gpu",
        "vendor": "NVIDIA",
        "model": "RTX 4070 SUPER",
        "sku": "RTX 4070 SUPER",
        "product_name": "ASUS Dual GeForce RTX 4070 SUPER EVO OC 12GB",
        "attributes": {"vram_gb": 12, "suffix": "SUPER"},
        "product_url": "https://www.centrecom.com.au/asus-dual-geforce-rtx-4070-super-evo-oc-12gb",
        "price": 1099.0,
    },
    {
        "category": "gpu",
        "vendor": "NVIDIA",
        "model": "RTX 4080 SUPER",
        "sku": "RTX 4080 SUPER",
        "product_name": "MSI GeForce RTX 4080 SUPER VENTUS 3X OC 16GB",
        "attributes": {"vram_gb": 16, "suffix": "SUPER"},
        "product_url": "https://www.centrecom.com.au/msi-geforce-rtx-4080-super-ventus-3x-oc-16gb",
        "price": 1899.0,
    },
    {
        "category": "nvme_m2",
        "vendor": "Samsung",
        "model": "990 PRO",
        "sku": "MZ-V9P1T0BW",
        "product_name": "Samsung 990 PRO 1TB NVMe M.2 Gen4 SSD",
        "attributes": {
            "brand": "Samsung",
            "series": "990 PRO",
            "capacity_gb": 1000,
            "gen": 4,
            "heatsink": False,
        },
        "product_url": "https://www.centrecom.com.au/samsung-990-pro-1tb-nvme-m2-gen4-ssd",
        "price": 169.0,
    },
    {
        "category": "nvme_m2",
        "vendor": "WD",
        "model": "SN850X",
        "sku": "WDS200T2XHE",
        "product_name": "WD Black SN850X 2TB NVMe Gen4 M.2 SSD with Heatsink",
        "attributes": {
            "brand": "WD",
            "series": "SN850X",
            "capacity_gb": 2000,
            "gen": 4,
            "heatsink": True,
        },
        "product_url": "https://www.centrecom.com.au/wd-black-sn850x-2tb-nvme-gen4-m2-ssd-heatsink",
        "price": 249.0,
    },
    {
        "category": "cpu",
        "vendor": "AMD",
        "model": "Ryzen 7 7800X3D",
        "sku": "100-100000910WOF",
        "product_name": "AMD Ryzen 7 7800X3D Desktop Processor",
        "attributes": {"brand": "AMD", "sku_name": "Ryzen 7 7800X3D", "suffix": "X3D"},
        "product_url": "https://www.centrecom.com.au/amd-ryzen-7-7800x3d-desktop-processor",
        "price": 569.0,
    },
    {
        "category": "cpu",
        "vendor": "Intel",
        "model": "Core i7-14700K",
        "sku": "BX8071514700K",
        "product_name": "Intel Core i7-14700K Desktop Processor",
        "attributes": {"brand": "Intel", "sku_name": "i7-14700K", "suffix": "K"},
        "product_url": "https://www.centrecom.com.au/intel-core-i7-14700k-desktop-processor",
        "price": 629.0,
    },
    {
        "category": "ram_kit",
        "vendor": "Corsair",
        "model": "Vengeance DDR5",
        "sku": "CMK32GX5M2B6000C36",
        "product_name": "Corsair Vengeance 32GB (2x16GB) DDR5-6000 CL36 Memory Kit",
        "attributes": {
            "ddr_gen": 5,
            "total_gb": 32,
            "stick_count": 2,
            "speed_mhz": 6000,
            "timings": "CL36",
        },
        "product_url": "https://www.centrecom.com.au/corsair-vengeance-32gb-2x16gb-ddr5-6000-cl36-memory-kit",
        "price": 189.0,
    },
    {
        "category": "ram_kit",
        "vendor": "G.Skill",
        "model": "Trident Z5 Neo DDR5",
        "sku": "F5-6000J3038F16GX2-TZ5N",
        "product_name": "G.Skill Trident Z5 Neo 32GB (2x16GB) DDR5-6000 CL30 Memory Kit",
        "attributes": {
            "ddr_gen": 5,
            "total_gb": 32,
            "stick_count": 2,
            "speed_mhz": 6000,
            "timings": "CL30",
        },
        "product_url": "https://www.centrecom.com.au/gskill-trident-z5-neo-32gb-2x16gb-ddr5-6000-cl30-memory-kit",
        "price": 239.0,
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize(value: Any) -> str:
    return _clean(value).lower()


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _safe_json_loads(raw: Any, fallback: Any) -> Any:
    if not isinstance(raw, str) or not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _parse_price(value: Any) -> float | None:
    text = _clean(value)
    if not text:
        return None
    match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)
    if match is None:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_capacity_gb(text: str) -> int | None:
    tb = re.search(r"\b(\d+(?:\.\d+)?)\s*tb\b", text, flags=re.IGNORECASE)
    if tb:
        return int(float(tb.group(1)) * 1000)
    gb = re.search(r"\b(\d{3,5})\s*gb\b", text, flags=re.IGNORECASE)
    if gb:
        return int(gb.group(1))
    return None


def _build_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{2,}", text.lower()))


def _coerce_json_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for item in value:
            out.extend(_coerce_json_objects(item))
        return out
    return []


def _extract_json_ld_blocks(html: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for raw in JSON_LD_RE.findall(html):
        text = _clean(raw)
        if not text:
            continue
        loaded = _safe_json_loads(text, None)
        if loaded is None:
            continue
        blocks.extend(_coerce_json_objects(loaded))
    return blocks


def _extract_html_meta_content(html: str, property_name: str) -> str | None:
    pattern = re.compile(
        rf"<meta[^>]+(?:property|name)=['\"]{re.escape(property_name)}['\"][^>]+content=['\"]([^'\"]+)['\"]",
        flags=re.IGNORECASE,
    )
    match = pattern.search(html)
    return _clean(match.group(1)) if match else None


def _is_waf_or_forbidden_page(html: str) -> bool:
    lowered = html.lower()
    return any(
        marker in lowered
        for marker in (
            "x-amzn-waf-action",
            "<title>403 forbidden",
            "access denied",
            "request blocked",
        )
    )


class MarketplaceBenchmarkService:
    """Cockpit-local new-retail benchmark overlay service (Centre Com v1)."""

    def __init__(self, state_store: StateStore) -> None:
        self._state_store = state_store
        self._lock = state_store._lock
        self._conn = state_store.conn
        # Keep the benchmark overlay usable out of the box with bounded fallback
        # entries, while explicit refresh performs bounded live ingest.
        if not self._has_seed_data():
            self._bootstrap_seed_snapshot()

    def _has_seed_data(self) -> bool:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT 1
                FROM retailer_products
                WHERE retailer_name = ?
                LIMIT 1
                """,
                (CENTRE_COM_RETAILER,),
            ).fetchone()
        return row is not None

    def _bootstrap_seed_snapshot(self) -> None:
        observed_at = _now_iso()
        for seed in CENTRE_COM_SEED_PRODUCTS:
            fallback_price = _parse_price(seed.get("price"))
            if fallback_price is None:
                continue
            canonical_id, _ = self._upsert_canonical_product(seed, observed_at)
            retailer_id, _ = self._upsert_retailer_product(canonical_id, seed, observed_at)
            self._insert_price_observation(
                retailer_id,
                float(fallback_price),
                observed_at=observed_at,
            )

    def refresh_centre_com_benchmarks(self) -> dict[str, Any]:
        observed_at = _now_iso()
        canonical_count = 0
        retailer_count = 0
        price_count = 0
        failures: list[str] = []
        source_counts = {
            OBS_SOURCE_LIVE_HTTP: 0,
            OBS_SOURCE_LIVE_BROWSER: 0,
            OBS_SOURCE_MANUAL_SNAPSHOT: 0,
            OBS_SOURCE_SEED_FALLBACK: 0,
        }
        manual_snapshot = self._load_manual_snapshot_index()

        for seed in CENTRE_COM_SEED_PRODUCTS:
            fetched = self._fetch_centre_com_product(seed, manual_snapshot=manual_snapshot)
            product_view = {**seed}
            if fetched.get("product_name"):
                product_view["product_name"] = fetched["product_name"]
            if fetched.get("price") is not None:
                product_view["price"] = fetched["price"]
            source = str(fetched.get("source") or OBS_SOURCE_SEED_FALLBACK)
            if source not in OBSERVATION_SOURCE_VALUES:
                source = OBS_SOURCE_SEED_FALLBACK
            fetch_error = _clean(fetched.get("fetch_error"))
            if fetch_error:
                failures.append(f"{seed.get('product_url')}: {fetch_error}")

            price = _parse_price(product_view.get("price"))
            if price is None:
                # Keep this catalog entry out of history if price parsing failed.
                continue

            canonical_id, created_canonical = self._upsert_canonical_product(
                product_view, observed_at
            )
            retailer_id, created_retailer = self._upsert_retailer_product(
                canonical_id,
                product_view,
                observed_at,
            )
            self._insert_price_observation(
                retailer_id,
                float(price),
                observed_at=observed_at,
                observation_source=source,
            )
            canonical_count += 1 if created_canonical else 0
            retailer_count += 1 if created_retailer else 0
            price_count += 1
            source_counts[source] += 1

        live_count = source_counts[OBS_SOURCE_LIVE_HTTP] + source_counts[OBS_SOURCE_LIVE_BROWSER]
        fallback_count = (
            source_counts[OBS_SOURCE_MANUAL_SNAPSHOT] + source_counts[OBS_SOURCE_SEED_FALLBACK]
        )
        ingest_mode = (
            "full_live"
            if price_count > 0 and live_count == price_count
            else "fallback_only"
            if live_count == 0
            else "mixed"
        )

        return {
            "retailer": CENTRE_COM_RETAILER,
            "observed_at": observed_at,
            "canonical_created": canonical_count,
            "retailer_products_created": retailer_count,
            "price_observations_added": price_count,
            "live_observations_added": live_count,
            "fallback_observations_added": fallback_count,
            "observation_sources": source_counts,
            "ingest_mode": ingest_mode,
            "fallback_policy": "live_http_then_live_browser_then_manual_snapshot_then_seed",
            "manual_snapshot_enabled": bool(manual_snapshot),
            "fetch_failures": failures[:10],
            "categories": sorted({row["category"] for row in CENTRE_COM_SEED_PRODUCTS}),
        }

    def _fetch_centre_com_product(
        self,
        seed: dict[str, Any],
        *,
        manual_snapshot: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        url = _clean(seed.get("product_url"))
        manual_snapshot = manual_snapshot or {}
        if not url:
            return {
                "product_name": _clean(seed.get("product_name")) or None,
                "price": _parse_price(seed.get("price")),
                "source": OBS_SOURCE_SEED_FALLBACK,
            }

        failures: list[str] = []

        try:
            html = self._fetch_html(url)
            if _is_waf_or_forbidden_page(html):
                raise RuntimeError("centre_com_http_blocked_by_waf")
            price = self._extract_product_price(html)
            if price is not None:
                return {
                    "product_name": self._extract_product_name(html)
                    or _clean(seed.get("product_name"))
                    or None,
                    "price": price,
                    "source": OBS_SOURCE_LIVE_HTTP,
                }
            failures.append("centre_com_http_no_price")
        except Exception as exc:
            failures.append(str(exc))

        try:
            html = self._fetch_html_via_browser(url)
            if _is_waf_or_forbidden_page(html):
                raise RuntimeError("centre_com_browser_blocked_by_waf")
            price = self._extract_product_price(html)
            if price is not None:
                return {
                    "product_name": self._extract_product_name(html)
                    or _clean(seed.get("product_name"))
                    or None,
                    "price": price,
                    "source": OBS_SOURCE_LIVE_BROWSER,
                }
            failures.append("centre_com_browser_no_price")
        except Exception as exc:
            failures.append(str(exc))

        snapshot_entry = self._lookup_manual_snapshot(seed, manual_snapshot)
        if snapshot_entry is not None:
            return {
                "product_name": _clean(snapshot_entry.get("product_name"))
                or _clean(seed.get("product_name"))
                or None,
                "price": _parse_price(snapshot_entry.get("price")),
                "source": OBS_SOURCE_MANUAL_SNAPSHOT,
                "fetch_error": "; ".join(failures[:3]),
            }

        return {
            "product_name": _clean(seed.get("product_name")) or None,
            "price": _parse_price(seed.get("price")),
            "source": OBS_SOURCE_SEED_FALLBACK,
            "fetch_error": "; ".join(failures[:3]),
        }

    def _fetch_html(self, url: str) -> str:
        request = Request(
            url=url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=12) as response:
                payload = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"centre_com_fetch_failed: {str(exc)}") from exc
        return payload.decode("utf-8", errors="replace")

    def _fetch_html_via_browser(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("centre_com_browser_fetch_unavailable: playwright_missing") from exc
        try:
            from app.services.marketplace_headless_runtime import resolve_marketplace_browser
        except Exception as exc:
            raise RuntimeError(
                "centre_com_browser_fetch_unavailable: browser_runtime_unavailable"
            ) from exc

        try:
            with sync_playwright() as playwright:
                _browser_family, browser_binary = resolve_marketplace_browser(
                    playwright_executable_path=str(playwright.chromium.executable_path or "").strip()
                    or None,
                )
                browser = playwright.chromium.launch(
                    executable_path=browser_binary,
                    headless=True,
                    args=[
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )
                try:
                    page = browser.new_page(
                        user_agent=(
                            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                        )
                    )
                    response = page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                    page.wait_for_timeout(800)
                    status = response.status if response is not None else None
                    html = page.content()
                finally:
                    browser.close()
        except Exception as exc:
            raise RuntimeError(f"centre_com_browser_fetch_failed: {str(exc)}") from exc

        if isinstance(status, int) and status >= 400:
            raise RuntimeError(f"centre_com_browser_fetch_failed: HTTP {status}")
        return html

    def _load_manual_snapshot_index(self) -> dict[str, dict[str, Any]]:
        snapshot_path = str(os.environ.get(MANUAL_SNAPSHOT_ENV) or "").strip()
        if not snapshot_path:
            return {}

        path = Path(snapshot_path).expanduser()
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return {}

        loaded = _safe_json_loads(raw, {})
        if isinstance(loaded, dict) and isinstance(loaded.get("items"), list):
            items = loaded["items"]
        elif isinstance(loaded, list):
            items = loaded
        elif isinstance(loaded, dict):
            items = list(loaded.values())
        else:
            items = []

        index: dict[str, dict[str, Any]] = {}
        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            price = _parse_price(raw_item.get("price"))
            if price is None:
                continue
            entry = {
                "price": float(price),
                "product_name": _clean(raw_item.get("product_name")),
                "product_url": _clean(raw_item.get("product_url")),
                "sku": _clean(raw_item.get("sku")),
            }
            for key in (entry["product_url"], entry["sku"], entry["product_name"]):
                normalized = _normalize(key)
                if normalized:
                    index[normalized] = entry
        return index

    def _lookup_manual_snapshot(
        self,
        seed: dict[str, Any],
        manual_snapshot: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not manual_snapshot:
            return None
        for key in (
            _clean(seed.get("product_url")),
            _clean(seed.get("sku")),
            _clean(seed.get("product_name")),
        ):
            normalized = _normalize(key)
            if normalized and normalized in manual_snapshot:
                return manual_snapshot[normalized]
        return None

    def _extract_product_name(self, html: str) -> str | None:
        for item in _extract_json_ld_blocks(html):
            value = _clean(item.get("name"))
            if value:
                return value
        return (
            _extract_html_meta_content(html, "og:title")
            or _extract_html_meta_content(html, "twitter:title")
        )

    def _extract_product_price(self, html: str) -> float | None:
        for item in _extract_json_ld_blocks(html):
            offers = item.get("offers")
            candidates = _coerce_json_objects(offers)
            if isinstance(offers, list):
                for entry in offers:
                    candidates.extend(_coerce_json_objects(entry))
            for offer in candidates:
                price = _parse_price(offer.get("price"))
                if price is not None:
                    return price

        for property_name in ("product:price:amount", "twitter:data1"):
            value = _extract_html_meta_content(html, property_name)
            price = _parse_price(value)
            if price is not None:
                return price

        # Fallback: locate inline JSON style price fields.
        inline = re.search(
            r'"(?:price|final_price|special_price)"\s*:\s*"?(?P<price>[0-9][0-9,]*(?:\.[0-9]{1,2})?)"?',
            html,
            flags=re.IGNORECASE,
        )
        if inline:
            return _parse_price(inline.group("price"))
        return None

    def enrich_match(self, match: dict[str, Any]) -> dict[str, Any]:
        category = self._infer_category(match)
        if not category:
            return {**match, "benchmark": None}

        candidates = self._list_candidate_products(category)
        if not candidates:
            return {**match, "benchmark": None}

        listing_view = self._extract_listing_attributes(category, match)
        scored: list[tuple[float, dict[str, Any], list[str]]] = []
        for candidate in candidates:
            confidence, rationale = self._score_candidate(category, listing_view, candidate)
            scored.append((confidence, candidate, rationale))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_confidence, best_candidate, rationale = scored[0]
        if best_confidence < UNMATCHED_THRESHOLD:
            return {
                **match,
                "benchmark": {
                    "source": CENTRE_COM_RETAILER,
                    "category": category,
                    "matched_product": None,
                    "current_price": None,
                    "median_30d": None,
                    "listing_delta_pct": None,
                    "freshness_hours": None,
                    "confidence": round(best_confidence, 3),
                    "low_confidence": True,
                    "review_status": "pending_review",
                    "warning": "Low-confidence benchmark match requires manual review.",
                    "rationale": rationale,
                    "wording": "new retail benchmark",
                },
            }

        current_price = best_candidate.get("current_price")
        median_30d = best_candidate.get("median_30d")
        freshness_hours = best_candidate.get("freshness_hours")
        listing_price = _parse_price(match.get("price_value") or match.get("price"))
        if listing_price is None and isinstance(match.get("price_value"), (int, float)):
            listing_price = float(match.get("price_value"))

        delta_pct = None
        if current_price and listing_price is not None and float(current_price) > 0:
            delta_pct = ((listing_price - float(current_price)) / float(current_price)) * 100.0

        low_confidence = best_confidence < LOW_CONFIDENCE_THRESHOLD
        persisted = self._upsert_listing_product_match(
            match=match,
            category=category,
            matched_retailer_product_id=str(best_candidate["retailer_product_id"]),
            confidence=best_confidence,
            low_confidence=low_confidence,
            rationale=rationale,
        )
        self._insert_listing_benchmark_score(
            match=match,
            matched_retailer_product_id=str(best_candidate["retailer_product_id"]),
            centre_com_price=current_price,
            centre_com_median_30d=median_30d,
            listing_price=listing_price,
            delta_pct=delta_pct,
            freshness_hours=freshness_hours,
            confidence=best_confidence,
            low_confidence=low_confidence,
        )

        review_status = str(persisted.get("review_status") or "pending_review")
        warning = None
        if low_confidence and review_status != "accepted":
            warning = "Low-confidence benchmark match requires manual review."

        return {
            **match,
            "benchmark": {
                "source": CENTRE_COM_RETAILER,
                "category": category,
                "matched_product": best_candidate.get("product_name"),
                "current_price": current_price,
                "median_30d": median_30d,
                "listing_delta_pct": delta_pct,
                "freshness_hours": freshness_hours,
                "confidence": round(best_confidence, 3),
                "low_confidence": low_confidence,
                "review_status": review_status,
                "warning": warning,
                "rationale": rationale,
                "wording": "new retail benchmark",
            },
        }

    def set_review_status(
        self,
        *,
        match_id: str,
        review_status: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        normalized = _normalize(review_status)
        if normalized not in REVIEW_STATUSES:
            raise ValueError(f"invalid review status: {review_status}")

        with self._lock:
            row = self._conn.execute(
                """
                SELECT listing_match_id, rationale_json
                FROM listing_product_matches
                WHERE match_id = ?
                LIMIT 1
                """,
                (match_id,),
            ).fetchone()
            if row is None:
                raise KeyError(match_id)

            rationale = _safe_json_loads(row["rationale_json"], [])
            if note:
                rationale = [*rationale, f"review_note: {_clean(note)}"]

            updated_at = _now_iso()
            self._conn.execute(
                """
                UPDATE listing_product_matches
                SET review_status = ?, warning = ?, rationale_json = ?, updated_at = ?
                WHERE listing_match_id = ?
                """,
                (
                    normalized,
                    None if normalized == "accepted" else "Manual review required",
                    json.dumps(rationale),
                    updated_at,
                    str(row["listing_match_id"]),
                ),
            )
            self._conn.commit()

        refreshed = self._get_listing_product_match(match_id)
        if refreshed is None:
            raise KeyError(match_id)
        return refreshed

    def _infer_category(self, match: dict[str, Any]) -> str | None:
        hint = _normalize(match.get("mission_category_hint"))
        if hint in SUPPORTED_CATEGORIES:
            return hint
        if hint in {"gpu", "graphics", "graphics_card"}:
            return "gpu"
        if hint in {"nvme", "ssd", "nvme_m2"}:
            return "nvme_m2"
        if hint in {"cpu", "processor"}:
            return "cpu"
        if hint in {"ram", "memory", "ram_kit"}:
            return "ram_kit"

        text = "\n".join(
            [
                _clean(match.get("title")),
                _clean(match.get("raw_text_snapshot")),
                _clean(match.get("price")),
            ]
        ).lower()
        if re.search(r"\b(rtx|gtx|radeon|rx\s*\d{4}|graphics card|gpu)\b", text):
            return "gpu"
        if re.search(r"\b(nvme|m\.2|gen4|gen5|pcie\s*4|pcie\s*5|ssd)\b", text):
            return "nvme_m2"
        if re.search(r"\b(ryzen|intel core|i[3579]-\d{4,5}|x3d|cpu|processor)\b", text):
            return "cpu"
        if re.search(r"\b(ddr4|ddr5|ram|memory kit|2x\d+gb|\d{4,5}mhz)\b", text):
            return "ram_kit"
        return None

    def _extract_listing_attributes(
        self,
        category: str,
        match: dict[str, Any],
    ) -> dict[str, Any]:
        text = " ".join(
            [
                _clean(match.get("title")),
                _clean(match.get("raw_text_snapshot")),
                _clean(match.get("price")),
            ]
        )
        lowered = text.lower()

        if category == "gpu":
            sku_match = re.search(
                r"\b(?:(rtx|gtx)\s*(\d{3,4})(?:\s*(ti|super))?|rx\s*(\d{4})(?:\s*(xt|xtx))?)\b",
                lowered,
            )
            sku = ""
            suffix = ""
            vendor = ""
            if sku_match:
                if sku_match.group(1):
                    vendor = "nvidia"
                    sku = f"{sku_match.group(1).upper()} {sku_match.group(2)}"
                    suffix = (sku_match.group(3) or "").upper()
                else:
                    vendor = "amd"
                    sku = f"RX {sku_match.group(4)}"
                    suffix = (sku_match.group(5) or "").upper()
            if not vendor and "nvidia" in lowered:
                vendor = "nvidia"
            if not vendor and "amd" in lowered:
                vendor = "amd"
            vram = re.search(r"\b(\d{1,2})\s*gb\b", lowered)
            return {
                "vendor": vendor,
                "sku": sku,
                "suffix": suffix,
                "vram_gb": int(vram.group(1)) if vram else None,
                "tokens": _build_tokens(lowered),
            }

        if category == "nvme_m2":
            gen_match = re.search(r"\bgen\s*([3-5])\b", lowered) or re.search(
                r"\bpcie\s*([3-5])\b", lowered
            )
            return {
                "brand": "samsung"
                if "samsung" in lowered
                else "wd"
                if "wd" in lowered or "western digital" in lowered
                else "crucial"
                if "crucial" in lowered
                else "",
                "series": "",
                "capacity_gb": _parse_capacity_gb(lowered),
                "gen": int(gen_match.group(1)) if gen_match else None,
                "heatsink": bool(re.search(r"\bheatsink\b", lowered)),
                "tokens": _build_tokens(lowered),
            }

        if category == "cpu":
            sku_match = re.search(
                r"\b(i[3579]-\d{4,5}[a-z]{0,3}|ryzen\s*[3579]\s*\d{4,5}[a-z0-9]{0,3})\b",
                lowered,
            )
            suffix_match = re.search(r"\b(x3d|[fkx])\b", lowered)
            return {
                "brand": "amd"
                if "ryzen" in lowered or "amd" in lowered
                else "intel"
                if "intel" in lowered or re.search(r"\bi[3579]-\d", lowered)
                else "",
                "sku_name": sku_match.group(1).upper() if sku_match else "",
                "suffix": suffix_match.group(1).upper() if suffix_match else "",
                "tokens": _build_tokens(lowered),
            }

        # ram_kit
        stick_match = re.search(r"\b(\d)\s*x\s*(\d{1,3})\s*gb\b", lowered)
        total_gb = None
        stick_count = None
        if stick_match:
            stick_count = int(stick_match.group(1))
            each = int(stick_match.group(2))
            total_gb = stick_count * each
        elif re.search(r"\b(\d{2,3})\s*gb\b", lowered):
            total_gb = int(re.search(r"\b(\d{2,3})\s*gb\b", lowered).group(1))
        ddr_match = re.search(r"\bddr\s*([345])\b", lowered)
        speed_match = re.search(r"\b(\d{4,5})\s*mhz\b", lowered)
        timing_match = re.search(r"\bcl\s*(\d{2})\b", lowered)
        return {
            "ddr_gen": int(ddr_match.group(1)) if ddr_match else None,
            "total_gb": total_gb,
            "stick_count": stick_count,
            "speed_mhz": int(speed_match.group(1)) if speed_match else None,
            "timings": f"CL{timing_match.group(1)}" if timing_match else None,
            "single_stick_hint": bool(re.search(r"\bsingle\s*stick\b", lowered)),
            "tokens": _build_tokens(lowered),
        }

    def _score_candidate(
        self,
        category: str,
        listing: dict[str, Any],
        candidate: dict[str, Any],
    ) -> tuple[float, list[str]]:
        attrs = candidate.get("attributes") or {}
        cand_name = _normalize(candidate.get("product_name"))
        rationale: list[str] = []
        score = 0.0

        if category == "gpu":
            l_vendor = _normalize(listing.get("vendor"))
            c_vendor = _normalize(attrs.get("vendor") or candidate.get("vendor"))
            if l_vendor and c_vendor and l_vendor == c_vendor:
                score += 0.2
                rationale.append("Vendor aligned")
            l_sku = _normalize(listing.get("sku"))
            c_sku = _normalize(attrs.get("sku") or attrs.get("sku_name") or candidate.get("model") or candidate.get("sku"))
            if l_sku and c_sku and (l_sku in c_sku or c_sku in l_sku):
                score += 0.45
                rationale.append("GPU SKU aligned")
            l_suffix = _normalize(listing.get("suffix"))
            c_suffix = _normalize(attrs.get("suffix"))
            if l_suffix and c_suffix and l_suffix == c_suffix:
                score += 0.15
                rationale.append("Suffix aligned")
            l_vram = listing.get("vram_gb")
            c_vram = attrs.get("vram_gb")
            if isinstance(l_vram, int) and isinstance(c_vram, int):
                if l_vram == c_vram:
                    score += 0.12
                    rationale.append("VRAM aligned")
                elif abs(l_vram - c_vram) <= 2:
                    score += 0.06
            overlap = len((listing.get("tokens") or set()) & set(cand_name.split()))
            score += min(0.08, overlap * 0.01)

        elif category == "nvme_m2":
            l_brand = _normalize(listing.get("brand"))
            c_brand = _normalize(attrs.get("brand") or candidate.get("vendor"))
            if l_brand and c_brand and l_brand == c_brand:
                score += 0.2
                rationale.append("Brand aligned")
            l_series = _normalize(listing.get("series"))
            c_series = _normalize(attrs.get("series") or candidate.get("model"))
            if l_series and c_series and (l_series in c_series or c_series in l_series):
                score += 0.25
                rationale.append("Series aligned")
            l_capacity = listing.get("capacity_gb")
            c_capacity = attrs.get("capacity_gb")
            if isinstance(l_capacity, int) and isinstance(c_capacity, int):
                if l_capacity == c_capacity:
                    score += 0.2
                    rationale.append("Capacity aligned")
                elif abs(l_capacity - c_capacity) <= 100:
                    score += 0.08
            l_gen = listing.get("gen")
            c_gen = attrs.get("gen")
            if isinstance(l_gen, int) and isinstance(c_gen, int) and l_gen == c_gen:
                score += 0.2
                rationale.append("PCIe generation aligned")
            if listing.get("heatsink") is not None and attrs.get("heatsink") is not None:
                if bool(listing.get("heatsink")) == bool(attrs.get("heatsink")):
                    score += 0.1
                    rationale.append("Heatsink profile aligned")

        elif category == "cpu":
            l_brand = _normalize(listing.get("brand"))
            c_brand = _normalize(attrs.get("brand") or candidate.get("vendor"))
            if l_brand and c_brand and l_brand == c_brand:
                score += 0.2
                rationale.append("Brand aligned")
            l_sku = _normalize(listing.get("sku_name"))
            c_sku = _normalize(attrs.get("sku_name") or candidate.get("model") or candidate.get("sku"))
            if l_sku and c_sku and (l_sku in c_sku or c_sku in l_sku):
                score += 0.5
                rationale.append("CPU SKU aligned")
            l_suffix = _normalize(listing.get("suffix"))
            c_suffix = _normalize(attrs.get("suffix"))
            if l_suffix and c_suffix and l_suffix == c_suffix:
                score += 0.2
                rationale.append("Suffix aligned")

        else:  # ram_kit
            l_ddr = listing.get("ddr_gen")
            c_ddr = attrs.get("ddr_gen")
            if isinstance(l_ddr, int) and isinstance(c_ddr, int) and l_ddr == c_ddr:
                score += 0.2
                rationale.append("DDR generation aligned")
            l_total = listing.get("total_gb")
            c_total = attrs.get("total_gb")
            if isinstance(l_total, int) and isinstance(c_total, int) and l_total == c_total:
                score += 0.2
                rationale.append("Total kit size aligned")
            l_sticks = listing.get("stick_count")
            c_sticks = attrs.get("stick_count")
            if isinstance(l_sticks, int) and isinstance(c_sticks, int):
                if l_sticks == c_sticks:
                    score += 0.2
                    rationale.append("Stick count aligned")
                elif listing.get("single_stick_hint") and c_sticks > 1:
                    score -= 0.2
                    rationale.append("Listing appears single-stick while benchmark is a multi-stick kit")
            l_speed = listing.get("speed_mhz")
            c_speed = attrs.get("speed_mhz")
            if isinstance(l_speed, int) and isinstance(c_speed, int):
                if l_speed == c_speed:
                    score += 0.2
                    rationale.append("Speed aligned")
                elif abs(l_speed - c_speed) <= 200:
                    score += 0.08
            l_timing = _normalize(listing.get("timings"))
            c_timing = _normalize(attrs.get("timings"))
            if l_timing and c_timing and l_timing == c_timing:
                score += 0.1
                rationale.append("Timings aligned")

        if not rationale:
            rationale.append("Token overlap only")
        return max(0.0, min(1.0, score)), rationale

    def _list_candidate_products(self, category: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT
                    rp.retailer_product_id,
                    rp.product_name,
                    rp.product_url,
                    rp.attributes_json AS retailer_attributes_json,
                    cp.vendor,
                    cp.model,
                    cp.sku,
                    cp.attributes_json AS canonical_attributes_json
                FROM retailer_products rp
                JOIN canonical_products cp ON cp.canonical_product_id = rp.canonical_product_id
                WHERE rp.retailer_name = ?
                  AND cp.category = ?
                """,
                (CENTRE_COM_RETAILER, category),
            ).fetchall()

        out: list[dict[str, Any]] = []
        now = _now()
        for row in rows:
            latest = self._latest_price_observation(str(row["retailer_product_id"]))
            if latest is None:
                continue
            observed_at = datetime.fromisoformat(str(latest["observed_at"]).replace("Z", "+00:00"))
            freshness_hours = max(0.0, (now - observed_at).total_seconds() / 3600.0)
            attrs = {
                **_safe_json_loads(row["canonical_attributes_json"], {}),
                **_safe_json_loads(row["retailer_attributes_json"], {}),
                "vendor": row["vendor"],
                "model": row["model"],
                "sku": row["sku"],
            }
            out.append(
                {
                    "retailer_product_id": str(row["retailer_product_id"]),
                    "product_name": str(row["product_name"]),
                    "product_url": row["product_url"],
                    "vendor": row["vendor"],
                    "model": row["model"],
                    "sku": row["sku"],
                    "attributes": attrs,
                    "current_price": float(latest["price"]),
                    "median_30d": self._median_30d(str(row["retailer_product_id"])),
                    "freshness_hours": round(freshness_hours, 2),
                }
            )
        return out

    def _latest_price_observation(self, retailer_product_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT observed_at, price
                FROM retailer_price_observations
                WHERE retailer_product_id = ?
                ORDER BY observed_at DESC
                LIMIT 1
                """,
                (retailer_product_id,),
            ).fetchone()
        if row is None:
            return None
        return {"observed_at": str(row["observed_at"]), "price": float(row["price"])}

    def _median_30d(self, retailer_product_id: str) -> float | None:
        cutoff = (_now() - timedelta(days=30)).replace(microsecond=0).isoformat()
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT price
                FROM retailer_price_observations
                WHERE retailer_product_id = ? AND observed_at >= ?
                ORDER BY observed_at DESC
                """,
                (retailer_product_id, cutoff),
            ).fetchall()
        prices = [float(row["price"]) for row in rows if row["price"] is not None]
        if not prices:
            return None
        return float(median(prices))

    def _upsert_canonical_product(
        self,
        seed: dict[str, Any],
        now_iso: str,
    ) -> tuple[str, bool]:
        category = str(seed["category"])
        sku = _clean(seed.get("sku"))
        product_name = _clean(seed.get("product_name"))
        vendor = _clean(seed.get("vendor")) or None
        model = _clean(seed.get("model")) or None
        attrs_json = json.dumps(seed.get("attributes") or {})

        with self._lock:
            row = self._conn.execute(
                """
                SELECT canonical_product_id
                FROM canonical_products
                WHERE category = ?
                  AND (
                    (COALESCE(sku, '') <> '' AND lower(sku) = lower(?))
                    OR lower(product_name) = lower(?)
                  )
                LIMIT 1
                """,
                (category, sku, product_name),
            ).fetchone()
            if row is None:
                canonical_id = _new_id("canon_prod_")
                self._conn.execute(
                    """
                    INSERT INTO canonical_products (
                        canonical_product_id, category, vendor, model, sku,
                        product_name, attributes_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        canonical_id,
                        category,
                        vendor,
                        model,
                        sku or None,
                        product_name,
                        attrs_json,
                        now_iso,
                        now_iso,
                    ),
                )
                self._conn.commit()
                return canonical_id, True

            canonical_id = str(row["canonical_product_id"])
            self._conn.execute(
                """
                UPDATE canonical_products
                SET vendor = ?, model = ?, sku = ?, product_name = ?,
                    attributes_json = ?, updated_at = ?
                WHERE canonical_product_id = ?
                """,
                (
                    vendor,
                    model,
                    sku or None,
                    product_name,
                    attrs_json,
                    now_iso,
                    canonical_id,
                ),
            )
            self._conn.commit()
        return canonical_id, False

    def _upsert_retailer_product(
        self,
        canonical_product_id: str,
        seed: dict[str, Any],
        now_iso: str,
    ) -> tuple[str, bool]:
        product_url = _clean(seed.get("product_url")) or "https://www.centrecom.com.au/"
        product_name = _clean(seed.get("product_name"))
        sku = _clean(seed.get("sku")) or None
        attrs_json = json.dumps(seed.get("attributes") or {})

        with self._lock:
            row = self._conn.execute(
                """
                SELECT retailer_product_id
                FROM retailer_products
                WHERE retailer_name = ? AND product_url = ?
                LIMIT 1
                """,
                (CENTRE_COM_RETAILER, product_url),
            ).fetchone()
            if row is None:
                retailer_product_id = _new_id("ret_prod_")
                self._conn.execute(
                    """
                    INSERT INTO retailer_products (
                        retailer_product_id, retailer_name, canonical_product_id,
                        product_name, product_url, sku, attributes_json,
                        created_at, updated_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        retailer_product_id,
                        CENTRE_COM_RETAILER,
                        canonical_product_id,
                        product_name,
                        product_url,
                        sku,
                        attrs_json,
                        now_iso,
                        now_iso,
                        now_iso,
                    ),
                )
                self._conn.commit()
                return retailer_product_id, True

            retailer_product_id = str(row["retailer_product_id"])
            self._conn.execute(
                """
                UPDATE retailer_products
                SET canonical_product_id = ?, product_name = ?, sku = ?,
                    attributes_json = ?, updated_at = ?, last_seen_at = ?
                WHERE retailer_product_id = ?
                """,
                (
                    canonical_product_id,
                    product_name,
                    sku,
                    attrs_json,
                    now_iso,
                    now_iso,
                    retailer_product_id,
                ),
            )
            self._conn.commit()
        return retailer_product_id, False

    def _insert_price_observation(
        self,
        retailer_product_id: str,
        price: float,
        *,
        observed_at: str,
        observation_source: str = OBS_SOURCE_SEED_FALLBACK,
    ) -> None:
        source = _normalize(observation_source)
        if source not in OBSERVATION_SOURCE_VALUES:
            source = OBS_SOURCE_SEED_FALLBACK
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO retailer_price_observations (
                    observation_id, retailer_product_id, observed_at, price,
                    currency, in_stock, observation_source
                ) VALUES (?, ?, ?, ?, 'AUD', 1, ?)
                """,
                (
                    _new_id("ret_price_"),
                    retailer_product_id,
                    observed_at,
                    price,
                    source,
                ),
            )
            self._conn.commit()

    def _upsert_listing_product_match(
        self,
        *,
        match: dict[str, Any],
        category: str,
        matched_retailer_product_id: str,
        confidence: float,
        low_confidence: bool,
        rationale: list[str],
    ) -> dict[str, Any]:
        match_id = _clean(match.get("match_id"))
        listing_id = _clean(match.get("listing_id"))
        if not match_id or not listing_id:
            raise ValueError("match_id and listing_id are required for benchmark linkage")

        warning = "Low-confidence benchmark match requires manual review." if low_confidence else None
        now_iso = _now_iso()

        existing = self._get_listing_product_match(match_id)
        if existing is None:
            review_status = "pending_review" if low_confidence else "auto_accepted"
            with self._lock:
                self._conn.execute(
                    """
                    INSERT INTO listing_product_matches (
                        listing_match_id, match_id, listing_id, mission_id,
                        matched_retailer_product_id, category, confidence,
                        review_status, warning, rationale_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _new_id("list_prod_match_"),
                        match_id,
                        listing_id,
                        _clean(match.get("mission_id")) or None,
                        matched_retailer_product_id,
                        category,
                        round(confidence, 4),
                        review_status,
                        warning,
                        json.dumps(rationale),
                        now_iso,
                        now_iso,
                    ),
                )
                self._conn.commit()
        else:
            existing_review = _normalize(existing.get("review_status"))
            review_status = existing_review if existing_review in REVIEW_STATUSES else "pending_review"
            if review_status == "auto_accepted" and low_confidence:
                review_status = "pending_review"
            with self._lock:
                self._conn.execute(
                    """
                    UPDATE listing_product_matches
                    SET matched_retailer_product_id = ?, category = ?, confidence = ?,
                        review_status = ?, warning = ?, rationale_json = ?, updated_at = ?
                    WHERE match_id = ?
                    """,
                    (
                        matched_retailer_product_id,
                        category,
                        round(confidence, 4),
                        review_status,
                        warning,
                        json.dumps(rationale),
                        now_iso,
                        match_id,
                    ),
                )
                self._conn.commit()

        persisted = self._get_listing_product_match(match_id)
        if persisted is None:
            raise ValueError("failed to persist listing-product match")
        return persisted

    def _insert_listing_benchmark_score(
        self,
        *,
        match: dict[str, Any],
        matched_retailer_product_id: str,
        centre_com_price: float | None,
        centre_com_median_30d: float | None,
        listing_price: float | None,
        delta_pct: float | None,
        freshness_hours: float | None,
        confidence: float,
        low_confidence: bool,
    ) -> None:
        match_id = _clean(match.get("match_id"))
        listing_id = _clean(match.get("listing_id"))
        if not match_id or not listing_id:
            return
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO listing_benchmark_scores (
                    score_id, match_id, listing_id, matched_retailer_product_id,
                    centre_com_price, centre_com_median_30d, listing_price,
                    delta_pct, freshness_hours, confidence, low_confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("bench_score_"),
                    match_id,
                    listing_id,
                    matched_retailer_product_id,
                    centre_com_price,
                    centre_com_median_30d,
                    listing_price,
                    delta_pct,
                    freshness_hours,
                    round(confidence, 4),
                    1 if low_confidence else 0,
                    _now_iso(),
                ),
            )
            self._conn.commit()

    def _get_listing_product_match(self, match_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT *
                FROM listing_product_matches
                WHERE match_id = ?
                LIMIT 1
                """,
                (match_id,),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["rationale"] = _safe_json_loads(item.pop("rationale_json"), [])
        return item
