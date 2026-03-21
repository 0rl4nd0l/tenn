import os, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx
from celery import chain
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
sys.path.append('/app_backend')

from app.core.config import settings
from app.providers.asx_provider import ASXProvider
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.services.storage import write_bytes, sha256_file, ensure_dir
from app.services.structured_chunking import chunk_prose_sections
from app.services.docling_extract import StructuredDocument
from app.services.embeddings import ensure_collection, upsert_points
from app.services.multipass_extraction import run_multipass_extraction, parse_period_end, EXTRACTOR_VERSION
from app.services.llamacpp_runtime import resolve_embedding_runtime_config
from app.services.llamacpp_embeddings import llamacpp_embed
from qdrant_client import QdrantClient
from app.celery_app import celery

DATABASE_URL=os.environ['DATABASE_URL']
DOCS_ROOT=os.environ.get('DOCS_ROOT','/data/asx/docs')
QDRANT_URL=os.environ.get('QDRANT_URL','http://qdrant:6333')
QDRANT_COLLECTION=os.environ.get('QDRANT_COLLECTION','asx_docs')
LLM_URL=os.environ.get('LLM_URL', os.environ.get('LLAMACPP_URL', settings.llamacpp_url))
EMBEDDING_URL=os.environ.get('EMBEDDING_URL', LLM_URL)
EMBED_MODEL=os.environ.get('EMBED_MODEL', settings.embed_model)
EXTRACT_MODEL=os.environ.get('EXTRACT_MODEL', settings.extract_model)

engine=create_engine(DATABASE_URL, pool_pre_ping=True)
Session=sessionmaker(bind=engine)

def _doc_path(ticker:str, doc_id:str)->str:
    d=Path(DOCS_ROOT)/ticker.upper()
    ensure_dir(str(d))
    return str(d/f"{doc_id}.pdf")

@celery.task(name='backfill_ticker')
def backfill_ticker(ticker:str, years:int=5):
    ticker=ticker.upper()
    provider=ASXProvider()
    end=datetime.now(timezone.utc)
    start=end-timedelta(days=365*years)
    found=provider.discover(ticker, start, end)

    db=Session()
    try:
        inserted=0
        for d in found:
            if db.query(Document).filter(Document.source_url==d.source_url).first():
                continue
            doc_id=uuid.uuid4()
            row=Document(document_id=doc_id,ticker=ticker,exchange='ASX',doc_class=d.doc_class,doc_subtype=d.doc_subtype,
                         published_at=d.published_at,period_end=d.period_end,title=d.title,source_url=d.source_url,
                         pdf_path=_doc_path(ticker,str(doc_id)),pdf_sha256='')
            db.add(row)
            inserted += 1
        db.commit()
        new_docs=db.query(Document).filter(Document.ticker==ticker, Document.pdf_sha256=='').all()
        for r in new_docs:
            chain(download_pdf.s(str(r.document_id)), process_document.s()).apply_async()
        return {"ticker":ticker,"found":len(found),"inserted":inserted,"enqueued":len(new_docs)}
    finally:
        db.close()

@celery.task(name='download_pdf')
def download_pdf(document_id:str):
    db=Session()
    try:
        doc=db.query(Document).filter(Document.document_id==document_id).first()
        if not doc: return {"error":"not found","document_id":document_id}
        r=httpx.get(doc.source_url, timeout=90.0, follow_redirects=True, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        write_bytes(doc.pdf_path, r.content)
        doc.pdf_sha256=sha256_file(doc.pdf_path)
        db.commit()
        return {"document_id":document_id}
    finally:
        db.close()

@celery.task(name='process_document')
def process_document(prev, document_id:str=None):
    if isinstance(prev, dict) and document_id is None:
        document_id=prev.get("document_id")
    if not document_id:
        return {"error":"missing document_id"}
    db=Session()
    q=QdrantClient(url=QDRANT_URL)
    try:
        doc=db.query(Document).filter(Document.document_id==document_id).first()
        if not doc: return {"error":"not found","document_id":document_id}
        existing_run=db.query(ExtractionRun).filter(
            ExtractionRun.document_id==doc.document_id,
            ExtractionRun.extractor_version==EXTRACTOR_VERSION,
            ExtractionRun.status=="ok",
        ).first()
        if existing_run:
            return {"ok":True,"document_id":document_id,"skipped":True,"reason":"already_extracted"}
        status = "ok"
        err = None
        structured = None
        conf = None
        chunks: list[str] = []
        try:
            doc_metadata={
                "document_id": str(doc.document_id),
                "ticker": str(doc.ticker or ""),
                "title": str(doc.title or ""),
            }
            multipass_result=run_multipass_extraction(doc.pdf_path, doc_metadata, None)
            chunks=chunk_prose_sections(StructuredDocument(sections=multipass_result.sections))
            status=multipass_result.status
            err=multipass_result.error
            structured=multipass_result.payload
            conf=float(structured.get("confidence_metrics") or 0.0)
        except Exception as e:
            status = "failed"
            err = str(e)
            structured = {"error": err}

        if chunks:
            embedding_base_url, embedding_model = resolve_embedding_runtime_config(
                base_url=EMBEDDING_URL,
                model=EMBED_MODEL,
            )
            batch_size=settings.embedding_batch_size
            vecs: list[list[float]] = []
            for batch_start in range(0, len(chunks), batch_size):
                batch=chunks[batch_start:batch_start + batch_size]
                vecs.extend(llamacpp_embed(embedding_base_url, embedding_model, batch))
            dim=len(vecs[0])
            ensure_collection(q, QDRANT_COLLECTION, dim)
            points=[{"id":str(uuid.uuid4()),"vector":v,"payload":{"document_id":str(doc.document_id),"ticker":doc.ticker,"doc_class":doc.doc_class,"doc_subtype":doc.doc_subtype,"chunk_index":i,"title":doc.title}} for i,(v,chunk) in enumerate(zip(vecs,chunks))]
            upsert_points(q, QDRANT_COLLECTION, points)

        run=ExtractionRun(document_id=doc.document_id, extractor_version=EXTRACTOR_VERSION, model_name=EXTRACT_MODEL, prompt_hash="v1",
                          status=status, confidence_overall=conf, error=err, structured_json=structured)
        db.add(run)
        db.commit()

        if status=="ok":
            ptype=structured.get("period_type")
            pend=parse_period_end(structured.get("period_end"))
            metrics=structured.get("metrics") or {}
            if ptype in ("Q","H","A") and pend:
                row=db.query(ASXPeriodicFinancial).filter(ASXPeriodicFinancial.ticker==doc.ticker, ASXPeriodicFinancial.period_end==pend, ASXPeriodicFinancial.period_type==ptype).first()
                if not row:
                    row=ASXPeriodicFinancial(ticker=doc.ticker, period_end=pend, period_type=ptype, source_document_id=doc.document_id)
                    db.add(row)
                for f in ["revenue","ebit","np_attributable","operating_cf","investing_cf","financing_cf","capex","cash_end","net_debt","shares_outstanding"]:
                    setattr(row, f, metrics.get(f, None))
                row.source_document_id=doc.document_id
                row.confidence_metrics=float(structured.get("confidence_metrics") or 0.0)
                db.commit()

            rn=db.query(ASXRiskNote).filter(ASXRiskNote.document_id==doc.document_id).first()
            if not rn:
                rn=ASXRiskNote(document_id=doc.document_id)
                db.add(rn)
            rn.risk_summary=structured.get("risk_summary")
            rn.risk_bullets=structured.get("risk_bullets")
            rn.guidance_summary=structured.get("guidance_summary")
            rn.material_changes=structured.get("material_changes")
            rn.confidence_narrative=float(structured.get("confidence_narrative") or 0.0)
            db.commit()

        return {"ok":True,"document_id":document_id,"chunks":len(chunks),"extraction_status":status}
    finally:
        db.close()
