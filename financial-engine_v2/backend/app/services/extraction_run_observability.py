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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _path(run_id: str) -> Path:
    return RUN_STATUS_ROOT / f"{run_id}.json"


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


def initialize_run_status(
    *,
    run_id: str,
    document_id: str,
    requested_method: str,
    strict_method: bool,
    message: str = "Extraction run queued.",
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "document_id": document_id,
        "requested_method": requested_method,
        "actual_method": None,
        "strict_method": bool(strict_method),
        "stage": "queued",
        "status": "pending",
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
        "completed_at": None,
        "elapsed_ms": 0,
        "last_message": message,
        "warning_codes": [],
        "error_codes": [],
        "warnings": [],
        "errors": [],
        "stage_timings_ms": {},
        "final_summary": None,
        "events": [],
    }
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
        or initialize_run_status(
            run_id=run_id,
            document_id=document_id,
            requested_method=requested_method,
            strict_method=strict_method,
        )
    )
    now = _now_iso()
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
    if error_code and error_code not in current["error_codes"]:
        current["error_codes"].append(error_code)
    if status in {"failed", "blocked"}:
        current["completed_at"] = now
    if stage == "completed" and status == "succeeded":
        current["completed_at"] = now
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
