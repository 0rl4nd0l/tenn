#!/usr/bin/env python3
import argparse
import calendar
import csv
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
from typing import Dict, Iterable, List, Optional, Tuple


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
BARE_YEAR_RE = re.compile(r"\b20\d{2}\b")
FY_PERIOD_RE = re.compile(r"\bFY\s*[-/]?\s*(\d{2,4})\b", re.IGNORECASE)
DOC_DATE_RE = re.compile(r"\b(20\d{2})[-_](\d{2})[-_](\d{2})\b")
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
    ("revenue", re.compile(r"\b(revenue|turnover|total income)\b", re.IGNORECASE)),
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
    ("operating_cash_flow", re.compile(r"\b(operating cash flow|cash from operations)\b", re.IGNORECASE)),
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
    "revenue": re.compile(r"\b(total\s+revenue|revenue|turnover|total\s+income)\b", re.IGNORECASE),
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
    "operating_cash_flow": re.compile(r"\b(operating\s+cash\s+flow|cash\s+from\s+operations)\b", re.IGNORECASE),
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
    (re.compile(r"\$\s*[A-Z]?[’']?000\b|\b[A$]{0,2}\s*'000\b", re.IGNORECASE), 1e3),
    (re.compile(r"\b(in\s+thousands|thousand\s+dollars|A\$'000)\b", re.IGNORECASE), 1e3),
    (re.compile(r"\$\s*[A-Z]?\s*(bn|billion)\b|\b(in\s+billions)\b", re.IGNORECASE), 1e9),
    (re.compile(r"\$\s*[A-Z]?\s*(m|million)\b|\b(in\s+millions)\b", re.IGNORECASE), 1e6),
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
    "cash_and_equivalents",
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
INCOME_STATEMENT_METRICS = {"revenue", "segment_revenue", "gross_profit", "ebit", "ebitda", "net_income", "npat", "eps"}
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
    "capex",
}
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
    out: List[str] = []
    seen_text = set()
    seen_dates = set()

    def push_date(day: int, month_token: str, year: int) -> None:
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
        out.append(lab)

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
        out.append(lab)
    loose_re = re.compile(r"\b(\d{1,2})\s+([A-Za-z](?:\s*[A-Za-z]){2,10})\s+(20\d{2})\b")
    for m in loose_re.finditer(src):
        try:
            day = int(m.group(1))
            year = int(m.group(3))
        except ValueError:
            continue
        push_date(day, m.group(2), year)

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
        push_date(d1, m.group(2), y1)
        push_date(d2, m.group(4), y2)
    return out


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


def normalize_period_for_db(period_label: str, doc_date: str = "") -> Tuple[str, str]:
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
    fy = FY_PERIOD_RE.search(period)
    if fy:
        y = _parse_year_token(fy.group(1))
        if y is not None:
            iso = f"{y:04d}-12-31"
            return iso, iso
    y2 = BARE_YEAR_RE.search(period)
    if y2:
        iso = f"{int(y2.group(0)):04d}-12-31"
        return iso, iso
    return "", doc_date


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
                statement_scope_reason TEXT NOT NULL DEFAULT '',
                block_id TEXT NOT NULL DEFAULT '',
                table_id TEXT NOT NULL DEFAULT '',
                table_page INTEGER NOT NULL DEFAULT 0,
                page_number INTEGER NOT NULL DEFAULT 0,
                line_no INTEGER NOT NULL DEFAULT 0,
                inside_table INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 0.0,
                canonical_confidence_score INTEGER NOT NULL DEFAULT 0,
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
            "balance_position": "TEXT NOT NULL DEFAULT ''",
            "balance_date": "TEXT NOT NULL DEFAULT ''",
            "statement_family": "TEXT NOT NULL DEFAULT ''",
            "canonical_confidence_score": "INTEGER NOT NULL DEFAULT 0",
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
                period_label, period_end_date, statement_period_label, statement_period_end, balance_position, balance_date,
                period_sort_date, period_sort_key, integrity_score, integrity_checks_evaluated, integrity_checks_passed,
                integrity_score_max, integrity_balance_sheet_pass, integrity_cash_flow_bridge_pass,
                integrity_retained_earnings_pass, integrity_income_integrity_pass, data_anomaly_level,
                statement_scope, statement_title, statement_family, statement_scope_reason,
                block_id, table_id, table_page, page_number, line_no,
                inside_table, confidence, canonical_confidence_score, source_mode, created_utc, updated_utc
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
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
                statement_scope_reason=excluded.statement_scope_reason,
                block_id=excluded.block_id,
                table_id=excluded.table_id,
                table_page=excluded.table_page,
                page_number=excluded.page_number,
                line_no=excluded.line_no,
                inside_table=excluded.inside_table,
                confidence=excluded.confidence,
                canonical_confidence_score=excluded.canonical_confidence_score,
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
                    str(row.get("statement_scope_reason", "")),
                    str(row.get("block_id", "")),
                    str(row.get("table_id", "")),
                    int(row.get("table_page", 0) or 0),
                    int(row.get("page_number", 0) or 0),
                    int(row.get("line_no", 0) or 0),
                    1 if bool(row.get("inside_table", False)) else 0,
                    float(row.get("confidence", 0.0) or 0.0),
                    int(row.get("canonical_confidence_score", 0) or 0),
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
    target = page_lines[target_idx]
    t_bbox = target.get("bbox")
    if not t_bbox:
        return ""
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
    if not candidates:
        return ""
    candidates.sort()
    return candidates[0][3]


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
        page_lines = sorted(by_page[page], key=lambda x: int(x["line_no_on_page"]))
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
    if has_note_marker:
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
            ctx_start = max(0, start_idx - 30)
            ctx_end = min(len(page_lines), end_idx + 8)
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
            context_text = "\n".join((context_lines + ([header_text] if header_text.strip() else []))[-40:])
            if len(region_text_lines) <= 60:
                block_text = "\n".join(region_text_lines)
            else:
                block_text = "\n".join(region_text_lines[:30] + ["..."] + region_text_lines[-30:])
            classify_header_parts = [scope_header, context_text, header_text]
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
                normalized_title = _normalize_space(title).lower()
                has_cashflow_title = bool(
                    re.search(
                        r"\b(cash\s+flows?|statement\s+of\s+cash\s+flows?|quarterly\s+cash\s+flow)\b",
                        normalized_title,
                        re.IGNORECASE,
                    )
                )
                if not has_cashflow_title:
                    title = "Consolidated statement of cash flows"
                elif re.search(r"\bconsolidated\s+statement\s+of\s+cash\s+flows?\b", normalized_title, re.IGNORECASE):
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
                region_kind = max(set(kinds), key=kinds.count)
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
                    if strict_metric_rows_only and metric in {"growth_pct", "guidance"}:
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
                            "row_label_metric_hit_count": len(row_label_metric_hits),
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


def split_rows_by_scope(rows: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    canonical_rows: List[Dict[str, object]] = []
    context_rows: List[Dict[str, object]] = []
    rejected_rows: List[Dict[str, object]] = []

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

    for r in rows:
        rr = dict(r)
        statement_scope = str(rr.get("statement_scope") or rr.get("statement_type", "")).strip().lower()
        inside_table = bool(rr.get("inside_table"))
        if not inside_table:
            rr["rejection_reason"] = "not_inside_table"
            rejected_rows.append(rr)
            continue
        if bool(rr.get("pro_forma_context")):
            rr["context_reason"] = "pro_forma_context"
            context_rows.append(rr)
            continue
        metric_name = str(rr.get("metric", "")).strip().lower()
        rr["metric_alias"] = str(rr.get("metric_alias", "")).strip() or infer_metric_alias(
            metric_name,
            row_label=str(rr.get("row_label", "")),
            line_text=str(rr.get("line", "")),
        )
        statement_title = str(rr.get("statement_title", rr.get("statement_scope_header", ""))).strip().lower()
        statement_family = str(rr.get("statement_family", "")).strip().lower() or infer_statement_family(
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
        expected_families = metric_expected_families(metric_name)
        statement_family = _recover_statement_family(metric_name, statement_family, rr)
        rr["statement_family"] = statement_family
        if expected_families and statement_family not in {"", "other"} and statement_family not in expected_families:
            rr["context_reason"] = "metric_statement_mismatch"
            context_rows.append(rr)
            continue
        row_label_raw = str(rr.get("row_label", ""))
        row_label_text = _normalize_space(row_label_raw).lower()
        if metric_name in MONEY_METRICS and row_label_text:
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
            if not COMBINED_LIAB_EQUITY_ROW_RE.search(row_label_text):
                rr["context_reason"] = "ambiguous_row_label"
                context_rows.append(rr)
                continue
        if metric_name in {"net_debt", "total_debt", "free_cash_flow", "operating_cash_flow"}:
            if re.match(r"^(less|add)\s*[:\-]", row_label_text):
                rr["context_reason"] = "component_adjustment_row"
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
        if metric_name in {"net_income", "npat"} and re.search(
            r"\b(total\s+comprehensive\s+income|other\s+comprehensive\s+income)\b",
            row_label_text,
            re.IGNORECASE,
        ):
            rr["context_reason"] = "comprehensive_income_context"
            context_rows.append(rr)
            continue
        _repair_non_month_end_period(rr)
        statement_period_end = str(rr.get("statement_period_end", "")).strip()
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
    canonical_rows, conflict_rows = resolve_canonical_conflicts(canonical_rows)
    context_rows.extend(conflict_rows)
    canonical_rows, bs_guard_rows = apply_balance_sheet_identity_guard(canonical_rows)
    context_rows.extend(bs_guard_rows)
    return {
        "canonical_rows": dedupe(canonical_rows),
        "context_rows": dedupe(context_rows),
        "rejected_rows": dedupe(rejected_rows),
    }


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
):
    by_page = _prepare_bbox_pages(pdf, timeout_sec=pdftotext_timeout_sec)
    if not by_page:
        empty_split = {"canonical_rows": [], "context_rows": [], "rejected_rows": []}
        if include_blocks:
            return [], [], empty_split
        return []
    blocks = segment_statement_blocks(pdf, source_kind=source_kind, prepared_pages=by_page)
    rows = extract_metrics_from_blocks(pdf, blocks, strict_metric_rows_only=strict_metric_rows_only, prepared_pages=by_page)
    split = split_rows_by_scope(rows)

    scope = (review_scope or "canonical").strip().lower()
    if scope == "context":
        selected = split["context_rows"]
    elif scope == "all":
        selected = rows
    else:
        selected = split["canonical_rows"]

    selected = dedupe(selected)
    if include_blocks:
        return selected, blocks, split
    return selected


def parse_scaled_number(raw: str, suffix: Optional[str]) -> Optional[float]:
    s = raw.strip()
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "")
    try:
        val = float(s)
    except ValueError:
        return None

    mult = 1.0
    if suffix:
        u = suffix.lower()
        if u in ("k", "thousand"):
            mult = 1e3
        elif u in ("m", "million", "mn", "mm"):
            mult = 1e6
        elif u in ("b", "billion", "bn"):
            mult = 1e9
        elif u in ("t", "trillion"):
            mult = 1e12
    val *= mult
    return -val if neg else val


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
    for line in reversed(lines):
        t = _normalize_space(line)
        if not t:
            continue
        if trailing_note_re.search(t) or PAGE_FOOTER_RE.search(t) or GENERIC_FOOTER_RE.search(t):
            continue
        if PARENT_SCOPE_RE.search(t) or CONSOLIDATED_SCOPE_RE.search(t) or APPENDIX_SCOPE_RE.search(t):
            return t
        if STATEMENT_LAYOUT_RE.search(t):
            return t
        if NOTE_SCOPE_RE.search(t) or NOTE_INLINE_SCOPE_RE.search(t) or NOTES_TO_SECTION_RE.search(t):
            return t
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
    for metric, pat in METRIC_PATTERNS:
        if pat.search(line):
            yield metric


def detect_metric_variant(metric: str, row_label: str = "", line_text: str = "", table_header_text: str = "") -> str:
    if metric not in {"revenue", "gross_profit", "ebitda", "ebit", "net_income", "npat"}:
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


def resolve_canonical_conflicts(canonical_rows: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Dict[str, object]]] = {}
    for rr in canonical_rows:
        key = (
            str(rr.get("file", "")),
            str(rr.get("metric", "")),
            str(rr.get("metric_variant", "")),
            str(rr.get("statement_period_end", "")),
            str(rr.get("balance_position", "")),
        )
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
                demoted.append(rr)
            continue
        kept.append(winner)
        for loser in ranked[1:]:
            rr = dict(loser)
            rr["context_reason"] = "canonical_conflict_same_period"
            rr["canonical_conflict_winner_line_no"] = winner.get("line_no", 0)
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
    anchors = [m.start() for m in METRIC_PATTERN_MAP[metric].finditer(line)]
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

    # Reject narrative commentary with event verbs by default.
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

    numeric_count = len(num_hits) + len(pct_hits)
    numeric_density = (numeric_count / max(1, len(words)))
    has_table_hint = bool(TABLE_LAYOUT_HINT_RE.search(text))
    has_table_gap = bool(TABLE_COLUMN_GAP_RE.search(line))
    has_leading_label = bool(label_match and label_match.start() <= 2)

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
                            "period": row_period or period,
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


def find_pdfs(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.pdf") if p.is_file())


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
        "statement_scope_reason",
        "block_id",
        "table_id",
        "table_page",
        "page_number",
        "note_number",
        "source_mode",
        "canonical_confidence_score",
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract financial metrics from PDFs")
    ap.add_argument("--pdf-dir", required=True, help="Folder containing PDF files")
    ap.add_argument("--out-csv", default="reports/financial_metrics.csv", help="Canonical CSV output path")
    ap.add_argument("--out-json", default="reports/financial_metrics.json", help="Canonical JSON output path")
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
    args = ap.parse_args()

    if shutil.which("pdftotext") is None:
        print("Missing dependency: pdftotext. Install: sudo apt install -y poppler-utils", file=sys.stderr)
        return 2

    pdf_dir = Path(args.pdf_dir).resolve()
    if not pdf_dir.exists():
        print(f"PDF directory not found: {pdf_dir}", file=sys.stderr)
        return 2

    pdfs = find_pdfs(pdf_dir)
    if not pdfs:
        print(f"No PDF files found in: {pdf_dir}", file=sys.stderr)
        return 2

    rows: List[Dict[str, object]] = []
    context_rows: List[Dict[str, object]] = []
    rejected_rows: List[Dict[str, object]] = []
    blocks_rows: List[Dict[str, object]] = []
    strict = not args.allow_narrative
    if strict and args.disable_table_first:
        print("[warn] --disable-table-first is ignored in strict canonical mode", file=sys.stderr)

    for pdf in pdfs:
        if strict:
            source_kind = classify_pdf_source_kind(pdf)
            try:
                _, blocks, split = extract_table_metrics(
                    pdf,
                    strict_metric_rows_only=True,
                    source_kind=source_kind,
                    review_scope="all",
                    include_blocks=True,
                    pdftotext_timeout_sec=args.pdftotext_timeout_sec,
                )
            except PDFParseTimeoutError as e:
                print(f"[warn] table parse timeout {pdf}: {e}", file=sys.stderr)
                blocks = []
                split = {
                    "canonical_rows": [],
                    "context_rows": [_build_parse_failure_context_row(pdf, reason="pdftotext_timeout", message=str(e))],
                    "rejected_rows": [],
                }
            except Exception as e:
                print(f"[warn] table parse failed {pdf}: {e}", file=sys.stderr)
                blocks = []
                split = {
                    "canonical_rows": [],
                    "context_rows": [_build_parse_failure_context_row(pdf, reason="table_parse_failed", message=str(e))],
                    "rejected_rows": [],
                }
            rows.extend(list(split.get("canonical_rows", [])))
            context_rows.extend(list(split.get("context_rows", [])))
            rejected_rows.extend(list(split.get("rejected_rows", [])))
            for b in blocks:
                blocks_rows.append(
                    {
                        "file": str(pdf),
                        "source_kind": source_kind,
                        **b,
                    }
                )
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
        active_section = ""
        for idx, line in enumerate(lines, start=1):
            heading = detect_section_heading(line)
            if heading:
                active_section = heading
            mult = infer_unit_multiplier(lines, idx)
            stmt_ctx = classify_statement_context(lines, idx, active_section=active_section)
            parsed = parse_line(
                pdf,
                idx,
                line,
                strict_table_only=strict,
                active_section=active_section,
                statement_type=str(stmt_ctx.get("statement_type", "")),
                statement_scope_header=str(stmt_ctx.get("statement_scope_header", "")),
                page_number=0,
                note_number=str(stmt_ctx.get("note_number", "")),
            )
            parsed = [apply_unit_multiplier(r, mult) for r in parsed]
            rows.extend(parsed)
            if args.allow_narrative:
                continue

            if strict and not is_canonical_statement_type(str(stmt_ctx.get("statement_type", ""))):
                continue

            has_metric = bool(list(iter_metric_hits(line)))
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
            for step in (1, 2):
                nxt_idx = idx - 1 + step
                if nxt_idx >= len(lines):
                    break
                nxt = lines[nxt_idx]
                if not parsed:
                    if is_numeric_table_fragment(nxt):
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
                if not parsed:
                    stitched = parse_line(
                        pdf,
                        idx,
                        combo,
                        strict_table_only=True,
                        active_section=active_section,
                        statement_type=str(stmt_ctx.get("statement_type", "")),
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
                        statement_type=str(stmt_ctx.get("statement_type", "")),
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
                    rows.extend(extras)
                    break

    rows = dedupe(rows)
    context_rows = dedupe(context_rows)
    rejected_rows = dedupe(rejected_rows)
    if not rows and strict and not context_rows and not rejected_rows:
        print("No metric candidates found. PDFs may be scanned images (OCR needed) or use unexpected formatting.")
        return 1

    for r in rows + context_rows + rejected_rows:
        r["confidence"] = score_confidence(r)

    annotate_integrity_metadata(rows)
    annotate_integrity_metadata(context_rows)
    annotate_integrity_metadata(rejected_rows)

    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    write_csv(rows, out_csv)
    write_json(rows, out_json)
    out_context_csv = Path(args.out_context_csv)
    out_context_json = Path(args.out_context_json)
    out_rejected_json = Path(args.out_rejected_json)
    out_blocks_json = Path(args.out_blocks_json)
    write_csv(context_rows, out_context_csv)
    write_json(context_rows, out_context_json)
    write_json(rejected_rows, out_rejected_json)
    write_json(blocks_rows, out_blocks_json)

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

    print(f"Extracted canonical metric candidates: {len(rows)}")
    print(f"Context-only rows: {len(context_rows)}")
    print(f"Rejected rows: {len(rejected_rows)}")
    print(f"Statement blocks: {len(blocks_rows)}")
    print(f"High-confidence rows (>= {args.min_confidence}): {len(high_rows)}")
    print(f"Canonical CSV: {out_csv}")
    print(f"Canonical JSON: {out_json}")
    print(f"Context CSV: {out_context_csv}")
    print(f"Context JSON: {out_context_json}")
    print(f"Rejected JSON: {out_rejected_json}")
    print(f"Blocks JSON: {out_blocks_json}")
    print(f"High CSV: {out_high_csv}")
    print(f"High JSON: {out_high_json}")
    if not args.no_sqlite:
        print(f"SQLite rows upserted: {sqlite_rows_written}")
        print(f"SQLite statement integrity rows upserted: {sqlite_integrity_written}")
        print(f"SQLite DB: {out_sqlite}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
