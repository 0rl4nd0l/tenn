from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.marketplace_price_intelligence import router
from app.routes import marketplace_price_intelligence as price_intelligence_routes
from app.services.marketplace_price_intelligence import (
    MarketplacePriceIntelligenceService,
    detect_listing_junk,
    listing_fingerprint,
    normalize_product_text,
)
from cockpit.storage.state import StateStore


def _state_store(tmp_path: Path) -> StateStore:
    return StateStore(str(tmp_path / "state.db"))


def _service(tmp_path: Path) -> MarketplacePriceIntelligenceService:
    return MarketplacePriceIntelligenceService(_state_store(tmp_path))


def _tracked_gpu(service: MarketplacePriceIntelligenceService) -> dict:
    return service.create_tracked_product(
        {
            "category": "gpu",
            "brand": "NVIDIA",
            "model_family": "RTX 4070",
            "variant": "SUPER 12GB",
            "aliases": ["4070 super"],
            "negative_terms": ["box only"],
        }
    )


def test_price_observation_schema_adds_transactional_column_to_existing_table(
    tmp_path: Path,
) -> None:
    store = _state_store(tmp_path)
    conn = store.conn
    conn.execute(
        """
        CREATE TABLE marketplace_price_observations (
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
            capture_mode TEXT NOT NULL DEFAULT 'manual',
            provenance_json TEXT NOT NULL DEFAULT '{}',
            review_state TEXT NOT NULL DEFAULT 'pending_review',
            review_reason TEXT,
            junk_flags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()

    service = MarketplacePriceIntelligenceService(store)
    columns = {
        str(row[1])
        for row in conn.execute(
            "PRAGMA table_info(marketplace_price_observations)"
        ).fetchall()
    }
    assert "is_transactional" in columns

    product = _tracked_gpu(service)
    observation = service.ingest_observation(
        {
            "tracked_product_id": product["tracked_product_id"],
            "source": "ebay_sold",
            "observed_at": "2026-04-20T10:00:00+00:00",
            "title": "RTX 4070 Super sold listing",
            "price": 610,
            "is_transactional": True,
        }
    )
    assert observation["is_transactional"] is True


def test_product_normalizer_extracts_pc_part_attributes() -> None:
    gpu = normalize_product_text("gpu", "MSI GeForce RTX 4070 Ti Super 16GB")
    assert gpu["attributes"]["vendor"] == "NVIDIA"
    assert gpu["attributes"]["chip_model"] == "RTX 4070"
    assert gpu["attributes"]["suffix"] == "TI SUPER"
    assert gpu["attributes"]["vram_gb"] == 16

    cpu = normalize_product_text("cpu", "AMD Ryzen 7 7800X3D")
    assert cpu["attributes"]["family"] == "Ryzen 7"
    assert cpu["attributes"]["exact_sku"] == "Ryzen 7 7800X3D"
    assert cpu["attributes"]["suffix"] == "X3D"

    ram = normalize_product_text("ram", "Corsair 32GB 2x16GB DDR5 6000MHz CL30")
    assert ram["attributes"]["ddr_generation"] == 5
    assert ram["attributes"]["total_capacity_gb"] == 32
    assert ram["attributes"]["stick_count"] == 2
    assert ram["attributes"]["speed_mhz"] == 6000
    assert ram["attributes"]["cas_latency"] == 30

    ssd = normalize_product_text("ssd", "Samsung 990 Pro 2TB NVMe Gen4")
    assert ssd["attributes"]["brand"] == "Samsung"
    assert ssd["attributes"]["model"] == "990 PRO"
    assert ssd["attributes"]["capacity_gb"] == 2000
    assert ssd["attributes"]["interface"] == "NVMe"
    assert ssd["attributes"]["pcie_generation"] == 4

    nv2 = normalize_product_text("nvme_m2", "Kingston NV2 2TB NVMe Gen4")
    assert nv2["category"] == "ssd"
    assert nv2["attributes"]["brand"] == "Kingston"
    assert nv2["attributes"]["model"] == "NV2"


def test_junk_detection_flags_negative_listing_patterns() -> None:
    result = detect_listing_junk(
        title="WTB broken RTX 4070 box only or swap for parts",
        price=1,
        category="gpu",
    )

    assert result["is_junk"] is True
    assert "wanted" in result["flags"]
    assert "swap_trade" in result["flags"]
    assert "broken_parts" in result["flags"]
    assert "box_only" in result["flags"]
    assert "placeholder_price" in result["flags"]


def test_listing_fingerprint_prefers_listing_id_then_url_then_text() -> None:
    by_id_a = listing_fingerprint(source="facebook", source_listing_id="ABC123")
    by_id_b = listing_fingerprint(
        source="facebook",
        source_listing_id="abc123",
        title="Different",
        price=10,
    )
    assert by_id_a == by_id_b

    by_url_a = listing_fingerprint(
        source="facebook",
        url="https://www.facebook.com/marketplace/item/123/?tracking=1",
    )
    by_url_b = listing_fingerprint(
        source="facebook",
        url="https://www.facebook.com/marketplace/item/123/",
    )
    assert by_url_a == by_url_b

    text_a = listing_fingerprint(
        source="manual",
        title="RTX 4070 Super",
        price=650,
        location="Melbourne",
    )
    text_b = listing_fingerprint(
        source="manual",
        title="RTX 4070 Super",
        price=651,
        location="Melbourne",
    )
    assert text_a != text_b


def test_candidate_product_reuse_and_listing_candidate_resolution(tmp_path: Path) -> None:
    service = _service(tmp_path)
    rtx_3090_spec = {
        "canonical_key": "gpu-nvidia-rtx-3090-24gb",
        "category": "gpu",
        "brand": "NVIDIA",
        "model_family": "RTX 3090",
        "variant": "24GB",
        "attributes": {"vram_gb": 24, "vendor": "NVIDIA"},
        "aliases": ["RTX 3090", "RTX 3090 24GB"],
    }
    rtx_4090_spec = {
        "canonical_key": "gpu-nvidia-rtx-4090-24gb",
        "category": "gpu",
        "brand": "NVIDIA",
        "model_family": "RTX 4090",
        "variant": "24GB",
        "attributes": {"vram_gb": 24, "vendor": "NVIDIA"},
        "aliases": ["RTX 4090", "RTX 4090 24GB"],
    }

    rtx_3090 = service.get_or_create_tracked_product(rtx_3090_spec)
    reused = service.get_or_create_tracked_product(rtx_3090_spec)
    rtx_4090 = service.get_or_create_tracked_product(rtx_4090_spec)

    assert reused["tracked_product_id"] == rtx_3090["tracked_product_id"]

    contexts = [
        {
            "candidate": {"fit_score": 95, "fit_label": "strong_fit"},
            "tracked_product": rtx_3090,
        },
        {
            "candidate": {"fit_score": 90, "fit_label": "fit"},
            "tracked_product": rtx_4090,
        },
    ]
    resolved = service.resolve_match_candidate(
        {
            "title": "NVIDIA RTX 3090 24GB",
            "raw_text_snapshot": "Used RTX 3090 24GB working condition.",
            "price": "$950",
        },
        contexts,
    )
    assert resolved["matched"] is True
    assert resolved["tracked_product"]["tracked_product_id"] == rtx_3090["tracked_product_id"]

    mismatch = service.resolve_match_candidate(
        {
            "title": "RTX 4070 Super 12GB",
            "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
            "price": "$600",
        },
        contexts,
    )
    assert mismatch["matched"] is False


def test_tracked_product_category_aliases_normalize_to_storage_contract(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    product = service.create_tracked_product(
        {
            "category": "nvme_m2",
            "brand": "Kingston",
            "model_family": "NV2",
            "variant": "2TB Gen4",
            "attributes": {"capacity_gb": 2000, "interface": "NVMe"},
        }
    )

    assert product["category"] == "ssd"
    listed = service.list_tracked_products(category="nvme_m2")
    assert listed[0]["tracked_product_id"] == product["tracked_product_id"]


def test_observation_ingest_updates_listing_timeline(tmp_path: Path) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)

    first = service.ingest_observation(
        {
            "tracked_product_id": product["tracked_product_id"],
            "source": "facebook",
            "observed_at": "2026-04-20T10:00:00+00:00",
            "source_listing_id": "listing-1",
            "title": "RTX 4070 Super 12GB",
            "price": 700,
            "review_state": "accepted",
        }
    )
    second = service.ingest_observation(
        {
            "tracked_product_id": product["tracked_product_id"],
            "source": "facebook",
            "observed_at": "2026-04-21T10:00:00+00:00",
            "source_listing_id": "listing-1",
            "title": "RTX 4070 Super 12GB price drop",
            "price": 650,
            "review_state": "accepted",
        }
    )

    assert first["listing_fingerprint"] == second["listing_fingerprint"]
    timelines = service.list_timelines(tracked_product_id=product["tracked_product_id"])
    assert len(timelines) == 1
    assert timelines[0]["latest_price"] == 650
    assert timelines[0]["price_change_count"] == 1
    assert len(timelines[0]["price_history"]) == 2


def test_observation_ingest_if_new_or_changed_skips_same_price(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    payload = {
        "tracked_product_id": product["tracked_product_id"],
        "source": "facebook",
        "observed_at": "2026-04-20T10:00:00+00:00",
        "source_listing_id": "listing-1",
        "title": "RTX 4070 Super 12GB",
        "price": 700,
        "capture_mode": "scanner",
        "review_state": "accepted",
    }

    first = service.ingest_observation_if_new_or_changed(payload)
    duplicate = service.ingest_observation_if_new_or_changed(
        {**payload, "observed_at": "2026-04-21T10:00:00+00:00"}
    )
    changed = service.ingest_observation_if_new_or_changed(
        {
            **payload,
            "observed_at": "2026-04-22T10:00:00+00:00",
            "price": 650,
        }
    )

    observations = service.list_observations(
        tracked_product_id=product["tracked_product_id"]
    )
    timelines = service.list_timelines(tracked_product_id=product["tracked_product_id"])
    assert first["created"] is True
    assert duplicate["created"] is False
    assert duplicate["deduped"] is True
    assert changed["created"] is True
    assert len(observations) == 2
    assert timelines[0]["latest_price"] == 650
    assert timelines[0]["price_change_count"] == 1


def test_benchmark_rollup_freshness_and_confidence_states(tmp_path: Path) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    prices = [620, 640, 660, 680, 700]
    for idx, price in enumerate(prices):
        service.ingest_observation(
            {
                "tracked_product_id": product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"listing-{idx}",
                "title": f"RTX 4070 Super 12GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )

    snapshot = service.rebuild_benchmark_snapshot(product["tracked_product_id"])

    assert snapshot["total_sample_size"] == 5
    assert snapshot["source_sample_sizes"] == {"facebook": 5}
    assert snapshot["rollups"]["30d"]["sample_size"] == 5
    assert snapshot["used_median"] == 660
    assert snapshot["fair_range_low"] == 640
    assert snapshot["fair_range_high"] == 680
    assert snapshot["freshness_status"] in {"fresh", "aging"}
    assert snapshot["confidence_label"] in {"medium", "high"}


def test_low_data_snapshot_is_provisional(tmp_path: Path) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    service.ingest_observation(
        {
            "tracked_product_id": product["tracked_product_id"],
            "source": "facebook",
            "observed_at": "2026-04-20T10:00:00+00:00",
            "source_listing_id": "single",
            "title": "RTX 4070 Super",
            "price": 700,
            "review_state": "accepted",
        }
    )

    snapshot = service.rebuild_benchmark_snapshot(product["tracked_product_id"])

    assert snapshot["freshness_status"] == "low_data"
    assert snapshot["confidence_label"] == "low"
    assert snapshot["warnings"]


def test_match_value_assessment_uses_latest_snapshot_without_changing_match_score(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    for idx, price in enumerate([620, 640, 660, 680, 700]):
        service.ingest_observation(
            {
                "tracked_product_id": product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"value-{idx}",
                "title": f"RTX 4070 Super 12GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    snapshot = service.rebuild_benchmark_snapshot(product["tracked_product_id"])
    match = {
        "match_id": "mp_match_value",
        "mission_id": "mp_mission_value",
        "title": "NVIDIA RTX 4070 Super 12GB",
        "price": "$610",
        "price_value": 610,
        "score": 44,
        "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
    }

    value = service.upsert_match_value_assessment(
        match=match,
        tracked_product=product,
        snapshot=snapshot,
    )

    assert match["score"] == 44
    assert value["state"] == "scored"
    assert value["value_score"] is not None
    assert value["value_label"] in {"excellent", "good"}
    assert value["benchmark_snapshot_id"] == snapshot["snapshot_id"]
    assert value["fair_low"] == 640
    assert value["fair_high"] == 680
    assert value["used_median"] == 660
    assert service.get_match_value_assessment(match["match_id"])["value_score"] == value["value_score"]


def test_match_price_comparison_reports_used_and_retail_deltas(tmp_path: Path) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    for idx, price in enumerate([620, 640, 660, 680, 700]):
        service.ingest_observation(
            {
                "tracked_product_id": product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"comparison-{idx}",
                "title": f"RTX 4070 Super 12GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    snapshot = service.rebuild_benchmark_snapshot(
        product["tracked_product_id"],
        retail_anchor={"source": "centre_com", "current_price": 999},
    )
    match = {
        "match_id": "mp_match_comparison",
        "mission_id": "mp_mission_comparison",
        "title": "NVIDIA RTX 4070 Super 12GB",
        "price": "$610",
        "price_value": 610,
        "score": 44,
        "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
    }
    value = service.assess_match_value(
        match=match,
        tracked_product=product,
        snapshot=snapshot,
    )

    comparison = service.build_match_price_comparison(
        match=match,
        value_context=value,
    )

    assert comparison["listing_price"] == 610
    assert comparison["used_market_median"] == 660
    assert comparison["retail_anchor_price"] == 999
    assert comparison["retail_anchor_label"] == "centre_com"
    assert comparison["delta_vs_used_median"] == {"amount": -50.0, "percent": -7.6}
    assert comparison["delta_vs_retail_anchor"] == {"amount": -389.0, "percent": -38.9}
    assert comparison["primary_anchor"] == {"kind": "used_market_median", "price": 660}
    assert comparison["verdict"] == "discount"
    assert comparison["color"] == "emerald"
    assert comparison["comparison_state"] == "used_market_comparison"
    assert comparison["unavailable_reason"] is None
    assert comparison["next_action"] is None


def test_match_price_comparison_explains_missing_benchmark_anchor(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    comparison = service.build_match_price_comparison(
        match={
            "match_id": "mp_match_listing_only",
            "mission_id": "mp_mission_listing_only",
            "title": "Kingston NV2 2TB NVMe SSD",
            "price": "AU$300 Kingston NV2 2TB NVMe SSD Melbourne, VIC",
            "price_value": 300,
            "raw_text_snapshot": "Kingston NV2 2TB NVMe SSD.",
        },
        value_context=None,
    )

    assert comparison["listing_price"] == 300
    assert comparison["used_market_median"] is None
    assert comparison["retail_anchor_price"] is None
    assert comparison["primary_anchor"] == {"kind": "none", "price": None}
    assert comparison["verdict"] == "unavailable"
    assert comparison["comparison_state"] == "missing_benchmark_anchor"
    assert "Listing price was captured" in comparison["unavailable_reason"]
    assert "tracked product benchmark" in comparison["next_action"]


def test_match_price_comparison_ignores_pending_low_confidence_retail_benchmark(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    match = {
        "match_id": "mp_match_pending_retail",
        "mission_id": "mp_mission_pending_retail",
        "title": "Corsair Vengeance LPX 32GB DDR4",
        "price": "$50",
        "price_value": 50,
        "raw_text_snapshot": "Corsair Vengeance LPX 32GB DDR4.",
        "benchmark": {
            "source": "centre_com",
            "matched_product": "Corsair Vengeance 32GB DDR5-6000 CL36 Memory Kit",
            "current_price": 189,
            "confidence": 0.4,
            "low_confidence": True,
            "review_status": "pending_review",
        },
    }

    comparison = service.build_match_price_comparison(match=match, value_context=None)

    assert comparison["listing_price"] == 50
    assert comparison["retail_anchor_price"] is None
    assert comparison["primary_anchor"] == {"kind": "none", "price": None}
    assert comparison["verdict"] == "unavailable"
    assert comparison["comparison_state"] == "retail_anchor_needs_review"
    assert comparison["ignored_retail_anchor"]["price"] == 189
    assert comparison["ignored_retail_anchor"]["review_status"] == "pending_review"
    assert "not used" in comparison["unavailable_reason"]


def test_match_price_comparison_uses_manually_accepted_low_confidence_retail_benchmark(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    comparison = service.build_match_price_comparison(
        match={
            "match_id": "mp_match_accepted_retail",
            "mission_id": "mp_mission_accepted_retail",
            "title": "Corsair Vengeance LPX 32GB DDR4",
            "price": "$50",
            "price_value": 50,
            "raw_text_snapshot": "Corsair Vengeance LPX 32GB DDR4.",
            "benchmark": {
                "source": "centre_com",
                "matched_product": "Corsair Vengeance 32GB DDR5-6000 CL36 Memory Kit",
                "current_price": 189,
                "confidence": 0.4,
                "low_confidence": True,
                "review_status": "accepted",
            },
        },
        value_context=None,
    )

    assert comparison["retail_anchor_price"] == 189
    assert comparison["comparison_state"] == "retail_anchor_only"
    assert comparison["verdict"] == "below_retail_anchor"
    assert comparison["ignored_retail_anchor"] is None


def test_value_assessment_reports_no_snapshot_low_data_and_stale_states(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    match = {
        "match_id": "mp_match_states",
        "mission_id": "mp_mission_states",
        "title": "RTX 4070 Super 12GB",
        "price": "$650",
        "raw_text_snapshot": "RTX 4070 Super 12GB working condition.",
    }

    no_snapshot = service.assess_match_value(
        match=match,
        tracked_product=product,
        snapshot=None,
    )
    assert no_snapshot["state"] == "value_unavailable"
    assert no_snapshot["value_confidence"] == "low"

    service.ingest_observation(
        {
            "tracked_product_id": product["tracked_product_id"],
            "source": "facebook",
            "observed_at": "2026-04-20T10:00:00+00:00",
            "source_listing_id": "low-data",
            "title": "RTX 4070 Super",
            "price": 700,
            "review_state": "accepted",
        }
    )
    low_data = service.rebuild_benchmark_snapshot(product["tracked_product_id"])
    low_data_value = service.assess_match_value(
        match=match,
        tracked_product=product,
        snapshot=low_data,
    )
    assert low_data_value["state"] == "insufficient_data"
    assert low_data_value["value_confidence"] == "low"

    stale_dir = tmp_path / "stale"
    stale_dir.mkdir()
    stale_service = _service(stale_dir)
    stale_product = _tracked_gpu(stale_service)
    for idx, price in enumerate([600, 620, 640]):
        stale_service.ingest_observation(
            {
                "tracked_product_id": stale_product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-01-0{idx + 1}T10:00:00+00:00",
                "source_listing_id": f"stale-{idx}",
                "title": f"RTX 4070 Super {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    stale_snapshot = stale_service.rebuild_benchmark_snapshot(
        stale_product["tracked_product_id"]
    )
    stale_value = stale_service.assess_match_value(
        match=match,
        tracked_product=stale_product,
        snapshot=stale_snapshot,
    )
    assert stale_value["state"] == "stale_benchmark"
    assert stale_value["value_confidence"] == "low"


def test_value_assessment_reports_ambiguous_variant_and_retail_anchor_only(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    product = _tracked_gpu(service)
    retail_only_snapshot = service.rebuild_benchmark_snapshot(
        product["tracked_product_id"],
        retail_anchor={"source": "centre_com", "price": 1099},
    )
    retail_only = service.assess_match_value(
        match={
            "match_id": "mp_match_retail",
            "mission_id": "mp_mission_retail",
            "title": "RTX 4070 Super 12GB",
            "price": "$650",
            "raw_text_snapshot": "RTX 4070 Super 12GB working condition.",
        },
        tracked_product=product,
        snapshot=retail_only_snapshot,
    )
    assert retail_only["state"] == "retail_anchor_only"
    assert retail_only["value_score"] is None
    assert retail_only["retail_anchor_price"] == 1099

    for idx, price in enumerate([620, 640, 660]):
        service.ingest_observation(
            {
                "tracked_product_id": product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"ambiguous-{idx}",
                "title": f"RTX 4070 Super {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    snapshot = service.rebuild_benchmark_snapshot(product["tracked_product_id"])
    ambiguous = service.assess_match_value(
        match={
            "match_id": "mp_match_ambiguous",
            "mission_id": "mp_mission_ambiguous",
            "title": "Gaming PC tower",
            "price": "$500",
            "raw_text_snapshot": "Full desktop tower with unspecified GPU.",
        },
        tracked_product=product,
        snapshot=snapshot,
    )
    assert ambiguous["state"] == "ambiguous_variant"
    assert ambiguous["value_confidence"] == "low"


def test_standalone_api_supports_foundation_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COCKPIT_STATE_DB", str(tmp_path / "state.db"))
    price_intelligence_routes._STATE_STORES.clear()

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit/marketplace/price-intelligence")
    client = TestClient(app)

    create_product = client.post(
        "/api/cockpit/marketplace/price-intelligence/tracked-products",
        json={
            "category": "ssd",
            "brand": "Samsung",
            "model_family": "990 Pro",
            "variant": "2TB",
            "aliases": ["990 pro 2tb"],
        },
    )
    assert create_product.status_code == 200
    product = create_product.json()
    assert product["category"] == "ssd"
    assert product["attributes"]["capacity_gb"] == 2000

    list_products = client.get(
        "/api/cockpit/marketplace/price-intelligence/tracked-products"
    )
    assert list_products.status_code == 200
    assert list_products.json()["items"][0]["tracked_product_id"] == product["tracked_product_id"]

    create_observation = client.post(
        "/api/cockpit/marketplace/price-intelligence/observations",
        json={
            "tracked_product_id": product["tracked_product_id"],
            "source": "manual",
            "observed_at": "2026-04-20T10:00:00+00:00",
            "source_listing_id": "ssd-1",
            "title": "Samsung 990 Pro 2TB NVMe Gen4",
            "price": 180,
            "review_state": "accepted",
        },
    )
    assert create_observation.status_code == 200
    assert create_observation.json()["listing_fingerprint"]

    observations = client.get(
        "/api/cockpit/marketplace/price-intelligence/observations",
        params={"tracked_product_id": product["tracked_product_id"]},
    )
    assert observations.status_code == 200
    assert observations.json()["items"][0]["title"] == "Samsung 990 Pro 2TB NVMe Gen4"

    timelines = client.get(
        "/api/cockpit/marketplace/price-intelligence/"
        f"tracked-products/{product['tracked_product_id']}/timelines"
    )
    assert timelines.status_code == 200
    assert timelines.json()["items"][0]["latest_price"] == 180

    snapshot = client.post(
        "/api/cockpit/marketplace/price-intelligence/"
        f"tracked-products/{product['tracked_product_id']}/benchmark-snapshots"
    )
    assert snapshot.status_code == 200
    assert snapshot.json()["total_sample_size"] == 1

    snapshots = client.get(
        "/api/cockpit/marketplace/price-intelligence/"
        f"tracked-products/{product['tracked_product_id']}/benchmark-snapshots"
    )
    assert snapshots.status_code == 200
    assert snapshots.json()["items"][0]["snapshot_id"] == snapshot.json()["snapshot_id"]
