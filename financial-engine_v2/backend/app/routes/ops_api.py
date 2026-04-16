"""Operational job-status API routes.

Provides REST endpoints for querying job runs, events, and artifacts,
plus an SSE endpoint for live streaming of job updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.routes import require_api_key
from app.services.job_tracker import get_tracker

logger = logging.getLogger(__name__)

router = APIRouter()


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
    items, total = tracker.store.list_job_runs(
        status=status, job_type=job_type, ticker=ticker, limit=limit, offset=offset
    )
    return {"items": items, "total": total}


@router.get("/jobs/active", response_model=JobListResponse)
def list_active_jobs():
    tracker = _require_tracker()
    items, total = tracker.store.list_job_runs(status="pending,running", limit=100)
    return {"items": items, "total": total}


@router.get("/jobs/{job_id}", response_model=JobRunResponse)
def get_job(job_id: str):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return run


@router.get("/jobs/{job_id}/events", response_model=JobEventListResponse)
def get_job_events(
    job_id: str,
    limit: int = Query(200, ge=1, le=1000),
):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    events = tracker.store.list_job_events(job_id, limit=limit)
    return {"items": events}


@router.get("/jobs/{job_id}/artifacts", response_model=JobArtifactListResponse)
def get_job_artifacts(job_id: str):
    tracker = _require_tracker()
    run = tracker.store.get_job_run(job_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
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
