from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.source_weighting import DEFAULT_HALF_LIFE_DAYS, DEFAULT_SOURCE_WEIGHTS


def _default_research_memory_root() -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    candidates = [
        Path(getattr(settings, "data_root", "/data")).expanduser().resolve()
        / "reports"
        / "research_memory",
        backend_root / "reports" / "research_memory",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if os.access(candidate, os.W_OK | os.X_OK):
                return candidate
        except OSError:
            continue
    return candidates[0]


RESEARCH_MEMORY_ROOT = _default_research_memory_root()
DEFAULT_SOURCE_REGISTRY_PATH = RESEARCH_MEMORY_ROOT / "source_registry.jsonl"
DEFAULT_DURABLE_UPLOAD_ROOT = RESEARCH_MEMORY_ROOT / "durable_uploads"

SUPPORTED_SOURCE_TYPES = {
    "book",
    "framework_pdf",
    "investor_letter",
    "youtube_transcript",
    "podcast_transcript",
    "market_commentary",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(f"source registry row {lineno} is not a JSON object")
            rows.append(payload)
    return rows


def _normalize_source_type(source_type: str) -> str:
    normalized = str(source_type or "").strip().lower()
    if normalized not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"unsupported source_type: {source_type}")
    return normalized


def build_source_id(
    *,
    source_type: str,
    source_name: str,
    fingerprint: str,
) -> str:
    normalized_type = _normalize_source_type(source_type)
    slug = _slugify(source_name) or normalized_type
    digest = hashlib.sha1(str(fingerprint).encode("utf-8")).hexdigest()[:16]
    return f"{normalized_type}:{slug}:{digest}"


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    source_type = _normalize_source_type(str(entry.get("source_type") or ""))
    source_name = str(entry.get("source_name") or "").strip()
    source_id = str(entry.get("source_id") or "").strip()
    if not source_id:
        raise ValueError("source_id is required")
    if not source_name:
        raise ValueError("source_name is required")

    credibility_weight = entry.get("credibility_weight")
    if credibility_weight in (None, ""):
        credibility_weight = DEFAULT_SOURCE_WEIGHTS[source_type]

    half_life = entry.get("time_decay_half_life_days")
    if half_life in (None, ""):
        half_life = DEFAULT_HALF_LIFE_DAYS[source_type]

    normalized = {
        "source_id": source_id,
        "source_type": source_type,
        "source_name": source_name,
        "credibility_weight": float(credibility_weight),
        "time_decay_half_life_days": float(half_life),
        "framework_family": str(entry.get("framework_family") or "").strip(),
        "review_status": str(entry.get("review_status") or "pending").strip() or "pending",
        "ingested_at": str(entry.get("ingested_at") or utc_now_iso()),
    }
    for optional_key in ("approved_at", "rejected_at", "published_at"):
        value = str(entry.get(optional_key) or "").strip()
        if value:
            normalized[optional_key] = value
    return normalized


class SourceRegistry:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_SOURCE_REGISTRY_PATH).expanduser().resolve()

    def all(self) -> list[dict[str, Any]]:
        return _load_jsonl(self.path)

    def get(self, source_id: str) -> dict[str, Any] | None:
        for row in self.all():
            if str(row.get("source_id") or "") == str(source_id or ""):
                return row
        return None

    def upsert(self, entry: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_entry(entry)
        rows = self.all()
        merged: list[dict[str, Any]] = []
        replaced = False
        for row in rows:
            if str(row.get("source_id") or "") == normalized["source_id"]:
                merged.append(normalized)
                replaced = True
            else:
                merged.append(row)
        if not replaced:
            merged.append(normalized)
        merged.sort(key=lambda row: str(row.get("source_id") or ""))
        _write_jsonl(self.path, merged)
        return normalized


def ingest_book(
    *,
    filename: str,
    content_bytes: bytes,
    source_name: str,
    source_type: str = "book",
    framework_family: str = "",
    credibility_weight: float | int | None = None,
    time_decay_half_life_days: float | int | None = None,
    review_status: str = "pending",
    registry_path: str | Path | None = None,
    upload_root: str | Path | None = None,
) -> dict[str, Any]:
    normalized_type = _normalize_source_type(source_type)
    if normalized_type not in {"book", "framework_pdf", "investor_letter"}:
        raise ValueError("book ingestion only supports durable source types")
    if not content_bytes.startswith(b"%PDF"):
        raise ValueError("book upload must be a PDF")

    registry = SourceRegistry(registry_path)
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    source_id = build_source_id(
        source_type=normalized_type,
        source_name=source_name or filename,
        fingerprint=f"{filename}:{sha256}",
    )

    upload_dir = Path(upload_root or DEFAULT_DURABLE_UPLOAD_ROOT).expanduser().resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename or f"{source_id}.pdf").name
    stored_path = upload_dir / f"{source_id.replace(':', '_')}_{safe_name}"
    stored_path.write_bytes(content_bytes)

    entry = registry.upsert(
        {
            "source_id": source_id,
            "source_type": normalized_type,
            "source_name": source_name or safe_name,
            "credibility_weight": credibility_weight,
            "time_decay_half_life_days": time_decay_half_life_days,
            "framework_family": framework_family,
            "review_status": review_status,
            "ingested_at": utc_now_iso(),
        }
    )
    return {
        "ok": True,
        "source_id": source_id,
        "stored_path": str(stored_path),
        "bytes_written": len(content_bytes),
        "registry_path": str(registry.path),
        "registry_entry": entry,
    }
