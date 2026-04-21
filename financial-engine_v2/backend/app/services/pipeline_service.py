from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, TypedDict

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.announcement_importance import classify_documents_and_materialize
from app.services import pipeline as pipeline_core
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


@dataclass
class PipelineJobSpec:
    ticker: str
    years: int
    process_documents: bool
    request_id: str | None = None
    mode: str = "sync"


class PipelineResult(TypedDict):
    ticker: str
    found: int
    inserted: int
    processed: int
    processed_ok_count: int
    extraction_failed_count: int
    skipped_download: int
    process_documents: bool
    importance_classification: dict[str, Any] | None
    provider_metrics: dict[str, Any]
    provider_failures_sample: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    error_count: int
    chunks_created: int
    chunks_skipped: int
    invalid_payloads: int
    written_points: int
    cancelled: bool


def run_pipeline_sync(spec: PipelineJobSpec) -> PipelineResult:
    ticker = str(spec.ticker or "").strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    if int(spec.years) <= 0:
        raise ValueError("years must be > 0")

    # Ops job-status tracking for the backfill (non-fatal if tracker unavailable)
    _ops_job_id: str | None = None
    try:
        from app.services.job_tracker import get_tracker

        _tracker = get_tracker()
        if _tracker is not None:
            _handle = _tracker.create_job(
                job_type="backfill",
                job_family="celery" if spec.mode == "celery" else "pipeline",
                title=f"Backfill {ticker} ({spec.years}y)",
                trigger_source=spec.mode,
                entity_scope="ticker",
                ticker=ticker,
                metadata={
                    "years": spec.years,
                    "process_documents": spec.process_documents,
                    "supports_cancellation": True,
                },
            )
            _tracker.start_job(_handle.job_id)
            _ops_job_id = _handle.job_id
    except Exception:
        logger.warning("ops tracker init for backfill failed (non-fatal)", exc_info=True)

    db = SessionLocal()
    try:
        def _cancel_requested() -> bool:
            if not _ops_job_id:
                return False
            tracker = get_tracker()
            if tracker is None:
                return False
            return tracker.is_cancellation_requested(_ops_job_id)

        if _cancel_requested():
            if _ops_job_id:
                try:
                    _tracker = get_tracker()
                    if _tracker:
                        _tracker.cancel_job(
                            _ops_job_id, "Backfill cancelled by user request."
                        )
                except Exception:
                    logger.warning(
                        "ops tracker cancellation for backfill failed (non-fatal)",
                        exc_info=True,
                    )
            return {
                "ticker": ticker,
                "found": 0,
                "inserted": 0,
                "processed": 0,
                "processed_ok_count": 0,
                "extraction_failed_count": 0,
                "skipped_download": 0,
                "process_documents": bool(spec.process_documents),
                "importance_classification": None,
                "provider_metrics": {},
                "provider_failures_sample": [],
                "errors": [],
                "error_count": 0,
                "chunks_created": 0,
                "chunks_skipped": 0,
                "invalid_payloads": 0,
                "written_points": 0,
                "cancelled": True,
            }

        discovery = pipeline_core.discover_and_insert_documents(
            db,
            ticker=ticker,
            years=int(spec.years),
        )
        doc_ids = discovery["new_document_ids"]

        # If we have no new docs, but processing is enabled and Qdrant collection is missing,
        # opportunistically re-process recent existing documents for this ticker to rebuild RAG.
        if not doc_ids and bool(spec.process_documents) and settings.enable_qdrant:
            try:
                q = QdrantClient(url=settings.qdrant_url, timeout=10)
                existing = {c.name for c in q.get_collections().collections}
                if settings.qdrant_collection not in existing:
                    cutoff_days = int(spec.years) * 365
                    recent_ids = (
                        db.query(Document.document_id)
                        .filter(Document.ticker == ticker)
                        .filter((Document.pdf_sha256.is_(None)) | (~Document.pdf_sha256.like("blocked_%")))
                        .order_by(Document.published_at.desc())
                        .limit(200)
                        .all()
                    )
                    doc_ids = [str(row[0]) for row in recent_ids]
            except Exception:
                # If Qdrant is unreachable or query fails, fall back to "new docs only".
                pass
        processed = 0
        skipped_download = 0
        extraction_failed_count = 0
        errors: list[dict[str, Any]] = []
        ingestion_metrics: dict[str, int] = {}
        total_docs = len(doc_ids)

        # Update ops tracker with total document count
        if _ops_job_id:
            try:
                _tracker = get_tracker()
                if _tracker:
                    _tracker.store.update_job_run(_ops_job_id, total_items=total_docs)
                    _tracker.change_phase(_ops_job_id, "processing", f"Processing {total_docs} documents")
            except Exception:
                pass

        try:
            for idx, document_id in enumerate(doc_ids):
                if _cancel_requested():
                    raise pipeline_core.PipelineJobCancelled(
                        "Backfill cancelled by user request."
                    )

                # Ops progress
                if _ops_job_id:
                    try:
                        _tracker = get_tracker()
                        if _tracker:
                            _tracker.record_progress(
                                _ops_job_id,
                                current=idx,
                                total=total_docs,
                                current_item_label=str(document_id)[:16],
                            )
                    except Exception:
                        pass
                try:
                    pipeline_core.download_pdf_for_document(db, document_id)
                except Exception as exc:
                    err_str = str(exc)
                    if "marketindex_headed_required" in err_str or "document_quarantined" in err_str:
                        skipped_download += 1
                    errors.append({"document_id": str(document_id), "stage": "download", "error": err_str})
                    continue
                processed += 1
                if bool(spec.process_documents):
                    try:
                        proc_result = pipeline_core.process_document(
                            document_id,
                            parent_job_id=_ops_job_id,
                        ) or {}
                        if (proc_result.get("extraction_status") or "").strip().lower() == "failed":
                            extraction_failed_count += 1
                            errors.append({
                                "document_id": str(document_id),
                                "stage": "process_document",
                                "error": "extraction_failed",
                                "extraction_status": proc_result.get("extraction_status"),
                            })
                        for key in ("chunks_created", "chunks_skipped", "invalid_payloads", "written_points"):
                            ingestion_metrics[key] = ingestion_metrics.get(key, 0) + int(proc_result.get(key) or 0)
                    except pipeline_core.PipelineJobCancelled:
                        raise
                    except Exception as exc:
                        extraction_failed_count += 1
                        errors.append({"document_id": str(document_id), "stage": "process_document", "error": str(exc)})
        except pipeline_core.PipelineJobCancelled as exc:
            if _ops_job_id:
                try:
                    _tracker = get_tracker()
                    if _tracker:
                        _tracker.cancel_job(_ops_job_id, str(exc))
                except Exception:
                    logger.warning("ops tracker cancellation for backfill failed (non-fatal)", exc_info=True)

            return {
                "ticker": discovery["ticker"],
                "found": discovery["found"],
                "inserted": discovery["inserted"],
                "processed": processed,
                "processed_ok_count": max(processed - extraction_failed_count, 0),
                "extraction_failed_count": extraction_failed_count,
                "skipped_download": skipped_download,
                "process_documents": bool(spec.process_documents),
                "importance_classification": None,
                "provider_metrics": discovery.get("provider_metrics") or {},
                "provider_failures_sample": discovery.get("provider_failures_sample") or [],
                "errors": errors,
                "error_count": len(errors),
                "chunks_created": int(ingestion_metrics.get("chunks_created", 0) or 0),
                "chunks_skipped": int(ingestion_metrics.get("chunks_skipped", 0) or 0),
                "invalid_payloads": int(ingestion_metrics.get("invalid_payloads", 0) or 0),
                "written_points": int(ingestion_metrics.get("written_points", 0) or 0),
                "cancelled": True,
            }

        processed_ok_count = processed - extraction_failed_count

        importance_classification = None
        if settings.enable_importance_classification:
            try:
                importance_classification = classify_documents_and_materialize(
                    db,
                    ticker=ticker,
                    document_ids=discovery["new_document_ids"],
                    output_root=settings.importance_output_root,
                    materialize_output=settings.importance_materialize_output,
                    include_pdf_text=settings.importance_include_pdf_text,
                    link_mode=settings.importance_link_mode,
                    sort_source_docs=settings.importance_sort_source_docs,
                )
            except Exception as exc:
                importance_classification = {"error": str(exc)}

        result = {
            "ticker": discovery["ticker"],
            "found": discovery["found"],
            "inserted": discovery["inserted"],
            "processed": processed,
            "processed_ok_count": processed_ok_count,
            "extraction_failed_count": extraction_failed_count,
            "skipped_download": skipped_download,
            "process_documents": bool(spec.process_documents),
            "importance_classification": importance_classification,
            "provider_metrics": discovery.get("provider_metrics") or {},
            "provider_failures_sample": discovery.get("provider_failures_sample") or [],
            "errors": errors,
            "error_count": len(errors),
            "chunks_created": int(ingestion_metrics.get("chunks_created", 0) or 0),
            "chunks_skipped": int(ingestion_metrics.get("chunks_skipped", 0) or 0),
            "invalid_payloads": int(ingestion_metrics.get("invalid_payloads", 0) or 0),
            "written_points": int(ingestion_metrics.get("written_points", 0) or 0),
            "cancelled": False,
        }

        # Ops tracker completion
        if _ops_job_id:
            try:
                _tracker = get_tracker()
                if _tracker:
                    _tracker.store.update_job_run(
                        _ops_job_id,
                        succeeded_items=processed_ok_count,
                        failed_items=extraction_failed_count,
                        skipped_items=skipped_download,
                        warning_count=len(errors),
                    )
                    summary = f"Backfill {ticker}: {processed_ok_count} ok, {extraction_failed_count} failed, {skipped_download} skipped"
                    _tracker.complete_job(_ops_job_id, summary=summary)
            except Exception:
                logger.warning("ops tracker completion for backfill failed (non-fatal)", exc_info=True)

        return result
    except Exception:
        if _ops_job_id:
            try:
                _tracker = get_tracker()
                if _tracker:
                    _tracker.fail_job(_ops_job_id, f"Backfill {ticker} failed")
            except Exception:
                pass
        raise
    finally:
        db.close()
