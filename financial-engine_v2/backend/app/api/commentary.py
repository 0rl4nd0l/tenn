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
from app.services.source_registry import SourceRegistry
from app.services.youtube_transcript_fetcher import (
    MembersOnlyVideoError,
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
RECENT_COMMENTARY_SOURCE_TYPES = {
    "youtube_transcript",
    "podcast_transcript",
    "market_commentary",
}


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
    payload = _point_payload(point)
    start = payload.get("segment_start_seconds") or payload.get("chunk_start_seconds") or 0
    try:
        segment_start_seconds = max(0, int(float(start)))
    except (TypeError, ValueError):
        segment_start_seconds = 0
    return {
        "chunk_id": _point_chunk_id(point, source_id),
        "segment_start_seconds": segment_start_seconds,
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _bounded_takeaway_limit(value: Any) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return 5
    return max(1, min(12, limit))


def _write_staged_points(path: Path, points: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for point in points:
            handle.write(json.dumps(point, ensure_ascii=False) + "\n")


def _review_takeaways_from_entry(
    entry: dict[str, Any] | None,
    source_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(entry, dict):
        return []
    rows = entry.get("review_takeaways")
    if not isinstance(rows, list):
        return []

    takeaways: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if isinstance(row, dict):
            text = _clean_takeaway_text(row.get("text"))
        else:
            text = _clean_takeaway_text(row)
        if not text:
            continue
        takeaways.append(
            {
                "text": text,
                "citations": [],
                "source_field": "operator_review",
                "score": 1.0,
                "review_index": index,
                "source_id": source_id,
            }
        )
    return takeaways


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
        chunk_added = False
        for piece in pieces:
            cleaned = _clean_takeaway_text(piece)
            if len(cleaned) < 45:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append((_sentence_score(cleaned), chunk_index, cleaned, point))
            chunk_added = True

        # Per-chunk fallback: if no sentence from this chunk qualified (e.g. short
        # caption phrases with no punctuation), use the first 260 chars of the chunk.
        if not chunk_added and text:
            cleaned = _clean_takeaway_text(text[:260])
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
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


def _first_readable_text(text: str) -> str:
    for piece in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")):
        cleaned = _clean_takeaway_text(piece)
        if len(cleaned) >= 45:
            return cleaned
    return _clean_takeaway_text(str(text or "")[:260])


def _chunk_outline(
    points: list[dict[str, Any]],
    source_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    outline: list[dict[str, Any]] = []
    for point in points[: max(0, limit)]:
        payload = _point_payload(point)
        try:
            chunk_index = int(payload.get("chunk_index", 0) or 0)
        except (TypeError, ValueError):
            chunk_index = 0
        summary = _first_readable_text(_point_text(point))
        if not summary:
            continue
        outline.append(
            {
                "title": f"Transcript section {chunk_index + 1}",
                "summary": summary,
                "citations": [_citation_for_point(point, source_id)],
                "chunk_index": chunk_index,
                "source_field": "chunk_outline",
            }
        )
    return outline


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


def _update_source_registry(
    source_id: str,
    status: str | None = None,
    *,
    credibility_weight: float | None = None,
) -> None:
    """Best-effort registry metadata update."""
    try:
        registry = SourceRegistry()
        entry = registry.get(source_id)
        if entry:
            if status is not None:
                entry["review_status"] = status
                if status == "approved":
                    entry["approved_at"] = _utc_now_iso()
            if credibility_weight is not None:
                entry["credibility_weight"] = float(credibility_weight)
            registry.upsert(entry)
    except Exception:
        logger.warning("Failed to update registry metadata for %s", source_id)


def _recent_commentary_items(
    rows: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        source_type = str(row.get("source_type") or "").strip().lower()
        source_name = str(row.get("source_name") or "").strip()
        review_status = str(row.get("review_status") or "").strip().lower()
        if (
            not source_id
            or source_type not in RECENT_COMMENTARY_SOURCE_TYPES
            or review_status != "approved"
        ):
            continue
        approved_at = str(row.get("approved_at") or row.get("ingested_at") or "").strip()
        item = {
            "source_id": source_id,
            "source_name": source_name or source_id,
            "source_type": source_type,
            "approved_at": approved_at,
            "review_status": review_status,
        }
        ingested_at = str(row.get("ingested_at") or "").strip()
        if ingested_at:
            item["ingested_at"] = ingested_at
        credibility_weight = row.get("credibility_weight")
        if credibility_weight not in (None, ""):
            item["credibility_weight"] = credibility_weight
        items.append(item)

    items.sort(
        key=lambda item: (
            str(item.get("approved_at") or ""),
            str(item.get("source_id") or ""),
        ),
        reverse=True,
    )
    return items[:limit]


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


class TranscriptReviewUpdateRequest(BaseModel):
    credibility_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    takeaways: list[str] | None = Field(default=None, max_length=12)


# ---------------------------------------------------------------------------
# GET /api/commentary/transcripts/pending
# ---------------------------------------------------------------------------

@router.get("/transcripts/pending")
def get_pending_transcripts(
    include_takeaways: bool = False,
    takeaway_limit: int = 5,
) -> dict[str, Any]:
    index = _load_index()
    pending = [
        {"source_id": sid, **meta}
        for sid, meta in sorted(index.items(), key=lambda kv: kv[1].get("staged_at", ""))
    ]
    if include_takeaways:
        for item in pending:
            source_id = str(item.get("source_id") or "").strip()
            if not source_id:
                continue
            item.update(_takeaway_enrichment(source_id, _bounded_takeaway_limit(takeaway_limit)))
    return {"pending": pending, "count": len(pending)}


# ---------------------------------------------------------------------------
# PATCH /api/commentary/transcripts/{source_id}/review
# ---------------------------------------------------------------------------

@router.patch(
    "/transcripts/{source_id}/review",
    dependencies=[Depends(require_api_key)],
)
def update_transcript_review(
    source_id: str,
    body: TranscriptReviewUpdateRequest,
) -> dict[str, Any]:
    sid = _validate_source_id(source_id)
    if body.credibility_weight is None and body.takeaways is None:
        raise HTTPException(
            status_code=422,
            detail="credibility_weight or takeaways is required",
        )

    index = _load_index()
    entry = index.get(sid)
    if not isinstance(entry, dict):
        raise HTTPException(status_code=404, detail=f"source_id not found in staging: {sid}")

    staged_path = Path(str(entry.get("path") or ""))
    if not staged_path.exists():
        raise HTTPException(status_code=404, detail=f"staged file missing: {staged_path}")

    points, _entry_copy = _load_staged_points_for_source(sid)
    if not points:
        raise HTTPException(status_code=422, detail="staged file is empty")

    updated_weight: float | None = None
    if body.credibility_weight is not None:
        updated_weight = float(body.credibility_weight)
        entry["credibility_weight"] = updated_weight
        for point in points:
            payload = _point_payload(point)
            payload["credibility_weight"] = updated_weight

    if body.takeaways is not None:
        cleaned_takeaways = [
            cleaned
            for cleaned in (_clean_takeaway_text(value) for value in body.takeaways)
            if cleaned
        ]
        entry["review_takeaways"] = [
            {
                "text": text,
                "source_field": "operator_review",
                "review_index": index,
            }
            for index, text in enumerate(cleaned_takeaways, start=1)
        ]
        for point in points:
            payload = _point_payload(point)
            payload["review_takeaways"] = cleaned_takeaways

    entry["review_updated_at"] = _utc_now_iso()
    index[sid] = entry
    _write_staged_points(staged_path, points)
    _save_index(index)

    if updated_weight is not None:
        _update_source_registry(sid, credibility_weight=updated_weight)

    return {
        "ok": True,
        "source_id": sid,
        "credibility_weight": entry.get("credibility_weight"),
        "takeaways": _review_takeaways_from_entry(entry, sid),
        "review_updated_at": entry["review_updated_at"],
    }


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

    review_weight = entry.get("credibility_weight")
    try:
        approved_weight = float(review_weight) if review_weight is not None else None
    except (TypeError, ValueError):
        approved_weight = None
    review_takeaways = _review_takeaways_from_entry(entry, sid)
    review_takeaway_texts = [
        str(row.get("text") or "").strip()
        for row in review_takeaways
        if str(row.get("text") or "").strip()
    ]
    if approved_weight is not None or review_takeaway_texts:
        for point in points:
            payload = _point_payload(point)
            if approved_weight is not None:
                payload["credibility_weight"] = approved_weight
            if review_takeaway_texts:
                payload["review_takeaways"] = review_takeaway_texts

    # Upsert to Qdrant
    try:
        client = verify_qdrant()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"qdrant_unavailable: {exc}") from exc

    collection = entry.get("collection_name", "commentary_chunks")
    result = upsert_points(client, collection, points)

    # Update source registry
    _update_source_registry(sid, "approved", credibility_weight=approved_weight)

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
        "credibility_weight": approved_weight,
        "takeaways": review_takeaways,
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
    takeaway_limit: int = Field(default=5, ge=1, le=12)


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

    generated_takeaways = list(takeaways)
    review_takeaways = _review_takeaways_from_entry(entry, source_id)
    if review_takeaways:
        takeaways = review_takeaways[:limit]
        takeaway_source = "operator_review"

    source_status = "staged" if points else "memo_only"
    outline = _chunk_outline(points, source_id, min(max(limit, 3), 8)) if points else []
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
        "generated_takeaways": generated_takeaways,
        "review_takeaways": review_takeaways,
        "credibility_weight": (entry or {}).get("credibility_weight"),
        "outline": outline,
        "digest": {
            "source_status": source_status,
            "chunk_count": len(points),
            "takeaway_source": takeaway_source,
            "memo_status": memo_status,
            "outline_count": len(outline),
        },
        "watchlist_suggestions": _watchlist_suggestions(memo, points, source_id),
        "model": "deterministic:commentary-staged-chunks",
        "prompt_version": "takeaways-v1-deterministic",
    }


def _takeaway_enrichment(source_id: str, limit: int) -> dict[str, Any]:
    try:
        takeaway_payload = _commentary_takeaways_payload(source_id, _bounded_takeaway_limit(limit))
    except HTTPException as exc:
        takeaway_payload = {
            "ok": False,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "takeaways": [],
            "watchlist_suggestions": [],
            "outline": [],
        }
    return {
        "takeaway_status": "ready" if takeaway_payload.get("ok") else "error",
        "takeaways": takeaway_payload.get("takeaways") or [],
        "watchlist_suggestions": takeaway_payload.get("watchlist_suggestions") or [],
        "outline": takeaway_payload.get("outline") or [],
        "takeaway_payload": takeaway_payload,
    }


@router.get(
    "/recent",
    dependencies=[Depends(require_api_key)],
)
def get_recent_commentary_sources(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        rows = SourceRegistry().all()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"source registry unavailable: {exc}") from exc
    items = _recent_commentary_items(rows, limit=limit)
    return {"items": items, "count": len(items)}


@router.post(
    "/takeaways",
    dependencies=[Depends(require_api_key)],
)
def get_commentary_takeaways(body: TakeawaysRequest) -> dict[str, Any]:
    source_id = _validate_source_id(body.source_id)
    return _commentary_takeaways_payload(source_id, _bounded_takeaway_limit(body.limit))


_MIN_CHARS_PER_SECOND = 2.0  # 120 chars/min — very conservative floor; real speech ≈700 chars/min


def _transcript_quality_warning(
    transcript_text: str,
    duration_seconds: int | None,
) -> str | None:
    """Return a warning string when transcript is suspiciously short for the video duration."""
    if not duration_seconds or duration_seconds < 60:
        return None
    actual_chars = len(transcript_text)
    min_expected = int(duration_seconds * _MIN_CHARS_PER_SECOND)
    if actual_chars >= min_expected:
        return None
    actual_minutes = round(actual_chars / max(duration_seconds / 60, 1))
    video_minutes = round(duration_seconds / 60)
    return (
        f"transcript appears incomplete: {actual_chars} chars ingested for a "
        f"{video_minutes}-minute video (expected at least {min_expected} chars). "
        f"Auto-generated captions may not be fully available yet — retry ingestion "
        f"after captions have been processed by YouTube."
    )


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
    except MembersOnlyVideoError as exc:
        raise HTTPException(
            status_code=403, detail=f"members-only video cannot be ingested: {url}"
        ) from exc
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
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502, detail=f"transcript fetch failed: {exc}"
        ) from exc

    quality_warning = _transcript_quality_warning(transcript_text, video.duration_seconds)
    if quality_warning:
        logger.warning(
            "transcript_quality_warning video_id=%s duration_s=%s chars=%s warning=%s",
            video.video_id,
            video.duration_seconds,
            len(transcript_text),
            quality_warning,
        )

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

    staging_result: dict[str, Any] = {
        **result,
        "video_id": video.video_id,
        "video_title": video.title,
        "channel": video.channel_name,
        "published_at": video.published_at,
        "webpage_url": video.webpage_url,
        "transcript_chars": len(transcript_text),
        "duration_seconds": video.duration_seconds,
    }
    if quality_warning:
        staging_result["transcript_quality_warning"] = quality_warning
    return staging_result


@router.post(
    "/ingest-url",
    dependencies=[Depends(require_api_key)],
)
def ingest_url(body: IngestUrlRequest) -> dict[str, Any]:
    result = _ingest_youtube_url_to_staging(
        body.url,
        credibility_weight=body.credibility_weight,
    )
    source_id = _validate_source_id(str(result.get("source_id") or ""))
    return {
        **result,
        **_takeaway_enrichment(source_id, _bounded_takeaway_limit(body.takeaway_limit)),
        "review_status": "staged" if result.get("staged") else "indexed",
        "commit_path": "/api/commentary/transcripts/{source_id}/approve",
    }


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
            results.append(
                {
                    **ingest_result,
                    **_takeaway_enrichment(source_id, _bounded_takeaway_limit(body.takeaway_limit)),
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
