from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.announcement_importance import classify_documents_and_materialize
from app.services import pipeline as pipeline_core


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
        max_workers = max(1, settings.backfill_concurrency)
        processed, skipped_download, extraction_failed_count, errors, ingestion_metrics = (
            pipeline_core._download_and_process_document_ids(
                doc_ids,
                bool(spec.process_documents),
                max_workers=max_workers,
            )
        )
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
