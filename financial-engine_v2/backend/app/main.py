import errno
import json
import logging
import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func

from app.api.routes import (
    BookIngestRequest,
    TranscriptIngestRequest,
    ingest_book_route,
    ingest_transcript_route,
    require_api_key,
    router,
)
from app.core.config import LOADED_ENV_FILES, PROJECT_ROOT, settings
from app.core.db import SessionLocal, engine
from app.models.base import Base
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.api.analysis import router as analysis_router
from app.api.context import router as context_router
from app.api.commentary import router as commentary_router
from app.api.extraction_review import router as extraction_review_router
from app.routes.chat import router as chat_router

try:
    from app.routes.cockpit_api import router as cockpit_api_router
except ImportError:
    cockpit_api_router = None
try:
    from app.routes.ops_api import router as ops_api_router
except ImportError:
    ops_api_router = None
from app.routes.research import router as research_router
from app.services.embeddings import (
    get_qdrant_collection_vector_config,
    validate_qdrant_collection,
    verify_qdrant,
)
from app.services.llm import embed_texts
from app.services.llamacpp_runtime import (
    build_embedding_headers,
    resolve_embedding_runtime_config,
    resolve_extraction_runtime_config,
    resolve_llm_runtime_config,
)
from app.services.extraction_eval import FixtureContext
from app.services.extraction_gold_eval import (
    RealGoldFixture,
    evaluate_real_gold_fixture,
)
from app.services.extraction_review import create_review_session_from_payload
from app.services.method_isolated_extraction import (
    normalize_extraction_method,
    run_method_isolated_extraction,
)
from app.services.ollama import probe_ollama_embeddings
from app.services.rag import query_news_chunks, query_rag
from app.services.eval_task_registry import get_eval_task_registry
from app.services.router_state import extraction_activity


app = FastAPI(title="Financial Engine v2")
app.include_router(router, prefix="/api")
app.include_router(chat_router)
app.include_router(chat_router, prefix="/api")
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(research_router, prefix="/research", tags=["research"])
app.include_router(context_router, prefix="/api/context", tags=["context"])
app.include_router(commentary_router, prefix="/api/commentary", tags=["commentary"])
app.include_router(
    extraction_review_router,
    prefix="/api/extraction-review",
    tags=["extraction_review"],
)
if cockpit_api_router is not None:
    app.include_router(cockpit_api_router, prefix="/api/cockpit", tags=["cockpit"])
if ops_api_router is not None:
    app.include_router(ops_api_router, prefix="/api/ops", tags=["ops"])


class RagQueryRequest(BaseModel):
    query: str
    source: Literal["asx_docs", "news", "commentary", "hybrid"] = "asx_docs"
    ticker: Optional[str] = None
    top_k: int = 8
    debug: bool = False
    provider: Optional[str] = None
    language: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class CapabilityProposalApplyRequest(BaseModel):
    proposal_id: str


REAL_GOLD_DATASET_DIR = PROJECT_ROOT / "data" / "extraction_gold_real"
REAL_GOLD_SUPPORTED_METRICS = ("revenue", "operating_cash_flow", "net_debt")
REAL_GOLD_METRIC_KEY_MAP = {
    "revenue": "revenue",
    "operating_cash_flow": "operating_cf",
    "net_debt": "net_debt",
}
REAL_GOLD_CONTEXT_FIELDS = ("period_type", "period_end", "currency", "scale")
DEFAULT_LOCAL_LLAMACPP_API_KEY = "local-openai-key"


@dataclass(frozen=True)
class RealGoldDocument:
    document_id: str
    source_file: str
    period_type: str
    period_end: str
    currency: str
    scale: str
    metrics: dict[str, float | None]
    expected_trust: str


class RealGoldEvalRequest(BaseModel):
    limit: int = 0
    tolerance: float = 0.01
    method: str = "auto"
    strict_method: bool = False
    # Optional prompt-bundle id to resolve via prompt_registry.resolve().
    # When None, the canonical "default" bundle is used (the same one that
    # pins extraction_runs.prompt_hash to its historical value).
    prompt_variant_id: str | None = None
    # Optional llama.cpp model id to pin for every LLM call in this run
    # (e.g. "qwen2.5-14b-instruct" vs "qwen3-30b-a3b-instruct"). When None,
    # the configured extraction default is used.
    model_override: str | None = None


def _discover_local_llamacpp_api_key() -> str:
    try:
        proc = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""

    for line in proc.stdout.splitlines():
        if "llama-server" not in line or "--api-key" not in line:
            continue
        _, _, tail = line.partition("--api-key")
        candidate = tail.strip().split(maxsplit=1)[0]
        if candidate:
            return candidate
    return ""


def _persist_local_llm_api_key() -> str:
    existing = str(os.environ.get("LLM_API_KEY") or "").strip()
    if existing:
        return existing

    detected = _discover_local_llamacpp_api_key()
    if not detected:
        detected = DEFAULT_LOCAL_LLAMACPP_API_KEY

    os.environ["LLM_API_KEY"] = detected
    return detected


def _load_real_gold_document(path: Path) -> RealGoldDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"gold file must be a JSON object: {path}")

    missing = [
        key
        for key in (
            "document_id",
            "source_file",
            "period_type",
            "period_end",
            "currency",
            "scale",
            "metrics",
            "expected_trust",
        )
        if key not in payload
    ]
    if missing:
        raise ValueError(f"missing required fields in {path}: {', '.join(missing)}")

    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, dict):
        raise ValueError(f"metrics must be an object in {path}")

    metrics: dict[str, float | None] = {}
    for metric_name, metric_value in metrics_raw.items():
        if metric_name not in REAL_GOLD_SUPPORTED_METRICS:
            raise ValueError(
                f"unsupported metric '{metric_name}' in {path}; "
                f"supported={REAL_GOLD_SUPPORTED_METRICS}"
            )
        if metric_value is None:
            metrics[metric_name] = None
        elif isinstance(metric_value, bool) or not isinstance(
            metric_value, (int, float)
        ):
            raise ValueError(
                f"metric '{metric_name}' must be numeric or null in {path}"
            )
        else:
            metrics[metric_name] = float(metric_value)

    expected_trust = str(payload.get("expected_trust") or "").strip().lower()
    if expected_trust not in {"trusted", "abstain", "quarantine"}:
        raise ValueError(f"invalid expected_trust '{expected_trust}' in {path}")

    period_type = str(payload.get("period_type") or "").strip().upper()
    if period_type not in {"A", "H", "Q"}:
        raise ValueError(f"period_type must be one of A/H/Q in {path}")

    currency = str(payload.get("currency") or "").strip().upper()
    if not currency:
        raise ValueError(f"currency must be non-empty in {path}")

    scale = str(payload.get("scale") or "").strip().lower()
    if scale not in {"units", "thousands", "millions"}:
        raise ValueError(f"scale must be units|thousands|millions in {path}")

    return RealGoldDocument(
        document_id=str(payload.get("document_id")),
        source_file=str(payload.get("source_file")),
        period_type=period_type,
        period_end=str(payload.get("period_end")),
        currency=currency,
        scale=scale,
        metrics=metrics,
        expected_trust=expected_trust,
    )


def _load_real_gold_dataset(dataset_dir: Path) -> list[RealGoldDocument]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"dataset directory not found: {dataset_dir}")

    docs = [
        _load_real_gold_document(path) for path in sorted(dataset_dir.glob("*.json"))
    ]
    if not docs:
        raise ValueError(f"no dataset files found in {dataset_dir}")
    return docs


def _resolve_real_gold_source_path(source_file: str) -> Path:
    candidate = Path(source_file)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"source file does not exist: {candidate}")

    for base in (PROJECT_ROOT, PROJECT_ROOT.parent):
        resolved = base / candidate
        if resolved.exists():
            return resolved

    raise FileNotFoundError(
        f"could not resolve source_file '{source_file}' relative to {PROJECT_ROOT}"
    )


def _extract_ticker_from_source_path(source_path: Path) -> str:
    parts = list(source_path.parts)
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "UNKNOWN"


def _normalize_real_gold_context(field: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if field in {"period_type", "currency"}:
        return text.upper()
    if field == "scale":
        return text.lower()
    if field == "period_end":
        return text[:10]
    return text


def _build_real_gold_fixture(
    doc: RealGoldDocument, tolerance: float
) -> RealGoldFixture:
    return RealGoldFixture(
        document_id=doc.document_id,
        context=FixtureContext(
            period_end=doc.period_end,
            period_type=doc.period_type,
            currency=doc.currency,
            scale=doc.scale,
        ),
        metrics=dict(doc.metrics),
        tolerances={metric: tolerance for metric in doc.metrics},
        expected_trust=doc.expected_trust,
    )


def _evaluate_real_gold_document(
    doc: RealGoldDocument,
    *,
    tolerance: float,
    method: str,
    strict_method: bool,
    prompt_variant_id: str | None = None,
    model_override: str | None = None,
) -> dict[str, Any]:
    _persist_local_llm_api_key()
    source_path = _resolve_real_gold_source_path(doc.source_file)
    metadata = {
        "document_id": doc.document_id,
        "ticker": _extract_ticker_from_source_path(source_path),
        "title": source_path.name,
    }

    extraction_error = None
    try:
        with extraction_activity(
            metadata={
                "document_id": doc.document_id,
                "requested_method": method,
                "strict_method": strict_method,
                "ticker": metadata["ticker"],
                "title": metadata["title"],
            }
        ):
            extraction_result = run_method_isolated_extraction(
                str(source_path),
                metadata,
                None,
                requested_method=method,
                strict_method=strict_method,
                skip_narrative=True,
                prompt_bundle_id=prompt_variant_id,
                model_override=model_override,
            )
        payload = (
            extraction_result.payload
            if isinstance(extraction_result.payload, dict)
            else {}
        )
        extraction_status = str(getattr(extraction_result, "status", "failed"))
        extraction_error = getattr(extraction_result, "error", None)
    except Exception as exc:  # noqa: BLE001
        payload = {}
        extraction_status = "failed"
        extraction_error = str(exc)

    expected_context = {
        "period_type": doc.period_type,
        "period_end": doc.period_end,
        "currency": doc.currency,
        "scale": doc.scale,
    }
    actual_context: dict[str, str | None] = {}
    context_mismatches: list[str] = []
    for field in REAL_GOLD_CONTEXT_FIELDS:
        expected_value = _normalize_real_gold_context(field, expected_context[field])
        actual_value = _normalize_real_gold_context(field, payload.get(field))
        actual_context[field] = actual_value
        if expected_value != actual_value:
            context_mismatches.append(
                f"{field}: expected={expected_value!r} actual={actual_value!r}"
            )

    normalized_metrics: dict[str, Any] = {}
    raw_metrics = (
        payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    )
    for metric_name, source_metric_key in REAL_GOLD_METRIC_KEY_MAP.items():
        normalized_metrics[metric_name] = raw_metrics.get(source_metric_key)

    evaluation_payload = dict(payload)
    evaluation_payload["metrics"] = normalized_metrics
    method_provenance = payload.get("_method_provenance")
    method_provenance = method_provenance if isinstance(method_provenance, dict) else {}

    evaluation = evaluate_real_gold_fixture(
        _build_real_gold_fixture(doc, tolerance),
        evaluation_payload,
    )
    metric_results: dict[str, dict[str, Any]] = {}
    metric_status_counts = {"correct": 0, "wrong": 0, "missing": 0, "abstain": 0}
    for metric in evaluation.metrics:
        metric_results[metric.metric] = {
            "status": metric.status.value,
            "expected": metric.expected,
            "actual": metric.actual,
            "reason": metric.reason,
            "source_metric_key": REAL_GOLD_METRIC_KEY_MAP.get(
                metric.metric, metric.metric
            ),
        }
        if metric.status.value in metric_status_counts:
            metric_status_counts[metric.status.value] += 1

    failed_metric_count = (
        metric_status_counts["wrong"]
        + metric_status_counts["missing"]
        + metric_status_counts["abstain"]
    )

    review_session_id: str | None = None
    review_item_count = 0
    review_reason: str | None = None
    if payload and (
        failed_metric_count > 0 or str(extraction_status or "") == "parser_error"
    ):
        try:
            review_session = create_review_session_from_payload(
                document_id=doc.document_id,
                ticker=metadata["ticker"],
                title=metadata["title"],
                pdf_path=doc.source_file,
                status=extraction_status,
                payload=payload,
                diagnostics={
                    "code": "real_gold_eval",
                    "message": "Generated from /api/extraction-eval/real-gold.",
                    "expected_trust": doc.expected_trust,
                },
            )
            review_session_id = str(review_session.get("session_id") or "").strip() or None
            review_item_count = len(review_session.get("items") or [])
            documents = review_session.get("documents")
            if isinstance(documents, list) and documents:
                review_reason = (
                    str(documents[0].get("reason") or "").strip() or None
                )
        except Exception as exc:  # noqa: BLE001
            review_reason = f"review_session_failed:{exc}"

    mismatch_reasons: list[str] = [*context_mismatches]
    for metric_name, result in metric_results.items():
        if result["status"] != "correct":
            mismatch_reasons.append(f"metric:{metric_name}:{result['reason']}")
    if evaluation.trust_matches_expected is False:
        mismatch_reasons.append(
            f"trust: expected={doc.expected_trust} actual={evaluation.trust.value}"
        )
    if extraction_error:
        mismatch_reasons.append(f"extraction_error:{extraction_error}")

    return {
        "document_id": doc.document_id,
        "source_file": doc.source_file,
        "source_path": str(source_path),
        "source_basename": source_path.name,
        "ticker": metadata["ticker"],
        "period_type": doc.period_type,
        "period_end": doc.period_end,
        "expected_trust": doc.expected_trust,
        "extraction_status": extraction_status,
        "extraction_error": extraction_error,
        "context_correct": evaluation.context_ok,
        "context_expected": expected_context,
        "context_actual": actual_context,
        "context_mismatches": context_mismatches,
        "metric_results": metric_results,
        "metric_status_counts": metric_status_counts,
        "correct_metric_count": metric_status_counts["correct"],
        "wrong_metric_count": metric_status_counts["wrong"],
        "missing_metric_count": metric_status_counts["missing"],
        "abstained_metric_count": metric_status_counts["abstain"],
        "failed_metric_count": failed_metric_count,
        "trust_outcome": evaluation.trust.value,
        "trust_triggers": evaluation.trust_triggers,
        "trust_matches_expected": evaluation.trust_matches_expected,
        "review_session_id": review_session_id,
        "review_item_count": review_item_count,
        "review_reason": review_reason,
        "mismatch_reasons": mismatch_reasons,
        "method_provenance": method_provenance,
    }


def _summarize_real_gold_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    trust_distribution = {"trusted": 0, "abstain": 0, "quarantine": 0}
    metric_status_counts = {"correct": 0, "wrong": 0, "missing": 0, "abstain": 0}
    per_metric_failure_counts: dict[str, dict[str, int]] = {
        metric: {"wrong": 0, "missing": 0, "abstain": 0}
        for metric in REAL_GOLD_SUPPORTED_METRICS
    }

    total_metric_checks = 0
    context_correct_count = 0
    trust_match_count = 0
    context_mismatch_field_count = 0
    failed_document_count = 0
    trust_trigger_counts: dict[str, int] = {}

    for result in results:
        trust = str(result.get("trust_outcome") or "abstain")
        trust_distribution[trust] = trust_distribution.get(trust, 0) + 1
        if result.get("context_correct"):
            context_correct_count += 1
        else:
            context_mismatch_field_count += len(result.get("context_mismatches", []))
        if result.get("trust_matches_expected"):
            trust_match_count += 1
        if result.get("failed_metric_count", 0) > 0 or not result.get(
            "context_correct", False
        ):
            failed_document_count += 1
        for trigger in result.get("trust_triggers", []):
            trust_trigger_counts[trigger] = trust_trigger_counts.get(trigger, 0) + 1

        for metric_name, metric_result in (result.get("metric_results") or {}).items():
            status = str(metric_result.get("status") or "missing")
            total_metric_checks += 1
            metric_status_counts[status] = metric_status_counts.get(status, 0) + 1
            if status in {"wrong", "missing", "abstain"}:
                per_metric_failure_counts.setdefault(
                    metric_name, {"wrong": 0, "missing": 0, "abstain": 0}
                )
                per_metric_failure_counts[metric_name][status] += 1

    correct_count = metric_status_counts.get("correct", 0)
    accuracy = (correct_count / total_metric_checks) if total_metric_checks else 0.0
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_documents": len(results),
        "failed_documents": failed_document_count,
        "context_correct_documents": context_correct_count,
        "context_mismatch_documents": len(results) - context_correct_count,
        "context_mismatch_fields": context_mismatch_field_count,
        "context_accuracy": (context_correct_count / len(results) if results else 0.0),
        "total_metric_checks": total_metric_checks,
        "metric_status_counts": metric_status_counts,
        "correct_count": metric_status_counts.get("correct", 0),
        "wrong_count": metric_status_counts.get("wrong", 0),
        "missing_count": metric_status_counts.get("missing", 0),
        "abstained_count": metric_status_counts.get("abstain", 0),
        "total_accuracy": accuracy,
        "trust_distribution": trust_distribution,
        "trust_matches_expected": trust_match_count,
        "trust_mismatches_expected": len(results) - trust_match_count,
        "trust_trigger_counts": dict(sorted(trust_trigger_counts.items())),
        "per_metric_failure_counts": per_metric_failure_counts,
    }


def _run_real_gold_eval_sync(body: RealGoldEvalRequest) -> dict[str, Any]:
    try:
        method = normalize_extraction_method(body.method)
        gold_docs = _load_real_gold_dataset(REAL_GOLD_DATASET_DIR)
        if body.limit > 0:
            gold_docs = gold_docs[: body.limit]
        tolerance = max(float(body.tolerance), 0.0)
        results = [
            _evaluate_real_gold_document(
                doc,
                tolerance=tolerance,
                method=method,
                strict_method=body.strict_method,
                prompt_variant_id=body.prompt_variant_id,
                model_override=body.model_override,
            )
            for doc in gold_docs
        ]
        return {
            "dataset_dir": str(REAL_GOLD_DATASET_DIR),
            "requested_method": method,
            "strict_method": body.strict_method,
            "prompt_variant_id": body.prompt_variant_id,
            "model_override": body.model_override,
            "summary": _summarize_real_gold_results(results),
            "documents": results,
        }
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"real gold eval failed: {exc}",
        ) from exc


def _run_real_gold_eval_background(
    task_id: str, body: RealGoldEvalRequest
) -> None:
    """Execute a real-gold eval run and funnel its outcome into the task registry.

    This is the worker body for the background-thread path. Both HTTPException
    (400s from input validation) and any other exception must be captured and
    recorded on the registry — otherwise the polling GET would never see the
    failure and the CLI would hang until its own timeout.
    """
    registry = get_eval_task_registry()
    registry.set_running(task_id)
    try:
        result = _run_real_gold_eval_sync(body)
    except HTTPException as exc:
        registry.set_failed(task_id, f"HTTP {exc.status_code}: {exc.detail}")
    except Exception as exc:  # noqa: BLE001 — surface every failure to the poller
        registry.set_failed(task_id, f"{type(exc).__name__}: {exc}")
    else:
        registry.set_completed(task_id, result)


@app.post("/api/extraction-eval/real-gold", dependencies=[Depends(require_api_key)])
def run_real_gold_eval(
    body: RealGoldEvalRequest,
    background: bool = Query(
        default=False,
        description=(
            "When true, schedule the eval on a background thread and return "
            "202 + task_id; poll GET /api/extraction-eval/real-gold/tasks/"
            "{task_id} for the result. When false (default), run blocking "
            "and return the full payload — preserves the legacy contract for "
            "cockpit-ui and the prompt×model matrix script."
        ),
    ),
):
    # Sync handler: FastAPI offloads this to the anyio threadpool so the event
    # loop stays responsive (e.g. /api/health) during a full-corpus run.
    # Docling timeouts are enforced by a spawn ProcessPoolExecutor in
    # docling_extract._run_docling_with_timeout, so main-thread signal state
    # is no longer required here.
    if not background:
        return _run_real_gold_eval_sync(body)

    registry = get_eval_task_registry()
    record = registry.register()
    thread = threading.Thread(
        target=_run_real_gold_eval_background,
        args=(record.task_id, body),
        name=f"real-gold-eval-{record.task_id[:8]}",
        daemon=True,
    )
    thread.start()
    return JSONResponse(
        status_code=202,
        content={
            "task_id": record.task_id,
            "status": record.status.value,
        },
    )


@app.get(
    "/api/extraction-eval/real-gold/tasks/{task_id}",
    dependencies=[Depends(require_api_key)],
)
def get_real_gold_eval_task(task_id: str) -> dict[str, Any]:
    """Poll the status/result of a background real-gold eval run."""
    record = get_eval_task_registry().get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"unknown task_id: {task_id}")
    return record.to_dict()


@app.post("/rag/query", dependencies=[Depends(require_api_key)])
def rag_query(body: RagQueryRequest):
    try:
        if body.source == "asx_docs":
            return query_rag(
                query=body.query,
                ticker=body.ticker,
                top_k=body.top_k,
                debug=body.debug,
            )
        elif body.source == "news":
            return query_news_chunks(
                query=body.query,
                ticker=body.ticker,
                provider=body.provider,
                language=body.language or "en",
                date_from=body.date_from,
                date_to=body.date_to,
                top_k=body.top_k,
            )
        elif body.source == "commentary":
            raise HTTPException(
                status_code=501,
                detail="commentary source not yet implemented via /rag/query — use /chat",
            )
        elif body.source == "hybrid":
            raise HTTPException(
                status_code=501,
                detail="hybrid source not yet implemented via /rag/query — use /chat",
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"unknown source: {body.source}"
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/ingest/transcript", dependencies=[Depends(require_api_key)])
def ingest_transcript_alias(body: TranscriptIngestRequest):
    return ingest_transcript_route(body)


@app.post("/ingest/book", dependencies=[Depends(require_api_key)])
def ingest_book_alias(body: BookIngestRequest):
    return ingest_book_route(body)


RUNTIME_EMBEDDING_MODEL_FILE = PROJECT_ROOT / "reports" / "runtime_embedding_model.txt"
COCKPIT_ACCESS_STATE_FILE = PROJECT_ROOT / "reports" / "cockpit_access_state.json"
logger = logging.getLogger(__name__)
VECTOR_ID_FORMAT = "document_id:chunk_index"
DISTANCE = "COSINE"


def _architecture_version_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
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
    return "unknown"


def _log_architecture_runtime_assertion() -> None:
    logger.info(
        "Architecture version: %s\nEmbedding model: %s\nVector ID format: %s\nDistance: %s",
        _architecture_version_hash(),
        str(settings.embed_model or "").strip(),
        VECTOR_ID_FORMAT,
        DISTANCE,
    )


def _log_runtime_feature_warnings() -> None:
    if not settings.enable_embeddings:
        logger.warning(
            "WARNING: embeddings disabled - RAG functionality will be limited"
        )
    if not settings.enable_extraction:
        logger.warning(
            "WARNING: extraction disabled - ingestion outputs will be limited"
        )


def _log_session_memory_startup_status() -> None:
    if not bool(getattr(settings, "enable_session_memory", True)):
        logger.info(
            "session_memory: session memory disabled (ENABLE_SESSION_MEMORY=false)"
        )
        return
    from app.services.session_memory import _log_startup_status

    _log_startup_status()


def _log_resolved_models() -> None:
    try:
        llm_url, llm_model = resolve_llm_runtime_config()
        logger.info("Resolved LLM (chat/routing): model=%s url=%s", llm_model, llm_url)
    except Exception as exc:
        logger.error("STARTUP: failed to resolve LLM runtime config: %s", exc)

    try:
        ext_url, ext_model = resolve_extraction_runtime_config()
        logger.info("Resolved extraction: model=%s url=%s", ext_model, ext_url)
    except Exception as exc:
        logger.error("STARTUP: failed to resolve extraction runtime config: %s", exc)

    try:
        emb_url, emb_model = resolve_embedding_runtime_config()
        logger.info("Resolved embedding: model=%s url=%s", emb_model, emb_url)
    except Exception as exc:
        logger.error("STARTUP: failed to resolve embedding runtime config: %s", exc)

    # Log Ollama URL separately since embeddings may route through it
    ollama_url = str(settings.ollama_url or "").strip()
    if ollama_url:
        logger.info("Ollama endpoint (embeddings backend): %s", ollama_url)


def _log_runtime_config() -> None:
    logger.info(
        "Runtime config -> TASK_MODE=%s, ENABLE_EMBEDDINGS=%s, QDRANT_URL=%s, CELERY_BROKER_URL=%s",
        settings.task_mode,
        str(settings.enable_embeddings).lower(),
        settings.qdrant_url,
        settings.celery_broker_url,
    )
    if LOADED_ENV_FILES:
        logger.debug("Loaded env files: %s", ", ".join(LOADED_ENV_FILES))


def _socket_can_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    with socket.create_connection((host, port), timeout=timeout):
        return True


def check_llamacpp(base_url: str) -> bool:
    target = str(base_url or "").strip().rstrip("/")
    if not target:
        raise RuntimeError("missing base URL")
    response = httpx.get(f"{target}/v1/models", timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("unexpected /v1/models payload")
    for row in models:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or "").strip()
        if ":" in model_id:
            raise RuntimeError("Endpoint appears to be Ollama, not llama.cpp")
    return True


def check_ollama(base_url: str) -> bool:
    target = str(base_url or "").strip().rstrip("/")
    if not target:
        raise RuntimeError("missing base URL")
    response = httpx.get(f"{target}/api/tags", timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("unexpected /api/tags payload")
    return True


def validate_backends(llamacpp_base_url: str, ollama_base_url: str) -> None:
    llama_url = str(llamacpp_base_url or "").strip().rstrip("/")
    ollama_url = str(ollama_base_url or "").strip().rstrip("/")
    if not llama_url:
        raise RuntimeError("llama.cpp base URL must be configured.")
    if ollama_url and (
        llama_url == ollama_url
        or llama_url.startswith(ollama_url)
        or ollama_url.startswith(llama_url)
    ):
        raise RuntimeError("Potential backend overlap detected")
    try:
        check_llamacpp(llama_url)
    except Exception as exc:
        raise RuntimeError(f"llama.cpp endpoint invalid: {exc}") from exc
    if not ollama_url:
        return
    try:
        check_ollama(ollama_url)
    except Exception as exc:
        raise RuntimeError(f"Ollama endpoint invalid: {exc}") from exc


def _redis_socket_target() -> tuple[str, int]:
    parsed = urlparse(str(settings.celery_broker_url or "").strip())
    host = str(parsed.hostname or "").strip() or "127.0.0.1"
    port = int(parsed.port or 6379)
    return host, port


def _redis_connected() -> bool:
    broker_url = str(settings.celery_broker_url or "").strip().lower()
    if not broker_url.startswith(("redis://", "rediss://")):
        return False
    host, port = _redis_socket_target()
    try:
        return _socket_can_connect(host, port)
    except OSError:
        return False


def _log_redis_startup_status() -> None:
    if _redis_connected():
        logger.info("Celery broker reachable at %s", settings.celery_broker_url)
        return
    if str(settings.task_mode or "").strip().lower() != "celery":
        logger.info(
            "Celery broker unreachable while TASK_MODE=%s; host will continue without broker-backed ingestion",
            settings.task_mode,
        )
        return
    logger.warning(
        "Celery broker unreachable; ingestion disabled",
        extra={
            "celery_broker_url": settings.celery_broker_url,
            "ingestion_disabled": True,
        },
    )


def _should_skip_qdrant_startup_validation(exc: Exception) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError) and exc.errno == errno.EPERM:
        return True
    return "Operation not permitted" in str(exc)


def _read_stored_embedding_model() -> str | None:
    if not RUNTIME_EMBEDDING_MODEL_FILE.exists():
        return None
    try:
        stored = RUNTIME_EMBEDDING_MODEL_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning(
            "Unable to read stored embedding model marker %s: %s",
            RUNTIME_EMBEDDING_MODEL_FILE,
            exc,
        )
        return None
    return stored or None


def _write_runtime_embedding_model(model_name: str) -> None:
    resolved_model = str(model_name or "").strip()
    if not resolved_model:
        raise RuntimeError("Embedding model is not configured")
    RUNTIME_EMBEDDING_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_EMBEDDING_MODEL_FILE.write_text(resolved_model, encoding="utf-8")


def _count_db_embedding_rows() -> tuple[int, int]:
    db = SessionLocal()
    try:
        document_count = int(db.query(func.count(Document.document_id)).scalar() or 0)
        extraction_count = int(db.query(func.count(ExtractionRun.run_id)).scalar() or 0)
        return document_count, extraction_count
    finally:
        db.close()


def _qdrant_collection_state(client, collection_name: str) -> tuple[bool, int]:
    collections = client.get_collections()
    names = {collection.name for collection in collections.collections}
    if collection_name not in names:
        return False, 0
    collection_info = client.get_collection(collection_name=collection_name)
    raw_points_count = getattr(collection_info, "points_count", None)
    if raw_points_count is None:
        raw_points_count = getattr(collection_info, "vectors_count", None)
    return True, int(raw_points_count or 0)


def _get_embedding_state_snapshot(client=None) -> dict[str, object]:
    document_count, extraction_count = _count_db_embedding_rows()
    qdrant_collection_exists = False
    qdrant_points_count = 0

    if client is not None:
        qdrant_collection_exists, qdrant_points_count = _qdrant_collection_state(
            client,
            settings.qdrant_collection,
        )

    return {
        "stored_model": _read_stored_embedding_model(),
        "configured_model": str(settings.embed_model or "").strip(),
        "document_count": document_count,
        "extraction_count": extraction_count,
        "qdrant_collection_exists": qdrant_collection_exists,
        "qdrant_points_count": qdrant_points_count,
    }


def _validate_embedding_model_on_startup(client=None) -> None:
    snapshot = _get_embedding_state_snapshot(client=client)
    stored_model = str(snapshot.get("stored_model") or "").strip()
    configured_model = str(snapshot.get("configured_model") or "").strip()
    document_count = int(snapshot.get("document_count") or 0)
    extraction_count = int(snapshot.get("extraction_count") or 0)
    qdrant_collection_exists = bool(snapshot.get("qdrant_collection_exists"))
    qdrant_points_count = int(snapshot.get("qdrant_points_count") or 0)
    has_db_state = document_count > 0 or extraction_count > 0
    has_vectors = qdrant_collection_exists and qdrant_points_count > 0

    if not configured_model:
        raise RuntimeError("Embedding model is not configured")
    if not stored_model:
        _write_runtime_embedding_model(configured_model)
        logger.info("Recorded runtime embedding model marker: %s", configured_model)
        return
    if has_db_state and not has_vectors:
        logger.warning(
            "Database has embedding metadata but Qdrant collection is empty; startup allowed with inconsistency warning configured=%s document_count=%d extraction_count=%d qdrant_collection_exists=%s qdrant_points_count=%d",
            configured_model,
            document_count,
            extraction_count,
            qdrant_collection_exists,
            qdrant_points_count,
        )
        if stored_model and stored_model != configured_model:
            logger.warning(
                "Stored embedding model differs from config while Qdrant is empty: stored=%s configured=%s",
                stored_model,
                configured_model,
            )
        return
    if stored_model == configured_model:
        return
    if not has_vectors:
        logger.warning(
            "Stored embedding model differs from config but empty Qdrant collection allows startup: stored=%s configured=%s qdrant_collection_exists=%s qdrant_points_count=%d",
            stored_model,
            configured_model,
            qdrant_collection_exists,
            qdrant_points_count,
        )
        return
    raise RuntimeError(
        f"Embedding model mismatch: stored model is '{stored_model}', configured model is '{configured_model}', "
        f"documents={document_count}, extraction_runs={extraction_count}, qdrant_points={qdrant_points_count}. "
        "Reset and rebuild ingestion before serving RAG queries."
    )


def _validate_qdrant_on_startup() -> None:
    if not settings.enable_qdrant or not settings.enable_embeddings:
        return
    try:
        client = verify_qdrant()
    except Exception as exc:
        if not _should_skip_qdrant_startup_validation(exc):
            raise
        logger.warning("WARNING: qdrant startup validation skipped: %s", exc)
        return

    existing_collection, points_count = _qdrant_collection_state(
        client, settings.qdrant_collection
    )
    snapshot = _get_embedding_state_snapshot(client=client)
    _validate_embedding_model_on_startup(client=client)
    vectors = embed_texts(
        ["x"],
        metadata={
            "task_type": "embedding",
            "component": "startup_validation",
            "operation": "qdrant_dimension_probe",
        },
    )
    if not vectors or not vectors[0]:
        raise RuntimeError(
            "Could not get embedding dimension from model: embedding service returned no vector. "
            "Ensure the embedding model is available before starting the application."
        )

    expected_dim = len(vectors[0])
    actual_dim = None
    actual_distance = None
    if existing_collection:
        collection_config = get_qdrant_collection_vector_config(
            client, settings.qdrant_collection
        )
        actual_dim = collection_config.get("actual_dim")
        actual_distance = collection_config.get("actual_distance")
        points_count = int(collection_config.get("points_count") or 0)
    logger.info(
        "qdrant_startup_state",
        extra={
            "qdrant_collection": settings.qdrant_collection,
            "qdrant_collection_exists": existing_collection,
            "qdrant_points_count": points_count,
            "document_count": int(snapshot.get("document_count") or 0),
            "extraction_count": int(snapshot.get("extraction_count") or 0),
            "embed_model": snapshot.get("configured_model"),
            "stored_embed_model": snapshot.get("stored_model"),
            "expected_dim": expected_dim,
            "actual_dim": actual_dim,
            "actual_distance": str(actual_distance)
            if actual_distance is not None
            else None,
        },
    )
    if not existing_collection:
        logger.info(
            "Qdrant collection '%s' does not exist; startup allowed and collection will be created during ingestion",
            settings.qdrant_collection,
        )
        return
    if points_count <= 0:
        logger.warning(
            "Qdrant collection '%s' exists but has 0 vectors; startup allowed expected_dim=%s actual_dim=%s",
            settings.qdrant_collection,
            expected_dim,
            actual_dim,
        )
        return
    try:
        validate_qdrant_collection(client, settings.qdrant_collection, expected_dim)
    except RuntimeError as exc:
        if "does not exist" not in str(exc):
            raise
        logger.warning(
            "WARNING: qdrant collection '%s' is missing - it will be created during ingestion or the first RAG query",
            settings.qdrant_collection,
        )
    except Exception as exc:
        if not _should_skip_qdrant_startup_validation(exc):
            raise
        logger.warning("WARNING: qdrant startup validation skipped: %s", exc)


def _system_status_snapshot() -> dict[str, object]:
    redis_connected = _redis_connected()
    qdrant_connected = False
    collections_present: list[str] = []
    document_count_estimate = 0
    latest_document = None
    latest_extraction = None
    try:
        db = SessionLocal()
        try:
            document_count_estimate = int(
                db.query(func.count(Document.document_id)).scalar() or 0
            )
            latest_document = db.query(func.max(Document.ingested_at)).scalar()
            latest_extraction = db.query(func.max(ExtractionRun.created_at)).scalar()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Database status probe failed: %s", exc)

    last_ingestion_candidates = [
        value.isoformat()
        for value in (latest_document, latest_extraction)
        if isinstance(value, datetime)
    ]
    last_ingestion_activity = (
        max(last_ingestion_candidates) if last_ingestion_candidates else None
    )

    try:
        client = verify_qdrant()
        qdrant_connected = True
        collections = client.get_collections()
        collections_present = sorted(
            collection.name for collection in collections.collections
        )
    except Exception as exc:
        logger.warning("Qdrant status probe failed: %s", exc)

    return {
        "redis_connected": redis_connected,
        "qdrant_connected": qdrant_connected,
        "collections_present": collections_present,
        "document_count_estimate": document_count_estimate,
        "last_ingestion_activity": last_ingestion_activity,
    }


def _probe_llamacpp_runtime(
    base_url: str, expected_model: str, *, timeout: float = 5.0
) -> dict[str, object]:
    normalized_url = str(base_url or "").strip().rstrip("/")
    expected = str(expected_model or "").strip()
    result: dict[str, object] = {
        "base_url": normalized_url,
        "expected_model": expected,
        "reachable": False,
        "loaded_models": [],
    }
    if not normalized_url:
        result["error"] = "base_url_not_configured"
        return result
    try:
        response = httpx.get(f"{normalized_url}/v1/models", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else []
        loaded_models: list[str] = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                model_id = str(row.get("id") or "").strip()
                if model_id:
                    loaded_models.append(model_id)
        result["reachable"] = True
        result["loaded_models"] = loaded_models
        result["model_available"] = bool(
            expected
            and any(expected.lower() in model.lower() for model in loaded_models)
        )
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result


def _probe_embedding_runtime(
    base_url: str, expected_model: str, *, timeout: float = 5.0
) -> dict[str, object]:
    normalized_url = str(base_url or "").strip().rstrip("/")
    expected = str(expected_model or "").strip()
    result: dict[str, object] = {
        "base_url": normalized_url,
        "expected_model": expected,
        "reachable": False,
    }
    if not normalized_url:
        result["error"] = "base_url_not_configured"
        return result
    try:
        parsed = urlparse(normalized_url)
        if parsed.port == 11434:
            probe = probe_ollama_embeddings(normalized_url, expected, timeout=timeout)
            result["reachable"] = True
            result["dimension"] = int(probe.get("dimension") or 0)
            result["provider"] = "ollama"
            return result
        response = httpx.post(
            f"{normalized_url}/v1/embeddings",
            json={"model": expected, "input": ["healthcheck"]},
            headers={"Content-Type": "application/json", **build_embedding_headers()},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else []
        dimension = 0
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            vector = rows[0].get("embedding") or []
            if isinstance(vector, list):
                dimension = len(vector)
        result["reachable"] = True
        result["dimension"] = dimension
        result["provider"] = "llamacpp"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result


def _database_state_snapshot() -> dict[str, object]:
    result: dict[str, object] = {
        "reachable": False,
        "document_count": 0,
        "extraction_count": 0,
    }
    try:
        document_count, extraction_count = _count_db_embedding_rows()
        result["reachable"] = True
        result["document_count"] = document_count
        result["extraction_count"] = extraction_count
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _feature_snapshot(
    name: str, *, configured: bool, blockers: list[str], details: dict[str, object]
) -> dict[str, object]:
    status = "available" if configured and not blockers else "blocked"
    if not configured:
        status = "disabled"
    return {
        "name": name,
        "configured": configured,
        "status": status,
        "available": configured and not blockers,
        "blockers": blockers,
        "details": details,
    }


def _default_access_state() -> dict[str, bool]:
    return {
        "web_enabled": True,
        "rag_enabled": True,
        "db_diagnostic_query_enabled": True,
    }


def _load_access_state() -> dict[str, bool]:
    defaults = _default_access_state()
    if not COCKPIT_ACCESS_STATE_FILE.exists():
        return defaults
    try:
        payload = json.loads(COCKPIT_ACCESS_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(payload, dict):
        return defaults
    return {
        "web_enabled": bool(payload.get("web_enabled", defaults["web_enabled"])),
        "rag_enabled": bool(payload.get("rag_enabled", defaults["rag_enabled"])),
        "db_diagnostic_query_enabled": bool(
            payload.get(
                "db_diagnostic_query_enabled",
                defaults["db_diagnostic_query_enabled"],
            )
        ),
    }


def _write_access_state(state: dict[str, bool]) -> dict[str, bool]:
    normalized = {
        "web_enabled": bool(state.get("web_enabled", False)),
        "rag_enabled": bool(state.get("rag_enabled", False)),
        "db_diagnostic_query_enabled": bool(
            state.get("db_diagnostic_query_enabled", False)
        ),
    }
    COCKPIT_ACCESS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COCKPIT_ACCESS_STATE_FILE.write_text(
        json.dumps(normalized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return normalized


def _proposal_snapshot(
    proposal_id: str,
    *,
    target: str,
    summary: str,
    blocker: str,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "id": proposal_id,
        "target": target,
        "summary": summary,
        "blocker": blocker,
        "requires_confirmation": True,
        "source": "backend",
    }
    if details:
        payload["details"] = details
    return payload


def _system_capabilities_snapshot() -> dict[str, object]:
    system_status = _system_status_snapshot()
    db_state = _database_state_snapshot()

    llm_url, llm_model = resolve_llm_runtime_config()
    extraction_url, extraction_model = resolve_extraction_runtime_config()
    embedding_url, embedding_model = resolve_embedding_runtime_config()

    chat_runtime = _probe_llamacpp_runtime(llm_url, llm_model)
    extraction_runtime = _probe_llamacpp_runtime(extraction_url, extraction_model)
    embedding_runtime = _probe_embedding_runtime(embedding_url, embedding_model)

    qdrant_state: dict[str, object] = {
        "enabled": bool(settings.enable_qdrant),
        "reachable": bool(system_status.get("qdrant_connected")),
        "collections_present": list(system_status.get("collections_present") or []),
        "collection": str(settings.qdrant_collection),
    }
    redis_state: dict[str, object] = {
        "reachable": bool(system_status.get("redis_connected")),
        "task_mode": str(settings.task_mode),
        "broker_url": str(settings.celery_broker_url),
    }

    embedding_snapshot = _get_embedding_state_snapshot()
    embedding_consistent = (
        not embedding_snapshot.get("stored_model")
        or embedding_snapshot.get("stored_model")
        == embedding_snapshot.get("configured_model")
        or int(embedding_snapshot.get("qdrant_points_count") or 0) == 0
    )

    ingestion_blockers: list[str] = []
    if (
        str(settings.task_mode).strip().lower() == "celery"
        and not redis_state["reachable"]
    ):
        ingestion_blockers.append("celery_broker_unreachable")
    extraction_blockers: list[str] = []
    if bool(settings.enable_extraction) and not extraction_runtime.get("reachable"):
        extraction_blockers.append("extraction_runtime_unreachable")
    embeddings_blockers: list[str] = []
    if bool(settings.enable_embeddings):
        if not embedding_runtime.get("reachable"):
            embeddings_blockers.append("embedding_runtime_unreachable")
        if not qdrant_state["reachable"]:
            embeddings_blockers.append("qdrant_unreachable")
        if not embedding_consistent:
            embeddings_blockers.append("embedding_model_mismatch")
    rag_blockers: list[str] = []
    if bool(settings.enable_embeddings and settings.enable_qdrant):
        rag_blockers.extend(embeddings_blockers)
        if int(embedding_snapshot.get("qdrant_points_count") or 0) <= 0:
            rag_blockers.append("qdrant_has_no_vectors")

    proposals: list[dict[str, object]] = []
    if "celery_broker_unreachable" in ingestion_blockers:
        proposals.append(
            _proposal_snapshot(
                "restore_redis_broker",
                target="ingestion",
                summary="Restore Redis connectivity for queued ingestion",
                blocker="celery_broker_unreachable",
                details=redis_state,
            )
        )
    if "extraction_runtime_unreachable" in extraction_blockers:
        proposals.append(
            _proposal_snapshot(
                "start_extraction_runtime",
                target="extraction",
                summary="Start or repair the extraction llama.cpp runtime",
                blocker="extraction_runtime_unreachable",
                details={
                    "runtime_url": extraction_url,
                    "model": extraction_model,
                    "runtime_probe": extraction_runtime,
                },
            )
        )
    if "embedding_runtime_unreachable" in embeddings_blockers:
        proposals.append(
            _proposal_snapshot(
                "restore_embedding_runtime",
                target="embeddings",
                summary="Restore the embedding runtime endpoint",
                blocker="embedding_runtime_unreachable",
                details={
                    "runtime_url": embedding_url,
                    "model": embedding_model,
                    "runtime_probe": embedding_runtime,
                },
            )
        )
    if "qdrant_unreachable" in embeddings_blockers:
        proposals.append(
            _proposal_snapshot(
                "restore_qdrant",
                target="embeddings",
                summary="Restore Qdrant connectivity before running embeddings or RAG",
                blocker="qdrant_unreachable",
                details=qdrant_state,
            )
        )
    if "embedding_model_mismatch" in embeddings_blockers:
        proposals.append(
            _proposal_snapshot(
                "rebuild_embeddings",
                target="embeddings",
                summary="Rebuild embeddings to reconcile stored and configured embedding models",
                blocker="embedding_model_mismatch",
                details={
                    "configured_model": embedding_snapshot.get("configured_model"),
                    "stored_model": embedding_snapshot.get("stored_model"),
                    "qdrant_points_count": embedding_snapshot.get(
                        "qdrant_points_count"
                    ),
                },
            )
        )
    if "qdrant_has_no_vectors" in rag_blockers:
        proposals.append(
            _proposal_snapshot(
                "reingest_documents",
                target="rag",
                summary="Run ingestion to populate vectors before using RAG",
                blocker="qdrant_has_no_vectors",
                details={
                    "collection": str(settings.qdrant_collection),
                    "document_count": db_state.get("document_count"),
                    "last_activity": system_status.get("last_ingestion_activity"),
                },
            )
        )

    overall_status = "ready"
    if any(
        feature["status"] == "blocked"
        for feature in {
            "ingestion": _feature_snapshot(
                "ingestion",
                configured=True,
                blockers=ingestion_blockers,
                details={
                    "task_mode": str(settings.task_mode),
                    "last_activity": system_status.get("last_ingestion_activity"),
                },
            ),
            "extraction": _feature_snapshot(
                "extraction",
                configured=bool(settings.enable_extraction),
                blockers=extraction_blockers,
                details={
                    "runtime_url": extraction_url,
                    "model": extraction_model,
                },
            ),
            "embeddings": _feature_snapshot(
                "embeddings",
                configured=bool(settings.enable_embeddings),
                blockers=embeddings_blockers,
                details={
                    "runtime_url": embedding_url,
                    "model": embedding_model,
                    "stored_model": embedding_snapshot.get("stored_model"),
                    "qdrant_points_count": embedding_snapshot.get(
                        "qdrant_points_count"
                    ),
                },
            ),
            "rag": _feature_snapshot(
                "rag",
                configured=bool(settings.enable_embeddings and settings.enable_qdrant),
                blockers=rag_blockers,
                details={
                    "collection": str(settings.qdrant_collection),
                    "document_count": db_state.get("document_count"),
                    "last_activity": system_status.get("last_ingestion_activity"),
                },
            ),
        }.values()
    ):
        overall_status = "degraded"

    features = {
        "ingestion": _feature_snapshot(
            "ingestion",
            configured=True,
            blockers=ingestion_blockers,
            details={
                "task_mode": str(settings.task_mode),
                "last_activity": system_status.get("last_ingestion_activity"),
            },
        ),
        "extraction": _feature_snapshot(
            "extraction",
            configured=bool(settings.enable_extraction),
            blockers=extraction_blockers,
            details={
                "runtime_url": extraction_url,
                "model": extraction_model,
            },
        ),
        "embeddings": _feature_snapshot(
            "embeddings",
            configured=bool(settings.enable_embeddings),
            blockers=embeddings_blockers,
            details={
                "runtime_url": embedding_url,
                "model": embedding_model,
                "stored_model": embedding_snapshot.get("stored_model"),
                "qdrant_points_count": embedding_snapshot.get("qdrant_points_count"),
            },
        ),
        "rag": _feature_snapshot(
            "rag",
            configured=bool(settings.enable_embeddings and settings.enable_qdrant),
            blockers=rag_blockers,
            details={
                "collection": str(settings.qdrant_collection),
                "document_count": db_state.get("document_count"),
                "last_activity": system_status.get("last_ingestion_activity"),
            },
        ),
    }

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "authority": "backend",
        "status": overall_status,
        "access": _load_access_state(),
        "api_health": {"status": "ok"},
        "dependencies": {
            "database": db_state,
            "redis": redis_state,
            "qdrant": qdrant_state,
            "chat_runtime": chat_runtime,
            "extraction_runtime": extraction_runtime,
            "embedding_runtime": embedding_runtime,
        },
        "features": features,
        "proposals": proposals,
    }


def _start_extraction_runtime_via_backend() -> dict[str, object]:
    script_path = PROJECT_ROOT.parent / "scripts" / "run_llama_server.sh"
    if not script_path.exists():
        return {
            "ok": False,
            "proposal_id": "start_extraction_runtime",
            "status": "failed",
            "message": f"runtime launcher missing: {script_path}",
        }

    try:
        subprocess.Popen(
            ["bash", str(script_path)],
            cwd=str(PROJECT_ROOT.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return {
            "ok": False,
            "proposal_id": "start_extraction_runtime",
            "status": "failed",
            "message": f"failed to launch extraction runtime: {exc}",
        }

    extraction_url, extraction_model = resolve_extraction_runtime_config()
    for _ in range(20):
        try:
            probe = _probe_llamacpp_runtime(
                extraction_url, extraction_model, timeout=2.0
            )
        except Exception as exc:
            probe = {"reachable": False, "error": str(exc)}
        if probe.get("reachable"):
            return {
                "ok": True,
                "proposal_id": "start_extraction_runtime",
                "status": "applied",
                "message": f"extraction runtime reachable at {extraction_url}",
                "probe": probe,
            }
        time.sleep(1.0)

    return {
        "ok": False,
        "proposal_id": "start_extraction_runtime",
        "status": "failed",
        "message": f"extraction runtime did not become ready at {extraction_url}",
    }


def _apply_capability_proposal(proposal_id: str) -> dict[str, object]:
    normalized = str(proposal_id or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="proposal_id is required")
    if normalized == "start_extraction_runtime":
        return _start_extraction_runtime_via_backend()
    if normalized in {
        "enable_web_access",
        "disable_web_access",
        "enable_rag_access",
        "disable_rag_access",
        "enable_dbdiag_access",
        "disable_dbdiag_access",
    }:
        state = _load_access_state()
        mapping = {
            "enable_web_access": ("web_enabled", True, "Web access enabled."),
            "disable_web_access": ("web_enabled", False, "Web access disabled."),
            "enable_rag_access": ("rag_enabled", True, "RAG access enabled."),
            "disable_rag_access": ("rag_enabled", False, "RAG access disabled."),
            "enable_dbdiag_access": (
                "db_diagnostic_query_enabled",
                True,
                "DB diagnostics enabled.",
            ),
            "disable_dbdiag_access": (
                "db_diagnostic_query_enabled",
                False,
                "DB diagnostics disabled.",
            ),
        }
        key, enabled, message = mapping[normalized]
        state[key] = enabled
        written = _write_access_state(state)
        return {
            "ok": True,
            "proposal_id": normalized,
            "status": "applied",
            "message": message,
            "access": written,
        }
    raise HTTPException(
        status_code=404, detail=f"unknown or unsupported proposal: {normalized}"
    )


@app.get("/api/system/status", dependencies=[Depends(require_api_key)])
def system_status():
    return _system_status_snapshot()


@app.get("/api/system/capabilities", dependencies=[Depends(require_api_key)])
def system_capabilities():
    return _system_capabilities_snapshot()


@app.post("/api/system/proposals/apply", dependencies=[Depends(require_api_key)])
def apply_system_proposal(body: CapabilityProposalApplyRequest):
    return _apply_capability_proposal(body.proposal_id)


@app.get("/api/queue/status", dependencies=[Depends(require_api_key)])
def queue_status():
    """Return Celery queue depths via Redis LLEN.

    Returns per-queue message counts and aggregate totals.
    Does not require live Celery workers — reads broker state directly.
    """
    from app.celery_app import _SPECIALIZED_QUEUES

    queues: dict[str, int] = {}
    total_queued = 0
    redis_ok = False

    if _redis_connected():
        redis_ok = True
        try:
            import redis as redis_lib

            host, port = _redis_socket_target()
            parsed = urlparse(str(settings.celery_broker_url or ""))
            db = int(parsed.path.lstrip("/") or "0")
            client = redis_lib.Redis(host=host, port=port, db=db, socket_timeout=2)
            for queue_name in _SPECIALIZED_QUEUES:
                depth = client.llen(queue_name) or 0
                queues[queue_name] = depth
                total_queued += depth
            client.close()
        except Exception as exc:
            logger.warning("Queue depth probe failed: %s", exc)
            redis_ok = False

    return {
        "redis_connected": redis_ok,
        "queues": queues,
        "total_queued": total_queued,
    }


@app.on_event("startup")
def startup():
    Path(settings.docs_root).mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    _init_ops_tracker()
    _log_runtime_config()
    _log_resolved_models()
    _log_runtime_feature_warnings()
    _log_session_memory_startup_status()
    _log_redis_startup_status()
    _validate_qdrant_on_startup()
    _log_architecture_runtime_assertion()


def _init_ops_tracker() -> None:
    """Initialize the operational job-status tracker (SQLite at DATA_ROOT/ops/ops.db)."""
    try:
        from app.services.ops_store import OpsStore
        from app.services.job_tracker import init_tracker

        ops_db_path = Path(settings.data_root) / "ops" / "ops.db"
        store = OpsStore(ops_db_path)
        store.cleanup(max_age_days=90)
        tracker = init_tracker(store)
        logger.info("Ops tracker initialized: %s", ops_db_path)
    except Exception:
        logger.warning("Ops tracker initialization failed — job tracking disabled", exc_info=True)
