"""commentary.py — Backend-authoritative commentary/transcript review endpoints.

Replicates the staging logic from cockpit's TranscriptReviewService using
backend-native services (verify_qdrant, upsert_points, SourceRegistry).
The staging index lives at ~/.tenn/memory/staged_chunks/index.json.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.routes import require_api_key
from app.services.channel_registry import ChannelConfig, ChannelRegistry
from app.services.commentary_ingest import ingest_transcript
from app.services.embeddings import upsert_points, verify_qdrant
from app.services.facebook_marketplace_inspector import (
    MARKETPLACE_TOPIC_TAGS,
    MarketplaceListingCapture,
    build_marketplace_listing_capture,
    inspect_facebook_marketplace_listing,
    is_facebook_marketplace_url,
)
from app.services.youtube_transcript_fetcher import (
    TranscriptUnavailableError,
    _default_fetch_transcript,  # private module-level fetcher; patched directly in tests
    fetch_video_metadata,
    resolve_channel_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["commentary"])

_SOURCE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-:]{1,192}$")
STAGED_CHUNKS_DIR = Path("~/.tenn/memory/staged_chunks").expanduser()
STAGED_CHUNKS_INDEX = STAGED_CHUNKS_DIR / "index.json"


def _validate_source_id(source_id: str) -> str:
    cleaned = (source_id or "").strip()
    if not cleaned or not _SOURCE_ID_RE.match(cleaned):
        raise HTTPException(status_code=400, detail="invalid source_id format")
    return cleaned


def _load_index() -> dict[str, Any]:
    if not STAGED_CHUNKS_INDEX.exists():
        return {}
    try:
        return json.loads(STAGED_CHUNKS_INDEX.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_index(index: dict[str, Any]) -> None:
    STAGED_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    STAGED_CHUNKS_INDEX.write_text(json.dumps(index, indent=2), "utf-8")


def _update_source_registry(source_id: str, status: str) -> None:
    """Best-effort registry status update."""
    try:
        from app.services.source_registry import SourceRegistry

        registry = SourceRegistry()
        entry = registry.get(source_id)
        if entry:
            entry["review_status"] = status
            registry.upsert(entry)
    except Exception:
        logger.warning("Failed to update registry status for %s", source_id)


# ---------------------------------------------------------------------------
# GET /api/commentary/transcripts/pending
# ---------------------------------------------------------------------------

@router.get("/transcripts/pending")
def get_pending_transcripts() -> dict[str, Any]:
    index = _load_index()
    pending = [
        {"source_id": sid, **meta}
        for sid, meta in sorted(index.items(), key=lambda kv: kv[1].get("staged_at", ""))
    ]
    return {"pending": pending, "count": len(pending)}


# ---------------------------------------------------------------------------
# POST /api/commentary/transcripts/{source_id}/approve
# ---------------------------------------------------------------------------

@router.post(
    "/transcripts/{source_id}/approve",
    dependencies=[Depends(require_api_key)],
)
def approve_transcript(source_id: str) -> dict[str, Any]:
    sid = _validate_source_id(source_id)
    index = _load_index()
    entry = index.get(sid)
    if not entry:
        raise HTTPException(status_code=404, detail=f"source_id not found in staging: {sid}")

    staged_path = Path(entry["path"])
    if not staged_path.exists():
        del index[sid]
        _save_index(index)
        raise HTTPException(status_code=404, detail=f"staged file missing: {staged_path}")

    # Read JSONL staged points
    points: list[dict[str, Any]] = []
    try:
        for line in staged_path.read_text("utf-8").splitlines():
            line = line.strip()
            if line:
                points.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"failed to read staged file: {exc}") from exc

    if not points:
        del index[sid]
        _save_index(index)
        staged_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="staged file is empty")

    # Upsert to Qdrant
    try:
        client = verify_qdrant()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"qdrant_unavailable: {exc}") from exc

    collection = entry.get("collection_name", "commentary_chunks")
    result = upsert_points(client, collection, points)

    # Update source registry
    _update_source_registry(sid, "approved")

    # Clean up staging
    staged_path.unlink(missing_ok=True)
    del index[sid]
    _save_index(index)

    logger.info("Approved and indexed %d chunks for %s", len(points), sid)
    return {
        "ok": True,
        "source_id": sid,
        "points_upserted": result.get("written_points", len(points)),
        "collection": collection,
    }


# ---------------------------------------------------------------------------
# POST /api/commentary/transcripts/{source_id}/reject
# ---------------------------------------------------------------------------

@router.post(
    "/transcripts/{source_id}/reject",
    dependencies=[Depends(require_api_key)],
)
def reject_transcript(source_id: str) -> dict[str, Any]:
    sid = _validate_source_id(source_id)
    index = _load_index()
    entry = index.get(sid)
    if not entry:
        raise HTTPException(status_code=404, detail=f"source_id not found in staging: {sid}")

    staged_path = Path(entry["path"])
    staged_path.unlink(missing_ok=True)
    del index[sid]
    _save_index(index)

    _update_source_registry(sid, "rejected")

    logger.info("Rejected and purged staged chunks for %s", sid)
    return {"ok": True, "source_id": sid}


# ---------------------------------------------------------------------------
# POST /api/commentary/transcripts/purge-expired
# ---------------------------------------------------------------------------

@router.post(
    "/transcripts/purge-expired",
    dependencies=[Depends(require_api_key)],
)
def purge_expired_transcripts(
    max_age_days: int = Query(default=7, ge=1, le=90),
) -> dict[str, Any]:
    index = _load_index()
    now = datetime.now(timezone.utc)
    purged: list[str] = []

    for sid, meta in list(index.items()):
        staged_at = meta.get("staged_at", "")
        if not staged_at:
            continue
        try:
            ts = datetime.fromisoformat(staged_at.replace("Z", "+00:00"))
            age_days = (now - ts).total_seconds() / 86400
            if age_days > max_age_days:
                path = Path(meta.get("path", ""))
                path.unlink(missing_ok=True)
                del index[sid]
                purged.append(sid)
                logger.info("Purged expired staged source: %s (%.1f days old)", sid, age_days)
        except (ValueError, TypeError):
            continue

    if purged:
        _save_index(index)

    return {"purged": purged, "count": len(purged)}


# ---------------------------------------------------------------------------
# POST /api/commentary/ingest-url
# ---------------------------------------------------------------------------

_YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=|youtu\.be/)[A-Za-z0-9_\-]{11}"
)


class AddChannelRequest(BaseModel):
    name_or_id: str
    credibility_weight: float = 0.55
    enabled: bool = True


class IngestUrlRequest(BaseModel):
    url: str


class InspectMarketplaceRequest(BaseModel):
    url: str


class IngestMarketplaceSnapshotRequest(BaseModel):
    url: str
    captured_at: str | None = None
    title: str | None = None
    price: str | None = None
    seller_name: str | None = None
    location: str | None = None
    description: str | None = None
    raw_text_lines: list[str] = []


def _stage_marketplace_capture(capture: MarketplaceListingCapture) -> dict[str, Any]:
    try:
        result = ingest_transcript(
            transcript_text=capture.transcript_text,
            source_name=capture.title or "Facebook Marketplace listing",
            source_type="market_commentary",
            speaker=capture.seller_name or "Facebook Marketplace",
            published_at=capture.captured_at,
            topic_tags=list(MARKETPLACE_TOPIC_TAGS),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"marketplace processing failed: {exc}"
        ) from exc

    return {
        **result,
        "source_name": capture.title or "Facebook Marketplace listing",
        "listing_title": capture.title,
        "price": capture.price,
        "seller_name": capture.seller_name,
        "location": capture.location,
        "captured_at": capture.captured_at,
        "screenshot_path": capture.screenshot_path,
        "webpage_url": capture.url,
        "source_kind": "concat",
    }


@router.post(
    "/ingest-url",
    dependencies=[Depends(require_api_key)],
)
def ingest_url(body: IngestUrlRequest) -> dict[str, Any]:
    url = str(body.url or "").strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")
    if not _YOUTUBE_URL_RE.search(url):
        raise HTTPException(
            status_code=422, detail="url must be a YouTube watch or short URL"
        )

    try:
        video = fetch_video_metadata(url)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502, detail=f"metadata fetch failed: {exc}"
        ) from exc

    try:
        transcript_text = _default_fetch_transcript(video)
    except TranscriptUnavailableError as exc:
        raise HTTPException(
            status_code=422, detail=f"transcript unavailable: {exc}"
        ) from exc

    try:
        result = ingest_transcript(
            transcript_text=transcript_text,
            source_name=video.title,
            source_type="youtube_transcript",
            speaker=video.channel_name,
            published_at=video.published_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"transcript processing failed: {exc}") from exc

    return {
        **result,
        "video_title": video.title,
        "channel": video.channel_name,
        "published_at": video.published_at,
        "webpage_url": video.webpage_url,
    }


@router.post(
    "/channels",
    dependencies=[Depends(require_api_key)],
)
def add_watched_channel(body: AddChannelRequest) -> dict[str, Any]:
    name_or_id = str(body.name_or_id or "").strip()
    if not name_or_id:
        raise HTTPException(status_code=422, detail="name_or_id is required")

    try:
        channel_id, canonical_name = resolve_channel_id(name_or_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    registry = ChannelRegistry()
    existing = registry.channels()
    already_existed = any(c.channel_id == channel_id for c in existing)

    if not already_existed:
        new_channel = ChannelConfig(
            name=canonical_name,
            channel_id=channel_id,
            credibility_weight=float(body.credibility_weight),
            enabled=body.enabled,
        )
        registry.save([*existing, new_channel])

    return {
        "channel_id": channel_id,
        "name": canonical_name,
        "enabled": body.enabled,
        "credibility_weight": body.credibility_weight,
        "already_existed": already_existed,
    }


@router.get(
    "/channels",
    dependencies=[Depends(require_api_key)],
)
def list_watched_channels() -> dict[str, Any]:
    registry = ChannelRegistry()
    channels = registry.channels()
    return {
        "channels": [c.to_dict() for c in channels],
        "count": len(channels),
    }


@router.post(
    "/inspect-marketplace",
    dependencies=[Depends(require_api_key)],
)
def inspect_marketplace(body: InspectMarketplaceRequest) -> dict[str, Any]:
    url = str(body.url or "").strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")
    if not is_facebook_marketplace_url(url):
        raise HTTPException(
            status_code=422,
            detail="url must be a Facebook Marketplace item URL",
        )

    try:
        capture = inspect_facebook_marketplace_listing(url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        if detail.startswith("marketplace_login_required:"):
            raise HTTPException(status_code=409, detail=detail) from exc
        if detail.startswith("marketplace_browser_unavailable:"):
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=502, detail=detail) from exc

    return _stage_marketplace_capture(capture)


@router.post(
    "/ingest-marketplace-snapshot",
    dependencies=[Depends(require_api_key)],
)
def ingest_marketplace_snapshot(
    body: IngestMarketplaceSnapshotRequest,
) -> dict[str, Any]:
    try:
        capture = build_marketplace_listing_capture(
            url=body.url,
            captured_at=body.captured_at,
            title=body.title,
            price=body.price,
            seller_name=body.seller_name,
            location=body.location,
            description=body.description,
            screenshot_path="",
            raw_text_lines=body.raw_text_lines,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _stage_marketplace_capture(capture)
