"""
multipass_extraction.py — 4-pass financial metric extraction pipeline.

Passes:
  1. Document Classifier (LLM): period, scale, currency
  2. Table Locator (deterministic): label tables by financial statement type
  3a. Metric Extractor (LLM): extract numbers from labelled tables
  3b. Narrative Extractor (LLM): extract risk/guidance from prose
  4. Reconciler (deterministic): merge, resolve conflicts, build final payload

Entry point: run_multipass_extraction(pdf_path, doc_metadata, llm_client)
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import Any, Optional, Sequence

from dateutil import parser as dtparser

from app.services.asx_extraction_contracts import (
    classify_and_select_extraction_contract,
    evaluate_contract_routing,
)
from app.services.extraction_run_observability import ExtractionRunObserver
from app.services.financial_metric_contract import CANONICAL_METRIC_FIELDS
from app.services.prompt_registry import PromptBundle, register_bundle, resolve

logger = logging.getLogger(__name__)


def parse_period_end(s: str | None) -> date | None:
    """Parse a period-end date string into a date object. Returns None on failure."""
    if not s:
        return None
    try:
        return dtparser.parse(s).date()
    except Exception:
        return None


def _derive_period_start(
    period_end: date | None, period_type: str | None
) -> date | None:
    """
    Derive period_start deterministically from period_end and period_type.

    Annual  (A): period_end − 12 months + 1 day  (e.g. 2024-06-30 → 2023-07-01)
    Half-year (H): period_end − 6 months + 1 day  (e.g. 2024-12-31 → 2024-07-01)
    Quarterly (Q): period_end − 3 months + 1 day  (e.g. 2024-09-30 → 2024-07-01)

    Returns None when either input is absent or period_type is unrecognised.
    """
    from dateutil.relativedelta import relativedelta

    if period_end is None or period_type not in ("A", "H", "Q"):
        return None
    months = {"A": 12, "H": 6, "Q": 3}[period_type]
    return period_end - relativedelta(months=months) + timedelta(days=1)


EXTRACTOR_VERSION = "docling_multipass_v1"

# Compatibility list used throughout the extractor; authority lives in the
# typed financial metric contract.
METRIC_FIELDS = list(CANONICAL_METRIC_FIELDS)

# Source priority for reconciliation (index 0 = highest priority)
SOURCE_PRIORITY = [
    "income_statement",
    "cashflow_statement",
    "net_debt_note",
    "balance_sheet",
    "share_capital",
    "market_update_table",
    "highlights",
]

SCALE_MULTIPLIERS = {
    "thousands": 1_000,
    "millions": 1_000_000,
    "billions": 1_000_000_000,
    "trillions": 1_000_000_000_000,
    "units": 1,
    "unknown": 1,
}

_ACCOUNTING_NUMBER_SUFFIX_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "thousands": 1_000,
    "m": 1_000_000,
    "mn": 1_000_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
    "billions": 1_000_000_000,
    "t": 1_000_000_000_000,
    "tn": 1_000_000_000_000,
    "trillion": 1_000_000_000_000,
    "trillions": 1_000_000_000_000,
}

_ACCOUNTING_NUMBER_RE = re.compile(
    r"^(?P<currency>(?:[A-Z]{1,3}\$|[A-Z]{3}|\$)\s*)?"
    r"(?P<num>[+-]?(?:\d+(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"\s*(?P<suffix>k|thousands?|mn|m|millions?|bn|b|billions?|tn|t|trillions?)?$",
    re.IGNORECASE,
)

_MARKET_UPDATE_HINT_RE = re.compile(r"\bmarket\s+update\b", re.IGNORECASE)
_MARKET_UPDATE_NET_REVENUE_LABELS = {"netrevenue", "netrev"}

SOURCE_DOCUMENT_CLASS_DEFINITIONS = {
    "financial_report": (
        "Source metadata has explicit annual, half-year, quarterly, or appendix "
        "financial-report evidence and may proceed through normal extraction gates."
    ),
    "advisory_only_document": (
        "Source metadata identifies an advisory-only announcement; it must not "
        "enter canary selection or metric extraction."
    ),
    "meeting_or_proxy_notice": (
        "Source metadata identifies meeting/proxy material, not a financial "
        "report; it must not enter canary selection or metric extraction."
    ),
    "board_change_notice": (
        "Source metadata identifies a board-change notice, not a financial "
        "report; it must not enter canary selection or metric extraction."
    ),
    "operational_project_update": (
        "Source metadata identifies an operational project update, not a "
        "financial report; it must not enter canary selection or metric extraction."
    ),
    "share_sale_or_gross_proceeds_announcement": (
        "Source metadata identifies a share-sale or gross-proceeds announcement, "
        "not a financial report; it must not enter canary selection or metric "
        "extraction."
    ),
    "pre_results_segment_re_presentation": (
        "Source metadata identifies a pre-results segment re-presentation "
        "document, not a financial report; it must not enter canary selection or "
        "metric extraction."
    ),
    "director_interest_notice": (
        "Source metadata identifies a director-interest securities notice, not a "
        "financial report; it must not enter canary selection or metric extraction."
    ),
    "webcast_details_notice": (
        "Source metadata identifies webcast-details logistics, not a financial "
        "report; it must not enter canary selection or metric extraction."
    ),
    "unknown_document": (
        "Source metadata is insufficient to classify the document; normal "
        "downstream gates still decide whether extraction is safe."
    ),
}


@dataclass
class MultipassResult:
    status: str  # "ok" | "ok_low_confidence" | "failed"
    payload: dict  # matches _upsert_financial_rows contract
    sections: list[dict]  # prose sections for Qdrant chunking
    error: Optional[str] = None


@dataclass(frozen=True)
class SourceDocumentClassification:
    document_class: str
    extraction_candidate_allowed: bool
    canary_candidate_allowed: bool
    reason: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_class": self.document_class,
            "extraction_candidate_allowed": self.extraction_candidate_allowed,
            "canary_candidate_allowed": self.canary_candidate_allowed,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "definition": SOURCE_DOCUMENT_CLASS_DEFINITIONS.get(
                self.document_class,
                SOURCE_DOCUMENT_CLASS_DEFINITIONS["unknown_document"],
            ),
        }


# ---------------------------------------------------------------------------
# Scale detection (deterministic, from table headers)
# ---------------------------------------------------------------------------

import re as _re

_SCALE_PATTERNS: list[tuple[str, str]] = [
    # Thousands: $'000, $A'000, $000 (ASX Appendix 5B uses "$A'000" notation)
    (r"\$A?['\u2018\u2019]?000[,s]?\b|\bthousands?\b", "thousands"),
    # Millions: spelled-out, $'000,000, compact $M / A$M notation (common in AU mining)
    (r"\$A?['\u2018\u2019]?000,000|\bmillions?\b|A?\$[Mm]\b|\$m\b", "millions"),
    (r"\bbillions?\b", "billions"),
    (
        r"(?:(?<!\w)RP\.?\s*trillions?\b|\bIDR\s*trillions?\b|"
        r"\brupiah\s*trillions?\b|\btrillions?\s+of\s+(?:rupiah|IDR)\b)",
        "trillions",
    ),
]
_SOURCE_TEXT_THOUSANDS_SCALE_RE = _re.compile(
    r"\$A?['\u2018\u2019]?000[,s]?\b|\$\s*000[,s]?\b",
    _re.IGNORECASE,
)

_RAW_DOLLAR_UNIT_RE = _re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:A\$|\$A|\$|AUD(?:\s+dollars?)?)"
    r"(?!\s*(?:'?\d{3}|0{3}|[mMbB]\b|bn\b|millions?\b|billions?\b|trillions?\b))"
    r"(?=\s|$|\)|,|;|:)",
    _re.IGNORECASE,
)
_STATEMENT_PAGE_SCALE_CAPTION_RE = _re.compile(
    r"\b(?:"
    r"consolidated\s+)?"
    r"(?:statement\s+of\s+(?:comprehensive\s+)?income|"
    r"statement\s+of\s+cash\s+flows?|"
    r"statement\s+of\s+financial\s+position|"
    r"balance\s+sheet)"
    r"\b",
    _re.IGNORECASE,
)
_SCALE_UNIT_ROW_CONTEXT_RE = _re.compile(
    r"^(?:notes?|note|period|current|prior|comparative|fy\d{2,4}|h[12]|"
    r"q[1-4]|\d{4}|20\d{2}|19\d{2}|as at|for the year|year ended|"
    r"half year|six months|quarter)$",
    _re.IGNORECASE,
)
_SCALE_UNIT_ROW_CONTEXT_PHRASE_RE = _re.compile(
    r"\b(?:for\s+the\s+)?(?:year|half[-\s]?year|six\s+months|quarter)\s+ended\b"
    r"|\bas\s+at\b"
    r"|\b(?:current|prior|comparative)\s+(?:period|year|half|quarter)\b"
    r"|\b(?:30|31)\s+(?:january|march|june|september|december)\b",
    _re.IGNORECASE,
)

_MILLION_UNIT_BOUNDARY = r"(?=\s|$|\)|%|,|;|:)"
_EXPLICIT_CURRENCY_MILLION_PATTERNS: list[tuple[str, str]] = [
    (
        rf"\b(?:AUD)\s*[Mm]{_MILLION_UNIT_BOUNDARY}"
        rf"|\b(?:AUD)\s+millions?\b"
        rf"|(?<!\w)(?:A\$|\$A)\s*[Mm]{_MILLION_UNIT_BOUNDARY}"
        rf"|(?<!\w)(?:A\$|\$A)\s+millions?\b",
        "AUD",
    ),
    (
        rf"\b(?:USD)\s*[Mm]{_MILLION_UNIT_BOUNDARY}"
        rf"|\b(?:USD)\s+millions?\b"
        rf"|(?<!\w)(?:US\$|\$US)\s*[Mm]{_MILLION_UNIT_BOUNDARY}"
        rf"|(?<!\w)(?:US\$|\$US)\s+millions?\b",
        "USD",
    ),
]

_CURRENCY_PATTERNS: list[tuple[str, str]] = [
    # AUD markers: A$, $A, AUD, Australian dollar(s)
    (r"\b(?:A\$|\$A|AUD|AUSTRALIAN\s+DOLLARS?)\b", "AUD"),
    # USD markers: US$, $US, USD, United States dollar(s)
    (r"\b(?:US\$|\$US|USD|UNITED\s+STATES\s+DOLLARS?)\b", "USD"),
    # GBP markers: £ (symbol may precede scale like £'000), GBP, British pound(s), sterling.
    # (?<!\w) avoids matching mid-word; symbol alternatives don't need a trailing \b since £
    # is itself non-word and ASX column headers use e.g. "£'000" or "£M".
    (r"(?:(?<!\w)£|\b(?:GBP|BRITISH\s+POUNDS?|STERLING)\b)", "GBP"),
    # EUR markers: € (similar to £), EUR, euro(s)
    (r"(?:(?<!\w)€|\b(?:EUR|EUROS?)\b)", "EUR"),
    # CAD markers: CA$, $CA (may appear as "CA$'000" or "CA$M"), CAD, Canadian dollar(s)
    (r"(?:(?<!\w)(?:CA\$|\$CA)|\b(?:CAD|CANADIAN\s+DOLLARS?)\b)", "CAD"),
    # NZD markers: NZ$, $NZ (may appear as "NZ$'000" or "NZ$M"), NZD, New Zealand dollar(s)
    (r"(?:(?<!\w)(?:NZ\$|\$NZ)|\b(?:NZD|NEW\s+ZEALAND\s+DOLLARS?)\b)", "NZD"),
    # CNY/CNH markers: CNY, CNH, RMB, yuan, renminbi (all word-bounded; no symbol in use)
    (r"\b(?:CNY|CNH|RMB|YUAN|RENMINBI)\b", "CNY"),
    # Indonesian rupiah markers: IDR, Rp, rupiah.
    (r"(?:(?<!\w)RP\.?(?!\w)|\b(?:IDR|RUPIAH|INDONESIAN\s+RUPIAH)\b)", "IDR"),
]

_ROW_LEVEL_CURRENCY_CONTEXT_HINTS: tuple[str, ...] = (
    "statement",
    "income",
    "cash flow",
    "financial position",
    "balance sheet",
    "share capital",
    "financial highlights",
    "summary",
)


def _table_allows_extended_unit_scan(table) -> bool:
    surfaces: list[str] = []
    if table.headers:
        surfaces.append(" ".join(str(h) for h in table.headers))
    if getattr(table, "caption", None):
        surfaces.append(str(table.caption))
    combined = " ".join(surfaces).lower()
    return bool(_re.search(r"\bappendix\s+4[de]\b", combined, _re.IGNORECASE))


def _table_allows_row_level_currency_scan(table) -> bool:
    """
    Only treat row text as currency evidence for canonical statement/highlight tables.

    Generic note tables often mention foreign-denominated debt instruments
    ("Euro bond", "JPY private placement") inside body rows; counting those rows as
    document currency evidence can incorrectly override the filing currency.
    """
    surfaces: list[str] = []
    if table.headers:
        surfaces.append(" ".join(str(h) for h in table.headers))
    if getattr(table, "caption", None):
        surfaces.append(str(table.caption))
    combined = " ".join(surfaces).lower()
    return any(hint in combined for hint in _ROW_LEVEL_CURRENCY_CONTEXT_HINTS)


def _explicit_currency_million_hits(text: str) -> dict[str, int]:
    hits: dict[str, int] = {}
    for pattern, currency in _EXPLICIT_CURRENCY_MILLION_PATTERNS:
        matches = _re.findall(pattern, text, _re.IGNORECASE)
        if matches:
            hits[currency] = hits.get(currency, 0) + len(matches)
    return hits


def _dominant_currency_from_hits(hits: dict[str, int]) -> str | None:
    if not hits:
        return None
    if len(hits) > 1:
        return ""
    return next(iter(hits))


def _detect_scale_marker_in_text(text: str) -> str:
    for pattern, scale in _SCALE_PATTERNS:
        if _re.search(pattern, text, _re.IGNORECASE):
            return scale
    return "unknown"


def _is_scale_unit_context_cell(cell: Any) -> bool:
    text = " ".join(str(cell or "").split()).strip()
    if not text:
        return True
    return bool(
        _SCALE_UNIT_ROW_CONTEXT_RE.search(text)
        or _SCALE_UNIT_ROW_CONTEXT_PHRASE_RE.search(text)
    )


def _scale_marker_cell_is_unit_context(cell: Any) -> bool:
    text = " ".join(str(cell or "").split()).strip()
    for pattern, _scale in _SCALE_PATTERNS:
        text = _re.sub(pattern, " ", text, flags=_re.IGNORECASE)
    text = _re.sub(
        r"(?<!\w)(?:A\$|\$A|US\$|\$US|\$|AUD|USD|RP\.?)(?!\w)",
        " ",
        text,
        flags=_re.IGNORECASE,
    )
    text = _re.sub(r"[\(\)\[\],;:]+", " ", text)
    text = " ".join(text.split()).strip()
    return _is_scale_unit_context_cell(text)


def _detect_scale_from_unit_rows(rows: list[list[Any]] | None) -> str:
    for row in rows or []:
        nonempty = [str(cell).strip() for cell in row if str(cell).strip()]
        if not nonempty:
            continue
        detected_scale = "unknown"
        non_unit_cells: list[str] = []
        for cell in nonempty:
            cell_scale = _detect_scale_marker_in_text(cell)
            if cell_scale != "unknown":
                if _scale_marker_cell_is_unit_context(cell):
                    detected_scale = cell_scale
                else:
                    non_unit_cells.append(cell)
                continue
            if _is_scale_unit_context_cell(cell):
                continue
            non_unit_cells.append(cell)
        if detected_scale != "unknown" and not non_unit_cells:
            return detected_scale
    return "unknown"


def _detect_explicit_currency_million_header(tables) -> str | None:
    hits: dict[str, int] = {}
    for table in tables[:20]:
        surfaces: list[str] = []
        if table.headers:
            surfaces.append(" ".join(str(h) for h in table.headers))
        if getattr(table, "caption", None):
            surfaces.append(str(table.caption))
        if _table_allows_extended_unit_scan(table):
            for row in (table.rows or [])[:20]:
                surfaces.append(" ".join(str(cell) for cell in row))

        combined = " ".join(surfaces)
        for currency, count in _explicit_currency_million_hits(combined).items():
            hits[currency] = hits.get(currency, 0) + count

    return _dominant_currency_from_hits(hits)


def _detect_scale_from_table(table) -> str:
    """Detect an explicit scale marker from one table's local source text."""
    surfaces: list[str] = []
    if table.headers:
        surfaces.append(" ".join(str(h) for h in table.headers))
    if getattr(table, "caption", None):
        surfaces.append(str(table.caption))

    combined = " ".join(surfaces)
    detected = _detect_scale_marker_in_text(combined)
    if detected != "unknown":
        return detected

    # Some parser paths fragment statement headings so the source-unit row
    # (for example: "Notes | $m | $m") lands below narrative rows. Only accept
    # rows that are unit/header context, not arbitrary prose rows.
    return _detect_scale_from_unit_rows(table.rows or [])


def _detect_scale_from_tables(tables) -> str:
    """
    Scan table headers, captions, and first few body rows for scale indicators
    ($'000, millions, etc.).
    Returns the first match, or 'unknown' if none found.
    ASX reports encode scale in column headings (e.g. "31 Dec 2025 $'000"),
    table captions, or sub-header rows just below the column headers.
    """
    for table in tables[:15]:
        detected = _detect_scale_from_table(table)
        if detected != "unknown":
            return detected

    for table in tables[:15]:
        surfaces: list[str] = []
        if table.headers:
            surfaces.append(" ".join(str(h) for h in table.headers))
        if getattr(table, "caption", None):
            surfaces.append(table.caption)
        if _table_allows_extended_unit_scan(table):
            for row in (table.rows or [])[:20]:
                surfaces.append(" ".join(str(cell) for cell in row))

        if _explicit_currency_million_hits(" ".join(surfaces)):
            return "millions"

    # Scale Policy V1: a plain currency/$ column unit is an explicit raw-dollar
    # table unit, not "unknown". This is intentionally checked after all
    # thousands/millions/billions patterns so scaled columns still win.
    for table in tables[:15]:
        surfaces: list[str] = []
        if table.headers:
            surfaces.append(" ".join(str(h) for h in table.headers))
        if getattr(table, "caption", None):
            surfaces.append(str(table.caption))
        for row in (table.rows or [])[:3]:
            surfaces.append(" ".join(str(cell) for cell in row))
        if _RAW_DOLLAR_UNIT_RE.search(" ".join(surfaces)):
            return "units"
    return "unknown"


def _detect_scale_from_source_text(text: Any) -> str:
    """Detect only explicit document-level scale markers from source text."""
    if _SOURCE_TEXT_THOUSANDS_SCALE_RE.search(str(text or "")):
        return "thousands"
    return "unknown"


def _detect_scale_from_statement_page_fragments(fragments: list[str]) -> str:
    detected_scales = {
        scale
        for fragment in fragments
        if (scale := _detect_scale_marker_in_text(fragment)) != "unknown"
        and _scale_marker_cell_is_unit_context(fragment)
    }
    if len(detected_scales) == 1:
        return next(iter(detected_scales))
    return "unknown"


def _detect_scale_from_statement_page_text(
    sections: list[dict] | None, tables: Any
) -> str:
    """
    Recover explicit statement-page scale when a parser drops the unit row.

    PyMuPDF table extraction can omit standalone "$M" / "$'000" column-unit rows
    from formal statement tables while preserving them in the page text. Limit this
    fallback to pages whose extracted table captions identify canonical statements,
    and abstain if those statement pages disagree on scale.
    """
    statement_pages: set[int] = set()
    for table in tables or []:
        surfaces: list[str] = []
        if getattr(table, "caption", None):
            surfaces.append(str(table.caption))
        if getattr(table, "headers", None):
            surfaces.append(" ".join(str(h) for h in table.headers))
        if not _STATEMENT_PAGE_SCALE_CAPTION_RE.search(" ".join(surfaces)):
            continue
        try:
            page = int(getattr(table, "page_number", 0))
        except (TypeError, ValueError):
            continue
        if page > 0:
            statement_pages.add(page)

    if not statement_pages:
        return "unknown"

    page_text: dict[int, list[str]] = {page: [] for page in statement_pages}
    for section in sections or []:
        try:
            page = int(section.get("page"))
        except (TypeError, ValueError):
            continue
        if page in page_text:
            text = str(section.get("text") or "").strip()
            if text:
                page_text[page].append(text)

    detected_scales = set()
    for page in sorted(statement_pages):
        scale = _detect_scale_from_statement_page_fragments(page_text.get(page, []))
        if scale != "unknown":
            detected_scales.add(scale)
    if len(detected_scales) == 1:
        return next(iter(detected_scales))
    return "unknown"


def _detect_scale_from_openability_phrase(text: Any) -> str:
    """Detect explicit scale markers captured by openability diagnostics."""
    value = str(text or "")
    for pattern, scale in _SCALE_PATTERNS:
        if _re.search(pattern, value, _re.IGNORECASE):
            return scale
    return "unknown"


def _detect_currency_from_tables(tables) -> str | None:
    """
    Detect a dominant document currency from table headers/captions/body rows.

    Returns a 3-letter currency code when one currency has clear evidence,
    an empty string for conflicting explicit evidence, and None when there is
    no evidence. Row-level evidence is limited to canonical
    statement/highlight tables so foreign-currency note text does not override
    the filing currency.
    """
    explicit_header_currency = _detect_explicit_currency_million_header(tables)
    if explicit_header_currency is not None:
        return explicit_header_currency

    hits: dict[str, int] = {}
    for table in tables[:20]:
        surfaces: list[str] = []
        if table.headers:
            surfaces.append(" ".join(str(h) for h in table.headers))
        if getattr(table, "caption", None):
            surfaces.append(str(table.caption))
        if _table_allows_row_level_currency_scan(table):
            for row in (table.rows or [])[:8]:
                surfaces.append(" ".join(str(cell) for cell in row))

        combined = " ".join(surfaces)
        for pattern, currency in _CURRENCY_PATTERNS:
            matches = _re.findall(pattern, combined, _re.IGNORECASE)
            if matches:
                hits[currency] = hits.get(currency, 0) + len(matches)

    return _dominant_currency_from_hits(hits)


# ---------------------------------------------------------------------------
# Pass 1 — Document Classifier
# ---------------------------------------------------------------------------

_PASS1_PROMPT = """You are a financial document classifier. Output ONLY valid JSON.

Given the document title and first-page text, extract:
- report_type: one of "A" (annual), "H" (half-year), "Q" (quarterly), or null
- period_end: the period end date as "YYYY-MM-DD", or null
- currency: three-letter currency code (e.g. "AUD"), or null
- scale: one of "thousands", "millions", "billions", "trillions", "units", or "unknown"
- classifier_confidence: float 0.0-1.0 (how confident you are in the above)

Schema:
{{
  "report_type": "A|H|Q|null",
  "period_end": "YYYY-MM-DD|null",
  "currency": "AUD|USD|...|null",
  "scale": "thousands|millions|billions|trillions|units|unknown",
  "classifier_confidence": 0.0
}}

Example — half-year report ending Dec 2025:
{{"report_type": "H", "period_end": "2025-12-31", "currency": "AUD", "scale": "thousands", "classifier_confidence": 0.92}}

Title: {title}
First page text:
{first_page_text}
"""


def _run_pass1_classifier(
    title: str,
    first_page_text: str,
    llm_client,
    *,
    prompt_bundle: PromptBundle | None = None,
    model_override: str | None = None,
) -> dict:
    """
    Pass 1: classify document type, period, currency, and scale.
    Returns dict with keys: report_type, period_end, currency, scale, classifier_confidence.
    """
    bundle = prompt_bundle or resolve("default")
    prompt = bundle.pass1.format(
        title=(title or "")[:200],
        first_page_text=(first_page_text or "")[:2000],  # first page, capped for safety
    )
    result = _llm_json_call(prompt, llm_client, max_tokens=256, model_override=model_override)
    # Normalise
    result.setdefault("report_type", None)
    result.setdefault("period_end", None)
    result.setdefault("currency", None)
    result.setdefault("scale", "unknown")
    if not result.get("scale"):
        result["scale"] = "unknown"
    result.setdefault("classifier_confidence", 0.0)
    return result


# ---------------------------------------------------------------------------
# Pass 2 — Table Locator (deterministic)
# ---------------------------------------------------------------------------

_TABLE_KEYWORDS: dict[str, list[str]] = {
    "cashflow_statement": [
        "cash flow",
        "cash from operations",
        "operating activities",
        "financing activities",
        "investing activities",
        "net cash",
        "cash at end",
        "cash generated from operations",  # BHP-style formal CF statement row label
    ],
    "income_statement": [
        "revenue",
        "profit",
        "earnings before",
        "ebit",
        "net profit",
        "profit after tax",
        "income statement",
        "statement of profit",
        "profit before taxation",  # formal income statement row (not in summaries)
        "income tax expense",  # formal income statement row
        "income tax",  # "Income tax (expense)/benefit" — handles parenthetical variants
        "from operations",  # "PROFIT/(LOSS) FROM OPERATIONS" — consolidated IS row
        "finance costs",  # formal IS row — absent from segment breakdowns
        "depreciation and amortisation",  # formal IS expense row — absent from segment tables
        "other comprehensive",  # OCI section — only in full IS, never in EBITDA recons
        "operating income",  # banking: ANZ uses "Operating income" not "Revenue"
        "net interest income",  # banking: core revenue line in consolidated IS
        "operating expenses",  # formal IS row — distinguishes full IS from segment recons
        # These keywords also appear in CF statements but do NOT cause cross-contamination:
        # each table is scored independently per statement type. A CF table may score 3
        # for income_statement, but the real IS scores 7+ because it has BOTH the P&L
        # keywords AND the OCI/tax/depreciation rows. Verified across all 6 fixtures:
        # MIN (pg14), BHP (pg44), RMS (pg20), SEG (pg12) all correctly selected.
    ],
    "balance_sheet": [
        "total assets",
        "current assets",
        "shareholders equity",
        "net assets",
        "total liabilities",
        "balance sheet",
        "statement of financial position",
        "non-current assets",  # formal balance sheet section
        "total equity",  # formal balance sheet row
    ],
    "share_capital": [
        "ordinary shares",
        "number of shares",
        "number of securities",
        "number of units",
        "no. of securities",
        "no of securities",
        "no. of units",
        "no of units",
        "shares on issue",
        "securities on issue",
        "units on issue",
        "shares issued",
        "stapled securities",
        "share capital",
        "shares at end",
        "weighted average number of shares",  # EPS note table
        "basic earnings per ordinary share",  # EPS note table
    ],
    "highlights": [
        "highlights",
        "key metrics",
        "summary",
        "at a glance",
        "key financials",
        "key information",  # Appendix 4D "Key Information" table (has EBIT, EBITDA labeled)
        "results for announcement",  # Appendix 4D summary tables — header bonus from _STATEMENT_HEADERS can fire
    ],
}

_POINT_IN_TIME_TABLE_MARKERS = ("as at", "at 31", "at 30", "at year end")
_NET_DEBT_DETAIL_DEBT_MARKERS = (
    "interest bearing liabilities",
    "borrowings",
    "gross debt",
    "debt facilities",
)
_NET_DEBT_DETAIL_CASH_MARKERS = ("cash and cash equivalents",)
_NET_DEBT_DETAIL_ADJUSTMENT_MARKERS = (
    "derivative",
    "net debt management",
    "index linked freight",
    "index-linked freight",
    "lease liabil",
)

# High-confidence header phrases — matching any grants a large bonus score so
# these tables win decisively over footnote/note tables with incidental keyword matches.
_STATEMENT_HEADERS: dict[str, list[str]] = {
    "cashflow_statement": ["statement of cash flows", "cash flow statement"],
    "income_statement": [
        "income statement",
        "statement of profit",
        "statement of comprehensive income",
    ],
    "balance_sheet": ["balance sheet", "statement of financial position"],
    "share_capital": [
        "number of shares",
        "number of securities",
        "number of units",
        "no. of securities",
        "no. of units",
        "weighted average",
    ],
    "highlights": ["appendix 4d", "results for announcement"],
}
_HEADER_BONUS = 10

# Minimum score for a table to be included in cashflow_statement merge.
# Score of 2 means at least 2 keyword matches (e.g. "operating activities" + "net cash")
# or 1 keyword + other body-text matches.  This avoids merging unrelated tables
# that only incidentally mention a single CF keyword.
_CF_MERGE_THRESHOLD = 2

# Cash-flow-specific phrases that disqualify a table from claiming the
# income_statement or balance_sheet slot.  ASX Appendix 5B documents have a
# single cash-flow statement split across several tables; those tables contain
# keywords like "income tax" and "non-current assets" that score well for IS/BS
# but are not actual income statements or balance sheets.  Checking against
# caption + headers is sufficient: every 5B table carries "statement of cash
# flows" or "cash flows from" in its header row, which never appears in a real
# income statement or balance sheet.
_CF_DISQUALIFY_PHRASES = [
    "cash flow",
    "statement of cash flows",
    "cash flows from",
    "appendix 5b",
]

# Segment breakdown tables (e.g. "Operating segments" in notes) should not claim
# the income_statement slot — they are divisional splits, not the consolidated IS.
_SEGMENT_DISQUALIFY_PHRASES = [
    "operating segments",
    "segment reporting",
    "reportable segments",
]

# Closed-group deed notes can embed a full-looking "statement of comprehensive
# income" table that is not the consolidated group truth surface.
_INCOME_STATEMENT_DISQUALIFY_PHRASES = [
    "deed of cross guarantee",
    "closed group",
    "retained earnings",
    "financial report contents",
]

_FORMAL_STATEMENT_SLOT_LABELS = (
    "income_statement",
    "cashflow_statement",
    "balance_sheet",
)

_STATEMENT_SLOT_DISQUALIFY_PHRASES = [
    "independentauditorsreviewreport",
    "independentauditorreviewreport",
    "independentauditorsreview",
    "independentauditorreview",
    "reportonthehalfyearfinancialreport",
    "auditorsresponsibilitiesforthereview",
]


def _merge_cf_tables(
    candidates: list[tuple[int, Any]],
) -> Any:
    """
    Merge multiple cashflow_statement candidate tables into one synthetic table.

    ASX Appendix 5B documents split the cash flow statement across several tables
    (sections 1–3 detail, section 4 reconciliation, section 5 bank balance).
    Docling parses each section as a separate table.  This function concatenates
    their rows (sorted by page number, then original order) so the LLM sees
    all cash-flow line items in one Pass 3a prompt.

    Duplicate header rows (e.g. repeated "Consolidated statement of cash flows")
    are deduplicated to keep the prompt concise.
    """
    from app.services.docling_extract import DoclingTable

    # Sort by page, preserving original order for same-page tables
    ordered = sorted(candidates, key=lambda x: x[1].page_number)

    # Use the headers from the highest-scoring table (most informative column headers)
    best_table = max(candidates, key=lambda x: x[0])[1]
    best_headers = best_table.headers
    best_raw_header_rows = list(
        getattr(best_table, "raw_header_rows", None) or [best_headers]
    )
    best_page = ordered[0][1].page_number

    merged_rows = [best_headers]  # start with header row
    seen_rows: set[str] = {" ".join(best_headers).strip().lower()}

    for _score, table in ordered:
        for row in table.rows:
            # Skip duplicate header/empty rows
            key = " ".join(str(c) for c in row).strip().lower()
            if key in seen_rows or not key:
                continue
            seen_rows.add(key)
            # Pad or trim row to match header width
            target_width = len(best_headers)
            if len(row) < target_width:
                row = row + [""] * (target_width - len(row))
            elif len(row) > target_width:
                row = row[:target_width]
            merged_rows.append(row)

    logger.info(
        "merged %d cashflow tables into synthetic table (%d rows, pages %s)",
        len(candidates),
        len(merged_rows),
        sorted(set(t.page_number for _, t in candidates)),
    )

    return DoclingTable(
        page_number=best_page,
        caption="Merged cashflow statement (Appendix 5B)",
        rows=merged_rows,
        headers=best_headers,
        raw_header_rows=best_raw_header_rows,
    )


def _table_precedence_text(table: Any, *, max_rows: int = 12) -> str:
    return _normalize_filter_text(
        " ".join(
            [
                str(getattr(table, "caption", "") or ""),
                " ".join(str(header) for header in getattr(table, "headers", []) or []),
                " ".join(
                    " ".join(str(cell) for cell in row)
                    for row in (getattr(table, "rows", []) or [])[:max_rows]
                    if row
                ),
            ]
        )
    )


def _statement_precedence_rank(table: Any) -> int:
    """Prefer group/full statements over wrappers or component-entity tables."""
    text = _table_precedence_text(table)
    rank = 0
    if any(marker in text for marker in _STATEMENT_SLOT_DISQUALIFY_PHRASES):
        rank -= 120
    if any(
        marker in text
        for marker in (
            "appendix4d",
            "appendix4e",
            "resultsforannouncement",
        )
    ):
        rank -= 80
    if any(
        marker in text
        for marker in (
            "deedofcrossguarantee",
            "closedgroup",
            "parententity",
            "companyonly",
        )
    ):
        rank -= 60
    if "consolidated" in text:
        rank += 80
    if any(
        marker in text
        for marker in (
            "stapledgroup",
            "stapledentity",
            "securityholders",
        )
    ):
        rank += 40
    if any(marker in text for marker in ("thegroup", "groupstatement")):
        rank += 20
    return rank


def _table_disqualified_from_formal_statement_slot(table: Any) -> bool:
    text = _table_precedence_text(table)
    return any(marker in text for marker in _STATEMENT_SLOT_DISQUALIFY_PHRASES)


def _cashflow_candidate_is_appendix_fragment(table: Any) -> bool:
    text = _table_precedence_text(table, max_rows=30)
    if "appendix5b" in text or "quarterlycashflowreport" in text:
        return True
    section_markers = {"1.9", "2.6", "3.10", "4.2", "4.3", "4.4", "4.6"}
    for row in getattr(table, "rows", []) or []:
        if not row:
            continue
        first_cell = str(row[0] or "").strip().rstrip(".")
        if first_cell in section_markers:
            return True
    return False


def _should_merge_cf_candidates(candidates: list[tuple[int, Any]]) -> bool:
    return bool(candidates) and all(
        _cashflow_candidate_is_appendix_fragment(table)
        for _score, table in candidates
    )


def _run_pass2_locator(tables) -> dict[str, Any]:
    """
    Pass 2: score each DoclingTable against keyword map. Returns labelled dict.
    Tables are matched to statement type by caption + first column text + headers.
    Tables with explicit statement-name headers receive a large bonus score so
    they win over footnote tables with incidental keyword matches.
    Unmatched tables go to 'unmatched' list.
    """
    from app.services.docling_extract import DoclingTable

    labelled: dict[str, Any] = {k: None for k in _TABLE_KEYWORDS}
    labelled["net_debt_note"] = None
    labelled["unmatched"] = []
    # share_capital is handled via _TABLE_KEYWORDS and pools above

    def _table_is_toc(table: DoclingTable) -> bool:
        """True when any individual column header is a bare 1-3 digit integer (page number)."""
        return any(
            _re.match(r"^\s*\d{1,3}\s*$", str(h or ""))
            for h in table.headers
            if str(h or "").strip()
        )

    def _table_has_numeric_data(table: DoclingTable) -> bool:
        """True when at least one body row (after the header) contains a digit.

        Financial statement tables always have numbers in their data columns.
        Glossary / definition tables (e.g. "Alternative Performance Measures")
        contain only prose descriptions and should not be selected as statement sources.
        """
        # Check rows 1..15 (skip row 0 which is often a repeated header)
        for row in table.rows[1:16]:
            for cell in row:
                if _re.search(r"\d", str(cell or "")):
                    return True
        return False

    def _score(table: DoclingTable, label: str, keywords: list[str]) -> int:
        # Include caption, all header cells, and ALL columns of first 30 body rows.
        # 30-row scan ensures we reach investing/financing sections in full CF statements
        # (e.g. BHP's CF statement has 40+ rows; "Financing activities" at row ~34).
        # Scanning all columns (not just column 0) is essential for ASX Appendix 5B
        # where column 0 is section numbers (1.1, 2.1, etc.) and column 1 has labels.
        header_text = " ".join(table.headers).lower()
        body_text = " ".join(
            " ".join(str(c) for c in row) for row in table.rows[:30] if row
        ).lower()
        text = table.caption.lower() + " " + header_text + " " + body_text
        score = sum(1 for kw in keywords if kw in text)
        # Bonus only when the explicit statement name appears in the column HEADERS
        # (not body text) — prevents index/checklist tables from claiming the bonus
        # just because they reference another statement by name in a row label.
        # Skip the bonus for TOC tables (bare page-number column header).
        header_only = table.caption.lower() + " " + header_text
        if not _table_is_toc(table):
            for phrase in _STATEMENT_HEADERS.get(label, []):
                if phrase in header_only:
                    score += _HEADER_BONUS
                    break
        # Penalise tables with no numeric data in body rows.  Glossary /
        # definition tables (e.g. "Alternative Performance Measures") match many
        # keywords but contain zero numbers — they must not win over actual
        # financial statements.
        if score > 0 and not _table_has_numeric_data(table):
            score = 0
        return score

    # Score each table against ALL statement types — a table may appear in multiple
    # candidate pools. This allows summary tables (e.g. Appendix 4D highlights) that
    # partially match income_statement keywords to also compete for the highlights slot.
    # Pool tuple: (score, is_not_toc, table) — tiebreak prefers non-TOC tables.
    pools: dict[str, list[tuple[int, bool, Any]]] = {k: [] for k in _TABLE_KEYWORDS}
    for table_index, table in enumerate(tables):
        if _normalized_table_index(table) is None:
            table.index_in_doc = table_index
        any_match = False
        is_not_toc = not _table_is_toc(table)
        # Pre-compute header/caption/body text for CF disqualification check.
        # Include first 10 body rows because some docling tables have generic
        # headers (e.g. '0','1','2','3') but contain "Cash flows from ..." in
        # the body rows — especially in Appendix 5B fragments.
        _hdr_caption = (
            (table.caption or "").lower()
            + " "
            + " ".join(str(h) for h in table.headers).lower()
            + " "
            + " ".join(
                " ".join(str(c) for c in row) for row in table.rows[:10] if row
            ).lower()
        )
        for label, keywords in _TABLE_KEYWORDS.items():
            score = _score(table, label, keywords)
            if score > 0:
                if (
                    label in _FORMAL_STATEMENT_SLOT_LABELS
                    and _table_disqualified_from_formal_statement_slot(table)
                ):
                    continue
                # CF disqualification: tables whose headers/caption contain
                # cash-flow-specific phrases must not claim income_statement
                # or balance_sheet slots — they are cash-flow tables that
                # happen to mention IS/BS keywords incidentally.
                if label in ("income_statement", "balance_sheet") and any(
                    p in _hdr_caption for p in _CF_DISQUALIFY_PHRASES
                ):
                    continue
                # Segment disqualification: divisional breakdown tables
                # share many IS keywords but are not the consolidated IS.
                # Detect by: (a) nearby section headings, or (b) 8+ columns
                # (segment tables have one column per division).
                if label == "income_statement" and (
                    any(p in _hdr_caption for p in _SEGMENT_DISQUALIFY_PHRASES)
                    or any(
                        p in _hdr_caption
                        for p in _INCOME_STATEMENT_DISQUALIFY_PHRASES
                    )
                    or len(table.headers) >= 8
                ):
                    continue
                pools[label].append((score, is_not_toc, table))
                any_match = True
        if not any_match:
            labelled["unmatched"].append(table)

    # For each label: highest score wins; if tied, non-TOC beats TOC; if still tied,
    # earlier page wins (formal statements appear before notes in ASX filings).
    # Negate page_number so that lower pages win on tiebreak.
    statement_precedence_labels = _FORMAL_STATEMENT_SLOT_LABELS
    for label in _TABLE_KEYWORDS:
        if pools[label]:
            candidates = pools[label]
            if label in statement_precedence_labels:
                max_score = max(score for score, _not_toc, _table in candidates)
                # Precedence is only safe among credible near-top candidates.
                # A weak note table that merely mentions "consolidated" must not
                # outrank a much stronger formal statement table.
                candidates = [
                    candidate
                    for candidate in candidates
                    if candidate[0] >= max_score - 2
                ]
            winner_score, _winner_not_toc, winner_table = max(
                candidates,
                key=lambda x: (
                    _statement_precedence_rank(x[2])
                    if label in statement_precedence_labels
                    else 0,
                    x[0],
                    x[1],
                    -x[2].page_number,
                ),
            )
            labelled[label] = winner_table
            if label in statement_precedence_labels:
                winner_key = (
                    _statement_precedence_rank(winner_table),
                    winner_score,
                    _winner_not_toc,
                )
                equally_bound = [
                    table
                    for score, is_not_toc, table in candidates
                    if table is not winner_table
                    and (
                        _statement_precedence_rank(table),
                        score,
                        is_not_toc,
                    )
                    == winner_key
                ]
                if equally_bound:
                    labelled[label] = None
                    labelled["unmatched"].extend([winner_table, *equally_bound])
                    logger.warning(
                        "Pass2 %s abstained: equal top table evidence",
                        label,
                    )
                    continue
            logger.info(
                "Pass2 %s: table=%d page=%d score=%d caption='%s'",
                label,
                getattr(winner_table, "index_in_doc", -1),
                winner_table.page_number,
                winner_score,
                (winner_table.caption or "")[:60],
            )

    # ASX Appendix 5B splits the cash flow statement across many tables
    # (operating, investing, financing, reconciliation).  When multiple tables
    # score ≥ _CF_MERGE_THRESHOLD for cashflow_statement, merge them into one
    # synthetic table so Pass 3a sees all cash-flow data in a single prompt.
    if pools["cashflow_statement"]:
        cf_candidates = [
            (score, tbl)
            for score, _not_toc, tbl in pools["cashflow_statement"]
            if score >= _CF_MERGE_THRESHOLD
        ]
        if len(cf_candidates) > 1 and _should_merge_cf_candidates(cf_candidates):
            labelled["cashflow_statement"] = _merge_cf_tables(cf_candidates)

    def _normalize_locator_text(value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        text = _re.sub(r"\([^)]*\)", " ", text)
        # Preserve calendar digits so "At 31 December" / "At 30 June" markers
        # survive point-in-time detection while still stripping footnote markers.
        text = _re.sub(r"[¹²³⁴⁵]", " ", text)
        text = _re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    def _row_has_numeric_payload(row: Any) -> bool:
        if not isinstance(row, (list, tuple)) or len(row) <= 1:
            return False
        return any(_re.search(r"\d", str(cell or "")) for cell in row[1:])

    def _share_capital_rank(table: DoclingTable) -> tuple[int, int]:
        header_text = _normalize_locator_text(table.caption) + " " + _normalize_locator_text(
            " ".join(str(h) for h in table.headers)
        )
        compact_header_text = _normalize_filter_text(header_text)
        row_labels = [
            _normalize_locator_text(row[0])
            for row in table.rows
            if isinstance(row, (list, tuple)) and row
        ]
        compact_row_labels = [_normalize_filter_text(label) for label in row_labels]

        explicit_count_header = int(
            "numberofshares" in compact_header_text
            or "numberofsecurities" in compact_header_text
            or "numberofunits" in compact_header_text
            or "noofsecurities" in compact_header_text
            or "noofunits" in compact_header_text
            or "sharesonissue" in compact_header_text
            or "securitiesonissue" in compact_header_text
            or "unitsonissue" in compact_header_text
            or "stapledsecurities" in compact_header_text
            or "ordinaryshares" in compact_header_text
        )
        explicit_period_end_row = int(
            any(
                (
                    "issuedordinaryshares" in label
                    or "sharesnotifiedtotheaustralianstockexchange" in label
                    or "sharesnotifiedtotheaustraliansecuritiesexchange" in label
                    or "sharesonissue" in label
                    or "securitiesonissue" in label
                    or "unitsonissue" in label
                    or "stapledsecurities" in label
                )
                and any(
                    marker in label
                    for marker in ("at30june", "at31december", "at30september")
                )
                for label in compact_row_labels
            )
        )
        weighted_average_only = int(
            compact_row_labels
            and all("weightedaverage" in label or not label for label in compact_row_labels[1:])
        )
        dollar_only_headers = int(
            any("usm" in _normalize_filter_text(h) for h in table.headers)
            and not explicit_count_header
        )

        rank = (
            explicit_count_header * 100
            + explicit_period_end_row * 50
            - weighted_average_only * 80
            - dollar_only_headers * 20
        )
        return rank, len(row_labels)

    if pools["share_capital"]:
        _winner_score, _winner_not_toc, winner_table = max(
            pools["share_capital"],
            key=lambda item: (
                _share_capital_rank(item[2])[0],
                item[0],
                item[1],
                _share_capital_rank(item[2])[1],
                -item[2].page_number,
            ),
        )
        share_rank, share_len = _share_capital_rank(winner_table)
        if share_rank > 0:
            labelled["share_capital"] = winner_table

    def _is_formula_style_net_debt_table(table: DoclingTable) -> bool:
        row_payloads = [
            (row, _normalize_locator_text(" ".join(str(cell) for cell in row)))
            for row in table.rows
            if row
        ]
        has_debt_component = any(
            marker in row_text
            and _row_has_numeric_payload(row)
            for row, row_text in row_payloads
            for marker in _NET_DEBT_DETAIL_DEBT_MARKERS
        )
        has_cash_component = any(
            marker in row_text
            and _row_has_numeric_payload(row)
            for row, row_text in row_payloads
            for marker in _NET_DEBT_DETAIL_CASH_MARKERS
        )
        has_adjustment_component = any(
            marker in row_text
            and _row_has_numeric_payload(row)
            for row, row_text in row_payloads
            for marker in _NET_DEBT_DETAIL_ADJUSTMENT_MARKERS
        )
        has_net_debt_row = any(
            _normalize_locator_text(row[0]) == "net debt" and _row_has_numeric_payload(row)
            for row, _row_text in row_payloads
        )
        return (
            has_net_debt_row
            and has_debt_component
            and has_cash_component
            and has_adjustment_component
        )

    def _table_has_point_in_time_stock_layout(table: DoclingTable) -> bool:
        """Detect current/non-current stock layouts that imply point-in-time debt."""
        header_text = (
            _normalize_locator_text(table.caption)
            + " "
            + _normalize_locator_text(" ".join(str(h) for h in table.headers))
        )
        if "carrying amount" in header_text or (
            "current" in header_text and "non current" in header_text
        ):
            return True

        for row in table.rows[:3]:
            cells = [
                _normalize_locator_text(cell)
                for cell in row
                if str(cell or "").strip()
            ]
            if not cells:
                continue
            cell_text = " ".join(cells)
            if "carrying amount" in cell_text:
                return True
            if "current" in cells and "non current" in cells:
                return True
        return False

    def _is_explicit_point_in_time_net_debt_row(
        table: DoclingTable, row_index: int
    ) -> bool:
        if row_index < 0 or row_index >= len(table.rows):
            return False
        row = table.rows[row_index]
        if not row:
            return False
        label = _normalize_locator_text(row[0])
        if label != "net debt" or not _row_has_numeric_payload(row):
            return False

        header_text = (
            _normalize_locator_text(table.caption)
            + " "
            + _normalize_locator_text(" ".join(str(h) for h in table.headers))
        )
        if any(marker in header_text for marker in _POINT_IN_TIME_TABLE_MARKERS):
            return True
        if _table_has_point_in_time_stock_layout(table):
            return True

        start = max(0, row_index - 3)
        context_rows = [
            _normalize_locator_text(" ".join(str(cell) for cell in table.rows[idx]))
            for idx in range(start, row_index)
        ]
        if any(
            any(marker in row_text for marker in _POINT_IN_TIME_TABLE_MARKERS)
            for row_text in context_rows
        ):
            return True

        # Do not treat annual formula-style tables as point-in-time net debt notes
        # without an "as at" / "at year end" marker. BHP's annual custom note is
        # explicit, but it is not the canonical point-in-time debt/cash metric this
        # slot is meant to surface.
        return False

    net_debt_candidates: list[tuple[int, int, int, DoclingTable]] = []
    for table in tables:
        for row_index, _row in enumerate(table.rows):
            if _is_explicit_point_in_time_net_debt_row(table, row_index):
                net_debt_candidates.append(
                    (
                        1,
                        -int(table.page_number),
                        -int(len(table.rows)),
                        table,
                    )
                )
                break

    if net_debt_candidates:
        labelled["net_debt_note"] = max(net_debt_candidates)[3]

    return labelled


_OPENABILITY_SYNTHETIC_CAPTIONS = {
    "income_statement": "Statement of profit or loss and comprehensive income",
    "balance_sheet": "Statement of financial position",
    "cashflow_statement": "Statement of cash flows",
}


def _valid_openability_diagnostics(structured_doc: Any) -> dict[str, Any] | None:
    diagnostics = getattr(structured_doc, "parser_diagnostics", {}) or {}
    openability = diagnostics.get("openability")
    if not isinstance(openability, dict):
        return None
    if openability.get("schema") != "docling_openability_diagnostics_v1":
        return None
    if openability.get("provenance_only") is not True:
        return None
    if openability.get("feeds_canonical_output") is not False:
        return None
    if openability.get("canonical_output_changed") is not False:
        return None
    return openability


def _openability_period_source_text(structured_doc: Any) -> str:
    """Return exact reporting-period phrases captured by openability diagnostics."""
    openability = _valid_openability_diagnostics(structured_doc)
    if openability is None:
        return ""
    records = openability.get("ocr_records")
    if not isinstance(records, list):
        return ""
    phrases: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        period_phrases = record.get("period_phrases")
        if not isinstance(period_phrases, list):
            continue
        for phrase in period_phrases:
            text = str(phrase or "").strip()
            if text and text not in phrases:
                phrases.append(text)
    return _combined_source_text(phrases)


def _build_openability_selected_tables(structured_doc: Any) -> list[Any]:
    """
    Convert existing opt-in openability diagnostics into synthetic statement tables.

    This does not run OCR and does not normalize values. It only bridges diagnostic
    source rows into the normal Pass 2/3a table path when period and scale evidence
    are already explicit in the diagnostic payload.
    """
    from app.services.docling_extract import DoclingTable

    openability = _valid_openability_diagnostics(structured_doc)
    if openability is None:
        return []

    records = openability.get("ocr_records")
    if not isinstance(records, list):
        return []

    synthetic_tables = []
    for record in records:
        if not isinstance(record, dict):
            continue
        statement_label = str(record.get("statement_label") or "").strip()
        caption_base = _OPENABILITY_SYNTHETIC_CAPTIONS.get(statement_label)
        if not caption_base:
            continue
        raw_period_phrases = record.get("period_phrases")
        if not isinstance(raw_period_phrases, list):
            continue
        period_phrases = [
            str(phrase).strip()
            for phrase in raw_period_phrases
            if str(phrase or "").strip()
        ]
        if not period_phrases:
            continue
        raw_scale_phrases = record.get("scale_phrases")
        if not isinstance(raw_scale_phrases, list):
            continue
        page_scale_evidence = [
            (str(phrase).strip(), _detect_scale_from_openability_phrase(phrase))
            for phrase in raw_scale_phrases
            if str(phrase or "").strip()
        ]
        page_scale_evidence = [
            evidence for evidence in page_scale_evidence if evidence[1] != "unknown"
        ]
        page_scales = {scale for _phrase, scale in page_scale_evidence}
        # Scale is a page-local assertion. Missing or conflicting evidence must
        # never inherit another OCR page's first scale phrase.
        if len(page_scales) != 1:
            continue
        scale = next(iter(page_scales))
        scale_phrases = sorted(
            {phrase for phrase, detected in page_scale_evidence if detected == scale}
        )
        scale_phrase = " ".join(scale_phrases)
        scale_source = f"ocr_page_{record.get('page')}"
        row_candidates = record.get("row_candidates")
        if not isinstance(row_candidates, list):
            continue

        page = int(record.get("page") or 0)
        period_phrase = period_phrases[0]
        header_value = f"{period_phrase} {scale_phrase}".strip()
        rows = [["Source row", header_value, "Diagnostic value candidates"]]
        accepted_candidates: list[dict[str, Any]] = []
        for candidate in row_candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("candidate_value_quality") != "financial_amount":
                continue
            confidence = candidate.get("recognition_confidence")
            if isinstance(confidence, bool):
                continue
            try:
                numeric_confidence = float(confidence)
            except (TypeError, ValueError):
                continue
            if not 80 <= numeric_confidence <= 100:
                continue
            source_text = str(candidate.get("source_text") or "").strip()
            candidate_value = str(candidate.get("candidate_value_text") or "").strip()
            source_region = candidate.get("source_region")
            source_row = candidate.get("source_row")
            source_cell = candidate.get("source_cell")
            if (
                not source_text
                or not candidate_value
                or not isinstance(source_region, dict)
                or source_row is None
                or not isinstance(source_cell, list)
            ):
                continue
            value_candidates = candidate.get("value_text_candidates")
            if isinstance(value_candidates, list):
                value_candidates_text = " | ".join(
                    str(value).strip()
                    for value in value_candidates
                    if str(value or "").strip()
                )
            else:
                value_candidates_text = candidate_value
            provenance = (
                f"page={record.get('page')}; region={source_region}; "
                f"row={source_row}; cells={source_cell}"
            )
            rows.append(
                [f"{source_text} [{provenance}]", candidate_value, value_candidates_text]
            )
            accepted_candidates.append(
                {
                    "page_number": page,
                    "source_region": dict(source_region),
                    "source_row": source_row,
                    "source_cell": list(source_cell),
                    "source_text": source_text,
                    "candidate_value_text": candidate_value,
                    "recognition_confidence": numeric_confidence,
                }
            )

        if len(rows) <= 1:
            continue
        caption = (
            f"{caption_base} (openability diagnostic; page {page}; "
            f"period={period_phrase}; scale={scale_phrase}; scale_source={scale_source})"
        )
        synthetic_tables.append(
            DoclingTable(
                page_number=page,
                caption=caption,
                headers=rows[0],
                rows=rows,
                ocr_source_candidates=accepted_candidates,
            )
        )

    return synthetic_tables


# ---------------------------------------------------------------------------
# Pass 3a — Per-Table Metric Extractor (LLM)
# ---------------------------------------------------------------------------

_PASS3A_PROMPT = """You are a financial metric extractor. Output ONLY valid JSON matching the schema below.

Document metadata:
- Period: {period_type} ending {period_end}
- Currency: {currency}
- Scale: {scale} (for your information only — output RAW values as they appear in the table)
  - Do NOT pre-multiply. Output 3241 if the table shows "3,241". The system applies the scale.
  - Example: table shows "Revenue: 485,630" with column header "$'000" → output 485630, NOT 485630000. The system multiplies by 1,000 automatically.

Table type: {table_type}
Table (markdown):
{table_markdown}

Extract ONLY these metrics relevant to {table_type}:
{metric_list}

Required JSON Output Format:
{{
  "thinking": "Brief step-by-step reasoning for the extraction (e.g., 'Found row X, verified column Y for period Z, checked scale in header')",
  "metrics": {{
{metric_schema}
  }},
  "row_refs": {{
    "metric_name": "original row label from markdown",
    ...
  }}
}}

Rules:
- Values in parentheses like (412) mean NEGATIVE: output -412 (raw, not pre-multiplied)
- Output null if the metric is NOT explicitly labeled in this table — do NOT estimate or derive it
- row_refs: for every non-null metric, you MUST provide the EXACT row label from the markdown table where you found the value. If you summed multiple rows (e.g. for capex), provide them all as a comma-separated list.
- revenue: extract the TOP-LINE revenue row — typically labeled "Revenue", "Sales revenue",
  "Total revenue", "Revenue from ordinary activities", "Operating revenue", or "Net revenue".
  DO NOT use: "Other income", "Interest income", "Total income" (which may include non-operating items),
  or "Net profit" as a proxy for revenue.
  For banks: "Net interest income" or "Total operating income" is the revenue equivalent.
- ebit: only output if a row is explicitly labeled "EBIT", "Earnings Before Interest and Tax",
  "Profit from operations", "Profit / (loss) from operating activities", "Operating profit",
  "Statutory EBIT", "Operating income", "Profit before income tax", or "Cash profit before tax".
  Do NOT use Net Profit as a proxy.
  CRITICAL: if the table has BOTH "Profit before credit impairment and income tax" AND
  "Profit before income tax", you MUST use "Profit before income tax" (the row AFTER credit impairment).
  "Profit before credit impairment and income tax" is NOT ebit.
- capex: Capital Expenditure must be a SPECIFIC LINE ITEM, NOT a total or subtotal.
  Correct labels: "Payments for property, plant and equipment", "Purchases of property, plant and equipment",
  "Purchase of PPE", "Additions to fixed assets", "Capital expenditure",
  "Payments for capital expenditure", "Expenditure on mining development",
  "Expenditure on mining production and development",
  "Net investments in other assets" (banking: ANZ-style capex equivalent).
  DO NOT use: "Net cash from investing activities", "Investing cash flow", "Capital and exploration expenditure", or any
  total/subtotal line. If only a total investing cash flow is present and no specific
  capex line exists, return null.
  Appendix 5B: if multiple capex sub-items exist (e.g. "property", "equipment",
  "development"), SUM them and output the total as capex.
- shares_outstanding: extract the PERIOD-END total ordinary shares on issue (count, not dollar amount).
  Correct labels: "Ordinary shares", "Shares on issue", "Number of shares on issue",
  "Fully paid ordinary shares", "Total ordinary shares", "Number of securities",
  "Securities on issue", "Stapled securities", "Number of units", or "Units on issue".
  DO NOT use: "Weighted average number of shares", "Diluted shares", or "Basic earnings per share" denominators.
  DO NOT extract from columns labeled "$", "$m", "$M", or any dollar-denominated header — those are
  dollar values of share capital, not share counts. If the only available data is dollar-denominated, return null.
  If both period-end and weighted-average rows are in the same table, use only the period-end row.
  EXCEPTION for share counts only (not dollar amounts): if the table expresses share counts in a scaled unit (e.g. "Million", "'000"), convert to the absolute count.
  Example: if the table shows "5,057" with row label containing "(Million)", output 5057000000 (not 5057).
  Example: if the table shows "196,478,902" as an absolute count, output 196478902.
- Column selection: if the table has multiple data columns (e.g. current half and prior half),
  extract values ONLY from the column whose header best matches the reporting date {period_end}.
  Never extract from prior-period or comparative columns.
  Set period_col to the exact column header you chose.
- net_debt: only output when the table has an explicit current-period row labeled "Net debt".
  Do NOT use "Opening net debt", "Movement in net debt", "Net debt plus total equity",
  "Net gearing ratio", or similarly derived/context rows.
- total_debt (balance_sheet only): sum of all financial debt — current + non-current borrowings,
  bonds, notes payable. Exclude AASB 16 / IFRS 16 lease liabilities unless no other financial
  debt exists. Output null if no financial debt is present (e.g. company is debt-free).

Schema:
{{
{metric_schema}
  "period_col": "string|null",
  "pass3_confidence": 0.0,
  "row_refs": {{}}
}}

Example — cashflow_statement in $A'000, period ending Dec 2025:
{{"operating_cf": 15234, "investing_cf": -8901, "financing_cf": -3456, "cash_end": 12345, "capex": -2100, "period_col": "Dec 2025", "pass3_confidence": 0.9, "row_refs": {{"operating_cf": "Net cash from operating activities", "capex": "Payments for property, plant and equipment"}}}}
"""

_METRIC_SCHEMA_BY_TABLE = {
    "cashflow_statement": [
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "cash_end",
        "capex",
    ],
    "income_statement": ["revenue", "ebit", "np_attributable"],
    "net_debt_note": ["net_debt"],
    # total_debt is an internal capture metric: not in METRIC_FIELDS, not stored in DB.
    # Pass 4 uses it to derive net_debt = total_debt - cash_end when net_debt is null.
    "balance_sheet": ["net_debt", "total_debt", "shares_outstanding"],
    "share_capital": ["shares_outstanding"],
    "highlights": METRIC_FIELDS,  # highlights may have any metric
}

_RETRY_KEY_METRICS_BY_TABLE: dict[str, list[str]] = {
    "cashflow_statement": ["operating_cf", "cash_end"],
    "income_statement": ["revenue"],
    "net_debt_note": ["net_debt"],
    "balance_sheet": ["net_debt", "total_debt"],
    "share_capital": ["shares_outstanding"],
}


def _needs_full_table_retry(table_type: str, extracted: dict[str, Any]) -> bool:
    """
    Decide whether a filtered-table extraction should be retried on full rows.

    Retry when table-specific key metrics are all null after filtered extraction.
    """
    key_metrics = _RETRY_KEY_METRICS_BY_TABLE.get(table_type)
    if key_metrics:
        return all(extracted.get(metric) is None for metric in key_metrics)

    metrics = _METRIC_SCHEMA_BY_TABLE.get(table_type, METRIC_FIELDS)
    return all(extracted.get(metric) is None for metric in metrics)


# ---------------------------------------------------------------------------
# Row filtering — reduce token count by keeping only metric-relevant rows.
# Applied to large tables (>20 rows) in CF, IS, BS only.
# ---------------------------------------------------------------------------

_ROW_KEYWORDS_BY_TABLE: dict[str, list[str]] = {
    "cashflow_statement": [
        "receipt",
        "payment",
        "net cash",
        "operating",
        "investing",
        "financing",
        "property plant",
        "capital expenditure",
        "cash and cash equivalent",
        "cash at end",
        "cash at the end",
        "net increase",
        "net decrease",
        "beginning",
        "end of",
        "exchange rate",
        # Appendix 5B section totals and key items
        "subtotal",
        "exploration",
        "development",
        "staff cost",
        "production",
        "related body corporate",
    ],
    "income_statement": [
        "revenue",
        "sales",
        "income",
        "profit",
        "loss",
        "ebit",
        "earnings before",
        "operations",
        "operating",
        "income tax",
        "attributable",
        "equity holder",
        "owners of",
        "non-controlling",
        "comprehensive",
        "net profit",
        "net loss",
    ],
    "balance_sheet": [
        "cash and cash equivalent",
        "borrowing",
        "interest bearing",
        "loan",
        "notes payable",
        "bond",
        "financial debt",
        "lease liab",
        "net asset",
        "total equity",
        "share capital",
        "issued capital",
        "ordinary share",
        "shares on issue",
        "total asset",
        "total liab",
        "net debt",
        "current",
        "non-current",
    ],
}

# Tables where filtering should NOT be applied.
_NO_FILTER_TABLES = {"highlights", "share_capital", "net_debt_note"}

# Minimum row count to trigger filtering — small tables are sent in full.
_FILTER_MIN_ROWS = 20


def _is_section_header(row: list[str]) -> bool:
    """A row is a section header if only the first cell has text (values are empty)."""
    if not row or len(row) < 2:
        return False
    first = str(row[0]).strip()
    if not first:
        return False
    return all(not str(c).strip() or str(c).strip() == "-" for c in row[1:])


def _is_total_row(row: list[str]) -> bool:
    """Check if a row is a total/subtotal line."""
    label = str(row[0]).strip().lower() if row else ""
    return any(
        kw in label
        for kw in ("total", "net cash", "net operating", "net increase", "net decrease")
    )


def _normalize_filter_text(value: str) -> str:
    """Collapse spacing/punctuation so compacted Docling labels still match."""
    return _re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _row_matches_keywords(row: list[str], keywords: list[str]) -> bool:
    """Check if a row label matches any metric-relevant keyword."""
    label = str(row[0]).strip().lower() if row else ""
    if any(kw in label for kw in keywords):
        return True
    compact_label = _normalize_filter_text(label)
    return any(_normalize_filter_text(kw) in compact_label for kw in keywords)


def _filter_table_rows(table, table_type: str) -> list[list[str]]:
    """Filter table rows to metric-relevant ones for reduced token usage.

    Strategy (from research agent assessment):
    - Always keep: row 0 (header), section headers, total/subtotal rows
    - Keep rows matching metric keywords for the table type
    - Keep rows adjacent to totals (metric values often sit above subtotals)
    - Insert '[... N rows omitted ...]' markers where rows are removed
    - Only filter tables with >20 rows in CF/IS/BS

    Returns filtered row list, or original rows if filtering not applicable.
    """
    if not table or not table.rows:
        return []

    rows = table.rows
    if table_type in _NO_FILTER_TABLES or len(rows) <= _FILTER_MIN_ROWS:
        return rows

    keywords = _ROW_KEYWORDS_BY_TABLE.get(table_type)
    if not keywords:
        return rows

    # Determine which row indices to keep.
    keep = set()
    keep.add(0)  # header row always kept

    for i, row in enumerate(rows):
        if _is_section_header(row):
            keep.add(i)
        elif _is_total_row(row):
            keep.add(i)
            if i > 0:
                keep.add(i - 1)  # row above total often has the metric
        elif _row_matches_keywords(row, keywords):
            keep.add(i)

    # Build filtered output with omission markers.
    filtered: list[list[str]] = []
    omitted_count = 0
    for i, row in enumerate(rows):
        if i in keep:
            if omitted_count > 0:
                ncols = len(row)
                marker = [f"[... {omitted_count} rows omitted ...]"] + [""] * (
                    ncols - 1
                )
                filtered.append(marker)
                omitted_count = 0
            filtered.append(row)
        else:
            omitted_count += 1

    if omitted_count > 0:
        ncols = len(rows[-1]) if rows else 1
        filtered.append(
            [f"[... {omitted_count} rows omitted ...]"] + [""] * (ncols - 1)
        )

    original_count = len(rows)
    filtered_count = len([r for r in filtered if not str(r[0]).startswith("[...")])
    if filtered_count < original_count:
        reduction = 1 - filtered_count / original_count
        # Safety valve: if filtering removed >80% of rows, the keyword list
        # doesn't match this table's format (e.g. Appendix 5B numbered items).
        # Fall back to the full table rather than sending near-empty data.
        if reduction > 0.80:
            logger.warning(
                "Filter too aggressive for %s: %d → %d rows (%.0f%% reduction) — using full table",
                table_type,
                original_count,
                filtered_count,
                reduction * 100,
            )
            return rows
        logger.info(
            "Filtered %s: %d → %d rows (%.0f%% reduction)",
            table_type,
            original_count,
            filtered_count,
            reduction * 100,
        )

    return filtered


def _table_to_markdown(
    table, max_rows: int = 30, *, rows_override: list[list[str]] | None = None
) -> str:
    """Convert DoclingTable rows to markdown string.

    max_rows caps body rows sent to the LLM (default 30 for single tables;
    callers may raise this for merged tables like Appendix 5B).
    rows_override: if provided, use these rows instead of table.rows (for pre-filtered rows).
    """
    rows = rows_override if rows_override is not None else (table.rows if table else [])
    headers = list(getattr(table, "headers", []) or []) if table else []
    if not rows and not headers:
        return ""
    body_rows = list(rows)
    if headers and body_rows and list(body_rows[0]) == headers:
        body_rows = body_rows[1:]
    header_row = headers or list(body_rows.pop(0))
    lines = [" | ".join(str(c) for c in header_row)]
    lines.append(" | ".join("---" for _ in header_row))
    for row in body_rows[:max_rows]:
        lines.append(" | ".join(str(c) for c in row))
    return "\n".join(lines)


_PERIOD_HEADER_DATE_RE = re.compile(
    r"\b(?:"
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}"
    r")\b",
    re.IGNORECASE,
)

_ABBREVIATED_PERIOD_EVIDENCE_RE = re.compile(
    r"\b(?:FY|H[12]|[12]H|HY|Q[1-4])\s*(?:FY)?\s*\d{2,4}\b"
    r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)[\s/-]+\d{2,4}\b"
    r"|\b(?:19|20)\d{2}\b",
    re.IGNORECASE,
)


def _period_dates_from_header_cell(cell: Any) -> list[date]:
    dates: list[date] = []
    for match in _PERIOD_HEADER_DATE_RE.finditer(str(cell or "")):
        try:
            parsed = dtparser.parse(match.group(0), dayfirst=True).date()
        except Exception:
            continue
        if parsed not in dates:
            dates.append(parsed)
    return dates


def _has_unresolved_period_evidence(value: Any) -> bool:
    residual = _PERIOD_HEADER_DATE_RE.sub(" ", str(value or ""))
    return bool(_ABBREVIATED_PERIOD_EVIDENCE_RE.search(residual))


def _normalized_table_index(table: Any) -> int | None:
    value = getattr(table, "index_in_doc", None)
    if isinstance(value, bool):
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized >= 0 else None


def _quarter_column_basis_evidence(value: Any) -> set[str]:
    normalized = " ".join(_re.findall(r"[a-z0-9]+", str(value or "").lower()))
    words = frozenset(normalized.split())
    if any(
        marker in normalized
        for marker in (
            "comparative",
            "prior quarter",
            "previous quarter",
            "corresponding period",
            "pcp",
        )
    ):
        return {"comparative"}
    period_only = bool(
        _re.search(r"\b(?:current quarter|quarter only|quarter ended)\b", normalized)
        or _re.search(r"\b(?:3|three) months?(?: period| ended)?\b", normalized)
    )
    year_to_date = bool(
        "year to date" in normalized
        or "ytd" in words
        or "cumulative" in words
        or _re.search(
            r"\b(?:6|six|9|nine|12|twelve) months?"
            r"(?: cumulative| period| ended)?\b",
            normalized,
        )
    )
    evidence: set[str] = set()
    if period_only:
        evidence.add("period_only")
    if year_to_date:
        evidence.add("year_to_date")
    return evidence


def _bind_current_period_column(
    table: Any,
    period_end: Any,
    *,
    period_basis: str | None = None,
) -> dict[str, Any]:
    """Bind an exact source header date to one value column, or fail closed."""
    requested = parse_period_end(str(period_end) if period_end else None)
    raw_rows = [
        [str(cell or "") for cell in row]
        for row in (getattr(table, "raw_header_rows", None) or [])
    ]
    if not raw_rows and getattr(table, "headers", None):
        raw_rows = [[str(cell or "") for cell in table.headers]]
    width = max((len(row) for row in raw_rows), default=0)
    column_dates: dict[int, list[date]] = {}
    column_texts: dict[int, list[str]] = {}
    source_cells: dict[int, list[dict[str, Any]]] = {}
    for row_index, row in enumerate(raw_rows):
        for column_index in range(width):
            if column_index == 0:
                # The first column is the row-label axis. Statement titles and
                # period phrases may span it, but it is never a value column.
                continue
            cell = row[column_index] if column_index < len(row) else ""
            if str(cell).strip():
                column_texts.setdefault(column_index, []).append(str(cell))
            dates = _period_dates_from_header_cell(cell)
            if not dates:
                continue
            for parsed in dates:
                if parsed not in column_dates.setdefault(column_index, []):
                    column_dates[column_index].append(parsed)
            source_cells.setdefault(column_index, []).append(
                {
                    "header_row_index": row_index,
                    "column_index": column_index,
                    "text": cell,
                    "dates": [parsed.isoformat() for parsed in dates],
                }
            )

    base = {
        "table_index": _normalized_table_index(table),
        "requested_period_end": requested.isoformat() if requested else None,
        "period_basis": period_basis,
        "column_role": None,
        "column_index": None,
        "header_cell": None,
        "source_header_cells": source_cells,
        "comparative_columns": [],
    }
    if requested is None:
        return {**base, "status": "DATA_MISSING", "reason": "requested_period_invalid"}
    metadata_date_columns = {
        index
        for index, texts in column_texts.items()
        if _re.search(
            r"\b(?:announcement|lodgement|publication|release|filing|report)"
            r"\s+date\b",
            " ".join(texts),
            _re.IGNORECASE,
        )
    }
    for index in metadata_date_columns:
        column_dates.pop(index, None)
        source_cells.pop(index, None)
    conflicting = [index for index, dates in column_dates.items() if len(dates) > 1]
    if conflicting:
        return {
            **base,
            "status": "DATA_MISSING",
            "reason": "conflicting_period_headers",
            "conflicting_columns": conflicting,
        }
    matches = [index for index, dates in column_dates.items() if dates == [requested]]
    basis_by_column = {
        index: set().union(
            *(_quarter_column_basis_evidence(text) for text in texts)
        )
        for index, texts in column_texts.items()
    }
    column_evidence = {
        index: {
            "table_index": _normalized_table_index(table),
            "column_index": index,
            "period_ends": [
                parsed.isoformat() for parsed in column_dates.get(index, ())
            ],
            "period_bases": sorted(basis_by_column.get(index, set())),
            "header_text": " ".join(texts),
        }
        for index, texts in column_texts.items()
    }
    base["column_evidence"] = column_evidence
    if period_basis in {"period_only", "year_to_date"}:
        conflicting_basis_columns = [
            index for index in matches if len(basis_by_column.get(index, set())) > 1
        ]
        if conflicting_basis_columns:
            return {
                **base,
                "status": "DATA_MISSING",
                "reason": "conflicting_quarter_basis",
                "conflicting_columns": conflicting_basis_columns,
            }
        if len(matches) > 1:
            matches = [
                index
                for index in matches
                if basis_by_column.get(index) == {period_basis}
            ]
    if len(matches) > 1:
        return {
            **base,
            "status": "DATA_MISSING",
            "reason": "duplicate_current_period_header",
            "duplicate_columns": matches,
        }
    if not matches:
        reason = (
            "requested_period_header_missing" if column_dates else "period_headers_missing"
        )
        return {**base, "status": "DATA_MISSING", "reason": reason}

    column_index = matches[0]
    if period_basis in {"period_only", "year_to_date"}:
        basis_evidence = basis_by_column.get(column_index, set())
        if basis_evidence != {period_basis}:
            return {
                **base,
                "status": "DATA_MISSING",
                "reason": (
                    "conflicting_quarter_basis"
                    if len(basis_evidence) > 1
                    else "quarter_basis_mismatch"
                    if basis_evidence
                    else "quarter_basis_missing"
                ),
                "column_index": column_index,
                "basis_evidence": sorted(basis_evidence),
            }
    evidence = source_cells[column_index][0]
    header_cell = (
        " ".join(column_texts.get(column_index, ()))
        if period_basis in {"period_only", "year_to_date"}
        else evidence["text"]
    )
    return {
        **base,
        "status": "BOUND",
        "reason": "exact_unique_period_header",
        "column_index": column_index,
        "column_role": (
            "current_quarter"
            if period_basis == "period_only"
            else "year_to_date"
            if period_basis == "year_to_date"
            else None
        ),
        "header_cell": header_cell,
        "header_row_index": evidence["header_row_index"],
        "comparative_columns": sorted(
            index
            for index, dates in column_dates.items()
            if dates
            and (
                dates != [requested]
                or "comparative" in basis_by_column.get(index, set())
            )
        ),
    }


def _parse_accounting_metric_number(value: Any) -> tuple[float, bool] | None:
    """Parse pass3a metric values and flag explicit unit suffixes."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value), False

    text = " ".join(str(value).split()).strip()
    if not text or text.lower() in {"n/a", "na", "nil", "none", "null", "-"}:
        return None

    neg_paren = text.startswith("(") and text.endswith(")")
    if neg_paren:
        text = text[1:-1].strip()

    match = _ACCOUNTING_NUMBER_RE.match(text)
    if not match:
        return None

    try:
        parsed = float(match.group("num").replace(",", ""))
    except ValueError:
        return None

    if neg_paren:
        parsed = -abs(parsed)

    suffix = str(match.group("suffix") or "").lower()
    if suffix:
        return parsed * _ACCOUNTING_NUMBER_SUFFIX_MULTIPLIERS[suffix], True
    return parsed, False


_CASHFLOW_STRONG_CAPEX_LABELS = (
    "paymentsforpropertyplantandequipment",
    "paymentforpropertyplantandequipment",
    "purchasesofpropertyplantandequipment",
    "purchaseofpropertyplantandequipment",
    "paymentsforppe",
    "paymentforppe",
    "purchasesofppe",
    "purchaseofppe",
)
_CASHFLOW_BANK_CAPEX_LABELS = (
    "netinvestmentsinotherassets",
)
_CASHFLOW_GROUPED_SECTION_LABELS = (
    "investingactivities",
    "cashflowsfrominvestingactivities",
    "cashflowsusedininvestingactivities",
    "cashflowsfromusedininvestingactivities",
    "cashflowsusedinfrominvestingactivities",
)
_CASHFLOW_NOTE_HEADER_LABELS = {"note", "notes"}
_CASHFLOW_WEAK_CAPEX_ROW_MARKERS = (
    "acquisitionofsubsidiary",
    "acquisitionofbusiness",
    "businesscombination",
    "cashacquired",
    "netofcashacquired",
    "developmentofopenpit",
    "undergroundmines",
    "minedevelopment",
    "exploration",
)
_CASHFLOW_DISALLOWED_CAPEX_ROW_MARKERS = (
    "investmentsecurities",
    "securitiesassets",
    "securitiespurchase",
    "securitiespurchases",
    "purchaseofsecurities",
    "purchasesofsecurities",
    "financialassets",
    "financialasset",
    "interestbearingfinancialassets",
)
_CASHFLOW_CAPEX_OUTFLOW_MARKERS = (
    "payment",
    "payments",
    "purchase",
    "purchases",
    "acquisition",
    "acquisitions",
    "expenditure",
    "additions",
)
_CASHFLOW_STRONG_CASH_END_LABELS = (
    "cashandcashequivalentsattheendofthehalfyear",
    "cashandcashequivalentsattheendoftheperiod",
    "cashandcashequivalentsattheend",
    "cashandcashequivalentsnetofoverdraftsattheendofthefinancialyear",
    "cashandcashequivalentsnetofoverdraftsattheend",
    "totalcashandcashequivalents",
)
_CASHFLOW_WEAK_CASH_END_ROW_MARKERS = (
    "cashandgold",
    "netincreasedecreaseincashandcashequivalents",
    "netincreaseincashandcashequivalents",
    "netdecreaseincashandcashequivalents",
    "beginningofthefinancialyear",
    "beginningoftheperiod",
)
_CASHFLOW_EXPLICIT_AMOUNT_RE = _re.compile(
    r"(?P<paren>\()?\s*"
    r"(?P<currency>A\$|\$A|US\$|\$US|\$|AUD|USD)?\s*"
    r"(?P<num>[+-]?(?:\d+(?:,\d{3})+|\d+)(?:\.\d+)?)\s*"
    r"(?P<suffix>thousands?|millions?|billions?|trillions?|mn|m|bn|b|tn|t)\b"
    r"\)?",
    _re.IGNORECASE,
)


def _normalise_fragmented_pdf_text(value: Any) -> str:
    text = " ".join(str(value or "").replace("\u00a0", " ").split()).strip()
    text = _re.sub(r"(?<=\d)\s+\.\s*(?=\d)", ".", text)
    text = _re.sub(r"\bmilli\s+on\b", "million", text, flags=_re.IGNORECASE)
    return text


def _cashflow_capex_row_is_weak(row_ref: Any) -> bool:
    compact = _normalize_filter_text(str(row_ref or ""))
    if not compact:
        return True
    if _cashflow_capex_row_is_disallowed_financial_asset(row_ref):
        return True
    if (
        len(_re.findall(r"payments?for", compact)) > 1
        or len(_re.findall(r"purchases?of", compact)) > 1
    ):
        return True
    if any(marker in compact for marker in _CASHFLOW_STRONG_CAPEX_LABELS):
        return False
    return any(marker in compact for marker in _CASHFLOW_WEAK_CAPEX_ROW_MARKERS)


def _cashflow_capex_row_is_disallowed_financial_asset(row_ref: Any) -> bool:
    compact = _normalize_filter_text(str(row_ref or ""))
    if not compact:
        return False
    if any(marker in compact for marker in _CASHFLOW_BANK_CAPEX_LABELS):
        return False
    financial_asset_text = _re.sub(r"nonfinancialassets?", "", compact)
    return any(
        marker in financial_asset_text
        for marker in _CASHFLOW_DISALLOWED_CAPEX_ROW_MARKERS
    )


def _cashflow_cash_end_row_is_weak(row_ref: Any) -> bool:
    compact = _normalize_filter_text(str(row_ref or ""))
    if not compact:
        return True
    if any(marker in compact for marker in _CASHFLOW_STRONG_CASH_END_LABELS):
        return False
    return any(marker in compact for marker in _CASHFLOW_WEAK_CASH_END_ROW_MARKERS)


def _cashflow_row_has_strong_capex_label(
    row: list[Any],
    *,
    bank_cashflow_context: bool = False,
) -> bool:
    compact = _normalize_filter_text(
        _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))
    )
    if any(marker in compact for marker in _CASHFLOW_STRONG_CAPEX_LABELS):
        return True
    return bank_cashflow_context and any(
        marker in compact for marker in _CASHFLOW_BANK_CAPEX_LABELS
    )


def _cashflow_table_has_bank_capex_context(table: Any) -> bool:
    compact = _normalize_filter_text(
        " ".join(
            [
                str(getattr(table, "caption", "") or ""),
                " ".join(str(header) for header in getattr(table, "headers", []) or []),
                " ".join(
                    " ".join(str(cell) for cell in row)
                    for row in (getattr(table, "rows", []) or [])
                    if row
                ),
            ]
        )
    )
    return any(
        marker in compact
        for marker in (*_CASHFLOW_BANK_CAPEX_LABELS, "investmentsecurities", "securitiesassets")
    )


def _cashflow_row_capex_label_priority(
    row: list[Any],
    *,
    bank_cashflow_context: bool = False,
) -> int:
    compact = _normalize_filter_text(
        _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))
    )
    if any(marker in compact for marker in _CASHFLOW_STRONG_CAPEX_LABELS):
        return 100
    if bank_cashflow_context and any(
        marker in compact for marker in _CASHFLOW_BANK_CAPEX_LABELS
    ):
        return 90
    return 0


def _cashflow_row_has_strong_cash_end_label(row: list[Any]) -> bool:
    compact = _normalize_filter_text(
        _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))
    )
    if any(marker in compact for marker in _CASHFLOW_WEAK_CASH_END_ROW_MARKERS):
        return False
    return any(marker in compact for marker in _CASHFLOW_STRONG_CASH_END_LABELS)


def _cashflow_row_is_outflow(row: list[Any]) -> bool:
    compact = _normalize_filter_text(
        _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))
    )
    return any(marker in compact for marker in _CASHFLOW_CAPEX_OUTFLOW_MARKERS)


def _cashflow_capex_row_ref(row: list[Any]) -> str:
    label_cells: list[str] = []
    for cell in row:
        text = _normalise_fragmented_pdf_text(cell)
        if not text:
            continue
        if _parse_accounting_metric_number(text) is not None:
            break
        if _CASHFLOW_EXPLICIT_AMOUNT_RE.search(text):
            break
        label_cells.append(text)

    label = _normalise_fragmented_pdf_text(" ".join(label_cells))
    if label:
        return label
    return _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))[:180]


def _cashflow_cash_end_row_ref(row: list[Any]) -> str:
    label_cells: list[str] = []
    for cell in row:
        text = _normalise_fragmented_pdf_text(cell)
        if not text:
            continue
        if _parse_accounting_metric_number(text) is not None:
            break
        label_cells.append(text)

    label = _normalise_fragmented_pdf_text(" ".join(label_cells))
    if label:
        return label
    return _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))[:180]


def _row_label_before_numeric_cells(row: list[Any]) -> str:
    label_cells: list[str] = []
    for cell in row:
        text = _normalise_fragmented_pdf_text(cell)
        if not text:
            continue
        if _parse_accounting_metric_number(text) is not None:
            if not label_cells:
                # Appendix statement item numbers can precede the actual row
                # label in a separate column (for example, "2.6", label, value).
                continue
            break
        if _CASHFLOW_EXPLICIT_AMOUNT_RE.search(text):
            break
        label_cells.append(text)
    return _normalise_fragmented_pdf_text(" ".join(label_cells))[:180]


_PERIOD_BOUND_STATEMENT_METRICS = {
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
}


def _period_bound_source_cell(
    table: Any,
    row_ref: Any,
    column_index: int,
    scale: str,
) -> dict[str, Any] | None:
    normalized_ref = _normalise_fragmented_pdf_text(str(row_ref or "")).lower()
    if not normalized_ref:
        return None
    exact_matches: list[tuple[int, list[Any], str]] = []
    fuzzy_matches: list[tuple[int, list[Any], str]] = []
    for row_index, row in enumerate(getattr(table, "rows", []) or []):
        if column_index >= len(row):
            continue
        row_label = _row_label_before_numeric_cells(row)
        normalized_label = _normalise_fragmented_pdf_text(row_label).lower()
        if not normalized_label:
            continue
        candidate = (row_index, row, row_label)
        if normalized_label == normalized_ref:
            exact_matches.append(candidate)
        elif normalized_label in normalized_ref or normalized_ref in normalized_label:
            fuzzy_matches.append(candidate)
    matches = exact_matches if exact_matches else fuzzy_matches
    if len(matches) != 1:
        return None

    row_index, row, row_label = matches[0]
    raw_cell = str(row[column_index] or "").strip()
    parsed = _parse_accounting_metric_number(raw_cell)
    if parsed is None:
        return None
    raw_value, has_explicit_unit = parsed
    scaled_value = (
        raw_value
        if has_explicit_unit
        else raw_value * SCALE_MULTIPLIERS.get(scale, 1)
    )
    return {
        "page_number": getattr(table, "page_number", None),
        "row_index": row_index,
        "column_index": column_index,
        "row_label": row_label,
        "raw_value": raw_cell,
        "scaled_value": scaled_value,
    }


def _bind_statement_metrics_to_current_period_cells(
    extracted: dict[str, Any],
    table: Any,
    *,
    period_end: Any,
    scale: str,
    period_basis: str | None = None,
) -> dict[str, Any]:
    """Replace statement metrics with their unique requested-period source cells."""
    binding = _bind_current_period_column(
        table, period_end, period_basis=period_basis
    )
    extracted["_period_binding"] = binding
    metric_names = [
        metric_name
        for metric_name in _PERIOD_BOUND_STATEMENT_METRICS
        if metric_name in extracted
    ]
    row_refs = extracted.get("row_refs", {})
    extracted["_period_source_cells"] = {}
    if binding.get("status") != "BOUND":
        # Missing, malformed, duplicated, or conflicting period evidence can
        # never preserve a value or source binding from an earlier pass.
        for metric_name in metric_names:
            extracted[metric_name] = None
            row_refs.pop(metric_name, None)
        extracted["period_col"] = None
        return extracted

    column_index = int(binding["column_index"])
    ocr_metric_provenance = extracted.get("_ocr_metric_provenance")
    if isinstance(ocr_metric_provenance, dict) and getattr(
        table, "ocr_source_candidates", None
    ):
        source_cells: dict[str, dict[str, Any]] = {}
        for metric_name in metric_names:
            candidate = ocr_metric_provenance.get(metric_name)
            if extracted.get(metric_name) is None or not isinstance(candidate, dict):
                extracted[metric_name] = None
                row_refs.pop(metric_name, None)
                continue
            parsed = _parse_accounting_metric_number(
                candidate.get("candidate_value_text")
            )
            if parsed is None:
                extracted[metric_name] = None
                row_refs.pop(metric_name, None)
                continue
            raw_value, has_explicit_unit = parsed
            scaled_value = (
                raw_value
                if has_explicit_unit
                else raw_value * SCALE_MULTIPLIERS.get(scale, 1)
            )
            row_refs[metric_name] = str(candidate.get("source_text") or "unknown")
            extracted[metric_name] = scaled_value
            source_cells[metric_name] = {
                "page_number": candidate.get("page_number"),
                "row_index": candidate.get("source_row"),
                "column_index": column_index,
                "row_label": candidate.get("source_text"),
                "raw_value": candidate.get("candidate_value_text"),
                "scaled_value": scaled_value,
                "header_cell": binding["header_cell"],
                "requested_period_end": binding["requested_period_end"],
            }
            if period_basis in {"period_only", "year_to_date"}:
                source_cells[metric_name].update(
                    table_index=binding["table_index"],
                    column_role=binding["column_role"],
                    period_basis=period_basis,
                )
        extracted["_period_source_cells"] = source_cells
        headers = list(getattr(table, "headers", []) or [])
        extracted["period_col"] = (
            headers[column_index]
            if column_index < len(headers) and headers[column_index]
            else binding["header_cell"]
        )
        return extracted

    source_cells: dict[str, dict[str, Any]] = {}
    for metric_name in metric_names:
        if extracted.get(metric_name) is None:
            row_refs.pop(metric_name, None)
            continue
        source_cell = _period_bound_source_cell(
            table,
            row_refs.get(metric_name),
            column_index,
            scale,
        )
        if source_cell is None:
            extracted[metric_name] = None
            row_refs.pop(metric_name, None)
            continue
        source_cell["header_cell"] = binding["header_cell"]
        source_cell["requested_period_end"] = binding["requested_period_end"]
        if period_basis in {"period_only", "year_to_date"}:
            source_cell["table_index"] = binding["table_index"]
            source_cell["column_role"] = binding["column_role"]
            source_cell["period_basis"] = period_basis
        extracted[metric_name] = source_cell["scaled_value"]
        source_cells[metric_name] = source_cell

    extracted["_period_source_cells"] = source_cells
    headers = list(getattr(table, "headers", []) or [])
    extracted["period_col"] = (
        headers[column_index]
        if column_index < len(headers) and headers[column_index]
        else binding["header_cell"]
    )
    return extracted


def _parse_current_period_metric_cell(row: list[Any], scale: str) -> float | None:
    parsed_values: list[tuple[float, bool]] = []
    for cell in row[1:]:
        parsed = _parse_accounting_metric_number(cell)
        if parsed is None:
            continue
        parsed_values.append(parsed)

    if not parsed_values:
        return None

    raw_value, has_explicit_unit = parsed_values[0]
    if (
        len(parsed_values) >= 2
        and not has_explicit_unit
        and abs(raw_value) < 100
        and abs(parsed_values[1][0]) >= 100
    ):
        raw_value, has_explicit_unit = parsed_values[1]

    if has_explicit_unit:
        return raw_value
    return raw_value * SCALE_MULTIPLIERS.get(scale, 1)


def _parse_cashflow_capex_row_amount(row: list[Any], scale: str) -> float | None:
    row_text = _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))
    for match in _CASHFLOW_EXPLICIT_AMOUNT_RE.finditer(row_text):
        try:
            raw_value = float(match.group("num").replace(",", ""))
        except ValueError:
            continue
        suffix = str(match.group("suffix") or "").lower()
        value = raw_value * _ACCOUNTING_NUMBER_SUFFIX_MULTIPLIERS[suffix]
        if match.group("paren"):
            value = -abs(value)
        if value > 0 and _cashflow_row_is_outflow(row):
            value = -value
        return value

    value = _parse_current_period_metric_cell(row, scale)
    if value is not None:
        if value > 0 and _cashflow_row_is_outflow(row):
            value = -value
        return value

    return None


def _parse_cashflow_cash_end_row_amount(row: list[Any], scale: str) -> float | None:
    return _parse_current_period_metric_cell(row, scale)


def _normalise_cashflow_row_ref(value: Any) -> str:
    return _normalise_fragmented_pdf_text(str(value or "")).lower()


def _cashflow_row_ref_matches(row_label: Any, row_ref: Any) -> bool:
    label = _normalise_cashflow_row_ref(row_label)
    ref = _normalise_cashflow_row_ref(row_ref)
    if not label or not ref:
        return False
    return label == ref or label in ref or ref in label


def _coerce_cashflow_metric_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    parsed_value = _parse_accounting_metric_number(value)
    if parsed_value is None:
        return None
    return parsed_value[0]


def _parse_cashflow_row_ref_current_period_amount(
    row: Sequence[Any],
    scale: str,
) -> float | None:
    multiplier = SCALE_MULTIPLIERS.get(scale, 1)
    for cell in list(row)[1:]:
        parsed_value = _parse_accounting_metric_number(cell)
        if parsed_value is None:
            continue
        raw_float, has_explicit_unit = parsed_value
        return raw_float if has_explicit_unit else raw_float * multiplier
    return None


def _recover_cashflow_row_ref_amount(
    rows: Sequence[Sequence[Any]] | None,
    row_ref: Any,
    scale: str,
) -> float | None:
    if not rows or not row_ref:
        return None

    for row in rows:
        if not row or not _cashflow_row_ref_matches(row[0], row_ref):
            continue
        return _parse_cashflow_row_ref_current_period_amount(row, scale)

    return None


def _replace_cashflow_metric_if_over_scaled_from_row_ref(
    extracted: dict[str, Any],
    rows: Sequence[Sequence[Any]] | None,
    metric_name: str,
    scale: str,
) -> None:
    row_refs = extracted.get("row_refs")
    if not isinstance(row_refs, dict):
        return

    extracted_value = _coerce_cashflow_metric_float(extracted.get(metric_name))
    source_value = _recover_cashflow_row_ref_amount(rows, row_refs.get(metric_name), scale)
    if extracted_value is None or source_value is None or source_value == 0:
        return

    ratio = abs(extracted_value / source_value)
    if 999.0 <= ratio <= 1001.0:
        extracted[metric_name] = source_value


def _cell_lines(value: Any) -> list[str]:
    return [
        line
        for line in (
            _normalise_fragmented_pdf_text(raw_line)
            for raw_line in str(value or "").replace("\u00a0", " ").splitlines()
        )
        if line
    ]


def _grouped_cashflow_current_value_cell_index(table: Any) -> int:
    headers = list(getattr(table, "headers", []) or [])
    if (
        len(headers) > 1
        and _normalize_filter_text(headers[1]) in _CASHFLOW_NOTE_HEADER_LABELS
    ):
        return 2
    return 1


def _parse_grouped_cashflow_current_period_amount(
    row: Sequence[Any],
    scale: str,
    value_cell_index: int,
) -> float | None:
    row_values = list(row)
    if value_cell_index >= len(row_values):
        return None
    parsed_value = _parse_accounting_metric_number(row_values[value_cell_index])
    if parsed_value is None:
        return None
    raw_float, has_explicit_unit = parsed_value
    if has_explicit_unit:
        return raw_float
    return raw_float * SCALE_MULTIPLIERS.get(scale, 1)


def _recover_grouped_cashflow_capex_from_table(
    table: Any, scale: str
) -> tuple[float, str] | None:
    rows = list(getattr(table, "rows", []) or [])
    value_cell_index = _grouped_cashflow_current_value_cell_index(table)
    bank_cashflow_context = _cashflow_table_has_bank_capex_context(table)
    for row_index, row in enumerate(rows):
        if not row:
            continue
        label_lines = [
            line
            for line in _cell_lines(row[0])
            if _normalize_filter_text(line) not in _CASHFLOW_GROUPED_SECTION_LABELS
        ]
        if len(label_lines) <= 1:
            continue
        target_index: int | None = None
        target_label = ""
        for index, label in enumerate(label_lines):
            if _cashflow_row_has_strong_capex_label(
                [label],
                bank_cashflow_context=bank_cashflow_context,
            ):
                target_index = index
                target_label = label
                break
        if target_index is None:
            continue

        current_values: list[float] = []
        same_row_current = _parse_grouped_cashflow_current_period_amount(
            row,
            scale,
            value_cell_index,
        )
        if same_row_current is not None:
            current_values.append(same_row_current)

        for follower in rows[row_index + 1 :]:
            if not follower or _normalise_fragmented_pdf_text(follower[0]):
                break
            value = _parse_grouped_cashflow_current_period_amount(
                follower,
                scale,
                value_cell_index,
            )
            if value is None:
                break
            current_values.append(value)
            if len(current_values) >= len(label_lines):
                break

        if target_index >= len(current_values):
            continue
        value = current_values[target_index]
        if value > 0:
            value = -value
        return value, target_label
    return None


def _recover_preferred_cashflow_capex_from_table(
    table, scale: str
) -> tuple[float, str] | None:
    grouped = _recover_grouped_cashflow_capex_from_table(table, scale)
    if grouped is not None:
        return grouped

    best: tuple[int, float, str] | None = None
    bank_cashflow_context = _cashflow_table_has_bank_capex_context(table)
    for row in table.rows or []:
        if _cashflow_capex_row_is_disallowed_financial_asset(
            _normalise_fragmented_pdf_text(" ".join(str(cell) for cell in row))
        ):
            continue
        priority = _cashflow_row_capex_label_priority(
            row,
            bank_cashflow_context=bank_cashflow_context,
        )
        if priority <= 0:
            continue
        value = _parse_cashflow_capex_row_amount(row, scale)
        if value is None:
            continue
        row_ref = _cashflow_capex_row_ref(row)
        if best is None or priority > best[0]:
            best = (priority, value, row_ref)
    if best is None:
        return None
    _, value, row_ref = best
    return value, row_ref


def _recover_preferred_cashflow_cash_end_from_table(
    table, scale: str
) -> tuple[float, str] | None:
    for row in table.rows or []:
        if not _cashflow_row_has_strong_cash_end_label(row):
            continue
        value = _parse_cashflow_cash_end_row_amount(row, scale)
        if value is None:
            continue
        return value, _cashflow_cash_end_row_ref(row)
    return None


def _recover_preferred_cashflow_cash_end_from_tables(
    tables: Any,
    scale: Any,
) -> tuple[float, str, Any, str, str] | None:
    for table in tables or []:
        table_scale = _detect_scale_from_table(table)
        scale_for_table = table_scale if table_scale != "unknown" else str(scale or "unknown")
        recovered = _recover_preferred_cashflow_cash_end_from_table(
            table,
            scale_for_table,
        )
        if recovered is None:
            continue
        value, row_ref = recovered
        return (
            value,
            row_ref,
            getattr(table, "page_number", None),
            scale_for_table,
            "table" if table_scale != "unknown" else "document",
        )
    return None


_APPENDIX5B_SECTION_TOTALS = {
    "1.9": "operating_cf",
    "2.6": "investing_cf",
    "3.10": "financing_cf",
    "4.2": "operating_cf",
    "4.3": "investing_cf",
    "4.4": "financing_cf",
    "4.6": "cash_end",
}


def _normalise_appendix5b_section(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", "", text)
    return text.rstrip(".")


def _table_has_appendix5b_sections(table: Any) -> bool:
    text = _normalize_filter_text(
        " ".join(
            [
                str(getattr(table, "caption", "") or ""),
                " ".join(str(header) for header in getattr(table, "headers", []) or []),
                " ".join(
                    " ".join(str(cell) for cell in row)
                    for row in (getattr(table, "rows", []) or [])[:8]
                    if row
                ),
            ]
        )
    )
    if "appendix5b" in text:
        return True
    if "quarterlycashflowreport" in text and "statementofcashflows" in text:
        return True
    return any(
        row
        and (
            _normalise_appendix5b_section(row[0]) in _APPENDIX5B_SECTION_TOTALS
            or re.search(r"\b(?:1\.9|2\.6|3\.10|4\.3|4\.6)\b", str(row[0] or ""))
        )
        for row in (getattr(table, "rows", []) or [])
    )


def _recover_appendix5b_section_totals_from_table(
    table: Any, scale: str
) -> dict[str, tuple[float, str]]:
    if not _table_has_appendix5b_sections(table):
        return {}

    recovered: dict[str, tuple[float, str]] = {}
    for row in getattr(table, "rows", []) or []:
        if not row:
            continue
        for section, multiline_metric_name in _APPENDIX5B_SECTION_TOTALS.items():
            summary_section = section in {"4.2", "4.3", "4.4"}
            if multiline_metric_name in recovered and not summary_section:
                continue
            multiline = _parse_appendix5b_multiline_section_value(
                row,
                section,
                scale,
            )
            if multiline is not None:
                recovered[multiline_metric_name] = multiline
        metric_name = _APPENDIX5B_SECTION_TOTALS.get(
            _normalise_appendix5b_section(row[0])
        )
        if metric_name is None or metric_name in recovered:
            continue
        value = _parse_current_period_metric_cell(row, scale)
        if value is None:
            continue
        row_ref = _row_label_before_numeric_cells(row[1:]) or _normalise_fragmented_pdf_text(
            " ".join(str(cell) for cell in row[:2])
        )
        recovered[metric_name] = (value, row_ref)
    return recovered


def _parse_appendix5b_multiline_section_value(
    row: list[Any], section: str, scale: str
) -> tuple[float, str] | None:
    if len(row) < 2:
        return None
    label_lines = _cell_lines(row[0])
    value_lines = _cell_lines(row[1])
    if not label_lines or not value_lines:
        return None

    sections: list[tuple[str, str]] = []
    for line in label_lines:
        match = re.match(r"\s*(\d+\.\d+)\b\s*(.*)", line)
        if match:
            sections.append((match.group(1), line))

    for index, (candidate_section, label) in enumerate(sections):
        if candidate_section != section or index >= len(value_lines):
            continue
        parsed = _parse_accounting_metric_number(value_lines[index])
        if parsed is None:
            return None
        raw_value, has_explicit_unit = parsed
        value = (
            raw_value
            if has_explicit_unit
            else raw_value * SCALE_MULTIPLIERS.get(scale, 1)
        )
        return value, label
    return None


def _is_missing_row_ref(value: Any) -> bool:
    text = " ".join(str(value or "").strip().lower().split())
    return not text or text in {"unknown", "n/a", "na", "null", "none", "-"}


def _markdown_row_labels(table_markdown: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in str(table_markdown or "").splitlines():
        if "|" not in line:
            continue
        first_cell = line.split("|", 1)[0].strip()
        if not first_cell or set(first_cell) <= {"-"}:
            continue
        normalized = _normalize_filter_text(first_cell)
        if normalized:
            labels.setdefault(normalized, first_cell)
    return labels


def _split_row_ref_candidates(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = re.split(r"[,;]", str(value or ""))
    return [str(item or "").strip() for item in raw_items if str(item or "").strip()]


def _income_metric_for_row_label(
    row_label: str, *, bank_operating_income_total: bool = False
) -> str | None:
    compact = _normalize_filter_text(row_label)
    if not compact:
        return None
    if compact == "operatingincome" and bank_operating_income_total:
        return "revenue"
    if compact in {
        "netinterestincome",
        "totaloperatingincome",
        "netoperatingincome",
    }:
        return "revenue"
    if "ebitda" not in compact and (
        compact == "ebit"
        or "earningsbeforeinterestandtax" in compact
        or "profitfromoperations" in compact
        or "profitlossfromoperations" in compact
        or "profitlossfromoperatingactivities" in compact
        or "operatingprofit" in compact
        or "statutoryebit" in compact
        or compact == "operatingincome"
        or "profitbeforeincometax" in compact
        or "profitbeforetax" in compact
        or "profitfortheperiodbeforetax" in compact
        or "lossprofitfortheperiodbeforetax" in compact
        or "cashprofitbeforetax" in compact
    ):
        return "ebit"
    if (
        "npat" in compact
        or "netprofitaftertax" in compact
        or "profitaftertax" in compact
        or "profitafterincometax" in compact
        or "profitlossaftertax" in compact
        or "profitlossafterincometax" in compact
        or "profitattributable" in compact
        or "netprofitattributable" in compact
    ):
        return "np_attributable"
    if "revenue" in compact and not any(
        marker in compact
        for marker in ("grossprofit", "otherincome", "interestincome", "netprofit")
    ):
        return "revenue"
    return None


_NP_ATTRIBUTABLE_OWNER_MARKERS = (
    "equityholdersoftheparent",
    "ordinaryequityholdersofthecompany",
    "attributabletobhpshareholders",
    "attributabletoshareholders",
    "attributabletoowners",
    "attributabletomembers",
    "attributabletoequityholders",
)
_NP_ATTRIBUTABLE_CHILD_OWNER_MARKERS = (
    "shareholdersof",
    "equityholdersof",
    "ownersof",
    "membersof",
)
_NP_ATTRIBUTABLE_REJECT_MARKERS = (
    "noncontrolling",
    "minority",
    "comprehensive",
)


def _income_row_is_attributable_profit(
    row_label: str, previous_labels: list[str]
) -> bool:
    compact = _normalize_filter_text(row_label)
    if not compact:
        return False
    if any(marker in compact for marker in _NP_ATTRIBUTABLE_REJECT_MARKERS):
        return False
    if not any(marker in compact for marker in _NP_ATTRIBUTABLE_OWNER_MARKERS):
        return False

    context = _normalize_filter_text(" ".join(previous_labels[-6:]))
    if "comprehensive" in context and "profit" not in context:
        return False
    if "totalcomprehensive" in context:
        return False
    return True


def _income_owner_attributable_line_index(
    label_lines: list[str],
    previous_labels: list[str],
) -> int | None:
    context = _normalize_filter_text(" ".join(previous_labels[-6:]))
    context_is_attributable_profit = "attributable" in context and "profit" in context
    for index, label in enumerate(label_lines):
        compact = _normalize_filter_text(label)
        if not compact:
            continue
        if any(marker in compact for marker in _NP_ATTRIBUTABLE_REJECT_MARKERS):
            continue
        if any(marker in compact for marker in _NP_ATTRIBUTABLE_OWNER_MARKERS):
            return index
        if context_is_attributable_profit and any(
            marker in compact for marker in _NP_ATTRIBUTABLE_CHILD_OWNER_MARKERS
        ):
            return index
    return None


def _row_ref_is_owner_attributable_np(row_ref: Any) -> bool:
    compact = _normalize_filter_text(str(row_ref or ""))
    if not compact or any(
        marker in compact for marker in _NP_ATTRIBUTABLE_REJECT_MARKERS
    ):
        return False
    return any(marker in compact for marker in _NP_ATTRIBUTABLE_OWNER_MARKERS) or any(
        marker in compact for marker in _NP_ATTRIBUTABLE_CHILD_OWNER_MARKERS
    )


def _np_attributable_source_is_generic_profit(row_ref: Any, provenance: Any) -> bool:
    compact = _normalize_filter_text(_combined_source_text(row_ref, provenance))
    if not compact or _row_ref_is_owner_attributable_np(compact):
        return False
    return any(
        marker in compact
        for marker in (
            "netprofitfortheperiod",
            "profitfortheperiod",
            "profitlossfortheperiod",
            "profitaftertaxation",
            "profitaftertax",
            "profitafterincometax",
            "profitlossaftertax",
            "profitlossafterincometax",
        )
    )


def _clean_income_statement_row_ref(label: Any) -> str:
    row_ref = _normalise_fragmented_pdf_text(label)
    return _re.sub(r"\s+\d+$", "", row_ref).strip()


def _recover_revenue_from_multiline_income_row(
    row: list[Any],
    scale: str,
    *,
    bank_operating_income_total: bool = False,
) -> tuple[float, str] | None:
    label_lines = _split_table_cell_lines(row[0]) if row else []
    if len(label_lines) < 2:
        return None

    best_line_index: int | None = None
    best_priority = -1
    for index, label in enumerate(label_lines):
        if (
            _income_metric_for_row_label(
                label,
                bank_operating_income_total=bank_operating_income_total,
            )
            != "revenue"
        ):
            continue
        priority = _income_metric_priority_for_row_label(label, "revenue", [])
        if priority > best_priority:
            best_line_index = index
            best_priority = priority
    if best_line_index is None:
        return None

    for cell in row[1:]:
        value_lines = _split_table_cell_lines(cell)
        if len(value_lines) <= best_line_index:
            continue
        value = _scaled_metric_value_from_text(
            value_lines[best_line_index],
            scale,
        )
        if value is not None:
            return value, _clean_income_statement_row_ref(
                label_lines[best_line_index]
            )
    return None


def _parse_fragmented_income_statement_current_period_cell(
    row: list[Any],
    scale: str,
) -> float | None:
    parsed_cells: list[tuple[str, float, bool]] = []
    for cell in row[1:]:
        text = _normalise_fragmented_pdf_text(cell)
        if not text:
            continue
        parsed = _parse_accounting_metric_number(text)
        if parsed is None:
            continue
        raw_value, has_explicit_unit = parsed
        parsed_cells.append((text, raw_value, has_explicit_unit))

    if len(parsed_cells) >= 2:
        first_text, first_raw, first_has_unit = parsed_cells[0]
        second_text, second_raw, second_has_unit = parsed_cells[1]
        if (
            not first_has_unit
            and not second_has_unit
            and first_raw.is_integer()
            and 0 < abs(first_raw) < 100
            and abs(second_raw) >= 100
            and "," in second_text
        ):
            second_digits = _re.sub(r"\D", "", second_text)
            if len(second_digits) >= 3:
                sign = -1 if first_raw < 0 or second_raw < 0 else 1
                raw_value = sign * float(f"{int(abs(first_raw))}{second_digits}")
                return raw_value * SCALE_MULTIPLIERS.get(scale, 1)

    return _parse_current_period_metric_cell(row, scale)


def _recover_owner_np_attributable_from_income_row(
    row: list[Any],
    row_label: str,
    previous_labels: list[str],
    scale: str,
) -> tuple[float, str] | None:
    label_lines = _split_table_cell_lines(row[0]) if row else []
    if not label_lines:
        label_lines = [row_label]
    owner_line_index = _income_owner_attributable_line_index(
        label_lines,
        previous_labels,
    )
    if owner_line_index is None and len(label_lines) == 1 and label_lines[0] != row_label:
        label_lines = [row_label]
        owner_line_index = _income_owner_attributable_line_index(
            label_lines,
            previous_labels,
        )
    if owner_line_index is None:
        return None

    row_ref = label_lines[owner_line_index].replace("BH P", "BHP")
    if len(label_lines) > 1:
        for cell in row[1:]:
            value_lines = _split_table_cell_lines(cell)
            if len(value_lines) <= owner_line_index:
                continue
            value = _scaled_metric_value_from_text(
                value_lines[owner_line_index],
                scale,
            )
            if value is not None:
                return value, row_ref

    value = _parse_fragmented_income_statement_current_period_cell(row, scale)
    if value is None:
        return None
    return value, row_ref


def _income_metric_row_ref_for_row(
    row: list[Any],
    row_label: str,
    metric_name: str,
    *,
    bank_operating_income_total: bool = False,
) -> str:
    if metric_name != "ebit":
        return row_label
    for label in _split_table_cell_lines(row[0]) if row else []:
        if (
            _income_metric_for_row_label(
                label,
                bank_operating_income_total=bank_operating_income_total,
            )
            != metric_name
        ):
            continue
        compact = _normalize_filter_text(label)
        if any(blocker in compact for blocker, _source_label in _EBIT_LABEL_BLOCKERS):
            continue
        return _clean_income_statement_row_ref(label)
    return row_label


def _income_metric_priority_for_row_label(
    row_label: str,
    metric_name: str,
    previous_labels: list[str],
) -> int:
    compact = _normalize_filter_text(row_label)
    if metric_name == "revenue":
        if compact in {"operatingincome", "totaloperatingincome", "netoperatingincome"}:
            return 95
        if "totaloperatingrevenue" in compact:
            return 110
        if "totalrevenuefromordinaryactivities" in compact:
            return 100
        if "revenuefromcontinuingoperations" in compact:
            return 90
        if compact in {"totalrevenue", "totalrevenues"} or "totalrevenue" in compact:
            return 80
        return 10
    if metric_name == "ebit":
        if "beforeincometax" in compact or "beforetax" in compact:
            return 90
        return 50
    if metric_name == "np_attributable":
        if _income_row_is_attributable_profit(row_label, previous_labels):
            return 150
        if _row_ref_is_owner_attributable_np(row_label):
            return 140
        if "netprofitattributable" in compact or "profitattributable" in compact:
            return 130
        if "afterincometaxfromcontinuingoperations" in compact:
            return 110
        if "profitafterincometax" in compact or "profitaftertax" in compact:
            return 100
        context = _normalize_filter_text(" ".join(previous_labels[-4:]))
        if (
            compact in {"profitfortheperiod", "profitforthehalfyearafterincometax"}
            or "profitfortheperiod" in compact
            or "profitforthehalfyearafterincometax" in compact
        ) and "incometax" in context:
            return 80
        return 50
    return 0


def _table_has_bank_operating_income_total_context(table: Any) -> bool:
    text = _table_precedence_text(table)
    if "netinterestincome" not in text:
        return False
    return any(
        marker in text
        for marker in (
            "creditimpairment",
            "profitbeforecreditimpairmentandincometax",
        )
    )


def _recover_income_statement_metrics_from_table(
    table: Any, scale: str, rows_override: list[list[Any]] | None = None
) -> dict[str, tuple[float, str]]:
    recovered: dict[str, tuple[int, float, str]] = {}
    previous_labels: list[str] = []
    formal_statement_context = any(
        marker in _table_precedence_text(table, max_rows=4)
        for marker in (
            "statementofcomprehensiveincome",
            "statementofprofitorloss",
        )
    )
    bank_operating_income_total = _table_has_bank_operating_income_total_context(table)
    rows = rows_override if rows_override is not None else getattr(table, "rows", [])
    for row in rows or []:
        if not row:
            continue
        row_label = _row_label_before_numeric_cells(row)
        if not row_label:
            continue

        revenue_recovery = _recover_revenue_from_multiline_income_row(
            row,
            scale,
            bank_operating_income_total=bank_operating_income_total,
        )
        if revenue_recovery is not None:
            value, row_ref = revenue_recovery
            priority = _income_metric_priority_for_row_label(
                row_ref,
                "revenue",
                previous_labels,
            )
            existing = recovered.get("revenue")
            if existing is None or priority > existing[0]:
                recovered["revenue"] = (priority, value, row_ref)

        owner_np_recovery = _recover_owner_np_attributable_from_income_row(
            row,
            row_label,
            previous_labels,
            scale,
        )
        if owner_np_recovery is not None:
            value, row_ref = owner_np_recovery
            existing = recovered.get("np_attributable")
            if existing is None or 150 > existing[0]:
                recovered["np_attributable"] = (150, value, row_ref)

        metric_name = _income_metric_for_row_label(
            row_label,
            bank_operating_income_total=bank_operating_income_total,
        )
        if metric_name == "np_attributable" and not any(
            marker in _normalize_filter_text(row_label)
            for marker in (
                "npat",
                "netprofitattributable",
                "profitattributable",
                "attributable",
                "profitaftertax",
                "profitafterincometax",
                "profitlossaftertax",
                "profitlossafterincometax",
            )
        ):
            metric_name = None
        if metric_name is None and _income_row_is_attributable_profit(
            row_label, previous_labels
        ):
            metric_name = "np_attributable"
        if metric_name is None and formal_statement_context:
            compact = _normalize_filter_text(row_label)
            context = _normalize_filter_text(" ".join(previous_labels[-4:]))
            if (
                compact in {"profitfortheperiod", "profitforthehalfyearafterincometax"}
                or "profitfortheperiod" in compact
            ) and "incometax" in context:
                metric_name = "np_attributable"

        if metric_name in {"revenue", "ebit", "np_attributable"}:
            value = _parse_current_period_metric_cell(row, scale)
            if value is not None:
                row_ref = _income_metric_row_ref_for_row(
                    row,
                    row_label,
                    metric_name,
                    bank_operating_income_total=bank_operating_income_total,
                )
                priority = _income_metric_priority_for_row_label(
                    row_ref,
                    metric_name,
                    previous_labels,
                )
                existing = recovered.get(metric_name)
                if existing is None or priority > existing[0]:
                    recovered[metric_name] = (priority, value, row_ref)

        previous_labels.append(row_label)
    return {
        metric_name: (value, row_label)
        for metric_name, (_priority, value, row_label) in recovered.items()
    }


_SHARE_COUNT_ROW_MARKERS = (
    "issuedordinarysharesfullypaidat",
    "issuedordinarysharesfullypaid",
    "sharesnotifiedtotheaustralianstockexchange",
    "sharesnotifiedtotheaustraliansecuritiesexchange",
    "balanceat31december",
    "balanceattheendoftheperiod",
    "balanceatendofperiod",
    "at31december",
    "at30june",
    "closingbalance",
    "ordinarysharesatendofperiod",
)


def _share_row_is_weighted_average(compact_text: str) -> bool:
    return "weighted" in compact_text and "average" in compact_text


def _share_count_multiplier_from_table(table: Any) -> int:
    text = _normalize_filter_text(
        " ".join(
            [
                str(getattr(table, "caption", "") or ""),
                " ".join(str(header) for header in getattr(table, "headers", []) or []),
                " ".join(
                    " ".join(str(cell) for cell in row)
                    for row in (getattr(table, "rows", []) or [])[:4]
                    if row
                ),
            ]
        )
    )
    if (
        "numberofsharesmillions" in text
        or ("numberofshares" in text and "millions" in text)
        or ("sharesmillions" in text and "usm" in text)
    ):
        return 1_000_000
    if (
        "no000s" in text
        or "numberofshares000" in text
        or ("numberofshares" in text and "000s" in text)
    ):
        return 1_000
    return 1


def _share_count_unit(multiplier: int) -> str:
    return {
        1: "units",
        1_000: "thousands",
        1_000_000: "millions",
        1_000_000_000: "billions",
        1_000_000_000_000: "trillions",
    }.get(multiplier, "unknown")


@dataclass(frozen=True)
class _RecoveredShareObservation:
    value: float
    row_ref: str
    row_index: int
    column_index: int
    raw_value: str
    source_unit: str
    unique_preferred_candidate: bool


def _share_count_cell_from_row(
    row: list[Any],
    *,
    table_multiplier: int,
) -> tuple[int, str, float, str] | None:
    parsed_cells: list[tuple[int, str, float, bool]] = []
    for column_index, cell in enumerate(row[1:], start=1):
        parsed = _parse_accounting_metric_number(cell)
        if parsed is None:
            continue
        parsed_cells.append((column_index, str(cell or "").strip(), *parsed))
    if not parsed_cells:
        return None

    selected = parsed_cells[0]
    if (
        len(parsed_cells) >= 2
        and not selected[3]
        and abs(selected[2]) < 100
        and abs(parsed_cells[1][2]) >= 100
    ):
        selected = parsed_cells[1]
    column_index, raw_cell, raw_value, has_explicit_unit = selected
    if has_explicit_unit or abs(raw_value) >= 1_000_000:
        effective_multiplier = 1
        value = raw_value
    else:
        effective_multiplier = table_multiplier
        value = raw_value * table_multiplier
    compact_label = _normalize_filter_text(_row_label_before_numeric_cells(row))
    if (
        value < 1_000_000
        and 100 <= abs(raw_value) < 1_000_000
        and "issuedordinarysharesfullypaid" in compact_label
        and len(parsed_cells) >= 2
    ):
        value = raw_value * 1_000_000
        effective_multiplier = 1_000_000
    return column_index, raw_cell, value, _share_count_unit(effective_multiplier)


def _share_count_table_surface(table: Any, *, row_limit: int = 10) -> str:
    return " ".join(
        [
            str(getattr(table, "caption", "") or ""),
            " ".join(str(header) for header in getattr(table, "headers", []) or []),
            " ".join(
                " ".join(str(cell) for cell in row)
                for row in (getattr(table, "rows", []) or [])[:row_limit]
                if row
            ),
        ]
    )


def _table_has_share_count_evidence(table: Any) -> bool:
    text = _share_count_table_surface(table)
    compact = _normalize_filter_text(text)
    if any(
        marker in compact
        for marker in ("numberofshares", "ordinaryshares", "sharecapital")
    ):
        return True

    words = set(_re.findall(r"[a-z]+", text.lower()))
    return {"issued", "treasury", "contributed", "shares", "equity"}.issubset(
        words
    )


def _share_row_period_match_rank(compact_label: str, period_end: Any) -> int:
    parsed_period_end = parse_period_end(str(period_end) if period_end else None)
    if parsed_period_end is None:
        return 0
    month_name = parsed_period_end.strftime("%B").lower()
    exact = _normalize_filter_text(
        f"At {parsed_period_end.day} {month_name} {parsed_period_end.year}"
    )
    without_year = _normalize_filter_text(f"At {parsed_period_end.day} {month_name}")
    if exact in compact_label:
        return 2
    if without_year in compact_label:
        return 1
    return 0


def _recover_preferred_share_observation_from_table(
    table: Any,
    *,
    period_end: Any = None,
) -> _RecoveredShareObservation | None:
    multiplier = _share_count_multiplier_from_table(table)
    table_has_share_count_evidence = _table_has_share_count_evidence(table)
    candidates: list[tuple[int, int, _RecoveredShareObservation]] = []
    for row_index, row in enumerate(getattr(table, "rows", []) or []):
        if not row:
            continue
        row_label = _row_label_before_numeric_cells(row)
        compact_label = _normalize_filter_text(row_label)
        if _share_row_is_weighted_average(compact_label):
            continue
        if not any(marker in compact_label for marker in _SHARE_COUNT_ROW_MARKERS):
            continue
        row_has_share_count_evidence = any(
            marker in compact_label
            for marker in ("share", "security", "securities", "unit", "stapled")
        )
        if (
            any(
                marker in compact_label
                for marker in (
                    "balanceat",
                    "at31december",
                    "at30june",
                    "closingbalance",
                    "ordinarysharesatendofperiod",
                )
            )
            and not table_has_share_count_evidence
            and not row_has_share_count_evidence
        ):
            continue
        selected_cell = _share_count_cell_from_row(
            row,
            table_multiplier=multiplier,
        )
        if selected_cell is None:
            continue
        column_index, raw_cell, value, source_unit = selected_cell
        if value >= 1_000_000:
            rank = 1
            if any(
                marker in compact_label
                for marker in (
                    "at30june",
                    "at31december",
                    "atend",
                    "endoftheperiod",
                    "balanceat31december",
                    "balanceattheendoftheperiod",
                    "balanceatendofperiod",
                    "closingbalance",
                )
            ):
                rank = 3
            if any(
                marker in compact_label
                for marker in ("beginning", "at1january", "atbeginning")
            ):
                rank = 0
            candidates.append(
                (
                    rank,
                    _share_row_period_match_rank(compact_label, period_end),
                    _RecoveredShareObservation(
                        value=value,
                        row_ref=row_label,
                        row_index=row_index,
                        column_index=column_index,
                        raw_value=raw_cell,
                        source_unit=source_unit,
                        unique_preferred_candidate=False,
                    ),
                )
            )
    if not candidates:
        return None
    _rank, _period_rank, observation = max(
        candidates,
        key=lambda item: (item[0], item[1], item[2].row_index),
    )
    unique_preferred_candidate = (
        len(
            [
                candidate
                for candidate in candidates
                if candidate[0:2] == (_rank, _period_rank)
            ]
        )
        == 1
    )
    return _RecoveredShareObservation(
        value=observation.value,
        row_ref=observation.row_ref,
        row_index=observation.row_index,
        column_index=observation.column_index,
        raw_value=observation.raw_value,
        source_unit=observation.source_unit,
        unique_preferred_candidate=unique_preferred_candidate,
    )


def _recover_preferred_share_observation_from_split_header_table(
    previous_table: Any,
    table: Any,
    *,
    period_end: Any = None,
) -> _RecoveredShareObservation | None:
    if previous_table is None:
        return None
    if getattr(previous_table, "page_number", None) != getattr(
        table, "page_number", None
    ):
        return None
    if not _table_has_share_count_evidence(previous_table):
        return None

    from app.services.docling_extract import DoclingTable

    combined = DoclingTable(
        page_number=getattr(table, "page_number", None),
        caption=" ".join(
            part
            for part in (
                str(getattr(previous_table, "caption", "") or ""),
                str(getattr(table, "caption", "") or ""),
            )
            if part
        ),
        headers=list(getattr(previous_table, "headers", []) or []),
        rows=list(getattr(previous_table, "rows", []) or [])
        + list(getattr(table, "rows", []) or []),
    )
    observation = _recover_preferred_share_observation_from_table(
        combined,
        period_end=period_end,
    )
    if observation is None:
        return None
    previous_row_count = len(getattr(previous_table, "rows", []) or [])
    if observation.row_index < previous_row_count:
        return None
    return _RecoveredShareObservation(
        value=observation.value,
        row_ref=observation.row_ref,
        row_index=observation.row_index - previous_row_count,
        column_index=observation.column_index,
        raw_value=observation.raw_value,
        source_unit=observation.source_unit,
        unique_preferred_candidate=observation.unique_preferred_candidate,
    )


def _period_bound_share_source_cell(
    table: Any,
    observation: _RecoveredShareObservation,
    *,
    period_end: Any,
) -> dict[str, Any] | None:
    if not observation.unique_preferred_candidate:
        return None
    requested = parse_period_end(str(period_end) if period_end else None)
    if requested is None:
        return None
    parsed = _parse_accounting_metric_number(observation.raw_value)
    multiplier = SCALE_MULTIPLIERS.get(observation.source_unit)
    if parsed is None or multiplier is None:
        return None
    raw_value, has_explicit_unit = parsed
    normalized = raw_value if has_explicit_unit else raw_value * multiplier
    if normalized != observation.value:
        return None
    row_dates = _period_dates_from_header_cell(observation.row_ref)
    if (
        (row_dates and row_dates != [requested])
        or _has_unresolved_period_evidence(observation.row_ref)
    ):
        return None
    header_rows = getattr(table, "raw_header_rows", None) or [
        getattr(table, "headers", None) or []
    ]
    selected_header_text = " ".join(
        str(row[observation.column_index] or "")
        for row in header_rows
        if observation.column_index < len(row)
    )
    if _has_unresolved_period_evidence(selected_header_text):
        return None

    binding = _bind_current_period_column(table, requested.isoformat())
    if (
        binding.get("status") == "BOUND"
        and binding.get("column_index") == observation.column_index
    ):
        header_cell = binding["header_cell"]
        column_role = binding.get("column_role")
    elif row_dates == [requested]:
        if _period_dates_from_header_cell(selected_header_text):
            return None
        header_cell = observation.row_ref
        column_role = "period_end_row"
    else:
        return None

    source_cell = {
        "page_number": getattr(table, "page_number", None),
        "row_index": observation.row_index,
        "column_index": observation.column_index,
        "row_label": observation.row_ref,
        "raw_value": observation.raw_value,
        "scaled_value": observation.value,
        "header_cell": header_cell,
        "requested_period_end": requested.isoformat(),
    }
    table_index = _normalized_table_index(table)
    if table_index is not None:
        source_cell["table_index"] = table_index
    if column_role is not None:
        source_cell["column_role"] = column_role
    return source_cell


def _expand_income_statement_row_refs(
    row_refs: Any, table_markdown: str, metrics_payload: dict[str, Any]
) -> dict[str, Any]:
    refs = dict(row_refs) if isinstance(row_refs, dict) else {}
    combined_candidates = _split_row_ref_candidates(refs.get("metric_name"))
    if not combined_candidates:
        return refs

    source_labels = _markdown_row_labels(table_markdown)
    for candidate in combined_candidates:
        source_label = source_labels.get(_normalize_filter_text(candidate))
        if not source_label:
            continue
        metric_name = _income_metric_for_row_label(source_label)
        if (
            metric_name in {"revenue", "ebit", "np_attributable"}
            and metrics_payload.get(metric_name) is not None
            and _is_missing_row_ref(refs.get(metric_name))
        ):
            refs[metric_name] = source_label
    return refs


def _sanitized_exception_chain(exc: Exception) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        response = getattr(current, "response", None)
        status_code = getattr(response, "status_code", None)
        chain.append(
            {
                "exception_type": type(current).__name__,
                "status_code": status_code if isinstance(status_code, int) else None,
            }
        )
        current = current.__cause__ or current.__context__
    return chain


def _capture_pass3a_failure(
    capture: SimpleQueue[dict[str, Any]] | None,
    *,
    table_type: str,
    initial_error: Exception,
    retry_error: Exception | None = None,
) -> None:
    if capture is None:
        return
    payload: dict[str, Any] = {
        "stage": "pass3a",
        "table_type": table_type,
        "initial_error_chain": _sanitized_exception_chain(initial_error),
    }
    if retry_error is not None:
        payload["retry_error_chain"] = _sanitized_exception_chain(retry_error)
    capture.put(payload)


def _extract_single_table(
    table_type: str,
    table,
    pass1_result: dict,
    scale: str,
    multiplier: float,
    llm_client,
    *,
    prompt_bundle: PromptBundle | None = None,
    model_override: str | None = None,
    failure_capture: SimpleQueue[dict[str, Any]] | None = None,
) -> dict | None:
    """Extract metrics from a single labelled table via one LLM call.

    Returns a tagged extraction dict, or None if extraction fails entirely.
    This function is safe to call from multiple threads — it uses only
    thread-local variables and thread-safe LLM/routing infrastructure.
    """
    bundle = prompt_bundle or resolve("default")
    metrics = _METRIC_SCHEMA_BY_TABLE.get(table_type, METRIC_FIELDS)
    contract_metrics = pass1_result.get("_contract_allowed_canonical_metrics")
    if isinstance(contract_metrics, (list, tuple, set, frozenset)):
        allowed_metrics = set(contract_metrics)
        metrics = [
            metric
            for metric in metrics
            if metric in allowed_metrics
            or (metric == "total_debt" and "net_debt" in allowed_metrics)
        ]
    if not metrics:
        return None
    metric_schema = "\n".join(f'  "{m}": "number|null",' for m in metrics)
    # Cash flow tables need a higher row cap:
    #   - Merged 5B tables may have 50+ rows (section 4 totals near the end)
    #   - Large-company CF statements (e.g. BHP) have 50+ rows with financing
    #     section and cash-end beyond row 30
    # Income statements also benefit from a higher cap to capture tax/OCI rows.
    if table_type == "cashflow_statement":
        row_cap = 65
    elif table_type == "income_statement":
        row_cap = 40
    else:
        row_cap = 30
    # Pre-filter rows to reduce token count on large tables.
    # Controlled by EXTRACTION_FILTER_ROWS env var (default: enabled).
    filter_enabled = os.environ.get("EXTRACTION_FILTER_ROWS", "1") != "0"
    if filter_enabled:
        filtered_rows = _filter_table_rows(table, table_type)
        markdown = _table_to_markdown(
            table,
            max_rows=row_cap,
            rows_override=filtered_rows,
        )
    else:
        filtered_rows = None
        markdown = _table_to_markdown(table, max_rows=row_cap)
    if not markdown:
        return None
    table_scale = _detect_scale_from_table(table)
    scale_for_table = table_scale if table_scale != "unknown" else scale
    multiplier_for_table = SCALE_MULTIPLIERS.get(scale_for_table, multiplier)
    scale_source = "table" if table_scale != "unknown" else "document"
    if table_scale != "unknown" and table_scale != scale:
        logger.info(
            "table-local scale (%s) overrides document-level scale (%s) for %s",
            table_scale,
            scale,
            table_type,
        )

    sanity_cap = _native_currency_sanity_cap(pass1_result.get("currency"))

    def _build_prompt(table_markdown: str) -> str:
        return bundle.pass3a.format(
            period_type=pass1_result.get("report_type", "?"),
            period_end=pass1_result.get("period_end", "?"),
            currency=pass1_result.get("currency", "AUD"),
            scale=scale_for_table,
            table_type=table_type,
            table_markdown=table_markdown,
            metric_list=", ".join(metrics),
            metric_schema=metric_schema,
        )

    def _build_output(
        raw_payload: dict[str, Any],
        *,
        table_markdown: str,
        rows_override: list[list[Any]] | None = None,
    ) -> dict[str, Any]:
        # Support both old flat format and new nested format
        metrics_payload = raw_payload.get("metrics")
        if not isinstance(metrics_payload, dict):
            metrics_payload = raw_payload

        raw_row_refs = raw_payload.get("row_refs")
        row_refs = dict(raw_row_refs) if isinstance(raw_row_refs, dict) else {}

        # shares_outstanding is always an absolute count — the prompt instructs the LLM
        # to output the absolute number (e.g. 5057000000 not 5057 when the table says
        # "5,057 (Million)"). No post-hoc scale multiplication needed.
        _COUNT_METRICS = {"shares_outstanding"}
        extracted = {
            "_source": table_type,
            "_page_number": getattr(table, "page_number", None),
            "_scale": scale_for_table,
            "_scale_source": scale_source,
            "_thinking": raw_payload.get("thinking"),
            "_markdown": table_markdown,
            "row_refs": row_refs,
        }
        ocr_candidates = getattr(table, "ocr_source_candidates", None)
        if not isinstance(ocr_candidates, list):
            ocr_candidates = []
        ocr_metric_provenance: dict[str, dict[str, Any]] = {}
        for metric_name in metrics:
            val = metrics_payload.get(metric_name)
            if val is not None:
                parsed_value = _parse_accounting_metric_number(val)
                if parsed_value is not None:
                    raw_float, has_explicit_unit = parsed_value
                    effective_multiplier = 1 if (
                        metric_name in _COUNT_METRICS or has_explicit_unit
                    ) else multiplier_for_table
                    scaled = raw_float * effective_multiplier
                    if (
                        effective_multiplier > 1
                        and abs(scaled) > sanity_cap
                        and abs(raw_float) <= sanity_cap
                    ):
                        logger.warning(
                            "LLM pre-scaled %s for %s: raw=%s, scaled=%s exceeds native cap %s — using raw value",
                            metric_name,
                            table_type,
                            raw_float,
                            scaled,
                            sanity_cap,
                        )
                        scaled = raw_float
                    if table_type == "net_debt_note" and metric_name == "net_debt":
                        # Point-in-time net debt note tables often present debt
                        # as a liability-style negative, while the canonical
                        # metric stores net debt as a positive magnitude.
                        scaled = abs(scaled)
                    extracted[metric_name] = scaled
                    if ocr_candidates:
                        matching_candidates = []
                        for candidate in ocr_candidates:
                            if not isinstance(candidate, dict):
                                continue
                            parsed_candidate = _parse_accounting_metric_number(
                                candidate.get("candidate_value_text")
                            )
                            if parsed_candidate is None:
                                continue
                            candidate_value, _candidate_has_unit = parsed_candidate
                            if abs(candidate_value - raw_float) <= 1e-9:
                                matching_candidates.append(candidate)
                        # OCR-derived metrics require one deterministic source
                        # cell mapping. Ambiguous or invented model values abstain.
                        if len(matching_candidates) != 1:
                            extracted[metric_name] = None
                        else:
                            ocr_metric_provenance[metric_name] = dict(
                                matching_candidates[0]
                            )
                            extracted["row_refs"][metric_name] = str(
                                matching_candidates[0]["source_text"]
                            )
                else:
                    extracted[metric_name] = None
            else:
                extracted[metric_name] = None
        if ocr_candidates:
            extracted["_ocr_metric_provenance"] = ocr_metric_provenance

        _MIN_PLAUSIBLE_SHARES = 1_000_000
        shares_val = extracted.get("shares_outstanding")
        if shares_val is not None:
            # Scan caption, all column headers, all first-column row labels, AND all
            # cells from the first 3 body rows.  SEG-style tables place the unit
            # indicator ("No. '000s") in the second column of the first body row —
            # not in the docling-extracted headers list — so limiting to row[0] alone
            # would miss it.
            share_surfaces = [
                table.caption or "",
                " ".join(str(h) for h in table.headers),
                " ".join(str(row[0]) for row in table.rows if row),
                " ".join(
                    " ".join(str(c) for c in row)
                    for row in (table.rows or [])[:3]
                    if row
                ),
            ]
            compact_share_text = _normalize_filter_text(" ".join(share_surfaces))
            has_share_count_evidence = any(
                marker in compact_share_text
                for marker in (
                    "numberofshares",
                    "numberofsecurities",
                    "numberofunits",
                    "noofsecurities",
                    # SEG-style column headers: "No. '000s" → "no000s" after normalization
                    "no000s",
                    "noofunits",
                    "sharesonissue",
                    "securitiesonissue",
                    "unitsonissue",
                    "stapledsecurities",
                    "issuedordinaryshares",
                    # Plain "Ordinary shares" row label (common in balance sheet tables)
                    "ordinaryshares",
                    "ordinarysharesfullypaid",
                    "fullypaidordinaryshares",
                    "sharesnotifiedtotheaustralianstockexchange",
                    "sharesnotifiedtotheaustraliansecuritiesexchange",
                )
            )
            if not has_share_count_evidence and table_type == "share_capital":
                has_share_count_evidence = (
                    "sharecapital" in compact_share_text
                    and "number" in compact_share_text
                )
            row_ref_text = _normalize_filter_text(
                str(
                    (
                        raw_payload.get("row_refs")
                        if isinstance(raw_payload.get("row_refs"), dict)
                        else {}
                    ).get("shares_outstanding")
                    or ""
                )
            )
            row_ref_is_weighted_average = _share_row_is_weighted_average(row_ref_text)
            row_ref_has_share_count_evidence = any(
                marker in row_ref_text
                for marker in (
                    "share",
                    "security",
                    "securities",
                    "unit",
                    "stapled",
                    "ordinary",
                    "issued",
                )
            )
            row_labels = [
                _normalize_filter_text(row[0]) for row in table.rows if row
            ]
            weighted_average_only = bool(row_labels) and all(
                _share_row_is_weighted_average(label) or not label
                for label in row_labels[1:]
            )
            if weighted_average_only or row_ref_is_weighted_average or (
                not has_share_count_evidence
                and not row_ref_has_share_count_evidence
            ):
                logger.info(
                    "Nulling shares_outstanding from %s due to weak count evidence",
                    table_type,
                )
                extracted["shares_outstanding"] = None
                shares_val = None
        if shares_val is not None and 0 < abs(shares_val) < _MIN_PLAUSIBLE_SHARES:
            header_caption_text = (
                (table.caption or "").lower()
                + " "
                + " ".join(str(h) for h in table.headers).lower()
            )
            body_text = " ".join(
                " ".join(str(c) for c in row) for row in table.rows[:15] if row
            ).lower()
            full_text = header_caption_text + " " + body_text
            if _re.search(r"'000|thousands|\bno\.\s*'?000", full_text, _re.IGNORECASE):
                extracted["shares_outstanding"] = shares_val * 1_000
                logger.info(
                    "shares_outstanding scaled ×1000: %.0f → %.0f (table text has '000 indicator)",
                    shares_val,
                    extracted["shares_outstanding"],
                )
            elif _re.search(r"\bmillion|\bm\b", full_text, _re.IGNORECASE):
                extracted["shares_outstanding"] = shares_val * 1_000_000
                logger.info(
                    "shares_outstanding scaled ×1M: %.0f → %.0f (table text has million indicator)",
                    shares_val,
                    extracted["shares_outstanding"],
                )
            elif scale_for_table in ("thousands", "millions"):
                doc_mult = SCALE_MULTIPLIERS.get(scale_for_table, 1)
                extracted["shares_outstanding"] = shares_val * doc_mult
                logger.info(
                    "shares_outstanding scaled ×%d (source scale=%s): %.0f → %.0f",
                    doc_mult,
                    scale_for_table,
                    shares_val,
                    extracted["shares_outstanding"],
                )

        extracted["row_refs"] = dict(raw_row_refs) if isinstance(raw_row_refs, dict) else {}
        extracted["period_col"] = raw_payload.get("period_col")
        if table_type == "income_statement":
            extracted["row_refs"] = _expand_income_statement_row_refs(
                extracted.get("row_refs"),
                table_markdown,
                metrics_payload,
            )
            for metric_name, (
                recovered_value,
                recovered_row_ref,
            ) in _recover_income_statement_metrics_from_table(
                table, scale_for_table, rows_override=rows_override
            ).items():
                if extracted.get(metric_name) is None:
                    extracted[metric_name] = recovered_value
                    extracted["row_refs"][metric_name] = recovered_row_ref
                    logger.info(
                        "Recovered income-statement %s from source row on page %s",
                        metric_name,
                        getattr(table, "page_number", "?"),
                    )
        if table_type == "share_capital":
            recovered_shares = _recover_preferred_share_observation_from_table(
                table,
                period_end=pass1_result.get("period_end"),
            )
            if recovered_shares is not None:
                extracted["shares_outstanding"] = recovered_shares.value
                extracted["row_refs"]["shares_outstanding"] = recovered_shares.row_ref
                logger.info(
                    "Recovered shares_outstanding from preferred share-count row on page %s",
                    getattr(table, "page_number", "?"),
                )
        if table_type == "balance_sheet" and extracted["row_refs"].get("total_debt"):
            preferred_total_debt_ref = _select_preferred_evidence_row_ref(
                extracted["row_refs"].get("total_debt"),
                strong_markers=_STRONG_TOTAL_DEBT_ROW_REFS,
                weak_markers=_WEAK_TOTAL_DEBT_ROW_REFS,
            )
            if preferred_total_debt_ref:
                extracted["row_refs"]["total_debt"] = preferred_total_debt_ref
        if (
            table_type == "balance_sheet"
            and extracted.get("total_debt") is not None
            and not extracted["row_refs"].get("total_debt")
        ):
            inferred_total_debt_ref = _infer_total_debt_row_ref(table)
            if inferred_total_debt_ref:
                extracted["row_refs"]["total_debt"] = inferred_total_debt_ref
        if table_type == "balance_sheet":
            recovered_total_debt = _recover_total_debt_from_balance_sheet_table(
                table,
                scale_for_table,
            )
            if recovered_total_debt is not None:
                recovered_value, recovered_row_refs = recovered_total_debt
                current_value = extracted.get("total_debt")
                should_replace = current_value is None
                if current_value is not None:
                    try:
                        should_replace = abs(float(current_value) - recovered_value) > 0.5
                    except (TypeError, ValueError):
                        should_replace = True
                if should_replace:
                    extracted["total_debt"] = recovered_value
                    extracted["row_refs"]["total_debt"] = recovered_row_refs
                    logger.info(
                        "Recovered total_debt from balance-sheet debt rows on page %s rows=%r",
                        getattr(table, "page_number", "?"),
                        recovered_row_refs,
                    )
        if table_type in {"net_debt_note", "balance_sheet"} and extracted.get("net_debt") is None:
            recovered = _recover_explicit_net_debt_from_table(
                table,
                period_end=pass1_result.get("period_end"),
            )
            if recovered is not None:
                raw_value, row_ref, period_col = recovered
                extracted["net_debt"] = abs(raw_value * multiplier)
                extracted["row_refs"]["net_debt"] = row_ref
                extracted["period_col"] = period_col
                logger.info(
                    "Recovered explicit net_debt deterministically from %s page %s row=%r period_col=%r",
                    table_type,
                    getattr(table, "page_number", "?"),
                    row_ref,
                    period_col,
                )
        if (
            table_type in {"net_debt_note", "balance_sheet"}
            and extracted.get("net_debt") is not None
            and not extracted["row_refs"].get("net_debt")
        ):
            extracted["row_refs"]["net_debt"] = "Net debt"
        if table_type == "cashflow_statement":
            for metric_name, (
                recovered_value,
                recovered_row_ref,
            ) in _recover_appendix5b_section_totals_from_table(
                table, scale_for_table
            ).items():
                if metric_name == "cash_end" and (
                    extracted.get("cash_end") is not None
                    and not _cashflow_cash_end_row_is_weak(
                        extracted["row_refs"].get("cash_end")
                    )
                ):
                    continue
                extracted[metric_name] = recovered_value
                extracted["row_refs"][metric_name] = recovered_row_ref
                logger.info(
                    "Recovered Appendix 5B %s section total from page %s",
                    metric_name,
                    getattr(table, "page_number", "?"),
                )
        if table_type == "cashflow_statement":
            recovered_capex = _recover_preferred_cashflow_capex_from_table(
                table, scale_for_table
            )
            current_row_ref = extracted["row_refs"].get("capex")
            if recovered_capex is not None:
                recovered_value, recovered_row_ref = recovered_capex
                current_capex = _coerce_cashflow_metric_float(extracted.get("capex"))
                should_replace_capex = (
                    current_capex is None
                    or _cashflow_capex_row_is_weak(current_row_ref)
                    or abs(current_capex - recovered_value) > 0.5
                )
                if should_replace_capex:
                    extracted["capex"] = recovered_value
                    extracted["row_refs"]["capex"] = recovered_row_ref
                    logger.info(
                        "Recovered cashflow capex from preferred PP&E row on page %s",
                        getattr(table, "page_number", "?"),
                    )
            elif _cashflow_capex_row_is_disallowed_financial_asset(current_row_ref):
                extracted["capex"] = None
                extracted["row_refs"].pop("capex", None)
                logger.info(
                    "Rejected cashflow capex from financial-asset row on page %s",
                    getattr(table, "page_number", "?"),
                )
        if table_type == "cashflow_statement" and (
            extracted.get("cash_end") is None
            or _cashflow_cash_end_row_is_weak(extracted["row_refs"].get("cash_end"))
        ):
            recovered_cash_end = _recover_preferred_cashflow_cash_end_from_table(
                table, scale_for_table
            )
            if recovered_cash_end is not None:
                recovered_value, recovered_row_ref = recovered_cash_end
                extracted["cash_end"] = recovered_value
                extracted["row_refs"]["cash_end"] = recovered_row_ref
                logger.info(
                    "Recovered cashflow cash_end from preferred cash-equivalents row on page %s",
                    getattr(table, "page_number", "?"),
                )
        if table_type == "cashflow_statement":
            cashflow_source_rows = (
                rows_override if rows_override is not None else getattr(table, "rows", None)
            )
            for metric_name in (
                "operating_cf",
                "investing_cf",
                "financing_cf",
                "cash_end",
            ):
                before_value = extracted.get(metric_name)
                _replace_cashflow_metric_if_over_scaled_from_row_ref(
                    extracted,
                    cashflow_source_rows,
                    metric_name,
                    scale_for_table,
                )
                if extracted.get(metric_name) != before_value:
                    logger.info(
                        "Corrected cashflow %s from row-ref source amount on page %s",
                        metric_name,
                        getattr(table, "page_number", "?"),
                    )
        if ocr_candidates:
            # Later native recovery gates rebuild row_refs. Restore the
            # deterministic OCR row binding before the existing period gate.
            for metric_name, candidate in ocr_metric_provenance.items():
                if extracted.get(metric_name) is not None:
                    extracted["row_refs"][metric_name] = str(
                        candidate["source_text"]
                    )
        if table_type in {"income_statement", "cashflow_statement"}:
            extracted = _bind_statement_metrics_to_current_period_cells(
                extracted,
                table,
                period_end=pass1_result.get("period_end"),
                scale=scale_for_table,
                period_basis=pass1_result.get("period_basis"),
            )
        if ocr_candidates:
            # Revalidate after every deterministic recovery/rebinding gate so
            # no final OCR-derived value can retain missing or stale mapping.
            final_ocr_provenance: dict[str, dict[str, Any]] = {}
            for metric_name in metrics:
                metric_value = extracted.get(metric_name)
                if metric_value is None:
                    continue
                effective_multiplier = (
                    1 if metric_name in _COUNT_METRICS else multiplier_for_table
                )
                expected_raw_value = float(metric_value) / effective_multiplier
                matching_candidates = []
                for candidate in ocr_candidates:
                    if not isinstance(candidate, dict):
                        continue
                    parsed_candidate = _parse_accounting_metric_number(
                        candidate.get("candidate_value_text")
                    )
                    if parsed_candidate is None:
                        continue
                    candidate_value, _candidate_has_unit = parsed_candidate
                    if abs(candidate_value - expected_raw_value) <= 1e-9:
                        matching_candidates.append(candidate)
                if len(matching_candidates) != 1:
                    extracted[metric_name] = None
                    extracted["row_refs"].pop(metric_name, None)
                    continue
                final_ocr_provenance[metric_name] = dict(matching_candidates[0])
            extracted["_ocr_metric_provenance"] = final_ocr_provenance
        return extracted

    prompt = _build_prompt(markdown)
    selected_markdown = markdown
    selected_rows = filtered_rows if filter_enabled else None

    try:
        raw = _llm_json_call(prompt, llm_client, max_tokens=2048, model_override=model_override)
    except Exception as e:
        logger.warning(
            "Pass 3a failed for %s: %s — retrying with truncated table", table_type, e
        )
        try:
            truncated_markdown = _table_to_markdown_truncated(table, max_rows=20)
            truncated_prompt = _build_prompt(truncated_markdown)
            raw = _llm_json_call(
                truncated_prompt, llm_client, max_tokens=1024, model_override=model_override
            )
            selected_markdown = truncated_markdown
            selected_rows = None
        except Exception as e2:
            logger.error("Pass 3a retry also failed for %s: %s", table_type, e2)
            _capture_pass3a_failure(
                failure_capture,
                table_type=table_type,
                initial_error=e,
                retry_error=e2,
            )
            return None

    selected_raw = raw
    out = _build_output(
        raw,
        table_markdown=selected_markdown,
        rows_override=selected_rows,
    )

    used_filtered_rows = bool(
        filter_enabled and filtered_rows is not None and filtered_rows != table.rows
    )
    if used_filtered_rows and _needs_full_table_retry(table_type, out):
        logger.info(
            "Pass3a %s: filtered extraction missed key metrics; retrying full table",
            table_type,
        )
        full_markdown = _table_to_markdown(table, max_rows=row_cap)
        if full_markdown and full_markdown != markdown:
            try:
                full_raw = _llm_json_call(
                    _build_prompt(full_markdown),
                    llm_client,
                    max_tokens=2048,
                    model_override=model_override,
                )
                full_out = _build_output(
                    full_raw,
                    table_markdown=full_markdown,
                    rows_override=None,
                )
                full_count = sum(1 for m in metrics if full_out.get(m) is not None)
                current_count = sum(1 for m in metrics if out.get(m) is not None)
                if full_count > current_count or not _needs_full_table_retry(
                    table_type,
                    full_out,
                ):
                    out = full_out
                    selected_raw = full_raw
                    logger.info(
                        "Pass3a %s: full-table retry improved extraction (%d → %d non-null)",
                        table_type,
                        current_count,
                        full_count,
                    )
            except Exception as retry_err:
                logger.warning(
                    "Pass3a %s: full-table retry failed: %s",
                    table_type,
                    retry_err,
                )

    # Compute confidence from observable results rather than relying on the
    # model's self-reported value (which is typically 0.0 regardless of quality).
    # Use fraction of expected metrics that were extracted as the signal.
    n_extracted = sum(1 for m in metrics if out.get(m) is not None)
    computed_conf = n_extracted / max(len(metrics), 1)
    try:
        model_conf = float(selected_raw.get("pass3_confidence", 0.0))
    except (TypeError, ValueError):
        model_conf = 0.0
    # Take max so a model that correctly reports high confidence is rewarded,
    # but a model that reports 0 doesn't drag down an otherwise complete extraction.
    out["pass3_confidence"] = max(computed_conf, model_conf)
    logger.info(
        "Pass3a %s: extracted %d metrics, confidence=%.2f",
        table_type,
        len([m for m in metrics if out.get(m) is not None]),
        out.get("pass3_confidence", 0),
    )
    return out


def _run_pass3a_metric_extractor(
    labelled_tables: dict[str, Any],
    pass1_result: dict,
    llm_client,
    *,
    prompt_bundle: PromptBundle | None = None,
    model_override: str | None = None,
    failure_capture: SimpleQueue[dict[str, Any]] | None = None,
) -> list[dict]:
    """
    Pass 3a: one LLM call per labelled table. Returns list of extraction dicts,
    each tagged with its source table type.

    By default, table extractions run in parallel (I/O-bound HTTP calls).
    Set EXTRACTION_PARALLEL=0 to disable parallelism and run sequentially.
    """
    bundle = prompt_bundle or resolve("default")
    scale = pass1_result.get("scale", "unknown")
    multiplier = SCALE_MULTIPLIERS.get(scale, 1)

    # Skip redundant table extractions when higher-priority sources are present.
    # Controlled by EXTRACTION_SKIP_REDUNDANT env var (default: enabled).
    skip_redundant = os.environ.get("EXTRACTION_SKIP_REDUNDANT", "1") != "0"
    skipped_tables: dict[str, str] = {}
    if skip_redundant:
        has_bs = labelled_tables.get("balance_sheet") is not None
        has_is = labelled_tables.get("income_statement") is not None
        has_cf = labelled_tables.get("cashflow_statement") is not None
        # share_capital is NOT skipped even when balance_sheet is present.
        # Balance sheets are dense and unreliable for share counts; the dedicated
        # share_capital table is the most reliable source for shares_outstanding.
        if has_is and has_cf and "highlights" in labelled_tables:
            skipped_tables["highlights"] = "income_statement + cashflow_statement"

    # Filter to extractable tables (preserving iteration order for deterministic output).
    eligible = []
    for tt, tbl in labelled_tables.items():
        if tt == "unmatched" or tbl is None:
            continue
        if tt in skipped_tables:
            logger.info("Skipping %s — covered by %s", tt, skipped_tables[tt])
            continue
        eligible.append((tt, tbl))

    parallel_enabled = os.environ.get("EXTRACTION_PARALLEL", "1") != "0"

    if parallel_enabled and len(eligible) > 1:
        logger.info("Pass 3a: extracting %d tables in parallel", len(eligible))
        # Use one thread per table; cap at 5 to avoid excessive concurrency.
        with ThreadPoolExecutor(max_workers=min(len(eligible), 5)) as pool:
            future_to_table_type = {
                pool.submit(
                    _extract_single_table,
                    table_type,
                    table,
                    pass1_result,
                    scale,
                    multiplier,
                    llm_client,
                    prompt_bundle=bundle,
                    model_override=model_override,
                    failure_capture=failure_capture,
                ): table_type
                for table_type, table in eligible
            }
            # Collect results keyed by table_type so we can restore original order.
            results_by_type: dict[str, dict] = {}
            for future in as_completed(future_to_table_type):
                tt = future_to_table_type[future]
                try:
                    result = future.result()
                    if result is not None:
                        results_by_type[tt] = result
                except Exception as exc:
                    logger.exception("Pass 3a thread failed for %s", tt)
                    _capture_pass3a_failure(
                        failure_capture,
                        table_type=tt,
                        initial_error=exc,
                    )
        # Preserve original table order from labelled_tables.
        results = [results_by_type[tt] for tt, _ in eligible if tt in results_by_type]
    else:
        if len(eligible) > 1:
            logger.info(
                "Pass 3a: extracting %d tables sequentially (EXTRACTION_PARALLEL=0)",
                len(eligible),
            )
        results = []
        for table_type, table in eligible:
            out = _extract_single_table(
                table_type,
                table,
                pass1_result,
                scale,
                multiplier,
                llm_client,
                prompt_bundle=bundle,
                model_override=model_override,
                failure_capture=failure_capture,
            )
            if out is not None:
                results.append(out)

    return results


def _market_update_period_quarter_label(period_end: Any) -> str | None:
    """Return the Australian FY quarter label implied by a quarter period end."""
    parsed = parse_period_end(str(period_end or ""))
    if parsed is None:
        return None
    quarter_by_month = {9: 1, 12: 2, 3: 3, 6: 4}
    quarter = quarter_by_month.get(parsed.month)
    if quarter is None:
        return None
    financial_year = parsed.year + 1 if parsed.month in {9, 12} else parsed.year
    return f"Q{quarter} FY{financial_year % 100:02d}"


def _market_update_context_text(title: Any, sections: list[dict] | None) -> str:
    section_text = " ".join(
        str(section.get("text") or "")
        for section in (sections or [])[:8]
        if isinstance(section, dict)
    )
    return f"{title or ''} {section_text}"


def _is_quarterly_market_update_context(
    *,
    title: Any,
    sections: list[dict] | None,
    pass1_result: dict,
) -> tuple[bool, str | None]:
    if pass1_result.get("report_type") != "Q":
        return False, None
    quarter_label = _market_update_period_quarter_label(pass1_result.get("period_end"))
    if not quarter_label:
        return False, None
    context = _market_update_context_text(title, sections)
    normalized = _normalize_filter_text(context)
    if not _MARKET_UPDATE_HINT_RE.search(context):
        return False, None
    if _normalize_filter_text(quarter_label) not in normalized:
        return False, None
    return True, quarter_label


def _market_update_net_revenue_column(row: Any) -> int | None:
    if not isinstance(row, (list, tuple)):
        return None
    for index, cell in enumerate(row):
        compact = _normalize_filter_text(cell)
        if compact in _MARKET_UPDATE_NET_REVENUE_LABELS:
            return index
    return None


def _source_scale_from_value_text(
    raw_value: Any,
    *,
    fallback_scale: Any,
    has_explicit_unit: bool,
) -> tuple[str, str] | None:
    if has_explicit_unit:
        compact = _normalize_filter_text(raw_value)
        if compact.endswith("k") or "thousand" in compact:
            return "thousands", "explicit_value_suffix"
        if compact.endswith(("m", "mn")) or "million" in compact:
            return "millions", "explicit_value_suffix"
        if compact.endswith(("b", "bn")) or "billion" in compact:
            return "billions", "explicit_value_suffix"
        if compact.endswith(("t", "tn")) or "trillion" in compact:
            return "trillions", "explicit_value_suffix"
    scale = str(fallback_scale or "unknown").strip()
    if scale and scale != "unknown" and scale in SCALE_MULTIPLIERS:
        return scale, "document"
    return None


def _extract_market_update_net_revenue_candidate(
    tables: Any,
    *,
    sections: list[dict] | None,
    pass1_result: dict,
    title: Any,
) -> dict[str, Any] | None:
    """
    Recover source-bound Net Revenue from quarterly market-update tables only.

    Market updates can disclose a current-quarter revenue table before a later
    Appendix 4C or business review. This emits one revenue candidate when the
    row label matches the current quarter and the column is explicitly Net
    Revenue. It intentionally emits no cash-flow, profit, balance-sheet, or
    annual metrics.
    """
    is_market_update, quarter_label = _is_quarterly_market_update_context(
        title=title,
        sections=sections,
        pass1_result=pass1_result,
    )
    if not is_market_update or quarter_label is None:
        return None
    target_row_label = _normalize_filter_text(quarter_label)

    for table in tables or []:
        rows = getattr(table, "rows", None)
        if not isinstance(rows, list) or not rows:
            continue
        for header_index, header_row in enumerate(rows[:4]):
            net_revenue_col = _market_update_net_revenue_column(header_row)
            if net_revenue_col is None:
                continue
            header_label = str(header_row[net_revenue_col] or "").strip()
            for row in rows[header_index + 1 :]:
                if not isinstance(row, (list, tuple)) or not row:
                    continue
                row_label = str(row[0] or "").strip()
                if _normalize_filter_text(row_label) != target_row_label:
                    continue
                if net_revenue_col >= len(row):
                    continue
                raw_value = row[net_revenue_col]
                parsed = _parse_accounting_metric_number(raw_value)
                if parsed is None:
                    continue
                raw_number, has_explicit_unit = parsed
                source_scale = _source_scale_from_value_text(
                    raw_value,
                    fallback_scale=pass1_result.get("scale", "unknown"),
                    has_explicit_unit=has_explicit_unit,
                )
                if source_scale is None:
                    continue
                scale, scale_source = source_scale
                multiplier = 1 if has_explicit_unit else SCALE_MULTIPLIERS[scale]
                revenue_value = raw_number * multiplier
                row_ref = f"{row_label} {header_label}".strip()
                logger.info(
                    "Recovered market-update Net Revenue from page %s row=%r value=%r scale=%s",
                    getattr(table, "page_number", "?"),
                    row_label,
                    raw_value,
                    scale,
                )
                return {
                    "_source": "market_update_table",
                    "_page_number": getattr(table, "page_number", None),
                    "_scale": scale,
                    "_scale_source": scale_source,
                    "_thinking": (
                        "Deterministic source-bound market update recovery: "
                        f"{row_ref} = {raw_value}"
                    ),
                    "_markdown": _table_to_markdown(table, max_rows=30),
                    "revenue": revenue_value,
                    "row_refs": {"revenue": row_ref},
                    "period_col": quarter_label,
                    "pass3_confidence": 0.9,
                }
    return None


def _table_to_markdown_truncated(table, max_rows: int = 20) -> str:
    """Truncated version for retry."""
    if not table or not table.rows:
        return ""
    rows = table.rows[:max_rows]
    lines = []
    for i, row in enumerate(rows):
        line = " | ".join(str(c) for c in row)
        lines.append(line)
        if i == 0:
            lines.append(" | ".join("---" for _ in row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pass 3b — Narrative Extractor (LLM)
# ---------------------------------------------------------------------------

_PASS3B_PROMPT = """You are a financial narrative extractor. Output ONLY valid JSON.

From the document text below, extract:
- risk_summary: 1-2 sentence summary of key risks (null if none mentioned)
- risk_bullets: list of specific risk items (null if none)
- guidance_summary: management outlook/guidance summary (null if not present)
- material_changes: any material changes to business or financial position (null if none)
- confidence_narrative: float 0-1 (confidence in extraction quality)

Schema:
{{
  "risk_summary": "string|null",
  "risk_bullets": ["string"]|null,
  "guidance_summary": "string|null",
  "material_changes": "string|null",
  "confidence_narrative": 0.0
}}

Document text (first 4000 chars of prose):
{prose_text}
"""

# Register the canonical "default" prompt bundle with the registry. The live
# extraction path resolves this bundle; the matrix runner can register
# additional variants under different ids for comparative evaluation.
register_bundle(
    PromptBundle(
        id="default",
        pass1=_PASS1_PROMPT,
        pass3a=_PASS3A_PROMPT,
        pass3b=_PASS3B_PROMPT,
        description="Canonical multipass prompts (pass1 classifier, pass3a metrics, pass3b narrative).",
    )
)

# Stable fingerprint of all extraction prompt templates.
# Changes when any prompt is edited — use this in ExtractionRun.prompt_hash
# so stale cached extractions can be detected if prompts are updated.
#
# Derived via the registry so prompt bundle variants can share the same
# hashing formula and remain linkable to historical extraction_runs rows.
PROMPT_HASH: str = resolve("default").compute_hash()


def _run_pass3b_narrative_extractor(
    sections: list[dict],
    llm_client,
    *,
    prompt_bundle: PromptBundle | None = None,
    model_override: str | None = None,
) -> dict:
    """
    Pass 3b: extract risk/guidance narrative from prose sections.
    Returns dict with narrative fields. All fields null on failure.
    """
    null_result = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }

    prose = " ".join(s["text"] for s in sections if s.get("text", "").strip())[:4000]
    if not prose:
        return null_result

    bundle = prompt_bundle or resolve("default")
    prompt = bundle.pass3b.format(prose_text=prose)
    try:
        raw = _llm_json_call(prompt, llm_client, max_tokens=512, model_override=model_override)
        return {
            "risk_summary": raw.get("risk_summary"),
            "risk_bullets": raw.get("risk_bullets"),
            "guidance_summary": raw.get("guidance_summary"),
            "material_changes": raw.get("material_changes"),
            "confidence_narrative": float(raw.get("confidence_narrative", 0.5)),
        }
    except Exception as e:
        logger.warning("Pass 3b narrative extraction failed: %s", e)
        return null_result


# ---------------------------------------------------------------------------
# Prose fallback — extract shares_outstanding from note sections
# ---------------------------------------------------------------------------

# Patterns that capture share counts in ASX filing prose.
# Examples:
#   "comprises 3,003,366,782 fully paid shares"
#   "1,924,937,480 ordinary shares on issue"
#   "Number of shares on issue: 280,874,770"
_SHARES_PROSE_PATTERNS = [
    # "comprises X,XXX shares" / "comprised of X shares"
    re.compile(
        r"compris\w*\s+([\d,]+(?:\.\d+)?)\s+(?:fully\s+paid\s+)?(?:ordinary\s+)?shares",
        re.IGNORECASE,
    ),
    # "X shares on issue" / "X ordinary shares on issue"
    re.compile(
        r"([\d,]+(?:\.\d+)?)\s+(?:fully\s+paid\s+)?(?:ordinary\s+)?shares\s+on\s+issue",
        re.IGNORECASE,
    ),
    # "shares on issue: X" / "number of shares on issue: X"
    re.compile(
        r"(?:number\s+of\s+)?shares\s+on\s+issue[:\s]+([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # "total issued shares X" / "total ordinary shares X"
    re.compile(
        r"total\s+(?:issued|ordinary)\s+(?:share\s+)?(?:capital\s+)?(?:of\s+)?([\d,]+(?:\.\d+)?)\s+shares",
        re.IGNORECASE,
    ),
]

_DUAL_LISTED_SHARES_ON_ISSUE_RE = re.compile(
    r"\bhad\s+([\d,]+(?:\.\d+)?)\s+"
    r"(million|millions|m|billion|billions|bn|b)\s+ordinary\s+shares\s+on\s+issue\b"
    r".*?"
    r"\bhad\s+([\d,]+(?:\.\d+)?)\s+"
    r"(million|millions|m|billion|billions|bn|b)\s+ordinary\s+shares\s+on\s+issue\b",
    re.IGNORECASE | re.DOTALL,
)

# Sections likely to contain share capital notes (filter for efficiency)
_SHARE_NOTE_RE = re.compile(
    r"note\s+\d+|share\s+capital|shares\s+on\s+issue|issued\s+capital",
    re.IGNORECASE,
)

_ADVISORY_ONLY_DOCUMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bquarterly\s+(?:activities\s+)?report\s+advisory\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bappendix\s+4[cd]\s+advisory\b", re.IGNORECASE),
)

_SOURCE_PERIOD_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "A",
        "annual_report_title",
        re.compile(r"\bannual\s+report\b", re.IGNORECASE),
    ),
    (
        "A",
        "year_ended_source_phrase",
        re.compile(r"(?<!half[-\s])\byear\s+ended\b", re.IGNORECASE),
    ),
    (
        "H",
        "half_year_source_phrase",
        re.compile(r"\bhalf[-\s]?year\b", re.IGNORECASE),
    ),
    (
        "H",
        "six_months_ended_source_phrase",
        re.compile(r"\b(?:six|6)\s+months?\s+ended\b", re.IGNORECASE),
    ),
    (
        "H",
        "appendix_4d_source_phrase",
        re.compile(r"\bappendix\s+4d\b", re.IGNORECASE),
    ),
    (
        "Q",
        "appendix_4c_source_phrase",
        re.compile(r"\bappendix[-\s]+4c\b", re.IGNORECASE),
    ),
    (
        "Q",
        "quarterly_source_phrase",
        re.compile(
            r"\bquarterly[-\s]+(?:cash[-\s]+flow|activities|activity|report)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Q",
        "appendix_5b_source_phrase",
        re.compile(r"\bappendix[-\s]+5b\b", re.IGNORECASE),
    ),
    (
        "Q",
        "quarterly_activity_report_source_phrase",
        re.compile(
            r"\bquarterly[-\s]+activit(?:y|ies)[-\s]+report\b",
            re.IGNORECASE,
        ),
    ),
)
_STRONG_QUARTERLY_SOURCE_REASONS = frozenset(
    {
        "appendix_4c_source_phrase",
        "appendix_5b_source_phrase",
        "quarterly_activity_report_source_phrase",
    }
)

_SOURCE_DATE_TEXT_FRAGMENT = (
    r"\d{1,2}(?:st|nd|rd|th)?\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+"
    r"\d{4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
)
_SOURCE_DATE_TEXT_PATTERN = rf"(?P<date>{_SOURCE_DATE_TEXT_FRAGMENT})"

_SOURCE_PERIOD_END_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "A",
        "year_ended_explicit_date",
        re.compile(
            rf"\b(?:for\s+the\s+)?(?:financial\s+)?(?<!half[-\s])year\s+ended\s+"
            rf"{_SOURCE_DATE_TEXT_PATTERN}",
            re.IGNORECASE,
        ),
    ),
    (
        "H",
        "half_year_ended_explicit_date",
        re.compile(
            rf"\b(?:for\s+the\s+)?(?:(?:half[-\s]?year)|(?:(?:six|6)\s+months?))"
            rf"\s+ended\s+{_SOURCE_DATE_TEXT_PATTERN}",
            re.IGNORECASE,
        ),
    ),
    (
        "Q",
        "quarter_ended_explicit_date",
        re.compile(
            rf"\b(?:for\s+the\s+)?(?:(?:quarter)|(?:(?:three|3)\s+months?))"
            rf"\s+ended\s+{_SOURCE_DATE_TEXT_PATTERN}",
            re.IGNORECASE,
        ),
    ),
)
_CURRENT_PERIOD_RANGE_PATTERN = re.compile(
    rf"\bcurrent\s+period\s*[:\-]\s*"
    rf"(?P<start_date>{_SOURCE_DATE_TEXT_FRAGMENT})"
    rf"\s*(?:to|through|-)\s*"
    rf"(?P<end_date>{_SOURCE_DATE_TEXT_FRAGMENT})",
    re.IGNORECASE,
)
_COMPARATIVE_PERIOD_CONTEXT_RE = re.compile(
    r"\b(?:comparative|comparatives|prior|previous|corresponding|pcp)\b",
    re.IGNORECASE,
)
_SAME_DOCUMENT_HALF_YEAR_PERIOD_END_REASONS = frozenset(
    {"half_year_ended_explicit_date", "current_period_explicit_range"}
)
_SAME_DOCUMENT_PERIOD_END_REASONS_BY_TYPE = {
    "A": frozenset({"year_ended_explicit_date"}),
    "H": _SAME_DOCUMENT_HALF_YEAR_PERIOD_END_REASONS,
}

_LEADING_ANNOUNCEMENT_DATE_RE = re.compile(
    r"^\s*(?P<date>\d{4}-\d{1,2}-\d{1,2})(?:[_\s-]|$)"
)
_ANNUAL_TITLE_HINT_RE = re.compile(
    r"\b(?:annual\s+report|appendix\s*4e)\b",
    re.IGNORECASE,
)
_HALF_YEAR_TITLE_HINT_RE = re.compile(
    r"\b(?:1h\s*fy\d{2,4}|half\s*year|interim|appendix\s*4d)\b",
    re.IGNORECASE,
)

_EXPLICIT_SOURCE_UNIT_VALUE_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:AUD|USD|IDR)?\s*"
    r"(?:A\$|\$A|US\$|\$US|RP\.?|\$)?\s*"
    r"\(?(-?\d+(?:,\d{3})*(?:\.\d+)?)\)?\s*"
    r"(million|millions|m|billion|billions|bn|b|trillion|trillions)\b",
    re.IGNORECASE,
)

_SOURCE_UNIT_MULTIPLIERS = {
    "m": 1_000_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
    "billions": 1_000_000_000,
    "trillion": 1_000_000_000_000,
    "trillions": 1_000_000_000_000,
}

_EBIT_LABEL_BLOCKERS = (
    ("ebitda", "ebitda"),
    ("earnings before interest tax depreciation", "ebitda"),
    ("earnings before interest, tax, depreciation", "ebitda"),
    ("earnings before interest and tax depreciation", "ebitda"),
    ("earnings before interest, taxes, depreciation", "ebitda"),
    ("net operating income", "net_operating_income"),
    ("profitbeforecreditimpairmentandincometax", "credit_impairment_pre_tax"),
)


def _extract_shares_from_prose(sections: list[dict]) -> tuple[float | None, str]:
    """Scan prose sections for share count mentions.

    Returns (shares_outstanding, provenance_string).
    Returns (None, "") if no match found.
    """
    # Filter to sections likely to mention share capital
    indexed_sections = [
        (index, s) for index, s in enumerate(sections) if s.get("text")
    ]
    candidates = [
        (index, s)
        for index, s in indexed_sections
        if _SHARE_NOTE_RE.search(s["text"])
    ]
    # Also scan all sections if no note-specific candidates found
    if not candidates:
        candidates = indexed_sections

    candidate_texts: list[tuple[Any, str]] = []
    for source_index, section in candidates:
        text = section["text"]
        page = section.get("page", "?")
        candidate_texts.append((page, text))
        window_parts = [text]
        for _follower_index, follower in indexed_sections[
            source_index + 1 : source_index + 3
        ]:
            if follower.get("page") != page:
                break
            window_parts.append(follower.get("text") or "")
        if len(window_parts) > 1:
            candidate_texts.append((page, " ".join(window_parts)))

    for page, text in candidate_texts:
        dual_match = _DUAL_LISTED_SHARES_ON_ISSUE_RE.search(text)
        if dual_match:
            values: list[float] = []
            for raw, unit in (
                (dual_match.group(1), dual_match.group(2)),
                (dual_match.group(3), dual_match.group(4)),
            ):
                try:
                    values.append(
                        float(raw.replace(",", "")) * _SOURCE_UNIT_MULTIPLIERS[unit.lower()]
                    )
                except (KeyError, ValueError):
                    values = []
                    break
            if values:
                value = sum(values)
                if 1_000_000 <= value <= 100_000_000_000:
                    provenance = f"prose_note:page_{page}:{dual_match.group(0)[:100]}"
                    logger.info(
                        "shares_outstanding from dual-listed prose: %.0f (page %s)",
                        value,
                        page,
                    )
                    return value, provenance

        for pattern in _SHARES_PROSE_PATTERNS:
            match = pattern.search(text)
            if match:
                raw = match.group(1).replace(",", "")
                try:
                    value = float(raw)
                except ValueError:
                    continue
                # Sanity: share counts should be > 1M and < 100B
                if value < 1_000_000 or value > 100_000_000_000:
                    logger.debug(
                        "Prose shares_outstanding %.0f outside sane range, skipping",
                        value,
                    )
                    continue
                provenance = f"prose_note:page_{page}:{match.group(0)[:60]}"
                logger.info(
                    "shares_outstanding from prose: %.0f (page %s)",
                    value,
                    page,
                )
                return value, provenance

    return None, ""


def _combined_source_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, str):
            if value.strip():
                parts.append(value.strip())
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        elif value is not None:
            text = str(value).strip()
            if text:
                parts.append(text)
    return " ".join(parts)


def _source_text_has(compact_text: str, phrase: str) -> bool:
    return _normalize_filter_text(phrase) in compact_text


def _detect_source_noncandidate_class(
    title: Any,
    first_page_text: Any,
) -> tuple[str, list[str]] | None:
    title_text = _combined_source_text(title)
    combined_text = _combined_source_text(title, first_page_text)
    compact_title = _normalize_filter_text(title_text)
    compact_text = _normalize_filter_text(combined_text)
    if not compact_text:
        return None

    if (
        _source_text_has(compact_title, "notice of annual general meeting proxy form")
        or _source_text_has(compact_title, "notice of meeting proxy form")
        or _source_text_has(compact_title, "notice of annual general meeting")
        or _source_text_has(compact_title, "notice of meeting and explanatory")
        or _source_text_has(compact_title, "results of meeting")
        or (
            _source_text_has(compact_text, "upcoming general meeting of shareholders")
            and _source_text_has(compact_text, "notice of meeting")
        )
        or (
            _source_text_has(compact_text, "notice of annual general meeting")
            and _source_text_has(compact_text, "proxy form")
        )
    ):
        return (
            "meeting_or_proxy_notice",
            ["meeting_or_proxy_notice_pattern"],
        )

    if _source_text_has(compact_title, "webcast details"):
        return (
            "webcast_details_notice",
            ["webcast_details_notice_pattern"],
        )

    if (
        _source_text_has(compact_title, "board changes")
        or (
            _source_text_has(compact_text, "board changes")
            and (
                _source_text_has(compact_text, "non executive director")
                or _source_text_has(compact_text, "securityholder approval")
            )
        )
    ):
        return (
            "board_change_notice",
            ["board_change_notice_pattern"],
        )

    if (
        _source_text_has(compact_title, "update in relation to")
        and _source_text_has(compact_title, "project")
    ) or (
        _source_text_has(compact_text, "update in relation to")
        and _source_text_has(compact_text, "project")
        and (
            _source_text_has(compact_text, "open pit mining")
            or _source_text_has(compact_text, "mining operations")
            or _source_text_has(compact_text, "project update")
        )
    ):
        return (
            "operational_project_update",
            ["operational_project_update_pattern"],
        )

    if (
        _source_text_has(compact_title, "shares sold")
        and _source_text_has(compact_title, "gross proceeds")
    ) or (
        _source_text_has(compact_text, "shares sold")
        and _source_text_has(compact_text, "gross proceeds")
    ):
        return (
            "share_sale_or_gross_proceeds_announcement",
            ["share_sale_gross_proceeds_pattern"],
        )

    if (
        _source_text_has(compact_title, "re presentation of segment results")
        or _source_text_has(compact_text, "re presentation of segment results")
    ) and (
        _source_text_has(compact_text, "plans to announce")
        or _source_text_has(compact_text, "no changes to statutory financial results")
        or _source_text_has(compact_text, "terminology changes")
    ):
        return (
            "pre_results_segment_re_presentation",
            ["pre_results_segment_re_presentation_pattern"],
        )

    if (
        _source_text_has(compact_title, "change of director s interest notice")
        or _source_text_has(compact_title, "change of directors interest notice")
        or (
            _source_text_has(compact_text, "appendix 3y change of director s interest notice")
            and _source_text_has(compact_text, "change of director s relevant interests")
        )
        or (
            _source_text_has(compact_text, "change of director s interest notice")
            and _source_text_has(compact_text, "notifiable interest of a director")
        )
    ):
        return (
            "director_interest_notice",
            ["director_interest_notice_pattern"],
        )

    return None


def is_advisory_only_document(title: Any, first_page_text: Any) -> bool:
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    return any(pattern.search(text) for pattern in _ADVISORY_ONLY_DOCUMENT_PATTERNS)


def _is_advisory_only_document(title: Any, first_page_text: Any) -> bool:
    return is_advisory_only_document(title, first_page_text)


def _detect_source_period_evidence(title: Any, first_page_text: Any) -> dict[str, Any]:
    """
    Detect explicit source-period wording without changing the extracted period.

    This is a contradiction guard only: ambiguous/multiple source-period signals are
    left reportable but non-blocking so the gate does not infer a corrected period.
    """
    hits: list[dict[str, str]] = []
    for source, text in (
        ("title", _combined_source_text(title)),
        ("source_text", _combined_source_text(first_page_text)),
    ):
        if not text:
            continue
        for period_type, reason, pattern in _SOURCE_PERIOD_PATTERNS:
            if pattern.search(text):
                hits.append(
                    {"period_type": period_type, "reason": reason, "source": source}
                )

    seen_types = sorted({hit["period_type"] for hit in hits})
    if len(seen_types) == 1:
        return {
            "period_type": seen_types[0],
            "reason": hits[0]["reason"],
            "hits": hits,
        }
    if len(seen_types) > 1:
        annual_hits = [hit for hit in hits if hit["period_type"] == "A"]
        quarterly_hits = [hit for hit in hits if hit["period_type"] == "Q"]
        if (
            annual_hits
            and quarterly_hits
            and all(hit["reason"] == "annual_report_title" for hit in annual_hits)
            and all(hit.get("source") != "title" for hit in annual_hits)
            and any(
                hit["reason"] in _STRONG_QUARTERLY_SOURCE_REASONS
                for hit in quarterly_hits
            )
        ):
            return {
                "period_type": "Q",
                "reason": "quarterly_source_precedence_over_annual_report_reference",
                "hits": hits,
            }
        return {"period_type": None, "reason": "ambiguous", "hits": hits}
    return {"period_type": None, "reason": "not_detected", "hits": []}


def _normalize_source_date_text(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)


def _source_period_match_context(text: str, start: int, end: int) -> str:
    context = text[max(0, start - 80) : min(len(text), end + 80)]
    return " ".join(context.split())[:240]


def _is_comparative_period_context(text: str, match_start: int) -> bool:
    line_start = text.rfind("\n", 0, match_start) + 1
    leading_context = text[line_start:match_start]
    return bool(_COMPARATIVE_PERIOD_CONTEXT_RE.search(leading_context or ""))


def _current_period_range_period_end_hits(source: str, text: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if source != "source_text":
        return hits
    for match in _CURRENT_PERIOD_RANGE_PATTERN.finditer(text):
        start_date = parse_period_end(
            _normalize_source_date_text(match.group("start_date"))
        )
        end_date = parse_period_end(_normalize_source_date_text(match.group("end_date")))
        if start_date is None or end_date is None:
            continue
        if _derive_period_start(end_date, "H") != start_date:
            continue
        context = _source_period_match_context(text, match.start(), match.end())
        hits.append(
            {
                "period_type": "H",
                "period_end": end_date.isoformat(),
                "period_start": start_date.isoformat(),
                "reason": "current_period_explicit_range",
                "source": source,
                "evidence": " ".join(match.group(0).split())[:200],
                "context": context,
                "is_comparative_context": "false",
            }
        )
    return hits


def _current_period_source_preference(
    hits: list[dict[str, str]]
) -> dict[str, Any] | None:
    current_hits = [
        hit
        for hit in hits
        if hit.get("source") == "source_text"
        and hit.get("reason") == "current_period_explicit_range"
    ]
    if not current_hits:
        return None
    current_dates = sorted({hit["period_end"] for hit in current_hits})
    current_types = sorted({hit["period_type"] for hit in current_hits})
    if len(current_dates) != 1 or current_types != ["H"]:
        return None

    period_end = current_dates[0]
    conflicting_hits = [hit for hit in hits if hit.get("period_end") != period_end]
    if not conflicting_hits:
        return None
    if any(hit.get("is_comparative_context") != "true" for hit in conflicting_hits):
        return None

    reason = "current_period_explicit_range"
    for hit in hits:
        if (
            hit.get("source") == "source_text"
            and hit.get("period_end") == period_end
            and hit.get("reason") == "half_year_ended_explicit_date"
            and hit.get("is_comparative_context") != "true"
        ):
            reason = "half_year_ended_explicit_date"
            break

    return {
        "period_type": "H",
        "period_end": period_end,
        "reason": reason,
        "hits": hits,
        "selection_rule": "current_period_source_text_over_comparative_period_end",
    }


def _detect_source_period_end_evidence(title: Any, source_text: Any) -> dict[str, Any]:
    """
    Detect explicit source period-end dates from typed reporting-period phrases.

    This helper is deliberately narrow: it accepts phrases such as
    "for the year ended 31 December 2025" and refuses ambiguous/multiple dates
    instead of inferring from publication dates, filenames, or loose references.
    """

    hits: list[dict[str, str]] = []
    for source, text in (
        ("title", _combined_source_text(title)),
        ("source_text", _combined_source_text(source_text)),
    ):
        if not text:
            continue
        for period_type, reason, pattern in _SOURCE_PERIOD_END_PATTERNS:
            for match in pattern.finditer(text):
                raw_date = _normalize_source_date_text(match.group("date"))
                parsed = parse_period_end(raw_date)
                if parsed is None:
                    continue
                context = _source_period_match_context(text, match.start(), match.end())
                hits.append(
                    {
                        "period_type": period_type,
                        "period_end": parsed.isoformat(),
                        "reason": reason,
                        "source": source,
                        "evidence": " ".join(match.group(0).split())[:200],
                        "context": context,
                        "is_comparative_context": (
                            "true"
                            if _is_comparative_period_context(text, match.start())
                            else "false"
                        ),
                    }
                )
        hits.extend(_current_period_range_period_end_hits(source, text))

    unique_dates = sorted({hit["period_end"] for hit in hits})
    unique_types = sorted({hit["period_type"] for hit in hits})
    current_period_preference = _current_period_source_preference(hits)
    if current_period_preference is not None:
        return current_period_preference
    if len(unique_dates) == 1 and len(unique_types) == 1:
        return {
            "period_type": unique_types[0],
            "period_end": unique_dates[0],
            "reason": hits[0]["reason"],
            "hits": hits,
        }
    if hits:
        return {
            "period_type": None,
            "period_end": None,
            "reason": "ambiguous",
            "hits": hits,
        }
    return {"period_type": None, "period_end": None, "reason": "not_detected", "hits": []}


def _has_source_text_period_end_hit(
    evidence: dict[str, Any], reason: str | None = None
) -> bool:
    hits = evidence.get("hits")
    if not isinstance(hits, list):
        return False
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        if hit.get("source") != "source_text":
            continue
        if reason is not None and hit.get("reason") != reason:
            continue
        if parse_period_end(str(hit.get("period_end") or "")) is None:
            continue
        return True
    return False


def _early_period_source_text(
    sections: list[dict],
    *,
    max_page: int = 4,
    max_sections_when_pages_unknown: int = 12,
    max_chars: int = 6000,
) -> str:
    """Return early source text suitable for document-level period evidence."""

    def _coerce_page(section: dict) -> int | None:
        try:
            return int(section.get("page"))
        except (TypeError, ValueError):
            return None

    page_numbers = [_coerce_page(section) for section in sections]
    has_real_page_numbers = any(page is not None and page > 0 for page in page_numbers)
    if has_real_page_numbers:
        selected = [
            str(section.get("text") or "").strip()
            for section, page in zip(sections, page_numbers)
            if page is not None and 0 < page <= max_page
        ]
    else:
        selected = [
            str(section.get("text") or "").strip()
            for section in sections[:max_sections_when_pages_unknown]
        ]
    return " ".join(part for part in selected if part)[:max_chars]


def classify_source_document(
    title: Any,
    first_page_text: Any,
) -> SourceDocumentClassification:
    """Classify source-document eligibility without inferring financial truth."""

    text = _combined_source_text(title, first_page_text)
    if is_advisory_only_document(title, first_page_text):
        return SourceDocumentClassification(
            document_class="advisory_only_document",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="advisory_only_document",
            evidence=["advisory_only_pattern"],
        )

    noncandidate = _detect_source_noncandidate_class(title, first_page_text)
    if noncandidate is not None:
        document_class, evidence = noncandidate
        return SourceDocumentClassification(
            document_class=document_class,
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason=f"source_noncandidate:{document_class}",
            evidence=evidence,
        )

    period_evidence = _detect_source_period_evidence(title, first_page_text)
    if period_evidence.get("period_type") in {"A", "H", "Q"}:
        return SourceDocumentClassification(
            document_class="financial_report",
            extraction_candidate_allowed=True,
            canary_candidate_allowed=True,
            reason=str(period_evidence.get("reason") or "source_period_evidence"),
            evidence=[
                str(hit.get("reason") or hit.get("period_type") or "")
                for hit in period_evidence.get("hits", [])
                if isinstance(hit, dict)
            ],
        )

    return SourceDocumentClassification(
        document_class="unknown_document",
        extraction_candidate_allowed=True,
        canary_candidate_allowed=True,
        reason="missing_explicit_source_document_classification"
        if not text
        else str(period_evidence.get("reason") or "unknown_document"),
        evidence=[],
    )


# ---------------------------------------------------------------------------
# Pass 4 — Reconciler (deterministic)
# ---------------------------------------------------------------------------

_STRONG_TOTAL_DEBT_ROW_REFS = (
    "total debt",
    "borrowings",
    "interest bearing liabilities",
    "interest-bearing liabilities",
    "interest bearing borrowings",
    "interest-bearing borrowings",
    "interest bearing debt",
    "interest-bearing debt",
    "financial debt",
    "bank debt",
    "bank loans",
    "loan",
    "loans",
    "notes payable",
    "senior notes",
    "bond",
    "bonds",
    "debt facility",
    "debt facilities",
)

_WEAK_TOTAL_DEBT_ROW_REFS = (
    "total liabilities",
    "total liab",
    "current liabilities",
    "non-current liabilities",
    "lease liability",
    "lease liabilities",
    "lease liab",
)


def _normalise_evidence_row_ref(row_ref: str | None) -> str:
    return " ".join(str(row_ref or "").strip().lower().split())


def _select_preferred_evidence_row_ref(
    row_ref: Any,
    *,
    strong_markers: tuple[str, ...],
    weak_markers: tuple[str, ...] = (),
) -> str | None:
    if isinstance(row_ref, (list, tuple, set)):
        candidates = [str(item or "").strip() for item in row_ref]
    else:
        candidates = [str(row_ref or "").strip()]

    best_candidate: str | None = None
    best_rank = len(strong_markers)
    for candidate in candidates:
        normalized = _normalise_evidence_row_ref(candidate)
        if not normalized:
            continue
        for rank, marker in enumerate(strong_markers):
            if marker in normalized and rank < best_rank:
                best_candidate = candidate
                best_rank = rank
                break
        if best_candidate is None and any(weak in normalized for weak in weak_markers):
            continue
    return best_candidate


def _infer_total_debt_row_ref(table) -> str | None:
    """Recover strong debt evidence when the model omits total_debt row refs."""
    for row in getattr(table, "rows", []) or []:
        if not row or not any(_re.search(r"\d", str(cell or "")) for cell in row[1:]):
            continue
        label = str(row[0] or "").strip()
        preferred = _select_preferred_evidence_row_ref(
            label,
            strong_markers=_STRONG_TOTAL_DEBT_ROW_REFS,
            weak_markers=_WEAK_TOTAL_DEBT_ROW_REFS,
        )
        if preferred:
            return preferred
    return None


def _recover_total_debt_from_balance_sheet_table(
    table: Any,
    scale: str,
) -> tuple[float, str | list[str]] | None:
    """Recover total financial debt from current-period balance-sheet debt rows."""
    rows = getattr(table, "rows", []) or []
    grouped_recovery = _total_debt_recovery_from_line_items(
        _iter_grouped_balance_sheet_debt_line_items(rows, scale)
    )
    if grouped_recovery is not None:
        return grouped_recovery

    line_items: list[tuple[str, float]] = []
    for row in rows:
        line_items.extend(_iter_balance_sheet_debt_line_items(row, scale))
    return _total_debt_recovery_from_line_items(line_items)


def _total_debt_recovery_from_line_items(
    line_items: list[tuple[str, float]],
) -> tuple[float, str | list[str]] | None:
    debt_components: list[tuple[str, float]] = []
    explicit_total_debt: tuple[float, str] | None = None
    for label, value in line_items:
        normalized = _normalise_evidence_row_ref(label)
        if normalized == "total debt":
            explicit_total_debt = (value, label)
            continue
        debt_components.append((label, value))

    if len(debt_components) >= 2:
        return sum(value for _label, value in debt_components), [
            label for label, _value in debt_components
        ]
    if debt_components:
        label, value = debt_components[0]
        return value, label
    if explicit_total_debt is not None:
        value, label = explicit_total_debt
        return value, label
    return None


def _iter_grouped_balance_sheet_debt_line_items(
    rows: list[list[Any]],
    scale: str,
) -> list[tuple[str, float]]:
    line_items: list[tuple[str, float]] = []
    for row_index, row in enumerate(rows):
        if not row or not str(row[0] or "").strip():
            continue

        label_lines = _split_table_cell_lines(row[0])
        if len(label_lines) < 2:
            continue
        if _is_balance_sheet_group_heading(label_lines[0]):
            label_lines = label_lines[1:]

        values: list[float | None] = []
        cursor = row_index + 1
        while cursor < len(rows) and len(values) < len(label_lines):
            value_row = rows[cursor]
            if value_row and str(value_row[0] or "").strip():
                break
            if value_row and any(str(cell or "").strip() for cell in value_row[1:]):
                values.append(_parse_current_period_metric_cell(value_row, scale))
            cursor += 1

        if len(values) < 2:
            continue
        for label, value in zip(label_lines, values):
            if value is None or value < 0:
                continue
            preferred = _select_preferred_evidence_row_ref(
                label,
                strong_markers=_STRONG_TOTAL_DEBT_ROW_REFS,
                weak_markers=_WEAK_TOTAL_DEBT_ROW_REFS,
            )
            if preferred:
                line_items.append((label, value))
    return line_items


def _iter_balance_sheet_debt_line_items(
    row: list[Any],
    scale: str,
) -> list[tuple[str, float]]:
    if not row or not any(_re.search(r"\d", str(cell or "")) for cell in row[1:]):
        return []

    label_lines = _split_table_cell_lines(row[0])
    value_cell_index = _current_period_value_cell_index(row)
    if value_cell_index is None:
        return []

    value_lines = _split_table_cell_lines(row[value_cell_index])
    parsed_value_lines = [
        _scaled_metric_value_from_text(line, scale) for line in value_lines
    ]
    parsed_value_lines = [value for value in parsed_value_lines if value is not None]

    line_items: list[tuple[str, float]] = []
    if label_lines and parsed_value_lines:
        if _is_balance_sheet_group_heading(label_lines[0]):
            label_lines = label_lines[1:]
        offset = 0
        if len(label_lines) == len(parsed_value_lines) + 1:
            offset = 1
        for label_index, label in enumerate(label_lines):
            value_index = label_index - offset
            if value_index < 0 or value_index >= len(parsed_value_lines):
                continue
            preferred = _select_preferred_evidence_row_ref(
                label,
                strong_markers=_STRONG_TOTAL_DEBT_ROW_REFS,
                weak_markers=_WEAK_TOTAL_DEBT_ROW_REFS,
            )
            if not preferred:
                continue
            value = parsed_value_lines[value_index]
            if value < 0:
                continue
            line_items.append((label, value))
        if line_items:
            return line_items

    label = str(row[0] or "").strip()
    preferred = _select_preferred_evidence_row_ref(
        label,
        strong_markers=_STRONG_TOTAL_DEBT_ROW_REFS,
        weak_markers=_WEAK_TOTAL_DEBT_ROW_REFS,
    )
    if not preferred:
        return []
    value = _parse_current_period_metric_cell(row, scale)
    if value is None or value < 0:
        return []
    return [(label, value)]


_BALANCE_SHEET_GROUP_HEADINGS = {
    "assets",
    "current assets",
    "non-current assets",
    "non current assets",
    "liabilities",
    "current liabilities",
    "non-current liabilities",
    "non current liabilities",
    "equity",
}


def _is_balance_sheet_group_heading(label: str) -> bool:
    normalized = _normalise_evidence_row_ref(label)
    normalized = _re.sub(r"[\u2010-\u2015\u2212]", "-", normalized)
    return normalized in _BALANCE_SHEET_GROUP_HEADINGS


def _split_table_cell_lines(cell: Any) -> list[str]:
    return [
        _normalise_fragmented_pdf_text(line)
        for line in str(cell or "").splitlines()
        if _normalise_fragmented_pdf_text(line)
    ]


def _current_period_value_cell_index(row: list[Any]) -> int | None:
    parsed_values: list[tuple[int, tuple[float, bool]]] = []
    for idx, cell in enumerate(row[1:], start=1):
        parsed = _parse_first_metric_number_in_cell(cell)
        if parsed is None:
            continue
        parsed_values.append((idx, parsed))

    if not parsed_values:
        return None

    idx, (raw_value, has_explicit_unit) = parsed_values[0]
    if (
        len(parsed_values) >= 2
        and not has_explicit_unit
        and abs(raw_value) < 100
        and abs(parsed_values[1][1][0]) >= 100
    ):
        idx = parsed_values[1][0]
    return idx


def _parse_first_metric_number_in_cell(cell: Any) -> tuple[float, bool] | None:
    parsed = _parse_accounting_metric_number(cell)
    if parsed is not None:
        return parsed
    for line in _split_table_cell_lines(cell):
        parsed = _parse_accounting_metric_number(line)
        if parsed is not None:
            return parsed
    return None


def _scaled_metric_value_from_text(text: Any, scale: str) -> float | None:
    parsed = _parse_accounting_metric_number(text)
    if parsed is None:
        return None
    raw_value, has_explicit_unit = parsed
    if has_explicit_unit:
        return raw_value
    return raw_value * SCALE_MULTIPLIERS.get(scale, 1)


def _parse_table_numeric_cell(cell: Any) -> float | None:
    """Parse a table cell into a numeric value, preserving accounting negatives."""
    text = str(cell or "").strip()
    if not text or text in {"-", "−", "–", "—"}:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    text = (
        text.replace(",", "")
        .replace("A$", "")
        .replace("US$", "")
        .replace("$", "")
        .replace("AUD", "")
        .replace("USD", "")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .strip()
    )
    if not text or not _re.search(r"\d", text):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if negative else value


def _forward_fill_header_row(row: list[Any], width: int) -> list[str]:
    filled = [""] * width
    carry = ""
    for idx in range(width):
        cell = row[idx] if idx < len(row) else ""
        text = str(cell or "").strip()
        if text:
            carry = text
            filled[idx] = text
        elif idx > 0 and carry:
            filled[idx] = carry
    return filled


def _net_debt_column_contexts(table: Any) -> dict[int, str]:
    """Build per-column header context for deterministic net_debt note recovery."""
    header_rows: list[list[Any]] = []
    if getattr(table, "headers", None):
        header_rows.append(list(table.headers))
    for row in (getattr(table, "rows", []) or [])[:2]:
        header_rows.append(list(row))

    width = max((len(row) for row in header_rows), default=0)
    if width <= 1:
        return {}

    column_parts: dict[int, list[str]] = {idx: [] for idx in range(1, width)}
    for row in header_rows:
        filled = _forward_fill_header_row(row, width)
        for idx in range(1, width):
            part = filled[idx].strip()
            if part and part not in column_parts[idx]:
                column_parts[idx].append(part)
    return {idx: " ".join(parts) for idx, parts in column_parts.items()}


def _net_debt_period_match_score(context: str, period_end: str | None) -> int:
    period = parse_period_end(period_end)
    if period is None:
        return 0

    context_lower = context.lower()
    exact_patterns = (
        rf"\b{period.day}\s+{period.strftime('%b').lower()}\s+{period.year}\b",
        rf"\b{period.day}\s+{period.strftime('%B').lower()}\s+{period.year}\b",
        rf"\b{period.strftime('%b').lower()}\s+{period.day},?\s+{period.year}\b",
        rf"\b{period.strftime('%B').lower()}\s+{period.day},?\s+{period.year}\b",
    )
    if any(_re.search(pattern, context_lower) for pattern in exact_patterns):
        return 100
    if (
        str(period.year) in context_lower
        and (
            period.strftime("%b").lower() in context_lower
            or period.strftime("%B").lower() in context_lower
        )
    ):
        return 50
    if _re.search(rf"\b{period.year}\b", context_lower):
        return 10
    return 0


def _recover_explicit_net_debt_from_table(
    table: Any, *, period_end: str | None
) -> tuple[float, str, str | None] | None:
    """Recover an explicit Net debt row from the selected note table when the LLM abstains."""
    rows = getattr(table, "rows", []) or []
    if not rows:
        return None

    contexts = _net_debt_column_contexts(table)
    for row in rows:
        if not row:
            continue
        if _normalise_evidence_row_ref(row[0]) != "net debt":
            continue

        numeric_candidates: list[tuple[int, int, float, str]] = []
        for col_idx in range(1, len(row)):
            value = _parse_table_numeric_cell(row[col_idx])
            if value is None:
                continue
            context = contexts.get(col_idx, "").strip()
            score = _net_debt_period_match_score(context, period_end)
            numeric_candidates.append((score, col_idx, value, context))

        if not numeric_candidates:
            return None
        if len(numeric_candidates) == 1:
            _score, _col_idx, value, context = numeric_candidates[0]
            return value, "Net debt", context or None

        best_score = max(candidate[0] for candidate in numeric_candidates)
        best_candidates = [
            candidate for candidate in numeric_candidates if candidate[0] == best_score
        ]
        if best_score > 0 and len(best_candidates) == 1:
            _score, _col_idx, value, context = best_candidates[0]
            return value, "Net debt", context or None

        logger.info(
            "Abstaining deterministic net_debt_note fallback on page %s due to ambiguous candidates: %s",
            getattr(table, "page_number", "?"),
            [
                {
                    "score": score,
                    "column": col_idx,
                    "value": value,
                    "context": context,
                }
                for score, col_idx, value, context in numeric_candidates
            ],
        )
        return None

    return None


_EXPLICIT_NET_DEBT_CONFIDENCE_FLOOR = 0.95
_DERIVED_NET_DEBT_CONFIDENCE_CAP = 0.55


def _coerce_confidence(confidence: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        return default


# Row label substrings that contain "net" and "debt" but represent derived/context
# values rather than an explicit point-in-time net debt figure.  These must be
# rejected so that the reconciler only accepts a direct "Net debt" row.
_DERIVED_NET_DEBT_ROW_FRAGMENTS = frozenset(
    {
        "opening net debt",
        "closing net debt",
        "movement in net debt",
        "net debt movement",
        "change in net debt",
        "net debt plus",
        "net debt management",
        "net debt ratio",
        "net debt to",
        "net debt and",
        "net gearing",
        # Reconciliation opening-balance labels common in mining-sector annual reports
        "net debt: beginning",
        # Movement labels using increase/decrease notation (ASX resources sector)
        "/(decrease) in net debt",
        "/(increase) in net debt",
    }
)


def _is_explicit_net_debt_evidence(row_ref: str | None) -> bool:
    """Return True only when row_ref names an explicit point-in-time net debt row.

    Rows that contain "net debt" but represent derived, movement, or ratio values
    are rejected via _DERIVED_NET_DEBT_ROW_FRAGMENTS so they cannot pollute the
    explicit net_debt candidate selection.
    """
    label = _normalise_evidence_row_ref(row_ref)
    if not label or "net" not in label or "debt" not in label:
        return False
    return not any(fragment in label for fragment in _DERIVED_NET_DEBT_ROW_FRAGMENTS)


def _is_strong_total_debt_evidence(row_ref: str | None, value: Any) -> bool:
    preferred = _select_preferred_evidence_row_ref(
        row_ref,
        strong_markers=_STRONG_TOTAL_DEBT_ROW_REFS,
        weak_markers=_WEAK_TOTAL_DEBT_ROW_REFS,
    )
    label = _normalise_evidence_row_ref(preferred)
    if not label or label == "unknown":
        return False
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return False
    if numeric_value < 0:
        return False
    return True


def _document_has_nonnumeric_net_debt_reference(tables: list[Any]) -> bool:
    """Detect glossary/definition-only net-debt mentions that should not enable derivation."""
    for table in tables:
        for row in getattr(table, "rows", []) or []:
            if not row:
                continue
            label = _normalise_evidence_row_ref(row[0])
            if label != "net debt":
                continue
            if not any(_re.search(r"\d", str(cell or "")) for cell in row[1:]):
                return True
    return False


def _select_explicit_net_debt_candidate(pass3a_results: list[dict]) -> dict | None:
    candidates: list[tuple[int, int, dict]] = []
    for extraction in pass3a_results:
        value = extraction.get("net_debt")
        if value is None:
            continue
        row_ref = extraction.get("row_refs", {}).get("net_debt")
        if not _is_explicit_net_debt_evidence(row_ref):
            logger.info(
                "Rejecting net_debt from %s due to non-explicit row_ref=%r",
                extraction.get("_source", "unknown"),
                row_ref,
            )
            continue
        source = extraction.get("_source", "unknown")
        preference_group = 0 if source != "balance_sheet" else 1
        source_rank = (
            SOURCE_PRIORITY.index(source)
            if source in SOURCE_PRIORITY
            else len(SOURCE_PRIORITY)
        )
        candidates.append((preference_group, source_rank, extraction))

    if not candidates:
        return None

    return min(candidates, key=lambda item: (item[0], item[1]))[2]


def _explicit_net_debt_confidence(extraction: dict) -> float:
    base_conf = _coerce_confidence(extraction.get("pass3_confidence", 0.5))
    return max(base_conf, _EXPLICIT_NET_DEBT_CONFIDENCE_FLOOR)


def _derived_net_debt_confidence(extraction: dict) -> float:
    base_conf = _coerce_confidence(extraction.get("pass3_confidence", 0.5))
    return min(base_conf, _DERIVED_NET_DEBT_CONFIDENCE_CAP)


_EXTRACTION_RE = re.compile(
    r"^(?P<label>[a-z_]+):(?P<location>page_[^:]+):(?P<detail>.+)$"
)


def _build_field_provenance_entry(
    *,
    metric_name: str,
    source: Any,
    page: Any,
    row_ref: Any,
    scale: Any,
    scale_source: Any,
    pass1_result: dict,
    source_cell: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build structured payload provenance from already source-bound evidence."""
    source_text = str(source or "unknown").strip() or "unknown"
    page_tag = f"page_{page}" if page is not None else "page_?"
    row_text = str(row_ref or "unknown").strip() or "unknown"
    scale_text = str(scale or "unknown").strip() or "unknown"
    scale_source_text = str(scale_source or "unknown").strip() or "unknown"

    entry: dict[str, Any] = {
        "metric": metric_name,
        "source": source_text,
        "table_label": source_text,
        "page_number": page if page is not None else "unknown",
        "page_tag": page_tag,
        "row_ref": row_text,
        "excerpt": row_text,
        "scale": scale_text,
        "scale_source": scale_source_text,
        "currency": str(pass1_result.get("currency") or "unknown"),
        "period_type": str(pass1_result.get("report_type") or "unknown"),
        "period_end": str(pass1_result.get("period_end") or "unknown"),
    }
    if source_cell:
        entry["source_cell"] = {
            key: source_cell[key]
            for key in (
                "page_number",
                "table_index",
                "row_index",
                "column_index",
                "column_role",
                "period_basis",
                "row_label",
                "raw_value",
                "header_cell",
                "requested_period_end",
            )
            if key in source_cell
        }
    for output_key, input_keys in {
        "source_document_id": (
            "source_document_id",
            "_source_document_id",
            "document_id",
            "_document_id",
        ),
        "extraction_run_id": ("extraction_run_id", "_extraction_run_id", "run_id"),
    }.items():
        for input_key in input_keys:
            raw = pass1_result.get(input_key)
            if raw:
                entry[output_key] = str(raw)
                break
    return entry


def _run_pass4_reconciler(
    pass3a_results: list[dict],
    pass3b_result: dict,
    pass1_result: dict,
    *,
    sections: list[dict] | None = None,
) -> dict:
    """
    Pass 4: merge all Pass 3a results into one canonical payload.
    Source priority: income_statement > cashflow_statement > balance_sheet > highlights.
    Falls back to prose extraction for shares_outstanding when tables yield null.
    Returns dict matching _upsert_financial_rows contract.
    """
    merged_metrics: dict[str, Any] = {m: None for m in METRIC_FIELDS}
    provenance: dict[str, str] = {}
    field_provenance: dict[str, dict[str, Any]] = {}
    row_refs: dict[str, str] = {}
    metric_source_scales: dict[str, str] = {}
    metric_scale_sources: dict[str, str] = {}
    thinking_map: dict[str, str] = {}
    markdown_map: dict[str, str] = {}
    confidence_weighted_sum = 0.0
    confidence_weight = 0

    # Sort by priority
    ordered = sorted(
        pass3a_results,
        key=lambda r: (
            SOURCE_PRIORITY.index(r.get("_source", "highlights"))
            if r.get("_source") in SOURCE_PRIORITY
            else len(SOURCE_PRIORITY)
        ),
    )

    # Lower priority first — higher priority overwrites
    for extraction in reversed(ordered):
        source = extraction.get("_source", "unknown")
        conf = _coerce_confidence(extraction.get("pass3_confidence", 0.5))
        page = extraction.get("_page_number")
        page_tag = f"page_{page}" if page is not None else "page_?"
        for m in METRIC_FIELDS:
            if m == "net_debt":
                continue
            if m in extraction and extraction[m] is not None:
                merged_metrics[m] = extraction[m]
                row_ref = extraction.get("row_refs", {}).get(m, "unknown")
                row_refs[m] = row_ref
                metric_scale = str(extraction.get("_scale") or "").strip()
                if metric_scale and metric_scale != "unknown":
                    metric_source_scales[m] = metric_scale
                    metric_scale_sources[m] = str(
                        extraction.get("_scale_source") or "unknown"
                    )
                thinking_map[m] = extraction.get("_thinking") or ""
                markdown_map[m] = extraction.get("_markdown") or ""
                provenance[m] = f"{source}:{page_tag}:{row_ref}"
                field_provenance[m] = _build_field_provenance_entry(
                    metric_name=m,
                    source=source,
                    page=page,
                    row_ref=row_ref,
                    scale=metric_scale,
                    scale_source=metric_scale_sources.get(m),
                    pass1_result=pass1_result,
                    source_cell=(extraction.get("_period_source_cells") or {}).get(m),
                )
                ocr_source = (extraction.get("_ocr_metric_provenance") or {}).get(m)
                if isinstance(ocr_source, dict):
                    field_provenance[m]["ocr_source"] = dict(ocr_source)
                confidence_weighted_sum += conf
                confidence_weight += 1

    explicit_net_debt = _select_explicit_net_debt_candidate(pass3a_results)
    if explicit_net_debt is not None:
        source = explicit_net_debt.get("_source", "unknown")
        page = explicit_net_debt.get("_page_number")
        page_tag = f"page_{page}" if page is not None else "page_?"
        row_ref = explicit_net_debt.get("row_refs", {}).get("net_debt", "unknown")
        merged_metrics["net_debt"] = explicit_net_debt["net_debt"]
        row_refs["net_debt"] = row_ref
        metric_scale = str(explicit_net_debt.get("_scale") or "").strip()
        if metric_scale and metric_scale != "unknown":
            metric_source_scales["net_debt"] = metric_scale
            metric_scale_sources["net_debt"] = str(
                explicit_net_debt.get("_scale_source") or "unknown"
            )
        thinking_map["net_debt"] = explicit_net_debt.get("_thinking") or ""
        markdown_map["net_debt"] = explicit_net_debt.get("_markdown") or ""
        provenance["net_debt"] = f"{source}:{page_tag}:{row_ref}"
        field_provenance["net_debt"] = _build_field_provenance_entry(
            metric_name="net_debt",
            source=source,
            page=page,
            row_ref=row_ref,
            scale=metric_scale,
            scale_source=metric_scale_sources.get("net_debt"),
            pass1_result=pass1_result,
        )
        ocr_source = (explicit_net_debt.get("_ocr_metric_provenance") or {}).get(
            "net_debt"
        )
        if isinstance(ocr_source, dict):
            field_provenance["net_debt"]["ocr_source"] = dict(ocr_source)
        net_debt_conf = _explicit_net_debt_confidence(explicit_net_debt)
        confidence_weighted_sum += net_debt_conf
        confidence_weight += 1
        logger.info(
            "Using explicit net_debt from %s with boosted confidence %.2f",
            source,
            net_debt_conf,
        )

    # B4: derive net_debt from balance sheet total_debt when not directly extracted.
    # total_debt is an internal capture field (not in METRIC_FIELDS) so it survives
    # only in the raw pass3a extraction dict, not in merged_metrics.
    if merged_metrics.get("net_debt") is None:
        if pass1_result.get("_block_derived_net_debt"):
            logger.info(
                "Skipping net_debt derivation due to non-numeric net debt reference in source tables"
            )
        else:
            bs_result = next(
                (r for r in pass3a_results if r.get("_source") == "balance_sheet"), None
            )
            if bs_result is not None:
                total_debt = bs_result.get("total_debt")
                total_debt_row_ref = bs_result.get("row_refs", {}).get("total_debt")
                cash_end = merged_metrics.get("cash_end")
                if (
                    total_debt is not None
                    and cash_end is not None
                    and _is_strong_total_debt_evidence(total_debt_row_ref, total_debt)
                ):
                    merged_metrics["net_debt"] = total_debt - cash_end
                    row_ref = f"total_debt({total_debt:.0f})-cash_end({cash_end:.0f})"
                    row_refs["net_debt"] = row_ref
                    provenance["net_debt"] = (
                        f"derived:balance_sheet:{row_ref}"
                    )
                    field_provenance["net_debt"] = _build_field_provenance_entry(
                        metric_name="net_debt",
                        source="derived:balance_sheet",
                        page=bs_result.get("_page_number"),
                        row_ref=row_ref,
                        scale=str(bs_result.get("_scale") or "").strip(),
                        scale_source=str(
                            bs_result.get("_scale_source") or "unknown"
                        ),
                        pass1_result=pass1_result,
                    )
                    net_debt_conf = _derived_net_debt_confidence(bs_result)
                    confidence_weighted_sum += net_debt_conf
                    confidence_weight += 1
                    logger.info(
                        "net_debt derived from balance sheet: %.0f - %.0f = %.0f (confidence=%.2f)",
                        total_debt,
                        cash_end,
                        merged_metrics["net_debt"],
                        net_debt_conf,
                    )
                elif total_debt is not None and cash_end is not None:
                    logger.info(
                        "Skipping net_debt derivation from weak debt evidence row_ref=%r value=%r",
                        total_debt_row_ref,
                        total_debt,
                    )

    # Prose fallback: shares_outstanding from note sections when tables yield null.
    # Banking filings (ANZ, WBC) often report share counts in prose Note 13/14
    # rather than in structured tables.
    contract_metrics = pass1_result.get("_contract_allowed_canonical_metrics")
    contract_allows_shares = (
        not isinstance(contract_metrics, (list, tuple, set, frozenset))
        or "shares_outstanding" in contract_metrics
    )
    if (
        contract_allows_shares
        and merged_metrics.get("shares_outstanding") is None
        and sections
    ):
        prose_shares, prose_prov = _extract_shares_from_prose(sections)
        if prose_shares is not None:
            merged_metrics["shares_outstanding"] = prose_shares
            provenance["shares_outstanding"] = prose_prov
            # Extract row_ref from prose_prov (e.g., prose_note:page_12:The Company had...)
            prose_match = _EXTRACTION_RE.match(prose_prov)
            if prose_match:
                row_refs["shares_outstanding"] = prose_match.group("detail")
                field_provenance["shares_outstanding"] = (
                    _build_field_provenance_entry(
                        metric_name="shares_outstanding",
                        source="prose_note",
                        page=prose_match.group("location").replace("page_", ""),
                        row_ref=prose_match.group("detail"),
                        scale=str(pass1_result.get("scale") or "unknown"),
                        scale_source="document",
                        pass1_result=pass1_result,
                    )
                )

    # Weighted average confidence — each source weighted by metrics contributed
    metric_confidence = (
        confidence_weighted_sum / max(confidence_weight, 1)
        if confidence_weight
        else 0.0
    )

    logger.info(
        "Pass4 merged: %s",
        {k: v for k, v in merged_metrics.items() if v is not None},
    )

    return {
        "period_type": pass1_result.get("report_type"),
        "period_end": pass1_result.get("period_end"),
        "source_period_type": pass1_result.get("_source_period_type"),
        "source_period_evidence": pass1_result.get("_source_period_evidence"),
        "source_period_end_evidence": pass1_result.get("_source_period_end_evidence"),
        "source_period_end_binding": pass1_result.get("_source_period_end_binding"),
        "source_document_classification": pass1_result.get(
            "_source_document_classification"
        ),
        "metrics": merged_metrics,
        "row_refs": row_refs,
        "metric_source_scales": metric_source_scales,
        "metric_scale_sources": metric_scale_sources,
        "field_provenance": field_provenance,
        "thinking": thinking_map,
        "markdown_tables": markdown_map,
        "confidence_metrics": round(metric_confidence, 3),
        "provenance": provenance,
        **pass3b_result,  # risk_summary, risk_bullets, guidance_summary, material_changes, confidence_narrative
    }


def _enforce_contract_metric_allowance(
    payload: dict[str, Any],
    allowed_metrics: Sequence[str],
) -> None:
    """Remove canonical metrics and their evidence outside a selected contract."""

    denied_metrics = set(METRIC_FIELDS) - set(allowed_metrics)
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    for metric_name in denied_metrics:
        metrics[metric_name] = None
        payload[metric_name] = None

    for evidence_key in (
        "row_refs",
        "metric_source_scales",
        "metric_scale_sources",
        "field_provenance",
        "thinking",
        "markdown_tables",
        "provenance",
    ):
        evidence = payload.get(evidence_key)
        if isinstance(evidence, dict):
            for metric_name in denied_metrics:
                evidence.pop(metric_name, None)

    payload["metrics"] = metrics


def _common_metric_source_scale(payload: dict, fallback: Any) -> str:
    """Return a common explicit metric source scale when all dollar metrics agree."""
    metric_scales = payload.get("metric_source_scales")
    metrics = payload.get("metrics")
    if not isinstance(metric_scales, dict) or not isinstance(metrics, dict):
        return str(fallback or "unknown")

    scales = {
        str(scale).strip()
        for metric_name, scale in metric_scales.items()
        if metric_name != "shares_outstanding"
        and metrics.get(metric_name) is not None
        and str(scale).strip()
        and str(scale).strip() != "unknown"
    }
    if len(scales) == 1:
        return next(iter(scales))
    return str(fallback or "unknown")


# ---------------------------------------------------------------------------
# Scale Validation — detect obviously wrong multiplier application
# ---------------------------------------------------------------------------

# ASX-listed companies have minimum plausible values for key metrics.
# Annual revenue < $1M is almost certainly a missing scale multiplier.
# These thresholds are intentionally loose — they catch egregious errors
# (e.g., 19.5 instead of 19,500,000,000) without flagging legitimate
# small-cap companies.
_SCALE_VALIDATION_THRESHOLDS: dict[str, dict[str, float]] = {
    "A": {  # Annual reports
        "revenue": 1_000_000,  # $1M — any ASX-listed company exceeds this
        "ebit": 100_000,  # $100K
        "np_attributable": 100_000,  # $100K
        "operating_cf": 100_000,  # $100K
    },
    "H": {  # Half-year
        "revenue": 500_000,  # $500K
        "ebit": 50_000,  # $50K
        "np_attributable": 50_000,  # $50K
        "operating_cf": 50_000,  # $50K
    },
    "Q": {  # Quarterly
        "revenue": 100_000,  # $100K
        "ebit": 10_000,  # $10K
    },
}

_DOLLAR_METRIC_FIELDS = tuple(m for m in METRIC_FIELDS if m != "shares_outstanding")
_ACCEPTED_OUTPUT_REVENUE_RATIO_RISK_FIELDS = (
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
)
_ACCEPTED_OUTPUT_REVENUE_RATIO_REVIEW_THRESHOLD = 10.0
_REAL_ESTATE_NET_DEBT_RATIO_CONTEXT_MARKERS = (
    "dexus",
    "reit",
    "realestate",
    "investmentproperty",
    "investmentproperties",
    "stapledsecurity",
    "stapledsecurities",
)
_SOURCE_BOUND_NET_DEBT_MARKERS = (
    "derivedbalancesheet",
    "netdebt",
    "totaldebt",
)

# Over-scale threshold: values above $500B are almost certainly over-multiplied
# for AUD-like currencies. High-denomination native currencies need explicit
# source-unit support and a currency-specific cap; this does not perform FX
# conversion or rewrite extracted values.
_DEFAULT_NATIVE_SANITY_CAP = 500_000_000_000  # $500B
_HIGH_DENOMINATION_NATIVE_SANITY_CAPS = {
    "IDR": 10_000_000_000_000_000,  # Rp10 quadrillion
}


def _normalize_currency_code(raw: Any) -> str:
    normalized = str(raw or "").strip().lower()
    if normalized in {"", "-", "n/a", "na", "none", "null", "unknown"}:
        return ""
    return normalized.upper()


def _native_currency_sanity_cap(raw_currency: Any) -> int:
    currency = _normalize_currency_code(raw_currency)
    return _HIGH_DENOMINATION_NATIVE_SANITY_CAPS.get(
        currency,
        _DEFAULT_NATIVE_SANITY_CAP,
    )


def _validate_scale(payload: dict) -> str:
    """
    Post-Pass-4 scale validation: detect values that are orders of magnitude
    too small (missing multiplier) or too large (double-multiplied).

    Returns one of:
      - "pass" — values are in a plausible range
      - "suspect_underscaled" — multiple metrics are suspiciously small
      - "suspect_overscaled" — at least one metric exceeds $500B

    This function only inspects, it does NOT modify the payload.
    """
    metrics = payload.get("metrics", {})
    period_type = payload.get("period_type", "A")
    currency = _normalize_currency_code(payload.get("currency"))
    sanity_cap = _native_currency_sanity_cap(currency)
    thresholds = _SCALE_VALIDATION_THRESHOLDS.get(
        period_type, _SCALE_VALIDATION_THRESHOLDS["A"]
    )

    # Check for over-scaled values
    for m, v in metrics.items():
        if v is not None and abs(v) > sanity_cap:
            logger.warning(
                "scale_validation: SUSPECT_OVERSCALED — %s=%s exceeds native "
                "currency cap %s (currency=%s, period_type=%s, period_end=%s)",
                m,
                v,
                sanity_cap,
                currency,
                period_type,
                payload.get("period_end"),
            )
            return "suspect_overscaled"

    # Check for under-scaled values: count how many key metrics fall below thresholds
    underscaled_count = 0
    checked_count = 0
    underscaled_details: list[str] = []
    for m, min_val in thresholds.items():
        val = metrics.get(m)
        if val is not None:
            checked_count += 1
            if abs(val) < min_val:
                underscaled_count += 1
                underscaled_details.append(f"{m}={val}")

    # Trigger if ALL checked metrics are below threshold (not just one — a single
    # small metric could be legitimate, e.g. small EBIT for a breakeven company)
    if checked_count > 0 and underscaled_count == checked_count:
        logger.warning(
            "scale_validation: SUSPECT_UNDERSCALED — all %d checked metrics below "
            "minimum thresholds: [%s] (period_type=%s, period_end=%s, scale=%s)",
            checked_count,
            ", ".join(underscaled_details),
            period_type,
            payload.get("period_end"),
            payload.get("scale", "unknown"),
        )
        return "suspect_underscaled"

    return "pass"


def _clean_payload_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "unknown"}:
        return None
    return text


def _coerce_metric_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_bound_real_estate_net_debt_ratio_is_expected(payload: dict) -> bool:
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    net_debt_source = _normalize_filter_text(
        _combined_source_text(
            row_refs.get("net_debt"),
            provenance.get("net_debt"),
            field_provenance.get("net_debt"),
        )
    )
    if not any(marker in net_debt_source for marker in _SOURCE_BOUND_NET_DEBT_MARKERS):
        return False

    context_values = [
        payload.get("document_title"),
        payload.get("document_subtype"),
        payload.get("source_bound"),
        payload.get("source_document_classification"),
        payload.get("source_period_end_evidence"),
        payload.get("wrapper_disclosures"),
        row_refs,
        provenance,
        field_provenance,
    ]
    context = _normalize_filter_text(_combined_source_text(*context_values))
    return any(
        marker in context
        for marker in _REAL_ESTATE_NET_DEBT_RATIO_CONTEXT_MARKERS
    )


def _accepted_output_scale_magnitude_risk_error(
    payload: dict,
    canonical_metrics: dict[str, Any],
) -> str | None:
    """Fail closed when an otherwise accepted output has scale/magnitude risk."""
    codes: list[str] = []
    scale = (_clean_payload_text(payload.get("scale")) or "unknown").lower()
    metric_source_scales_raw = payload.get("metric_source_scales")
    metric_source_scales: dict[str, str] = {}
    if isinstance(metric_source_scales_raw, dict):
        for metric_name, scale_value in metric_source_scales_raw.items():
            if metric_name not in _DOLLAR_METRIC_FIELDS:
                continue
            if canonical_metrics.get(metric_name) is None:
                continue
            metric_scale = _clean_payload_text(scale_value)
            if metric_scale is not None:
                metric_source_scales[str(metric_name)] = metric_scale.lower()

    distinct_metric_scales = sorted(set(metric_source_scales.values()))
    if len(distinct_metric_scales) > 1:
        codes.append("mixed_metric_source_scales")

    if scale != "unknown":
        if any(metric_scale != scale for metric_scale in metric_source_scales.values()):
            codes.append("payload_scale_differs_from_metric_source_scale")

    revenue = _coerce_metric_number(canonical_metrics.get("revenue"))
    if revenue is not None and abs(revenue) > 0:
        for metric_name in _ACCEPTED_OUTPUT_REVENUE_RATIO_RISK_FIELDS:
            value = _coerce_metric_number(canonical_metrics.get(metric_name))
            if value is None:
                continue
            ratio = abs(value) / abs(revenue)
            if ratio >= _ACCEPTED_OUTPUT_REVENUE_RATIO_REVIEW_THRESHOLD:
                if (
                    metric_name == "net_debt"
                    and _source_bound_real_estate_net_debt_ratio_is_expected(payload)
                ):
                    continue
                codes.append("metric_revenue_ratio_high")
                break

    if not codes:
        return None
    suffix = ",".join(dict.fromkeys(codes))
    return f"validation_gate:accepted_output_scale_magnitude_risk:{suffix}"


# ---------------------------------------------------------------------------
# Validation Gate
# ---------------------------------------------------------------------------

_APPENDIX_WRAPPER_DOCUMENT_MARKERS = ("appendix4d", "appendix4e")
_APPENDIX_WRAPPER_REQUIRED_METRICS = {"revenue", "np_attributable"}
_APPENDIX_WRAPPER_SOURCE_METRICS = _APPENDIX_WRAPPER_REQUIRED_METRICS | {"ebit"}
_APPENDIX_WRAPPER_DISCLOSURE_MARKER_GROUPS: tuple[tuple[str, ...], ...] = (
    ("ntapersecurity", "nettangibleassetspersecurity"),
    ("dividendsdistributions", "dividends", "distribution"),
    ("recorddate",),
    ("associatesandjointventures", "jointventures", "associates"),
)
_APPENDIX_WRAPPER_DISCLOSURE_LABELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Net tangible assets per security", ("ntapersecurity", "nettangibleassetspersecurity")),
    ("Dividends / distributions", ("dividendsdistributions", "dividends", "distribution")),
    ("Record date for determining entitlement", ("recorddate",)),
    (
        "Details of associates and joint ventures entities",
        ("associatesandjointventures", "jointventures", "associates"),
    ),
)
_APPENDIX_WRAPPER_REVENUE_LABELS = (
    "totalrevenuesandotherincome",
    "revenuefromordinaryactivities",
    "revenuesfromordinaryactivities",
)
_APPENDIX_WRAPPER_NP_ATTRIBUTABLE_LABELS = (
    "netprofitafterincometaxexpensefromordinaryactivities",
    "profitafterincometaxexpensefromordinaryactivities",
    "profitfromordinaryactivitiesaftertax",
    "lossfromordinaryactivitiesaftertax",
    "profitforthehalfyearfromordinaryactivitiesaftertaxattributable",
    "profitforthehalfyearattributabletotheowners",
    "profitfortheperiodfromordinaryactivitiesaftertaxattributable",
    "netlossprofitaftertaxattributabletomembers",
    "netlossprofitaftertaxattributable",
)
_APPENDIX_WRAPPER_EBIT_LABELS = (
    "earningsbeforeinterestandtaxebit",
    "earningsbeforeinteresttaxebit",
    "earningsbeforeinterestandtax",
)
_APPENDIX_WRAPPER_EBIT_REJECT_LABELS = (
    "ebitda",
    "depreciationandamortisation",
    "depreciationamortisation",
)
_SOURCE_NUMBER_RE = re.compile(r"^\(?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?$")


def _appendix_wrapper_subtype_from_text(*values: Any) -> str | None:
    compact = _normalize_filter_text(_combined_source_text(*values))
    if "appendix4d" in compact:
        return "appendix4d"
    if "appendix4e" in compact:
        return "appendix4e"
    return None


def _source_sections_for_pages(
    sections: list[dict] | None,
    *,
    max_page: int = 4,
) -> list[dict]:
    if not sections:
        return []
    selected: list[dict] = []
    for section in sections:
        try:
            page = int(section.get("page"))
        except (TypeError, ValueError):
            page = None
        if page is None or 0 < page <= max_page:
            selected.append(section)
    return selected


def _appendix_wrapper_source_text(
    sections: list[dict] | None,
    tables: Any,
    *,
    max_page: int = 4,
    max_chars: int = 12000,
) -> str:
    fragments: list[str] = []
    for section in _source_sections_for_pages(sections, max_page=max_page):
        text = str(section.get("text") or "").strip()
        if text:
            fragments.append(text)

    for table in tables or []:
        try:
            page = int(getattr(table, "page_number", 0))
        except (TypeError, ValueError):
            page = 0
        if page and page > max_page:
            continue
        fragments.extend(_flatten_payload_text(getattr(table, "caption", "")))
        fragments.extend(_flatten_payload_text(getattr(table, "headers", [])))
        fragments.extend(_flatten_payload_text(getattr(table, "rows", [])[:12]))

    return " ".join(fragment for fragment in fragments if fragment)[:max_chars]


def _parse_source_numeric_value(value: Any) -> float | None:
    text = str(value or "").strip().replace("\u00a0", " ")
    if not text or "%" in text or "$" in text:
        return None
    if re.fullmatch(r"\d+\.\d+", text):
        return None
    if re.search(r"[A-Za-z]", text):
        return None
    if not _SOURCE_NUMBER_RE.match(text):
        return None
    negative = text.startswith("(") and text.endswith(")")
    normalised = text.strip("()").replace(",", "")
    try:
        parsed = float(normalised)
    except ValueError:
        return None
    return -parsed if negative else parsed


def _scale_source_value(value: float, scale: Any) -> float:
    return value * SCALE_MULTIPLIERS.get(str(scale or "unknown"), 1)


def _appendix_wrapper_label_from_table_row(row: list[Any]) -> str:
    label_parts: list[str] = []
    for cell in row:
        text = _normalise_fragmented_pdf_text(cell)
        if not text:
            continue
        if _parse_source_numeric_value(text) is not None:
            break
        if "%" in text or "$" in text or re.fullmatch(r"\d+(?:\.\d+)?", text):
            continue
        label_parts.append(text)
    return " ".join(" ".join(label_parts).split())[:120]


def _find_appendix_wrapper_metric_in_tables(
    tables: Any,
    label_markers: tuple[str, ...],
    *,
    scale: Any,
    max_page: int = 4,
    reject_markers: tuple[str, ...] = (),
) -> tuple[float, str, str] | None:
    for table in tables or []:
        try:
            page = int(getattr(table, "page_number", 0))
        except (TypeError, ValueError):
            page = 0
        if page and page > max_page:
            continue
        for row in getattr(table, "rows", []) or []:
            row_text = _normalise_fragmented_pdf_text(
                " ".join(str(cell) for cell in row)
            )
            compact_row = _normalize_filter_text(row_text)
            if not any(marker in compact_row for marker in label_markers):
                continue
            if any(marker in compact_row for marker in reject_markers):
                continue
            label = _appendix_wrapper_label_from_table_row(row)
            if not label:
                continue
            for cell in row[1:]:
                raw_value = _parse_source_numeric_value(cell)
                if raw_value is None:
                    continue
                value = _scale_source_value(raw_value, scale)
                return value, label, f"appendix_wrapper:page_{page or '?'}:{label}"
    return None


def _find_appendix_wrapper_metric_in_sections(
    sections: list[dict],
    label_markers: tuple[str, ...],
    *,
    scale: Any,
) -> tuple[float, str, str] | None:
    texts = [str(section.get("text") or "").strip() for section in sections]
    pages = [section.get("page") for section in sections]
    for idx, text in enumerate(texts):
        if "%" in text or "$" in text or re.fullmatch(r"\d+(?:\.\d+)?", text):
            continue
        label_window = " ".join(texts[idx : idx + 4])
        compact_label = _normalize_filter_text(label_window)
        if not any(marker in compact_label for marker in label_markers):
            continue
        label_parts: list[str] = []
        for label_idx in range(idx, min(idx + 4, len(texts))):
            label_text = texts[label_idx]
            if label_idx > idx and _parse_source_numeric_value(label_text) is not None:
                break
            if (
                "%" in label_text
                or "$" in label_text
                or re.fullmatch(r"\d+(?:\.\d+)?", label_text)
            ):
                continue
            label_parts.append(label_text)
        label = " ".join(" ".join(label_parts).split())[:120]
        for value_idx in range(idx + 1, min(idx + 10, len(texts))):
            raw_value = _parse_source_numeric_value(texts[value_idx])
            if raw_value is None:
                continue
            page = str(pages[value_idx] or pages[idx] or "?")
            value = _scale_source_value(raw_value, scale)
            return value, label, f"appendix_wrapper:page_{page}:{label}"
    return None


def _detect_appendix_wrapper_disclosures(source_text: str) -> list[str]:
    compact = _normalize_filter_text(source_text)
    disclosures: list[str] = []
    for label, marker_group in _APPENDIX_WRAPPER_DISCLOSURE_LABELS:
        if any(marker in compact for marker in marker_group):
            disclosures.append(label)
    return disclosures


def _build_appendix_wrapper_source_payload(
    *,
    title: Any,
    sections: list[dict] | None,
    tables: Any,
    period_evidence: dict[str, Any],
    period_end_evidence: dict[str, Any],
    scale: Any,
    currency: Any,
) -> dict[str, Any]:
    source_text = _appendix_wrapper_source_text(sections, tables)
    subtype = _appendix_wrapper_subtype_from_text(title, source_text)
    if subtype is None:
        return {"is_wrapper": False}

    source_sections = _source_sections_for_pages(sections)
    source_text_period_end = (
        period_end_evidence.get("period_end")
        if _has_source_text_period_end_hit(period_end_evidence)
        else None
    )
    source_payload: dict[str, Any] = {
        "is_wrapper": True,
        "document_subtype": subtype,
        "document_title": str(title or "").strip(),
        "period_type": period_end_evidence.get("period_type")
        or period_evidence.get("period_type"),
        "period_end": source_text_period_end,
        "scale": scale,
        "currency": _normalize_currency_code(currency) or None,
        "wrapper_disclosures": _detect_appendix_wrapper_disclosures(source_text),
        "metrics": {},
        "row_refs": {},
        "provenance": {},
    }

    if not source_payload["document_title"]:
        source_payload["document_title"] = (
            "Appendix 4D" if subtype == "appendix4d" else "Appendix 4E"
        )

    if str(scale or "").strip().lower() not in ("", "unknown"):
        revenue = _find_appendix_wrapper_metric_in_sections(
            source_sections,
            _APPENDIX_WRAPPER_REVENUE_LABELS,
            scale=scale,
        )
        if revenue is not None:
            value, row_ref, provenance = revenue
            source_payload["metrics"]["revenue"] = value
            source_payload["row_refs"]["revenue"] = row_ref
            source_payload["provenance"]["revenue"] = provenance

        ebit = _find_appendix_wrapper_metric_in_tables(
            tables,
            _APPENDIX_WRAPPER_EBIT_LABELS,
            scale=scale,
            reject_markers=_APPENDIX_WRAPPER_EBIT_REJECT_LABELS,
        )
        if ebit is not None:
            value, row_ref, provenance = ebit
            source_payload["metrics"]["ebit"] = value
            source_payload["row_refs"]["ebit"] = row_ref
            source_payload["provenance"]["ebit"] = provenance

        np_attributable = _find_appendix_wrapper_metric_in_tables(
            tables,
            _APPENDIX_WRAPPER_NP_ATTRIBUTABLE_LABELS,
            scale=scale,
        )
        if np_attributable is None:
            np_attributable = _find_appendix_wrapper_metric_in_sections(
                source_sections,
                _APPENDIX_WRAPPER_NP_ATTRIBUTABLE_LABELS,
                scale=scale,
            )
        if np_attributable is not None:
            value, row_ref, provenance = np_attributable
            source_payload["metrics"]["np_attributable"] = value
            source_payload["row_refs"]["np_attributable"] = row_ref
            source_payload["provenance"]["np_attributable"] = provenance

    return source_payload


_APPENDIX_WRAPPER_WEAK_ROW_MARKERS = (
    "previousperiod",
    "priorperiod",
    "comparativeperiod",
    "previousyear",
    "prioryear",
    "footnote",
)


def _appendix_wrapper_source_row_is_weak(value: Any) -> bool:
    compact = _normalize_filter_text(value)
    return any(marker in compact for marker in _APPENDIX_WRAPPER_WEAK_ROW_MARKERS)


def _source_text_is_appendix_wrapper(value: Any) -> bool:
    compact = _normalize_filter_text(value)
    return "appendixwrapper" in compact


def _apply_appendix_wrapper_source_payload(
    payload: dict[str, Any],
    wrapper_source: dict[str, Any] | None,
) -> None:
    if not isinstance(wrapper_source, dict) or not wrapper_source.get("is_wrapper"):
        return

    if wrapper_source.get("period_type") in {"A", "H", "Q"}:
        payload["period_type"] = wrapper_source["period_type"]
    if wrapper_source.get("period_end"):
        payload["period_end"] = wrapper_source["period_end"]

    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )
    weak_wrapper_metrics = {
        metric_name
        for metric_name in _APPENDIX_WRAPPER_SOURCE_METRICS
        if _appendix_wrapper_source_row_is_weak(
            wrapper_source.get("row_refs", {}).get(metric_name)
        )
        or _appendix_wrapper_source_row_is_weak(
            wrapper_source.get("provenance", {}).get(metric_name)
        )
    }
    wrapper_scale = str(wrapper_source.get("scale") or "").strip()
    for metric_name, value in wrapper_source.get("metrics", {}).items():
        if metric_name in _APPENDIX_WRAPPER_SOURCE_METRICS and value is not None:
            if metric_name in weak_wrapper_metrics and metrics.get(metric_name) is not None:
                continue
            metrics[metric_name] = value
            payload[metric_name] = value
            if wrapper_scale and wrapper_scale != "unknown":
                metric_source_scales[metric_name] = wrapper_scale
                metric_scale_sources[metric_name] = "wrapper"
    for metric_name, row_ref in wrapper_source.get("row_refs", {}).items():
        if metric_name in _APPENDIX_WRAPPER_SOURCE_METRICS:
            if metric_name in weak_wrapper_metrics and metrics.get(metric_name) is not None:
                continue
            row_refs[metric_name] = row_ref
    for metric_name, source in wrapper_source.get("provenance", {}).items():
        if metric_name in _APPENDIX_WRAPPER_SOURCE_METRICS:
            if metric_name in weak_wrapper_metrics and metrics.get(metric_name) is not None:
                continue
            provenance[metric_name] = source
            source_match = _EXTRACTION_RE.match(str(source))
            if source_match:
                page = source_match.group("location").replace("page_", "")
                row_ref = row_refs.get(metric_name) or source_match.group("detail")
                field_provenance[metric_name] = _build_field_provenance_entry(
                    metric_name=metric_name,
                    source=source_match.group("label"),
                    page=page,
                    row_ref=row_ref,
                    scale=wrapper_source.get("scale") or payload.get("scale"),
                    scale_source="wrapper",
                    pass1_result={
                        "report_type": wrapper_source.get("period_type")
                        or payload.get("period_type"),
                        "period_end": wrapper_source.get("period_end")
                        or payload.get("period_end"),
                        "currency": wrapper_source.get("currency")
                        or payload.get("currency"),
                    },
                )
    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources

    if wrapper_source.get("wrapper_disclosures") is not None:
        payload["wrapper_disclosures"] = list(wrapper_source["wrapper_disclosures"])

    source_bound = payload.get("source_bound")
    if not isinstance(source_bound, dict):
        source_bound = {}
    for key in (
        "document_subtype",
        "document_title",
        "period_type",
        "period_end",
        "scale",
        "currency",
    ):
        if wrapper_source.get(key) not in (None, ""):
            source_bound[key] = wrapper_source[key]
    payload["source_bound"] = source_bound

    wrapper_metric_names = {
        name
        for name, value in wrapper_source.get("metrics", {}).items()
        if name in _APPENDIX_WRAPPER_REQUIRED_METRICS and value is not None
    }
    if _APPENDIX_WRAPPER_REQUIRED_METRICS.issubset(wrapper_metric_names):
        payload["confidence_metrics"] = max(
            _coerce_confidence(payload.get("confidence_metrics", 0.0)),
            0.9,
        )


def _is_financial_report_contents_index_text(normalized_text: str) -> bool:
    return (
        "notestothefinancialstatements" in normalized_text
        and "consolidatedstatementofcashflows" in normalized_text
        and any(
            marker in normalized_text
            for marker in (
                "consolidatedstatementofcomprehensiveincome",
                "consolidatedincomestatement",
                "consolidatedstatementofprofitorloss",
            )
        )
    )


def _table_has_income_statement_source_rows(table: Any) -> bool:
    text = _normalize_filter_text(
        " ".join(
            [
                str(getattr(table, "caption", "") or ""),
                " ".join(str(header) for header in getattr(table, "headers", []) or []),
                " ".join(
                    " ".join(str(cell) for cell in row)
                    for row in (getattr(table, "rows", []) or [])[:50]
                    if row
                ),
            ]
        )
    )
    if _is_financial_report_contents_index_text(text):
        return False
    if any(
        marker in text
        for marker in (
            "appendix4d",
            "appendix4e",
            "resultsforannouncement",
        )
    ):
        return False
    if any(
        _normalize_filter_text(marker) in text
        for marker in (
            *_SEGMENT_DISQUALIFY_PHRASES,
            *_INCOME_STATEMENT_DISQUALIFY_PHRASES,
        )
    ):
        return False
    return any(
        marker in text
        for marker in (
            "incomestatement",
            "statementofcomprehensiveincome",
            "statementofprofitorloss",
            "profitlossfromoperations",
            "profitfromoperations",
            "revenuefromcontinuingoperations",
            "totalrevenuefromordinaryactivities",
            "profitlossforthehalfyearisattributableto",
            "attributabletobhpshareholders",
            "equityholdersoftheparent",
            "profitbeforecreditimpairmentandincometax",
            "profitattributabletoshareholdersofthecompany",
        )
    )


def _preferred_statement_tables(tables: Any) -> list[Any]:
    def _page_number(table: Any) -> int:
        try:
            return int(getattr(table, "page_number", 0) or 0)
        except (TypeError, ValueError):
            return 0

    return sorted(
        list(tables or []),
        key=lambda table: (-_statement_precedence_rank(table), _page_number(table)),
    )


def _apply_preferred_income_statement_source_payload(
    payload: dict[str, Any],
    tables: Any,
    *,
    scale: Any,
    pass1_result: dict,
) -> None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )

    def _existing_income_statement_metric_is_rejected(metric_name: str) -> bool:
        if metric_name != "ebit":
            return False
        compact = _normalize_filter_text(
            _combined_source_text(row_refs.get(metric_name), provenance.get(metric_name))
        )
        return any(blocker in compact for blocker, _source_label in _EBIT_LABEL_BLOCKERS)

    def _existing_income_statement_metric_scale_conflicts(
        metric_name: str,
        preferred_scale: str,
        table_scale: str,
    ) -> bool:
        if metric_name not in {"revenue", "ebit", "np_attributable"}:
            return False
        if table_scale == "unknown":
            return False
        normalized_preferred = str(preferred_scale or "").strip().lower()
        if not normalized_preferred or normalized_preferred == "unknown":
            return False
        target_scale = str(scale or "").strip().lower()
        if normalized_preferred != target_scale:
            return False
        existing_scale = str(metric_source_scales.get(metric_name) or "").strip().lower()
        if not existing_scale or existing_scale == "unknown":
            return False
        if existing_scale == normalized_preferred:
            return False
        existing_provenance = str(provenance.get(metric_name) or "").strip().lower()
        return existing_provenance.startswith("income_statement:")

    def _existing_income_statement_metric_has_lower_priority(
        metric_name: str,
        recovered_row_ref: str,
    ) -> bool:
        if metric_name != "revenue":
            return False
        existing_provenance = str(provenance.get(metric_name) or "").strip().lower()
        if not existing_provenance.startswith("income_statement:"):
            return False
        existing_priority = _income_metric_priority_for_row_label(
            str(row_refs.get(metric_name) or ""),
            metric_name,
            [],
        )
        recovered_priority = _income_metric_priority_for_row_label(
            recovered_row_ref,
            metric_name,
            [],
        )
        return recovered_priority > existing_priority

    for table in _preferred_statement_tables(tables):
        if not _table_has_income_statement_source_rows(table):
            continue
        table_scale = _detect_scale_from_table(table)
        scale_for_table = table_scale if table_scale != "unknown" else str(scale or "unknown")
        period_binding = _bind_current_period_column(
            table,
            pass1_result.get("period_end"),
            period_basis=pass1_result.get("period_basis"),
        )
        for metric_name, (
            recovered_value,
            recovered_row_ref,
        ) in _recover_income_statement_metrics_from_table(
            table,
            scale_for_table,
        ).items():
            existing_is_weak_wrapper = _appendix_wrapper_source_row_is_weak(
                row_refs.get(metric_name)
            ) or _appendix_wrapper_source_row_is_weak(provenance.get(metric_name))
            existing_is_appendix_wrapper = _source_text_is_appendix_wrapper(
                row_refs.get(metric_name)
            ) or _source_text_is_appendix_wrapper(provenance.get(metric_name))
            existing_is_rejected = _existing_income_statement_metric_is_rejected(
                metric_name
            )
            existing_is_generic_np_attributable = (
                metric_name == "np_attributable"
                and _row_ref_is_owner_attributable_np(recovered_row_ref)
                and _np_attributable_source_is_generic_profit(
                    row_refs.get(metric_name),
                    provenance.get(metric_name),
                )
            )
            existing_scale_conflicts_with_preferred = (
                _existing_income_statement_metric_scale_conflicts(
                    metric_name,
                    scale_for_table,
                    table_scale,
                )
            )
            existing_has_lower_priority = (
                _existing_income_statement_metric_has_lower_priority(
                    metric_name,
                    recovered_row_ref,
                )
            )
            if metrics.get(metric_name) is not None and not (
                existing_is_weak_wrapper
                or existing_is_appendix_wrapper
                or existing_is_rejected
                or existing_is_generic_np_attributable
                or existing_scale_conflicts_with_preferred
                or existing_has_lower_priority
            ):
                continue
            metrics[metric_name] = recovered_value
            payload[metric_name] = recovered_value
            row_refs[metric_name] = recovered_row_ref
            page_tag = f"page_{getattr(table, 'page_number', '?')}"
            provenance[metric_name] = f"income_statement:{page_tag}:{recovered_row_ref}"
            if scale_for_table and scale_for_table != "unknown":
                metric_source_scales[metric_name] = scale_for_table
                metric_scale_sources[metric_name] = (
                    "table" if table_scale != "unknown" else "document"
                )
            source_cell = None
            if period_binding.get("status") == "BOUND":
                candidate_source_cell = _period_bound_source_cell(
                    table,
                    recovered_row_ref,
                    period_binding["column_index"],
                    scale_for_table,
                )
                if (
                    candidate_source_cell is not None
                    and candidate_source_cell.get("scaled_value") == recovered_value
                ):
                    candidate_source_cell["header_cell"] = period_binding["header_cell"]
                    candidate_source_cell["requested_period_end"] = period_binding[
                        "requested_period_end"
                    ]
                    source_cell = candidate_source_cell
            field_provenance[metric_name] = _build_field_provenance_entry(
                metric_name=metric_name,
                source="income_statement",
                page=getattr(table, "page_number", None),
                row_ref=recovered_row_ref,
                scale=scale_for_table,
                scale_source=metric_scale_sources.get(metric_name),
                pass1_result=pass1_result,
                source_cell=source_cell,
            )

    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources


def _sections_by_page(sections: list[dict] | None) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}
    for section in sections or []:
        try:
            page = int(section.get("page"))
        except (TypeError, ValueError):
            continue
        text = _normalise_fragmented_pdf_text(section.get("text"))
        if not text:
            continue
        pages.setdefault(page, []).append(text)
    return pages


def _statement_text_value_after_label(
    lines: list[str],
    index: int,
    scale: str,
    *,
    label_width: int = 1,
) -> float | None:
    row = [lines[index]] + lines[index + label_width : index + label_width + 6]
    return _parse_current_period_metric_cell(row, scale)


_STATEMENT_INLINE_NUMBER_RE = re.compile(r"\(?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?")


def _statement_text_inline_value(label: str, scale: str) -> float | None:
    parsed_values: list[tuple[float, bool]] = []
    for match in _STATEMENT_INLINE_NUMBER_RE.finditer(label):
        parsed = _parse_accounting_metric_number(match.group(0))
        if parsed is not None:
            parsed_values.append(parsed)
    if not parsed_values:
        return None

    raw_float, has_explicit_unit = parsed_values[0]
    if (
        len(parsed_values) >= 2
        and not has_explicit_unit
        and 0 < abs(raw_float) < 20
        and abs(parsed_values[1][0]) >= 100
    ):
        raw_float, has_explicit_unit = parsed_values[1]
    return (
        raw_float
        if has_explicit_unit
        else raw_float * SCALE_MULTIPLIERS.get(scale, 1)
    )


def _statement_text_label_without_inline_values(label: str) -> str:
    return _STATEMENT_INLINE_NUMBER_RE.sub("", label).strip()


def _combined_statement_text_label(lines: list[str], index: int) -> tuple[str, int]:
    label = lines[index]
    if index + 1 >= len(lines):
        return label, 1
    next_line = lines[index + 1]
    if _parse_accounting_metric_number(next_line) is not None:
        return label, 1
    compact = _normalize_filter_text(label)
    next_compact = _normalize_filter_text(next_line)
    if (
        compact.endswith("from")
        or compact.endswith("of")
        or (compact.startswith("profitloss") and next_compact)
    ):
        return f"{label} {next_line}", 2
    return label, 1


def _recover_income_statement_metrics_from_statement_text(
    lines: list[str],
    scale: str,
) -> dict[str, tuple[float, str]]:
    recovered: dict[str, tuple[int, float, str]] = {}
    previous_labels: list[str] = []
    for index, raw_line in enumerate(lines):
        label, label_width = _combined_statement_text_label(lines, index)
        compact = _normalize_filter_text(label)
        if not compact or _parse_accounting_metric_number(label) is not None:
            continue

        metric_name = _income_metric_for_row_label(label)
        if metric_name is None and (
            "profitlossafterincometaxfromcontinuingoperations" in compact
            or "profitlossforthehalfyearafterincometax" in compact
            or "profitforthehalfyearafterincometax" in compact
        ):
            metric_name = "np_attributable"
        if metric_name is None and "beforeincometax" in compact and "profit" in compact:
            metric_name = "ebit"

        if metric_name in {"revenue", "ebit", "np_attributable"}:
            value = _statement_text_value_after_label(
                lines,
                index,
                scale,
                label_width=label_width,
            )
            recovered_row_ref = label
            if value is None:
                value = _statement_text_inline_value(label, scale)
                if value is not None:
                    recovered_row_ref = _statement_text_label_without_inline_values(label)
            if value is not None:
                priority = _income_metric_priority_for_row_label(
                    label,
                    metric_name,
                    previous_labels,
                )
                existing = recovered.get(metric_name)
                if existing is None or priority > existing[0]:
                    recovered[metric_name] = (priority, value, recovered_row_ref)
        previous_labels.append(label)
    return {
        metric_name: (value, row_ref)
        for metric_name, (_priority, value, row_ref) in recovered.items()
    }


def _payload_ebit_source_is_rejected(payload: dict[str, Any]) -> bool:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    if metrics.get("ebit") is None:
        return False
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    compact = _normalize_filter_text(
        _combined_source_text(row_refs.get("ebit"), provenance.get("ebit"))
    )
    return any(blocker in compact for blocker, _source_label in _EBIT_LABEL_BLOCKERS)


_REVENUE_NARRATIVE_REJECT_MARKERS = (
    "futuresalesrevenue",
    "materialdeclineinfuturesalesrevenue",
    "managementexpects",
    "scheduledtoexpire",
)


def _payload_revenue_source_is_rejected(payload: dict[str, Any]) -> bool:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    if metrics.get("revenue") is None:
        return False
    compact = _normalize_filter_text(_payload_metric_source_text(payload, "revenue"))
    return "revenue" in compact and any(
        marker in compact for marker in _REVENUE_NARRATIVE_REJECT_MARKERS
    )


def _clear_payload_metric(payload: dict[str, Any], metric_name: str) -> None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )
    metrics[metric_name] = None
    payload[metric_name] = None
    row_refs.pop(metric_name, None)
    provenance.pop(metric_name, None)
    field_provenance.pop(metric_name, None)
    metric_source_scales.pop(metric_name, None)
    metric_scale_sources.pop(metric_name, None)
    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources


_APPENDIX_TABLE_ROWS = {
    "1.9": ("Net cash from / (used in) operating activities", "operating_cf"),
    "2.6": ("Net cash from / (used in) investing activities", "investing_cf"),
    "3.10": ("Net cash from / (used in) financing activities", "financing_cf"),
    "4.6": ("Cash and cash equivalents at end of period", "cash_end"),
    "5.5": (
        "Cash and cash equivalents at end of quarter (should equal item 4.6 above)",
        "cash_end",
    ),
}
_APPENDIX_TABLE_SCALE_CONFLICT = object()


def _trusted_appendix_cashflow_form(pass1_result: dict[str, Any]) -> str | None:
    classification = pass1_result.get("_asx_document_type_classification")
    contract = pass1_result.get("_asx_extraction_contract")
    routing = pass1_result.get("_asx_extraction_contract_routing")
    if not all(isinstance(item, dict) for item in (classification, contract, routing)):
        return None
    document_type = classification.get("document_type")
    if document_type not in {"appendix_4c", "appendix_5b"}:
        return None
    contract_id = f"asx_{document_type}_extraction_contract_v1"
    if (
        classification.get("abstain") is not False
        or contract.get("document_type") != document_type
        or contract.get("contract_id") != contract_id
        or contract.get("abstain") is not False
        or routing.get("contract_id") != contract_id
        or routing.get("allowed") is not True
        or routing.get("abstain") is not False
    ):
        return None
    return document_type.removeprefix("appendix_")


def _appendix_table_scale_markers(value: Any) -> set[str]:
    text = str(value or "")
    return {
        scale
        for pattern, scale in _SCALE_PATTERNS
        if _re.search(pattern, text, _re.IGNORECASE)
    }


def _appendix_table_has_trusted_cashflow_identity(
    table: Any, *, trusted_form: str
) -> bool:
    headers = list(getattr(table, "headers", None) or [])
    rows = list(getattr(table, "rows", None) or [])
    anchor = " ".join(
        [
            str(getattr(table, "caption", "") or ""),
            " ".join(str(cell) for cell in headers),
            " ".join(
                " ".join(str(cell) for cell in row)
                for row in rows[:4]
                if isinstance(row, (list, tuple))
            ),
        ]
    )
    explicit_forms = {
        match.lower()
        for match in re.findall(r"\bAppendix\s+(4C|5B)\b", anchor, re.IGNORECASE)
    }
    return (
        len(explicit_forms) <= 1
        and (not explicit_forms or explicit_forms == {trusted_form})
        and "consolidatedstatementofcashflows" in _normalize_filter_text(anchor)
    )


def _appendix_table_context(
    table: Any,
    *,
    trusted_form: str,
    document_scale: Any,
) -> tuple[int, str, str] | object | None:
    headers = list(getattr(table, "headers", None) or [])
    if not _appendix_table_has_trusted_cashflow_identity(
        table, trusted_form=trusted_form
    ):
        return None
    current_columns = [
        index
        for index, header in enumerate(headers)
        if re.search(r"\bcurrent\s+(?:quarter|period)\b", str(header), re.IGNORECASE)
        and not re.search(
            r"\b(?:previous|prior|comparative|year\s+to\s+date|ytd)\b",
            str(header),
            re.IGNORECASE,
        )
    ]
    if len(current_columns) != 1:
        return None
    current_column = current_columns[0]
    header_scales = _appendix_table_scale_markers(headers[current_column])
    caption_scales = _appendix_table_scale_markers(getattr(table, "caption", ""))
    if len(header_scales) > 1 or len(caption_scales) > 1:
        return _APPENDIX_TABLE_SCALE_CONFLICT
    header_scale = next(iter(header_scales), None)
    caption_scale = next(iter(caption_scales), None)
    if header_scale and caption_scale and header_scale != caption_scale:
        return _APPENDIX_TABLE_SCALE_CONFLICT
    if not header_scale and any(
        _appendix_table_scale_markers(header)
        for index, header in enumerate(headers)
        if index != current_column
    ):
        return None
    scale = header_scale or caption_scale or str(document_scale or "unknown").lower()
    if scale not in SCALE_MULTIPLIERS or scale == "unknown":
        return None
    return current_column, scale, "table" if header_scale or caption_scale else "document"


def _appendix_table_row(row: Sequence[Any]) -> tuple[str, str, str, bool] | None:
    if len(row) < 2:
        return None
    item = _normalise_appendix5b_section(row[0])
    expected = _APPENDIX_TABLE_ROWS.get(item)
    if expected is None:
        return None
    label = _normalise_fragmented_pdf_text(row[1])
    return item, label, expected[1], label == expected[0]


def _recover_structured_appendix_cashflow(
    tables: Any,
    *,
    trusted_form: str,
    document_scale: Any,
) -> tuple[dict[str, tuple[float, str, Any, str, str]], set[str]]:
    observations: dict[
        tuple[str, str], list[tuple[float, str, Any, str, str, tuple[int, Any, int]]]
    ] = {}
    ambiguous: set[str] = set()
    for table_index, table in enumerate(tables or []):
        recognized = {
            match[2]
            for row in getattr(table, "rows", None) or []
            if isinstance(row, (list, tuple))
            and (match := _appendix_table_row(row)) is not None
        }
        context = _appendix_table_context(
            table, trusted_form=trusted_form, document_scale=document_scale
        )
        if context is _APPENDIX_TABLE_SCALE_CONFLICT:
            ambiguous.update(recognized)
            continue
        if context is None:
            if _appendix_table_has_trusted_cashflow_identity(
                table, trusted_form=trusted_form
            ):
                ambiguous.update(recognized)
            continue
        current_column, scale, scale_source = context
        for row_index, row in enumerate(getattr(table, "rows", None) or []):
            if not isinstance(row, (list, tuple)):
                continue
            match = _appendix_table_row(row)
            if match is None:
                continue
            item, label, metric, label_is_valid = match
            if not label_is_valid:
                ambiguous.add(metric)
                continue
            if item == "5.5" and trusted_form != "4c":
                ambiguous.add(metric)
                continue
            if current_column >= len(row):
                ambiguous.add(metric)
                continue
            parsed = _parse_accounting_metric_number(row[current_column])
            if parsed is None:
                ambiguous.add(metric)
                continue
            raw, explicit_unit = parsed
            value = raw if explicit_unit else raw * SCALE_MULTIPLIERS[scale]
            kind = "check" if item == "5.5" else "primary"
            observations.setdefault((metric, kind), []).append(
                (
                    value,
                    f"{item} {label}",
                    getattr(table, "page_number", None),
                    scale,
                    scale_source,
                    (table_index, getattr(table, "page_number", None), row_index),
                )
            )
    metrics = {metric for metric, _kind in observations}
    scales = {item[3] for values in observations.values() for item in values}
    scale_sources = {item[4] for values in observations.values() for item in values}
    if len(scales) > 1 or len(scale_sources) > 1:
        return {}, ambiguous | metrics
    recovered: dict[str, tuple[float, str, Any, str, str]] = {}
    for metric in metrics:
        if metric in ambiguous:
            continue
        primary = observations.get((metric, "primary"), [])
        checks = observations.get((metric, "check"), [])
        if (
            len({item[0] for item in primary}) > 1
            or len({item[0] for item in checks}) > 1
            or len({item[5] for item in primary}) > 1
            or len({item[5] for item in checks}) > 1
        ):
            ambiguous.add(metric)
            continue
        if (
            metric == "cash_end"
            and primary
            and checks
            and primary[0][0] != checks[0][0]
        ):
            ambiguous.add(metric)
            continue
        if primary:
            recovered[metric] = primary[0][:5]
        elif trusted_form == "4c" and len(checks) == 1:
            recovered[metric] = checks[0][:5]
    return recovered, ambiguous


def _apply_structured_appendix_cashflow_payload(
    payload: dict[str, Any], tables: Any, *, pass1_result: dict[str, Any]
) -> None:
    trusted_form = _trusted_appendix_cashflow_form(pass1_result)
    if trusted_form is None:
        return
    recovered, ambiguous = _recover_structured_appendix_cashflow(
        tables,
        trusted_form=trusted_form,
        document_scale=payload.get("scale") or pass1_result.get("scale"),
    )
    for metric in ambiguous:
        _clear_payload_metric(payload, metric)
    for metric, (value, row_ref, page, scale, scale_source) in recovered.items():
        payload.setdefault("metrics", {})[metric] = value
        payload[metric] = value
        payload.setdefault("row_refs", {})[metric] = row_ref
        page_tag = page if page is not None else "?"
        payload.setdefault("provenance", {})[metric] = f"source_table:page_{page_tag}:{row_ref}"
        payload.setdefault("metric_source_scales", {})[metric] = scale
        payload.setdefault("metric_scale_sources", {})[metric] = scale_source
        payload.setdefault("field_provenance", {})[metric] = _build_field_provenance_entry(
            metric_name=metric,
            source="source_table",
            page=page,
            row_ref=row_ref,
            scale=scale,
            scale_source=scale_source,
            pass1_result=pass1_result,
        )


def _read_pdf_pages_for_statement_text(source_path: Any) -> list[tuple[int, list[str]]]:
    path = Path(str(source_path or ""))
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return []
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.debug("statement pdf text unavailable: path=%s", path)
        return []
    if result.returncode != 0:
        logger.debug(
            "statement pdf text unavailable: path=%s returncode=%s",
            path,
            result.returncode,
        )
        return []

    pages: list[tuple[int, list[str]]] = []
    for page_index, page_text in enumerate(result.stdout.split("\f"), start=1):
        lines = [
            line
            for line in (
                _normalise_fragmented_pdf_text(raw_line)
                for raw_line in page_text.splitlines()
            )
            if line
        ]
        if lines:
            pages.append((page_index, lines))
    return pages


def _apply_rejected_ebit_from_pdf_statement_text(
    payload: dict[str, Any],
    source_path: Any,
    *,
    scale: Any,
    pass1_result: dict,
) -> None:
    if not _payload_ebit_source_is_rejected(payload):
        return

    scale_for_text = str(scale or "unknown")
    for page, lines in _statement_text_pages(
        [
            {"page": page, "text": line}
            for page, page_lines in _read_pdf_pages_for_statement_text(source_path)
            for line in page_lines
        ],
        (
            "consolidatedincomestatement",
            "consolidatedstatementofcomprehensiveincome",
            "consolidatedstatementofprofitorloss",
        ),
    ):
        recovered = _recover_income_statement_metrics_from_statement_text(
            lines,
            scale_for_text,
        )
        value_and_ref = recovered.get("ebit")
        if value_and_ref is None:
            continue
        value, row_ref = value_and_ref
        if any(
            blocker in _normalize_filter_text(row_ref)
            for blocker, _source_label in _EBIT_LABEL_BLOCKERS
        ):
            continue

        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
        row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
        provenance = (
            payload.get("provenance")
            if isinstance(payload.get("provenance"), dict)
            else {}
        )
        field_provenance = (
            payload.get("field_provenance")
            if isinstance(payload.get("field_provenance"), dict)
            else {}
        )
        metric_source_scales = (
            payload.get("metric_source_scales")
            if isinstance(payload.get("metric_source_scales"), dict)
            else {}
        )
        metric_scale_sources = (
            payload.get("metric_scale_sources")
            if isinstance(payload.get("metric_scale_sources"), dict)
            else {}
        )

        metrics["ebit"] = value
        payload["ebit"] = value
        row_refs["ebit"] = row_ref
        provenance["ebit"] = f"income_statement:page_{page}:{row_ref}"
        if scale_for_text and scale_for_text != "unknown":
            metric_source_scales["ebit"] = scale_for_text
            metric_scale_sources["ebit"] = "source_text"
        field_provenance["ebit"] = _build_field_provenance_entry(
            metric_name="ebit",
            source="income_statement",
            page=page,
            row_ref=row_ref,
            scale=scale_for_text,
            scale_source="source_text",
            pass1_result=pass1_result,
        )

        payload["metrics"] = metrics
        payload["row_refs"] = row_refs
        payload["provenance"] = provenance
        payload["field_provenance"] = field_provenance
        payload["metric_source_scales"] = metric_source_scales
        payload["metric_scale_sources"] = metric_scale_sources
        logger.info(
            "Recovered rejected EBIT from source PDF statement text page %s row=%r",
            page,
            row_ref,
        )
        return


_APPENDIX5B_SOURCE_TEXT_LABELS = {
    "1.9": "Net cash from / (used in) operating activities",
    "2.6": "Net cash from / (used in) investing activities",
    "3.10": "Net cash from / (used in) financing activities",
    "4.6": "Cash and cash equivalents at end of period",
}


def _appendix5b_source_text_page_is_candidate(lines: Sequence[str]) -> bool:
    compact = _normalize_filter_text(" ".join(lines[:40]))
    return (
        "appendix5b" in compact
        and "quarterlycashflowreport" in compact
        and "consolidatedstatementofcashflows" in compact
    )


def _appendix5b_source_text_value_after_section(
    lines: Sequence[str],
    index: int,
    section: str,
    scale: str,
) -> float | None:
    section_re = re.compile(rf"^\s*{re.escape(section)}\b")
    for line in lines[index : index + 5]:
        text = section_re.sub("", line, count=1)
        for match in _STATEMENT_INLINE_NUMBER_RE.finditer(text):
            parsed = _parse_accounting_metric_number(match.group(0))
            if parsed is None:
                continue
            raw_float, has_explicit_unit = parsed
            return (
                raw_float
                if has_explicit_unit
                else raw_float * SCALE_MULTIPLIERS.get(scale, 1)
            )
    return None


def _recover_appendix5b_metrics_from_source_text_pages(
    pages: Sequence[tuple[int, list[str]]],
    scale: str,
) -> dict[str, tuple[float, str, int]]:
    recovered: dict[str, tuple[float, str, int]] = {}
    for page, lines in pages:
        if not _appendix5b_source_text_page_is_candidate(lines):
            continue
        for index, line in enumerate(lines):
            for section, metric_name in _APPENDIX5B_SECTION_TOTALS.items():
                if section not in _APPENDIX5B_SOURCE_TEXT_LABELS:
                    continue
                if metric_name in recovered:
                    continue
                if not re.match(rf"^\s*{re.escape(section)}\b", line):
                    continue
                value = _appendix5b_source_text_value_after_section(
                    lines,
                    index,
                    section,
                    scale,
                )
                if value is None:
                    continue
                recovered[metric_name] = (
                    value,
                    _APPENDIX5B_SOURCE_TEXT_LABELS[section],
                    page,
                )
    return recovered


def _apply_appendix5b_source_text_payload(
    payload: dict[str, Any],
    source_path: Any,
    *,
    scale: Any,
    pass1_result: dict,
) -> None:
    scale_for_text = str(scale or "unknown")
    if scale_for_text == "unknown":
        return

    recovered = _recover_appendix5b_metrics_from_source_text_pages(
        _read_pdf_pages_for_statement_text(source_path),
        scale_for_text,
    )
    if not recovered:
        return

    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )

    for metric_name, (value, row_ref, page) in recovered.items():
        current_row_ref = row_refs.get(metric_name)
        if (
            metrics.get(metric_name) is not None
            and metric_name != "cash_end"
            and current_row_ref
        ):
            continue
        if (
            metric_name == "cash_end"
            and metrics.get(metric_name) is not None
            and not _cashflow_cash_end_row_is_weak(current_row_ref)
        ):
            continue

        metrics[metric_name] = value
        payload[metric_name] = value
        row_refs[metric_name] = row_ref
        provenance[metric_name] = f"cashflow_statement:page_{page}:{row_ref}"
        metric_source_scales[metric_name] = scale_for_text
        metric_scale_sources[metric_name] = "source_text"
        field_provenance[metric_name] = _build_field_provenance_entry(
            metric_name=metric_name,
            source="cashflow_statement",
            page=page,
            row_ref=row_ref,
            scale=scale_for_text,
            scale_source="source_text",
            pass1_result=pass1_result,
        )

    appendix5b_core_metrics = (
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "cash_end",
    )
    if all(metrics.get(metric_name) is not None for metric_name in appendix5b_core_metrics):
        payload["confidence_metrics"] = max(
            _coerce_confidence(payload.get("confidence_metrics", 0.0)),
            0.85,
        )

    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources


def _cashflow_statement_text_has_bank_capex_context(lines: list[str]) -> bool:
    compact = _normalize_filter_text(" ".join(lines))
    return any(
        marker in compact
        for marker in (*_CASHFLOW_BANK_CAPEX_LABELS, "investmentsecurities", "securitiesassets")
    )


def _cashflow_metric_for_statement_text_label(
    label: str,
    *,
    bank_cashflow_context: bool = False,
) -> str | None:
    compact = _normalize_filter_text(label)
    if "netoperatingcashflowsprovidedbyoperatingactivities" in compact:
        return "operating_cf"
    if "netcash" in compact and "operatingactivities" in compact:
        return "operating_cf"
    if "netcash" in compact and "investingactivities" in compact:
        return "investing_cf"
    if "netcash" in compact and "financingactivities" in compact:
        return "financing_cf"
    if _cashflow_row_has_strong_cash_end_label([label]):
        return "cash_end"
    if _cashflow_row_has_strong_capex_label(
        [label],
        bank_cashflow_context=bank_cashflow_context,
    ):
        return "capex"
    return None


def _recover_cashflow_metrics_from_statement_text(
    lines: list[str],
    scale: str,
) -> dict[str, tuple[float, str]]:
    recovered: dict[str, tuple[float, str]] = {}
    bank_cashflow_context = _cashflow_statement_text_has_bank_capex_context(lines)
    for index, label in enumerate(lines):
        metric_name = _cashflow_metric_for_statement_text_label(
            label,
            bank_cashflow_context=bank_cashflow_context,
        )
        if metric_name is None:
            continue
        row = [label] + lines[index + 1 : index + 7]
        if metric_name == "capex":
            value = _statement_text_inline_value(label, scale)
            if value is None:
                value = _parse_cashflow_capex_row_amount(row, scale)
        else:
            value = _parse_current_period_metric_cell(row, scale)
        if value is None:
            continue
        row_ref = (
            _statement_text_label_without_inline_values(label)
            if metric_name == "capex"
            else label
        )
        recovered[metric_name] = (value, row_ref)
    return recovered


def _statement_text_pages(
    sections: list[dict] | None,
    markers: tuple[str, ...],
) -> list[tuple[int, list[str]]]:
    pages = _sections_by_page(sections)
    selected: list[tuple[int, list[str]]] = []
    for page, lines in pages.items():
        compact = _normalize_filter_text(" ".join(lines[:40]))
        compact_page = _normalize_filter_text(" ".join(lines))
        if (
            any(marker in compact for marker in markers)
            and "resultsforannouncement" not in compact
            and not _is_financial_report_contents_index_text(compact_page)
        ):
            selected.append((page, lines))
    return sorted(selected, key=lambda item: item[0])


def _apply_preferred_statement_text_source_payload(
    payload: dict[str, Any],
    sections: list[dict] | None,
    *,
    scale: Any,
    pass1_result: dict,
) -> None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )
    scale_for_text = str(scale or "unknown")

    def _existing_statement_text_metric_is_rejected(metric_name: str) -> bool:
        if metric_name == "ebit":
            compact = _normalize_filter_text(
                _combined_source_text(
                    row_refs.get(metric_name), provenance.get(metric_name)
                )
            )
            return any(
                blocker in compact for blocker, _source_label in _EBIT_LABEL_BLOCKERS
            )
        if metric_name == "revenue":
            return _payload_revenue_source_is_rejected(payload)
        return False

    for page, lines in _statement_text_pages(
        sections,
        (
            "consolidatedincomestatement",
            "consolidatedstatementofcomprehensiveincome",
            "consolidatedstatementofprofitorloss",
        ),
    ):
        recovered = _recover_income_statement_metrics_from_statement_text(
            lines,
            scale_for_text,
        )
        if not recovered:
            continue
        for metric_name, (value, row_ref) in recovered.items():
            existing_is_appendix_wrapper = _source_text_is_appendix_wrapper(
                row_refs.get(metric_name)
            ) or _source_text_is_appendix_wrapper(provenance.get(metric_name))
            existing_is_rejected = _existing_statement_text_metric_is_rejected(
                metric_name
            )
            if metrics.get(metric_name) is not None and not (
                existing_is_appendix_wrapper or existing_is_rejected
            ):
                continue
            metrics[metric_name] = value
            payload[metric_name] = value
            row_refs[metric_name] = row_ref
            provenance[metric_name] = f"income_statement:page_{page}:{row_ref}"
            if scale_for_text and scale_for_text != "unknown":
                metric_source_scales[metric_name] = scale_for_text
                metric_scale_sources[metric_name] = "source_text"
            field_provenance[metric_name] = _build_field_provenance_entry(
                metric_name=metric_name,
                source="income_statement",
                page=page,
                row_ref=row_ref,
                scale=scale_for_text,
                scale_source="source_text",
                pass1_result=pass1_result,
            )
        break

    if _payload_revenue_source_is_rejected(payload):
        _clear_payload_metric(payload, "revenue")

    for page, lines in _statement_text_pages(
        sections,
        ("consolidatedstatementofcashflows", "statementofcashflows"),
    ):
        bank_cashflow_context = _cashflow_statement_text_has_bank_capex_context(lines)
        recovered = _recover_cashflow_metrics_from_statement_text(lines, scale_for_text)
        if not recovered:
            continue
        for metric_name, (value, row_ref) in recovered.items():
            current_row = row_refs.get(metric_name)
            should_replace_capex = (
                metric_name == "capex"
                and _cashflow_row_has_strong_capex_label(
                    [row_ref],
                    bank_cashflow_context=bank_cashflow_context,
                )
                and not _cashflow_row_has_strong_capex_label(
                    [current_row],
                    bank_cashflow_context=bank_cashflow_context,
                )
            )
            if (
                metrics.get(metric_name) is not None
                and metric_name != "cash_end"
                and not should_replace_capex
            ):
                continue
            if (
                metric_name == "cash_end"
                and metrics.get(metric_name) is not None
                and not _cashflow_cash_end_row_is_weak(current_row)
            ):
                continue
            metrics[metric_name] = value
            payload[metric_name] = value
            row_refs[metric_name] = row_ref
            provenance[metric_name] = f"cashflow_statement:page_{page}:{row_ref}"
            if scale_for_text and scale_for_text != "unknown":
                metric_source_scales[metric_name] = scale_for_text
                metric_scale_sources[metric_name] = "source_text"
            field_provenance[metric_name] = _build_field_provenance_entry(
                metric_name=metric_name,
                source="cashflow_statement",
                page=page,
                row_ref=row_ref,
                scale=scale_for_text,
                scale_source="source_text",
                pass1_result=pass1_result,
            )
        break

    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources


def _apply_bank_cashflow_capex_source_text_payload(
    payload: dict[str, Any],
    source_path: Any,
    *,
    scale: Any,
    pass1_result: dict,
) -> None:
    scale_for_text = str(scale or "unknown")
    if scale_for_text == "unknown":
        return

    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )

    for page, lines in _read_pdf_pages_for_statement_text(source_path):
        compact_page = _normalize_filter_text(" ".join(lines))
        if (
            "cashflowsfrominvestingactivities" not in compact_page
            and "statementofcashflows" not in compact_page
        ):
            continue
        if not _cashflow_statement_text_has_bank_capex_context(lines):
            continue
        recovered = _recover_cashflow_metrics_from_statement_text(lines, scale_for_text)
        if "capex" not in recovered:
            continue
        current_row = row_refs.get("capex")
        if metrics.get("capex") is not None and not _cashflow_capex_row_is_weak(
            current_row
        ):
            return

        value, row_ref = recovered["capex"]
        metrics["capex"] = value
        payload["capex"] = value
        row_refs["capex"] = row_ref
        provenance["capex"] = f"cashflow_statement:page_{page}:{row_ref}"
        metric_source_scales["capex"] = scale_for_text
        metric_scale_sources["capex"] = "source_text"
        field_provenance["capex"] = _build_field_provenance_entry(
            metric_name="capex",
            source="cashflow_statement",
            page=page,
            row_ref=row_ref,
            scale=scale_for_text,
            scale_source="source_text",
            pass1_result=pass1_result,
        )
        break

    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources


def _apply_preferred_shares_source_payload(
    payload: dict[str, Any],
    tables: Any,
    *,
    pass1_result: dict,
    capture_benchmark_source_cell: bool = False,
) -> None:
    previous_table = None
    for table in tables or []:
        recovered = _recover_preferred_share_observation_from_table(
            table,
            period_end=pass1_result.get("period_end"),
        )
        if recovered is None:
            recovered = _recover_preferred_share_observation_from_split_header_table(
                previous_table,
                table,
                period_end=pass1_result.get("period_end"),
            )
        if recovered is None:
            previous_table = table
            continue
        recovered_value = recovered.value
        recovered_row_ref = recovered.row_ref
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
        row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
        provenance = (
            payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
        )
        field_provenance = (
            payload.get("field_provenance")
            if isinstance(payload.get("field_provenance"), dict)
            else {}
        )
        source_cell = (
            _period_bound_share_source_cell(
                table,
                recovered,
                period_end=pass1_result.get("period_end"),
            )
            if capture_benchmark_source_cell
            else None
        )
        metrics["shares_outstanding"] = recovered_value
        payload["shares_outstanding"] = recovered_value
        row_refs["shares_outstanding"] = recovered_row_ref
        page_tag = f"page_{getattr(table, 'page_number', '?')}"
        provenance["shares_outstanding"] = f"share_capital:{page_tag}:{recovered_row_ref}"
        field_provenance["shares_outstanding"] = _build_field_provenance_entry(
            metric_name="shares_outstanding",
            source="share_capital",
            page=getattr(table, "page_number", None),
            row_ref=recovered_row_ref,
            scale=recovered.source_unit if capture_benchmark_source_cell else "units",
            scale_source="source_table",
            pass1_result=pass1_result,
            source_cell=source_cell,
        )
        payload["metrics"] = metrics
        payload["row_refs"] = row_refs
        payload["provenance"] = provenance
        payload["field_provenance"] = field_provenance
        if capture_benchmark_source_cell:
            metric_source_scales = (
                payload.get("metric_source_scales")
                if isinstance(payload.get("metric_source_scales"), dict)
                else {}
            )
            metric_scale_sources = (
                payload.get("metric_scale_sources")
                if isinstance(payload.get("metric_scale_sources"), dict)
                else {}
            )
            metric_source_scales["shares_outstanding"] = recovered.source_unit
            metric_scale_sources["shares_outstanding"] = "source_table"
            payload["metric_source_scales"] = metric_source_scales
            payload["metric_scale_sources"] = metric_scale_sources
        return


def _apply_preferred_cash_end_source_payload(
    payload: dict[str, Any],
    tables: Any,
    *,
    scale: Any,
    pass1_result: dict,
) -> None:
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    if (
        payload.get("cash_end") is not None
        and not _cashflow_cash_end_row_is_weak(row_refs.get("cash_end"))
    ):
        return

    recovered = _recover_preferred_cashflow_cash_end_from_tables(tables, scale)
    if recovered is None:
        return

    value, row_ref, page, metric_scale, scale_source = recovered
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    field_provenance = (
        payload.get("field_provenance")
        if isinstance(payload.get("field_provenance"), dict)
        else {}
    )
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )

    metrics["cash_end"] = value
    payload["cash_end"] = value
    row_refs["cash_end"] = row_ref
    page_tag = f"page_{page}" if page is not None else "page_?"
    provenance["cash_end"] = f"source_table:{page_tag}:{row_ref}"
    if metric_scale and metric_scale != "unknown":
        metric_source_scales["cash_end"] = metric_scale
        metric_scale_sources["cash_end"] = scale_source
    field_provenance["cash_end"] = _build_field_provenance_entry(
        metric_name="cash_end",
        source="source_table",
        page=page,
        row_ref=row_ref,
        scale=metric_scale,
        scale_source=scale_source,
        pass1_result=pass1_result,
    )

    payload["metrics"] = metrics
    payload["row_refs"] = row_refs
    payload["provenance"] = provenance
    payload["field_provenance"] = field_provenance
    payload["metric_source_scales"] = metric_source_scales
    payload["metric_scale_sources"] = metric_scale_sources


def _payload_metric_source_text(payload: dict, metric_name: str) -> str:
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    return _combined_source_text(
        row_refs.get(metric_name),
        provenance.get(metric_name),
    )


def _flatten_payload_text(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        fragments: list[str] = []
        for key, item in value.items():
            fragments.extend(_flatten_payload_text(key))
            fragments.extend(_flatten_payload_text(item))
        return fragments
    if isinstance(value, (list, tuple, set)):
        fragments: list[str] = []
        for item in value:
            fragments.extend(_flatten_payload_text(item))
        return fragments
    text = str(value).strip()
    return [text] if text else []


def _combined_payload_text(payload: dict, *keys: str) -> str:
    fragments: list[str] = []
    for key in keys:
        fragments.extend(_flatten_payload_text(payload.get(key)))
    return " ".join(fragments)


def _is_appendix_wrapper_document(payload: dict) -> bool:
    source_bound = payload.get("source_bound")
    if not isinstance(source_bound, dict):
        source_bound = {}
    source_classification = payload.get("source_document_classification")
    if not isinstance(source_classification, dict):
        source_classification = {}

    fragments = _flatten_payload_text(
        [
            payload.get("document_subtype"),
            payload.get("doc_subtype"),
            payload.get("source_doc_subtype"),
            payload.get("document_title"),
            payload.get("title"),
            payload.get("source_title"),
            payload.get("announcement_title"),
            source_bound.get("document_subtype"),
            source_bound.get("document_title"),
            source_classification.get("reason"),
            source_classification.get("evidence"),
        ]
    )
    combined = _normalize_filter_text(" ".join(fragments))
    if not combined:
        return False
    return any(marker in combined for marker in _APPENDIX_WRAPPER_DOCUMENT_MARKERS)


def _wrapper_disclosure_evidence_present(payload: dict) -> bool:
    combined = _normalize_filter_text(
        _combined_payload_text(
            payload,
            "wrapper_disclosures",
            "disclosure_evidence",
            "source_evidence",
            "source_notes",
        )
    )
    if not combined:
        return False
    return all(
        any(marker in combined for marker in marker_group)
        for marker_group in _APPENDIX_WRAPPER_DISCLOSURE_MARKER_GROUPS
    )


def _wrapper_source_bound_ready(payload: dict) -> bool:
    source_bound = payload.get("source_bound")
    if not isinstance(source_bound, dict):
        return False

    required_fields = ("period_end", "period_type", "scale", "currency")
    for required_field in required_fields:
        value = source_bound.get(required_field)
        if value in (None, ""):
            return False
        if required_field == "scale" and str(value).strip().lower() == "unknown":
            return False

    for required_field in ("period_end", "period_type", "scale"):
        payload_value = payload.get(required_field)
        source_value = source_bound.get(required_field)
        if payload_value in (None, "") or source_value in (None, ""):
            continue
        if str(payload_value).strip().lower() != str(source_value).strip().lower():
            return False

    payload_currency = _normalize_currency_code(payload.get("currency"))
    source_currency = _normalize_currency_code(source_bound.get("currency"))
    return payload_currency == source_currency


def _appendix_wrapper_minimum_override(
    payload: dict,
    canonical_metrics: dict[str, Any],
) -> tuple[bool, str | None]:
    if not _is_appendix_wrapper_document(payload):
        return False, None

    non_null_names = {
        name for name, value in canonical_metrics.items() if value is not None
    }
    if len(non_null_names) != 2:
        return False, None
    if non_null_names != _APPENDIX_WRAPPER_REQUIRED_METRICS:
        return False, "validation_gate:wrapper_missing_required_canonical_metrics"
    if not _wrapper_source_bound_ready(payload):
        return False, "validation_gate:wrapper_missing_source_bound_context"
    if not _wrapper_disclosure_evidence_present(payload):
        return False, "validation_gate:wrapper_missing_disclosure_evidence"
    return True, None


def _metric_label_mismatch(payload: dict) -> tuple[str, str] | None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    if metrics.get("ebit") is None:
        return None
    evidence = _normalise_evidence_row_ref(_payload_metric_source_text(payload, "ebit"))
    if not evidence:
        return None
    compact = evidence.replace(",", "")
    for blocker, source_label in _EBIT_LABEL_BLOCKERS:
        if blocker in compact:
            return "ebit", source_label
    return None


def _explicit_unit_values_from_text(text: str) -> list[float]:
    values: list[float] = []
    for match in _EXPLICIT_SOURCE_UNIT_VALUE_RE.finditer(text or ""):
        raw_value = match.group(1).replace(",", "")
        unit = match.group(2).lower()
        multiplier = _SOURCE_UNIT_MULTIPLIERS.get(unit)
        if multiplier is None:
            continue
        try:
            values.append(abs(float(raw_value)) * multiplier)
        except (TypeError, ValueError):
            continue
    return values


def _within_relative_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    if expected == 0:
        return abs(actual) <= tolerance
    return abs(actual - expected) / abs(expected) <= tolerance


def _source_unit_value_mismatch(payload: dict) -> tuple[str, float, float] | None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    for metric_name, actual_raw in metrics.items():
        if actual_raw is None:
            continue
        try:
            actual = abs(float(actual_raw))
        except (TypeError, ValueError):
            continue
        source_values = _explicit_unit_values_from_text(
            _payload_metric_source_text(payload, metric_name)
        )
        source_values = [value for value in source_values if value > 0]
        if not source_values:
            continue
        if any(
            _within_relative_tolerance(actual, expected, 0.05)
            for expected in source_values
        ):
            continue
        for expected in source_values:
            ratio = max(actual / expected, expected / actual) if actual else float("inf")
            if ratio >= 100:
                return metric_name, actual, expected
    return None


def _source_period_type_candidates(payload: dict) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    source_period_type = str(payload.get("source_period_type") or "").strip()
    reason = ""
    evidence = payload.get("source_period_evidence")
    if isinstance(evidence, dict):
        reason = str(evidence.get("reason") or "").strip()
    if source_period_type in {"A", "H", "Q"}:
        candidates.append((source_period_type, reason or "explicit_source_period"))

    period_end_evidence = payload.get("source_period_end_evidence")
    if isinstance(period_end_evidence, dict):
        period_end_type = str(period_end_evidence.get("period_type") or "").strip()
        period_end_reason = str(period_end_evidence.get("reason") or "").strip()
        if period_end_type in {"A", "H", "Q"}:
            candidate = (
                period_end_type,
                period_end_reason or "explicit_source_period_end",
            )
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _period_source_mismatch(payload: dict) -> tuple[str, str, str] | None:
    period_type = str(payload.get("period_type") or "").strip()
    if period_type not in {"A", "H", "Q"}:
        return None
    for source_period_type, reason in _source_period_type_candidates(payload):
        if source_period_type != period_type:
            return period_type, source_period_type, reason
    return None


def _period_end_source_mismatch(payload: dict) -> tuple[str, str, str] | None:
    evidence = payload.get("source_period_end_evidence")
    if not isinstance(evidence, dict):
        return None
    source_period_end = str(evidence.get("period_end") or "").strip()
    payload_period_end = str(payload.get("period_end") or "").strip()
    if not source_period_end or not payload_period_end:
        return None
    source_date = parse_period_end(source_period_end)
    payload_date = parse_period_end(payload_period_end)
    if source_date is None or payload_date is None:
        return None
    if source_date == payload_date:
        return None
    reason = str(evidence.get("reason") or "").strip() or "explicit_source_period_end"
    return payload_date.isoformat(), source_date.isoformat(), reason


def _payload_source_titles(payload: dict) -> list[str]:
    titles: list[str] = []
    for key in ("document_title", "announcement_title", "title"):
        value = payload.get(key)
        if value:
            titles.append(str(value))
    source_bound = payload.get("source_bound")
    if isinstance(source_bound, dict):
        for key in ("document_title", "announcement_title", "title"):
            value = source_bound.get(key)
            if value:
                titles.append(str(value))
    deduped: list[str] = []
    for title in titles:
        if title not in deduped:
            deduped.append(title)
    return deduped


def _leading_announcement_date_from_title(title: str) -> date | None:
    basename = title.rsplit("/", 1)[-1]
    match = _LEADING_ANNOUNCEMENT_DATE_RE.search(basename)
    if not match:
        return None
    return parse_period_end(match.group("date"))


def _has_half_year_title_hint(payload: dict, titles: list[str]) -> bool:
    source_bound = payload.get("source_bound")
    if isinstance(source_bound, dict):
        subtype = str(source_bound.get("document_subtype") or "").lower()
        if subtype.replace("_", "").replace("-", "") in {"appendix4d", "4d"}:
            return True
    for title in titles:
        normalized = re.sub(r"[_\-]+", " ", title)
        if _HALF_YEAR_TITLE_HINT_RE.search(normalized):
            return True
    return False


def _has_annual_title_hint(title: str) -> bool:
    normalized = re.sub(r"[_\-]+", " ", title)
    return bool(_ANNUAL_TITLE_HINT_RE.search(normalized))


def _bind_explicit_source_period_end_over_announcement_date(
    pass1_result: dict,
    source_period_end_evidence: dict,
    title: Any,
) -> bool:
    """
    Replace an announcement-date period_end only with exact source text.

    This is the narrow positive counterpart to
    `_announcement_date_period_end_mismatch`: title dates still fail closed unless
    an explicit same-document period-end phrase is present in parsed source text.
    """

    report_type = str(
        pass1_result.get("report_type") or pass1_result.get("period_type") or ""
    ).strip()
    if report_type not in {"A", "H"}:
        return False
    if source_period_end_evidence.get("period_type") != report_type:
        return False
    evidence_reason = str(source_period_end_evidence.get("reason") or "")
    allowed_reasons = _SAME_DOCUMENT_PERIOD_END_REASONS_BY_TYPE.get(
        report_type, frozenset()
    )
    if evidence_reason not in allowed_reasons:
        return False
    if not _has_source_text_period_end_hit(
        source_period_end_evidence,
        reason=evidence_reason,
    ):
        return False

    current_period_end = parse_period_end(str(pass1_result.get("period_end") or ""))
    source_period_end = parse_period_end(
        str(source_period_end_evidence.get("period_end") or "")
    )
    if current_period_end is None or source_period_end is None:
        return False
    if current_period_end == source_period_end:
        return False

    title_text = str(title or "")
    if report_type == "H" and not _has_half_year_title_hint({}, [title_text]):
        return False
    if report_type == "A" and not _has_annual_title_hint(title_text):
        return False
    title_date = _leading_announcement_date_from_title(title_text)
    if title_date is None or title_date != current_period_end:
        return False

    pass1_result["period_end"] = source_period_end.isoformat()
    period_label = "annual" if report_type == "A" else "half_year"
    pass1_result["_source_period_end_binding"] = {
        "reason": (
            f"explicit_source_{period_label}_period_end_over_announcement_title_date"
        ),
        "from_period_end": current_period_end.isoformat(),
        "to_period_end": source_period_end.isoformat(),
        "source_period_end_reason": source_period_end_evidence.get("reason"),
    }
    return True


_COMPANION_PERIOD_SOURCE_ROLE_PRIORITY = {
    "appendix4d": 0,
    "half_year_financial_report": 1,
    "results_announcement": 2,
}


def _source_identity_from_path(source_path: Any) -> dict[str, str]:
    path_text = str(source_path or "")
    parts = [part for part in path_text.split("/") if part]
    ticker = ""
    category = ""
    try:
        docs_index = parts.index("docs")
        ticker = parts[docs_index + 1] if len(parts) > docs_index + 1 else ""
        category = parts[docs_index + 2] if len(parts) > docs_index + 2 else ""
    except ValueError:
        pass
    basename = os.path.basename(path_text)
    date_match = _LEADING_ANNOUNCEMENT_DATE_RE.search(basename)
    return {
        "path": path_text,
        "basename": basename,
        "ticker": ticker.upper(),
        "category": category,
        "announcement_date": date_match.group("date") if date_match else "",
    }


def _companion_source_role(source_path: Any, title: Any = "") -> str:
    text = f"{source_path or ''} {title or ''}".lower()
    compact = re.sub(r"[^a-z0-9]+", "", text)
    if "appendix4d" in compact:
        return "appendix4d"
    if "halfyear" in compact and (
        "financialreport" in compact or "financialstatements" in compact
    ):
        return "half_year_financial_report"
    if "resultsannouncement" in compact or "announcement" in compact:
        return "results_announcement"
    return "companion"


def _is_same_day_same_ticker_companion(
    target_source_path: Any, companion_source_path: Any
) -> bool:
    target = _source_identity_from_path(target_source_path)
    companion = _source_identity_from_path(companion_source_path)
    if not target["path"] or not companion["path"]:
        return False
    if os.path.abspath(target["path"]) == os.path.abspath(companion["path"]):
        return False
    if not target["ticker"] or target["ticker"] != companion["ticker"]:
        return False
    if not target["announcement_date"] or (
        target["announcement_date"] != companion["announcement_date"]
    ):
        return False
    if companion["category"] and companion["category"] != "financial_performance":
        return False
    if target["category"] and companion["category"]:
        return target["category"] == companion["category"]
    return True


def _read_pdf_text_for_companion_period_source(source_path: Any) -> str:
    path = Path(str(source_path or ""))
    if not path.is_file() or path.suffix.lower() != ".pdf":
        logger.debug(
            "companion period source text unavailable: path=%s reason=not_a_pdf_file",
            path,
        )
        return ""
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "4", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.debug(
            "companion period source text unavailable: path=%s reason=pdftotext_unavailable_or_timeout",
            path,
        )
        return ""
    if result.returncode != 0:
        logger.debug(
            "companion period source text unavailable: path=%s reason=pdftotext_failed returncode=%s",
            path,
            result.returncode,
        )
        return ""
    return result.stdout[:12000]


def _discover_same_day_companion_period_sources(
    target_source_path: Any,
) -> list[dict[str, Any]]:
    target_path = Path(str(target_source_path or ""))
    if not target_path.parent.is_dir():
        return []

    companions: list[dict[str, Any]] = []
    for candidate in sorted(target_path.parent.glob("*.pdf")):
        if not _is_same_day_same_ticker_companion(target_path, candidate):
            continue
        role = _companion_source_role(candidate)
        if role not in _COMPANION_PERIOD_SOURCE_ROLE_PRIORITY:
            continue
        source_text = _read_pdf_text_for_companion_period_source(candidate)
        evidence = _detect_source_period_end_evidence(candidate.name, source_text)
        companions.append(
            {
                "source_path": str(candidate),
                "source_role": role,
                "period_end_evidence": evidence,
            }
        )
    return companions


def _bind_companion_source_period_end_over_announcement_date(
    pass1_result: dict,
    target_source_period_end_evidence: dict,
    title: Any,
    *,
    target_source_path: Any = "",
    companion_sources: list[dict[str, Any]] | None = None,
) -> bool:
    """
    Bind a half-year period end from a same-day issuer companion document.

    This intentionally does not infer from filenames, publication dates, or
    loose title dates.  It only accepts an explicit half-year period-end phrase
    in companion source text, with same-day same-ticker provenance retained.
    """

    report_type = str(
        pass1_result.get("report_type") or pass1_result.get("period_type") or ""
    ).strip()
    if report_type != "H":
        return False
    if _has_source_text_period_end_hit(
        target_source_period_end_evidence,
        reason="half_year_ended_explicit_date",
    ):
        return False

    current_period_end = parse_period_end(str(pass1_result.get("period_end") or ""))
    if current_period_end is None:
        return False
    title_text = str(title or "")
    if not _has_half_year_title_hint({}, [title_text]):
        return False
    title_date = _leading_announcement_date_from_title(title_text)
    if title_date is None:
        return False

    sources = (
        companion_sources
        if companion_sources is not None
        else _discover_same_day_companion_period_sources(target_source_path)
    )
    eligible: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_path = str(source.get("source_path") or "")
        if not _is_same_day_same_ticker_companion(target_source_path, source_path):
            continue
        evidence = source.get("period_end_evidence")
        if not isinstance(evidence, dict):
            continue
        if evidence.get("period_type") != "H":
            continue
        if evidence.get("reason") != "half_year_ended_explicit_date":
            continue
        if not _has_source_text_period_end_hit(
            evidence,
            reason="half_year_ended_explicit_date",
        ):
            continue
        source_period_end = parse_period_end(str(evidence.get("period_end") or ""))
        if source_period_end is None:
            continue
        role = str(source.get("source_role") or "").strip() or _companion_source_role(
            source_path
        )
        if role not in _COMPANION_PERIOD_SOURCE_ROLE_PRIORITY:
            continue
        eligible.append(
            {
                "source_path": source_path,
                "source_role": role,
                "period_end": source_period_end,
                "period_end_evidence": evidence,
            }
        )

    period_ends = sorted({item["period_end"].isoformat() for item in eligible})
    if len(period_ends) > 1:
        pass1_result["_companion_source_period_end_binding_error"] = (
            "companion_period_end_conflict"
        )
        return False
    if not eligible:
        return False

    chosen = sorted(
        eligible,
        key=lambda item: (
            _COMPANION_PERIOD_SOURCE_ROLE_PRIORITY.get(item["source_role"], 99),
            item["source_path"],
        ),
    )[0]
    source_period_end = chosen["period_end"]
    if current_period_end == source_period_end:
        return False

    binding_reason = (
        "explicit_companion_source_half_year_period_end_over_announcement_title_date"
        if title_date == current_period_end
        else "explicit_companion_source_half_year_period_end_over_unsupported_pass1_period_end"
    )
    binding = {
        "reason": binding_reason,
        "from_period_end": current_period_end.isoformat(),
        "to_period_end": source_period_end.isoformat(),
        "source_period_end_reason": chosen["period_end_evidence"].get("reason"),
        "target_document_title": title_text,
        "target_source_path": str(target_source_path or ""),
        "period_source_path": chosen["source_path"],
        "period_source_role": chosen["source_role"],
        "selection_rule": "same_day_same_ticker_companion_period_source",
        "target_title_announcement_date": title_date.isoformat(),
        "corroborating_source_paths": [
            item["source_path"]
            for item in sorted(eligible, key=lambda item: item["source_path"])
            if item["source_path"] != chosen["source_path"]
        ],
    }

    evidence_for_payload = dict(chosen["period_end_evidence"])
    evidence_for_payload["period_source_path"] = chosen["source_path"]
    evidence_for_payload["period_source_role"] = chosen["source_role"]

    pass1_result["period_end"] = source_period_end.isoformat()
    pass1_result["_source_period_end_binding"] = binding
    pass1_result["_companion_source_period_end_evidence"] = evidence_for_payload
    return True


def _announcement_date_period_end_mismatch(
    payload: dict,
) -> tuple[str, str, str] | None:
    if payload.get("period_type") != "H":
        return None
    payload_date = parse_period_end(str(payload.get("period_end") or ""))
    if payload_date is None:
        return None
    titles = _payload_source_titles(payload)
    if not titles or not _has_half_year_title_hint(payload, titles):
        return None
    for title in titles:
        title_date = _leading_announcement_date_from_title(title)
        if title_date is not None and title_date == payload_date:
            return (
                payload_date.isoformat(),
                title_date.isoformat(),
                "leading_title_date",
            )
    return None


def _source_bound_native_currency_status_can_be_ok(
    payload: dict,
    canonical_metrics: dict[str, Any],
    currency: str,
) -> bool:
    """Allow source-bound native-currency reports to pass without FX conversion.

    Non-AUD remains a structured warning. The status can be `ok` only when the
    payload carries enough deterministic source binding to show values are in
    the stated native currency and scale, not an unverified LLM guess.
    """
    if currency in {"AUD", "UNKNOWN", ""}:
        return False
    if _coerce_confidence(payload.get("confidence_metrics", 0.0), 0.0) < 0.70:
        return False

    source_bound = (
        payload.get("source_bound")
        if isinstance(payload.get("source_bound"), dict)
        else {}
    )
    if not source_bound:
        return False
    if _normalize_currency_code(source_bound.get("currency")) != currency:
        return False
    for source_field in ("period_type", "period_end", "scale"):
        payload_value = str(payload.get(source_field) or "").strip().lower()
        source_value = str(source_bound.get(source_field) or "").strip().lower()
        if not payload_value or source_value != payload_value:
            return False
    if str(payload.get("scale") or "").strip().lower() == "unknown":
        return False

    non_null_metrics = [
        metric_name
        for metric_name, value in canonical_metrics.items()
        if value is not None
    ]
    if len(non_null_metrics) < (1 if payload.get("period_type") == "Q" else 3):
        return False

    payload_scale = str(payload.get("scale") or "").strip().lower()
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    scale_bound_metrics = [
        metric_name
        for metric_name in non_null_metrics
        if str(metric_source_scales.get(metric_name) or "").strip().lower()
        == payload_scale
    ]
    if len(scale_bound_metrics) < min(3, len(non_null_metrics)):
        return False

    row_refs = (
        payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    )
    provenance = (
        payload.get("provenance")
        if isinstance(payload.get("provenance"), dict)
        else {}
    )
    evidenced_metrics = [
        metric_name
        for metric_name in non_null_metrics
        if _normalize_filter_text(
            _combined_source_text(
                row_refs.get(metric_name),
                provenance.get(metric_name),
            )
        )
        not in {"", "unknown"}
    ]
    return len(evidenced_metrics) >= min(3, len(non_null_metrics))


def _validate_gate(payload: dict) -> tuple[str, Optional[str]]:
    """
    Validate the reconciled payload before DB upsert.
    Returns (status, error). status is one of: "ok", "ok_low_confidence", "failed".
    """
    from dateutil import parser as dtparser

    # Hard blocks
    scale_validation = payload.get("scale_validation", "pass")
    if scale_validation != "pass":
        return "failed", f"validation_gate:scale_validation:{scale_validation}"

    if not payload.get("period_end"):
        return "failed", "validation_gate:missing_period_end"

    try:
        dtparser.parse(str(payload["period_end"]))
    except Exception:
        return "failed", "validation_gate:invalid_period_end"

    if payload.get("period_type") not in ("A", "H", "Q"):
        return (
            "failed",
            f"validation_gate:invalid_period_type:{payload.get('period_type')}",
        )

    if payload.get("scale") == "unknown":
        return "failed", "validation_gate:scale_unknown"

    currency = _normalize_currency_code(payload.get("currency"))
    if not currency:
        return "failed", "validation_gate:currency_unknown"

    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    canonical_metrics = {metric_name: metrics.get(metric_name) for metric_name in METRIC_FIELDS}
    mismatch = _metric_label_mismatch(payload)
    if mismatch is not None:
        metric_name, source_label = mismatch
        return (
            "failed",
            f"validation_gate:metric_label_mismatch:{metric_name}:{source_label}",
        )

    source_unit_mismatch = _source_unit_value_mismatch(payload)
    if source_unit_mismatch is not None:
        metric_name, actual, expected = source_unit_mismatch
        return (
            "failed",
            "validation_gate:source_unit_value_mismatch:"
            f"{metric_name}:actual={actual:g}:source_unit={expected:g}",
        )

    period_mismatch = _period_source_mismatch(payload)
    if period_mismatch is not None:
        period_type, source_period_type, reason = period_mismatch
        return (
            "failed",
            "validation_gate:period_source_mismatch:"
            f"payload={period_type}:source={source_period_type}:{reason}",
        )

    period_end_mismatch = _period_end_source_mismatch(payload)
    if period_end_mismatch is not None:
        period_end, source_period_end, reason = period_end_mismatch
        return (
            "failed",
            "validation_gate:period_end_source_mismatch:"
            f"payload={period_end}:source={source_period_end}:{reason}",
        )

    announcement_period_mismatch = _announcement_date_period_end_mismatch(payload)
    if announcement_period_mismatch is not None:
        period_end, title_date, reason = announcement_period_mismatch
        return (
            "failed",
            "validation_gate:announcement_date_period_end:"
            f"period_type=H:period_end={period_end}:title_date={title_date}:{reason}",
        )

    non_null = [v for v in canonical_metrics.values() if v is not None]
    wrapper_override, wrapper_error = _appendix_wrapper_minimum_override(
        payload,
        canonical_metrics,
    )
    if wrapper_error is not None:
        return "failed", wrapper_error

    # Quarterly Appendix 5B filings are structurally limited to cash-flow metrics;
    # they never contain income-statement or balance-sheet rows.  A minimum of 1
    # non-null metric is sufficient to confirm a legitimate quarterly extraction,
    # provided all other gates (scale, period_end, confidence, sanity cap) pass.
    # Annual and half-year reports must still provide at least 3 non-null metrics.
    min_metrics = 2 if wrapper_override else (1 if payload.get("period_type") == "Q" else 3)
    if len(non_null) < min_metrics:
        return "failed", f"validation_gate:insufficient_metrics:{len(non_null)}"

    sanity_cap = _native_currency_sanity_cap(payload.get("currency"))
    for m, v in canonical_metrics.items():
        if v is not None and abs(v) > sanity_cap:
            return "failed", f"validation_gate:sanity_cap_exceeded:{m}={v}"

    scale_magnitude_risk_error = _accepted_output_scale_magnitude_risk_error(
        payload,
        canonical_metrics,
    )
    if scale_magnitude_risk_error is not None:
        return "failed", scale_magnitude_risk_error

    confidence = payload.get("confidence_metrics", 0.0)
    if confidence < 0.60:
        return "failed", f"validation_gate:low_confidence:{confidence}"

    # Non-AUD currency: values are stored as-is with no FX conversion.
    # Flag as ok_low_confidence so consumers know to treat values with caution,
    # but only after all quality gates pass — non-AUD must not bypass them.
    # A warning was already emitted at ingestion time in run_multipass_extraction.
    if currency != "AUD":
        if _source_bound_native_currency_status_can_be_ok(
            payload,
            canonical_metrics,
            currency,
        ):
            logger.warning(
                "validation_gate:non_aud_currency:%s — native-currency values "
                "are source-bound; status remains ok",
                currency,
            )
            return "ok", None
        logger.warning(
            "validation_gate:non_aud_currency:%s — downgrading to ok_low_confidence (no FX policy)",
            currency,
        )
        return "ok_low_confidence", None

    # Soft warning
    if confidence < 0.70:
        return "ok_low_confidence", None

    return "ok", None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_multipass_extraction(
    pdf_path: str,
    doc_metadata: dict,
    llm_client,
    *,
    skip_narrative: bool = False,
    parser_backend: str | None = None,
    strict_parser: bool = False,
    observer: ExtractionRunObserver | None = None,
    debug_capture: dict[str, Any] | None = None,
    prompt_bundle_id: str | None = None,
    model_override: str | None = None,
    openability_diagnostics: bool = False,
    openability_pages: list[int] | None = None,
    openability_selected_tables: bool = False,
    capture_pass3a_failures: bool = False,
    capture_benchmark_source_cells: bool = False,
) -> MultipassResult:
    """
    Orchestrate all 4 passes and return a MultipassResult.
    doc_metadata: {"document_id": str, "ticker": str, "title": str}

    skip_narrative: when True, skip the Pass 3b LLM call and use null
    narrative fields.  Also respects env var EXTRACTION_SKIP_NARRATIVE=1.
    Useful for backfill runs and eval harness where only metrics matter.

    prompt_bundle_id: optional id of a registered PromptBundle (default: the
    canonical "default" bundle that pins ``extraction_runs.prompt_hash`` to
    the historical value). Unknown ids raise KeyError — see prompt_registry.

    model_override: optional model id to pin for every LLM call in this run
    (e.g. matrix runner comparing ``qwen2.5-14b-instruct`` vs another model).

    openability_selected_tables: explicit diagnostic bridge for parser-openability
    gaps. Defaults off; when enabled, parser diagnostics are requested and any
    source-bound openability rows are converted into synthetic tables that still
    pass through normal Pass 2/3a/4 validation gates.

    capture_benchmark_source_cells: opt-in v2 replay evidence. Defaults off so
    normal extraction and v1 replay metadata remain unchanged.
    """
    bundle = resolve(prompt_bundle_id)

    null_payload = {m: None for m in METRIC_FIELDS}
    null_payload.update(
        {
            "period_type": None,
            "period_end": None,
            "period_start": None,
            "confidence_metrics": 0.0,
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.0,
            "provenance": {},
        }
    )

    title = doc_metadata.get("title", "")
    preparse_source_document_classification = classify_source_document(title, "")
    if not preparse_source_document_classification.extraction_candidate_allowed:
        error = f"validation_gate:{preparse_source_document_classification.reason}"
        logger.warning(
            "source document blocked before parser: title=%r class=%s",
            title,
            preparse_source_document_classification.document_class,
        )
        null_payload["source_period_evidence"] = _detect_source_period_evidence(
            title,
            "",
        )
        null_payload["source_period_end_evidence"] = _detect_source_period_end_evidence(
            title,
            "",
        )
        null_payload["source_document_classification"] = (
            preparse_source_document_classification.to_dict()
        )
        null_payload["source_document_gate"] = (
            preparse_source_document_classification.reason
        )
        if observer is not None:
            observer.emit(
                "parser",
                "blocked",
                "Source document blocked before parser.",
                error_code="source_document_non_candidate",
                details={
                    "document_class": (
                        preparse_source_document_classification.document_class
                    ),
                    "reason": preparse_source_document_classification.reason,
                },
            )
        return MultipassResult(
            status="failed",
            payload=null_payload,
            sections=[],
            error=error,
        )

    # Extract structured document
    from app.services.docling_extract import ExtractionTimeoutError, extract_structured

    if observer is not None:
        observer.emit("parser", "running", "Loading document parser output.")
    try:
        structured_doc = extract_structured(
            pdf_path,
            backend=parser_backend or "",
            strict_backend=strict_parser,
            openability_diagnostics=(
                openability_diagnostics or openability_selected_tables
            ),
            openability_pages=openability_pages,
        )
    except Exception as e:
        # If Docling fails, we must report PARSER_ERROR so Manual Review is triggered.
        is_parser_error = (
            isinstance(e, ExtractionTimeoutError) or "docling" in str(e).lower()
        )
        logger.error(
            "docling_extract failed for %s (parser_error=%s): %s",
            pdf_path,
            is_parser_error,
            e,
        )
        if observer is not None:
            observer.emit(
                "parser",
                "blocked" if is_parser_error else "failed",
                f"Parser failed: {e}",
                error_code="parser_failed",
                details={"parser_backend": parser_backend, "error": str(e)},
            )
        null_payload["_structured_extraction"] = {
            "parser_id": parser_backend or "auto",
            "page_count": 0,
            "docling_version": None,
            "fallback_used": False,
            "warnings": [],
        }
        return MultipassResult(
            status="parser_error" if is_parser_error else "failed",
            payload=null_payload,
            sections=[],
            error=str(e),
        )
    if observer is not None:
        observer.emit(
            "parser",
            "succeeded",
            f"Parsed document with {structured_doc.extraction_method}.",
            details={
                "actual_method": structured_doc.extraction_method,
                "page_count": structured_doc.page_count,
                "table_count": len(structured_doc.tables),
            },
        )

    # Pass 1: Classify — use title + first page only (not arbitrary 1500 chars).
    # ASX filings have all classification info (period, type, currency, scale)
    # on page 1.  Sending less text = fewer input tokens = faster LLM inference.
    first_page_sections = [s for s in structured_doc.sections if s.get("page", 0) <= 1]
    if not first_page_sections:
        # Fallback: some PDFs have page=0 for all sections (e.g. pymupdf fallback).
        first_page_sections = structured_doc.sections[:3]
    first_page_text = " ".join(s["text"] for s in first_page_sections)
    early_period_text = _early_period_source_text(structured_doc.sections)
    openability_period_text = (
        _openability_period_source_text(structured_doc)
        if openability_selected_tables
        else ""
    )
    source_period_text = _combined_source_text(
        early_period_text or first_page_text,
        openability_period_text,
    )
    source_period_evidence = _detect_source_period_evidence(
        title, source_period_text
    )
    source_period_end_evidence = _detect_source_period_end_evidence(
        title, source_period_text
    )
    source_document_classification = classify_source_document(title, first_page_text)
    if not source_document_classification.extraction_candidate_allowed:
        error = f"validation_gate:{source_document_classification.reason}"
        logger.warning(
            "source document blocked before metric extraction: title=%r class=%s",
            title,
            source_document_classification.document_class,
        )
        null_payload["source_period_evidence"] = source_period_evidence
        null_payload["source_period_end_evidence"] = source_period_end_evidence
        null_payload["source_document_classification"] = (
            source_document_classification.to_dict()
        )
        null_payload["source_document_gate"] = source_document_classification.reason
        return MultipassResult(
            status="failed",
            payload=null_payload,
            sections=structured_doc.sections,
            error=error,
        )

    document_type_classification, contract_selection = (
        classify_and_select_extraction_contract(
            {
                "first_page_title_text": first_page_text,
                "asx_announcement_title": title,
                "document_pages": [
                    {
                        "page": section.get("page"),
                        "text": section.get("text"),
                    }
                    for section in structured_doc.sections
                ],
            }
        )
    )
    null_payload["asx_document_type_classification"] = (
        document_type_classification.to_dict()
    )
    null_payload["asx_extraction_contract"] = contract_selection.to_dict()
    if contract_selection.abstain or contract_selection.contract is None:
        error = "validation_gate:extraction_contract_abstain"
        null_payload["source_period_evidence"] = source_period_evidence
        null_payload["source_period_end_evidence"] = source_period_end_evidence
        null_payload["source_document_classification"] = (
            source_document_classification.to_dict()
        )
        null_payload["source_document_gate"] = (
            "extraction_contract_abstain"
        )
        return MultipassResult(
            status="failed",
            payload=null_payload,
            sections=structured_doc.sections,
            error=error,
        )

    if observer is not None:
        observer.emit("pass1_classifier", "running", "Running pass 1 classifier.")
    try:
        pass1 = _run_pass1_classifier(
            title,
            first_page_text,
            llm_client,
            prompt_bundle=bundle,
            model_override=model_override,
        )
    except Exception as e:
        logger.error("Pass 1 failed: %s", e)
        if observer is not None:
            observer.emit(
                "pass1_classifier",
                "failed",
                f"Pass 1 failed: {e}",
                error_code="pass1_failed",
            )
        return MultipassResult(
            status="failed",
            payload=null_payload,
            sections=structured_doc.sections,
            error=f"pass1:{e}",
        )

    if pass1.get("classifier_confidence", 0) < 0.60:
        if observer is not None:
            observer.emit(
                "pass1_classifier",
                "failed",
                "Classifier confidence below threshold.",
                error_code="classifier_low_confidence",
                details={"classifier_confidence": pass1.get("classifier_confidence")},
            )
        return MultipassResult(
            status="failed",
            payload=null_payload,
            sections=structured_doc.sections,
            error=f"classifier_low_confidence:{pass1.get('classifier_confidence')}",
        )
    if observer is not None:
        observer.emit("pass1_classifier", "succeeded", "Pass 1 completed.")
    if (
        not pass1.get("period_end")
        and source_period_end_evidence.get("period_end")
        and _has_source_text_period_end_hit(source_period_end_evidence)
    ):
        pass1["period_end"] = source_period_end_evidence["period_end"]
    else:
        same_document_bound = _bind_explicit_source_period_end_over_announcement_date(
            pass1,
            source_period_end_evidence,
            title,
        )
        if not same_document_bound:
            _bind_companion_source_period_end_over_announcement_date(
                pass1,
                source_period_end_evidence,
                title,
                target_source_path=pdf_path,
            )
    source_period_end_evidence_for_payload = (
        pass1.get("_companion_source_period_end_evidence")
        or source_period_end_evidence
    )
    pass1["_source_period_evidence"] = source_period_evidence
    pass1["_source_period_end_evidence"] = source_period_end_evidence_for_payload
    pass1["_source_period_type"] = source_period_evidence.get("period_type")
    pass1["_source_document_classification"] = source_document_classification.to_dict()

    structured_tables = list(structured_doc.tables)
    if openability_selected_tables:
        openability_tables = _build_openability_selected_tables(structured_doc)
        if openability_tables:
            structured_tables.extend(openability_tables)
            if debug_capture is not None:
                debug_capture["openability_selected_tables"] = [
                    {
                        "page_number": table.page_number,
                        "caption": table.caption,
                        "row_count": len(table.rows),
                    }
                    for table in openability_tables
                ]
            logger.info(
                "Added %d openability diagnostic selected tables",
                len(openability_tables),
            )

    # Table-header scale detection is always authoritative — ASX filings print scale
    # explicitly in column headers ($'000, A$M, etc.) which is more reliable than
    # LLM text inference. Run unconditionally; fall back to Pass 1 if headers give nothing.
    detected = _detect_scale_from_tables(structured_tables)
    if detected != "unknown":
        if pass1.get("scale", "unknown") not in (detected, "unknown", None, ""):
            logger.info(
                "scale from table headers (%s) overrides Pass 1 (%s)",
                detected,
                pass1.get("scale"),
            )
        pass1["scale"] = detected
    else:
        statement_page_scale = _detect_scale_from_statement_page_text(
            structured_doc.sections, structured_tables
        )
        source_text_scale = statement_page_scale
        if source_text_scale == "unknown":
            source_text_scale = _detect_scale_from_source_text(
                early_period_text or first_page_text
            )
        if source_text_scale != "unknown":
            if pass1.get("scale", "unknown") not in (
                source_text_scale,
                "unknown",
                None,
                "",
            ):
                logger.info(
                    "scale from explicit source text (%s) overrides Pass 1 (%s)",
                    source_text_scale,
                    pass1.get("scale"),
                )
            pass1["scale"] = source_text_scale
    if pass1.get("scale", "unknown") in ("unknown", None, ""):
        logger.warning("scale unknown from both table headers and Pass 1 classifier")

    detected_currency = _detect_currency_from_tables(structured_tables)
    if detected_currency is not None:
        classifier_currency = str(pass1.get("currency") or "").strip().upper()
        if detected_currency == "":
            logger.warning(
                "conflicting explicit currency evidence in statement tables; abstaining"
            )
            pass1["currency"] = ""
        elif classifier_currency != detected_currency:
            logger.info(
                "currency from table headers (%s) overrides Pass 1 (%s)",
                detected_currency,
                classifier_currency or "<empty>",
            )
            pass1["currency"] = detected_currency

    _currency = _normalize_currency_code(pass1.get("currency"))
    pass1["currency"] = _currency
    if _currency and _currency != "AUD":
        logger.warning(
            "non-AUD currency detected: %s — values stored as-is (no FX conversion applied)",
            _currency,
        )

    appendix_wrapper_source = _build_appendix_wrapper_source_payload(
        title=title,
        sections=structured_doc.sections,
        tables=structured_tables,
        period_evidence=source_period_evidence,
        period_end_evidence=source_period_end_evidence_for_payload,
        scale=pass1.get("scale", "unknown"),
        currency=pass1.get("currency"),
    )
    if appendix_wrapper_source.get("is_wrapper"):
        pass1["_appendix_wrapper_source"] = appendix_wrapper_source
        if appendix_wrapper_source.get("period_type") in {"A", "H", "Q"}:
            if pass1.get("report_type") != appendix_wrapper_source["period_type"]:
                logger.info(
                    "Appendix wrapper source period type (%s) overrides Pass 1 (%s)",
                    appendix_wrapper_source["period_type"],
                    pass1.get("report_type"),
                )
            pass1["report_type"] = appendix_wrapper_source["period_type"]
        if appendix_wrapper_source.get("period_end"):
            pass1["period_end"] = appendix_wrapper_source["period_end"]

    contract_routing = evaluate_contract_routing(
        contract_selection,
        period_basis=pass1.get("report_type"),
        available_context={
            "document_type_anchor",
            *({"period_basis"} if pass1.get("report_type") else set()),
        },
        source_evidence_count=len(
            document_type_classification.positive_evidence
        ),
    )
    if not contract_routing.allowed or contract_routing.contract is None:
        reason = (
            contract_routing.reasons[0]
            if contract_routing.reasons
            else "extraction_contract_abstain"
        )
        null_payload["asx_extraction_contract_routing"] = (
            contract_routing.to_dict()
        )
        null_payload["source_period_evidence"] = source_period_evidence
        null_payload["source_period_end_evidence"] = (
            source_period_end_evidence_for_payload
        )
        null_payload["source_document_classification"] = (
            source_document_classification.to_dict()
        )
        null_payload["source_document_gate"] = reason
        return MultipassResult(
            status="failed",
            payload=null_payload,
            sections=structured_doc.sections,
            error=f"validation_gate:{reason}",
        )
    allowed_contract_metrics = tuple(
        contract_routing.contract.allowed_canonical_metrics
    )
    pass1["_contract_allowed_canonical_metrics"] = allowed_contract_metrics
    pass1["_asx_document_type_classification"] = (
        document_type_classification.to_dict()
    )
    pass1["_asx_extraction_contract"] = contract_selection.to_dict()
    pass1["_asx_extraction_contract_routing"] = contract_routing.to_dict()

    # Pass 2: Locate tables
    if observer is not None:
        observer.emit("pass2_locator", "running", "Locating statement tables.")
    labelled = _run_pass2_locator(structured_tables)
    pass1["_block_derived_net_debt"] = bool(
        _document_has_nonnumeric_net_debt_reference(structured_tables)
    )
    if observer is not None:
        observer.emit("pass2_locator", "succeeded", "Pass 2 completed.")

    # Pass 3a: Extract metrics
    if observer is not None:
        observer.emit(
            "pass3a_metrics",
            "running",
            "Extracting metric candidates.",
        )
    pass3a_failure_queue: SimpleQueue[dict[str, Any]] | None = (
        SimpleQueue() if capture_pass3a_failures else None
    )
    try:
        pass3a_results = _run_pass3a_metric_extractor(
            labelled,
            pass1,
            llm_client,
            prompt_bundle=bundle,
            model_override=model_override,
            failure_capture=pass3a_failure_queue,
        )
    except Exception as e:
        if observer is not None:
            observer.emit(
                "pass3a_metrics",
                "failed",
                f"Pass 3a failed: {e}",
                error_code="pass3a_failed",
            )
        raise
    finally:
        if debug_capture is not None and pass3a_failure_queue is not None:
            pass3a_failures: list[dict[str, Any]] = []
            while True:
                try:
                    pass3a_failures.append(pass3a_failure_queue.get_nowait())
                except Empty:
                    break
            debug_capture["pass3a_failures"] = sorted(
                pass3a_failures,
                key=lambda row: (str(row.get("table_type") or ""), json.dumps(row)),
            )
    allowed_internal_metrics = (
        {"total_debt"} if "net_debt" in allowed_contract_metrics else set()
    )
    allowed_result_keys = set(allowed_contract_metrics) | allowed_internal_metrics
    for result in pass3a_results:
        if not isinstance(result, dict):
            continue
        for metric_name in METRIC_FIELDS:
            if metric_name not in allowed_result_keys:
                result.pop(metric_name, None)
        if "total_debt" not in allowed_result_keys:
            result.pop("total_debt", None)
        row_refs = result.get("row_refs")
        if isinstance(row_refs, dict):
            result["row_refs"] = {
                metric_name: row_ref
                for metric_name, row_ref in row_refs.items()
                if metric_name in allowed_result_keys
            }
    if "revenue" in allowed_contract_metrics:
        market_update_revenue = _extract_market_update_net_revenue_candidate(
            structured_tables,
            sections=structured_doc.sections,
            pass1_result=pass1,
            title=title,
        )
        if market_update_revenue is not None:
            pass3a_results.append(market_update_revenue)
    if debug_capture is not None:
        debug_capture["pass3a_results"] = json.loads(json.dumps(pass3a_results))
    if observer is not None:
        observer.emit("pass3a_metrics", "succeeded", "Pass 3a completed.")

    # Pass 3b: Extract narrative (skippable for metrics-only runs)
    _skip = skip_narrative or os.environ.get("EXTRACTION_SKIP_NARRATIVE", "") == "1"
    if _skip:
        logger.info(
            "Pass 3b skipped (skip_narrative=%s, env=%s)",
            skip_narrative,
            os.environ.get("EXTRACTION_SKIP_NARRATIVE", ""),
        )
        if observer is not None:
            observer.emit(
                "pass3b_narrative",
                "skipped",
                "Pass 3b skipped for metrics-only extraction.",
            )
        pass3b_result = {
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.0,
        }
    else:
        if observer is not None:
            observer.emit(
                "pass3b_narrative",
                "running",
                "Extracting narrative evidence.",
            )
        try:
            pass3b_result = _run_pass3b_narrative_extractor(
                structured_doc.sections,
                llm_client,
                prompt_bundle=bundle,
                model_override=model_override,
            )
        except Exception as e:
            if observer is not None:
                observer.emit(
                    "pass3b_narrative",
                    "failed",
                    f"Pass 3b failed: {e}",
                    error_code="pass3b_failed",
                )
            raise
        if observer is not None:
            observer.emit("pass3b_narrative", "succeeded", "Pass 3b completed.")

    # Pass 4: Reconcile
    if observer is not None:
        observer.emit(
            "pass4_reconciliation",
            "running",
            "Reconciling extracted fields.",
        )
    payload = _run_pass4_reconciler(
        pass3a_results,
        pass3b_result,
        pass1,
        sections=structured_doc.sections,
    )
    if observer is not None:
        observer.emit(
            "pass4_reconciliation",
            "succeeded",
            "Pass 4 completed.",
        )

    # Derive period_start deterministically — schema column exists but was not populated.
    _pe = parse_period_end(payload.get("period_end"))
    payload["period_start"] = _derive_period_start(_pe, payload.get("period_type"))

    # Flatten metrics into payload for _upsert_financial_rows compat
    for m in METRIC_FIELDS:
        payload[m] = payload["metrics"].get(m)

    payload["_structured_extraction"] = {
        "parser_id": structured_doc.extraction_method,
        "page_count": structured_doc.page_count,
        "docling_version": structured_doc.docling_version or None,
        "fallback_used": structured_doc.extraction_method.startswith("pymupdf")
        and (parser_backend in (None, "", "docling")),
        "warnings": [],
    }

    # Propagate scale and currency from Pass 1 into payload so _validate_gate
    # can inspect them and so _upsert_financial_rows stores the correct currency.
    # An absent currency remains empty so validation abstains rather than guessing AUD.
    payload["scale"] = _common_metric_source_scale(
        payload,
        pass1.get("scale", "unknown") or "unknown",
    )
    payload["currency"] = pass1.get("currency") or ""
    payload["document_title"] = title
    _apply_appendix_wrapper_source_payload(
        payload,
        pass1.get("_appendix_wrapper_source"),
    )
    if set(allowed_contract_metrics) & {"revenue", "ebit", "np_attributable"}:
        _apply_preferred_income_statement_source_payload(
            payload,
            structured_tables,
            scale=payload.get("scale") or pass1.get("scale", "unknown"),
            pass1_result=pass1,
        )
        _apply_preferred_statement_text_source_payload(
            payload,
            structured_doc.sections,
            scale=payload.get("scale") or pass1.get("scale", "unknown"),
            pass1_result=pass1,
        )
    _apply_bank_cashflow_capex_source_text_payload(
        payload,
        pdf_path,
        scale=payload.get("scale") or pass1.get("scale", "unknown"),
        pass1_result=pass1,
    )
    if "ebit" in allowed_contract_metrics:
        _apply_rejected_ebit_from_pdf_statement_text(
            payload,
            pdf_path,
            scale=payload.get("scale") or pass1.get("scale", "unknown"),
            pass1_result=pass1,
        )
    _apply_appendix5b_source_text_payload(
        payload,
        pdf_path,
        scale=payload.get("scale") or pass1.get("scale", "unknown"),
        pass1_result=pass1,
    )
    if "shares_outstanding" in allowed_contract_metrics:
        _apply_preferred_shares_source_payload(
            payload,
            structured_tables,
            pass1_result=pass1,
            capture_benchmark_source_cell=capture_benchmark_source_cells,
        )
    if "cash_end" in allowed_contract_metrics:
        _apply_preferred_cash_end_source_payload(
            payload,
            structured_tables,
            scale=payload.get("scale") or pass1.get("scale", "unknown"),
            pass1_result=pass1,
        )
    if set(allowed_contract_metrics) & {
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "cash_end",
    }:
        _apply_structured_appendix_cashflow_payload(
            payload,
            structured_tables,
            pass1_result=pass1,
        )
    _enforce_contract_metric_allowance(payload, allowed_contract_metrics)
    source_bound = payload.get("source_bound")
    if not isinstance(source_bound, dict):
        source_bound = {}
    source_bound.update(
        {
            "period_type": payload.get("period_type"),
            "period_end": payload.get("period_end"),
            "scale": payload.get("scale"),
            "currency": payload.get("currency"),
            "document_title": title,
        }
    )
    payload["source_bound"] = source_bound
    payload["asx_document_type_classification"] = (
        document_type_classification.to_dict()
    )
    payload["asx_extraction_contract"] = contract_selection.to_dict()
    payload["asx_extraction_contract_routing"] = contract_routing.to_dict()
    _pe = parse_period_end(payload.get("period_end"))
    payload["period_start"] = _derive_period_start(_pe, payload.get("period_type"))

    # Surface non-AUD currency as a structured warning for operator visibility.
    # Values are stored in native currency with no FX conversion; downstream
    # consumers must not compare them directly with AUD-denominated peers.
    if payload["currency"] and payload["currency"] != "AUD":
        payload["_structured_extraction"]["warnings"].append(
            f"non_aud_currency:{payload['currency']} — values in native currency, no FX conversion"
        )

    # Scale validation — detect obviously wrong multiplier application
    scale_validation = _validate_scale(payload)
    payload["scale_validation"] = scale_validation
    if scale_validation != "pass":
        logger.warning(
            "scale_validation=%s for %s %s %s — marking as failed to prevent "
            "bad data from entering the DB",
            scale_validation,
            doc_metadata.get("ticker", "?"),
            payload.get("period_end", "?"),
            payload.get("period_type", "?"),
        )

    # Validate
    if observer is not None:
        observer.emit("validation", "running", "Running validation gates.")
    status, error = _validate_gate(payload)
    logger.info(
        "Gate: status=%s, confidence=%.3f, non_null_metrics=%d",
        status,
        payload.get("confidence_metrics", 0),
        len([v for v in payload.get("metrics", {}).values() if v is not None]),
    )
    if observer is not None:
        observer.emit(
            "validation",
            "succeeded" if status in {"ok", "ok_low_confidence"} else "failed",
            "Validation completed."
            if status in {"ok", "ok_low_confidence"}
            else f"Validation failed: {error}",
            error_code=None
            if status in {"ok", "ok_low_confidence"}
            else "validation_failed",
            details={"extraction_status": status, "error": error},
        )

    return MultipassResult(
        status=status,
        payload=payload,
        sections=structured_doc.sections,
        error=error,
    )


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------


def _llm_json_call(
    prompt: str,
    llm_client,
    max_tokens: int = 512,
    *,
    model_override: str | None = None,
) -> dict:
    """
    Call the LLM with JSON mode enforced. Returns parsed dict.
    Raises on invalid JSON or connection failure.

    llm_client may be:
    - httpx.Client pointing at an OpenAI-compatible endpoint (llamacpp / Ollama)
    - anthropic.Anthropic instance — uses Claude directly via the Anthropic SDK

    ``model_override`` pins a specific model for this call (e.g. matrix runner
    comparing ``qwen2.5-14b-instruct`` against ``qwen3-30b-a3b-instruct``). When
    ``None``, the configured extraction default is used.
    """
    import json as _json

    # Anthropic SDK path
    try:
        import anthropic as _anthropic

        if isinstance(llm_client, _anthropic.Anthropic):
            model = model_override or getattr(
                llm_client, "_extraction_model", "claude-opus-4-6"
            )
            msg = llm_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
                system="You are a financial document extraction assistant. Always respond with valid JSON only, no markdown, no explanation.",
            )
            text = msg.content[0].text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = _json.loads(text)
            if not isinstance(result, dict):
                raise ValueError(f"LLM returned non-dict: {type(result)}")
            return result
    except ImportError:
        pass

    # OpenAI-compatible path (llamacpp / Ollama)
    from app.services.llm import generate_json

    metadata: dict[str, Any] = {
        "task_type": "reasoning",
        "component": "multipass_extraction",
    }
    if model_override:
        # Honoured by _resolve_runtime_from_metadata in app.services.llm.
        metadata["requested_model"] = model_override
    result = generate_json(prompt, metadata=metadata, client=llm_client)
    if not isinstance(result, dict):
        raise ValueError(f"LLM returned non-dict: {type(result)}")
    return result
