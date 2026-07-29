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
from app.services.embeddings import (
    delete_points_for_document,
    ensure_collection,
    log_rejected_payload,
    upsert_points,
    validate_payload,
)
from app.services.extraction_run_observability import (
    ExtractionRunObserver,
    initialize_run_status,
)
from app.services.financial_metric_contract import PERSISTED_METRIC_COLUMNS
from app.services.financial_observations import stage_financial_observations
from app.services.announcement_importance import (
    classify_documents_and_materialize,
    classify_title_extraction_skip,
)
from app.services.llm import embed_texts, generate_json, get_routing_decision
from app.services.multipass_extraction import (
    run_multipass_extraction,
    EXTRACTOR_VERSION,
    PROMPT_HASH,
    parse_period_end,
)
from app.services.structured_chunking import chunk_prose_sections
from app.services.docling_extract import StructuredDocument
from app.services.pipeline_stages import (
    DocumentProcessResult,
    DownloadProcessAggregate,
    EmbeddingStageStatus,
    ExtractionStageResult,
    ExtractionStageStatus,
    attach_reproducibility_metadata,
    build_reproducibility_metadata,
    normalize_document_process_result,
    run_embedding_stage,
)
from app.services.storage import ensure_dir, sha256_file, write_bytes


logger = logging.getLogger(__name__)


class PipelineJobCancelled(RuntimeError):
    """Raised when a tracked pipeline operation is cancelled by the user."""


def _ops_job_cancel_requested(job_id: str | None) -> bool:
    resolved_job_id = str(job_id or "").strip()
    if not resolved_job_id:
        return False
    try:
        from app.services.job_tracker import get_tracker

        tracker = get_tracker()
        if tracker is None:
            return False
        return tracker.is_cancellation_requested(resolved_job_id)
    except Exception:
        logger.debug(
            "pipeline cancellation probe failed for %s",
            resolved_job_id,
            exc_info=True,
        )
        return False


def _raise_if_ops_job_cancelled(*job_ids: str | None) -> None:
    for job_id in job_ids:
        if _ops_job_cancel_requested(job_id):
            raise PipelineJobCancelled(
                "Pipeline operation cancelled by user request."
            )


# ── Job-tracker bridge ─────────────────────────────────────────────────────
# Bridges ExtractionRunObserver events into the unified ops job-status layer.
# Purely additive — never raises; extraction proceeds regardless of tracker state.


_OBSERVER_STAGE_TO_PHASE = {
    "queued": "queued",
    "starting": "starting",
    "document_load": "document_load",
    "parser": "parser",
    "pass1_classifier": "pass1_classifier",
    "pass2_locator": "pass2_locator",
    "pass3a_metrics": "pass3a_metrics",
    "pass3b_narrative": "pass3b_narrative",
    "pass4_reconciliation": "pass4_reconciliation",
    "validation": "validation",
    "chunking": "chunking",
    "embedding": "embedding",
    "persistence": "persistence",
    "completed": "completed",
}


def _bridge_observer_to_tracker(
    observer: ExtractionRunObserver, tracker_job_id: str
) -> None:
    """Wrap observer.emit to also forward events to the ops JobTracker.

    The original emit behaviour is fully preserved.  Tracker failures
    are logged at WARNING level and never propagate.
    """
    from app.services.job_tracker import get_tracker

    original_emit = observer.emit

    def bridged_emit(stage, status, message, **kwargs):
        result = original_emit(stage, status, message, **kwargs)
        try:
            tracker = get_tracker()
            if tracker is None:
                return result
            phase = _OBSERVER_STAGE_TO_PHASE.get(stage, stage)
            if status == "running":
                tracker.change_phase(tracker_job_id, phase, message)
            elif status == "succeeded" and stage == "completed":
                tracker.complete_job(tracker_job_id, summary=message)
            elif status in ("failed", "blocked"):
                tracker.fail_job(tracker_job_id, message)
            elif status == "succeeded":
                tracker.change_phase(tracker_job_id, phase, message)
        except Exception:
            logger.warning(
                "ops tracker bridge error (non-fatal)", exc_info=True
            )
        return result

    observer.emit = bridged_emit


# Process-local in-memory embedding cache (key: SHA256(text), value: embedding vector).
# Only used when settings.enable_embedding_cache is True.
_embedding_cache: dict[str, list[float]] = {}
DOCUMENT_QUARANTINE_RULES_PATH = (
    PROJECT_ROOT / "config" / "document_quarantine_rules.json"
)
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
        logger.warning(
            "failed to read document quarantine rules from %s: %s", path, exc
        )
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
        logger.warning(
            "failed to stat document quarantine rules %s: %s",
            DOCUMENT_QUARANTINE_RULES_PATH,
            exc,
        )
        mtime = None

    if (
        _document_quarantine_rules_cache is None
        or _document_quarantine_rules_cache_mtime != mtime
    ):
        _document_quarantine_rules_cache = _load_document_quarantine_rules(
            DOCUMENT_QUARANTINE_RULES_PATH
        )
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
        part
        for part in (str(title or ""), str(source_url or ""), str(pdf_path or ""))
        if str(part).strip()
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
            if (
                needle in haystack
                or needle.replace("-", " ").replace("_", " ") in haystack_norm
            ):
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
    "missing_pdf_file",
    "parser_timeout",
    "classifier_low_confidence",
    "llm_invalid_json",
    "provider_network",
    "corrupted_pdf",
    "unknown",
)


def classify_extraction_failure(
    error_text: Any, structured_json: Mapping[str, Any] | None = None
) -> str:
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

    if any(
        token in text
        for token in (
            "no such file or directory",
            "filenotfounderror",
            "cannot find the file",
            "cannot find the path",
        )
    ):
        return "missing_pdf_file"

    if any(
        token in text
        for token in (
            "timeout",
            "timed out",
            "deadline exceeded",
            "took too long",
            "extractiontimeouterror",
        )
    ):
        return "parser_timeout"

    if any(
        token in text
        for token in (
            "docling failed",
            "docling strict backend rejected",
            "pipeline standardpdfpipeline failed",
        )
    ):
        return "parser_error"

    if any(
        token in text
        for token in (
            "classifier_low_confidence",
            "classifier confidence below threshold",
            "pass1_classifier",
        )
    ):
        return "classifier_low_confidence"

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

    direct = re.search(
        r"https://announcements\.asx\.com\.au/asxpdf/[^\s\"'<>]+\.pdf",
        html_text,
        flags=re.I,
    )
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


def _remap_legacy_pdf_path(path: Path) -> Path | None:
    docs_root = Path(settings.docs_root).expanduser().resolve()
    parts = path.parts
    for idx in range(len(parts) - 1):
        if parts[idx : idx + 2] == ("asx", "docs"):
            suffix = parts[idx + 2 :]
            if not suffix:
                return None
            return docs_root.joinpath(*suffix).resolve()
    return None


def _resolve_pdf_path(value: str | None) -> str:
    """Resolve pdf_path to an absolute path under the active docs root when possible."""
    raw = str(value or "").strip()
    if not raw:
        return raw
    docs_root = Path(settings.docs_root).expanduser().resolve()
    path = Path(raw).expanduser()
    if path.is_absolute():
        if path.exists():
            return str(path.resolve())
        remapped = _remap_legacy_pdf_path(path)
        if remapped is not None and remapped.exists():
            return str(remapped)
        return str(path)
    return str((docs_root / path).resolve())


def _repair_document_pdf_path_if_needed(db, doc, resolved_pdf_path: str) -> str:
    resolved = str(resolved_pdf_path or "").strip()
    if not resolved or resolved == str(doc.pdf_path or "").strip():
        return resolved
    doc.pdf_path = resolved
    db.commit()
    return resolved


def _build_missing_pdf_error(doc, *, resolved_pdf_path: str) -> str:
    return (
        "PDF file not found for extraction. "
        f"document_id={doc.document_id} "
        f"ticker={str(doc.ticker or '').strip().upper()} "
        f"stored_pdf_path={str(doc.pdf_path or '').strip()} "
        f"resolved_pdf_path={resolved_pdf_path} "
        f"docs_root={Path(settings.docs_root).expanduser().resolve()} "
        f"data_root={Path(settings.data_root).expanduser().resolve()} "
        f"database_url={settings.database_url}"
    )


def _pending_pdf_download(doc) -> bool:
    marker = str(getattr(doc, "pdf_sha256", "") or "").strip()
    return not marker


def _download_pending_pdf_for_processing(
    db,
    doc,
    observer: ExtractionRunObserver,
    *,
    resolved_pdf_path: str,
) -> tuple[str, str | None]:
    if resolved_pdf_path and Path(resolved_pdf_path).exists():
        return resolved_pdf_path, None
    if not _pending_pdf_download(doc):
        return resolved_pdf_path, None

    observer.emit(
        "document_download",
        "running",
        "PDF missing locally; downloading pending source PDF before extraction.",
        details={
            "stored_pdf_path": str(doc.pdf_path or "").strip(),
            "source_url": str(doc.source_url or "").strip(),
        },
    )
    try:
        download_pdf_for_document(db, str(doc.document_id))
    except Exception as exc:
        error_text = str(exc)
        observer.emit(
            "document_download",
            "failed",
            f"Automatic PDF download failed: {error_text}",
            error_code=classify_extraction_failure(error_text, None),
            details={
                "stored_pdf_path": str(doc.pdf_path or "").strip(),
                "source_url": str(doc.source_url or "").strip(),
            },
        )
        return resolved_pdf_path, error_text

    refreshed_pdf_path = _resolve_pdf_path(doc.pdf_path)
    observer.emit(
        "document_download",
        "succeeded",
        "Pending source PDF downloaded before extraction.",
        details={
            "stored_pdf_path": str(doc.pdf_path or "").strip(),
            "resolved_pdf_path": refreshed_pdf_path,
        },
    )
    return refreshed_pdf_path, None


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
    if (
        current_path
        and current_path.exists()
        and current_path != canonical_path
        and not canonical_path.exists()
    ):
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
    skipped_quarantine = 0
    prepared = []
    seen_source_urls: set[str] = set()

    for discovered_doc in discovered_docs:
        ticker = (discovered_doc.ticker or "").upper().strip()
        if not ticker:
            logger.warning(
                "ASX skip",
                extra={
                    "reason": "invalid_structure",
                    "data": {
                        "missing": "ticker",
                        "discovered_doc": str(discovered_doc),
                    },
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
                        "source_url": str(
                            getattr(discovered_doc, "source_url", "") or ""
                        )[:500],
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
                    "data": {
                        "ticker": ticker,
                        "source_url": source_url,
                        "scope": "batch",
                    },
                },
            )
            continue
        seen_source_urls.add(source_url)
        q_reason = _match_document_quarantine_reason(
            ticker=ticker,
            title=getattr(discovered_doc, "title", ""),
            source_url=source_url,
        )
        if q_reason:
            skipped_quarantine += 1
            logger.info(
                "quarantined at insert ticker=%s title=%s reason=%s",
                ticker,
                str(getattr(discovered_doc, "title", "") or "").strip()[:160],
                q_reason,
            )
            continue
        prepared.append((discovered_doc, ticker, source_url))

    source_urls = [row[2] for row in prepared]
    existing_source_urls: set[str] = set()
    if source_urls:
        existing_rows = (
            db.query(Document.source_url)
            .filter(Document.source_url.in_(source_urls))
            .all()
        )
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
            exists = (
                db.query(Document.document_id)
                .filter(Document.source_url == source_url)
                .first()
            )
            if exists:
                duplicate_existing += 1
                logger.warning(
                    "ASX skip",
                    extra={
                        "reason": "duplicate",
                        "data": {
                            "ticker": ticker,
                            "source_url": source_url,
                            "scope": "db_race",
                        },
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
                        "data": {
                            "ticker": ticker,
                            "source_url": source_url,
                            "scope": "db_commit",
                        },
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
        "skipped_quarantine": skipped_quarantine,
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
    return [
        document_id_by_source_url[source_url]
        for source_url in source_urls
        if source_url in document_id_by_source_url
    ]


def discover_and_insert_documents(db, ticker, years=5):
    ticker = ticker.upper()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * years)
    discovered = ASXProvider().discover(ticker, start, end)
    if settings.enable_marketindex_fallback:
        marketindex_docs = MarketIndexProvider(
            settings.marketindex_announcements_file
        ).discover(ticker, start, end)
        discovered_by_url = {item.source_url: item for item in discovered}
        for item in marketindex_docs:
            if item.source_url not in discovered_by_url:
                discovered.append(item)

    discovered_total = len(discovered)
    inserted_payload = insert_discovered_documents(db, discovered)
    quarantined_count = int(inserted_payload.get("skipped_quarantine", 0) or 0)
    discovered_document_ids = _load_discovered_document_ids(db, discovered)
    return {
        "ticker": ticker,
        "found": discovered_total,
        "eligible_found": max(0, discovered_total - quarantined_count),
        "quarantined": quarantined_count,
        "inserted": inserted_payload["inserted"],
        "new_document_ids": discovered_document_ids,
        "inserted_document_ids": inserted_payload["new_document_ids"],
    }


def download_pdf_for_document(
    db, document_id, http_client: Optional[httpx.Client] = None
):
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


def _metric_provenance_for_written_values(
    *,
    metrics: Mapping[str, Any],
    structured: Mapping[str, Any],
    written_values: Mapping[str, Any],
) -> dict[str, dict[str, Any]] | None:
    raw_provenance = structured.get("field_provenance")
    if not isinstance(raw_provenance, Mapping):
        raw_provenance = structured.get("metric_provenance")
    if not isinstance(raw_provenance, Mapping):
        return None

    metric_provenance: dict[str, dict[str, Any]] = {}
    for field, value in written_values.items():
        if value is None or field not in metrics:
            continue
        entry = raw_provenance.get(field)
        if not isinstance(entry, Mapping):
            continue
        metric_provenance[field] = dict(entry)
    return metric_provenance or None


def _upsert_financial_rows(db, doc, structured):
    period_type = structured.get("period_type")
    period_end = parse_period_end(structured.get("period_end"))
    metrics = structured.get("metrics") or {}
    financial_rows_written = 0

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

        metric_fields = PERSISTED_METRIC_COLUMNS
        written_values = {}
        for field in metric_fields:
            value = _coerce_float(metrics.get(field, None))
            setattr(row, field, value)
            written_values[field] = value
        row.source_document_id = doc.document_id
        row.confidence_metrics = _coerce_float(structured.get("confidence_metrics"))
        row.metric_provenance = _metric_provenance_for_written_values(
            metrics=metrics,
            structured=structured,
            written_values=written_values,
        )
        row.period_start = parse_period_end(structured.get("period_start"))
        row.currency = structured.get("currency") or None
        financial_rows_written = 1

    _upsert_risk_note(db, doc, structured, allow_empty=False)
    # NOTE: caller is responsible for db.commit() — do not commit here so that
    # ExtractionRun and financial rows are written in a single atomic transaction.
    return financial_rows_written


def _has_narrative_content(structured: Mapping[str, Any]) -> bool:
    if _coerce_text(structured.get("risk_summary")):
        return True
    if _coerce_risk_bullets(structured.get("risk_bullets")):
        return True
    if _coerce_text(structured.get("guidance_summary")):
        return True
    if _coerce_text(structured.get("material_changes"), join_lists=True):
        return True
    return False


def _upsert_risk_note(
    db,
    doc,
    structured: Mapping[str, Any],
    *,
    allow_empty: bool,
) -> int:
    has_narrative = _has_narrative_content(structured)
    if not allow_empty and not has_narrative:
        return 0

    risk_note = (
        db.query(ASXRiskNote).filter(ASXRiskNote.document_id == doc.document_id).first()
    )
    if not risk_note:
        risk_note = ASXRiskNote(document_id=doc.document_id)
        db.add(risk_note)

    risk_note.risk_summary = _coerce_text(structured.get("risk_summary"))
    risk_note.risk_bullets = _coerce_risk_bullets(structured.get("risk_bullets"))
    risk_note.guidance_summary = _coerce_text(structured.get("guidance_summary"))
    risk_note.material_changes = _coerce_text(
        structured.get("material_changes"), join_lists=True
    )
    risk_note.confidence_narrative = _coerce_float(
        structured.get("confidence_narrative")
    )
    return int(has_narrative)


def _should_persist_failed_narrative(
    extraction_stage: ExtractionStageResult,
) -> bool:
    if extraction_stage.status != ExtractionStageStatus.FAILED:
        return False
    error_text = str(extraction_stage.error or "").strip().lower()
    if not error_text.startswith("validation_gate:"):
        return False
    payload = extraction_stage.payload
    if not isinstance(payload, Mapping):
        return False
    return _has_narrative_content(payload)


def process_document(
    document_id,
    qdrant_client: Optional[QdrantClient] = None,
    ollama_client: Optional[httpx.Client] = None,
    *,
    run_id: str | None = None,
    parent_job_id: str | None = None,
    requested_method: str = "auto",
    strict_method: bool = False,
    skip_narrative: bool = False,
):
    db = SessionLocal()
    try:
        resolved_run_id = str(run_id or uuid.uuid4())
        doc_uuid = _coerce_uuid(document_id)
        doc = db.query(Document).filter(Document.document_id == doc_uuid).first()
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        initialize_run_status(
            run_id=resolved_run_id,
            document_id=str(doc_uuid),
            requested_method=requested_method,
            strict_method=strict_method,
        )
        observer = ExtractionRunObserver(
            run_id=resolved_run_id,
            document_id=str(doc_uuid),
            requested_method=requested_method,
            strict_method=strict_method,
        )
        cancellation_job_ids = tuple(
            job_id
            for job_id in (resolved_run_id, parent_job_id)
            if str(job_id or "").strip()
        )
        # Bridge observer events into the ops job-status layer
        try:
            from app.services.job_tracker import get_tracker

            _ops_tracker = get_tracker()
            if _ops_tracker is not None:
                _ops_handle = _ops_tracker.create_job(
                    job_type="extraction",
                    job_family="pipeline",
                    title=f"Extract {doc.ticker or ''} {(doc.title or '')[:60]}",
                    trigger_source="api",
                    entity_scope="document",
                    ticker=doc.ticker,
                    job_id=resolved_run_id,
                    metadata={
                        "document_id": str(doc_uuid),
                        "supports_cancellation": True,
                    },
                )
                _ops_tracker.start_job(_ops_handle.job_id)
                _bridge_observer_to_tracker(observer, _ops_handle.job_id)
        except Exception:
            logger.warning("ops tracker init for extraction failed (non-fatal)", exc_info=True)
        observer.emit("starting", "running", "Extraction run started.")
        _raise_if_ops_job_cancelled(*cancellation_job_ids)

        # --- Structured extraction stage ---
        observer.emit(
            "document_load", "running", "Loading document metadata and PDF path."
        )
        resolved_pdf_path = _resolve_pdf_path(doc.pdf_path)
        doc_metadata = {
            "document_id": str(doc.document_id),
            "ticker": str(doc.ticker or ""),
            "title": str(doc.title or ""),
        }
        observer.emit(
            "document_load",
            "succeeded",
            "Document metadata loaded.",
            details={"resolved_pdf_path": resolved_pdf_path},
        )
        _raise_if_ops_job_cancelled(*cancellation_job_ids)
        default_model_name = "qwen2.5-32b-instruct"
        if resolved_pdf_path and resolved_pdf_path != str(doc.pdf_path or "").strip():
            resolved_pdf_path = _repair_document_pdf_path_if_needed(
                db, doc, resolved_pdf_path
            )
            observer.emit(
                "document_load",
                "running",
                "Document PDF path repaired to active docs root.",
                details={"stored_pdf_path": doc.pdf_path},
            )
        if not settings.enable_extraction:
            observer.emit(
                "env_check",
                "blocked",
                "Extraction disabled in current profile.",
                warning_code="extraction_disabled",
            )
            extraction_stage = ExtractionStageResult(
                status=ExtractionStageStatus.SKIPPED,
                payload={"status": "skipped_extraction"},
                sections=[],
                model_name=None,
                failure_code="disabled",
            )
        else:
            title_skip = classify_title_extraction_skip(
                title=doc.title,
                doc_class=doc.doc_class,
                doc_subtype=doc.doc_subtype,
            )
            if bool(title_skip.get("skip_extraction")):
                matched_keywords = list(title_skip.get("matched_keywords") or [])
                skip_reason = (
                    str(title_skip.get("reason") or "").strip()
                    or "non_financial_admin_title"
                )
                observer.emit(
                    "document_gate",
                    "skipped",
                    "Skipping extraction for non-financial administrative announcement.",
                    warning_code="extraction_skipped_non_financial_title",
                    details={
                        "skip_reason": skip_reason,
                        "matched_keywords": matched_keywords,
                        "title": str(doc.title or "").strip(),
                    },
                )
                extraction_stage = ExtractionStageResult(
                    status=ExtractionStageStatus.SKIPPED,
                    payload={
                        "status": "skipped_extraction",
                        "skip_reason": skip_reason,
                        "matched_keywords": matched_keywords,
                    },
                    sections=[],
                    model_name=None,
                    failure_code=skip_reason,
                )
            else:
                auto_download_error: str | None = None
                if not resolved_pdf_path or not Path(resolved_pdf_path).exists():
                    resolved_pdf_path, auto_download_error = (
                        _download_pending_pdf_for_processing(
                            db,
                            doc,
                            observer,
                            resolved_pdf_path=resolved_pdf_path,
                        )
                    )
                if not resolved_pdf_path or not Path(resolved_pdf_path).exists():
                    error_text = _build_missing_pdf_error(
                        doc,
                        resolved_pdf_path=resolved_pdf_path,
                    )
                    if auto_download_error:
                        error_text = (
                            f"{error_text} automatic_download_error={auto_download_error}"
                        )
                    extraction_stage = ExtractionStageResult(
                        status=ExtractionStageStatus.FAILED,
                        payload={"error": error_text},
                        sections=[],
                        error=error_text,
                        confidence=None,
                        model_name=default_model_name,
                        failure_code="missing_pdf_file",
                    )
                    observer.emit(
                        "document_load",
                        "failed",
                        error_text,
                        error_code="missing_pdf_file",
                        details={
                            "stored_pdf_path": str(doc.pdf_path or "").strip(),
                            "resolved_pdf_path": resolved_pdf_path,
                            "docs_root": str(
                                Path(settings.docs_root).expanduser().resolve()
                            ),
                            "data_root": str(
                                Path(settings.data_root).expanduser().resolve()
                            ),
                            "database_url": settings.database_url,
                        },
                    )
                else:
                    from app.services.router_state import extraction_activity
                    from app.services.method_isolated_extraction import (
                        run_method_isolated_extraction,
                    )

                    try:
                        with extraction_activity(
                            metadata={
                                "run_id": resolved_run_id,
                                "document_id": str(doc.document_id),
                                "requested_method": requested_method,
                                "strict_method": strict_method,
                                "skip_narrative": bool(skip_narrative),
                                "ticker": str(doc.ticker or "").strip().upper(),
                                "title": str(doc.title or "").strip(),
                            }
                        ):
                            _raise_if_ops_job_cancelled(*cancellation_job_ids)
                            multipass_result = run_method_isolated_extraction(
                                resolved_pdf_path,
                                dict(doc_metadata),
                                ollama_client,
                                observer=observer,
                                requested_method=requested_method,
                                strict_method=strict_method,
                                skip_narrative=skip_narrative,
                            )
                        _raise_if_ops_job_cancelled(*cancellation_job_ids)
                    except PipelineJobCancelled:
                        raise
                    except Exception as exc:
                        error_text = str(exc)
                        observer.emit(
                            "failed",
                            "failed",
                            f"Extraction failed: {error_text}",
                            error_code="extraction_failed",
                        )
                        extraction_stage = ExtractionStageResult(
                            status=ExtractionStageStatus.FAILED,
                            payload={"error": error_text},
                            sections=[],
                            error=error_text,
                            confidence=None,
                            model_name=default_model_name,
                            failure_code=classify_extraction_failure(error_text, None),
                        )
                    else:
                        raw_payload = getattr(multipass_result, "payload", None)
                        if isinstance(raw_payload, dict):
                            payload = raw_payload
                        elif isinstance(raw_payload, Mapping):
                            payload = dict(raw_payload)
                        else:
                            payload = {}
                        if not payload:
                            payload = {"error": "invalid_multipass_payload"}

                        raw_sections = getattr(multipass_result, "sections", None)
                        sections = (
                            list(raw_sections) if isinstance(raw_sections, list) else []
                        )

                        raw_status = (
                            str(getattr(multipass_result, "status", "")).strip().lower()
                        )
                        if raw_status == ExtractionStageStatus.OK.value:
                            status = ExtractionStageStatus.OK
                        elif raw_status == ExtractionStageStatus.OK_LOW_CONFIDENCE.value:
                            status = ExtractionStageStatus.OK_LOW_CONFIDENCE
                        elif raw_status == ExtractionStageStatus.SKIPPED.value:
                            status = ExtractionStageStatus.SKIPPED
                        elif raw_status == ExtractionStageStatus.PARSER_ERROR.value:
                            status = ExtractionStageStatus.PARSER_ERROR
                        else:
                            status = ExtractionStageStatus.FAILED

                        error = getattr(multipass_result, "error", None)
                        raw_confidence = payload.get("confidence_metrics")
                        confidence = (
                            float(raw_confidence)
                            if isinstance(raw_confidence, (int, float))
                            and not isinstance(raw_confidence, bool)
                            else None
                        )
                        failure_code: Optional[str] = None
                        if status in {
                            ExtractionStageStatus.FAILED,
                            ExtractionStageStatus.PARSER_ERROR,
                        }:
                            failure_code = classify_extraction_failure(error, payload)

                        method_provenance = payload.get("_method_provenance")
                        model_name = default_model_name
                        if isinstance(method_provenance, Mapping):
                            method_model = str(
                                method_provenance.get("model_id") or ""
                            ).strip()
                            if method_model:
                                model_name = method_model

                        extraction_stage = ExtractionStageResult(
                            status=status,
                            payload=payload,
                            sections=sections,
                            error=error,
                            confidence=confidence,
                            model_name=model_name,
                            failure_code=failure_code,
                        )

        structured = extraction_stage.payload
        confidence = extraction_stage.confidence
        metrics_payload = (
            structured.get("metrics")
            if isinstance(structured.get("metrics"), Mapping)
            else {}
        )
        reviewable_metrics_count = sum(
            1 for value in metrics_payload.values() if value is not None
        )
        chunks_created = 0
        chunks_skipped = 0
        invalid_payloads = 0
        written_points = 0
        skipped_invalid_vectors = 0
        if extraction_stage.status in {
            ExtractionStageStatus.OK,
            ExtractionStageStatus.OK_LOW_CONFIDENCE,
        }:
            _raise_if_ops_job_cancelled(*cancellation_job_ids)
            sections_for_chunks = extraction_stage.sections
            # Use structured sections for prose chunking, not raw parser text.
            _doc_for_chunks = StructuredDocument(sections=sections_for_chunks)
            observer.emit(
                "chunking", "running", "Chunking extracted sections for embeddings."
            )
            try:
                _raise_if_ops_job_cancelled(*cancellation_job_ids)
                chunks = chunk_prose_sections(_doc_for_chunks)
            except PipelineJobCancelled:
                raise
            except Exception as exc:
                observer.emit(
                    "chunking",
                    "failed",
                    f"Chunking failed: {exc}",
                    error_code="chunking_failed",
                )
                raise
            observer.emit(
                "chunking",
                "succeeded",
                "Chunking completed.",
                details={"chunks_created": len(chunks)},
            )
            observer.emit("embedding", "running", "Writing chunks to vector storage.")
            _raise_if_ops_job_cancelled(*cancellation_job_ids)
            embedding_stage = run_embedding_stage(
                chunks=chunks,
                doc=doc,
                enable_embeddings=settings.enable_embeddings,
                enable_qdrant=settings.enable_qdrant,
                qdrant_client=qdrant_client,
                qdrant_url=settings.qdrant_url,
                qdrant_collection=settings.qdrant_collection,
                ollama_client=ollama_client,
                embed_chunks=_embed_chunks,
                qdrant_client_factory=lambda url: QdrantClient(url=url),
                ensure_collection_fn=ensure_collection,
                delete_points_for_document_fn=delete_points_for_document,
                upsert_points_fn=upsert_points,
                validate_payload_fn=validate_payload,
                log_rejected_payload_fn=log_rejected_payload,
                logger_obj=logger,
            )
            _raise_if_ops_job_cancelled(*cancellation_job_ids)
            observer.emit(
                "embedding",
                "blocked"
                if embedding_stage.status == EmbeddingStageStatus.SKIPPED
                else "succeeded",
                "Embedding skipped in current profile."
                if embedding_stage.status == EmbeddingStageStatus.SKIPPED
                else "Embedding completed.",
                warning_code="embedding_skipped"
                if embedding_stage.status == EmbeddingStageStatus.SKIPPED
                else None,
                details={
                    "chunks_created": embedding_stage.chunks_created,
                    "chunks_skipped": embedding_stage.chunks_skipped,
                    "invalid_payloads": embedding_stage.invalid_payloads,
                    "written_points": embedding_stage.written_points,
                    "skipped_invalid_vectors": embedding_stage.skipped_invalid_vectors,
                },
            )

            chunks_created = embedding_stage.chunks_created
            chunks_skipped = embedding_stage.chunks_skipped
            invalid_payloads = embedding_stage.invalid_payloads
            written_points = embedding_stage.written_points
            skipped_invalid_vectors = embedding_stage.skipped_invalid_vectors
        else:
            observer.emit(
                "chunking",
                "skipped",
                "Chunking skipped because extraction did not produce persistable sections.",
                details={"extraction_status": extraction_stage.status.value},
            )
            observer.emit(
                "embedding",
                "skipped",
                "Embedding skipped because extraction did not produce chunks.",
                details={
                    "extraction_status": extraction_stage.status.value,
                    "chunks_created": 0,
                    "chunks_skipped": 0,
                    "invalid_payloads": 0,
                    "written_points": 0,
                    "skipped_invalid_vectors": 0,
                },
            )

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

        reproducibility = build_reproducibility_metadata(
            doc=doc,
            resolved_pdf_path=resolved_pdf_path,
            extractor_version=EXTRACTOR_VERSION,
            prompt_hash=PROMPT_HASH,
            stage_result=extraction_stage,
        )
        structured_with_repro = attach_reproducibility_metadata(
            structured, reproducibility
        )

        run = ExtractionRun(
            run_id=uuid.UUID(resolved_run_id),
            document_id=doc.document_id,
            extractor_version=EXTRACTOR_VERSION,
            model_name=extraction_stage.model_name or settings.extract_model,
            prompt_hash=PROMPT_HASH,
            status=extraction_stage.status.value,
            confidence_overall=confidence,
            error=extraction_stage.error,
            structured_json=_json_safe(structured_with_repro),
        )
        financial_rows_written = 0
        risk_note_written = 0
        observer.emit("persistence", "running", "Persisting extraction outputs.")
        try:
            _raise_if_ops_job_cancelled(*cancellation_job_ids)
            db.add(run)
            if extraction_stage.status in {
                ExtractionStageStatus.OK,
                ExtractionStageStatus.OK_LOW_CONFIDENCE,
            }:
                observation_payload = dict(structured)
                observation_payload["_observation_extraction_status"] = (
                    extraction_stage.status.value
                )
                stage_financial_observations(
                    db,
                    document=doc,
                    extraction_run=run,
                    structured=observation_payload,
                )
                financial_rows_written = _upsert_financial_rows(db, doc, structured)
                risk_note_written = int(
                    _has_narrative_content(structured)
                    if isinstance(structured, Mapping)
                    else 0
                )
            elif _should_persist_failed_narrative(extraction_stage):
                risk_note_written = _upsert_risk_note(
                    db,
                    doc,
                    structured,
                    allow_empty=False,
                )
            db.commit()  # single atomic commit: ExtractionRun + financial rows together
        except PipelineJobCancelled:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            observer.emit(
                "persistence",
                "failed",
                f"Persistence failed: {exc}",
                error_code="persistence_failed",
            )
            raise
        observer.emit(
            "persistence",
            "succeeded",
            "Persistence completed.",
            details={
                "persisted": True,
                "financial_rows_written": financial_rows_written,
                "risk_note_written": risk_note_written,
                "reviewable_metrics_count": reviewable_metrics_count,
            },
        )
        final_summary = {
            "run_id": resolved_run_id,
            "document_id": str(doc.document_id),
            "extraction_status": extraction_stage.status.value,
            "error": extraction_stage.error,
            "failure_code": extraction_stage.failure_code,
            "persisted": True,
            "reviewable_metrics_count": reviewable_metrics_count,
            "financial_rows_written": financial_rows_written,
            "risk_note_written": risk_note_written,
            "written_points": written_points,
        }
        observer.final_summary(final_summary)
        if extraction_stage.status in {
            ExtractionStageStatus.OK,
            ExtractionStageStatus.OK_LOW_CONFIDENCE,
            ExtractionStageStatus.SKIPPED,
        }:
            observer.emit(
                "completed",
                "succeeded",
                f"Extraction completed with status {extraction_stage.status.value}.",
                details=final_summary,
            )
            
            # Trigger Thesis Watchdog monitoring
            if extraction_stage.status in {ExtractionStageStatus.OK, ExtractionStageStatus.OK_LOW_CONFIDENCE}:
                try:
                    from app.worker_tasks import thesis_watchdog_check
                    thesis_watchdog_check.delay(
                        document_id=str(doc.document_id),
                        ticker=str(doc.ticker),
                        new_data=structured,
                        doc_title=str(doc.title or "Unknown Announcement")
                    )
                except Exception as watchdog_exc:
                    logger.warning(f"Failed to trigger Thesis Watchdog: {watchdog_exc}")
        else:
            observer.emit(
                "failed",
                "failed",
                f"Extraction finished with status {extraction_stage.status.value}.",
                error_code=extraction_stage.failure_code or "extraction_failed",
                details=final_summary,
            )

        return {
            "ok": True,
            "document_id": str(doc.document_id),
            "run_id": str(run.run_id),
            "chunks": chunks_created,
            "extraction_status": extraction_stage.status.value,
            "method_provenance": structured_with_repro.get("_method_provenance"),
            "skipped_invalid_vectors": skipped_invalid_vectors,
            "chunks_created": chunks_created,
            "chunks_skipped": chunks_skipped,
            "invalid_payloads": invalid_payloads,
            "written_points": written_points,
        }
    except PipelineJobCancelled as exc:
        db.rollback()
        observer.final_summary(
            {
                "run_id": resolved_run_id,
                "document_id": str(doc_uuid),
                "extraction_status": "cancelled",
                "error": str(exc),
                "persisted": False,
            }
        )
        try:
            from app.services.job_tracker import get_tracker

            tracker = get_tracker()
            if tracker is not None:
                tracker.cancel_job(resolved_run_id, str(exc))
        except Exception:
            logger.warning(
                "ops tracker cancellation for extraction failed (non-fatal)",
                exc_info=True,
            )
        raise
    finally:
        db.close()


def _download_and_process_one(
    document_id,
    process_documents: bool,
    http_client: Optional[httpx.Client],
    qdrant_client: Optional[QdrantClient],
    ollama_client: Optional[httpx.Client],
) -> DocumentProcessResult:
    """Run download + optional process for one document."""
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
        return DocumentProcessResult(
            processed=1,
            skipped_download=0,
            error=None,
            extraction_status=(
                str(extraction_status) if extraction_status is not None else None
            ),
            chunks_created=int((result or {}).get("chunks_created", 0) or 0),
            chunks_skipped=int((result or {}).get("chunks_skipped", 0) or 0),
            invalid_payloads=int((result or {}).get("invalid_payloads", 0) or 0),
            written_points=int((result or {}).get("written_points", 0) or 0),
        )
    except RuntimeError as exc:
        if "marketindex_headed_required" in str(exc):
            doc = (
                db.query(Document)
                .filter(Document.document_id == _coerce_uuid(document_id))
                .first()
            )
            if doc:
                doc.pdf_sha256 = "blocked_marketindex_headed_required"
                db.commit()
            return DocumentProcessResult(processed=0, skipped_download=1)
        if "document_quarantined" in str(exc):
            return DocumentProcessResult(processed=0, skipped_download=1)
        db.rollback()
        return DocumentProcessResult(
            processed=0,
            skipped_download=0,
            error=str(exc),
        )
    except httpx.HTTPStatusError as exc:
        request_url = str(exc.request.url)
        if exc.response.status_code == 403 and "marketindex.com.au" in request_url:
            doc = (
                db.query(Document)
                .filter(Document.document_id == _coerce_uuid(document_id))
                .first()
            )
            if doc:
                doc.pdf_sha256 = "blocked_marketindex_403"
                db.commit()
            return DocumentProcessResult(processed=0, skipped_download=1)
        db.rollback()
        return DocumentProcessResult(
            processed=0,
            skipped_download=0,
            error=str(exc),
        )
    except Exception as exc:
        db.rollback()
        return DocumentProcessResult(
            processed=0,
            skipped_download=0,
            error=str(exc),
        )
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

    aggregate = DownloadProcessAggregate()

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
                aggregate.add(document_id, normalize_document_process_result(out))
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
                        aggregate.add(
                            document_id,
                            normalize_document_process_result(out),
                        )
                    except Exception as exc:
                        aggregate.errors.append(
                            {"document_id": str(document_id), "error": str(exc)}
                        )
    finally:
        if own_http:
            http_client.close()
        if own_ollama and ollama_client is not None:
            ollama_client.close()

    return aggregate.to_legacy_tuple()


def backfill_ticker_sync(
    ticker, years=5, process_documents=True, max_workers: Optional[int] = None
):
    db = SessionLocal()
    _ops_job_id = None
    try:
        ticker_upper = ticker.upper() if ticker else ""
        # Register backfill job with ops tracker
        try:
            from app.services.job_tracker import get_tracker

            _ops_tracker = get_tracker()
            if _ops_tracker is not None:
                _ops_handle = _ops_tracker.create_job(
                    job_type="backfill",
                    job_family="pipeline",
                    title=f"Backfill {ticker_upper} ({years}y)",
                    trigger_source="api",
                    entity_scope="ticker",
                    ticker=ticker_upper,
                    metadata={"years": years, "process_documents": process_documents},
                )
                _ops_tracker.start_job(_ops_handle.job_id)
                _ops_job_id = _ops_handle.job_id
        except Exception:
            logger.warning("ops tracker init for backfill failed (non-fatal)", exc_info=True)
        existing_doc_count = (
            db.query(Document).filter(Document.ticker == ticker_upper).count()
        )
        discovery = discover_and_insert_documents(db, ticker=ticker, years=years)
        doc_ids = discovery["new_document_ids"]
        workers = (
            max(1, int(max_workers))
            if max_workers is not None
            else max(1, settings.backfill_concurrency)
        )
        processed, skipped_download, _extraction_failed, errors, ingestion_metrics = (
            _download_and_process_document_ids(
                doc_ids,
                process_documents,
                max_workers=workers,
            )
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
                "invalid_payloads": int(
                    ingestion_metrics.get("invalid_payloads", 0) or 0
                ),
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

        result = {
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
        # Complete ops job
        if _ops_job_id:
            try:
                from app.services.job_tracker import get_tracker

                _t = get_tracker()
                if _t is not None:
                    summary = f"Backfill {ticker_upper}: {processed} processed, {len(errors)} errors"
                    if errors:
                        _t.fail_job(_ops_job_id, summary)
                    else:
                        _t.record_progress(
                            _ops_job_id,
                            current=processed,
                            total=len(doc_ids),
                        )
                        _t.complete_job(_ops_job_id, summary=summary)
            except Exception:
                logger.warning("ops tracker completion for backfill failed (non-fatal)", exc_info=True)
        return result
    finally:
        db.close()
