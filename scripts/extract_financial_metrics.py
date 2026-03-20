#!/usr/bin/env python3
import argparse
import calendar
from collections import Counter
import csv
import os
import hashlib
import html
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from financial_normalization import (
    normalize_financial_value,
    normalize_metric_rows as _normalize_metric_rows,
    parse_accounting_number,
)
from document_classifier import classify_document
from extractor_fallback_policy import evaluate_docling_fallback
from financial_identity_resolver import resolve_duplicate_metrics
from metric_ontology_mapper import canonicalize_metric_row, canonicalize_metric_rows
from period_ontology_mapper import normalize_period_row, normalize_period_rows
from statement_classifier import classify_table_statement
from table_scope_classifier import classify_table_scope
from table_structure_reconciliation import compute_table_identity, detect_year_columns, reconcile_table_dataframe
from validate_financial_coverage_gates import build_report as build_financial_coverage_gate_report
from validate_financial_metrics_gates import build_report as build_financial_metrics_gate_report


DEFAULT_DOCUMENT_QUARANTINE_RULES_PATH = (
    Path(__file__).resolve().parents[1] / "financial-engine_v2" / "config" / "document_quarantine_rules.json"
).resolve()
NON_FINANCIAL_DOCUMENT_SKIP_REASON = "non_financial_document"
UUID_PDF_SUFFIX_RE = re.compile(
    r"_(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.pdf$",
    re.IGNORECASE,
)
strict_docling_mode = True


def normalize_metric_name(name: str) -> str:
    if not name:
        return name
    normalized = name.lower().strip()

    replacements = {
        "total revenue": "revenue",
        "revenue ($m)": "revenue",
        "revenue (m)": "revenue",
        "net profit after tax": "npat",
        "profit after tax": "npat",
        "net income": "npat",
    }

    for source, target in replacements.items():
        if source in normalized:
            return target

    return normalized


def normalize_period(dt):
    if not dt:
        return dt
    if isinstance(dt, datetime):
        return dt.replace(day=1)
    if isinstance(dt, date):
        return dt.replace(day=1)
    if isinstance(dt, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt.strip()):
        try:
            return date.fromisoformat(dt.strip()).replace(day=1).isoformat()
        except ValueError:
            return dt
    try:
        return dt.replace(day=1)
    except Exception:
        return dt


def _apply_extraction_normalization(row: Dict[str, object]) -> None:
    metric = normalize_metric_name(str(row.get("metric", "")).strip())
    if metric:
        row["metric"] = metric
    metric_base = normalize_metric_name(str(row.get("metric_base", "")).strip())
    if metric_base:
        row["metric_base"] = metric_base
    for key in ("period", "statement_period"):
        normalized_period = normalize_period(row.get(key))
        if normalized_period:
            row[key] = normalized_period


def safe_module_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"[warn] classifier failure: {e}", file=sys.stderr)
        return {
            "error": str(e),
            "result": None,
        }


NUM_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<currency>(?:A|US|C|NZ)?[$€£])?\s*(?P<num>\(?-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)?)\s*(?P<suffix>bn|mn|mm|k|m|b|t|million|billion|thousand|trillion)?\b",
    re.IGNORECASE,
)
NUM_TOKEN_RE = re.compile(
    r"^(?P<currency>(?:A|US|C|NZ)?[$€£])?\s*(?P<num>\(?-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)?)\s*(?P<suffix>bn|mn|mm|k|m|b|t|million|billion|thousand|trillion)?$",
    re.IGNORECASE,
)
PCT_RE = re.compile(r"(?P<pct>-?\d+(?:\.\d+)?)\s*%")
MONTH_TOKEN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
PERIOD_RE = re.compile(
    r"\b((?:FY|Q[1-4]|H[12])\s*[-/]?\s*(?:20)?\d{2}|(?:20)\d{2}|TTM|LTM|year ended|quarter ended)\b",
    re.IGNORECASE,
)
DATE_PERIOD_RE = re.compile(rf"\b\d{{1,2}}\s+{MONTH_TOKEN}\s+20\d{{2}}\b", re.IGNORECASE)
PERIOD_PHRASE_RE = re.compile(
    rf"\b((?:for\s+the\s+)?(?:\d{{1,2}}\s+months?|quarter|half(?:[-\s]?year)?|year)\s+ended\s+\d{{1,2}}\s+{MONTH_TOKEN}\s+20\d{{2}})\b",
    re.IGNORECASE,
)
FISCAL_PERIOD_RE = re.compile(r"\b(?:FY|Q[1-4]|H[12])\s*[-/]?\s*(?:20)?\d{2}\b", re.IGNORECASE)
RELATIVE_PERIOD_RE = re.compile(
    r"\b(?:current|previous|prior)\s+(?:quarter|half(?:[-\s]?year)|year|period)\b",
    re.IGNORECASE,
)
MONTHS_ENDED_RE = re.compile(r"\b(\d{1,2})\s+months?\s+ended\b", re.IGNORECASE)
QUARTERLY_PERIOD_RE = re.compile(
    r"\b(quarter(?:ly)?|q[1-4]|three\s+months?\s+ended|3\s+months?\s+ended|current\s+quarter|previous\s+quarter|prior\s+quarter)\b",
    re.IGNORECASE,
)
HALF_YEAR_PERIOD_RE = re.compile(
    r"\b(half(?:[-\s]?year(?:ly)?)?|h[12]|six\s+months?\s+ended|6\s+months?\s+ended|interim)\b",
    re.IGNORECASE,
)
ANNUAL_PERIOD_RE = re.compile(
    r"\b(year\s+ended|annual|full\s+year|fy\s*[-/]?\s*(?:20)?\d{2}|12\s+months?\s+ended)\b",
    re.IGNORECASE,
)
DOC_QUARTERLY_HINT_RE = re.compile(r"\b(quarterly|appendix\s*4c)\b", re.IGNORECASE)
DOC_HALF_YEAR_HINT_RE = re.compile(r"\b(half\s*year(?:ly)?|interim)\b", re.IGNORECASE)
DOC_ANNUAL_HINT_RE = re.compile(
    r"\b(annual\s*report|appendix\s*4e|preliminary\s*final\s*report|full\s*year)\b",
    re.IGNORECASE,
)
BARE_YEAR_RE = re.compile(r"\b20\d{2}\b")
FY_PERIOD_RE = re.compile(r"\bFY\s*[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
HY_PERIOD_RE = re.compile(r"\bHY\s*[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
H1_PERIOD_RE = re.compile(r"\b(?:H1|1H)\s*(?:FY\s*)?[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
H2_PERIOD_RE = re.compile(r"\b(?:H2|2H)\s*(?:FY\s*)?[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
DOC_DATE_RE = re.compile(r"\b(20\d{2})[-_](\d{2})[-_](\d{2})\b")
STATEMENT_DATE_WORD_RE = re.compile(rf"\b(\d{{1,2}})[-_ ]({MONTH_TOKEN})[-_ ](20\d{{2}})\b", re.IGNORECASE)
EBITDA_LABEL_RE = re.compile(
    r"\b(?:(statutory|underlying|adjusted)\s+)?ebitda(?:\s+before\s+significant\s+items)?\b",
    re.IGNORECASE,
)
EBIT_LABEL_RE = re.compile(
    r"\b(?:(statutory|underlying|adjusted)\s+)?ebit(?:\s+before\s+significant\s+items)?\b|"
    r"\boperating\s+(?:profit|income)\b|\bprofit\s+from\s+operations\b",
    re.IGNORECASE,
)
TOTAL_DEBT_LABEL_RE = re.compile(
    r"\b(total\s+debt|total\s+borrowings|total\s+interest[- ]bearing\s+liabilities|interest[- ]bearing\s+debt|borrowings?)\b",
    re.IGNORECASE,
)
NET_DEBT_LABEL_RE = re.compile(r"\bnet\s+debt\b", re.IGNORECASE)
TOTAL_ASSETS_LABEL_RE = re.compile(r"\btotal\s+assets?\b", re.IGNORECASE)
TOTAL_LIABILITIES_LABEL_RE = re.compile(r"\btotal\s+liabilities?\b", re.IGNORECASE)
TOTAL_EQUITY_LABEL_RE = re.compile(
    r"\b(total\s+equity|total\s+shareholders'?\s+equity|"
    r"equity\s+attributable\s+to\s+(?:owners|equity\s+holders)|net\s+assets)\b",
    re.IGNORECASE,
)
CURRENT_ASSETS_LABEL_RE = re.compile(r"\bcurrent\s+assets?\b", re.IGNORECASE)
CURRENT_LIABILITIES_LABEL_RE = re.compile(r"\bcurrent\s+liabilities?\b", re.IGNORECASE)
GROWTH_LABEL_RE = re.compile(r"\b(yoy|year[- ]over[- ]year|qoq|cagr)\b", re.IGNORECASE)

METRIC_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "revenue",
        re.compile(
            r"\b(revenue|turnover|total income|total operating income|operating income|net operating income|"
            r"net interest income|non-interest income)\b",
            re.IGNORECASE,
        ),
    ),
    ("segment_revenue", re.compile(r"\b(segment revenue|division revenue|business unit revenue|media revenue)\b", re.IGNORECASE)),
    ("gross_profit", re.compile(r"\b(gross profit|gross income)\b", re.IGNORECASE)),
    ("gross_margin_pct", re.compile(r"\b(gross margin)\b", re.IGNORECASE)),
    ("ebitda", EBITDA_LABEL_RE),
    ("ebit", EBIT_LABEL_RE),
    ("operating_margin_pct", re.compile(r"\b(operating margin|ebit margin)\b", re.IGNORECASE)),
    (
        "net_income",
        re.compile(
            r"\b(net income|net profit|profit after tax(?:ation)?|loss after tax(?:ation)?|pat|"
            r"profit\s*/?\s*\(?loss\)?\s+after\s+income\s+tax(?:\s+expense)?|"
            r"loss after income tax(?:\s+expense)?|profit or loss after tax|"
            r"(?:profit|loss)(?:\s+after\s+tax(?:ation)?)?\s+attributable\s+to\s+(?:owners|members|shareholders|equity\s+holders))\b",
            re.IGNORECASE,
        ),
    ),
    ("npat", re.compile(r"\b(npat|net profit after tax)\b", re.IGNORECASE)),
    ("eps", re.compile(r"\b(eps|earnings per share)\b", re.IGNORECASE)),
    ("free_cash_flow", re.compile(r"\b(free cash flow|fcf)\b", re.IGNORECASE)),
    (
        "operating_cash_flow",
        re.compile(
            r"\b(net\s+operating\s+cash\s+flows?|operating\s+cash\s+flows?|cash\s+from\s+operations?|"
            r"net\s+cash\s+(?:provided\s+by|generated\s+from)\s+operating\s+activities)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "change_in_working_capital",
        re.compile(r"\b(change(?:s)?\s+in|movement(?:s)?\s+in)?\s*working\s+capital\b", re.IGNORECASE),
    ),
    (
        "income_tax_paid",
        re.compile(
            r"\b((?:net\s+)?income\s+tax(?:ation)?(?:\s+and\s+royalty[-\s]?related\s+taxation)?\s+paid|"
            r"net\s+income\s+tax\s+and\s+royalty[-\s]?related\s+taxation\s+paid|"
            r"net\s+cash\s+tax\s+paid)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "royalties_paid",
        re.compile(r"\b(royalt(?:y|ies).{0,40}\bpaid|royalty[-\s]?related\s+taxation\s+paid)\b", re.IGNORECASE),
    ),
    (
        "change_in_inventories",
        re.compile(
            r"\b((?:change(?:s)?|movement(?:s)?|increase|decrease)"
            r"(?:/\(?(?:decrease|increase)\)?)?\s+in\s+inventor(?:y|ies)|"
            r"inventor(?:y|ies)\s+movement(?:s)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "change_in_receivables",
        re.compile(
            r"\b((?:change(?:s)?|movement(?:s)?|increase|decrease)"
            r"(?:/\(?(?:decrease|increase)\)?)?\s+in\s+receivables?|"
            r"receivables?\s+movement(?:s)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "change_in_payables",
        re.compile(
            r"\b((?:change(?:s)?|movement(?:s)?|increase|decrease)"
            r"(?:/\(?(?:decrease|increase)\)?)?\s+in\s+payables?|"
            r"payables?\s+movement(?:s)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "depreciation_and_amortisation",
        re.compile(r"\b(depreciation(?:\s+and\s+amorti[sz]ation)?|amorti[sz]ation)\b", re.IGNORECASE),
    ),
    (
        "impairment_expense",
        re.compile(r"\b(impairment(?:\s+(?:charge|expense|loss(?:es)?))?)\b", re.IGNORECASE),
    ),
    (
        "cash_and_equivalents",
        re.compile(
            r"\b(cash equivalents|cash (?:and equivalents|balance|position|on hand)|cash(?!\s*flow))\b",
            re.IGNORECASE,
        ),
    ),
    ("net_debt", NET_DEBT_LABEL_RE),
    ("total_debt", TOTAL_DEBT_LABEL_RE),
    ("current_assets", CURRENT_ASSETS_LABEL_RE),
    ("current_liabilities", CURRENT_LIABILITIES_LABEL_RE),
    ("total_assets", TOTAL_ASSETS_LABEL_RE),
    ("total_liabilities", TOTAL_LIABILITIES_LABEL_RE),
    ("total_equity", TOTAL_EQUITY_LABEL_RE),
    ("shares_outstanding", re.compile(r"\b(shares outstanding|shares on issue|issued shares|ordinary shares on issue|weighted average number of ordinary shares)\b", re.IGNORECASE)),
    ("roic_pct", re.compile(r"\b(roic|return on invested capital)\b", re.IGNORECASE)),
    ("capex", re.compile(r"\b(capex|capital expenditure)\b", re.IGNORECASE)),
    ("guidance", re.compile(r"\b(guidance|outlook|forecast|expects?|targets?)\b", re.IGNORECASE)),
    ("growth_pct", GROWTH_LABEL_RE),
]
METRIC_PATTERN_MAP = {metric: pat for metric, pat in METRIC_PATTERNS}
TABLE_NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(received|sale|sold|disposal|divestment|proceeds|completion|compared|grew|grown|increased|decreased|improved|up by|down by|issued|stating|updating|was|were|amounted|represented|delivered|targeting|forecast|held|projection|projections|range|available|approximately|approx\.?|generated|underpinned|supports?|resulted|remains?)\b",
    re.IGNORECASE,
)
TABLE_COMPARATIVE_NARRATIVE_RE = re.compile(
    r"\b(higher|lower)\s+than\b|"
    r"\bprior\s+(?:period|corresponding\s+period)\b|"
    r"\bfrom\s+one\s+customer\b|"
    r"\bof\s+.+\btotal\s+revenue\b|"
    r"\bon\s+a\s+statutory\s+basis\b|"
    r"\bpro\s+forma\s+forecast\b|"
    r"\bpartly\s+offset\s+by\b",
    re.IGNORECASE,
)
TABLE_SENTENCE_CONTEXT_RE = re.compile(
    r"\b(with|while|because|therefore|reflecting|driven|following|which|that|due to|to settle|had available|amounted to)\b",
    re.IGNORECASE,
)
TABLE_ROW_CONTAMINATION_RE = re.compile(
    r"\b(for\s+personal\s+use\s+only|expected\s+to|business\s+is|now\s+than|we\s+also)\b",
    re.IGNORECASE,
)
TABLE_LAYOUT_HINT_RE = re.compile(r"\b(31\s+dec(?:ember)?|30\s+jun(?:e)?|fy\d{2}|q[1-4]|h[12]|total)\b", re.IGNORECASE)
RECONCILIATION_CONTEXT_RE = re.compile(
    r"\b(impact\s+on\s+consolidated\s+statement|previously\s+disclosed|"
    r"transactions?\s+with\s+minority|flow\s+through\s+shares?|"
    r"net\s+debt\s+waterfall|alternative\s+performance\s+measures?|non[-\s]?ifrs|"
    r"net\s+operating\s+assets?|balance\s+sheet\s+movement|"
    r"reconcile(?:s|d)?\s+net\s+operating\s+assets|discontinued\s+operations|"
    r"net\s+assets?\s+disposed|assets?\s+disposed|assets?\s+held\s+for\s+sale|"
    r"assets?\s+acquired|net\s+identifiable\s+assets?|business\s+combinations?|"
    r"news\s+release|apms?\s+derived|debt\s+and\s+sources\s+of\s+liquidity|"
    r"net\s+debt\s+management\s+related\s+instruments?|"
    r"deed\s+of\s+cross\s+guarantee|party\s+to\s+the\s+deed|"
    r"financial\s+impacts?\s+of)\b",
    re.IGNORECASE,
)
CASH_RECONCILIATION_CONTEXT_RE = re.compile(
    r"\b(net\s+debt\s+waterfall|alternative\s+performance\s+measures?|non[-\s]?ifrs|"
    r"net\s+operating\s+assets?|net\s+assets?|balance\s+sheet\s+movement|"
    r"reconcile(?:s|d)?\s+net\s+operating\s+assets|discontinued\s+operations)\b",
    re.IGNORECASE,
)
CASH_NON_BALANCE_ROW_RE = re.compile(
    r"\b(net\s+(?:increase|decrease|movement|change)\s+in\s+cash\s+and\s+cash\s+equivalents|"
    r"cash\s+and\s+cash\s+equivalents\s+(?:acquired|disposed))\b",
    re.IGNORECASE,
)
OPERATING_CASH_FLOW_COMPONENT_RE = re.compile(
    r"\b(working\s+capital(?:\s+movements?)?|"
    r"net\s+cash\s+tax\s+paid|income\s+tax(?:ation)?(?:\s+and\s+royalty[-\s]?related\s+taxation)?\s+(?:paid|refunded)|"
    r"royalty[-\s]?related\s+taxation|"
    r"proceeds?\s*/?\s*\(?settlements?\)?\s+of\s+cash\s+management\s+related\s+instruments?|"
    r"cash\s+management\s+related\s+instruments?|"
    r"foreign\s+currency\s+exchange\s+rate\s+changes?\s+on\s+cash\s+and\s+cash\s+equivalents?)\b",
    re.IGNORECASE,
)
VALUE_PLACEHOLDER_RE = re.compile(r"^\s*[-—–]\s*$")
NOTE_REFERENCE_LINE_RE = re.compile(r"^\s*\d{1,3}(?:\([A-Za-z0-9]+\))?\s*$")
SECTION_HEADING_ONLY_RE = re.compile(
    r"^\s*(?:current|non[-\s]?current)\s+(?:assets?|liabilities?)\s*$|^\s*(?:assets?|liabilities?|equity)\s*$",
    re.IGNORECASE,
)
COMBINED_LIAB_EQUITY_ROW_RE = re.compile(
    r"\b(total\s+liabilities\s+and\s+(?:equity|net\s+assets?|net\s+assets?\s+attributable)|"
    r"liabilities?\s+and\s+equity|liabilities?\s+and\s+net\s+assets?)\b",
    re.IGNORECASE,
)
SECTION_EXCLUDED_RE = re.compile(
    r"\b(liquidity\s+risk|credit\s+risk|market\s+risk|financial\s+risk|risk\s+management|interest\s+rate\s+risk|foreign\s+exchange\s+risk|currency\s+risk)\b",
    re.IGNORECASE,
)
FINANCIAL_SECTION_RE = re.compile(
    r"\b(statement\s+of|financial\s+statements?|financial\s+report|financial\s+position|cash\s+flows?|"
    r"profit\s+or\s+loss|comprehensive\s+income|balance\s+sheet|income\s+statement|"
    r"notes?\s+to\s+the\s+financial\s+statements?|appendix[\s\-_]*(4c|4d|4e|5b)|"
    r"consolidated\s+(statement|financial))\b",
    re.IGNORECASE,
)
PRESENTATIONAL_SECTION_RE = re.compile(
    r"\b(chairman|chairperson|ceo|managing\s+director|review\s+of\s+operations|operating\s+review|"
    r"operations?\s+review|exploration|highlights|letter\s+to\s+shareholders|investor|presentation|"
    r"strategy|business\s+review|corporate\s+overview|sustainability|financial\s+performance|low\s+gearing)\b",
    re.IGNORECASE,
)
STATEMENT_LAYOUT_RE = re.compile(
    r"\b(statement\s+of\s+(profit\s+or\s+loss|financial\s+position|cash\s+flows?|comprehensive\s+income)|"
    r"income\s+statement|balance\s+sheet|financial\s+position)\b",
    re.IGNORECASE,
)
CONSOLIDATED_SCOPE_RE = re.compile(r"\bconsolidated\b", re.IGNORECASE)
PARENT_SCOPE_RE = re.compile(r"\bparent\b|\bparent\s+entity\s+information\b", re.IGNORECASE)
PARENT_ENTITY_FINANCIAL_RE = re.compile(
    r"\b(parent\s+entity\s+financial\s+information|financial\s+information\s+for\s+the\s+parent\s+entity|"
    r"individual\s+financial\s+statements?\s+for\s+the\s+parent\s+entity)\b",
    re.IGNORECASE,
)
NOTE_SCOPE_RE = re.compile(
    rf"(?mi)^\s*note\s+(\d{{1,3}}[A-Za-z]?)\b(?!\s+{MONTH_TOKEN}\b)",
    re.IGNORECASE,
)
NOTE_INLINE_SCOPE_RE = re.compile(
    rf"\bnote\s+(\d{{1,3}}[A-Za-z]?)\s*[:\).\-](?!\s*{MONTH_TOKEN}\b)",
    re.IGNORECASE,
)
NOTES_TO_SECTION_RE = re.compile(r"\bnotes?\s+to\s+the\b", re.IGNORECASE)
APPENDIX_SCOPE_RE = re.compile(
    r"(?:^|[^A-Za-z0-9])appendix[\s\-_]*(4c|4d|4e|5b)(?=$|[^A-Za-z0-9])|"
    r"\bquarterly[\s\-_]*cash[\s\-_]*flow\b",
    re.IGNORECASE,
)
PRO_FORMA_CONTEXT_RE = re.compile(r"\b(pro\s*forma|forecast|(?:19|20)\d{2}[ap])\b", re.IGNORECASE)
ACQUISITION_CONTRIBUTION_RE = re.compile(
    r"\bcontributed\s+(?:revenue|income|profit|ebit|ebitda|cash)\b|\bfrom\s+acquisition\s+date\b",
    re.IGNORECASE,
)
WEAK_TITLE_RE = re.compile(
    r"^\(|\bshould\s+equal\s+item\b|\bnote:\b|\bmust\s+include\s+a\s+description\b|"
    r"^consolidated$|^group$|^page\s+\d+\s+of\s+\d+$",
    re.IGNORECASE,
)
PAGE_FOOTER_RE = re.compile(r"^\s*page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE)
GENERIC_FOOTER_RE = re.compile(r"\bfor\s+personal\s+use\s+only\b", re.IGNORECASE)
TABLE_COLUMN_GAP_RE = re.compile(r"\S\s{2,}\S")
MONTH_RE = re.compile(rf"\b{MONTH_TOKEN}\b", re.IGNORECASE)
METRIC_TABLE_LABELS: Dict[str, re.Pattern[str]] = {
    "revenue": re.compile(
        r"\b(total\s+revenue|revenue|turnover|total\s+income|total\s+operating\s+income|"
        r"operating\s+income|net\s+operating\s+income|net\s+interest\s+income|non-interest\s+income)\b",
        re.IGNORECASE,
    ),
    "segment_revenue": re.compile(r"\b(segment|division|business unit|media)\s+revenue\b", re.IGNORECASE),
    "gross_profit": re.compile(r"\b(gross\s+profit|gross\s+income)\b", re.IGNORECASE),
    "gross_margin_pct": re.compile(r"\b(gross\s+margin)\b", re.IGNORECASE),
    "ebitda": EBITDA_LABEL_RE,
    "ebit": EBIT_LABEL_RE,
    "operating_margin_pct": re.compile(r"\b(operating\s+margin|ebit\s+margin)\b", re.IGNORECASE),
    "net_income": re.compile(
        r"\b(net\s+income|net\s+profit|profit\s+after\s+tax(?:ation)?|loss\s+after\s+tax(?:ation)?|pat|"
        r"profit\s*/?\s*\(?loss\)?\s+after\s+income\s+tax(?:\s+expense)?|"
        r"loss\s+after\s+income\s+tax(?:\s+expense)?|profit\s+or\s+loss\s+after\s+tax|"
        r"(?:profit|loss)(?:\s+after\s+tax(?:ation)?)?\s+attributable\s+to\s+(?:owners|members|shareholders|equity\s+holders))\b",
        re.IGNORECASE,
    ),
    "npat": re.compile(r"\b(npat|net\s+profit\s+after\s+tax)\b", re.IGNORECASE),
    "eps": re.compile(r"\b(eps|earnings\s+per\s+share)\b", re.IGNORECASE),
    "free_cash_flow": re.compile(r"\b(free\s+cash\s+flow|fcf)\b", re.IGNORECASE),
    "operating_cash_flow": re.compile(
        r"\b(net\s+operating\s+cash\s+flows?|operating\s+cash\s+flows?|cash\s+from\s+operations?|"
        r"net\s+cash\s+(?:provided\s+by|generated\s+from)\s+operating\s+activities)\b",
        re.IGNORECASE,
    ),
    "change_in_working_capital": re.compile(
        r"\b(change(?:s)?\s+in|movement(?:s)?\s+in)?\s*working\s+capital\b", re.IGNORECASE
    ),
    "income_tax_paid": re.compile(
        r"\b((?:net\s+)?income\s+tax(?:ation)?(?:\s+and\s+royalty[-\s]?related\s+taxation)?\s+paid|"
        r"net\s+income\s+tax\s+and\s+royalty[-\s]?related\s+taxation\s+paid|"
        r"net\s+cash\s+tax\s+paid)\b",
        re.IGNORECASE,
    ),
    "royalties_paid": re.compile(
        r"\b(royalt(?:y|ies).{0,40}\bpaid|royalty[-\s]?related\s+taxation\s+paid)\b",
        re.IGNORECASE,
    ),
    "change_in_inventories": re.compile(
        r"\b((?:change(?:s)?|movement(?:s)?|increase|decrease)"
        r"(?:/\(?(?:decrease|increase)\)?)?\s+in\s+inventor(?:y|ies)|"
        r"inventor(?:y|ies)\s+movement(?:s)?)\b",
        re.IGNORECASE,
    ),
    "change_in_receivables": re.compile(
        r"\b((?:change(?:s)?|movement(?:s)?|increase|decrease)"
        r"(?:/\(?(?:decrease|increase)\)?)?\s+in\s+receivables?|"
        r"receivables?\s+movement(?:s)?)\b",
        re.IGNORECASE,
    ),
    "change_in_payables": re.compile(
        r"\b((?:change(?:s)?|movement(?:s)?|increase|decrease)"
        r"(?:/\(?(?:decrease|increase)\)?)?\s+in\s+payables?|"
        r"payables?\s+movement(?:s)?)\b",
        re.IGNORECASE,
    ),
    "depreciation_and_amortisation": re.compile(
        r"\b(depreciation(?:\s+and\s+amorti[sz]ation)?|amorti[sz]ation)\b",
        re.IGNORECASE,
    ),
    "impairment_expense": re.compile(
        r"\b(impairment(?:\s+(?:charge|expense|loss(?:es)?))?)\b",
        re.IGNORECASE,
    ),
    "cash_and_equivalents": re.compile(
        r"\b(cash\s+and\s+cash\s+equivalents|cash\s+equivalents|cash\s+on\s+hand|cash\s+at\s+bank|cash\s+balance)\b",
        re.IGNORECASE,
    ),
    "net_debt": NET_DEBT_LABEL_RE,
    "total_debt": TOTAL_DEBT_LABEL_RE,
    "current_assets": CURRENT_ASSETS_LABEL_RE,
    "current_liabilities": CURRENT_LIABILITIES_LABEL_RE,
    "total_assets": TOTAL_ASSETS_LABEL_RE,
    "total_liabilities": TOTAL_LIABILITIES_LABEL_RE,
    "total_equity": TOTAL_EQUITY_LABEL_RE,
    "shares_outstanding": re.compile(
        r"\b(shares\s+outstanding|shares\s+on\s+issue|issued\s+shares|ordinary\s+shares\s+on\s+issue|weighted\s+average\s+number\s+of\s+ordinary\s+shares)\b",
        re.IGNORECASE,
    ),
    "roic_pct": re.compile(r"\b(roic|return\s+on\s+invested\s+capital)\b", re.IGNORECASE),
    "capex": re.compile(r"\b(capex|capital\s+expenditure)\b", re.IGNORECASE),
    "guidance": re.compile(r"\b(guidance|outlook|forecast|expects?|targets?)\b", re.IGNORECASE),
    "growth_pct": GROWTH_LABEL_RE,
}
UNIT_HINT_RE = [
    (
        re.compile(
            r"(?:\b(?:US|A|C|NZ)\$\s*[’']?000\b|\$\s*[’']?000\b|\b[A$]{0,2}\s*'000\b)",
            re.IGNORECASE,
        ),
        1e3,
    ),
    (re.compile(r"\b(in\s+thousands|thousand\s+dollars|(?:US|A|C|NZ)\$'000)\b", re.IGNORECASE), 1e3),
    (re.compile(r"(?:\b(?:US|A|C|NZ)\$\s*(?:bn|billion)\b|\$\s*(?:bn|billion)\b|\b(in\s+billions)\b)", re.IGNORECASE), 1e9),
    (
        re.compile(
            r"(?:\b(?:US|A|C|NZ)\$\s*(?:m|mn|mm|million)\b|\$\s*(?:m|mn|mm|million)\b|\b(in\s+millions)\b)",
            re.IGNORECASE,
        ),
        1e6,
    ),
]
MONEY_METRICS = {
    "revenue",
    "segment_revenue",
    "gross_profit",
    "ebitda",
    "ebit",
    "net_income",
    "npat",
    "free_cash_flow",
    "operating_cash_flow",
    "change_in_working_capital",
    "income_tax_paid",
    "royalties_paid",
    "change_in_inventories",
    "change_in_receivables",
    "change_in_payables",
    "depreciation_and_amortisation",
    "impairment_expense",
    "cash_and_equivalents",
    "cash_and_equivalents_opening",
    "cash_and_equivalents_closing",
    "net_debt",
    "total_debt",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "capex",
}
SOURCE_MODE_PREFERENCE = {
    "table_bbox": 4,
    "docling_table": 3,
    "line": 2,
    "parse_error": 1,
}
DOC_PROFILE_PREFERENCE = {
    "audited_statement": 5,
    "official_results": 4,
    "pillar3": 3,
    "appendix_presentation": 2,
    "narrative_table": 1,
}
DEFAULT_COVERAGE_REQUIRED_METRICS_BY_PROFILE: Dict[str, List[str]] = {
    "resources": ["revenue", "net_income", "total_assets", "total_liabilities"],
    "banks": ["revenue", "net_income", "total_assets", "total_liabilities", "total_equity"],
}
BANK_TICKERS = {"CBA", "ANZ", "NAB", "WBC", "MQG", "BEN", "BOQ", "SUN"}
METRIC_BACKFILL_ALLOWED_DOC_PROFILES: Dict[str, Set[str]] = {
    "revenue": {"audited_statement", "official_results", "pillar3", "appendix_presentation"},
    "net_income": {"audited_statement", "official_results", "appendix_presentation"},
    "total_assets": {"audited_statement", "official_results", "pillar3", "appendix_presentation"},
    "total_liabilities": {"audited_statement", "official_results", "pillar3", "appendix_presentation"},
    "total_equity": {"audited_statement", "official_results", "pillar3", "appendix_presentation"},
    "cash_and_equivalents": {"audited_statement", "official_results", "appendix_presentation"},
}
BACKFILL_MIN_CONFIDENCE = 0.85
LARGE_MONEY_METRICS = {
    "revenue",
    "segment_revenue",
    "gross_profit",
    "ebitda",
    "ebit",
    "net_income",
    "npat",
    "free_cash_flow",
    "operating_cash_flow",
    "change_in_working_capital",
    "income_tax_paid",
    "royalties_paid",
    "change_in_inventories",
    "change_in_receivables",
    "change_in_payables",
    "depreciation_and_amortisation",
    "impairment_expense",
    "cash_and_equivalents",
    "cash_and_equivalents_opening",
    "cash_and_equivalents_closing",
    "net_debt",
    "total_debt",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "capex",
}

CANONICAL_STATEMENT_SCOPES = {"consolidated_statement", "appendix_statement"}
CANONICAL_CONFIDENCE_THRESHOLD = 2
PRIMARY_VARIANT_BASE_ORDER = (
    "",
    "statutory",
    "reported",
    "ifrs",
    "gaap",
    "adjusted",
    "before_significant_items",
    "ex_significant_items",
    "underlying",
)
INCOME_STATEMENT_METRICS = {
    "revenue",
    "segment_revenue",
    "gross_profit",
    "ebit",
    "ebitda",
    "net_income",
    "npat",
    "eps",
    "depreciation_and_amortisation",
    "impairment_expense",
}
BALANCE_SHEET_METRICS = {
    "cash_and_equivalents",
    "total_debt",
    "net_debt",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
}
CASH_FLOW_METRICS = {
    "cash_and_equivalents_opening",
    "cash_and_equivalents_closing",
    "free_cash_flow",
    "operating_cash_flow",
    "change_in_working_capital",
    "income_tax_paid",
    "royalties_paid",
    "change_in_inventories",
    "change_in_receivables",
    "change_in_payables",
    "capex",
}
OCF_COMPONENT_METRICS = {
    "change_in_working_capital",
    "income_tax_paid",
    "royalties_paid",
    "change_in_inventories",
    "change_in_receivables",
    "change_in_payables",
}
PROMOTABLE_TABLE_CONTEXT_REASONS = {"reconciliation_context"}
PROMOTABLE_TABLE_CONTEXT_METRICS = {
    "free_cash_flow",
    "operating_cash_flow",
    "capex",
    "net_debt",
    "total_debt",
}
EXPANDED_PROMOTABLE_TABLE_CONTEXT_REASONS = {"non_canonical_scope"}
EXPANDED_PROMOTABLE_TABLE_CONTEXT_METRICS = (
    set(METRIC_TABLE_LABELS.keys())
    | {
        "cash_and_equivalents_opening",
        "cash_and_equivalents_closing",
    }
)
EXPANDED_NARRATIVE_CONTEXT_METRICS = {
    "segment_revenue",
    "gross_profit",
    "gross_margin_pct",
    "operating_margin_pct",
    "npat",
    "shares_outstanding",
    "roic_pct",
    "guidance",
    "growth_pct",
}
TABLE_DERIVED_CANONICAL_SOURCE_MODES = {"table_bbox", "docling_table"}
SOURCE_CANONICAL_RE = re.compile(
    r"(appendix[\s\-_]*(4c|4d|4e|5b)|quarterly[\s\-_]*cash[\s\-_]*flow|"
    r"annual[\s\-_]*report|half[\s\-_]*year(?:ly)?|interim[\s\-_]*financial|financial[\s\-_]*report|full[\s\-_]*year)",
    re.IGNORECASE,
)
SOURCE_CONTEXT_RE = re.compile(
    r"(activities[\s\-_]*report|operations[\s\-_]*update|investor[\s\-_]*presentation|appendix[\s\-_]*3[ab]|change[\s\-_]*of[\s\-_]*director)",
    re.IGNORECASE,
)
CURRENCY_HINT_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:\bCAD\b|C\$|\$C(?:AD)?|CA\$|CDN\$)", re.IGNORECASE), "C$"),
    (re.compile(r"(?:\bAUD\b|A\$|\$A(?:UD)?)", re.IGNORECASE), "A$"),
    (re.compile(r"(?:\bUSD\b|US\$|\$U(?:SD)?)", re.IGNORECASE), "US$"),
    (re.compile(r"(?:\bNZD\b|NZ\$|\$NZD?)", re.IGNORECASE), "NZ$"),
    (re.compile(r"(?:\bEUR\b|€)", re.IGNORECASE), "€"),
    (re.compile(r"(?:\bGBP\b|£)", re.IGNORECASE), "£"),
]
APPENDIX_FORM_LAYOUT_RE = re.compile(
    r"\b(cash\s+and\s+cash\s+equivalents\s+at\s+end\s+of\s+(?:quarter|period)|"
    r"consolidated\s+statement\s+of\s+cash\s+flows?|listing\s+rule\s+4\.7b|item\s+\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
APPENDIX_METRIC_TABLE_RE = re.compile(
    r"\b(npat\s+to\s+ebitda|segment\s+ebitda|company\s+performance\s+metric|"
    r"ebitda|npat|operating\s+profit|revenue|gross\s+profit|total\s+assets?|"
    r"total\s+liabilities?|net\s+assets?)\b",
    re.IGNORECASE,
)
EQUITY_ROLLFORWARD_RE = re.compile(
    r"\b(transactions?\s+with|movement[s]?\s+in|retained\s+earnings|reserves?|share\s+capital|"
    r"attributable\s+to\s+owners|opening\s+balance|closing\s+balance|"
    r"flow\s+through\s+shares?|dividends?\s+paid|other\s+comprehensive\s+income)\b",
    re.IGNORECASE,
)
MONTH_NUM_BY_TOKEN = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class PDFParseTimeoutError(RuntimeError):
    pass


def _normalize_timeout_seconds(timeout_sec: Optional[float]) -> Optional[float]:
    if timeout_sec is None:
        return None
    try:
        t = float(timeout_sec)
    except (TypeError, ValueError):
        return None
    if t <= 0:
        return None
    return t


def _build_parse_failure_context_row(pdf: Path, *, reason: str, message: str = "") -> Dict[str, object]:
    return {
        "file": str(pdf),
        "line_no": 0,
        "metric": "",
        "metric_base": "",
        "metric_variant": "",
        "metric_alias": "",
        "value_type": "",
        "raw_value": "",
        "value": "",
        "currency": "",
        "period": "",
        "statement_period": "",
        "statement_period_end": "",
        "balance_position": "",
        "balance_date": "",
        "confidence": 0.0,
        "line": "",
        "row_label": "",
        "inside_table": False,
        "statement_scope": "other",
        "statement_title": "",
        "statement_family": "other",
        "table_statement_type": "unknown",
        "table_statement_confidence": 0.0,
        "statement_scope_reason": reason,
        "block_id": "",
        "table_id": "",
        "table_page": 0,
        "page_number": 0,
        "note_number": "",
        "source_mode": "parse_error",
        "canonical_confidence_score": 0,
        "context_reason": reason,
        "parse_error": message[:500],
    }


def extract_pdf_text(pdf: Path, timeout_sec: Optional[float] = None) -> str:
    timeout = _normalize_timeout_seconds(timeout_sec)
    try:
        cp = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        sec = int(timeout) if timeout is not None else 0
        raise PDFParseTimeoutError(f"pdftotext -layout timed out after {sec}s for {pdf}") from exc
    return cp.stdout.replace("\r", "\n")


def _is_valid_xml_char(ch: str) -> bool:
    cp = ord(ch)
    return (
        cp == 0x9
        or cp == 0xA
        or cp == 0xD
        or (0x20 <= cp <= 0xD7FF)
        or (0xE000 <= cp <= 0xFFFD)
        or (0x10000 <= cp <= 0x10FFFF)
    )


def sanitize_xml_text(s: str) -> str:
    return "".join(ch for ch in s if _is_valid_xml_char(ch))


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_bbox_layout_lines(pdf: Path, timeout_sec: Optional[float] = None) -> List[Dict[str, object]]:
    timeout = _normalize_timeout_seconds(timeout_sec)
    try:
        cp = subprocess.run(
            ["pdftotext", "-bbox-layout", str(pdf), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        sec = int(timeout) if timeout is not None else 0
        raise PDFParseTimeoutError(f"pdftotext -bbox-layout timed out after {sec}s for {pdf}") from exc
    xml_text = sanitize_xml_text(cp.stdout.decode("utf-8", errors="replace"))
    root = ET.fromstring(xml_text)
    out: List[Dict[str, object]] = []
    global_line_no = 0

    for page_idx, page in enumerate((e for e in root.iter() if _local_name(e.tag) == "page"), start=1):
        line_no_on_page = 0
        for line in (e for e in page.iter() if _local_name(e.tag) == "line"):
            words = [w for w in line if _local_name(w.tag) == "word"]
            if not words:
                continue
            line_words: List[Dict[str, object]] = []
            x0 = y0 = float("inf")
            x1 = y1 = float("-inf")
            for w in words:
                text = html.unescape("".join(w.itertext()).strip())
                if not text:
                    continue
                text = "".join(ch for ch in text if ch >= " " or ch in "\t\n\r")
                if not text:
                    continue
                wx0 = float(w.attrib.get("xMin", "0"))
                wy0 = float(w.attrib.get("yMin", "0"))
                wx1 = float(w.attrib.get("xMax", "0"))
                wy1 = float(w.attrib.get("yMax", "0"))
                x0 = min(x0, wx0)
                y0 = min(y0, wy0)
                x1 = max(x1, wx1)
                y1 = max(y1, wy1)
                line_words.append(
                    {
                        "text": text,
                        "x0": wx0,
                        "y0": wy0,
                        "x1": wx1,
                        "y1": wy1,
                        "x_center": (wx0 + wx1) / 2.0,
                    }
                )
            if not line_words:
                continue
            line_words.sort(key=lambda w: float(w["x0"]))
            line_text = " ".join(str(w["text"]) for w in line_words).strip()
            if not line_text:
                continue
            line_no_on_page += 1
            global_line_no += 1
            out.append(
                {
                    "page": page_idx,
                    "line_no": global_line_no,
                    "line_no_on_page": line_no_on_page,
                    "text": line_text,
                    "bbox": [x0, y0, x1, y1],
                    "words": line_words,
                }
            )
    return out


def _clean_numeric_token(text: str) -> str:
    t = text.replace("\u2212", "-").strip()
    t = t.strip("[]{}")
    # Strip trailing punctuation that is not part of numeric formats.
    while t and t[-1] in {";", ":"}:
        t = t[:-1]
    if t.endswith(","):
        t = t[:-1]
    return t.strip()


def parse_numeric_word_token(word_text: str) -> Optional[Dict[str, object]]:
    t = _clean_numeric_token(word_text)
    if not t:
        return None

    pm = re.fullmatch(r"\(?-?\d[\d,]*(?:\.\d+)?\)?%", t)
    if pm:
        num = t[:-1]
        val = parse_scaled_number(num, None)
        if val is None:
            return None
        return {
            "raw_value": t,
            "value_type": "percent",
            "value": float(val),
            "currency": "",
            "suffix": "",
            "minor_for_table": False,
        }

    m = NUM_TOKEN_RE.fullmatch(t)
    if not m:
        return None
    raw_num = m.group("num")
    suffix = m.group("suffix") or ""
    val = parse_scaled_number(raw_num, suffix)
    if val is None:
        return None
    return {
        "raw_value": t,
        "value_type": "amount",
        "value": float(val),
        "currency": m.group("currency") or "",
        "suffix": suffix,
        "minor_for_table": (
            (not (m.group("currency") or suffix))
            and (
                (
                    float(val).is_integer()
                    and (
                        1900 <= abs(float(val)) <= 2100
                        or len(raw_num.replace(",", "").replace("(", "").replace(")", "").replace("-", "")) <= 2
                    )
                )
                or ("." in raw_num and abs(float(val)) < 10.0)
            )
        ),
    }


def cluster_positions(xs: List[float], tol: float = 26.0) -> List[float]:
    if not xs:
        return []
    xs = sorted(xs)
    clusters: List[List[float]] = [[xs[0]]]
    for x in xs[1:]:
        prev = clusters[-1]
        center = sum(prev) / len(prev)
        if abs(x - center) <= tol:
            prev.append(x)
        else:
            clusters.append([x])
    return [sum(c) / len(c) for c in clusters]


def _column_index_for_x(x: float, centers: List[float], tol: float = 36.0) -> Optional[int]:
    if not centers:
        return None
    idx = min(range(len(centers)), key=lambda i: abs(centers[i] - x))
    if abs(centers[idx] - x) > tol:
        return None
    return idx


def _header_indices_for_region(page_lines: List[Dict[str, object]], start_idx: int) -> List[int]:
    out: List[int] = []
    blank_run = 0
    max_lookback = 16
    for i in range(start_idx - 1, max(-1, start_idx - max_lookback - 1), -1):
        line = page_lines[i]
        text = str(line["text"]).strip()
        if not text:
            blank_run += 1
            if blank_run >= 2 and out:
                break
            continue
        blank_run = 0
        num_count = len([t for t in line.get("numeric_words", []) if not bool(t.get("minor_for_table"))])
        has_period = bool(extract_period_labels(text)) or bool(MONTH_RE.search(text))
        has_unit = detect_unit_multiplier(text) is not None
        has_note = bool(re.search(r"^\s*note\b", text, re.IGNORECASE))
        shortish = len(text.split()) <= 8

        # A substantive numeric row usually means we've moved past header band.
        if num_count >= 1 and not (has_period or has_unit):
            break
        if has_period or has_unit or has_note:
            out.append(i)
            continue
        if shortish:
            out.append(i)
            continue
        if out:
            break
        break
    out.sort()
    return out


def infer_column_metadata(
    page_lines: List[Dict[str, object]], header_idxs: List[int], centers: List[float]
) -> List[Dict[str, object]]:
    cols: List[Dict[str, object]] = []
    sorted_centers = sorted(float(c) for c in centers)
    min_gap = None
    for i in range(1, len(sorted_centers)):
        gap = sorted_centers[i] - sorted_centers[i - 1]
        if gap <= 0:
            continue
        if min_gap is None or gap < min_gap:
            min_gap = gap
    x_tol = 56.0
    if min_gap is not None:
        x_tol = max(14.0, min(56.0, min_gap * 0.45))
    for c in centers:
        near_words: List[str] = []
        for i in header_idxs:
            for w in page_lines[i]["words"]:
                if abs(float(w["x_center"]) - c) <= x_tol:
                    near_words.append(str(w["text"]))
        near_text = " ".join(near_words).strip()
        period = ""
        labels = extract_period_labels(near_text)
        if labels:
            period = labels[-1][1]
            mixed_date = infer_header_date_from_mixed_text(near_text)
            if mixed_date and _period_label_kind(period) in {"year", "yearish", "other"}:
                period = mixed_date
        else:
            mixed_date = infer_header_date_from_mixed_text(near_text)
            if mixed_date:
                period = mixed_date
            else:
                m = re.search(r"\b(?:FY|Q[1-4]|H[12])\s*[-/]?\s*(?:20)?\d{2}\b", near_text, re.IGNORECASE)
                if m:
                    period = " ".join(m.group(0).split())
                else:
                    y = re.search(r"\b20\d{2}[A-Za-z]?\b", near_text)
                    if y:
                        period = y.group(0)
        if not period:
            m = re.search(r"\b(?:FY|Q[1-4]|H[12])\s*[-/]?\s*(?:20)?\d{2}\b", near_text, re.IGNORECASE)
            if m:
                period = " ".join(m.group(0).split())
            else:
                y = re.search(r"\b20\d{2}[A-Za-z]?\b", near_text)
                if y:
                    period = y.group(0)
        if not period:
            rel = RELATIVE_PERIOD_RE.search(near_text)
            if rel:
                period = " ".join(rel.group(0).split())
        is_variance = bool(re.search(r"\b(var|variance|change|delta|%|vs)\b", near_text, re.IGNORECASE))
        cols.append({"x_center": c, "header_text": near_text, "period": period, "is_variance": is_variance})
    return cols


def infer_header_date_from_mixed_text(text: str) -> str:
    raw = _normalize_space(text)
    if not raw:
        return ""
    tokens = re.findall(r"[A-Za-z]+|\d{1,4}", raw)
    if not tokens:
        return ""
    month_positions: List[Tuple[int, str]] = []
    for i, tok in enumerate(tokens):
        month_num = MONTH_NUM_BY_TOKEN.get(tok.lower())
        if month_num is not None:
            month_positions.append((i, calendar.month_name[month_num]))
    if not month_positions:
        return ""
    year_positions = [(i, int(tok)) for i, tok in enumerate(tokens) if re.fullmatch(r"20\d{2}", tok)]
    day_positions = [(i, int(tok)) for i, tok in enumerate(tokens) if re.fullmatch(r"\d{1,2}", tok) and 1 <= int(tok) <= 31]
    if not year_positions or not day_positions:
        return ""
    best = None
    for m_idx, month_name in month_positions:
        nearest_year = min(year_positions, key=lambda t: abs(t[0] - m_idx))
        nearest_day = min(day_positions, key=lambda t: abs(t[0] - m_idx))
        score = abs(nearest_year[0] - m_idx) + abs(nearest_day[0] - m_idx)
        if best is None or score < best[0]:
            best = (score, nearest_day[1], month_name, nearest_year[1])
    if not best:
        return ""
    _, day, month_name, year = best
    return f"{day} {month_name} {year}"


def _period_label_kind(label: str) -> str:
    text = _normalize_space(label)
    lower = text.lower()
    if not text:
        return "other"
    if PERIOD_PHRASE_RE.search(text):
        return "phrase"
    if RELATIVE_PERIOD_RE.search(text):
        return "relative"
    has_date = bool(DATE_PERIOD_RE.search(text))
    has_fiscal = bool(FISCAL_PERIOD_RE.search(text))
    if has_date and has_fiscal:
        return "fiscal_date"
    if has_date:
        return "date"
    if has_fiscal:
        return "fiscal"
    if BARE_YEAR_RE.fullmatch(text):
        return "year"
    if BARE_YEAR_RE.search(text):
        return "yearish"
    if "quarter" in lower or "half" in lower or "year" in lower:
        return "period_word"
    return "other"


def _period_specificity_rank(label: str) -> int:
    kind = _period_label_kind(label)
    ranks = {
        "phrase": 0,
        "fiscal_date": 1,
        "date": 2,
        "fiscal": 3,
        "relative": 4,
        "period_word": 5,
        "other": 6,
        "yearish": 7,
        "year": 8,
    }
    return ranks.get(kind, 9)


def infer_region_period_hint(page_lines: List[Dict[str, object]], start_idx: int, end_idx: int) -> str:
    if not page_lines:
        return ""
    scan_start = max(0, start_idx - 60)
    scan_end = min(len(page_lines), end_idx + 60)
    candidates: List[Dict[str, object]] = []
    for i in range(scan_start, scan_end):
        txt = str(page_lines[i].get("text", ""))
        labels = extract_period_labels(txt)
        if not labels:
            continue
        dist = min(abs(i - start_idx), abs(i - end_idx))
        for _, label in labels:
            norm = _normalize_space(label)
            candidates.append(
                {
                    "line_idx": i,
                    "dist": dist,
                    "label": norm,
                    "rank": _period_specificity_rank(norm),
                    "kind": _period_label_kind(norm),
                }
            )
    if not candidates:
        return ""
    center = (start_idx + end_idx) / 2.0
    best = min(candidates, key=lambda c: (int(c["rank"]), int(c["dist"]), abs(float(c["line_idx"]) - center)))
    best_label = str(best["label"])
    best_kind = str(best["kind"])
    best_line = int(best["line_idx"])

    # Attach a nearby complement so period hints capture both code+date when available
    # (e.g., "Q4 2025 (31 December 2025)").
    partner: Optional[Dict[str, object]] = None
    if best_kind in {"fiscal", "date", "fiscal_date"}:
        wanted = {"date", "fiscal", "fiscal_date"}
        for cand in candidates:
            if cand is best:
                continue
            if str(cand["kind"]) not in wanted:
                continue
            if abs(int(cand["line_idx"]) - best_line) > 6:
                continue
            if partner is None or (int(cand["rank"]), int(cand["dist"])) < (
                int(partner["rank"]),
                int(partner["dist"]),
            ):
                partner = cand
    if partner:
        partner_label = str(partner["label"])
        if partner_label != best_label:
            if _period_label_kind(best_label) in {"fiscal", "fiscal_date"} and _period_label_kind(partner_label) == "date":
                return f"{best_label} ({partner_label})"
            if _period_label_kind(best_label) == "date" and _period_label_kind(partner_label) in {"fiscal", "fiscal_date"}:
                return f"{partner_label} ({best_label})"
    return best_label


def infer_document_period_hint(by_page: Dict[int, List[Dict[str, object]]]) -> str:
    candidates: List[Dict[str, object]] = []
    seen: set = set()

    def add_candidates(text: str, page: int, idx: int) -> None:
        txt = _normalize_space(text)
        if not txt:
            return
        labels = extract_period_labels(txt)
        if not labels:
            return
        lower = txt.lower()
        ctx_match = re.search(r"\b(quarter\s+ended|period\s+ending|months?\s+ended|as\s+at|year\s+ended)\b", lower)
        for pos, label in labels:
            norm = _normalize_space(label)
            context_pref = 1
            if ctx_match and pos >= ctx_match.start():
                context_pref = 0
            key = (norm.lower(), page, context_pref)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "label": norm,
                    "kind": _period_label_kind(norm),
                    "rank": _period_specificity_rank(norm),
                    "page": page,
                    "idx": idx,
                    "context_pref": context_pref,
                }
            )

    for page in sorted(by_page.keys()):
        lines = by_page[page]
        for idx, ln in enumerate(lines):
            txt = str(ln.get("text", ""))
            add_candidates(txt, page, idx)
            if idx + 1 < len(lines):
                next_txt = str(lines[idx + 1].get("text", ""))
                add_candidates(f"{txt} {next_txt}", page, idx)
    if not candidates:
        return ""

    preferred = [c for c in candidates if str(c["kind"]) in {"phrase", "fiscal_date", "date", "fiscal"}]
    search = preferred or candidates
    best = min(
        search,
        key=lambda c: (int(c["context_pref"]), int(c["rank"]), int(c["page"]), int(c["idx"])),
    )
    return str(best["label"])


def _parse_date_label(text: str) -> Optional[date]:
    m = DATE_PERIOD_RE.search(text or "")
    if m:
        parts = m.group(0).split()
        if len(parts) == 3:
            try:
                day = int(parts[0])
                year = int(parts[2])
            except ValueError:
                day = -1
                year = -1
            month_token = re.sub(r"[^A-Za-z]", "", parts[1]).lower()
            month = MONTH_NUM_BY_TOKEN.get(month_token)
            if month is not None and day > 0 and year > 0:
                try:
                    return date(year, month, day)
                except ValueError:
                    pass
    for label in _extract_explicit_date_labels(text):
        m2 = DATE_PERIOD_RE.search(label)
        if not m2:
            continue
        p2 = m2.group(0).split()
        if len(p2) != 3:
            continue
        try:
            day2 = int(p2[0])
            year2 = int(p2[2])
        except ValueError:
            continue
        month_token2 = re.sub(r"[^A-Za-z]", "", p2[1]).lower()
        month2 = MONTH_NUM_BY_TOKEN.get(month_token2)
        if month2 is None:
            continue
        try:
            return date(year2, month2, day2)
        except ValueError:
            continue
    return None


def _extract_explicit_date_labels(text: str) -> List[str]:
    src = text or ""
    result_with_pos: List[Tuple[int, str]] = []
    seen_text = set()
    seen_dates = set()

    def push_date(day: int, month_token: str, year: int, pos: int) -> None:
        month = MONTH_NUM_BY_TOKEN.get(re.sub(r"[^A-Za-z]", "", month_token).lower())
        if month is None:
            return
        try:
            d = date(year, month, day)
        except ValueError:
            return
        lab = f"{d.day} {calendar.month_name[d.month]} {d.year}"
        key = lab.lower()
        dk = d.isoformat()
        if dk in seen_dates or key in seen_text:
            return
        seen_dates.add(dk)
        seen_text.add(key)
        result_with_pos.append((pos, lab))

    for m in DATE_PERIOD_RE.finditer(src):
        lab = _normalize_space(m.group(0))
        key = lab.lower()
        try:
            p = lab.split()
            d = date(
                int(p[2]),
                MONTH_NUM_BY_TOKEN.get(re.sub(r"[^A-Za-z]", "", p[1]).lower(), 0),
                int(p[0]),
            )
            dk = d.isoformat()
        except Exception:
            dk = ""
        if (dk and dk in seen_dates) or key in seen_text:
            continue
        if dk:
            seen_dates.add(dk)
        seen_text.add(key)
        result_with_pos.append((m.start(), lab))
    loose_re = re.compile(r"\b(\d{1,2})\s+([A-Za-z](?:\s*[A-Za-z]){2,10})\s+(20\d{2})\b")
    for m in loose_re.finditer(src):
        try:
            day = int(m.group(1))
            year = int(m.group(3))
        except ValueError:
            continue
        push_date(day, m.group(2), year, m.start())

    # Compact date headers in statements often use 2-digit years with spaces:
    #   "31 Dec 25", "30 Jun 24", "As at 31 Dec 25"
    short_year_space_re = re.compile(
        r"\b(?:AS\s+AT\s+)?(\d{1,2})\s+([A-Za-z](?:\s*[A-Za-z]){2,10})\s+(\d{2})\b",
        re.IGNORECASE,
    )
    for m in short_year_space_re.finditer(src):
        try:
            day = int(m.group(1))
            yy = int(m.group(3))
        except ValueError:
            continue
        full_year = 2000 + yy if yy <= 50 else 1900 + yy
        push_date(day, m.group(2), full_year, m.start())

    # Handle compressed two-column headers:
    #   "31 March 31 December 2025 2024" -> ["31 March 2025", "31 December 2024"]
    split_seq_re = re.compile(
        r"\b(\d{1,2})\s+([A-Za-z](?:\s*[A-Za-z]){2,10})\s+"
        r"(\d{1,2})\s+([A-Za-z](?:\s*[A-Za-z]){2,10})\s+"
        r"(20\d{2})\s+(20\d{2})\b"
    )
    for m in split_seq_re.finditer(src):
        try:
            d1 = int(m.group(1))
            d2 = int(m.group(3))
            y1 = int(m.group(5))
            y2 = int(m.group(6))
        except ValueError:
            continue
        push_date(d1, m.group(2), y1, m.start())
        push_date(d2, m.group(4), y2, m.start(3))

    # Prospectus / balance sheet headers: "AS AT 30-JUN-25", "30-JUN-24", "AS AT 30 June 2025"
    as_at_dd_mon_re = re.compile(
        r"\b(?:AS\s+AT\s+)?(\d{1,2})[-/]([A-Za-z]{3,4})[-/](\d{2,4})\b",
        re.IGNORECASE,
    )
    for m in as_at_dd_mon_re.finditer(src):
        try:
            day = int(m.group(1))
            month_token = m.group(2).strip()
            year_val = int(m.group(3))
        except ValueError:
            continue
        if year_val < 100:
            full_year = 2000 + year_val if year_val <= 50 else 1900 + year_val
        else:
            full_year = year_val
        month_num = MONTH_NUM_BY_TOKEN.get(re.sub(r"[^A-Za-z]", "", month_token).lower())
        if month_num is None:
            continue
        try:
            d = date(full_year, month_num, day)
        except ValueError:
            continue
        lab = f"{d.day} {calendar.month_name[d.month]} {d.year}"
        if lab.lower() in seen_text or d.isoformat() in seen_dates:
            continue
        seen_dates.add(d.isoformat())
        seen_text.add(lab.lower())
        result_with_pos.append((m.start(), lab))

    result_with_pos.sort(key=lambda x: x[0])
    return [lab for (_, lab) in result_with_pos]


def _parse_quarter_end_label(text: str) -> Optional[date]:
    m = re.search(r"\bQ([1-4])\s*[-/]?\s*(\d{2,4})\b", text or "", re.IGNORECASE)
    if not m:
        return None
    q = int(m.group(1))
    raw_year = int(m.group(2))
    year = raw_year if raw_year >= 100 else 2000 + raw_year
    month_day = {
        1: (3, 31),
        2: (6, 30),
        3: (9, 30),
        4: (12, 31),
    }
    month, day = month_day[q]
    return date(year, month, day)


def _format_date_label(d: date) -> str:
    return f"{d.day} {d.strftime('%B')} {d.year}"


def _is_quarter_end(d: date) -> bool:
    if d.month not in (3, 6, 9, 12):
        return False
    return d.day == calendar.monthrange(d.year, d.month)[1]


def _is_month_end(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def _shift_months(year: int, month: int, delta: int) -> Tuple[int, int]:
    m = month + delta
    y = year
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return y, m


def _quarter_end_for_month(year: int, month: int) -> date:
    q_end_month = ((month - 1) // 3 + 1) * 3
    q_end_day = calendar.monthrange(year, q_end_month)[1]
    return date(year, q_end_month, q_end_day)


def _quarter_end_on_or_before(d: date) -> date:
    q_end = _quarter_end_for_month(d.year, d.month)
    if d >= q_end:
        return q_end
    prev_y, prev_m = _shift_months(q_end.year, q_end.month, -3)
    prev_day = calendar.monthrange(prev_y, prev_m)[1]
    return date(prev_y, prev_m, prev_day)


def _previous_quarter_end(d: date) -> date:
    prev_y, prev_m = _shift_months(d.year, d.month, -3)
    prev_day = calendar.monthrange(prev_y, prev_m)[1]
    return date(prev_y, prev_m, prev_day)


def _previous_quarter_label_from_hint(hint: str) -> str:
    anchor = _parse_date_label(hint) or _parse_quarter_end_label(hint)
    if anchor is None:
        return ""
    base_qe = anchor if _is_quarter_end(anchor) else _quarter_end_on_or_before(anchor)
    return _format_date_label(_previous_quarter_end(base_qe))


def _extract_date_component_from_period_label(label: str) -> str:
    txt = (label or "").strip()
    if not txt:
        return ""
    m = DATE_PERIOD_RE.search(txt)
    if m:
        return _normalize_space(m.group(0))
    q = _parse_quarter_end_label(txt)
    if q is not None:
        return _format_date_label(q)
    return ""


def _extract_row_anchor_day_month(text: str) -> Optional[Tuple[int, int]]:
    m = re.search(rf"\b(?:as\s+at|at)\s+(\d{{1,2}})\s+({MONTH_TOKEN})\b", text or "", re.IGNORECASE)
    if not m:
        return None
    try:
        day = int(m.group(1))
    except ValueError:
        return None
    month_token = re.sub(r"[^A-Za-z]", "", m.group(2)).lower()
    month = MONTH_NUM_BY_TOKEN.get(month_token)
    if month is None:
        return None
    return (day, month)


def _year_from_period_hint(text: str) -> Optional[int]:
    d = _parse_date_label(text or "")
    if d is not None:
        return d.year
    q = _parse_quarter_end_label(text or "")
    if q is not None:
        return q.year
    fy = FY_PERIOD_RE.search(text or "")
    if fy:
        y = _parse_year_token(fy.group(1))
        if y is not None:
            return y
    by = BARE_YEAR_RE.search(text or "")
    if by:
        try:
            return int(by.group(0))
        except ValueError:
            return None
    return None


def _date_label_for_year_in_text(text: str, year: int) -> str:
    for label in _extract_explicit_date_labels(text):
        if _year_from_period_hint(label) == year:
            return label
    return ""


def _normalize_statement_title_value(text: str, statement_scope: str = "") -> str:
    t = _normalize_space(text)
    if not t:
        return ""
    lower = t.lower()
    consolidated_like = statement_scope in {"consolidated_statement", "appendix_statement"} or "consolidated" in lower
    if re.search(r"\bstatement\s+of\s+cash\s+flows?\b", lower):
        return "Consolidated statement of cash flows" if consolidated_like else "Statement of cash flows"
    if re.search(r"\bstatement\s+of\s+financial\s+position\b", lower):
        return "Consolidated statement of financial position" if consolidated_like else "Statement of financial position"
    if re.search(r"\bstatement\s+of\s+comprehensive\s+income\b", lower):
        return "Consolidated statement of comprehensive income" if consolidated_like else "Statement of comprehensive income"
    if re.search(r"\bstatement\s+of\s+profit\s+or\s+loss\b", lower):
        return "Consolidated statement of profit or loss" if consolidated_like else "Statement of profit or loss"
    return t


def _infer_statement_title_from_context(context_text: str, statement_scope: str = "") -> str:
    ctx = _normalize_space(context_text)
    if not ctx:
        return ""
    lower = ctx.lower()
    consolidated_like = statement_scope in {"consolidated_statement", "appendix_statement"} or "consolidated" in lower
    if re.search(r"\bstatement\s+of\s+cash\s+flows?\b|\bcash\s+flows?\b", lower):
        return "Consolidated statement of cash flows" if consolidated_like else "Statement of cash flows"
    if re.search(r"\bstatement\s+of\s+financial\s+position\b|\bfinancial\s+position\b", lower):
        return "Consolidated statement of financial position" if consolidated_like else "Statement of financial position"
    if re.search(r"\bstatement\s+of\s+comprehensive\s+income\b|\bcomprehensive\s+income\b", lower):
        return "Consolidated statement of comprehensive income" if consolidated_like else "Statement of comprehensive income"
    if re.search(r"\bstatement\s+of\s+profit\s+or\s+loss\b|\bprofit\s+or\s+loss\b", lower):
        return "Consolidated statement of profit or loss" if consolidated_like else "Statement of profit or loss"
    return ""


def infer_statement_family(statement_title: str, statement_scope: str = "", context_text: str = "") -> str:
    combined = _normalize_space(f"{statement_title} {context_text}").lower()
    scope = (statement_scope or "").strip().lower()
    if scope == "appendix_statement":
        if re.search(
            r"\b(profit\s+or\s+loss|statement\s+of\s+comprehensive\s+income|income\s+statement|"
            r"\brevenue\b|\bgross\s+profit\b|\bebitda?\b|\bnpat\b|operating\s+profit|"
            r"(?:profit|loss)\s+after\s+income\s+tax)\b",
            combined,
            re.IGNORECASE,
        ):
            return "income_statement"
        if re.search(
            r"\b(financial\s+position|balance\s+sheet|total\s+assets?|total\s+liabilities?|net\s+assets?|equity)\b",
            combined,
            re.IGNORECASE,
        ):
            return "balance_sheet"
        return "cash_flow"
    if not combined:
        return "other"
    if re.search(r"\b(cash\s+flows?|statement\s+of\s+cash\s+flows?)\b", combined):
        return "cash_flow"
    if re.search(r"\b(profit\s+or\s+loss|statement\s+of\s+comprehensive\s+income|income\s+statement)\b", combined):
        return "income_statement"
    if re.search(r"\bchanges?\s+in\s+equity\b", combined):
        return "equity_statement"
    if EQUITY_ROLLFORWARD_RE.search(combined) and not re.search(
        r"\b(financial\s+position|balance\s+sheet|total\s+assets?|total\s+liabilities?)\b",
        combined,
    ):
        return "equity_statement"
    if re.search(r"\b(financial\s+position|balance\s+sheet)\b", combined):
        return "balance_sheet"
    if re.search(r"\bcomprehensive\s+income\b", combined):
        return "income_statement"
    return "other"


def table_statement_type_to_family(statement_type: str) -> str:
    normalized = str(statement_type or "").strip().lower()
    if normalized == "income_statement":
        return "income_statement"
    if normalized == "balance_sheet":
        return "balance_sheet"
    if normalized == "cash_flow_statement":
        return "cash_flow"
    return "other"


def table_statement_type_to_title(statement_type: str) -> str:
    normalized = str(statement_type or "").strip().lower()
    if normalized == "income_statement":
        return "Statement of profit or loss"
    if normalized == "balance_sheet":
        return "Statement of financial position"
    if normalized == "cash_flow_statement":
        return "Statement of cash flows"
    return ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def infer_doc_date_from_path(file_path: str) -> str:
    candidates = [Path(file_path).name, file_path]
    for txt in candidates:
        m = DOC_DATE_RE.search(txt)
        if not m:
            continue
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            continue
    return ""


def infer_statement_period_end_from_path(file_path: str) -> str:
    candidates = [Path(file_path).stem, Path(file_path).name, file_path]
    best_date: Optional[date] = None
    for txt in candidates:
        norm = txt.replace("_", " ").replace("-", " ")
        for m in STATEMENT_DATE_WORD_RE.finditer(norm):
            try:
                day = int(m.group(1))
                year = int(m.group(3))
            except ValueError:
                continue
            month_token = re.sub(r"[^A-Za-z]", "", m.group(2)).lower()
            month_num = MONTH_NUM_BY_TOKEN.get(month_token)
            if month_num is None:
                continue
            try:
                d = date(year, month_num, day)
            except ValueError:
                continue
            if best_date is None or d > best_date:
                best_date = d
    return best_date.isoformat() if best_date is not None else ""


def infer_period_hint_from_docling_header(
    header_text: str,
    file_path: str = "",
    doc_date: str = "",
    allow_fallback_dates: bool = False,
) -> Tuple[str, str]:
    header = _normalize_space(header_text or "")

    dated_candidates: List[Tuple[date, str]] = []
    for label in _extract_explicit_date_labels(header):
        parsed = _parse_date_label(label) or _parse_quarter_end_label(label)
        if parsed is not None:
            dated_candidates.append((parsed, label))
    if dated_candidates:
        best_date, best_label = max(dated_candidates, key=lambda t: t[0])
        return best_label, best_date.isoformat()

    normalized_candidates: List[Tuple[str, str]] = []
    for m in FISCAL_PERIOD_RE.finditer(header):
        label = _normalize_space(m.group(0))
        period_end, _ = normalize_period_for_db(label, doc_date=doc_date)
        if period_end:
            normalized_candidates.append((period_end, label))
    if not normalized_candidates:
        for m in BARE_YEAR_RE.finditer(header):
            label = _normalize_space(m.group(0))
            period_end, _ = normalize_period_for_db(label, doc_date=doc_date)
            if period_end:
                normalized_candidates.append((period_end, label))
    if normalized_candidates:
        period_end, label = max(normalized_candidates, key=lambda t: t[0])
        return label, period_end

    if allow_fallback_dates:
        path_period_end = infer_statement_period_end_from_path(file_path) if file_path else ""
        if path_period_end:
            return path_period_end[:4], path_period_end
        if doc_date:
            return doc_date, doc_date
    return "", ""


def infer_company_from_path(file_path: str) -> str:
    p = Path(file_path)
    parts = p.parts
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if len(parts) >= 2:
        return parts[-2]
    return ""


def infer_doc_type_from_path(file_path: str) -> str:
    p = Path(file_path)
    parts = p.parts
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 2 < len(parts):
            return parts[idx + 2]
    return ""


def _parse_year_token(token: str) -> Optional[int]:
    t = token.strip()
    if not t.isdigit():
        return None
    year = int(t)
    if len(t) == 2:
        year += 2000
    if 1900 <= year <= 2100:
        return year
    return None


def normalize_period_for_db(period_label: str, doc_date: str = "", allow_doc_date_fallback: bool = True) -> Tuple[str, str]:
    period = _normalize_space(period_label or "")
    if not period:
        return "", doc_date
    lower = period.lower()
    explicit = _parse_date_label(period) or _parse_quarter_end_label(period)
    if explicit is not None and ("current quarter" in lower or "previous quarter" in lower):
        if "current quarter" in lower:
            qe = explicit if _is_quarter_end(explicit) else _quarter_end_on_or_before(explicit)
            iso = qe.isoformat()
            return iso, iso
        if "previous quarter" in lower or "prior quarter" in lower:
            if _is_quarter_end(explicit):
                iso = explicit.isoformat()
                return iso, iso
            current_qe = _quarter_end_on_or_before(explicit)
            prev_qe = _previous_quarter_end(current_qe)
            iso = prev_qe.isoformat()
            return iso, iso
    if explicit is not None:
        if "quarter ended" in lower and not _is_quarter_end(explicit):
            explicit = _quarter_end_on_or_before(explicit)
        iso = explicit.isoformat()
        return iso, iso
    # ASX fiscal shorthand mapping:
    # FY25 -> 2025-06-30, HY25/H1 FY25 -> 2024-12-31, H2 FY25 -> 2025-06-30
    h2 = H2_PERIOD_RE.search(period)
    if h2:
        y = _parse_year_token(h2.group(1))
        if y is not None:
            iso = f"{y:04d}-06-30"
            return iso, iso
    h1 = H1_PERIOD_RE.search(period) or HY_PERIOD_RE.search(period)
    if h1:
        y = _parse_year_token(h1.group(1))
        if y is not None:
            iso = f"{(y - 1):04d}-12-31"
            return iso, iso
    fy = FY_PERIOD_RE.search(period)
    if fy:
        y = _parse_year_token(fy.group(1))
        if y is not None:
            iso = f"{y:04d}-06-30"
            return iso, iso
    y2 = BARE_YEAR_RE.search(period)
    if y2:
        iso = f"{int(y2.group(0)):04d}-12-31"
        return iso, iso
    return "", (doc_date if allow_doc_date_fallback else "")


def infer_period_metadata(row: Dict[str, object]) -> Dict[str, object]:
    metric = str(row.get("metric", "")).strip().lower()
    statement_family = str(row.get("statement_family", "")).strip().lower()
    period_label = str(row.get("statement_period", "")).strip() or str(row.get("period", "")).strip()
    statement_period_end = str(row.get("statement_period_end", "")).strip()
    file_name = Path(str(row.get("file", ""))).name.lower()
    file_hint_text = _normalize_space(re.sub(r"[_-]+", " ", file_name))
    period_text = _normalize_space(period_label)
    context_text = _normalize_space(
        " ".join(
            [
                period_text,
                str(row.get("period", "")),
                str(row.get("table_header_text", "")),
                str(row.get("statement_scope_header", "")),
                str(row.get("statement_title", "")),
                str(row.get("row_label", "")),
                str(row.get("line", "")),
                file_name,
            ]
        )
    )
    scope = "unknown"
    if metric in BALANCE_SHEET_METRICS or statement_family == "balance_sheet":
        scope = "stock"
    elif metric in INCOME_STATEMENT_METRICS or metric in CASH_FLOW_METRICS or statement_family in {"income_statement", "cash_flow"}:
        scope = "flow"

    def _infer_reporting_cadence() -> Tuple[str, int, str]:
        # 1) Strongest signal: explicit period label on the row itself.
        months_match = MONTHS_ENDED_RE.search(period_text)
        if months_match:
            months = int(months_match.group(1))
            if months == 3:
                return "quarterly", 3, "statement_period_label"
            if months == 6:
                return "half_yearly", 6, "statement_period_label"
            if months == 12:
                return "annual", 12, "statement_period_label"
            return "other", months, "statement_period_label"

        if QUARTERLY_PERIOD_RE.search(period_text):
            return "quarterly", 3, "statement_period_label"
        if HALF_YEAR_PERIOD_RE.search(period_text):
            return "half_yearly", 6, "statement_period_label"
        if ANNUAL_PERIOD_RE.search(period_text):
            return "annual", 12, "statement_period_label"

        # 2) Phrase/date pairing from headers/context (e.g. "year ended 30 June 2023").
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", statement_period_end):
            for m in PERIOD_PHRASE_RE.finditer(context_text):
                phrase = _normalize_space(m.group(0))
                phrase_period_end, _ = normalize_period_for_db(phrase, allow_doc_date_fallback=False)
                if phrase_period_end != statement_period_end:
                    continue
                phrase_lower = phrase.lower()
                months_match = MONTHS_ENDED_RE.search(phrase_lower)
                if months_match:
                    months = int(months_match.group(1))
                    if months == 3:
                        return "quarterly", 3, "matched_period_phrase"
                    if months == 6:
                        return "half_yearly", 6, "matched_period_phrase"
                    if months == 12:
                        return "annual", 12, "matched_period_phrase"
                    return "other", months, "matched_period_phrase"
                if "quarter" in phrase_lower:
                    return "quarterly", 3, "matched_period_phrase"
                if "half" in phrase_lower:
                    return "half_yearly", 6, "matched_period_phrase"
                if "year" in phrase_lower:
                    return "annual", 12, "matched_period_phrase"

        # 3) Secondary signal: broad context text.
        months_match = MONTHS_ENDED_RE.search(context_text)
        if months_match:
            months = int(months_match.group(1))
            if months == 3:
                return "quarterly", 3, "context_period_phrase"
            if months == 6:
                return "half_yearly", 6, "context_period_phrase"
            if months == 12:
                return "annual", 12, "context_period_phrase"
            return "other", months, "context_period_phrase"

        if QUARTERLY_PERIOD_RE.search(context_text):
            return "quarterly", 3, "context_period_phrase"
        if HALF_YEAR_PERIOD_RE.search(context_text):
            return "half_yearly", 6, "context_period_phrase"
        if ANNUAL_PERIOD_RE.search(context_text):
            return "annual", 12, "context_period_phrase"

        # 4) Document-level hints from filename slug (fallback only).
        if DOC_QUARTERLY_HINT_RE.search(file_hint_text):
            return "quarterly", 3, "document_name_hint"
        if DOC_HALF_YEAR_HINT_RE.search(file_hint_text):
            return "half_yearly", 6, "document_name_hint"
        if DOC_ANNUAL_HINT_RE.search(file_hint_text):
            return "annual", 12, "document_name_hint"

        return "unknown", 0, "unresolved"

    reporting_cadence, reporting_period_months, reporting_cadence_source = _infer_reporting_cadence()
    if scope == "stock":
        period_type = "point_in_time"
        period_length_months = 0
        period_source = "statement_family_stock"
    else:
        period_type = reporting_cadence
        period_length_months = reporting_period_months
        period_source = reporting_cadence_source

    return {
        "period_label_effective": period_label,
        "period_type": period_type,
        "period_scope": scope,
        "period_length_months": period_length_months,
        "period_inference_source": period_source,
        "reporting_cadence": reporting_cadence,
        "reporting_period_months": reporting_period_months,
        "reporting_cadence_inference_source": reporting_cadence_source,
        "fiscal_tag": (
            "FY"
            if (reporting_cadence == "annual" or reporting_period_months == 12 or period_type == "annual")
            else (
                "HY"
                if (reporting_cadence == "half_yearly" or reporting_period_months == 6 or period_type == "half_yearly")
                else (
                    "QTR"
                    if (reporting_cadence == "quarterly" or reporting_period_months == 3 or period_type == "quarterly")
                    else "PIT"
                )
            )
        ),
    }


def annotate_period_metadata(rows: List[Dict[str, object]]) -> None:
    for rr in rows:
        rr.update(infer_period_metadata(rr))


def _to_float_or_none(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _to_int_flag(value: object, default: int = -1) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    if text in {"true", "t", "yes", "y", "1"}:
        return 1
    if text in {"false", "f", "no", "n", "0"}:
        return 0
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _metric_row_db_id(row: Dict[str, object]) -> str:
    col_x = row.get("col_x", "")
    col_x_text = ""
    if col_x not in ("", None):
        try:
            col_x_text = f"{float(col_x):.4f}"
        except (TypeError, ValueError):
            col_x_text = str(col_x)
    key_parts = [
        str(row.get("file", "")),
        str(row.get("line_no", "")),
        str(row.get("metric", "")),
        str(row.get("metric_variant", "")),
        str(row.get("value_type", "")),
        str(row.get("balance_position", "")),
        str(row.get("table_id", "")),
        str(row.get("block_id", "")),
        str(row.get("page_number", "")),
        col_x_text,
        str(row.get("raw_value", "")),
    ]
    key = "|".join(key_parts)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def store_metrics_sqlite(rows: List[Dict[str, object]], db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_metrics (
                metric_row_id TEXT PRIMARY KEY,
                file TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                doc_type TEXT NOT NULL DEFAULT '',
                doc_date TEXT NOT NULL DEFAULT '',
                metric TEXT NOT NULL,
                metric_base TEXT NOT NULL DEFAULT '',
                metric_variant TEXT NOT NULL DEFAULT '',
                metric_alias TEXT NOT NULL DEFAULT '',
                value_type TEXT NOT NULL,
                value_num REAL,
                raw_value TEXT NOT NULL DEFAULT '',
                currency TEXT NOT NULL DEFAULT '',
                period_label TEXT NOT NULL DEFAULT '',
                period_end_date TEXT NOT NULL DEFAULT '',
                statement_period_label TEXT NOT NULL DEFAULT '',
                statement_period_end TEXT NOT NULL DEFAULT '',
                period_label_effective TEXT NOT NULL DEFAULT '',
                period_type TEXT NOT NULL DEFAULT '',
                period_scope TEXT NOT NULL DEFAULT '',
                period_length_months INTEGER NOT NULL DEFAULT 0,
                period_inference_source TEXT NOT NULL DEFAULT '',
                reporting_cadence TEXT NOT NULL DEFAULT '',
                reporting_period_months INTEGER NOT NULL DEFAULT 0,
                reporting_cadence_inference_source TEXT NOT NULL DEFAULT '',
                balance_position TEXT NOT NULL DEFAULT '',
                balance_date TEXT NOT NULL DEFAULT '',
                period_sort_date TEXT NOT NULL DEFAULT '',
                period_sort_key INTEGER NOT NULL DEFAULT 0,
                integrity_score INTEGER NOT NULL DEFAULT 0,
                integrity_checks_evaluated INTEGER NOT NULL DEFAULT 0,
                integrity_checks_passed INTEGER NOT NULL DEFAULT 0,
                integrity_score_max INTEGER NOT NULL DEFAULT 4,
                integrity_balance_sheet_pass INTEGER NOT NULL DEFAULT -1,
                integrity_cash_flow_bridge_pass INTEGER NOT NULL DEFAULT -1,
                integrity_retained_earnings_pass INTEGER NOT NULL DEFAULT -1,
                integrity_income_integrity_pass INTEGER NOT NULL DEFAULT -1,
                data_anomaly_level TEXT NOT NULL DEFAULT 'UNKNOWN',
                statement_scope TEXT NOT NULL DEFAULT '',
                statement_title TEXT NOT NULL DEFAULT '',
                statement_family TEXT NOT NULL DEFAULT '',
                table_statement_type TEXT NOT NULL DEFAULT '',
                table_statement_confidence REAL NOT NULL DEFAULT 0.0,
                statement_scope_reason TEXT NOT NULL DEFAULT '',
                block_id TEXT NOT NULL DEFAULT '',
                table_id TEXT NOT NULL DEFAULT '',
                table_page INTEGER NOT NULL DEFAULT 0,
                page_number INTEGER NOT NULL DEFAULT 0,
                line_no INTEGER NOT NULL DEFAULT 0,
                inside_table INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 0.0,
                canonical_confidence_score INTEGER NOT NULL DEFAULT 0,
                canonical_tier TEXT NOT NULL DEFAULT '',
                canonical_promotion_reason TEXT NOT NULL DEFAULT '',
                promoted_to_canonical_tier INTEGER NOT NULL DEFAULT 0,
                source_mode TEXT NOT NULL DEFAULT '',
                created_utc TEXT NOT NULL,
                updated_utc TEXT NOT NULL
            )
            """
        )
        cur.execute("PRAGMA table_info(financial_metrics)")
        existing_cols = {str(row[1]) for row in cur.fetchall()}
        add_columns = {
            "metric_base": "TEXT NOT NULL DEFAULT ''",
            "metric_variant": "TEXT NOT NULL DEFAULT ''",
            "metric_alias": "TEXT NOT NULL DEFAULT ''",
            "statement_period_label": "TEXT NOT NULL DEFAULT ''",
            "statement_period_end": "TEXT NOT NULL DEFAULT ''",
            "period_label_effective": "TEXT NOT NULL DEFAULT ''",
            "period_type": "TEXT NOT NULL DEFAULT ''",
            "period_scope": "TEXT NOT NULL DEFAULT ''",
            "period_length_months": "INTEGER NOT NULL DEFAULT 0",
            "period_inference_source": "TEXT NOT NULL DEFAULT ''",
            "reporting_cadence": "TEXT NOT NULL DEFAULT ''",
            "reporting_period_months": "INTEGER NOT NULL DEFAULT 0",
            "reporting_cadence_inference_source": "TEXT NOT NULL DEFAULT ''",
            "balance_position": "TEXT NOT NULL DEFAULT ''",
            "balance_date": "TEXT NOT NULL DEFAULT ''",
            "statement_family": "TEXT NOT NULL DEFAULT ''",
            "table_statement_type": "TEXT NOT NULL DEFAULT ''",
            "table_statement_confidence": "REAL NOT NULL DEFAULT 0.0",
            "canonical_confidence_score": "INTEGER NOT NULL DEFAULT 0",
            "canonical_tier": "TEXT NOT NULL DEFAULT ''",
            "canonical_promotion_reason": "TEXT NOT NULL DEFAULT ''",
            "promoted_to_canonical_tier": "INTEGER NOT NULL DEFAULT 0",
            "integrity_score": "INTEGER NOT NULL DEFAULT 0",
            "integrity_checks_evaluated": "INTEGER NOT NULL DEFAULT 0",
            "integrity_checks_passed": "INTEGER NOT NULL DEFAULT 0",
            "integrity_score_max": "INTEGER NOT NULL DEFAULT 4",
            "integrity_balance_sheet_pass": "INTEGER NOT NULL DEFAULT -1",
            "integrity_cash_flow_bridge_pass": "INTEGER NOT NULL DEFAULT -1",
            "integrity_retained_earnings_pass": "INTEGER NOT NULL DEFAULT -1",
            "integrity_income_integrity_pass": "INTEGER NOT NULL DEFAULT -1",
            "data_anomaly_level": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        }
        for col, ddl in add_columns.items():
            if col not in existing_cols:
                cur.execute(f"ALTER TABLE financial_metrics ADD COLUMN {col} {ddl}")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_fin_metrics_company_metric_date "
            "ON financial_metrics(company, metric, period_sort_key)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_fin_metrics_metric_date "
            "ON financial_metrics(metric, period_sort_key)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_fin_metrics_scope "
            "ON financial_metrics(statement_scope)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_fin_metrics_doc_date "
            "ON financial_metrics(doc_date)"
        )

        upsert_sql = """
            INSERT INTO financial_metrics (
                metric_row_id, file, company, doc_type, doc_date,
                metric, metric_base, metric_variant, metric_alias, value_type, value_num, raw_value, currency,
                period_label, period_end_date, statement_period_label, statement_period_end,
                period_label_effective, period_type, period_scope, period_length_months, period_inference_source,
                reporting_cadence, reporting_period_months, reporting_cadence_inference_source,
                balance_position, balance_date,
                period_sort_date, period_sort_key, integrity_score, integrity_checks_evaluated, integrity_checks_passed,
                integrity_score_max, integrity_balance_sheet_pass, integrity_cash_flow_bridge_pass,
                integrity_retained_earnings_pass, integrity_income_integrity_pass, data_anomaly_level,
                statement_scope, statement_title, statement_family, table_statement_type, table_statement_confidence,
                statement_scope_reason,
                block_id, table_id, table_page, page_number, line_no,
                inside_table, confidence, canonical_confidence_score, canonical_tier, canonical_promotion_reason,
                promoted_to_canonical_tier, source_mode, created_utc, updated_utc
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(metric_row_id) DO UPDATE SET
                company=excluded.company,
                doc_type=excluded.doc_type,
                doc_date=excluded.doc_date,
                metric=excluded.metric,
                metric_base=excluded.metric_base,
                metric_variant=excluded.metric_variant,
                metric_alias=excluded.metric_alias,
                value_type=excluded.value_type,
                value_num=excluded.value_num,
                raw_value=excluded.raw_value,
                currency=excluded.currency,
                period_label=excluded.period_label,
                period_end_date=excluded.period_end_date,
                statement_period_label=excluded.statement_period_label,
                statement_period_end=excluded.statement_period_end,
                period_label_effective=excluded.period_label_effective,
                period_type=excluded.period_type,
                period_scope=excluded.period_scope,
                period_length_months=excluded.period_length_months,
                period_inference_source=excluded.period_inference_source,
                reporting_cadence=excluded.reporting_cadence,
                reporting_period_months=excluded.reporting_period_months,
                reporting_cadence_inference_source=excluded.reporting_cadence_inference_source,
                balance_position=excluded.balance_position,
                balance_date=excluded.balance_date,
                period_sort_date=excluded.period_sort_date,
                period_sort_key=excluded.period_sort_key,
                integrity_score=excluded.integrity_score,
                integrity_checks_evaluated=excluded.integrity_checks_evaluated,
                integrity_checks_passed=excluded.integrity_checks_passed,
                integrity_score_max=excluded.integrity_score_max,
                integrity_balance_sheet_pass=excluded.integrity_balance_sheet_pass,
                integrity_cash_flow_bridge_pass=excluded.integrity_cash_flow_bridge_pass,
                integrity_retained_earnings_pass=excluded.integrity_retained_earnings_pass,
                integrity_income_integrity_pass=excluded.integrity_income_integrity_pass,
                data_anomaly_level=excluded.data_anomaly_level,
                statement_scope=excluded.statement_scope,
                statement_title=excluded.statement_title,
                statement_family=excluded.statement_family,
                table_statement_type=excluded.table_statement_type,
                table_statement_confidence=excluded.table_statement_confidence,
                statement_scope_reason=excluded.statement_scope_reason,
                block_id=excluded.block_id,
                table_id=excluded.table_id,
                table_page=excluded.table_page,
                page_number=excluded.page_number,
                line_no=excluded.line_no,
                inside_table=excluded.inside_table,
                confidence=excluded.confidence,
                canonical_confidence_score=excluded.canonical_confidence_score,
                canonical_tier=excluded.canonical_tier,
                canonical_promotion_reason=excluded.canonical_promotion_reason,
                promoted_to_canonical_tier=excluded.promoted_to_canonical_tier,
                source_mode=excluded.source_mode,
                updated_utc=excluded.updated_utc
        """

        written = 0
        now = utc_now_iso()
        for row in rows:
            file_path = str(row.get("file", ""))
            doc_date = infer_doc_date_from_path(file_path)
            period_label = str(row.get("period", "")).strip()
            statement_period_label = str(row.get("statement_period", "")).strip() or period_label
            period_end_date, period_sort_date = normalize_period_for_db(period_label, doc_date=doc_date)
            statement_period_end, statement_period_sort = normalize_period_for_db(statement_period_label, doc_date=doc_date)
            sort_date = statement_period_sort or period_sort_date
            period_label_effective = str(row.get("period_label_effective", "")).strip() or statement_period_label
            period_type = str(row.get("period_type", "")).strip()
            period_scope = str(row.get("period_scope", "")).strip()
            period_length_months = int(row.get("period_length_months", 0) or 0)
            period_inference_source = str(row.get("period_inference_source", "")).strip()
            reporting_cadence = str(row.get("reporting_cadence", "")).strip()
            reporting_period_months = int(row.get("reporting_period_months", 0) or 0)
            reporting_cadence_inference_source = str(row.get("reporting_cadence_inference_source", "")).strip()
            canonical_tier = str(row.get("canonical_tier", "")).strip()
            canonical_promotion_reason = str(row.get("canonical_promotion_reason", "")).strip()
            promoted_to_canonical_tier = _to_int_flag(row.get("promoted_to_canonical_tier"), default=0)
            period_sort_key = 0
            if sort_date:
                try:
                    period_sort_key = int(sort_date.replace("-", ""))
                except ValueError:
                    period_sort_key = 0
            cur.execute(
                upsert_sql,
                (
                    _metric_row_db_id(row),
                    file_path,
                    infer_company_from_path(file_path),
                    infer_doc_type_from_path(file_path),
                    doc_date,
                    str(row.get("metric", "")),
                    str(row.get("metric_base", "")),
                    str(row.get("metric_variant", "")),
                    str(row.get("metric_alias", "")),
                    str(row.get("value_type", "")),
                    _to_float_or_none(row.get("value")),
                    str(row.get("raw_value", "")),
                    str(row.get("currency", "")),
                    period_label,
                    period_end_date,
                    statement_period_label,
                    statement_period_end,
                    period_label_effective,
                    period_type,
                    period_scope,
                    period_length_months,
                    period_inference_source,
                    reporting_cadence,
                    reporting_period_months,
                    reporting_cadence_inference_source,
                    str(row.get("balance_position", "")),
                    str(row.get("balance_date", "")),
                    sort_date,
                    period_sort_key,
                    int(row.get("integrity_score", 0) or 0),
                    int(row.get("integrity_checks_evaluated", 0) or 0),
                    int(row.get("integrity_checks_passed", 0) or 0),
                    int(row.get("integrity_score_max", 4) or 4),
                    _to_int_flag(row.get("integrity_balance_sheet_pass"), default=-1),
                    _to_int_flag(row.get("integrity_cash_flow_bridge_pass"), default=-1),
                    _to_int_flag(row.get("integrity_retained_earnings_pass"), default=-1),
                    _to_int_flag(row.get("integrity_income_integrity_pass"), default=-1),
                    str(row.get("data_anomaly_level", "UNKNOWN")),
                    str(row.get("statement_scope", row.get("statement_type", ""))),
                    str(row.get("statement_title", "")),
                    str(row.get("statement_family", "")),
                    str(row.get("table_statement_type", "")),
                    float(row.get("table_statement_confidence", 0.0) or 0.0),
                    str(row.get("statement_scope_reason", "")),
                    str(row.get("block_id", "")),
                    str(row.get("table_id", "")),
                    int(row.get("table_page", 0) or 0),
                    int(row.get("page_number", 0) or 0),
                    int(row.get("line_no", 0) or 0),
                    1 if bool(row.get("inside_table", False)) else 0,
                    float(row.get("confidence", 0.0) or 0.0),
                    int(row.get("canonical_confidence_score", 0) or 0),
                    canonical_tier,
                    canonical_promotion_reason,
                    promoted_to_canonical_tier,
                    str(row.get("source_mode", "")),
                    now,
                    now,
                ),
            )
            written += 1
        conn.commit()
        return written
    finally:
        conn.close()


def _collapse_integrity_flag(values: List[int]) -> int:
    if any(v == 0 for v in values):
        return 0
    if any(v == 1 for v in values):
        return 1
    return -1


def _integrity_flag_to_json_value(flag: int) -> Optional[bool]:
    if flag == 1:
        return True
    if flag == 0:
        return False
    return None


def build_statement_integrity_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    groups: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for row in rows:
        file_path = str(row.get("file", "")).strip()
        period_end = str(row.get("statement_period_end", "")).strip()
        if not file_path or not period_end:
            continue
        groups.setdefault((file_path, period_end), []).append(row)

    if not groups:
        return []

    anomaly_rank = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    out: List[Dict[str, object]] = []
    now = utc_now_iso()
    for (file_path, period_end), rs in groups.items():
        rep = sorted(
            rs,
            key=lambda r: (
                int(r.get("canonical_confidence_score", 0) or 0),
                float(r.get("confidence", 0.0) or 0.0),
                int(r.get("line_no", 0) or 0),
            ),
            reverse=True,
        )[0]

        bs_pass = _collapse_integrity_flag([_to_int_flag(r.get("integrity_balance_sheet_pass"), default=-1) for r in rs])
        cf_pass = _collapse_integrity_flag([_to_int_flag(r.get("integrity_cash_flow_bridge_pass"), default=-1) for r in rs])
        re_pass = _collapse_integrity_flag([_to_int_flag(r.get("integrity_retained_earnings_pass"), default=-1) for r in rs])
        income_pass = _collapse_integrity_flag([_to_int_flag(r.get("integrity_income_integrity_pass"), default=-1) for r in rs])

        anomalies = [str(r.get("data_anomaly_level", "UNKNOWN")).upper() for r in rs]
        data_anomaly_level = max(anomalies, key=lambda x: anomaly_rank.get(x, -1))

        statement_period_label = str(rep.get("statement_period", "")).strip() or str(rep.get("period", "")).strip()
        statement_period_end = period_end
        period_sort_date = statement_period_end if re.fullmatch(r"\d{4}-\d{2}-\d{2}", statement_period_end) else ""
        period_sort_key = int(period_sort_date.replace("-", "")) if period_sort_date else 0

        evaluated_flags = {
            "balance_sheet_identity": _integrity_flag_to_json_value(bs_pass),
            "cash_flow_bridge": _integrity_flag_to_json_value(cf_pass),
            "retained_earnings_roll": _integrity_flag_to_json_value(re_pass),
            "income_integrity": _integrity_flag_to_json_value(income_pass),
        }

        out.append(
            {
                "file": file_path,
                "company": infer_company_from_path(file_path),
                "doc_type": infer_doc_type_from_path(file_path),
                "doc_date": infer_doc_date_from_path(file_path),
                "statement_period_label": statement_period_label,
                "statement_period_end": statement_period_end,
                "period_sort_date": period_sort_date,
                "period_sort_key": period_sort_key,
                "integrity_score": int(max((int(r.get("integrity_score", 0) or 0) for r in rs), default=0)),
                "integrity_score_max": int(max((int(r.get("integrity_score_max", 4) or 4) for r in rs), default=4)),
                "integrity_checks_evaluated": int(max((int(r.get("integrity_checks_evaluated", 0) or 0) for r in rs), default=0)),
                "integrity_checks_passed": int(max((int(r.get("integrity_checks_passed", 0) or 0) for r in rs), default=0)),
                "bs_pass": bs_pass,
                "cf_pass": cf_pass,
                "re_pass": re_pass,
                "income_pass": income_pass,
                "data_anomaly_level": data_anomaly_level,
                "evaluated_flags_json": json.dumps(evaluated_flags, sort_keys=True),
                "created_utc": now,
                "updated_utc": now,
            }
        )
    return out


def store_statement_integrity_sqlite(rows: List[Dict[str, object]], db_path: Path) -> int:
    statement_rows = build_statement_integrity_rows(rows)
    if not statement_rows:
        return 0

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_statement_integrity (
                file TEXT NOT NULL,
                statement_period_end TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                doc_type TEXT NOT NULL DEFAULT '',
                doc_date TEXT NOT NULL DEFAULT '',
                statement_period_label TEXT NOT NULL DEFAULT '',
                period_sort_date TEXT NOT NULL DEFAULT '',
                period_sort_key INTEGER NOT NULL DEFAULT 0,
                integrity_score INTEGER NOT NULL DEFAULT 0,
                integrity_score_max INTEGER NOT NULL DEFAULT 4,
                integrity_checks_evaluated INTEGER NOT NULL DEFAULT 0,
                integrity_checks_passed INTEGER NOT NULL DEFAULT 0,
                bs_pass INTEGER NOT NULL DEFAULT -1,
                cf_pass INTEGER NOT NULL DEFAULT -1,
                re_pass INTEGER NOT NULL DEFAULT -1,
                income_pass INTEGER NOT NULL DEFAULT -1,
                data_anomaly_level TEXT NOT NULL DEFAULT 'UNKNOWN',
                evaluated_flags_json TEXT NOT NULL DEFAULT '{}',
                created_utc TEXT NOT NULL DEFAULT '',
                updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (file, statement_period_end)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_stmt_integrity_company_period "
            "ON financial_statement_integrity(company, period_sort_key)"
        )
        upsert_sql = """
            INSERT INTO financial_statement_integrity (
                file, statement_period_end, company, doc_type, doc_date, statement_period_label,
                period_sort_date, period_sort_key, integrity_score, integrity_score_max,
                integrity_checks_evaluated, integrity_checks_passed, bs_pass, cf_pass, re_pass, income_pass,
                data_anomaly_level, evaluated_flags_json, created_utc, updated_utc
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            ON CONFLICT(file, statement_period_end) DO UPDATE SET
                company=excluded.company,
                doc_type=excluded.doc_type,
                doc_date=excluded.doc_date,
                statement_period_label=excluded.statement_period_label,
                period_sort_date=excluded.period_sort_date,
                period_sort_key=excluded.period_sort_key,
                integrity_score=excluded.integrity_score,
                integrity_score_max=excluded.integrity_score_max,
                integrity_checks_evaluated=excluded.integrity_checks_evaluated,
                integrity_checks_passed=excluded.integrity_checks_passed,
                bs_pass=excluded.bs_pass,
                cf_pass=excluded.cf_pass,
                re_pass=excluded.re_pass,
                income_pass=excluded.income_pass,
                data_anomaly_level=excluded.data_anomaly_level,
                evaluated_flags_json=excluded.evaluated_flags_json,
                updated_utc=excluded.updated_utc
        """
        now = utc_now_iso()
        for r in statement_rows:
            cur.execute(
                upsert_sql,
                (
                    str(r.get("file", "")),
                    str(r.get("statement_period_end", "")),
                    str(r.get("company", "")),
                    str(r.get("doc_type", "")),
                    str(r.get("doc_date", "")),
                    str(r.get("statement_period_label", "")),
                    str(r.get("period_sort_date", "")),
                    int(r.get("period_sort_key", 0) or 0),
                    int(r.get("integrity_score", 0) or 0),
                    int(r.get("integrity_score_max", 4) or 4),
                    int(r.get("integrity_checks_evaluated", 0) or 0),
                    int(r.get("integrity_checks_passed", 0) or 0),
                    _to_int_flag(r.get("bs_pass"), default=-1),
                    _to_int_flag(r.get("cf_pass"), default=-1),
                    _to_int_flag(r.get("re_pass"), default=-1),
                    _to_int_flag(r.get("income_pass"), default=-1),
                    str(r.get("data_anomaly_level", "UNKNOWN")),
                    str(r.get("evaluated_flags_json", "{}")),
                    str(r.get("created_utc", now)),
                    now,
                ),
            )
        conn.commit()
        return len(statement_rows)
    finally:
        conn.close()


def detect_table_regions(page_lines: List[Dict[str, object]], min_data_rows: int = 2) -> List[Dict[str, object]]:
    data_idxs = [
        i
        for i, ln in enumerate(page_lines)
        if len([t for t in ln.get("numeric_words", []) if not bool(t.get("minor_for_table"))]) >= 1
    ]
    if not data_idxs:
        return []

    groups: List[List[int]] = []
    cur: List[int] = []
    prev = -999
    max_row_gap = 8
    for idx in data_idxs:
        if not cur or idx - prev <= max_row_gap:
            cur.append(idx)
        else:
            groups.append(cur)
            cur = [idx]
        prev = idx
    if cur:
        groups.append(cur)

    regions: List[Dict[str, object]] = []
    for g in groups:
        data_lines = [
            page_lines[i]
            for i in g
            if len([t for t in page_lines[i].get("numeric_words", []) if not bool(t.get("minor_for_table"))]) >= 1
        ]
        if len(data_lines) < min_data_rows:
            continue
        xs: List[float] = []
        for ln in data_lines:
            xs.extend(float(t["x_center"]) for t in ln.get("numeric_words", []) if not bool(t.get("minor_for_table")))
        centers = cluster_positions(xs, tol=26.0)
        if len(centers) < 2:
            continue
        good_rows = 0
        for ln in data_lines:
            assigned = 0
            for t in ln.get("numeric_words", []):
                if bool(t.get("minor_for_table")):
                    continue
                if _column_index_for_x(float(t["x_center"]), centers, tol=38.0) is not None:
                    assigned += 1
            if assigned >= 1:
                good_rows += 1
        if good_rows < min_data_rows:
            continue

        start_idx = min(g)
        end_idx = max(g)
        header_idxs = _header_indices_for_region(page_lines, start_idx)
        columns = infer_column_metadata(page_lines, header_idxs, centers)

        line_slice = page_lines[start_idx : end_idx + 1]
        bbox = [
            min(float(ln["bbox"][0]) for ln in line_slice),
            min(float(ln["bbox"][1]) for ln in line_slice),
            max(float(ln["bbox"][2]) for ln in line_slice),
            max(float(ln["bbox"][3]) for ln in line_slice),
        ]
        header_text = " ".join(str(page_lines[i]["text"]) for i in header_idxs)
        period_hint = infer_region_period_hint(page_lines, start_idx, end_idx)
        region_text_for_currency = " ".join(str(ln.get("text", "")) for ln in line_slice[:120])
        currency_hint_window = " ".join(
            str(page_lines[i]["text"])
            for i in range(max(0, start_idx - 6), min(len(page_lines), start_idx + 3))
        )
        currency_hint = detect_currency_hint(f"{header_text} {currency_hint_window} {region_text_for_currency}")
        unit_multiplier = detect_unit_multiplier(header_text) or 1.0
        regions.append(
            {
                "start_idx": start_idx,
                "end_idx": end_idx,
                "header_idxs": header_idxs,
                "columns": columns,
                "bbox": bbox,
                "unit_multiplier": unit_multiplier,
                "header_text": header_text,
                "currency_hint": currency_hint,
                "period_hint": period_hint,
            }
        )
    return regions


def _row_label_text_from_line(line: Dict[str, object], first_col_x: float) -> str:
    words = line.get("words", [])
    label_words = [w for w in words if float(w["x1"]) < first_col_x - 12.0]
    if label_words:
        return " ".join(str(w["text"]) for w in label_words).strip()
    # Fallback: use text prefix before first numeric token.
    text = str(line.get("text", ""))
    m = NUM_RE.search(text) or PCT_RE.search(text)
    if m:
        return text[: m.start()].strip()
    return ""


def _row_label_text_from_aligned_lines(
    page_lines: List[Dict[str, object]],
    start_idx: int,
    end_idx: int,
    target_idx: int,
    first_col_x: float,
) -> str:
    def _is_label_line_candidate(idx: int) -> bool:
        if idx < start_idx or idx > end_idx:
            return False
        ln = page_lines[idx]
        text = _normalize_space(str(ln.get("text", "")))
        if not text:
            return False
        if VALUE_PLACEHOLDER_RE.fullmatch(text):
            return False
        if NOTE_REFERENCE_LINE_RE.fullmatch(text):
            return False
        if PAGE_FOOTER_RE.search(text) or GENERIC_FOOTER_RE.search(text):
            return False
        if not re.search(r"[A-Za-z]", text):
            return False
        num_count = len([t for t in ln.get("numeric_words", []) if not bool(t.get("minor_for_table"))])
        if num_count > 0:
            return False
        bbox = ln.get("bbox")
        if bbox and float(bbox[2]) >= first_col_x - 6.0:
            return False
        return True

    def _row_label_from_stacked_value_band() -> str:
        # Some statement tables are encoded in stacked columns:
        # labels first, then one numeric line per row for each period column.
        lookback_start = max(start_idx, target_idx - 80)
        anchor_idx = -1
        for j in range(target_idx - 1, lookback_start - 1, -1):
            if not _is_label_line_candidate(j):
                continue
            if list(iter_metric_hits(str(page_lines[j].get("text", "")))):
                anchor_idx = j
                break
        if anchor_idx < 0:
            return ""

        label_start = anchor_idx
        while label_start - 1 >= lookback_start and _is_label_line_candidate(label_start - 1):
            label_start -= 1
            if anchor_idx - label_start > 24:
                break
        label_lines: List[Tuple[int, str]] = []
        for j in range(label_start, anchor_idx + 1):
            if not _is_label_line_candidate(j):
                continue
            txt = _normalize_space(str(page_lines[j].get("text", "")))
            if SECTION_HEADING_ONLY_RE.fullmatch(txt):
                continue
            label_lines.append((j, txt))
        if len(label_lines) < 2:
            return ""

        value_band_idxs: List[int] = []
        saw_values = False
        for j in range(anchor_idx + 1, end_idx + 1):
            ln = page_lines[j]
            txt = _normalize_space(str(ln.get("text", "")))
            num_count = len([t for t in ln.get("numeric_words", []) if not bool(t.get("minor_for_table"))])
            is_placeholder = bool(VALUE_PLACEHOLDER_RE.fullmatch(txt))
            is_note_ref = bool(NOTE_REFERENCE_LINE_RE.fullmatch(txt))
            if (num_count > 0 and not is_note_ref) or is_placeholder:
                value_band_idxs.append(j)
                saw_values = True
                continue
            if not saw_values:
                # Skip note/index columns between row labels and numeric cells.
                if is_note_ref or not txt:
                    continue
                continue
            # Stop once numeric stack ended and the next text block begins.
            if txt:
                break

        if target_idx not in value_band_idxs:
            return ""
        n_labels = len(label_lines)
        n_values = len(value_band_idxs)
        if n_values < n_labels:
            return ""
        # Require a compact, well-formed stacked band (typically 2-3 periods).
        # This avoids overextending alignment across mixed sections where labels
        # and values are no longer row-synchronous.
        if n_values > n_labels * 3:
            return ""
        if n_values % n_labels != 0:
            return ""

        pos = value_band_idxs.index(target_idx)
        mapped = label_lines[pos % n_labels][1]
        return mapped

    target = page_lines[target_idx]
    t_bbox = target.get("bbox")
    if not t_bbox:
        return _row_label_from_stacked_value_band()
    ty0 = float(t_bbox[1])
    ty1 = float(t_bbox[3])
    tyc = (ty0 + ty1) / 2.0
    candidates: List[Tuple[float, int, int, str]] = []
    for j in range(start_idx, end_idx + 1):
        if j == target_idx:
            continue
        ln = page_lines[j]
        text = str(ln.get("text", "")).strip()
        if not text:
            continue
        if PAGE_FOOTER_RE.search(text) or GENERIC_FOOTER_RE.search(text):
            continue
        num_count = len([t for t in ln.get("numeric_words", []) if not bool(t.get("minor_for_table"))])
        if num_count > 0:
            continue
        bbox = ln.get("bbox")
        if not bbox:
            continue
        lx1 = float(bbox[2])
        if lx1 >= first_col_x - 6.0:
            continue
        ly0 = float(bbox[1])
        ly1 = float(bbox[3])
        lyc = (ly0 + ly1) / 2.0
        y_overlap = min(ty1, ly1) - max(ty0, ly0)
        if y_overlap <= 0.0 and abs(lyc - tyc) > 3.2:
            continue
        candidates.append((abs(lyc - tyc), -len(text), j, text))
    if candidates:
        candidates.sort()
        return candidates[0][3]
    return _row_label_from_stacked_value_band()


def classify_pdf_source_kind(pdf: Path) -> str:
    text = f"{str(pdf).lower()} {pdf.name.lower()}"
    if APPENDIX_SCOPE_RE.search(text):
        return "appendix_report"
    if SOURCE_CANONICAL_RE.search(text):
        return "canonical_report"
    if SOURCE_CONTEXT_RE.search(text):
        return "context_update"
    return "other"


def _prepare_bbox_pages(pdf: Path, timeout_sec: Optional[float] = None) -> Dict[int, List[Dict[str, object]]]:
    lines = parse_bbox_layout_lines(pdf, timeout_sec=timeout_sec)
    by_page: Dict[int, List[Dict[str, object]]] = {}
    for ln in lines:
        page = int(ln["page"])
        num_words = []
        for w in ln.get("words", []):
            parsed = parse_numeric_word_token(str(w["text"]))
            if not parsed:
                continue
            num_words.append(
                {
                    **parsed,
                    "x_center": float(w["x_center"]),
                    "bbox": [w["x0"], w["y0"], w["x1"], w["y1"]],
                }
            )
        ln["numeric_words"] = num_words
        by_page.setdefault(page, []).append(ln)

    for page in list(by_page.keys()):
        # Sort by geometric position (y then x) for stable order across duplicate PDFs; pdftotext XML
        # element order can differ for identical layouts, causing different line indices otherwise.
        bbox_default = [0.0, 0.0, 0.0, 0.0]
        page_lines = sorted(
            by_page[page],
            key=lambda ln: (float((ln.get("bbox") or bbox_default)[1]), float((ln.get("bbox") or bbox_default)[0])),
        )
        for i, ln in enumerate(page_lines, start=1):
            ln["line_no_on_page"] = i
        active_section = ""
        for ln in page_lines:
            heading = detect_section_heading(str(ln.get("text", "")))
            if heading:
                active_section = heading
            ln["section_heading"] = active_section
            ln["section_kind"] = section_mode(active_section)
        by_page[page] = page_lines
    return by_page


def classify_statement_scope(block_text: str, header_text: str, source_kind: str) -> Tuple[str, str]:
    text = _normalize_space(f"{header_text}\n{block_text}")
    if not text:
        return "other", "empty_context"
    has_appendix_marker = bool(APPENDIX_SCOPE_RE.search(text))
    has_statement_layout = bool(STATEMENT_LAYOUT_RE.search(text))
    has_consolidated_marker = bool(CONSOLIDATED_SCOPE_RE.search(text))
    has_appendix_form_layout = bool(APPENDIX_FORM_LAYOUT_RE.search(text))
    has_note_marker = (
        bool(NOTE_SCOPE_RE.search(header_text))
        or bool(NOTE_INLINE_SCOPE_RE.search(text))
        or bool(NOTES_TO_SECTION_RE.search(text))
    )
    if PARENT_SCOPE_RE.search(text):
        return "parent_statement", "parent_marker"
    # Do not treat as note_disclosure when the only note signal is generic "notes to the"
    # and we have statement layout in a canonical report (primary statement table).
    note_is_generic_only = (
        (bool(NOTES_TO_SECTION_RE.search(text)) or bool(NOTES_TO_SECTION_RE.search(header_text)))
        and not NOTE_SCOPE_RE.search(header_text)
        and not NOTE_INLINE_SCOPE_RE.search(text)
    )
    if has_note_marker and not (
        note_is_generic_only and has_statement_layout and source_kind == "canonical_report"
    ):
        return "note_disclosure", "note_marker"
    if source_kind == "appendix_report" and has_appendix_form_layout:
        return "appendix_statement", "appendix_source_kind"
    if has_appendix_marker and APPENDIX_METRIC_TABLE_RE.search(text):
        return "appendix_statement", "appendix_metric_table"
    if source_kind == "appendix_report" and has_statement_layout:
        return "appendix_statement", "appendix_layout_source_kind"
    if has_statement_layout and has_consolidated_marker:
        return "consolidated_statement", "consolidated_layout"
    if source_kind == "canonical_report" and has_statement_layout:
        return "consolidated_statement", "canonical_layout_source_kind"
    if has_statement_layout:
        return "other", "layout_without_scope_marker"
    if has_appendix_marker:
        return "other", "appendix_marker_without_layout"
    if section_mode(text) == "presentational":
        return "narrative", "presentational_context"
    return "other", "fallback_other"


def segment_statement_blocks(
    pdf: Path,
    source_kind: str = "",
    prepared_pages: Optional[Dict[int, List[Dict[str, object]]]] = None,
) -> List[Dict[str, object]]:
    by_page = prepared_pages or _prepare_bbox_pages(pdf)
    if not by_page:
        return []
    source_kind = source_kind or classify_pdf_source_kind(pdf)
    blocks: List[Dict[str, object]] = []
    block_seq = 0
    stem = Path(pdf).stem

    for page in sorted(by_page.keys()):
        page_lines = by_page[page]
        regions = detect_table_regions(page_lines, min_data_rows=2)
        for region in regions:
            start_idx = int(region["start_idx"])
            end_idx = int(region["end_idx"])
            ctx_start = max(0, start_idx - 120)
            ctx_end = min(len(page_lines), end_idx + 12)
            context_lines = [
                str(ln.get("text", ""))
                for ln in page_lines[ctx_start:ctx_end]
                if str(ln.get("text", "")).strip()
            ]
            region_text_lines = [
                str(ln.get("text", ""))
                for ln in page_lines[start_idx : end_idx + 1]
                if str(ln.get("text", "")).strip()
            ]
            header_text = str(region.get("header_text", ""))
            scope_header = extract_statement_scope_header(context_lines)
            compact_context_lines = list(context_lines)
            if len(compact_context_lines) > 80:
                compact_context_lines = compact_context_lines[:20] + compact_context_lines[-60:]
            context_text = "\n".join(compact_context_lines + ([header_text] if header_text.strip() else []))
            if len(region_text_lines) <= 60:
                block_text = "\n".join(region_text_lines)
            else:
                block_text = "\n".join(region_text_lines[:30] + ["..."] + region_text_lines[-30:])
            parent_entity_context = bool(PARENT_ENTITY_FINANCIAL_RE.search("\n".join(context_lines)))
            classify_header_parts = [scope_header, context_text, header_text]
            if parent_entity_context:
                # Preserve explicit parent-entity marker so scope classification can fail closed.
                classify_header_parts.append("Parent entity financial information")
            classify_header = "\n".join([p for p in classify_header_parts if p.strip()])
            statement_scope, scope_reason = classify_statement_scope(
                block_text=block_text,
                header_text=classify_header,
                source_kind=source_kind,
            )
            title = scope_header or header_text.strip() or (region_text_lines[0] if region_text_lines else "")
            title = _normalize_statement_title_value(title, statement_scope=statement_scope)
            if re.fullmatch(r"\d{1,3}", _normalize_space(title)):
                title = ""
            if statement_scope in CANONICAL_STATEMENT_SCOPES and title and WEAK_TITLE_RE.search(title):
                title = ""
            if statement_scope in CANONICAL_STATEMENT_SCOPES and (not title or len(title.split()) > 18):
                for cand in reversed(context_lines):
                    t = _normalize_space(cand)
                    if not t or len(t.split()) > 18:
                        continue
                    if WEAK_TITLE_RE.search(t):
                        continue
                    if APPENDIX_SCOPE_RE.search(t) or STATEMENT_LAYOUT_RE.search(t):
                        title = _normalize_statement_title_value(t, statement_scope=statement_scope)
                        break
            if statement_scope in CANONICAL_STATEMENT_SCOPES and (not title or len(title.split()) > 18):
                ht = _normalize_space(header_text)
                if ht and not WEAK_TITLE_RE.search(ht):
                    title = _normalize_statement_title_value(ht, statement_scope=statement_scope)
            if statement_scope in CANONICAL_STATEMENT_SCOPES and (not title or WEAK_TITLE_RE.search(title)):
                title = "Consolidated statement of cash flows" if statement_scope == "appendix_statement" else title
            if statement_scope == "appendix_statement":
                # Appendix reports can contain all core statements. Prefer an
                # inferred family-specific title instead of coercing all
                # appendix blocks to cash-flow titles.
                appendix_hint_family = infer_statement_family(
                    statement_title=title,
                    statement_scope=statement_scope,
                    context_text=f"{context_text}\n{header_text}\n{block_text}",
                )
                if appendix_hint_family == "balance_sheet":
                    title = "Consolidated statement of financial position"
                elif appendix_hint_family == "income_statement":
                    title = "Consolidated statement of comprehensive income"
                elif appendix_hint_family == "equity_statement":
                    title = "Consolidated statement of changes in equity"
                elif appendix_hint_family == "cash_flow":
                    title = "Consolidated statement of cash flows"
                else:
                    normalized_title = _normalize_space(title).lower()
                    if re.search(
                        r"\b(cash\s+flows?|statement\s+of\s+cash\s+flows?|quarterly\s+cash\s+flow)\b",
                        normalized_title,
                        re.IGNORECASE,
                    ):
                        title = "Consolidated statement of cash flows"
            if re.search(r"\bconsolidated\s+statement\s+of\s+cash\s+flows?\b", _normalize_space(title), re.IGNORECASE):
                title = "Consolidated statement of cash flows"
            if (
                statement_scope == "appendix_statement"
                and title
                and not STATEMENT_LAYOUT_RE.search(title)
                and not APPENDIX_SCOPE_RE.search(title)
            ):
                title = "Consolidated statement of cash flows"
            if statement_scope in CANONICAL_STATEMENT_SCOPES and (not title or re.fullmatch(r"\d{1,3}", _normalize_space(title))):
                inferred = _infer_statement_title_from_context(context_text, statement_scope=statement_scope)
                if inferred:
                    title = inferred
            statement_family = infer_statement_family(
                statement_title=title,
                statement_scope=statement_scope,
                context_text=context_text,
            )

            line_start = int(page_lines[start_idx]["line_no"])
            line_end = int(page_lines[end_idx]["line_no"])
            note_number = extract_note_number(context_text)

            should_merge = False
            if blocks:
                prev = blocks[-1]
                if (
                    int(prev.get("page_start", -1)) == page
                    and int(prev.get("page_end", -1)) == page
                    and str(prev.get("statement_scope", "")) == statement_scope
                    and _normalize_space(str(prev.get("title", ""))).lower() == _normalize_space(title).lower()
                ):
                    prev_regions = list(prev.get("table_regions", []))
                    if prev_regions:
                        prev_end_idx = int(prev_regions[-1].get("end_idx", -999))
                        if start_idx - prev_end_idx <= 2:
                            should_merge = True

            if should_merge:
                block = blocks[-1]
                table_regions = list(block.get("table_regions", []))
                table_idx = len(table_regions) + 1
                table_id = f"{block['block_id']}:t{table_idx}"
                table_regions.append(
                    {
                        "table_id": table_id,
                        "page": page,
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "bbox": region.get("bbox"),
                        "columns": list(region.get("columns", [])),
                        "header_text": header_text,
                        "unit_multiplier": float(region.get("unit_multiplier", 1.0) or 1.0),
                        "currency_hint": str(region.get("currency_hint", "")),
                        "period_hint": str(region.get("period_hint", "")),
                    }
                )
                block["table_regions"] = table_regions
                block["line_end"] = max(int(block.get("line_end", line_end)), line_end)
                block["context_text"] = "\n".join([str(block.get("context_text", "")), context_text]).strip()
                if not str(block.get("note_number", "")) and note_number:
                    block["note_number"] = note_number
                if str(block.get("statement_family", "other")) == "other" and statement_family != "other":
                    block["statement_family"] = statement_family
                if parent_entity_context:
                    block["parent_entity_context"] = True
                continue

            block_seq += 1
            block_id = f"{stem}:p{page}-{page}:b{block_seq}"
            blocks.append(
                {
                    "block_id": block_id,
                    "title": title,
                    "statement_scope": statement_scope,
                    "statement_family": statement_family,
                    "scope_reason": scope_reason,
                    "page_start": int(page),
                    "page_end": int(page),
                    "line_start": line_start,
                    "line_end": line_end,
                    "context_text": context_text,
                    "parent_entity_context": parent_entity_context,
                    "note_number": note_number,
                    "table_regions": [
                        {
                            "table_id": f"{block_id}:t1",
                            "page": page,
                            "start_idx": start_idx,
                            "end_idx": end_idx,
                            "bbox": region.get("bbox"),
                            "columns": list(region.get("columns", [])),
                            "header_text": header_text,
                            "unit_multiplier": float(region.get("unit_multiplier", 1.0) or 1.0),
                            "currency_hint": str(region.get("currency_hint", "")),
                            "period_hint": str(region.get("period_hint", "")),
                        }
                    ],
                }
            )
    return blocks


def extract_metrics_from_blocks(
    pdf: Path,
    blocks: List[Dict[str, object]],
    strict_metric_rows_only: bool = True,
    prepared_pages: Optional[Dict[int, List[Dict[str, object]]]] = None,
    expanded_metric_scope: bool = False,
) -> List[Dict[str, object]]:
    by_page = prepared_pages or _prepare_bbox_pages(pdf)
    if not by_page or not blocks:
        return []
    document_period_hint = infer_document_period_hint(by_page)

    out: List[Dict[str, object]] = []
    percent_metrics = {"gross_margin_pct", "operating_margin_pct", "roic_pct", "growth_pct"}
    for block in blocks:
        statement_scope = str(block.get("statement_scope", "other"))
        statement_title = str(block.get("title", ""))
        statement_family = str(block.get("statement_family", "")).strip().lower() or infer_statement_family(
            statement_title=statement_title,
            statement_scope=statement_scope,
            context_text=str(block.get("context_text", "")),
        )
        scope_reason = str(block.get("scope_reason", ""))
        block_id = str(block.get("block_id", ""))
        note_number = str(block.get("note_number", ""))
        block_context_text = str(block.get("context_text", ""))
        block_parent_entity_context = bool(block.get("parent_entity_context")) or bool(
            PARENT_ENTITY_FINANCIAL_RE.search(block_context_text)
        )
        block_is_pro_forma = bool(PRO_FORMA_CONTEXT_RE.search(block_context_text))

        for region in list(block.get("table_regions", [])):
            page = int(region.get("page", 0) or 0)
            page_lines = by_page.get(page, [])
            if not page_lines:
                continue
            start_idx = int(region.get("start_idx", 0))
            end_idx = int(region.get("end_idx", 0))
            columns = list(region.get("columns", []))
            if not columns:
                continue
            region_currency_hint = str(region.get("currency_hint", "")).strip()
            if not region_currency_hint:
                near_start = max(0, start_idx - 40)
                near_end = min(len(page_lines), end_idx + 12)
                near_text = " ".join(str(page_lines[i].get("text", "")) for i in range(near_start, near_end))
                region_currency_hint = detect_currency_hint(near_text)
            if not region_currency_hint:
                region_currency_hint = detect_currency_hint(" ".join(str(ln.get("text", "")) for ln in page_lines))
            region_header_text = str(region.get("header_text", ""))
            region_is_pro_forma = block_is_pro_forma or bool(PRO_FORMA_CONTEXT_RE.search(region_header_text))
            region_lines = page_lines[start_idx : end_idx + 1]
            kinds = [str(ln.get("section_kind", "")) for ln in region_lines if str(ln.get("section_kind", ""))]
            region_kind = "unknown"
            if kinds:
                # Deterministic tie-break: set iteration order is undefined; when counts tie, prefer
                # "financial" so we don't skip regions that could be either financial or presentational.
                counts = {k: kinds.count(k) for k in set(kinds)}
                max_count = max(counts.values())
                candidates = [k for k, c in counts.items() if c == max_count]
                region_kind = "financial" if "financial" in candidates else min(candidates)
            if region_kind == "unknown" and statement_scope in CANONICAL_STATEMENT_SCOPES:
                region_kind = "financial"
            if strict_metric_rows_only and region_kind == "presentational":
                continue

            first_col_x = min(float(c["x_center"]) for c in columns)
            ordered_table_col_indices = [i for i, col in enumerate(columns) if not bool(col.get("is_variance"))]
            for idx in range(start_idx, end_idx + 1):
                line = page_lines[idx]
                row_num_words = list(line.get("numeric_words", []))
                if len(row_num_words) < 1:
                    continue
                line_text = str(line.get("text", ""))
                row_label = _row_label_text_from_line(line, first_col_x)
                if not row_label:
                    label_search_start = max(0, idx - 40)
                    label_search_end = min(len(page_lines) - 1, idx + 40)
                    row_label = _row_label_text_from_aligned_lines(
                        page_lines=page_lines,
                        start_idx=label_search_start,
                        end_idx=label_search_end,
                        target_idx=idx,
                        first_col_x=first_col_x,
                    )
                if not row_label and idx > 0:
                    label_parts: List[str] = []
                    label_part_idxs: List[int] = []
                    for back in range(idx - 1, max(-1, idx - 5), -1):
                        prev = page_lines[back]
                        prev_nums = len([t for t in prev.get("numeric_words", []) if not bool(t.get("minor_for_table"))])
                        prev_text = str(prev.get("text", "")).strip()
                        if prev_nums > 0:
                            continue
                        if not prev_text:
                            continue
                        label_parts.insert(0, prev_text)
                        label_part_idxs.insert(0, back)
                        if len(label_parts) >= 3:
                            break
                    if label_parts:
                        metric_line_pos = None
                        for pos, part in enumerate(label_parts):
                            if list(iter_metric_hits(part)):
                                metric_line_pos = pos
                                break
                        if metric_line_pos is not None:
                            label_parts = label_parts[metric_line_pos:]
                            label_part_idxs = label_part_idxs[metric_line_pos:]
                    if label_parts and label_part_idxs:
                        label_idx = label_part_idxs[-1]
                        numeric_since_label = 0
                        for probe in range(label_idx + 1, idx + 1):
                            probe_line = page_lines[probe]
                            probe_nums = len(
                                [t for t in probe_line.get("numeric_words", []) if not bool(t.get("minor_for_table"))]
                            )
                            if probe_nums >= 1:
                                numeric_since_label += 1
                        max_numeric_lines = max(1, len(ordered_table_col_indices))
                        if numeric_since_label > max_numeric_lines:
                            label_parts = []
                    row_label = " ".join(label_parts).strip()
                    if row_label and not re.search(r"[A-Za-z]", row_label):
                        row_label = ""

                row_label_metric_hits = list(iter_metric_hits(row_label)) if row_label else []
                metrics = list(row_label_metric_hits)
                label_text_for_match = row_label or line_text
                if not metrics and len([t for t in row_num_words if not bool(t.get("minor_for_table"))]) >= 2:
                    metrics = list(iter_metric_hits(line_text))
                    label_text_for_match = line_text
                if strict_metric_rows_only and len(metrics) > 1:
                    line_metrics = list(iter_metric_hits(line_text))
                    if len(line_metrics) == 1:
                        metrics = line_metrics
                    elif not line_metrics:
                        # Merged OCR rows can include multiple labels in one synthetic
                        # row label; keep the first hit to avoid metric fan-out.
                        metrics = [metrics[0]]
                if not metrics:
                    continue

                per_col_best: Dict[int, Dict[str, object]] = {}
                for tok in row_num_words:
                    if strict_metric_rows_only and bool(tok.get("minor_for_table")):
                        continue
                    cidx = _column_index_for_x(float(tok["x_center"]), [float(c["x_center"]) for c in columns], tol=38.0)
                    if cidx is None:
                        continue
                    if bool(columns[cidx].get("is_variance")):
                        continue
                    prev = per_col_best.get(cidx)
                    if prev is None or abs(float(tok.get("value", 0.0))) > abs(float(prev.get("value", 0.0))):
                        per_col_best[cidx] = tok

                if not per_col_best:
                    continue

                for metric in metrics:
                    if strict_metric_rows_only and not expanded_metric_scope and metric in {"growth_pct", "guidance"}:
                        continue
                    label_pat = METRIC_TABLE_LABELS.get(metric)
                    if strict_metric_rows_only and label_pat and not label_pat.search(label_text_for_match):
                        continue
                    if strict_metric_rows_only:
                        full_line = line_text
                        if label_text_for_match and label_text_for_match not in full_line:
                            full_line = f"{label_text_for_match} {full_line}".strip()
                        full_num_hits = [m for m in NUM_RE.finditer(full_line)]
                        full_pct_hits = [m for m in PCT_RE.finditer(full_line)]
                        if not is_explicit_table_metric_line(
                            full_line,
                            metric,
                            full_num_hits,
                            full_pct_hits,
                            section_kind=region_kind,
                        ):
                            continue
                    for cidx, tok in sorted(per_col_best.items(), key=lambda t: t[0]):
                        value_type = str(tok.get("value_type", "amount"))
                        if metric in percent_metrics and value_type != "percent":
                            continue
                        if metric not in percent_metrics and value_type != "amount":
                            continue
                        row_context_text = _normalize_space(f"{row_label} {line_text}")
                        row_currency_hint = detect_currency_hint(row_context_text)
                        region_multiplier = float(region.get("unit_multiplier", 1.0) or 1.0)
                        row_multiplier = detect_unit_multiplier(row_context_text) or 1.0
                        effective_multiplier = row_multiplier if row_multiplier != 1.0 else region_multiplier
                        base_period_value = str(columns[cidx].get("period", "")).strip() or str(region.get("period_hint", "")).strip()
                        statement_period_value = _resolve_table_period_for_column(
                            base_period=base_period_value,
                            row_label=row_label,
                            line_text=line_text,
                            block_context=str(block.get("context_text", "")),
                            col_idx=cidx,
                            ordered_col_indices=ordered_table_col_indices,
                            document_period_hint=document_period_hint,
                            allow_row_anchor=False,
                            statement_scope=statement_scope,
                            table_header_text=region_header_text,
                        )
                        period_value = _resolve_table_period_for_column(
                            base_period=base_period_value,
                            row_label=row_label,
                            line_text=line_text,
                            block_context=str(block.get("context_text", "")),
                            col_idx=cidx,
                            ordered_col_indices=ordered_table_col_indices,
                            document_period_hint=document_period_hint,
                            statement_scope=statement_scope,
                            table_header_text=region_header_text,
                        )
                        metric_name = metric
                        balance_position = ""
                        balance_date = ""
                        row_ctx_l = row_context_text.lower()
                        if metric == "cash_and_equivalents":
                            has_at_end = bool(
                                re.search(
                                    r"\b(at\s+(?:the\s+)?end\s+of\s+(?:quarter|period|year|half[\-\s]?year)|"
                                    r"end\s+of\s+(?:quarter|period|year|half[\-\s]?year)|"
                                    r"at\s+31\s+dec(?:ember)?|at\s+(?:the\s+)?end\s+of)\b",
                                    row_ctx_l,
                                )
                            )
                            has_opening = bool(
                                re.search(
                                    r"\b(at\s+(?:the\s+)?1\s+july|"
                                    r"at\s+(?:the\s+)?beginning(?:\s+of\s+(?:period|year|quarter|half[\-\s]?year))?|"
                                    r"opening|beginning(?:\s+of\s+(?:period|year|quarter|half[\-\s]?year))?)\b",
                                    row_ctx_l,
                                )
                            )
                            if has_opening:
                                metric_name = "cash_and_equivalents_opening"
                                balance_position = "opening"
                            elif has_at_end:
                                metric_name = "cash_and_equivalents_closing"
                                balance_position = "closing"
                            if balance_position:
                                period_l = period_value.lower()
                                if balance_position == "opening":
                                    if period_l.startswith("current quarter") or period_l.startswith("previous quarter"):
                                        opening_date = _previous_quarter_label_from_hint(period_value)
                                        balance_date = opening_date or _extract_date_component_from_period_label(period_value)
                                    else:
                                        balance_date = period_value
                                else:
                                    balance_date = _extract_date_component_from_period_label(period_value) or period_value
                        statement_period_end, _ = normalize_period_for_db(
                            statement_period_value or period_value,
                            doc_date=infer_doc_date_from_path(str(pdf)),
                            allow_doc_date_fallback=False,
                        )
                        metric_variant = detect_metric_variant(
                            metric_name,
                            row_label=row_label,
                            line_text=line_text,
                            table_header_text=region_header_text,
                        )
                        metric_alias = infer_metric_alias(metric_name, row_label=row_label, line_text=line_text)
                        rec = {
                            "file": str(pdf),
                            "line_no": int(line["line_no"]),
                            "metric": metric_name,
                            "metric_base": metric,
                            "metric_variant": metric_variant,
                            "metric_alias": metric_alias,
                            "value_type": value_type,
                            "raw_value": str(tok.get("raw_value", "")),
                            "value": tok.get("value", ""),
                            "currency": str(tok.get("currency", "") or row_currency_hint or region_currency_hint),
                            "period": period_value,
                            "statement_period": statement_period_value,
                            "statement_period_end": statement_period_end,
                            "balance_position": balance_position,
                            "balance_date": balance_date,
                            "confidence": 0.0,
                            "line": str(line["text"]),
                            "row_label": row_label,
                            "row_label_metric_hit_count": len(metrics),
                            "source_mode": "table_bbox",
                            "table_id": str(region.get("table_id", "")),
                            "table_page": int(page),
                            "table_bbox": region.get("bbox"),
                            "row_bbox": line.get("bbox"),
                            "col_x": float(columns[cidx]["x_center"]),
                            "table_header_text": region_header_text,
                            "statement_type": statement_scope,
                            "statement_scope_header": statement_title,
                            "statement_scope": statement_scope,
                            "statement_title": statement_title,
                            "statement_family": statement_family,
                            "statement_scope_reason": scope_reason,
                            "block_id": block_id,
                            "block_context_text": block_context_text,
                            "parent_entity_context": block_parent_entity_context,
                            "inside_table": True,
                            "page_number": int(page),
                            "note_number": note_number,
                            "pro_forma_context": region_is_pro_forma,
                        }
                        if value_type == "amount":
                            rec = apply_unit_multiplier(rec, effective_multiplier)
                        out.append(rec)
    return dedupe(out)


def _resolve_table_period_for_column(
    *,
    base_period: str,
    row_label: str,
    line_text: str,
    block_context: str,
    col_idx: int,
    ordered_col_indices: List[int],
    document_period_hint: str = "",
    allow_row_anchor: bool = True,
    statement_scope: str = "",
    table_header_text: str = "",
) -> str:
    period = (base_period or "").strip()
    doc_hint = (document_period_hint or "").strip()
    col_order_idx = -1
    try:
        col_order_idx = ordered_col_indices.index(col_idx)
    except ValueError:
        col_order_idx = -1
    header_dates = _extract_explicit_date_labels(table_header_text)
    context_dates = _extract_explicit_date_labels(block_context)

    def _date_for_col(date_labels: List[str]) -> str:
        if col_order_idx < 0 or not date_labels:
            return ""
        ncols = len(ordered_col_indices)
        ndates = len(date_labels)
        if ncols <= ndates:
            idx = col_order_idx
        else:
            # Right-align date labels against data columns when extra numeric
            # columns exist (for example row codes or note references).
            idx = col_order_idx - (ncols - ndates)
        if 0 <= idx < ndates:
            return date_labels[idx]
        trailing_cols = ncols - 1 - col_order_idx
        idx2 = ndates - 1 - trailing_cols
        if 0 <= idx2 < ndates:
            return date_labels[idx2]
        return ""

    if col_order_idx >= 0:
        hdr_period = _date_for_col(header_dates)
        if hdr_period:
            # Prefer column-level period metadata when it already resolved to an
            # explicit date. Header date extraction can be out-of-order in
            # stacked appendix layouts where labels are interleaved.
            if not period or not DATE_PERIOD_RE.search(period):
                period = hdr_period
        elif not period:
            ctx_period = _date_for_col(context_dates)
            if ctx_period:
                period = ctx_period
    if period and BARE_YEAR_RE.fullmatch(period):
        period_year = int(period)
        mapped = ""
        cand = _date_for_col(header_dates)
        if cand and _year_from_period_hint(cand) == period_year:
            mapped = cand
        if not mapped:
            cand = _date_for_col(context_dates)
            if cand and _year_from_period_hint(cand) == period_year:
                mapped = cand
        ctx_date = mapped or _date_label_for_year_in_text(block_context, period_year)
        if ctx_date:
            period = ctx_date
        else:
            doc_year = _year_from_period_hint(doc_hint)
            if doc_year is not None and str(doc_year) == period:
                period = doc_hint
            else:
                anchor = _parse_date_label(doc_hint) or _parse_date_label(block_context)
                if anchor is not None:
                    period = f"{anchor.day} {calendar.month_name[anchor.month]} {period_year}"
    row_ctx_raw = _normalize_space(f"{row_label} {line_text}")
    row_anchor = _extract_row_anchor_day_month(row_ctx_raw) if allow_row_anchor else None
    if row_anchor is not None:
        year = _year_from_period_hint(period) or _year_from_period_hint(doc_hint)
        if year is not None:
            day, month = row_anchor
            month_name = calendar.month_name[month]
            return f"{day} {month_name} {year}"
    if len(ordered_col_indices) < 2:
        return period
    quarter_cols = ordered_col_indices[-2:] if len(ordered_col_indices) >= 2 else ordered_col_indices
    current_col = quarter_cols[0] if quarter_cols else -1
    previous_col = quarter_cols[1] if len(quarter_cols) >= 2 else -1
    row_ctx = row_ctx_raw.lower()
    block_ctx = _normalize_space(block_context).lower()
    period_l = period.lower()

    has_cash_row_shape = bool(
        re.search(
            r"\bcash\s+and\s+cash\s+equivalents\b",
            row_ctx,
            re.IGNORECASE,
        )
    ) and bool(re.search(r"\b(at\s+end\s+of|at\s+beginning\s+of)\b", row_ctx, re.IGNORECASE))
    if (
        "current quarter" in block_ctx
        and ("quarter" in row_ctx or has_cash_row_shape)
    ):
        if col_idx == current_col:
            if period_l.startswith("current quarter"):
                if doc_hint and doc_hint.lower() not in period_l:
                    return f"Current quarter - {doc_hint}"
                return period
            if period_l.startswith("previous quarter") or period_l.startswith("prior quarter"):
                if doc_hint:
                    return f"Current quarter - {doc_hint}"
                return "Current quarter"
            if period:
                return f"Current quarter - {period}"
            if doc_hint:
                return f"Current quarter - {doc_hint}"
            return "Current quarter"
        if col_idx == previous_col:
            if period_l.startswith("previous quarter") or period_l.startswith("prior quarter"):
                if DATE_PERIOD_RE.search(period):
                    return period
                prev_hint = _previous_quarter_label_from_hint(doc_hint or period)
                if prev_hint:
                    return f"Previous quarter - {prev_hint}"
                return period
            if period_l.startswith("current quarter"):
                prev_hint = _previous_quarter_label_from_hint(doc_hint or period)
                if prev_hint:
                    return f"Previous quarter - {prev_hint}"
                return "Previous quarter"
            prev_hint = _previous_quarter_label_from_hint(doc_hint or period)
            if prev_hint:
                return f"Previous quarter - {prev_hint}"
            return "Previous quarter"
    if (
        not period
        and statement_scope == "appendix_statement"
        and len(ordered_col_indices) >= 2
        and doc_hint
    ):
        anchor = _parse_date_label(doc_hint) or _parse_quarter_end_label(doc_hint)
        if anchor is not None:
            current_qe = anchor if _is_quarter_end(anchor) else _quarter_end_on_or_before(anchor)
            current_label = _format_date_label(current_qe)
            if col_idx == current_col:
                return f"Current quarter - {current_label}"
            if col_idx == previous_col:
                previous_label = _format_date_label(_previous_quarter_end(current_qe))
                return f"Previous quarter - {previous_label}"
    return period


def metric_expected_families(metric_name: str) -> set:
    m = (metric_name or "").strip().lower()
    if not m:
        return set()
    if m in INCOME_STATEMENT_METRICS:
        return {"income_statement"}
    if m in BALANCE_SHEET_METRICS:
        # Cash appears in both balance sheet and cash flow statements.
        if m == "cash_and_equivalents":
            return {"balance_sheet", "cash_flow"}
        return {"balance_sheet"}
    if m in CASH_FLOW_METRICS:
        return {"cash_flow"}
    return set()


def _is_money_amount_row(row: Dict[str, object]) -> bool:
    return str(row.get("value_type", "")).strip().lower() == "amount" and str(row.get("metric", "")).strip().lower() in MONEY_METRICS


def _safe_abs_value(row: Dict[str, object]) -> Optional[float]:
    try:
        return abs(float(row.get("value", "")))
    except (TypeError, ValueError):
        return None


def _raw_has_explicit_scale(raw_value: str) -> bool:
    raw = (raw_value or "").strip().lower()
    if not raw:
        return False
    if re.search(r"\b(thousand|million|billion|trillion|mn|mm|bn)\b", raw):
        return True
    return bool(re.search(r"\d(?:\.\d+)?\s*[kmbt]\b", raw))


def _inline_scale_multiplier_for_raw(raw_value: str, text: str) -> float:
    raw = _normalize_space(raw_value or "")
    hay = _normalize_space(text or "")
    if not raw or not hay:
        return 1.0
    pat = re.compile(
        rf"{re.escape(raw)}\s*(bn|billion|mn|mm|million|thousand|trillion|k|m|b|t)\b",
        re.IGNORECASE,
    )
    m = pat.search(hay)
    if not m:
        return 1.0
    return _suffix_multiplier(m.group(1))


def _contextual_unit_multiplier(row: Dict[str, object]) -> float:
    candidates: List[float] = []
    raw_value = str(row.get("raw_value", ""))
    local_fields = [
        str(row.get("line", "")),
        str(row.get("row_label", "")),
        str(row.get("table_header_text", "")),
        str(row.get("statement_scope_header", "")),
        str(row.get("statement_title", "")),
        str(row.get("block_context_text", "")),
    ]
    for txt in local_fields:
        if not txt:
            continue
        hint = detect_unit_multiplier(txt)
        if hint is not None and hint > 1.0:
            candidates.append(float(hint))
    inline_fields = local_fields
    for txt in inline_fields:
        if not txt:
            continue
        inline_hint = _inline_scale_multiplier_for_raw(raw_value, txt)
        if inline_hint > 1.0:
            candidates.append(float(inline_hint))
    return max(candidates) if candidates else 1.0


def _maybe_repair_contextual_unit_scaling(row: Dict[str, object]) -> bool:
    if not _is_money_amount_row(row):
        return False
    raw_value = str(row.get("raw_value", ""))
    if _raw_has_explicit_scale(raw_value):
        return False
    abs_value = _safe_abs_value(row)
    if abs_value is None or abs_value >= 1_000_000:
        return False
    multiplier = _contextual_unit_multiplier(row)
    if multiplier <= 1.0:
        return False
    try:
        row["value"] = float(row.get("value", 0.0)) * multiplier
    except (TypeError, ValueError):
        return False
    row["unit_multiplier_repair"] = multiplier
    row["unit_multiplier_repair_source"] = "context"
    return True


def _fallback_group_multiplier(row: Dict[str, object]) -> float:
    raw_value = str(row.get("raw_value", "")).strip()
    if _raw_has_explicit_scale(raw_value):
        return 1.0
    if re.search(r"\d{1,3}(?:,\d{3})+", raw_value):
        return 1e6
    return 1.0


def _should_flag_under_scaled_amount(row: Dict[str, object], group_has_large_anchor: bool) -> bool:
    if not group_has_large_anchor:
        return False
    if not _is_money_amount_row(row):
        return False
    abs_value = _safe_abs_value(row)
    if abs_value is None or abs_value >= 1_000_000:
        return False
    if _raw_has_explicit_scale(str(row.get("raw_value", ""))):
        return False
    metric = str(row.get("metric", "")).strip().lower()
    if metric not in LARGE_MONEY_METRICS:
        return False
    row_label = str(row.get("row_label", ""))
    if not _is_strong_metric_row_label(metric, row_label):
        return False
    raw_value = str(row.get("raw_value", ""))
    if re.search(r"\d{1,3}(?:,\d{3})+", raw_value):
        return True
    currency_hint = str(row.get("currency", "")).strip() or detect_currency_hint(raw_value)
    if currency_hint and re.search(r"\d+\.\d+", raw_value):
        return True
    return False


def repair_under_scaled_money_rows(canonical_rows: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for rr in canonical_rows:
        key = (str(rr.get("file", "")), str(rr.get("statement_period_end", "")))
        grouped.setdefault(key, []).append(rr)

    kept: List[Dict[str, object]] = []
    demoted: List[Dict[str, object]] = []
    for _, rows in grouped.items():
        group_has_large_anchor = any(
            (_is_money_amount_row(r) and (_safe_abs_value(r) or 0.0) >= 100_000_000.0)
            for r in rows
        )
        for rr in rows:
            if not _is_money_amount_row(rr):
                kept.append(rr)
                continue
            _maybe_repair_contextual_unit_scaling(rr)
            abs_value = _safe_abs_value(rr)
            if group_has_large_anchor and abs_value is not None and abs_value < 1_000_000:
                fallback_mult = _fallback_group_multiplier(rr)
                if fallback_mult > 1.0:
                    try:
                        rr["value"] = float(rr.get("value", 0.0)) * fallback_mult
                        rr["unit_multiplier_repair"] = fallback_mult
                        rr["unit_multiplier_repair_source"] = "group_fallback"
                    except (TypeError, ValueError):
                        pass
            if _should_flag_under_scaled_amount(rr, group_has_large_anchor):
                demoted_row = dict(rr)
                demoted_row["context_reason"] = "under_scaled_amount_candidate"
                demoted.append(demoted_row)
                continue
            kept.append(rr)
    return kept, demoted


def _canonical_conflict_key(row: Dict[str, object]) -> Tuple[str, str, str, str, str, str]:
    return (
        _canonical_entity_key(row),
        str(row.get("metric_base", "")).strip().lower() or str(row.get("metric", "")).strip().lower(),
        str(row.get("statement_period_end", "")),
        str(row.get("statement_family", "")).strip().lower(),
        str(row.get("definition_scope", "")).strip().lower() or "reported",
        _flow_duration_group_key(row),
    )


def _is_promotable_table_context_row(row: Dict[str, object], expanded_metric_scope: bool = False) -> bool:
    metric = str(row.get("metric", "")).strip().lower()
    promotable_metrics = set(PROMOTABLE_TABLE_CONTEXT_METRICS)
    promotable_reasons = set(PROMOTABLE_TABLE_CONTEXT_REASONS)
    if expanded_metric_scope:
        promotable_metrics.update(EXPANDED_PROMOTABLE_TABLE_CONTEXT_METRICS)
        promotable_reasons.update(EXPANDED_PROMOTABLE_TABLE_CONTEXT_REASONS)
    if metric not in promotable_metrics:
        return False
    reason = str(row.get("context_reason", "")).strip().lower()
    if reason not in promotable_reasons:
        return False
    if not bool(row.get("inside_table")):
        return False
    source_mode = str(row.get("source_mode", "")).strip().lower()
    if source_mode not in TABLE_DERIVED_CANONICAL_SOURCE_MODES:
        return False
    value_type = str(row.get("value_type", "")).strip().lower()
    if value_type not in {"amount", "percent"}:
        return False
    period_end = str(row.get("statement_period_end", "")).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_end):
        return False
    try:
        parsed_period_end = date.fromisoformat(period_end)
    except ValueError:
        return False
    if not _is_month_end(parsed_period_end):
        return False
    row_label = str(row.get("row_label", ""))
    if not _is_strong_metric_row_label(metric, row_label):
        return False
    row_label_text = _normalize_space(row_label).lower()
    if metric in {"net_debt", "total_debt"} and re.match(r"^(less|add)\s*[:\-]", row_label_text):
        return False
    if metric == "net_debt" and re.search(r"\bmanagement\s+related\s+instruments?\b", row_label_text):
        return False
    if metric in {"net_debt", "total_debt"} and re.search(
        r"\b(at\s+(?:the\s+)?beginning(?:\s+of\s+(?:the\s+)?(?:period|year|quarter|half[\-\s]?year))?|"
        r"beginning(?:\s+of\s+(?:the\s+)?(?:period|year|quarter|half[\-\s]?year))?|"
        r"opening(?:\s+balance)?)\b",
        row_label_text,
        re.IGNORECASE,
    ):
        return False
    if metric in MONEY_METRICS:
        abs_value = _safe_abs_value(row)
        if abs_value is None:
            return False
        if abs_value < 1_000_000:
            return False
    if expanded_metric_scope and reason in EXPANDED_PROMOTABLE_TABLE_CONTEXT_REASONS:
        expected_families = metric_expected_families(metric)
        conf_score = canonical_confidence_score(row, expected_families)
        if conf_score < CANONICAL_CONFIDENCE_THRESHOLD:
            return False
    return True


def promote_table_context_rows(
    canonical_rows: List[Dict[str, object]],
    context_rows: List[Dict[str, object]],
    expanded_metric_scope: bool = False,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], int]:
    for rr in canonical_rows:
        rr.setdefault("canonical_tier", "strict")

    existing_keys = {_canonical_conflict_key(r) for r in canonical_rows}
    promoted_count = 0
    updated_context_rows: List[Dict[str, object]] = []

    for rr in context_rows:
        if not _is_promotable_table_context_row(rr, expanded_metric_scope=expanded_metric_scope):
            updated_context_rows.append(rr)
            continue
        candidate_key = _canonical_conflict_key(rr)
        if candidate_key in existing_keys:
            updated_context_rows.append(rr)
            continue
        promoted_row = dict(rr)
        promoted_row["canonical_tier"] = "table_promoted"
        promoted_row["canonical_promotion_reason"] = str(rr.get("context_reason", "")).strip()
        promoted_row.pop("context_reason", None)
        expected_families = metric_expected_families(str(promoted_row.get("metric", "")).strip().lower())
        promoted_row["canonical_confidence_score"] = max(
            int(promoted_row.get("canonical_confidence_score", 0) or 0),
            canonical_confidence_score(promoted_row, expected_families),
            1,
        )
        canonical_rows.append(promoted_row)
        existing_keys.add(candidate_key)
        promoted_count += 1

        context_row = dict(rr)
        context_row["promoted_to_canonical_tier"] = True
        updated_context_rows.append(context_row)

    return canonical_rows, updated_context_rows, promoted_count


def _table_identity_periods(period_columns: Sequence[object]) -> List[str]:
    periods = sorted({_normalize_space(column) for column in period_columns if _normalize_space(column)})
    return periods


def _table_identity_for_row(row: Dict[str, object]) -> Dict[str, object]:
    identity = row.get("_table_identity")
    statement_type = str(row.get("table_statement_type", "")).strip().lower() or "unknown"
    table_scope = str(row.get("table_scope", "")).strip().lower() or "unknown"
    periods: List[str] = []
    if isinstance(identity, dict):
        statement_type = str(identity.get("statement_type", "")).strip().lower() or statement_type
        table_scope = str(identity.get("table_scope", "")).strip().lower() or table_scope
        raw_periods = identity.get("periods", [])
        if isinstance(raw_periods, (list, tuple, set)):
            periods = _table_identity_periods(list(raw_periods))
    if not periods:
        periods = _table_identity_periods(
            [
                str(row.get("statement_period", "")),
                str(row.get("period", "")),
            ]
        )
    return {
        "statement_type": statement_type,
        "table_scope": table_scope,
        "periods": periods,
    }


def is_cashflow(statement_type: str) -> bool:
    return statement_type == "cash_flow"


def should_enable_hybrid(docling_rows: int, tsr_tables: int) -> bool:
    return docling_rows < 15 or tsr_tables == 0


def _has_tsr_table_identity(row: Dict[str, object]) -> bool:
    if isinstance(row.get("_table_identity"), dict):
        return True
    return str(row.get("source_mode", "")).strip().lower() == "docling_table"


def _safe_row_confidence(row: Dict[str, object]) -> float:
    try:
        return float(row.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _tsr_duplicate_row_rank(row: Dict[str, object]) -> Tuple[int, float, float, int, int, int]:
    return (
        int(row.get("canonical_confidence_score", 0) or 0),
        float(row.get("table_scope_confidence", 0.0) or 0.0),
        _safe_row_confidence(row),
        1 if _is_strong_metric_row_label(str(row.get("metric", "")), str(row.get("row_label", ""))) else 0,
        0 if _is_layout_weak(str(row.get("statement_title", "")), str(row.get("table_header_text", ""))) else 1,
        -int(row.get("line_no", 0) or 0),
    )


def apply_tsr_table_identity_preference(
    canonical_rows: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], int]:
    grouped: Dict[Tuple[str, str, str, str, str, str], List[Dict[str, object]]] = {}
    for rr in canonical_rows:
        grouped.setdefault(_canonical_conflict_key(rr), []).append(rr)

    kept: List[Dict[str, object]] = []
    demoted: List[Dict[str, object]] = []
    demoted_count = 0

    for rows in grouped.values():
        if len(rows) <= 1 or not any(_has_tsr_table_identity(row) for row in rows):
            kept.extend(rows)
            continue

        identities = {id(row): _table_identity_for_row(row) for row in rows}
        allow_partial_columns = False
        if any(is_cashflow(str(identity.get("statement_type", "")).strip().lower()) for identity in identities.values()):
            allow_partial_columns = True
        if allow_partial_columns:
            kept.extend(rows)
            continue
        consolidated_rows = [row for row in rows if identities[id(row)]["table_scope"] == "consolidated"]
        unknown_rows = [row for row in rows if identities[id(row)]["table_scope"] == "unknown"]

        winner = None
        if consolidated_rows:
            winner = max(consolidated_rows, key=_tsr_duplicate_row_rank)
        elif unknown_rows:
            winner = max(unknown_rows, key=_tsr_duplicate_row_rank)

        if winner is not None:
            kept.append(winner)
            for loser in rows:
                if loser is winner:
                    continue
                rr = dict(loser)
                rr["context_reason"] = "duplicate_metric_non_consolidated_table"
                rr["canonical_conflict_winner_line_no"] = winner.get("line_no", 0)
                rr["canonical_conflict_winner_file"] = winner.get("file", "")
                demoted.append(rr)
                demoted_count += 1
            continue

        for loser in rows:
            rr = dict(loser)
            rr["context_reason"] = "duplicate_metric_non_consolidated_table"
            demoted.append(rr)
            demoted_count += 1

    return kept, demoted, demoted_count


def _strip_tsr_reconciliation_metadata(rows: List[Dict[str, object]]) -> None:
    for row in rows:
        row.pop("_table_identity", None)


def _normalization_fingerprint(row: Dict[str, object]) -> Tuple[str, str, str, str, str, str, str]:
    return (
        str(row.get("metric", "")).strip(),
        str(row.get("metric_base", "")).strip(),
        str(row.get("metric_alias", "")).strip(),
        str(row.get("statement_period", "")).strip(),
        str(row.get("period", "")).strip(),
        str(row.get("statement_period_end", "")).strip(),
        str(row.get("period_end", "")).strip(),
    )


def is_low_quality_row(row) -> bool:
    if row is None:
        return True

    source_mode = row.get("source_mode") if isinstance(row, dict) else getattr(row, "source_mode", None)
    if str(source_mode or "").strip().lower() != "docling_table":
        return False

    value = row.get("value") if isinstance(row, dict) else getattr(row, "value", None)
    if value in {None, ""}:
        return True

    metric_name = (
        row.get("metric_name")
        if isinstance(row, dict)
        else getattr(row, "metric_name", None)
    )
    if metric_name in {None, ""}:
        metric_name = row.get("metric") if isinstance(row, dict) else getattr(row, "metric", None)
    if metric_name in {None, ""}:
        return True

    if isinstance(value, (int, float)) and abs(value) < 1e-6:
        return True

    period_end = row.get("period_end") if isinstance(row, dict) else getattr(row, "period_end", None)
    if period_end in {None, ""}:
        period_end = (
            row.get("statement_period_end")
            if isinstance(row, dict)
            else getattr(row, "statement_period_end", None)
        )
    if not period_end:
        return True

    return False


def build_routing_summary(
    context_rows: Sequence[Dict[str, object]],
    rejected_rows: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    reason_counts: Counter[str] = Counter()
    for row in context_rows:
        reason = str(row.get("context_reason", "")).strip() or "unclassified_context"
        reason_counts[reason] += 1
    for row in rejected_rows:
        reason = str(row.get("rejection_reason", "")).strip() or "unclassified_rejection"
        reason_counts[reason] += 1
    ordered_reason_counts = dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])))
    return {
        "context_rows": len(context_rows),
        "rejected_rows": len(rejected_rows),
        "rejection_reasons": ordered_reason_counts,
    }


def build_split_result(
    canonical_rows: Sequence[Dict[str, object]],
    context_rows: Sequence[Dict[str, object]],
    rejected_rows: Sequence[Dict[str, object]],
    *,
    promoted_count: int = 0,
    diagnostics: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    canonical_rows_deduped = dedupe(list(canonical_rows))
    context_rows_deduped = dedupe(list(context_rows))
    rejected_rows_deduped = dedupe(list(rejected_rows))
    result: Dict[str, object] = {
        "canonical_rows": canonical_rows_deduped,
        "context_rows": context_rows_deduped,
        "rejected_rows": rejected_rows_deduped,
        "promoted_rows_count": promoted_count,
        "routing_summary": build_routing_summary(context_rows_deduped, rejected_rows_deduped),
        "diagnostics": {"normalization_corrections": 0},
    }
    if diagnostics:
        result["diagnostics"] = {
            **dict(result.get("diagnostics", {})),
            **dict(diagnostics),
        }
    return result


def normalize_document_classifier_result(result: Optional[Dict[str, object]]) -> Dict[str, object]:
    result = dict(result or {})
    return {
        "is_financial": bool(result.get("is_financial", True)),
        "document_type": str(result.get("document_type", "")).strip(),
    }


def build_nonfinancial_docling_skip_split(
    pdf: Path,
    document_classifier: Dict[str, object],
) -> Dict[str, object]:
    classifier_result = normalize_document_classifier_result(document_classifier)
    return build_split_result(
        [],
        [
            _build_parse_failure_context_row(
                pdf,
                reason=NON_FINANCIAL_DOCUMENT_SKIP_REASON,
                message=str(classifier_result.get("document_type", "")).strip(),
            )
        ],
        [],
        diagnostics={
            "docling_row_count_before_filtering": 0,
            "reconciliation_repairs": 0,
            "tsr_tables_processed": 0,
            "document_classifier": classifier_result,
            "skip_reason": NON_FINANCIAL_DOCUMENT_SKIP_REASON,
        },
    )


def split_rows_by_scope(
    rows: List[Dict[str, object]],
    expanded_metric_scope: bool = False,
    docling_row_count_before_filtering: int = 0,
) -> Dict[str, object]:
    canonical_rows: List[Dict[str, object]] = []
    context_rows: List[Dict[str, object]] = []
    rejected_rows: List[Dict[str, object]] = []
    tsr_duplicate_rows_demoted = 0

    # Keep a per-file month-end hint from any valid balance-sheet stock row so
    # sibling total-rows that lose period labels can still be attached to the
    # correct reporting period.
    file_balance_period_hint: Dict[str, date] = {}
    for r0 in rows:
        metric0 = str(r0.get("metric", "")).strip().lower()
        if metric0 not in BALANCE_SHEET_METRICS:
            continue
        period0 = str(r0.get("statement_period_end", "")).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period0):
            continue
        try:
            period_dt0 = date.fromisoformat(period0)
        except ValueError:
            continue
        if not _is_month_end(period_dt0):
            continue
        file0 = str(r0.get("file", "")).strip()
        if not file0:
            continue
        parent_ctx0 = _normalize_space(
            f"{r0.get('statement_scope_header', '')} {r0.get('statement_title', '')} "
            f"{r0.get('table_header_text', '')} {r0.get('block_context_text', '')}"
        )
        if PARENT_SCOPE_RE.search(parent_ctx0) or PARENT_ENTITY_FINANCIAL_RE.search(parent_ctx0):
            continue
        prev_dt0 = file_balance_period_hint.get(file0)
        if prev_dt0 is None or period_dt0 > prev_dt0:
            file_balance_period_hint[file0] = period_dt0

    def _infer_balance_sheet_period_from_doc_date(file_path: str) -> Optional[date]:
        doc_date_iso = infer_doc_date_from_path(file_path)
        if not doc_date_iso:
            return None
        try:
            doc_dt = date.fromisoformat(doc_date_iso)
        except ValueError:
            return None
        candidates = [
            date(doc_dt.year, 6, 30),
            date(doc_dt.year, 12, 31),
            date(doc_dt.year - 1, 6, 30),
            date(doc_dt.year - 1, 12, 31),
        ]
        on_or_before = [d for d in candidates if d <= doc_dt]
        if not on_or_before:
            return None
        return max(on_or_before)

    def _recover_statement_family(metric_name_local: str, current_family: str, rr: Dict[str, object]) -> str:
        fam = (current_family or "").strip().lower()
        if fam not in {"cash_flow", "other", ""}:
            return fam
        ctx = _normalize_space(
            f"{rr.get('statement_title', '')} {rr.get('statement_scope_header', '')} {rr.get('table_header_text', '')}"
        )
        if not ctx:
            return fam
        if metric_name_local in INCOME_STATEMENT_METRICS and re.search(
            r"\b(income\s+statement|profit\s+or\s+loss|comprehensive\s+income)\b", ctx, re.IGNORECASE
        ):
            return "income_statement"
        if metric_name_local in BALANCE_SHEET_METRICS and re.search(
            r"\b(balance\s+sheet|financial\s+position)\b", ctx, re.IGNORECASE
        ):
            return "balance_sheet"
        return fam

    def _repair_non_month_end_period(rr: Dict[str, object]) -> None:
        metric_name_local = str(rr.get("metric", "")).strip().lower()
        if metric_name_local not in MONEY_METRICS:
            return
        period_end_raw = str(rr.get("statement_period_end", "")).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_end_raw):
            return
        try:
            parsed_period_end = date.fromisoformat(period_end_raw)
        except ValueError:
            return
        if _is_month_end(parsed_period_end):
            return
        header_text = _normalize_space(f"{rr.get('table_header_text', '')} {rr.get('statement_title', '')}")
        if not header_text:
            return
        date_labels = _extract_explicit_date_labels(header_text)
        candidates: List[Tuple[str, date]] = []
        for lbl in date_labels:
            d = _parse_date_label(lbl) or _parse_quarter_end_label(lbl)
            if d is not None and _is_month_end(d):
                candidates.append((lbl, d))
        if not candidates:
            return
        same_year = [c for c in candidates if c[1].year == parsed_period_end.year]
        chosen_label, chosen_date = same_year[0] if same_year else candidates[0]
        rr["period"] = chosen_label
        rr["statement_period"] = chosen_label
        rr["statement_period_end"] = chosen_date.isoformat()

    def _repair_month_start_period_end(rr: Dict[str, object]) -> None:
        metric_name_local = str(rr.get("metric", "")).strip().lower()
        if metric_name_local not in MONEY_METRICS:
            return
        period_end_raw = str(rr.get("statement_period_end", "")).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_end_raw):
            return
        try:
            parsed_period_end = date.fromisoformat(period_end_raw)
        except ValueError:
            return
        if parsed_period_end.day != 1:
            return
        month_last_day = calendar.monthrange(parsed_period_end.year, parsed_period_end.month)[1]
        repaired = parsed_period_end.replace(day=month_last_day)
        rr["statement_period_end"] = repaired.isoformat()

    def _is_operating_cash_flow_component_row(rr: Dict[str, object]) -> bool:
        if str(rr.get("metric", "")).strip().lower() != "operating_cash_flow":
            return False
        row_label_text_local = _normalize_space(str(rr.get("row_label", ""))).lower()
        line_text_local = _normalize_space(str(rr.get("line", ""))).lower()
        if not row_label_text_local and not line_text_local:
            return False
        hay = f"{row_label_text_local} {line_text_local}"
        if not OPERATING_CASH_FLOW_COMPONENT_RE.search(hay):
            return False
        if re.search(
            r"\bnet\s+operating\s+cash\s+flows?\s+from\s+(continuing|discontinued)\s+operations\b",
            row_label_text_local,
            re.IGNORECASE,
        ):
            return False
        if re.fullmatch(r"net\s+operating\s+cash\s+flows?", row_label_text_local, re.IGNORECASE):
            return False
        return True

    def _is_balance_sheet_line_fallback_candidate(rr: Dict[str, object]) -> bool:
        metric_name_local = str(rr.get("metric", "")).strip().lower()
        if metric_name_local not in {"total_assets", "total_liabilities", "total_equity"}:
            return False
        if str(rr.get("value_type", "")).strip().lower() != "amount":
            return False
        source_mode = str(rr.get("source_mode", "")).strip().lower()
        if source_mode not in {"", "line"}:
            return False
        row_label_local = str(rr.get("row_label", ""))
        row_label_text_local = _normalize_space(row_label_local).lower()
        if not row_label_text_local:
            return False
        if not _is_strong_metric_row_label(metric_name_local, row_label_local):
            return False
        if not re.match(r"^total\s+(assets?|liabilities?|equity|net\s+assets?)\b", row_label_text_local, re.IGNORECASE):
            return False
        ctx = _normalize_space(
            f"{rr.get('statement_scope_header', '')} {rr.get('statement_title', '')} "
            f"{rr.get('table_header_text', '')} {rr.get('block_context_text', '')} {rr.get('line', '')}"
        )
        if PARENT_SCOPE_RE.search(ctx) or PARENT_ENTITY_FINANCIAL_RE.search(ctx):
            return False
        if RECONCILIATION_CONTEXT_RE.search(ctx):
            return False
        line_local = _normalize_space(str(rr.get("line", "")) or row_label_local)
        if len(list(NUM_RE.finditer(line_local))) < 2:
            return False
        return True

    def _recover_balance_sheet_period_end(rr: Dict[str, object]) -> None:
        metric_name_local = str(rr.get("metric", "")).strip().lower()
        if metric_name_local not in BALANCE_SHEET_METRICS:
            return
        period_end_local = str(rr.get("statement_period_end", "")).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_end_local):
            try:
                parsed = date.fromisoformat(period_end_local)
            except ValueError:
                parsed = None
            if parsed is not None and _is_month_end(parsed):
                return
        file_key = str(rr.get("file", "")).strip()
        if not file_key:
            return
        hint_dt = file_balance_period_hint.get(file_key)
        if hint_dt is None:
            hint_dt = _infer_balance_sheet_period_from_doc_date(file_key)
            if hint_dt is None:
                return
        hint_label = _format_date_label(hint_dt)
        rr["statement_period_end"] = hint_dt.isoformat()
        if not str(rr.get("statement_period", "")).strip():
            rr["statement_period"] = hint_label
        if not str(rr.get("period", "")).strip():
            rr["period"] = str(rr.get("statement_period", "")).strip() or hint_label

    normalization_corrections = 0
    for r in rows:
        rr = dict(r)
        _apply_extraction_normalization(rr)
        before_normalization = _normalization_fingerprint(rr)
        canonicalize_metric_row(rr)
        normalize_period_row(rr, resolver=normalize_period_for_db)
        if _normalization_fingerprint(rr) != before_normalization:
            normalization_corrections += 1
        statement_scope = str(rr.get("statement_scope") or rr.get("statement_type", "")).strip().lower()
        inside_table = bool(rr.get("inside_table"))
        if not inside_table and _is_balance_sheet_line_fallback_candidate(rr):
            rr["inside_table"] = True
            inside_table = True
        if not inside_table:
            rr["rejection_reason"] = "not_inside_table"
            rejected_rows.append(rr)
            continue
        if bool(rr.get("pro_forma_context")):
            rr["context_reason"] = "pro_forma_context"
            context_rows.append(rr)
            continue
        table_scope = str(rr.get("table_scope", "")).strip().lower()
        if table_scope and table_scope not in {"consolidated", "unknown"}:
            rr["context_reason"] = "non_consolidated_table_scope"
            context_rows.append(rr)
            continue
        metric_name = str(rr.get("metric", "")).strip().lower()
        rr["metric_alias"] = str(rr.get("metric_alias", "")).strip() or infer_metric_alias(
            metric_name,
            row_label=str(rr.get("row_label", "")),
            line_text=str(rr.get("line", "")),
        )
        table_statement_type = str(rr.get("table_statement_type", "")).strip().lower()
        allow_period_mismatch = False
        allow_partial_columns = False
        if is_cashflow(table_statement_type):
            allow_period_mismatch = True
            allow_partial_columns = True
        classified_statement_family = table_statement_type_to_family(table_statement_type)
        statement_title = str(rr.get("statement_title", rr.get("statement_scope_header", ""))).strip().lower()
        statement_family = str(rr.get("statement_family", "")).strip().lower()
        if classified_statement_family != "other":
            statement_family = classified_statement_family
        if statement_family in {"", "other"}:
            statement_family = infer_statement_family(
                statement_title=statement_title,
                statement_scope=statement_scope,
                context_text=str(rr.get("line", "")),
            )
        rr["statement_family"] = statement_family
        title_ctx = _normalize_space(f"{rr.get('table_header_text', '')} {rr.get('statement_scope_header', '')}")
        if statement_family == "income_statement" and re.search(
            r"\b(financial\s+position|balance\s+sheet|cash\s+flows?)\b", statement_title, re.IGNORECASE
        ):
            if re.search(
                r"\b(profit\s+or\s+loss|comprehensive\s+income|income\s+statement|"
                r"loss\s+after\s+income\s+tax|profit\s+after\s+tax|"
                r"\brevenue\b|\bgross\s+profit\b|\bebitda?\b|\bnpat\b|operating\s+profit)\b",
                title_ctx,
                re.IGNORECASE,
            ):
                rr["statement_title"] = "Consolidated statement of comprehensive income"
                statement_title = rr["statement_title"].lower()
        if statement_family == "balance_sheet" and re.search(r"\bcash\s+flows?\b", statement_title, re.IGNORECASE):
            if re.search(
                r"\b(financial\s+position|balance\s+sheet|total\s+assets?|total\s+liabilities?|net\s+assets?|equity)\b",
                title_ctx,
                re.IGNORECASE,
            ):
                rr["statement_title"] = "Consolidated statement of financial position"
                statement_title = rr["statement_title"].lower()
        reconciliation_ctx = _normalize_space(
            f"{rr.get('table_header_text', '')} {rr.get('statement_title', '')} {rr.get('row_label', '')} {rr.get('line', '')}"
        )
        if RECONCILIATION_CONTEXT_RE.search(reconciliation_ctx):
            rr["context_reason"] = "reconciliation_context"
            context_rows.append(rr)
            continue
        if metric_name in INCOME_STATEMENT_METRICS and ACQUISITION_CONTRIBUTION_RE.search(reconciliation_ctx):
            rr["context_reason"] = "acquisition_contribution_context"
            context_rows.append(rr)
            continue
        parent_entity_flag_raw = rr.get("parent_entity_context")
        parent_entity_flag = bool(parent_entity_flag_raw)
        if isinstance(parent_entity_flag_raw, str):
            parent_entity_flag = parent_entity_flag_raw.strip().lower() in {"1", "true", "yes", "y"}
        parent_entity_ctx = _normalize_space(
            f"{rr.get('block_context_text', '')} {rr.get('table_header_text', '')} "
            f"{rr.get('statement_scope_header', '')} {rr.get('statement_title', '')} {rr.get('line', '')}"
        )
        if metric_name in MONEY_METRICS and (parent_entity_flag or PARENT_ENTITY_FINANCIAL_RE.search(parent_entity_ctx)):
            rr["context_reason"] = "parent_entity_context"
            context_rows.append(rr)
            continue
        expected_families = metric_expected_families(metric_name)
        if (
            expected_families
            and classified_statement_family not in {"", "other"}
            and classified_statement_family not in expected_families
            and not allow_partial_columns
        ):
            rr["context_reason"] = "statement_type_metric_conflict"
            context_rows.append(rr)
            continue
        statement_family = _recover_statement_family(metric_name, statement_family, rr)
        rr["statement_family"] = statement_family
        source_mode = str(rr.get("source_mode", "")).strip().lower()
        source_kind_local = str(rr.get("source_kind", "")).strip().lower()
        header_ctx = _normalize_space(
            f"{rr.get('table_header_text', '')} {rr.get('statement_scope_header', '')} {rr.get('statement_title', '')}"
        )
        if (
            source_mode == "docling_table"
            and source_kind_local == "other"
            and metric_name in BALANCE_SHEET_METRICS
            and statement_family == "balance_sheet"
            and not re.search(r"\bconsolidated\b", header_ctx, re.IGNORECASE)
        ):
            rr["context_reason"] = "docling_other_non_consolidated_balance_sheet"
            context_rows.append(rr)
            continue
        if (
            source_mode == "docling_table"
            and metric_name in BALANCE_SHEET_METRICS
            and statement_family == "balance_sheet"
            and re.search(r"\bcompany\b", header_ctx, re.IGNORECASE)
            and not re.search(r"\bconsolidated\b", header_ctx, re.IGNORECASE)
        ):
            rr["context_reason"] = "docling_company_column_balance_sheet"
            context_rows.append(rr)
            continue
        if (
            source_mode == "docling_table"
            and metric_name in MONEY_METRICS
            and re.search(r"\bpro\s*forma\b", header_ctx, re.IGNORECASE)
        ):
            rr["context_reason"] = "pro_forma_context"
            context_rows.append(rr)
            continue
        if (
            expected_families
            and statement_family not in {"", "other"}
            and statement_family not in expected_families
            and not allow_partial_columns
        ):
            rr["context_reason"] = "metric_statement_mismatch"
            context_rows.append(rr)
            continue
        row_label_raw = str(rr.get("row_label", ""))
        row_label_text = _normalize_space(row_label_raw).lower()
        if (
            source_mode == "docling_table"
            and metric_name == "cash_and_equivalents"
            and statement_family in {"", "other"}
            and re.search(r"\bcash\s+at\s+bank\b", row_label_text, re.IGNORECASE)
        ):
            rr["context_reason"] = "cash_non_statement_context"
            context_rows.append(rr)
            continue
        strong_balance_total_row = (
            metric_name in BALANCE_SHEET_METRICS
            and _is_strong_metric_row_label(metric_name, row_label_raw)
            and bool(re.match(r"^total\s+(assets?|liabilities?|equity|net\s+assets?)\b", row_label_text, re.IGNORECASE))
        )
        if strong_balance_total_row and statement_family in {"", "other", "cash_flow"}:
            bs_ctx = _normalize_space(
                f"{rr.get('statement_scope_header', '')} {rr.get('statement_title', '')} {rr.get('table_header_text', '')} {row_label_raw}"
            )
            if re.search(
                r"\b(financial\s+position|balance\s+sheet|total\s+assets?|total\s+liabilities?|total\s+equity|net\s+assets)\b",
                bs_ctx,
                re.IGNORECASE,
            ):
                statement_family = "balance_sheet"
                rr["statement_family"] = statement_family
        if strong_balance_total_row and statement_scope == "other" and statement_family == "balance_sheet":
            scope_ctx = _normalize_space(
                f"{rr.get('statement_scope_header', '')} {rr.get('statement_title', '')} "
                f"{rr.get('table_header_text', '')} {rr.get('block_context_text', '')}"
            )
            if not PARENT_SCOPE_RE.search(scope_ctx) and not PARENT_ENTITY_FINANCIAL_RE.search(scope_ctx):
                statement_scope = "consolidated_statement"
                rr["statement_scope"] = statement_scope
                if not str(rr.get("statement_scope_reason", "")).strip():
                    rr["statement_scope_reason"] = "balance_sheet_total_row_recovery"
        if metric_name == "eps":
            eps_ctx = _normalize_space(
                f"{row_label_raw} {rr.get('line', '')} {rr.get('table_header_text', '')} {rr.get('statement_scope_header', '')}"
            )
            eps_curr = str(rr.get("currency", "")).strip()
            if re.search(r"\bus\s*cents?\b", eps_ctx, re.IGNORECASE):
                if eps_curr in {"", "$", "US$"}:
                    rr["currency"] = "USc"
            elif re.search(r"\ba\s*cents?\b", eps_ctx, re.IGNORECASE):
                if eps_curr in {"", "$", "A$"}:
                    rr["currency"] = "Ac"
            elif re.search(r"\bcents?\b", eps_ctx, re.IGNORECASE) and eps_curr in {"", "$"}:
                rr["currency"] = "cents"
        if metric_name in MONEY_METRICS and row_label_text:
            if TABLE_ROW_CONTAMINATION_RE.search(row_label_text):
                rr["context_reason"] = "narrative_row_label"
                context_rows.append(rr)
                continue
            if re.search(r"[•▪◦]", row_label_raw):
                rr["context_reason"] = "narrative_row_label"
                context_rows.append(rr)
                continue
            if re.search(r"^(this|we|our|it)\b", row_label_text):
                rr["context_reason"] = "narrative_row_label"
                context_rows.append(rr)
                continue
            if metric_name in {"free_cash_flow", "operating_cash_flow", "net_debt"}:
                if row_label_text.endswith(" of") or "annual report" in row_label_text:
                    rr["context_reason"] = "narrative_row_label"
                    context_rows.append(rr)
                    continue
            if len(row_label_text.split()) > 10 and TABLE_NEGATIVE_CONTEXT_RE.search(row_label_text):
                rr["context_reason"] = "narrative_row_label"
                context_rows.append(rr)
                continue
        if metric_name == "current_assets" and re.search(r"\bnon[-\s]?current\s+assets?\b", row_label_text):
            rr["context_reason"] = "non_current_row_label"
            context_rows.append(rr)
            continue
        if metric_name == "current_liabilities" and re.search(r"\bnon[-\s]?current\s+liabilities?\b", row_label_text):
            rr["context_reason"] = "non_current_row_label"
            context_rows.append(rr)
            continue
        row_label_metric_hit_count = int(rr.get("row_label_metric_hit_count", 0) or 0)
        if metric_name in MONEY_METRICS and row_label_metric_hit_count > 1:
            if (
                metric_name not in OCF_COMPONENT_METRICS
                and metric_name not in {"depreciation_and_amortisation", "impairment_expense"}
                and not COMBINED_LIAB_EQUITY_ROW_RE.search(row_label_text)
            ):
                rr["context_reason"] = "ambiguous_row_label"
                context_rows.append(rr)
                continue
        if metric_name in {"net_debt", "total_debt", "free_cash_flow", "operating_cash_flow"}:
            if re.match(r"^(less|add)\s*[:\-]", row_label_text):
                rr["context_reason"] = "component_adjustment_row"
                context_rows.append(rr)
                continue
        if _is_operating_cash_flow_component_row(rr):
            rr["context_reason"] = "component_adjustment_row"
            context_rows.append(rr)
            continue
        if metric_name in {"net_debt", "total_debt"} and re.search(
            r"\b(at\s+(?:the\s+)?beginning(?:\s+of\s+(?:the\s+)?(?:period|year|quarter|half[\-\s]?year))?|"
            r"beginning(?:\s+of\s+(?:the\s+)?(?:period|year|quarter|half[\-\s]?year))?|"
            r"opening(?:\s+balance)?)\b",
            row_label_text,
            re.IGNORECASE,
        ):
            rr["context_reason"] = "opening_balance_context"
            context_rows.append(rr)
            continue
        if metric_name in {"total_liabilities", "total_equity"} and COMBINED_LIAB_EQUITY_ROW_RE.search(row_label_text):
            rr["context_reason"] = "combined_liabilities_equity_row"
            context_rows.append(rr)
            continue
        if metric_name in {"cash_and_equivalents", "cash_and_equivalents_opening", "cash_and_equivalents_closing"}:
            if CASH_RECONCILIATION_CONTEXT_RE.search(reconciliation_ctx):
                rr["context_reason"] = "cash_reconciliation_context"
                context_rows.append(rr)
                continue
            if re.search(r"\bcash\s+award\b|\bremuneration\b|\bcdp\b", row_label_text):
                rr["context_reason"] = "cash_keyword_false_positive"
                context_rows.append(rr)
                continue
            if metric_name == "cash_and_equivalents" and CASH_NON_BALANCE_ROW_RE.search(row_label_text):
                rr["context_reason"] = "cash_non_balance_context"
                context_rows.append(rr)
                continue
            if metric_name == "cash_and_equivalents" and statement_family == "cash_flow":
                if not re.search(
                    r"\b(at\s+the?\s+(?:beginning|end)\b|at\s+beginning\b|at\s+end\b|opening\b|closing\b)",
                    row_label_text,
                    re.IGNORECASE,
                ):
                    rr["context_reason"] = "cash_flow_scope_non_terminal_cash"
                    context_rows.append(rr)
                    continue
        if metric_name in {"net_income", "npat"} and re.search(
            r"\b(total\s+comprehensive\s+income|other\s+comprehensive\s+income)\b",
            row_label_text,
            re.IGNORECASE,
        ):
            rr["context_reason"] = "comprehensive_income_context"
            context_rows.append(rr)
            continue
        if metric_name in MONEY_METRICS and _is_synthetic_numeric_header(str(rr.get("table_header_text", ""))):
            rr["context_reason"] = "synthetic_table_header"
            context_rows.append(rr)
            continue
        _recover_balance_sheet_period_end(rr)
        _repair_month_start_period_end(rr)
        _repair_non_month_end_period(rr)
        statement_period_end = str(rr.get("statement_period_end", "")).strip()
        value_type = str(rr.get("value_type", "")).strip().lower()
        if value_type in {"amount", "percent"} and re.fullmatch(r"\d{4}-\d{2}-\d{2}", statement_period_end):
            try:
                parsed_statement_end = date.fromisoformat(statement_period_end)
            except ValueError:
                parsed_statement_end = None
            if (
                parsed_statement_end is not None
                and not _is_month_end(parsed_statement_end)
                and not allow_period_mismatch
            ):
                rr["context_reason"] = "non_month_end_period_unresolved"
                context_rows.append(rr)
                continue
        if not statement_period_end:
            rr["context_reason"] = "missing_statement_period_end"
            context_rows.append(rr)
            continue
        if statement_scope not in CANONICAL_STATEMENT_SCOPES:
            rr["context_reason"] = "non_canonical_scope"
            context_rows.append(rr)
            continue
        conf_score = canonical_confidence_score(rr, expected_families)
        rr["canonical_confidence_score"] = conf_score
        if conf_score < CANONICAL_CONFIDENCE_THRESHOLD:
            rr["context_reason"] = "low_canonical_confidence"
            context_rows.append(rr)
            continue
        canonical_rows.append(rr)
    canonical_rows, context_rows, promoted_count = promote_table_context_rows(
        canonical_rows,
        context_rows,
        expanded_metric_scope=expanded_metric_scope,
    )
    canonicalize_metric_rows(canonical_rows)
    canonicalize_metric_rows(context_rows)
    canonicalize_metric_rows(rejected_rows)
    normalize_period_rows(canonical_rows, resolver=normalize_period_for_db)
    normalize_period_rows(context_rows, resolver=normalize_period_for_db)
    normalize_period_rows(rejected_rows, resolver=normalize_period_for_db)
    normalize_metric_rows(canonical_rows)
    normalize_metric_rows(context_rows)
    normalize_metric_rows(rejected_rows)
    canonical_rows, scale_guard_rows = repair_under_scaled_money_rows(canonical_rows)
    context_rows.extend(scale_guard_rows)
    canonical_rows, tsr_demoted_rows, tsr_duplicate_rows_demoted = apply_tsr_table_identity_preference(canonical_rows)
    context_rows.extend(tsr_demoted_rows)
    unfiltered_context_rows = list(context_rows)
    context_rows = [r for r in context_rows if not is_low_quality_row(r)]

    # Prevent over-filtering collapse on richer Docling documents.
    if not context_rows and int(docling_row_count_before_filtering or 0) > 10:
        context_rows = unfiltered_context_rows[:3]

    def allow_partial_rows(
        docling_rows: int,
        partial_context_rows: int,
    ) -> bool:
        return docling_rows > 20 and partial_context_rows >= 0

    if not context_rows and allow_partial_rows(
        int(docling_row_count_before_filtering or 0),
        len(context_rows),
    ):
        partial_count = min(3, len(canonical_rows))
        partial_rows = canonical_rows[:partial_count]
        canonical_rows = canonical_rows[partial_count:]
        context_rows = list(partial_rows)
    canonical_rows, conflict_rows = resolve_canonical_conflicts(canonical_rows)
    context_rows.extend(conflict_rows)
    canonical_rows, bs_guard_rows = apply_balance_sheet_identity_guard(canonical_rows)
    context_rows.extend(bs_guard_rows)
    for rr in canonical_rows:
        rr.pop("table_scope", None)
        rr.pop("table_scope_confidence", None)
    _strip_tsr_reconciliation_metadata(canonical_rows)
    _strip_tsr_reconciliation_metadata(context_rows)
    _strip_tsr_reconciliation_metadata(rejected_rows)
    return build_split_result(
        canonical_rows,
        context_rows,
        rejected_rows,
        promoted_count=promoted_count,
        diagnostics={
            "normalization_corrections": normalization_corrections,
            "tsr_duplicate_rows_demoted": tsr_duplicate_rows_demoted,
        },
    )


def annotate_integrity_metadata(rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    try:
        import audit_financial_metric_quality as _integrity
    except Exception:
        _integrity = None

    integrity_index = {}
    if _integrity is not None:
        try:
            integrity_index = _integrity.build_integrity_index(rows)
        except Exception:
            integrity_index = {}

    for r in rows:
        key = (
            str(r.get("file", "")),
            str(r.get("statement_period_end", "")).strip() or str(r.get("period_end_date", "")).strip(),
        )
        meta = integrity_index.get(key, {})
        r["integrity_balance_sheet_pass"] = meta.get("balance_sheet_identity_pass", None)
        r["integrity_cash_flow_bridge_pass"] = meta.get("cash_flow_bridge_pass", None)
        r["integrity_retained_earnings_pass"] = meta.get("retained_earnings_roll_pass", None)
        r["integrity_income_integrity_pass"] = meta.get("income_integrity_pass", None)
        r["integrity_checks_evaluated"] = int(meta.get("integrity_checks_evaluated", 0) or 0)
        r["integrity_checks_passed"] = int(meta.get("integrity_checks_passed", 0) or 0)
        r["integrity_score"] = int(meta.get("integrity_score", 0) or 0)
        r["integrity_score_max"] = int(meta.get("integrity_score_max", 4) or 4)
        r["data_anomaly_level"] = str(meta.get("data_anomaly_level", "UNKNOWN"))


def summarize_statement_blocks(blocks: List[Dict[str, object]]) -> Dict[str, object]:
    by_scope: Dict[str, int] = {}
    by_family: Dict[str, int] = {}
    for b in blocks:
        scope = str(b.get("statement_scope", "other"))
        family = str(b.get("statement_family", "other"))
        by_scope[scope] = by_scope.get(scope, 0) + 1
        by_family[family] = by_family.get(family, 0) + 1
    return {"total_blocks": len(blocks), "by_scope": by_scope, "by_family": by_family}


def extract_table_metrics(
    pdf: Path,
    strict_metric_rows_only: bool = True,
    source_kind: str = "",
    review_scope: str = "canonical",
    include_blocks: bool = False,
    pdftotext_timeout_sec: Optional[float] = None,
    expanded_metric_scope: bool = False,
):
    by_page = _prepare_bbox_pages(pdf, timeout_sec=pdftotext_timeout_sec)
    if not by_page:
        empty_split = build_split_result([], [], [])
        if include_blocks:
            return [], [], empty_split
        return []
    blocks = segment_statement_blocks(pdf, source_kind=source_kind, prepared_pages=by_page)
    if expanded_metric_scope:
        rows = extract_metrics_from_blocks(
            pdf,
            blocks,
            strict_metric_rows_only=strict_metric_rows_only,
            expanded_metric_scope=True,
            prepared_pages=by_page,
        )
    else:
        rows = extract_metrics_from_blocks(
            pdf,
            blocks,
            strict_metric_rows_only=strict_metric_rows_only,
            prepared_pages=by_page,
        )
    resolved_rows, resolved_conflict_rows, resolution_diagnostics = resolve_duplicate_metrics(rows)
    split = split_rows_by_scope(
        resolved_rows,
        expanded_metric_scope=expanded_metric_scope,
    )
    split = _merge_resolution_into_split(split, resolved_conflict_rows, resolution_diagnostics)

    scope = (review_scope or "canonical").strip().lower()
    if scope == "context":
        selected = split["context_rows"]
    elif scope == "all":
        selected = resolved_rows
    else:
        selected = split["canonical_rows"]

    selected = dedupe(selected)
    if include_blocks:
        return selected, blocks, split
    return selected


_DOCLING_CONVERTER_CACHE: Dict[Tuple[bool, str, int], object] = {}
_DOCLING_INIT_ERROR_CACHE: Dict[Tuple[bool, str, int], str] = {}


def _docling_cuda_available() -> bool:
    cuda_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES")
    if cuda_visible_devices is not None:
        vis = str(cuda_visible_devices).strip().lower()
        if vis in {"", "-1", "none", "null"}:
            return False
    try:
        import torch  # type: ignore[import-not-found]

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def resolve_docling_runtime_settings(
    *,
    requested_table_mode: str,
    requested_num_threads: int,
    cuda_available: bool,
) -> Tuple[str, int]:
    """Resolve Docling runtime defaults based on accelerator availability."""
    mode = str(requested_table_mode or "").strip().lower()
    if mode not in {"auto", "accurate", "fast"}:
        mode = "auto"
    if mode == "auto":
        mode = "fast"

    num_threads = int(requested_num_threads or 0)
    if num_threads <= 0:
        num_threads = 4
    return mode, num_threads


def _get_docling_converter(
    do_ocr: bool = False,
    table_mode: str = "fast",
    num_threads: int = 0,
):
    """Lazily initialize and cache a Docling converter for this process."""
    use_ocr = False
    mode = str(table_mode or "fast").strip().lower()
    if mode not in {"accurate", "fast"}:
        mode = "fast"
    threads = int(num_threads or 0)
    cache_key = (use_ocr, mode, max(0, threads))
    cached_converter = _DOCLING_CONVERTER_CACHE.get(cache_key)
    if cached_converter is not None:
        return cached_converter, None
    cached_error = _DOCLING_INIT_ERROR_CACHE.get(cache_key)
    if cached_error is not None:
        return None, cached_error
    try:
        import docling  # type: ignore[import-not-found]  # noqa: F401
        from docling.datamodel.base_models import InputFormat  # type: ignore[import-not-found]
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode  # type: ignore[import-not-found]
        from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore[import-not-found]
    except Exception as e:
        _DOCLING_INIT_ERROR_CACHE[cache_key] = "Docling environment not available. Ensure .venv-docling-gpu exists."
        return None, _DOCLING_INIT_ERROR_CACHE[cache_key]
    try:
        pipeline_options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        if hasattr(pipeline_options, "do_layout_analysis"):
            pipeline_options.do_layout_analysis = True
        pipeline_options.table_structure_options.mode = TableFormerMode(mode)
        pipeline_options.table_structure_options.do_cell_matching = False
        if threads > 0:
            pipeline_options.accelerator_options.num_threads = threads
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
    except Exception as e:
        _DOCLING_INIT_ERROR_CACHE[cache_key] = str(e)
        return None, _DOCLING_INIT_ERROR_CACHE[cache_key]
    _DOCLING_CONVERTER_CACHE[cache_key] = converter
    return converter, None


def _map_docling_header_date_to_value_column(
    *,
    value_col_indices: List[int],
    value_col_idx: int,
    header_dates: List[str],
) -> str:
    """Map explicit header date labels to a value column index."""
    if not header_dates:
        return ""
    ncols = len(value_col_indices)
    if ncols <= 0:
        return ""
    try:
        col_order_idx = value_col_indices.index(value_col_idx)
    except ValueError:
        return ""
    ndates = len(header_dates)
    if ncols <= ndates:
        idx = col_order_idx
    else:
        idx = col_order_idx - (ncols - ndates)
    if 0 <= idx < ndates:
        return header_dates[idx]
    trailing_cols = ncols - 1 - col_order_idx
    idx2 = ndates - 1 - trailing_cols
    if 0 <= idx2 < ndates:
        return header_dates[idx2]
    return ""


def extract_table_metrics_docling(
    pdf: Path,
    strict_metric_rows_only: bool = True,
    source_kind: str = "",
    review_scope: str = "canonical",
    include_blocks: bool = False,
    converter: Optional[object] = None,
    expanded_metric_scope: bool = False,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], Dict[str, object]]:
    """
    Extract financial metrics from PDF using Docling table detection.
    Returns (all_rows, blocks, split) compatible with extract_table_metrics.
    Requires: docling. Returns empty result if docling unavailable.
    """
    if converter is None:
        converter, _ = _get_docling_converter()
    if converter is None:
        empty_split = build_split_result(
            [],
            [],
            [],
            diagnostics={
                "docling_row_count_before_filtering": 0,
                "reconciliation_repairs": 0,
                "tsr_tables_processed": 0,
            },
        )
        return [], [], empty_split

    if not pdf.exists():
        empty_split = build_split_result(
            [],
            [],
            [],
            diagnostics={
                "docling_row_count_before_filtering": 0,
                "reconciliation_repairs": 0,
                "tsr_tables_processed": 0,
            },
        )
        return [], [], empty_split

    try:
        conv_res = converter.convert(str(pdf))
    except Exception as e:
        empty_split = build_split_result(
            [],
            [_build_parse_failure_context_row(pdf, reason="docling_convert_failed", message=str(e))],
            [],
            diagnostics={
                "docling_row_count_before_filtering": 0,
                "reconciliation_repairs": 0,
                "tsr_tables_processed": 0,
            },
        )
        return [], [], empty_split

    doc = conv_res.document
    tables = list(doc.tables)
    doc_date = infer_doc_date_from_path(str(pdf))
    out: List[Dict[str, object]] = []
    blocks_for_audit: List[Dict[str, object]] = []
    doc_currency_hints: List[str] = []
    reconciliation_repairs = 0
    tsr_tables_processed = 0
    table_statement_type_counts: Counter[str] = Counter()

    for tbl_idx, table in enumerate(tables):
        try:
            df = table.export_to_dataframe(doc=doc)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df, reconciliation_meta = reconcile_table_dataframe(df)
        year_columns = list(reconciliation_meta.get("year_columns", []))
        reconciliation_repairs += int(reconciliation_meta.get("repaired_rows", 0) or 0)
        tsr_tables_processed += int(reconciliation_meta.get("tsr_tables_processed", 0) or 0)

        # Infer period from column headers (join all header cells)
        header_parts: List[str] = []
        for c in df.columns:
            header_parts.append(str(c).strip())
        header_text = " ".join(header_parts)
        period_hint, statement_period_end = infer_period_hint_from_docling_header(
            header_text,
            file_path=str(pdf),
            doc_date=doc_date,
        )

        table_text = header_text + " " + " ".join(str(v) for row in df.values for v in row)
        table_text_lower = table_text.lower()
        table_currency_hint = detect_currency_hint(table_text) or ("$" if "$" in table_text else "")
        if table_currency_hint:
            doc_currency_hints.append(table_currency_hint)
        table_classification = safe_module_call(
            classify_table_statement,
            [list(df.columns), list(df.values)],
        )
        if isinstance(table_classification, dict) and "error" in table_classification:
            table_classification = table_classification.get("result") or {}
        if not isinstance(table_classification, dict):
            table_classification = {}
        table_statement_type = str(table_classification.get("statement_type", "unknown")).strip().lower() or "unknown"
        table_statement_confidence = float(table_classification.get("confidence", 0.0) or 0.0)
        scope_info = safe_module_call(classify_table_scope, header_text, table_text)
        if isinstance(scope_info, dict) and "error" in scope_info:
            scope_info = scope_info.get("result") or {}
        if not isinstance(scope_info, dict):
            scope_info = {}
        table_scope = str(scope_info.get("table_scope", "unknown")).strip().lower() or "unknown"
        table_scope_confidence = float(scope_info.get("confidence", 0.0) or 0.0)
        table_statement_type_counts[table_statement_type] += 1
        classified_statement_family = table_statement_type_to_family(table_statement_type)
        classified_statement_title = table_statement_type_to_title(table_statement_type)
        if classified_statement_family != "other":
            statement_family = classified_statement_family
            statement_title = classified_statement_title
        elif table_statement_type == "notes":
            statement_family = "other"
            statement_title = ""
        elif re.search(r"\b(cash\s+flows?|net\s+cash|operating\s+activities)\b", table_text_lower):
            statement_family = "cash_flow"
            statement_title = "Statement of cash flows"
        elif re.search(r"\b(total\s+assets?|financial\s+position|balance\s+sheet|net\s+assets?)\b", table_text_lower):
            statement_family = "balance_sheet"
            statement_title = "Statement of financial position"
        elif re.search(r"\b(revenue|ebitda|profit\s+.*\s+tax|net\s+profit)\b", table_text_lower):
            statement_family = "income_statement"
            statement_title = "Statement of profit or loss"
        else:
            statement_family = "other"
            statement_title = ""

        blocks_for_audit.append({
            "block_id": f"docling_table_{tbl_idx + 1}",
            "title": statement_title,
            "statement_family": statement_family,
            "table_statement_type": table_statement_type,
            "table_statement_confidence": table_statement_confidence,
            "table_scope": table_scope,
            "table_scope_confidence": table_scope_confidence,
            "table_count": 1,
            "reconciliation_year_columns": len(year_columns),
            "reconciliation_repaired_rows": int(reconciliation_meta.get("repaired_rows", 0) or 0),
            "tsr_tables_processed": int(reconciliation_meta.get("tsr_tables_processed", 0) or 0),
        })

        # Find value columns: columns with date/$/year in header (exclude Note ref columns)
        value_col_indices: List[int] = []
        for cidx, col_name in enumerate(df.columns):
            col_str = str(col_name).strip()
            if not col_str or col_str.lower() in ("note", "notes", ""):
                continue
            if col_str.isdigit() or re.match(r"^\d+[A-Za-z]?$", col_str):
                continue
            if DATE_PERIOD_RE.search(col_str) or "$" in col_str or re.search(r"20\d{2}", col_str):
                value_col_indices.append(cidx)
        if not value_col_indices and year_columns:
            value_col_indices = list(year_columns)
        if not value_col_indices:
            value_col_indices = [len(df.columns) - 1] if len(df.columns) > 0 else []
        if not value_col_indices:
            continue

        legacy_last_value_col_mode = str(os.environ.get("DOCLING_LEGACY_LAST_VALUE_COLUMN", "0")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        value_columns_with_periods: List[Tuple[int, str, str]] = []
        if legacy_last_value_col_mode:
            selected_value_col = value_col_indices[-1]
            effective_period_hint = period_hint
            effective_statement_period_end = statement_period_end
            value_columns_with_periods = [
                (
                    selected_value_col,
                    effective_period_hint,
                    effective_statement_period_end,
                )
            ]
        else:
            header_dates = _extract_explicit_date_labels(header_text)
            value_col_period_map: Dict[int, Tuple[str, str]] = {}
            for value_col in value_col_indices:
                if value_col >= len(df.columns):
                    continue
                col_label = _normalize_space(str(df.columns[value_col]))
                col_period_hint, col_period_end = infer_period_hint_from_docling_header(
                    col_label,
                    file_path=str(pdf),
                    doc_date=doc_date,
                )
                if not col_period_end:
                    mapped_date_label = _map_docling_header_date_to_value_column(
                        value_col_indices=value_col_indices,
                        value_col_idx=value_col,
                        header_dates=header_dates,
                    )
                    if mapped_date_label:
                        parsed_mapped = _parse_date_label(mapped_date_label) or _parse_quarter_end_label(mapped_date_label)
                        if parsed_mapped is not None:
                            col_period_hint = mapped_date_label
                            col_period_end = parsed_mapped.isoformat()
                if not col_period_end and statement_period_end and len(value_col_indices) == 1:
                    col_period_hint = period_hint
                    col_period_end = statement_period_end
                value_col_period_map[value_col] = (col_period_hint, col_period_end)

            selected_value_col = value_col_indices[-1]
            if statement_period_end:
                matching_cols = [c for c in value_col_indices if value_col_period_map.get(c, ("", ""))[1] == statement_period_end]
                if matching_cols:
                    selected_value_col = matching_cols[0]
            if selected_value_col not in value_col_period_map:
                cols_with_period = [c for c in value_col_indices if value_col_period_map.get(c, ("", ""))[1]]
                if cols_with_period:
                    selected_value_col = max(
                        cols_with_period,
                        key=lambda c: value_col_period_map.get(c, ("", ""))[1],
                    )
            selected_period_hint, selected_period_end = value_col_period_map.get(selected_value_col, ("", ""))
            effective_period_hint = selected_period_hint or period_hint
            effective_statement_period_end = selected_period_end or statement_period_end
            cols_with_period = [
                (c, value_col_period_map.get(c, ("", ""))[0], value_col_period_map.get(c, ("", ""))[1])
                for c in value_col_indices
                if value_col_period_map.get(c, ("", ""))[1]
            ]
            if cols_with_period:
                value_columns_with_periods = cols_with_period
            else:
                value_columns_with_periods = [
                    (
                        selected_value_col,
                        effective_period_hint,
                        effective_statement_period_end,
                    )
                ]

        # Label columns: typically first 1-2 columns before value columns
        label_end = min(value_col_indices) if value_col_indices else len(df.columns)
        label_col_indices = list(range(0, label_end))

        currency_hint = table_currency_hint or detect_currency_hint(header_text) or ("$" if "$" in header_text else "")
        table_out: List[Dict[str, object]] = []

        for row_idx, row in df.iterrows():
            label_parts = [str(row.iloc[j]) for j in label_col_indices if j < len(row)]
            row_label = _normalize_space(" ".join(p for p in label_parts if p and str(p).strip() and str(p) != "nan"))
            if not row_label or len(row_label) < 2:
                continue

            metrics = list(iter_metric_hits(row_label))
            if not metrics:
                continue
            if strict_metric_rows_only and not expanded_metric_scope and any(m in {"growth_pct", "guidance"} for m in metrics):
                continue

            # Emit one datapoint per mapped period/value column.
            for value_col, row_period_hint, row_period_end in value_columns_with_periods:
                if value_col >= len(row):
                    continue
                raw_val = str(row.iloc[value_col]).strip()
                if not raw_val or raw_val.lower() in ("-", "nan", "n/a", "–", "—", ""):
                    continue
                m = NUM_TOKEN_RE.match(raw_val)
                if not m:
                    continue
                raw_num = m.group("num")
                suffix = m.group("suffix") or ""
                parsed = parse_scaled_number(raw_num, suffix)
                if parsed is None:
                    continue

                for metric in metrics:
                    if strict_metric_rows_only and not expanded_metric_scope and metric in {"growth_pct", "guidance"}:
                        continue
                    metric_name = metric
                    row_ctx = row_label.lower()
                    if metric == "cash_and_equivalents":
                        if re.search(r"\b(at\s+(?:the\s+)?end\s+of|end\s+of\s+(?:period|year)|at\s+31\s+dec|at\s+30\s+jun)\b", row_ctx):
                            metric_name = "cash_and_equivalents_closing"
                        elif re.search(r"\b(opening|beginning|at\s+1\s+july)\b", row_ctx):
                            metric_name = "cash_and_equivalents_opening"
                    explicit_currency = m.group("currency") or ""

                    rec = {
                        "file": str(pdf),
                        "source_file": str(pdf),
                        "source_kind": source_kind or "",
                        "line_no": int(row_idx) + 1,
                        "metric": metric_name,
                        "metric_base": metric,
                        "metric_variant": "",
                        "metric_alias": infer_metric_alias(metric_name, row_label=row_label, line_text=""),
                        "value_type": "amount",
                        "raw_value": raw_val,
                        "value": float(parsed),
                        "currency": explicit_currency or currency_hint,
                        "period": row_period_hint,
                        "statement_period": row_period_hint,
                        "statement_period_end": row_period_end,
                        "balance_position": "",
                        "balance_date": "",
                        "confidence": 0.0,
                        "line": row_label,
                        "row_label": row_label,
                        "row_label_metric_hit_count": len(metrics),
                        "source_mode": "docling_table",
                        "table_id": str(tbl_idx + 1),
                        "table_header_text": header_text[:200],
                        "statement_type": "consolidated_statement",
                        "statement_scope_header": statement_title,
                        "statement_scope": "consolidated_statement",
                        "statement_title": statement_title,
                        "statement_family": statement_family,
                        "table_statement_type": table_statement_type,
                        "table_statement_confidence": table_statement_confidence,
                        "table_scope": table_scope,
                        "table_scope_confidence": table_scope_confidence,
                        "statement_scope_reason": "docling_table",
                        "block_id": f"docling_table_{tbl_idx + 1}",
                        "block_context_text": "",
                        "parent_entity_context": False,
                        "inside_table": True,
                        "page_number": 0,
                        "note_number": "",
                        "pro_forma_context": False,
                    }
                    rec = apply_unit_multiplier(rec, detect_unit_multiplier(header_text) or 1.0)
                    _apply_extraction_normalization(rec)
                    table_out.append(rec)

        raw_table_identity = compute_table_identity(table_out)
        table_identity = {
            "statement_type": table_statement_type,
            "table_scope": table_scope,
            "periods": _table_identity_periods(
                [str(df.columns[idx]).strip() for idx in year_columns if 0 <= idx < len(df.columns)]
            ),
        }
        if raw_table_identity is not None:
            table_identity["statement_type"] = str(raw_table_identity[0] or table_statement_type).strip().lower() or table_statement_type
            normalized_period = normalize_period(raw_table_identity[1])
            if normalized_period:
                table_identity["periods"] = _table_identity_periods([normalized_period])
            identity_metrics = [metric for metric in raw_table_identity[2] if metric]
            if identity_metrics:
                table_identity["metrics"] = list(identity_metrics)

        for rec in table_out:
            rec["_table_identity"] = dict(table_identity)
            out.append(rec)

    dominant_currency_hint = ""
    if doc_currency_hints:
        preferred = [c for c in doc_currency_hints if c and c != "$"]
        hint_pool = preferred or doc_currency_hints
        dominant_currency_hint = Counter(hint_pool).most_common(1)[0][0]
    else:
        observed = [str(r.get("currency", "")).strip() for r in out if str(r.get("currency", "")).strip()]
        preferred = [c for c in observed if c != "$"]
        hint_pool = preferred or observed
        if hint_pool:
            dominant_currency_hint = Counter(hint_pool).most_common(1)[0][0]

    for rec in out:
        if not str(rec.get("source_file", "")).strip():
            rec["source_file"] = str(pdf)
        if str(rec.get("currency", "")).strip():
            continue
        if str(rec.get("value_type", "")).strip().lower() != "amount":
            continue
        if str(rec.get("metric", "")).strip().lower() not in MONEY_METRICS:
            continue
        if dominant_currency_hint:
            rec["currency"] = dominant_currency_hint

    resolved_out, resolved_conflict_rows, resolution_diagnostics = resolve_duplicate_metrics(out)
    split = split_rows_by_scope(
        resolved_out,
        expanded_metric_scope=expanded_metric_scope,
        docling_row_count_before_filtering=len(out),
    )
    split = _merge_resolution_into_split(split, resolved_conflict_rows, resolution_diagnostics)
    split_diagnostics = dict(split.get("diagnostics", {}))
    split_diagnostics.update(
        {
            "docling_row_count_before_filtering": len(out),
            "reconciliation_repairs": reconciliation_repairs,
            "tsr_tables_processed": tsr_tables_processed,
            "table_statement_type_counts": dict(sorted(table_statement_type_counts.items(), key=lambda item: item[0])),
        }
    )
    split["diagnostics"] = split_diagnostics
    scope = (review_scope or "canonical").strip().lower()
    if scope == "context":
        selected = split["context_rows"]
    elif scope == "all":
        selected = resolved_out
    else:
        selected = split["canonical_rows"]
    selected = dedupe(selected)
    if include_blocks:
        return selected, blocks_for_audit, split
    return selected, [], split


def _suffix_multiplier(suffix: Optional[str]) -> float:
    if not suffix:
        return 1.0
    u = suffix.lower()
    if u in ("k", "thousand"):
        return 1e3
    if u in ("m", "million", "mn", "mm"):
        return 1e6
    if u in ("b", "billion", "bn"):
        return 1e9
    if u in ("t", "trillion"):
        return 1e12
    return 1.0


def parse_scaled_number(raw: str, suffix: Optional[str]) -> Optional[float]:
    val = parse_accounting_number(raw)
    if val is None:
        return None

    mult = _suffix_multiplier(suffix)
    return float(val) * mult


def normalize_metric_value(metric_name: str, value: object) -> object:
    return normalize_financial_value(metric_name, value)


def normalize_metric_rows(rows: List[Dict[str, object]]) -> None:
    _normalize_metric_rows(rows)


def detect_period(line: str) -> str:
    labels = extract_period_labels(line)
    if labels:
        return labels[0][1]
    m = PERIOD_RE.search(line)
    return m.group(1) if m else ""


def extract_period_labels(line: str) -> List[Tuple[int, str]]:
    labels: List[Tuple[int, str]] = []
    seen = set()
    phrase_spans: List[Tuple[int, int]] = []

    for m in PERIOD_PHRASE_RE.finditer(line):
        txt = " ".join(m.group(0).split())
        key = (m.start(), txt.lower())
        if key in seen:
            continue
        seen.add(key)
        phrase_spans.append((m.start(), m.end()))
        labels.append((m.start(), txt))

    for m in DATE_PERIOD_RE.finditer(line):
        if any(s <= m.start() and m.end() <= e for s, e in phrase_spans):
            continue
        txt = " ".join(m.group(0).split())
        key = (m.start(), txt.lower())
        if key in seen:
            continue
        seen.add(key)
        labels.append((m.start(), txt))

    for m in FISCAL_PERIOD_RE.finditer(line):
        txt = " ".join(m.group(0).split())
        key = (m.start(), txt.lower())
        if key in seen:
            continue
        seen.add(key)
        labels.append((m.start(), txt))

    for m in RELATIVE_PERIOD_RE.finditer(line):
        txt = " ".join(m.group(0).split())
        key = (m.start(), txt.lower())
        if key in seen:
            continue
        seen.add(key)
        labels.append((m.start(), txt))

    # Fallback only: include bare years when no explicit date/fiscal labels are present.
    if not labels:
        for m in BARE_YEAR_RE.finditer(line):
            txt = m.group(0)
            key = (m.start(), txt)
            if key in seen:
                continue
            seen.add(key)
            labels.append((m.start(), txt))

    labels.sort(key=lambda t: t[0])
    return labels


def detect_section_heading(line: str) -> str:
    text = " ".join(line.strip().split())
    if not text:
        return ""
    if len(text) > 96:
        return ""
    if text.endswith("."):
        return ""
    if NUM_RE.search(text) or PCT_RE.search(text):
        return ""

    # Allow common heading prefixes such as "7. Liquidity risk".
    clean = re.sub(r"^[\s\d\.\)\(]+", "", text).strip()
    if not clean:
        return ""
    words = re.findall(r"[A-Za-z]+", clean)
    if not words or len(words) > 8:
        return ""
    title_like = sum(1 for w in words if w[0].isupper())
    if clean.isupper() or title_like >= max(1, len(words) - 1):
        return clean.lower()
    # Sentence-case short headings are common in annual report highlight pages.
    if clean[0].isupper() and len(words) <= 8 and "," not in clean and ";" not in clean and ":" not in clean:
        return clean.lower()
    return ""


def is_excluded_section_heading(section_heading: str) -> bool:
    if not section_heading:
        return False
    return bool(SECTION_EXCLUDED_RE.search(section_heading))


def section_mode(section_heading: str) -> str:
    if not section_heading:
        return "unknown"
    if FINANCIAL_SECTION_RE.search(section_heading):
        return "financial"
    if PRESENTATIONAL_SECTION_RE.search(section_heading):
        return "presentational"
    return "unknown"


def _normalize_space(text: str) -> str:
    return " ".join(text.split())


def extract_note_number(text: str) -> str:
    m = NOTE_SCOPE_RE.search(text or "")
    if not m:
        m = NOTE_INLINE_SCOPE_RE.search(text or "")
    return m.group(1) if m else ""


def extract_statement_scope_header(lines: List[str]) -> str:
    if not lines:
        return ""
    trailing_note_re = re.compile(r"\bshould\s+be\s+read\s+in\s+conjunction\b", re.IGNORECASE)
    candidate_statement: Optional[str] = None
    candidate_note: Optional[str] = None
    for line in reversed(lines):
        t = _normalize_space(line)
        if not t:
            continue
        if trailing_note_re.search(t) or PAGE_FOOTER_RE.search(t) or GENERIC_FOOTER_RE.search(t):
            continue
        if candidate_statement is None and (
            PARENT_SCOPE_RE.search(t)
            or CONSOLIDATED_SCOPE_RE.search(t)
            or APPENDIX_SCOPE_RE.search(t)
            or STATEMENT_LAYOUT_RE.search(t)
        ):
            candidate_statement = t
        if candidate_note is None and (
            NOTE_SCOPE_RE.search(t) or NOTE_INLINE_SCOPE_RE.search(t) or NOTES_TO_SECTION_RE.search(t)
        ):
            candidate_note = t
    if candidate_statement is not None:
        return candidate_statement
    if candidate_note is not None:
        return candidate_note
    for line in reversed(lines):
        t = _normalize_space(line)
        if PAGE_FOOTER_RE.search(t) or GENERIC_FOOTER_RE.search(t):
            continue
        if t:
            return t
    return ""


def classify_financial_statement(section_text: str) -> str:
    text = _normalize_space(section_text or "")
    if not text:
        return "other"
    has_statement_layout = bool(STATEMENT_LAYOUT_RE.search(text))
    has_parent = bool(PARENT_SCOPE_RE.search(text))
    has_consolidated = bool(CONSOLIDATED_SCOPE_RE.search(text))
    has_note = bool(NOTE_SCOPE_RE.search(text) or NOTE_INLINE_SCOPE_RE.search(text) or NOTES_TO_SECTION_RE.search(text))
    has_appendix = bool(APPENDIX_SCOPE_RE.search(text))

    if has_parent:
        return "parent_statement"
    if has_consolidated:
        return "consolidated_statement"
    if has_appendix:
        return "appendix_statement"
    if has_statement_layout and not has_note:
        return "consolidated_statement"
    if has_note:
        return "note_disclosure"
    if has_statement_layout:
        return "other"
    if section_mode(text) == "presentational":
        return "narrative"
    return "other"


def is_canonical_statement_type(statement_type: str) -> bool:
    return statement_type in CANONICAL_STATEMENT_SCOPES


def classify_statement_context(lines: List[str], idx_1based: int, active_section: str = "") -> Dict[str, str]:
    idx0 = max(0, idx_1based - 1)
    start = max(0, idx0 - 20)
    end = min(len(lines), idx0 + 12)
    # Include limited lookahead so parent/note scope labels that follow a row
    # still scope that row correctly.
    window = [ln for ln in lines[start:end] if ln and ln.strip()]
    if active_section:
        window.append(active_section)
    scope_header = extract_statement_scope_header(window[-24:])
    context_text = "\n".join(window[-24:])
    statement_type = classify_financial_statement(context_text)
    note_number = extract_note_number(context_text)
    return {
        "statement_type": statement_type,
        "statement_scope": statement_type,
        "statement_scope_header": scope_header,
        "note_number": note_number,
    }


def iter_metric_hits(line: str) -> Iterable[str]:
    hits: List[str] = []
    for metric, pat in METRIC_PATTERNS:
        if pat.search(line):
            hits.append(metric)
    hit_set = set(hits)
    if "operating_cash_flow" in hit_set and any(m in hit_set for m in OCF_COMPONENT_METRICS):
        hits = [m for m in hits if m != "operating_cash_flow"]
    for metric in hits:
        yield metric


def detect_metric_variant(metric: str, row_label: str = "", line_text: str = "", table_header_text: str = "") -> str:
    if metric not in {"revenue", "gross_profit", "ebitda", "ebit", "net_income", "npat", "eps", "dps"}:
        return ""
    text = _normalize_space(f"{row_label} {line_text} {table_header_text}").lower()
    if not text:
        return ""

    variant = ""
    if "statutory" in text:
        variant = "statutory"
    elif "underlying" in text:
        variant = "underlying"
    elif "adjusted" in text:
        variant = "adjusted"

    if re.search(r"\bbefore\s+significant\s+items\b", text):
        return f"{variant}_before_significant_items" if variant else "before_significant_items"
    if re.search(r"\b(excluding|exclude|excl\.?)\s+(?:non[-\s]?recurring|one[-\s]?off|significant\s+items?)\b", text):
        return f"{variant}_ex_significant_items" if variant else "ex_significant_items"
    return variant


def infer_metric_alias(metric: str, row_label: str = "", line_text: str = "") -> str:
    m = (metric or "").strip().lower()
    if m != "total_equity":
        return ""
    txt = _normalize_space(f"{row_label} {line_text}").lower()
    if not txt:
        return ""
    if re.search(r"\bnet\s+assets?\b", txt):
        return "net_assets"
    if re.search(r"\bshareholders'?\s+funds?\b", txt):
        return "shareholders_funds"
    if re.search(r"\bequity\s+attributable\s+to\s+owners\b", txt):
        return "equity_attributable_to_owners"
    if re.search(r"\btotal\s+equity\b", txt):
        return "total_equity"
    return ""


def _is_strong_metric_row_label(metric: str, row_label: str) -> bool:
    lbl = _normalize_space(row_label or "")
    if not lbl:
        return False
    pat = METRIC_TABLE_LABELS.get(metric)
    if pat is None:
        return False
    return bool(pat.search(lbl))


def _period_from_header_confident(period_label: str, table_header_text: str, statement_title: str = "") -> bool:
    per = _normalize_space(period_label or "")
    if not per:
        return False
    header = _normalize_space(f"{table_header_text} {statement_title}")
    header_dates = _extract_explicit_date_labels(header)
    if not header_dates:
        return False
    if _parse_date_label(per) is not None or _parse_quarter_end_label(per) is not None:
        return True
    per_l = per.lower()
    if per_l.startswith("current quarter -") or per_l.startswith("previous quarter -") or per_l.startswith("prior quarter -"):
        return bool(_extract_date_component_from_period_label(per))
    return False


def _is_layout_weak(statement_title: str, table_header_text: str) -> bool:
    title = _normalize_space(statement_title or "")
    header = _normalize_space(table_header_text or "")
    if not title and not header:
        return True
    if title and (WEAK_TITLE_RE.search(title) or PAGE_FOOTER_RE.search(title) or GENERIC_FOOTER_RE.search(title)):
        return True
    if not title and len(header.split()) < 2:
        return True
    return False


def _is_synthetic_numeric_header(table_header_text: str) -> bool:
    header = _normalize_space(table_header_text or "")
    if not header:
        return False
    tokens = header.split()
    if len(tokens) < 2:
        return False
    if not all(tok.isdigit() for tok in tokens):
        return False
    nums = [int(tok) for tok in tokens]
    # Typical DataFrame placeholder headers emitted by some Docling tables.
    return all(nums[i] - nums[i - 1] == 1 for i in range(1, len(nums))) and nums[-1] <= 10


def canonical_confidence_score(row: Dict[str, object], expected_families: set) -> int:
    metric = str(row.get("metric", "")).strip().lower()
    scope = str(row.get("statement_scope", row.get("statement_type", ""))).strip().lower()
    statement_family = str(row.get("statement_family", "")).strip().lower()
    row_label = str(row.get("row_label", ""))
    table_header_text = str(row.get("table_header_text", ""))
    statement_title = str(row.get("statement_title", row.get("statement_scope_header", "")))
    period_label = str(row.get("period", ""))

    score = 0
    if scope in CANONICAL_STATEMENT_SCOPES:
        score += 1
    if expected_families and statement_family in expected_families:
        score += 1
    if _period_from_header_confident(period_label, table_header_text, statement_title):
        score += 1
    if _is_strong_metric_row_label(metric, row_label):
        score += 1
    reconciliation_ctx = _normalize_space(f"{table_header_text} {statement_title} {row_label} {row.get('line', '')}")
    if RECONCILIATION_CONTEXT_RE.search(reconciliation_ctx):
        score -= 1
    if _is_layout_weak(statement_title, table_header_text):
        score -= 1
    return score


def _canonical_entity_key(row: Dict[str, object]) -> str:
    explicit_company = _normalize_space(str(row.get("company", ""))).upper()
    if explicit_company:
        return explicit_company
    file_path = str(row.get("file", ""))
    inferred = _normalize_space(infer_company_from_path(file_path)).upper()
    if inferred:
        return inferred
    return _normalize_space(file_path).lower()


def resolve_canonical_conflicts(canonical_rows: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str, str, str, str, str], List[Dict[str, object]]] = {}
    for rr in canonical_rows:
        key = _canonical_conflict_key(rr)
        grouped.setdefault(key, []).append(rr)

    kept: List[Dict[str, object]] = []
    demoted: List[Dict[str, object]] = []
    for _, rows in grouped.items():
        if len(rows) <= 1:
            kept.extend(rows)
            continue
        ranked = sorted(
            rows,
            key=lambda r: (
                1 if str(r.get("canonical_tier", "strict")).strip().lower() == "strict" else 0,
                int(r.get("canonical_confidence_score", 0)),
                1 if _is_strong_metric_row_label(str(r.get("metric", "")), str(r.get("row_label", ""))) else 0,
                0 if _is_layout_weak(str(r.get("statement_title", "")), str(r.get("table_header_text", ""))) else 1,
                -int(r.get("line_no", 0) or 0),
            ),
            reverse=True,
        )
        winner = ranked[0]
        uniq_vals = {
            (
                str(r.get("value", "")),
                str(r.get("raw_value", "")),
                str(r.get("currency", "")),
            )
            for r in rows
        }
        if len(uniq_vals) <= 1:
            kept.append(winner)
            for loser in ranked[1:]:
                rr = dict(loser)
                rr["context_reason"] = "canonical_duplicate_same_period"
                rr["canonical_conflict_winner_line_no"] = winner.get("line_no", 0)
                rr["canonical_conflict_winner_file"] = winner.get("file", "")
                demoted.append(rr)
            continue
        kept.append(winner)
        for loser in ranked[1:]:
            rr = dict(loser)
            rr["context_reason"] = "canonical_conflict_same_period"
            rr["canonical_conflict_winner_line_no"] = winner.get("line_no", 0)
            rr["canonical_conflict_winner_file"] = winner.get("file", "")
            demoted.append(rr)
    return kept, demoted


def apply_balance_sheet_identity_guard(
    canonical_rows: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for rr in canonical_rows:
        key = (str(rr.get("file", "")), str(rr.get("statement_period_end", "")))
        grouped.setdefault(key, []).append(rr)

    keep_ids = {id(r) for r in canonical_rows}
    demoted: List[Dict[str, object]] = []

    def _row_value(row: Dict[str, object]) -> Optional[float]:
        try:
            return float(row.get("value", ""))
        except (TypeError, ValueError):
            return None

    def _row_rank(row: Dict[str, object]) -> Tuple[int, int]:
        return (
            int(row.get("canonical_confidence_score", 0) or 0),
            1 if _is_strong_metric_row_label(str(row.get("metric", "")), str(row.get("row_label", ""))) else 0,
        )

    for _, rows in grouped.items():
        assets = [r for r in rows if str(r.get("metric", "")) == "total_assets" and _row_value(r) is not None]
        liabs = [r for r in rows if str(r.get("metric", "")) == "total_liabilities" and _row_value(r) is not None]
        equity = [r for r in rows if str(r.get("metric", "")) == "total_equity" and _row_value(r) is not None]
        if not assets or not liabs or not equity:
            continue
        asset_row = max(assets, key=_row_rank)
        asset_value = _row_value(asset_row)
        if asset_value is None:
            continue
        max_equity_abs = max(abs(_row_value(r) or 0.0) for r in equity)
        tol = max(1.0, abs(asset_value) * 0.0005)
        if max_equity_abs <= tol:
            continue
        for lr in liabs:
            lr_val = _row_value(lr)
            if lr_val is None:
                continue
            lbl = _normalize_space(str(lr.get("row_label", ""))).lower()
            if not lbl.startswith("total liabilities"):
                continue
            if abs(lr_val - asset_value) > tol:
                continue
            if id(lr) not in keep_ids:
                continue
            keep_ids.remove(id(lr))
            rr = dict(lr)
            rr["context_reason"] = "balance_sheet_identity_guard"
            demoted.append(rr)

    kept = [r for r in canonical_rows if id(r) in keep_ids]
    return kept, demoted


def choose_percent_hit(
    line: str, metric: str, pct_hits: List[re.Match[str]]
) -> Optional[re.Match[str]]:
    if not pct_hits:
        return None
    anchors = [m.start() for m in METRIC_PATTERN_MAP[metric].finditer(line)]
    if not anchors:
        return pct_hits[0]
    return min(pct_hits, key=lambda m: min(abs(m.start() - a) for a in anchors))


def rank_amount_hits(
    line: str, metric: str, num_hits: List[re.Match[str]], pct_hits: List[re.Match[str]]
) -> List[Tuple[float, re.Match[str], float, str]]:
    metric_matches = list(METRIC_PATTERN_MAP[metric].finditer(line))
    anchors = [m.start() for m in metric_matches]
    anchor_ends = [m.end() for m in metric_matches]
    cutoff_after_pct = None
    if pct_hits:
        cutoff_after_pct = pct_hits[0].start()

    has_substantive_pre_pct_amount = False
    if cutoff_after_pct is not None and metric in MONEY_METRICS:
        for nm in num_hits:
            if nm.start("num") >= cutoff_after_pct:
                continue
            raw_num = nm.group("num")
            if (
                raw_num.startswith("(")
                and not raw_num.endswith(")")
                and nm.end("num") < len(line)
                and line[nm.end("num")] == ")"
            ):
                raw_num = raw_num + ")"
            currency = nm.group("currency") or ""
            suffix = nm.group("suffix") or ""
            parsed = parse_scaled_number(raw_num, suffix)
            if parsed is None:
                continue
            if (
                not currency
                and not suffix
                and re.match(r"^\d+\.\d+$", raw_num.strip())
                and nm.start("num") <= 8
            ):
                continue
            if nm.start("num") > 0 and line[nm.start("num") - 1] in {"-", "/"}:
                prev_ch = line[nm.start("num") - 2] if nm.start("num") > 1 else ""
                if prev_ch.isalpha():
                    continue
            if nm.start("num") > 0 and line[nm.start("num") - 1].isalpha():
                continue
            if not currency and not suffix and abs(parsed).is_integer() and 1900 <= abs(parsed) <= 2100:
                continue
            if not currency and not suffix and abs(parsed) < 100:
                continue
            has_substantive_pre_pct_amount = True
            break

    ranked: List[Tuple[float, re.Match[str], float, str]] = []
    for nm in num_hits:
        raw_num = nm.group("num")
        if (
            raw_num.startswith("(")
            and not raw_num.endswith(")")
            and nm.end("num") < len(line)
            and line[nm.end("num")] == ")"
        ):
            raw_num = raw_num + ")"
        raw_value_text = nm.group(0).strip()
        if raw_num.endswith(")") and not raw_value_text.endswith(")"):
            raw_value_text = raw_value_text + ")"
        currency = nm.group("currency") or ""
        suffix = nm.group("suffix") or ""
        parsed = parse_scaled_number(raw_num, suffix)
        if parsed is None:
            continue

        # Skip row/item codes like "2.1" or "4.6" that appear at the start of table rows.
        if (
            not currency
            and not suffix
            and re.match(r"^\d+\.\d+$", raw_num.strip())
            and nm.start("num") <= 8
        ):
            continue
        # Skip identifier-like tokens in labels (e.g., AASB-16, EBITDA1).
        if nm.start("num") > 0 and line[nm.start("num") - 1] in {"-", "/"}:
            prev_ch = line[nm.start("num") - 2] if nm.start("num") > 1 else ""
            if prev_ch.isalpha():
                continue
        if nm.start("num") > 0 and line[nm.start("num") - 1].isalpha():
            continue

        # Skip ordinals like "6th", "1st" that often appear in prose dates/footnotes.
        tail = line[nm.end("num") : nm.end("num") + 2].lower()
        if tail in {"st", "nd", "rd", "th"} and not suffix:
            continue

        # Bare years are usually period markers rather than metric values.
        if not currency and not suffix and abs(parsed).is_integer() and 1900 <= abs(parsed) <= 2100:
            continue

        # Skip day-of-month values adjacent to month names (date labels, not metrics).
        if not currency and not suffix and abs(parsed).is_integer() and 1 <= abs(parsed) <= 31:
            nearby = line[max(0, nm.start("num") - 16) : min(len(line), nm.end("num") + 16)]
            if MONTH_RE.search(nearby):
                continue
            if re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", line):
                continue

        # Skip note index numbers (e.g., "Note 18") irrespective of magnitude.
        if not currency and not suffix:
            prefix = line[max(0, nm.start("num") - 16) : nm.start("num")].lower()
            if re.search(r"\bnote\s*$", prefix):
                continue

        # Skip note/footnote-like low integers (e.g., "Note 7", superscripts).
        if not currency and not suffix and abs(parsed).is_integer() and 0 <= abs(parsed) < 10:
            prefix = line[max(0, nm.start("num") - 16) : nm.start("num")].lower()
            if re.search(r"\b(note|see|refer|footnote)\s*$", prefix) or len(raw_num.strip()) <= 1:
                continue
            # Skip compact reference markers like "1, 2" after labels.
            plain = raw_num.replace(",", "").replace("(", "").replace(")", "").strip()
            if plain.lstrip("-").isdigit() and len(plain.lstrip("-")) <= 2:
                continue

        # Guidance lines often include dates/footnotes; keep numeric guidance only
        # when there is an explicit money/scale signal.
        if metric == "guidance" and not currency and not suffix:
            continue
        # Ignore percentage tokens when selecting amount metrics.
        if metric in MONEY_METRICS:
            tail_after = line[nm.end("num") :].lstrip()
            if tail_after.startswith("%"):
                continue
        # For rows with an explicit percentage change column, avoid trailing change values.
        if (
            cutoff_after_pct is not None
            and nm.start("num") > cutoff_after_pct
            and metric in MONEY_METRICS
            and has_substantive_pre_pct_amount
        ):
            continue

        score = 0.0
        if currency:
            score += 4.0
        if suffix:
            score += 3.0
        if not currency and not suffix and abs(parsed) < 10:
            score -= 2.0
        if abs(parsed) >= 1000:
            score += 2.0
        elif abs(parsed) >= 100:
            score += 1.0
        if "." in raw_num:
            score += 1.0
        if len(raw_num.replace(",", "").replace("(", "").replace(")", "")) >= 4:
            score += 0.5
        if anchors:
            dist = min(abs(nm.start("num") - a) for a in anchors)
            score -= min(dist / 200.0, 2.0)
        # Prefer amount that appears after the metric label (e.g. "NPAT $18m" not "$44m" before NPAT)
        if anchor_ends and nm.start("num") >= max(anchor_ends):
            score += 3.0
        ranked.append((score, nm, parsed, raw_value_text))

    ranked.sort(key=lambda t: t[0], reverse=True)
    return ranked


def choose_amount_hit(
    line: str, metric: str, num_hits: List[re.Match[str]], pct_hits: List[re.Match[str]]
) -> Optional[Tuple[re.Match[str], float, str]]:
    ranked = rank_amount_hits(line, metric, num_hits, pct_hits)
    if not ranked:
        return None
    best = ranked[0]
    return best[1], best[2], best[3]


def choose_amount_hits_with_periods(
    line: str, metric: str, num_hits: List[re.Match[str]], pct_hits: List[re.Match[str]]
) -> List[Tuple[re.Match[str], float, str, str]]:
    ranked = rank_amount_hits(line, metric, num_hits, pct_hits)
    if not ranked:
        return []

    # Keep highest-scored hit per numeric span, then order by appearance in line.
    by_span: Dict[Tuple[int, int], Tuple[float, re.Match[str], float, str]] = {}
    for score, nm, parsed, raw in ranked:
        span = (nm.start("num"), nm.end("num"))
        if span not in by_span:
            by_span[span] = (score, nm, parsed, raw)
    candidates = sorted(by_span.values(), key=lambda t: t[1].start("num"))
    period_labels = extract_period_labels(line)

    # If we have multiple period labels and multiple amount cells, emit one row per paired period.
    if len(period_labels) >= 2 and len(candidates) >= 2:
        assigned: List[Tuple[re.Match[str], float, str, str]] = []
        used = set()
        for p_pos, p_txt in period_labels:
            best_idx = None
            best_key = None
            for i, cand in enumerate(candidates):
                if i in used:
                    continue
                score, nm, _, _ = cand
                key = (abs(nm.start("num") - p_pos), -score)
                if best_key is None or key < best_key:
                    best_key = key
                    best_idx = i
            if best_idx is None:
                continue
            used.add(best_idx)
            _, nm, parsed, raw = candidates[best_idx]
            assigned.append((nm, parsed, raw, p_txt))
            if len(used) >= len(candidates):
                break
        if len(assigned) >= 2:
            assigned.sort(key=lambda t: t[0].start("num"))
            return assigned

    # Fallback to single best hit and assign closest explicit period label, if available.
    _, best_nm, best_parsed, best_raw = ranked[0]
    best_period = ""
    if period_labels:
        best_period = min(period_labels, key=lambda t: abs(best_nm.start("num") - t[0]))[1]
    else:
        best_period = detect_period(line)
    return [(best_nm, best_parsed, best_raw, best_period)]


def detect_unit_multiplier(line: str) -> Optional[float]:
    text = line.strip()
    if not text:
        return None
    for pat, mult in UNIT_HINT_RE:
        if pat.search(text):
            return mult
    return None


def detect_currency_hint(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    for pat, currency in CURRENCY_HINT_PATTERNS:
        if pat.search(s):
            return currency
    if "$" in s:
        return "$"
    return ""


def infer_unit_multiplier(lines: List[str], idx: int, lookback: int = 24, lookahead: int = 24) -> float:
    start = max(0, idx - lookback - 1)
    window = lines[start:idx]
    for line in reversed(window):
        m = detect_unit_multiplier(line)
        if m is not None:
            return m
    # Some Appendix 4C layouts place $A'000 headers immediately below a page break.
    # If backward scan misses, use a short forward scan as fallback.
    end = min(len(lines), idx + lookahead)
    for line in lines[idx:end]:
        m = detect_unit_multiplier(line)
        if m is not None:
            return m
    return 1.0


def apply_unit_multiplier(row: Dict[str, object], multiplier: float) -> Dict[str, object]:
    if multiplier == 1.0:
        return row
    if str(row.get("value_type", "")) != "amount":
        return row
    metric = str(row.get("metric", ""))
    if metric not in MONEY_METRICS:
        return row
    raw = str(row.get("raw_value", "")).lower()
    if any(tok in raw for tok in ("thousand", "million", "billion", "trillion", "k", "m", "b", "t")):
        # Avoid double scaling when explicit suffix already exists in value.
        if re.search(r"\b(thousand|million|billion|trillion)\b", raw) or re.search(r"\d\s*[kmbt]\b", raw):
            return row
    try:
        row["value"] = float(row.get("value", 0.0)) * multiplier
    except (ValueError, TypeError):
        return row
    return row


def is_explicit_table_metric_line(
    line: str,
    metric: str,
    num_hits: List[re.Match[str]],
    pct_hits: List[re.Match[str]],
    section_kind: str = "unknown",
) -> bool:
    label_pat = METRIC_TABLE_LABELS.get(metric)
    label_match = None
    if label_pat:
        label_match = label_pat.search(line)
        if not label_match:
            return False
        # If metric keyword appears very late, it is often commentary text, not row label.
        if label_match.start() > 60:
            return False
        prefix = line[: label_match.start()].strip()
        if prefix:
            # Allow compact row prefixes such as "4.6" or "Total", but reject narrative preambles.
            if "," in prefix:
                return False
            prefix_words = prefix.split()
            if len(prefix_words) > 3:
                return False
            if re.search(r"\b(as at|company|group|had|has|have|available|amounted|settle)\b", prefix, re.IGNORECASE):
                return False

    text = line.strip()
    words = text.split()
    has_currency_or_scale = any((m.group("currency") or m.group("suffix")) for m in num_hits)
    numeric_count = len(num_hits) + len(pct_hits)
    numeric_density = (numeric_count / max(1, len(words)))
    has_table_hint = bool(TABLE_LAYOUT_HINT_RE.search(text))
    has_table_gap = bool(TABLE_COLUMN_GAP_RE.search(line))

    # Reject header-like footnote references such as "EBITDA 1, 2".
    if num_hits and not pct_hits and not has_currency_or_scale:
        tiny_tokens = 0
        for nm in num_hits:
            raw = nm.group("num")
            parsed = parse_scaled_number(raw, nm.group("suffix") or "")
            if parsed is None:
                continue
            plain = raw.replace(",", "").replace("(", "").replace(")", "").strip()
            if plain.lstrip("-").isdigit() and abs(parsed).is_integer() and abs(parsed) < 10:
                tiny_tokens += 1
        if tiny_tokens == len(num_hits):
            return False

    # Presentation bullets usually indicate narrative commentary.
    if "•" in text or "▪" in text:
        return False

    relax_narrative_filter = (
        metric in OCF_COMPONENT_METRICS
        and section_kind == "financial"
        and label_match is not None
        and (has_table_gap or numeric_count >= 2)
    )

    # Reject narrative commentary with event verbs by default.
    if not relax_narrative_filter:
        if TABLE_NEGATIVE_CONTEXT_RE.search(text):
            return False
        if TABLE_COMPARATIVE_NARRATIVE_RE.search(text):
            return False
        if TABLE_SENTENCE_CONTEXT_RE.search(text):
            return False
    if text.endswith("."):
        return False
    if text.endswith(";"):
        return False

    has_leading_label = False
    if label_match:
        label_prefix = text[: label_match.start()].strip().lower()
        has_leading_label = label_match.start() <= 2
        if (
            not has_leading_label
            and metric in {"current_assets", "current_liabilities"}
            and label_prefix in {"total", "total:", "total-"}
        ):
            has_leading_label = True

    # In unknown/presentational sections, require stronger table layout evidence.
    if section_kind != "financial":
        if not (has_table_gap or has_leading_label or numeric_count >= 3):
            return False

    if metric.endswith("_pct") or metric in {"growth_pct", "roic_pct"}:
        return len(pct_hits) > 0 and (numeric_count >= 2 or has_table_hint)
    if metric == "guidance":
        # Keep guidance strict: table-like and not prose commentary.
        return numeric_count >= 1 and has_table_hint and numeric_density >= 0.06 and len(words) <= 22

    if section_kind == "financial" and has_table_gap and numeric_count >= 2:
        return True

    # Strict amount metrics: usually need multiple numeric cells, but allow single-cell
    # rows in financial statements when the metric label is explicit and leading.
    if numeric_count < 2:
        if (
            numeric_count == 1
            and section_kind == "financial"
            and has_leading_label
            and len(words) <= 12
        ):
            return True
        return False
    if has_currency_or_scale or has_table_hint:
        return numeric_density >= 0.06 and len(words) <= 26
    # Fallback for compact table rows with bare numbers (no $/suffix in extracted text).
    return numeric_density >= 0.18 and len(words) <= 18


def is_numeric_table_fragment(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    num_hits = [m for m in NUM_RE.finditer(text)]
    pct_hits = [m for m in PCT_RE.finditer(text)]
    words = text.split()
    numeric_count = len(num_hits) + len(pct_hits)
    density = numeric_count / max(1, len(words))
    if numeric_count < 2:
        return False
    if density < 0.2:
        return False
    if len(words) > 18:
        return False
    if TABLE_SENTENCE_CONTEXT_RE.search(text) or TABLE_NEGATIVE_CONTEXT_RE.search(text):
        return False
    return True


def is_table_label_continuation_fragment(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    if NUM_RE.search(text) or PCT_RE.search(text):
        return False
    if len(text.split()) > 10:
        return False
    if text.endswith("."):
        return False
    if TABLE_SENTENCE_CONTEXT_RE.search(text):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def should_try_continuation_stitch(line: str, next_line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    if not list(iter_metric_hits(text)):
        return False
    if text.endswith(":") or text.endswith("(") or text.count("(") > text.count(")"):
        return bool(NUM_RE.search(next_line) or PCT_RE.search(next_line))
    return False


_CASHFLOW_BRIDGE_LABEL_PATTERNS: Dict[str, re.Pattern[str]] = {
    "change_in_working_capital": re.compile(r"\bworking\s+capital\b", re.IGNORECASE),
    "income_tax_paid": re.compile(
        r"\b(net\s+)?income\s+tax(?:ation)?(?:\s+and\s+royalty[-\s]?related\s+taxation)?\s+paid\b",
        re.IGNORECASE,
    ),
    "royalties_paid": re.compile(r"\broyalty[-\s]?related\s+taxation\s+paid\b", re.IGNORECASE),
    "change_in_inventories": re.compile(
        r"\b(change(?:s)?|increase|decrease)(?:/\(?(?:decrease|increase)\)?)?\s+in\s+inventor(?:y|ies)\b",
        re.IGNORECASE,
    ),
    "change_in_receivables": re.compile(
        r"\b(change(?:s)?|increase|decrease)(?:/\(?(?:decrease|increase)\)?)?\s+in\s+receivables?\b",
        re.IGNORECASE,
    ),
    "change_in_payables": re.compile(
        r"\b(change(?:s)?|increase|decrease)(?:/\(?(?:decrease|increase)\)?)?\s+in\s+payables?\b",
        re.IGNORECASE,
    ),
}


def _extract_nearby_column_periods(lines: List[str], idx: int, lookback: int = 120) -> List[str]:
    start = max(0, idx - lookback)
    window = " ".join(lines[start:idx])
    matches = _extract_explicit_date_labels(window)
    out: List[str] = []
    for m in reversed(matches):
        norm, _ = normalize_period_for_db(m, allow_doc_date_fallback=False)
        if norm and norm not in out:
            out.append(norm)
        if len(out) >= 3:
            break
    return list(reversed(out))


def _extract_nearby_currency(lines: List[str], idx: int, lookback: int = 60) -> str:
    start = max(0, idx - lookback)
    window = " ".join(lines[start:idx]).lower()
    if "us$" in window:
        return "US$"
    if "a$" in window:
        return "A$"
    if "nz$" in window:
        return "NZ$"
    if "£" in window or "gbp" in window:
        return "GBP"
    if "€" in window or "eur" in window:
        return "EUR"
    return ""


def extract_cashflow_bridge_rows_from_lines(
    pdf: Path,
    lines: List[str],
    *,
    statement_scope_header: str = "",
) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for idx0, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        matched_metrics = [metric for metric, pat in _CASHFLOW_BRIDGE_LABEL_PATTERNS.items() if pat.search(text)]
        if not matched_metrics:
            continue

        numeric_tokens: List[str] = []
        for back in range(1, 9):
            j = idx0 - back
            if j < 0:
                break
            t = lines[j].strip()
            if not t:
                continue
            m = NUM_RE.search(t)
            if m:
                numeric_tokens.append(m.group(0))
                if len(numeric_tokens) >= 3:
                    break
                continue
            if numeric_tokens:
                break
        if len(numeric_tokens) < 3:
            for fwd in range(1, 9):
                j = idx0 + fwd
                if j >= len(lines):
                    break
                t = lines[j].strip()
                if not t:
                    continue
                m = NUM_RE.search(t)
                if m:
                    numeric_tokens.append(m.group(0))
                    if len(numeric_tokens) >= 3:
                        break
                    continue
                if numeric_tokens:
                    break
        if not numeric_tokens:
            continue

        numeric_tokens = list(reversed(numeric_tokens[:3]))
        periods = _extract_nearby_column_periods(lines, idx0)
        if not periods:
            periods = [""] * len(numeric_tokens)
        elif len(periods) < len(numeric_tokens):
            periods = ([""] * (len(numeric_tokens) - len(periods))) + periods
        else:
            periods = periods[-len(numeric_tokens):]
        currency = _extract_nearby_currency(lines, idx0)

        for metric in matched_metrics:
            metric_variant = detect_metric_variant(
                metric,
                row_label=text,
                line_text=text,
                table_header_text=statement_scope_header,
            )
            metric_alias = infer_metric_alias(metric, row_label=text, line_text=text)
            for raw_value, period in zip(numeric_tokens, periods):
                parsed = parse_scaled_number(raw_value, "")
                if parsed is None:
                    continue
                statement_period = period
                statement_period_end, _ = normalize_period_for_db(
                    statement_period,
                    allow_doc_date_fallback=False,
                )
                out.append(
                    {
                        "file": str(pdf),
                        "line_no": idx0 + 1,
                        "metric": metric,
                        "metric_base": metric,
                        "metric_variant": metric_variant,
                        "metric_alias": metric_alias,
                        "value_type": "amount",
                        "raw_value": raw_value,
                        "value": parsed,
                        "currency": currency,
                        "period": period,
                        "statement_period": statement_period,
                        "statement_period_end": statement_period_end,
                        "confidence": 0.0,
                        "line": text,
                        "row_label": text,
                        "statement_type": "cash_flow_statement",
                        "statement_scope_header": statement_scope_header or "cash flow statement",
                        "statement_scope": "cash_flow_statement",
                        "statement_title": statement_scope_header or "cash flow statement",
                        "statement_family": "cash_flow",
                        "statement_scope_reason": "cashflow_row_assembler",
                        "block_id": "",
                        "inside_table": False,
                        "page_number": 0,
                        "note_number": "",
                        "source_mode": "cashflow_row_assembler",
                        "context_reason": "cashflow_row_assembler",
                    }
                )
    return dedupe(out)


def parse_line(
    file_path: Path,
    line_no: int,
    line: str,
    strict_table_only: bool = True,
    active_section: str = "",
    statement_type: str = "",
    statement_scope_header: str = "",
    page_number: int = 0,
    note_number: str = "",
) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    if not line.strip():
        return out

    doc_date = infer_doc_date_from_path(str(file_path))
    statement_scope = (statement_type or "").strip()
    statement_family = infer_statement_family(
        statement_title=statement_scope_header,
        statement_scope=statement_scope,
        context_text=active_section or line,
    )
    if strict_table_only and statement_type and not is_canonical_statement_type(statement_type):
        return out

    sec_kind = section_mode(active_section)
    if strict_table_only:
        if is_excluded_section_heading(active_section) and not is_numeric_table_fragment(line):
            return out
        if sec_kind == "presentational" and not is_numeric_table_fragment(line):
            return out

    metrics = list(iter_metric_hits(line))
    if not metrics:
        return out

    period = detect_period(line)
    pct_hits = [m for m in PCT_RE.finditer(line)]
    num_hits = [m for m in NUM_RE.finditer(line)]

    for metric in metrics:
        metric_variant = detect_metric_variant(
            metric,
            row_label=line,
            line_text=line,
            table_header_text=statement_scope_header,
        )
        metric_alias = infer_metric_alias(metric, row_label=line, line_text=line)
        if strict_table_only and metric == "growth_pct":
            continue
        if strict_table_only and not is_explicit_table_metric_line(line, metric, num_hits, pct_hits, section_kind=sec_kind):
            continue
        captured = False
        if metric.endswith("_pct") or metric == "growth_pct":
            pm = choose_percent_hit(line, metric, pct_hits)
            if pm:
                statement_period = period
                statement_period_end, _ = normalize_period_for_db(
                    statement_period,
                    doc_date=doc_date,
                    allow_doc_date_fallback=False,
                )
                out.append(
                    {
                        "file": str(file_path),
                        "line_no": line_no,
                        "metric": metric,
                        "metric_base": metric,
                        "metric_variant": metric_variant,
                        "metric_alias": metric_alias,
                        "value_type": "percent",
                        "raw_value": pm.group(0),
                        "value": float(pm.group("pct")),
                        "currency": "",
                        "period": period,
                        "statement_period": statement_period,
                        "statement_period_end": statement_period_end,
                        "confidence": 0.0,
                        "line": line.strip(),
                        "statement_type": statement_type,
                        "statement_scope_header": statement_scope_header,
                        "statement_scope": statement_scope,
                        "statement_title": statement_scope_header,
                        "statement_family": statement_family,
                        "statement_scope_reason": "",
                        "block_id": "",
                        "inside_table": False,
                        "page_number": int(page_number or 0),
                        "note_number": note_number,
                    }
                )
                captured = True
        elif not captured:
            picked_rows = choose_amount_hits_with_periods(line, metric, num_hits, pct_hits)
            if picked_rows:
                for nm, parsed, raw_value_text, row_period in picked_rows:
                    statement_period = row_period or period
                    statement_period_end, _ = normalize_period_for_db(
                        statement_period,
                        doc_date=doc_date,
                        allow_doc_date_fallback=False,
                    )
                    out.append(
                        {
                            "file": str(file_path),
                            "line_no": line_no,
                            "metric": metric,
                            "metric_base": metric,
                            "metric_variant": metric_variant,
                            "metric_alias": metric_alias,
                            "value_type": "amount",
                            "raw_value": raw_value_text,
                            "value": parsed,
                            "currency": nm.group("currency") or "",
                            "period": statement_period,
                            "statement_period": statement_period,
                            "statement_period_end": statement_period_end,
                            "confidence": 0.0,
                            "line": line.strip(),
                            "statement_type": statement_type,
                            "statement_scope_header": statement_scope_header,
                            "statement_scope": statement_scope,
                            "statement_title": statement_scope_header,
                            "statement_family": statement_family,
                            "statement_scope_reason": "",
                            "block_id": "",
                            "inside_table": False,
                            "page_number": int(page_number or 0),
                            "note_number": note_number,
                        }
                    )
                captured = True
        if not captured and not strict_table_only:
            statement_period = period
            statement_period_end, _ = normalize_period_for_db(
                statement_period,
                doc_date=doc_date,
                allow_doc_date_fallback=False,
            )
            out.append(
                {
                    "file": str(file_path),
                    "line_no": line_no,
                    "metric": metric,
                    "metric_base": metric,
                    "metric_variant": metric_variant,
                    "metric_alias": metric_alias,
                    "value_type": "text",
                    "raw_value": "",
                    "value": "",
                    "currency": "",
                    "period": period,
                    "statement_period": statement_period,
                    "statement_period_end": statement_period_end,
                    "confidence": 0.0,
                    "line": line.strip(),
                    "statement_type": statement_type,
                    "statement_scope_header": statement_scope_header,
                    "statement_scope": statement_scope,
                    "statement_title": statement_scope_header,
                    "statement_family": statement_family,
                    "statement_scope_reason": "",
                    "block_id": "",
                    "inside_table": False,
                    "page_number": int(page_number or 0),
                    "note_number": note_number,
                }
            )
    return out


def extract_expanded_narrative_context_rows(
    pdf: Path,
    pdftotext_timeout_sec: Optional[float] = None,
) -> List[Dict[str, object]]:
    text = extract_pdf_text(pdf, timeout_sec=pdftotext_timeout_sec)
    lines = text.splitlines()
    if not lines:
        return []

    active_section = ""
    context_rows: List[Dict[str, object]] = []
    for idx, line in enumerate(lines, start=1):
        heading = detect_section_heading(line)
        if heading:
            active_section = heading
        stmt_ctx = classify_statement_context(lines, idx, active_section=active_section)
        parsed = parse_line(
            pdf,
            idx,
            line,
            strict_table_only=False,
            active_section=active_section,
            statement_type=str(stmt_ctx.get("statement_type", "")),
            statement_scope_header=str(stmt_ctx.get("statement_scope_header", "")),
            page_number=0,
            note_number=str(stmt_ctx.get("note_number", "")),
        )
        mult = infer_unit_multiplier(lines, idx)
        parsed = [apply_unit_multiplier(r, mult) for r in parsed]
        for row in parsed:
            metric = str(row.get("metric", "")).strip().lower()
            if metric not in EXPANDED_NARRATIVE_CONTEXT_METRICS:
                continue
            value_type = str(row.get("value_type", "")).strip().lower()
            if value_type not in {"amount", "percent", "text"}:
                continue
            rr = dict(row)
            rr.setdefault("row_label", str(rr.get("line", "")).strip())
            rr["source_mode"] = "expanded_narrative"
            stmt_scope = str(rr.get("statement_scope", rr.get("statement_type", ""))).strip()
            rr["statement_scope"] = stmt_scope or "other"
            rr["statement_type"] = str(rr.get("statement_type", "")).strip() or rr["statement_scope"]
            rr["statement_scope_reason"] = str(rr.get("statement_scope_reason", "")).strip() or "expanded_narrative"
            rr["inside_table"] = False
            rr["context_reason"] = "expanded_narrative_scope"
            context_rows.append(rr)

    return dedupe(context_rows)


def find_pdfs(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.pdf") if p.is_file())


def _as_string_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def load_document_quarantine_rules(path: Path) -> List[Dict[str, object]]:
    p = Path(path).expanduser()
    if not p.exists() or not p.is_file():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(payload, dict):
        raw_rules = payload.get("rules")
    elif isinstance(payload, list):
        raw_rules = payload
    else:
        raw_rules = None

    rules: List[Dict[str, object]] = []
    if not isinstance(raw_rules, list):
        return rules

    for raw in raw_rules:
        if not isinstance(raw, dict):
            continue
        ticker = str(raw.get("ticker", "")).strip().upper()
        reason = str(raw.get("reason", "")).strip() or "document_quarantine"
        terms: List[str] = []
        for key in (
            "match_substrings",
            "path_substrings",
            "title_substrings",
            "source_substrings",
            "substrings",
        ):
            terms.extend(_as_string_list(raw.get(key)))
        uniq_terms = sorted({term.lower() for term in terms if term.strip()})
        if not uniq_terms:
            continue
        rules.append(
            {
                "ticker": ticker,
                "reason": reason,
                "match_substrings": uniq_terms,
            }
        )
    return rules


def _infer_ticker_from_docs_path(file_path: Path) -> str:
    parts = list(file_path.parts)
    parts_lower = [part.lower() for part in parts]
    try:
        idx = parts_lower.index("docs")
    except ValueError:
        return ""
    if idx + 1 >= len(parts):
        return ""
    return parts[idx + 1].upper()


def match_document_quarantine_reason(file_path: Path, rules: List[Dict[str, object]]) -> str:
    if not rules:
        return ""
    path_text = str(file_path).lower()
    path_norm = path_text.replace("-", " ").replace("_", " ")
    ticker = _infer_ticker_from_docs_path(file_path)
    for rule in rules:
        rule_ticker = str(rule.get("ticker", "")).strip().upper()
        if rule_ticker and ticker != rule_ticker:
            continue
        terms = rule.get("match_substrings")
        if not isinstance(terms, list):
            continue
        for term in terms:
            needle = str(term).strip().lower()
            if not needle:
                continue
            if needle in path_text or needle.replace("-", " ").replace("_", " ") in path_norm:
                return str(rule.get("reason", "")).strip() or "document_quarantine"
    return ""


def dedupe(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen = set()
    out = []
    for r in rows:
        key = (
            r.get("file", ""),
            r.get("metric", ""),
            r.get("metric_variant", ""),
            r.get("raw_value", ""),
            r.get("period", ""),
            r.get("balance_position", ""),
            r.get("line", ""),
            r.get("statement_scope", r.get("statement_type", "")),
            r.get("block_id", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _normalize_variant_file_path(file_path: str) -> str:
    p = Path(file_path or "")
    name = p.name
    normalized_name = UUID_PDF_SUFFIX_RE.sub(".pdf", name)
    if normalized_name == name:
        return str(p)
    return str(p.with_name(normalized_name))


def _stable_value_key(value: object) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return _normalize_space(str(value))
    if f.is_integer():
        return str(int(f))
    return f"{f:.12g}"


def _variant_dedupe_key(row: Dict[str, object]) -> Tuple[str, str, str, str, str, str, str, str]:
    return (
        _normalize_variant_file_path(str(row.get("file", ""))),
        str(row.get("metric", "")),
        str(row.get("value_type", "")),
        str(row.get("statement_period_end", "")),
        str(row.get("balance_position", "")),
        _normalize_space(str(row.get("row_label", ""))).lower(),
        _stable_value_key(row.get("value", "")),
        str(row.get("currency", "")),
    )


def _variant_row_rank(row: Dict[str, object]) -> Tuple[int, int, int, int]:
    metric = str(row.get("metric", ""))
    row_label = str(row.get("row_label", ""))
    source_mode = str(row.get("source_mode", "")).strip().lower()
    return (
        int(row.get("canonical_confidence_score", 0) or 0),
        1 if _is_strong_metric_row_label(metric, row_label) else 0,
        int(SOURCE_MODE_PREFERENCE.get(source_mode, 0)),
        -int(row.get("line_no", 0) or 0),
    )


def dedupe_variant_document_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str, str, str, str, str, str, str], List[Dict[str, object]]] = {}
    for r in rows:
        grouped.setdefault(_variant_dedupe_key(r), []).append(r)

    out: List[Dict[str, object]] = []
    for group in grouped.values():
        if len(group) == 1:
            out.append(group[0])
            continue
        ranked = sorted(group, key=_variant_row_rank, reverse=True)
        out.append(ranked[0])
    return out


def _primary_variant_rank(variant: str) -> int:
    v = str(variant or "").strip().lower()
    if not v:
        return 0
    for idx, token in enumerate(PRIMARY_VARIANT_BASE_ORDER):
        if token and token in v:
            return idx + 1
    return len(PRIMARY_VARIANT_BASE_ORDER) + 1


def _flow_duration_group_key(row: Dict[str, object]) -> str:
    metric = str(row.get("metric", "")).strip().lower()
    period_scope = str(row.get("period_scope", "")).strip().lower()
    is_flow_metric = metric in INCOME_STATEMENT_METRICS or metric in CASH_FLOW_METRICS
    if period_scope != "flow" and not is_flow_metric:
        return ""
    try:
        months = int(row.get("reporting_period_months", 0) or 0)
    except (TypeError, ValueError):
        months = 0
    if months > 0:
        return f"{months}m"
    cadence = str(row.get("reporting_cadence", "")).strip().lower()
    if cadence in {"quarterly", "half_yearly", "annual"}:
        return cadence
    return ""


def _primary_row_rank(row: Dict[str, object]) -> Tuple[int, int, int, int, int, int, int]:
    metric = str(row.get("metric", "")).strip().lower()
    row_label = str(row.get("row_label", ""))
    source_mode = str(row.get("source_mode", "")).strip().lower()
    doc_profile_score = int(DOC_PROFILE_PREFERENCE.get(_document_profile_from_row(row), 0))
    return (
        1 if str(row.get("canonical_tier", "strict")).strip().lower() == "strict" else 0,
        -_primary_variant_rank(str(row.get("metric_variant", ""))),
        int(row.get("canonical_confidence_score", 0) or 0),
        doc_profile_score,
        1 if _is_strong_metric_row_label(metric, row_label) else 0,
        int(SOURCE_MODE_PREFERENCE.get(source_mode, 0)),
        -int(row.get("line_no", 0) or 0),
    )


def _infer_definition_scope(row: Dict[str, object]) -> str:
    explicit = str(row.get("definition_scope", "")).strip().lower()
    if explicit in {"reported", "underlying", "continuing", "discontinued", "attributable"}:
        return explicit
    text = _normalize_space(
        " ".join(
            [
                str(row.get("metric_variant", "")),
                str(row.get("row_label", "")),
                str(row.get("line", "")),
                str(row.get("statement_title", "")),
            ]
        )
    ).lower()
    if "discontinued" in text:
        return "discontinued"
    if "continuing" in text:
        return "continuing"
    if "attributable" in text:
        return "attributable"
    if any(tok in text for tok in ("underlying", "adjusted", "before significant items", "before-significant-items")):
        return "underlying"
    if any(tok in text for tok in ("statutory", "reported", "ifrs", "gaap")):
        return "reported"
    return "reported"


def annotate_definition_scope(rows: List[Dict[str, object]]) -> None:
    for rr in rows:
        metric_base = str(rr.get("metric_base", "")).strip().lower() or str(rr.get("metric", "")).strip().lower()
        rr["metric_base"] = metric_base
        rr["definition_scope"] = _infer_definition_scope(rr)


def _canonical_selection_key(row: Dict[str, object]) -> Tuple[str, str, str, str, str, str, str, str]:
    metric_base = str(row.get("metric_base", "")).strip().lower() or str(row.get("metric", "")).strip().lower()
    statement_family = str(row.get("statement_family", "")).strip().lower()
    definition_scope = str(row.get("definition_scope", "")).strip().lower() or "reported"
    return (
        _canonical_entity_key(row),
        metric_base,
        str(row.get("statement_period_end", "")).strip(),
        statement_family,
        definition_scope,
        str(row.get("value_type", "")).strip().lower(),
        str(row.get("balance_position", "")).strip().lower(),
        _flow_duration_group_key(row),
    )


def mark_primary_metric_rows(rows: List[Dict[str, object]]) -> None:
    grouped: Dict[Tuple[str, str, str, str, str, str, str, str], List[Dict[str, object]]] = {}
    for rr in rows:
        key = _canonical_selection_key(rr)
        grouped.setdefault(key, []).append(rr)

    for group_rows in grouped.values():
        if not group_rows:
            continue
        winner = max(group_rows, key=_primary_row_rank)
        winner_line = int(winner.get("line_no", 0) or 0)
        winner_file = str(winner.get("file", ""))
        for rr in group_rows:
            is_primary = rr is winner
            rr["primary_metric_value"] = is_primary
            if is_primary:
                rr.pop("primary_conflict_winner_line_no", None)
                rr.pop("primary_conflict_winner_file", None)
                continue
            rr["primary_conflict_winner_line_no"] = winner_line
            rr["primary_conflict_winner_file"] = winner_file


def _infer_company_profile(rows: Sequence[Dict[str, object]], coverage_profile: str) -> str:
    profile = str(coverage_profile or "auto").strip().lower()
    if profile in {"resources", "banks"}:
        return profile
    tickers = {infer_company_from_path(str(r.get("file", ""))).upper() for r in rows if str(r.get("file", "")).strip()}
    if any(t in BANK_TICKERS for t in tickers):
        return "banks"
    return "resources"


def _document_profile_from_row(row: Dict[str, object]) -> str:
    file_path = str(row.get("file", "")).lower()
    source_mode = str(row.get("source_mode", "")).strip().lower()
    if "pillar 3" in file_path or "pillar-3" in file_path or "pillar3" in file_path:
        return "pillar3"
    if "annual-report" in file_path or "annual_report" in file_path or "annual report" in file_path:
        return "audited_statement"
    if any(tok in file_path for tok in ("half-year", "half_year", "results", "financial-report", "financial_report", "preliminary-final")):
        return "official_results"
    if any(tok in file_path for tok in ("appendix", "investor-presentation", "presentation")):
        return "appendix_presentation"
    if source_mode in {"table_bbox", "docling_table"}:
        return "narrative_table"
    return "narrative_table"


def _valid_period_end(row: Dict[str, object]) -> bool:
    period_end = str(row.get("statement_period_end", "")).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period_end):
        return False
    try:
        date.fromisoformat(period_end)
    except ValueError:
        return False
    return True


def _is_backfill_candidate(
    row: Dict[str, object],
    *,
    min_confidence: float,
) -> bool:
    if not _valid_period_end(row):
        return False
    value_type = str(row.get("value_type", "")).strip().lower()
    if value_type not in {"amount", "percent"}:
        return False
    try:
        conf = float(row.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < min_confidence:
        return False
    metric = str(row.get("metric_base", "")).strip().lower() or str(row.get("metric", "")).strip().lower()
    allowed_profiles = METRIC_BACKFILL_ALLOWED_DOC_PROFILES.get(metric)
    if not allowed_profiles:
        return False
    doc_profile = _document_profile_from_row(row)
    if doc_profile not in allowed_profiles:
        return False
    return True


def _backfill_rank(row: Dict[str, object]) -> Tuple[int, int, int, float, int, int]:
    source_mode = str(row.get("source_mode", "")).strip().lower()
    try:
        conf = float(row.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    return (
        int(DOC_PROFILE_PREFERENCE.get(_document_profile_from_row(row), 0)),
        int(SOURCE_MODE_PREFERENCE.get(source_mode, 0)),
        int(row.get("canonical_confidence_score", 0) or 0),
        conf,
        1 if _is_strong_metric_row_label(str(row.get("metric", "")), str(row.get("row_label", ""))) else 0,
        -int(row.get("line_no", 0) or 0),
    )


def _cash_snapshot_derivatives(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str, str, str], Dict[str, Dict[str, object]]] = {}
    for rr in rows:
        metric = str(rr.get("metric", "")).strip().lower()
        if metric not in {"cash_and_equivalents_opening", "cash_and_equivalents_closing"}:
            continue
        key = (
            _canonical_entity_key(rr),
            str(rr.get("statement_period_end", "")).strip(),
            str(rr.get("statement_family", "")).strip().lower(),
            str(rr.get("definition_scope", "")).strip().lower() or "reported",
        )
        slot = grouped.setdefault(key, {})
        existing = slot.get(metric)
        if existing is None or _backfill_rank(rr) > _backfill_rank(existing):
            slot[metric] = rr

    out: List[Dict[str, object]] = []
    for key, source_rows in grouped.items():
        src = source_rows.get("cash_and_equivalents_closing") or source_rows.get("cash_and_equivalents_opening")
        if not src:
            continue
        derived = dict(src)
        derived["metric"] = "cash_and_equivalents"
        derived["metric_base"] = "cash_and_equivalents"
        derived["metric_variant"] = str(derived.get("metric_variant", "")).strip()
        derived["backfill_rule"] = "cash_snapshot_from_opening_closing"
        derived["backfill_source"] = str(src.get("metric", ""))
        derived["source_confidence"] = float(src.get("confidence", 0.0) or 0.0)
        out.append(derived)
    return out


def build_coverage_enhanced_rows(
    primary_rows: Sequence[Dict[str, object]],
    all_canonical_rows: Sequence[Dict[str, object]],
    context_rows: Sequence[Dict[str, object]],
    *,
    min_confidence: float = BACKFILL_MIN_CONFIDENCE,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    enhanced_rows: List[Dict[str, object]] = []
    for rr in primary_rows:
        out = dict(rr)
        out["is_backfilled"] = False
        out["backfill_source"] = ""
        out["backfill_rule"] = ""
        out["source_confidence"] = float(out.get("confidence", 0.0) or 0.0)
        enhanced_rows.append(out)

    existing_keys = {_canonical_selection_key(r) for r in enhanced_rows}
    backfill_audit: List[Dict[str, object]] = []
    candidate_pool = [dict(r) for r in all_canonical_rows if not bool(r.get("primary_metric_value"))]
    candidate_pool.extend(dict(r) for r in context_rows)
    candidate_pool.extend(_cash_snapshot_derivatives(list(all_canonical_rows) + list(context_rows)))

    grouped_candidates: Dict[Tuple[str, str, str, str, str, str, str, str], List[Dict[str, object]]] = {}
    for cand in candidate_pool:
        annotate_definition_scope([cand])
        if not _is_backfill_candidate(cand, min_confidence=min_confidence):
            continue
        key = _canonical_selection_key(cand)
        if key in existing_keys:
            continue
        grouped_candidates.setdefault(key, []).append(cand)

    for key, candidates in grouped_candidates.items():
        ranked = sorted(candidates, key=_backfill_rank, reverse=True)
        winner = dict(ranked[0])
        winner["primary_metric_value"] = True
        winner["is_backfilled"] = True
        winner["backfill_source"] = f"{_document_profile_from_row(winner)}:{str(winner.get('source_mode', '')).strip().lower()}"
        winner["backfill_rule"] = str(winner.get("backfill_rule", "")).strip() or "deterministic_missing_primary_backfill"
        winner["source_confidence"] = float(winner.get("confidence", 0.0) or 0.0)
        enhanced_rows.append(winner)
        existing_keys.add(key)

        for loser in ranked[1:]:
            backfill_audit.append(
                {
                    "selection_key": {
                        "entity": key[0],
                        "metric_base": key[1],
                        "statement_period_end": key[2],
                        "statement_family": key[3],
                        "definition_scope": key[4],
                    },
                    "winner_file": str(winner.get("file", "")),
                    "winner_line_no": int(winner.get("line_no", 0) or 0),
                    "loser_file": str(loser.get("file", "")),
                    "loser_line_no": int(loser.get("line_no", 0) or 0),
                    "loser_metric": str(loser.get("metric", "")),
                    "loser_source_mode": str(loser.get("source_mode", "")),
                    "loser_confidence": float(loser.get("confidence", 0.0) or 0.0),
                }
            )

    return dedupe(enhanced_rows), backfill_audit


def _confidence_band(score: object) -> str:
    try:
        v = float(score or 0.0)
    except (TypeError, ValueError):
        v = 0.0
    if v >= 0.95:
        return "very_high"
    if v >= 0.85:
        return "high"
    if v >= 0.70:
        return "medium"
    return "low"


def _datapoint_id(row: Dict[str, object], scope: str) -> str:
    key = "|".join(
        [
            scope,
            str(row.get("file", "")),
            str(row.get("line_no", "")),
            str(row.get("metric_base", "")),
            str(row.get("metric", "")),
            str(row.get("statement_period_end", "")),
            str(row.get("balance_position", "")),
            str(row.get("value_type", "")),
            str(row.get("raw_value", "")),
            str(row.get("value", "")),
            str(row.get("currency", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def build_all_datapoints_rows(
    primary_rows: Sequence[Dict[str, object]],
    all_canonical_rows: Sequence[Dict[str, object]],
    context_rows: Sequence[Dict[str, object]],
    rejected_rows: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    primary_ids = {id(r) for r in primary_rows}
    out: List[Dict[str, object]] = []

    def _append(rows: Sequence[Dict[str, object]], scope: str) -> None:
        for rr in rows:
            rec = dict(rr)
            score = float(rec.get("confidence", 0.0) or 0.0)
            rec["datapoint_id"] = _datapoint_id(rec, scope)
            rec["datapoint_scope"] = scope
            rec["datapoint_status"] = (
                "selected"
                if scope == "canonical_primary"
                else ("available" if scope == "canonical_non_primary" else ("demoted" if scope == "context" else "rejected"))
            )
            rec["confidence_score"] = score
            rec["confidence_band"] = _confidence_band(score)
            rec["is_primary_metric_value"] = bool(rec.get("primary_metric_value")) or (scope == "canonical_primary")
            rec["is_backfilled"] = bool(rec.get("is_backfilled", False))
            rec["label_reason"] = str(
                rec.get("context_reason", "") or rec.get("rejection_reason", "") or rec.get("statement_scope_reason", "")
            ).strip()
            out.append(rec)

    _append(primary_rows, "canonical_primary")
    _append([r for r in all_canonical_rows if id(r) not in primary_ids], "canonical_non_primary")
    _append(context_rows, "context")
    _append(rejected_rows, "rejected")
    return dedupe(out)


def write_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "file",
        "line_no",
        "metric",
        "metric_base",
        "metric_variant",
        "metric_alias",
        "value_type",
        "raw_value",
        "value",
        "currency",
        "period",
        "statement_period",
        "statement_period_end",
        "definition_scope",
        "period_label_effective",
        "period_type",
        "fiscal_tag",
        "period_scope",
        "period_length_months",
        "period_inference_source",
        "reporting_cadence",
        "reporting_period_months",
        "reporting_cadence_inference_source",
        "balance_position",
        "balance_date",
        "integrity_score",
        "integrity_checks_evaluated",
        "integrity_checks_passed",
        "integrity_score_max",
        "integrity_balance_sheet_pass",
        "integrity_cash_flow_bridge_pass",
        "integrity_retained_earnings_pass",
        "integrity_income_integrity_pass",
        "data_anomaly_level",
        "confidence",
        "line",
        "row_label",
        "inside_table",
        "statement_scope",
        "statement_title",
        "statement_family",
        "table_statement_type",
        "table_statement_confidence",
        "statement_scope_reason",
        "block_id",
        "table_id",
        "table_page",
        "page_number",
        "note_number",
        "source_mode",
        "canonical_confidence_score",
        "canonical_tier",
        "canonical_promotion_reason",
        "promoted_to_canonical_tier",
        "primary_metric_value",
        "primary_conflict_winner_line_no",
        "primary_conflict_winner_file",
        "is_backfilled",
        "backfill_source",
        "backfill_rule",
        "source_confidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_json(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def _document_routing_summary(split: Dict[str, object]) -> Dict[str, object]:
    context_rows = list(split.get("context_rows", []) or [])
    rejected_rows = list(split.get("rejected_rows", []) or [])
    return build_routing_summary(context_rows, rejected_rows)


def _document_split_diagnostics(split: Dict[str, object]) -> Dict[str, object]:
    diagnostics = split.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        return {}
    return dict(diagnostics)


def _merge_resolution_into_split(
    split: Dict[str, object],
    resolved_context_rows: Sequence[Dict[str, object]],
    resolution_diagnostics: Dict[str, object],
) -> Dict[str, object]:
    merged_context_rows = list(split.get("context_rows", []) or [])
    if resolved_context_rows:
        merged_context_rows.extend(list(resolved_context_rows))
        split["context_rows"] = dedupe(merged_context_rows)
    diagnostics = dict(split.get("diagnostics", {}) or {})
    diagnostics.update(dict(resolution_diagnostics or {}))
    split["diagnostics"] = diagnostics
    split["routing_summary"] = build_routing_summary(
        list(split.get("context_rows", []) or []),
        list(split.get("rejected_rows", []) or []),
    )
    return split


def build_period_metadata_summary(rows: List[Dict[str, object]]) -> Tuple[Dict[str, int], int, Dict[str, int], int]:
    period_type_counts: Counter[str] = Counter()
    reporting_cadence_counts: Counter[str] = Counter()
    unresolved_flow = 0
    unresolved_stock_cadence = 0
    for rr in rows:
        period_type = str(rr.get("period_type", "unknown")).strip() or "unknown"
        period_scope = str(rr.get("period_scope", "")).strip()
        reporting_cadence = str(rr.get("reporting_cadence", "unknown")).strip() or "unknown"
        period_type_counts[period_type] += 1
        reporting_cadence_counts[reporting_cadence] += 1
        if period_scope == "flow" and period_type in {"", "unknown", "other"}:
            unresolved_flow += 1
        if period_scope == "stock" and reporting_cadence in {"", "unknown", "other"}:
            unresolved_stock_cadence += 1
    return (
        dict(sorted(period_type_counts.items(), key=lambda kv: kv[0])),
        unresolved_flow,
        dict(sorted(reporting_cadence_counts.items(), key=lambda kv: kv[0])),
        unresolved_stock_cadence,
    )


def score_confidence(row: Dict[str, object]) -> float:
    value_type = str(row.get("value_type", ""))
    metric = str(row.get("metric", ""))
    raw_value = str(row.get("raw_value", ""))
    currency = str(row.get("currency", ""))
    period = str(row.get("period", ""))
    statement_scope = str(row.get("statement_scope", row.get("statement_type", ""))).strip().lower()
    inside_table = bool(row.get("inside_table", False))

    if statement_scope and statement_scope not in CANONICAL_STATEMENT_SCOPES:
        return 0.0
    if not inside_table and statement_scope:
        return 0.0

    if value_type == "percent":
        score = 0.85
    elif value_type == "amount":
        score = 0.7
        if currency:
            score += 0.15
        if any(x in raw_value.lower() for x in ["m", "b", "k", "t", "million", "billion", "thousand", "trillion"]):
            score += 0.1
        if re.search(r"\d\.\d", raw_value):
            score += 0.05
    else:
        score = 0.35

    if metric == "guidance" and value_type == "text":
        score += 0.1
    if period:
        score += 0.05

    return round(max(0.0, min(1.0, score)), 2)


def validate_canonical_row(row: Dict[str, object]) -> List[str]:
    """Validate a canonical metric row; returns list of error messages (empty if valid)."""
    errors: List[str] = []
    if not str(row.get("file", "")).strip():
        errors.append("missing file")
    if not str(row.get("metric", "")).strip():
        errors.append("missing metric")
    vt = str(row.get("value_type", ""))
    if vt not in ("amount", "percent", "text"):
        errors.append(f"invalid value_type: {vt!r}")
    try:
        c = float(row.get("confidence", 0))
        if not (0 <= c <= 1):
            errors.append(f"confidence out of range: {c}")
    except (TypeError, ValueError):
        errors.append("invalid confidence")
    if vt in ("amount", "percent"):
        try:
            v = float(row.get("value", 0))
            if not abs(v) < 1e18:
                errors.append("value overflow")
        except (TypeError, ValueError):
            errors.append("invalid value for amount/percent")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract financial metrics from PDFs")
    input_group = ap.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf-dir", help="Folder containing PDF files")
    input_group.add_argument("--pdf", help="Single PDF file to process")
    ap.add_argument("--out-csv", default="reports/financial_metrics.csv", help="Canonical CSV output path")
    ap.add_argument(
        "--out-json",
        default="reports/financial_metrics.json",
        help="Primary canonical JSON output path (one default row per metric/period).",
    )
    ap.add_argument(
        "--out-all-variants-json",
        default="reports/financial_metrics_all_variants.json",
        help="All canonical rows JSON output path (includes non-primary variants for audit/debug).",
    )
    ap.add_argument(
        "--out-primary-csv",
        default="reports/financial_metrics_primary.csv",
        help="Primary canonical CSV output path (one default row per metric/period).",
    )
    ap.add_argument(
        "--out-primary-json",
        default="reports/financial_metrics_primary.json",
        help="Primary canonical JSON output path (one default row per metric/period).",
    )
    ap.add_argument(
        "--out-all-datapoints-json",
        default="reports/financial_metrics_all_datapoints.json",
        help="All extracted datapoints JSON (primary + non-primary + context + rejected) with confidence/status labels.",
    )
    ap.add_argument(
        "--out-coverage-enhanced-json",
        default="reports/financial_metrics_coverage_enhanced.json",
        help="Coverage-enhanced JSON output path (canonical + deterministic backfills).",
    )
    ap.add_argument(
        "--out-coverage-backfill-audit-json",
        default="reports/financial_metrics_coverage_backfill_audit.json",
        help="Backfill audit trail JSON path (winner/loser candidate records).",
    )
    ap.add_argument(
        "--out-context-csv",
        default="reports/financial_metrics_context.csv",
        help="Context CSV output path",
    )
    ap.add_argument(
        "--out-context-json",
        default="reports/financial_metrics_context.json",
        help="Context JSON output path",
    )
    ap.add_argument(
        "--out-rejected-json",
        default="reports/financial_metrics_rejected.json",
        help="Rejected JSON output path",
    )
    ap.add_argument(
        "--out-blocks-json",
        default="reports/financial_statement_blocks.json",
        help="Statement block audit JSON output path",
    )
    ap.add_argument(
        "--out-document-diagnostics-json",
        default="",
        help="Optional per-document observability JSON output path.",
    )
    ap.add_argument(
        "--out-sqlite",
        default="reports/financial_metrics.sqlite",
        help="Canonical SQLite output path for time-ordered metric rows",
    )
    ap.add_argument(
        "--no-sqlite",
        action="store_true",
        help="Disable SQLite write",
    )
    ap.add_argument(
        "--allow-narrative",
        action="store_true",
        help="Also extract from narrative sentences (less strict). Default is strict table-only extraction.",
    )
    ap.add_argument(
        "--expanded-metric-scope",
        action="store_true",
        help=(
            "Strict mode only: include additional table metrics and allow non_canonical_scope table promotions "
            "when confidence checks pass. Canonical promotions keep existing table_promoted labels."
        ),
    )
    ap.add_argument(
        "--out-high-csv",
        default="reports/financial_metrics_high_confidence.csv",
        help="CSV output path for rows with confidence >= --min-confidence",
    )
    ap.add_argument(
        "--out-high-json",
        default="reports/financial_metrics_high_confidence.json",
        help="JSON output path for rows with confidence >= --min-confidence",
    )
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Minimum confidence threshold for high-confidence outputs",
    )
    ap.add_argument(
        "--disable-table-first",
        action="store_true",
        help=(
            "Deprecated in strict mode. Canonical extraction is always table-first and no line fallback is used."
        ),
    )
    ap.add_argument(
        "--pdftotext-timeout-sec",
        type=float,
        default=180.0,
        help="Per-file timeout for pdftotext calls in seconds (<=0 disables timeout).",
    )
    ap.add_argument(
        "--extractor",
        choices=["pdftotext", "docling"],
        default="pdftotext",
        help="Table extraction backend: pdftotext (default) or docling. Docling uses ML for layout/table detection.",
    )
    ap.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU fallback for Docling (default is GPU when available).",
    )
    ap.add_argument(
        "--docling-ocr",
        action="store_true",
        help="Enable OCR in Docling. Default is disabled for faster parsing on text-layer PDFs.",
    )
    ap.add_argument(
        "--docling-table-mode",
        choices=["auto", "accurate", "fast"],
        default="auto",
        help=(
            "Docling table structure mode. Default auto: accurate on CUDA, fast on CPU fallback "
            "for better throughput."
        ),
    )
    ap.add_argument(
        "--docling-num-threads",
        type=int,
        default=0,
        help=(
            "Docling accelerator thread count override (<=0 uses runtime default; "
            "auto selects 2 on CPU fallback)."
        ),
    )
    ap.add_argument(
        "--force-extract",
        action="store_true",
        help="Bypass the first-page document classifier and always run the selected extractor.",
    )
    ap.add_argument(
        "--quarantine-rules-json",
        default=str(DEFAULT_DOCUMENT_QUARANTINE_RULES_PATH),
        help=(
            "Path to document quarantine rules JSON. "
            "Default: financial-engine_v2/config/document_quarantine_rules.json"
        ),
    )
    ap.add_argument(
        "--no-quarantine-rules",
        action="store_true",
        help="Disable document quarantine filtering.",
    )
    ap.add_argument(
        "--dedupe-variant-docs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Collapse duplicate rows across UUID-suffixed copies of the same PDF stem. "
            "Default: enabled."
        ),
    )
    ap.add_argument(
        "--enforce-financial-gates",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail run when hard ingestion gates fail on primary output rows. Default: enabled.",
    )
    ap.add_argument(
        "--financial-gates-report",
        default="",
        help=(
            "Optional path for financial gate report JSON. "
            "Default: <out-json stem>.gates.json"
        ),
    )
    ap.add_argument(
        "--enforce-coverage-gates",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail run when coverage gate checks fail. Default: disabled.",
    )
    ap.add_argument(
        "--coverage-required-metrics",
        default="",
        help="Optional comma-separated required metrics override for coverage gate checks.",
    )
    ap.add_argument(
        "--coverage-profile",
        default="auto",
        choices=["auto", "resources", "banks"],
        help="Coverage profile for required metric expectations. Default: auto.",
    )
    ap.add_argument(
        "--coverage-period-types",
        default="annual,half_yearly",
        help="Comma-separated period types for coverage gate checks.",
    )
    ap.add_argument(
        "--coverage-recent-periods",
        type=int,
        default=2,
        help="How many latest periods per company+period_type to enforce in coverage gates.",
    )
    ap.add_argument(
        "--coverage-gates-report",
        default="",
        help="Optional path for canonical coverage gate report JSON. Default: <out-json stem>.coverage_gates.json",
    )
    ap.add_argument(
        "--coverage-enhanced-gates-report",
        default="",
        help=(
            "Optional path for coverage-enhanced gate report JSON. "
            "Default: <out-coverage-enhanced-json stem>.coverage_gates.json"
        ),
    )
    args = ap.parse_args()

    strict = not args.allow_narrative
    use_docling = args.extractor == "docling"
    line_parse_enabled = not (
        use_docling
        and strict_docling_mode
        and strict
        and not bool(args.expanded_metric_scope)
    )
    docling_converter = None
    if use_docling:
        if "--cpu" in sys.argv or args.cpu:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
        cuda_available = _docling_cuda_available()
        docling_table_mode, docling_num_threads = resolve_docling_runtime_settings(
            requested_table_mode=args.docling_table_mode,
            requested_num_threads=args.docling_num_threads,
            cuda_available=cuda_available,
        )
        print(
            (
                "[info] docling runtime: "
                f"cuda_available={cuda_available} "
                f"table_mode={docling_table_mode} "
                f"num_threads={docling_num_threads if docling_num_threads > 0 else 'default'} "
                "ocr=False"
            ),
            file=sys.stderr,
        )
        docling_converter, docling_init_error = _get_docling_converter(
            do_ocr=False,
            table_mode=docling_table_mode,
            num_threads=docling_num_threads,
        )
        if docling_converter is None and docling_init_error:
            raise RuntimeError(str(docling_init_error))
    needs_pdftotext = (not use_docling) or line_parse_enabled
    if needs_pdftotext and shutil.which("pdftotext") is None:
        print("Missing dependency: pdftotext. Install: sudo apt install -y poppler-utils", file=sys.stderr)
        return 2
    if use_docling and strict and strict_docling_mode and not bool(args.expanded_metric_scope):
        print(
            "[info] strict Docling mode: pdftotext line pass is conditional on Docling signal strength.",
            file=sys.stderr,
        )

    if args.pdf:
        pdf_path = Path(args.pdf).resolve()
        if not pdf_path.exists():
            print(f"PDF file not found: {pdf_path}", file=sys.stderr)
            return 2
        if not pdf_path.is_file():
            print(f"PDF path is not a file: {pdf_path}", file=sys.stderr)
            return 2
        pdf_dir = pdf_path.parent
        pdfs = [pdf_path]
        input_target_label = str(pdf_path)
    else:
        pdf_dir = Path(args.pdf_dir).resolve()
        if not pdf_dir.exists():
            print(f"PDF directory not found: {pdf_dir}", file=sys.stderr)
            return 2
        if not pdf_dir.is_dir():
            print(f"PDF directory is not a directory: {pdf_dir}", file=sys.stderr)
            return 2
        pdfs = find_pdfs(pdf_dir)
        input_target_label = str(pdf_dir)
    if not pdfs:
        print(f"No PDF files found in: {input_target_label}", file=sys.stderr)
        return 2

    quarantine_rules: List[Dict[str, object]] = []
    quarantined_pdfs: List[Tuple[Path, str]] = []
    if not args.no_quarantine_rules:
        quarantine_rules = load_document_quarantine_rules(Path(args.quarantine_rules_json))
        if quarantine_rules:
            retained_pdfs: List[Path] = []
            for pdf in pdfs:
                reason = match_document_quarantine_reason(pdf, quarantine_rules)
                if reason:
                    quarantined_pdfs.append((pdf, reason))
                    continue
                retained_pdfs.append(pdf)
            pdfs = retained_pdfs
            if quarantined_pdfs:
                print(
                    f"[quarantine] skipped {len(quarantined_pdfs)} PDF(s) via {args.quarantine_rules_json}",
                    file=sys.stderr,
                )
                preview_count = min(10, len(quarantined_pdfs))
                for pdf, reason in quarantined_pdfs[:preview_count]:
                    print(f"[quarantine] {pdf} :: {reason}", file=sys.stderr)
                if len(quarantined_pdfs) > preview_count:
                    print(
                        f"[quarantine] ... {len(quarantined_pdfs) - preview_count} more skipped",
                        file=sys.stderr,
                    )
        elif args.quarantine_rules_json:
            qr_path = Path(args.quarantine_rules_json).expanduser()
            if qr_path.exists():
                print(
                    f"[warn] quarantine rules file has no valid rules: {qr_path}",
                    file=sys.stderr,
                )

    if not pdfs:
        print(f"No PDF files found in: {input_target_label} after quarantine filtering", file=sys.stderr)
        return 2

    rows: List[Dict[str, object]] = []
    context_rows: List[Dict[str, object]] = []
    rejected_rows: List[Dict[str, object]] = []
    blocks_rows: List[Dict[str, object]] = []
    document_diagnostics: List[Dict[str, object]] = []
    for pdf, reason in quarantined_pdfs:
        context_rows.append(_build_parse_failure_context_row(pdf, reason="document_quarantined", message=reason))
    if strict and args.disable_table_first:
        print("[warn] --disable-table-first is ignored in strict canonical mode", file=sys.stderr)

    total_pdfs = len(pdfs)
    for pdf_idx, pdf in enumerate(pdfs, start=1):
        print(f"[progress] [{pdf_idx}/{total_pdfs}] {pdf}", file=sys.stderr)
        skip_pdftotext_pass = not line_parse_enabled
        if strict:
            source_kind = classify_pdf_source_kind(pdf)
            extractor_selected = "docling" if use_docling else "pdftotext"
            document_classifier = {"is_financial": True, "document_type": ""}
            docling_row_count_before_filtering = 0
            tsr_tables_processed = 0
            fallback_decision: Dict[str, object] = {
                "should_fallback": False,
                "reasons": [],
                "fallback_reason": None,
                "consistency_report": {"failed_checks": []},
            }
            docling_split_diagnostics: Dict[str, object] = {}
            try:
                document_classifier = normalize_document_classifier_result(classify_document(pdf))
            except Exception as e:
                print(f"[warn] document classifier failed {pdf}: {e}", file=sys.stderr)
                document_classifier = {
                    "is_financial": True,
                    "document_type": "classifier_error",
                }
            try:
                if use_docling:
                    if not args.force_extract and not bool(document_classifier.get("is_financial", True)):
                        blocks = []
                        split = build_nonfinancial_docling_skip_split(pdf, document_classifier)
                        extractor_selected = "skipped_non_financial"
                        print(
                            f"[info] document classifier skipped docling {pdf}: "
                            f"{document_classifier.get('document_type', '')}",
                            file=sys.stderr,
                        )
                    else:
                        _, blocks, split = extract_table_metrics_docling(
                            pdf,
                            strict_metric_rows_only=True,
                            expanded_metric_scope=bool(args.expanded_metric_scope),
                            source_kind=source_kind,
                            review_scope="all",
                            include_blocks=True,
                            converter=docling_converter,
                        )
                        docling_split_diagnostics = _document_split_diagnostics(split)
                        docling_row_count_before_filtering = int(
                            docling_split_diagnostics.get("docling_row_count_before_filtering", 0) or 0
                        )
                        tsr_tables_processed = int(docling_split_diagnostics.get("tsr_tables_processed", 0) or 0)
                        if strict_docling_mode and strict:
                            skip_pdftotext_pass = not should_enable_hybrid(
                                docling_row_count_before_filtering,
                                tsr_tables_processed,
                            )
                        fallback_decision = evaluate_docling_fallback(split)
                        if fallback_decision.get("should_fallback"):
                            reason_text = ",".join(str(reason) for reason in fallback_decision.get("reasons", []))
                            print(f"[info] docling fallback -> pdftotext {pdf}: {reason_text}", file=sys.stderr)
                            skip_pdftotext_pass = True
                            try:
                                _, fallback_blocks, fallback_split = extract_table_metrics(
                                    pdf,
                                    strict_metric_rows_only=True,
                                    expanded_metric_scope=bool(args.expanded_metric_scope),
                                    source_kind=source_kind,
                                    review_scope="all",
                                    include_blocks=True,
                                    pdftotext_timeout_sec=args.pdftotext_timeout_sec,
                                )
                                fallback_split["context_rows"] = list(fallback_split.get("context_rows", [])) + [
                                    _build_parse_failure_context_row(
                                        pdf,
                                        reason="docling_fallback",
                                        message=reason_text,
                                    )
                                ]
                                blocks = fallback_blocks
                                split = fallback_split
                                extractor_selected = "pdftotext"
                            except PDFParseTimeoutError as e:
                                split["context_rows"] = list(split.get("context_rows", [])) + [
                                    _build_parse_failure_context_row(
                                        pdf,
                                        reason="docling_fallback_pdftotext_timeout",
                                        message=str(e),
                                    )
                                ]
                            except Exception as e:
                                split["context_rows"] = list(split.get("context_rows", [])) + [
                                    _build_parse_failure_context_row(
                                        pdf,
                                        reason="docling_fallback_pdftotext_failed",
                                        message=str(e),
                                    )
                                ]
                else:
                    _, blocks, split = extract_table_metrics(
                        pdf,
                        strict_metric_rows_only=True,
                        expanded_metric_scope=bool(args.expanded_metric_scope),
                        source_kind=source_kind,
                        review_scope="all",
                        include_blocks=True,
                        pdftotext_timeout_sec=args.pdftotext_timeout_sec,
                    )
            except PDFParseTimeoutError as e:
                print(f"[warn] table parse timeout {pdf}: {e}", file=sys.stderr)
                blocks = []
                split = build_split_result(
                    [],
                    [_build_parse_failure_context_row(pdf, reason="pdftotext_timeout", message=str(e))],
                    [],
                )
            except Exception as e:
                print(f"[warn] table parse failed {pdf}: {e}", file=sys.stderr)
                blocks = []
                split = build_split_result(
                    [],
                    [_build_parse_failure_context_row(pdf, reason="table_parse_failed", message=str(e))],
                    [],
                )
            split_diagnostics = dict(_document_split_diagnostics(split))
            split_diagnostics["document_classifier"] = dict(document_classifier)
            split["diagnostics"] = split_diagnostics
            selected_routing_summary = _document_routing_summary(split)
            selected_split_diagnostics = _document_split_diagnostics(split)
            consistency_report = fallback_decision.get("consistency_report", {})
            consistency_failures = 0
            if isinstance(consistency_report, dict):
                consistency_failures = len(list(consistency_report.get("failed_checks", []) or []))
            document_diagnostics.append(
                {
                    "ticker": pdf.parent.parent.name,
                    "document": str(pdf),
                    "source_kind": source_kind,
                    "extractor_requested": "docling" if use_docling else "pdftotext",
                    "extractor_selected": extractor_selected,
                    "fallback_triggered": bool(fallback_decision.get("should_fallback", False)),
                    "fallback_reason": fallback_decision.get("fallback_reason"),
                    "fallback_reasons": list(fallback_decision.get("reasons", []) or []),
                    "fallback_suppressed": bool(fallback_decision.get("fallback_suppressed", False)),
                    "fallback_suppression_reason": str(
                        fallback_decision.get("fallback_suppression_reason", "") or ""
                    ).strip()
                    or None,
                    "docling_row_count_before_filtering": int(
                        docling_split_diagnostics.get("docling_row_count_before_filtering", 0) or 0
                    ),
                    "skip_reason": str(selected_split_diagnostics.get("skip_reason", "")).strip() or None,
                    "document_classifier": dict(selected_split_diagnostics.get("document_classifier", {}) or {}),
                    "context_rows": int(selected_routing_summary.get("context_rows", 0) or 0),
                    "rejected_rows": int(selected_routing_summary.get("rejected_rows", 0) or 0),
                    "rejection_reasons": dict(selected_routing_summary.get("rejection_reasons", {}) or {}),
                    "tsr_tables_processed": int(docling_split_diagnostics.get("tsr_tables_processed", 0) or 0),
                    "reconciliation_repairs": int(docling_split_diagnostics.get("reconciliation_repairs", 0) or 0),
                    "tsr_duplicate_rows_demoted": int(selected_split_diagnostics.get("tsr_duplicate_rows_demoted", 0) or 0),
                    "table_statement_type_counts": dict(selected_split_diagnostics.get("table_statement_type_counts", {}) or {}),
                    "identity_resolution_applied": bool(selected_split_diagnostics.get("identity_resolution_applied", False)),
                    "identity_resolution_conflicts": int(selected_split_diagnostics.get("identity_resolution_conflicts", 0) or 0),
                    "consistency_failures": consistency_failures,
                    "normalization_corrections": int(selected_split_diagnostics.get("normalization_corrections", 0) or 0),
                }
            )
            rows.extend(list(split.get("canonical_rows", [])))
            context_rows.extend(list(split.get("context_rows", [])))
            rejected_rows.extend(list(split.get("rejected_rows", [])))
            if use_docling and not args.force_extract and not bool(document_classifier.get("is_financial", True)):
                continue
            if args.expanded_metric_scope and source_kind == "other":
                try:
                    expanded_context = extract_expanded_narrative_context_rows(
                        pdf,
                        pdftotext_timeout_sec=args.pdftotext_timeout_sec,
                    )
                except PDFParseTimeoutError as e:
                    print(f"[warn] expanded narrative parse timeout {pdf}: {e}", file=sys.stderr)
                    expanded_context = [
                        _build_parse_failure_context_row(pdf, reason="expanded_narrative_timeout", message=str(e))
                    ]
                except subprocess.CalledProcessError as e:
                    print(f"[warn] expanded narrative parse failed {pdf}: {e}", file=sys.stderr)
                    expanded_context = [
                        _build_parse_failure_context_row(
                            pdf,
                            reason="expanded_narrative_parse_failed",
                            message=str(e),
                        )
                    ]
                except Exception as e:
                    print(f"[warn] expanded narrative extraction failed {pdf}: {e}", file=sys.stderr)
                    expanded_context = [
                        _build_parse_failure_context_row(
                            pdf,
                            reason="expanded_narrative_failed",
                            message=str(e),
                        )
                    ]
                context_rows.extend(expanded_context)
            for b in blocks:
                blocks_rows.append(
                    {
                        "file": str(pdf),
                        "source_kind": source_kind,
                        **b,
                    }
                )

        if skip_pdftotext_pass:
            continue

        try:
            text = extract_pdf_text(pdf, timeout_sec=args.pdftotext_timeout_sec)
        except PDFParseTimeoutError as e:
            print(f"[warn] parse timeout {pdf}: {e}", file=sys.stderr)
            context_rows.append(_build_parse_failure_context_row(pdf, reason="pdftotext_timeout", message=str(e)))
            continue
        except subprocess.CalledProcessError as e:
            print(f"[warn] failed to parse {pdf}: {e}", file=sys.stderr)
            context_rows.append(_build_parse_failure_context_row(pdf, reason="parse_failed", message=str(e)))
            continue
        lines = text.splitlines()
        if strict:
            assembled_cashflow_rows = extract_cashflow_bridge_rows_from_lines(pdf, lines)
            context_rows.extend(assembled_cashflow_rows)
        active_section = ""
        for idx, line in enumerate(lines, start=1):
            heading = detect_section_heading(line)
            if heading:
                active_section = heading
            mult = infer_unit_multiplier(lines, idx)
            stmt_ctx = classify_statement_context(lines, idx, active_section=active_section)
            statement_type = str(stmt_ctx.get("statement_type", ""))
            canonical_stmt = is_canonical_statement_type(statement_type)
            line_metric_hits = list(iter_metric_hits(line))
            cashflow_bridge_hits = {
                "operating_cash_flow",
                "cash_and_equivalents_opening",
                "cash_and_equivalents_closing",
                "capex",
            } | OCF_COMPONENT_METRICS
            parsed = parse_line(
                pdf,
                idx,
                line,
                strict_table_only=strict,
                active_section=active_section,
                statement_type=statement_type,
                statement_scope_header=str(stmt_ctx.get("statement_scope_header", "")),
                page_number=0,
                note_number=str(stmt_ctx.get("note_number", "")),
            )
            parsed = [apply_unit_multiplier(r, mult) for r in parsed]
            for rr in parsed:
                rr.setdefault("row_label", str(rr.get("line", "")).strip())
                rr["source_mode"] = str(rr.get("source_mode", "")).strip() or "line"
                rr["context_reason"] = str(rr.get("context_reason", "")).strip() or "line_parse_fallback"
            if strict:
                context_rows.extend(parsed)
            else:
                rows.extend(parsed)
            if args.allow_narrative:
                continue

            if strict and not canonical_stmt:
                if not any(m in cashflow_bridge_hits for m in line_metric_hits):
                    continue

            has_metric = bool(line_metric_hits)
            if not has_metric:
                continue

            should_try = False
            if not parsed:
                should_try = True
            elif idx < len(lines):
                should_try = should_try_continuation_stitch(line, lines[idx])

            if not should_try:
                continue

            existing_keys = {
                (str(r.get("metric", "")), str(r.get("value_type", "")), str(r.get("raw_value", "")), str(r.get("period", "")))
                for r in parsed
            }
            stitched_any = False
            for step in range(1, 9):
                nxt_idx = idx - 1 + step
                if nxt_idx >= len(lines):
                    break
                nxt = lines[nxt_idx]
                nxt_stripped = nxt.strip()
                if not nxt_stripped:
                    continue
                if not parsed:
                    if NUM_RE.search(nxt) or PCT_RE.search(nxt):
                        pass
                    elif step == 1 and is_table_label_continuation_fragment(nxt):
                        # Allow one wrapped label line before numeric columns.
                        continue
                    else:
                        break
                else:
                    if not (NUM_RE.search(nxt) or PCT_RE.search(nxt)):
                        break
                combo_parts = [line.strip()] + [lines[idx - 1 + k].strip() for k in range(1, step + 1)]
                combo = " ".join(p for p in combo_parts if p)
                strict_stitch = strict and canonical_stmt
                if not parsed:
                    stitched = parse_line(
                        pdf,
                        idx,
                        combo,
                        strict_table_only=strict_stitch,
                        active_section=active_section,
                        statement_type=statement_type,
                        statement_scope_header=str(stmt_ctx.get("statement_scope_header", "")),
                        page_number=0,
                        note_number=str(stmt_ctx.get("note_number", "")),
                    )
                else:
                    # For continuation lines (e.g., wrapped comparative period values), allow
                    # relaxed parse but keep only non-text rows for metrics already detected.
                    stitched = parse_line(
                        pdf,
                        idx,
                        combo,
                        strict_table_only=False,
                        active_section=active_section,
                        statement_type=statement_type,
                        statement_scope_header=str(stmt_ctx.get("statement_scope_header", "")),
                        page_number=0,
                        note_number=str(stmt_ctx.get("note_number", "")),
                    )
                    parsed_metrics = {str(r.get("metric", "")) for r in parsed}
                    stitched = [
                        r
                        for r in stitched
                        if str(r.get("value_type", "")) in {"amount", "percent"}
                        and str(r.get("metric", "")) in parsed_metrics
                    ]
                stitched = [apply_unit_multiplier(r, infer_unit_multiplier(lines, idx + step)) for r in stitched]
                if not stitched:
                    continue
                extras = [
                    r
                    for r in stitched
                    if (
                        str(r.get("metric", "")),
                        str(r.get("value_type", "")),
                        str(r.get("raw_value", "")),
                        str(r.get("period", "")),
                    )
                    not in existing_keys
                ]
                if extras:
                    for rr in extras:
                        rr.setdefault("row_label", str(rr.get("line", "")).strip())
                        rr["source_mode"] = "line_stitch_forward"
                        rr["context_reason"] = str(rr.get("context_reason", "")).strip() or "line_stitch_forward"
                    if strict:
                        context_rows.extend(extras)
                    elif canonical_stmt:
                        rows.extend(extras)
                    else:
                        context_rows.extend(extras)
                    stitched_any = True
                    break

            if not parsed and not stitched_any and any(m in cashflow_bridge_hits for m in line_metric_hits):
                back_numeric_lines: List[str] = []
                for back_step in range(1, 9):
                    prev_idx = idx - 1 - back_step
                    if prev_idx < 0:
                        break
                    prev_line = lines[prev_idx].strip()
                    if not prev_line:
                        continue
                    if NUM_RE.search(prev_line) or PCT_RE.search(prev_line):
                        back_numeric_lines.append(prev_line)
                        if len(back_numeric_lines) >= 3:
                            break
                        continue
                    if back_numeric_lines:
                        break
                    if is_table_label_continuation_fragment(prev_line):
                        continue
                    break

                if back_numeric_lines:
                    back_combo = " ".join([line.strip()] + list(reversed(back_numeric_lines)))
                    stitched_back = parse_line(
                        pdf,
                        idx,
                        back_combo,
                        strict_table_only=False,
                        active_section=active_section,
                        statement_type=statement_type,
                        statement_scope_header=str(stmt_ctx.get("statement_scope_header", "")),
                        page_number=0,
                        note_number=str(stmt_ctx.get("note_number", "")),
                    )
                    stitched_back = [apply_unit_multiplier(r, mult) for r in stitched_back]
                    back_extras = [
                        r
                        for r in stitched_back
                        if (
                            str(r.get("metric", "")),
                            str(r.get("value_type", "")),
                            str(r.get("raw_value", "")),
                            str(r.get("period", "")),
                        )
                        not in existing_keys
                    ]
                    if back_extras:
                        for rr in back_extras:
                            rr.setdefault("row_label", str(rr.get("line", "")).strip())
                            rr["source_mode"] = "line_stitch_backward"
                            rr["context_reason"] = str(rr.get("context_reason", "")).strip() or "line_stitch_backward"
                        if strict:
                            context_rows.extend(back_extras)
                        elif canonical_stmt:
                            rows.extend(back_extras)
                        else:
                            context_rows.extend(back_extras)

    normalize_metric_rows(rows)
    normalize_metric_rows(context_rows)
    normalize_metric_rows(rejected_rows)
    rows = dedupe(rows)
    context_rows = dedupe(context_rows)
    rejected_rows = dedupe(rejected_rows)
    annotate_definition_scope(rows)
    annotate_definition_scope(context_rows)
    annotate_definition_scope(rejected_rows)
    if args.dedupe_variant_docs:
        rows = dedupe_variant_document_rows(rows)
        context_rows = dedupe_variant_document_rows(context_rows)
        rejected_rows = dedupe_variant_document_rows(rejected_rows)
    rows, global_identity_resolution_rows, _ = resolve_duplicate_metrics(rows)
    if global_identity_resolution_rows:
        context_rows.extend(global_identity_resolution_rows)
        context_rows = dedupe(context_rows)
    rows, global_conflict_rows = resolve_canonical_conflicts(rows)
    if global_conflict_rows:
        context_rows.extend(global_conflict_rows)
        context_rows = dedupe(context_rows)
    if not rows and strict and not context_rows and not rejected_rows:
        print("No metric candidates found. PDFs may be scanned images (OCR needed) or use unexpected formatting.")
        return 1

    annotate_period_metadata(rows)
    annotate_period_metadata(context_rows)
    annotate_period_metadata(rejected_rows)

    for r in rows + context_rows + rejected_rows:
        r["confidence"] = score_confidence(r)

    invalid_canonical_rows: List[Dict[str, object]] = []
    valid_canonical_rows: List[Dict[str, object]] = []
    for r in rows:
        errs = validate_canonical_row(r)
        if not errs:
            valid_canonical_rows.append(r)
            continue
        rr = dict(r)
        rr["rejection_reason"] = "canonical_validation_failed"
        rr["validation_errors"] = "; ".join(errs)
        invalid_canonical_rows.append(rr)
    rows = dedupe(valid_canonical_rows)
    if invalid_canonical_rows:
        rejected_rows.extend(invalid_canonical_rows)
        rejected_rows = dedupe(rejected_rows)

    annotate_integrity_metadata(rows)
    annotate_integrity_metadata(context_rows)
    annotate_integrity_metadata(rejected_rows)
    mark_primary_metric_rows(rows)
    primary_rows = [r for r in rows if bool(r.get("primary_metric_value"))]
    primary_rows = dedupe(primary_rows)
    coverage_enhanced_rows, backfill_audit_rows = build_coverage_enhanced_rows(primary_rows, rows, context_rows)
    all_datapoints_rows = build_all_datapoints_rows(primary_rows, rows, context_rows, rejected_rows)

    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_all_variants_json = Path(args.out_all_variants_json)
    out_primary_csv = Path(args.out_primary_csv)
    out_primary_json = Path(args.out_primary_json)
    out_all_datapoints_json = Path(args.out_all_datapoints_json)
    out_coverage_enhanced_json = Path(args.out_coverage_enhanced_json)
    out_coverage_backfill_audit_json = Path(args.out_coverage_backfill_audit_json)
    write_csv(rows, out_csv)
    write_json(primary_rows, out_json)
    write_json(rows, out_all_variants_json)
    write_csv(primary_rows, out_primary_csv)
    write_json(primary_rows, out_primary_json)
    write_json(all_datapoints_rows, out_all_datapoints_json)
    write_json(coverage_enhanced_rows, out_coverage_enhanced_json)
    write_json(backfill_audit_rows, out_coverage_backfill_audit_json)
    out_context_csv = Path(args.out_context_csv)
    out_context_json = Path(args.out_context_json)
    out_rejected_json = Path(args.out_rejected_json)
    out_blocks_json = Path(args.out_blocks_json)
    write_csv(context_rows, out_context_csv)
    write_json(context_rows, out_context_json)
    write_json(rejected_rows, out_rejected_json)
    write_json(blocks_rows, out_blocks_json)
    if args.out_document_diagnostics_json:
        write_json(document_diagnostics, Path(args.out_document_diagnostics_json))

    high_rows = [r for r in rows if float(r.get("confidence", 0.0)) >= args.min_confidence]
    out_high_csv = Path(args.out_high_csv)
    out_high_json = Path(args.out_high_json)
    write_csv(high_rows, out_high_csv)
    write_json(high_rows, out_high_json)
    out_sqlite = Path(args.out_sqlite)
    sqlite_rows_written = 0
    sqlite_integrity_written = 0
    if not args.no_sqlite:
        sqlite_rows_written = store_metrics_sqlite(rows, out_sqlite)
        sqlite_integrity_written = store_statement_integrity_sqlite(rows, out_sqlite)

    gate_report = build_financial_metrics_gate_report(primary_rows, max_sample=20)
    gate_report["input_file"] = str(out_json.resolve())
    gate_report["rows_skipped_non_object"] = 0
    if args.financial_gates_report:
        gates_report_path = Path(args.financial_gates_report)
    else:
        gates_report_path = out_json.with_suffix(".gates.json")
    gates_report_path.parent.mkdir(parents=True, exist_ok=True)
    with gates_report_path.open("w", encoding="utf-8") as gf:
        json.dump(gate_report, gf, indent=2)

    coverage_profile = _infer_company_profile(primary_rows or coverage_enhanced_rows, args.coverage_profile)
    coverage_required_metrics = [tok.strip().lower() for tok in str(args.coverage_required_metrics or "").split(",") if tok.strip()]
    if not coverage_required_metrics:
        coverage_required_metrics = list(DEFAULT_COVERAGE_REQUIRED_METRICS_BY_PROFILE.get(coverage_profile, []))
    coverage_period_types = [tok.strip().lower() for tok in str(args.coverage_period_types or "").split(",") if tok.strip()]
    coverage_report_canonical = build_financial_coverage_gate_report(
        primary_rows,
        required_metrics=coverage_required_metrics,
        period_types=coverage_period_types,
        recent_periods=max(1, int(args.coverage_recent_periods)),
        coverage_profile=coverage_profile,
    )
    coverage_report_canonical["input_file"] = str(out_json.resolve())
    coverage_report_canonical["rows_skipped_non_object"] = 0
    coverage_report_enhanced = build_financial_coverage_gate_report(
        coverage_enhanced_rows,
        required_metrics=coverage_required_metrics,
        period_types=coverage_period_types,
        recent_periods=max(1, int(args.coverage_recent_periods)),
        coverage_profile=coverage_profile,
    )
    coverage_report_enhanced["input_file"] = str(out_coverage_enhanced_json.resolve())
    coverage_report_enhanced["rows_skipped_non_object"] = 0
    if args.coverage_gates_report:
        coverage_report_path = Path(args.coverage_gates_report)
    else:
        coverage_report_path = out_json.with_suffix(".coverage_gates.json")
    coverage_report_path.parent.mkdir(parents=True, exist_ok=True)
    with coverage_report_path.open("w", encoding="utf-8") as cf:
        json.dump(coverage_report_canonical, cf, indent=2)
    if args.coverage_enhanced_gates_report:
        coverage_enhanced_report_path = Path(args.coverage_enhanced_gates_report)
    else:
        coverage_enhanced_report_path = out_coverage_enhanced_json.with_suffix(".coverage_gates.json")
    coverage_enhanced_report_path.parent.mkdir(parents=True, exist_ok=True)
    with coverage_enhanced_report_path.open("w", encoding="utf-8") as cf:
        json.dump(coverage_report_enhanced, cf, indent=2)

    print(f"Extracted canonical metric candidates: {len(rows)}")
    print(f"Primary canonical rows: {len(primary_rows)}")
    promoted_rows = sum(1 for r in rows if str(r.get("canonical_tier", "")).strip().lower() == "table_promoted")
    print(f"Table-context promoted canonical rows: {promoted_rows}")
    print(f"Context-only rows: {len(context_rows)}")
    print(f"Rejected rows: {len(rejected_rows)}")
    period_type_counts, unresolved_flow, reporting_cadence_counts, unresolved_stock_cadence = build_period_metadata_summary(rows)
    if period_type_counts:
        period_type_counts_text = ", ".join(f"{k}={v}" for k, v in period_type_counts.items())
        print(f"Canonical period types: {period_type_counts_text}")
    if reporting_cadence_counts:
        reporting_cadence_text = ", ".join(f"{k}={v}" for k, v in reporting_cadence_counts.items())
        print(f"Canonical reporting cadence: {reporting_cadence_text}")
    print(f"Flow metrics with unresolved period type: {unresolved_flow}")
    print(f"Stock metrics with unresolved reporting cadence: {unresolved_stock_cadence}")
    print(f"Statement blocks: {len(blocks_rows)}")
    print(f"High-confidence rows (>= {args.min_confidence}): {len(high_rows)}")
    print(f"Canonical CSV: {out_csv}")
    print(f"Primary canonical JSON: {out_json}")
    print(f"All datapoints JSON: {out_all_datapoints_json}")
    print(f"Coverage-enhanced JSON: {out_coverage_enhanced_json}")
    print(f"Coverage backfill audit JSON: {out_coverage_backfill_audit_json}")
    print(f"All-variants JSON: {out_all_variants_json}")
    print(f"Primary CSV: {out_primary_csv}")
    print(f"Primary JSON: {out_primary_json}")
    print(f"Context CSV: {out_context_csv}")
    print(f"Context JSON: {out_context_json}")
    print(f"Rejected JSON: {out_rejected_json}")
    print(f"Blocks JSON: {out_blocks_json}")
    print(f"High CSV: {out_high_csv}")
    print(f"High JSON: {out_high_json}")
    print(
        "Financial gates: "
        f"pass={gate_report.get('gate_pass')} "
        f"duplicates={gate_report.get('duplicates')} "
        f"conflicts={gate_report.get('conflicts')} "
        f"empty_currency={gate_report.get('empty_currency')}"
    )
    print(f"Financial gates report: {gates_report_path}")
    print(
        "Coverage gates (canonical): "
        f"pass={coverage_report_canonical.get('gate_pass')} "
        f"checks_failed={coverage_report_canonical.get('checks_failed')} "
        f"checks_total={coverage_report_canonical.get('checks_total')}"
    )
    print(f"Coverage gates report: {coverage_report_path}")
    print(
        "Coverage gates (enhanced): "
        f"pass={coverage_report_enhanced.get('gate_pass')} "
        f"checks_failed={coverage_report_enhanced.get('checks_failed')} "
        f"checks_total={coverage_report_enhanced.get('checks_total')}"
    )
    print(f"Coverage-enhanced gates report: {coverage_enhanced_report_path}")
    if not args.no_sqlite:
        print(f"SQLite rows upserted: {sqlite_rows_written}")
        print(f"SQLite statement integrity rows upserted: {sqlite_integrity_written}")
        print(f"SQLite DB: {out_sqlite}")
    if args.enforce_financial_gates and not bool(gate_report.get("gate_pass")):
        failed = gate_report.get("failed_gates") or []
        print(
            "[error] Financial ingestion gates failed: "
            + ", ".join(str(x) for x in failed),
            file=sys.stderr,
        )
        return 1
    if args.enforce_coverage_gates and (
        (not bool(coverage_report_canonical.get("gate_pass")))
        or (not bool(coverage_report_enhanced.get("gate_pass")))
    ):
        print(
            "[error] Coverage gates failed: "
            f"canonical={coverage_report_canonical.get('checks_failed')}/{coverage_report_canonical.get('checks_total')}, "
            f"enhanced={coverage_report_enhanced.get('checks_failed')}/{coverage_report_enhanced.get('checks_total')}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
