import hashlib
import json
import logging
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any, Mapping, Optional

import concurrent.futures
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from sqlalchemy.exc import IntegrityError

from app.core.config import PROJECT_ROOT, settings
from app.core.db import SessionLocal
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.providers.marketindex_provider import MarketIndexProvider
from app.services.asx import ASXProvider
from app.services.embeddings import delete_points_for_document, ensure_collection, log_rejected_payload, upsert_points, validate_payload
from app.services.announcement_importance import classify_documents_and_materialize
from app.services.llm import embed_texts, generate_json, get_routing_decision
from app.services.multipass_extraction import run_multipass_extraction, EXTRACTOR_VERSION, PROMPT_HASH, parse_period_end
from app.services.structured_chunking import chunk_prose_sections
from app.services.docling_extract import StructuredDocument
from app.services.storage import ensure_dir, sha256_file, write_bytes


logger = logging.getLogger(__name__)

# Process-local in-memory embedding cache (key: SHA256(text), value: embedding vector).
# Only used when settings.enable_embedding_cache is True.
_embedding_cache: dict[str, list[float]] = {}
DOCUMENT_QUARANTINE_RULES_PATH = PROJECT_ROOT / "config" / "document_quarantine_rules.json"
_document_quarantine_rules_cache: Optional[list[dict[str, Any]]] = None
_document_quarantine_rules_cache_mtime: Optional[float] = None


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _load_document_quarantine_rules(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("failed to read document quarantine rules from %s: %s", path, exc)
        return []

    if isinstance(payload, dict):
        raw_rules = payload.get("rules")
    elif isinstance(payload, list):
        raw_rules = payload
    else:
        raw_rules = None

    if not isinstance(raw_rules, list):
        return []

    rules: list[dict[str, Any]] = []
    for raw in raw_rules:
        if not isinstance(raw, Mapping):
            continue
        ticker = str(raw.get("ticker", "")).strip().upper()
        reason = str(raw.get("reason", "")).strip() or "document_quarantine"
        terms: list[str] = []
        for key in (
            "match_substrings",
            "path_substrings",
            "title_substrings",
            "source_substrings",
            "substrings",
        ):
            terms.extend(_as_string_list(raw.get(key)))
        normalized = sorted({term.lower() for term in terms if term.strip()})
        if not normalized:
            continue
        rules.append(
            {
                "ticker": ticker,
                "reason": reason,
                "match_substrings": normalized,
            }
        )
    return rules


def _get_document_quarantine_rules() -> list[dict[str, Any]]:
    global _document_quarantine_rules_cache
    global _document_quarantine_rules_cache_mtime

    mtime: Optional[float] = None
    try:
        mtime = float(DOCUMENT_QUARANTINE_RULES_PATH.stat().st_mtime)
    except FileNotFoundError:
        mtime = None
    except Exception as exc:
        logger.warning("failed to stat document quarantine rules %s: %s", DOCUMENT_QUARANTINE_RULES_PATH, exc)
        mtime = None

    if _document_quarantine_rules_cache is None or _document_quarantine_rules_cache_mtime != mtime:
        _document_quarantine_rules_cache = _load_document_quarantine_rules(DOCUMENT_QUARANTINE_RULES_PATH)
        _document_quarantine_rules_cache_mtime = mtime
    return _document_quarantine_rules_cache


def _match_document_quarantine_reason(
    *,
    ticker: str,
    title: Any = "",
    source_url: Any = "",
    pdf_path: Any = "",
) -> str:
    rules = _get_document_quarantine_rules()
    if not rules:
        return ""

    ticker_upper = str(ticker or "").strip().upper()
    haystack = " ".join(
        part for part in (str(title or ""), str(source_url or ""), str(pdf_path or "")) if str(part).strip()
    ).lower()
    haystack_norm = haystack.replace("-", " ").replace("_", " ")

    for rule in rules:
        rule_ticker = str(rule.get("ticker", "")).strip().upper()
        if rule_ticker and ticker_upper and rule_ticker != ticker_upper:
            continue
        terms = rule.get("match_substrings")
        if not isinstance(terms, list):
            continue
        for term in terms:
            needle = str(term).strip().lower()
            if not needle:
                continue
            if needle in haystack or needle.replace("-", " ").replace("_", " ") in haystack_norm:
                return str(rule.get("reason", "")).strip() or "document_quarantine"
    return ""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _embed_texts_batched(
    texts: list[str],
    ollama_client: Optional[httpx.Client] = None,
) -> list[list[float]]:
    """Embed texts in batches of embedding_batch_size. Preserves order. Fail-fast on error."""
    if not texts:
        return []
    batch_size = max(1, settings.embedding_batch_size)
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        t0 = time.perf_counter()
        batch_vectors = embed_texts(
            batch,
            metadata={
                "task_type": "embedding",
                "component": "pipeline._embed_texts_batched",
                "text_count": len(batch),
            },
            client=ollama_client,
        )
        elapsed = time.perf_counter() - t0
        logger.debug(
            "embedding batch %d–%d (%d texts) in %.3fs",
            start,
            start + len(batch),
            len(batch),
            elapsed,
        )
        out.extend(list(v) for v in batch_vectors)
    return out


def _embed_chunks(
    chunks: list[str],
    ollama_client: Optional[httpx.Client] = None,
) -> list[list[float]]:
    """Compute embeddings for chunks, optionally using in-memory cache. Output order matches input."""
    if not chunks:
        return []
    if not settings.enable_embedding_cache:
        return _embed_texts_batched(chunks, ollama_client=ollama_client)
    keys = [_sha256_text(c) for c in chunks]
    misses = [i for i in range(len(chunks)) if keys[i] not in _embedding_cache]
    if misses:
        miss_texts = [chunks[i] for i in misses]
        new_vectors = _embed_texts_batched(miss_texts, ollama_client=ollama_client)
        for j, idx in enumerate(misses):
            _embedding_cache[keys[idx]] = list(new_vectors[j])
    return [_embedding_cache[keys[i]] for i in range(len(chunks))]


EXTRACTION_FAILURE_TAXONOMY = (
    "ocr_or_text_unavailable",
    "parser_timeout",
    "llm_invalid_json",
    "provider_network",
    "corrupted_pdf",
    "unknown",
)


def classify_extraction_failure(error_text: Any, structured_json: Mapping[str, Any] | None = None) -> str:
    text = str(error_text or "").strip().lower()
    structured = dict(structured_json or {})
    if not text and structured:
        text = json.dumps(structured, ensure_ascii=False).lower()
    if not text:
        return "unknown"

    if any(
        token in text
        for token in (
            "empty text",
            "no text",
            "text unavailable",
            "ocr",
            "unable to extract text",
            "could not extract text",
        )
    ):
        return "ocr_or_text_unavailable"

    if any(token in text for token in ("timeout", "timed out", "deadline exceeded", "took too long")):
        return "parser_timeout"

    if any(
        token in text
        for token in (
            "invalid json",
            "jsondecodeerror",
            "expecting value",
            "malformed json",
            "could not parse json",
            "json parse",
        )
    ):
        return "llm_invalid_json"

    if any(
        token in text
        for token in (
            "connection",
            "connecterror",
            "network",
            "name resolution",
            "dns",
            "refused",
            "temporarily unavailable",
            "httpx",
            "ssl",
        )
    ):
        return "provider_network"

    if any(
        token in text
        for token in (
            "not a pdf",
            "corrupt",
            "trailer not found",
            "eof marker",
            "pdfsyntaxerror",
            "cannot open pdf",
            "invalid pdf",
        )
    ):
        return "corrupted_pdf"

    return "unknown"


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


def _download_bytes(url, client: Optional[httpx.Client] = None):
    try:
        if client is not None:
            response = client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        else:
            response = httpx.get(
                url,
                timeout=90.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 407, 503):
            try:
                from scrapling.fetchers import Fetcher
                page = Fetcher.get(url, timeout=90.0)
                content = getattr(page, "content", None) or getattr(page, "body", None)
                if content is not None and isinstance(content, bytes):
                    class _ScraplingFallbackResponse:
                        pass
                    out = _ScraplingFallbackResponse()
                    out.content = content
                    out.text = content.decode("utf-8", errors="replace")
                    out.raise_for_status = lambda: None
                    return out
            except Exception:
                pass
        raise


def _coerce_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _coerce_float(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"none", "null", "na", "n/a", "nan", "unknown"}:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _coerce_text(value, *, join_lists: bool = False):
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        txt = value.strip()
        return txt or None
    if isinstance(value, list):
        parts = []
        for item in value:
            txt = _coerce_text(item)
            if txt:
                parts.append(txt)
        if not parts:
            return None
        if join_lists:
            return "\n".join(parts)
        return json.dumps(parts, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    txt = str(value).strip()
    return txt or None


def _coerce_risk_bullets(value):
    if value is None:
        return None
    if isinstance(value, list):
        out = []
        for item in value:
            txt = _coerce_text(item)
            if txt:
                out.append(txt)
        return out or None
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        if txt.startswith("[") and txt.endswith("]"):
            try:
                parsed = json.loads(txt)
                if isinstance(parsed, list):
                    return _coerce_risk_bullets(parsed)
            except Exception:
                pass
        bits = [p.strip(" -\t") for p in re.split(r"[;\n]+", txt) if p.strip(" -\t")]
        if len(bits) >= 2:
            return bits
        return [txt]
    as_text = _coerce_text(value)
    return [as_text] if as_text else None


def _resolve_pdf_path(value: str | None) -> str:
    """Resolve pdf_path to an absolute path. Relative paths are resolved under settings.docs_root so worker and API share the same layout."""
    raw = str(value or "").strip()
    if not raw:
        return raw
    path = Path(raw).expanduser()
    if path.is_absolute():
        return str(path)
    return str((Path(settings.docs_root) / path).resolve())


def _normalize_source_url(url: str | None) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    try:
        parts = urlsplit(text)
        scheme = (parts.scheme or "https").lower()
        netloc = parts.netloc.lower()
        path = re.sub(r"/{2,}", "/", parts.path or "")
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        query_items = parse_qsl(parts.query, keep_blank_values=True)
        query = urlencode(sorted(query_items))
        return urlunsplit((scheme, netloc, path, query, ""))
    except Exception:
        return text


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
    duplicate_in_batch = 0
    duplicate_existing = 0
    skipped_missing_source_url = 0
    prepared = []
    seen_source_urls: set[str] = set()

    for discovered_doc in discovered_docs:
        ticker = (discovered_doc.ticker or "").upper().strip()
        if not ticker:
            logger.warning(
                "ASX skip",
                extra={
                    "reason": "invalid_structure",
                    "data": {"missing": "ticker", "discovered_doc": str(discovered_doc)},
                },
            )
            continue
        per_ticker_found[ticker] = per_ticker_found.get(ticker, 0) + 1

        source_url = _normalize_source_url(discovered_doc.source_url)
        if not source_url:
            skipped_missing_source_url += 1
            logger.warning(
                "ASX skip",
                extra={
                    "reason": "missing_source_url",
                    "data": {
                        "ticker": ticker,
                        "title": str(getattr(discovered_doc, "title", "") or "")[:200],
                        "source_url": str(getattr(discovered_doc, "source_url", "") or "")[:500],
                    },
                },
            )
            continue
        if source_url in seen_source_urls:
            duplicate_in_batch += 1
            logger.warning(
                "ASX skip",
                extra={
                    "reason": "duplicate",
                    "data": {"ticker": ticker, "source_url": source_url, "scope": "batch"},
                },
            )
            continue
        seen_source_urls.add(source_url)
        prepared.append((discovered_doc, ticker, source_url))

    source_urls = [row[2] for row in prepared]
    existing_source_urls: set[str] = set()
    if source_urls:
        existing_rows = db.query(Document.source_url).filter(Document.source_url.in_(source_urls)).all()
        existing_source_urls = {str(row[0]) for row in existing_rows if row and row[0]}

    for discovered_doc, ticker, source_url in prepared:
        if source_url in existing_source_urls:
            duplicate_existing += 1
            logger.warning(
                "ASX skip",
                extra={
                    "reason": "duplicate",
                    "data": {"ticker": ticker, "source_url": source_url, "scope": "db"},
                },
            )
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
            source_url=source_url,
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

    try:
        db.commit()
    except IntegrityError:
        # Race-safe fallback: if another worker inserted same source_url first, continue without aborting batch.
        db.rollback()
        inserted = 0
        new_document_ids = []
        per_ticker_inserted = {}
        duplicate_existing = 0
        for discovered_doc, ticker, source_url in prepared:
            exists = db.query(Document.document_id).filter(Document.source_url == source_url).first()
            if exists:
                duplicate_existing += 1
                logger.warning(
                    "ASX skip",
                    extra={
                        "reason": "duplicate",
                        "data": {"ticker": ticker, "source_url": source_url, "scope": "db_race"},
                    },
                )
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
                source_url=source_url,
                pdf_path=_doc_path(
                    ticker=ticker,
                    doc_id=str(doc_id),
                    published_at=discovered_doc.published_at,
                    title=discovered_doc.title,
                ),
                pdf_sha256="",
            )
            db.add(row)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                duplicate_existing += 1
                logger.warning(
                    "ASX skip",
                    extra={
                        "reason": "duplicate",
                        "data": {"ticker": ticker, "source_url": source_url, "scope": "db_commit"},
                    },
                )
                continue
            inserted += 1
            new_document_ids.append(str(doc_id))
            per_ticker_inserted[ticker] = per_ticker_inserted.get(ticker, 0) + 1

    return {
        "found": len(discovered_docs),
        "inserted": inserted,
        "new_document_ids": new_document_ids,
        "found_by_ticker": per_ticker_found,
        "inserted_by_ticker": per_ticker_inserted,
        "duplicate_in_batch": duplicate_in_batch,
        "duplicate_existing": duplicate_existing,
        "skipped_missing_source_url": skipped_missing_source_url,
    }


def _load_discovered_document_ids(db, discovered_docs) -> list[str]:
    source_urls: list[str] = []
    seen_source_urls: set[str] = set()
    for discovered_doc in discovered_docs:
        source_url = _normalize_source_url(getattr(discovered_doc, "source_url", None))
        if not source_url or source_url in seen_source_urls:
            continue
        seen_source_urls.add(source_url)
        source_urls.append(source_url)

    if not source_urls:
        return []

    rows = (
        db.query(Document.document_id, Document.source_url)
        .filter(Document.source_url.in_(source_urls))
        .all()
    )
    document_id_by_source_url = {
        str(source_url): str(document_id)
        for document_id, source_url in rows
        if document_id and source_url
    }
    return [document_id_by_source_url[source_url] for source_url in source_urls if source_url in document_id_by_source_url]


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

    discovered_before_quarantine = len(discovered)
    quarantined_count = 0
    if discovered:
        retained = []
        for item in discovered:
            reason = _match_document_quarantine_reason(
                ticker=str(getattr(item, "ticker", "") or ticker),
                title=getattr(item, "title", ""),
                source_url=getattr(item, "source_url", ""),
            )
            if reason:
                quarantined_count += 1
                logger.info(
                    "quarantined discovered document ticker=%s title=%s reason=%s",
                    ticker,
                    str(getattr(item, "title", "") or "").strip()[:160],
                    reason,
                )
                continue
            retained.append(item)
        discovered = retained

    inserted_payload = insert_discovered_documents(db, discovered)
    discovered_document_ids = _load_discovered_document_ids(db, discovered)
    return {
        "ticker": ticker,
        "found": discovered_before_quarantine,
        "eligible_found": len(discovered),
        "quarantined": quarantined_count,
        "inserted": inserted_payload["inserted"],
        "new_document_ids": discovered_document_ids,
        "inserted_document_ids": inserted_payload["new_document_ids"],
    }


def download_pdf_for_document(db, document_id, http_client: Optional[httpx.Client] = None):
    doc_uuid = _coerce_uuid(document_id)
    doc = db.query(Document).filter(Document.document_id == doc_uuid).first()
    if not doc:
        raise ValueError(f"Document not found: {document_id}")

    quarantine_reason = _match_document_quarantine_reason(
        ticker=doc.ticker,
        title=doc.title,
        source_url=doc.source_url,
        pdf_path=doc.pdf_path,
    )
    if quarantine_reason:
        doc.pdf_sha256 = "blocked_document_quarantine"
        db.commit()
        raise RuntimeError(f"document_quarantined: {quarantine_reason}")

    if _is_marketindex_url(doc.source_url):
        raise RuntimeError(
            "marketindex_headed_required: MarketIndex URLs must be fetched via headed browser session."
        )

    # Always normalize to canonical readable path before writing.
    _ensure_document_pdf_path(doc)

    response = _download_bytes(doc.source_url, client=http_client)
    content = response.content
    if not content.startswith(b"%PDF"):
        resolved_pdf_url = _extract_pdf_url_from_html(response.text, doc.source_url)
        if resolved_pdf_url:
            fallback_response = _download_bytes(resolved_pdf_url, client=http_client)
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
            setattr(row, field, _coerce_float(metrics.get(field, None)))
        row.source_document_id = doc.document_id
        row.confidence_metrics = _coerce_float(structured.get("confidence_metrics"))
        row.period_start = parse_period_end(structured.get("period_start"))
        row.currency = structured.get("currency") or None

    risk_note = db.query(ASXRiskNote).filter(ASXRiskNote.document_id == doc.document_id).first()
    if not risk_note:
        risk_note = ASXRiskNote(document_id=doc.document_id)
        db.add(risk_note)

    risk_note.risk_summary = _coerce_text(structured.get("risk_summary"))
    risk_note.risk_bullets = _coerce_risk_bullets(structured.get("risk_bullets"))
    risk_note.guidance_summary = _coerce_text(structured.get("guidance_summary"))
    risk_note.material_changes = _coerce_text(structured.get("material_changes"), join_lists=True)
    risk_note.confidence_narrative = _coerce_float(structured.get("confidence_narrative"))
    # NOTE: caller is responsible for db.commit() — do not commit here so that
    # ExtractionRun and financial rows are written in a single atomic transaction.


def process_document(
    document_id,
    qdrant_client: Optional[QdrantClient] = None,
    ollama_client: Optional[httpx.Client] = None,
):
    db = SessionLocal()
    try:
        doc_uuid = _coerce_uuid(document_id)
        doc = db.query(Document).filter(Document.document_id == doc_uuid).first()
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # --- New multi-pass extraction ---
        multipass_result = None
        sections_for_chunks: list[dict] = []
        status = "skipped"
        error = None
        structured: dict = {"status": "skipped_extraction"}
        confidence = None
        extraction_model_name = None

        if settings.enable_extraction:
            try:
                doc_metadata = {
                    "document_id": str(doc.document_id),
                    "ticker": str(doc.ticker or ""),
                    "title": str(doc.title or ""),
                }
                multipass_result = run_multipass_extraction(
                    _resolve_pdf_path(doc.pdf_path),
                    doc_metadata,
                    ollama_client,
                )
                sections_for_chunks = multipass_result.sections
                status = multipass_result.status
                error = multipass_result.error
                structured = multipass_result.payload
                confidence = structured.get("confidence_metrics")
                extraction_model_name = "qwen2.5-32b-instruct"
            except Exception as exc:
                status = "failed"
                error = str(exc)
                structured = {"error": error}
                sections_for_chunks = []

        # --- Use structured sections for prose chunking (not raw text) ---
        _doc_for_chunks = StructuredDocument(sections=sections_for_chunks)
        chunks = chunk_prose_sections(_doc_for_chunks)
        chunks_created = len(chunks)
        chunks_skipped = 0
        invalid_payloads = 0
        written_points = 0

        skipped_invalid_vectors = 0
        if settings.enable_embeddings and chunks:
            if doc.document_id is None:
                log_rejected_payload(
                    "document_id is None before embedding",
                    payload={"document_id": None, "ticker": doc.ticker},
                    collection=settings.qdrant_collection,
                    source=doc.source_url,
                )
                skipped_invalid_vectors = len(chunks)
                invalid_payloads += len(chunks)
                chunks_skipped += len(chunks)
            elif not str(doc.ticker or "").strip():
                log_rejected_payload(
                    "ticker is missing before embedding",
                    payload={"document_id": str(doc.document_id).lower(), "ticker": doc.ticker},
                    collection=settings.qdrant_collection,
                    source=doc.source_url,
                )
                skipped_invalid_vectors = len(chunks)
                invalid_payloads += len(chunks)
                chunks_skipped += len(chunks)
            else:
                doc_id_str = str(doc.document_id).lower()
                try:
                    uuid.UUID(doc_id_str)
                except Exception:
                    log_rejected_payload(
                        "document_id is not a canonical UUID before embedding",
                        payload={"document_id": doc_id_str, "ticker": doc.ticker},
                        collection=settings.qdrant_collection,
                        source=doc.source_url,
                    )
                    skipped_invalid_vectors = len(chunks)
                    invalid_payloads += len(chunks)
                    chunks_skipped += len(chunks)
                    doc_id_str = ""
                if doc_id_str:
                    vectors = _embed_chunks(chunks, ollama_client=ollama_client)
                else:
                    vectors = []
                if len(vectors) != len(chunks):
                    mismatch_count = abs(len(chunks) - len(vectors))
                    skipped_invalid_vectors += mismatch_count
                    chunks_skipped += mismatch_count
                    logger.error(
                        "Embedding/vector count mismatch for document_id=%s ticker=%s source=%s expected=%d got=%d",
                        doc_id_str,
                        doc.ticker,
                        doc.source_url,
                        len(chunks),
                        len(vectors),
                    )
                if settings.enable_qdrant and vectors:
                    qc = qdrant_client if qdrant_client is not None else QdrantClient(url=settings.qdrant_url)
                    usable_vectors = vectors[: len(chunks)]
                    vector_dimension = len(usable_vectors[0])
                    ensure_collection(qc, settings.qdrant_collection, vector_dimension)
                    points = []
                    for index, vector in enumerate(usable_vectors):
                        point_id = f"{doc_id_str}:{index}"
                        payload = {
                            "document_id": doc_id_str,
                            "ticker": doc.ticker,
                            "doc_class": doc.doc_class,
                            "doc_subtype": doc.doc_subtype,
                            "chunk_index": index,
                            "title": doc.title,
                        }
                        is_valid, reason = validate_payload(payload)
                        if not is_valid:
                            skipped_invalid_vectors += 1
                            invalid_payloads += 1
                            chunks_skipped += 1
                            log_rejected_payload(
                                reason or "payload validation failed",
                                payload=payload,
                                collection=settings.qdrant_collection,
                                point_id=point_id,
                                source=doc.source_url,
                            )
                            continue
                        points.append(
                            {
                                "id": point_id,
                                "vector": vector,
                                "payload": payload,
                            }
                        )
                    if points:
                        delete_points_for_document(qc, settings.qdrant_collection, doc_id_str)
                    upsert_result = dict(upsert_points(qc, settings.qdrant_collection, points) or {})
                    written_points += int(upsert_result.get("written_points", 0))
                    rejected_payloads = int(upsert_result.get("rejected_payloads", 0))
                    invalid_payloads += rejected_payloads
                    chunks_skipped += rejected_payloads

        logger.info(
            "document_ingestion_result",
            extra={
                "ticker": str(doc.ticker or "").strip().upper(),
                "document_id": str(doc.document_id),
                "documents_processed": 1,
                "chunks_created": chunks_created,
                "chunks_skipped": chunks_skipped,
                "invalid_payloads": invalid_payloads,
                "written_points": written_points,
                "skipped_invalid_vectors": skipped_invalid_vectors,
            },
        )

        def _json_safe(obj: Any) -> Any:
            """Recursively convert date/datetime to ISO strings for JSON storage."""
            if isinstance(obj, dict):
                return {k: _json_safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_json_safe(v) for v in obj]
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return obj

        run = ExtractionRun(
            document_id=doc.document_id,
            extractor_version=EXTRACTOR_VERSION,
            model_name=extraction_model_name or settings.extract_model,
            prompt_hash=PROMPT_HASH,
            status=status,
            confidence_overall=confidence,
            error=error,
            structured_json=_json_safe(structured),
        )
        db.add(run)
        if status in {"ok", "ok_low_confidence"}:
            _upsert_financial_rows(db, doc, structured)
        db.commit()  # single atomic commit: ExtractionRun + financial rows together

        return {
            "ok": True,
            "document_id": str(doc.document_id),
            "chunks": chunks_created,
            "extraction_status": status,
            "skipped_invalid_vectors": skipped_invalid_vectors,
            "chunks_created": chunks_created,
            "chunks_skipped": chunks_skipped,
            "invalid_payloads": invalid_payloads,
            "written_points": written_points,
        }
    finally:
        db.close()


def _download_and_process_one(
    document_id,
    process_documents: bool,
    http_client: Optional[httpx.Client],
    qdrant_client: Optional[QdrantClient],
    ollama_client: Optional[httpx.Client],
) -> dict:
    """Run download + optional process for one document. Returns dict with processed, skipped_download, error, extraction_status."""
    db = SessionLocal()
    try:
        download_pdf_for_document(db, document_id, http_client=http_client)
        extraction_status = None
        result = None
        if process_documents:
            result = process_document(
                document_id,
                qdrant_client=qdrant_client,
                ollama_client=ollama_client,
            )
            extraction_status = (result or {}).get("extraction_status")
        return {
            "processed": 1,
            "skipped_download": 0,
            "error": None,
            "extraction_status": extraction_status,
            "chunks_created": int((result or {}).get("chunks_created", 0) or 0),
            "chunks_skipped": int((result or {}).get("chunks_skipped", 0) or 0),
            "invalid_payloads": int((result or {}).get("invalid_payloads", 0) or 0),
            "written_points": int((result or {}).get("written_points", 0) or 0),
        }
    except RuntimeError as exc:
        if "marketindex_headed_required" in str(exc):
            doc = db.query(Document).filter(Document.document_id == _coerce_uuid(document_id)).first()
            if doc:
                doc.pdf_sha256 = "blocked_marketindex_headed_required"
                db.commit()
            return {
                "processed": 0,
                "skipped_download": 1,
                "error": None,
                "extraction_status": None,
                "chunks_created": 0,
                "chunks_skipped": 0,
                "invalid_payloads": 0,
                "written_points": 0,
            }
        if "document_quarantined" in str(exc):
            return {
                "processed": 0,
                "skipped_download": 1,
                "error": None,
                "extraction_status": None,
                "chunks_created": 0,
                "chunks_skipped": 0,
                "invalid_payloads": 0,
                "written_points": 0,
            }
        db.rollback()
        return {
            "processed": 0,
            "skipped_download": 0,
            "error": str(exc),
            "extraction_status": None,
            "chunks_created": 0,
            "chunks_skipped": 0,
            "invalid_payloads": 0,
            "written_points": 0,
        }
    except httpx.HTTPStatusError as exc:
        request_url = str(exc.request.url)
        if exc.response.status_code == 403 and "marketindex.com.au" in request_url:
            doc = db.query(Document).filter(Document.document_id == _coerce_uuid(document_id)).first()
            if doc:
                doc.pdf_sha256 = "blocked_marketindex_403"
                db.commit()
            return {
                "processed": 0,
                "skipped_download": 1,
                "error": None,
                "extraction_status": None,
                "chunks_created": 0,
                "chunks_skipped": 0,
                "invalid_payloads": 0,
                "written_points": 0,
            }
        db.rollback()
        return {
            "processed": 0,
            "skipped_download": 0,
            "error": str(exc),
            "extraction_status": None,
            "chunks_created": 0,
            "chunks_skipped": 0,
            "invalid_payloads": 0,
            "written_points": 0,
        }
    except Exception as exc:
        db.rollback()
        return {
            "processed": 0,
            "skipped_download": 0,
            "error": str(exc),
            "extraction_status": None,
            "chunks_created": 0,
            "chunks_skipped": 0,
            "invalid_payloads": 0,
            "written_points": 0,
        }
    finally:
        db.close()


def _download_and_process_document_ids(
    document_ids: list,
    process_documents: bool,
    max_workers: int = 1,
    qdrant_client: Optional[QdrantClient] = None,
    http_client: Optional[httpx.Client] = None,
) -> tuple[int, int, int, list, dict[str, int]]:
    """Download and optionally process documents. Returns aggregate processing counts and ingestion metrics."""
    max_workers = max(1, int(max_workers))
    own_http = http_client is None
    own_qdrant = qdrant_client is None and process_documents
    own_ollama = process_documents

    if own_http:
        http_client = httpx.Client(timeout=90.0)
    if own_qdrant:
        qdrant_client = QdrantClient(url=settings.qdrant_url)
    if own_ollama:
        ollama_client = httpx.Client(timeout=480.0)
    else:
        ollama_client = None

    processed = 0
    skipped_download = 0
    extraction_failed_count = 0
    errors: list[dict] = []
    chunks_created = 0
    chunks_skipped = 0
    invalid_payloads = 0
    written_points = 0

    try:
        if max_workers == 1:
            for document_id in document_ids:
                out = _download_and_process_one(
                    document_id,
                    process_documents,
                    http_client,
                    qdrant_client,
                    ollama_client,
                )
                processed += out["processed"]
                skipped_download += out["skipped_download"]
                chunks_created += int(out.get("chunks_created", 0) or 0)
                chunks_skipped += int(out.get("chunks_skipped", 0) or 0)
                invalid_payloads += int(out.get("invalid_payloads", 0) or 0)
                written_points += int(out.get("written_points", 0) or 0)
                if (out.get("extraction_status") or "").strip().lower() == "failed":
                    extraction_failed_count += 1
                    errors.append(
                        {
                            "document_id": str(document_id),
                            "stage": "process_document",
                            "error": "extraction_failed",
                            "extraction_status": out.get("extraction_status"),
                        }
                    )
                elif out["error"] is not None:
                    errors.append({"document_id": str(document_id), "error": out["error"]})
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        _download_and_process_one,
                        document_id,
                        process_documents,
                        http_client,
                        qdrant_client,
                        ollama_client,
                    ): document_id
                    for document_id in document_ids
                }
                for fut in concurrent.futures.as_completed(futures):
                    document_id = futures[fut]
                    try:
                        out = fut.result()
                        processed += out["processed"]
                        skipped_download += out["skipped_download"]
                        chunks_created += int(out.get("chunks_created", 0) or 0)
                        chunks_skipped += int(out.get("chunks_skipped", 0) or 0)
                        invalid_payloads += int(out.get("invalid_payloads", 0) or 0)
                        written_points += int(out.get("written_points", 0) or 0)
                        if (out.get("extraction_status") or "").strip().lower() == "failed":
                            extraction_failed_count += 1
                            errors.append(
                                {
                                    "document_id": str(document_id),
                                    "stage": "process_document",
                                    "error": "extraction_failed",
                                    "extraction_status": out.get("extraction_status"),
                                }
                            )
                        elif out["error"] is not None:
                            errors.append({"document_id": str(document_id), "error": out["error"]})
                    except Exception as exc:
                        errors.append({"document_id": str(document_id), "error": str(exc)})
    finally:
        if own_http:
            http_client.close()
        if own_ollama and ollama_client is not None:
            ollama_client.close()

    return processed, skipped_download, extraction_failed_count, errors, {
        "chunks_created": chunks_created,
        "chunks_skipped": chunks_skipped,
        "invalid_payloads": invalid_payloads,
        "written_points": written_points,
    }


def backfill_ticker_sync(ticker, years=5, process_documents=True, max_workers: Optional[int] = None):
    db = SessionLocal()
    try:
        ticker_upper = ticker.upper() if ticker else ""
        existing_doc_count = db.query(Document).filter(Document.ticker == ticker_upper).count()
        discovery = discover_and_insert_documents(db, ticker=ticker, years=years)
        doc_ids = discovery["new_document_ids"]
        workers = max(1, int(max_workers)) if max_workers is not None else max(1, settings.backfill_concurrency)
        processed, skipped_download, _extraction_failed, errors, ingestion_metrics = _download_and_process_document_ids(
            doc_ids,
            process_documents,
            max_workers=workers,
        )
        logger.info(
            "ticker_ingestion_result",
            extra={
                "ticker": ticker_upper,
                "documents_processed": processed,
                "documents_discovered": discovery["found"],
                "documents_inserted": discovery["inserted"],
                "documents_skipped_download": skipped_download,
                "chunks_created": int(ingestion_metrics.get("chunks_created", 0) or 0),
                "chunks_skipped": int(ingestion_metrics.get("chunks_skipped", 0) or 0),
                "invalid_payloads": int(ingestion_metrics.get("invalid_payloads", 0) or 0),
                "written_points": int(ingestion_metrics.get("written_points", 0) or 0),
                "error_count": len(errors),
            },
        )

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
            "eligible_found": discovery.get("eligible_found", discovery["found"]),
            "quarantined_documents": discovery.get("quarantined", 0),
            "inserted": discovery["inserted"],
            "existing_doc_count": existing_doc_count,
            "processed": processed,
            "skipped_download": skipped_download,
            "process_documents": process_documents,
            "importance_classification": importance_classification,
            "errors": errors,
            "error_count": len(errors),
            "chunks_created": int(ingestion_metrics.get("chunks_created", 0) or 0),
            "chunks_skipped": int(ingestion_metrics.get("chunks_skipped", 0) or 0),
            "invalid_payloads": int(ingestion_metrics.get("invalid_payloads", 0) or 0),
            "written_points": int(ingestion_metrics.get("written_points", 0) or 0),
        }
    finally:
        db.close()
