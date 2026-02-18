from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from celery import Celery
from app.core.config import settings
from app.core.db import get_db
from app.models.documents import Document
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.providers.universe import ASX20
from app.services.pipeline import backfill_ticker_sync

router=APIRouter()
celery=Celery("fe_api", broker=settings.celery_broker_url, backend=settings.celery_result_backend)

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

@router.post("/backfill/asx20")
def backfill_asx20(years:int=1, process_documents:bool=False):
    if settings.task_mode.lower()=="sync":
        results=[backfill_ticker_sync(t, years=years, process_documents=process_documents) for t in ASX20]
        return {"mode":"sync","processed":len(results),"results":results}
    for t in ASX20:
        celery.send_task("backfill_ticker", args=[t])
    return {"mode":"celery","enqueued":len(ASX20),"tickers":ASX20}

@router.post("/backfill/ticker/{ticker}")
def backfill_ticker(ticker:str, years:int=1, process_documents:bool=False):
    if settings.task_mode.lower()=="sync":
        result=backfill_ticker_sync(ticker.upper(), years=years, process_documents=process_documents)
        return {"mode":"sync", **result}
    celery.send_task("backfill_ticker", args=[ticker.upper()])
    return {"mode":"celery","enqueued":1,"ticker":ticker.upper()}
