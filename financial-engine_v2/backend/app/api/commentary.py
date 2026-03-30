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

from app.api.routes import require_api_key
from app.services.embeddings import upsert_points, verify_qdrant

logger = logging.getLogger(__name__)

router = APIRouter(tags=["commentary"])

_SOURCE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
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
