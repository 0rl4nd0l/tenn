from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.company_memory import CompanyMemoryStore
from app.services.market_memory import MarketMemoryStore
from app.services.query_orchestrator import QueryOrchestrator
from app.services.thesis_audit import ResearchReportInput, ThesisAuditService
from app.services.user_thesis_memory import UserThesisMemoryStore

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_UPLOAD_BYTES = 12 * 1024 * 1024
_MAX_BASE64_CHARS = int(_MAX_UPLOAD_BYTES * 1.4)


class ThesisAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)
    report_text: str | None = Field(default=None, max_length=300_000)
    filename: str | None = Field(default=None, max_length=240)
    mime_type: str | None = Field(default=None, max_length=160)
    content_base64: str | None = Field(default=None, max_length=_MAX_BASE64_CHARS)
    focus: str | None = Field(default=None, max_length=500)


class _ContextFinancialTruthProvider:
    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]:
        ticker = str(entities.get("primary_ticker") or "").strip().upper()
        if not ticker:
            return {
                "source": "financial_truth",
                "status": "no_entity",
                "items": [],
                "query": query,
                "intent": intent,
            }

        try:
            from app.api.context import get_ticker_context
            from app.core.db import SessionLocal
        except Exception as exc:
            return {
                "source": "financial_truth",
                "status": "error",
                "items": [],
                "ticker": ticker,
                "error": f"context loader unavailable: {exc}",
                "query": query,
                "intent": intent,
            }

        db = SessionLocal()
        try:
            payload = get_ticker_context(
                ticker=ticker,
                docs_limit=16,
                financials_limit=24,
                announcements_limit=24,
                failures_limit=12,
                low_confidence_limit=12,
                db=db,
            )
        except Exception as exc:
            return {
                "source": "financial_truth",
                "status": "error",
                "items": [],
                "ticker": ticker,
                "error": str(exc),
                "query": query,
                "intent": intent,
            }
        finally:
            db.close()

        errors = payload.get("errors") or []
        return {
            "source": "financial_truth",
            "status": "partial_error" if errors else "ok",
            "ticker": ticker,
            "items": payload.get("financials") or [],
            "docs": payload.get("docs") or [],
            "financials": payload.get("financials") or [],
            "latest_financial_snapshot": payload.get("latest_financial_snapshot") or {},
            "announcement_context": payload.get("announcement_context") or [],
            "extraction_failures": payload.get("extraction_failures") or [],
            "low_confidence_financials": payload.get("low_confidence_financials") or [],
            "errors": errors,
            "query": query,
            "intent": intent,
        }


def _extract_pdf_text(content_bytes: bytes) -> str:
    if not content_bytes.startswith(b"%PDF"):
        raise ValueError("uploaded file is not a PDF")
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:
        raise RuntimeError(f"PDF parser unavailable: {exc}") from exc

    document = None
    try:
        document = fitz.open(stream=content_bytes, filetype="pdf")
        chunks: list[str] = []
        total_chars = 0
        max_chars = 300_000
        for page in document:
            text = str(page.get_text("text") or "")
            text = re.sub(r"\s+\n", "\n", text)
            text = re.sub(r"[ \t]+", " ", text).strip()
            if not text:
                continue
            remaining = max_chars - total_chars
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining]
            chunks.append(text)
            total_chars += len(text)
        combined = "\n".join(chunks).strip()
        if not combined:
            raise ValueError("no extractable text found in PDF")
        return combined
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"failed to read PDF content: {exc}") from exc
    finally:
        if document is not None:
            try:
                document.close()
            except Exception:
                pass


def _decode_report_text(payload: ThesisAuditRequest) -> str:
    if payload.report_text and payload.report_text.strip():
        return payload.report_text.strip()

    content_base64 = str(payload.content_base64 or "").strip()
    if not content_base64:
        raise HTTPException(status_code=400, detail="report_text or content_base64 is required")
    if len(content_base64) > _MAX_BASE64_CHARS:
        raise HTTPException(status_code=413, detail="uploaded report is too large")
    try:
        content_bytes = base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid base64 content") from exc
    if len(content_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="uploaded report is too large")

    filename = Path(str(payload.filename or "").strip()).name
    suffix = Path(filename).suffix.lower()
    mime_type = str(payload.mime_type or "").strip().lower()
    is_pdf = suffix == ".pdf" or "pdf" in mime_type or content_bytes.startswith(b"%PDF")
    if is_pdf:
        try:
            return _extract_pdf_text(content_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        return content_bytes.decode("utf-8-sig", errors="replace").strip()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"could not decode report text: {exc}") from exc


def _build_service() -> ThesisAuditService:
    orchestrator = QueryOrchestrator(
        financial_truth_provider=_ContextFinancialTruthProvider(),
        company_memory_provider=CompanyMemoryStore(),
        market_memory_provider=MarketMemoryStore(),
        user_thesis_memory_provider=UserThesisMemoryStore(),
    )
    return ThesisAuditService(orchestrator=orchestrator)


@router.post("/thesis-audit")
def run_thesis_audit(payload: ThesisAuditRequest) -> dict[str, Any]:
    report_text = _decode_report_text(payload)
    try:
        report = ResearchReportInput(
            ticker=payload.ticker,
            report_text=report_text,
            filename=Path(str(payload.filename or "").strip()).name or None,
            focus=payload.focus,
        )
        audit = _build_service().audit(report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("thesis audit failed")
        raise HTTPException(status_code=500, detail=f"thesis audit failed: {str(exc)[:200]}") from exc
    return audit.to_dict()
