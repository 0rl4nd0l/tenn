from __future__ import annotations

import asyncio
import csv
import json
import logging
import math
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import IO, Any, AsyncGenerator, Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import PROJECT_ROOT, settings
from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.cockpit_service import CockpitService
from app.services.llamacpp_runtime import (
    is_manual_fallback_llm_model,
    resolve_llm_runtime_config,
)
from app.services.marketplace_browser_profile import check_marketplace_browser_health
from app.services.marketplace_mission_service import (
    MarketplaceMissionError,
    MarketplaceMissionNotFound,
    MarketplaceMissionService,
)
from app.services.marketplace_scanner import MarketplaceScanCancelled, MarketplaceScanner
from app.services.router_state import get_extraction_activity_snapshot
from cockpit.core.config import (
    compute_effective_cockpit_config,
    effective_anthropic_api_key,
    load_env,
)
from cockpit.core.conversation_commands import derive_conversational_command
from cockpit.integrations.qual_context_bootstrap import context_enabled

router = APIRouter()
logger = logging.getLogger(__name__)
_MARKETPLACE_SCHEDULER_LOCK = threading.Lock()
_MARKETPLACE_SCHEDULER_STARTED = False
_MARKETPLACE_SCHEDULER_INTERVAL_SECONDS = 60

# How long the SSE chat stream may remain silent before emitting a keepalive
# comment. Module-level so tests can monkey-patch it to a smaller value.
SSE_KEEPALIVE_INTERVAL_SECONDS = 10.0


@dataclass
class QueuedActionJobRuntime:
    job_id: str
    action_id: str
    started_at: str
    stop_event: threading.Event = field(default_factory=threading.Event)
    process: subprocess.Popen[str] | None = None
    terminal_status: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_process(self, proc: subprocess.Popen[str] | None) -> None:
        with self._lock:
            self.process = proc

    def get_process(self) -> subprocess.Popen[str] | None:
        with self._lock:
            return self.process

    def record_terminal(self, status: str) -> bool:
        with self._lock:
            if self.terminal_status is not None:
                return False
            self.terminal_status = status
            return True


_queued_action_jobs: dict[str, QueuedActionJobRuntime] = {}
_queued_action_jobs_lock = threading.Lock()


def _register_queued_action_job(runtime: QueuedActionJobRuntime) -> None:
    with _queued_action_jobs_lock:
        _queued_action_jobs[runtime.job_id] = runtime


def _get_queued_action_job(job_id: str) -> QueuedActionJobRuntime | None:
    with _queued_action_jobs_lock:
        return _queued_action_jobs.get(job_id)


def _forget_queued_action_job(job_id: str) -> None:
    with _queued_action_jobs_lock:
        _queued_action_jobs.pop(job_id, None)


def _get_backend_job_tracker() -> Any | None:
    try:
        from app.services.job_tracker import get_tracker

        return get_tracker()
    except Exception as exc:
        logger.debug("Backend job tracker unavailable: %s", exc)
        return None


def _best_effort_tracker_call(method: str, *args: Any, **kwargs: Any) -> None:
    tracker = _get_backend_job_tracker()
    if tracker is None:
        return
    try:
        getattr(tracker, method)(*args, **kwargs)
    except Exception as exc:
        logger.debug("Backend tracker %s failed for %s: %s", method, kwargs.get("job_id"), exc)


def _action_job_ticker(args: dict[str, Any]) -> str | None:
    raw = str(args.get("ticker") or args.get("tickers") or "").strip()
    if not raw:
        return None
    return raw.split(",")[0].strip().upper() or None


def _persist_action_job_row(
    service: CockpitService,
    *,
    job_id: str,
    action_id: str,
    args: dict[str, Any],
    started_at: str,
    status: str,
    stdout_path: Path,
    stderr_path: Path,
    exit_code: int | None = None,
    ended_at: str | None = None,
    progress_stage: str | None = None,
    progress_pct: float | None = None,
) -> None:
    existing = service.state_store.get_job(job_id)
    if existing is not None:
        if progress_stage is None:
            progress_stage = existing.get("progress_stage")
        if progress_pct is None:
            progress_pct = existing.get("progress_pct")
    service.state_store.add_job(
        {
            "job_id": job_id,
            "action_id": action_id,
            "args": args,
            "started_at": started_at,
            "ended_at": ended_at,
            "status": status,
            "exit_code": exit_code,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "artifacts": [],
            "progress_stage": progress_stage,
            "progress_pct": progress_pct,
        }
    )

_ACTION_JOB_PROCS: dict[str, subprocess.Popen[str]] = {}
_ACTION_JOB_PROC_LOCK = threading.Lock()
_ACTION_JOB_CANCEL_REQUESTS: set[str] = set()


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
    class ExtractionActivityRun(BaseModel):
        token: str
        run_id: str | None = None
        document_id: str | None = None
        requested_method: str | None = None
        strict_method: bool | None = None
        ticker: str | None = None
        title: str | None = None
        expires_at: float | None = None
        expires_in_seconds: int | None = None

    llm_model: str | None = None
    llm_endpoint: str | None = None
    anthropic_key_configured: bool = False
    extraction_active: bool = False
    extraction_activity_source: str | None = None
    extraction_activity_expires_in_seconds: int | None = None
    extraction_active_runs: list[ExtractionActivityRun] = Field(default_factory=list)
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
    manual_fallback: bool = False


class ModelGroup(BaseModel):
    location: str
    label: str
    models: list[ModelInfo] = Field(default_factory=list)


def _pick_preferred_loaded_model_id(server_models: dict[str, dict[str, Any]]) -> str | None:
    """Prefer native stack models over manual-fallback IDs (e.g. gpt-oss) when several are loaded."""
    loaded = sorted(
        mid
        for mid, inf in server_models.items()
        if str(inf.get("status") or "") == "loaded"
    )
    if not loaded:
        return None
    primary = [m for m in loaded if not is_manual_fallback_llm_model(m)]
    return primary[0] if primary else loaded[0]


def _hoist_manual_fallback_model_groups(groups: list[ModelGroup]) -> list[ModelGroup]:
    """Move opt-in / fallback models into a dedicated trailing group for the settings UI."""
    bucket: list[ModelInfo] = []
    out: list[ModelGroup] = []
    for g in groups:
        kept: list[ModelInfo] = []
        for m in g.models:
            is_fb = is_manual_fallback_llm_model(f"{m.id} {m.filename}")
            entry = ModelInfo(
                id=m.id,
                filename=m.filename,
                size_gb=m.size_gb,
                quantization=m.quantization,
                available=m.available,
                manual_fallback=is_fb,
            )
            if is_fb:
                bucket.append(entry)
            else:
                kept.append(entry)
        if kept:
            out.append(ModelGroup(location=g.location, label=g.label, models=kept))
    if bucket:
        out.append(
            ModelGroup(
                location="manual_fallback",
                label="Manual fallback (opt-in)",
                models=bucket,
            )
        )
    return out


class AvailableModelsResponse(BaseModel):
    groups: list[ModelGroup] = Field(default_factory=list)
    active_model: str | None = None


class ModelLoadRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_id: str | None = None


class ModelLoadResponse(BaseModel):
    ok: bool
    requested_model: str
    resolved_model: str | None = None
    runtime_url: str | None = None
    already_loaded: bool = False
    message: str


class QueueStatusResponse(BaseModel):
    pending: int = 0
    active: int = 0
    completed: int = 0
    failed: int = 0


class CockpitHoldingRecord(BaseModel):
    holding_id: str
    ticker: str
    account_label: str | None = None
    thesis_bucket: str | None = None
    status: str | None = None
    quantity: float | None = None
    avg_cost: float | None = None
    cost_currency: str | None = None
    opened_at: str | None = None
    updated_at: str | None = None
    note: str | None = None


class CockpitHoldingListResponse(BaseModel):
    items: list[CockpitHoldingRecord] = Field(default_factory=list)


class CockpitHoldingCreateRequest(BaseModel):
    ticker: str
    account_label: str | None = None
    thesis_bucket: str | None = None
    quantity: float | None = None
    avg_cost: float | None = None
    cost_currency: str | None = None
    opened_at: str | None = None
    note: str | None = None


class CockpitHoldingUpdateRequest(BaseModel):
    ticker: str | None = None
    account_label: str | None = None
    thesis_bucket: str | None = None
    status: str | None = None
    quantity: float | None = None
    avg_cost: float | None = None
    cost_currency: str | None = None
    opened_at: str | None = None
    note: str | None = None


class CockpitHoldingMutationResponse(BaseModel):
    ok: bool
    holding_id: str


def _effective_cockpit_feature_flags(
    effective_cfg: dict[str, Any],
) -> dict[str, bool]:
    web_cfg = effective_cfg.get("web") if isinstance(effective_cfg.get("web"), dict) else {}
    rag_cfg = effective_cfg.get("rag") if isinstance(effective_cfg.get("rag"), dict) else {}
    db_cfg = effective_cfg.get("db") if isinstance(effective_cfg.get("db"), dict) else {}
    qual_cfg = (
        rag_cfg.get("qualitative_context")
        if isinstance(rag_cfg.get("qualitative_context"), dict)
        else {}
    )
    news_cfg = (
        rag_cfg.get("news_context")
        if isinstance(rag_cfg.get("news_context"), dict)
        else {}
    )

    rag_setting = rag_cfg.get("enabled")
    rag_config_enabled = (
        bool(rag_setting)
        if rag_setting is not None
        else bool(settings.enable_embeddings and settings.enable_qdrant)
    )
    rag_path_enabled = bool(rag_cfg.get("backend_search_enabled", False)) or context_enabled(
        qual_cfg, default=False
    ) or context_enabled(news_cfg, default=False)

    return {
        "web_search": bool(web_cfg.get("enabled_default", False)),
        "rag": rag_config_enabled and (
            rag_path_enabled or bool(settings.enable_embeddings and settings.enable_qdrant)
        ),
        "extraction": bool(settings.enable_extraction),
        "session_memory": bool(getattr(settings, "enable_session_memory", True)),
        "db_diagnostics": bool(db_cfg.get("diagnostic_query_enabled", False)),
    }


class IntelPulseStats(BaseModel):
    document_count: int = 0
    extraction_count: int = 0
    signal_count: int = 0
    memory_count: int = 0
    population_index: float = 0.0
    trust_score_avg: float = 0.0
    quarantine_rate: float = 0.0


class IntelPulseStageHealth(BaseModel):
    id: str
    label: str
    health: float
    status: str


class IntelPulseFailure(BaseModel):
    id: str
    entity: str
    type: str
    message: str
    confidence: float
    timestamp: str


class IntelPulseResponse(BaseModel):
    stats: IntelPulseStats
    pipeline: list[IntelPulseStageHealth]
    failures: list[IntelPulseFailure] | None = None


class IntelPulseEntityMetric(BaseModel):
    entity: str
    metrics: dict[
        str, str
    ]  # metric_name -> status (populated, abstain, failed, sparse)


class IntelPulseMatrixResponse(BaseModel):
    stage: str
    entities: list[IntelPulseEntityMetric]


# ---------------------------------------------------------------------------
# Helper: normalize chat sources for cockpit UI
# ---------------------------------------------------------------------------


def _safe_source_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if math.isfinite(numeric) else 0.0


def _clean_source_text(value: Any, *, max_chars: int = 280) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _summarize_scalar_fields(raw: dict[str, Any], *, max_items: int = 4) -> str | None:
    bits: list[str] = []
    for key, value in raw.items():
        if isinstance(value, (dict, list, tuple, set)) or value is None:
            continue
        label = str(key).strip().replace("_", " ")
        text = str(value).strip()
        if not label or not text:
            continue
        bits.append(f"{label}: {text}")
        if len(bits) >= max_items:
            break
    if not bits:
        return None
    return _clean_source_text("; ".join(bits))


def _normalize_source_item(
    raw: dict[str, Any],
    *,
    default_title: str = "Source",
    kind: str = "context",
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    title = str(
        raw.get("title")
        or raw.get("source_name")
        or raw.get("source")
        or raw.get("file")
        or raw.get("document_id")
        or default_title
    ).strip()
    url = str(raw.get("url") or raw.get("source_url") or "").strip()
    document_id = str(raw.get("document_id") or raw.get("source_document_id") or "").strip()
    source_id = str(raw.get("source_id") or raw.get("chunk_id") or "").strip()
    path = str(raw.get("path") or raw.get("pdf_path") or raw.get("file") or "").strip()
    doc_type = str(
        raw.get("doc_type")
        or raw.get("doc_class")
        or raw.get("source_corpus")
        or raw.get("corpus")
        or ""
    ).strip()
    published_at = str(raw.get("published_at") or "").strip()
    snippet = _clean_source_text(
        raw.get("snippet")
        or raw.get("text")
        or raw.get("excerpt")
        or raw.get("content")
        or raw.get("claim")
    )

    if not title and not url and not snippet and not document_id and not path:
        return None

    return {
        "title": title or default_title,
        "score": _safe_source_score(
            raw.get("score") or raw.get("final_score") or raw.get("semantic_score")
        ),
        "url": url or None,
        "snippet": snippet,
        "published_at": published_at or None,
        "document_id": document_id or None,
        "source_id": source_id or None,
        "doc_type": doc_type or None,
        "path": path or None,
        "kind": kind,
    }


def _append_source_item(
    items: list[dict[str, Any]],
    seen: set[str],
    raw: dict[str, Any],
    *,
    default_title: str = "Source",
    kind: str = "context",
    limit: int = 10,
) -> None:
    if len(items) >= limit:
        return

    item = _normalize_source_item(raw, default_title=default_title, kind=kind)
    if item is None:
        return

    dedupe_key = next(
        (
            str(candidate).strip().lower()
            for candidate in (
                item.get("url"),
                item.get("source_id"),
                item.get("document_id"),
                item.get("title"),
            )
            if str(candidate or "").strip()
        ),
        "",
    )
    if not dedupe_key or dedupe_key in seen:
        return

    seen.add(dedupe_key)
    items.append(item)


def _decode_truncated_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    """Best-effort decode for historical truncated tool payload envelopes.

    Older tool truncation stored a JSON string under ``data`` which made source
    extraction impossible. Newer truncation keeps structured fields, so this is
    primarily a backward-compatible decoder.
    """
    if not isinstance(result, dict):
        return {}
    if not result.get("_truncated"):
        return result
    data = result.get("data")
    if not isinstance(data, str):
        return result

    parsed: dict[str, Any] | None = None
    try:
        raw = json.loads(data)
        if isinstance(raw, dict):
            parsed = raw
    except (TypeError, ValueError, json.JSONDecodeError):
        # Try parsing up to the last complete object brace.
        last_brace = data.rfind("}")
        if last_brace > 1:
            candidate = data[: last_brace + 1]
            try:
                raw = json.loads(candidate)
                if isinstance(raw, dict):
                    parsed = raw
            except (TypeError, ValueError, json.JSONDecodeError):
                parsed = None

    if parsed is None:
        return result

    merged = dict(parsed)
    for key, value in result.items():
        if key in {"data"}:
            continue
        if key not in merged or merged.get(key) in (None, "", [], {}):
            merged[key] = value
    return merged


def _build_ui_sources(evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for ev in evidence or []:
        if not isinstance(ev, dict):
            continue
        ev_type = str(ev.get("type") or "").strip().lower()
        details_payload = ev.get("details")
        details = details_payload if isinstance(details_payload, dict) else {}

        if ev_type == "local_context":
            qual_context = (
                details.get("qual_context") if isinstance(details.get("qual_context"), dict) else {}
            )
            for hit in qual_context.get("hits", []) if isinstance(qual_context.get("hits"), list) else []:
                if isinstance(hit, dict):
                    _append_source_item(
                        items,
                        seen,
                        hit,
                        default_title="Context source",
                        kind="rag",
                    )

            for row in details.get("docs", []) if isinstance(details.get("docs"), list) else []:
                if isinstance(row, dict):
                    _append_source_item(
                        items,
                        seen,
                        row,
                        default_title="Document",
                        kind="document",
                    )

            for row in details.get("doc_snippets", []) if isinstance(details.get("doc_snippets"), list) else []:
                if isinstance(row, dict):
                    _append_source_item(
                        items,
                        seen,
                        row,
                        default_title="Document excerpt",
                        kind="document",
                    )

            for row in details.get("web_facts", []) if isinstance(details.get("web_facts"), list) else []:
                if isinstance(row, dict):
                    _append_source_item(
                        items,
                        seen,
                        row,
                        default_title="Web fact",
                        kind="web",
                    )

        elif ev_type == "company_dump":
            backend = details.get("backend") if isinstance(details.get("backend"), dict) else {}
            for row in backend.get("docs", []) if isinstance(backend.get("docs"), list) else []:
                if isinstance(row, dict):
                    _append_source_item(
                        items,
                        seen,
                        row,
                        default_title="Company document",
                        kind="document",
                    )

            for row in backend.get("announcement_context", []) if isinstance(backend.get("announcement_context"), list) else []:
                if isinstance(row, dict):
                    _append_source_item(
                        items,
                        seen,
                        row,
                        default_title="Announcement excerpt",
                        kind="document",
                    )

        elif ev_type == "news_search":
            for row in details.get("hits", []) if isinstance(details.get("hits"), list) else []:
                if isinstance(row, dict):
                    _append_source_item(
                        items,
                        seen,
                        row,
                        default_title="News source",
                        kind="news",
                    )

        elif ev_type in {"news_summary", "article_request"}:
            _append_source_item(
                items,
                seen,
                details,
                default_title="News source",
                kind="news",
            )

        elif ev_type == "web":
            pages = details.get("pages") if isinstance(details.get("pages"), list) else []
            facts = details.get("facts") if isinstance(details.get("facts"), list) else []
            if pages:
                for row in pages:
                    if isinstance(row, dict):
                        _append_source_item(
                            items,
                            seen,
                            row,
                            default_title="Web source",
                            kind="web",
                        )
            elif facts:
                for row in facts:
                    if isinstance(row, dict):
                        _append_source_item(
                            items,
                            seen,
                            row,
                            default_title="Web source",
                            kind="web",
                        )
            else:
                _append_source_item(
                    items,
                    seen,
                    details,
                    default_title="Web source",
                    kind="web",
                )

        elif ev_type == "runtime_clock":
            _append_source_item(
                items,
                seen,
                details,
                default_title="Cockpit runtime clock",
                kind="context",
            )

        elif ev_type == "holdings":
            rows = (
                details_payload
                if isinstance(details_payload, list)
                else (
                    details.get("items")
                    if isinstance(details.get("items"), list)
                    else []
                )
            )
            for row in rows:
                if not isinstance(row, dict):
                    continue
                ticker = str(row.get("ticker") or "").strip().upper()
                account = str(row.get("account_label") or "").strip()
                qty = row.get("quantity")
                avg_cost = row.get("avg_cost")
                bits: list[str] = []
                if account:
                    bits.append(f"Account: {account}")
                if qty is not None:
                    bits.append(f"Quantity: {qty}")
                if avg_cost is not None:
                    bits.append(f"Avg cost: {avg_cost}")
                _append_source_item(
                    items,
                    seen,
                    {
                        **row,
                        "title": f"{ticker or 'Holding'} holding",
                        "source_id": (
                            row.get("holding_id")
                            or (f"holding:{ticker}" if ticker else None)
                        ),
                        "snippet": "; ".join(bits) if bits else None,
                    },
                    default_title="Holding",
                    kind="context",
                )

        elif ev_type == "watchlist":
            rows = (
                details_payload
                if isinstance(details_payload, list)
                else (
                    details.get("items")
                    if isinstance(details.get("items"), list)
                    else []
                )
            )
            for row in rows:
                ticker = ""
                added_at = None
                if isinstance(row, dict):
                    ticker = str(row.get("ticker") or "").strip().upper()
                    added_at = row.get("added_at")
                elif isinstance(row, str):
                    ticker = row.strip().upper()
                if not ticker:
                    continue
                added_text = str(added_at or "").strip()
                _append_source_item(
                    items,
                    seen,
                    {
                        "title": f"{ticker} watchlist",
                        "source_id": f"watchlist:{ticker}",
                        "snippet": (
                            f"Added: {added_text[:10]}" if added_text else "Tracked in watchlist."
                        ),
                    },
                    default_title="Watchlist item",
                    kind="context",
                )

        elif ev.get("tool") and not ev.get("type"):
            # Agent loop evidence format: {tool, arguments, result}
            # Handle search_news and gather_local_context tool results.
            tool_name = str(ev.get("tool") or "")
            result = ev.get("result") or {}
            if isinstance(result, dict):
                result = _decode_truncated_tool_result(result)
                if tool_name == "search_news":
                    for hit in result.get("hits") or []:
                        if isinstance(hit, dict):
                            _append_source_item(
                                items,
                                seen,
                                hit,
                                default_title="News article",
                                kind="news",
                            )
                elif tool_name == "search_announcements":
                    for row in result.get("documents") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                row,
                                default_title="Announcement document",
                                kind="document",
                            )
                    for row in result.get("context") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                row,
                                default_title="Announcement excerpt",
                                kind="document",
                            )
                elif tool_name in ("gather_local_context", "query_ticker_data"):
                    for hit in result.get("hits") or result.get("rag_hits") or []:
                        if isinstance(hit, dict):
                            _append_source_item(
                                items,
                                seen,
                                hit,
                                default_title="Context source",
                                kind="rag",
                            )
                    for row in result.get("docs") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                row,
                                default_title="Document",
                                kind="document",
                            )
                elif tool_name == "get_financials":
                    for row in result.get("financials") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                {
                                    **row,
                                    "title": (
                                        f"{row.get('ticker') or 'Financials'} "
                                        f"{row.get('period_type') or ''} "
                                        f"{row.get('period_end') or ''}"
                                    ).strip(),
                                    "document_id": row.get("source_document_id"),
                                    "published_at": row.get("period_end"),
                                    "doc_type": row.get("period_type"),
                                    "snippet": result.get("narrative") or None,
                                },
                                default_title="Financial period",
                                kind="document",
                            )
                elif tool_name == "recall_dossier":
                    for row in result.get("findings") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                {
                                    **row,
                                    "title": (
                                        str(row.get("source") or "").strip()
                                        or str(row.get("category") or "").strip()
                                        or "Dossier finding"
                                    ),
                                    "url": row.get("source_url"),
                                    "snippet": row.get("finding_with_age") or row.get("finding"),
                                    "published_at": row.get("ts"),
                                    "score": row.get("confidence"),
                                },
                                default_title="Dossier finding",
                                kind="context",
                            )
                elif tool_name == "deep_research":
                    research = result.get("research")
                    if isinstance(research, dict):
                        _append_source_item(
                            items,
                            seen,
                            {
                                "title": "Deep research brief",
                                "source_id": f"deep_research:{result.get('ticker') or ''}",
                                "snippet": research.get("summary"),
                                "score": research.get("confidence"),
                            },
                            default_title="Deep research brief",
                            kind="context",
                        )
                elif tool_name == "search_web":
                    for row in result.get("results") or result.get("pages") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                row,
                                default_title="Web result",
                                kind="web",
                            )
                elif tool_name == "fetch_url":
                    _append_source_item(
                        items,
                        seen,
                        result,
                        default_title="Fetched page",
                        kind="web",
                    )
                elif tool_name == "get_data_quality":
                    for row in result.get("recent_failures") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                row,
                                default_title="Extraction failure",
                                kind="document",
                            )
                    for row in result.get("recent_low_conf_rows") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                {
                                    **row,
                                    "title": (
                                        f"{row.get('ticker') or 'Low-confidence'} "
                                        f"{row.get('period_type') or ''} "
                                        f"{row.get('period_end') or ''}"
                                    ).strip(),
                                    "document_id": row.get("source_document_id"),
                                    "published_at": row.get("period_end"),
                                    "score": row.get("confidence_metrics"),
                                    "snippet": (
                                        f"Confidence {row.get('confidence_metrics')}"
                                        if row.get("confidence_metrics") is not None
                                        else None
                                    ),
                                },
                                default_title="Low-confidence financial",
                                kind="context",
                            )
                elif tool_name == "run_analysis":
                    for row in result.get("modules") or []:
                        if not isinstance(row, dict):
                            continue
                        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
                        metric_bits = [
                            f"{key}: {value}"
                            for key, value in metrics.items()
                            if value not in (None, "")
                        ]
                        snippet = str(row.get("narrative") or "").strip()
                        if not snippet and metric_bits:
                            snippet = ", ".join(metric_bits)
                        _append_source_item(
                            items,
                            seen,
                            {
                                "title": f"{row.get('module') or 'Analysis'} analysis",
                                "source_id": (
                                    f"analysis:{result.get('ticker') or ''}:{row.get('module') or ''}"
                                ),
                                "snippet": snippet or None,
                                "score": 1.0 if row.get("status") == "complete" else 0.0,
                            },
                            default_title="Analysis result",
                            kind="context",
                        )
                elif tool_name == "get_price":
                    price = result.get("price") if isinstance(result.get("price"), dict) else {}
                    current = price.get("current") if isinstance(price.get("current"), dict) else {}
                    _append_source_item(
                        items,
                        seen,
                        {
                            "title": f"{result.get('ticker') or 'Ticker'} price data",
                            "source_id": (
                                f"price:{result.get('ticker') or ''}:{price.get('range') or ''}:{price.get('interval') or ''}"
                            ),
                            "snippet": (
                                f"Provider: {price.get('provider') or 'unknown'}. "
                                f"Market time: {current.get('market_time') or 'unknown'}."
                            ),
                        },
                        default_title="Price data",
                        kind="context",
                    )
                elif tool_name == "get_price_on_date":
                    _append_source_item(
                        items,
                        seen,
                        {
                            "title": (
                                f"{result.get('ticker') or 'Ticker'} price on "
                                f"{result.get('date') or 'requested date'}"
                            ),
                            "source_id": (
                                f"price_on_date:{result.get('ticker') or ''}:{result.get('date') or ''}"
                            ),
                            "snippet": (
                                f"Open {result.get('open')}, high {result.get('high')}, "
                                f"low {result.get('low')}, close {result.get('close')}."
                            ),
                        },
                        default_title="Historical price",
                        kind="context",
                    )
                elif tool_name == "get_price_range":
                    _append_source_item(
                        items,
                        seen,
                        {
                            "title": (
                                f"{result.get('ticker') or 'Ticker'} price range "
                                f"{result.get('start_date') or ''} to {result.get('end_date') or ''}"
                            ).strip(),
                            "source_id": (
                                f"price_range:{result.get('ticker') or ''}:{result.get('start_date') or ''}:{result.get('end_date') or ''}"
                            ),
                            "snippet": f"{result.get('data_points') or 0} price observations returned.",
                        },
                        default_title="Price range",
                        kind="context",
                    )
                elif tool_name == "search_social":
                    for row in result.get("stories") or result.get("results") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                row,
                                default_title="Social result",
                                kind="web",
                            )
                elif tool_name == "get_watchlist_alerts":
                    for row in result.get("alerts") or []:
                        if isinstance(row, dict):
                            _append_source_item(
                                items,
                                seen,
                                {
                                    **row,
                                    "title": (
                                        f"{row.get('ticker') or 'Watchlist'} "
                                        f"{row.get('type') or 'alert'}"
                                    ).strip(),
                                    "source_id": row.get("id"),
                                    "snippet": row.get("message"),
                                    "published_at": row.get("ts"),
                                },
                                default_title="Watchlist alert",
                                kind="context",
                            )
                elif tool_name == "tv_screener":
                    market = str(result.get("market") or "").strip().upper()
                    for index, row in enumerate(result.get("results") or []):
                        if not isinstance(row, dict):
                            continue
                        symbol = str(
                            row.get("symbol")
                            or row.get("ticker")
                            or row.get("code")
                            or row.get("name")
                            or ""
                        ).strip()
                        _append_source_item(
                            items,
                            seen,
                            {
                                **row,
                                "title": (
                                    f"{symbol or 'Market mover'}"
                                    f"{f' ({market})' if market else ''}"
                                ),
                                "source_id": f"tv_screener:{market}:{symbol or index}",
                                "snippet": _summarize_scalar_fields(row, max_items=5),
                            },
                            default_title="TradingView screener",
                            kind="context",
                        )
                elif tool_name == "get_tv_indicators":
                    ticker = str(result.get("ticker") or "").strip().upper()
                    exchange = str(result.get("exchange") or "").strip().upper()
                    indicators = (
                        result.get("indicators")
                        if isinstance(result.get("indicators"), dict)
                        else {}
                    )
                    indicator_bits: list[str] = []
                    for name, value in indicators.items():
                        if isinstance(value, dict):
                            err = str(value.get("error") or "").strip()
                            if err:
                                indicator_bits.append(f"{name}: error ({err})")
                        elif value is not None:
                            indicator_bits.append(f"{name}: {value}")
                        if len(indicator_bits) >= 6:
                            break
                    _append_source_item(
                        items,
                        seen,
                        {
                            "title": f"{exchange + ':' if exchange else ''}{ticker or 'Ticker'} indicators",
                            "source_id": f"tv_indicators:{exchange}:{ticker}",
                            "snippet": _clean_source_text("; ".join(indicator_bits)),
                        },
                        default_title="TradingView indicators",
                        kind="context",
                    )

        if len(items) >= 10:
            break

    return items


_NON_SUBSTANTIVE_CHAT_MESSAGE_RE = re.compile(
    r"^\s*(?:"
    r"/[a-z_][\w-]*.*|"
    r"hi|hello|hey|yo|sup|"
    r"good (?:morning|afternoon|evening)|"
    r"thanks|thank you|"
    r"ok(?:ay)?|yes|no|sure|cool|continue|go on|"
    r"help(?: me)?|"
    r"what can you do\??|"
    r"show sources|show source|sources\??"
    r")\s*$",
    re.IGNORECASE,
)
_EXPLICIT_UNVERIFIED_RESPONSE_RE = re.compile(
    r"\b(?:cannot|can't|can not|do not|don't|won't)\s+"
    r"(?:verify|confirm|substantiate|make factual claims)\b|"
    r"\bnot enough (?:evidence|sources|current evidence|retrieved context|information)\b|"
    r"\bunable to verify\b",
    re.IGNORECASE,
)
_CONTAINS_FINANCIAL_CLAIM_RE = re.compile(
    r"\b[A-Z]{2,5}\b|"                                     # ASX tickers / company abbreviations
    r"\$[\d,]+(?:\.\d+)?[MBKmb]?\b|"                      # dollar amounts
    r"\b\d+(?:\.\d+)?%\b|"                                 # percentages
    r"\b(?:announced|reported|upgraded|downgraded|raised|cut|beat|missed|"
    r"acquired|merged|divested|appointed|resigned|flagged|guided|earnings|"
    r"revenue|profit|loss|EBIT|EBITDA|dividend|buyback|placement)\b",
    re.IGNORECASE,
)
_SOURCE_CONTRACT_REFUSAL = (
    "I can't verify that from current evidence, and I won't make factual claims unless "
    "the supporting sources can be shown in the Sources dropdown. Please narrow the "
    "question or ask me to fetch the relevant news, announcements, financials, or price data first."
)


def _message_requires_visible_sources(message: str) -> bool:
    text = str(message or "").strip()
    if not text:
        return False
    # Natural-language control phrases (e.g. "daily market update") are
    # deterministically rewritten to slash commands inside ChatController.
    # Treat them the same as explicit slash commands so source-contract
    # grounding does not mask command output.
    if derive_conversational_command(text):
        return False
    return _NON_SUBSTANTIVE_CHAT_MESSAGE_RE.fullmatch(text) is None


def _enforce_visible_source_contract(message: str, response: Any) -> list[dict[str, Any]]:
    sources = _build_ui_sources(getattr(response, "evidence", None) or [])
    text = str(getattr(response, "text", "") or "").strip()

    if not text or getattr(response, "action_preview", None) is not None:
        return sources
    if not _message_requires_visible_sources(message):
        return sources
    if sources:
        return sources
    # Only allow the "explicit unverified" bypass when the response is a PURE
    # statement of inability — no named tickers, monetary figures, events, or
    # company-specific claims. A hedged hallucination ("the evidence is
    # incomplete, but BHP reported...") must still be blocked.
    if _EXPLICIT_UNVERIFIED_RESPONSE_RE.search(text) and not _CONTAINS_FINANCIAL_CLAIM_RE.search(text):
        return sources

    meta = dict(getattr(response, "routing_metadata", None) or {})
    meta["grounding_guard"] = "missing_visible_sources"
    # Build a tool audit so the UI can surface "Searched X: 0 results"
    # rather than a completely empty sources panel.
    evidence = getattr(response, "evidence", None) or []
    tool_audit = []
    for ev in evidence:
        if not isinstance(ev, dict):
            continue
        tool = ev.get("tool", "")
        result = ev.get("result", {})
        if not isinstance(result, dict):
            continue
        hit_count = result.get("hit_count") or len(result.get("hits", [])) or len(result.get("results", []))
        audit_entry: dict[str, Any] = {"tool": tool, "hit_count": hit_count}
        if result.get("error"):
            audit_entry["error"] = str(result["error"])[:120]
        if tool:
            tool_audit.append(audit_entry)
    if tool_audit:
        meta["tool_audit"] = tool_audit
    response.routing_metadata = meta
    response.text = _SOURCE_CONTRACT_REFUSAL
    return []


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

    load_env(PROJECT_ROOT)

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
    preferred_loaded = _pick_preferred_loaded_model_id(server_models)
    if preferred_loaded:
        llm_model = preferred_loaded

    config_path_value = str(
        os.getenv("COCKPIT_CONFIG") or "config/cockpit.yaml"
    ).strip()
    config_path = Path(config_path_value)
    if not config_path.is_absolute():
        config_path = (PROJECT_ROOT / config_path).resolve()

    effective_cfg = compute_effective_cockpit_config(
        PROJECT_ROOT,
        str(config_path),
        profile=str(os.getenv("COCKPIT_PROFILE") or "default").strip() or "default",
        read_only=False,
        no_web=False,
    )
    cockpit_llm = (
        effective_cfg.get("cockpit_llm")
        if isinstance(effective_cfg.get("cockpit_llm"), dict)
        else {}
    )
    backend_cfg = (
        effective_cfg.get("backend")
        if isinstance(effective_cfg.get("backend"), dict)
        else {}
    )
    runtime_cfg = (
        effective_cfg.get("runtime")
        if isinstance(effective_cfg.get("runtime"), dict)
        else {}
    )
    anthropic_key_configured = bool(effective_anthropic_api_key(cockpit_llm))
    extraction_activity = get_extraction_activity_snapshot()

    return CockpitConfigResponse(
        llm_model=llm_model,
        llm_endpoint=llm_endpoint,
        anthropic_key_configured=anthropic_key_configured,
        extraction_active=bool(extraction_activity.get("active")),
        extraction_activity_source=str(extraction_activity.get("source") or "none"),
        extraction_activity_expires_in_seconds=int(
            extraction_activity.get("expires_in_seconds") or 0
        ),
        extraction_active_runs=[
            CockpitConfigResponse.ExtractionActivityRun(
                token=str(run.get("token") or "").strip(),
                run_id=str(run.get("run_id") or "").strip() or None,
                document_id=str(run.get("document_id") or "").strip() or None,
                requested_method=str(run.get("requested_method") or "").strip() or None,
                strict_method=(
                    bool(run.get("strict_method"))
                    if run.get("strict_method") is not None
                    else None
                ),
                ticker=str(run.get("ticker") or "").strip() or None,
                title=str(run.get("title") or "").strip() or None,
                expires_at=(
                    float(run.get("expires_at"))
                    if run.get("expires_at") is not None
                    else None
                ),
                expires_in_seconds=(
                    int(run.get("expires_in_seconds"))
                    if run.get("expires_in_seconds") is not None
                    else None
                ),
            )
            for run in (extraction_activity.get("active_runs") or [])
            if str(run.get("token") or "").strip()
        ],
        extract_model=str(settings.extract_model or "").strip() or None,
        embed_model=str(settings.embed_model or "").strip() or None,
        routing_policy=str(cockpit_llm.get("hybrid_router_policy") or "").strip() or None,
        backend_url=str(backend_cfg.get("api_base_url") or "").strip() or None,
        profile=(
            str(
                cockpit_llm.get("llm_profile_label")
                or runtime_cfg.get("profile")
                or os.environ.get("LOCAL_BACKEND_PROFILE")
                or ""
            ).strip()
            or None
        ),
        features=_effective_cockpit_feature_flags(effective_cfg),
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
    return _fetch_runtime_models()


def _fetch_runtime_models(base_url: str | None = None) -> dict[str, dict[str, Any]]:
    """Query a llama.cpp runtime /v1/models and return {model_id: {status, path_stem}}."""
    llamacpp_url = str(base_url or settings.llamacpp_url or "").strip().rstrip("/")
    if not llamacpp_url:
        return {}
    headers: dict[str, str] = {}
    api_key = (
        str(os.getenv("LLM_API_KEY") or "").strip()
        or str(os.getenv("LLAMA_SERVER_API_KEY") or "").strip()
        or str(os.getenv("LLAMACPP_API_KEY") or "").strip()
    )
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = httpx.get(f"{llamacpp_url}/v1/models", headers=headers, timeout=3.0)
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


def _normalize_model_identifier(value: str | None) -> str:
    return str(value or "").strip().removeprefix("model:").lower()


def _model_alias_tokens(model_id: str, info: dict[str, Any] | None = None) -> set[str]:
    tokens = {_normalize_model_identifier(model_id)}
    if str(model_id).startswith("model:"):
        tokens.add(_normalize_model_identifier(str(model_id).split(":", 1)[1]))
    if info:
        tokens.add(_normalize_model_identifier(str(info.get("path_stem") or "").strip()))
    return {token for token in tokens if token}


def _find_matching_runtime_model(
    runtime_models: dict[str, dict[str, Any]],
    requested_model: str,
) -> str | None:
    requested_tokens = _model_alias_tokens(requested_model)
    if not requested_tokens:
        return None

    preferred_match: str | None = None
    for model_id, info in runtime_models.items():
        matches = any(
            req == token or req.startswith(token) or token.startswith(req)
            for req in requested_tokens
            for token in _model_alias_tokens(model_id, info)
        )
        if not matches:
            continue
        if str(model_id).startswith("model:"):
            return model_id
        if preferred_match is None:
            preferred_match = model_id

    return preferred_match


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
    active_model = _pick_preferred_loaded_model_id(server_models)
    for model_id, info in server_models.items():
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

    server_groups = _build_server_model_groups(server_models) if server_models else []
    if not groups:
        groups = server_groups
    elif server_groups:
        local_by_location = {group.location: group for group in groups}
        server_by_location = {group.location: group for group in server_groups}
        merged_groups: list[ModelGroup] = []
        for loc in _MODEL_LOCATIONS:
            group = local_by_location.get(loc["location"]) or server_by_location.get(
                loc["location"]
            )
            if group is not None:
                merged_groups.append(group)
        groups = merged_groups

    groups = _hoist_manual_fallback_model_groups(groups)

    return AvailableModelsResponse(
        groups=groups,
        active_model=active_model,
    )


@router.post("/models/load", response_model=ModelLoadResponse)
def cockpit_load_model(payload: ModelLoadRequest) -> ModelLoadResponse:
    from cockpit.integrations.llamacpp_manager import load_model_api

    runtime_url, default_model = resolve_llm_runtime_config(model=payload.model_id)
    requested_model = str(payload.model_id or default_model or "").strip()
    if not requested_model:
        raise HTTPException(status_code=400, detail="model_id is required")

    runtime_models = _fetch_runtime_models(runtime_url)
    matched_model = _find_matching_runtime_model(runtime_models, requested_model)
    resolved_model = matched_model or requested_model

    if runtime_models and matched_model is None:
        available_models = sorted(runtime_models.keys())
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Model '{requested_model}' is not available on the configured chat runtime.",
                "requested_model": requested_model,
                "runtime_url": runtime_url,
                "available_models": available_models,
            },
        )

    if any(
        info.get("status") == "loaded"
        and (
            _normalize_model_identifier(resolved_model)
            in _normalize_model_identifier(model_id)
            or _normalize_model_identifier(resolved_model)
            in _normalize_model_identifier(str(info.get("path_stem") or ""))
        )
        for model_id, info in runtime_models.items()
    ):
        return ModelLoadResponse(
            ok=True,
            requested_model=requested_model,
            resolved_model=resolved_model,
            runtime_url=runtime_url,
            already_loaded=True,
            message=f"Model '{resolved_model}' is already loaded.",
        )

    parsed = urlparse(runtime_url)
    host = str(parsed.hostname or "").strip()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        raise HTTPException(
            status_code=500,
            detail=f"Configured extraction runtime URL is invalid: {runtime_url}",
        )

    api_key = (
        str(os.getenv("LLM_API_KEY") or "").strip()
        or str(os.getenv("LLAMA_SERVER_API_KEY") or "").strip()
        or str(os.getenv("LLAMACPP_API_KEY") or "").strip()
        or "local-openai-key"
    )

    status_messages: list[str] = []
    ok = load_model_api(
        host=host,
        port=str(port),
        model_name=resolved_model,
        api_key=api_key,
        timeout=300.0,
        on_status=status_messages.append,
    )
    if not ok:
        detail = status_messages[-1] if status_messages else f"Failed to load model '{resolved_model}'."
        raise HTTPException(
            status_code=400,
            detail={
                "message": detail,
                "requested_model": requested_model,
                "resolved_model": resolved_model,
                "runtime_url": runtime_url,
                "status_messages": status_messages,
            },
        )

    return ModelLoadResponse(
        ok=True,
        requested_model=requested_model,
        resolved_model=resolved_model,
        runtime_url=runtime_url,
        already_loaded=False,
        message=status_messages[-1] if status_messages else f"Model '{resolved_model}' loaded.",
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


@router.get("/holdings", response_model=CockpitHoldingListResponse)
def cockpit_list_holdings(
    ticker: str | None = None,
    include_archived: bool = False,
) -> CockpitHoldingListResponse:
    try:
        service = CockpitService.get_instance()
        rows = service.state_store.list_holdings(
            ticker=ticker,
            include_archived=include_archived,
        )
        return CockpitHoldingListResponse(
            items=[CockpitHoldingRecord(**dict(row)) for row in rows]
        )
    except Exception as exc:
        logger.exception("Failed to list cockpit holdings")
        raise HTTPException(status_code=500, detail=f"Failed to list holdings: {str(exc)}") from exc


@router.post("/holdings", response_model=CockpitHoldingRecord)
def cockpit_add_holding(payload: CockpitHoldingCreateRequest) -> CockpitHoldingRecord:
    ticker = str(payload.ticker or "").strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")

    try:
        service = CockpitService.get_instance()
        state_store = service.state_store
        holding_id = state_store.add_holding(
            ticker=ticker,
            account_label=payload.account_label,
            thesis_bucket=payload.thesis_bucket,
            quantity=payload.quantity,
            avg_cost=payload.avg_cost,
            cost_currency=payload.cost_currency,
            opened_at=payload.opened_at,
            note=payload.note,
        )
        row = state_store.get_holding(holding_id)
    except Exception as exc:
        logger.exception("Failed to add cockpit holding")
        raise HTTPException(status_code=500, detail=f"Failed to add holding: {str(exc)}") from exc

    if row is None:
        raise HTTPException(status_code=500, detail="Holding was created but could not be reloaded")
    return CockpitHoldingRecord(**dict(row))


@router.patch("/holdings/{holding_id}", response_model=CockpitHoldingRecord)
def cockpit_update_holding(
    holding_id: str,
    payload: CockpitHoldingUpdateRequest,
) -> CockpitHoldingRecord:
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields supplied for update")

    if "ticker" in fields:
        ticker_value = str(fields.get("ticker") or "").strip().upper()
        if not ticker_value:
            raise HTTPException(status_code=400, detail="ticker cannot be blank")
        fields["ticker"] = ticker_value

    try:
        service = CockpitService.get_instance()
        state_store = service.state_store
        updated = state_store.update_holding(holding_id, **fields)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Holding not found: {holding_id}")
        row = state_store.get_holding(holding_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update cockpit holding")
        raise HTTPException(status_code=500, detail=f"Failed to update holding: {str(exc)}") from exc

    if row is None:
        raise HTTPException(status_code=404, detail=f"Holding not found: {holding_id}")
    return CockpitHoldingRecord(**dict(row))


@router.delete("/holdings/{holding_id}", response_model=CockpitHoldingMutationResponse)
def cockpit_remove_holding(holding_id: str) -> CockpitHoldingMutationResponse:
    try:
        service = CockpitService.get_instance()
        removed = service.state_store.remove_holding(holding_id)
    except Exception as exc:
        logger.exception("Failed to remove cockpit holding")
        raise HTTPException(status_code=500, detail=f"Failed to remove holding: {str(exc)}") from exc

    if not removed:
        raise HTTPException(status_code=404, detail=f"Holding not found: {holding_id}")
    return CockpitHoldingMutationResponse(ok=True, holding_id=holding_id)


@router.get("/pulse", response_model=IntelPulseResponse)
def cockpit_intel_pulse(ticker: str | None = None) -> IntelPulseResponse:
    """Return system population and quality metrics for Intel Pulse."""
    try:
        service = CockpitService.get_instance()
        return service.get_intel_pulse_stats(ticker)
    except Exception as exc:
        logger.exception("Failed to fetch intel pulse stats")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/matrix", response_model=IntelPulseMatrixResponse)
def cockpit_intel_matrix(
    stage: str, ticker: str | None = None
) -> IntelPulseMatrixResponse:
    """Return diagnostic density matrix for Intel Pulse."""
    try:
        service = CockpitService.get_instance()
        return service.get_diagnostic_matrix(stage, ticker)
    except Exception as exc:
        logger.exception("Failed to fetch diagnostic matrix")
        raise HTTPException(status_code=500, detail=str(exc))


class CockpitChatRequest(BaseModel):
    class AttachedSource(BaseModel):
        source_id: str
        source_kind: Literal["ephemeral", "concat", "primary"]

    message: str
    mode: str = "analysis"
    ticker: str | None = None
    session_id: str | None = None
    stream: bool = True
    model: str | None = None
    web_search: bool | None = None
    rag: bool | None = None
    db_diagnostics: bool | None = None
    attached_sources: list[AttachedSource] = Field(default_factory=list)


class CockpitActionExecuteRequest(BaseModel):
    action_id: str
    args: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    wait: bool = True


class CockpitActionExecuteResponse(BaseModel):
    ok: bool = True
    action_id: str
    result: str = ""
    exit_code: int = 0
    job_id: str | None = None
    status: str | None = None
    queued: bool = False
    chart: dict[str, str] | None = None


class CockpitActionJobStatusResponse(BaseModel):
    ok: bool = True
    job_id: str
    action_id: str
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    exit_code: int | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    result: str | None = None
    progress_stage: str | None = None
    progress_pct: float | None = None


class MarketplaceMissionRecord(BaseModel):
    mission_id: str
    name: str
    status: str
    brief: str
    category_hint: str | None = None
    hard_filters: dict[str, Any] = Field(default_factory=dict)
    soft_preferences: dict[str, Any] = Field(default_factory=dict)
    search_config: dict[str, Any] = Field(default_factory=dict)
    scan_config: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    last_scan_at: str | None = None


class MarketplaceMissionListResponse(BaseModel):
    items: list[MarketplaceMissionRecord] = Field(default_factory=list)


class MarketplaceMissionUpsertRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    brief: str | None = None
    category_hint: str | None = None
    hard_filters: dict[str, Any] = Field(default_factory=dict)
    soft_preferences: dict[str, Any] = Field(default_factory=dict)
    search_config: dict[str, Any] = Field(default_factory=dict)
    scan_config: dict[str, Any] = Field(default_factory=dict)


class MarketplaceBrowserHealthResponse(BaseModel):
    status: str
    cdp_url: str
    browser_family: str
    profile_path: str
    logged_in: bool
    challenge_detected: bool
    last_checked_at: str
    detail: str | None = None
    final_url: str | None = None


class MarketplaceScanRequest(BaseModel):
    mission_id: str | None = None


class MarketplaceScanJobListResponse(BaseModel):
    items: list[CockpitActionJobStatusResponse] = Field(default_factory=list)


class MarketplaceMatchRecord(BaseModel):
    match_id: str
    mission_id: str
    mission_name: str | None = None
    listing_id: str
    listing_url: str
    title: str
    price: str | None = None
    price_value: float | None = None
    location: str | None = None
    seller_name: str | None = None
    captured_at: str
    score: int
    decision_band: str
    reasons_for: list[str] = Field(default_factory=list)
    reasons_against: list[str] = Field(default_factory=list)
    confidence: float | None = None
    raw_text_snapshot: str
    screenshot_path: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: str


class MarketplaceMatchListResponse(BaseModel):
    items: list[MarketplaceMatchRecord] = Field(default_factory=list)


class MarketplaceMatchStatusRequest(BaseModel):
    status: str


class MarketplaceAlertRecord(BaseModel):
    alert_id: str
    mission_id: str
    mission_name: str | None = None
    match_id: str
    match_title: str | None = None
    listing_url: str | None = None
    price: str | None = None
    location: str | None = None
    decision_band: str | None = None
    status: str
    created_at: str
    updated_at: str
    trigger_reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketplaceAlertListResponse(BaseModel):
    items: list[MarketplaceAlertRecord] = Field(default_factory=list)


class MarketplaceAlertStatusRequest(BaseModel):
    status: str


class CockpitFeedbackFlagRequest(BaseModel):
    session_id: str | None = None
    ticker: str | None = None
    feedback_type: Literal["good", "poor"] = "poor"
    capture_kind: Literal["chat_feedback", "ui_issue"] = "chat_feedback"
    note: str | None = None
    flagged_message: dict[str, Any] = Field(default_factory=dict)
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    frontend_context: dict[str, Any] = Field(default_factory=dict)
    screenshot: dict[str, Any] | None = None


class CockpitFeedbackFlagResponse(BaseModel):
    ok: bool = True
    report_id: str
    feedback_type: Literal["good", "poor"]
    capture_kind: Literal["chat_feedback", "ui_issue"] = "chat_feedback"
    report_dir: str
    bundle_path: str
    summary_path: str
    analysis_path: str | None = None
    read_api_path: str
    codex_prompt: str
    analysis_summary: str | None = None


class CockpitFlaggedReportListItem(BaseModel):
    report_id: str
    feedback_type: Literal["good", "poor"]
    capture_kind: Literal["chat_feedback", "ui_issue"] = "chat_feedback"
    session_id: str
    ticker: str | None = None
    saved_at: str | None = None
    note: str | None = None
    flagged_response_excerpt: str | None = None
    read_api_path: str


class CockpitFlaggedReportListResponse(BaseModel):
    items: list[CockpitFlaggedReportListItem] = Field(default_factory=list)


class CockpitFlaggedReportResponse(BaseModel):
    report_id: str
    feedback_type: Literal["good", "poor"]
    capture_kind: Literal["chat_feedback", "ui_issue"] = "chat_feedback"
    report_dir: str
    bundle_path: str
    summary_path: str
    analysis_path: str | None = None
    read_api_path: str
    bundle: dict[str, Any] = Field(default_factory=dict)
    summary_markdown: str = ""
    analysis: dict[str, Any] | None = None


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


def _clip_action_output(value: str | None, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:limit]


def _read_job_output(path: str | None, limit: int = 12000) -> str:
    raw_path = str(path or "").strip()
    if not raw_path:
        return ""
    try:
        return _clip_action_output(Path(raw_path).read_text(encoding="utf-8"), limit)
    except OSError:
        return ""


def _run_action_subprocess(
    *,
    normalized_command: list[str],
    repo_root: Path,
    action_env: dict[str, str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        normalized_command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env=action_env,
    )


def _run_action_subprocess_streaming(
    *,
    job_id: str,
    normalized_command: list[str],
    repo_root: Path,
    action_env: dict[str, str],
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
    on_stdout_line: Callable[[str], None] | None = None,
) -> tuple[int, str, str]:
    """Run a subprocess, streaming stdout/stderr to log files line-by-line.

    Returns ``(exit_code, stdout_text, stderr_text)``.
    """

    def _pump(
        pipe: IO[str],
        dest: IO[str],
        callback: Callable[[str], None] | None,
    ) -> None:
        """Read lines from *pipe*, write to *dest* (flushed), optionally call *callback*."""
        try:
            for raw_line in pipe:
                dest.write(raw_line)
                dest.flush()
                if callback is not None:
                    callback(raw_line)
        except ValueError:
            pass  # pipe closed

    with (
        stdout_path.open("w", encoding="utf-8") as out_f,
        stderr_path.open("w", encoding="utf-8") as err_f,
    ):
        proc = subprocess.Popen(
            normalized_command,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=action_env,
        )
        with _ACTION_JOB_PROC_LOCK:
            _ACTION_JOB_PROCS[job_id] = proc
        t_out = threading.Thread(
            target=_pump, args=(proc.stdout, out_f, on_stdout_line), daemon=True
        )
        t_err = threading.Thread(
            target=_pump, args=(proc.stderr, err_f, None), daemon=True
        )
        t_out.start()
        t_err.start()

        try:
            proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            with _ACTION_JOB_PROC_LOCK:
                _ACTION_JOB_PROCS.pop(job_id, None)
            return 124, "", f"Action timed out after {timeout_seconds}s\n"

        t_out.join(timeout=5)
        t_err.join(timeout=5)
        with _ACTION_JOB_PROC_LOCK:
            _ACTION_JOB_PROCS.pop(job_id, None)

    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    return proc.returncode, stdout_text, stderr_text


def _read_job_output_tail(raw_path: str | None, max_bytes: int = 64000) -> str:
    """Read the last *max_bytes* of a log file (for tailing in-progress jobs)."""
    if not raw_path:
        return ""
    p = Path(raw_path)
    if not p.is_file():
        return ""
    try:
        size = p.stat().st_size
        with p.open("r", encoding="utf-8", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                f.readline()  # skip partial first line
            return f.read()
    except OSError:
        return ""


def _serialize_action_job_status(
    service: CockpitService, job_id: str, *, tail: int = 0
) -> dict[str, Any]:
    job = service.state_store.get_job(job_id)
    if job is None:
        raise FileNotFoundError(job_id)

    status = str(job.get("status") or "unknown")
    result_text = ""
    if status == "success":
        result_text = _read_job_output(job.get("stdout_path"))
    elif status == "failed":
        result_text = _read_job_output(job.get("stderr_path")) or _read_job_output(
            job.get("stdout_path")
        )
    elif status == "running":
        raw = _read_job_output_tail(job.get("stdout_path"))
        if tail > 0:
            result_text = "\n".join(raw.splitlines()[-tail:])
        else:
            result_text = raw

    return {
        "ok": True,
        "job_id": str(job.get("job_id") or job_id),
        "action_id": str(job.get("action_id") or ""),
        "status": status,
        "started_at": job.get("started_at"),
        "ended_at": job.get("ended_at"),
        "exit_code": job.get("exit_code"),
        "stdout_path": job.get("stdout_path"),
        "stderr_path": job.get("stderr_path"),
        "result": result_text or None,
        "progress_stage": job.get("progress_stage"),
        "progress_pct": job.get("progress_pct"),
    }


def _marketplace_mission_service(service: CockpitService) -> MarketplaceMissionService:
    _ensure_marketplace_scan_scheduler(service)
    return MarketplaceMissionService(service.state_store)


def _list_marketplace_scan_jobs(
    service: CockpitService, *, limit: int = 50
) -> list[dict[str, Any]]:
    rows = service.state_store.list_jobs(limit=max(limit * 5, 100))
    items: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("action_id") or "") != "marketplace_scan":
            continue
        items.append(
            {
                "ok": True,
                "job_id": str(row.get("job_id") or ""),
                "action_id": "marketplace_scan",
                "status": str(row.get("status") or "unknown"),
                "started_at": row.get("started_at"),
                "ended_at": row.get("ended_at"),
                "exit_code": row.get("exit_code"),
                "stdout_path": row.get("stdout_path"),
                "stderr_path": row.get("stderr_path"),
                "result": None,
                "progress_stage": row.get("progress_stage"),
                "progress_pct": row.get("progress_pct"),
            }
        )
        if len(items) >= limit:
            break
    return items


def _write_marketplace_job_line(handle: IO[str], message: str) -> None:
    handle.write(message.rstrip() + "\n")
    handle.flush()


def _marketplace_scan_in_progress(service: CockpitService) -> bool:
    for job in _list_marketplace_scan_jobs(service, limit=50):
        if str(job.get("status") or "") in {"queued", "running"}:
            return True
    return False


def _run_marketplace_scan_job(
    *,
    service: CockpitService,
    mission_id: str | None,
    job_id: str,
    stdout_path: Path,
    stderr_path: Path,
    tracker: Any | None,
    stop_event: threading.Event,
) -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    mission_service = _marketplace_mission_service(service)
    title = "Marketplace scan"
    if mission_id:
        mission = mission_service.get_mission(mission_id)
        if mission is not None:
            title = f"Marketplace scan: {mission['name']}"

    _persist_action_job_row(
        service,
        job_id=job_id,
        action_id="marketplace_scan",
        args={"mission_id": mission_id},
        started_at=started_at,
        status="running",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        progress_stage="Starting Marketplace scan",
        progress_pct=0.0,
    )
    if tracker is not None:
        _best_effort_tracker_call("start_job", job_id)
        _best_effort_tracker_call(
            "change_phase", job_id, "marketplace_scan", message=f"Started {title}"
        )

    with stdout_path.open("a", encoding="utf-8") as stdout_handle, stderr_path.open(
        "a", encoding="utf-8"
    ) as stderr_handle:
        scanner = MarketplaceScanner(mission_service)

        def progress(stage: str, pct: float | None) -> None:
            service.state_store.update_job_progress(job_id, stage, pct)
            if tracker is not None:
                _best_effort_tracker_call("change_phase", job_id, stage, message=stage)
                if pct is not None:
                    bounded = max(0, min(100, int(pct)))
                    _best_effort_tracker_call(
                        "record_progress",
                        job_id,
                        current=bounded,
                        total=100,
                        message=stage,
                    )

        def log(message: str) -> None:
            _write_marketplace_job_line(stdout_handle, message)

        try:
            result = scanner.run_sync(
                mission_id=mission_id,
                progress=progress,
                log=log,
                cancel_requested=stop_event.is_set,
            )
            _write_marketplace_job_line(stdout_handle, json.dumps(result, indent=2))
            ended_at = datetime.now(timezone.utc).isoformat()
            _persist_action_job_row(
                service,
                job_id=job_id,
                action_id="marketplace_scan",
                args={"mission_id": mission_id},
                started_at=started_at,
                ended_at=ended_at,
                status="success",
                exit_code=0,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            if tracker is not None:
                _best_effort_tracker_call("complete_job", job_id, result.get("summary"))
        except MarketplaceScanCancelled as exc:
            _write_marketplace_job_line(stdout_handle, str(exc))
            ended_at = datetime.now(timezone.utc).isoformat()
            _persist_action_job_row(
                service,
                job_id=job_id,
                action_id="marketplace_scan",
                args={"mission_id": mission_id},
                started_at=started_at,
                ended_at=ended_at,
                status="cancelled",
                exit_code=130,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                progress_stage="Cancelled",
                progress_pct=100.0,
            )
            if tracker is not None:
                _best_effort_tracker_call("cancel_job", job_id, reason=str(exc))
        except Exception as exc:
            _write_marketplace_job_line(stderr_handle, str(exc))
            ended_at = datetime.now(timezone.utc).isoformat()
            _persist_action_job_row(
                service,
                job_id=job_id,
                action_id="marketplace_scan",
                args={"mission_id": mission_id},
                started_at=started_at,
                ended_at=ended_at,
                status="failed",
                exit_code=1,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            if tracker is not None:
                _best_effort_tracker_call("fail_job", job_id, str(exc))
        finally:
            _forget_queued_action_job(job_id)


def _launch_marketplace_scan_job(
    service: CockpitService,
    *,
    mission_id: str | None,
    trigger_source: str = "cockpit",
) -> dict[str, Any]:
    tracker = _get_backend_job_tracker()
    job_id = uuid.uuid4().hex
    logs_dir = Path(service.artifact_store.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / f"{job_id}.out.log"
    stderr_path = logs_dir / f"{job_id}.err.log"
    started_at = datetime.now(timezone.utc).isoformat()
    title = "Marketplace scan"

    if tracker is not None:
        _best_effort_tracker_call(
            "create_job",
            job_id=job_id,
            job_type="marketplace_scan",
            job_family="marketplace",
            title=title,
            trigger_source=trigger_source,
            entity_scope=mission_id or "all",
            metadata={"mission_id": mission_id, "trigger_source": trigger_source},
        )
        _best_effort_tracker_call(
            "add_artifact",
            job_id,
            artifact_type="log",
            artifact_label="stdout log",
            artifact_path=str(stdout_path),
        )
        _best_effort_tracker_call(
            "add_artifact",
            job_id,
            artifact_type="log",
            artifact_label="stderr log",
            artifact_path=str(stderr_path),
        )

    _persist_action_job_row(
        service,
        job_id=job_id,
        action_id="marketplace_scan",
        args={"mission_id": mission_id},
        started_at=started_at,
        status="queued",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        progress_stage="Queued",
        progress_pct=0.0,
    )
    runtime = QueuedActionJobRuntime(
        job_id=job_id,
        action_id="marketplace_scan",
        started_at=started_at,
    )
    _register_queued_action_job(runtime)

    worker = threading.Thread(
        target=_run_marketplace_scan_job,
        kwargs={
            "service": service,
            "mission_id": mission_id,
            "job_id": job_id,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "tracker": tracker,
            "stop_event": runtime.stop_event,
        },
        daemon=True,
        name=f"marketplace-scan-{job_id[:8]}",
    )
    worker.start()

    return {
        "ok": True,
        "action_id": "marketplace_scan",
        "result": f"Queued marketplace scan job ({trigger_source})",
        "exit_code": 0,
        "job_id": job_id,
        "status": "queued",
        "queued": True,
    }


def _run_marketplace_scheduler_tick(service: CockpitService) -> list[dict[str, Any]]:
    mission_service = MarketplaceMissionService(service.state_store)
    due_missions = mission_service.due_missions()
    if not due_missions or _marketplace_scan_in_progress(service):
        return []

    health = check_marketplace_browser_health()
    if str(health.get("status") or "") != "ready":
        return []

    launched: list[dict[str, Any]] = []
    mission = due_missions[0]
    queued = _launch_marketplace_scan_job(
        service,
        mission_id=str(mission.get("mission_id") or "") or None,
        trigger_source="scheduler",
    )
    launched.append(
        {
            "mission_id": mission.get("mission_id"),
            "job_id": queued.get("job_id"),
        }
    )
    return launched


def _marketplace_scheduler_loop(service: CockpitService) -> None:
    while True:
        try:
            launched = _run_marketplace_scheduler_tick(service)
            if launched:
                logger.info("Marketplace scheduler queued %d scan(s)", len(launched))
        except Exception:
            logger.exception("Marketplace scheduler tick failed")
        time.sleep(_MARKETPLACE_SCHEDULER_INTERVAL_SECONDS)


def _ensure_marketplace_scan_scheduler(service: CockpitService) -> None:
    global _MARKETPLACE_SCHEDULER_STARTED
    with _MARKETPLACE_SCHEDULER_LOCK:
        if _MARKETPLACE_SCHEDULER_STARTED:
            return
        worker = threading.Thread(
            target=_marketplace_scheduler_loop,
            kwargs={"service": service},
            daemon=True,
            name="marketplace-scheduler",
        )
        worker.start()
        _MARKETPLACE_SCHEDULER_STARTED = True


def _launch_action_job(
    *,
    service: CockpitService,
    action_id: str,
    args: dict[str, Any],
    normalized_command: list[str],
    action_env: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    from app.services.job_tracker import get_tracker

    job_id = uuid.uuid4().hex
    logs_dir = Path(service.artifact_store.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / f"{job_id}.out.log"
    stderr_path = logs_dir / f"{job_id}.err.log"
    started_at = datetime.now(timezone.utc).isoformat()
    tracker = get_tracker()
    ticker = str(args.get("ticker") or "").strip().upper() or None
    tickers = str(args.get("tickers") or "").strip().upper()
    entity_scope = tickers or action_id
    if not ticker and tickers and "," not in tickers:
        ticker = tickers
    action_label = action_id
    try:
        action_label = str(service.action_registry.get(action_id).label or action_id)
    except Exception:
        action_label = action_id

    if tracker is not None:
        try:
            tracker.create_job(
                job_id=job_id,
                job_type=action_id,
                job_family="cockpit_action",
                title=action_label,
                trigger_source="cockpit",
                entity_scope=entity_scope,
                ticker=ticker,
                metadata={"args": args},
            )
            tracker.add_artifact(
                job_id,
                artifact_type="log",
                artifact_label="stdout log",
                artifact_path=str(stdout_path),
            )
            tracker.add_artifact(
                job_id,
                artifact_type="log",
                artifact_label="stderr log",
                artifact_path=str(stderr_path),
            )
        except Exception:
            logger.warning(
                "ops tracker init for cockpit action failed (non-fatal)",
                exc_info=True,
            )

    service.state_store.add_job(
        {
            "job_id": job_id,
            "action_id": action_id,
            "args": args,
            "started_at": started_at,
            "ended_at": None,
            "status": "queued",
            "exit_code": None,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "artifacts": [],
        }
    )

    def _worker() -> None:
        from app.services.progress_parser import parse_progress_line

        if tracker is not None:
            try:
                tracker.start_job(job_id)
            except Exception:
                logger.warning(
                    "ops tracker start for cockpit action failed (non-fatal)",
                    exc_info=True,
                )
        service.state_store.add_job(
            {
                "job_id": job_id,
                "action_id": action_id,
                "args": args,
                "started_at": started_at,
                "ended_at": None,
                "status": "running",
                "exit_code": None,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "artifacts": [],
            }
        )

        _last_stage: str | None = None

        def _on_stdout_line(line: str) -> None:
            nonlocal _last_stage
            info = parse_progress_line(line)
            if info is None:
                return
            # Debounce: only write to DB when stage or pct changes
            if info.stage != _last_stage or info.pct is not None:
                _last_stage = info.stage
                service.state_store.update_job_progress(
                    job_id, info.stage, info.pct
                )
                if tracker is not None:
                    try:
                        tracker.change_phase(
                            job_id, info.stage, message=info.detail or info.stage
                        )
                        if info.current is not None and info.total is not None:
                            # Update tracker metrics so JobDetailPanel shows the progress bar
                            tracker.store.update_job_run(
                                job_id,
                                total_items=info.total,
                                succeeded_items=info.current,
                                current_item_label=info.detail,
                            )
                            tracker.record_progress(
                                job_id,
                                current=info.current,
                                total=info.total,
                                message=info.detail
                                or f"{info.current}/{info.total}",
                            )
                        elif info.percent_override is not None:
                            tracker.record_progress(
                                job_id,
                                current=int(info.percent_override),
                                total=100,
                                message=info.detail or f"{info.percent_override}%",
                            )
                    except Exception:
                        logger.warning(
                            "ops tracker progress for cockpit action failed (non-fatal)",
                            exc_info=True,
                        )

        exit_code: int | None = None
        status = "failed"
        stdout_text = ""
        stderr_text = ""
        try:
            exit_code, stdout_text, stderr_text = _run_action_subprocess_streaming(
                job_id=job_id,
                normalized_command=normalized_command,
                repo_root=Path(service.repo_root),
                action_env=action_env,
                timeout_seconds=timeout_seconds,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                on_stdout_line=_on_stdout_line,
            )
            with _ACTION_JOB_PROC_LOCK:
                was_cancelled = job_id in _ACTION_JOB_CANCEL_REQUESTS
                if was_cancelled:
                    _ACTION_JOB_CANCEL_REQUESTS.discard(job_id)
            status = (
                "cancelled" if was_cancelled else "success" if exit_code == 0 else "failed"
            )
        except Exception as exc:
            stderr_path.write_text(
                f"Action execution failed: {exc}\n", encoding="utf-8"
            )
            stderr_text = f"Action execution failed: {exc}\n"
            status = "failed"

        # Update the job status without overwriting the progress metrics
        service.state_store.update_job_status(
            job_id,
            status=status,
            exit_code=exit_code,
            ended_at=datetime.now(timezone.utc).isoformat(),
        )
        if tracker is not None:
            try:
                if status == "success":
                    tracker.complete_job(
                        job_id,
                        summary=_clip_action_output(
                            stdout_text or f"Action {action_id} completed successfully",
                            4000,
                        ),
                    )
                elif status == "cancelled":
                    tracker.cancel_job(job_id, reason="Cockpit action cancelled")
                else:
                    tracker.fail_job(
                        job_id,
                        _clip_action_output(
                            stderr_text or stdout_text or f"Action {action_id} failed",
                            4000,
                        ),
                    )
            except Exception:
                logger.warning(
                    "ops tracker finalize for cockpit action failed (non-fatal)",
                    exc_info=True,
                )

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name=f"cockpit-action-{job_id[:8]}",
    )
    thread.start()
    return {
        "ok": True,
        "action_id": action_id,
        "result": f"Queued action {action_id}",
        "exit_code": 0,
        "job_id": job_id,
        "status": "queued",
        "queued": True,
    }


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


def _build_filestats_chart_from_chat_response(
    response: Any,
) -> dict[str, str] | None:
    try:
        from cockpit.core.plotly_html import build_filestats_dashboard_html
    except Exception as exc:
        logger.debug("Filestats dashboard builder unavailable: %s", exc)
        return None

    evidence = getattr(response, "evidence", None)
    if not isinstance(evidence, list):
        return None

    for item in evidence:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "") != "company_dump":
            continue
        details = item.get("details")
        if not isinstance(details, dict):
            continue

        backend = details.get("backend")
        if not isinstance(backend, dict):
            continue

        ticker = (
            str(details.get("ticker") or backend.get("ticker") or "UNKNOWN")
            .strip()
            .upper()
        )
        cockpit_local_memory = details.get("cockpit_local_memory")
        if not isinstance(cockpit_local_memory, dict):
            cockpit_local_memory = {}

        payload = {
            **backend,
            "ticker": ticker,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cockpit_local_memory": cockpit_local_memory,
        }
        try:
            html = build_filestats_dashboard_html(payload)
        except Exception as exc:
            logger.warning("Failed to build filestats dashboard HTML: %s", exc)
            return None
        return {
            "title": f"{ticker} filestats dashboard",
            "html": html,
        }

    return None


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
        if script_path.is_absolute() and not script_path.exists():
            shared_root_override = str(
                os.getenv("COCKPIT_SHARED_SCRIPTS_ROOT") or ""
            ).strip()
            candidate_roots = [
                Path(shared_root_override) if shared_root_override else None,
                Path("/workspace/scripts"),
                Path("/workspace-scripts"),
            ]
            for root in candidate_roots:
                if root is None:
                    continue
                candidate = (root / script_path.name).resolve()
                if candidate.exists():
                    normalized[1] = str(candidate)
                    script_path = candidate
                    break

        if not script_path.is_absolute():
            candidates: list[Path] = [
                (repo_root / script_path).resolve(),
                (Path("/app") / script_path).resolve(),
                (Path("/scripts") / script_path.name).resolve(),
                (Path("/workspace/scripts") / script_path.name).resolve(),
                (Path("/workspace-scripts") / script_path.name).resolve(),
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
    shared_scripts_root = str(
        os.getenv("COCKPIT_SHARED_SCRIPTS_ROOT") or ""
    ).strip()
    candidates = [
        str((repo_root / "backend").resolve()),
        str((repo_root / "cockpit").resolve()),
        str((repo_root.parent / "scripts").resolve()),
        str((repo_root / "scripts").resolve()),
        shared_scripts_root,
        "/app",
        "/app/cockpit",
        "/scripts",
        "/workspace/scripts",
    ]
    merged = [p for p in candidates if p]
    if existing:
        merged.append(existing)
    env["PYTHONPATH"] = ":".join(merged)
    return env


def _execute_user_thesis_action(
    action_id: str,
    args: dict[str, Any],
) -> CockpitActionExecuteResponse:
    from app.services.user_thesis_memory import UserThesisMemoryStore

    store = UserThesisMemoryStore()
    ticker = str(args.get("ticker") or "").strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")

    if action_id == "create_thesis":
        statement = str(args.get("thesis") or "").strip()
        signal = str(args.get("signal") or "HOLD").strip().upper()
        if not statement:
            raise HTTPException(status_code=400, detail="thesis is required")
        proposal = store.create_proposal(
            ticker=ticker,
            proposal_type="create_thesis",
            statement=statement,
            signal=signal,
            confidence=0.7,
            metadata={"source_action_id": action_id},
            requested_by="cockpit_user",
        )
    elif action_id == "add_thesis_evidence":
        statement = str(args.get("finding") or "").strip()
        if not statement:
            raise HTTPException(status_code=400, detail="finding is required")
        is_supporting = bool(args.get("is_supporting", True))
        proposal = store.create_proposal(
            ticker=ticker,
            proposal_type="add_evidence",
            statement=statement,
            confidence=0.7,
            metadata={
                "source_action_id": action_id,
                "is_supporting": is_supporting,
            },
            requested_by="cockpit_user",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported strategy action: {action_id}",
        )

    proposal_id = str(proposal.get("proposal_id") or "")
    store.confirm_proposal(
        proposal_id,
        note="confirmed via cockpit action execute",
    )
    applied = store.apply_confirmed_proposal(proposal_id)
    entry = dict(applied.get("entry") or {})
    statement = str(entry.get("statement") or proposal.get("statement") or "").strip()
    if len(statement) > 180:
        statement = statement[:177] + "..."

    return CockpitActionExecuteResponse(
        ok=True,
        action_id=action_id,
        result=(
            f"Recorded user thesis memory for {ticker}: {statement}"
            f" (proposal_id={proposal_id})"
        ),
        exit_code=0,
        status="success",
    )


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
    if action_id in {"create_thesis", "add_thesis_evidence"}:
        try:
            return await asyncio.to_thread(
                _execute_user_thesis_action,
                action_id,
                args,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Strategy memory action execution failed: %s", action_id)
            raise HTTPException(
                status_code=500,
                detail=f"Strategy memory action failed: {str(exc)}",
            ) from exc

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

    if not payload.wait:
        queued = _launch_action_job(
            service=service,
            action_id=action_id,
            args=args,
            normalized_command=normalized_command,
            action_env=action_env,
            timeout_seconds=timeout_seconds,
        )
        return CockpitActionExecuteResponse(**queued)

    try:
        proc = await asyncio.to_thread(
            _run_action_subprocess,
            normalized_command=normalized_command,
            repo_root=Path(service.repo_root),
            action_env=action_env,
            timeout_seconds=timeout_seconds,
        )
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
        status="success",
    )


@router.get("/action/jobs/{job_id}", response_model=CockpitActionJobStatusResponse)
async def cockpit_get_action_job(job_id: str, tail: int = 0):
    """Return persisted status for a queued cockpit action."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for action job read")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    try:
        result = await asyncio.to_thread(
            _serialize_action_job_status, service, job_id, tail=tail
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Cockpit action job read failed")
        raise HTTPException(
            status_code=500,
            detail=f"Action job read failed: {str(exc)}",
        ) from exc

    return CockpitActionJobStatusResponse(**result)


@router.post("/action/jobs/{job_id}/stop")
async def cockpit_stop_action_job(job_id: str):
    """Stop a running queued cockpit action job."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for action stop")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    runtime = _get_queued_action_job(job_id)
    if runtime is not None:
        runtime.stop_event.set()

    with _ACTION_JOB_PROC_LOCK:
        proc = _ACTION_JOB_PROCS.get(job_id)
        if proc is not None:
            _ACTION_JOB_CANCEL_REQUESTS.add(job_id)

    if proc is not None:
        try:
            proc.terminate()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stop action job: {str(exc)}",
            ) from exc
        return {"ok": True, "job_id": job_id, "status": "cancelling"}

    if runtime is not None:
        return {"ok": True, "job_id": job_id, "status": "cancelling"}

    tracker = _get_backend_job_tracker()
    tracker_job: dict[str, Any] | None = None
    if tracker is not None:
        try:
            tracker_job = tracker.store.get_job_run(job_id)
        except Exception as exc:
            logger.debug("Tracker job lookup failed for %s: %s", job_id, exc)

    if tracker_job is not None:
        tracker_status = str(tracker_job.get("status") or "unknown")
        if tracker_status in {"succeeded", "failed", "cancelled"}:
            return {"ok": True, "job_id": job_id, "status": tracker_status}

        tracker_job_type = str(tracker_job.get("job_type") or "").strip().lower()
        tracker_job_family = (
            str(tracker_job.get("job_family") or "").strip().lower()
        )
        tracker_metadata = dict(tracker_job.get("metadata") or {})
        tracker_supports_cancellation = bool(
            tracker_metadata.get("supports_cancellation")
        )
        if (
            tracker_supports_cancellation
            and tracker_job_type in {"extraction", "backfill"}
            and tracker_job_family in {"pipeline", "celery"}
        ):
            try:
                tracker.request_cancellation(
                    job_id, reason="Cancellation requested from Cockpit."
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to request operation cancellation: {str(exc)}",
                ) from exc
            return {"ok": True, "job_id": job_id, "status": "cancelling"}

    job = service.state_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Action job not found: {job_id}")

    status = str(job.get("status") or "unknown")
    if status in {"success", "failed", "cancelled"}:
        return {"ok": True, "job_id": job_id, "status": status}

    raise HTTPException(
        status_code=409,
        detail=f"Action job is not currently stoppable: {job_id}",
    )


@router.get(
    "/marketplace/browser-health",
    response_model=MarketplaceBrowserHealthResponse,
)
async def cockpit_marketplace_browser_health():
    try:
        health = await asyncio.to_thread(check_marketplace_browser_health)
    except Exception as exc:
        logger.exception("Marketplace browser health check failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace browser health check failed: {str(exc)}",
        ) from exc
    return MarketplaceBrowserHealthResponse(**health)


@router.get(
    "/marketplace/missions",
    response_model=MarketplaceMissionListResponse,
)
async def cockpit_list_marketplace_missions(status: str | None = None):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        statuses = [item.strip().lower() for item in str(status or "").split(",") if item.strip()]
        items = await asyncio.to_thread(mission_service.list_missions, statuses=statuses or None)
    except Exception as exc:
        logger.exception("Marketplace mission listing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace mission listing failed: {str(exc)}",
        ) from exc
    return MarketplaceMissionListResponse(items=items)


@router.post(
    "/marketplace/missions",
    response_model=MarketplaceMissionRecord,
)
async def cockpit_create_marketplace_mission(payload: MarketplaceMissionUpsertRequest):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        mission = await asyncio.to_thread(mission_service.create_mission, payload.model_dump())
    except MarketplaceMissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Marketplace mission creation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace mission creation failed: {str(exc)}",
        ) from exc
    return MarketplaceMissionRecord(**mission)


@router.get(
    "/marketplace/missions/{mission_id}",
    response_model=MarketplaceMissionRecord,
)
async def cockpit_get_marketplace_mission(mission_id: str):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        mission = await asyncio.to_thread(mission_service.get_mission, mission_id)
    except Exception as exc:
        logger.exception("Marketplace mission read failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace mission read failed: {str(exc)}",
        ) from exc
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Marketplace mission not found: {mission_id}")
    return MarketplaceMissionRecord(**mission)


@router.patch(
    "/marketplace/missions/{mission_id}",
    response_model=MarketplaceMissionRecord,
)
async def cockpit_update_marketplace_mission(
    mission_id: str,
    payload: MarketplaceMissionUpsertRequest,
):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        mission = await asyncio.to_thread(
            mission_service.update_mission,
            mission_id,
            payload.model_dump(exclude_none=True),
        )
    except MarketplaceMissionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Marketplace mission not found: {exc}") from exc
    except MarketplaceMissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Marketplace mission update failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace mission update failed: {str(exc)}",
        ) from exc
    return MarketplaceMissionRecord(**mission)


@router.get(
    "/marketplace/scans",
    response_model=MarketplaceScanJobListResponse,
)
async def cockpit_list_marketplace_scan_jobs(limit: int = 50):
    try:
        service = CockpitService.get_instance()
        items = await asyncio.to_thread(_list_marketplace_scan_jobs, service, limit=limit)
    except Exception as exc:
        logger.exception("Marketplace scan listing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace scan listing failed: {str(exc)}",
        ) from exc
    return MarketplaceScanJobListResponse(
        items=[CockpitActionJobStatusResponse(**item) for item in items]
    )


@router.post(
    "/marketplace/scans",
    response_model=CockpitActionExecuteResponse,
)
async def cockpit_trigger_marketplace_scan(payload: MarketplaceScanRequest):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for marketplace scan")
        raise HTTPException(
            status_code=500,
            detail=f"Service initialization failed: {str(exc)}",
        ) from exc

    mission_id = str(payload.mission_id or "").strip() or None
    if mission_id:
        mission = await asyncio.to_thread(mission_service.get_mission, mission_id)
        if mission is None:
            raise HTTPException(status_code=404, detail=f"Marketplace mission not found: {mission_id}")
    else:
        active_missions = await asyncio.to_thread(mission_service.list_missions, statuses=["active"])
        if not active_missions:
            raise HTTPException(status_code=400, detail="No active Marketplace missions are available to scan")

    health = await asyncio.to_thread(check_marketplace_browser_health)
    if str(health.get("status")) != "ready":
        code = 409 if str(health.get("status")) in {"login_required", "challenge_detected"} else 503
        raise HTTPException(status_code=code, detail=str(health.get("detail") or health.get("status")))

    if await asyncio.to_thread(_marketplace_scan_in_progress, service):
        raise HTTPException(
            status_code=409,
            detail="A Marketplace scan is already in progress. Please wait for it to finish or stop it first.",
        )

    try:
        queued = await asyncio.to_thread(
            _launch_marketplace_scan_job,
            service,
            mission_id=mission_id,
        )
    except Exception as exc:
        logger.exception("Marketplace scan launch failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace scan launch failed: {str(exc)}",
        ) from exc
    return CockpitActionExecuteResponse(**queued)


@router.get(
    "/marketplace/scans/{job_id}",
    response_model=CockpitActionJobStatusResponse,
)
async def cockpit_get_marketplace_scan_job(job_id: str, tail: int = 0):
    try:
        service = CockpitService.get_instance()
        result = await asyncio.to_thread(
            _serialize_action_job_status,
            service,
            job_id,
            tail=tail,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Marketplace scan job not found: {exc}") from exc
    except Exception as exc:
        logger.exception("Marketplace scan job read failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace scan job read failed: {str(exc)}",
        ) from exc
    if str(result.get("action_id") or "") != "marketplace_scan":
        raise HTTPException(status_code=404, detail=f"Marketplace scan job not found: {job_id}")
    return CockpitActionJobStatusResponse(**result)


@router.get(
    "/marketplace/matches",
    response_model=MarketplaceMatchListResponse,
)
async def cockpit_list_marketplace_matches(
    mission_id: str | None = None,
    status: str | None = None,
    decision_band: str | None = None,
    limit: int = 100,
):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        items = await asyncio.to_thread(
            mission_service.list_matches,
            mission_id=mission_id,
            status=status,
            decision_band=decision_band,
            limit=limit,
        )
    except Exception as exc:
        logger.exception("Marketplace match listing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace match listing failed: {str(exc)}",
        ) from exc
    return MarketplaceMatchListResponse(items=items)


@router.get(
    "/marketplace/matches/{match_id}",
    response_model=MarketplaceMatchRecord,
)
async def cockpit_get_marketplace_match(match_id: str):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        match = await asyncio.to_thread(mission_service.get_match, match_id)
    except Exception as exc:
        logger.exception("Marketplace match read failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace match read failed: {str(exc)}",
        ) from exc
    if match is None:
        raise HTTPException(status_code=404, detail=f"Marketplace match not found: {match_id}")
    return MarketplaceMatchRecord(**match)


@router.patch(
    "/marketplace/matches/{match_id}",
    response_model=MarketplaceMatchRecord,
)
async def cockpit_update_marketplace_match(
    match_id: str,
    payload: MarketplaceMatchStatusRequest,
):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        match = await asyncio.to_thread(
            mission_service.update_match_status,
            match_id,
            payload.status,
        )
    except MarketplaceMissionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Marketplace match not found: {exc}") from exc
    except MarketplaceMissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Marketplace match update failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace match update failed: {str(exc)}",
        ) from exc
    return MarketplaceMatchRecord(**match)


@router.get(
    "/marketplace/alerts",
    response_model=MarketplaceAlertListResponse,
)
async def cockpit_list_marketplace_alerts(
    mission_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        items = await asyncio.to_thread(
            mission_service.list_alerts,
            mission_id=mission_id,
            status=status,
            limit=limit,
        )
    except Exception as exc:
        logger.exception("Marketplace alert listing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace alert listing failed: {str(exc)}",
        ) from exc
    return MarketplaceAlertListResponse(items=items)


@router.patch(
    "/marketplace/alerts/{alert_id}",
    response_model=MarketplaceAlertRecord,
)
async def cockpit_update_marketplace_alert(
    alert_id: str,
    payload: MarketplaceAlertStatusRequest,
):
    try:
        service = CockpitService.get_instance()
        mission_service = _marketplace_mission_service(service)
        alert = await asyncio.to_thread(
            mission_service.update_alert_status,
            alert_id,
            payload.status,
        )
    except MarketplaceMissionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Marketplace alert not found: {exc}") from exc
    except MarketplaceMissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Marketplace alert update failed")
        raise HTTPException(
            status_code=500,
            detail=f"Marketplace alert update failed: {str(exc)}",
        ) from exc
    return MarketplaceAlertRecord(**alert)


@router.post("/feedback/flag", response_model=CockpitFeedbackFlagResponse)
async def cockpit_flag_feedback(payload: CockpitFeedbackFlagRequest):
    """Persist a flagged cockpit chat turn with relevant backend diagnostics."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for feedback capture")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    try:
        result = await asyncio.to_thread(
            service.flag_chat_feedback,
            session_id=payload.session_id,
            ticker=payload.ticker,
            feedback_type=payload.feedback_type,
            capture_kind=payload.capture_kind,
            note=payload.note,
            flagged_message=payload.flagged_message,
            transcript=payload.transcript,
            frontend_context=payload.frontend_context,
            screenshot=payload.screenshot,
        )
    except Exception as exc:
        logger.exception("Cockpit feedback capture failed")
        raise HTTPException(
            status_code=500,
            detail=f"Feedback capture failed: {str(exc)}",
        ) from exc

    return CockpitFeedbackFlagResponse(**result)


@router.get("/feedback/flags", response_model=CockpitFlaggedReportListResponse)
async def cockpit_list_flagged_feedback(limit: int = 25):
    """List recent flagged cockpit chat reports."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for feedback listing")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    try:
        items = await asyncio.to_thread(service.list_flagged_reports, limit)
    except Exception as exc:
        logger.exception("Cockpit feedback listing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Feedback listing failed: {str(exc)}",
        ) from exc

    return CockpitFlaggedReportListResponse(items=items)


@router.get("/feedback/flags/{report_id}", response_model=CockpitFlaggedReportResponse)
async def cockpit_get_flagged_feedback(report_id: str):
    """Return one flagged cockpit chat report by report_id."""
    try:
        service = CockpitService.get_instance()
    except Exception as exc:
        logger.exception("Failed to initialize CockpitService for feedback read")
        raise HTTPException(
            status_code=500, detail=f"Service initialization failed: {str(exc)}"
        ) from exc

    try:
        result = await asyncio.to_thread(service.get_flagged_report, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Cockpit feedback read failed")
        raise HTTPException(
            status_code=500,
            detail=f"Feedback read failed: {str(exc)}",
        ) from exc

    return CockpitFlaggedReportResponse(**result)


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
            attached_sources = [item.model_dump() for item in payload.attached_sources]
            response = await asyncio.to_thread(
                service.chat_stream,
                message=payload.message,
                ticker=payload.ticker,
                session_id=payload.session_id,
                enable_web=payload.web_search,
                model=payload.model,
                rag=payload.rag,
                db_diagnostics=payload.db_diagnostics,
                ui_mode=payload.mode,
                attached_sources=attached_sources,
            )
            sources = _enforce_visible_source_contract(payload.message, response)
            rendered_chart = _build_filestats_chart_from_chat_response(response)
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
                    "source": response.routing_metadata.get("source")
                    if response.routing_metadata
                    else "local",
                    "action_preview": response.action_preview,
                    "chart": rendered_chart,
                    "sources": sources,
                },
            }
        except Exception as exc:
            logger.exception("Cockpit chat non-streaming error")
            raise HTTPException(
                status_code=500, detail=f"Chat processing failed: {str(exc)}"
            ) from exc

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

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
                attached_sources = [item.model_dump() for item in payload.attached_sources]
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
                    ui_mode=payload.mode,
                    attached_sources=attached_sources,
                )
                sources = _enforce_visible_source_contract(payload.message, response)

                # After streaming finishes, send metadata and final state
                if response.tool_traces:
                    for trace in response.tool_traces:
                        await queue.put({"type": "tool_trace", "data": trace})

                if sources:
                    await queue.put({"type": "sources", "data": {"items": sources}})

                if response.action_preview:
                    await queue.put(
                        {"type": "action_preview", "data": response.action_preview}
                    )

                rendered_chart = _build_filestats_chart_from_chat_response(response)
                if rendered_chart:
                    await queue.put({"type": "chart", "data": rendered_chart})

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
                            "chart": rendered_chart,
                            "sources": sources,
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

        # SSE keepalive: yield a comment line if no real event has been sent
        # for this long. Prevents intermediaries (nginx, corporate proxies) from
        # silently tearing down the connection during long LLM passes, and gives
        # the client a signal that the server is still alive.
        keepalive_interval = SSE_KEEPALIVE_INTERVAL_SECONDS
        last_yield_monotonic = time.monotonic()

        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                worker_task.cancel()
                break

            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                if time.monotonic() - last_yield_monotonic >= keepalive_interval:
                    yield ": keepalive\n\n"
                    last_yield_monotonic = time.monotonic()
                continue

            if item is None:
                break

            yield f"data: {json.dumps(item)}\n\n"
            last_yield_monotonic = time.monotonic()

        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# -------------------------------------------------------------------
# TradingView Pine Script webhook endpoints
# -------------------------------------------------------------------


class TvAlertPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    ticker: str
    action: str = "neutral"
    price: float | None = None
    message: str | None = None
    timestamp: str | None = None


_TV_ALERTS_LOCK = threading.Lock()
_TV_ALERTS_MAX = 200


def _tv_alerts_path() -> Path:
    data_root = Path(settings.data_root) if hasattr(settings, "data_root") else Path("/tmp")
    return data_root / "tv_alerts.json"


def _load_tv_alerts() -> list[dict]:
    p = _tv_alerts_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def _save_tv_alerts(alerts: list[dict]) -> None:
    p = _tv_alerts_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(alerts, default=str))
    tmp.replace(p)


@router.post("/tv/alert", tags=["tradingview"])
async def receive_tv_alert(
    payload: TvAlertPayload,
    request: Request,
) -> dict:
    """Receive a Pine Script webhook alert from TradingView."""
    token = os.environ.get("TV_WEBHOOK_TOKEN", "")
    if token:
        incoming = request.headers.get("X-TradingView-Webhook-Token", "")
        if incoming != token:
            raise HTTPException(status_code=403, detail="Invalid webhook token")

    entry: dict = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    with _TV_ALERTS_LOCK:
        alerts = _load_tv_alerts()
        alerts.append(entry)
        if len(alerts) > _TV_ALERTS_MAX:
            alerts = alerts[-_TV_ALERTS_MAX:]
        _save_tv_alerts(alerts)

    logger.info("TV alert received: %s %s @ %s", payload.ticker, payload.action, payload.price)
    return {"ok": True, "received": entry}


@router.get("/tv/alerts", tags=["tradingview"])
async def get_tv_alerts(limit: int = 50) -> dict:
    """Return recent TradingView Pine Script alerts."""
    limit = max(1, min(limit, 200))
    with _TV_ALERTS_LOCK:
        alerts = _load_tv_alerts()
    return {"ok": True, "count": len(alerts[-limit:]), "alerts": list(reversed(alerts[-limit:]))}
