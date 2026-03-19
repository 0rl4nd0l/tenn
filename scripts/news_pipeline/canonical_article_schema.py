"""
Canonical article schema for the news substrate (Layer 2).

All ingest paths that feed the single RAG builder must produce records that
validate against this schema. See docs/architecture/15_news_substrate.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Canonical field names (output of normalization)
CANONICAL_KEYS = (
    "document_id",
    "ticker",
    "title",
    "body",
    "source",
    "published_at",
    "corpus",
    "url",
    "provider",
    "topic",
    "description",
)

# Required: at least one identifier, content, and time.
# We accept multiple input key names; validator checks that after mapping we have required canonical keys.
REQUIRED_CANONICAL = ("document_id", "published_at")
REQUIRED_CONTENT = ("title", "body")  # at least one non-empty

# Input key aliases (first match wins when normalizing)
ID_ALIASES = ("document_id", "record_id", "id", "_id", "guid", "article_id")
TITLE_ALIASES = ("title", "headline")
BODY_ALIASES = ("body", "text", "content")
SOURCE_ALIASES = ("source", "source_name", "publisher", "site_name")
PUBLISHED_ALIASES = ("published_at", "published_at_utc", "date", "publish_date")
URL_ALIASES = ("url", "link", "canonical_url")


def _first_non_empty(row: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    extra = row.get("extra_fields")
    if isinstance(extra, dict):
        for k in keys:
            v = extra.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
    return ""


def normalize_to_canonical(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a raw ingest row to canonical keys (best-effort)."""
    doc_id = _first_non_empty(row, *ID_ALIASES)
    if not doc_id and (_first_non_empty(row, *URL_ALIASES) or _first_non_empty(row, *TITLE_ALIASES)):
        import hashlib
        blob = _first_non_empty(row, *URL_ALIASES) or _first_non_empty(row, *TITLE_ALIASES)
        doc_id = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:24]
    return {
        "document_id": doc_id,
        "ticker": _first_non_empty(row, "ticker", "tickers", "stocks"),
        "title": _first_non_empty(row, *TITLE_ALIASES),
        "body": _first_non_empty(row, *BODY_ALIASES),
        "source": _first_non_empty(row, *SOURCE_ALIASES),
        "published_at": _first_non_empty(row, *PUBLISHED_ALIASES),
        "corpus": _first_non_empty(row, "corpus") or "",
        "url": _first_non_empty(row, *URL_ALIASES),
        "provider": _first_non_empty(row, "provider"),
        "topic": _first_non_empty(row, "topic", "category"),
        "description": _first_non_empty(row, "description"),
    }


def validate_canonical_article(row: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate a raw or normalized article row against the canonical schema.

    Args:
        row: Raw ingest row (will be normalized for check) or already canonical dict.
        strict: If True, require both title and body non-empty; else at least one.

    Returns:
        (ok, list of error messages).
    """
    errors: List[str] = []
    canonical = normalize_to_canonical(row) if not all(k in row for k in ("document_id", "published_at")) else row

    if not (canonical.get("document_id") or "").strip():
        errors.append("missing document_id (or id/record_id/guid/url)")

    if not (canonical.get("published_at") or "").strip():
        errors.append("missing published_at (or date/publish_date)")

    title = (canonical.get("title") or "").strip()
    body = (canonical.get("body") or "").strip()
    if strict and (not title or not body):
        errors.append("strict: both title and body required")
    elif not title and not body:
        errors.append("missing content (need at least title or body)")

    return (len(errors) == 0, errors)


def validate_canonical_article_strict(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate with strict=True (both title and body required)."""
    return validate_canonical_article(row, strict=True)
