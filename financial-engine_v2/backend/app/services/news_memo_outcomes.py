from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TextIO

from app.services.source_registry import RESEARCH_MEMORY_ROOT


DEFAULT_NEWS_MEMO_OUTCOMES_PATH = RESEARCH_MEMORY_ROOT / "news_memo_outcomes.jsonl"
_SCHEMA_VERSION = 1
_TERMINAL_STATES = frozenset({"completed", "needs_retry", "failed"})
_ROW_FIELDS = frozenset(
    {
        "schema_version",
        "correlation_id",
        "source_id",
        "task_id",
        "attempt_started_at_utc",
        "dispatch_state",
        "accepted_at_utc",
        "terminal_state",
        "reason",
        "error_class",
        "completed_at_utc",
        "updated_at_utc",
    }
)
_STRING_FIELDS = _ROW_FIELDS - {"schema_version"}
_DISPATCH_STATES = frozenset({"", "accepted", "dispatch_failed"})
_ROW_TERMINAL_STATES = _TERMINAL_STATES | {"", "dispatch_failed"}
_LIFECYCLE_TIMESTAMP_FIELDS = (
    "attempt_started_at_utc",
    "accepted_at_utc",
    "completed_at_utc",
    "updated_at_utc",
)
_SHARED_FILE_MODE = 0o660


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_utc_timestamp(value: str, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"news memo outcome {field_name} is required")
    normalized = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"news memo outcome {field_name} must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"news memo outcome {field_name} must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat()


def resolve_news_memo_outcomes_path(*, memos_path: str | Path | None = None) -> Path:
    if memos_path:
        return (
            Path(memos_path)
            .expanduser()
            .resolve()
            .with_name(DEFAULT_NEWS_MEMO_OUTCOMES_PATH.name)
        )
    return DEFAULT_NEWS_MEMO_OUTCOMES_PATH.expanduser().resolve()


def _validate_outcome_row(payload: dict[str, Any], *, lineno: int) -> None:
    if set(payload) != _ROW_FIELDS:
        raise RuntimeError(f"news memo outcome row {lineno} has invalid schema fields")
    for field_name in _STRING_FIELDS:
        field_value = payload.get(field_name)
        if not isinstance(field_value, str):
            raise RuntimeError(
                f"news memo outcome row {lineno} field {field_name} is not a string"
            )
        if field_value != field_value.strip():
            raise RuntimeError(
                f"news memo outcome row {lineno} field {field_name} is non-canonical"
            )
    for field_name in (
        "correlation_id",
        "source_id",
        "attempt_started_at_utc",
        "updated_at_utc",
    ):
        if not str(payload.get(field_name) or "").strip():
            raise RuntimeError(f"news memo outcome row {lineno} has no {field_name}")

    for field_name in _LIFECYCLE_TIMESTAMP_FIELDS:
        timestamp = str(payload.get(field_name) or "").strip()
        if not timestamp:
            continue
        try:
            canonical = _canonical_utc_timestamp(
                timestamp,
                field_name=field_name,
            )
        except ValueError as exc:
            raise RuntimeError(
                f"news memo outcome row {lineno} has invalid {field_name}"
            ) from exc
        if canonical != timestamp:
            raise RuntimeError(
                f"news memo outcome row {lineno} has non-canonical {field_name}"
            )

    dispatch_state = str(payload.get("dispatch_state") or "").strip()
    terminal_state = str(payload.get("terminal_state") or "").strip()
    accepted_at_utc = str(payload.get("accepted_at_utc") or "").strip()
    completed_at_utc = str(payload.get("completed_at_utc") or "").strip()
    if dispatch_state not in _DISPATCH_STATES:
        raise RuntimeError(f"news memo outcome row {lineno} has invalid dispatch_state")
    if terminal_state not in _ROW_TERMINAL_STATES:
        raise RuntimeError(f"news memo outcome row {lineno} has invalid terminal_state")
    if bool(accepted_at_utc) != (dispatch_state == "accepted"):
        raise RuntimeError(
            f"news memo outcome row {lineno} has inconsistent acceptance fields"
        )
    if bool(completed_at_utc) != bool(terminal_state):
        raise RuntimeError(
            f"news memo outcome row {lineno} has inconsistent terminal fields"
        )
    if (dispatch_state == "dispatch_failed") != (terminal_state == "dispatch_failed"):
        raise RuntimeError(
            f"news memo outcome row {lineno} has inconsistent dispatch failure"
        )
    if not dispatch_state and not terminal_state:
        raise RuntimeError(f"news memo outcome row {lineno} has no lifecycle evidence")


def load_news_memo_outcomes(path: str | Path) -> list[dict[str, Any]]:
    outcomes_path = Path(path).expanduser().resolve()
    if not outcomes_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with outcomes_path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"news memo outcome row {lineno} is not a JSON object"
                )
            schema_version = payload.get("schema_version")
            if type(schema_version) is not int or schema_version != _SCHEMA_VERSION:
                raise RuntimeError(
                    f"news memo outcome row {lineno} has unsupported schema_version"
                )
            _validate_outcome_row(payload, lineno=lineno)
            correlation_id = str(payload.get("correlation_id") or "").strip()
            if correlation_id in seen:
                raise RuntimeError(
                    f"news memo outcome row {lineno} duplicates correlation_id"
                )
            seen.add(correlation_id)
            rows.append(payload)
    return rows


def _cooperative_owner(path: Path) -> tuple[int, int]:
    anchor = path if path.exists() else path.parent
    metadata = anchor.stat()
    return metadata.st_uid, metadata.st_gid


def _apply_cooperative_metadata(
    file_descriptor: int,
    *,
    owner_uid: int,
    owner_gid: int,
) -> None:
    if os.geteuid() == 0:
        os.fchown(file_descriptor, owner_uid, owner_gid)
    os.fchmod(file_descriptor, _SHARED_FILE_MODE)


def _open_cooperative_lock(path: Path, *, owner_source: Path) -> TextIO:
    owner_uid, owner_gid = _cooperative_owner(owner_source)
    file_descriptor = os.open(
        path,
        os.O_RDWR | os.O_CREAT | os.O_CLOEXEC,
        _SHARED_FILE_MODE,
    )
    try:
        _apply_cooperative_metadata(
            file_descriptor,
            owner_uid=owner_uid,
            owner_gid=owner_gid,
        )
        return os.fdopen(file_descriptor, "a+", encoding="utf-8")
    except Exception:
        os.close(file_descriptor)
        raise


def _atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    owner_uid, owner_gid = _cooperative_owner(path)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            _apply_cooperative_metadata(
                handle.fileno(),
                owner_uid=owner_uid,
                owner_gid=owner_gid,
            )
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class NewsMemoOutcomeStore:
    def __init__(self, *, memos_path: str | Path | None = None) -> None:
        self.path = resolve_news_memo_outcomes_path(memos_path=memos_path)
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    def record_dispatch_accepted(
        self,
        *,
        correlation_id: str,
        source_id: str,
        attempt_started_at_utc: str,
        task_id: str,
    ) -> dict[str, Any]:
        return self._merge(
            correlation_id=correlation_id,
            source_id=source_id,
            attempt_started_at_utc=attempt_started_at_utc,
            task_id=task_id,
            dispatch_state="accepted",
            accepted_at_utc=utc_now_iso(),
        )

    def record_dispatch_failed(
        self,
        *,
        correlation_id: str,
        source_id: str,
        attempt_started_at_utc: str,
        error_class: str,
    ) -> dict[str, Any]:
        completed_at_utc = utc_now_iso()
        return self._merge(
            correlation_id=correlation_id,
            source_id=source_id,
            attempt_started_at_utc=attempt_started_at_utc,
            dispatch_state="dispatch_failed",
            terminal_state="dispatch_failed",
            reason="broker_dispatch_exception",
            error_class=str(error_class or "").strip(),
            completed_at_utc=completed_at_utc,
        )

    def record_terminal(
        self,
        *,
        correlation_id: str,
        source_id: str,
        attempt_started_at_utc: str,
        task_id: str,
        terminal_state: str,
        reason: str = "",
        error_class: str = "",
    ) -> dict[str, Any]:
        normalized_state = str(terminal_state or "").strip()
        if normalized_state not in _TERMINAL_STATES:
            raise ValueError(f"unsupported news memo terminal_state: {terminal_state}")
        return self._merge(
            correlation_id=correlation_id,
            source_id=source_id,
            attempt_started_at_utc=attempt_started_at_utc,
            task_id=task_id,
            terminal_state=normalized_state,
            reason=str(reason or "").strip(),
            error_class=str(error_class or "").strip(),
            completed_at_utc=utc_now_iso(),
        )

    def reconcile_latest(
        self,
        source_ids: Iterable[str],
        *,
        sample_limit: int = 10,
    ) -> dict[str, Any]:
        ordered_source_ids = list(
            dict.fromkeys(
                normalized
                for source_id in source_ids
                if (normalized := str(source_id or "").strip())
            )
        )
        classes = (
            "accepted-pending",
            "completed",
            "needs-retry",
            "failed",
            "dispatch-failed",
            "no-attempt",
        )
        counts = {classification: 0 for classification in classes}
        samples: dict[str, list[dict[str, str]]] = {
            classification: [] for classification in classes
        }
        exists = self.path.exists()
        try:
            rows = load_news_memo_outcomes(self.path)
        except Exception as exc:
            return {
                "status": "degraded",
                "path": str(self.path),
                "exists": exists,
                "read_errors": 1,
                "read_error_classes": [type(exc).__name__],
                "counts": counts,
                "samples": samples,
            }

        requested = set(ordered_source_ids)
        latest_by_source: dict[str, dict[str, Any]] = {}
        for row in rows:
            source_id = str(row.get("source_id") or "").strip()
            if source_id not in requested:
                continue
            ordering_key = (
                str(row.get("attempt_started_at_utc") or ""),
                str(row.get("correlation_id") or ""),
            )
            current = latest_by_source.get(source_id)
            if current is None or ordering_key > (
                str(current.get("attempt_started_at_utc") or ""),
                str(current.get("correlation_id") or ""),
            ):
                latest_by_source[source_id] = row

        bounded_sample_limit = max(0, int(sample_limit))
        for source_id in ordered_source_ids:
            row = latest_by_source.get(source_id)
            terminal_state = str((row or {}).get("terminal_state") or "").strip()
            dispatch_state = str((row or {}).get("dispatch_state") or "").strip()
            if terminal_state == "completed":
                classification = "completed"
            elif terminal_state == "needs_retry":
                classification = "needs-retry"
            elif terminal_state == "failed":
                classification = "failed"
            elif terminal_state == "dispatch_failed":
                classification = "dispatch-failed"
            elif dispatch_state == "accepted":
                classification = "accepted-pending"
            else:
                classification = "no-attempt"
            counts[classification] += 1
            if len(samples[classification]) < bounded_sample_limit:
                samples[classification].append(
                    {
                        "source_id": source_id,
                        "correlation_id": str((row or {}).get("correlation_id") or ""),
                        "task_id": str((row or {}).get("task_id") or ""),
                    }
                )

        return {
            "status": "ok",
            "path": str(self.path),
            "exists": exists,
            "read_errors": 0,
            "read_error_classes": [],
            "counts": counts,
            "samples": samples,
        }

    def _merge(
        self,
        *,
        correlation_id: str,
        source_id: str,
        attempt_started_at_utc: str,
        task_id: str = "",
        dispatch_state: str = "",
        accepted_at_utc: str = "",
        terminal_state: str = "",
        reason: str = "",
        error_class: str = "",
        completed_at_utc: str = "",
    ) -> dict[str, Any]:
        normalized_correlation_id = str(correlation_id or "").strip()
        normalized_source_id = str(source_id or "").strip()
        normalized_started_at = str(attempt_started_at_utc or "").strip()
        if not normalized_correlation_id:
            raise ValueError("news memo outcome correlation_id is required")
        if not normalized_source_id:
            raise ValueError("news memo outcome source_id is required")
        if not normalized_started_at:
            raise ValueError("news memo outcome attempt_started_at_utc is required")
        normalized_started_at = _canonical_utc_timestamp(
            normalized_started_at,
            field_name="attempt_started_at_utc",
        )
        normalized_accepted_at = (
            _canonical_utc_timestamp(
                accepted_at_utc,
                field_name="accepted_at_utc",
            )
            if accepted_at_utc
            else ""
        )
        normalized_completed_at = (
            _canonical_utc_timestamp(
                completed_at_utc,
                field_name="completed_at_utc",
            )
            if completed_at_utc
            else ""
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _open_cooperative_lock(
            self.lock_path,
            owner_source=self.path,
        ) as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            rows = load_news_memo_outcomes(self.path)
            existing = next(
                (
                    row
                    for row in rows
                    if str(row.get("correlation_id") or "") == normalized_correlation_id
                ),
                None,
            )
            if existing is None:
                merged = {
                    "schema_version": _SCHEMA_VERSION,
                    "correlation_id": normalized_correlation_id,
                    "source_id": normalized_source_id,
                    "task_id": "",
                    "attempt_started_at_utc": normalized_started_at,
                    "dispatch_state": "",
                    "accepted_at_utc": "",
                    "terminal_state": "",
                    "reason": "",
                    "error_class": "",
                    "completed_at_utc": "",
                    "updated_at_utc": "",
                }
                rows.append(merged)
            else:
                merged = existing
                if str(merged.get("source_id") or "") != normalized_source_id:
                    raise RuntimeError("news memo outcome source_id conflict")
                if (
                    str(merged.get("attempt_started_at_utc") or "")
                    != normalized_started_at
                ):
                    raise RuntimeError(
                        "news memo outcome attempt_started_at_utc conflict"
                    )

            normalized_task_id = str(task_id or "").strip()
            existing_task_id = str(merged.get("task_id") or "").strip()
            if normalized_task_id and existing_task_id not in {"", normalized_task_id}:
                raise RuntimeError("news memo outcome task_id conflict")
            if normalized_task_id:
                merged["task_id"] = normalized_task_id

            existing_dispatch = str(merged.get("dispatch_state") or "").strip()
            if dispatch_state and existing_dispatch not in {"", dispatch_state}:
                raise RuntimeError("news memo outcome dispatch_state conflict")
            if dispatch_state:
                merged["dispatch_state"] = dispatch_state
            if normalized_accepted_at:
                existing_accepted_at = str(merged.get("accepted_at_utc") or "").strip()
                if not existing_accepted_at:
                    merged["accepted_at_utc"] = normalized_accepted_at

            existing_terminal = str(merged.get("terminal_state") or "").strip()
            if terminal_state and existing_terminal not in {"", terminal_state}:
                raise RuntimeError("news memo outcome terminal_state conflict")
            if terminal_state:
                merged["terminal_state"] = terminal_state
                for field_name, field_value in (
                    ("reason", reason),
                    ("error_class", error_class),
                ):
                    existing_value = str(merged.get(field_name) or "").strip()
                    if field_value and existing_value not in {"", field_value}:
                        raise RuntimeError(f"news memo outcome {field_name} conflict")
                    if field_value and not existing_value:
                        merged[field_name] = field_value
                if (
                    normalized_completed_at
                    and not str(merged.get("completed_at_utc") or "").strip()
                ):
                    merged["completed_at_utc"] = normalized_completed_at
            merged["updated_at_utc"] = _canonical_utc_timestamp(
                utc_now_iso(),
                field_name="updated_at_utc",
            )
            rows.sort(
                key=lambda row: (
                    str(row.get("attempt_started_at_utc") or ""),
                    str(row.get("correlation_id") or ""),
                )
            )
            _atomic_write_jsonl(self.path, rows)
            return dict(merged)
