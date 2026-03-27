"""Transcript review service — approve/reject staged hot-source transcripts."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

STAGED_CHUNKS_DIR = Path("~/.tenn/memory/staged_chunks").expanduser()
STAGED_CHUNKS_INDEX = STAGED_CHUNKS_DIR / "index.json"


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


class TranscriptReviewService:
    """List, approve, reject, and purge staged transcript chunks."""

    def list_pending(self) -> list[dict[str, Any]]:
        index = _load_index()
        return [
            {"source_id": sid, **meta}
            for sid, meta in sorted(index.items(), key=lambda kv: kv[1].get("staged_at", ""))
        ]

    def approve(self, source_id: str, *, qdrant_url: str | None = None) -> dict[str, Any]:
        index = _load_index()
        entry = index.get(source_id)
        if not entry:
            return {"ok": False, "error": f"source_id not found in staging: {source_id}"}

        staged_path = Path(entry["path"])
        if not staged_path.exists():
            del index[source_id]
            _save_index(index)
            return {"ok": False, "error": f"staged file missing: {staged_path}"}

        # Read staged points
        points: list[dict[str, Any]] = []
        for line in staged_path.read_text("utf-8").splitlines():
            line = line.strip()
            if line:
                points.append(json.loads(line))

        if not points:
            del index[source_id]
            _save_index(index)
            staged_path.unlink(missing_ok=True)
            return {"ok": False, "error": "staged file is empty"}

        # Upsert to Qdrant
        from app.services.embeddings import upsert_points, verify_qdrant

        client = verify_qdrant(qdrant_url=qdrant_url)
        collection = entry.get("collection_name", "commentary_chunks")
        upsert_points(client, collection, points)

        # Update source registry
        try:
            from app.services.source_registry import SourceRegistry

            registry = SourceRegistry()
            reg_entry = registry.get(source_id)
            if reg_entry:
                reg_entry["review_status"] = "approved"
                registry.upsert(reg_entry)
        except Exception:
            _logger.warning("Failed to update registry status for %s", source_id)

        # Clean up staging
        staged_path.unlink(missing_ok=True)
        del index[source_id]
        _save_index(index)

        _logger.info("Approved and indexed %d chunks for %s", len(points), source_id)
        return {"ok": True, "source_id": source_id, "chunks_indexed": len(points), "collection": collection}

    def reject(self, source_id: str) -> dict[str, Any]:
        index = _load_index()
        entry = index.get(source_id)
        if not entry:
            return {"ok": False, "error": f"source_id not found in staging: {source_id}"}

        staged_path = Path(entry["path"])
        staged_path.unlink(missing_ok=True)
        del index[source_id]
        _save_index(index)

        # Update source registry
        try:
            from app.services.source_registry import SourceRegistry

            registry = SourceRegistry()
            reg_entry = registry.get(source_id)
            if reg_entry:
                reg_entry["review_status"] = "rejected"
                registry.upsert(reg_entry)
        except Exception:
            _logger.warning("Failed to update registry status for %s", source_id)

        _logger.info("Rejected and purged staged chunks for %s", source_id)
        return {"ok": True, "source_id": source_id}

    def purge_expired(self, max_age_days: int = 7) -> list[str]:
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
                    _logger.info("Purged expired staged source: %s (%.1f days old)", sid, age_days)
            except (ValueError, TypeError):
                continue
        if purged:
            _save_index(index)
        return purged
