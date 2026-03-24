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

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

from dateutil import parser as dtparser

logger = logging.getLogger(__name__)


def parse_period_end(s: str | None) -> date | None:
    """Parse a period-end date string into a date object. Returns None on failure."""
    if not s:
        return None
    try:
        return dtparser.parse(s).date()
    except Exception:
        return None


def _derive_period_start(period_end: date | None, period_type: str | None) -> date | None:
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
    "revenue", "ebit", "np_attributable",
    "operating_cf", "investing_cf", "financing_cf",
    "capex", "cash_end", "net_debt", "shares_outstanding",
]

# Source priority for reconciliation (index 0 = highest priority)
SOURCE_PRIORITY = ["income_statement", "cashflow_statement", "balance_sheet", "share_capital", "highlights"]

SCALE_MULTIPLIERS = {
    "thousands": 1_000,
    "millions": 1_000_000,
    "billions": 1_000_000_000,
    "units": 1,
    "unknown": 1,
}


@dataclass
class MultipassResult:
    status: str            # "ok" | "ok_low_confidence" | "failed"
    payload: dict          # matches _upsert_financial_rows contract
    sections: list[dict]   # prose sections for Qdrant chunking
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Scale detection (deterministic, from table headers)
# ---------------------------------------------------------------------------

import re as _re

_SCALE_PATTERNS: list[tuple[str, str]] = [
    (r"\$'?000[,s]?\b|\bthousands?\b", "thousands"),
    # Millions: spelled-out, $'000,000, compact $M / A$M notation (common in AU mining)
    (r"\$'?000,000|\bmillions?\b|A?\$[Mm]\b|\$m\b", "millions"),
    (r"\bbillions?\b", "billions"),
]


def _detect_scale_from_tables(tables) -> str:
    """
    Scan table column headers for scale indicators ($'000, millions, etc.).
    Returns the first match, or 'unknown' if none found.
    ASX reports consistently encode scale in column headings (e.g. "31 Dec 2025 $'000").
    """
    for table in tables[:15]:
        header_text = " ".join(table.headers)
        for pattern, scale in _SCALE_PATTERNS:
            if _re.search(pattern, header_text, _re.IGNORECASE):
                return scale
    return "unknown"


# ---------------------------------------------------------------------------
# Pass 1 — Document Classifier
# ---------------------------------------------------------------------------

_PASS1_PROMPT = """You are a financial document classifier. Output ONLY valid JSON.

Given the document title and first-page text, extract:
- report_type: one of "A" (annual), "H" (half-year), "Q" (quarterly), or null
- period_end: the period end date as "YYYY-MM-DD", or null
- currency: three-letter currency code (e.g. "AUD"), or null
- scale: one of "thousands", "millions", "billions", "units", or "unknown"
- classifier_confidence: float 0.0-1.0 (how confident you are in the above)

Schema:
{{
  "report_type": "A|H|Q|null",
  "period_end": "YYYY-MM-DD|null",
  "currency": "AUD|USD|...|null",
  "scale": "thousands|millions|billions|units|unknown",
  "classifier_confidence": 0.0
}}

Title: {title}
First page text (first 1500 chars):
{first_page_text}
"""


def _run_pass1_classifier(
    title: str,
    first_page_text: str,
    llm_client,
) -> dict:
    """
    Pass 1: classify document type, period, currency, and scale.
    Returns dict with keys: report_type, period_end, currency, scale, classifier_confidence.
    """
    prompt = _PASS1_PROMPT.format(
        title=(title or "")[:200],
        first_page_text=(first_page_text or "")[:1500],
    )
    result = _llm_json_call(prompt, llm_client, max_tokens=256)
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
        "cash flow", "cash from operations", "operating activities",
        "financing activities", "investing activities", "net cash", "cash at end",
    ],
    "income_statement": [
        "revenue", "profit", "earnings before", "ebit", "net profit",
        "profit after tax", "income statement", "statement of profit",
    ],
    "balance_sheet": [
        "total assets", "current assets", "shareholders equity", "net assets",
        "total liabilities", "balance sheet", "statement of financial position",
    ],
    "share_capital": [
        "ordinary shares", "number of shares", "shares on issue", "shares issued",
        "share capital", "shares at end",
    ],
    "highlights": [
        "highlights", "key metrics", "summary", "at a glance", "key financials",
        "key information",  # Appendix 4D "Key Information" table (has EBIT, EBITDA labeled)
        "results for announcement",  # Appendix 4D summary tables — header bonus from _STATEMENT_HEADERS can fire
    ],
}

# High-confidence header phrases — matching any grants a large bonus score so
# these tables win decisively over footnote/note tables with incidental keyword matches.
_STATEMENT_HEADERS: dict[str, list[str]] = {
    "cashflow_statement": ["statement of cash flows", "cash flow statement"],
    "income_statement": [
        "income statement", "statement of profit", "statement of comprehensive income",
    ],
    "balance_sheet": ["balance sheet", "statement of financial position"],
    "share_capital": ["share capital", "number of shares"],
    "highlights": ["appendix 4d", "results for announcement"],
}
_HEADER_BONUS = 10


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
    labelled["unmatched"] = []
    # share_capital is handled via _TABLE_KEYWORDS and pools above

    def _table_is_toc(table: DoclingTable) -> bool:
        """True when any individual column header is a bare 1-3 digit integer (page number)."""
        return any(
            _re.match(r"^\s*\d{1,3}\s*$", str(h or ""))
            for h in table.headers
            if str(h or "").strip()
        )

    def _score(table: DoclingTable, label: str, keywords: list[str]) -> int:
        # Include caption, all header cells, and first-column of first 15 rows.
        # 15-row scan covers all three cash-flow sections and full asset/liability blocks.
        header_text = " ".join(table.headers).lower()
        body_text = " ".join(row[0] for row in table.rows[:15] if row).lower()
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
        return score

    # Score each table against ALL statement types — a table may appear in multiple
    # candidate pools. This allows summary tables (e.g. Appendix 4D highlights) that
    # partially match income_statement keywords to also compete for the highlights slot.
    # Pool tuple: (score, is_not_toc, table) — tiebreak prefers non-TOC tables.
    pools: dict[str, list[tuple[int, bool, Any]]] = {k: [] for k in _TABLE_KEYWORDS}
    for table in tables:
        any_match = False
        is_not_toc = not _table_is_toc(table)
        for label, keywords in _TABLE_KEYWORDS.items():
            score = _score(table, label, keywords)
            if score > 0:
                pools[label].append((score, is_not_toc, table))
                any_match = True
        if not any_match:
            labelled["unmatched"].append(table)

    # For each label: highest score wins; if tied, non-TOC beats TOC; if still tied,
    # earlier page wins (formal statements appear before notes in ASX filings).
    for label in _TABLE_KEYWORDS:
        if pools[label]:
            labelled[label] = max(
                pools[label], key=lambda x: (x[0], x[1], x[2].page_number)
            )[2]

    return labelled


# ---------------------------------------------------------------------------
# Pass 3a — Per-Table Metric Extractor (LLM)
# ---------------------------------------------------------------------------

_PASS3A_PROMPT = """You are a financial metric extractor. Output ONLY valid JSON.

Document metadata:
- Period: {period_type} ending {period_end}
- Currency: {currency}
- Scale: {scale} (for your information only — output RAW values as they appear in the table)
  - Do NOT pre-multiply. Output 3241 if the table shows "3,241". The system applies the scale.

Table type: {table_type}
Table (markdown):
{table_markdown}

Extract ONLY these metrics relevant to {table_type}:
{metric_list}

Rules:
- Values in parentheses like (412) mean NEGATIVE: output -412 (raw, not pre-multiplied)
- Output null if the metric is NOT explicitly labeled in this table — do NOT estimate or derive it
- ebit: only output if a row is explicitly labeled "EBIT", "Earnings Before Interest and Tax", or equivalent — do NOT use PBT or Profit Before Tax as a proxy
- capex: look for "Payments for property, plant and equipment" or "Capital expenditure" in investing activities — output null if not found
- shares_outstanding: look for total ordinary shares on issue (count, not dollar amount) — typically labeled "Ordinary shares" or "Shares on issue"
- Column selection: if the table has multiple data columns (e.g. current half and prior half),
  extract values ONLY from the column whose header best matches the reporting date {period_end}.
  Never extract from prior-period or comparative columns.
  Set period_col to the exact column header you chose.
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
"""

_METRIC_SCHEMA_BY_TABLE = {
    "cashflow_statement": ["operating_cf", "investing_cf", "financing_cf", "cash_end", "capex"],
    "income_statement": ["revenue", "ebit", "np_attributable"],
    # total_debt is an internal capture metric: not in METRIC_FIELDS, not stored in DB.
    # Pass 4 uses it to derive net_debt = total_debt - cash_end when net_debt is null.
    "balance_sheet": ["net_debt", "total_debt", "shares_outstanding"],
    "share_capital": ["shares_outstanding"],
    "highlights": METRIC_FIELDS,  # highlights may have any metric
}


def _table_to_markdown(table) -> str:
    """Convert DoclingTable rows to markdown string."""
    if not table or not table.rows:
        return ""
    lines = []
    for i, row in enumerate(table.rows[:30]):  # cap at 30 rows
        line = " | ".join(str(c) for c in row)
        lines.append(line)
        if i == 0:
            lines.append(" | ".join("---" for _ in row))
    return "\n".join(lines)


def _run_pass3a_metric_extractor(
    labelled_tables: dict[str, Any],
    pass1_result: dict,
    llm_client,
) -> list[dict]:
    """
    Pass 3a: one LLM call per labelled table. Returns list of extraction dicts,
    each tagged with its source table type.
    """
    results = []
    scale = pass1_result.get("scale", "unknown")
    multiplier = SCALE_MULTIPLIERS.get(scale, 1)

    for table_type, table in labelled_tables.items():
        if table_type == "unmatched" or table is None:
            continue
        metrics = _METRIC_SCHEMA_BY_TABLE.get(table_type, METRIC_FIELDS)
        metric_schema = "\n".join(f'  "{m}": "number|null",' for m in metrics)
        markdown = _table_to_markdown(table)
        if not markdown:
            continue

        prompt = _PASS3A_PROMPT.format(
            period_type=pass1_result.get("report_type", "?"),
            period_end=pass1_result.get("period_end", "?"),
            currency=pass1_result.get("currency", "AUD"),
            scale=scale,
            table_type=table_type,
            table_markdown=markdown,
            metric_list=", ".join(metrics),
            metric_schema=metric_schema,
        )

        try:
            raw = _llm_json_call(prompt, llm_client, max_tokens=1024)
        except Exception as e:
            logger.warning("Pass 3a failed for %s: %s — retrying with truncated table", table_type, e)
            try:
                truncated_prompt = _PASS3A_PROMPT.format(
                    period_type=pass1_result.get("report_type", "?"),
                    period_end=pass1_result.get("period_end", "?"),
                    currency=pass1_result.get("currency", "AUD"),
                    scale=scale,
                    table_type=table_type,
                    table_markdown=_table_to_markdown_truncated(table, max_rows=20),
                    metric_list=", ".join(metrics),
                    metric_schema=metric_schema,
                )
                raw = _llm_json_call(truncated_prompt, llm_client, max_tokens=1024)
            except Exception as e2:
                logger.error("Pass 3a retry also failed for %s: %s", table_type, e2)
                continue

        # Apply scale multiplier to monetary values only.
        # Count metrics (share counts etc.) are always absolute integers — never scaled.
        _COUNT_METRICS = {"shares_outstanding"}
        out = {"_source": table_type, "_page_number": getattr(table, "page_number", None)}
        for m in metrics:
            val = raw.get(m)
            if val is not None:
                try:
                    effective_multiplier = 1 if m in _COUNT_METRICS else multiplier
                    out[m] = float(val) * effective_multiplier
                except (TypeError, ValueError):
                    out[m] = None
            else:
                out[m] = None
        # Compute confidence from observable results rather than relying on the
        # model's self-reported value (which is typically 0.0 regardless of quality).
        # Use fraction of expected metrics that were extracted as the signal.
        n_extracted = sum(1 for m in metrics if out.get(m) is not None)
        computed_conf = n_extracted / max(len(metrics), 1)
        model_conf = float(raw.get("pass3_confidence", 0.0))
        # Take max so a model that correctly reports high confidence is rewarded,
        # but a model that reports 0 doesn't drag down an otherwise complete extraction.
        out["pass3_confidence"] = max(computed_conf, model_conf)
        out["row_refs"] = raw.get("row_refs", {})
        out["period_col"] = raw.get("period_col")
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

# Stable fingerprint of all extraction prompt templates.
# Changes when any prompt is edited — use this in ExtractionRun.prompt_hash
# so stale cached extractions can be detected if prompts are updated.
PROMPT_HASH: str = hashlib.sha256(
    (_PASS1_PROMPT + _PASS3A_PROMPT + _PASS3B_PROMPT).encode()
).hexdigest()[:16]


def _run_pass3b_narrative_extractor(sections: list[dict], llm_client) -> dict:
    """
    Pass 3b: extract risk/guidance narrative from prose sections.
    Returns dict with narrative fields. All fields null on failure.
    """
    null_result = {
        "risk_summary": None, "risk_bullets": None,
        "guidance_summary": None, "material_changes": None,
        "confidence_narrative": 0.0,
    }

    prose = " ".join(s["text"] for s in sections if s.get("text", "").strip())[:4000]
    if not prose:
        return null_result

    prompt = _PASS3B_PROMPT.format(prose_text=prose)
    try:
        raw = _llm_json_call(prompt, llm_client, max_tokens=512)
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
# Pass 4 — Reconciler (deterministic)
# ---------------------------------------------------------------------------

def _run_pass4_reconciler(
    pass3a_results: list[dict],
    pass3b_result: dict,
    pass1_result: dict,
) -> dict:
    """
    Pass 4: merge all Pass 3a results into one canonical payload.
    Source priority: income_statement > cashflow_statement > balance_sheet > highlights.
    Returns dict matching _upsert_financial_rows contract.
    """
    merged_metrics: dict[str, Any] = {m: None for m in METRIC_FIELDS}
    provenance: dict[str, str] = {}
    source_stats: dict[str, tuple[float, int]] = {}  # {source: (confidence, n_contributed)}

    # Sort by priority
    ordered = sorted(
        pass3a_results,
        key=lambda r: SOURCE_PRIORITY.index(r.get("_source", "highlights"))
        if r.get("_source") in SOURCE_PRIORITY else len(SOURCE_PRIORITY),
    )

    # Lower priority first — higher priority overwrites
    for extraction in reversed(ordered):
        source = extraction.get("_source", "unknown")
        conf = extraction.get("pass3_confidence", 0.5)
        contributed = 0
        page = extraction.get("_page_number")
        page_tag = f"page_{page}" if page is not None else "page_?"
        for m in METRIC_FIELDS:
            if m in extraction and extraction[m] is not None:
                merged_metrics[m] = extraction[m]
                row_ref = extraction.get("row_refs", {}).get(m, "unknown")
                provenance[m] = f"{source}:{page_tag}:{row_ref}"
                contributed += 1
        source_stats[source] = (conf, contributed)

    # B4: derive net_debt from balance sheet total_debt when not directly extracted.
    # total_debt is an internal capture field (not in METRIC_FIELDS) so it survives
    # only in the raw pass3a extraction dict, not in merged_metrics.
    if merged_metrics.get("net_debt") is None:
        bs_result = next(
            (r for r in pass3a_results if r.get("_source") == "balance_sheet"), None
        )
        if bs_result is not None:
            total_debt = bs_result.get("total_debt")
            cash_end = merged_metrics.get("cash_end")
            if total_debt is not None and cash_end is not None:
                merged_metrics["net_debt"] = total_debt - cash_end
                provenance["net_debt"] = (
                    f"derived:balance_sheet:total_debt({total_debt:.0f})"
                    f"-cash_end({cash_end:.0f})"
                )
                logger.info(
                    "net_debt derived from balance sheet: %.0f - %.0f = %.0f",
                    total_debt, cash_end, merged_metrics["net_debt"],
                )

    # Weighted average confidence — each source weighted by metrics contributed
    total_weight = sum(n for _, n in source_stats.values())
    metric_confidence = (
        sum(c * n for c, n in source_stats.values()) / max(total_weight, 1)
        if source_stats else 0.0
    )

    return {
        "period_type": pass1_result.get("report_type"),
        "period_end": pass1_result.get("period_end"),
        "metrics": merged_metrics,
        "confidence_metrics": round(metric_confidence, 3),
        "provenance": provenance,
        **pass3b_result,  # risk_summary, risk_bullets, guidance_summary, material_changes, confidence_narrative
    }


# ---------------------------------------------------------------------------
# Validation Gate
# ---------------------------------------------------------------------------

SANITY_CAP = 500_000_000_000  # $500B


def _validate_gate(payload: dict) -> tuple[str, Optional[str]]:
    """
    Validate the reconciled payload before DB upsert.
    Returns (status, error). status is one of: "ok", "ok_low_confidence", "failed".
    """
    from dateutil import parser as dtparser

    # Hard blocks
    if not payload.get("period_end"):
        return "failed", "validation_gate:missing_period_end"

    try:
        dtparser.parse(str(payload["period_end"]))
    except Exception:
        return "failed", "validation_gate:invalid_period_end"

    if payload.get("period_type") not in ("A", "H", "Q"):
        return "failed", f"validation_gate:invalid_period_type:{payload.get('period_type')}"

    if payload.get("scale") == "unknown":
        return "failed", "validation_gate:scale_unknown"

    metrics = payload.get("metrics", {})
    non_null = [v for v in metrics.values() if v is not None]
    if len(non_null) < 3:
        return "failed", f"validation_gate:insufficient_metrics:{len(non_null)}"

    for m, v in metrics.items():
        if v is not None and abs(v) > SANITY_CAP:
            return "failed", f"validation_gate:sanity_cap_exceeded:{m}={v}"

    confidence = payload.get("confidence_metrics", 0.0)
    if confidence < 0.60:
        return "failed", f"validation_gate:low_confidence:{confidence}"

    # Non-AUD currency: values are stored as-is with no FX conversion.
    # Flag as ok_low_confidence so consumers know to treat values with caution,
    # but only after all quality gates pass — non-AUD must not bypass them.
    # A warning was already emitted at ingestion time in run_multipass_extraction.
    _currency = (payload.get("currency") or "AUD").upper()
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
) -> MultipassResult:
    """
    Orchestrate all 4 passes and return a MultipassResult.
    doc_metadata: {"document_id": str, "ticker": str, "title": str}
    """
    from app.services.docling_extract import extract_structured

    null_payload = {m: None for m in METRIC_FIELDS}
    null_payload.update({
        "period_type": None, "period_end": None, "period_start": None, "confidence_metrics": 0.0,
        "risk_summary": None, "risk_bullets": None, "guidance_summary": None,
        "material_changes": None, "confidence_narrative": 0.0, "provenance": {},
    })

    # Extract structured document
    try:
        structured_doc = extract_structured(pdf_path)
    except Exception as e:
        logger.error("docling_extract failed for %s: %s", pdf_path, e)
        return MultipassResult(status="failed", payload=null_payload, sections=[], error=str(e))

    # Pass 1: Classify
    first_page_text = " ".join(
        s["text"] for s in structured_doc.sections[:5]
    )[:1500]
    title = doc_metadata.get("title", "")

    try:
        pass1 = _run_pass1_classifier(title, first_page_text, llm_client)
    except Exception as e:
        logger.error("Pass 1 failed: %s", e)
        return MultipassResult(status="failed", payload=null_payload,
                               sections=structured_doc.sections, error=f"pass1:{e}")

    if pass1.get("classifier_confidence", 0) < 0.60:
        return MultipassResult(
            status="failed", payload=null_payload,
            sections=structured_doc.sections,
            error=f"classifier_low_confidence:{pass1.get('classifier_confidence')}",
        )

    # Table-header scale detection is always authoritative — ASX filings print scale
    # explicitly in column headers ($'000, A$M, etc.) which is more reliable than
    # LLM text inference. Run unconditionally; fall back to Pass 1 if headers give nothing.
    detected = _detect_scale_from_tables(structured_doc.tables)
    if detected != "unknown":
        if pass1.get("scale", "unknown") not in (detected, "unknown", None, ""):
            logger.info(
                "scale from table headers (%s) overrides Pass 1 (%s)",
                detected, pass1.get("scale"),
            )
        pass1["scale"] = detected
    elif pass1.get("scale", "unknown") in ("unknown", None, ""):
        logger.warning("scale unknown from both table headers and Pass 1 classifier")

    _currency = pass1.get("currency", "AUD") or "AUD"
    if _currency.upper() != "AUD":
        logger.warning(
            "non-AUD currency detected: %s — values stored as-is (no FX conversion applied)",
            _currency,
        )

    # Pass 2: Locate tables
    labelled = _run_pass2_locator(structured_doc.tables)

    # Pass 3a: Extract metrics
    pass3a_results = _run_pass3a_metric_extractor(labelled, pass1, llm_client)

    # Pass 3b: Extract narrative
    pass3b_result = _run_pass3b_narrative_extractor(structured_doc.sections, llm_client)

    # Pass 4: Reconcile
    payload = _run_pass4_reconciler(pass3a_results, pass3b_result, pass1)

    # Derive period_start deterministically — schema column exists but was not populated.
    _pe = parse_period_end(payload.get("period_end"))
    payload["period_start"] = _derive_period_start(_pe, payload.get("period_type"))

    # Flatten metrics into payload for _upsert_financial_rows compat
    for m in METRIC_FIELDS:
        payload[m] = payload["metrics"].get(m)

    # Propagate scale and currency from Pass 1 into payload so _validate_gate
    # can inspect them and so _upsert_financial_rows stores the correct currency.
    payload["scale"] = pass1.get("scale", "unknown") or "unknown"
    payload["currency"] = pass1.get("currency", "AUD") or "AUD"

    # Validate
    status, error = _validate_gate(payload)

    return MultipassResult(
        status=status,
        payload=payload,
        sections=structured_doc.sections,
        error=error,
    )


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _llm_json_call(prompt: str, llm_client, max_tokens: int = 512) -> dict:
    """
    Call the LLM with JSON mode enforced. Returns parsed dict.
    Raises on invalid JSON or connection failure.

    llm_client may be:
    - httpx.Client pointing at an OpenAI-compatible endpoint (llamacpp / Ollama)
    - anthropic.Anthropic instance — uses Claude directly via the Anthropic SDK
    """
    import json as _json

    # Anthropic SDK path
    try:
        import anthropic as _anthropic
        if isinstance(llm_client, _anthropic.Anthropic):
            model = getattr(llm_client, "_extraction_model", "claude-opus-4-6")
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
    metadata = {"task_type": "reasoning", "component": "multipass_extraction"}
    result = generate_json(prompt, metadata=metadata, client=llm_client)
    if not isinstance(result, dict):
        raise ValueError(f"LLM returned non-dict: {type(result)}")
    return result
