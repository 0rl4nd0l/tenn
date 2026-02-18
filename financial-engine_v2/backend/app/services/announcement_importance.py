from __future__ import annotations

import shutil
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz

from app.models.documents import Document


ANNOUNCEMENT_TYPES = [
    "financial_performance",
    "operations_projects",
    "ownership_and_holders",
    "management_and_governance",
    "capital_structure_securities",
    "investor_communications",
    "regulatory_status",
    "other",
]

LEGACY_TYPE_DIRS = {
    "quarterly_cashflow_4c",
    "financial_results",
    "operations_update",
    "presentation_webinar",
    "substantial_holding",
    "director_management",
    "securities_capital_structure",
    "meeting_governance",
    "compliance_regulatory",
}

TYPE_KEYWORDS: dict[str, set[str]] = {
    "financial_performance": {
        "appendix 4c",
        "appendix 4d",
        "appendix 4e",
        "quarterly report",
        "quarterly activities",
        "annual report",
        "half year",
        "half-year",
        "interim report",
        "financial report",
        "results",
        "preliminary final report",
    },
    "operations_projects": {
        "activities report",
        "operational update",
        "production report",
        "resource update",
        "drilling update",
        "guidance",
        "project update",
        "trading update",
    },
    "investor_communications": {
        "investor presentation",
        "presentation",
        "webinar",
        "conference",
        "investor day",
    },
    "ownership_and_holders": {
        "substantial holder",
        "substantial holding",
        "becoming a substantial holder",
        "ceasing to be a substantial holder",
        "change in substantial holding",
        "change in director's interest",
    },
    "management_and_governance": {
        "change of director",
        "appointment of director",
        "resignation of director",
        "executive",
        "leadership",
        "ceo",
        "cfo",
        "notice of meeting",
        "proxy",
        "agm",
        "annual general meeting",
        "corporate governance",
        "constitution",
    },
    "capital_structure_securities": {
        "appendix 2a",
        "appendix 2b",
        "appendix 3x",
        "appendix 3y",
        "appendix 3z",
        "application for quotation",
        "quotation of securities",
        "issue of securities",
        "unquoted securities",
        "cleansing notice",
    },
    "regulatory_status": {
        "trading halt",
        "suspension",
        "reinstatement",
        "asx release",
    },
}

FINANCIAL_TEXT_MARKERS = {
    "income statement",
    "balance sheet",
    "cash flow",
    "operating cash",
    "revenue",
    "ebitda",
    "earnings per share",
    "net profit",
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _slug(value: str | None, max_len: int = 96) -> str:
    text = _norm(value)
    out = []
    dash = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            dash = False
        else:
            if not dash:
                out.append("-")
                dash = True
    s = "".join(out).strip("-")
    return (s[:max_len].strip("-") or "announcement")


def _date_token(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return "undated"


def _hits(text: str, keywords: set[str]) -> list[str]:
    return [kw for kw in keywords if kw in text]


def _extract_pdf_excerpt(pdf_path: str, max_pages: int = 2, max_chars: int = 12000) -> str:
    path = Path(pdf_path)
    if not path.exists():
        return ""

    chunks: list[str] = []
    total = 0
    with fitz.open(path) as doc:
        page_count = min(max_pages, doc.page_count)
        for page_index in range(page_count):
            page = doc[page_index]
            text = page.get_text("text") or ""
            if not text:
                continue
            remaining = max_chars - total
            if remaining <= 0:
                break
            take = text[:remaining]
            chunks.append(take)
            total += len(take)
            if total >= max_chars:
                break
    return "\n".join(chunks).lower()


def classify_announcement(
    *,
    title: str | None,
    doc_class: str | None,
    doc_subtype: str | None,
    pdf_excerpt: str | None,
) -> dict[str, Any]:
    title_n = _norm(title)
    class_n = _norm(doc_class)
    subtype_n = _norm(doc_subtype)
    text_n = _norm(pdf_excerpt)

    # Structural first: ASX subtype/class is the most reliable categorization signal.
    if subtype_n in {"4c", "4d", "4e"} or "appendix 4c" in title_n or "appendix 4d" in title_n or "appendix 4e" in title_n:
        announcement_type = "financial_performance"
        structural_hits = ["subtype_or_title_financial_appendix"]
    elif class_n in {"annual", "half_year"}:
        announcement_type = "financial_performance"
        structural_hits = ["class_financial_results"]
    else:
        announcement_type = "other"
        structural_hits = []

    keyword_hits: dict[str, list[str]] = {}
    if announcement_type == "other":
        for cand in ANNOUNCEMENT_TYPES:
            kws = TYPE_KEYWORDS.get(cand, set())
            if not kws:
                continue
            hits = _hits(title_n, kws)
            if hits:
                keyword_hits[cand] = hits
        if keyword_hits:
            announcement_type = max(keyword_hits.items(), key=lambda kv: len(kv[1]))[0]

    financial_text_hits = _hits(text_n, FINANCIAL_TEXT_MARKERS) if text_n else []
    if announcement_type == "other" and financial_text_hits:
        announcement_type = "financial_performance"

    score = (
        len(structural_hits) * 3
        + len(keyword_hits.get(announcement_type, [])) * 2
        + len(financial_text_hits)
    )

    return {
        "label": announcement_type,
        "announcement_type": announcement_type,
        "score": score,
        "signals": {
            "structural_hits": structural_hits,
            "keyword_hits": keyword_hits.get(announcement_type, []),
            "financial_text_hits": financial_text_hits[:8],
            "doc_class": class_n,
            "doc_subtype": subtype_n,
        },
    }


def _materialize_document_link(
    *,
    pdf_path: str,
    ticker: str,
    document_id: str,
    label: str,
    score: int,
    published_at: Any,
    title: str | None,
    output_root: Path,
    link_mode: str,
) -> dict[str, str]:
    source = Path(pdf_path).resolve()
    target_dir = output_root / ticker.upper() / label
    target_dir.mkdir(parents=True, exist_ok=True)
    priority = {name: idx + 1 for idx, name in enumerate(ANNOUNCEMENT_TYPES)}.get(label, 99)
    score_token = max(-99, min(99, int(score)))
    date_token = _date_token(published_at)
    title_slug = _slug(title)
    target_name = f"{priority:02d}_s{score_token:+03d}_{date_token}_{title_slug}_{document_id}.pdf"
    target = target_dir / target_name

    # Keep one materialized file per document per label to avoid duplicates across reruns.
    doc_suffix = f"_{document_id}.pdf"
    for candidate in target_dir.glob(f"*{doc_suffix}"):
        if candidate == target:
            continue
        if candidate.exists() or candidate.is_symlink():
            candidate.unlink()

    if target.exists() or target.is_symlink():
        target.unlink()

    method = link_mode
    if link_mode == "symlink":
        try:
            target.symlink_to(source)
        except OSError:
            shutil.copy2(source, target)
            method = "copy_fallback"
    else:
        shutil.copy2(source, target)
        method = "copy"

    return {"target_path": str(target), "materialized_via": method}


def _relocate_source_into_label_dir(
    *,
    source_path: Path,
    ticker: str,
    label: str,
) -> Path:
    # Keep sorted source docs under docs/<TICKER>/<announcement_type>/...
    ticker_root = source_path.parent
    known_dirs = set(ANNOUNCEMENT_TYPES) | LEGACY_TYPE_DIRS | {"high", "medium", "low", "irrelevant"}
    if ticker_root.name.lower() in known_dirs:
        ticker_root = ticker_root.parent

    target_dir = ticker_root / label
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source_path.name
    if source_path.resolve() == target.resolve():
        return source_path

    if target.exists() and target.resolve() != source_path.resolve():
        stem = target.stem
        suffix = target.suffix
        n = 1
        while True:
            candidate = target_dir / f"{stem}__{n}{suffix}"
            if not candidate.exists():
                target = candidate
                break
            n += 1

    source_path.rename(target)
    return target


def _prune_empty_legacy_dirs(ticker_root: Path) -> None:
    for name in ["high", "medium", "low", "irrelevant", *sorted(LEGACY_TYPE_DIRS)]:
        p = ticker_root / name
        if p.exists() and p.is_dir():
            try:
                next(p.iterdir())
            except StopIteration:
                p.rmdir()


def _purge_legacy_dirs(ticker_root: Path) -> None:
    for name in ["high", "medium", "low", "irrelevant", *sorted(LEGACY_TYPE_DIRS)]:
        p = ticker_root / name
        if p.exists() and p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def classify_documents_and_materialize(
    db,
    *,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
    limit: int = 0,
    output_root: str = "./data/asx/importance",
    include_pdf_text: bool = True,
    link_mode: str = "symlink",
    sort_source_docs: bool = True,
    only_unsorted: bool = False,
) -> dict[str, Any]:
    query = db.query(Document)
    if ticker:
        query = query.filter(Document.ticker == ticker.upper())
    if document_ids:
        uuid_ids = []
        for raw_id in document_ids:
            try:
                uuid_ids.append(uuid.UUID(str(raw_id)))
            except Exception:
                continue
        if uuid_ids:
            query = query.filter(Document.document_id.in_(uuid_ids))
        else:
            return {
                "output_root": str(Path(output_root)),
                "classified_count": 0,
                "skipped_count": 0,
                "by_type": {},
                "by_label": {},
                "link_mode": link_mode,
                "items": [],
                "error": "no valid UUID document_ids supplied",
            }
    query = query.order_by(Document.published_at.desc().nullslast())
    if limit and limit > 0:
        query = query.limit(limit)

    rows = query.all()
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    skipped = 0
    classified: list[dict[str, Any]] = []

    for row in rows:
        path = Path(row.pdf_path or "")
        marker = (row.pdf_sha256 or "").strip().lower()
        if not path.exists() or not marker or marker.startswith("blocked_"):
            skipped += 1
            continue
        if only_unsorted:
            docs_ticker_root = (Path("./data/asx/docs") / (row.ticker or "").upper()).resolve()
            try:
                rel = path.resolve().relative_to(docs_ticker_root)
                parts = rel.parts
                if len(parts) >= 2 and parts[0] in ANNOUNCEMENT_TYPES:
                    skipped += 1
                    continue
            except Exception:
                pass

        excerpt = _extract_pdf_excerpt(str(path)) if include_pdf_text else ""
        decision = classify_announcement(
            title=row.title,
            doc_class=row.doc_class,
            doc_subtype=row.doc_subtype,
            pdf_excerpt=excerpt,
        )
        if sort_source_docs:
            try:
                moved_path = _relocate_source_into_label_dir(
                    source_path=path,
                    ticker=row.ticker,
                    label=decision["label"],
                )
                if str(moved_path) != (row.pdf_path or ""):
                    row.pdf_path = str(moved_path)
                    db.commit()
                path = moved_path
            except Exception:
                db.rollback()
        materialized = _materialize_document_link(
            pdf_path=str(path),
            ticker=row.ticker,
            document_id=str(row.document_id),
            label=decision["label"],
            score=decision["score"],
            published_at=row.published_at,
            title=row.title,
            output_root=root,
            link_mode=link_mode,
        )

        counts[decision["label"]] += 1
        classified.append(
            {
                "document_id": str(row.document_id),
                "ticker": row.ticker,
                "title": row.title,
                "label": decision["label"],
                "score": decision["score"],
                "signals": decision["signals"],
                "pdf_path": str(path),
                "target_path": materialized["target_path"],
            }
        )

    if ticker:
        docs_ticker_root = Path("./data/asx/docs") / ticker.upper()
        if docs_ticker_root.exists():
            _prune_empty_legacy_dirs(docs_ticker_root)
        importance_ticker_root = root / ticker.upper()
        if importance_ticker_root.exists():
            # Output mirror is generated data; remove legacy importance buckets during migration.
            _purge_legacy_dirs(importance_ticker_root)

    return {
        "output_root": str(root),
        "classified_count": len(classified),
        "skipped_count": skipped,
        "by_type": dict(counts),
        "by_label": dict(counts),
        "link_mode": link_mode,
        "sort_source_docs": sort_source_docs,
        "items": classified,
    }
