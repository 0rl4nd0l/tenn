from __future__ import annotations

import asyncio
import os
import threading
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import PROJECT_ROOT
from app.services.marketplace_price_intelligence import (
    MarketplacePriceIntelligenceService,
    detect_listing_junk,
    normalize_product_text,
)
from app.services.ebay_sold_scanner import EbaySoldScanner
from cockpit.storage.state import StateStore


router = APIRouter()
_STATE_STORE_LOCK = threading.Lock()
_STATE_STORES: dict[str, StateStore] = {}


class TrackedProductCreateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    category: str
    brand: str | None = None
    model_family: str | None = None
    variant: str | None = None
    canonical_key: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    negative_terms: list[str] = Field(default_factory=list)
    status: str = "active"


class PriceObservationCreateRequest(BaseModel):
    tracked_product_id: str
    source: str
    observed_at: str | None = None
    source_listing_id: str | None = None
    title: str
    price: float
    currency: str = "AUD"
    url: str | None = None
    location: str | None = None
    seller_type: str | None = None
    condition_label: str | None = None
    match_confidence: float | None = None
    is_transactional: bool = False
    capture_mode: str = "manual"
    provenance: dict[str, Any] = Field(default_factory=dict)
    review_state: str | None = None
    review_reason: str | None = None


class EbaySyncRequest(BaseModel):
    query: str | None = None


class BenchmarkSnapshotRequest(BaseModel):
    retail_anchor: dict[str, Any] = Field(default_factory=dict)


def _service() -> MarketplacePriceIntelligenceService:
    db_path = str(
        os.getenv("COCKPIT_STATE_DB")
        or (PROJECT_ROOT / "data" / "cockpit" / "state.db")
    )
    with _STATE_STORE_LOCK:
        state_store = _STATE_STORES.get(db_path)
        if state_store is None:
            state_store = StateStore(db_path)
            _STATE_STORES[db_path] = state_store
    return MarketplacePriceIntelligenceService(state_store)


def _payload_dict(payload: BaseModel) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.get("/normalize")
async def normalize_product(category: str = Query(...), text: str = Query(...)):
    try:
        normalized = normalize_product_text(category, text)
        junk = detect_listing_junk(title=text, category=normalized["category"])
        return {"normalized": normalized, "junk": junk}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tracked-products")
async def list_tracked_products(
    status: str | None = None,
    category: str | None = None,
):
    try:
        items = await asyncio.to_thread(
            _service().list_tracked_products,
            status=status,
            category=category,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace price intelligence list failed: {str(exc)}",
        ) from exc
    return {"items": items}


@router.post("/tracked-products")
async def create_tracked_product(payload: TrackedProductCreateRequest):
    try:
        return await asyncio.to_thread(_service().create_tracked_product, _payload_dict(payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace tracked product create failed: {str(exc)}",
        ) from exc


@router.get("/tracked-products/{tracked_product_id}")
async def get_tracked_product(tracked_product_id: str):
    product = await asyncio.to_thread(_service().get_tracked_product, tracked_product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="tracked product not found")
    return product


@router.post("/observations")
async def create_observation(payload: PriceObservationCreateRequest):
    try:
        return await asyncio.to_thread(_service().ingest_observation, _payload_dict(payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace observation ingest failed: {str(exc)}",
        ) from exc


@router.get("/observations")
async def list_observations(
    tracked_product_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    items = await asyncio.to_thread(
        _service().list_observations,
        tracked_product_id=tracked_product_id,
        limit=limit,
    )
    return {"items": items}


@router.get("/tracked-products/{tracked_product_id}/timelines")
async def list_timelines(tracked_product_id: str):
    if await asyncio.to_thread(_service().get_tracked_product, tracked_product_id) is None:
        raise HTTPException(status_code=404, detail="tracked product not found")
    items = await asyncio.to_thread(
        _service().list_timelines,
        tracked_product_id=tracked_product_id,
    )
    return {"items": items}


@router.post("/tracked-products/{tracked_product_id}/benchmark-snapshots")
async def rebuild_benchmark_snapshot(
    tracked_product_id: str,
    payload: BenchmarkSnapshotRequest | None = None,
):
    try:
        return await asyncio.to_thread(
            _service().rebuild_benchmark_snapshot,
            tracked_product_id,
            retail_anchor=(payload.retail_anchor if payload else {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tracked-products/{tracked_product_id}/ebay-sync")
async def sync_ebay_sold_data(
    tracked_product_id: str,
    payload: EbaySyncRequest | None = None,
):
    service = _service()
    product = await asyncio.to_thread(service.get_tracked_product, tracked_product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="tracked product not found")
    
    query = (payload.query if payload and payload.query else product["canonical_key"])
    scanner = EbaySoldScanner(service)
    
    # Running synchronously in a thread for now as per project preference for simple routes
    try:
        stats = await scanner.scrape_sold_items(tracked_product_id, query)
        return stats
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"eBay sold sync failed: {str(exc)}",
        ) from exc


@router.get("/tracked-products/{tracked_product_id}/benchmark-snapshots")
async def list_benchmark_snapshots(
    tracked_product_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    if await asyncio.to_thread(_service().get_tracked_product, tracked_product_id) is None:
        raise HTTPException(status_code=404, detail="tracked product not found")
    items = await asyncio.to_thread(
        _service().list_benchmark_snapshots,
        tracked_product_id=tracked_product_id,
        limit=limit,
    )
    return {"items": items}
