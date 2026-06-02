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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

from dateutil import parser as dtparser

from app.services.extraction_run_observability import ExtractionRunObserver
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

# All 10 metric field names — used by Guard A and _upsert_financial_rows
METRIC_FIELDS = [
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
]

# Source priority for reconciliation (index 0 = highest priority)
SOURCE_PRIORITY = [
    "income_statement",
    "cashflow_statement",
    "net_debt_note",
    "balance_sheet",
    "share_capital",
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

SOURCE_DOCUMENT_CLASS_DEFINITIONS = {
    "financial_report": (
        "Source metadata has explicit annual, half-year, quarterly, or appendix "
        "financial-report evidence and may proceed through normal extraction gates."
    ),
    "advisory_only_document": (
        "Source metadata identifies an advisory-only announcement; it must not "
        "enter canary selection or metric extraction."
    ),
    "meeting_results_notice": (
        "Source metadata identifies an AGM/meeting result or poll notice; it "
        "must not enter canonical metric extraction."
    ),
    "meeting_notice": (
        "Source metadata identifies a shareholder meeting notice, proxy form, "
        "or voting-material announcement; it must not enter canonical metric "
        "extraction."
    ),
    "unaudited_financial_update_without_formal_statements": (
        "Source metadata identifies an unaudited headline update without formal "
        "financial statements; it must not enter canonical metric extraction."
    ),
    "capital_management_update_without_formal_statements": (
        "Source metadata identifies a buyback or purchase-plan result notice "
        "without formal Appendix or financial-statement evidence; it must not "
        "enter canonical metric extraction."
    ),
    "pre_results_update_without_formal_statements": (
        "Source metadata identifies a pre-results or notable-items announcement "
        "without formal Appendix or financial-statement evidence; it must not "
        "enter canonical metric extraction."
    ),
    "operational_update_without_formal_statements": (
        "Source metadata identifies a customer, contract, or revenue update "
        "without formal Appendix or financial-statement evidence; it must not "
        "enter canonical metric extraction."
    ),
    "non_financial_update_without_formal_statements": (
        "Source metadata identifies a drilling, exploration-results, programme, "
        "monthly fund, or shareholder-summary update without formal Appendix or "
        "financial-statement evidence; it must not enter canonical metric "
        "extraction."
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

_THOUSANDS_SCALE_PATTERN = (
    r"(?<!\w)(?:"
    r"(?:A\$|\$A|US\$|\$US|\$[A-Z]{2,3}|[A-Z]{3}|\$)"
    r"\s*[\u2019']?\s*000(?!,000\b)"
    r"|[\u2019']\s*000(?!,000\b)"
    r")[,s]?\b|\bthousands?\b"
)
_MILLIONS_SCALE_PATTERN = (
    r"(?<!\w)(?:"
    r"(?:A\$|\$A|US\$|\$US|\$[A-Z]{2,3}|[A-Z]{3}|\$)"
    r"\s*[\u2019']?\s*000,000"
    r"|[\u2019']\s*000,000"
    r")\b|\bmillions?\b|A?\$[Mm]\b|\$m\b"
)
_SCALE_PATTERNS: list[tuple[str, str]] = [
    # Thousands: $'000, $A'000, $USD'000, smart-apostrophe $USD'000, $000.
    (_THOUSANDS_SCALE_PATTERN, "thousands"),
    # Millions: spelled-out, $'000,000, compact $M / A$M notation.
    (_MILLIONS_SCALE_PATTERN, "millions"),
    (r"\bbillions?\b", "billions"),
    (
        r"(?:(?<!\w)RP\.?\s*trillions?\b|\bIDR\s*trillions?\b|"
        r"\brupiah\s*trillions?\b|\btrillions?\s+of\s+(?:rupiah|IDR)\b)",
        "trillions",
    ),
]

_IDR_MILLIONS_STATEMENT_UNIT_RE = _re.compile(
    r"\bexpressed\s+in\s+millions?\s+of\s+rupiah\b"
    r"|\bpresented\s+in\s+millions?\s+of\s+rupiah\b"
    r"|\bdisajikan\s+dalam\s+jutaan\s+rupiah\b"
    r"|\bdalam\s+jutaan\s+rupiah\b"
    r"|\bjutaan\s+rupiah\b"
    r"|(?<!\w)rp\.?\s*juta(?:an)?\b",
    _re.IGNORECASE,
)

_FINANCIAL_STATEMENT_UNIT_CONTEXT_RE = _re.compile(
    r"\bstatement\s+of\s+(?:financial\s+position|profit|comprehensive|cash\s*flows?|changes\s+in\s+equity)\b"
    r"|\bconsolidated\s+statement\s+of\s+(?:financial\s+position|profit|comprehensive|cash\s*flows?|changes\s+in\s+equity)\b"
    r"|\bcash\s*flows?\s+from\s*operating\s+activities\b"
    r"|\bcash\s*flows?\s+from\s*investing\s+activities\b"
    r"|\bcash\s*flows?\s+from\s*financing\s+activities\b"
    r"|\blaporan\s+(?:posisi\s+keuangan|laba\s+rugi|penghasilan\s+komprehensif|arus\s+kas|perubahan\s+ekuitas)\b",
    _re.IGNORECASE,
)

_RAW_DOLLAR_UNIT_RE = _re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:A\$|\$A|\$|AUD(?:\s+dollars?)?)"
    r"(?!\s*(?:'?\d{3}|0{3}|[mMbB]\b|bn\b|millions?\b|billions?\b|trillions?\b))"
    r"(?=\s|$|\)|,|;|:)",
    _re.IGNORECASE,
)
_APPENDIX_FULL_DOLLAR_VALUE_RE = _re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:A\$|\$A|\$)"
    r"\s*\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?"
    r"(?!\s*(?:[mMbB]\b|bn\b|millions?\b|billions?\b|trillions?\b))",
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


def _table_text_surfaces(table, *, row_limit: int = 3) -> list[str]:
    surfaces: list[str] = []
    if table.headers:
        surfaces.append(" ".join(str(h) for h in table.headers))
    if getattr(table, "caption", None):
        surfaces.append(str(table.caption))
    for row in (table.rows or [])[:row_limit]:
        surfaces.append(" ".join(str(cell) for cell in row))
    return surfaces


def _detect_scale_from_text(text: str) -> str:
    for pattern, scale in _SCALE_PATTERNS:
        if _re.search(pattern, text, _re.IGNORECASE):
            return scale
    return "unknown"


def _has_financial_statement_context(text: str) -> bool:
    return bool(_FINANCIAL_STATEMENT_UNIT_CONTEXT_RE.search(text))


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
    ranked = sorted(hits.items(), key=lambda item: item[1], reverse=True)
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


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


def _detect_idr_millions_statement_scale(tables) -> bool:
    """
    Detect explicit Indonesian financial-statement units.

    ATM-style filings may have an Appendix 4E summary in Rp trillions while the
    formal statements say "Expressed in Millions of Rupiah". The statement unit
    governs extraction values, so this check intentionally runs before the
    generic first-match scale scan.
    """
    for table in tables[:20]:
        surfaces: list[str] = []
        if table.headers:
            surfaces.append(" ".join(str(h) for h in table.headers))
        if getattr(table, "caption", None):
            surfaces.append(str(table.caption))
        for row in (table.rows or [])[:3]:
            surfaces.append(" ".join(str(cell) for cell in row))

        if _IDR_MILLIONS_STATEMENT_UNIT_RE.search(" ".join(surfaces)):
            return True
    return False


def _detect_scale_from_sections(sections) -> str:
    """Detect formal statement units that Docling kept as page text sections."""
    page_texts: dict[int, list[str]] = {}
    for section in sections or []:
        if isinstance(section, dict):
            text = str(section.get("text") or "")
            page = section.get("page")
        else:
            text = str(getattr(section, "text", "") or "")
            page = getattr(section, "page", None)
        if not text:
            continue
        if _IDR_MILLIONS_STATEMENT_UNIT_RE.search(
            text
        ) and _has_financial_statement_context(text):
            return "millions"
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            continue
        page_texts.setdefault(page_number, []).append(text)

    for page_number in sorted(page_texts):
        text = " ".join(page_texts[page_number])
        if not _has_financial_statement_context(text):
            continue
        detected = _detect_scale_from_text(text)
        if detected != "unknown":
            return detected

    return "unknown"


def _detect_scale_from_tables(tables) -> str:
    """
    Scan table headers, captions, and first few body rows for scale indicators
    ($'000, millions, etc.).
    Returns the first match, or 'unknown' if none found.
    ASX reports encode scale in column headings (e.g. "31 Dec 2025 $'000"),
    table captions, or sub-header rows just below the column headers.
    """
    if _detect_idr_millions_statement_scale(tables):
        return "millions"

    for table in tables or []:
        combined = " ".join(_table_text_surfaces(table, row_limit=8))
        if not _has_financial_statement_context(combined):
            continue
        detected = _detect_scale_from_text(combined)
        if detected != "unknown":
            return detected

    for table in tables[:15]:
        # Build list of text surfaces to scan: headers, caption, first 3 body rows
        detected = _detect_scale_from_text(" ".join(_table_text_surfaces(table)))
        if detected != "unknown":
            return detected

    for table in tables[:15]:
        surfaces: list[str] = _table_text_surfaces(table, row_limit=0)
        if _table_allows_extended_unit_scan(table):
            for row in (table.rows or [])[:20]:
                surfaces.append(" ".join(str(cell) for cell in row))

        if _explicit_currency_million_hits(" ".join(surfaces)):
            return "millions"

    # Appendix 4D/4E summary tables sometimes express every selected value as
    # an explicit full-dollar amount (e.g. "$138,176,320") without a separate
    # "$" column header. Treat that as source-unit evidence for raw units after
    # all scaled-unit and currency-million checks have had priority.
    for table in tables[:15]:
        if not _table_allows_extended_unit_scan(table):
            continue
        surfaces = [
            " ".join(str(cell) for cell in row)
            for row in (table.rows or [])[:20]
            if row
        ]
        if _APPENDIX_FULL_DOLLAR_VALUE_RE.search(" ".join(surfaces)):
            return "units"

    for table in tables or []:
        combined = " ".join(_table_text_surfaces(table, row_limit=8))
        if _has_financial_statement_context(combined) and _RAW_DOLLAR_UNIT_RE.search(
            combined
        ):
            return "units"

    # Scale Policy V1: a plain currency/$ column unit is an explicit raw-dollar
    # table unit, not "unknown". This is intentionally checked after all
    # thousands/millions/billions patterns so scaled columns still win.
    for table in tables[:15]:
        if _RAW_DOLLAR_UNIT_RE.search(" ".join(_table_text_surfaces(table))):
            return "units"
    return "unknown"


def _detect_currency_from_tables(tables) -> str | None:
    """
    Detect a dominant document currency from table headers/captions/body rows.

    Returns a 3-letter currency code when one currency has clear evidence,
    otherwise returns None. Row-level evidence is limited to canonical
    statement/highlight tables so foreign-currency note text does not override
    the filing currency.
    """
    explicit_header_currency = _detect_explicit_currency_million_header(tables)
    if explicit_header_currency:
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
    result.setdefault("currency", "AUD")
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
        "attributable to",  # continued IS owner-attributable rows
        "owners of the parent",  # bilingual continued IS tables
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
_INCOME_STATEMENT_MERGE_THRESHOLD = 3
_INCOME_STATEMENT_MERGE_PAGE_WINDOW = 2

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
    best_headers = max(candidates, key=lambda x: x[0])[1].headers
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
    )


def _merge_income_statement_tables(
    candidates: list[tuple[int, Any]],
) -> Any:
    """Merge immediate income-statement continuation tables.

    Bilingual annual reports can split the consolidated statement of profit or
    loss across consecutive PDF pages. The first page contains revenue/operating
    profit, while the continuation page contains the owner-attributable profit
    rows. Keeping only the highest-scoring first page lets the model select total
    profit instead of parent-owner profit.
    """
    from app.services.docling_extract import DoclingTable

    ordered = sorted(candidates, key=lambda item: item[1].page_number)
    best_table = max(candidates, key=lambda item: item[0])[1]
    best_headers = list(best_table.headers or [])
    best_page = ordered[0][1].page_number
    target_width = max(
        [len(best_headers)]
        + [len(row) for _score, table in candidates for row in (table.rows or [])],
        default=0,
    )

    merged_rows: list[list[str]] = []
    seen_rows: set[str] = set()
    if best_headers:
        header = best_headers + [""] * max(0, target_width - len(best_headers))
        merged_rows.append(header[:target_width])
        seen_rows.add(" ".join(header).strip().lower())

    for _score, table in ordered:
        for row in table.rows:
            key = " ".join(str(c) for c in row).strip().lower()
            if key in seen_rows or not key:
                continue
            seen_rows.add(key)
            normalized_row = [str(cell) for cell in row]
            if target_width:
                if len(normalized_row) < target_width:
                    normalized_row = normalized_row + [""] * (
                        target_width - len(normalized_row)
                    )
                elif len(normalized_row) > target_width:
                    normalized_row = normalized_row[:target_width]
            merged_rows.append(normalized_row)

    logger.info(
        "merged %d income statement tables into synthetic table (%d rows, pages %s)",
        len(candidates),
        len(merged_rows),
        sorted(set(t.page_number for _score, t in candidates)),
    )

    return DoclingTable(
        page_number=best_page,
        caption="Merged income statement",
        rows=merged_rows,
        headers=best_headers,
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
    for table in tables:
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
    for label in _TABLE_KEYWORDS:
        if pools[label]:
            winner_score, _winner_not_toc, winner_table = max(
                pools[label], key=lambda x: (x[0], x[1], -x[2].page_number)
            )
            labelled[label] = winner_table
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
        if len(cf_candidates) > 1:
            labelled["cashflow_statement"] = _merge_cf_tables(cf_candidates)

    if pools["income_statement"] and labelled.get("income_statement") is not None:
        winner = labelled["income_statement"]
        winner_page = int(getattr(winner, "page_number", 0) or 0)
        is_candidates = [
            (score, tbl)
            for score, _not_toc, tbl in pools["income_statement"]
            if score >= _INCOME_STATEMENT_MERGE_THRESHOLD
            and abs(int(getattr(tbl, "page_number", 0) or 0) - winner_page)
            <= _INCOME_STATEMENT_MERGE_PAGE_WINDOW
        ]
        if len(is_candidates) > 1:
            labelled["income_statement"] = _merge_income_statement_tables(is_candidates)

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
            _is_explicit_net_debt_evidence(row[0]) and _row_has_numeric_payload(row)
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

    def _table_has_balance_sheet_section_context(
        table: DoclingTable, row_index: int
    ) -> bool:
        """Detect summary tables where a Balance Sheet section owns the net-debt row."""
        start = max(0, row_index - 6)
        for idx in range(start, row_index):
            row_text = _normalize_locator_text(
                " ".join(str(cell) for cell in table.rows[idx])
            )
            if row_text in {"balance sheet", "statement of financial position"}:
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
        if not _is_explicit_net_debt_evidence(row[0]) or not _row_has_numeric_payload(row):
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
        if _table_has_balance_sheet_section_context(table, row_index):
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
  "Statutory EBIT", or "Operating income".
  Do NOT use Net Profit as a proxy.
  Do NOT use generic "Profit before income tax", "Loss before income tax",
  "Profit before taxation", "Loss before taxation", "Profit before tax", or
  "Cash profit before tax" as EBIT unless the same row is explicitly labeled
  EBIT or operating profit/income.
  CRITICAL: "Profit before credit impairment and income tax" is NOT ebit.
  Generic profit/loss-before-tax rows are also NOT ebit unless the same row is
  explicitly labeled EBIT or operating profit/income.
- np_attributable: extract profit/loss after tax attributable to owners, shareholders,
  ordinary equity holders, or security holders when that row is explicitly present.
  Do NOT use total comprehensive income attributable to owners as a substitute.
  If no owner-attributable profit/loss row is present, use the explicit statutory
  profit/loss after income tax for the period, not total comprehensive income.
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
    if not rows:
        return ""
    lines = []
    for i, row in enumerate(rows[:max_rows]):
        line = " | ".join(str(c) for c in row)
        lines.append(line)
        if i == 0:
            lines.append(" | ".join("---" for _ in row))
    return "\n".join(lines)


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
) -> dict | None:
    """Extract metrics from a single labelled table via one LLM call.

    Returns a tagged extraction dict, or None if extraction fails entirely.
    This function is safe to call from multiple threads — it uses only
    thread-local variables and thread-safe LLM/routing infrastructure.
    """
    bundle = prompt_bundle or resolve("default")
    metrics = _METRIC_SCHEMA_BY_TABLE.get(table_type, METRIC_FIELDS)
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
    sanity_cap = _native_currency_sanity_cap(pass1_result.get("currency"))

    def _build_prompt(table_markdown: str) -> str:
        return bundle.pass3a.format(
            period_type=pass1_result.get("report_type", "?"),
            period_end=pass1_result.get("period_end", "?"),
            currency=pass1_result.get("currency", "AUD"),
            scale=scale,
            table_type=table_type,
            table_markdown=table_markdown,
            metric_list=", ".join(metrics),
            metric_schema=metric_schema,
        )

    def _build_output(
        raw_payload: dict[str, Any], *, table_markdown: str
    ) -> dict[str, Any]:
        # Support both old flat format and new nested format
        metrics_payload = raw_payload.get("metrics")
        if not isinstance(metrics_payload, dict):
            metrics_payload = raw_payload

        # shares_outstanding is always an absolute count — the prompt instructs the LLM
        # to output the absolute number (e.g. 5057000000 not 5057 when the table says
        # "5,057 (Million)"). No post-hoc scale multiplication needed.
        _COUNT_METRICS = {"shares_outstanding"}
        extracted = {
            "_source": table_type,
            "_page_number": getattr(table, "page_number", None),
            "_thinking": raw_payload.get("thinking"),
            "_markdown": table_markdown,
            "row_refs": raw_payload.get("row_refs", {}),
        }
        for metric_name in metrics:
            val = metrics_payload.get(metric_name)
            if val is not None:
                try:
                    raw_float = float(val)
                    effective_multiplier = (
                        1 if metric_name in _COUNT_METRICS else multiplier
                    )
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
                except (TypeError, ValueError):
                    extracted[metric_name] = None
            else:
                extracted[metric_name] = None

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
            row_labels = [
                _normalize_filter_text(row[0]) for row in table.rows if row
            ]
            weighted_average_only = bool(row_labels) and all(
                "weightedaverage" in label or not label for label in row_labels[1:]
            )
            # An absolute count (≥ 1M) is self-evident: the LLM was instructed
            # to return the absolute share count, so a value this large cannot
            # be an unscaled row number from a dollar-denominated column.
            # Only apply the null guard when the value is small enough that it
            # could be a scaled placeholder rather than a genuine count.
            _already_absolute = abs(shares_val) >= _MIN_PLAUSIBLE_SHARES
            if weighted_average_only or (
                not has_share_count_evidence and not _already_absolute
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
            elif scale in ("thousands", "millions"):
                doc_mult = SCALE_MULTIPLIERS.get(scale, 1)
                extracted["shares_outstanding"] = shares_val * doc_mult
                logger.info(
                    "shares_outstanding scaled ×%d (doc-level scale=%s): %.0f → %.0f",
                    doc_mult,
                    scale,
                    shares_val,
                    extracted["shares_outstanding"],
                )

        extracted["row_refs"] = raw_payload.get("row_refs", {})
        extracted["period_col"] = raw_payload.get("period_col")
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
        if table_type == "net_debt_note" and extracted.get("net_debt") is None:
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
                    "Recovered explicit net_debt deterministically from page %s row=%r period_col=%r",
                    getattr(table, "page_number", "?"),
                    row_ref,
                    period_col,
                )
        if (
            table_type == "net_debt_note"
            and extracted.get("net_debt") is not None
            and not extracted["row_refs"].get("net_debt")
        ):
            extracted["row_refs"]["net_debt"] = "Net debt"
        return extracted

    prompt = _build_prompt(markdown)
    selected_markdown = markdown

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
        except Exception as e2:
            logger.error("Pass 3a retry also failed for %s: %s", table_type, e2)
            return None

    selected_raw = raw
    out = _build_output(raw, table_markdown=selected_markdown)

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
                full_out = _build_output(full_raw, table_markdown=full_markdown)
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
                except Exception:
                    logger.exception("Pass 3a thread failed for %s", tt)
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
            )
            if out is not None:
                results.append(out)

    return results


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

_MEETING_RESULTS_NOTICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:^|[-_\s])results?[-_\s]+of[-_\s]+(?:\d{4}[-_\s]+)?"
        r"(?:annual[-_\s]+general[-_\s]+meeting|agm)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(r"\bresults?\s+of\s+meeting\b", re.IGNORECASE),
    re.compile(
        r"\b(?:annual\s+general\s+meeting|agm)\b.*\b(?:poll\s+results?|proxy\s+votes?|"
        r"resolutions?\s+(?:were\s+)?(?:passed|decided)|section\s+251aa|"
        r"listing\s+rule\s+3\.13\.2)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])result[-_\s]+of[-_\s]+"
        r"(?:annual[-_\s]+general[-_\s]+meeting|agm)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])results?[-_\s]+of[-_\s]+"
        r"(?:[A-Za-z0-9]+[-_\s]+){0,8}"
        r"(?:annual[-_\s]+general[-_\s]+meeting|agm)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)

_MEETING_NOTICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bnotice[-_\s]+of[-_\s]+(?:annual[-_\s]+general[-_\s]+meeting|meeting)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bupcoming[-_\s]+annual[-_\s]+general[-_\s]+meeting\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bannual[-_\s]+general[-_\s]+meeting\b.*\b(?:notice[-_\s]+of[-_\s]+meeting|"
        r"proxy[-_\s]+form|voting|shareholders?[-_\s]+are[-_\s]+encouraged|"
        r"explanatory[-_\s]+memorandum)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bproxy[-_\s]+form\b.*\bannual[-_\s]+general[-_\s]+meeting\b",
        re.IGNORECASE,
    ),
)

_FORMAL_FINANCIAL_STATEMENT_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bappendix\s+4[cde]\b", re.IGNORECASE),
    re.compile(r"\bappendix\s+5b\b", re.IGNORECASE),
    re.compile(r"\bquarterly\s+cash\s+flow\s+report\b", re.IGNORECASE),
    re.compile(r"\bresults?\s+for\s+announcement\s+to\s+the\s+market\b", re.IGNORECASE),
    re.compile(r"\bstatement\s+of\s+(?:profit|financial\s+position|cash\s+flows?)\b", re.IGNORECASE),
    re.compile(r"\bconsolidated\s+statement\b", re.IGNORECASE),
)

_NON_STATEMENT_FINANCIAL_UPDATE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfinancial\s+update\b", re.IGNORECASE),
)

_NON_STATEMENT_FINANCIAL_UPDATE_CONTEXT: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bahead\s+of\s+(?:its\s+)?planned\s+release\b", re.IGNORECASE),
    re.compile(r"\bsubject\s+to\s+audit\b", re.IGNORECASE),
    re.compile(r"\bheadline\s+financial\s+information\b", re.IGNORECASE),
    re.compile(r"\banticipates\s+the\s+following\s+headline\b", re.IGNORECASE),
)

_PROTECTED_REPORT_RESULT_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:^|[-_\s])(?:annual|full[-_\s]+year|fy\d{2,4})[-_\s]+"
        r"(?:financial[-_\s]+)?(?:report|results?|accounts?)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:half[-_\s]+year|hy\d{2,4}|h[12]|[12]h)[-_\s]+"
        r"(?:financial[-_\s]+)?(?:report|results?|accounts?)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)

_CAPITAL_MANAGEMENT_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS: tuple[
    re.Pattern[str], ...
] = (
    re.compile(
        r"\b(?:on[-_\s]+market[-_\s]+|off[-_\s]+market[-_\s]+|selective[-_\s]+)?"
        r"(?:ordinary[-_\s]+shares?|shares?|securities?)[-_\s]+"
        r"buy[-_\s]*backs?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbuy[-_\s]*backs?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bto[-_\s]+buy[-_\s]+back[-_\s]+up[-_\s]+to\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])results?[-_\s]+of[-_\s]+"
        r"(?:share|unit|security|securities)[-_\s]+purchase[-_\s]+plan"
        r"(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:share|unit|security|securities)[-_\s]+purchase[-_\s]+plan"
        r"[-_\s]+(?:results?|upp[-_\s]+results?|final[-_\s]+issue|"
        r"correction[-_\s]+to[-_\s]+announcement)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:completion|final[-_\s]+issue)[-_\s]+of[-_\s]+"
        r"(?:share|unit|security|securities)[-_\s]+purchase[-_\s]+plan"
        r"(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)

_PRE_RESULTS_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS: tuple[
    re.Pattern[str], ...
] = (
    re.compile(
        r"(?:^|[-_\s])(?:notable[-_\s]+items?|pre[-_\s]+results?)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:full|half)[-_\s]+year[-_\s]+\d{2,4}[-_\s]+notable[-_\s]+items?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bresults?\s+are\s+scheduled\s+to\s+be\s+announced\b",
        re.IGNORECASE,
    ),
)

_OPERATIONAL_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS: tuple[
    re.Pattern[str], ...
] = (
    re.compile(r"\bpurchase[-_\s]+orders?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:binding[-_\s]+)?(?:sale|sales|supply|customer|client|commercial)"
        r"[-_\s]+agreement\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:customer|client|commercial|sale|sales|purchase[-_\s]+order)"
        r"\b.{0,80}\bagreement\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bsigns?\b.{0,80}\b(?:client|customer|contract|agreement)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:client|customer|contract|agreement)\b.{0,80}"
        r"\b(?:revenue|fee|signed|awarded|secured)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bgrows?[-_\s]+q[1-4][\-_\s]+revenue\b", re.IGNORECASE),
    re.compile(
        r"\b(?:new|first|major)[-_\s]+(?:client|customer|contract)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:capital[-_\s]+rais(?:e|ing)|institutional[-_\s]+placement|"
        r"placement[-_\s]+to[-_\s]+raise)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])raises?\b[-_\s\w$,.]{0,60}\b\d+(?:\.\d+)?\s*"
        r"(?:m|million|b|billion)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:launch|launched|launches|rollout|introduction)"
        r"[-_\s]+of[-_\s]+"
        r"(?:[A-Za-z0-9]+[-_\s]+){0,8}"
        r"(?:services?|products?|platform|vertical|solution|program|programme)"
        r"(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)

_NON_FINANCIAL_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS: tuple[
    re.Pattern[str], ...
] = (
    re.compile(
        r"\b(?:drill(?:ing)?|assay|rc|diamond)[-_\s\w,.%/@]{0,120}"
        r"\bresults?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bresults?\b[-_\s\w,.%/@]{0,120}"
        r"\b(?:drill(?:ing)?|assay|rc|diamond)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:excellent[-_\s]+)?base[-_\s]+metals[-_\s]+results?"
        r"(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:annual[-_\s]+general[-_\s]+meeting|agm)"
        r"[-_\s]+presentations?(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])(?:notice[-_\s]+of[-_\s]+)?"
        r"(?:(?:full|half)[-_\s]+year[-_\s]+|quarterly[-_\s]+)?"
        r"results?[-_\s]+(?:briefing|presentations?|webcast|webinar|teleconference)"
        r"(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(r"\bprogramme[-_\s]+results?\b", re.IGNORECASE),
    re.compile(
        r"\bmineral[-_\s]+resource[-_\s]+(?:estimate|update|model)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bmre\b.{0,80}\b(?:planned|update|reported)\b", re.IGNORECASE),
    re.compile(r"(?:^|[-_\s])monthly[-_\s]+report(?![A-Za-z0-9])", re.IGNORECASE),
    re.compile(
        r"(?:^|[-_\s])annual[-_\s]+asx[-_\s]+shareholder[-_\s]+summary"
        r"(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])shareholder[-_\s]+summary(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])additional[-_\s]+asx[-_\s]+information(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[-_\s])distribution[-_\s]+of[-_\s]+shareholders(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)

_STANDALONE_QUARTERLY_ACTIVITIES_REPORT_PATTERN = re.compile(
    r"(?:^|[-_\s])"
    r"(?:(?:march|june|september|december)[-_\s]+)?"
    r"quarterly[-_\s]+activities[-_\s]+report"
    r"(?=$|\.pdf\b|[-_\s]+[0-9a-f]{4,}(?:[-_\s][0-9a-f]{2,})*)",
    re.IGNORECASE,
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
        re.compile(r"\bappendix\s+4c\b", re.IGNORECASE),
    ),
    (
        "Q",
        "quarterly_source_phrase",
        re.compile(r"\bquarterly\s+(?:cash\s+flow|activities|report)\b", re.IGNORECASE),
    ),
)

_SOURCE_YEAR_TEXT_PATTERN = r"\d\s*\d\s*\d\s*\d"

_SOURCE_DATE_TEXT_PATTERN = (
    r"(?P<date>"
    r"\d{1,2}(?:st|nd|rd|th)?\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+"
    rf"{_SOURCE_YEAR_TEXT_PATTERN}"
    rf"|{_SOURCE_YEAR_TEXT_PATTERN}\s*-\s*\d{{1,2}}\s*-\s*\d{{1,2}}"
    r")"
)

_SOURCE_PERIOD_END_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "A",
        "year_ended_explicit_date",
        re.compile(
            rf"\b(?:for\s+the\s+|the\s+)?(?:financial\s+)?"
            rf"(?<!half[-\s])year\s+ended\s+"
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
            rf"\s+ended(?:\s+\([^)]*\))?\s+{_SOURCE_DATE_TEXT_PATTERN}",
            re.IGNORECASE,
        ),
    ),
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

_PROSE_HIGHLIGHT_VALUE = (
    r"(?:AUD\s*)?"
    r"(?:A\$|\$A|\$)?\s*"
    r"(?P<value>\(?-?\d+(?:,\d{3})*(?:\.\d+)?\)?)\s*"
    r"(?P<unit>million|millions|m|billion|billions|bn|b)\b"
)

_PROSE_HIGHLIGHT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "revenue",
        re.compile(
            rf"\b(?:1h|h1|first\s+half|half[-\s]?year)?\s*"
            rf"revenue\s+of\s+{_PROSE_HIGHLIGHT_VALUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "np_attributable",
        re.compile(
            rf"\bNPAT\b(?:\s+\w+){{0,3}}\s+(?:of\s+|at\s+)?"
            rf"{_PROSE_HIGHLIGHT_VALUE}",
            re.IGNORECASE,
        ),
    ),
    (
        "cash_end",
        re.compile(
            rf"\bcash\s+of\s+{_PROSE_HIGHLIGHT_VALUE}\s+as\s+at\b",
            re.IGNORECASE,
        ),
    ),
)

_PROSE_HIGHLIGHT_BLOCKERS = (
    "guidance",
    "forecast",
    "projected",
    "projection",
    "target",
    "expected",
)

_EBIT_LABEL_BLOCKERS = (
    "ebitda",
    "earnings before interest tax depreciation",
    "earnings before interest, tax, depreciation",
    "earnings before interest and tax depreciation",
    "earnings before interest, taxes, depreciation",
)

_EBIT_PRE_TAX_LABEL_BLOCKERS = (
    "profit before income tax",
    "loss before income tax",
    "profit/(loss) before income tax",
    "profit or loss before income tax",
    "profit before taxation",
    "loss before taxation",
    "profit before tax",
    "loss before tax",
    "cash profit before tax",
    "laba sebelum pajak",
)

_EBIT_PRE_TAX_EXPLICIT_ALLOW_MARKERS = (
    "ebit",
    "operating profit",
    "operating income",
    "profit from operations",
    "profit/(loss) from operating activities",
    "laba usaha",
)


def _extract_shares_from_prose(sections: list[dict]) -> tuple[float | None, str]:
    """Scan prose sections for share count mentions.

    Returns (shares_outstanding, provenance_string).
    Returns (None, "") if no match found.
    """
    # Filter to sections likely to mention share capital
    candidates = [
        s for s in sections if s.get("text") and _SHARE_NOTE_RE.search(s["text"])
    ]
    # Also scan all sections if no note-specific candidates found
    if not candidates:
        candidates = [s for s in sections if s.get("text")]

    for section in candidates:
        text = section["text"]
        page = section.get("page", "?")
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


def _parse_prose_highlight_value(match: re.Match[str]) -> float | None:
    raw = str(match.group("value") or "").strip()
    unit = str(match.group("unit") or "").strip().lower()
    multiplier = _SOURCE_UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()").replace(",", "")
    try:
        value = float(raw) * multiplier
    except ValueError:
        return None
    matched_text = match.group(0).lower()
    if "loss" in matched_text or negative:
        value = -abs(value)
    return value


def _section_page_number(section: dict) -> int | None:
    try:
        return int(section.get("page"))
    except (TypeError, ValueError):
        return None


def _extract_metric_highlights_from_prose(
    sections: list[dict],
) -> tuple[dict[str, float], dict[str, str], dict[str, str]]:
    """Extract explicit current-period financial facts from prose highlights.

    This fallback is intentionally narrow: it reads only explicit money values
    tied to canonical metric labels and skips forecast/guidance contexts. It is
    not a substitute for table extraction and must not map EBITDA to EBIT.
    """
    metrics: dict[str, float] = {}
    provenance: dict[str, str] = {}
    row_refs: dict[str, str] = {}
    candidates = [
        section
        for section in sections
        if section.get("text")
        and (page := _section_page_number(section)) is not None
        and 0 < page <= 3
    ]
    if not candidates:
        candidates = [section for section in sections if section.get("text")][:8]

    for section in candidates:
        text = str(section.get("text") or "")
        page = section.get("page", "?")
        for metric_name, pattern in _PROSE_HIGHLIGHT_PATTERNS:
            if metric_name in metrics:
                continue
            match = pattern.search(text)
            if not match:
                continue
            matched_text = " ".join(match.group(0).split())
            context = text[max(0, match.start() - 80) : match.end()].lower()
            if metric_name == "revenue" and any(
                blocker in context for blocker in _PROSE_HIGHLIGHT_BLOCKERS
            ):
                continue
            value = _parse_prose_highlight_value(match)
            if value is None:
                continue
            metrics[metric_name] = value
            row_refs[metric_name] = matched_text[:120]
            provenance[metric_name] = f"prose_highlight:page_{page}:{matched_text[:120]}"

    return metrics, provenance, row_refs


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


def is_advisory_only_document(title: Any, first_page_text: Any) -> bool:
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    return any(pattern.search(text) for pattern in _ADVISORY_ONLY_DOCUMENT_PATTERNS)


def _is_advisory_only_document(title: Any, first_page_text: Any) -> bool:
    return is_advisory_only_document(title, first_page_text)


def _is_meeting_results_notice(title: Any, first_page_text: Any) -> bool:
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    return any(pattern.search(text) for pattern in _MEETING_RESULTS_NOTICE_PATTERNS)


def _is_meeting_notice(title: Any, first_page_text: Any) -> bool:
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    return any(pattern.search(text) for pattern in _MEETING_NOTICE_PATTERNS)


def _has_formal_financial_statement_marker(text: str) -> bool:
    return any(pattern.search(text) for pattern in _FORMAL_FINANCIAL_STATEMENT_MARKERS)


def _has_protected_report_result_title(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PROTECTED_REPORT_RESULT_TITLE_PATTERNS)


def _is_unaudited_non_statement_financial_update(
    title: Any,
    first_page_text: Any,
) -> bool:
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    if not any(pattern.search(text) for pattern in _NON_STATEMENT_FINANCIAL_UPDATE_MARKERS):
        return False
    if _has_formal_financial_statement_marker(text):
        return False

    # Title-only candidate selection may only have a filename such as
    # "financial-update". That is a likely update notice, not a formal report.
    if not str(first_page_text or "").strip():
        return True

    return any(
        pattern.search(text) for pattern in _NON_STATEMENT_FINANCIAL_UPDATE_CONTEXT
    )


def _is_capital_management_update_without_formal_statements(
    title: Any,
    first_page_text: Any,
) -> bool:
    title_text = _combined_source_text(title)
    if (
        title_text
        and _has_protected_report_result_title(title_text)
        and any(
            pattern.search(title_text)
            for pattern in _CAPITAL_MANAGEMENT_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS
        )
    ):
        return False

    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    if _has_formal_financial_statement_marker(text):
        return False
    if _detect_source_period_evidence(title, first_page_text).get("period_type") in {
        "A",
        "H",
        "Q",
    }:
        return False
    return any(
        pattern.search(text)
        for pattern in _CAPITAL_MANAGEMENT_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS
    )


def _is_pre_results_update_without_formal_statements(
    title: Any,
    first_page_text: Any,
) -> bool:
    title_text = _combined_source_text(title)
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    if _has_formal_financial_statement_marker(text):
        return False
    if title_text and _has_protected_report_result_title(title_text):
        return False
    return any(
        pattern.search(text)
        for pattern in _PRE_RESULTS_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS
    )


def _is_operational_update_without_formal_statements(
    title: Any,
    first_page_text: Any,
) -> bool:
    title_text = _combined_source_text(title)
    text = _combined_source_text(title, first_page_text)
    if (
        title_text
        and not _has_formal_financial_statement_marker(text)
        and _STANDALONE_QUARTERLY_ACTIVITIES_REPORT_PATTERN.search(title_text)
    ):
        return True

    if (
        title_text
        and not _has_formal_financial_statement_marker(title_text)
        and _detect_source_period_evidence(title_text, "").get("period_type")
        not in {"A", "H", "Q"}
        and any(
            pattern.search(title_text)
            for pattern in _OPERATIONAL_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS
        )
    ):
        return True

    if not text:
        return False
    if _has_formal_financial_statement_marker(text):
        return False
    if _detect_source_period_evidence(title, first_page_text).get("period_type") in {
        "A",
        "H",
        "Q",
    }:
        return False
    return any(
        pattern.search(text)
        for pattern in _OPERATIONAL_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS
    )


def _is_non_financial_update_without_formal_statements(
    title: Any,
    first_page_text: Any,
) -> bool:
    text = _combined_source_text(title, first_page_text)
    if not text:
        return False
    if _has_formal_financial_statement_marker(text):
        return False
    if _detect_source_period_evidence(title, first_page_text).get("period_type") in {
        "A",
        "H",
        "Q",
    }:
        return False
    return any(
        pattern.search(text)
        for pattern in _NON_FINANCIAL_UPDATE_WITHOUT_FORMAL_STATEMENT_MARKERS
    )


def _detect_source_period_evidence(title: Any, first_page_text: Any) -> dict[str, Any]:
    """
    Detect explicit source-period wording without changing the extracted period.

    This is a contradiction guard only: ambiguous/multiple source-period signals are
    left reportable but non-blocking so the gate does not infer a corrected period.
    """
    text = _combined_source_text(title, first_page_text)
    hits: list[dict[str, str]] = []
    for period_type, reason, pattern in _SOURCE_PERIOD_PATTERNS:
        if pattern.search(text):
            hits.append({"period_type": period_type, "reason": reason})

    seen_types = sorted({hit["period_type"] for hit in hits})
    if len(seen_types) == 1:
        return {
            "period_type": seen_types[0],
            "reason": hits[0]["reason"],
            "hits": hits,
        }
    if len(seen_types) > 1:
        return {"period_type": None, "reason": "ambiguous", "hits": hits}
    return {"period_type": None, "reason": "not_detected", "hits": []}


def _normalize_source_date_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)
    return re.sub(
        r"\b(?:\d\s*){4}\b",
        lambda match: re.sub(r"\s+", "", match.group(0)),
        text,
    )


def _detect_source_period_end_evidence(title: Any, source_text: Any) -> dict[str, Any]:
    """
    Detect explicit source period-end dates from typed reporting-period phrases.

    This helper is deliberately narrow: it accepts phrases such as
    "for the year ended 31 December 2025" and refuses ambiguous/multiple dates
    instead of inferring from publication dates, filenames, or loose references.
    """

    text = _combined_source_text(title, source_text)
    hits: list[dict[str, str]] = []
    for period_type, reason, pattern in _SOURCE_PERIOD_END_PATTERNS:
        for match in pattern.finditer(text):
            raw_date = _normalize_source_date_text(match.group("date"))
            parsed = parse_period_end(raw_date)
            if parsed is None:
                continue
            hits.append(
                {
                    "period_type": period_type,
                    "period_end": parsed.isoformat(),
                    "reason": reason,
                    "evidence": " ".join(match.group(0).split())[:200],
                }
            )

    unique_dates = sorted({hit["period_end"] for hit in hits})
    unique_types = sorted({hit["period_type"] for hit in hits})
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


def _apply_source_period_end_type_correction(
    pass1: dict[str, Any],
    source_period_end_evidence: dict[str, Any],
) -> None:
    """Correct Pass 1 period type only from unambiguous typed source-date evidence."""

    source_period_type = str(source_period_end_evidence.get("period_type") or "").strip()
    source_period_end = str(source_period_end_evidence.get("period_end") or "").strip()
    if source_period_type not in {"A", "H", "Q"} or not source_period_end:
        return

    current_period_type = str(pass1.get("report_type") or "").strip()
    if current_period_type == source_period_type:
        return
    if current_period_type and current_period_type not in {"A", "H", "Q"}:
        return

    pass1["_source_period_type_correction"] = {
        "from": current_period_type or None,
        "to": source_period_type,
        "reason": str(source_period_end_evidence.get("reason") or "").strip()
        or "explicit_source_period_end",
        "period_end": source_period_end,
    }
    pass1["report_type"] = source_period_type


def _apply_source_period_end_correction(
    pass1: dict[str, Any],
    source_period_end_evidence: dict[str, Any],
) -> None:
    """Correct Pass 1 period end only from unambiguous typed source-date evidence."""

    source_period_type = str(source_period_end_evidence.get("period_type") or "").strip()
    source_period_end = str(source_period_end_evidence.get("period_end") or "").strip()
    if source_period_type not in {"A", "H", "Q"} or not source_period_end:
        return

    current_period_type = str(pass1.get("report_type") or "").strip()
    if current_period_type in {"A", "H", "Q"} and current_period_type != source_period_type:
        return

    source_date = parse_period_end(source_period_end)
    current_period_end = str(pass1.get("period_end") or "").strip()
    current_date = parse_period_end(current_period_end)
    if source_date is None or current_date == source_date:
        return

    pass1["_source_period_end_correction"] = {
        "from": current_date.isoformat() if current_date is not None else None,
        "to": source_date.isoformat(),
        "reason": str(source_period_end_evidence.get("reason") or "").strip()
        or "explicit_source_period_end",
    }
    pass1["period_end"] = source_date.isoformat()


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


def _early_period_table_text(
    tables: list[Any],
    *,
    max_page: int = 4,
    max_tables: int = 12,
    max_chars: int = 6000,
) -> str:
    """Return early table text for typed source-period evidence only."""
    selected: list[str] = []
    for table in tables:
        try:
            page_number = int(getattr(table, "page_number", 0) or 0)
        except (TypeError, ValueError):
            page_number = 0
        if page_number and page_number > max_page:
            continue

        parts: list[str] = []
        caption = str(getattr(table, "caption", "") or "").strip()
        if caption:
            parts.append(caption)
        headers = getattr(table, "headers", []) or []
        if headers:
            parts.append(" ".join(str(cell) for cell in headers if str(cell).strip()))
        for row in getattr(table, "rows", []) or []:
            row_text = " ".join(str(cell) for cell in row if str(cell).strip()).strip()
            if row_text:
                parts.append(row_text)
        rows = [list(row) for row in getattr(table, "rows", []) or []]
        width = max((len(row) for row in rows), default=0)
        for col_idx in range(width):
            column_text = " ".join(
                str(row[col_idx]).strip()
                for row in rows
                if col_idx < len(row) and str(row[col_idx]).strip()
            )
            if column_text:
                parts.append(column_text)
        table_text = " ".join(parts).strip()
        if table_text:
            selected.append(table_text)
        if len(selected) >= max_tables:
            break

    return " ".join(selected)[:max_chars]


def _formal_statement_source_text(
    sections: list[dict],
    tables: list[Any],
    *,
    max_chars: int = 8000,
) -> str:
    """Return explicit formal-statement text from late annual-report pages."""

    selected: list[str] = []
    page_texts: dict[int, list[str]] = {}

    for section in sections or []:
        if isinstance(section, dict):
            text = str(section.get("text") or "").strip()
            page = section.get("page")
        else:
            text = str(getattr(section, "text", "") or "").strip()
            page = getattr(section, "page", None)
        if not text:
            continue
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            continue
        page_texts.setdefault(page_number, []).append(text)

    for page_number in sorted(page_texts):
        page_text = " ".join(page_texts[page_number])
        if _has_financial_statement_context(page_text):
            selected.append(page_text)

    for table in tables or []:
        table_text = " ".join(_table_text_surfaces(table, row_limit=8))
        if _has_financial_statement_context(table_text):
            selected.append(table_text)

    return " ".join(selected)[:max_chars]


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
    if _is_meeting_results_notice(title, first_page_text):
        return SourceDocumentClassification(
            document_class="meeting_results_notice",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="meeting_results_notice",
            evidence=["meeting_results_notice_pattern"],
        )
    if _is_meeting_notice(title, first_page_text):
        return SourceDocumentClassification(
            document_class="meeting_notice",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="meeting_notice",
            evidence=["meeting_notice_pattern"],
        )
    if _is_unaudited_non_statement_financial_update(title, first_page_text):
        return SourceDocumentClassification(
            document_class="unaudited_financial_update_without_formal_statements",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="unaudited_financial_update_without_formal_statements",
            evidence=["financial_update_without_formal_statement_pattern"],
        )
    if _is_capital_management_update_without_formal_statements(title, first_page_text):
        return SourceDocumentClassification(
            document_class="capital_management_update_without_formal_statements",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="capital_management_update_without_formal_statements",
            evidence=["capital_management_without_formal_statement_pattern"],
        )
    if _is_pre_results_update_without_formal_statements(title, first_page_text):
        return SourceDocumentClassification(
            document_class="pre_results_update_without_formal_statements",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="pre_results_update_without_formal_statements",
            evidence=["pre_results_without_formal_statement_pattern"],
        )
    if _is_operational_update_without_formal_statements(title, first_page_text):
        return SourceDocumentClassification(
            document_class="operational_update_without_formal_statements",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="operational_update_without_formal_statements",
            evidence=["operational_update_without_formal_statement_pattern"],
        )
    if _is_non_financial_update_without_formal_statements(title, first_page_text):
        return SourceDocumentClassification(
            document_class="non_financial_update_without_formal_statements",
            extraction_candidate_allowed=False,
            canary_candidate_allowed=False,
            reason="non_financial_update_without_formal_statements",
            evidence=["non_financial_update_without_formal_statement_pattern"],
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
        if any(weak in normalized for weak in weak_markers):
            continue
        for rank, marker in enumerate(strong_markers):
            if marker in normalized and rank < best_rank:
                best_candidate = candidate
                best_rank = rank
                break
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


def _parse_statement_numeric_cell(cell: Any) -> float | None:
    """Parse statement cells, including Indonesian dot thousands separators."""
    text = str(cell or "").strip()
    if not text or text in {"-", "−", "–", "—"}:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    text = (
        text.replace("A$", "")
        .replace("US$", "")
        .replace("$", "")
        .replace("AUD", "")
        .replace("USD", "")
        .replace("IDR", "")
        .replace("Rp", "")
        .replace("RP", "")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .strip()
    )
    if _re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?", text):
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    if not text or not _re.search(r"\d", text):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if negative else value


def _markdown_table_rows(markdown: Any) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in str(markdown or "").splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if not any(cells):
            continue
        non_empty = [cell for cell in cells if cell]
        if non_empty and all(_re.fullmatch(r"-+", cell) for cell in non_empty):
            continue
        rows.append(cells)
    return rows


def _statement_row_label(row: list[str]) -> str:
    parts: list[str] = []
    for cell in row:
        text = str(cell or "").strip()
        if not text:
            continue
        if _parse_statement_numeric_cell(text) is not None:
            continue
        normalized = _normalise_evidence_row_ref(text)
        if normalized in {"note", "notes", "catatan/ notes"}:
            continue
        parts.append(text)
    return " ".join(parts).strip()[:220] or (str(row[0]).strip() if row else "")


def _statement_note_columns(rows: list[list[str]]) -> set[int]:
    note_columns: set[int] = set()
    for row in rows[:5]:
        for idx, cell in enumerate(row):
            normalized = _normalise_evidence_row_ref(cell)
            if normalized in {"note", "notes", "catatan/ notes"}:
                note_columns.add(idx)
    return note_columns


def _first_current_period_value(
    row: list[str], note_columns: set[int] | None = None
) -> float | None:
    parsed: list[tuple[str, float]] = []
    note_columns = note_columns or set()
    for idx, cell in enumerate(row[1:], start=1):
        if idx in note_columns:
            continue
        value = _parse_statement_numeric_cell(cell)
        if value is not None:
            parsed.append((str(cell or "").strip(), value))
    if not parsed:
        return None
    return parsed[0][1]


_NPAT_OWNER_MARKERS = (
    "owners of the parent",
    "owners of parent",
    "owner of the parent",
    "pemilik entitas induk",
    "ordinary equity holders",
    "shareholders of",
    "security holders",
    "members of",
)

_NPAT_PROFIT_CONTEXT_MARKERS = (
    "profit",
    "loss",
    "laba",
    "rugi",
)

_NPAT_ATTRIBUTABLE_CONTEXT_MARKERS = (
    "attributable",
    "diatribusikan",
)

_NPAT_TOTAL_COMPREHENSIVE_MARKERS = (
    "total comprehensive",
    "penghasilan komprehensif",
)

_NPAT_TOTAL_PROFIT_ROW_MARKERS = (
    "laba tahun berjalan",
    "profit for the year",
    "net profit for the year",
    "net loss for the year",
)

_NPAT_PROFIT_AFTER_TAX_ROW_MARKERS = (
    "profit/(loss) after income tax expense for the year",
    "profit/(loss) after income tax expense for the period",
    "profit/(loss) after income tax expense for the half-year",
    "profit after income tax expense for the year",
    "loss after income tax expense for the year",
)


def _find_owner_attributable_profit_row(
    rows: list[list[str]],
) -> tuple[float, str] | None:
    note_columns = _statement_note_columns(rows)
    for idx, row in enumerate(rows):
        label = _normalise_evidence_row_ref(_statement_row_label(row))
        if not any(marker in label for marker in _NPAT_OWNER_MARKERS):
            continue
        context_rows = rows[max(0, idx - 6) : idx]
        context = _normalise_evidence_row_ref(
            " ".join(_statement_row_label(context_row) for context_row in context_rows)
        )
        evidence_context = f"{context} {label}".strip()
        if any(
            marker in evidence_context for marker in _NPAT_TOTAL_COMPREHENSIVE_MARKERS
        ):
            continue
        if not any(
            marker in evidence_context for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS
        ):
            continue
        if not any(
            marker in evidence_context for marker in _NPAT_PROFIT_CONTEXT_MARKERS
        ):
            continue
        value = _first_current_period_value(row, note_columns)
        if value is None:
            continue
        row_label = _statement_row_label(row)
        row_is_self_contained = any(
            marker in label for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS
        ) and any(marker in label for marker in _NPAT_PROFIT_CONTEXT_MARKERS)
        if row_is_self_contained:
            return value, row_label
        heading = _statement_row_label(context_rows[-1]) if context_rows else ""
        return value, f"{heading} {row_label}".strip()
    return None


def _find_profit_after_tax_row(rows: list[list[str]]) -> tuple[float, str] | None:
    note_columns = _statement_note_columns(rows)
    for row in rows:
        label = _normalise_evidence_row_ref(_statement_row_label(row))
        if any(marker in label for marker in _NPAT_TOTAL_COMPREHENSIVE_MARKERS):
            continue
        if not any(marker in label for marker in _NPAT_PROFIT_AFTER_TAX_ROW_MARKERS):
            continue
        value = _first_current_period_value(row, note_columns)
        if value is None:
            continue
        return value, _statement_row_label(row)
    return None


def _np_attributable_selection_needs_repair(row_ref: Any, provenance: Any) -> bool:
    evidence = _normalise_evidence_row_ref(_combined_source_text(row_ref, provenance))
    if not evidence:
        return False
    if any(marker in evidence for marker in _NPAT_TOTAL_COMPREHENSIVE_MARKERS):
        return True
    owner_selected = any(marker in evidence for marker in _NPAT_OWNER_MARKERS)
    owner_context_is_profit = any(
        marker in evidence for marker in _NPAT_PROFIT_CONTEXT_MARKERS
    ) and any(marker in evidence for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS)
    if owner_selected and not owner_context_is_profit:
        return True
    if any(marker in evidence for marker in _NPAT_TOTAL_PROFIT_ROW_MARKERS) and not any(
        marker in evidence for marker in _NPAT_ATTRIBUTABLE_CONTEXT_MARKERS
    ):
        return True
    return False


def _repair_np_attributable_from_income_statement(
    *,
    merged_metrics: dict[str, Any],
    row_refs: dict[str, str],
    provenance: dict[str, str],
    markdown_map: dict[str, str],
    pass1_result: dict[str, Any],
) -> None:
    if merged_metrics.get("np_attributable") is None:
        return
    if not _np_attributable_selection_needs_repair(
        row_refs.get("np_attributable"),
        provenance.get("np_attributable"),
    ):
        return

    rows = _markdown_table_rows(markdown_map.get("np_attributable"))
    if not rows:
        return

    candidate = _find_owner_attributable_profit_row(rows)
    if candidate is None:
        candidate = _find_profit_after_tax_row(rows)
    if candidate is None:
        return

    raw_value, source_row_ref = candidate
    multiplier = SCALE_MULTIPLIERS.get(pass1_result.get("scale", "unknown"), 1)
    merged_metrics["np_attributable"] = raw_value * multiplier
    row_refs["np_attributable"] = source_row_ref
    provenance["np_attributable"] = f"income_statement:deterministic:{source_row_ref}"
    logger.info(
        "Repaired np_attributable from explicit income-statement row_ref=%r",
        source_row_ref,
    )


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
    for row_number, row in enumerate(header_rows):
        if row_number > 0 and row and str(row[0] or "").strip():
            trailing_cells = [str(cell or "").strip() for cell in row[1:]]
            if not any(trailing_cells):
                continue
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
    short_year = period.strftime("%y")
    exact_patterns = (
        rf"\b{period.day}\s+{period.strftime('%b').lower()}\s+{period.year}\b",
        rf"\b{period.day}\s+{period.strftime('%B').lower()}\s+{period.year}\b",
        rf"\b{period.day}\s+{period.strftime('%b').lower()}\s+{short_year}\b",
        rf"\b{period.day}\s+{period.strftime('%B').lower()}\s+{short_year}\b",
        rf"\b{period.strftime('%b').lower()}\s+{period.day},?\s+{period.year}\b",
        rf"\b{period.strftime('%B').lower()}\s+{period.day},?\s+{period.year}\b",
        rf"\b{period.strftime('%b').lower()}\s+{period.day},?\s+{short_year}\b",
        rf"\b{period.strftime('%B').lower()}\s+{period.day},?\s+{short_year}\b",
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


_PERIOD_COLUMN_DATE_RE = _re.compile(
    r"\b\d{1,2}\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}\b"
    r"|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{2,4}\b"
    r"|\b\d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2}\b",
    _re.IGNORECASE,
)


def _period_column_matches_reporting_period(
    period_col: Any, period_end: str | None
) -> bool:
    text = str(period_col or "").strip()
    if not text:
        return True
    period = parse_period_end(period_end)
    if period is None:
        return True

    saw_explicit_date = False
    for match in _PERIOD_COLUMN_DATE_RE.finditer(text):
        parsed = parse_period_end(match.group(0))
        if parsed is None:
            continue
        saw_explicit_date = True
        if parsed == period:
            return True

    if saw_explicit_date:
        return False
    return _net_debt_period_match_score(text, period_end) > 0


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
        row_ref = str(row[0] or "").strip()
        if not _is_explicit_net_debt_evidence(row_ref):
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
            return value, row_ref, context or None

        best_score = max(candidate[0] for candidate in numeric_candidates)
        best_candidates = [
            candidate for candidate in numeric_candidates if candidate[0] == best_score
        ]
        if best_score > 0 and len(best_candidates) == 1:
            _score, _col_idx, value, context = best_candidates[0]
            return value, row_ref, context or None

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
        "included in net debt",
        "derivatives included in net debt",
        "equity and net debt",
        "equity and net drawn debt",
        "included in net drawn debt",
        "net drawn debt ratio",
        "net drawn debt to",
        "net drawn debt and",
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
    row_refs: dict[str, str] = {}
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
                thinking_map[m] = extraction.get("_thinking") or ""
                markdown_map[m] = extraction.get("_markdown") or ""
                provenance[m] = f"{source}:{page_tag}:{row_ref}"
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
        thinking_map["net_debt"] = explicit_net_debt.get("_thinking") or ""
        markdown_map["net_debt"] = explicit_net_debt.get("_markdown") or ""
        provenance["net_debt"] = f"{source}:{page_tag}:{row_ref}"
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
                period_col = bs_result.get("period_col")
                cash_end = merged_metrics.get("cash_end")
                derived_net_debt = (
                    total_debt - cash_end
                    if total_debt is not None and cash_end is not None
                    else None
                )
                period_col_matches = _period_column_matches_reporting_period(
                    period_col,
                    pass1_result.get("period_end"),
                )
                if (
                    total_debt is not None
                    and cash_end is not None
                    and derived_net_debt is not None
                    and derived_net_debt >= 0
                    and period_col_matches
                    and _is_strong_total_debt_evidence(total_debt_row_ref, total_debt)
                ):
                    merged_metrics["net_debt"] = derived_net_debt
                    row_ref = f"total_debt({total_debt:.0f})-cash_end({cash_end:.0f})"
                    row_refs["net_debt"] = row_ref
                    provenance["net_debt"] = (
                        f"derived:balance_sheet:{row_ref}"
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
                elif derived_net_debt is not None and derived_net_debt < 0:
                    logger.info(
                        "Skipping negative derived net_debt from total_debt=%r cash_end=%r",
                        total_debt,
                        cash_end,
                    )
                elif total_debt is not None and cash_end is not None and not period_col_matches:
                    logger.info(
                        "Skipping net_debt derivation from non-current debt period_col=%r for period_end=%r",
                        period_col,
                        pass1_result.get("period_end"),
                    )
                elif total_debt is not None and cash_end is not None:
                    logger.info(
                        "Skipping net_debt derivation from weak debt evidence row_ref=%r value=%r",
                        total_debt_row_ref,
                        total_debt,
                    )

    _repair_np_attributable_from_income_statement(
        merged_metrics=merged_metrics,
        row_refs=row_refs,
        provenance=provenance,
        markdown_map=markdown_map,
        pass1_result=pass1_result,
    )

    # Prose fallback: shares_outstanding from note sections when tables yield null.
    # Banking filings (ANZ, WBC) often report share counts in prose Note 13/14
    # rather than in structured tables.
    if merged_metrics.get("shares_outstanding") is None and sections:
        prose_shares, prose_prov = _extract_shares_from_prose(sections)
        if prose_shares is not None:
            merged_metrics["shares_outstanding"] = prose_shares
            provenance["shares_outstanding"] = prose_prov
            # Extract row_ref from prose_prov (e.g., prose_note:page_12:The Company had...)
            prose_match = _EXTRACTION_RE.match(prose_prov)
            if prose_match:
                row_refs["shares_outstanding"] = prose_match.group("detail")

    if sections:
        prose_metrics, prose_provenance, prose_row_refs = (
            _extract_metric_highlights_from_prose(sections)
        )
        for metric_name, value in prose_metrics.items():
            if merged_metrics.get(metric_name) is not None:
                continue
            merged_metrics[metric_name] = value
            provenance[metric_name] = prose_provenance[metric_name]
            row_refs[metric_name] = prose_row_refs[metric_name]
            confidence_weighted_sum += 0.72
            confidence_weight += 1

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
        "source_period_type_correction": pass1_result.get(
            "_source_period_type_correction"
        ),
        "source_period_end_correction": pass1_result.get(
            "_source_period_end_correction"
        ),
        "source_document_classification": pass1_result.get(
            "_source_document_classification"
        ),
        "metrics": merged_metrics,
        "row_refs": row_refs,
        "thinking": thinking_map,
        "markdown_tables": markdown_map,
        "confidence_metrics": round(metric_confidence, 3),
        "provenance": provenance,
        **pass3b_result,  # risk_summary, risk_bullets, guidance_summary, material_changes, confidence_narrative
    }


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

# Over-scale threshold: values above $500B are almost certainly over-multiplied
# for AUD-like currencies. High-denomination native currencies need explicit
# source-unit support and a currency-specific cap; this does not perform FX
# conversion or rewrite extracted values.
_DEFAULT_NATIVE_SANITY_CAP = 500_000_000_000  # $500B
_HIGH_DENOMINATION_NATIVE_SANITY_CAPS = {
    "IDR": 10_000_000_000_000_000,  # Rp10 quadrillion
}


def _normalize_currency_code(raw: Any) -> str:
    if not raw or str(raw).strip().lower() == "null":
        return "AUD"
    return str(raw).strip().upper()


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


# ---------------------------------------------------------------------------
# Validation Gate
# ---------------------------------------------------------------------------

def _payload_metric_source_text(payload: dict, metric_name: str) -> str:
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    provenance = (
        payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    )
    return _combined_source_text(
        row_refs.get(metric_name),
        provenance.get(metric_name),
    )


def _metric_label_mismatch(payload: dict) -> tuple[str, str] | None:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    if metrics.get("ebit") is None:
        return None
    evidence = _normalise_evidence_row_ref(_payload_metric_source_text(payload, "ebit"))
    if not evidence:
        return None
    compact = evidence.replace(",", "")
    if any(blocker in compact for blocker in _EBIT_LABEL_BLOCKERS):
        return "ebit", "ebitda"
    if any(blocker in compact for blocker in _EBIT_PRE_TAX_LABEL_BLOCKERS) and not any(
        marker in compact for marker in _EBIT_PRE_TAX_EXPLICIT_ALLOW_MARKERS
    ):
        return "ebit", "pre_tax"
    return None


def _abstain_metric_label_mismatches(payload: dict) -> list[dict[str, str]]:
    """Null invalid metric values whose evidence label is explicitly disallowed."""

    abstentions: list[dict[str, str]] = []
    while True:
        mismatch = _metric_label_mismatch(payload)
        if mismatch is None:
            return abstentions

        metric_name, source_label = mismatch
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict) or metric_name not in metrics:
            return abstentions

        evidence = _payload_metric_source_text(payload, metric_name)
        abstentions.append(
            {
                "metric": metric_name,
                "reason": f"metric_label_mismatch:{source_label}",
                "evidence": evidence[:240],
            }
        )
        metrics[metric_name] = None
        payload[metric_name] = None
        for mapping_name in ("row_refs", "provenance", "thinking", "markdown_tables"):
            mapping = payload.get(mapping_name)
            if isinstance(mapping, dict):
                mapping.pop(metric_name, None)
        payload.setdefault("metric_abstentions", []).append(abstentions[-1])


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

    metrics = payload.get("metrics", {})
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

    non_null = [v for v in metrics.values() if v is not None]
    # Quarterly Appendix 5B filings are structurally limited to cash-flow metrics;
    # they never contain income-statement or balance-sheet rows.  A minimum of 1
    # non-null metric is sufficient to confirm a legitimate quarterly extraction,
    # provided all other gates (scale, period_end, confidence, sanity cap) pass.
    # Annual and half-year reports must still provide at least 3 non-null metrics.
    min_metrics = 1 if payload.get("period_type") == "Q" else 3
    if len(non_null) < min_metrics:
        return "failed", f"validation_gate:insufficient_metrics:{len(non_null)}"

    sanity_cap = _native_currency_sanity_cap(payload.get("currency"))
    for m, v in metrics.items():
        if v is not None and abs(v) > sanity_cap:
            return "failed", f"validation_gate:sanity_cap_exceeded:{m}={v}"

    confidence = payload.get("confidence_metrics", 0.0)
    if confidence < 0.60:
        return "failed", f"validation_gate:low_confidence:{confidence}"

    # Non-AUD currency: values are stored as-is with no FX conversion.
    # Flag as ok_low_confidence so consumers know to treat values with caution,
    # but only after all quality gates pass — non-AUD must not bypass them.
    # A warning was already emitted at ingestion time in run_multipass_extraction.
    _currency = _normalize_currency_code(payload.get("currency"))
    if _currency != "AUD":
        logger.warning(
            "validation_gate:non_aud_currency:%s — downgrading to ok_low_confidence (no FX policy)",
            _currency,
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
    """
    from app.services.docling_extract import ExtractionTimeoutError, extract_structured

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

    # Extract structured document
    if observer is not None:
        observer.emit("parser", "running", "Loading document parser output.")
    try:
        structured_doc = extract_structured(
            pdf_path,
            backend=parser_backend or "",
            strict_backend=strict_parser,
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
    title = doc_metadata.get("title", "")

    source_period_evidence = _detect_source_period_evidence(
        title, early_period_text or first_page_text
    )
    source_period_end_evidence = _detect_source_period_end_evidence(
        title, early_period_text or first_page_text
    )
    if not source_period_end_evidence.get("period_end"):
        early_table_text = _early_period_table_text(structured_doc.tables)
        if early_table_text:
            source_period_end_evidence = _detect_source_period_end_evidence(
                title,
                " ".join(
                    part
                    for part in (early_period_text or first_page_text, early_table_text)
                    if part
                ),
            )
    if not source_period_end_evidence.get("period_end"):
        statement_text = _formal_statement_source_text(
            structured_doc.sections,
            structured_doc.tables,
        )
        if statement_text:
            source_period_end_evidence = _detect_source_period_end_evidence(
                title,
                statement_text,
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
    if not pass1.get("period_end") and source_period_end_evidence.get("period_end"):
        pass1["period_end"] = source_period_end_evidence["period_end"]
    _apply_source_period_end_type_correction(pass1, source_period_end_evidence)
    _apply_source_period_end_correction(pass1, source_period_end_evidence)
    pass1["_source_period_evidence"] = source_period_evidence
    pass1["_source_period_end_evidence"] = source_period_end_evidence
    pass1["_source_period_type"] = source_period_evidence.get("period_type")
    pass1["_source_document_classification"] = source_document_classification.to_dict()

    # Deterministic source-unit detection is authoritative over LLM text inference.
    # Prefer explicit formal-statement section units when Docling keeps unit text
    # outside the table object; otherwise use table headers/captions/body rows.
    detected = _detect_scale_from_tables(structured_doc.tables)
    section_detected = _detect_scale_from_sections(structured_doc.sections)
    if section_detected != "unknown":
        if detected not in ("unknown", section_detected):
            logger.info(
                "scale from statement sections (%s) overrides table scan (%s)",
                section_detected,
                detected,
            )
        detected = section_detected
    if detected != "unknown":
        if pass1.get("scale", "unknown") not in (detected, "unknown", None, ""):
            logger.info(
                "scale from deterministic source units (%s) overrides Pass 1 (%s)",
                detected,
                pass1.get("scale"),
            )
        pass1["scale"] = detected
    elif pass1.get("scale", "unknown") in ("unknown", None, ""):
        logger.warning("scale unknown from both table headers and Pass 1 classifier")

    detected_currency = _detect_currency_from_tables(structured_doc.tables)
    if detected_currency:
        classifier_currency = str(pass1.get("currency") or "").strip().upper()
        if classifier_currency != detected_currency:
            logger.info(
                "currency from table headers (%s) overrides Pass 1 (%s)",
                detected_currency,
                classifier_currency or "<empty>",
            )
            pass1["currency"] = detected_currency

    _raw_pass1_currency = pass1.get("currency") or ""
    if not _raw_pass1_currency or str(_raw_pass1_currency).strip().lower() == "null":
        _raw_pass1_currency = "AUD"
    _currency = str(_raw_pass1_currency).upper()
    pass1["currency"] = _currency  # normalise in-place so propagation is consistent
    if _currency != "AUD":
        logger.warning(
            "non-AUD currency detected: %s — values stored as-is (no FX conversion applied)",
            _currency,
        )

    # Pass 2: Locate tables
    if observer is not None:
        observer.emit("pass2_locator", "running", "Locating statement tables.")
    labelled = _run_pass2_locator(structured_doc.tables)
    pass1["_block_derived_net_debt"] = bool(
        _document_has_nonnumeric_net_debt_reference(structured_doc.tables)
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
    try:
        pass3a_results = _run_pass3a_metric_extractor(
            labelled,
            pass1,
            llm_client,
            prompt_bundle=bundle,
            model_override=model_override,
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
    # pass1["currency"] was already normalised (string "null" → "AUD") at detection time.
    payload["scale"] = pass1.get("scale", "unknown") or "unknown"
    payload["currency"] = pass1.get("currency") or "AUD"

    # Surface non-AUD currency as a structured warning for operator visibility.
    # Values are stored in native currency with no FX conversion; downstream
    # consumers must not compare them directly with AUD-denominated peers.
    if payload["currency"] != "AUD":
        payload["_structured_extraction"]["warnings"].append(
            f"non_aud_currency:{payload['currency']} — values in native currency, no FX conversion"
        )

    metric_label_abstentions = _abstain_metric_label_mismatches(payload)
    for abstention in metric_label_abstentions:
        payload["_structured_extraction"]["warnings"].append(
            f"{abstention['reason']}:{abstention['metric']} — metric abstained"
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
