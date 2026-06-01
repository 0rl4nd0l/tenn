#!/usr/bin/env python3
"""
broad_extraction_test.py — Robustness test for multipass extraction across
hundreds of random ASX financial filings.

NOT an accuracy test (no ground truth). Measures:
  - Crash rate, status distribution, error classification
  - Per-metric coverage (how often each metric is non-null)
  - Structural validity (period_end, period_type, scale)
  - Sanity checks (revenue > 0, shares > 0 when present)
  - Timing: per-doc P50/P95/P99

Usage:
  python scripts/broad_extraction_test.py --count 200 --seed 42
  python scripts/broad_extraction_test.py --count 20 --docs-root /data/asx/docs
  python scripts/broad_extraction_test.py --count 50 --resume   # pick up where left off
  python scripts/broad_extraction_test.py --count 200 --anthropic  # use Anthropic API

Requires: llama.cpp on :8001 (or --anthropic flag with ANTHROPIC_API_KEY set)
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import random
import statistics
import sys
import time
import traceback
from pathlib import Path, PurePosixPath

# Add backend to path so we can import app.services
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

# Ensure extraction routes to the correct llama.cpp endpoint.
# Router mode: single server on 8001 handles both chat and extraction.
# EXTRACTION_LLAMACPP_URL is legacy; defaults to LLAMACPP_URL when unset.
if not os.environ.get("EXTRACTION_LLAMACPP_URL"):
    os.environ["EXTRACTION_LLAMACPP_URL"] = os.environ.get("LLAMACPP_URL", "http://127.0.0.1:8001")

# Auto-detect LLM_API_KEY from llama-server process args if not already set
if not os.environ.get("LLM_API_KEY"):
    import subprocess as _sp
    try:
        _ps = _sp.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5,
        )
        for _line in _ps.stdout.splitlines():
            if "llama-server" in _line and "--api-key" in _line:
                _parts = _line.split("--api-key")
                if len(_parts) > 1:
                    _key = _parts[1].strip().split()[0]
                    os.environ["LLM_API_KEY"] = _key
                    break
    except Exception:
        pass
# Suppress noisy loggers during bulk runs
for name in ("httpx", "httpcore", "urllib3", "app.services.llm"):
    logging.getLogger(name).setLevel(logging.ERROR)

METRIC_FIELDS = [
    "revenue", "ebit", "np_attributable",
    "operating_cf", "investing_cf", "financing_cf",
    "capex", "cash_end", "net_debt", "shares_outstanding",
]

DEFAULT_DOCS_ROOT = _REPO_ROOT / "data" / "asx" / "docs"
HOST_DOCS_ROOT = Path("/data/asx/docs")
RESULTS_DIR = _REPO_ROOT / "scripts" / "broad_test_results"


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in paths:
        key = str(path.expanduser().resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path.expanduser())
    return deduped


def _candidate_docs_roots(explicit_docs_root: str | Path | None = None) -> list[Path]:
    explicit = str(explicit_docs_root or "").strip()
    if explicit:
        return _dedupe_paths([Path(explicit)])

    candidates: list[Path] = []
    env_docs_root = os.environ.get("DOCS_ROOT", "").strip()
    if env_docs_root:
        candidates.append(Path(env_docs_root))

    data_root = os.environ.get("DATA_ROOT", "").strip()
    if data_root:
        candidates.append(Path(data_root) / "asx" / "docs")

    candidates.extend([DEFAULT_DOCS_ROOT, HOST_DOCS_ROOT])
    return _dedupe_paths(candidates)


def _scan_financial_performance_pdfs(docs_root: Path) -> list[Path]:
    if not docs_root.is_dir():
        return []
    return sorted(docs_root.glob("*/financial_performance/*.pdf"))


def _root_has_financial_pdfs(docs_root: Path) -> bool:
    if not docs_root.is_dir():
        return False
    try:
        next(docs_root.glob("*/financial_performance/*.pdf"))
    except StopIteration:
        return False
    return True


def resolve_docs_root(explicit_docs_root: str | Path | None = None) -> Path:
    """Resolve the source-PDF root for broad robustness runs.

    An explicit root is authoritative even if empty, so callers can test or
    intentionally scope a run without falling through to host data.
    """

    candidates = _candidate_docs_roots(explicit_docs_root)
    if explicit_docs_root:
        return candidates[0]

    for candidate in candidates:
        if _root_has_financial_pdfs(candidate):
            return candidate
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return DEFAULT_DOCS_ROOT


def discover_pdfs(docs_root: str | Path | None = None) -> list[Path]:
    """Find all financial_performance PDFs across all tickers."""
    return _scan_financial_performance_pdfs(resolve_docs_root(docs_root))


def _source_path_for_record(
    pdf_path: Path,
    docs_root: str | Path | None = None,
) -> str:
    path = Path(pdf_path)
    root = resolve_docs_root(docs_root).resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    try:
        relative_to_docs = resolved_path.relative_to(root)
    except ValueError:
        try:
            return str(path.relative_to(_REPO_ROOT))
        except ValueError:
            return str(path)
    return PurePosixPath("data/asx/docs", *relative_to_docs.parts).as_posix()


def _ticker_from_path(pdf_path: Path) -> str:
    """Extract ticker from path like .../BHP/financial_performance/xxx.pdf"""
    return pdf_path.parent.parent.name


def _doc_id_from_path(pdf_path: Path) -> str:
    """Extract document_id UUID from filename (last segment before .pdf)."""
    stem = pdf_path.stem
    parts = stem.rsplit("_", 1)
    return parts[-1] if len(parts) > 1 else stem


def make_llm_client(use_anthropic: bool):
    """Create an LLM client for extraction."""
    if use_anthropic:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("ERROR: --anthropic requires ANTHROPIC_API_KEY env var", file=sys.stderr)
            sys.exit(1)
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("EVAL_CLAUDE_MODEL", "claude-sonnet-4-20250514")
        client._extraction_model = model
        print(f"Using Anthropic API ({model})")
        return client
    else:
        import httpx
        base_url = os.environ.get("LLAMACPP_URL", "http://127.0.0.1:8001")
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        headers = {}
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not api_key:
            # Try reading OpenClaw gateway token
            openclaw_cfg = Path.home() / ".openclaw" / "openclaw.json"
            if openclaw_cfg.exists():
                try:
                    cfg = json.loads(openclaw_cfg.read_text())
                    api_key = cfg.get("gateway", {}).get("auth", {}).get("token", "")
                except Exception:
                    pass
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        client = httpx.Client(base_url=base_url, timeout=120.0, headers=headers)
        # Quick health check
        try:
            r = client.get("/models")
            r.raise_for_status()
        except Exception as e:
            print(f"ERROR: llama.cpp not reachable at {base_url}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Using llama.cpp at {base_url}")
        return client


def run_one(
    pdf_path: Path,
    llm_client,
    *,
    docs_root: str | Path | None = None,
) -> dict:
    """Run extraction on a single PDF. Returns result dict."""
    from app.services.multipass_extraction import run_multipass_extraction

    ticker = _ticker_from_path(pdf_path)
    doc_id = _doc_id_from_path(pdf_path)
    doc_metadata = {
        "document_id": doc_id,
        "ticker": ticker,
        "title": pdf_path.name,
    }

    record = {
        "pdf_path": _source_path_for_record(pdf_path, docs_root),
        "ticker": ticker,
        "document_id": doc_id,
        "status": None,
        "error": None,
        "elapsed_s": None,
        "metrics": {},
        "period_type": None,
        "period_end": None,
        "scale": None,
        "confidence": None,
        "non_null_metrics": 0,
        "table_count": None,
        "page_count": None,
        "sanity": {},
    }

    t0 = time.monotonic()
    try:
        result = run_multipass_extraction(
            str(pdf_path), doc_metadata, llm_client, skip_narrative=True,
        )
        elapsed = time.monotonic() - t0
        record["elapsed_s"] = round(elapsed, 2)
        record["status"] = result.status
        record["error"] = result.error

        payload = result.payload or {}
        metrics = payload.get("metrics", {})
        record["metrics"] = {k: metrics.get(k) for k in METRIC_FIELDS}
        record["period_type"] = payload.get("period_type")
        record["period_end"] = str(payload.get("period_end")) if payload.get("period_end") else None
        record["scale"] = payload.get("scale")
        record["confidence"] = payload.get("confidence_metrics")
        record["non_null_metrics"] = sum(1 for v in metrics.values() if v is not None)

        # Sanity checks (only when metric is present)
        sanity = {}
        if metrics.get("revenue") is not None:
            sanity["revenue_positive"] = metrics["revenue"] > 0
        if metrics.get("shares_outstanding") is not None:
            sanity["shares_positive"] = metrics["shares_outstanding"] > 0
        if metrics.get("cash_end") is not None:
            sanity["cash_end_positive"] = metrics["cash_end"] > 0
        pe = payload.get("period_end")
        if pe:
            sanity["period_end_valid"] = pe not in (None, "None", "")
        pt = payload.get("period_type")
        if pt:
            sanity["period_type_valid"] = pt in ("A", "H", "Q")
        record["sanity"] = sanity

    except Exception as e:
        elapsed = time.monotonic() - t0
        record["elapsed_s"] = round(elapsed, 2)
        record["status"] = "exception"
        record["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)

    return record


def compute_summary(results: list[dict]) -> dict:
    """Compute aggregate stats from all results."""
    total = len(results)
    if total == 0:
        return {
            "total": 0,
            "status_distribution": {},
            "success_rate": 0,
            "error_classification": {},
            "metric_coverage": {
                metric: {"present": 0, "total": 0, "rate": 0}
                for metric in METRIC_FIELDS
            },
            "nonnull_metric_distribution": {},
            "timing": {},
            "sanity_checks": {
                check_name: {"passed": 0, "total": 0, "rate": 0}
                for check_name in (
                    "revenue_positive",
                    "shares_positive",
                    "cash_end_positive",
                    "period_end_valid",
                    "period_type_valid",
                )
            },
            "unique_tickers": 0,
            "period_type_distribution": {},
            "scale_distribution": {},
        }

    # Status distribution
    status_counts: dict[str, int] = {}
    for r in results:
        s = r["status"] or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    # Error classification
    error_classes: dict[str, int] = {}
    for r in results:
        err = r.get("error")
        if err:
            # Classify by prefix
            if err.startswith("pass1:"):
                cls = "pass1_failure"
            elif "low_confidence" in err:
                cls = "classifier_low_confidence"
            elif "timeout" in err.lower() or "sigalrm" in err.lower():
                cls = "timeout"
            elif "Exception" in (r["status"] or ""):
                cls = "python_exception"
            else:
                cls = err.split(":")[0] if ":" in err else "other"
            error_classes[cls] = error_classes.get(cls, 0) + 1

    # Metric coverage (across non-failed results)
    ok_results = [r for r in results if r["status"] in ("ok", "ok_low_confidence")]
    metric_coverage: dict[str, dict] = {}
    for m in METRIC_FIELDS:
        present = sum(1 for r in ok_results if r["metrics"].get(m) is not None)
        metric_coverage[m] = {
            "present": present,
            "total": len(ok_results),
            "rate": round(present / len(ok_results), 4) if ok_results else 0,
        }

    # Non-null metric count distribution
    nonnull_counts = [r["non_null_metrics"] for r in ok_results]
    nonnull_dist = {}
    if nonnull_counts:
        nonnull_dist = {
            "mean": round(statistics.mean(nonnull_counts), 2),
            "median": statistics.median(nonnull_counts),
            "min": min(nonnull_counts),
            "max": max(nonnull_counts),
        }

    # Timing stats
    timings = [r["elapsed_s"] for r in results if r["elapsed_s"] is not None]
    timing_stats = {}
    if timings:
        timings_sorted = sorted(timings)
        timing_stats = {
            "mean_s": round(statistics.mean(timings), 2),
            "median_s": round(statistics.median(timings), 2),
            "p95_s": round(timings_sorted[int(len(timings_sorted) * 0.95)], 2),
            "p99_s": round(timings_sorted[int(len(timings_sorted) * 0.99)], 2),
            "min_s": round(min(timings), 2),
            "max_s": round(max(timings), 2),
            "total_s": round(sum(timings), 1),
        }

    # Sanity check pass rates
    sanity_stats: dict[str, dict] = {}
    for check_name in ("revenue_positive", "shares_positive", "cash_end_positive",
                       "period_end_valid", "period_type_valid"):
        applicable = [r for r in ok_results if check_name in r.get("sanity", {})]
        passed = sum(1 for r in applicable if r["sanity"][check_name])
        sanity_stats[check_name] = {
            "passed": passed,
            "total": len(applicable),
            "rate": round(passed / len(applicable), 4) if applicable else 0,
        }

    # Ticker diversity
    tickers = set(r["ticker"] for r in results)
    period_types = {}
    for r in ok_results:
        pt = r.get("period_type") or "unknown"
        period_types[pt] = period_types.get(pt, 0) + 1

    # Scale distribution
    scales = {}
    for r in ok_results:
        sc = r.get("scale") or "unknown"
        scales[sc] = scales.get(sc, 0) + 1

    return {
        "total": total,
        "status_distribution": status_counts,
        "success_rate": round(len(ok_results) / total, 4),
        "error_classification": error_classes,
        "metric_coverage": metric_coverage,
        "nonnull_metric_distribution": nonnull_dist,
        "timing": timing_stats,
        "sanity_checks": sanity_stats,
        "unique_tickers": len(tickers),
        "period_type_distribution": period_types,
        "scale_distribution": scales,
    }


def print_summary(summary: dict) -> None:
    """Print human-readable summary to console."""
    total = summary["total"]
    print(f"\n{'='*70}")
    print(f"  BROAD EXTRACTION TEST — {total} documents")
    print(f"{'='*70}\n")

    # Status
    print("STATUS DISTRIBUTION:")
    for status, count in sorted(summary["status_distribution"].items()):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {status:25s} {count:4d} ({pct:5.1f}%) {bar}")

    sr = summary["success_rate"]
    print(f"\n  Success rate: {sr:.1%}")

    # Errors
    if summary["error_classification"]:
        print(f"\nERROR CLASSIFICATION:")
        for cls, count in sorted(summary["error_classification"].items(), key=lambda x: -x[1]):
            print(f"  {cls:35s} {count:4d}")

    # Metric coverage
    print(f"\nMETRIC COVERAGE (across {summary['status_distribution'].get('ok', 0) + summary['status_distribution'].get('ok_low_confidence', 0)} successful extractions):")
    for m, stats in summary["metric_coverage"].items():
        rate = stats["rate"]
        bar = "█" * int(rate * 30)
        print(f"  {m:22s} {stats['present']:4d}/{stats['total']:4d} ({rate:5.1%}) {bar}")

    # Non-null distribution
    nd = summary.get("nonnull_metric_distribution", {})
    if nd:
        print(f"\n  Non-null metrics per doc: mean={nd['mean']:.1f}, median={nd['median']}, range=[{nd['min']},{nd['max']}]")

    # Sanity checks
    print(f"\nSANITY CHECKS:")
    for check, stats in summary["sanity_checks"].items():
        rate = stats["rate"]
        if stats["total"] == 0:
            label = "N/A"
        elif rate >= 0.95:
            label = "PASS"
        elif rate >= 0.80:
            label = "WARN"
        else:
            label = "FAIL"
        print(f"  {check:25s} {stats['passed']:4d}/{stats['total']:4d} ({rate:5.1%}) [{label}]")

    # Period type + scale
    print(f"\nPERIOD TYPE DISTRIBUTION:")
    for pt, count in sorted(summary.get("period_type_distribution", {}).items()):
        print(f"  {pt:5s} {count:4d}")

    print(f"\nSCALE DISTRIBUTION:")
    for sc, count in sorted(summary.get("scale_distribution", {}).items()):
        print(f"  {sc:15s} {count:4d}")

    # Timing
    ts = summary.get("timing", {})
    if ts:
        print(f"\nTIMING:")
        print(f"  Mean: {ts['mean_s']:.1f}s  Median: {ts['median_s']:.1f}s  P95: {ts['p95_s']:.1f}s  P99: {ts['p99_s']:.1f}s")
        print(f"  Range: [{ts['min_s']:.1f}s, {ts['max_s']:.1f}s]  Total: {ts['total_s']:.0f}s ({ts['total_s']/60:.1f}min)")

    print(f"\n  Unique tickers sampled: {summary['unique_tickers']}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Broad extraction robustness test")
    parser.add_argument("--count", type=int, default=200, help="Number of PDFs to sample (default: 200)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--resume", action="store_true", help="Resume from existing results file")
    parser.add_argument("--anthropic", action="store_true", help="Use Anthropic API instead of local llama.cpp")
    parser.add_argument("--output-dir", type=str, default=str(RESULTS_DIR), help="Output directory for results")
    parser.add_argument(
        "--docs-root",
        default=None,
        help=(
            "Root containing ASX filing PDFs. Defaults to DOCS_ROOT, "
            "DATA_ROOT/asx/docs, repo-local data/asx/docs, then /data/asx/docs."
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = output_dir / f"broad_test_{ts}.json"

    # Discover all PDFs
    print("Discovering PDFs...")
    docs_root = resolve_docs_root(args.docs_root)
    all_pdfs = discover_pdfs(docs_root)
    print(f"Using docs root: {docs_root}")
    print(f"Found {len(all_pdfs)} financial_performance PDFs across {len(set(_ticker_from_path(p) for p in all_pdfs))} tickers")

    # Sample
    rng = random.Random(args.seed)
    sample_size = min(args.count, len(all_pdfs))
    sample = rng.sample(all_pdfs, sample_size)
    print(f"Sampled {sample_size} PDFs (seed={args.seed})")

    # Resume: load existing results and skip already-processed paths
    existing_results: list[dict] = []
    processed_paths: set[str] = set()
    if args.resume:
        # Find most recent results file
        existing_files = sorted(output_dir.glob("broad_test_*.json"), reverse=True)
        if existing_files:
            latest = existing_files[0]
            print(f"Resuming from {latest.name}")
            data = json.loads(latest.read_text())
            existing_results = data.get("results", [])
            processed_paths = {r["pdf_path"] for r in existing_results}
            results_path = latest  # overwrite same file
            print(f"  Already processed: {len(processed_paths)}")

    # Run extraction
    results = list(existing_results)
    remaining = [p for p in sample if _source_path_for_record(p, docs_root) not in processed_paths]
    total_remaining = len(remaining)

    if total_remaining == 0:
        print("All samples already processed. Nothing to do.")
    else:
        print(f"\nRunning extraction on {total_remaining} PDFs...")
        print(f"Estimated time: ~{total_remaining * 45 / 60:.0f} min (at ~45s/doc with llama.cpp)\n")

    llm_client = make_llm_client(args.anthropic) if total_remaining > 0 else None

    for i, pdf_path in enumerate(remaining):
        if llm_client is None:
            raise RuntimeError("LLM client was not initialized for a non-empty run")
        ticker = _ticker_from_path(pdf_path)
        done_total = len(results)
        elapsed_total = sum(r["elapsed_s"] for r in results if r["elapsed_s"]) or 0.001
        avg_per_doc = elapsed_total / max(done_total, 1)
        eta_s = avg_per_doc * (total_remaining - i)

        print(f"[{i+1}/{total_remaining}] {ticker}/{pdf_path.name[:50]}...", end="", flush=True)

        record = run_one(pdf_path, llm_client, docs_root=docs_root)
        results.append(record)

        status = record["status"]
        elapsed = record["elapsed_s"] or 0
        nn = record["non_null_metrics"]
        emoji = {"ok": "OK", "ok_low_confidence": "LC", "failed": "FL", "exception": "EX"}.get(status, "??")

        print(f" [{emoji}] {elapsed:.1f}s  metrics={nn}/10  ETA={eta_s/60:.0f}min")

        # Incremental save (crash-safe)
        if (i + 1) % 5 == 0 or i == total_remaining - 1:
            summary = compute_summary(results)
            report = {
                "run_metadata": {
                    "timestamp": ts,
                    "seed": args.seed,
                    "requested_count": args.count,
                    "actual_count": len(results),
                    "backend": "anthropic" if args.anthropic else "llamacpp",
                    "docs_root": str(docs_root),
                },
                "summary": summary,
                "results": results,
            }
            results_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Final summary
    summary = compute_summary(results)
    report = {
        "run_metadata": {
            "timestamp": ts,
            "seed": args.seed,
            "requested_count": args.count,
            "actual_count": len(results),
            "backend": "anthropic" if args.anthropic else "llamacpp",
            "docs_root": str(docs_root),
        },
        "summary": summary,
        "results": results,
    }
    results_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print_summary(summary)
    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    main()
