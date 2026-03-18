#!/usr/bin/env python3
"""Inspect RAG retrieval distribution: run random queries and report metrics.

- Runs 20 random queries sampled from document titles and recent document titles.
- Collects top_3 tickers, score distribution, unique document_id coverage.
- Reports: ticker dominance (%), average top score, retrieval entropy (Shannon).

Read-only: no DB modification, no Qdrant modification.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.services.rag import query_rag  # noqa: E402

NUM_QUERIES = 20
TOP_N = 3
RECENT_DAYS = 180
DEFAULT_SEED = 42


def _get_query_pool(session, *, recent_days: int, seed: int) -> list[tuple[str, str]]:
    """Build pool of (query_text, source_label) from document titles and recent titles. Read-only."""
    # All documents with a non-empty title
    rows = (
        session.query(Document.title, Document.published_at)
        .filter(Document.title.isnot(None), Document.title != "")
        .all()
    )
    if not rows:
        return []

    # Recent cutoff; recent document "content" sampled as recent titles (no excerpt store in backend)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=recent_days)) if recent_days else None
    all_titles: list[str] = []
    recent_titles: list[str] = []
    for title, published_at in rows:
        t = (title or "").strip()
        if not t:
            continue
        all_titles.append(t)
        if cutoff is not None and published_at is not None:
            pub = published_at.replace(tzinfo=timezone.utc) if getattr(published_at, "tzinfo") is None else published_at
            if pub >= cutoff:
                recent_titles.append(t)

    rng = random.Random(seed)
    pool: list[tuple[str, str]] = []
    # Prefer mix: half from recent (if available), half from all
    n_recent = min(NUM_QUERIES // 2, len(recent_titles)) if recent_titles else 0
    n_rest = NUM_QUERIES - n_recent
    if n_recent > 0:
        pool.extend((rng.choice(recent_titles), "recent_title") for _ in range(n_recent))
    if n_rest > 0 and all_titles:
        pool.extend((rng.choice(all_titles), "title") for _ in range(n_rest))
    rng.shuffle(pool)
    return pool[:NUM_QUERIES]


def _shannon_entropy(counts: Counter[str], total: int) -> float:
    """Shannon entropy in bits: -sum(p_i * log2(p_i))."""
    if total <= 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def run() -> dict:
    """Run 20 random queries, collect top-3 tickers/scores/doc_ids, compute and return report. Read-only."""
    session = SessionLocal()
    try:
        pool = _get_query_pool(session, recent_days=RECENT_DAYS, seed=DEFAULT_SEED)
    finally:
        session.close()

    if len(pool) < NUM_QUERIES:
        print(
            f"Warning: only {len(pool)} query strings available (need {NUM_QUERIES}). Proceeding with {len(pool)}.",
            file=sys.stderr,
        )

    all_top_tickers: list[list[str]] = []
    all_top_scores: list[list[float]] = []
    all_top_doc_ids: list[set[str]] = []
    top_scores_per_query: list[float] = []

    for query_text, source in pool:
        try:
            result = query_rag(query=query_text, ticker=None, top_k=8)
        except Exception as e:
            print(f"query_rag failed for '{query_text[:50]}...': {e}", file=sys.stderr)
            all_top_tickers.append([])
            all_top_scores.append([])
            all_top_doc_ids.append(set())
            top_scores_per_query.append(0.0)
            continue

        hits = result.get("hits") or []
        top = hits[:TOP_N]
        tickers = [str(h.get("ticker") or "").strip() or "<empty>" for h in top]
        scores = [float(h.get("score") or 0.0) for h in top]
        doc_ids = {str(h.get("document_id") or "").strip() for h in top if (h.get("document_id") or "").strip()}

        all_top_tickers.append(tickers)
        all_top_scores.append(scores)
        all_top_doc_ids.append(doc_ids)
        top_scores_per_query.append(scores[0] if scores else 0.0)

    # Flatten ticker counts for dominance and entropy
    ticker_counts: Counter[str] = Counter()
    for tickers in all_top_tickers:
        for t in tickers:
            ticker_counts[t] += 1
    total_slots = sum(ticker_counts.values())
    if total_slots == 0:
        dominant_ticker = ""
        dominance_pct = 0.0
        entropy = 0.0
    else:
        dominant_ticker, dominant_count = ticker_counts.most_common(1)[0]
        dominance_pct = 100.0 * dominant_count / total_slots
        entropy = _shannon_entropy(ticker_counts, total_slots)

    avg_top_score = sum(top_scores_per_query) / len(top_scores_per_query) if top_scores_per_query else 0.0
    unique_doc_ids_global: set[str] = set()
    for s in all_top_doc_ids:
        unique_doc_ids_global |= s
    unique_doc_ids_global.discard("")
    per_query_unique = [len(s) for s in all_top_doc_ids]

    report = {
        "num_queries": len(pool),
        "top_n": TOP_N,
        "ticker_dominance": {
            "top_ticker": dominant_ticker,
            "top_ticker_share_pct": round(dominance_pct, 2),
            "total_ticker_slots": total_slots,
        },
        "average_top_score": round(avg_top_score, 4),
        "retrieval_entropy_bits": round(entropy, 4),
        "unique_document_id_coverage": {
            "total_unique_in_top_n": len(unique_doc_ids_global),
            "per_query_unique_min": min(per_query_unique) if per_query_unique else 0,
            "per_query_unique_max": max(per_query_unique) if per_query_unique else 0,
            "per_query_unique_avg": round(sum(per_query_unique) / len(per_query_unique), 2) if per_query_unique else 0,
        },
        "score_distribution": {
            "top_score_per_query_avg": round(avg_top_score, 4),
            "all_top_scores_flat": [s for scores in all_top_scores for s in scores],
        },
        "ticker_distribution": dict(ticker_counts.most_common(20)),
    }
    return report


def main() -> None:
    if not getattr(settings, "enable_embeddings", True) or not getattr(settings, "enable_qdrant", True):
        print("RAG is disabled (embeddings or qdrant). Set enable_embeddings and enable_qdrant.", file=sys.stderr)
        sys.exit(2)

    report = run()

    print("=== Retrieval distribution report (read-only) ===\n")
    print("Ticker dominance (top ticker share %):")
    print(f"  top_ticker:           {report['ticker_dominance']['top_ticker']}")
    print(f"  top_ticker_share_pct: {report['ticker_dominance']['top_ticker_share_pct']}%")
    print(f"  total_ticker_slots:   {report['ticker_dominance']['total_ticker_slots']}")
    print("\nAverage top score:")
    print(f"  {report['average_top_score']}")
    print("\nRetrieval entropy (Shannon, bits):")
    print(f"  {report['retrieval_entropy_bits']}")
    print("\nUnique document_id coverage (top-N across all queries):")
    cov = report["unique_document_id_coverage"]
    print(f"  total_unique_in_top_n: {cov['total_unique_in_top_n']}")
    print(f"  per_query unique: min={cov['per_query_unique_min']}, max={cov['per_query_unique_max']}, avg={cov['per_query_unique_avg']}")
    print("\nTicker distribution (top 20):")
    for t, c in list(report["ticker_distribution"].items())[:20]:
        print(f"  {t}: {c}")

    out = REPO_ROOT / "reports" / "inspect_retrieval_distribution_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to {out}")


if __name__ == "__main__":
    main()
