#!/usr/bin/env python3
"""
Quantify ASX headline/media coverage from a local context_chunks SQLite corpus.
"""

import argparse
import datetime
import json
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set
from urllib.parse import urlparse


ASX_TICKER_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{0,11})(?:\.AX)?(?![A-Za-z0-9])")
ASX_KEYWORD_RE = re.compile(r"\bASX\b")


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.replace(" ", "")
    return raw.rstrip("/")


def normalize_ticker(value: Any) -> str:
    out = re.sub(r"[^A-Za-z0-9.]", "", str(value or "").strip().upper())
    if not out:
        return ""
    if len(out) > 12:
        return ""
    return out


def parse_ticker_blob(value: Any) -> List[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    if "|" in raw:
        parts = [part for part in raw.split("|") if part.strip()]
    else:
        parts = [part for part in re.split(r"[,\s;/]+", raw) if part.strip()]
    out = sorted({normalize_ticker(part) for part in parts if normalize_ticker(part)})
    return out


def parse_domain(value: Any) -> str:
    raw = normalize_space(value).lower()
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    try:
        host = str(urlparse(candidate).netloc or "").strip().lower()
    except Exception:
        host = ""
    if not host:
        host = raw.split("/")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((100.0 * float(part)) / float(total), 4)


def load_asx_tickers(path: Path) -> List[str]:
    if not path.exists():
        raise RuntimeError(f"ASX ticker file not found: {path}")
    seen: Set[str] = set()
    out: List[str] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            base = line.split("#", 1)[0].strip()
            if not base:
                continue
            token = normalize_ticker(base)
            if not token:
                continue
            if token in seen:
                continue
            seen.add(token)
            out.append(token)
    return out


def sqlite_columns(cur: sqlite3.Cursor, table: str) -> List[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(row[1]) for row in rows]


def iter_corpus_rows(conn: sqlite3.Connection, corpus: str) -> Iterator[Dict[str, str]]:
    cur = conn.cursor()
    cols = set(sqlite_columns(cur, "context_chunks"))
    wanted = ["chunk_id", "corpus", "ticker", "title", "text", "url", "source"]
    select_parts = [col if col in cols else f"'' AS {col}" for col in wanted]
    sql = f"SELECT {', '.join(select_parts)} FROM context_chunks"
    params: List[str] = []
    if corpus and "corpus" in cols:
        sql += " WHERE corpus = ?"
        params.append(corpus)
    for row in cur.execute(sql, tuple(params)):
        payload = {wanted[idx]: str(value or "") for idx, value in enumerate(row)}
        yield payload


def estimate_article_key(*, chunk_id: str, url: str, title: str) -> str:
    norm_url = normalize_url(url)
    norm_title = normalize_space(title).lower()
    if norm_url or norm_title:
        return f"{norm_url}||{norm_title}"
    return f"chunk:{chunk_id}"


def detect_asx_ticker_hits(
    *,
    ticker_blob: str,
    title: str,
    text: str,
    ticker_allowlist: Set[str],
) -> Set[str]:
    hits: Set[str] = set()
    for ticker in parse_ticker_blob(ticker_blob):
        if ticker in ticker_allowlist:
            hits.add(ticker)
    payload = f"{title}\n{text}"
    for raw in ASX_TICKER_TOKEN_RE.findall(payload):
        sym = normalize_ticker(raw)
        if sym and sym in ticker_allowlist:
            hits.add(sym)
    return hits


def build_coverage_report(
    *,
    news_db_path: Path,
    corpus: str,
    asx_tickers: Sequence[str],
) -> Dict[str, Any]:
    ticker_order = [normalize_ticker(sym) for sym in asx_tickers if normalize_ticker(sym)]
    ticker_set = set(ticker_order)
    per_ticker_articles: Dict[str, Set[str]] = {sym: set() for sym in ticker_order}
    per_ticker_chunk_counts: Counter[str] = Counter()
    top_au_domains: Counter[str] = Counter()
    article_keys: Set[str] = set()

    total_chunks = 0
    chunks_with_asx_match = 0
    chunks_with_asx_keyword = 0

    conn = sqlite3.connect(str(news_db_path))
    try:
        for row in iter_corpus_rows(conn=conn, corpus=corpus):
            total_chunks += 1
            chunk_id = str(row.get("chunk_id", "")).strip()
            title = str(row.get("title", ""))
            text = str(row.get("text", ""))
            ticker_blob = str(row.get("ticker", ""))
            url = str(row.get("url", ""))
            source = str(row.get("source", ""))

            article_key = estimate_article_key(chunk_id=chunk_id, url=url, title=title)
            article_keys.add(article_key)

            if ASX_KEYWORD_RE.search(title) or ASX_KEYWORD_RE.search(text):
                chunks_with_asx_keyword += 1

            row_domains = set()
            for candidate in (url, source):
                domain = parse_domain(candidate)
                if domain.endswith(".com.au"):
                    row_domains.add(domain)
            for domain in row_domains:
                top_au_domains[domain] += 1

            hits = detect_asx_ticker_hits(
                ticker_blob=ticker_blob,
                title=title,
                text=text,
                ticker_allowlist=ticker_set,
            )
            if hits:
                chunks_with_asx_match += 1
                for sym in hits:
                    per_ticker_articles.setdefault(sym, set()).add(article_key)
                    per_ticker_chunk_counts[sym] += 1
    finally:
        conn.close()

    per_ticker_counts = {sym: len(per_ticker_articles.get(sym, set())) for sym in ticker_order}
    zero_hit_tickers = [sym for sym in ticker_order if per_ticker_counts.get(sym, 0) <= 0]
    per_ticker_article_values = [int(per_ticker_counts.get(sym, 0)) for sym in ticker_order]
    median_articles = float(statistics.median(per_ticker_article_values)) if per_ticker_article_values else 0.0

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "corpus": corpus,
        "total_chunks": int(total_chunks),
        "articles_estimated": int(len(article_keys)),
        "asx_summary": {
            "tickers_total": int(len(ticker_order)),
            "tickers_with_hits": int(sum(1 for value in per_ticker_counts.values() if int(value) > 0)),
            "tickers_zero_hits": int(len(zero_hit_tickers)),
            "median_articles_per_ticker": round(median_articles, 4),
            "chunks_with_asx_ticker_pct": pct(chunks_with_asx_match, total_chunks),
        },
        "top_au_domains": {domain: int(count) for domain, count in top_au_domains.most_common(20)},
        "asx_keyword_pct": pct(chunks_with_asx_keyword, total_chunks),
        "per_ticker_counts": {sym: int(per_ticker_counts.get(sym, 0)) for sym in ticker_order},
        "zero_hit_tickers": zero_hit_tickers,
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Quantify ASX news coverage in context_chunks SQLite corpora.")
    ap.add_argument("--news-db-path", default="reports/qual_context/news.sqlite", help="Path to news SQLite DB")
    ap.add_argument("--corpus", default="news", help="Corpus label to quantify")
    ap.add_argument("--asx-tickers-file", required=True, help="TXT file with one ASX ticker per line")
    ap.add_argument("--out-json", default="reports/analysis/asx_coverage_baseline.json", help="Output JSON path")
    args = ap.parse_args()

    db_path = Path(args.news_db_path).expanduser().resolve()
    if not db_path.exists():
        print(f"News DB path not found: {db_path}", file=sys.stderr)
        return 2

    ticker_path = Path(args.asx_tickers_file).expanduser().resolve()
    try:
        asx_tickers = load_asx_tickers(ticker_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not asx_tickers:
        print(f"No ASX tickers parsed from: {ticker_path}", file=sys.stderr)
        return 2

    try:
        report = build_coverage_report(
            news_db_path=db_path,
            corpus=str(args.corpus or "").strip(),
            asx_tickers=asx_tickers,
        )
    except sqlite3.OperationalError as exc:
        print(f"SQLite error while quantifying coverage: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
