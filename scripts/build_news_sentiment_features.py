#!/usr/bin/env python3
"""
Build advisory-only news sentiment features from the news context SQLite DB.

This script is intentionally non-executive: it computes signals for analysis
workflows and does not place orders or trigger trading actions.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sqlite3
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_CONTEXT_DB, resolve_path  # noqa: E402


POSITIVE_LEXICON: dict[str, float] = {
    "beat estimates": 1.8,
    "beats estimates": 1.8,
    "raises guidance": 1.9,
    "raised guidance": 1.9,
    "guidance raised": 1.8,
    "upgrade": 1.2,
    "upgraded": 1.2,
    "record revenue": 1.5,
    "strong demand": 1.2,
    "margin expansion": 1.4,
    "expanding margin": 1.4,
    "profit growth": 1.4,
    "cash flow improved": 1.3,
    "debt reduction": 1.3,
    "deleveraging": 1.2,
    "buyback": 1.0,
}

NEGATIVE_LEXICON: dict[str, float] = {
    "miss estimates": 1.8,
    "missed estimates": 1.8,
    "cuts guidance": 1.9,
    "cut guidance": 1.9,
    "guidance cut": 1.8,
    "downgrade": 1.2,
    "downgraded": 1.2,
    "profit warning": 1.8,
    "margin pressure": 1.4,
    "margin contraction": 1.5,
    "weak demand": 1.2,
    "liquidity concern": 1.6,
    "cash burn": 1.5,
    "debt maturity risk": 1.7,
    "covenant breach": 2.2,
    "default risk": 2.2,
    "bankruptcy": 2.5,
    "trading halt": 1.2,
}

WS_RE = re.compile(r"\s+")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TICKER_PATTERNS = [
    re.compile(r"\$([A-Z]{1,6})\b"),
    re.compile(r"\b(?:NYSE|NASDAQ|ASX|LSE|TSX|HKEX|TSE)\s*[:\-]\s*([A-Z]{1,6})\b"),
    re.compile(r"\(([A-Z]{1,6})\.[A-Z]{1,4}\)"),
    re.compile(r"\b([A-Z]{1,6})\.[A-Z]{1,4}\b"),
]
TICKER_STOPWORDS = {
    "CEO",
    "CFO",
    "EPS",
    "USD",
    "GDP",
    "ETF",
    "IPO",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
}
STRICT_TICKER_STOPWORDS = {
    "BANK",
    "BANKS",
    "ENERGY",
    "NAMED",
    "OPTION",
    "OPTIONS",
    "STOCK",
    "STOCKS",
}
_TICKER_IDENTITY_MAP_CACHE: frozenset[str] | None = None

EVENT_FAMILY_RULES: dict[str, dict[str, Any]] = {
    "earnings_results": {
        "base_materiality": 0.8,
        "keywords": (
            "earnings",
            "results",
            "quarterly",
            "half year",
            "annual report",
            "revenue",
            "profit",
            "ebit",
            "ebitda",
            "margin",
        ),
    },
    "guidance_outlook": {
        "base_materiality": 0.82,
        "keywords": (
            "guidance",
            "outlook",
            "forecast",
            "expect",
            "reaffirm",
            "upgrade",
            "downgrade",
        ),
    },
    "capital_structure_balance_sheet": {
        "base_materiality": 0.86,
        "keywords": (
            "capital raise",
            "placement",
            "liquidity",
            "refinanc",
            "debt",
            "covenant",
            "cash burn",
            "buyback",
            "dividend",
            "balance sheet",
        ),
    },
    "contract_customer_demand": {
        "base_materiality": 0.7,
        "keywords": (
            "contract",
            "customer",
            "order",
            "agreement",
            "demand",
            "sales pipeline",
            "booking",
        ),
    },
    "operations_supply": {
        "base_materiality": 0.74,
        "keywords": (
            "operations",
            "production",
            "shipment",
            "supply",
            "outage",
            "delay",
            "mine",
            "plant",
            "factory",
        ),
    },
    "management_governance": {
        "base_materiality": 0.9,
        "keywords": (
            "ceo",
            "cfo",
            "board",
            "director",
            "chair",
            "management",
            "governance",
            "resign",
            "appoint",
        ),
    },
    "regulatory_legal": {
        "base_materiality": 0.92,
        "keywords": (
            "regulator",
            "regulatory",
            "legal",
            "court",
            "lawsuit",
            "investigation",
            "approval",
            "permit",
            "compliance",
            "penalty",
        ),
    },
    "m_and_a_corporate_actions": {
        "base_materiality": 0.78,
        "keywords": (
            "acquisition",
            "merger",
            "takeover",
            "scheme",
            "spin-off",
            "divest",
            "asset sale",
            "review",
        ),
    },
    "macro_sector": {
        "base_materiality": 0.52,
        "keywords": (
            "inflation",
            "interest rate",
            "commodity price",
            "sector",
            "macro",
            "rba",
            "policy",
        ),
    },
}
NEGATIVE_SHOCK_FAMILIES = {"management_governance", "regulatory_legal"}
DEFAULT_EVENT_FAMILY = "general_company_news"
CLUSTER_WINDOW_HOURS = 48.0
EMBEDDING_SIMILARITY_THRESHOLD = 0.74
LEXICAL_SIMILARITY_THRESHOLD = 0.2


@dataclass
class NewsArticle:
    article_key: str
    title: str
    source: str
    url: str
    published_at: str
    doc_date: str
    ticker_blob: str
    topic: str
    text: str
    article_lookup_key: str = ""
    company: str = ""
    corpus: str = ""
    ticker_relevance_json: str = ""
    embedding: tuple[float, ...] = field(default_factory=tuple)


@dataclass
class ArticleSentiment:
    article_key: str
    title: str
    source: str
    url: str
    published_at: str
    doc_date: str
    ticker_blob: str
    topic: str
    sentiment_score: float
    confidence: float
    positive_hits: int
    negative_hits: int
    signal_hits: int
    scorer: str
    article_lookup_key: str = ""
    corpus: str = ""


@dataclass
class TickerWindowSentiment:
    as_of_date: str
    ticker: str
    window_days: int
    article_count: int
    source_count: int
    weighted_sentiment: float
    score_0_100: float
    avg_confidence: float
    avg_signal_hits: float
    avg_article_age_days: float


@dataclass
class ArticleIntelligenceRow:
    article_lookup_key: str
    article_key: str
    ticker: str
    title: str
    source: str
    url: str
    published_at: str
    doc_date: str
    topic: str
    corpus: str
    sentiment_score: float
    sentiment_confidence: float
    event_family: str
    event_materiality: float
    relation_type: str
    relevance_score: float
    cluster_id: str = ""
    cluster_similarity: float = 0.0
    ret_1d: float | None = None
    ret_3d: float | None = None
    ret_5d: float | None = None
    abs_ret_1d: float | None = None
    price_confirmation_score: float | None = None
    narrative_shock_flag: int = 0
    shock_severity: float = 0.0


@dataclass
class EventClusterRow:
    cluster_id: str
    ticker: str
    event_family: str
    cluster_sentiment: float
    cluster_materiality: float
    article_count: int
    source_count: int
    start_published_at: str
    end_published_at: str
    article_lookup_keys_json: str
    cluster_strength: float = 0.0


@dataclass
class IntelligenceTickerWindowRow:
    as_of_date: str
    ticker: str
    window_days: int
    article_count: int
    source_count: int
    weighted_sentiment: float
    dominant_event_types: str
    bullish_article_share: float
    bearish_article_share: float
    event_frequency: int
    source_diversity: float
    primary_company_share: float
    narrative_score_0_100: float
    narrative_shock_flag: int
    shock_type: str
    shock_severity: float


@dataclass
class AlphaEventStatRow:
    event_family: str
    window_days: int
    sample_size: int
    avg_ret: float
    median_ret: float
    avg_abs_ret: float
    win_rate: float
    pos_rate: float
    neg_rate: float
    avg_price_confirmation_score: float | None
    avg_materiality: float
    avg_sentiment: float
    shock_rate: float
    alpha_score: float
    confidence_score: float


@dataclass
class AlphaTickerEventStatRow:
    ticker: str
    event_family: str
    window_days: int
    sample_size: int
    avg_ret: float
    median_ret: float
    avg_abs_ret: float
    win_rate: float
    avg_price_confirmation_score: float | None
    avg_materiality: float
    avg_sentiment: float
    shock_rate: float
    alpha_score: float
    confidence_score: float


@dataclass
class AlphaArticlePredictionRow:
    article_lookup_key: str
    ticker: str
    event_family: str
    window_days: int
    prior_source: str
    expected_return: float
    expected_abs_return: float
    win_rate: float
    confidence_score: float
    alpha_score: float
    sample_size_used: int
    prediction_explanation_json: str


ALPHA_WINDOWS: tuple[tuple[int, str], ...] = (
    (1, "ret_1d"),
    (3, "ret_3d"),
    (5, "ret_5d"),
)
TICKER_ALPHA_MIN_SAMPLE_SIZE = 5
PREDICTION_MIN_SAMPLE_SIZE = 3


def normalize_space(value: Any) -> str:
    return WS_RE.sub(" ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def normalize_url(value: Any) -> str:
    txt = str(value or "").strip()
    if not txt:
        return ""
    return txt.replace(" ", "").rstrip("/")


def parse_ticker_blob(blob: str) -> list[str]:
    raw = str(blob or "").strip()
    if not raw:
        return []
    if "|" in raw:
        parts = [p for p in raw.split("|") if p.strip()]
    else:
        parts = [p for p in re.split(r"[,\s;/]+", raw) if p.strip()]
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        token = re.sub(r"[^A-Za-z0-9.\-]", "", part.strip().upper())
        if not token or len(token) > 12:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def normalize_ticker_symbol(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9.\-]", "", str(value or "").strip().upper())
    if not token or len(token) > 12:
        return ""
    return token


def serialize_tickers(values: Sequence[str]) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = normalize_ticker_symbol(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    out.sort()
    if not out:
        return ""
    return "|" + "|".join(out) + "|"


def infer_ticker_blob(title: str, text: str, *, existing_blob: str, company_fallback: str) -> str:
    existing = parse_ticker_blob(existing_blob)
    seen: set[str] = set(existing)
    out: list[str] = list(existing)

    company = normalize_ticker_symbol(company_fallback)
    if company and company not in {"NEWS"} and 2 <= len(company) <= 6 and company not in seen:
        seen.add(company)
        out.append(company)

    probe = f"{title} {text}".upper()
    for pattern in TICKER_PATTERNS:
        for match in pattern.findall(probe):
            token = normalize_ticker_symbol(match)
            if not token or token in TICKER_STOPWORDS or token in seen:
                continue
            seen.add(token)
            out.append(token)
    return serialize_tickers(out)


def _parse_iso_date(value: str) -> dt.date | None:
    txt = str(value or "").strip()
    if not txt:
        return None
    if len(txt) >= 10 and DATE_RE.fullmatch(txt[:10]):
        try:
            return dt.date.fromisoformat(txt[:10])
        except ValueError:
            return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(txt)
    except ValueError:
        return None
    return parsed.date()


def parse_windows(raw: str) -> list[int]:
    values: list[int] = []
    seen: set[int] = set()
    for token in re.split(r"[,\s]+", str(raw or "").strip()):
        if not token:
            continue
        value = int(token)
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        values.append(value)
    values.sort()
    if not values:
        raise ValueError("At least one positive window is required.")
    return values


def _ticker_identity_map_paths() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[1]
    return (
        root / "config" / "ticker_identity_map.json",
        root / "financial-engine_v2" / "config" / "ticker_identity_map.json",
    )


def _ticker_identity_whitelist() -> frozenset[str]:
    global _TICKER_IDENTITY_MAP_CACHE
    if _TICKER_IDENTITY_MAP_CACHE is not None:
        return _TICKER_IDENTITY_MAP_CACHE
    for path in _ticker_identity_map_paths():
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        whitelist = frozenset(
            token
            for raw_ticker in payload.keys()
            for token in [normalize_ticker_symbol(str(raw_ticker or ""))]
            if token and token not in STRICT_TICKER_STOPWORDS
        )
        if whitelist:
            _TICKER_IDENTITY_MAP_CACHE = whitelist
            return whitelist
    raise RuntimeError(
        "DATA_MISSING: ticker identity map not found at config/ticker_identity_map.json"
    )


def _filter_whitelisted_tickers(values: Sequence[str]) -> list[str]:
    whitelist = _ticker_identity_whitelist()
    out: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        ticker = normalize_ticker_symbol(raw_value)
        if not ticker or ticker in seen:
            continue
        if ticker in STRICT_TICKER_STOPWORDS:
            continue
        if ticker not in whitelist:
            continue
        seen.add(ticker)
        out.append(ticker)
    return out


def sqlite_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(row[1]) for row in rows]


def _article_lookup_key_from_chunk_id(chunk_id: str) -> str:
    text = str(chunk_id or "").strip()
    if not text:
        return ""
    parts = text.split(":")
    if len(parts) >= 4 and parts[-2].isdigit():
        return ":".join(parts[:-2])
    if len(parts) >= 2 and parts[-1].isdigit():
        return ":".join(parts[:-1])
    return text


def _article_key(url: str, title: str, published_at: str, doc_date: str, ticker_blob: str, source: str) -> str:
    if url:
        seed = f"url:{url.lower()}"
    else:
        seed = "|".join(
            [
                normalize_space(title).lower(),
                str(published_at or "").strip(),
                str(doc_date or "").strip(),
                str(ticker_blob or "").strip(),
                normalize_space(source).lower(),
            ]
        )
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:24]


def _safe_date_for_sort(published_at: str, doc_date: str) -> str:
    d = _parse_iso_date(published_at) or _parse_iso_date(doc_date)
    return d.isoformat() if d else ""


def _parse_iso_datetime(value: str) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _parse_ticker_relevance_json(raw_value: Any) -> dict[str, dict[str, Any]]:
    raw = str(raw_value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for raw_ticker, raw_row in parsed.items():
        ticker = normalize_ticker_symbol(str(raw_ticker or ""))
        if not ticker or not isinstance(raw_row, dict):
            continue
        out[ticker] = dict(raw_row)
    return out


def _merge_ticker_relevance_maps(
    current: dict[str, dict[str, Any]],
    incoming: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out = {key: dict(value) for key, value in current.items()}
    for ticker, row in incoming.items():
        existing = out.get(ticker)
        if existing is None:
            out[ticker] = dict(row)
            continue
        current_score = _safe_float(existing.get("score")) or 0.0
        incoming_score = _safe_float(row.get("score")) or 0.0
        if incoming_score > current_score:
            out[ticker] = dict(row)
            continue
        if bool(row.get("primary")) and not bool(existing.get("primary")):
            existing["primary"] = True
        if not existing.get("label") and row.get("label"):
            existing["label"] = row.get("label")
    return out


def _serialize_ticker_relevance_map(rows: dict[str, dict[str, Any]]) -> str:
    if not rows:
        return ""
    return json.dumps(rows, ensure_ascii=False, sort_keys=True)


def _parse_embedding_json(raw_value: Any) -> tuple[float, ...]:
    raw = str(raw_value or "").strip()
    if not raw:
        return ()
    try:
        parsed = json.loads(raw)
    except Exception:
        return ()
    if not isinstance(parsed, list):
        return ()
    vector: list[float] = []
    for item in parsed:
        value = _safe_float(item)
        if value is None:
            return ()
        vector.append(float(value))
    return tuple(vector)


def _normalize_vector(values: Sequence[float]) -> tuple[float, ...]:
    norm = math.sqrt(sum(float(item) * float(item) for item in values))
    if norm <= 0:
        return ()
    return tuple(float(item) / norm for item in values)


def _average_vectors(vectors: Sequence[Sequence[float]]) -> tuple[float, ...]:
    rows = [tuple(float(item) for item in vector) for vector in vectors if vector]
    if not rows:
        return ()
    dim = len(rows[0])
    if dim <= 0:
        return ()
    accum = [0.0] * dim
    count = 0
    for row in rows:
        if len(row) != dim:
            continue
        for idx, value in enumerate(row):
            accum[idx] += float(value)
        count += 1
    if count <= 0:
        return ()
    return _normalize_vector([value / float(count) for value in accum])


def _cosine_similarity(lhs: Sequence[float], rhs: Sequence[float]) -> float | None:
    if not lhs or not rhs or len(lhs) != len(rhs):
        return None
    dot = sum(float(a) * float(b) for a, b in zip(lhs, rhs))
    lhs_norm = math.sqrt(sum(float(a) * float(a) for a in lhs))
    rhs_norm = math.sqrt(sum(float(b) * float(b) for b in rhs))
    if lhs_norm <= 0 or rhs_norm <= 0:
        return None
    return float(dot / (lhs_norm * rhs_norm))


def _lexical_similarity(lhs: str, rhs: str) -> float:
    lhs_tokens = {token for token in re.findall(r"[A-Za-z0-9]{4,}", str(lhs or "").lower())}
    rhs_tokens = {token for token in re.findall(r"[A-Za-z0-9]{4,}", str(rhs or "").lower())}
    if not lhs_tokens or not rhs_tokens:
        return 0.0
    return float(len(lhs_tokens & rhs_tokens)) / float(len(lhs_tokens | rhs_tokens))


def _semantic_similarity(
    *,
    lhs_vector: Sequence[float],
    rhs_vector: Sequence[float],
    lhs_text: str,
    rhs_text: str,
) -> float:
    cosine = _cosine_similarity(lhs_vector, rhs_vector)
    if cosine is not None:
        return cosine
    return _lexical_similarity(lhs_text, rhs_text)


def _count_phrase_hits(text: str, keywords: Sequence[str]) -> int:
    lowered = f" {str(text or '').lower()} "
    count = 0
    for phrase in keywords:
        token = normalize_space(phrase).lower()
        if not token:
            continue
        if " " in token:
            count += lowered.count(token)
        else:
            count += len(re.findall(rf"\b{re.escape(token)}\b", lowered))
    return count


def classify_event_family(
    *,
    title: str,
    text: str,
    topic: str,
    relation_type: str,
    relevance_score: float,
    sentiment_score: float,
) -> tuple[str, float]:
    title_text = normalize_space(title).lower()
    body_text = normalize_space(text).lower()
    topic_text = normalize_space(topic).lower()
    best_family = DEFAULT_EVENT_FAMILY
    best_score = 0.0
    best_materiality = 0.35
    for family, rule in EVENT_FAMILY_RULES.items():
        keywords = tuple(str(item) for item in rule.get("keywords") or ())
        title_hits = _count_phrase_hits(title_text, keywords)
        body_hits = _count_phrase_hits(body_text, keywords)
        topic_hits = _count_phrase_hits(topic_text, keywords)
        family_score = (title_hits * 1.8) + float(body_hits) + (topic_hits * 0.8)
        if family_score <= best_score:
            continue
        best_score = family_score
        best_family = family
        base_materiality = float(rule.get("base_materiality") or 0.35)
        relation_bonus = {
            "primary_company": 0.16,
            "company_context": 0.08,
            "sector_context": 0.04,
            "mention": 0.02,
        }.get(str(relation_type or "").strip().lower(), 0.0)
        best_materiality = min(
            1.0,
            base_materiality
            + (0.08 * min(3, title_hits))
            + (0.04 * min(5, body_hits))
            + relation_bonus
            + (0.12 * max(0.0, float(relevance_score)))
            + (0.05 * abs(float(sentiment_score))),
        )
    if best_family == DEFAULT_EVENT_FAMILY:
        fallback_materiality = 0.28 + (0.12 * max(0.0, float(relevance_score))) + (0.06 * abs(float(sentiment_score)))
        return DEFAULT_EVENT_FAMILY, float(min(0.7, fallback_materiality))
    return best_family, float(best_materiality)


def _choose_price_range(earliest_day: dt.date | None) -> str:
    if earliest_day is None:
        return "1y"
    age_days = (dt.datetime.now(dt.timezone.utc).date() - earliest_day).days
    if age_days <= 35:
        return "3mo"
    if age_days <= 120:
        return "6mo"
    if age_days <= 370:
        return "1y"
    if age_days <= 740:
        return "2y"
    if age_days <= 1850:
        return "5y"
    if age_days <= 3650:
        return "10y"
    return "max"


def load_news_articles_from_sqlite(
    *,
    db_path: Path,
    doc_type_filter: str,
    min_text_chars: int,
    max_article_chars: int,
    max_articles: int,
) -> list[NewsArticle]:
    if not db_path.exists() or not db_path.is_file():
        raise FileNotFoundError(f"News DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cols = set(sqlite_columns(cur, "context_chunks"))
        if "text" not in cols:
            raise RuntimeError("context_chunks.text column is required")
        select_parts = []
        for col in (
            "chunk_id",
            "title",
            "source",
            "url",
            "published_at",
            "doc_date",
            "ticker",
            "topic",
            "company",
            "corpus",
            "ticker_relevance_json",
            "embedding_json",
            "text",
        ):
            if col in cols:
                select_parts.append(col)
            else:
                select_parts.append(f"'' AS {col}")
        where_parts: list[str] = []
        args: list[str] = []
        if "corpus" in cols:
            where_parts.append("corpus LIKE ?")
            args.append("news%")
        if doc_type_filter and "doc_type" in cols:
            where_parts.append("doc_type = ?")
            args.append(doc_type_filter)

        sql = f"SELECT {', '.join(select_parts)} FROM context_chunks"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        rows = cur.execute(sql, args).fetchall()
    finally:
        conn.close()

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        (
            chunk_id,
            title,
            source,
            url,
            published_at,
            doc_date,
            ticker_blob,
            topic,
            company,
            corpus,
            ticker_relevance_json,
            embedding_json,
            text,
        ) = [str(item or "") for item in row]
        clean_text = normalize_space(text)
        if len(clean_text) < max(1, int(min_text_chars)):
            continue
        clean_url = normalize_url(url)
        legacy_key = _article_key(
            url=clean_url,
            title=title,
            published_at=published_at,
            doc_date=doc_date,
            ticker_blob=ticker_blob,
            source=source,
        )
        lookup_key = _article_lookup_key_from_chunk_id(chunk_id) or legacy_key
        payload = grouped.get(lookup_key)
        if payload is None:
            payload = {
                "article_key": legacy_key,
                "article_lookup_key": lookup_key,
                "title": normalize_space(title),
                "source": normalize_space(source),
                "url": clean_url,
                "published_at": str(published_at or "").strip(),
                "doc_date": str(doc_date or "").strip(),
                "ticker_blob": str(ticker_blob or "").strip(),
                "topic": normalize_space(topic),
                "company": normalize_ticker_symbol(company),
                "corpus": str(corpus or "").strip(),
                "ticker_relevance_map": _parse_ticker_relevance_json(ticker_relevance_json),
                "parts": [],
                "part_keys": set(),
                "embeddings": [],
            }
            grouped[lookup_key] = payload
        else:
            payload["ticker_relevance_map"] = _merge_ticker_relevance_maps(
                payload.get("ticker_relevance_map", {}),
                _parse_ticker_relevance_json(ticker_relevance_json),
            )

        part_key = hashlib.sha1(clean_text.encode("utf-8")).hexdigest()[:16]
        if part_key in payload["part_keys"]:
            continue
        payload["part_keys"].add(part_key)
        payload["parts"].append(clean_text)
        vector = _parse_embedding_json(embedding_json)
        if vector:
            payload["embeddings"].append(vector)

    articles: list[NewsArticle] = []
    for payload in grouped.values():
        parts = payload.get("parts", [])
        merged = normalize_space(" ".join(str(part) for part in parts))
        merged = merged[: max(1, int(max_article_chars))]
        if len(merged) < max(1, int(min_text_chars)):
            continue
        ticker_blob = infer_ticker_blob(
            title=str(payload.get("title", "")),
            text=merged,
            existing_blob=str(payload.get("ticker_blob", "")),
            company_fallback=str(payload.get("company", "")),
        )
        ticker_relevance_map = payload.get("ticker_relevance_map", {})
        articles.append(
            NewsArticle(
                article_key=str(payload.get("article_key", "")),
                article_lookup_key=str(payload.get("article_lookup_key", "")),
                title=str(payload.get("title", "")),
                source=str(payload.get("source", "")),
                url=str(payload.get("url", "")),
                published_at=str(payload.get("published_at", "")),
                doc_date=str(payload.get("doc_date", "")),
                ticker_blob=ticker_blob,
                topic=str(payload.get("topic", "")),
                text=merged,
                company=str(payload.get("company", "")),
                corpus=str(payload.get("corpus", "")),
                ticker_relevance_json=_serialize_ticker_relevance_map(
                    ticker_relevance_map if isinstance(ticker_relevance_map, dict) else {}
                ),
                embedding=_average_vectors(payload.get("embeddings", [])),
            )
        )

    articles.sort(key=lambda row: _safe_date_for_sort(row.published_at, row.doc_date), reverse=True)
    if max_articles > 0:
        return articles[: max_articles]
    return articles


def _count_weighted_hits(text: str, lexicon: dict[str, float]) -> tuple[float, int]:
    lowered = f" {str(text or '').lower()} "
    total_weight = 0.0
    hit_count = 0
    for term, weight in lexicon.items():
        if " " in term:
            count = lowered.count(term)
        else:
            count = len(re.findall(rf"\b{re.escape(term)}\b", lowered))
        if count <= 0:
            continue
        total_weight += float(weight) * float(count)
        hit_count += int(count)
    return total_weight, hit_count


def score_article_lexical(article: NewsArticle) -> ArticleSentiment:
    title = normalize_space(article.title)
    body = normalize_space(article.text)
    text = f"{title}. {body}".strip()
    pos_weight, pos_hits = _count_weighted_hits(text, POSITIVE_LEXICON)
    neg_weight, neg_hits = _count_weighted_hits(text, NEGATIVE_LEXICON)

    denom = pos_weight + neg_weight + 2.5
    raw = 0.0 if denom <= 0 else (pos_weight - neg_weight) / denom
    score = max(-1.0, min(1.0, raw))

    signal_hits = pos_hits + neg_hits
    length_factor = min(1.0, len(text) / 1600.0)
    confidence = min(0.95, 0.18 + 0.07 * min(8, signal_hits) + 0.2 * length_factor)
    confidence = max(0.05, confidence)

    return ArticleSentiment(
        article_key=article.article_key,
        article_lookup_key=article.article_lookup_key,
        title=article.title,
        source=article.source,
        url=article.url,
        published_at=article.published_at,
        doc_date=article.doc_date,
        ticker_blob=article.ticker_blob,
        topic=article.topic,
        sentiment_score=float(score),
        confidence=float(confidence),
        positive_hits=int(pos_hits),
        negative_hits=int(neg_hits),
        signal_hits=int(signal_hits),
        scorer="lexical",
        corpus=article.corpus,
    )


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def _score_article_with_ollama(
    article: NewsArticle,
    *,
    endpoint: str,
    model: str,
    timeout_seconds: float,
) -> ArticleSentiment:
    prompt = (
        "You score financial news sentiment.\n"
        "Return strict JSON with keys sentiment and confidence only.\n"
        "sentiment: float in [-1,1], confidence: float in [0,1].\n"
        "Title: "
        + normalize_space(article.title)
        + "\nText: "
        + normalize_space(article.text)[:1800]
    )
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/api/generate",
        data=json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=max(1.0, float(timeout_seconds))) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    raw = payload.get("response")
    if not isinstance(raw, str):
        raise RuntimeError("ollama response missing JSON string in `response`")
    parsed = json.loads(raw)
    sentiment = _safe_float(parsed.get("sentiment"))
    confidence = _safe_float(parsed.get("confidence"))
    if sentiment is None:
        raise RuntimeError("ollama response missing numeric `sentiment`")
    if confidence is None:
        confidence = 0.5
    sentiment = max(-1.0, min(1.0, sentiment))
    confidence = max(0.05, min(0.95, confidence))

    return ArticleSentiment(
        article_key=article.article_key,
        article_lookup_key=article.article_lookup_key,
        title=article.title,
        source=article.source,
        url=article.url,
        published_at=article.published_at,
        doc_date=article.doc_date,
        ticker_blob=article.ticker_blob,
        topic=article.topic,
        sentiment_score=float(sentiment),
        confidence=float(confidence),
        positive_hits=0,
        negative_hits=0,
        signal_hits=0,
        scorer=f"ollama:{model}",
        corpus=article.corpus,
    )


def score_articles(
    articles: Sequence[NewsArticle],
    *,
    scorer: str,
    ollama_endpoint: str,
    ollama_model: str,
    ollama_timeout_seconds: float,
) -> tuple[list[ArticleSentiment], int]:
    scored: list[ArticleSentiment] = []
    fallback_count = 0
    for article in articles:
        if scorer == "ollama":
            try:
                scored.append(
                    _score_article_with_ollama(
                        article,
                        endpoint=ollama_endpoint,
                        model=ollama_model,
                        timeout_seconds=ollama_timeout_seconds,
                    )
                )
                continue
            except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError):
                fallback_count += 1
        scored.append(score_article_lexical(article))
    return scored, fallback_count


def aggregate_ticker_windows(
    *,
    article_scores: Sequence[ArticleSentiment],
    as_of_date: dt.date,
    windows: Sequence[int],
    half_life_days: float,
    ticker_filter: str,
) -> list[TickerWindowSentiment]:
    normalized_filter = re.sub(r"[^A-Za-z0-9.\-]", "", str(ticker_filter or "").strip().upper())
    payload: dict[tuple[str, int], dict[str, Any]] = {}
    hl = max(0.1, float(half_life_days))

    for row in article_scores:
        article_day = _parse_iso_date(row.published_at) or _parse_iso_date(row.doc_date)
        if article_day is None:
            continue
        age_days = (as_of_date - article_day).days
        if age_days < 0:
            age_days = 0
        tickers = parse_ticker_blob(row.ticker_blob)
        if not tickers:
            continue
        for ticker in tickers:
            if normalized_filter and ticker != normalized_filter:
                continue
            for window in windows:
                if age_days > int(window):
                    continue
                key = (ticker, int(window))
                acc = payload.get(key)
                if acc is None:
                    acc = {
                        "article_count": 0,
                        "weighted_sum": 0.0,
                        "weight_sum": 0.0,
                        "confidence_sum": 0.0,
                        "signal_hits_sum": 0.0,
                        "age_days_sum": 0.0,
                        "sources": set(),
                    }
                    payload[key] = acc
                recency_weight = math.exp(-(math.log(2.0) / hl) * float(age_days))
                weight = max(0.05, float(row.confidence)) * recency_weight
                acc["article_count"] += 1
                acc["weighted_sum"] += float(row.sentiment_score) * weight
                acc["weight_sum"] += weight
                acc["confidence_sum"] += max(0.0, float(row.confidence))
                acc["signal_hits_sum"] += max(0.0, float(row.signal_hits))
                acc["age_days_sum"] += float(age_days)
                source = normalize_space(row.source).lower()
                if source:
                    acc["sources"].add(source)

    out: list[TickerWindowSentiment] = []
    for (ticker, window), acc in payload.items():
        weight_sum = float(acc["weight_sum"])
        article_count = int(acc["article_count"])
        if article_count <= 0:
            continue
        weighted = 0.0 if weight_sum <= 0 else float(acc["weighted_sum"]) / weight_sum
        weighted = max(-1.0, min(1.0, weighted))
        score_0_100 = (weighted + 1.0) * 50.0
        avg_conf = float(acc["confidence_sum"]) / float(article_count)
        avg_hits = float(acc["signal_hits_sum"]) / float(article_count)
        avg_age = float(acc["age_days_sum"]) / float(article_count)
        out.append(
            TickerWindowSentiment(
                as_of_date=as_of_date.isoformat(),
                ticker=ticker,
                window_days=int(window),
                article_count=article_count,
                source_count=len(acc["sources"]),
                weighted_sentiment=float(round(weighted, 6)),
                score_0_100=float(round(score_0_100, 3)),
                avg_confidence=float(round(avg_conf, 6)),
                avg_signal_hits=float(round(avg_hits, 6)),
                avg_article_age_days=float(round(avg_age, 6)),
            )
        )
    out.sort(key=lambda row: (row.ticker, row.window_days))
    return out


def _relation_signal_for_ticker(article: NewsArticle, ticker: str) -> tuple[str, float]:
    relevance_map = _parse_ticker_relevance_json(article.ticker_relevance_json)
    row = relevance_map.get(ticker)
    if isinstance(row, dict):
        relation_type = str(row.get("label") or "").strip().lower() or "mention"
        relevance_score = _safe_float(row.get("score")) or 0.0
        return relation_type, float(max(0.0, min(1.0, relevance_score)))
    company = normalize_ticker_symbol(article.company)
    article_tickers = parse_ticker_blob(article.ticker_blob)
    if company and company == ticker:
        return "primary_company", 0.55
    if ticker in article_tickers and len(article_tickers) <= 1:
        return "company_context", 0.42
    if ticker in article_tickers:
        return "mention", 0.22
    return "mention", 0.0


def _article_tickers_for_intelligence(article: NewsArticle) -> list[str]:
    relevance_map = _parse_ticker_relevance_json(article.ticker_relevance_json)
    candidates = sorted(relevance_map.keys()) if relevance_map else []
    company = normalize_ticker_symbol(article.company)
    if company and company != "NEWS":
        candidates.append(company)
    return _filter_whitelisted_tickers(candidates)


def _fetch_price_payload(
    *,
    base_url: str,
    ticker: str,
    range_: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "ticker": ticker,
            "exchange": "ASX",
            "range": range_,
            "interval": "1d",
        }
    )
    url = base_url.rstrip("/") + "/api/price?" + query
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=max(1.0, float(timeout_seconds))) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"DATA_MISSING: invalid price payload for {ticker}")
    return payload


def _load_price_history_by_ticker(
    *,
    tickers: Sequence[str],
    earliest_day: dt.date | None,
    base_url: str,
    timeout_seconds: float,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    if not tickers:
        return out
    if not str(base_url or "").strip():
        raise RuntimeError("DATA_MISSING: price API base URL is required for price reaction analytics")
    range_value = _choose_price_range(earliest_day)
    skipped_tickers: list[tuple[str, str]] = []
    normalized_tickers = sorted({normalize_ticker_symbol(item) for item in tickers if normalize_ticker_symbol(item)})
    for ticker in normalized_tickers:
        try:
            payload = _fetch_price_payload(
                base_url=base_url,
                ticker=ticker,
                range_=range_value,
                timeout_seconds=timeout_seconds,
            )
            history = payload.get("history")
            if not isinstance(history, list):
                raise RuntimeError(f"missing history rows for {ticker}")
            clean_rows = [row for row in history if isinstance(row, dict)]
            if not clean_rows:
                raise RuntimeError(f"empty history rows for {ticker}")
            out[ticker] = clean_rows
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, TimeoutError) as exc:
            skipped_tickers.append((ticker, str(exc)))
            print(
                f"[build_news_sentiment_features] price history skipped for {ticker}: {str(exc)[:200]}",
                file=sys.stderr,
                flush=True,
            )
    if normalized_tickers and not out:
        raise RuntimeError(
            "DATA_MISSING: unable to load price history for any ticker from the configured price API"
        )
    if skipped_tickers:
        print(
            f"[build_news_sentiment_features] price history loaded for {len(out)}/{len(normalized_tickers)} tickers",
            file=sys.stderr,
            flush=True,
        )
    return out


def _prepare_price_series(history_rows: Sequence[dict[str, Any]]) -> list[tuple[dt.date, float]]:
    deduped: dict[str, tuple[dt.date, float]] = {}
    for row in history_rows:
        if not isinstance(row, dict):
            continue
        value = _safe_float(row.get("close"))
        if value is None:
            continue
        day = _parse_iso_date(str(row.get("timestamp") or ""))
        if day is None:
            continue
        deduped[day.isoformat()] = (day, float(value))
    ordered = sorted(deduped.values(), key=lambda item: item[0].isoformat())
    return ordered


def _warn_price_data_unavailable(ticker: str, warned_tickers: set[str]) -> None:
    if ticker in warned_tickers:
        return
    warned_tickers.add(ticker)
    print(f"Price data unavailable for ticker {ticker}", file=sys.stderr, flush=True)


def _window_half_life_days(base_half_life_days: float, window_days: int) -> float:
    if int(window_days) == 7:
        return max(0.1, float(base_half_life_days) * 0.5)
    return max(0.1, float(base_half_life_days))


def _compute_price_reaction(
    *,
    article_day: dt.date | None,
    sentiment_score: float,
    price_rows: Sequence[dict[str, Any]],
) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    if article_day is None:
        return None, None, None, None, None
    series = _prepare_price_series(price_rows)
    if len(series) < 2:
        return None, None, None, None, None
    baseline_idx = -1
    for idx, (day, _close) in enumerate(series):
        if day <= article_day:
            baseline_idx = idx
        else:
            break
    if baseline_idx < 0:
        return None, None, None, None, None
    base = series[baseline_idx][1]
    if base == 0:
        return None, None, None, None, None

    def _ret(offset: int) -> float | None:
        target_idx = baseline_idx + offset
        if target_idx >= len(series):
            return None
        return ((series[target_idx][1] / base) - 1.0) * 100.0

    ret_1d = _ret(1)
    ret_3d = _ret(3)
    ret_5d = _ret(5)
    abs_ret_1d = abs(ret_1d) if ret_1d is not None else None
    polarity = 1.0 if sentiment_score > 0.08 else (-1.0 if sentiment_score < -0.08 else 0.0)
    confirmation_score = None
    if polarity != 0.0:
        weighted = 0.0
        total_weight = 0.0
        for value, weight in ((ret_1d, 0.5), (ret_3d, 0.3), (ret_5d, 0.2)):
            if value is None:
                continue
            weighted += max(-1.0, min(1.0, float(value) / 5.0)) * weight
            total_weight += weight
        if total_weight > 0:
            confirmation_score = max(-1.0, min(1.0, (weighted / total_weight) * polarity))
    return ret_1d, ret_3d, ret_5d, abs_ret_1d, confirmation_score


def build_article_intelligence_rows(
    *,
    articles: Sequence[NewsArticle],
    article_scores: Sequence[ArticleSentiment],
    price_history_by_ticker: dict[str, list[dict[str, Any]]],
    ticker_filter: str = "",
) -> list[ArticleIntelligenceRow]:
    article_by_key = {row.article_key: row for row in articles}
    normalized_filter = normalize_ticker_symbol(ticker_filter)
    out: list[ArticleIntelligenceRow] = []
    warned_tickers: set[str] = set()
    for score in article_scores:
        article = article_by_key.get(score.article_key)
        if article is None:
            continue
        tickers = _article_tickers_for_intelligence(article)
        if not tickers:
            continue
        article_day = _parse_iso_date(article.published_at) or _parse_iso_date(article.doc_date)
        for ticker in tickers:
            if normalized_filter and ticker != normalized_filter:
                continue
            relation_type, relevance_score = _relation_signal_for_ticker(article, ticker)
            event_family, event_materiality = classify_event_family(
                title=article.title,
                text=article.text,
                topic=article.topic,
                relation_type=relation_type,
                relevance_score=relevance_score,
                sentiment_score=score.sentiment_score,
            )
            price_rows = price_history_by_ticker.get(ticker, [])
            ret_1d, ret_3d, ret_5d, abs_ret_1d, confirmation_score = _compute_price_reaction(
                article_day=article_day,
                sentiment_score=score.sentiment_score,
                price_rows=price_rows,
            )
            if not price_rows or (article_day is not None and all(
                value is None for value in (ret_1d, ret_3d, ret_5d, abs_ret_1d, confirmation_score)
            )):
                _warn_price_data_unavailable(ticker, warned_tickers)
            out.append(
                ArticleIntelligenceRow(
                    article_lookup_key=article.article_lookup_key or article.article_key,
                    article_key=article.article_key,
                    ticker=ticker,
                    title=article.title,
                    source=article.source,
                    url=article.url,
                    published_at=article.published_at,
                    doc_date=article.doc_date,
                    topic=article.topic,
                    corpus=article.corpus,
                    sentiment_score=float(score.sentiment_score),
                    sentiment_confidence=float(score.confidence),
                    event_family=event_family,
                    event_materiality=float(event_materiality),
                    relation_type=relation_type,
                    relevance_score=float(relevance_score),
                    ret_1d=ret_1d,
                    ret_3d=ret_3d,
                    ret_5d=ret_5d,
                    abs_ret_1d=abs_ret_1d,
                    price_confirmation_score=confirmation_score,
                )
            )
    out.sort(key=lambda row: (row.ticker, row.published_at, row.article_lookup_key))
    return out


def build_event_clusters(
    *,
    article_rows: Sequence[ArticleIntelligenceRow],
    articles: Sequence[NewsArticle],
) -> list[EventClusterRow]:
    article_lookup = {row.article_lookup_key: row for row in articles}
    grouped: dict[tuple[str, str], list[ArticleIntelligenceRow]] = {}
    for row in article_rows:
        grouped.setdefault((row.ticker, row.event_family), []).append(row)

    cluster_rows: list[EventClusterRow] = []
    for (ticker, event_family), rows in grouped.items():
        rows.sort(key=lambda item: (item.published_at, item.article_lookup_key))
        clusters: list[dict[str, Any]] = []
        for row in rows:
            article = article_lookup.get(row.article_lookup_key)
            row_dt = _parse_iso_datetime(row.published_at) or (
                dt.datetime.combine(_parse_iso_date(row.doc_date) or dt.date.min, dt.time.min, tzinfo=dt.timezone.utc)
                if _parse_iso_date(row.doc_date)
                else None
            )
            row_text = f"{row.title} {article.text if article is not None else ''}"
            row_vector = article.embedding if article is not None else ()
            best_cluster: dict[str, Any] | None = None
            best_similarity = -1.0
            for cluster in reversed(clusters):
                end_dt = cluster.get("end_dt")
                if row_dt is not None and isinstance(end_dt, dt.datetime):
                    hours_delta = abs((row_dt - end_dt).total_seconds()) / 3600.0
                    if hours_delta > CLUSTER_WINDOW_HOURS:
                        continue
                similarity = _semantic_similarity(
                    lhs_vector=row_vector,
                    rhs_vector=cluster.get("centroid_vector") or (),
                    lhs_text=row_text,
                    rhs_text=cluster.get("summary_text") or "",
                )
                threshold = EMBEDDING_SIMILARITY_THRESHOLD if row_vector and cluster.get("centroid_vector") else LEXICAL_SIMILARITY_THRESHOLD
                if similarity < threshold or similarity <= best_similarity:
                    continue
                best_similarity = similarity
                best_cluster = cluster

            if best_cluster is None:
                cluster_id = hashlib.sha1(
                    f"{ticker}|{event_family}|{row.article_lookup_key}".encode("utf-8")
                ).hexdigest()[:24]
                best_cluster = {
                    "cluster_id": cluster_id,
                    "ticker": ticker,
                    "event_family": event_family,
                    "article_lookup_keys": [],
                    "sources": set(),
                    "sentiment_weighted_sum": 0.0,
                    "sentiment_weight_sum": 0.0,
                    "materiality_sum": 0.0,
                    "max_materiality": 0.0,
                    "start_dt": row_dt,
                    "end_dt": row_dt,
                    "summary_text": row_text[:1800],
                    "vectors": [],
                    "centroid_vector": (),
                }
                clusters.append(best_cluster)
                row.cluster_similarity = 1.0
            else:
                row.cluster_similarity = float(best_similarity)

            best_cluster["article_lookup_keys"].append(row.article_lookup_key)
            source_key = normalize_space(row.source).lower()
            if source_key:
                best_cluster["sources"].add(source_key)
            sentiment_weight = max(0.05, row.sentiment_confidence) * max(0.2, row.relevance_score)
            best_cluster["sentiment_weighted_sum"] += float(row.sentiment_score) * sentiment_weight
            best_cluster["sentiment_weight_sum"] += sentiment_weight
            best_cluster["materiality_sum"] += float(row.event_materiality)
            best_cluster["max_materiality"] = max(best_cluster["max_materiality"], float(row.event_materiality))
            if row_dt is not None:
                if best_cluster.get("start_dt") is None or row_dt < best_cluster["start_dt"]:
                    best_cluster["start_dt"] = row_dt
                if best_cluster.get("end_dt") is None or row_dt > best_cluster["end_dt"]:
                    best_cluster["end_dt"] = row_dt
            if row_vector:
                best_cluster["vectors"].append(tuple(row_vector))
                best_cluster["centroid_vector"] = _average_vectors(best_cluster["vectors"])
            row.cluster_id = str(best_cluster["cluster_id"])

        for cluster in clusters:
            weight_sum = float(cluster.get("sentiment_weight_sum") or 0.0)
            cluster_sentiment = (
                float(cluster.get("sentiment_weighted_sum") or 0.0) / weight_sum if weight_sum > 0 else 0.0
            )
            article_count = len(cluster.get("article_lookup_keys") or [])
            source_count = len(cluster.get("sources") or [])
            avg_materiality = (
                float(cluster.get("materiality_sum") or 0.0) / float(article_count) if article_count > 0 else 0.0
            )
            cluster_strength = math.log(float(article_count) + 1.0) * float(source_count) * float(avg_materiality)
            cluster_rows.append(
                EventClusterRow(
                    cluster_id=str(cluster.get("cluster_id") or ""),
                    ticker=ticker,
                    event_family=event_family,
                    cluster_sentiment=float(max(-1.0, min(1.0, cluster_sentiment))),
                    cluster_materiality=float(cluster.get("max_materiality") or 0.0),
                    article_count=article_count,
                    source_count=source_count,
                    start_published_at=cluster.get("start_dt").isoformat().replace("+00:00", "Z")
                    if isinstance(cluster.get("start_dt"), dt.datetime)
                    else "",
                    end_published_at=cluster.get("end_dt").isoformat().replace("+00:00", "Z")
                    if isinstance(cluster.get("end_dt"), dt.datetime)
                    else "",
                    article_lookup_keys_json=json.dumps(cluster.get("article_lookup_keys") or [], ensure_ascii=False),
                    cluster_strength=float(round(cluster_strength, 6)),
                )
            )

    cluster_rows.sort(key=lambda row: (row.ticker, row.end_published_at, row.cluster_id))
    return cluster_rows


def annotate_article_narrative_shocks(*, article_rows: Sequence[ArticleIntelligenceRow]) -> None:
    grouped: dict[str, list[ArticleIntelligenceRow]] = {}
    for row in article_rows:
        grouped.setdefault(row.ticker, []).append(row)

    for rows in grouped.values():
        rows.sort(key=lambda item: (item.published_at, item.article_lookup_key))
        dated_rows = [
            (row, _parse_iso_date(row.published_at) or _parse_iso_date(row.doc_date))
            for row in rows
        ]
        for row, current_day in dated_rows:
            if current_day is None:
                row.narrative_shock_flag = 0
                row.shock_severity = 0.0
                continue
            recent_7 = [
                candidate
                for candidate, candidate_day in dated_rows
                if candidate_day is not None and 0 <= (current_day - candidate_day).days <= 7
            ]
            recent_30 = [
                candidate
                for candidate, candidate_day in dated_rows
                if candidate_day is not None and 0 <= (current_day - candidate_day).days <= 30
            ]
            if not recent_7 or not recent_30:
                row.narrative_shock_flag = 0
                row.shock_severity = 0.0
                continue

            def _window_sentiment(values: Sequence[ArticleIntelligenceRow]) -> float:
                weighted_sum = 0.0
                weight_sum = 0.0
                for candidate in values:
                    weight = max(0.05, float(candidate.sentiment_confidence))
                    weight *= max(0.2, float(candidate.relevance_score)) * (0.5 + float(candidate.event_materiality))
                    weighted_sum += float(candidate.sentiment_score) * weight
                    weight_sum += weight
                return (weighted_sum / weight_sum) if weight_sum > 0 else 0.0

            sentiment_7d = _window_sentiment(recent_7)
            sentiment_30d = _window_sentiment(recent_30)
            shift_severity = 0.0
            delta = abs(sentiment_7d - sentiment_30d)
            if delta >= 0.3:
                shift_severity = min(100.0, (delta / 0.75) * 100.0)

            cluster_ids_7d = {
                candidate.cluster_id or candidate.article_lookup_key
                for candidate in recent_7
                if (candidate.cluster_id or candidate.article_lookup_key)
            }
            cluster_ids_30d = {
                candidate.cluster_id or candidate.article_lookup_key
                for candidate in recent_30
                if (candidate.cluster_id or candidate.article_lookup_key)
            }
            density_severity = 0.0
            rate_7d = float(len(cluster_ids_7d)) / 7.0
            rate_30d = float(max(1, len(cluster_ids_30d))) / 30.0
            if rate_7d >= max(0.2, rate_30d * 1.8) and len(cluster_ids_7d) >= 2:
                density_severity = min(100.0, ((rate_7d / max(rate_30d, 0.1)) - 1.0) * 45.0)

            burst_count = sum(
                1
                for candidate in recent_7
                if candidate.event_family in NEGATIVE_SHOCK_FAMILIES
                and candidate.sentiment_score <= -0.1
                and candidate.event_materiality >= 0.6
            )
            burst_severity = 0.0
            if burst_count >= 2:
                burst_severity = min(100.0, 55.0 + ((burst_count - 2) * 15.0))

            shock_severity = max(burst_severity, shift_severity, density_severity)
            row.narrative_shock_flag = 1 if shock_severity >= 55.0 else 0
            row.shock_severity = float(round(shock_severity if row.narrative_shock_flag else 0.0, 3))


def _compute_narrative_score(
    *,
    weighted_sentiment: float,
    bullish_share: float,
    bearish_share: float,
    source_diversity: float,
    primary_company_share: float,
    event_frequency: int,
    shock_penalty: float,
) -> float:
    score = 50.0
    score += float(weighted_sentiment) * 26.0
    score += (float(bullish_share) - float(bearish_share)) * 14.0
    score += float(source_diversity) * 6.0
    score += float(primary_company_share) * 8.0
    score += min(10.0, float(event_frequency) * 1.5)
    score -= float(shock_penalty)
    return max(0.0, min(100.0, score))


def build_narrative_windows(
    *,
    article_rows: Sequence[ArticleIntelligenceRow],
    cluster_rows: Sequence[EventClusterRow],
    as_of_date: dt.date,
    windows: Sequence[int],
    half_life_days: float,
    ticker_filter: str,
) -> list[IntelligenceTickerWindowRow]:
    normalized_filter = normalize_ticker_symbol(ticker_filter)
    payload: dict[tuple[str, int], dict[str, Any]] = {}
    hl = max(0.1, float(half_life_days))

    for row in article_rows:
        if normalized_filter and row.ticker != normalized_filter:
            continue
        article_day = _parse_iso_date(row.published_at) or _parse_iso_date(row.doc_date)
        if article_day is None:
            continue
        age_days = (as_of_date - article_day).days
        if age_days < 0:
            age_days = 0
        for window in windows:
            if age_days > int(window):
                continue
            key = (row.ticker, int(window))
            acc = payload.get(key)
            if acc is None:
                acc = {
                    "article_count": 0,
                    "sources": set(),
                    "weighted_sum": 0.0,
                    "weight_sum": 0.0,
                    "bullish_count": 0,
                    "bearish_count": 0,
                    "event_weights": {},
                    "primary_weight": 0.0,
                    "cluster_ids": set(),
                    "shock_penalty": 0.0,
                }
                payload[key] = acc
            window_half_life = _window_half_life_days(hl, int(window))
            recency_weight = math.exp(-(math.log(2.0) / window_half_life) * float(age_days))
            weight = max(0.05, row.sentiment_confidence) * recency_weight
            weight *= max(0.2, row.relevance_score) * (0.5 + row.event_materiality)
            acc["article_count"] += 1
            acc["sources"].add(normalize_space(row.source).lower())
            acc["weighted_sum"] += float(row.sentiment_score) * weight
            acc["weight_sum"] += weight
            if row.sentiment_score >= 0.15:
                acc["bullish_count"] += 1
            if row.sentiment_score <= -0.15:
                acc["bearish_count"] += 1
            acc["event_weights"][row.event_family] = float(acc["event_weights"].get(row.event_family, 0.0)) + weight
            if row.relation_type == "primary_company":
                acc["primary_weight"] += weight
            if row.cluster_id:
                acc["cluster_ids"].add(row.cluster_id)

    out: list[IntelligenceTickerWindowRow] = []
    for (ticker, window), acc in payload.items():
        article_count = int(acc["article_count"])
        if article_count <= 0:
            continue
        weight_sum = float(acc["weight_sum"])
        weighted_sentiment = float(acc["weighted_sum"]) / weight_sum if weight_sum > 0 else 0.0
        event_weights = sorted(
            ((family, float(weight)) for family, weight in (acc.get("event_weights") or {}).items()),
            key=lambda item: (-item[1], item[0]),
        )
        dominant_event_types = json.dumps(
            [
                {"event_family": family, "weight": round(weight, 6)}
                for family, weight in event_weights[:3]
            ],
            ensure_ascii=False,
        )
        source_count = len([item for item in acc["sources"] if item])
        source_diversity = float(source_count) / float(article_count) if article_count > 0 else 0.0
        primary_company_share = float(acc["primary_weight"]) / weight_sum if weight_sum > 0 else 0.0
        bullish_share = float(acc["bullish_count"]) / float(article_count)
        bearish_share = float(acc["bearish_count"]) / float(article_count)
        event_frequency = len(acc["cluster_ids"])
        out.append(
            IntelligenceTickerWindowRow(
                as_of_date=as_of_date.isoformat(),
                ticker=ticker,
                window_days=int(window),
                article_count=article_count,
                source_count=source_count,
                weighted_sentiment=float(round(max(-1.0, min(1.0, weighted_sentiment)), 6)),
                dominant_event_types=dominant_event_types,
                bullish_article_share=float(round(bullish_share, 6)),
                bearish_article_share=float(round(bearish_share, 6)),
                event_frequency=int(event_frequency),
                source_diversity=float(round(source_diversity, 6)),
                primary_company_share=float(round(primary_company_share, 6)),
                narrative_score_0_100=0.0,
                narrative_shock_flag=0,
                shock_type="",
                shock_severity=0.0,
            )
        )

    rows_by_ticker: dict[str, dict[int, IntelligenceTickerWindowRow]] = {}
    for row in out:
        rows_by_ticker.setdefault(row.ticker, {})[int(row.window_days)] = row

    for ticker, window_map in rows_by_ticker.items():
        row_7d = window_map.get(7)
        row_30d = window_map.get(30)
        row_90d = window_map.get(90)
        shift_severity = 0.0
        if row_7d is not None and row_30d is not None:
            delta = abs(float(row_7d.weighted_sentiment) - float(row_30d.weighted_sentiment))
            if delta >= 0.3:
                shift_severity = min(100.0, (delta / 0.75) * 100.0)
        density_severity = 0.0
        if row_7d is not None and row_30d is not None:
            rate_7d = float(row_7d.event_frequency) / 7.0
            rate_30d = float(max(1, row_30d.event_frequency)) / 30.0
            if rate_7d >= max(0.2, rate_30d * 1.8) and row_7d.event_frequency >= 2:
                density_severity = min(100.0, ((rate_7d / max(rate_30d, 0.1)) - 1.0) * 45.0)
        burst_count = 0
        for row in article_rows:
            if row.ticker != ticker:
                continue
            article_day = _parse_iso_date(row.published_at) or _parse_iso_date(row.doc_date)
            if article_day is None or (as_of_date - article_day).days > 7:
                continue
            if row.event_family in NEGATIVE_SHOCK_FAMILIES and row.sentiment_score <= -0.1 and row.event_materiality >= 0.6:
                burst_count += 1
        burst_severity = 0.0
        if burst_count >= 2:
            burst_severity = min(100.0, 55.0 + ((burst_count - 2) * 15.0))

        shock_type = ""
        shock_severity = 0.0
        for candidate_type, candidate_severity in (
            ("governance_regulatory_burst", burst_severity),
            ("sentiment_regime_shift", shift_severity),
            ("event_density_spike", density_severity),
        ):
            if candidate_severity > shock_severity:
                shock_type = candidate_type
                shock_severity = candidate_severity

        for row in window_map.values():
            row.narrative_shock_flag = 1 if shock_severity >= 55.0 else 0
            row.shock_type = shock_type if row.narrative_shock_flag else ""
            row.shock_severity = float(round(shock_severity if row.narrative_shock_flag else 0.0, 3))
            shock_penalty = row.shock_severity * 0.12 if row.narrative_shock_flag else 0.0
            row.narrative_score_0_100 = float(
                round(
                    _compute_narrative_score(
                        weighted_sentiment=row.weighted_sentiment,
                        bullish_share=row.bullish_article_share,
                        bearish_share=row.bearish_article_share,
                        source_diversity=row.source_diversity,
                        primary_company_share=row.primary_company_share,
                        event_frequency=row.event_frequency,
                        shock_penalty=shock_penalty,
                    ),
                    3,
                )
            )

    out.sort(key=lambda row: (row.ticker, row.window_days))
    return out


def _alpha_return_for_window(row: ArticleIntelligenceRow, window_days: int) -> float | None:
    attr_name = {1: "ret_1d", 3: "ret_3d", 5: "ret_5d"}.get(int(window_days))
    if not attr_name:
        return None
    value = getattr(row, attr_name, None)
    if value is None:
        return None
    value_f = float(value)
    return value_f if math.isfinite(value_f) else None


def _alpha_confidence_score(*, sample_size: int, avg_abs_ret: float, avg_ret: float) -> float:
    if sample_size <= 0:
        return 0.0
    sample_term = min(1.0, math.log(float(sample_size) + 1.0) / math.log(50.0))
    dispersion = max(0.0, float(avg_abs_ret) - abs(float(avg_ret)))
    volatility_proxy = min(1.0, dispersion / max(float(avg_abs_ret), 1.0))
    confidence = sample_term * (1.0 - min(0.5, volatility_proxy))
    return float(round(max(0.0, min(1.0, confidence)), 6))


def _build_alpha_stat_row(
    *,
    event_family: str,
    window_days: int,
    rows: Sequence[ArticleIntelligenceRow],
    ticker: str | None = None,
) -> AlphaEventStatRow | AlphaTickerEventStatRow | None:
    realized_returns = [
        value
        for row in rows
        for value in [_alpha_return_for_window(row, int(window_days))]
        if value is not None
    ]
    if not realized_returns:
        return None
    sample_size = len(realized_returns)
    avg_ret = sum(realized_returns) / float(sample_size)
    median_ret = float(statistics.median(realized_returns))
    avg_abs_ret = sum(abs(value) for value in realized_returns) / float(sample_size)
    pos_rate = sum(1 for value in realized_returns if value > 0) / float(sample_size)
    neg_rate = sum(1 for value in realized_returns if value < 0) / float(sample_size)
    if avg_ret > 0:
        win_rate = pos_rate
    elif avg_ret < 0:
        win_rate = neg_rate
    else:
        win_rate = 0.5

    confirmation_values = [
        float(row.price_confirmation_score)
        for row in rows
        if row.price_confirmation_score is not None and math.isfinite(float(row.price_confirmation_score))
    ]
    avg_confirmation = (
        sum(confirmation_values) / float(len(confirmation_values)) if confirmation_values else None
    )
    avg_materiality = sum(float(row.event_materiality) for row in rows) / float(len(rows))
    avg_sentiment = sum(float(row.sentiment_score) for row in rows) / float(len(rows))
    shock_rate = sum(int(row.narrative_shock_flag) for row in rows) / float(len(rows))
    # Alpha score captures directional usefulness; larger absolute values imply a stronger
    # historical return profile for the event family and horizon.
    alpha_score = float(avg_ret) * math.sqrt(float(sample_size)) * (0.5 + (float(win_rate) / 2.0))
    # Confidence is bounded and rewards broader, less noisy samples without implying certainty.
    confidence_score = _alpha_confidence_score(
        sample_size=sample_size,
        avg_abs_ret=avg_abs_ret,
        avg_ret=avg_ret,
    )

    common_kwargs = {
        "event_family": event_family,
        "window_days": int(window_days),
        "sample_size": int(sample_size),
        "avg_ret": float(round(avg_ret, 6)),
        "median_ret": float(round(median_ret, 6)),
        "avg_abs_ret": float(round(avg_abs_ret, 6)),
        "win_rate": float(round(win_rate, 6)),
        "avg_price_confirmation_score": float(round(avg_confirmation, 6)) if avg_confirmation is not None else None,
        "avg_materiality": float(round(avg_materiality, 6)),
        "avg_sentiment": float(round(avg_sentiment, 6)),
        "shock_rate": float(round(shock_rate, 6)),
        "alpha_score": float(round(alpha_score, 6)),
        "confidence_score": float(round(confidence_score, 6)),
    }
    if ticker is not None:
        return AlphaTickerEventStatRow(
            ticker=ticker,
            **common_kwargs,
        )
    return AlphaEventStatRow(
        pos_rate=float(round(pos_rate, 6)),
        neg_rate=float(round(neg_rate, 6)),
        **common_kwargs,
    )


def build_alpha_statistics(
    *,
    intelligence_rows: Sequence[ArticleIntelligenceRow],
) -> tuple[list[AlphaEventStatRow], list[AlphaTickerEventStatRow]]:
    by_event: dict[tuple[str, int], list[ArticleIntelligenceRow]] = {}
    by_ticker_event: dict[tuple[str, str, int], list[ArticleIntelligenceRow]] = {}
    for row in intelligence_rows:
        event_family = str(row.event_family or "").strip()
        if not event_family:
            continue
        for window_days, _attr_name in ALPHA_WINDOWS:
            if _alpha_return_for_window(row, int(window_days)) is None:
                continue
            by_event.setdefault((event_family, int(window_days)), []).append(row)
            by_ticker_event.setdefault((row.ticker, event_family, int(window_days)), []).append(row)

    event_stats: list[AlphaEventStatRow] = []
    for (event_family, window_days), rows in by_event.items():
        built = _build_alpha_stat_row(
            event_family=event_family,
            window_days=window_days,
            rows=rows,
        )
        if isinstance(built, AlphaEventStatRow):
            event_stats.append(built)

    ticker_stats: list[AlphaTickerEventStatRow] = []
    for (ticker, event_family, window_days), rows in by_ticker_event.items():
        built = _build_alpha_stat_row(
            ticker=ticker,
            event_family=event_family,
            window_days=window_days,
            rows=rows,
        )
        if isinstance(built, AlphaTickerEventStatRow):
            ticker_stats.append(built)

    event_stats.sort(key=lambda row: (row.event_family, row.window_days))
    ticker_stats.sort(key=lambda row: (row.ticker, row.event_family, row.window_days))
    return event_stats, ticker_stats


def build_alpha_article_predictions(
    *,
    intelligence_rows: Sequence[ArticleIntelligenceRow],
    global_event_stats: Sequence[AlphaEventStatRow],
    ticker_event_stats: Sequence[AlphaTickerEventStatRow],
) -> list[AlphaArticlePredictionRow]:
    global_lookup = {
        (row.event_family, int(row.window_days)): row
        for row in global_event_stats
    }
    ticker_lookup = {
        (row.ticker, row.event_family, int(row.window_days)): row
        for row in ticker_event_stats
    }
    out: list[AlphaArticlePredictionRow] = []
    for row in intelligence_rows:
        event_family = str(row.event_family or "").strip()
        if not event_family:
            continue
        for window_days, _attr_name in ALPHA_WINDOWS:
            prior_source = ""
            prior_row: AlphaEventStatRow | AlphaTickerEventStatRow | None = None
            ticker_prior = ticker_lookup.get((row.ticker, event_family, int(window_days)))
            if ticker_prior is not None and int(ticker_prior.sample_size) >= TICKER_ALPHA_MIN_SAMPLE_SIZE:
                prior_row = ticker_prior
                prior_source = "ticker_event"
            else:
                prior_row = global_lookup.get((event_family, int(window_days)))
                prior_source = "global_event" if prior_row is not None else ""
            if prior_row is None or int(prior_row.sample_size) < PREDICTION_MIN_SAMPLE_SIZE:
                continue
            explanation = {
                "event_family": event_family,
                "prior_source": prior_source,
                "sample_size_used": int(prior_row.sample_size),
                "avg_materiality_in_prior": float(prior_row.avg_materiality),
                "avg_sentiment_in_prior": float(prior_row.avg_sentiment),
                "row_is_narrative_shock": bool(int(row.narrative_shock_flag)),
                "row_sentiment_polarity": (
                    "positive"
                    if float(row.sentiment_score) > 0.05
                    else "negative"
                    if float(row.sentiment_score) < -0.05
                    else "neutral"
                ),
                "advisory_only": True,
                "note": (
                    "Historical advisory prior only; not a guarantee and should not override "
                    "filing evidence or hard fundamentals."
                ),
            }
            out.append(
                AlphaArticlePredictionRow(
                    article_lookup_key=row.article_lookup_key,
                    ticker=row.ticker,
                    event_family=event_family,
                    window_days=int(window_days),
                    prior_source=prior_source,
                    expected_return=float(prior_row.avg_ret),
                    expected_abs_return=float(prior_row.avg_abs_ret),
                    win_rate=float(prior_row.win_rate),
                    confidence_score=float(prior_row.confidence_score),
                    alpha_score=float(prior_row.alpha_score),
                    sample_size_used=int(prior_row.sample_size),
                    prediction_explanation_json=json.dumps(explanation, ensure_ascii=False, sort_keys=True),
                )
            )
    out.sort(key=lambda row: (row.ticker, row.article_lookup_key, row.window_days))
    return out


def write_json(
    *,
    path: Path,
    as_of_date: dt.date,
    source_db: Path,
    scorer: str,
    fallback_count: int,
    windows: Sequence[int],
    ticker_rows: Sequence[TickerWindowSentiment],
    intelligence_rows: Sequence[ArticleIntelligenceRow],
    cluster_rows: Sequence[EventClusterRow],
    narrative_rows: Sequence[IntelligenceTickerWindowRow],
    include_articles: bool,
    article_rows: Sequence[ArticleSentiment],
) -> None:
    payload: dict[str, Any] = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "as_of_date": as_of_date.isoformat(),
        "source_news_db": str(source_db),
        "scorer": scorer,
        "fallback_to_lexical_count": int(fallback_count),
        "windows": [int(w) for w in windows],
        "ticker_window_count": len(ticker_rows),
        "article_count": len(article_rows),
        "article_intelligence_count": len(intelligence_rows),
        "event_cluster_count": len(cluster_rows),
        "narrative_window_count": len(narrative_rows),
        "ticker_windows": [asdict(row) for row in ticker_rows],
        "article_intelligence": [asdict(row) for row in intelligence_rows],
        "event_clusters": [asdict(row) for row in cluster_rows],
        "narrative_windows": [asdict(row) for row in narrative_rows],
    }
    if include_articles:
        payload["articles"] = [asdict(row) for row in article_rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv_rows(rows: Iterable[TickerWindowSentiment], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "as_of_date",
                "ticker",
                "window_days",
                "article_count",
                "source_count",
                "weighted_sentiment",
                "score_0_100",
                "avg_confidence",
                "avg_signal_hits",
                "avg_article_age_days",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.as_of_date,
                    row.ticker,
                    row.window_days,
                    row.article_count,
                    row.source_count,
                    f"{row.weighted_sentiment:.6f}",
                    f"{row.score_0_100:.3f}",
                    f"{row.avg_confidence:.6f}",
                    f"{row.avg_signal_hits:.6f}",
                    f"{row.avg_article_age_days:.6f}",
                ]
            )


def store_sqlite(
    *,
    db_path: Path,
    article_rows: Sequence[ArticleSentiment],
    ticker_rows: Sequence[TickerWindowSentiment],
    intelligence_rows: Sequence[ArticleIntelligenceRow],
    cluster_rows: Sequence[EventClusterRow],
    narrative_rows: Sequence[IntelligenceTickerWindowRow],
    alpha_event_stats: Sequence[AlphaEventStatRow],
    alpha_ticker_event_stats: Sequence[AlphaTickerEventStatRow],
    alpha_predictions: Sequence[AlphaArticlePredictionRow],
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_sentiment_article_scores (
                article_key TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                doc_date TEXT NOT NULL DEFAULT '',
                ticker_blob TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                sentiment_score REAL NOT NULL,
                confidence REAL NOT NULL,
                positive_hits INTEGER NOT NULL DEFAULT 0,
                negative_hits INTEGER NOT NULL DEFAULT 0,
                signal_hits INTEGER NOT NULL DEFAULT 0,
                scorer TEXT NOT NULL DEFAULT '',
                updated_utc TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_sentiment_ticker_windows (
                as_of_date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                article_count INTEGER NOT NULL,
                source_count INTEGER NOT NULL,
                weighted_sentiment REAL NOT NULL,
                score_0_100 REAL NOT NULL,
                avg_confidence REAL NOT NULL,
                avg_signal_hits REAL NOT NULL,
                avg_article_age_days REAL NOT NULL,
                updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (as_of_date, ticker, window_days)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_sentiment_ticker_windows_ticker "
            "ON news_sentiment_ticker_windows(ticker, window_days)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_intelligence_article_ticker (
                article_lookup_key TEXT NOT NULL,
                article_key TEXT NOT NULL DEFAULT '',
                ticker TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                doc_date TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                corpus TEXT NOT NULL DEFAULT '',
                sentiment_score REAL NOT NULL,
                sentiment_confidence REAL NOT NULL,
                event_family TEXT NOT NULL DEFAULT '',
                event_materiality REAL NOT NULL,
                relation_type TEXT NOT NULL DEFAULT '',
                relevance_score REAL NOT NULL,
                cluster_id TEXT NOT NULL DEFAULT '',
                cluster_similarity REAL NOT NULL DEFAULT 0,
                ret_1d REAL,
                ret_3d REAL,
                ret_5d REAL,
                abs_ret_1d REAL,
                price_confirmation_score REAL,
                narrative_shock_flag INTEGER NOT NULL DEFAULT 0,
                shock_severity REAL NOT NULL DEFAULT 0,
                updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (article_lookup_key, ticker)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_intelligence_article_ticker_ticker "
            "ON news_intelligence_article_ticker(ticker, published_at)"
        )
        article_intelligence_columns = sqlite_columns(cur, "news_intelligence_article_ticker")
        if "narrative_shock_flag" not in article_intelligence_columns:
            cur.execute(
                "ALTER TABLE news_intelligence_article_ticker "
                "ADD COLUMN narrative_shock_flag INTEGER NOT NULL DEFAULT 0"
            )
        if "shock_severity" not in article_intelligence_columns:
            cur.execute(
                "ALTER TABLE news_intelligence_article_ticker "
                "ADD COLUMN shock_severity REAL NOT NULL DEFAULT 0"
            )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_event_clusters (
                cluster_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                event_family TEXT NOT NULL DEFAULT '',
                cluster_sentiment REAL NOT NULL,
                cluster_materiality REAL NOT NULL,
                article_count INTEGER NOT NULL,
                source_count INTEGER NOT NULL,
                start_published_at TEXT NOT NULL DEFAULT '',
                end_published_at TEXT NOT NULL DEFAULT '',
                article_lookup_keys_json TEXT NOT NULL DEFAULT '',
                cluster_strength REAL,
                updated_utc TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_event_clusters_ticker "
            "ON news_event_clusters(ticker, end_published_at)"
        )
        if "cluster_strength" not in sqlite_columns(cur, "news_event_clusters"):
            cur.execute("ALTER TABLE news_event_clusters ADD COLUMN cluster_strength REAL")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_intelligence_ticker_windows (
                as_of_date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                article_count INTEGER NOT NULL,
                source_count INTEGER NOT NULL,
                weighted_sentiment REAL NOT NULL,
                dominant_event_types TEXT NOT NULL DEFAULT '[]',
                bullish_article_share REAL NOT NULL,
                bearish_article_share REAL NOT NULL,
                event_frequency INTEGER NOT NULL,
                source_diversity REAL NOT NULL,
                primary_company_share REAL NOT NULL,
                narrative_score_0_100 REAL NOT NULL,
                narrative_shock_flag INTEGER NOT NULL DEFAULT 0,
                shock_type TEXT NOT NULL DEFAULT '',
                shock_severity REAL NOT NULL DEFAULT 0,
                updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (as_of_date, ticker, window_days)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_intelligence_ticker_windows_ticker "
            "ON news_intelligence_ticker_windows(ticker, window_days)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_alpha_event_stats (
                event_family TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                sample_size INTEGER NOT NULL,
                avg_ret REAL NOT NULL,
                median_ret REAL NOT NULL,
                avg_abs_ret REAL NOT NULL,
                win_rate REAL NOT NULL,
                pos_rate REAL NOT NULL,
                neg_rate REAL NOT NULL,
                avg_price_confirmation_score REAL,
                avg_materiality REAL NOT NULL,
                avg_sentiment REAL NOT NULL,
                shock_rate REAL NOT NULL,
                alpha_score REAL NOT NULL,
                confidence_score REAL NOT NULL,
                last_updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (event_family, window_days)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_alpha_event_stats_window "
            "ON news_alpha_event_stats(window_days, alpha_score)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_alpha_ticker_event_stats (
                ticker TEXT NOT NULL,
                event_family TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                sample_size INTEGER NOT NULL,
                avg_ret REAL NOT NULL,
                median_ret REAL NOT NULL,
                avg_abs_ret REAL NOT NULL,
                win_rate REAL NOT NULL,
                avg_price_confirmation_score REAL,
                avg_materiality REAL NOT NULL,
                avg_sentiment REAL NOT NULL,
                shock_rate REAL NOT NULL,
                alpha_score REAL NOT NULL,
                confidence_score REAL NOT NULL,
                last_updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (ticker, event_family, window_days)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_alpha_ticker_event_stats_lookup "
            "ON news_alpha_ticker_event_stats(ticker, window_days, alpha_score)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS news_alpha_article_predictions (
                article_lookup_key TEXT NOT NULL,
                ticker TEXT NOT NULL,
                event_family TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                prior_source TEXT NOT NULL DEFAULT '',
                expected_return REAL NOT NULL,
                expected_abs_return REAL NOT NULL,
                win_rate REAL NOT NULL,
                confidence_score REAL NOT NULL,
                alpha_score REAL NOT NULL,
                sample_size_used INTEGER NOT NULL,
                prediction_explanation_json TEXT NOT NULL DEFAULT '{}',
                derived_at_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (article_lookup_key, ticker, window_days)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_alpha_article_predictions_lookup "
            "ON news_alpha_article_predictions(ticker, window_days, confidence_score)"
        )

        # This builder materializes a current derived snapshot. Clear prior rows so
        # stale tickers/clusters/windows from earlier runs do not persist.
        cur.execute("DELETE FROM news_sentiment_article_scores")
        cur.execute("DELETE FROM news_sentiment_ticker_windows")
        cur.execute("DELETE FROM news_intelligence_article_ticker")
        cur.execute("DELETE FROM news_event_clusters")
        cur.execute("DELETE FROM news_intelligence_ticker_windows")
        cur.execute("DELETE FROM news_alpha_event_stats")
        cur.execute("DELETE FROM news_alpha_ticker_event_stats")
        cur.execute("DELETE FROM news_alpha_article_predictions")

        now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        cur.executemany(
            """
            INSERT INTO news_sentiment_article_scores(
                article_key, title, source, url, published_at, doc_date, ticker_blob, topic,
                sentiment_score, confidence, positive_hits, negative_hits, signal_hits, scorer, updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_key) DO UPDATE SET
                title=excluded.title,
                source=excluded.source,
                url=excluded.url,
                published_at=excluded.published_at,
                doc_date=excluded.doc_date,
                ticker_blob=excluded.ticker_blob,
                topic=excluded.topic,
                sentiment_score=excluded.sentiment_score,
                confidence=excluded.confidence,
                positive_hits=excluded.positive_hits,
                negative_hits=excluded.negative_hits,
                signal_hits=excluded.signal_hits,
                scorer=excluded.scorer,
                updated_utc=excluded.updated_utc
            """,
            [
                (
                    row.article_key,
                    row.title,
                    row.source,
                    row.url,
                    row.published_at,
                    row.doc_date,
                    row.ticker_blob,
                    row.topic,
                    float(row.sentiment_score),
                    float(row.confidence),
                    int(row.positive_hits),
                    int(row.negative_hits),
                    int(row.signal_hits),
                    row.scorer,
                    now_utc,
                )
                for row in article_rows
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_sentiment_ticker_windows(
                as_of_date, ticker, window_days, article_count, source_count, weighted_sentiment,
                score_0_100, avg_confidence, avg_signal_hits, avg_article_age_days, updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(as_of_date, ticker, window_days) DO UPDATE SET
                article_count=excluded.article_count,
                source_count=excluded.source_count,
                weighted_sentiment=excluded.weighted_sentiment,
                score_0_100=excluded.score_0_100,
                avg_confidence=excluded.avg_confidence,
                avg_signal_hits=excluded.avg_signal_hits,
                avg_article_age_days=excluded.avg_article_age_days,
                updated_utc=excluded.updated_utc
            """,
            [
                (
                    row.as_of_date,
                    row.ticker,
                    int(row.window_days),
                    int(row.article_count),
                    int(row.source_count),
                    float(row.weighted_sentiment),
                    float(row.score_0_100),
                    float(row.avg_confidence),
                    float(row.avg_signal_hits),
                    float(row.avg_article_age_days),
                    now_utc,
                )
                for row in ticker_rows
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_intelligence_article_ticker(
                article_lookup_key, article_key, ticker, title, source, url, published_at, doc_date, topic, corpus,
                sentiment_score, sentiment_confidence, event_family, event_materiality, relation_type, relevance_score,
                cluster_id, cluster_similarity, ret_1d, ret_3d, ret_5d, abs_ret_1d, price_confirmation_score,
                narrative_shock_flag, shock_severity, updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_lookup_key, ticker) DO UPDATE SET
                article_key=excluded.article_key,
                title=excluded.title,
                source=excluded.source,
                url=excluded.url,
                published_at=excluded.published_at,
                doc_date=excluded.doc_date,
                topic=excluded.topic,
                corpus=excluded.corpus,
                sentiment_score=excluded.sentiment_score,
                sentiment_confidence=excluded.sentiment_confidence,
                event_family=excluded.event_family,
                event_materiality=excluded.event_materiality,
                relation_type=excluded.relation_type,
                relevance_score=excluded.relevance_score,
                cluster_id=excluded.cluster_id,
                cluster_similarity=excluded.cluster_similarity,
                ret_1d=excluded.ret_1d,
                ret_3d=excluded.ret_3d,
                ret_5d=excluded.ret_5d,
                abs_ret_1d=excluded.abs_ret_1d,
                price_confirmation_score=excluded.price_confirmation_score,
                narrative_shock_flag=excluded.narrative_shock_flag,
                shock_severity=excluded.shock_severity,
                updated_utc=excluded.updated_utc
            """,
            [
                (
                    row.article_lookup_key,
                    row.article_key,
                    row.ticker,
                    row.title,
                    row.source,
                    row.url,
                    row.published_at,
                    row.doc_date,
                    row.topic,
                    row.corpus,
                    float(row.sentiment_score),
                    float(row.sentiment_confidence),
                    row.event_family,
                    float(row.event_materiality),
                    row.relation_type,
                    float(row.relevance_score),
                    row.cluster_id,
                    float(row.cluster_similarity),
                    row.ret_1d,
                    row.ret_3d,
                    row.ret_5d,
                    row.abs_ret_1d,
                    row.price_confirmation_score,
                    int(row.narrative_shock_flag),
                    float(row.shock_severity),
                    now_utc,
                )
                for row in intelligence_rows
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_event_clusters(
                cluster_id, ticker, event_family, cluster_sentiment, cluster_materiality, article_count, source_count,
                start_published_at, end_published_at, article_lookup_keys_json, cluster_strength, updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cluster_id) DO UPDATE SET
                ticker=excluded.ticker,
                event_family=excluded.event_family,
                cluster_sentiment=excluded.cluster_sentiment,
                cluster_materiality=excluded.cluster_materiality,
                article_count=excluded.article_count,
                source_count=excluded.source_count,
                start_published_at=excluded.start_published_at,
                end_published_at=excluded.end_published_at,
                article_lookup_keys_json=excluded.article_lookup_keys_json,
                cluster_strength=excluded.cluster_strength,
                updated_utc=excluded.updated_utc
            """,
            [
                (
                    row.cluster_id,
                    row.ticker,
                    row.event_family,
                    float(row.cluster_sentiment),
                    float(row.cluster_materiality),
                    int(row.article_count),
                    int(row.source_count),
                    row.start_published_at,
                    row.end_published_at,
                    row.article_lookup_keys_json,
                    float(row.cluster_strength),
                    now_utc,
                )
                for row in cluster_rows
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_intelligence_ticker_windows(
                as_of_date, ticker, window_days, article_count, source_count, weighted_sentiment, dominant_event_types,
                bullish_article_share, bearish_article_share, event_frequency, source_diversity, primary_company_share,
                narrative_score_0_100, narrative_shock_flag, shock_type, shock_severity, updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(as_of_date, ticker, window_days) DO UPDATE SET
                article_count=excluded.article_count,
                source_count=excluded.source_count,
                weighted_sentiment=excluded.weighted_sentiment,
                dominant_event_types=excluded.dominant_event_types,
                bullish_article_share=excluded.bullish_article_share,
                bearish_article_share=excluded.bearish_article_share,
                event_frequency=excluded.event_frequency,
                source_diversity=excluded.source_diversity,
                primary_company_share=excluded.primary_company_share,
                narrative_score_0_100=excluded.narrative_score_0_100,
                narrative_shock_flag=excluded.narrative_shock_flag,
                shock_type=excluded.shock_type,
                shock_severity=excluded.shock_severity,
                updated_utc=excluded.updated_utc
            """,
            [
                (
                    row.as_of_date,
                    row.ticker,
                    int(row.window_days),
                    int(row.article_count),
                    int(row.source_count),
                    float(row.weighted_sentiment),
                    row.dominant_event_types,
                    float(row.bullish_article_share),
                    float(row.bearish_article_share),
                    int(row.event_frequency),
                    float(row.source_diversity),
                    float(row.primary_company_share),
                    float(row.narrative_score_0_100),
                    int(row.narrative_shock_flag),
                    row.shock_type,
                    float(row.shock_severity),
                    now_utc,
                )
                for row in narrative_rows
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_alpha_event_stats(
                event_family, window_days, sample_size, avg_ret, median_ret, avg_abs_ret, win_rate, pos_rate,
                neg_rate, avg_price_confirmation_score, avg_materiality, avg_sentiment, shock_rate, alpha_score,
                confidence_score, last_updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_family, window_days) DO UPDATE SET
                sample_size=excluded.sample_size,
                avg_ret=excluded.avg_ret,
                median_ret=excluded.median_ret,
                avg_abs_ret=excluded.avg_abs_ret,
                win_rate=excluded.win_rate,
                pos_rate=excluded.pos_rate,
                neg_rate=excluded.neg_rate,
                avg_price_confirmation_score=excluded.avg_price_confirmation_score,
                avg_materiality=excluded.avg_materiality,
                avg_sentiment=excluded.avg_sentiment,
                shock_rate=excluded.shock_rate,
                alpha_score=excluded.alpha_score,
                confidence_score=excluded.confidence_score,
                last_updated_utc=excluded.last_updated_utc
            """,
            [
                (
                    row.event_family,
                    int(row.window_days),
                    int(row.sample_size),
                    float(row.avg_ret),
                    float(row.median_ret),
                    float(row.avg_abs_ret),
                    float(row.win_rate),
                    float(row.pos_rate),
                    float(row.neg_rate),
                    row.avg_price_confirmation_score,
                    float(row.avg_materiality),
                    float(row.avg_sentiment),
                    float(row.shock_rate),
                    float(row.alpha_score),
                    float(row.confidence_score),
                    now_utc,
                )
                for row in alpha_event_stats
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_alpha_ticker_event_stats(
                ticker, event_family, window_days, sample_size, avg_ret, median_ret, avg_abs_ret, win_rate,
                avg_price_confirmation_score, avg_materiality, avg_sentiment, shock_rate, alpha_score,
                confidence_score, last_updated_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, event_family, window_days) DO UPDATE SET
                sample_size=excluded.sample_size,
                avg_ret=excluded.avg_ret,
                median_ret=excluded.median_ret,
                avg_abs_ret=excluded.avg_abs_ret,
                win_rate=excluded.win_rate,
                avg_price_confirmation_score=excluded.avg_price_confirmation_score,
                avg_materiality=excluded.avg_materiality,
                avg_sentiment=excluded.avg_sentiment,
                shock_rate=excluded.shock_rate,
                alpha_score=excluded.alpha_score,
                confidence_score=excluded.confidence_score,
                last_updated_utc=excluded.last_updated_utc
            """,
            [
                (
                    row.ticker,
                    row.event_family,
                    int(row.window_days),
                    int(row.sample_size),
                    float(row.avg_ret),
                    float(row.median_ret),
                    float(row.avg_abs_ret),
                    float(row.win_rate),
                    row.avg_price_confirmation_score,
                    float(row.avg_materiality),
                    float(row.avg_sentiment),
                    float(row.shock_rate),
                    float(row.alpha_score),
                    float(row.confidence_score),
                    now_utc,
                )
                for row in alpha_ticker_event_stats
            ],
        )
        cur.executemany(
            """
            INSERT INTO news_alpha_article_predictions(
                article_lookup_key, ticker, event_family, window_days, prior_source, expected_return,
                expected_abs_return, win_rate, confidence_score, alpha_score, sample_size_used,
                prediction_explanation_json, derived_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_lookup_key, ticker, window_days) DO UPDATE SET
                event_family=excluded.event_family,
                prior_source=excluded.prior_source,
                expected_return=excluded.expected_return,
                expected_abs_return=excluded.expected_abs_return,
                win_rate=excluded.win_rate,
                confidence_score=excluded.confidence_score,
                alpha_score=excluded.alpha_score,
                sample_size_used=excluded.sample_size_used,
                prediction_explanation_json=excluded.prediction_explanation_json,
                derived_at_utc=excluded.derived_at_utc
            """,
            [
                (
                    row.article_lookup_key,
                    row.ticker,
                    row.event_family,
                    int(row.window_days),
                    row.prior_source,
                    float(row.expected_return),
                    float(row.expected_abs_return),
                    float(row.win_rate),
                    float(row.confidence_score),
                    float(row.alpha_score),
                    int(row.sample_size_used),
                    row.prediction_explanation_json,
                    now_utc,
                )
                for row in alpha_predictions
            ],
        )
        conn.commit()
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build advisory-only news sentiment feature aggregates.")
    ap.add_argument("--news-db", default=str(DEFAULT_NEWS_CONTEXT_DB), help="Input news SQLite path")
    ap.add_argument("--out-json", default="reports/news_sentiment_features.json", help="Output summary JSON path")
    ap.add_argument("--out-csv", default="reports/news_sentiment_features.csv", help="Output ticker CSV path")
    ap.add_argument(
        "--out-sqlite",
        default="reports/news_sentiment_features.sqlite",
        help="Output SQLite path for article and ticker sentiment tables",
    )
    ap.add_argument("--windows", default="7,30,90", help="Comma-separated windows in days")
    ap.add_argument("--half-life-days", type=float, default=7.0, help="Recency decay half-life in days")
    ap.add_argument("--as-of-date", default="", help="As-of date YYYY-MM-DD (default: UTC today)")
    ap.add_argument("--ticker-filter", default="", help="Optional single ticker filter")
    ap.add_argument("--doc-type-filter", default="news_article", help="Doc type filter (default: news_article)")
    ap.add_argument("--min-text-chars", type=int, default=120, help="Drop rows/articles shorter than this")
    ap.add_argument("--max-article-chars", type=int, default=2200, help="Max merged text chars per article")
    ap.add_argument("--max-articles", type=int, default=0, help="Optional cap on merged article count")
    ap.add_argument("--scorer", choices=["lexical", "ollama"], default="lexical", help="Article scorer backend")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama base URL")
    ap.add_argument("--ollama-model", default="qwen2.5:7b-instruct", help="Ollama model for --scorer ollama")
    ap.add_argument("--ollama-timeout-seconds", type=float, default=30.0, help="Ollama request timeout")
    ap.add_argument(
        "--price-api-base-url",
        default="http://127.0.0.1:8000",
        help="Backend API base URL used for price reaction analytics",
    )
    ap.add_argument(
        "--price-timeout-seconds",
        type=float,
        default=20.0,
        help="Price API request timeout",
    )
    ap.add_argument(
        "--skip-price-reactions",
        action="store_true",
        help="Skip price reaction analytics when market data is unavailable",
    )
    ap.add_argument("--include-articles", action="store_true", help="Include per-article scores in JSON output")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    windows = parse_windows(args.windows)
    as_of_date = _parse_iso_date(args.as_of_date) if args.as_of_date else dt.datetime.now(dt.timezone.utc).date()
    if as_of_date is None:
        raise ValueError(f"Invalid --as-of-date: {args.as_of_date}")

    source_db = resolve_path(args.news_db)
    out_json = Path(args.out_json).expanduser()
    out_csv = Path(args.out_csv).expanduser()
    out_sqlite = Path(args.out_sqlite).expanduser()

    articles = load_news_articles_from_sqlite(
        db_path=source_db,
        doc_type_filter=str(args.doc_type_filter or "").strip(),
        min_text_chars=int(args.min_text_chars),
        max_article_chars=int(args.max_article_chars),
        max_articles=int(args.max_articles),
    )
    if not articles:
        print("No eligible news articles found after filters.")
        return 0

    article_scores, fallback_count = score_articles(
        articles,
        scorer=args.scorer,
        ollama_endpoint=args.ollama_endpoint,
        ollama_model=args.ollama_model,
        ollama_timeout_seconds=float(args.ollama_timeout_seconds),
    )
    normalized_ticker_filter = normalize_ticker_symbol(args.ticker_filter)
    unique_tickers = sorted(
        {
            ticker
            for article in articles
            for ticker in _article_tickers_for_intelligence(article)
            if ticker and (not normalized_ticker_filter or ticker == normalized_ticker_filter)
        }
    )
    earliest_article_day = min(
        (
            article_day
            for article in articles
            for article_day in [(_parse_iso_date(article.published_at) or _parse_iso_date(article.doc_date))]
            if article_day is not None
        ),
        default=None,
    )
    price_history_by_ticker: dict[str, list[dict[str, Any]]] = {}
    if unique_tickers and not bool(args.skip_price_reactions):
        price_history_by_ticker = _load_price_history_by_ticker(
            tickers=unique_tickers,
            earliest_day=earliest_article_day,
            base_url=str(args.price_api_base_url or "").strip(),
            timeout_seconds=float(args.price_timeout_seconds),
        )
    intelligence_rows = build_article_intelligence_rows(
        articles=articles,
        article_scores=article_scores,
        price_history_by_ticker=price_history_by_ticker,
        ticker_filter=args.ticker_filter,
    )
    cluster_rows = build_event_clusters(
        article_rows=intelligence_rows,
        articles=articles,
    )
    annotate_article_narrative_shocks(article_rows=intelligence_rows)
    ticker_rows = aggregate_ticker_windows(
        article_scores=article_scores,
        as_of_date=as_of_date,
        windows=windows,
        half_life_days=float(args.half_life_days),
        ticker_filter=args.ticker_filter,
    )
    narrative_rows = build_narrative_windows(
        article_rows=intelligence_rows,
        cluster_rows=cluster_rows,
        as_of_date=as_of_date,
        windows=windows,
        half_life_days=float(args.half_life_days),
        ticker_filter=args.ticker_filter,
    )
    alpha_event_stats, alpha_ticker_event_stats = build_alpha_statistics(
        intelligence_rows=intelligence_rows,
    )
    alpha_predictions = build_alpha_article_predictions(
        intelligence_rows=intelligence_rows,
        global_event_stats=alpha_event_stats,
        ticker_event_stats=alpha_ticker_event_stats,
    )

    write_json(
        path=out_json,
        as_of_date=as_of_date,
        source_db=source_db,
        scorer=args.scorer,
        fallback_count=fallback_count,
        windows=windows,
        ticker_rows=ticker_rows,
        intelligence_rows=intelligence_rows,
        cluster_rows=cluster_rows,
        narrative_rows=narrative_rows,
        include_articles=bool(args.include_articles),
        article_rows=article_scores,
    )
    write_csv_rows(ticker_rows, out_csv)
    store_sqlite(
        db_path=out_sqlite,
        article_rows=article_scores,
        ticker_rows=ticker_rows,
        intelligence_rows=intelligence_rows,
        cluster_rows=cluster_rows,
        narrative_rows=narrative_rows,
        alpha_event_stats=alpha_event_stats,
        alpha_ticker_event_stats=alpha_ticker_event_stats,
        alpha_predictions=alpha_predictions,
    )

    print(f"Articles scored: {len(article_scores)}")
    print(f"Ticker-window rows: {len(ticker_rows)}")
    print(f"Article intelligence rows: {len(intelligence_rows)}")
    print(f"Event clusters: {len(cluster_rows)}")
    print(f"Narrative windows: {len(narrative_rows)}")
    print(f"Alpha event priors: {len(alpha_event_stats)}")
    print(f"Ticker alpha priors: {len(alpha_ticker_event_stats)}")
    print(f"Article alpha predictions: {len(alpha_predictions)}")
    print(f"JSON: {out_json}")
    print(f"CSV: {out_csv}")
    print(f"SQLite: {out_sqlite}")
    if args.scorer == "ollama" and fallback_count:
        print(f"Ollama fallbacks to lexical: {fallback_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
