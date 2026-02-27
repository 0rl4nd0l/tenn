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
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


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


def sqlite_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(row[1]) for row in rows]


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
        for col in ("title", "source", "url", "published_at", "doc_date", "ticker", "topic", "company", "text"):
            if col in cols:
                select_parts.append(col)
            else:
                select_parts.append(f"'' AS {col}")
        where_parts: list[str] = []
        args: list[str] = []
        if "corpus" in cols:
            where_parts.append("corpus = ?")
            args.append("news")
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
        title, source, url, published_at, doc_date, ticker_blob, topic, company, text = [str(item or "") for item in row]
        clean_text = normalize_space(text)
        if len(clean_text) < max(1, int(min_text_chars)):
            continue
        clean_url = normalize_url(url)
        key = _article_key(
            url=clean_url,
            title=title,
            published_at=published_at,
            doc_date=doc_date,
            ticker_blob=ticker_blob,
            source=source,
        )
        payload = grouped.get(key)
        if payload is None:
            payload = {
                "title": normalize_space(title),
                "source": normalize_space(source),
                "url": clean_url,
                "published_at": str(published_at or "").strip(),
                "doc_date": str(doc_date or "").strip(),
                "ticker_blob": str(ticker_blob or "").strip(),
                "topic": normalize_space(topic),
                "company": normalize_ticker_symbol(company),
                "parts": [],
                "part_keys": set(),
            }
            grouped[key] = payload

        part_key = hashlib.sha1(clean_text.encode("utf-8")).hexdigest()[:16]
        if part_key in payload["part_keys"]:
            continue
        payload["part_keys"].add(part_key)
        payload["parts"].append(clean_text)

    articles: list[NewsArticle] = []
    for key, payload in grouped.items():
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
        articles.append(
            NewsArticle(
                article_key=key,
                title=str(payload.get("title", "")),
                source=str(payload.get("source", "")),
                url=str(payload.get("url", "")),
                published_at=str(payload.get("published_at", "")),
                doc_date=str(payload.get("doc_date", "")),
                ticker_blob=ticker_blob,
                topic=str(payload.get("topic", "")),
                text=merged,
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


def write_json(
    *,
    path: Path,
    as_of_date: dt.date,
    source_db: Path,
    scorer: str,
    fallback_count: int,
    windows: Sequence[int],
    ticker_rows: Sequence[TickerWindowSentiment],
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
        "ticker_windows": [asdict(row) for row in ticker_rows],
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
        conn.commit()
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build advisory-only news sentiment feature aggregates.")
    ap.add_argument("--news-db", default="reports/qual_context/news.sqlite", help="Input news SQLite path")
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
    ap.add_argument("--include-articles", action="store_true", help="Include per-article scores in JSON output")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    windows = parse_windows(args.windows)
    as_of_date = _parse_iso_date(args.as_of_date) if args.as_of_date else dt.datetime.now(dt.timezone.utc).date()
    if as_of_date is None:
        raise ValueError(f"Invalid --as-of-date: {args.as_of_date}")

    source_db = Path(args.news_db).expanduser()
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
    ticker_rows = aggregate_ticker_windows(
        article_scores=article_scores,
        as_of_date=as_of_date,
        windows=windows,
        half_life_days=float(args.half_life_days),
        ticker_filter=args.ticker_filter,
    )

    write_json(
        path=out_json,
        as_of_date=as_of_date,
        source_db=source_db,
        scorer=args.scorer,
        fallback_count=fallback_count,
        windows=windows,
        ticker_rows=ticker_rows,
        include_articles=bool(args.include_articles),
        article_rows=article_scores,
    )
    write_csv_rows(ticker_rows, out_csv)
    store_sqlite(db_path=out_sqlite, article_rows=article_scores, ticker_rows=ticker_rows)

    print(f"Articles scored: {len(article_scores)}")
    print(f"Ticker-window rows: {len(ticker_rows)}")
    print(f"JSON: {out_json}")
    print(f"CSV: {out_csv}")
    print(f"SQLite: {out_sqlite}")
    if args.scorer == "ollama" and fallback_count:
        print(f"Ollama fallbacks to lexical: {fallback_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
