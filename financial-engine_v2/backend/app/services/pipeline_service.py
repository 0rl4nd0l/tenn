from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.announcement_importance import classify_documents_and_materialize
from app.services import pipeline as pipeline_core
from qdrant_client import QdrantClient


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


def run_pipeline_sync(spec: PipelineJobSpec) -> PipelineResult:
    ticker = str(spec.ticker or "").strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    if int(spec.years) <= 0:
        raise ValueError("years must be > 0")

    db = SessionLocal()
    try:
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

        for document_id in doc_ids:
            try:
                pipeline_core.download_pdf_for_document(db, document_id)
            except Exception as exc:
                errors.append({"document_id": str(document_id), "stage": "download", "error": str(exc)})
                continue
            processed += 1
            if bool(spec.process_documents):
                try:
                    proc_result = pipeline_core.process_document(document_id) or {}
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
                except Exception as exc:
                    extraction_failed_count += 1
                    errors.append({"document_id": str(document_id), "stage": "process_document", "error": str(exc)})

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

        return {
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
        }
    finally:
        db.close()
