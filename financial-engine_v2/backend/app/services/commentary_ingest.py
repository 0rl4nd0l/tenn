from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Callable

from qdrant_client import QdrantClient

from app.tasks.commentary_tasks import extract_commentary_memo_task
from app.services.structured_chunking import chunk_commentary_text
from app.services.commentary_memo_extractor import (
    DEFAULT_COMMENTARY_MEMOS_PATH,
    CommentaryMemoExtractor,
)
from app.services.embeddings import (
    embed_texts_batched,
    ensure_collection,
    resolve_llamacpp_embedding_config,
    verify_qdrant,
)
from app.services.llamacpp_runtime import resolve_llm_runtime_config
from app.services.source_registry import SourceRegistry, build_source_id, utc_now_iso
from app.services.source_weighting import DEFAULT_HALF_LIFE_DAYS, DEFAULT_SOURCE_WEIGHTS


HOT_SOURCE_TYPES = {
    "youtube_transcript",
    "podcast_transcript",
    "market_commentary",
}

STAGED_CHUNKS_DIR = Path("~/.tenn/memory/staged_chunks").expanduser()
STAGED_CHUNKS_INDEX = STAGED_CHUNKS_DIR / "index.json"

_logger = logging.getLogger(__name__)


def _load_staging_index() -> dict[str, Any]:
    if not STAGED_CHUNKS_INDEX.exists():
        return {}
    try:
        return json.loads(STAGED_CHUNKS_INDEX.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_staging_index(index: dict[str, Any]) -> None:
    STAGED_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    STAGED_CHUNKS_INDEX.write_text(json.dumps(index, indent=2), "utf-8")


def _default_embed_batch(texts: list[str], *, llm_url: str | None, model: str | None) -> list[list[float]]:
    return embed_texts_batched(texts, llm_url=llm_url, model=model)


def _clean_transcript_line(raw_line: Any) -> str:
    line = re.sub(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s*", "", str(raw_line or ""))
    line = re.sub(r"^\s*\[[^\]]+\]\s*$", "", line)
    return re.sub(r"\s+", " ", line).strip()


def clean_transcript_text(transcript_text: str) -> str:
    lines = []
    for raw_line in str(transcript_text or "").replace("\r", "\n").splitlines():
        line = _clean_transcript_line(raw_line)
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _unique_chunks(chunks: list[str]) -> list[str]:
    deduped: list[str] = []
    seen = set()
    for chunk in chunks:
        normalized = re.sub(r"\s+", " ", str(chunk or "")).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(str(chunk).strip())
    return deduped


def _coerce_optional_seconds(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return None
    return coerced if coerced >= 0 else None


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_transcript_segments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    segments: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        text = clean_transcript_text(str(row.get("text") or ""))
        if not text:
            continue
        segments.append(
            {
                "text": text,
                "segment_start_seconds": _coerce_optional_seconds(
                    _first_present(row, "segment_start_seconds", "start")
                ),
                "segment_end_seconds": _coerce_optional_seconds(
                    _first_present(row, "segment_end_seconds", "end")
                ),
            }
        )
    return segments


def _split_timed_text_unit(
    text: str,
    *,
    start: float | None,
    end: float | None,
    max_chars: int,
) -> list[dict[str, Any]]:
    normalized = _clean_transcript_line(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [
            {
                "text": normalized,
                "segment_start_seconds": start,
                "segment_end_seconds": end,
            }
        ]

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized)
        if sentence.strip()
    ]
    candidates = sentences if len(sentences) > 1 else [normalized]
    raw_units: list[str] = []
    for candidate in candidates:
        if len(candidate) <= max_chars:
            raw_units.append(candidate)
            continue
        words = re.findall(r"\S+", candidate)
        current: list[str] = []
        current_len = 0
        for word in words:
            separator = 1 if current else 0
            if current and current_len + separator + len(word) > max_chars:
                raw_units.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += separator + len(word)
        if current:
            raw_units.append(" ".join(current))

    return [
        {
            "text": unit,
            "segment_start_seconds": start,
            "segment_end_seconds": end,
        }
        for unit in raw_units
        if unit
    ]


def _timed_chunk_payload(units: list[dict[str, Any]]) -> dict[str, Any]:
    starts = [
        unit.get("segment_start_seconds")
        for unit in units
        if unit.get("segment_start_seconds") is not None
    ]
    ends = [
        unit.get("segment_end_seconds")
        for unit in units
        if unit.get("segment_end_seconds") is not None
    ]
    return {
        "text": "\n".join(str(unit.get("text") or "").strip() for unit in units).strip(),
        "segment_start_seconds": starts[0] if starts else None,
        "segment_end_seconds": ends[-1] if ends else None,
    }


def _chunk_timed_segments(
    transcript_segments: list[dict[str, Any]],
    *,
    max_chars: int = 1400,
    min_chars: int = 650,
) -> list[dict[str, Any]]:
    resolved_max = max(120, int(max_chars))
    resolved_min = max(0, min(int(min_chars), resolved_max))
    units: list[dict[str, Any]] = []
    for segment in transcript_segments:
        units.extend(
            _split_timed_text_unit(
                str(segment.get("text") or ""),
                start=segment.get("segment_start_seconds"),
                end=segment.get("segment_end_seconds"),
                max_chars=resolved_max,
            )
        )
    if not units:
        return []

    chunks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_len = 0
    for unit in units:
        text = str(unit.get("text") or "").strip()
        if not text:
            continue
        separator = 1 if current else 0
        next_len = current_len + separator + len(text)
        if current and next_len > resolved_max and current_len >= resolved_min:
            chunks.append(_timed_chunk_payload(current))
            current = [unit]
            current_len = len(text)
        elif current and next_len > resolved_max:
            chunks.append(_timed_chunk_payload(current))
            current = [unit]
            current_len = len(text)
        else:
            current.append(unit)
            current_len = next_len

    if current:
        chunks.append(_timed_chunk_payload(current))

    deduped: list[dict[str, Any]] = []
    seen = set()
    for chunk in chunks:
        normalized = re.sub(r"\s+", " ", str(chunk.get("text") or "")).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(chunk)
    return deduped


def _nullable_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def ingest_transcript(
    *,
    transcript_text: str,
    source_name: str,
    source_type: str,
    speaker: str,
    published_at: str,
    topic_tags: list[str] | None = None,
    credibility_weight: float | int | None = None,
    decay_half_life_days: float | int | None = None,
    source_id: str | None = None,
    video_id: str | None = None,
    webpage_url: str | None = None,
    transcript_segments: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    qdrant_client: QdrantClient | Any | None = None,
    registry_path: str | Path | None = None,
    memos_path: str | Path | None = None,
    collection_name: str = "commentary_chunks",
    qdrant_url: str | None = None,
    llm_url: str | None = None,
    embed_model: str | None = None,
    embed_batch_fn: Callable[..., list[list[float]]] | None = None,
    memo_extractor: CommentaryMemoExtractor | None = None,
) -> dict[str, Any]:
    normalized_type = str(source_type or "").strip().lower()
    if normalized_type not in HOT_SOURCE_TYPES:
        raise ValueError("transcript ingestion only supports commentary source types")

    cleaned = clean_transcript_text(transcript_text)
    if not cleaned:
        raise ValueError("transcript_text is required")

    registry = SourceRegistry(registry_path)
    resolved_credibility = (
        float(credibility_weight)
        if credibility_weight not in (None, "")
        else float(DEFAULT_SOURCE_WEIGHTS[normalized_type])
    )
    resolved_half_life = (
        float(decay_half_life_days)
        if decay_half_life_days not in (None, "")
        else float(DEFAULT_HALF_LIFE_DAYS[normalized_type])
    )
    fingerprint = hashlib.sha256(
        f"{source_name}|{speaker}|{published_at}|{cleaned}".encode("utf-8")
    ).hexdigest()
    resolved_source_id = source_id or build_source_id(
        source_type=normalized_type,
        source_name=source_name,
        fingerprint=fingerprint,
    )

    registry_entry = registry.upsert(
        {
            "source_id": resolved_source_id,
            "source_type": normalized_type,
            "source_name": source_name,
            "credibility_weight": resolved_credibility,
            "time_decay_half_life_days": resolved_half_life,
            "framework_family": "",
            "review_status": "pending",
            "ingested_at": utc_now_iso(),
        }
    )

    sorted_tags = sorted(
        {
            str(tag or "").strip()
            for tag in (topic_tags or [])
            if str(tag or "").strip()
        }
    )
    resolved_generation_url, resolved_generation_model = resolve_llm_runtime_config(
        base_url=llm_url,
    )
    resolved_embedding_url, resolved_embedding_model = resolve_llamacpp_embedding_config(
        llm_url=llm_url,
        model=embed_model,
    )
    normalized_segments = _normalize_transcript_segments(
        transcript_segments or getattr(transcript_text, "segment_timing", None)
    )
    segment_cleaned = clean_transcript_text(
        "\n".join(str(segment.get("text") or "") for segment in normalized_segments)
    )
    timed_chunks = (
        _chunk_timed_segments(normalized_segments)
        if normalized_segments and segment_cleaned == cleaned
        else []
    )
    if timed_chunks:
        chunks = [str(chunk["text"]) for chunk in timed_chunks]
    else:
        chunks = _unique_chunks(chunk_commentary_text(cleaned, max_chars=1400))
        timed_chunks = [
            {
                "text": chunk,
                "segment_start_seconds": None,
                "segment_end_seconds": None,
            }
            for chunk in chunks
        ]
    client = qdrant_client or verify_qdrant(qdrant_url=qdrant_url)
    embed = embed_batch_fn or _default_embed_batch
    vectors = embed(
        chunks,
        llm_url=resolved_embedding_url,
        model=resolved_embedding_model,
    )
    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"embedding batch size mismatch: expected {len(chunks)}, got {len(vectors)}"
        )

    resolved_collection_name = collection_name
    if vectors:
        resolved_collection_name = ensure_collection(client, collection_name, len(vectors[0]))

    points: list[dict[str, Any]] = []
    normalized_video_id = _nullable_text(video_id)
    normalized_webpage_url = _nullable_text(webpage_url)
    for index, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
        chunk_id = f"{resolved_source_id}:{index}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"commentary_chunks:{chunk_id}"))
        timing = timed_chunks[index] if index < len(timed_chunks) else {}
        points.append(
            {
                "id": point_id,
                "vector": list(vector),
                "payload": {
                    "chunk_id": chunk_id,
                    "source_id": resolved_source_id,
                    "chunk_index": index,
                    "text": chunk_text,
                    "source_name": source_name,
                    "source_type": normalized_type,
                    "speaker": str(speaker or "").strip(),
                    "published_at": str(published_at or "").strip(),
                    "credibility_weight": resolved_credibility,
                    "decay_half_life": resolved_half_life,
                    "topic_tags": sorted_tags,
                    "video_id": normalized_video_id,
                    "webpage_url": normalized_webpage_url,
                    "segment_start_seconds": timing.get("segment_start_seconds"),
                    "segment_end_seconds": timing.get("segment_end_seconds"),
                },
            }
        )
    # --- Staging gate: hot sources are staged for review, not auto-indexed ---
    staged = False
    if points:
        staging_index = _load_staging_index()
        if resolved_source_id in staging_index:
            _logger.warning("Staging skipped — source_id already staged: %s", resolved_source_id)
        else:
            try:
                STAGED_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
                staged_path = STAGED_CHUNKS_DIR / f"{resolved_source_id}.jsonl"
                with staged_path.open("w", encoding="utf-8") as f:
                    for pt in points:
                        f.write(json.dumps(pt) + "\n")
                staging_index[resolved_source_id] = {
                    "path": str(staged_path),
                    "source_type": normalized_type,
                    "source_name": source_name,
                    "title": source_name,
                    "staged_at": utc_now_iso(),
                    "chunk_count": len(points),
                    "published_at": str(published_at or ""),
                    "collection_name": resolved_collection_name,
                    "credibility_weight": resolved_credibility,
                    "video_id": normalized_video_id,
                    "webpage_url": normalized_webpage_url,
                }
                _save_staging_index(staging_index)
                staged = True
                _logger.info(
                    "Staged %d chunks for review: %s (%s)",
                    len(points), resolved_source_id, normalized_type,
                )
            except Exception:
                _logger.exception("Staging failed for %s — skipping (not indexed)", resolved_source_id)

    resolved_memos_path = Path(
        getattr(memo_extractor, "memos_path", None) or memos_path or DEFAULT_COMMENTARY_MEMOS_PATH
    ).expanduser().resolve()
    memo_payload: dict[str, Any] = {
        "source_id": resolved_source_id,
        "transcript_text": cleaned,
        "speaker": speaker,
        "source_type": normalized_type,
        "published_at": published_at,
        "llm_url": resolved_generation_url,
        "llm_model": resolved_generation_model,
        "memos_path": str(resolved_memos_path),
    }

    memo = None
    try:
        extract_commentary_memo_task.delay(memo_payload)
        print("[INFO] memo extraction queued")
    except Exception as e:
        print(f"[WARN] memo extraction queue failed: {e}")

    print("[INFO] transcript stored successfully (memo optional)")

    return {
        "ok": True,
        "source_id": resolved_source_id,
        "collection": resolved_collection_name,
        "chunks_staged": len(points) if staged else 0,
        "chunks_indexed": 0 if staged else len(points),
        "staged": staged,
        "registry_path": str(registry.path),
        "memos_path": str(resolved_memos_path),
        "registry_entry": registry_entry,
        "credibility_weight": resolved_credibility,
        "memo": memo,
    }
