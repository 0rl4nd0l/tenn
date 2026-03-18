from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any, Callable

from app.services.source_registry import SourceRegistry, build_source_id


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_INBOX_ROOT = WORKSPACE_ROOT / "inbox"
DEFAULT_TRANSCRIPTS_DIR = DEFAULT_INBOX_ROOT / "transcripts"
DEFAULT_BOOKS_DIR = DEFAULT_INBOX_ROOT / "books"
DEFAULT_PROCESSED_DIR = WORKSPACE_ROOT / "processed"
DEFAULT_FAILED_DIR = WORKSPACE_ROOT / "failed"
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_SOURCE_TYPE = "youtube_transcript"
DEFAULT_STATE_FILENAME = ".transcript_watcher_state.json"


@dataclass(frozen=True)
class TranscriptMetadata:
    source_name: str
    source_type: str = DEFAULT_SOURCE_TYPE
    speaker: str = ""
    published_at: str = ""
    topic_tags: tuple[str, ...] = ()
    credibility_weight: float | None = None
    decay_half_life_days: float | None = None


@dataclass(frozen=True)
class TranscriptJob:
    path: Path
    metadata: TranscriptMetadata
    transcript_text: str


@dataclass(frozen=True)
class TranscriptProcessResult:
    status: str
    path: Path
    destination_path: Path | None = None
    source_id: str | None = None
    error: str = ""


def _utc_iso_from_mtime(path: Path) -> str:
    stat = path.stat()
    return (
        datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _clean_transcript_text(transcript_text: str) -> str:
    import re

    lines = []
    for raw_line in str(transcript_text or "").replace("\r", "\n").splitlines():
        line = re.sub(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s*", "", raw_line)
        line = re.sub(r"^\s*\[[^\]]+\]\s*$", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _normalize_topic_tags(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [item for item in str(value).split(",")]

    normalized: list[str] = []
    seen = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _parse_front_matter_value(raw_value: str) -> Any:
    value = str(raw_value or "").strip()
    if not value:
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip('"').strip("'")


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, normalized

    metadata_lines: list[str] = []
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            metadata: dict[str, Any] = {}
            for raw_line in metadata_lines:
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#") or ":" not in stripped:
                    continue
                key, raw_value = stripped.split(":", 1)
                metadata[key.strip()] = _parse_front_matter_value(raw_value)
            body = "\n".join(lines[index + 1 :]).lstrip("\n")
            return metadata, body
        metadata_lines.append(line)
    return {}, normalized


def parse_transcript_job(path: str | Path) -> TranscriptJob:
    transcript_path = Path(path).expanduser().resolve()
    raw_text = transcript_path.read_text(encoding="utf-8")
    metadata_block, transcript_text = _parse_front_matter(raw_text)

    source_name = str(metadata_block.get("source_name") or transcript_path.name).strip() or transcript_path.name
    source_type = str(metadata_block.get("source_type") or DEFAULT_SOURCE_TYPE).strip() or DEFAULT_SOURCE_TYPE
    speaker_default = transcript_path.stem or transcript_path.name
    speaker = str(metadata_block.get("speaker") or speaker_default).strip() or speaker_default
    published_at = str(metadata_block.get("published_at") or _utc_iso_from_mtime(transcript_path)).strip()

    metadata = TranscriptMetadata(
        source_name=source_name,
        source_type=source_type,
        speaker=speaker,
        published_at=published_at,
        topic_tags=_normalize_topic_tags(metadata_block.get("topic_tags")),
        credibility_weight=_coerce_float(metadata_block.get("credibility_weight")),
        decay_half_life_days=_coerce_float(metadata_block.get("decay_half_life_days")),
    )
    return TranscriptJob(
        path=transcript_path,
        metadata=metadata,
        transcript_text=str(transcript_text or "").strip(),
    )


def compute_transcript_source_id(
    *,
    transcript_text: str,
    metadata: TranscriptMetadata,
) -> str:
    cleaned = _clean_transcript_text(transcript_text)
    if not cleaned:
        raise ValueError("transcript_text is required")

    fingerprint = hashlib.sha256(
        f"{metadata.source_name}|{metadata.speaker}|{metadata.published_at}|{cleaned}".encode("utf-8")
    ).hexdigest()
    return build_source_id(
        source_type=metadata.source_type,
        source_name=metadata.source_name,
        fingerprint=fingerprint,
    )


def render_transcript_drop_file(
    *,
    transcript_text: str,
    metadata: TranscriptMetadata,
) -> str:
    payload = {
        "source_name": metadata.source_name,
        "source_type": metadata.source_type,
        "speaker": metadata.speaker,
        "published_at": metadata.published_at,
        "topic_tags": list(metadata.topic_tags),
        "credibility_weight": metadata.credibility_weight,
        "decay_half_life_days": metadata.decay_half_life_days,
    }
    lines = ["---"]
    for key, value in payload.items():
        if value in (None, "", []):
            continue
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["---", str(transcript_text or "").strip(), ""])
    return "\n".join(lines)


def _default_ingest_runner(job: TranscriptJob) -> dict[str, Any]:
    from app.services.commentary_ingest import ingest_transcript

    return ingest_transcript(
        transcript_text=job.transcript_text,
        source_name=job.metadata.source_name,
        source_type=job.metadata.source_type,
        speaker=job.metadata.speaker,
        published_at=job.metadata.published_at,
        topic_tags=list(job.metadata.topic_tags),
        credibility_weight=job.metadata.credibility_weight,
        decay_half_life_days=job.metadata.decay_half_life_days,
    )


class TranscriptProcessor:
    def __init__(
        self,
        *,
        inbox_dir: str | Path | None = None,
        books_dir: str | Path | None = None,
        processed_dir: str | Path | None = None,
        failed_dir: str | Path | None = None,
        state_path: str | Path | None = None,
        registry_path: str | Path | None = None,
        ingest_runner: Callable[[TranscriptJob], dict[str, Any]] | None = None,
    ) -> None:
        self.inbox_dir = Path(inbox_dir or DEFAULT_TRANSCRIPTS_DIR).expanduser().resolve()
        self.books_dir = Path(books_dir or DEFAULT_BOOKS_DIR).expanduser().resolve()
        self.processed_dir = Path(processed_dir or DEFAULT_PROCESSED_DIR).expanduser().resolve()
        self.failed_dir = Path(failed_dir or DEFAULT_FAILED_DIR).expanduser().resolve()
        self.state_path = (
            Path(state_path).expanduser().resolve()
            if state_path is not None
            else (self.processed_dir / DEFAULT_STATE_FILENAME).resolve()
        )
        self.registry = SourceRegistry(registry_path)
        self.ingest_runner = ingest_runner or _default_ingest_runner
        self._processed_filenames = self._load_processed_filenames()

    def ensure_directories(self) -> None:
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def duplicate_source_id(self, job: TranscriptJob) -> str | None:
        source_id = self.duplicate_source_id_for_text(
            transcript_text=job.transcript_text,
            metadata=job.metadata,
        )
        return source_id

    def duplicate_source_id_for_text(
        self,
        *,
        transcript_text: str,
        metadata: TranscriptMetadata,
    ) -> str | None:
        source_id = compute_transcript_source_id(
            transcript_text=transcript_text,
            metadata=metadata,
        )
        if self.registry.get(source_id) is not None:
            return source_id
        return None

    def write_drop_file(
        self,
        *,
        file_name: str,
        transcript_text: str,
        metadata: TranscriptMetadata,
    ) -> Path:
        self.ensure_directories()
        target = self._unique_destination(self.inbox_dir, Path(file_name).name)
        target.write_text(
            render_transcript_drop_file(
                transcript_text=transcript_text,
                metadata=metadata,
            ),
            encoding="utf-8",
        )
        return target

    def process_file(self, path: str | Path) -> TranscriptProcessResult:
        self.ensure_directories()
        transcript_path = Path(path).expanduser().resolve()
        try:
            if self._has_processed_filename(transcript_path.name):
                destination = self._move_to_directory(transcript_path, self.processed_dir)
                return TranscriptProcessResult(
                    status="duplicate",
                    path=transcript_path,
                    destination_path=destination,
                )

            job = parse_transcript_job(transcript_path)
            duplicate_source_id = self.duplicate_source_id(job)
            if duplicate_source_id is not None:
                destination = self._move_to_directory(transcript_path, self.processed_dir)
                self._mark_processed_filename(transcript_path.name)
                return TranscriptProcessResult(
                    status="duplicate",
                    path=job.path,
                    destination_path=destination,
                    source_id=duplicate_source_id,
                )

            payload = self.ingest_runner(job)
            destination = self._move_to_directory(transcript_path, self.processed_dir)
            self._mark_processed_filename(transcript_path.name)
            return TranscriptProcessResult(
                status="ingested",
                path=job.path,
                destination_path=destination,
                source_id=str(payload.get("source_id") or ""),
            )
        except Exception as exc:
            destination = None
            if transcript_path.exists():
                destination = self._move_to_directory(transcript_path, self.failed_dir)
            return TranscriptProcessResult(
                status="failed",
                path=transcript_path,
                destination_path=destination,
                error=str(exc),
            )

    @staticmethod
    def _unique_destination(directory: Path, name: str) -> Path:
        candidate = directory / Path(name).name
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        index = 1
        while True:
            attempt = directory / f"{stem}_{index}{suffix}"
            if not attempt.exists():
                return attempt
            index += 1

    def _move_to_directory(self, path: Path, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        destination = self._unique_destination(directory, path.name)
        shutil.move(str(path), str(destination))
        return destination

    def _load_processed_filenames(self) -> set[str]:
        if not self.state_path.exists():
            return set()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()
        if not isinstance(payload, dict):
            return set()
        names = payload.get("processed_filenames")
        if not isinstance(names, list):
            return set()
        return {
            Path(str(name)).name
            for name in names
            if str(name or "").strip()
        }

    def _save_processed_filenames(self) -> None:
        payload = {
            "processed_filenames": sorted(self._processed_filenames),
        }
        self.state_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _has_processed_filename(self, name: str) -> bool:
        return Path(name).name in self._processed_filenames

    def _mark_processed_filename(self, name: str) -> None:
        normalized_name = Path(name).name
        if not normalized_name:
            return
        if normalized_name in self._processed_filenames:
            return
        self._processed_filenames.add(normalized_name)
        self._save_processed_filenames()


class TranscriptWatcher:
    def __init__(
        self,
        *,
        processor: TranscriptProcessor | None = None,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        self.processor = processor or TranscriptProcessor()
        self.poll_interval_seconds = max(1.0, float(poll_interval_seconds))

    def poll_once(self) -> list[TranscriptProcessResult]:
        self.processor.ensure_directories()
        candidates = sorted(
            path
            for path in self.processor.inbox_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".txt"
        )
        return [self.processor.process_file(path) for path in candidates]

    def run_forever(self, *, stop_event: Event | None = None) -> None:
        guard = stop_event or Event()
        while not guard.is_set():
            self.poll_once()
            guard.wait(self.poll_interval_seconds)
