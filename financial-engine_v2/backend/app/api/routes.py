import base64
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.celery_app import celery
from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.models.documents import Document
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.models.extractions import ExtractionRun
from app.providers.universe import ASX20
from app.providers.market_price_provider import (
    MarketPriceProvider,
    MarketPriceProviderError,
)
from app.providers.openbb_sidecar_provider import (
    OpenBBSidecarProvider,
    OpenBBSidecarProviderError,
)
from app.services.analysis.risk_module import run_risk_analysis
from app.services.commentary_ingest import ingest_transcript
from app.services.openbb_staging import (
    persist_fundamental_snapshot,
    persist_price_snapshot,
)
from app.services.pipeline_service import PipelineJobSpec, run_pipeline_sync
from app.services.extraction_run_observability import initialize_run_status
from app.services.source_registry import ingest_book

router = APIRouter()


class TranscriptIngestRequest(BaseModel):
    filename: str
    text: str
    source_name: str
    source_type: str = "youtube_transcript"
    speaker: str
    published_at: str
    topic_tags: list[str] = Field(default_factory=list)
    credibility_weight: float | None = None
    decay_half_life_days: float | None = None


class BookIngestRequest(BaseModel):
    filename: str
    content_base64: str
    source_name: str
    source_type: str = "book"
    framework_family: str = ""
    credibility_weight: float | None = None
    time_decay_half_life_days: float | None = None
    review_status: str = "pending"


class ProcessDocumentRequest(BaseModel):
    method: str = "auto"
    strict_method: bool = False


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    configured_key = str(getattr(settings, "local_api_key", "") or "").strip()
    if not configured_key:
        return
    if x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _market_data_mode() -> str:
    value = str(getattr(settings, "market_data_mode", "yahoo") or "").strip().lower()
    return value if value in {"yahoo", "openbb_sidecar"} else "yahoo"


def _openbb_sidecar_provider() -> OpenBBSidecarProvider:
    return OpenBBSidecarProvider(
        base_url=getattr(settings, "openbb_sidecar_base_url", "http://localhost:8081"),
        timeout=getattr(settings, "openbb_sidecar_timeout_seconds", 20.0),
    )


def _staging_writes_enabled() -> bool:
    return bool(getattr(settings, "openbb_sidecar_enable_staging_writes", False))


def _persist_openbb_price_snapshot(
    *,
    ticker: str,
    exchange: str,
    payload: dict,
    range_: str,
    interval: str,
) -> None:
    if not _staging_writes_enabled():
        return
    db = SessionLocal()
    try:
        persist_price_snapshot(
            db,
            ticker=ticker,
            exchange=exchange,
            payload=payload,
            params={"range": range_, "interval": interval},
        )
    finally:
        db.close()


def _persist_openbb_fundamental_snapshot(
    *,
    ticker: str,
    exchange: str,
    dataset_type: str,
    payload: dict,
    params: dict,
    statement_type: str | None = None,
    period: str | None = None,
) -> None:
    if not _staging_writes_enabled():
        return
    db = SessionLocal()
    try:
        persist_fundamental_snapshot(
            db,
            ticker=ticker,
            exchange=exchange,
            dataset_type=dataset_type,
            payload=payload,
            params=params,
            statement_type=statement_type,
            period=period,
        )
    finally:
        db.close()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/ingest/transcript", dependencies=[Depends(require_api_key)])
def ingest_transcript_route(body: TranscriptIngestRequest):
    try:
        return ingest_transcript(
            transcript_text=body.text,
            source_name=body.source_name,
            source_type=body.source_type,
            speaker=body.speaker,
            published_at=body.published_at,
            topic_tags=body.topic_tags,
            credibility_weight=body.credibility_weight,
            decay_half_life_days=body.decay_half_life_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/ingest/book", dependencies=[Depends(require_api_key)])
def ingest_book_route(body: BookIngestRequest):
    try:
        content_bytes = base64.b64decode(body.content_base64, validate=True)
        return ingest_book(
            filename=body.filename,
            content_bytes=content_bytes,
            source_name=body.source_name,
            source_type=body.source_type,
            framework_family=body.framework_family,
            credibility_weight=body.credibility_weight,
            time_decay_half_life_days=body.time_decay_half_life_days,
            review_status=body.review_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/docs")
def docs(ticker: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Document)
        .filter(Document.ticker == ticker)
        .order_by(Document.published_at.desc().nullslast())
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


@router.get("/financials")
def financials(ticker: str, db: Session = Depends(get_db)):
    rows = (
        db.query(ASXPeriodicFinancial)
        .filter(ASXPeriodicFinancial.ticker == ticker)
        .order_by(ASXPeriodicFinancial.period_end.desc())
        .all()
    )

    def n(x):
        return str(x) if x is not None else None

    return [
        {
            "ticker": r.ticker,
            "period_end": r.period_end,
            "period_type": r.period_type,
            "revenue": n(r.revenue),
            "ebit": n(r.ebit),
            "np_attributable": n(r.np_attributable),
            "operating_cf": n(r.operating_cf),
            "investing_cf": n(r.investing_cf),
            "financing_cf": n(r.financing_cf),
            "capex": n(r.capex),
            "cash_end": n(r.cash_end),
            "net_debt": n(r.net_debt),
            "shares_outstanding": n(r.shares_outstanding),
            "confidence_metrics": r.confidence_metrics,
            "source_document_id": str(r.source_document_id),
        }
        for r in rows
    ]


@router.get("/risk")
def risk(document_id: str, db: Session = Depends(get_db)):
    r = db.query(ASXRiskNote).filter(ASXRiskNote.document_id == document_id).first()
    if not r:
        return {"document_id": document_id, "risk_summary": None, "risk_bullets": None}
    return {
        "document_id": str(r.document_id),
        "risk_summary": r.risk_summary,
        "risk_bullets": r.risk_bullets,
        "guidance_summary": r.guidance_summary,
        "material_changes": r.material_changes,
        "confidence_narrative": r.confidence_narrative,
    }


@router.get("/price")
def price(
    ticker: str,
    range_: str = Query("1mo", alias="range"),
    interval: str = Query("1d"),
    exchange: str = Query("ASX"),
):
    try:
        mode = _market_data_mode()
        if mode == "openbb_sidecar":
            try:
                payload = _openbb_sidecar_provider().fetch_price(
                    ticker=ticker,
                    exchange=exchange,
                    range_=range_,
                    interval=interval,
                )
                _persist_openbb_price_snapshot(
                    ticker=ticker,
                    exchange=exchange,
                    payload=payload,
                    range_=range_,
                    interval=interval,
                )
                return payload
            except OpenBBSidecarProviderError as sidecar_exc:
                logger.warning(
                    "openbb sidecar unavailable (%s), falling back to Yahoo Finance for %s",
                    sidecar_exc,
                    ticker,
                )

        provider = MarketPriceProvider(
            base_url=getattr(
                settings, "market_data_base_url", "https://query1.finance.yahoo.com"
            ),
            timeout=getattr(settings, "market_data_timeout_seconds", 20.0),
        )
        return provider.fetch(
            ticker=ticker, exchange=exchange, range_=range_, interval=interval
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (MarketPriceProviderError, OpenBBSidecarProviderError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/fundamentals/profile")
def fundamentals_profile(
    ticker: str,
    exchange: str = Query("ASX"),
):
    try:
        payload = _openbb_sidecar_provider().fetch_fundamentals_profile(
            ticker=ticker, exchange=exchange
        )
        _persist_openbb_fundamental_snapshot(
            ticker=ticker,
            exchange=exchange,
            dataset_type="profile",
            payload=payload,
            params={},
        )
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenBBSidecarProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/fundamentals/summary")
def fundamentals_summary(
    ticker: str,
    exchange: str = Query("ASX"),
):
    try:
        payload = _openbb_sidecar_provider().fetch_fundamentals_summary(
            ticker=ticker, exchange=exchange
        )
        _persist_openbb_fundamental_snapshot(
            ticker=ticker,
            exchange=exchange,
            dataset_type="summary",
            payload=payload,
            params={},
        )
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenBBSidecarProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/fundamentals/statements")
def fundamentals_statements(
    ticker: str,
    exchange: str = Query("ASX"),
    statement_type: str = Query("income"),
    period: str = Query("annual"),
    limit: int = Query(8, ge=1, le=40),
):
    try:
        payload = _openbb_sidecar_provider().fetch_fundamentals_statements(
            ticker=ticker,
            exchange=exchange,
            statement_type=statement_type,
            period=period,
            limit=limit,
        )
        _persist_openbb_fundamental_snapshot(
            ticker=ticker,
            exchange=exchange,
            dataset_type="statements",
            payload=payload,
            params={"limit": limit},
            statement_type=statement_type,
            period=period,
        )
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenBBSidecarProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/backfill/asx20", dependencies=[Depends(require_api_key)])
def backfill_asx20(years: int = 1, process_documents: bool = False):
    if settings.task_mode.lower() == "sync":
        results = [
            run_pipeline_sync(
                PipelineJobSpec(
                    ticker=t,
                    years=years,
                    process_documents=process_documents,
                    mode="sync",
                )
            )
            for t in ASX20
        ]
        return {"mode": "sync", "processed": len(results), "results": results}
    for t in ASX20:
        celery.send_task(
            "backfill_ticker",
            args=[t],
            kwargs={"years": years, "process_documents": process_documents},
            queue="ingest",
            routing_key="ingest",
        )
    return {"mode": "celery", "enqueued": len(ASX20), "tickers": ASX20}


@router.post("/backfill/ticker/{ticker}", dependencies=[Depends(require_api_key)])
def backfill_ticker(ticker: str, years: int = 1, process_documents: bool = False):
    if settings.task_mode.lower() == "sync":
        result = run_pipeline_sync(
            PipelineJobSpec(
                ticker=ticker.upper(),
                years=years,
                process_documents=process_documents,
                mode="sync",
            )
        )
        return {"mode": "sync", **result}
    celery.send_task(
        "backfill_ticker",
        args=[ticker.upper()],
        kwargs={"years": years, "process_documents": process_documents},
        queue="ingest",
        routing_key="ingest",
    )
    return {"mode": "celery", "enqueued": 1, "ticker": ticker.upper()}


@router.post("/process/document/{document_id}", dependencies=[Depends(require_api_key)])
def process_single_document(
    document_id: str,
    payload: ProcessDocumentRequest | None = None,
):
    """Trigger extraction (and embedding) for a single already-downloaded document.

    Useful for re-processing a document without re-running discovery or download.
    The pipeline skips re-extraction if a successful ExtractionRun already exists
    for the current EXTRACTOR_VERSION.
    """
    from app.services.pipeline import process_document

    requested_method = payload.method if payload is not None else "auto"
    strict_method = payload.strict_method if payload is not None else False
    run_id = str(uuid.uuid4())
    initialize_run_status(
        run_id=run_id,
        document_id=document_id,
        requested_method=requested_method,
        strict_method=strict_method,
        details={"trigger": "api_process_document"},
    )
    if settings.task_mode.lower() == "sync":
        result = process_document(
            document_id,
            run_id=run_id,
            requested_method=requested_method,
            strict_method=strict_method,
        )
        return {"mode": "sync", "document_id": document_id, **(result or {})}
    task = celery.send_task(
        "process_document",
        args=[{"document_id": document_id}, document_id],
        kwargs={
            "run_id": run_id,
            "requested_method": requested_method,
            "strict_method": strict_method,
        },
        queue="llm_gpu",
        routing_key="llm_gpu",
    )
    return {
        "mode": "celery",
        "enqueued": 1,
        "run_id": run_id,
        "task_id": str(getattr(task, "id", "") or "") or None,
        "document_id": document_id,
        "requested_method": requested_method,
        "strict_method": strict_method,
    }


@router.post("/process/ticker/{ticker}", dependencies=[Depends(require_api_key)])
def process_unextracted_for_ticker(ticker: str, limit: int = Query(default=50, le=500)):
    """Process all downloaded-but-unextracted documents for a ticker.

    Identifies documents where pdf_sha256 is populated but no ExtractionRun exists,
    and triggers process_document for each. Useful to recover from the state where
    backfill ran without process_documents=true.
    """
    from app.services.pipeline import process_document

    db = SessionLocal()
    try:
        extracted_doc_ids = db.query(ExtractionRun.document_id)
        unextracted = (
            db.query(Document)
            .filter(
                Document.ticker == ticker.upper(),
                Document.pdf_sha256 != "",
                ~Document.document_id.in_(extracted_doc_ids),
            )
            .limit(limit)
            .all()
        )
        if not unextracted:
            return {
                "ticker": ticker.upper(),
                "queued": 0,
                "message": "no unextracted documents found",
            }

        if settings.task_mode.lower() == "sync":
            results = []
            for doc in unextracted:
                r = process_document(str(doc.document_id))
                results.append({"document_id": str(doc.document_id), **(r or {})})
            return {
                "mode": "sync",
                "ticker": ticker.upper(),
                "queued": len(results),
                "results": results,
            }

        for doc in unextracted:
            celery.send_task(
                "process_document",
                args=[{"document_id": str(doc.document_id)}, str(doc.document_id)],
                queue="llm_gpu",
                routing_key="llm_gpu",
            )
        return {"mode": "celery", "ticker": ticker.upper(), "queued": len(unextracted)}
    finally:
        db.close()


# GET /api/rag/query REMOVED — migrated to POST /rag/query with source="news".
# All callers (cockpit BackendApiClient, tools.py, qual_context.py) now use
# the unified POST /rag/query endpoint. Logic moved to app.services.rag.query_news_chunks().


@router.get("/analysis/risk", dependencies=[Depends(require_api_key)])
def analysis_risk(
    ticker: str,
    include_news: bool = Query(default=True),
    rag_top_k: int = Query(default=6, ge=1, le=20),
    news_top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Structured risk report for a ticker.

    Aggregates extracted risk notes from Postgres, supporting evidence from
    RAG (asx_docs), and optionally recent news context. Deterministic —
    no LLM calls. Read-only.
    """
    try:
        return run_risk_analysis(
            ticker,
            db,
            include_news=include_news,
            rag_top_k=rag_top_k,
            news_top_k=news_top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
