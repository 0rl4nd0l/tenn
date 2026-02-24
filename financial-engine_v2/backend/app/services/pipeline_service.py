from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any, TypedDict

import httpx

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.documents import Document
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


def _coerce_uuid(value: Any) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


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
        processed = 0
        processed_ok_count = 0
        extraction_failed_count = 0
        skipped_download = 0
        errors: list[dict[str, Any]] = []

        for document_id in discovery["new_document_ids"]:
            try:
                pipeline_core.download_pdf_for_document(db, document_id)
                extraction_result: dict[str, Any] | None = None
                if bool(spec.process_documents):
                    extraction_result = pipeline_core.process_document(document_id)
                    extraction_status = str((extraction_result or {}).get("extraction_status") or "").strip().lower()
                    if extraction_status == "failed":
                        extraction_failed_count += 1
                        errors.append(
                            {
                                "document_id": document_id,
                                "stage": "process_document",
                                "error": "extraction_failed",
                                "extraction_status": extraction_status,
                                "details": extraction_result,
                            }
                        )
                    else:
                        processed_ok_count += 1
                else:
                    processed_ok_count += 1
                processed += 1
            except RuntimeError as exc:
                if "marketindex_headed_required" in str(exc):
                    doc = db.query(Document).filter(
                        Document.document_id == _coerce_uuid(document_id)
                    ).first()
                    if doc:
                        doc.pdf_sha256 = "blocked_marketindex_headed_required"
                        db.commit()
                    skipped_download += 1
                    continue
                db.rollback()
                errors.append({"document_id": document_id, "error": str(exc)})
            except httpx.HTTPStatusError as exc:
                request_url = str(exc.request.url)
                if exc.response.status_code == 403 and "marketindex.com.au" in request_url:
                    doc = db.query(Document).filter(
                        Document.document_id == _coerce_uuid(document_id)
                    ).first()
                    if doc:
                        doc.pdf_sha256 = "blocked_marketindex_403"
                        db.commit()
                    skipped_download += 1
                    continue
                db.rollback()
                errors.append({"document_id": document_id, "error": str(exc)})
            except Exception as exc:
                db.rollback()
                errors.append({"document_id": document_id, "error": str(exc)})

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
        }
    finally:
        db.close()
