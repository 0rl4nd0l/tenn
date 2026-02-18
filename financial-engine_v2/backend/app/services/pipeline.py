import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.providers.asx_provider import ASXProvider
from app.providers.marketindex_provider import MarketIndexProvider
from app.services.chunking import simple_chunk
from app.services.embeddings import ensure_collection, upsert_points
from app.services.extraction import EXTRACTOR_VERSION, build_prompt, parse_period_end
from app.services.ollama import ollama_embed, ollama_generate_json
from app.services.announcement_importance import classify_documents_and_materialize
from app.services.storage import ensure_dir, sha256_file, write_bytes
from app.services.text_extract import extract_text_from_pdf


def _extract_pdf_url_from_html(html_text, page_url):
    if not html_text:
        return None

    direct = re.search(r"https://announcements\.asx\.com\.au/asxpdf/[^\s\"'<>]+\.pdf", html_text, flags=re.I)
    if direct:
        return direct.group(0)

    soup = BeautifulSoup(html_text, "lxml")
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if href and ".pdf" in href.lower():
            return urljoin(page_url, href)
    return None


def _is_marketindex_url(url):
    text = (url or "").lower()
    return "marketindex.com.au" in text


def _download_bytes(url):
    response = httpx.get(
        url,
        timeout=90.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    return response


def _coerce_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _slugify_filename_component(value, max_length=96):
    """Build a filesystem-safe, readable filename token from announcement title."""
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "announcement"
    return text[:max_length].strip("-") or "announcement"


def _doc_date_component(published_at):
    if not published_at:
        return "undated"
    if isinstance(published_at, datetime):
        return published_at.strftime("%Y-%m-%d")
    return "undated"


def _doc_path(ticker, doc_id, published_at=None, title=None):
    directory = Path(settings.docs_root) / ticker.upper()
    ensure_dir(str(directory))
    date_component = _doc_date_component(published_at)
    title_component = _slugify_filename_component(title)
    filename = f"{date_component}_{title_component}_{doc_id}.pdf"
    return str(directory / filename)


def _canonical_doc_pdf_path(doc):
    return _doc_path(
        ticker=doc.ticker,
        doc_id=str(doc.document_id),
        published_at=doc.published_at,
        title=doc.title,
    )


def _ensure_document_pdf_path(doc):
    """Keep document path on canonical readable filename for first-write correctness."""
    canonical = _canonical_doc_pdf_path(doc)
    if doc.pdf_path == canonical:
        return canonical

    current_path = Path(doc.pdf_path) if doc.pdf_path else None
    canonical_path = Path(canonical)
    ensure_dir(str(canonical_path.parent))

    # If an old-name file exists but canonical doesn't, move it so DB and disk align.
    if current_path and current_path.exists() and current_path != canonical_path and not canonical_path.exists():
        current_path.rename(canonical_path)

    doc.pdf_path = canonical
    return canonical


def insert_discovered_documents(db, discovered_docs):
    inserted = 0
    new_document_ids = []
    per_ticker_found: dict[str, int] = {}
    per_ticker_inserted: dict[str, int] = {}

    for discovered_doc in discovered_docs:
        ticker = (discovered_doc.ticker or "").upper().strip()
        if not ticker:
            continue
        per_ticker_found[ticker] = per_ticker_found.get(ticker, 0) + 1

        existing = db.query(Document).filter(Document.source_url == discovered_doc.source_url).first()
        if existing:
            continue

        doc_id = uuid.uuid4()
        row = Document(
            document_id=doc_id,
            ticker=ticker,
            exchange=discovered_doc.exchange or "ASX",
            doc_class=discovered_doc.doc_class,
            doc_subtype=discovered_doc.doc_subtype,
            published_at=discovered_doc.published_at,
            period_end=discovered_doc.period_end,
            title=discovered_doc.title,
            source_url=discovered_doc.source_url,
            pdf_path=_doc_path(
                ticker=ticker,
                doc_id=str(doc_id),
                published_at=discovered_doc.published_at,
                title=discovered_doc.title,
            ),
            pdf_sha256="",
        )
        db.add(row)
        inserted += 1
        new_document_ids.append(str(doc_id))
        per_ticker_inserted[ticker] = per_ticker_inserted.get(ticker, 0) + 1

    db.commit()
    return {
        "found": len(discovered_docs),
        "inserted": inserted,
        "new_document_ids": new_document_ids,
        "found_by_ticker": per_ticker_found,
        "inserted_by_ticker": per_ticker_inserted,
    }


def discover_and_insert_documents(db, ticker, years=5):
    ticker = ticker.upper()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * years)
    discovered = ASXProvider().discover(ticker, start, end)
    if settings.enable_marketindex_fallback:
        marketindex_docs = MarketIndexProvider(settings.marketindex_announcements_file).discover(ticker, start, end)
        discovered_by_url = {item.source_url: item for item in discovered}
        for item in marketindex_docs:
            if item.source_url not in discovered_by_url:
                discovered.append(item)

    inserted_payload = insert_discovered_documents(db, discovered)
    return {
        "ticker": ticker,
        "found": len(discovered),
        "inserted": inserted_payload["inserted"],
        "new_document_ids": inserted_payload["new_document_ids"],
    }


def download_pdf_for_document(db, document_id):
    doc_uuid = _coerce_uuid(document_id)
    doc = db.query(Document).filter(Document.document_id == doc_uuid).first()
    if not doc:
        raise ValueError(f"Document not found: {document_id}")

    if _is_marketindex_url(doc.source_url):
        raise RuntimeError(
            "marketindex_headed_required: MarketIndex URLs must be fetched via headed browser session."
        )

    # Always normalize to canonical readable path before writing.
    _ensure_document_pdf_path(doc)

    response = _download_bytes(doc.source_url)
    content = response.content
    if not content.startswith(b"%PDF"):
        resolved_pdf_url = _extract_pdf_url_from_html(response.text, doc.source_url)
        if resolved_pdf_url:
            fallback_response = _download_bytes(resolved_pdf_url)
            if fallback_response.content.startswith(b"%PDF"):
                content = fallback_response.content

    if not content.startswith(b"%PDF"):
        raise ValueError(f"Downloaded content is not a PDF for document {document_id}")

    write_bytes(doc.pdf_path, content)
    doc.pdf_sha256 = sha256_file(doc.pdf_path)
    db.commit()

    return {"document_id": str(doc.document_id), "bytes": len(content)}


def _upsert_financial_rows(db, doc, structured):
    period_type = structured.get("period_type")
    period_end = parse_period_end(structured.get("period_end"))
    metrics = structured.get("metrics") or {}

    if period_type in ("Q", "H", "A") and period_end:
        row = (
            db.query(ASXPeriodicFinancial)
            .filter(
                ASXPeriodicFinancial.ticker == doc.ticker,
                ASXPeriodicFinancial.period_end == period_end,
                ASXPeriodicFinancial.period_type == period_type,
            )
            .first()
        )
        if not row:
            row = ASXPeriodicFinancial(
                ticker=doc.ticker,
                period_end=period_end,
                period_type=period_type,
                source_document_id=doc.document_id,
            )
            db.add(row)

        for field in [
            "revenue",
            "ebit",
            "np_attributable",
            "operating_cf",
            "investing_cf",
            "financing_cf",
            "capex",
            "cash_end",
            "net_debt",
            "shares_outstanding",
        ]:
            setattr(row, field, metrics.get(field, None))
        row.source_document_id = doc.document_id
        row.confidence_metrics = float(structured.get("confidence_metrics") or 0.0)

    risk_note = db.query(ASXRiskNote).filter(ASXRiskNote.document_id == doc.document_id).first()
    if not risk_note:
        risk_note = ASXRiskNote(document_id=doc.document_id)
        db.add(risk_note)

    risk_note.risk_summary = structured.get("risk_summary")
    risk_note.risk_bullets = structured.get("risk_bullets")
    risk_note.guidance_summary = structured.get("guidance_summary")
    risk_note.material_changes = structured.get("material_changes")
    risk_note.confidence_narrative = float(structured.get("confidence_narrative") or 0.0)
    db.commit()


def process_document(document_id):
    db = SessionLocal()
    try:
        doc_uuid = _coerce_uuid(document_id)
        doc = db.query(Document).filter(Document.document_id == doc_uuid).first()
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        text = extract_text_from_pdf(doc.pdf_path)
        chunks = simple_chunk(text, max_chars=4500)

        if settings.enable_embeddings and chunks:
            vectors = ollama_embed(settings.ollama_url, settings.embed_model, chunks)
            if settings.enable_qdrant:
                client = QdrantClient(url=settings.qdrant_url)
                vector_dimension = len(vectors[0])
                ensure_collection(client, settings.qdrant_collection, vector_dimension)
                points = []
                for index, vector in enumerate(vectors):
                    points.append(
                        {
                            "id": str(uuid.uuid4()),
                            "vector": vector,
                            "payload": {
                                "document_id": str(doc.document_id),
                                "ticker": doc.ticker,
                                "doc_class": doc.doc_class,
                                "doc_subtype": doc.doc_subtype,
                                "chunk_index": index,
                                "title": doc.title,
                            },
                        }
                    )
                upsert_points(client, settings.qdrant_collection, points)

        status = "skipped"
        error = None
        structured = {"status": "skipped_extraction"}
        confidence = None

        if settings.enable_extraction:
            try:
                structured = ollama_generate_json(
                    settings.ollama_url,
                    settings.extract_model,
                    build_prompt(text),
                )
                confidence = float(structured.get("confidence_metrics") or 0.0)
                status = "ok"
            except Exception as exc:
                status = "failed"
                error = str(exc)
                structured = {"error": error}

        run = ExtractionRun(
            document_id=doc.document_id,
            extractor_version=EXTRACTOR_VERSION,
            model_name=settings.extract_model,
            prompt_hash="v1",
            status=status,
            confidence_overall=confidence,
            error=error,
            structured_json=structured,
        )
        db.add(run)
        db.commit()

        if status == "ok":
            _upsert_financial_rows(db, doc, structured)

        return {"ok": True, "document_id": str(doc.document_id), "chunks": len(chunks), "extraction_status": status}
    finally:
        db.close()


def backfill_ticker_sync(ticker, years=5, process_documents=True):
    db = SessionLocal()
    try:
        discovery = discover_and_insert_documents(db, ticker=ticker, years=years)
        processed = 0
        skipped_download = 0
        errors = []

        for document_id in discovery["new_document_ids"]:
            try:
                download_pdf_for_document(db, document_id)
                if process_documents:
                    process_document(document_id)
                processed += 1
            except RuntimeError as exc:
                if "marketindex_headed_required" in str(exc):
                    doc = db.query(Document).filter(Document.document_id == _coerce_uuid(document_id)).first()
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
                    doc = db.query(Document).filter(Document.document_id == _coerce_uuid(document_id)).first()
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
            "skipped_download": skipped_download,
            "process_documents": process_documents,
            "importance_classification": importance_classification,
            "errors": errors,
            "error_count": len(errors),
        }
    finally:
        db.close()
