#!/usr/bin/env python3
"""
Compare ASX coverage metrics between baseline and optimized quantification runs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return payload


def fnum(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def inum(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def build_comparison(*, baseline: Dict[str, Any], optimised: Dict[str, Any]) -> Dict[str, Any]:
    baseline_summary = baseline.get("asx_summary", {}) if isinstance(baseline.get("asx_summary"), dict) else {}
    optimised_summary = optimised.get("asx_summary", {}) if isinstance(optimised.get("asx_summary"), dict) else {}

    baseline_chunks_pct = fnum(baseline_summary.get("chunks_with_asx_ticker_pct"))
    optimised_chunks_pct = fnum(optimised_summary.get("chunks_with_asx_ticker_pct"))
    baseline_hits = inum(baseline_summary.get("tickers_with_hits"))
    optimised_hits = inum(optimised_summary.get("tickers_with_hits"))
    baseline_median = fnum(baseline_summary.get("median_articles_per_ticker"))
    optimised_median = fnum(optimised_summary.get("median_articles_per_ticker"))

    return {
        "baseline_chunks_with_asx_pct": round(baseline_chunks_pct, 4),
        "optimised_chunks_with_asx_pct": round(optimised_chunks_pct, 4),
        "baseline_tickers_with_hits": baseline_hits,
        "optimised_tickers_with_hits": optimised_hits,
        "coverage_delta_pct": round(optimised_chunks_pct - baseline_chunks_pct, 4),
        "median_articles_delta": round(optimised_median - baseline_median, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare ASX coverage JSON outputs from baseline and optimized runs.")
    ap.add_argument("--baseline-json", required=True, help="Baseline quantification JSON path")
    ap.add_argument("--optimised-json", required=True, help="Optimised quantification JSON path")
    ap.add_argument("--out-json", required=True, help="Output comparison JSON path")
    args = ap.parse_args()

    baseline_path = Path(args.baseline_json).expanduser().resolve()
    optimised_path = Path(args.optimised_json).expanduser().resolve()
    if not baseline_path.exists():
        print(f"Baseline JSON not found: {baseline_path}", file=sys.stderr)
        return 2
    if not optimised_path.exists():
        print(f"Optimised JSON not found: {optimised_path}", file=sys.stderr)
        return 2

    try:
        baseline = load_json(baseline_path)
        optimised = load_json(optimised_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report = build_comparison(baseline=baseline, optimised=optimised)
    out_path = Path(args.out_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
