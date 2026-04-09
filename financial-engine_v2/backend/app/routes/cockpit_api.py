from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
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
    details: dict[str, Any] | None = None


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


class ModelInfo(BaseModel):
    id: str
    filename: str
    size_gb: float
    quantization: str | None = None
    available: bool = True


class ModelGroup(BaseModel):
    location: str
    label: str
    models: list[ModelInfo] = Field(default_factory=list)


class AvailableModelsResponse(BaseModel):
    groups: list[ModelGroup] = Field(default_factory=list)
    active_model: str | None = None


class QueueStatusResponse(BaseModel):
    pending: int = 0
    active: int = 0
    completed: int = 0
    failed: int = 0


# ---------------------------------------------------------------------------
# Helper: probe a single HTTP endpoint
# ---------------------------------------------------------------------------


def _probe_http(
    url: str, path: str, *, timeout: float = 3.0
) -> tuple[bool, float, str | None]:
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


def _probe_gpu() -> ServiceHealthItem:
    """Return a compact GPU runtime summary for the cockpit sidebar."""
    try:
        start = time.monotonic()
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    except FileNotFoundError:
        return ServiceHealthItem(
            name="gpu", status="unknown", error="nvidia-smi not installed"
        )
    except subprocess.TimeoutExpired:
        return ServiceHealthItem(
            name="gpu", status="degraded", error="nvidia-smi timed out"
        )
    except Exception as exc:
        return ServiceHealthItem(name="gpu", status="degraded", error=str(exc))

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return ServiceHealthItem(
            name="gpu",
            status="degraded",
            response_time_ms=elapsed_ms,
            error=stderr or f"nvidia-smi exited {result.returncode}",
        )

    lines = [
        line.strip() for line in (result.stdout or "").splitlines() if line.strip()
    ]
    if not lines:
        return ServiceHealthItem(
            name="gpu",
            status="unknown",
            response_time_ms=elapsed_ms,
            error="no GPU devices reported",
        )

    gpus: list[dict[str, Any]] = []
    for line in lines:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            continue
        name, temp_raw, util_raw, used_raw, total_raw = parts[:5]
        try:
            temp = float(temp_raw)
        except ValueError:
            temp = None
        try:
            util = float(util_raw)
        except ValueError:
            util = None
        try:
            used = float(used_raw)
            total = float(total_raw)
        except ValueError:
            used = None
            total = None
        gpus.append(
            {
                "name": name or "GPU",
                "temp_c": temp,
                "util_percent": util,
                "mem_used_mib": used,
                "mem_total_mib": total,
            }
        )

    if not gpus:
        return ServiceHealthItem(
            name="gpu",
            status="unknown",
            response_time_ms=elapsed_ms,
            error="unable to parse GPU status",
        )

    return ServiceHealthItem(
        name="gpu",
        status="healthy",
        response_time_ms=elapsed_ms,
        details={"gpus": gpus},
    )


# ---------------------------------------------------------------------------
# GET /api/cockpit/health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=AggregatedHealthResponse)
def cockpit_health() -> AggregatedHealthResponse:
    """Aggregated health check probing backend, llama.cpp, Ollama, Qdrant, and Redis."""
    services: list[ServiceHealthItem] = []

    # 1. Backend (self-check — always healthy if this code runs)
    services.append(
        ServiceHealthItem(
            name="backend",
            status="healthy",
            endpoint="http://localhost:8000",
        )
    )

    # 2. llama.cpp
    llamacpp_url = str(settings.llamacpp_url or "").strip().rstrip("/")
    ok, latency, err = _probe_http(llamacpp_url, "/v1/models")
    services.append(
        ServiceHealthItem(
            name="llamacpp",
            status="healthy" if ok else "down",
            endpoint=llamacpp_url or None,
            response_time_ms=latency if ok else None,
            error=err,
        )
    )

    # 3. Ollama
    ollama_url = str(settings.ollama_url or "").strip().rstrip("/")
    if ollama_url:
        ok, latency, err = _probe_http(ollama_url, "/api/tags")
        services.append(
            ServiceHealthItem(
                name="ollama",
                status="healthy" if ok else "down",
                endpoint=ollama_url,
                response_time_ms=latency if ok else None,
                error=err,
            )
        )
    else:
        services.append(
            ServiceHealthItem(
                name="ollama",
                status="unknown",
                error="not configured",
            )
        )

    # 4. Qdrant
    qdrant_url = str(settings.qdrant_url or "").strip().rstrip("/")
    if settings.enable_qdrant and qdrant_url:
        ok, latency, err = _probe_http(qdrant_url, "/collections")
        services.append(
            ServiceHealthItem(
                name="qdrant",
                status="healthy" if ok else "down",
                endpoint=qdrant_url,
                response_time_ms=latency if ok else None,
                error=err,
            )
        )
    else:
        services.append(
            ServiceHealthItem(
                name="qdrant",
                status="unknown",
                error="disabled" if not settings.enable_qdrant else "not configured",
            )
        )

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

    services.append(
        ServiceHealthItem(
            name="redis",
            status="healthy" if redis_ok else "down",
            endpoint=str(settings.celery_broker_url or None),
            response_time_ms=redis_latency if redis_ok else None,
            error=redis_err,
        )
    )

    services.append(_probe_gpu())

    # 7. CockpitService initialization
    cs_ok = False
    cs_latency: float = 0.0
    cs_err: str | None = None
    try:
        cs_start = time.monotonic()
        CockpitService.get_instance()
        cs_latency = round((time.monotonic() - cs_start) * 1000, 1)
        cs_ok = True
    except Exception as exc:
        cs_err = str(exc)

    services.append(
        ServiceHealthItem(
            name="cockpit_service",
            status="healthy" if cs_ok else "down",
            response_time_ms=cs_latency if cs_ok else None,
            error=cs_err,
        )
    )

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

    server_models = _fetch_llama_server_models()
    for model_id, info in server_models.items():
        if info.get("status") == "loaded":
            llm_model = model_id
            break

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
# GET /api/cockpit/models
# ---------------------------------------------------------------------------


def _parse_quantization(filename: str) -> str | None:
    """Extract quantization tag from GGUF filename (e.g. 'Q4_K_M' from '...-Q4_K_M.gguf')."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    parts = stem.split("-")
    for part in reversed(parts):
        upper = part.upper()
        if upper.startswith("Q") and any(c.isdigit() for c in upper):
            return upper
        if upper in ("MXFP4", "FP16", "BF16", "F16", "F32"):
            return upper
    return None


def _extract_model_path(status_obj: dict[str, Any]) -> str:
    args_list = status_obj.get("args") or []
    for i, arg in enumerate(args_list):
        if arg == "--model" and i + 1 < len(args_list):
            return str(args_list[i + 1] or "").strip()

    preset_text = str(status_obj.get("preset") or "")
    for line in preset_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip().lower() == "model":
            return value.strip()
    return ""


def _path_location_key(path_text: str) -> str:
    return path_text.replace("\\", "/").rstrip("/").lower()


def _classify_model_location(model_path: str) -> dict[str, str] | None:
    normalized = _path_location_key(model_path)
    if not normalized:
        return None

    for loc in _MODEL_LOCATIONS:
        dir_path = os.environ.get(loc["env_key"], "").strip() if loc["env_key"] else ""
        if not dir_path:
            dir_path = loc["default"]
        if dir_path and normalized.startswith(_path_location_key(dir_path) + "/"):
            return loc

    if "/.cache/llmfit/models/" in normalized:
        return next(loc for loc in _MODEL_LOCATIONS if loc["location"] == "ssd")
    if "/cold_storage/models/" in normalized:
        return next(loc for loc in _MODEL_LOCATIONS if loc["location"] == "hdd")
    return None


def _choose_preferred_model_id(path_stem: str, server_model_ids: list[str]) -> str:
    norm_stem = path_stem.strip().lower()
    if not server_model_ids:
        return path_stem

    normalized_ids = [
        model_id for model_id in server_model_ids if str(model_id).strip()
    ]
    alias_ids = [
        model_id for model_id in normalized_ids if model_id.startswith("model:")
    ]
    for model_id in alias_ids:
        short = model_id.split(":", 1)[1].strip().lower()
        if short and (
            norm_stem == short
            or norm_stem.startswith(short)
            or short.startswith(norm_stem)
        ):
            return model_id

    for model_id in normalized_ids:
        if model_id.strip().lower() == norm_stem:
            return model_id
    return path_stem


def _build_server_model_groups(
    server_models: dict[str, dict[str, Any]],
) -> list[ModelGroup]:
    grouped: dict[str, list[ModelInfo]] = {
        loc["location"]: [] for loc in _MODEL_LOCATIONS
    }
    by_path: dict[str, dict[str, Any]] = {}

    for model_id, info in server_models.items():
        model_path = str(info.get("model_path") or "").strip()
        if not model_path:
            continue
        location = _classify_model_location(model_path)
        if location is None:
            continue

        normalized_path = _path_location_key(model_path)
        entry = by_path.setdefault(
            normalized_path,
            {
                "path": model_path,
                "filename": Path(model_path).name,
                "stem": Path(model_path).stem,
                "location": location,
                "server_ids": set(),
            },
        )
        entry["server_ids"].add(model_id)

    all_server_ids = list(server_models.keys())
    for entry in sorted(
        by_path.values(), key=lambda item: str(item["filename"]).lower()
    ):
        filename = str(entry["filename"])
        path_stem = str(entry["stem"])
        model_path = str(entry["path"])
        model_file = Path(model_path)
        size_gb = 0.0
        if model_file.is_file():
            size_gb = round(model_file.stat().st_size / (1024**3), 1)

        location = entry["location"]
        grouped[location["location"]].append(
            ModelInfo(
                id=_choose_preferred_model_id(
                    path_stem,
                    list(entry["server_ids"]) + all_server_ids,
                ),
                filename=filename,
                size_gb=size_gb,
                quantization=_parse_quantization(filename),
                available=location["location"] != "hdd",
            )
        )

    result: list[ModelGroup] = []
    for loc in _MODEL_LOCATIONS:
        models = grouped.get(loc["location"], [])
        if models:
            result.append(
                ModelGroup(
                    location=loc["location"],
                    label=loc["label"],
                    models=models,
                )
            )
    return result


def _scan_model_directory(dir_path: str) -> list[ModelInfo]:
    """Scan a directory for .gguf files and return ModelInfo list."""
    results: list[ModelInfo] = []
    p = Path(dir_path)
    if not p.is_dir():
        return results
    for f in sorted(p.glob("*.gguf")):
        if not f.is_file():
            continue
        size_bytes = f.stat().st_size
        stem = f.stem
        results.append(
            ModelInfo(
                id=stem,
                filename=f.name,
                size_gb=round(size_bytes / (1024**3), 1),
                quantization=_parse_quantization(f.name),
                available=True,
            )
        )
    return results


_MODEL_LOCATIONS: list[dict[str, str]] = [
    {
        "env_key": "COCKPIT_MODELS_NVME_DIR",
        "default": "/mnt/nvme/tenn/models",
        "label": "NVMe (Fast)",
        "location": "nvme",
    },
    {
        "env_key": "COCKPIT_MODELS_SSD_DIR",
        "default": str(Path.home() / ".cache" / "llmfit" / "models"),
        "label": "SSD Cache",
        "location": "ssd",
    },
    {
        "env_key": "COCKPIT_MODELS_HDD_DIR",
        "default": str(Path.home() / "cold_storage" / "models"),
        "label": "HDD Cold Storage",
        "location": "hdd",
    },
]


def _fetch_llama_server_models() -> dict[str, dict[str, Any]]:
    """Query llama-server /v1/models and return {model_id: {status, path_stem}}."""
    llamacpp_url = str(settings.llamacpp_url or "").strip().rstrip("/")
    if not llamacpp_url:
        return {}
    try:
        resp = httpx.get(f"{llamacpp_url}/v1/models", timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    result: dict[str, dict[str, Any]] = {}
    for entry in data.get("data", []):
        model_id = str(entry.get("id", "")).strip()
        if not model_id:
            continue
        status_obj = entry.get("status") or {}
        status_val = str(status_obj.get("value", "unknown"))
        model_path = _extract_model_path(status_obj)
        result[model_id] = {
            "status": status_val,
            "model_path": model_path,
            "path_stem": Path(model_path).stem if model_path else "",
        }
    return result


@router.get("/models", response_model=AvailableModelsResponse)
def cockpit_available_models() -> AvailableModelsResponse:
    """Return all discoverable GGUF models grouped by storage location.

    Model IDs are resolved from llama-server's registry so the UI sends
    exactly the ID that llama-server expects in chat requests.
    """
    server_models = _fetch_llama_server_models()
    all_server_ids = list(server_models.keys())

    # Build filename_stem → preferred server model ID lookup
    stem_to_server_id: dict[str, str] = {}
    active_model: str | None = None
    for model_id, info in server_models.items():
        if info["status"] == "loaded":
            active_model = model_id
        stem = info.get("path_stem", "")
        if stem:
            # Prefer model:alias form over bare filename stems
            existing = stem_to_server_id.get(stem, "")
            if not existing or model_id.startswith("model:"):
                stem_to_server_id[stem] = model_id

    # Map preset aliases that lack explicit --model paths
    for model_id in server_models:
        if model_id.startswith("model:"):
            short = model_id.split(":", 1)[1]
            if short not in stem_to_server_id:
                stem_to_server_id[short] = model_id

    groups: list[ModelGroup] = []
    seen_files: set[str] = set()

    for loc in _MODEL_LOCATIONS:
        dir_path = os.environ.get(loc["env_key"], "").strip() if loc["env_key"] else ""
        if not dir_path:
            dir_path = loc["default"]

        raw_models = _scan_model_directory(dir_path)
        unique_models: list[ModelInfo] = []
        for m in raw_models:
            if m.filename in seen_files:
                continue
            seen_files.add(m.filename)
            server_id = _choose_preferred_model_id(
                m.id,
                [stem_to_server_id.get(m.id, "")] + all_server_ids,
            )
            unique_models.append(
                ModelInfo(
                    id=server_id if server_id else m.id,
                    filename=m.filename,
                    size_gb=m.size_gb,
                    quantization=m.quantization,
                    available=loc["location"] != "hdd",
                )
            )

        if unique_models:
            groups.append(
                ModelGroup(
                    location=loc["location"],
                    label=loc["label"],
                    models=unique_models,
                )
            )

    if not groups:
        groups = _build_server_model_groups(server_models)

    return AvailableModelsResponse(
        groups=groups,
        active_model=active_model,
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
    active_count = 0
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

        # Probe active tasks via Celery inspect (best-effort, short timeout).
        try:
            from app.celery_app import celery_app

            inspector = celery_app.control.inspect(timeout=1.0)
            active_tasks = inspector.active() or {}
            for worker_tasks in active_tasks.values():
                active_count += len(worker_tasks)
        except Exception:
            pass  # workers may be offline

        client.close()
    except Exception as exc:
        logger.debug("Queue status probe failed (non-fatal): %s", exc)

    return QueueStatusResponse(
        pending=total_queued,
        active=active_count,
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
    model: str | None = None
    web_search: bool | None = None
    rag: bool | None = None
    db_diagnostics: bool | None = None


class CockpitActionExecuteRequest(BaseModel):
    action_id: str
    args: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None


class CockpitActionExecuteResponse(BaseModel):
    ok: bool = True
    action_id: str
    result: str
    exit_code: int = 0
    chart: dict[str, str] | None = None


def _coerce_float(raw: Any) -> float | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _coerce_int(raw: Any) -> int | None:
    value = _coerce_float(raw)
    if value is None:
        return None
    return int(value)


def _resolve_chart_csv_path(repo_root: Path, raw_path: str) -> Path:
    raw_text = str(raw_path or "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Chart CSV path is required")

    candidate = Path(raw_text)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed_root = (repo_root / "reports" / "candles").resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Chart CSV must be under reports/candles",
        ) from exc

    if not candidate.exists():
        raise HTTPException(
            status_code=404, detail=f"Chart CSV not found: {candidate.name}"
        )
    return candidate


def _read_chart_rows_from_csv(csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                {
                    "timestamp": str(row.get("timestamp") or ""),
                    "open": _coerce_float(row.get("open")),
                    "high": _coerce_float(row.get("high")),
                    "low": _coerce_float(row.get("low")),
                    "close": _coerce_float(row.get("close")),
                    "volume": _coerce_int(row.get("volume")),
                }
            )
    return rows


def _build_candlestick_chart_response(
    service: CockpitService,
    action_id: str,
    args: dict[str, Any],
) -> CockpitActionExecuteResponse:
    from cockpit.core.plotly_html import build_candlestick_dashboard_html

    ticker = str(args.get("ticker") or "UNKNOWN").strip().upper() or "UNKNOWN"
    timeframe = str(args.get("timeframe") or "1d").strip() or "1d"
    mode_flag = str(args.get("mode_flag") or "").strip()

    price_state: dict[str, Any] = {}
    recent_history: list[dict[str, Any]] = []
    csv_error: HTTPException | None = None

    if mode_flag == "-f":
        try:
            csv_path = _resolve_chart_csv_path(
                service.repo_root, str(args.get("mode_value") or "")
            )
            recent_history = _read_chart_rows_from_csv(csv_path)
            if recent_history:
                latest_close = recent_history[-1].get("close")
                price_state = {
                    "current": {"close": latest_close},
                    "metrics": {"sample_count": len(recent_history)},
                }
        except HTTPException as exc:
            csv_error = exc

    if not recent_history:
        try:
            bundle = service.tool_router.get_price_context_for_window(
                ticker,
                range_="1y",
                interval=timeframe,
                max_history_rows=260,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if not isinstance(bundle, dict):
            raise HTTPException(
                status_code=502, detail=f"Chart data unavailable for {ticker}"
            )

        price = bundle.get("price") if isinstance(bundle.get("price"), dict) else {}
        recent_history = (
            price.get("recent_history")
            if isinstance(price.get("recent_history"), list)
            else []
        )
        if not recent_history:
            if csv_error is not None:
                raise csv_error
            raise HTTPException(
                status_code=404, detail=f"No OHLC data available for {ticker}"
            )
        price_state = (
            bundle.get("price_state")
            if isinstance(bundle.get("price_state"), dict)
            else {}
        )

    html = build_candlestick_dashboard_html(
        {
            "ticker": ticker,
            "window": "1y",
            "price_state": price_state,
            "recent_history": recent_history,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    service.artifact_store.write_text(
        f"reports/cockpit/{ticker}_{ts}_candlestick_dashboard.html",
        html,
    )
    return CockpitActionExecuteResponse(
        ok=True,
        action_id=action_id,
        result=f"Candlestick chart rendered for {ticker} ({timeframe}).",
        exit_code=0,
        chart={
            "title": f"{ticker} candlestick chart",
            "html": html,
        },
    )


class CockpitActionPreviewRequest(BaseModel):
    action_id: str
    args: dict[str, Any] = Field(default_factory=dict)


class CockpitActionPreviewResponse(BaseModel):
    action_id: str
    command: list[str]
    summary: str
    estimated_impact: str
    timeout_seconds: int
    guard_message: str | None = None


@router.post("/action/preview", response_model=CockpitActionPreviewResponse)
async def cockpit_preview_action(payload: CockpitActionPreviewRequest):
    """Preview an action: show the command that would run, impact, and guard warnings."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for action preview")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    action_id = str(payload.action_id or "").strip()
    if not action_id:
        raise HTTPException(status_code=400, detail="action_id is required")

    args = payload.args if isinstance(payload.args, dict) else {}

    try:
        preview = service.action_registry.preview(action_id, args)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Unknown action_id: {action_id}"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CockpitActionPreviewResponse(
        action_id=preview.action_id,
        command=preview.command,
        summary=preview.summary,
        estimated_impact=preview.estimated_impact,
        timeout_seconds=preview.timeout_seconds,
        guard_message=preview.guard_message,
    )


def _normalize_action_command(command: list[str], repo_root: Path) -> list[str]:
    """Best-effort command normalization for container/runtime differences."""
    if not command:
        return command

    normalized = list(command)

    # Python launcher normalization: ActionRegistry may include /.venv/bin/python which
    # does not exist in some backend container setups.
    python_bin = Path(normalized[0])
    if not python_bin.exists():
        normalized[0] = sys.executable

    # Script path fallback: resolve against known mount points.
    if len(normalized) > 1:
        raw_script = normalized[1]
        script_path = Path(raw_script)
        if not script_path.is_absolute():
            candidates: list[Path] = [
                (repo_root / script_path).resolve(),
                (Path("/app") / script_path).resolve(),
                (Path("/scripts") / script_path.name).resolve(),
            ]
            if raw_script.startswith("../scripts/"):
                candidates.append(
                    (Path("/scripts") / raw_script.split("/")[-1]).resolve()
                )

            for candidate in candidates:
                if candidate.exists():
                    normalized[1] = str(candidate)
                    break

    return normalized


def _build_action_env(repo_root: Path) -> dict[str, str]:
    """Ensure action subprocesses can import backend/cockpit modules."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    candidates = [
        str((repo_root / "backend").resolve()),
        str((repo_root / "cockpit").resolve()),
        "/app",
        "/app/cockpit",
    ]
    merged = [p for p in candidates if p]
    if existing:
        merged.append(existing)
    env["PYTHONPATH"] = ":".join(merged)
    return env


@router.post("/action/execute", response_model=CockpitActionExecuteResponse)
async def cockpit_execute_action(payload: CockpitActionExecuteRequest):
    """Execute a confirmed cockpit action command and return output."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for action execution")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    action_id = str(payload.action_id or "").strip()
    if not action_id:
        raise HTTPException(status_code=400, detail="action_id is required")

    args = payload.args if isinstance(payload.args, dict) else {}

    try:
        preview = service.action_registry.preview(action_id, args)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Unknown action_id: {action_id}"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if action_id == "show_candlestick":
        return _build_candlestick_chart_response(service, action_id, args)

    timeout_seconds = max(1, int(preview.timeout_seconds or 300))
    normalized_command = _normalize_action_command(
        preview.command, Path(service.repo_root)
    )
    action_env = _build_action_env(Path(service.repo_root))

    def _run_action() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            normalized_command,
            cwd=str(service.repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=action_env,
        )

    try:
        proc = await asyncio.to_thread(_run_action)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Action timed out after {timeout_seconds}s: {action_id}",
        ) from exc
    except Exception as exc:
        logger.exception("Action execution failed: %s", action_id)
        raise HTTPException(
            status_code=500,
            detail=f"Action execution failed: {str(exc)}",
        ) from exc

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if proc.returncode != 0:
        detail = stderr or stdout or f"Action failed with exit code {proc.returncode}"
        raise HTTPException(status_code=500, detail=detail[:4000])

    output = stdout or stderr or f"Action {action_id} completed successfully"
    return CockpitActionExecuteResponse(
        ok=True,
        action_id=action_id,
        result=output[:12000],
        exit_code=proc.returncode,
    )


@router.post("/chat")
async def cockpit_chat(payload: CockpitChatRequest, request: Request):
    """
    Unified cockpit chat endpoint supporting SSE streaming.
    Matches the TUI's ChatController logic but exposed for the Web UI.
    """
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    if not payload.stream:
        # Blocking implementation if requested (rare for this UI)
        try:
            response = service.chat_stream(
                message=payload.message,
                ticker=payload.ticker,
                session_id=payload.session_id,
                enable_web=payload.web_search,
                model=payload.model,
                rag=payload.rag,
                db_diagnostics=payload.db_diagnostics,
            )
            return {
                "type": "done",
                "data": {
                    "text": response.text,
                    "model": response.routing_metadata.get("model")
                    if response.routing_metadata
                    else "local",
                    "latency_ms": response.routing_metadata.get("latency_ms")
                    if response.routing_metadata
                    else 0,
                    "cost_usd": response.routing_metadata.get("cost_usd")
                    if response.routing_metadata
                    else 0,
                    "action_preview": response.action_preview,
                },
            }
        except Exception as exc:
            logger.exception("Cockpit chat non-streaming error")
            raise HTTPException(
                status_code=500, detail=f"Chat processing failed: {str(exc)}"
            ) from exc

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_chunk(chunk: str):
            # This runs in the LLM thread (from ChatController)
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "chunk", "data": {"text": chunk}}
            )

        def on_status(stage: str):
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "status", "data": {"stage": stage}}
            )

        async def run_chat():
            try:
                await queue.put(
                    {"type": "status", "data": {"stage": "Resolving request context"}}
                )
                # ChatController.build_chat_response is synchronous and blocking.
                # We run it in a thread to keep the event loop free.
                response = await asyncio.to_thread(
                    service.chat_stream,
                    message=payload.message,
                    ticker=payload.ticker,
                    session_id=payload.session_id,
                    on_chunk=on_chunk,
                    on_status=on_status,
                    enable_web=payload.web_search,
                    model=payload.model,
                    rag=payload.rag,
                    db_diagnostics=payload.db_diagnostics,
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
                                sources.append(
                                    {
                                        "title": hit.get("title")
                                        or hit.get("file")
                                        or "Source",
                                        "score": hit.get("score")
                                        or hit.get("final_score")
                                        or 0.0,
                                    }
                                )
                    if sources:
                        await queue.put({"type": "sources", "data": {"items": sources}})

                if response.action_preview:
                    await queue.put(
                        {"type": "action_preview", "data": response.action_preview}
                    )

                # Final 'done' event with metrics
                meta = response.routing_metadata or {}
                await queue.put(
                    {
                        "type": "done",
                        "data": {
                            "text": response.text,
                            "model": meta.get("model", "local"),
                            "latency_ms": meta.get("latency_ms", 0),
                            "cost_usd": meta.get("cost_usd", 0),
                            "source": meta.get("source", "local"),
                        },
                    }
                )
            except asyncio.CancelledError:
                logger.info("Cockpit chat stream cancelled by client disconnect")
            except Exception as exc:
                logger.exception("Cockpit chat streaming error")
                await queue.put({"type": "error", "data": str(exc)})
            finally:
                # Signal end of stream
                await queue.put(None)

        # Emit an immediate status so UI leaves "Preparing request" quickly.
        yield f"data: {json.dumps({'type': 'status', 'data': {'stage': 'Request accepted'}})}\n\n"

        # Start the chat worker
        worker_task = asyncio.create_task(run_chat())

        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                worker_task.cancel()
                break

            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            yield f"data: {json.dumps(item)}\n\n"

        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
