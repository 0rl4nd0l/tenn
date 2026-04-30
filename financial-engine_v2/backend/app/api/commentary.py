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
from pydantic import BaseModel, Field

from app.api.routes import require_api_key
from app.services.channel_registry import ChannelConfig, ChannelRegistry
from app.services.commentary_ingest import ingest_transcript
from app.services.commentary_memo_extractor import load_commentary_memos
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
    YoutubeChannelResolutionError,
    _default_fetch_transcript,  # private module-level fetcher; patched directly in tests
    fetch_video_metadata,
    list_recent_channel_videos,
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


def _point_payload(point: dict[str, Any]) -> dict[str, Any]:
    payload = point.get("payload") if isinstance(point, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _point_text(point: dict[str, Any]) -> str:
    return str(_point_payload(point).get("text") or "").strip()


def _point_chunk_id(point: dict[str, Any], source_id: str) -> str:
    payload = _point_payload(point)
    chunk_id = str(payload.get("chunk_id") or "").strip()
    if chunk_id:
        return chunk_id
    try:
        chunk_index = int(payload.get("chunk_index", 0) or 0)
    except (TypeError, ValueError):
        chunk_index = 0
    return f"{source_id}:{chunk_index}"


def _citation_for_point(point: dict[str, Any], source_id: str) -> dict[str, Any]:
    return {
        "chunk_id": _point_chunk_id(point, source_id),
        "segment_start_seconds": 0,
    }


def _load_staged_points_for_source(
    source_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    index = _load_index()
    entry = index.get(source_id)
    if not entry:
        return [], None

    staged_path = Path(str(entry.get("path") or ""))
    if not staged_path.exists():
        raise HTTPException(status_code=404, detail=f"staged file missing: {staged_path}")

    points: list[dict[str, Any]] = []
    try:
        for raw_line in staged_path.read_text("utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            point = json.loads(line)
            if not isinstance(point, dict):
                continue
            payload = _point_payload(point)
            payload_source_id = str(payload.get("source_id") or source_id).strip()
            if payload_source_id == source_id:
                points.append(point)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"failed to read staged file: {exc}") from exc

    return points, dict(entry)


def _load_commentary_memo_for_source(source_id: str) -> tuple[dict[str, Any] | None, str]:
    try:
        rows = load_commentary_memos()
    except Exception as exc:  # noqa: BLE001 - memo store errors are surfaced in response metadata
        logger.warning("Failed to load commentary memos for %s: %s", source_id, exc)
        return None, f"error: {exc}"

    for row in rows:
        if str(row.get("source_id") or "").strip() == source_id:
            return dict(row), "ready"
    return None, "missing"


def _clean_takeaway_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" -\t\r\n")
    if len(text) > 360:
        text = text[:357].rstrip() + "..."
    return text


def _citation_for_text(
    text: str,
    points: list[dict[str, Any]],
    source_id: str,
) -> list[dict[str, Any]]:
    if not points:
        return []
    needle = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    if not needle:
        return [_citation_for_point(points[0], source_id)]

    for point in points:
        haystack = re.sub(r"\s+", " ", _point_text(point)).lower()
        if needle and needle in haystack:
            return [_citation_for_point(point, source_id)]

    words = {
        token
        for token in re.findall(r"[a-z0-9]{4,}", needle)
        if token not in {"this", "that", "with", "from", "they", "have", "will"}
    }
    if not words:
        return [_citation_for_point(points[0], source_id)]

    best_point = points[0]
    best_score = -1
    for point in points:
        haystack_words = set(re.findall(r"[a-z0-9]{4,}", _point_text(point).lower()))
        score = len(words & haystack_words)
        if score > best_score:
            best_point = point
            best_score = score
    return [_citation_for_point(best_point, source_id)]


def _memo_takeaways(
    memo: dict[str, Any],
    points: list[dict[str, Any]],
    source_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    fields = (
        ("claims", "Claim"),
        ("catalysts", "Catalyst"),
        ("risks", "Risk"),
    )
    for field, label in fields:
        values = memo.get(field)
        if not isinstance(values, list):
            continue
        for value in values:
            cleaned = _clean_takeaway_text(value)
            key = cleaned.lower()
            if not cleaned or key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "text": f"{label}: {cleaned}",
                    "citations": _citation_for_text(cleaned, points, source_id),
                    "source_field": field,
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


_TAKEAWAY_KEYWORDS = {
    "acquisition",
    "balance sheet",
    "cash flow",
    "catalyst",
    "cost",
    "debt",
    "demand",
    "dividend",
    "earnings",
    "guidance",
    "growth",
    "margin",
    "market",
    "price",
    "production",
    "profit",
    "revenue",
    "risk",
    "supply",
    "valuation",
}


def _sentence_score(sentence: str) -> float:
    lowered = sentence.lower()
    score = 0.0
    for keyword in _TAKEAWAY_KEYWORDS:
        if keyword in lowered:
            score += 1.0
    if re.search(r"\d", sentence):
        score += 0.6
    if 80 <= len(sentence) <= 240:
        score += 0.4
    return score


def _chunk_takeaways(
    points: list[dict[str, Any]],
    source_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, int, str, dict[str, Any]]] = []
    seen: set[str] = set()
    for point in points:
        payload = _point_payload(point)
        try:
            chunk_index = int(payload.get("chunk_index", 0) or 0)
        except (TypeError, ValueError):
            chunk_index = 0
        text = _point_text(point)
        pieces = re.split(r"(?<=[.!?])\s+|\n+", text)
        for piece in pieces:
            cleaned = _clean_takeaway_text(piece)
            if len(cleaned) < 45:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append((_sentence_score(cleaned), chunk_index, cleaned, point))

        if not candidates and text:
            cleaned = _clean_takeaway_text(text[:260])
            if cleaned:
                candidates.append((_sentence_score(cleaned), chunk_index, cleaned, point))

    candidates.sort(key=lambda row: (-row[0], row[1], row[2].lower()))
    return [
        {
            "text": text,
            "citations": [_citation_for_point(point, source_id)],
            "source_field": "chunk_text",
            "score": round(score, 3),
        }
        for score, _chunk_index, text, point in candidates[:limit]
    ]


_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")
_TICKER_STOPWORDS = {
    "AND",
    "ASX",
    "CEO",
    "CFO",
    "EPS",
    "FY",
    "GDP",
    "LLC",
    "LTD",
    "THE",
    "USD",
}


def _watchlist_suggestions(
    memo: dict[str, Any] | None,
    points: list[dict[str, Any]],
    source_id: str,
) -> list[dict[str, Any]]:
    if not memo:
        return []
    values = memo.get("tickers")
    if not isinstance(values, list):
        return []

    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        ticker = str(value or "").strip().upper()
        if (
            not ticker
            or ticker in seen
            or ticker in _TICKER_STOPWORDS
            or not _TICKER_RE.fullmatch(ticker)
        ):
            continue
        seen.add(ticker)
        suggestions.append(
            {
                "ticker": ticker,
                "commentary": "Ticker mentioned in the extracted commentary memo.",
                "citations": _citation_for_text(ticker, points, source_id),
            }
        )
    return suggestions


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


def _youtube_channel_error_detail(
    exc: RuntimeError,
    *,
    name_or_id: str,
) -> dict[str, str]:
    error_code = getattr(exc, "error_code", "youtube_channel_lookup_failed")
    return {
        "error": str(error_code),
        "message": str(exc).strip() or exc.__class__.__name__,
        "name_or_id": name_or_id,
        "suggestion": "Provide a YouTube channel URL, @handle, or raw channel ID.",
    }


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
    credibility_weight: float = Field(default=0.55, ge=0.0, le=1.0)
    enabled: bool = True


class RecentChannelVideosRequest(BaseModel):
    name_or_id: str
    limit: int = Field(default=8, ge=1, le=20)


class TakeawaysRequest(BaseModel):
    source_id: str
    limit: int = Field(default=5, ge=1, le=12)


class IngestUrlRequest(BaseModel):
    url: str
    credibility_weight: float | None = Field(default=None, ge=0.0, le=1.0)


class IngestUrlsRequest(BaseModel):
    urls: list[str] = Field(default_factory=list, min_length=1, max_length=5)
    credibility_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    takeaway_limit: int = Field(default=5, ge=1, le=12)


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


def _commentary_takeaways_payload(source_id: str, limit: int) -> dict[str, Any]:
    points, entry = _load_staged_points_for_source(source_id)
    memo, memo_status = _load_commentary_memo_for_source(source_id)

    if not points and memo is None:
        status_code = 503 if memo_status.startswith("error:") else 404
        raise HTTPException(
            status_code=status_code,
            detail=f"source_id not found in staged chunks or commentary memos: {source_id}",
        )

    takeaways = _memo_takeaways(memo, points, source_id, limit) if memo else []
    takeaway_source = "memo" if takeaways else "chunks"
    if len(takeaways) < limit and points:
        existing = {str(row.get("text") or "").lower() for row in takeaways}
        for row in _chunk_takeaways(points, source_id, limit):
            key = str(row.get("text") or "").lower()
            if key in existing:
                continue
            takeaways.append(row)
            existing.add(key)
            if len(takeaways) >= limit:
                break
        if memo and takeaway_source == "memo" and any(
            row.get("source_field") == "chunk_text" for row in takeaways
        ):
            takeaway_source = "memo+chunks"

    source_status = "staged" if points else "memo_only"
    return {
        "ok": True,
        "source_id": source_id,
        "source_status": source_status,
        "source_name": (entry or {}).get("source_name") or (entry or {}).get("title") or "",
        "published_at": (entry or {}).get("published_at") or (memo or {}).get("published_at") or "",
        "chunk_count": len(points),
        "memo_status": memo_status,
        "takeaway_source": takeaway_source,
        "takeaways": takeaways,
        "watchlist_suggestions": _watchlist_suggestions(memo, points, source_id),
        "model": "deterministic:commentary-staged-chunks",
        "prompt_version": "takeaways-v1-deterministic",
    }


@router.post(
    "/takeaways",
    dependencies=[Depends(require_api_key)],
)
def get_commentary_takeaways(body: TakeawaysRequest) -> dict[str, Any]:
    source_id = _validate_source_id(body.source_id)
    return _commentary_takeaways_payload(source_id, int(body.limit))


def _ingest_youtube_url_to_staging(
    url: str,
    *,
    credibility_weight: float | None = None,
) -> dict[str, Any]:
    url = str(url or "").strip()
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

    ingest_kwargs: dict[str, Any] = {
        "transcript_text": transcript_text,
        "source_name": video.title,
        "source_type": "youtube_transcript",
        "speaker": video.channel_name,
        "published_at": video.published_at or "",
    }
    if credibility_weight is not None:
        ingest_kwargs["credibility_weight"] = credibility_weight

    try:
        result = ingest_transcript(**ingest_kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"transcript processing failed: {exc}") from exc

    return {
        **result,
        "video_id": video.video_id,
        "video_title": video.title,
        "channel": video.channel_name,
        "published_at": video.published_at,
        "webpage_url": video.webpage_url,
    }


@router.post(
    "/ingest-url",
    dependencies=[Depends(require_api_key)],
)
def ingest_url(body: IngestUrlRequest) -> dict[str, Any]:
    return _ingest_youtube_url_to_staging(
        body.url,
        credibility_weight=body.credibility_weight,
    )


@router.post(
    "/ingest-urls",
    dependencies=[Depends(require_api_key)],
)
def ingest_urls(body: IngestUrlsRequest) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for url in body.urls:
        normalized_url = str(url or "").strip()
        try:
            ingest_result = _ingest_youtube_url_to_staging(
                normalized_url,
                credibility_weight=body.credibility_weight,
            )
            source_id = _validate_source_id(str(ingest_result.get("source_id") or ""))
            try:
                takeaway_payload = _commentary_takeaways_payload(
                    source_id,
                    int(body.takeaway_limit),
                )
            except HTTPException as exc:
                takeaway_payload = {
                    "ok": False,
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "takeaways": [],
                    "watchlist_suggestions": [],
                }
            results.append(
                {
                    **ingest_result,
                    "takeaway_status": "ready" if takeaway_payload.get("ok") else "error",
                    "takeaways": takeaway_payload.get("takeaways") or [],
                    "watchlist_suggestions": takeaway_payload.get("watchlist_suggestions") or [],
                    "takeaway_payload": takeaway_payload,
                    "review_status": "staged" if ingest_result.get("staged") else "indexed",
                }
            )
        except HTTPException as exc:
            errors.append(
                {
                    "url": normalized_url,
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                }
            )

    return {
        "ok": not errors,
        "count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "requires_review": any(item.get("staged") for item in results),
        "commit_path": "/api/commentary/transcripts/{source_id}/approve",
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
    except YoutubeChannelResolutionError as exc:
        raise HTTPException(
            status_code=502,
            detail=_youtube_channel_error_detail(exc, name_or_id=name_or_id),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=_youtube_channel_error_detail(exc, name_or_id=name_or_id),
        ) from exc

    registry = ChannelRegistry()
    existing = registry.channels()
    existing_channel = next((c for c in existing if c.channel_id == channel_id), None)
    already_existed = existing_channel is not None

    if not already_existed:
        new_channel = ChannelConfig(
            name=canonical_name,
            channel_id=channel_id,
            credibility_weight=float(body.credibility_weight),
            enabled=body.enabled,
        )
        registry.save([*existing, new_channel])
        stored_channel = new_channel
    else:
        stored_channel = existing_channel

    return {
        "channel_id": channel_id,
        "name": stored_channel.name,
        "enabled": stored_channel.enabled,
        "credibility_weight": stored_channel.credibility_weight,
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
    "/channels/recent-videos",
    dependencies=[Depends(require_api_key)],
)
def get_recent_channel_videos(body: RecentChannelVideosRequest) -> dict[str, Any]:
    name_or_id = str(body.name_or_id or "").strip()
    if not name_or_id:
        raise HTTPException(status_code=422, detail="name_or_id is required")

    try:
        return list_recent_channel_videos(name_or_id, limit=body.limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except YoutubeChannelResolutionError as exc:
        raise HTTPException(
            status_code=502,
            detail=_youtube_channel_error_detail(exc, name_or_id=name_or_id),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=_youtube_channel_error_detail(exc, name_or_id=name_or_id),
        ) from exc


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
