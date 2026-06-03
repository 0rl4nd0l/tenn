from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from celery import Celery
from app.api.security import require_api_key
from app.core.config import settings
from app.core.db import get_db
from app.models.documents import Document
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.providers.universe import ASX20
from app.providers.market_price_provider import MarketPriceProvider, MarketPriceProviderError
from app.services.pipeline_service import PipelineJobSpec, run_pipeline_sync

router = APIRouter()
celery = Celery("fe_api", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery.conf.task_default_queue = "default"
celery.conf.task_default_exchange = "default"
celery.conf.task_default_routing_key = "default"

TickerPath = Path(..., pattern=r"^[A-Z0-9]{2,6}$")
TickerQuery = Query(..., pattern=r"^[A-Za-z0-9]{2,6}$")
YearsQuery = Query(1, ge=1, le=10)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/docs")
def docs(
    ticker: str = TickerQuery,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    ticker = ticker.upper()
    rows = db.query(Document).filter(Document.ticker == ticker).order_by(Document.published_at.desc().nullslast()).all()
    return [
        {
            "document_id": str(r.document_id),
            "ticker": r.ticker,
            "doc_class": r.doc_class,
            "doc_subtype": r.doc_subtype,
            "published_at": r.published_at,
            "title": r.title,
            "source_url": r.source_url,
            "has_pdf": bool(r.pdf_sha256),
            "download_status": getattr(r, "download_status", None) or ("downloaded" if r.pdf_sha256 else "pending"),
            "download_error_code": getattr(r, "download_error_code", None),
        }
        for r in rows
    ]


@router.get("/financials")
def financials(
    ticker: str = TickerQuery,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    ticker = ticker.upper()
    rows = db.query(ASXPeriodicFinancial).filter(ASXPeriodicFinancial.ticker == ticker).order_by(ASXPeriodicFinancial.period_end.desc()).all()

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
            "metric_provenance": getattr(r, "metric_provenance", None),
            "source_document_id": str(r.source_document_id),
        }
        for r in rows
    ]


@router.get("/risk")
def risk(
    document_id: str = Query(..., min_length=1, max_length=80),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
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
    ticker: str = TickerQuery,
    range_: str = Query("1mo", alias="range", pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query("1d", pattern=r"^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$"),
    exchange: str = Query("ASX", pattern=r"^[A-Z]{2,8}$"),
    _: None = Depends(require_api_key),
):
    provider = MarketPriceProvider(
        base_url=getattr(settings, "market_data_base_url", "https://query1.finance.yahoo.com"),
        timeout=getattr(settings, "market_data_timeout_seconds", 20.0),
    )
    try:
        return provider.fetch(ticker=ticker.upper(), exchange=exchange, range_=range_, interval=interval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MarketPriceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/backfill/asx20")
def backfill_asx20(
    years: int = YearsQuery,
    process_documents: bool = False,
    _: None = Depends(require_api_key),
):
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
            args=[t, years, process_documents],
            queue="default",
            routing_key="default",
        )
    return {"mode": "celery", "enqueued": len(ASX20), "tickers": ASX20, "years": years, "process_documents": process_documents}


@router.post("/backfill/ticker/{ticker}")
def backfill_ticker(
    ticker: str = TickerPath,
    years: int = YearsQuery,
    process_documents: bool = False,
    _: None = Depends(require_api_key),
):
    ticker = ticker.upper()
    if settings.task_mode.lower() == "sync":
        result = run_pipeline_sync(
            PipelineJobSpec(
                ticker=ticker,
                years=years,
                process_documents=process_documents,
                mode="sync",
            )
        )
        return {"mode": "sync", **result}
    celery.send_task(
        "backfill_ticker",
        args=[ticker, years, process_documents],
        queue="default",
        routing_key="default",
    )
    return {"mode": "celery", "enqueued": 1, "ticker": ticker, "years": years, "process_documents": process_documents}
