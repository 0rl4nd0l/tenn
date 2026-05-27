#!/usr/bin/env python3
"""
Drift detection harness for the canonical news context DB.

Compares current news.sqlite state to a saved baseline (corpus counts, total chunks).
Use after run_news_pipeline to detect unexpected regression or expansion.
See docs/architecture/15_news_substrate.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import (  # noqa: E402
    DEFAULT_NEWS_BASELINE_JSON,
    DEFAULT_NEWS_CONTEXT_DB,
    resolve_path,
)

DEFAULT_NEWS_SQLITE = DEFAULT_NEWS_CONTEXT_DB


SAMPLE_SIZE = 500  # stable sample size for content-sensitive hashes


def _snapshot_db(db_path: Path, news_only: bool) -> dict:
    where = " WHERE corpus LIKE 'news%'" if news_only else ""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM context_chunks" + where)
    total = cur.fetchone()[0]
    cur.execute(
        "SELECT corpus, COUNT(*) AS n FROM context_chunks" + where + " GROUP BY corpus ORDER BY corpus"
    )
    by_corpus = {row["corpus"]: row["n"] for row in cur.fetchall()}

    # Sample chunk_id list (stable order) for content-sensitive drift
    cur.execute(
        "SELECT chunk_id FROM context_chunks" + where + " ORDER BY chunk_id LIMIT " + str(SAMPLE_SIZE)
    )
    sample_chunk_ids = [row["chunk_id"] for row in cur.fetchall()]
    chunk_id_sample_hash = hashlib.sha256(
        "\n".join(sample_chunk_ids).encode("utf-8")
    ).hexdigest()[:16] if sample_chunk_ids else ""

    # Document-like prefix from chunk_id (e.g. "news:abc123" from "news:abc123:0" or "news:abc123:0:digest")
    cur.execute(
        "SELECT chunk_id FROM context_chunks" + where + " ORDER BY chunk_id"
    )
    seen_doc: set[str] = set()
    for row in cur.fetchall():
        cid = row["chunk_id"]
        # Take prefix before last two colon-segments (chunk index and optional digest)
        parts = cid.split(":")
        if len(parts) >= 2:
            doc_prefix = ":".join(parts[:2])  # e.g. news:article_id or news_newspaper4k:record_id
            seen_doc.add(doc_prefix)
        if len(seen_doc) >= SAMPLE_SIZE:
            break
    doc_sample = sorted(seen_doc)[:SAMPLE_SIZE]
    doc_id_sample_hash = hashlib.sha256(
        "\n".join(doc_sample).encode("utf-8")
    ).hexdigest()[:16] if doc_sample else ""

    # Top sources distribution (source column)
    source_where = (where + " AND (source IS NOT NULL AND source != '')") if where else " WHERE (source IS NOT NULL AND source != '')"
    cur.execute(
        "SELECT source, COUNT(*) AS n FROM context_chunks"
        + source_where
        + " GROUP BY source ORDER BY n DESC LIMIT 100"
    )
    top_sources = {row["source"]: row["n"] for row in cur.fetchall()}
    sources_hash = hashlib.sha256(
        json.dumps(top_sources, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16] if top_sources else ""

    conn.close()
    return {
        "total_chunks": total,
        "by_corpus": by_corpus,
        "chunk_id_sample_hash": chunk_id_sample_hash,
        "doc_id_sample_hash": doc_id_sample_hash,
        "top_sources_hash": sources_hash,
    }


def _corpus_hash(by_corpus: dict) -> str:
    canonical = json.dumps({k: by_corpus[k] for k in sorted(by_corpus)}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Detect drift in news context DB vs baseline (corpus counts, total chunks)",
    )
    ap.add_argument(
        "--db",
        default=str(DEFAULT_NEWS_SQLITE),
        help="Path to news context SQLite",
    )
    ap.add_argument(
        "--baseline",
        default="",
        help="Path to baseline JSON (expected counts). Default: reports/qual_context/news_baseline.json",
    )
    ap.add_argument(
        "--news-only",
        action="store_true",
        help="Restrict to corpora matching corpus LIKE 'news%%'",
    )
    ap.add_argument(
        "--tolerance-pct",
        type=float,
        default=25.0,
        help="Allow corpus count to drop by this pct before flagging drift (default: 25)",
    )
    ap.add_argument(
        "--fail-on-new-corpus",
        action="store_true",
        help="Treat presence of a corpus not in baseline as drift",
    )
    ap.add_argument(
        "--no-fail-on-missing-corpus",
        action="store_true",
        help="Do not treat missing baseline corpus in actual as drift",
    )
    ap.add_argument(
        "--save-baseline",
        action="store_true",
        help="Write current DB state to baseline path and exit 0",
    )
    ap.add_argument(
        "--out-json",
        default="",
        help="Write drift report JSON to this path",
    )
    args = ap.parse_args(argv)

    db_path = resolve_path(args.db)
    if not db_path.exists():
        print(f"[detect_news_context_drift] DB not found: {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='context_chunks'")
    if not cur.fetchone():
        print("[detect_news_context_drift] Table context_chunks not found", file=sys.stderr)
        conn.close()
        return 2
    conn.close()

    actual = _snapshot_db(db_path, news_only=args.news_only)
    actual["corpus_hash"] = _corpus_hash(actual["by_corpus"])

    baseline_path = resolve_path(args.baseline) if args.baseline else DEFAULT_NEWS_BASELINE_JSON

    if args.save_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        if baseline_path.exists():
            try:
                with open(baseline_path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                old_total = int(old.get("total_chunks") or 0)
                old_corpus = old.get("by_corpus") or {}
                cur_total = actual["total_chunks"]
                cur_corpus = actual["by_corpus"]
                delta_total = cur_total - old_total
                corpus_deltas = [
                    f"{c}: {cur_corpus.get(c, 0) - old_corpus.get(c, 0):+d}"
                    for c in sorted(set(old_corpus) | set(cur_corpus))
                    if cur_corpus.get(c, 0) != old_corpus.get(c, 0)
                ]
                summary = f"Previous total: {old_total}, current: {cur_total} (Δ{delta_total:+d})"
                if corpus_deltas:
                    summary += ". Corpus changes: " + ", ".join(corpus_deltas[:10])
                if len(corpus_deltas) > 10:
                    summary += f" (+{len(corpus_deltas) - 10} more)"
                summary += ". Saving new baseline."
                print(f"[detect_news_context_drift] {summary}")
            except (json.JSONDecodeError, OSError):
                print(f"[detect_news_context_drift] Saving new baseline (total_chunks={actual['total_chunks']}).")
        else:
            print(f"[detect_news_context_drift] Saving initial baseline (total_chunks={actual['total_chunks']}).")
        payload = {
            "version": 2,
            "db": str(db_path),
            "total_chunks": actual["total_chunks"],
            "by_corpus": actual["by_corpus"],
            "corpus_hash": actual["corpus_hash"],
            "chunk_id_sample_hash": actual.get("chunk_id_sample_hash", ""),
            "doc_id_sample_hash": actual.get("doc_id_sample_hash", ""),
            "top_sources_hash": actual.get("top_sources_hash", ""),
        }
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        print(f"[detect_news_context_drift] Saved baseline to {baseline_path}")
        return 0

    if not baseline_path.exists():
        print(f"[detect_news_context_drift] No baseline at {baseline_path}; run with --save-baseline first", file=sys.stderr)
        return 2

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    baseline_corpus = baseline_data.get("by_corpus") or {}
    baseline_total = int(baseline_data.get("total_chunks") or 0)

    reasons: list[str] = []
    deltas: dict = {"total": actual["total_chunks"] - baseline_total}

    # Hash-based drift (same count but different content)
    if actual.get("chunk_id_sample_hash") and baseline_data.get("chunk_id_sample_hash"):
        if actual["chunk_id_sample_hash"] != baseline_data["chunk_id_sample_hash"]:
            reasons.append("chunk_id_sample_hash_mismatch")
    if actual.get("doc_id_sample_hash") and baseline_data.get("doc_id_sample_hash"):
        if actual["doc_id_sample_hash"] != baseline_data["doc_id_sample_hash"]:
            reasons.append("doc_id_sample_hash_mismatch")
    if actual.get("top_sources_hash") and baseline_data.get("top_sources_hash"):
        if actual["top_sources_hash"] != baseline_data["top_sources_hash"]:
            reasons.append("top_sources_hash_mismatch")

    # New corpus
    actual_corpora = set(actual["by_corpus"])
    baseline_corpora = set(baseline_corpus)
    new_corpora = actual_corpora - baseline_corpora
    missing_corpora = baseline_corpora - actual_corpora

    if new_corpora and args.fail_on_new_corpus:
        reasons.append(f"new_corpus: {sorted(new_corpora)}")
    fail_on_missing = not getattr(args, "no_fail_on_missing_corpus", False)
    if missing_corpora and fail_on_missing:
        reasons.append(f"missing_corpus: {sorted(missing_corpora)}")

    # Per-corpus drop
    tolerance_pct = max(0.0, min(100.0, args.tolerance_pct)) / 100.0
    for corpus in baseline_corpora & actual_corpora:
        b = baseline_corpus.get(corpus) or 0
        a = actual["by_corpus"].get(corpus) or 0
        if b > 0 and a < b:
            drop_pct = (b - a) / b
            if drop_pct > tolerance_pct:
                reasons.append(f"corpus_drop: {corpus} {b} -> {a} (drop {drop_pct:.1%} > {tolerance_pct:.1%})")
        deltas[corpus] = a - b

    drift_detected = len(reasons) > 0

    report = {
        "drift_detected": drift_detected,
        "reasons": reasons,
        "actual": {
            "total_chunks": actual["total_chunks"],
            "by_corpus": actual["by_corpus"],
            "corpus_hash": actual["corpus_hash"],
            "chunk_id_sample_hash": actual.get("chunk_id_sample_hash"),
            "doc_id_sample_hash": actual.get("doc_id_sample_hash"),
            "top_sources_hash": actual.get("top_sources_hash"),
        },
        "baseline": {
            "path": str(baseline_path),
            "total_chunks": baseline_total,
            "by_corpus": baseline_corpus,
            "chunk_id_sample_hash": baseline_data.get("chunk_id_sample_hash"),
            "doc_id_sample_hash": baseline_data.get("doc_id_sample_hash"),
            "top_sources_hash": baseline_data.get("top_sources_hash"),
        },
        "deltas": deltas,
    }

    if args.out_json:
        out_path = Path(args.out_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(f"[detect_news_context_drift] Wrote report to {out_path}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if drift_detected:
        print("[detect_news_context_drift] DRIFT DETECTED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
