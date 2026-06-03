from __future__ import annotations

import os
import sys

BACKEND_ROOT = os.environ.get("BACKEND_APP_ROOT", "/app_backend")
if BACKEND_ROOT and BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.db import SessionLocal
from app.services.pipeline import download_pdf_for_document, process_document as process_document_sync
from app.services.pipeline_service import PipelineJobSpec, run_pipeline_sync

from .celery_app import celery


@celery.task(name="backfill_ticker")
def backfill_ticker(
    ticker: str,
    years: int = 5,
    process_documents: bool = True,
    request_id: str | None = None,
):
    """Worker wrapper for the canonical backend pipeline service."""
    return run_pipeline_sync(
        PipelineJobSpec(
            ticker=ticker,
            years=years,
            process_documents=process_documents,
            request_id=request_id,
            mode="celery",
        )
    )


@celery.task(name="download_pdf")
def download_pdf(document_id: str):
    db = SessionLocal()
    try:
        return download_pdf_for_document(db, document_id)
    finally:
        db.close()


@celery.task(name="process_document")
def process_document(prev=None, document_id: str | None = None):
    if isinstance(prev, dict) and not document_id:
        document_id = str(prev.get("document_id") or "").strip()
    if not document_id:
        return {"error": "missing document_id"}
    return process_document_sync(document_id)
