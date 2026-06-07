from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings

RUN_STATUS_ROOT = (
    Path(settings.data_root).resolve() / "reports" / "extraction_review" / "run_status"
)
MAX_EVENTS = 200
EXPECTED_STAGE_SEQUENCE = (
    "parser",
    "pass1_classifier",
    "pass2_locator",
    "pass3a_metrics",
    "pass3b_narrative",
    "pass4_reconciliation",
    "validation",
    "chunking",
    "embedding",
    "persistence",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _elapsed_ms(started_at: str | None, completed_at: str | None = None) -> int:
    started = _parse_iso(started_at)
    if started is None:
        return 0
    finished = _parse_iso(completed_at) or _now()
    return max(0, int((finished - started).total_seconds() * 1000))


def _elapsed_between(started_at: str | None, timestamp: str | None) -> int:
    started = _parse_iso(started_at)
    finished = _parse_iso(timestamp)
    if started is None or finished is None:
        return 0
    return max(0, int((finished - started).total_seconds() * 1000))


def _path(run_id: str) -> Path:
    return RUN_STATUS_ROOT / f"{run_id}.json"


def _base_payload(
    *,
    run_id: str,
    document_id: str,
    requested_method: str,
    strict_method: bool,
) -> dict[str, Any]:
    now = _now_iso()
    return {
        "run_id": run_id,
        "document_id": document_id,
        "requested_method": requested_method,
        "actual_method": None,
        "strict_method": bool(strict_method),
        "stage": "queued",
        "status": "pending",
        "queued_at": now,
        "worker_started_at": None,
        "started_at": None,
        "updated_at": now,
        "completed_at": None,
        "elapsed_ms": 0,
        "queue_wait_ms": 0,
        "last_message": "Extraction run queued.",
        "warning_codes": [],
        "error_codes": [],
        "warnings": [],
        "errors": [],
        "stage_timings_ms": {},
        "final_summary": None,
        "events": [],
        "_stage_started_at": {},
    }


def _append_issue(
    bucket: list[dict[str, Any]],
    *,
    stage: str,
    code: str,
    message: str,
    timestamp: str,
    details: Mapping[str, Any] | None,
) -> None:
    issue_details = dict(details or {})
    for existing in bucket:
        if (
            str(existing.get("stage") or "") == stage
            and str(existing.get("code") or "") == code
            and existing.get("details") == issue_details
        ):
            return
    bucket.append(
        {
            "stage": stage,
            "code": code,
            "message": message,
            "timestamp": timestamp,
            "details": issue_details,
        }
    )


def _terminal_status(status: str) -> bool:
    return status in {"succeeded", "failed", "blocked", "skipped"}


def _record_stage_timing(
    payload: dict[str, Any], *, stage: str, status: str, timestamp: str
) -> None:
    started = dict(payload.get("_stage_started_at") or {})
    timings = dict(payload.get("stage_timings_ms") or {})
    if status == "running":
        started.setdefault(stage, timestamp)
    elif _terminal_status(status):
        stage_started_at = started.pop(stage, None)
        if stage_started_at is None:
            timings.setdefault(stage, 0)
        else:
            timings[stage] = _elapsed_between(stage_started_at, timestamp)
    payload["_stage_started_at"] = started
    payload["stage_timings_ms"] = timings


def _add_missing_stage_warnings(payload: dict[str, Any], *, timestamp: str) -> None:
    warning_codes = set(payload.get("warning_codes") or [])
    if {
        "extraction_disabled",
        "extraction_skipped_non_financial_title",
    } & warning_codes:
        return
    seen_stages = {
        str(event.get("stage") or "") for event in payload.get("events") or []
    }
    warnings = list(payload.get("warnings") or [])
    warning_codes_list = list(payload.get("warning_codes") or [])
    for stage in EXPECTED_STAGE_SEQUENCE:
        if stage in seen_stages:
            continue
        code = f"missing_stage_event:{stage}"
        _append_issue(
            warnings,
            stage=stage,
            code=code,
            message=f"No observability event was recorded for stage '{stage}'.",
            timestamp=timestamp,
            details={"expected_stage": stage},
        )
        if code not in warning_codes_list:
            warning_codes_list.append(code)
    payload["warnings"] = warnings
    payload["warning_codes"] = warning_codes_list


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load(run_id: str) -> dict[str, Any] | None:
    path = _path(run_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def has_run_status(run_id: str) -> bool:
    return _path(str(run_id or "").strip()).exists()


def initialize_run_status(
    *,
    run_id: str,
    document_id: str,
    requested_method: str,
    strict_method: bool,
    message: str = "Extraction run queued.",
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _load(run_id) or _base_payload(
        run_id=run_id,
        document_id=document_id,
        requested_method=requested_method,
        strict_method=strict_method,
    )
    return emit_run_event(
        run_id=run_id,
        document_id=document_id,
        requested_method=requested_method,
        actual_method=None,
        strict_method=strict_method,
        stage="queued",
        status="pending",
        message=message,
        details=details,
        payload=payload,
    )


def emit_run_event(
    *,
    run_id: str,
    document_id: str,
    requested_method: str,
    actual_method: str | None,
    strict_method: bool,
    stage: str,
    status: str,
    message: str,
    warning_code: str | None = None,
    error_code: str | None = None,
    details: Mapping[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = (
        payload
        or _load(run_id)
        or _base_payload(
            run_id=run_id,
            document_id=document_id,
            requested_method=requested_method,
            strict_method=strict_method,
        )
    )
    now = _now_iso()
    current.setdefault("queued_at", current.get("started_at") or now)
    current.setdefault("worker_started_at", None)
    current.setdefault("started_at", None)
    current.setdefault("warning_codes", [])
    current.setdefault("error_codes", [])
    current.setdefault("warnings", [])
    current.setdefault("errors", [])
    current.setdefault("stage_timings_ms", {})
    current.setdefault("_stage_started_at", {})
    if stage == "starting" and not current.get("worker_started_at"):
        current["worker_started_at"] = now
        current["started_at"] = now
        current["queue_wait_ms"] = _elapsed_between(current.get("queued_at"), now)
    _record_stage_timing(current, stage=stage, status=status, timestamp=now)
    current.update(
        {
            "document_id": document_id,
            "requested_method": requested_method,
            "actual_method": actual_method or current.get("actual_method"),
            "strict_method": bool(strict_method),
            "stage": stage,
            "status": status,
            "updated_at": now,
            "last_message": message,
            "elapsed_ms": _elapsed_ms(
                current.get("queued_at"), current.get("completed_at")
            ),
        }
    )
    event = {
        "run_id": run_id,
        "document_id": document_id,
        "requested_method": requested_method,
        "actual_method": actual_method,
        "strict_method": bool(strict_method),
        "stage": stage,
        "status": status,
        "timestamp": now,
        "elapsed_ms": current.get("elapsed_ms", 0),
        "message": message,
        "warning_code": warning_code,
        "error_code": error_code,
        "details": dict(details or {}),
    }
    current["events"] = [*(current.get("events") or []), event][-MAX_EVENTS:]
    if warning_code and warning_code not in current["warning_codes"]:
        current["warning_codes"].append(warning_code)
        _append_issue(
            current["warnings"],
            stage=stage,
            code=warning_code,
            message=message,
            timestamp=now,
            details=details,
        )
    if error_code and error_code not in current["error_codes"]:
        current["error_codes"].append(error_code)
        _append_issue(
            current["errors"],
            stage=stage,
            code=error_code,
            message=message,
            timestamp=now,
            details=details,
        )
    if status in {"failed", "blocked"} and not error_code:
        code = f"{stage}_{status}"
        if code not in current["error_codes"]:
            current["error_codes"].append(code)
        _append_issue(
            current["errors"],
            stage=stage,
            code=code,
            message=message,
            timestamp=now,
            details=details,
        )
    if status in {"failed", "blocked"}:
        current["completed_at"] = now
    if stage == "completed" and status == "succeeded":
        current["completed_at"] = now
    if current.get("completed_at"):
        current["elapsed_ms"] = _elapsed_ms(
            current.get("queued_at"), current.get("completed_at")
        )
        if stage == "completed" and status == "succeeded":
            _add_missing_stage_warnings(current, timestamp=now)
    _write(_path(run_id), current)
    return current


def attach_final_summary(run_id: str, summary: Mapping[str, Any]) -> dict[str, Any]:
    payload = _load(run_id)
    if payload is None:
        raise FileNotFoundError(f"run status not found: {run_id}")
    payload["final_summary"] = dict(summary)
    _write(_path(run_id), payload)
    return payload


def get_run_status(run_id: str, *, limit: int = 120) -> dict[str, Any]:
    payload = _load(run_id)
    if payload is None:
        raise FileNotFoundError(f"run status not found: {run_id}")
    events = list(payload.get("events") or [])[-max(1, min(limit, 500)) :]
    summary = dict(payload)
    summary.pop("events", None)
    summary.pop("_stage_started_at", None)
    return {"summary": summary, "events": events}


class ExtractionRunObserver:
    def __init__(
        self,
        *,
        run_id: str,
        document_id: str,
        requested_method: str,
        strict_method: bool,
    ) -> None:
        self.run_id = run_id
        self.document_id = document_id
        self.requested_method = requested_method
        self.strict_method = bool(strict_method)
        self.actual_method: str | None = None

    def set_actual_method(self, actual_method: str | None) -> None:
        self.actual_method = str(actual_method or "").strip() or self.actual_method

    def emit(
        self,
        stage: str,
        status: str,
        message: str,
        *,
        warning_code: str | None = None,
        error_code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return emit_run_event(
            run_id=self.run_id,
            document_id=self.document_id,
            requested_method=self.requested_method,
            actual_method=self.actual_method,
            strict_method=self.strict_method,
            stage=stage,
            status=status,
            message=message,
            warning_code=warning_code,
            error_code=error_code,
            details=details,
        )

    def final_summary(self, summary: Mapping[str, Any]) -> dict[str, Any]:
        return attach_final_summary(self.run_id, summary)
