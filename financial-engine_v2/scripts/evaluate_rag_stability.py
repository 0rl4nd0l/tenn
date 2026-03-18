#!/usr/bin/env python3
"""
Evaluate RAG stability: run fixed test queries against POST /rag/query,
save results, and optionally compare to a previous run (rank/score drift).

Read-only: does not modify DB, Qdrant, or backend.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Script lives in financial-engine_v2/scripts/
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports" / "rag_stability"
LATEST_SUMMARY_PATH = REPORTS_DIR / "latest_summary.json"

# Fixed list of 15 test queries
TEST_QUERIES = [
    "What are the key risks to the business?",
    "How do margins compare to prior year?",
    "What is the company's leverage and debt level?",
    "How is capital allocated between dividends and buybacks?",
    "What were earnings and profitability trends?",
    "What is management's view on growth opportunities?",
    "What guidance did management provide for the next period?",
    "How strong is the company's liquidity position?",
    "What are the main drivers of cash flow?",
    "What strategic risks does the company face?",
    "Risk factors and mitigation strategies",
    "Operating margins and cost structure",
    "Debt covenants and refinancing risk",
    "Capital allocation priorities and M&A",
    "Free cash flow and cash conversion",
]

BACKEND_URL_DEFAULT = "http://localhost:8000"
TOP_K = 5
REQUEST_TIMEOUT = 30.0


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _backend_url() -> str:
    return (os.environ.get("BACKEND_URL") or os.environ.get("COCKPIT_BACKEND_API_URL") or BACKEND_URL_DEFAULT).strip().rstrip("/")


def run_query(base_url: str, query: str) -> dict:
    """POST /rag/query and return parsed payload. Raises on HTTP error."""
    url = f"{base_url}/rag/query"
    payload = {"query": query.strip(), "ticker": None, "top_k": TOP_K}
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json() if response.content else {}


def capture_result(query: str, payload: dict) -> dict:
    """Extract query, top_5_document_ids, top_5_scores, candidate_count, filtered_count."""
    hits = payload.get("hits") or []
    top5 = hits[:TOP_K]
    return {
        "query": query,
        "top_5_document_ids": [str(h.get("document_id") or "") for h in top5],
        "top_5_scores": [float(h.get("score") or 0.0) for h in top5],
        "candidate_count": payload.get("candidate_count", 0),
        "filtered_count": payload.get("filtered_count", 0),
    }


def load_previous_run(reports_dir: Path) -> dict | None:
    """Load the most recent previous run (by timestamp in filename). Returns None if none."""
    if not reports_dir.exists():
        return None
    json_files = sorted(reports_dir.glob("*.json"), reverse=True)
    # Skip current run if we're about to write it (compare only to strictly earlier runs)
    for path in json_files:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("results") is not None:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def compare_runs(prev: dict, curr: dict) -> dict:
    """Compare current run to previous: rank drift, score drift, missing/new hits."""
    prev_results = {r["query"]: r for r in prev.get("results") or []}
    curr_results = {r["query"]: r for r in curr.get("results") or []}
    queries = sorted(set(prev_results) & set(curr_results))
    rank_drifts: list[float] = []
    score_drifts: list[float] = []
    max_score_drift = 0.0
    queries_with_drift = 0
    large_drift_queries: list[str] = []
    missing_hits: dict[str, list[str]] = {}
    new_hits: dict[str, list[str]] = {}

    for q in queries:
        pr = prev_results[q]
        cr = curr_results[q]
        prev_ids = (pr.get("top_5_document_ids") or [])[:TOP_K]
        curr_ids = (cr.get("top_5_document_ids") or [])[:TOP_K]
        prev_scores = (pr.get("top_5_scores") or [])[:TOP_K]
        curr_scores = (cr.get("top_5_scores") or [])[:TOP_K]

        # Pad to length 5 for comparison
        while len(prev_ids) < TOP_K:
            prev_ids.append("")
            prev_scores.append(0.0)
        while len(curr_ids) < TOP_K:
            curr_ids.append("")
            curr_scores.append(0.0)

        # Rank drift: count positions where document_id changed
        positions_changed = sum(1 for i in range(TOP_K) if prev_ids[i] != curr_ids[i])
        rank_drifts.append(positions_changed)
        if positions_changed > 0:
            queries_with_drift += 1

        # Score drift: absolute difference per position
        for i in range(TOP_K):
            d = abs(curr_scores[i] - prev_scores[i])
            score_drifts.append(d)
            if d > max_score_drift:
                max_score_drift = d

        # Large drift: >20% (interpret as >20% of positions changed, i.e. >1 of 5)
        if positions_changed / TOP_K > 0.2:
            large_drift_queries.append(q)

        # Missing previous hits: in prev top 5 but not in curr top 5
        prev_set = {x for x in prev_ids if x}
        curr_set = {x for x in curr_ids if x}
        missing = list(prev_set - curr_set)
        new = list(curr_set - prev_set)
        if missing:
            missing_hits[q] = missing
        if new:
            new_hits[q] = new

    n_queries = len(queries)
    n_positions = n_queries * TOP_K
    avg_rank_drift = sum(rank_drifts) / n_queries if n_queries else 0.0
    avg_score_drift = sum(score_drifts) / n_positions if n_positions else 0.0
    pct_queries_with_drift = (100.0 * queries_with_drift / n_queries) if n_queries else 0.0

    return {
        "avg_rank_drift": round(avg_rank_drift, 4),
        "avg_score_drift": round(avg_score_drift, 4),
        "max_score_drift": round(max_score_drift, 4),
        "pct_queries_with_drift": round(pct_queries_with_drift, 2),
        "queries_with_large_drift": large_drift_queries,
        "missing_previous_hits": missing_hits,
        "new_hits": new_hits,
        "compared_queries": n_queries,
    }


def write_latest_summary(
    reports_dir: Path,
    timestamp: str,
    comparison: dict | None,
) -> None:
    """Write a compact, stable JSON summary for dashboard consumption."""
    if comparison is not None:
        summary = {
            "avg_rank_drift": comparison["avg_rank_drift"],
            "avg_score_drift": comparison["avg_score_drift"],
            "drift_percentage": comparison["pct_queries_with_drift"],
            "timestamp": timestamp,
        }
    else:
        summary = {
            "avg_rank_drift": None,
            "avg_score_drift": None,
            "drift_percentage": None,
            "timestamp": timestamp,
        }
    path = reports_dir / "latest_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=0)


def main() -> int:
    reports_dir = REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _utc_timestamp()
    out_path = reports_dir / f"{timestamp}.json"

    base_url = _backend_url()
    results: list[dict] = []
    any_zero_hits = False

    print(f"Backend: {base_url}")
    print(f"Queries: {len(TEST_QUERIES)}")
    print(f"Output:  {out_path}")

    for query in TEST_QUERIES:
        try:
            payload = run_query(base_url, query)
        except httpx.HTTPStatusError as e:
            print(f"Error querying '{query[:50]}...': HTTP {e.response.status_code}", file=sys.stderr)
            raise SystemExit(2) from e
        except Exception as e:
            print(f"Error querying '{query[:50]}...': {e}", file=sys.stderr)
            raise SystemExit(2) from e

        rec = capture_result(query, payload)
        results.append(rec)
        if (payload.get("filtered_count") or 0) == 0:
            any_zero_hits = True

    report = {
        "timestamp": timestamp,
        "backend_url": base_url,
        "top_k": TOP_K,
        "results": results,
    }

    prev = load_previous_run(reports_dir)
    if prev is not None:
        comparison = compare_runs(prev, report)
        report["comparison"] = comparison
        avg_rank_drift = comparison["avg_rank_drift"]
        avg_score_drift = comparison["avg_score_drift"]
        max_score_drift = comparison["max_score_drift"]
        pct_drift = comparison["pct_queries_with_drift"]
        large = comparison["queries_with_large_drift"]

        print("\n--- Stability summary (vs previous run) ---")
        print(f"  avg_rank_drift:        {avg_rank_drift:.4f}")
        print(f"  avg_score_drift:       {avg_score_drift:.4f}")
        print(f"  max_score_drift:       {max_score_drift:.4f}")
        print(f"  % queries with drift:  {pct_drift:.2f}%")
        print(f"  queries with large drift (>20%): {len(large)}")
        for q in large:
            print(f"    - {q[:70]}...")
        if comparison.get("missing_previous_hits"):
            print("  missing_previous_hits (sample):", list(comparison["missing_previous_hits"].items())[:3])
        if comparison.get("new_hits"):
            print("  new_hits (sample):", list(comparison["new_hits"].items())[:3])

    else:
        print("\nNo previous run found; skipping comparison.")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {out_path}")

    comparison = report.get("comparison")
    write_latest_summary(reports_dir, timestamp, comparison)
    print(f"Wrote {LATEST_SUMMARY_PATH}")

    # Exit non-zero conditions (after writing report)
    if any_zero_hits:
        print("Exit: at least one query returned 0 hits.", file=sys.stderr)
        return 1
    if prev is not None:
        comp = report.get("comparison", {})
        if comp.get("avg_rank_drift", 0) > 2:
            print(f"Exit: avg_rank_drift {comp['avg_rank_drift']} > 2.", file=sys.stderr)
            return 1
        if comp.get("avg_score_drift", 0) > 0.15:
            print(f"Exit: avg_score_drift {comp['avg_score_drift']} > 0.15.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
