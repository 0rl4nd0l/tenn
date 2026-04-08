from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import PROJECT_ROOT, settings
from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.cockpit_service import CockpitService

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class ServiceHealthItem(BaseModel):
    name: str
    status: str  # "healthy" | "degraded" | "down" | "unknown"
    endpoint: str | None = None
    response_time_ms: float | None = None
    error: str | None = None


class AggregatedHealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "down"
    services: list[ServiceHealthItem] = Field(default_factory=list)


class CockpitConfigResponse(BaseModel):
    llm_model: str | None = None
    llm_endpoint: str | None = None
    extract_model: str | None = None
    embed_model: str | None = None
    routing_policy: str | None = None
    backend_url: str | None = None
    profile: str | None = None
    features: dict[str, bool] = Field(default_factory=dict)
    python_version: str | None = None
    git_branch: str | None = None
    data_root: str | None = None


class QueueStatusResponse(BaseModel):
    pending: int = 0
    active: int = 0
    completed: int = 0
    failed: int = 0


# ---------------------------------------------------------------------------
# Helper: probe a single HTTP endpoint
# ---------------------------------------------------------------------------


def _probe_http(url: str, path: str, *, timeout: float = 3.0) -> tuple[bool, float, str | None]:
    """Return (reachable, latency_ms, error_or_none)."""
    target = str(url or "").strip().rstrip("/")
    if not target:
        return False, 0.0, "not configured"
    try:
        start = time.monotonic()
        resp = httpx.get(f"{target}{path}", timeout=timeout)
        elapsed_ms = (time.monotonic() - start) * 1000
        resp.raise_for_status()
        return True, round(elapsed_ms, 1), None
    except Exception as exc:
        return False, 0.0, str(exc)


# ---------------------------------------------------------------------------
# GET /api/cockpit/health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=AggregatedHealthResponse)
def cockpit_health() -> AggregatedHealthResponse:
    """Aggregated health check probing backend, llama.cpp, Ollama, Qdrant, and Redis."""
    services: list[ServiceHealthItem] = []

    # 1. Backend (self-check — always healthy if this code runs)
    services.append(ServiceHealthItem(
        name="backend",
        status="healthy",
        endpoint="http://localhost:8000",
    ))

    # 2. llama.cpp
    llamacpp_url = str(settings.llamacpp_url or "").strip().rstrip("/")
    ok, latency, err = _probe_http(llamacpp_url, "/v1/models")
    services.append(ServiceHealthItem(
        name="llamacpp",
        status="healthy" if ok else "down",
        endpoint=llamacpp_url or None,
        response_time_ms=latency if ok else None,
        error=err,
    ))

    # 3. Ollama
    ollama_url = str(settings.ollama_url or "").strip().rstrip("/")
    if ollama_url:
        ok, latency, err = _probe_http(ollama_url, "/api/tags")
        services.append(ServiceHealthItem(
            name="ollama",
            status="healthy" if ok else "down",
            endpoint=ollama_url,
            response_time_ms=latency if ok else None,
            error=err,
        ))
    else:
        services.append(ServiceHealthItem(
            name="ollama",
            status="unknown",
            error="not configured",
        ))

    # 4. Qdrant
    qdrant_url = str(settings.qdrant_url or "").strip().rstrip("/")
    if settings.enable_qdrant and qdrant_url:
        ok, latency, err = _probe_http(qdrant_url, "/collections")
        services.append(ServiceHealthItem(
            name="qdrant",
            status="healthy" if ok else "down",
            endpoint=qdrant_url,
            response_time_ms=latency if ok else None,
            error=err,
        ))
    else:
        services.append(ServiceHealthItem(
            name="qdrant",
            status="unknown",
            error="disabled" if not settings.enable_qdrant else "not configured",
        ))

    # 5. Redis
    redis_ok = False
    redis_err: str | None = None
    try:
        import socket as _socket

        parsed = urlparse(str(settings.celery_broker_url or ""))
        host = str(parsed.hostname or "127.0.0.1").strip()
        port = int(parsed.port or 6379)
        start = time.monotonic()
        with _socket.create_connection((host, port), timeout=2.0):
            redis_latency = round((time.monotonic() - start) * 1000, 1)
            redis_ok = True
    except Exception as exc:
        redis_latency = 0.0
        redis_err = str(exc)

    services.append(ServiceHealthItem(
        name="redis",
        status="healthy" if redis_ok else "down",
        endpoint=str(settings.celery_broker_url or None),
        response_time_ms=redis_latency if redis_ok else None,
        error=redis_err,
    ))

    # Derive overall status
    statuses = [s.status for s in services]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "down" for s in statuses if s != "unknown"):
        overall = "degraded"
    else:
        overall = "healthy"

    return AggregatedHealthResponse(status=overall, services=services)


# ---------------------------------------------------------------------------
# GET /api/cockpit/config
# ---------------------------------------------------------------------------


def _git_branch() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=PROJECT_ROOT.parent,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


@router.get("/config", response_model=CockpitConfigResponse)
def cockpit_config() -> CockpitConfigResponse:
    """Return system configuration for the cockpit settings screen."""
    from app.services.llamacpp_runtime import resolve_llm_runtime_config

    llm_endpoint: str | None = None
    llm_model: str | None = None
    try:
        llm_url, llm_mdl = resolve_llm_runtime_config()
        llm_endpoint = llm_url
        llm_model = llm_mdl
    except Exception:
        llm_endpoint = str(settings.llamacpp_url or "").strip() or None
        llm_model = None

    import os

    return CockpitConfigResponse(
        llm_model=llm_model,
        llm_endpoint=llm_endpoint,
        extract_model=str(settings.extract_model or "").strip() or None,
        embed_model=str(settings.embed_model or "").strip() or None,
        routing_policy="adaptive",
        backend_url="http://localhost:8000",
        profile=os.environ.get("LOCAL_BACKEND_PROFILE"),
        features={
            "web_search": False,
            "rag": bool(settings.enable_embeddings and settings.enable_qdrant),
            "extraction": bool(settings.enable_extraction),
            "session_memory": bool(getattr(settings, "enable_session_memory", True)),
        },
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        git_branch=_git_branch(),
        data_root=str(settings.data_root or "").strip() or None,
    )


# ---------------------------------------------------------------------------
# GET /api/cockpit/queue
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=QueueStatusResponse)
def cockpit_queue_status() -> QueueStatusResponse:
    """Return queue statistics in the shape the cockpit UI expects.

    Maps the richer Redis-based queue probe into {pending, active, completed, failed}.
    Celery does not natively expose completed/failed counts via broker state alone,
    so those are reported as 0 unless a result backend is queryable.
    """
    total_queued = 0
    try:
        parsed = urlparse(str(settings.celery_broker_url or ""))
        host = str(parsed.hostname or "127.0.0.1").strip()
        port = int(parsed.port or 6379)

        import socket as _socket

        with _socket.create_connection((host, port), timeout=2.0):
            pass  # socket reachable

        import redis as redis_lib
        from app.celery_app import _SPECIALIZED_QUEUES

        db = int((parsed.path or "").lstrip("/") or "0")
        client = redis_lib.Redis(host=host, port=port, db=db, socket_timeout=2)
        for queue_name in _SPECIALIZED_QUEUES:
            depth = client.llen(queue_name) or 0
            total_queued += depth
        client.close()
    except Exception as exc:
        logger.debug("Queue status probe failed (non-fatal): %s", exc)

    return QueueStatusResponse(
        pending=total_queued,
        active=0,
        completed=0,
        failed=0,
    )


# ---------------------------------------------------------------------------
# GET /api/cockpit/docs
# ---------------------------------------------------------------------------


@router.get("/docs")
def cockpit_docs():
    """Return recent documents across all tickers for the cockpit history screen.

    Unlike the main /api/docs endpoint which requires a ticker parameter, this
    returns the most recent documents globally (capped at 200).
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(Document)
            .order_by(Document.published_at.desc().nullslast())
            .limit(200)
            .all()
        )
        return [
            {
                "document_id": str(r.document_id),
                "ticker": r.ticker,
                "doc_class": r.doc_class,
                "doc_subtype": r.doc_subtype,
                "published_at": r.published_at,
                "title": r.title,
                "source_url": r.source_url,
                "pdf_path": r.pdf_path,
            }
            for r in rows
        ]
    finally:
        db.close()

class CockpitChatRequest(BaseModel):
    message: str
    mode: str = "analysis"
    ticker: str | None = None
    session_id: str | None = None
    stream: bool = True

@router.post("/chat")
async def cockpit_chat(payload: CockpitChatRequest, request: Request):
    """
    Unified cockpit chat endpoint supporting SSE streaming.
    Matches the TUI's ChatController logic but exposed for the Web UI.
    """
    service = CockpitService.get_instance()
    
    if not payload.stream:
        # Blocking implementation if requested (rare for this UI)
        response = service.chat_stream(
            message=payload.message,
            ticker=payload.ticker,
            session_id=payload.session_id
        )
        return {
            "type": "done",
            "data": {
                "text": response.text,
                "model": response.routing_metadata.get("model") if response.routing_metadata else "local",
                "latency_ms": response.routing_metadata.get("latency_ms") if response.routing_metadata else 0,
                "cost_usd": response.routing_metadata.get("cost_usd") if response.routing_metadata else 0,
            }
        }

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_chunk(chunk: str):
            # This runs in the LLM thread (from ChatController)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "chunk", "data": {"text": chunk}})

        async def run_chat():
            try:
                # ChatController.build_chat_response is synchronous and blocking.
                # We run it in a thread to keep the event loop free.
                response = await asyncio.to_thread(
                    service.chat_stream,
                    message=payload.message,
                    ticker=payload.ticker,
                    session_id=payload.session_id,
                    on_chunk=on_chunk
                )
                
                # After streaming finishes, send metadata and final state
                if response.tool_traces:
                    for trace in response.tool_traces:
                        await queue.put({"type": "tool_trace", "data": trace})
                
                if response.evidence:
                    # Filter/format sources for the UI
                    sources = []
                    for ev in response.evidence:
                        if ev.get("type") == "local_context":
                            details = ev.get("details", {})
                            for hit in details.get("qual_context", {}).get("hits", []):
                                sources.append({
                                    "title": hit.get("title") or hit.get("file") or "Source",
                                    "score": hit.get("score") or hit.get("final_score") or 0.0
                                })
                    if sources:
                        await queue.put({"type": "sources", "data": {"items": sources}})

                if response.action_preview:
                    await queue.put({"type": "action_preview", "data": response.action_preview})

                # Final 'done' event with metrics
                meta = response.routing_metadata or {}
                await queue.put({
                    "type": "done",
                    "data": {
                        "text": response.text,
                        "model": meta.get("model", "local"),
                        "latency_ms": meta.get("latency_ms", 0),
                        "cost_usd": meta.get("cost_usd", 0),
                        "source": meta.get("source", "local")
                    }
                })
            except Exception as exc:
                logger.exception("Cockpit chat streaming error")
                await queue.put({"type": "error", "data": str(exc)})
            finally:
                # Signal end of stream
                await queue.put(None)

        # Start the chat worker
        worker_task = asyncio.create_task(run_chat())

        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                worker_task.cancel()
                break
                
            item = await queue.get()
            if item is None:
                break
            
            yield f"data: {json.dumps(item)}\n\n"
        
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
