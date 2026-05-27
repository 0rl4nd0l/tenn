#!/usr/bin/env python3
"""
Post-index audit for news context corpus quality.

This script inspects context_chunks metadata and reports coverage, ticker quality,
and AU relevance proxies to help assess retrieval readiness.
"""

import argparse
import datetime
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set
from urllib.parse import urlparse

import build_qualitative_context_db as ctx
import build_news_context_db as news_ctx
from news_pipeline.cli_common import DEFAULT_NEWS_CONTEXT_DB, resolve_path


AU_HINT_RE = re.compile(r"\b(asx|australia|australian|rba|asic|apra|aud)\b", re.IGNORECASE)


def sqlite_columns(cur: sqlite3.Cursor, table: str) -> List[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(r[1]) for r in rows]


def pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((100.0 * float(part)) / float(total), 4)


def percentile(values: Sequence[int], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(int(v) for v in values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = max(0.0, min(1.0, float(q))) * float(len(ordered) - 1)
    lo = int(rank)
    hi = min(len(ordered) - 1, lo + 1)
    if lo == hi:
        return float(ordered[lo])
    frac = rank - float(lo)
    return float(ordered[lo]) * (1.0 - frac) + float(ordered[hi]) * frac


def top_counts(counter: Counter[str], top_n: int, key_name: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key, count in counter.most_common(max(1, int(top_n))):
        out.append({key_name: key, "count": int(count)})
    return out


def parse_domain(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        host = str(urlparse(raw).netloc or "").strip().lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def has_au_hint(*, source: str, domain: str, title: str, topic: str, text: str) -> bool:
    if domain.endswith(".au"):
        return True
    payload = " ".join(
        part
        for part in (
            str(source or ""),
            str(domain or ""),
            str(title or ""),
            str(topic or ""),
            str(text or "")[:700],
        )
        if part
    )
    if not payload:
        return False
    return bool(AU_HINT_RE.search(payload))


def iter_context_rows(
    *,
    db_path: Path,
    corpus_filter: str,
    doc_type_filter: str,
) -> Iterator[Dict[str, str]]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cols = set(sqlite_columns(cur, "context_chunks"))
        wanted = [
            "chunk_id",
            "corpus",
            "doc_type",
            "doc_date",
            "published_at",
            "source",
            "ticker",
            "topic",
            "url",
            "file",
            "title",
            "company",
            "text",
        ]
        select_parts = [col if col in cols else f"'' AS {col}" for col in wanted]
        sql = f"SELECT {', '.join(select_parts)} FROM context_chunks"
        where: List[str] = []
        args: List[str] = []
        if corpus_filter and "corpus" in cols:
            where.append("corpus = ?")
            args.append(corpus_filter)
        if doc_type_filter and "doc_type" in cols:
            where.append("doc_type = ?")
            args.append(doc_type_filter)
        if where:
            sql += " WHERE " + " AND ".join(where)

        for row in cur.execute(sql, tuple(args)):
            payload = {wanted[idx]: str(value or "") for idx, value in enumerate(row)}
            yield payload
    finally:
        conn.close()


def build_report(
    *,
    db_path: Path,
    corpus_filter: str,
    doc_type_filter: str,
    top_n: int,
    ticker_allowlist: Optional[Set[str]],
) -> Dict[str, Any]:
    chunk_count = 0
    chunks_with_doc_date = 0
    chunks_with_published_at = 0
    chunks_with_ticker = 0
    chunks_with_url = 0
    chunks_with_au_hint = 0
    chunks_all_tickers_allowlisted = 0
    chunks_with_unknown_ticker = 0

    min_doc_date = ""
    max_doc_date = ""
    chunk_lengths: List[int] = []
    unique_tickers: Set[str] = set()
    corpus_counter: Counter[str] = Counter()
    doc_type_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    ticker_counter: Counter[str] = Counter()
    unknown_ticker_counter: Counter[str] = Counter()

    article_chunk_counts: Dict[str, int] = {}
    article_has_ticker: Set[str] = set()
    article_has_au_hint: Set[str] = set()
    article_has_unknown_ticker: Set[str] = set()

    allowlist_enabled = bool(ticker_allowlist)

    for row in iter_context_rows(db_path=db_path, corpus_filter=corpus_filter, doc_type_filter=doc_type_filter):
        chunk_count += 1
        corpus = str(row.get("corpus", "")).strip() or "unknown"
        doc_type = str(row.get("doc_type", "")).strip() or "unknown"
        source = str(row.get("source", "")).strip().lower() or "unknown"
        doc_date = str(row.get("doc_date", "")).strip()
        published_at = str(row.get("published_at", "")).strip()
        ticker_blob = str(row.get("ticker", "")).strip()
        url = str(row.get("url", "")).strip()
        file_ref = str(row.get("file", "")).strip()
        title = str(row.get("title", "")).strip()
        topic = str(row.get("topic", "")).strip()
        text = str(row.get("text", "")).strip()

        corpus_counter[corpus] += 1
        doc_type_counter[doc_type] += 1
        source_counter[source] += 1
        chunk_lengths.append(len(text))

        if url:
            chunks_with_url += 1
        domain = parse_domain(url or file_ref)
        if domain:
            domain_counter[domain] += 1

        if doc_date:
            chunks_with_doc_date += 1
            if not min_doc_date or doc_date < min_doc_date:
                min_doc_date = doc_date
            if not max_doc_date or doc_date > max_doc_date:
                max_doc_date = doc_date
        if published_at:
            chunks_with_published_at += 1

        tickers = ctx.parse_ticker_blob(ticker_blob)
        unknown_tickers: List[str] = []
        if tickers:
            chunks_with_ticker += 1
            for sym in tickers:
                unique_tickers.add(sym)
                ticker_counter[sym] += 1
            if allowlist_enabled:
                unknown_tickers = [sym for sym in tickers if sym not in ticker_allowlist]
                if unknown_tickers:
                    chunks_with_unknown_ticker += 1
                    for sym in unknown_tickers:
                        unknown_ticker_counter[sym] += 1
                else:
                    chunks_all_tickers_allowlisted += 1

        au_hint = has_au_hint(source=source, domain=domain, title=title, topic=topic, text=text)
        if au_hint:
            chunks_with_au_hint += 1

        article_key = url or file_ref or str(row.get("chunk_id", "")).strip()
        article_chunk_counts[article_key] = article_chunk_counts.get(article_key, 0) + 1
        if tickers:
            article_has_ticker.add(article_key)
        if au_hint:
            article_has_au_hint.add(article_key)
        if unknown_tickers:
            article_has_unknown_ticker.add(article_key)

    total_articles = len(article_chunk_counts)
    chunks_per_article = list(article_chunk_counts.values())

    report: Dict[str, Any] = {
        "db_path": str(db_path),
        "generated_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "filters": {
            "corpus_filter": corpus_filter,
            "doc_type_filter": doc_type_filter,
        },
        "allowlist": {
            "enabled": allowlist_enabled,
            "size": len(ticker_allowlist or set()),
        },
        "coverage": {
            "chunks_total": chunk_count,
            "chunks_with_doc_date": chunks_with_doc_date,
            "chunks_with_published_at": chunks_with_published_at,
            "chunks_with_ticker": chunks_with_ticker,
            "chunks_with_url": chunks_with_url,
            "chunks_with_au_hint": chunks_with_au_hint,
            "doc_date_coverage_pct": pct(chunks_with_doc_date, chunk_count),
            "published_at_coverage_pct": pct(chunks_with_published_at, chunk_count),
            "ticker_coverage_pct": pct(chunks_with_ticker, chunk_count),
            "url_coverage_pct": pct(chunks_with_url, chunk_count),
            "au_hint_coverage_pct": pct(chunks_with_au_hint, chunk_count),
        },
        "date_span": {
            "min_doc_date": min_doc_date,
            "max_doc_date": max_doc_date,
        },
        "chunk_length": {
            "avg_chars": round(sum(chunk_lengths) / max(1, len(chunk_lengths)), 2),
            "p50_chars": round(percentile(chunk_lengths, 0.50), 2),
            "p95_chars": round(percentile(chunk_lengths, 0.95), 2),
            "max_chars": max(chunk_lengths) if chunk_lengths else 0,
        },
        "article_stats": {
            "articles_estimated": total_articles,
            "articles_with_ticker": len(article_has_ticker),
            "articles_with_au_hint": len(article_has_au_hint),
            "articles_with_unknown_ticker": len(article_has_unknown_ticker),
            "article_ticker_coverage_pct": pct(len(article_has_ticker), total_articles),
            "article_au_hint_coverage_pct": pct(len(article_has_au_hint), total_articles),
            "avg_chunks_per_article": round(sum(chunks_per_article) / max(1, len(chunks_per_article)), 3),
            "p95_chunks_per_article": round(percentile(chunks_per_article, 0.95), 2),
            "max_chunks_per_article": max(chunks_per_article) if chunks_per_article else 0,
        },
        "ticker_quality": {
            "unique_tickers": len(unique_tickers),
            "chunks_all_tickers_allowlisted": chunks_all_tickers_allowlisted,
            "chunks_with_unknown_ticker": chunks_with_unknown_ticker,
            "unknown_ticker_chunk_rate_pct": pct(chunks_with_unknown_ticker, chunk_count),
            "allowlisted_ticker_chunk_rate_pct": pct(chunks_all_tickers_allowlisted, chunk_count),
        },
        "top": {
            "corpora": top_counts(corpus_counter, top_n=top_n, key_name="corpus"),
            "doc_types": top_counts(doc_type_counter, top_n=top_n, key_name="doc_type"),
            "sources": top_counts(source_counter, top_n=top_n, key_name="source"),
            "domains": top_counts(domain_counter, top_n=top_n, key_name="domain"),
            "tickers": top_counts(ticker_counter, top_n=top_n, key_name="ticker"),
            "unknown_tickers": top_counts(unknown_ticker_counter, top_n=top_n, key_name="ticker"),
        },
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit news context SQLite corpus quality.")
    ap.add_argument("--db", default=str(DEFAULT_NEWS_CONTEXT_DB), help="Path to context SQLite DB")
    ap.add_argument("--corpus-filter", default="", help="Optional corpus filter")
    ap.add_argument("--doc-type-filter", default="", help="Optional doc_type filter")
    ap.add_argument("--top-n", type=int, default=20, help="Top-N values in distributions")
    ap.add_argument("--ticker-allowlist-path", default="", help="Optional ticker allowlist path")
    ap.add_argument(
        "--use-default-asx-allowlist",
        action="store_true",
        help=f"Use default ASX ticker allowlist at ./{news_ctx.DEFAULT_ASX_ALLOWLIST_RELATIVE}",
    )
    ap.add_argument(
        "--out-json",
        default="reports/qual_context/news_corpus_audit.json",
        help="Output JSON summary path",
    )
    args = ap.parse_args()

    db_path = resolve_path(args.db)
    if not db_path.exists():
        print(f"DB path not found: {db_path}")
        return 2

    allowlist_path = str(args.ticker_allowlist_path or "").strip()
    if args.use_default_asx_allowlist and not allowlist_path:
        allowlist_path = str(news_ctx.default_asx_allowlist_path())

    ticker_allowlist: Optional[Set[str]] = None
    if allowlist_path:
        try:
            ticker_allowlist = news_ctx.load_ticker_allowlist(Path(allowlist_path).expanduser().resolve())
        except RuntimeError as exc:
            print(str(exc))
            return 2
        if not ticker_allowlist:
            print(f"Ticker allowlist is empty after parsing: {allowlist_path}")
            return 2

    report = build_report(
        db_path=db_path,
        corpus_filter=str(args.corpus_filter or "").strip(),
        doc_type_filter=str(args.doc_type_filter or "").strip(),
        top_n=max(1, int(args.top_n)),
        ticker_allowlist=ticker_allowlist,
    )

    out_path = Path(args.out_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "out_json": str(out_path),
                "chunks_total": report["coverage"]["chunks_total"],
                "articles_estimated": report["article_stats"]["articles_estimated"],
                "doc_date_coverage_pct": report["coverage"]["doc_date_coverage_pct"],
                "ticker_coverage_pct": report["coverage"]["ticker_coverage_pct"],
                "unknown_ticker_chunk_rate_pct": report["ticker_quality"]["unknown_ticker_chunk_rate_pct"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
