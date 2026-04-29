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
