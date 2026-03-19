#!/usr/bin/env python3
"""
Run extract_financial_metrics on multiple ticker PDF dirs and summarize.
Uses full ticker directory (all subfolders) so prospectus, appendix, etc. are all scanned.
Validates canonical output: ISO statement_period_end and no conflicting values per (logical_doc, period, metric).

Usage:
  python scripts/run_extract_broad_tickers.py --max-tickers 20
  python scripts/run_extract_broad_tickers.py --max-tickers 50 --max-pdfs-per-ticker 300   # skip huge dirs
  python scripts/run_extract_broad_tickers.py --max-tickers 10 --timeout-per-ticker 900   # long timeout per ticker
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "financial-engine_v2" / "data" / "asx" / "docs"
OUT_DIR = ROOT / "reports" / "broad_ticker_test"

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Logical doc: filename stem without UUID so duplicate PDFs (same report, different UUID) group together
LOGICAL_DOC_RE = re.compile(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$", re.I)


def find_ticker_dirs_with_pdfs(max_tickers=None, max_pdfs_per_ticker=None):
    """Find ticker dirs that contain at least one PDF (any subfolder). Uses full ticker path for extraction.
    If max_pdfs_per_ticker is set, only include tickers with PDF count <= that limit (avoids blocking on huge dirs)."""
    if not DOCS.exists():
        return []
    out = []
    for ticker_dir in sorted(DOCS.iterdir()):
        if not ticker_dir.is_dir():
            continue
        pdfs = list(ticker_dir.rglob("*.pdf"))
        n = len(pdfs)
        if n == 0:
            continue
        if max_pdfs_per_ticker is not None and n > max_pdfs_per_ticker:
            continue
        out.append((ticker_dir.name, str(ticker_dir), n))
        if max_tickers and len(out) >= max_tickers:
            break
    return out


def _logical_doc(file_path: str) -> str:
    """Return logical document key: path with UUID suffix removed so duplicate PDFs (same report) group together."""
    if not file_path:
        return file_path
    return LOGICAL_DOC_RE.sub(".pdf", file_path)


def validate_canonical_logic(rows: list) -> dict:
    """Check canonical output for accuracy and logic: ISO period_end, no conflicting same-key values.
    Conflict key is (logical_doc, period, metric) so duplicate PDFs (same report, different UUID) that
    agree on value are not flagged; only real inconsistencies (same report, different values) are."""
    issues = []
    period_ok = 0
    period_bad = 0
    for r in rows:
        period_end = (r.get("statement_period_end") or "").strip()
        if not period_end:
            continue
        if ISO_DATE_RE.match(period_end):
            period_ok += 1
        else:
            period_bad += 1
            issues.append(f"Non-ISO statement_period_end: {period_end!r} in {r.get('file', '')!r} metric={r.get('metric')}")
    # Conflict = same (logical_doc, period, metric) with different values (normalize numbers)
    def _norm_val(v):
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return v

    key_to_values = {}
    for r in rows:
        logical = _logical_doc(r.get("file") or "")
        k = (logical, r.get("statement_period_end"), r.get("metric"))
        v = r.get("value")
        key_to_values.setdefault(k, []).append(v)
    distinct = {k: len(set(_norm_val(v) for v in vals if _norm_val(v) is not None)) for k, vals in key_to_values.items()}
    conflicts = [k for k, cnt in distinct.items() if cnt > 1]
    for k in conflicts:
        vals = key_to_values[k]
        unique = sorted(set(_norm_val(v) for v in vals if _norm_val(v) is not None))
        issues.append(f"Conflicting values for doc={k[0]!r} period={k[1]!r} metric={k[2]!r}: {unique}")
    return {
        "period_ok": period_ok,
        "period_bad": period_bad,
        "conflicts": len(conflicts),
        "issues": issues[:20],
        "valid": period_bad == 0 and len(conflicts) == 0,
    }


def run_extract(pdf_dir: str, out_prefix: Path, timeout_seconds: int = 600) -> dict:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = out_prefix / "canonical.csv"
    json_path = out_prefix / "canonical.json"
    ctx_csv = out_prefix / "context.csv"
    ctx_json = out_prefix / "context.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "extract_financial_metrics.py"),
        "--pdf-dir", pdf_dir,
        "--out-csv", str(csv_path),
        "--out-json", str(json_path),
        "--out-context-csv", str(ctx_csv),
        "--out-context-json", str(ctx_json),
        "--no-sqlite",
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        # Treat "no metric candidates" (e.g. scanned PDFs, unexpected format) as success with 0 rows
        no_candidates = "No metric candidates found" in (result.stdout or "") or "No metric candidates found" in (result.stderr or "")
        summary = {
            "ok": result.returncode == 0 or (result.returncode == 1 and no_candidates),
            "returncode": result.returncode,
        }
        if result.stderr:
            summary["stderr_lines"] = result.stderr.strip().split("\n")[-5:]
        if not summary["ok"] and result.stdout:
            summary["stdout_tail"] = result.stdout.strip().split("\n")[-5:]
        if no_candidates and result.returncode == 1:
            summary["no_metric_candidates"] = True
        if json_path.exists():
            with open(json_path) as f:
                rows = json.load(f)
            summary["canonical_rows"] = len(rows)
            metrics = {}
            for r in rows:
                m = r.get("metric", "")
                metrics[m] = metrics.get(m, 0) + 1
            summary["metrics_seen"] = metrics
            validation = validate_canonical_logic(rows)
            summary["validation"] = validation
            if not validation["valid"]:
                summary["validation_issues"] = validation["issues"]
        else:
            summary["canonical_rows"] = 0
        if summary.get("no_metric_candidates"):
            summary["canonical_rows"] = 0
        if ctx_json.exists():
            with open(ctx_json) as f:
                summary["context_rows"] = len(json.load(f))
        else:
            summary["context_rows"] = 0
        return summary
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "returncode": -1, "error": str(e)}


def main():
    ap = argparse.ArgumentParser(description="Run PDF extraction across multiple tickers (full ticker dir)")
    ap.add_argument("--max-tickers", type=int, default=20, help="Max ticker dirs to run (default 20)")
    ap.add_argument("--max-pdfs-per-ticker", type=int, default=None, help="Skip tickers with more than N PDFs (avoids long runs)")
    ap.add_argument("--timeout-per-ticker", type=int, default=600, help="Timeout per ticker in seconds (default 600)")
    ap.add_argument("--out-dir", default=str(OUT_DIR), help="Output base dir")
    args = ap.parse_args()

    tickers = find_ticker_dirs_with_pdfs(max_tickers=args.max_tickers, max_pdfs_per_ticker=args.max_pdfs_per_ticker)
    if not tickers:
        print("No ticker dirs with PDFs found under", DOCS, file=sys.stderr)
        return 2

    out_base = Path(args.out_dir)
    print(f"Running extraction for {len(tickers)} tickers (full dir each): {[t[0] for t in tickers]}")
    results = {}
    validation_failures = []
    for ticker, pdf_dir, pdf_count in tickers:
        out_prefix = out_base / ticker
        print(f"  {ticker} ({pdf_count} PDFs) ... ", end="", flush=True)
        summary = run_extract(pdf_dir, out_prefix, timeout_seconds=args.timeout_per_ticker)
        summary["pdf_count"] = pdf_count
        results[ticker] = summary
        if summary["ok"]:
            v = summary.get("validation", {})
            valid = v.get("valid", True)
            rows = summary.get("canonical_rows", 0)
            ctx = summary.get("context_rows", 0)
            if valid:
                print(f"ok rows={rows} context={ctx}")
            else:
                print(f"ok rows={rows} VALIDATION ISSUES")
                validation_failures.append((ticker, v.get("issues", [])))
        else:
            print(f"FAIL rc={summary.get('returncode')} {summary.get('error', '')}")

    # Summary
    ok = sum(1 for r in results.values() if r.get("ok"))
    total_rows = sum(r.get("canonical_rows", 0) for r in results.values())
    all_valid = not validation_failures
    print(f"\nDone: {ok}/{len(results)} tickers ok, {total_rows} total canonical rows")
    if validation_failures:
        print("Validation issues (accuracy/logic):")
        for t, issues in validation_failures:
            for i in issues[:5]:
                print(f"  {t}: {i}")
            if len(issues) > 5:
                print(f"  {t}: ... and {len(issues) - 5} more")
    if ok < len(results):
        for t, r in results.items():
            if not r.get("ok"):
                print(f"  {t}: {r.get('error', r.get('stderr_lines', []))}")
    return 0 if (ok == len(results) and all_valid) else 1


if __name__ == "__main__":
    raise SystemExit(main())
