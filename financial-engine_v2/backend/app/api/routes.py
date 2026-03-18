from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from celery import Celery
from app.core.config import settings
from app.core.db import get_db
from app.models.documents import Document
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.providers.universe import ASX20
from app.providers.market_price_provider import MarketPriceProvider, MarketPriceProviderError
from app.services.pipeline import backfill_ticker_sync
from app.services.news_intelligence import (
    build_news_intelligence_for_ticker,
    get_company_news,
    get_company_narratives,
    get_company_news_snapshot,
    get_company_sentiment,
    semantic_news_search,
)

router=APIRouter()
celery=Celery("fe_api", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery.conf.task_default_queue = "default"
celery.conf.task_default_exchange = "default"
celery.conf.task_default_routing_key = "default"

@router.get("/health")
def health(): return {"status":"ok"}

@router.get("/docs")
def docs(ticker:str, db:Session=Depends(get_db)):
    rows=db.query(Document).filter(Document.ticker==ticker).order_by(Document.published_at.desc().nullslast()).all()
    return [{"document_id":str(r.document_id),"ticker":r.ticker,"doc_class":r.doc_class,"doc_subtype":r.doc_subtype,
             "published_at":r.published_at,"title":r.title,"source_url":r.source_url,"pdf_path":r.pdf_path} for r in rows]

@router.get("/financials")
def financials(ticker:str, db:Session=Depends(get_db)):
    rows=db.query(ASXPeriodicFinancial).filter(ASXPeriodicFinancial.ticker==ticker).order_by(ASXPeriodicFinancial.period_end.desc()).all()
    def n(x): return str(x) if x is not None else None
    return [{"ticker":r.ticker,"period_end":r.period_end,"period_type":r.period_type,"revenue":n(r.revenue),"ebit":n(r.ebit),
             "np_attributable":n(r.np_attributable),"operating_cf":n(r.operating_cf),"investing_cf":n(r.investing_cf),
             "financing_cf":n(r.financing_cf),"capex":n(r.capex),"cash_end":n(r.cash_end),"net_debt":n(r.net_debt),
             "shares_outstanding":n(r.shares_outstanding),"confidence_metrics":r.confidence_metrics,"source_document_id":str(r.source_document_id)} for r in rows]

@router.get("/risk")
def risk(document_id:str, db:Session=Depends(get_db)):
    r=db.query(ASXRiskNote).filter(ASXRiskNote.document_id==document_id).first()
    if not r: return {"document_id":document_id,"risk_summary":None,"risk_bullets":None}
    return {"document_id":str(r.document_id),"risk_summary":r.risk_summary,"risk_bullets":r.risk_bullets,
            "guidance_summary":r.guidance_summary,"material_changes":r.material_changes,"confidence_narrative":r.confidence_narrative}

@router.get("/price")
def price(
    ticker:str,
    range_:str=Query("1mo", alias="range"),
    interval:str=Query("1d"),
    exchange:str=Query("ASX"),
):
    provider=MarketPriceProvider(
        base_url=getattr(settings, "market_data_base_url", "https://query1.finance.yahoo.com"),
        timeout=getattr(settings, "market_data_timeout_seconds", 20.0),
    )
    try:
        return provider.fetch(ticker=ticker, exchange=exchange, range_=range_, interval=interval)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MarketPriceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.post("/backfill/asx20")
def backfill_asx20(years:int=1, process_documents:bool=False):
    if settings.task_mode.lower()=="sync":
        results=[backfill_ticker_sync(t, years=years, process_documents=process_documents) for t in ASX20]
        return {"mode":"sync","processed":len(results),"results":results}
    for t in ASX20:
        celery.send_task("backfill_ticker", args=[t], queue="default", routing_key="default")
    return {"mode":"celery","enqueued":len(ASX20),"tickers":ASX20}

@router.post("/backfill/ticker/{ticker}")
def backfill_ticker(ticker:str, years:int=1, process_documents:bool=False):
    if settings.task_mode.lower()=="sync":
        result=backfill_ticker_sync(ticker.upper(), years=years, process_documents=process_documents)
        return {"mode":"sync", **result}
    celery.send_task("backfill_ticker", args=[ticker.upper()], queue="default", routing_key="default")
    return {"mode":"celery","enqueued":1,"ticker":ticker.upper()}


@router.post("/news/rebuild/{ticker}")
def rebuild_news_intelligence(
    ticker: str,
    run_mode: str = Query("incremental", pattern="^(incremental|backfill)$"),
    db: Session = Depends(get_db),
):
    return build_news_intelligence_for_ticker(db, ticker.upper(), run_mode=run_mode)


@router.get("/news/company/{ticker}")
def company_news(
    ticker: str,
    window: str = Query("30d"),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return get_company_news(db, ticker.upper(), window=window, limit=limit)


@router.get("/news/sentiment/{ticker}")
def company_sentiment(
    ticker: str,
    window: str = Query("30d"),
    db: Session = Depends(get_db),
):
    return get_company_sentiment(db, ticker.upper(), window=window)


@router.get("/news/narratives/{ticker}")
def company_narratives(
    ticker: str,
    window: str = Query("30d"),
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return get_company_narratives(db, ticker.upper(), window=window, limit=limit)


@router.get("/news/snapshot/{ticker}")
def company_news_snapshot(ticker: str, db: Session = Depends(get_db)):
    return get_company_news_snapshot(db, ticker.upper())


@router.get("/news/semantic-search")
def company_semantic_news_search(
    query: str,
    ticker: str | None = None,
    record_type: str | None = None,
    top_k: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
):
    filters = {"ticker": ticker, "record_type": record_type}
    return semantic_news_search(db, query=query, filters=filters, top_k=top_k)
