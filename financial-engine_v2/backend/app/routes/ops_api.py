"""Operational job-status API routes.

Provides REST endpoints for querying job runs, events, and artifacts,
plus an SSE endpoint for live streaming of job updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.routes import require_api_key
from app.services.job_tracker import get_tracker
from app.services.router_state import get_extraction_activity_snapshot

logger = logging.getLogger(__name__)

router = APIRouter()
_SYNTHETIC_EXTRACTION_PREFIX = "extraction-activity:"


# ── Response models ────────────────────────────────────────────────────────


class JobRunResponse(BaseModel):
    job_id: str
    job_type: str
    job_family: str
    status: str
    phase: str | None = None
    title: str
    summary: str | None = None
    trigger_source: str | None = None
    entity_scope: str | None = None
    ticker: str | None = None
    total_items: int = 0
    succeeded_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    warning_count: int = 0
    error_count: int = 0
    current_item_label: str | None = None
    queued_at: str
    started_at: str | None = None
    updated_at: str
    completed_at: str | None = None
    elapsed_ms: int = 0
    metadata: dict[str, Any] | None = None


class JobEventResponse(BaseModel):
    event_id: str
    job_id: str
    event_type: str
    phase: str | None = None
    message: str
    progress_current: int | None = None
    progress_total: int | None = None
    progress_pct: float | None = None
    timestamp: str
    payload: dict[str, Any] | None = None


class JobArtifactResponse(BaseModel):
    artifact_id: str
    job_id: str
    artifact_type: str
    artifact_path: str | None = None
    artifact_label: str
    metadata: dict[str, Any] | None = None
    created_at: str


class JobListResponse(BaseModel):
    items: list[JobRunResponse]
    total: int


class JobEventListResponse(BaseModel):
    items: list[JobEventResponse]


class JobArtifactListResponse(BaseModel):
    items: list[JobArtifactResponse]


class ExternalJobStartRequest(BaseModel):
    job_type: str
    job_family: str
    title: str
    trigger_source: str | None = None
    entity_scope: str | None = None
    ticker: str | None = None
    total_items: int = Field(default=0, ge=0)
    metadata: dict[str, Any] | None = None
    job_id: str | None = None
    start: bool = True
    phase: str | None = None
    phase_message: str | None = None


class ExternalJobPhaseRequest(BaseModel):
    phase: str
    message: str = ""


class ExternalJobCompletionRequest(BaseModel):
    summary: str | None = None


class ExternalJobFailureRequest(BaseModel):
    error: str


class ExternalJobCancellationRequest(BaseModel):
    reason: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────


def _require_tracker():
    tracker = get_tracker()
    if tracker is None:
        raise HTTPException(
            status_code=503,
            detail="Ops tracker not initialized",
        )
    return tracker


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _synthetic_job_id(active_run: dict[str, Any]) -> str | None:
    run_id = _clean_text(active_run.get("run_id"))
    if run_id:
        return run_id
    token = _clean_text(active_run.get("token"))
    if token:
        return f"{_SYNTHETIC_EXTRACTION_PREFIX}{token}"
    return None


def _build_synthetic_extraction_job(active_run: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    job_id = _synthetic_job_id(active_run)
    if not job_id:
        return None

    ticker = _clean_text(active_run.get("ticker"))
    document_id = _clean_text(active_run.get("document_id"))
    title = _clean_text(active_run.get("title"))
    requested_method = _clean_text(active_run.get("requested_method"))
    started_at = _clean_text(active_run.get("started_at")) or _now_iso()

    if title:
        resolved_title = f"{ticker} | {title}" if ticker else title
    elif document_id:
        resolved_title = f"{ticker} | {document_id}" if ticker else document_id
    else:
        resolved_title = "External extraction activity"

    summary = (
        "Extraction activity is running and was reported via the backend extraction activity snapshot. "
        "No persisted ops tracker row exists for this run yet."
    )

    metadata = {
        "synthetic": True,
        "synthetic_source": "extraction_activity",
        "activity_source": source,
        "token": _clean_text(active_run.get("token")),
        "run_id": _clean_text(active_run.get("run_id")),
        "document_id": document_id,
        "requested_method": requested_method,
        "strict_method": active_run.get("strict_method"),
        "expires_at": active_run.get("expires_at"),
        "expires_in_seconds": active_run.get("expires_in_seconds"),
    }

    return {
        "job_id": job_id,
        "job_type": "extraction",
        "job_family": "external_activity",
        "status": "running",
        "phase": requested_method or "active",
        "title": resolved_title,
        "summary": summary,
        "trigger_source": "external",
        "entity_scope": "document",
        "ticker": ticker,
        "total_items": 0,
        "succeeded_items": 0,
        "failed_items": 0,
        "skipped_items": 0,
        "warning_count": 0,
        "error_count": 0,
        "current_item_label": document_id or requested_method,
        "queued_at": started_at,
        "started_at": started_at,
        "updated_at": started_at,
        "completed_at": None,
        "elapsed_ms": 0,
        "metadata": metadata,
    }


def _list_synthetic_extraction_jobs(
    *,
    status: str | None = None,
    job_type: str | None = None,
    ticker: str | None = None,
) -> dict[str, dict[str, Any]]:
    if job_type and job_type != "extraction":
        return {}

    if status:
        requested_statuses = {part.strip() for part in status.split(",") if part.strip()}
        if requested_statuses and requested_statuses.isdisjoint({"pending", "running"}):
            return {}

    snapshot = get_extraction_activity_snapshot()
    if not bool(snapshot.get("active")):
        return {}

    requested_ticker = _clean_text(ticker)
    jobs: dict[str, dict[str, Any]] = {}
    for raw_run in snapshot.get("active_runs") or []:
        if not isinstance(raw_run, dict):
            continue
        run_ticker = _clean_text(raw_run.get("ticker"))
        if requested_ticker and (run_ticker or "").upper() != requested_ticker.upper():
            continue
        synthetic = _build_synthetic_extraction_job(
            raw_run,
            source=str(snapshot.get("source") or "none"),
        )
        if synthetic is None:
            continue
        jobs[str(synthetic["job_id"])] = synthetic
    return jobs


def _merge_visible_jobs(
    persisted_items: list[dict[str, Any]],
    synthetic_jobs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    seen_job_ids = {str(item.get("job_id") or "") for item in persisted_items}
    combined = list(persisted_items)
    combined.extend(
        job
        for job_id, job in synthetic_jobs.items()
        if job_id not in seen_job_ids
    )
    combined.sort(
        key=lambda item: (
            str(item.get("queued_at") or ""),
            str(item.get("job_id") or ""),
        ),
        reverse=True,
    )
    return combined


def _synthetic_job_events(job: dict[str, Any]) -> list[dict[str, Any]]:
    timestamp = str(job.get("started_at") or job.get("queued_at") or _now_iso())
    method = _clean_text(((job.get("metadata") or {}) if isinstance(job.get("metadata"), dict) else {}).get("requested_method"))
    message = "External extraction activity detected."
    if method:
        message = f"External extraction activity detected (method: {method})."
    phase = _clean_text(job.get("phase"))
    return [
        {
            "event_id": f"{job['job_id']}:synthetic-started",
            "job_id": job["job_id"],
            "event_type": "job.started",
            "phase": phase,
            "message": message,
            "progress_current": None,
            "progress_total": None,
            "progress_pct": None,
            "timestamp": timestamp,
            "payload": {
                "synthetic": True,
                "document_id": ((job.get("metadata") or {}) if isinstance(job.get("metadata"), dict) else {}).get("document_id"),
            },
        }
    ]


def _resolve_job(
    tracker,
    job_id: str,
    *,
    synthetic_jobs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    run = tracker.store.get_job_run(job_id)
    if run is not None:
        return run
    synthetic = (synthetic_jobs or _list_synthetic_extraction_jobs()).get(job_id)
    if synthetic is not None:
        return synthetic
    return None


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post(
    "/jobs/external/start",
    response_model=JobRunResponse,
    dependencies=[Depends(require_api_key)],
)
def start_external_job(body: ExternalJobStartRequest):
    tracker = _require_tracker()
    handle = tracker.create_job(
        job_id=body.job_id,
        job_type=body.job_type,
        job_family=body.job_family,
        title=body.title,
        trigger_source=body.trigger_source,
        entity_scope=body.entity_scope,
        ticker=body.ticker,
        total_items=body.total_items,
        metadata=body.metadata,
    )
    if body.start:
        tracker.start_job(handle.job_id)
    if body.phase:
        tracker.change_phase(
            handle.job_id,
            body.phase,
            message=body.phase_message or f"Phase: {body.phase}",
        )
    run = tracker.store.get_job_run(handle.job_id)
    if run is None:
        raise HTTPException(status_code=500, detail="Failed to create external job")
    return run


@router.post(
    "/jobs/{job_id}/external/phase",
    response_model=JobRunResponse,
    dependencies=[Depends(require_api_key)],
)
def set_external_job_phase(job_id: str, body: ExternalJobPhaseRequest):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    tracker.change_phase(job_id, body.phase, message=body.message)
    updated = tracker.store.get_job_run(job_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update job phase")
    return updated


@router.post(
    "/jobs/{job_id}/external/complete",
    response_model=JobRunResponse,
    dependencies=[Depends(require_api_key)],
)
def complete_external_job(job_id: str, body: ExternalJobCompletionRequest):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    tracker.complete_job(job_id, summary=body.summary)
    updated = tracker.store.get_job_run(job_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to complete job")
    return updated


@router.post(
    "/jobs/{job_id}/external/fail",
    response_model=JobRunResponse,
    dependencies=[Depends(require_api_key)],
)
def fail_external_job(job_id: str, body: ExternalJobFailureRequest):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    tracker.fail_job(job_id, body.error)
    updated = tracker.store.get_job_run(job_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to fail job")
    return updated


@router.post(
    "/jobs/{job_id}/external/cancel",
    response_model=JobRunResponse,
    dependencies=[Depends(require_api_key)],
)
def cancel_external_job(job_id: str, body: ExternalJobCancellationRequest):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    tracker.cancel_job(job_id, reason=body.reason)
    updated = tracker.store.get_job_run(job_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to cancel job")
    return updated


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    status: str | None = Query(None, description="Filter by status (comma-separated)"),
    job_type: str | None = Query(None, description="Filter by job type"),
    ticker: str | None = Query(None, description="Filter by ticker"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    tracker = _require_tracker()
    synthetic_jobs = _list_synthetic_extraction_jobs(
        status=status,
        job_type=job_type,
        ticker=ticker,
    )
    fetch_limit = max(limit + offset + len(synthetic_jobs), 1000)
    persisted_items, persisted_total = tracker.store.list_job_runs(
        status=status,
        job_type=job_type,
        ticker=ticker,
        limit=fetch_limit,
        offset=0,
    )
    merged_items = _merge_visible_jobs(persisted_items, synthetic_jobs)
    persisted_ids = {str(item.get("job_id") or "") for item in persisted_items}
    synthetic_total = sum(
        1 for job_id in synthetic_jobs if job_id not in persisted_ids
    )
    return {
        "items": merged_items[offset : offset + limit],
        "total": persisted_total + synthetic_total,
    }


@router.get("/jobs/active", response_model=JobListResponse)
def list_active_jobs():
    tracker = _require_tracker()
    synthetic_jobs = _list_synthetic_extraction_jobs(status="pending,running")
    persisted_items, persisted_total = tracker.store.list_job_runs(
        status="pending,running",
        limit=max(100 + len(synthetic_jobs), 1000),
        offset=0,
    )
    merged_items = _merge_visible_jobs(persisted_items, synthetic_jobs)
    persisted_ids = {str(item.get("job_id") or "") for item in persisted_items}
    synthetic_total = sum(
        1 for job_id in synthetic_jobs if job_id not in persisted_ids
    )
    return {"items": merged_items[:100], "total": persisted_total + synthetic_total}


@router.get("/jobs/{job_id}", response_model=JobRunResponse)
def get_job(job_id: str):
    tracker = _require_tracker()
    synthetic_jobs = _list_synthetic_extraction_jobs()
    run = _resolve_job(tracker, job_id, synthetic_jobs=synthetic_jobs)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return run


@router.get("/jobs/{job_id}/events", response_model=JobEventListResponse)
def get_job_events(
    job_id: str,
    limit: int = Query(200, ge=1, le=1000),
):
    tracker = _require_tracker()
    synthetic_jobs = _list_synthetic_extraction_jobs()
    run = _resolve_job(tracker, job_id, synthetic_jobs=synthetic_jobs)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job_id in synthetic_jobs:
        return {"items": _synthetic_job_events(run)[:limit]}
    events = tracker.store.list_job_events(job_id, limit=limit)
    return {"items": events}


@router.get("/jobs/{job_id}/artifacts", response_model=JobArtifactListResponse)
def get_job_artifacts(job_id: str):
    tracker = _require_tracker()
    synthetic_jobs = _list_synthetic_extraction_jobs()
    run = _resolve_job(tracker, job_id, synthetic_jobs=synthetic_jobs)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job_id in synthetic_jobs:
        return {"items": []}
    artifacts = tracker.store.list_job_artifacts(job_id)
    return {"items": artifacts}


@router.get("/stream")
async def stream_events(
    request: Request,
    job_id: str | None = Query(None, description="Filter to a specific job"),
):
    tracker = _require_tracker()

    async def event_generator():
        q = tracker.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
                    continue

                if job_id and event.get("job_id") != job_id:
                    continue

                yield f"data: {json.dumps(event)}\n\n"
        finally:
            tracker.unsubscribe(q)

    return StreamingResponse(
        event_generator(), media_type="text/event-stream"
    )
