#!/usr/bin/env python3
"""Incremental ticker expansion workflow for financial metric hardening.

This script is designed for slow, deterministic onboarding of new tickers.
For each ticker it can:
1) Select a bounded subset of latest PDFs.
2) Run baseline extraction (extract_financial_metrics.py).
3) Run section_capture_layer hardening pass.
4) Compute canonical hygiene checks.
5) Bootstrap gold templates for manual labeling.
6) Score against curated gold if ticker gold already exists.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.runtime_python import print_runtime_info, resolve_python


DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
DOC_ID_SUFFIX_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _extract_date_key(name: str) -> str:
    m = DATE_PREFIX_RE.match(str(name or "").strip())
    if m:
        return str(m.group(1))
    return "0000-00-00"


def _pdf_financial_relevance_score(name: str) -> int:
    text = str(name or "").strip().lower()
    if not text:
        return 0

    score = 0
    positive_weights: List[Tuple[str, int]] = [
        ("annual-report", 5),
        ("annual_report", 5),
        ("half-year", 5),
        ("half_year", 5),
        ("interim-report", 5),
        ("financial-report", 5),
        ("report-and-accounts", 5),
        ("appendix-4e", 4),
        ("appendix-4d", 4),
        ("form-20-f", 4),
        ("results-announcement", 4),
        ("full-year-results", 4),
        ("half-year-results", 4),
        ("preliminary-final-report", 4),
    ]
    negative_weights: List[Tuple[str, int]] = [
        ("agm", -6),
        ("annual-general-meeting", -6),
        ("voting-results", -5),
        ("chair-address", -4),
        ("webcast", -3),
        ("conference-call", -3),
        ("conference call", -3),
        ("media-release", -3),
        ("media_release", -3),
        ("notice-of", -3),
        ("results-of-meeting", -4),
    ]

    for token, weight in positive_weights:
        if token in text:
            score += int(weight)
    for token, weight in negative_weights:
        if token in text:
            score += int(weight)
    return int(score)


def _pdf_report_bucket(name: str) -> str:
    text = str(name or "").strip().lower()
    if not text:
        return "other"

    half_tokens = (
        "half-year",
        "half year",
        "half_year",
        "half-yearly",
        "half yearly",
        "interim-report",
        "interim report",
        "appendix-4d",
        "1h",
    )
    annual_tokens = (
        "annual-report",
        "annual report",
        "annual_report",
        "appendix-4e",
        "full-year",
        "full year",
        "preliminary-final-report",
        "form-20-f",
        "statutory-accounts-for-the-full-year",
    )

    if any(tok in text for tok in half_tokens):
        return "half"
    if any(tok in text for tok in annual_tokens):
        return "annual"
    return "other"


def _date_year(name: str) -> int:
    date_key = _extract_date_key(name)
    try:
        return int(date_key[:4])
    except Exception:
        return 0


def _annual_quality_tier(name: str) -> int:
    text = str(name or "").strip().lower()
    if "appendix-4e" in text:
        return 4
    if "annual-financial-report" in text or "financial-report" in text:
        return 3
    if "full-year-results" in text or "preliminary-final-report" in text:
        return 2
    if "annual-report" in text:
        return 1
    return 0


def _half_quality_tier(name: str) -> int:
    text = str(name or "").strip().lower()
    if "appendix-4d" in text:
        return 4
    if "half-year-financial-report" in text or "half-yearly-report" in text:
        return 3
    if "half-year-accounts" in text or "interim-report" in text:
        return 2
    if "half-year" in text or "interim" in text:
        return 1
    return 0


def _rank_key(name: str) -> Tuple[int, str, str]:
    return (
        _pdf_financial_relevance_score(name),
        _extract_date_key(name),
        name,
    )


def _doc_id_from_pdf_name(name: str) -> str:
    stem = Path(str(name or "")).stem
    m = DOC_ID_SUFFIX_RE.search(stem)
    if m:
        return str(m.group(1)).lower()
    return stem


def _ticker_from_file_path(path: Path) -> str:
    parts = path.parts
    if "docs" in parts:
        i = parts.index("docs")
        if i + 1 < len(parts):
            return str(parts[i + 1]).upper()
    return ""


def _run_cmd(cmd: Sequence[str], *, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env=env,
    )


def _read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hygiene(canonical_csv: Path) -> Dict[str, int]:
    rows = 0
    blank_period_end = 0
    cashflow_unmapped = 0
    with canonical_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for rec in reader:
            rows += 1
            if not str(rec.get("statement_period_end", rec.get("period_end", ""))).strip():
                blank_period_end += 1
            metric = str(rec.get("metric_base", rec.get("metric", ""))).strip().lower()
            if metric == "cashflow_unmapped":
                cashflow_unmapped += 1
    return {
        "rows": int(rows),
        "blank_period_end": int(blank_period_end),
        "cashflow_unmapped": int(cashflow_unmapped),
    }


def _csv_row_count(path: Path) -> int:
    rows = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for _ in reader:
            rows += 1
    return int(rows)


def _discover_pdfs(pdf_dir: Path) -> List[Path]:
    return sorted((p for p in pdf_dir.rglob("*.pdf") if p.is_file()), key=lambda p: p.name)


def _select_latest_pdfs(pdfs: Sequence[Path], max_docs: int) -> List[Path]:
    sorted_pdfs = sorted(
        list(pdfs),
        key=lambda p: (_pdf_financial_relevance_score(p.name), _extract_date_key(p.name), p.name),
        reverse=True,
    )
    limit = int(max(1, max_docs))
    if limit == 1:
        return sorted_pdfs[:1]

    picked: List[Path] = []
    annual_candidate = next((p for p in sorted_pdfs if _pdf_report_bucket(p.name) == "annual"), None)
    half_candidate = next((p for p in sorted_pdfs if _pdf_report_bucket(p.name) == "half"), None)

    # Prefer broad statement coverage by including one annual and one half-year report when available.
    if annual_candidate is not None:
        picked.append(annual_candidate)
    if half_candidate is not None and half_candidate not in picked:
        picked.append(half_candidate)

    for p in sorted_pdfs:
        if p in picked:
            continue
        picked.append(p)
        if len(picked) >= limit:
            break
    return picked[:limit]


def _select_annual_per_year_pdfs(pdfs: Sequence[Path], max_docs: int) -> List[Path]:
    limit = int(max(1, max_docs))
    all_pdfs = list(pdfs)
    annual_pdfs = [p for p in all_pdfs if _pdf_report_bucket(p.name) == "annual"]
    by_year: Dict[int, List[Path]] = {}
    for p in annual_pdfs:
        y = _date_year(p.name)
        if y <= 0:
            continue
        by_year.setdefault(y, []).append(p)

    picked: List[Path] = []
    for year in sorted(by_year.keys(), reverse=True):
        candidates = sorted(
            by_year[year],
            key=lambda p: (
                _annual_quality_tier(p.name),
                _rank_key(p.name),
            ),
            reverse=True,
        )
        if candidates:
            picked.append(candidates[0])
        if len(picked) >= limit:
            return picked[:limit]

    half_candidates = sorted(
        [p for p in all_pdfs if _pdf_report_bucket(p.name) == "half" and p not in picked],
        key=lambda p: (
            _half_quality_tier(p.name),
            _rank_key(p.name),
        ),
        reverse=True,
    )
    for p in half_candidates:
        picked.append(p)
        if len(picked) >= limit:
            return picked[:limit]

    remainder = sorted(
        [p for p in all_pdfs if p not in picked],
        key=lambda p: _rank_key(p.name),
        reverse=True,
    )
    for p in remainder:
        picked.append(p)
        if len(picked) >= limit:
            break
    return picked[:limit]


def _select_pdfs(pdfs: Sequence[Path], max_docs: int, selection_strategy: str) -> List[Path]:
    strategy = str(selection_strategy or "latest_relevance").strip().lower()
    if strategy == "annual_per_year":
        return _select_annual_per_year_pdfs(pdfs, max_docs)
    return _select_latest_pdfs(pdfs, max_docs)


def _link_subset_pdfs(selected_pdfs: Sequence[Path], subset_pdf_dir: Path) -> List[str]:
    subset_pdf_dir.mkdir(parents=True, exist_ok=True)
    linked: List[str] = []
    for src in selected_pdfs:
        dst = subset_pdf_dir / src.name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src.resolve())
        linked.append(str(dst))
    return linked


def _count_gold_docs(gold_ticker_dir: Path) -> int:
    if not gold_ticker_dir.exists():
        return 0
    return int(len(list(gold_ticker_dir.glob("*.json"))))


@dataclass
class ExpansionConfig:
    repo_root: Path
    python_bin: Path
    docs_root: Path
    gold_root: Path
    out_root: Path
    max_pdfs_per_ticker: int
    selection_strategy: str
    force_section_pass: bool
    audit_cashflow_pre_scope: int


def run_ticker_onboarding(cfg: ExpansionConfig, ticker: str, batch_dir: Path) -> Dict[str, object]:
    ticker_u = str(ticker).strip().upper()
    ticker_dir = cfg.docs_root / ticker_u / "financial_performance"
    ticker_out = batch_dir / ticker_u
    ticker_out.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, object] = {
        "ticker": ticker_u,
        "generated_at_utc": _utc_now(),
        "status": "pending",
        "paths": {},
        "commands": {},
    }

    if not ticker_dir.exists():
        summary["status"] = "skipped_missing_pdf_dir"
        summary["reason"] = f"Missing directory: {ticker_dir}"
        return summary

    all_pdfs = _discover_pdfs(ticker_dir)
    if not all_pdfs:
        summary["status"] = "skipped_no_pdfs"
        summary["reason"] = f"No PDFs found in: {ticker_dir}"
        return summary

    selected_pdfs = _select_pdfs(all_pdfs, cfg.max_pdfs_per_ticker, cfg.selection_strategy)
    subset_pdf_dir = ticker_out / "pdf_subset"
    linked_paths = _link_subset_pdfs(selected_pdfs, subset_pdf_dir)

    summary["pdf_selection"] = {
        "selection_strategy": str(cfg.selection_strategy),
        "source_dir": str(ticker_dir),
        "total_pdfs_available": int(len(all_pdfs)),
        "selected_pdf_count": int(len(selected_pdfs)),
        "selected_pdf_names": [p.name for p in selected_pdfs],
        "selected_doc_ids": [_doc_id_from_pdf_name(p.name) for p in selected_pdfs],
        "linked_pdf_paths": linked_paths,
    }

    extract_out_dir = ticker_out / "extract_baseline"
    extract_out_dir.mkdir(parents=True, exist_ok=True)
    baseline_csv = extract_out_dir / "canonical_baseline.csv"
    baseline_json = extract_out_dir / "canonical_baseline.json"
    baseline_ctx_csv = extract_out_dir / "canonical_context.csv"
    baseline_ctx_json = extract_out_dir / "canonical_context.json"
    baseline_rejected_json = extract_out_dir / "canonical_rejected.json"
    baseline_blocks_json = extract_out_dir / "canonical_blocks.json"
    baseline_high_csv = extract_out_dir / "canonical_high.csv"
    baseline_high_json = extract_out_dir / "canonical_high.json"
    baseline_sqlite = extract_out_dir / "canonical.sqlite"

    extract_cmd = [
        str(cfg.python_bin),
        str(cfg.repo_root / "scripts" / "extract_financial_metrics.py"),
        "--pdf-dir",
        str(subset_pdf_dir),
        "--out-csv",
        str(baseline_csv),
        "--out-json",
        str(baseline_json),
        "--out-context-csv",
        str(baseline_ctx_csv),
        "--out-context-json",
        str(baseline_ctx_json),
        "--out-rejected-json",
        str(baseline_rejected_json),
        "--out-blocks-json",
        str(baseline_blocks_json),
        "--out-high-csv",
        str(baseline_high_csv),
        "--out-high-json",
        str(baseline_high_json),
        "--out-sqlite",
        str(baseline_sqlite),
    ]
    extract_cp = _run_cmd(extract_cmd)
    summary["commands"]["extract_financial_metrics"] = {
        "cmd": extract_cmd,
        "returncode": int(extract_cp.returncode),
        "stdout_tail": str(extract_cp.stdout).splitlines()[-20:],
        "stderr_tail": str(extract_cp.stderr).splitlines()[-20:],
    }
    if extract_cp.returncode != 0:
        summary["status"] = "failed_extract"
        return summary
    if not baseline_csv.exists():
        summary["status"] = "failed_missing_baseline_csv"
        return summary

    baseline_rows = _csv_row_count(baseline_csv)
    summary["baseline"] = {
        "rows": int(baseline_rows),
        "baseline_csv": str(baseline_csv),
    }
    if baseline_rows <= 0:
        summary["status"] = "skipped_empty_baseline"
        summary["reason"] = "No canonical metric candidates extracted from selected PDFs."
        return summary

    section_out_dir = ticker_out / "section_capture"
    section_out_dir.mkdir(parents=True, exist_ok=True)
    section_cmd = [
        str(cfg.python_bin),
        str(cfg.repo_root / "section_capture_layer.py"),
        "--pdf-dir",
        str(subset_pdf_dir),
        "--canonical",
        str(baseline_csv),
        "--out-dir",
        str(section_out_dir),
    ]
    if cfg.force_section_pass:
        section_cmd.append("--force-section-pass")
    section_cmd.extend(
        [
            "--audit-cashflow-pre-scope",
            str(int(cfg.audit_cashflow_pre_scope)),
        ]
    )
    section_cp = _run_cmd(section_cmd)
    summary["commands"]["section_capture_layer"] = {
        "cmd": section_cmd,
        "returncode": int(section_cp.returncode),
        "stdout_tail": str(section_cp.stdout).splitlines()[-30:],
        "stderr_tail": str(section_cp.stderr).splitlines()[-30:],
    }
    if section_cp.returncode != 0:
        summary["status"] = "failed_section_capture"
        return summary

    hardened_csv = section_out_dir / "canonical_section_capture.csv"
    if not hardened_csv.exists():
        summary["status"] = "failed_missing_hardened_csv"
        return summary

    hygiene = _canonical_hygiene(hardened_csv)
    section_summary_path = section_out_dir / "section_capture_improvement_summary.json"
    section_summary = _read_json(section_summary_path) if section_summary_path.exists() else {}

    bootstrap_out_dir = ticker_out / "gold_templates"
    bootstrap_cmd = [
        str(cfg.python_bin),
        str(cfg.repo_root / "scripts" / "bootstrap_gold_templates.py"),
        "--canonical-csv",
        str(hardened_csv),
        "--out-dir",
        str(bootstrap_out_dir),
        "--tickers",
        ticker_u,
        "--docs-per-ticker",
        str(int(cfg.max_pdfs_per_ticker)),
    ]
    bootstrap_cp = _run_cmd(bootstrap_cmd)
    summary["commands"]["bootstrap_gold_templates"] = {
        "cmd": bootstrap_cmd,
        "returncode": int(bootstrap_cp.returncode),
        "stdout_tail": str(bootstrap_cp.stdout).splitlines()[-20:],
        "stderr_tail": str(bootstrap_cp.stderr).splitlines()[-20:],
    }
    if bootstrap_cp.returncode != 0:
        summary["status"] = "failed_bootstrap_gold_templates"
        return summary

    score_result: Dict[str, object] = {
        "scored": False,
        "reason": "no_curated_gold",
    }
    gold_ticker_dir = cfg.gold_root / ticker_u
    curated_gold_docs = _count_gold_docs(gold_ticker_dir)
    if curated_gold_docs > 0:
        score_out_dir = ticker_out / "score_curated_gold"
        score_cmd = [
            str(cfg.python_bin),
            str(cfg.repo_root / "scripts" / "score_gold_set.py"),
            "--gold-dir",
            str(gold_ticker_dir),
            "--canonical-csv",
            str(hardened_csv),
            "--out-dir",
            str(score_out_dir),
        ]
        score_cp = _run_cmd(score_cmd)
        summary["commands"]["score_gold_set"] = {
            "cmd": score_cmd,
            "returncode": int(score_cp.returncode),
            "stdout_tail": str(score_cp.stdout).splitlines()[-20:],
            "stderr_tail": str(score_cp.stderr).splitlines()[-20:],
        }
        if score_cp.returncode == 0 and (score_out_dir / "scorecard.json").exists():
            scorecard = _read_json(score_out_dir / "scorecard.json")
            score_result = {
                "scored": True,
                "gold_docs": int(curated_gold_docs),
                "scorecard_json": str(score_out_dir / "scorecard.json"),
                "totals": scorecard.get("totals", {}),
            }
        else:
            score_result = {
                "scored": False,
                "reason": "score_failed",
            }

    templ_dir = bootstrap_out_dir / ticker_u
    templ_count = _count_gold_docs(templ_dir)
    summary["paths"] = {
        "ticker_output_dir": str(ticker_out),
        "baseline_csv": str(baseline_csv),
        "hardened_csv": str(hardened_csv),
        "section_capture_summary_json": str(section_summary_path),
        "gold_templates_dir": str(templ_dir),
    }
    summary["hygiene"] = hygiene
    summary["section_capture_summary"] = {
        "candidate_rows_added": int(section_summary.get("candidate_rows_added", 0) or 0),
        "pdfs_processed_in_section_pass": int(section_summary.get("pdfs_processed_in_section_pass", 0) or 0),
        "ocr_stats": section_summary.get("ocr_stats", {}),
    }
    summary["gold_templates"] = {
        "template_docs_created": int(templ_count),
        "template_dir": str(templ_dir),
    }
    summary["curated_gold_score"] = score_result
    summary["status"] = "ok"
    return summary


def run_batch(cfg: ExpansionConfig, tickers: Sequence[str]) -> Dict[str, object]:
    run_id = f"run_{_timestamp_slug()}_ticker_expansion_batch"
    batch_dir = cfg.out_root / run_id
    batch_dir.mkdir(parents=True, exist_ok=False)

    ticker_results: List[Dict[str, object]] = []
    for ticker in tickers:
        ticker_results.append(run_ticker_onboarding(cfg, ticker, batch_dir))

    status_counts: Dict[str, int] = {}
    for rec in ticker_results:
        key = str(rec.get("status", "unknown"))
        status_counts[key] = int(status_counts.get(key, 0)) + 1

    curated_scored = [r for r in ticker_results if bool(r.get("curated_gold_score", {}).get("scored"))]
    scorecards = [Path(str(r["curated_gold_score"]["scorecard_json"])) for r in curated_scored if r.get("curated_gold_score", {}).get("scorecard_json")]

    aggregate_result: Dict[str, object] = {
        "aggregated": False,
        "reason": "no_curated_gold_scorecards",
    }
    if scorecards:
        aggregate_out = batch_dir / "aggregate_curated_gold"
        agg_cmd = [
            str(cfg.python_bin),
            str(cfg.repo_root / "scripts" / "score_gold_run_matrix.py"),
        ]
        for sc in scorecards:
            agg_cmd.extend(["--scorecard", str(sc)])
        agg_cmd.extend(["--out-dir", str(aggregate_out)])
        agg_cp = _run_cmd(agg_cmd)
        if agg_cp.returncode == 0 and (aggregate_out / "aggregate_scorecard.json").exists():
            aggregate_result = {
                "aggregated": True,
                "aggregate_scorecard_json": str(aggregate_out / "aggregate_scorecard.json"),
                "stdout_tail": str(agg_cp.stdout).splitlines()[-20:],
                "stderr_tail": str(agg_cp.stderr).splitlines()[-20:],
            }
        else:
            aggregate_result = {
                "aggregated": False,
                "reason": "aggregate_failed",
                "stdout_tail": str(agg_cp.stdout).splitlines()[-20:],
                "stderr_tail": str(agg_cp.stderr).splitlines()[-20:],
            }

    summary = {
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "batch_dir": str(batch_dir),
        "config": {
            "repo_root": str(cfg.repo_root),
            "python_bin": str(cfg.python_bin),
            "docs_root": str(cfg.docs_root),
            "gold_root": str(cfg.gold_root),
            "max_pdfs_per_ticker": int(cfg.max_pdfs_per_ticker),
            "selection_strategy": str(cfg.selection_strategy),
            "force_section_pass": bool(cfg.force_section_pass),
            "audit_cashflow_pre_scope": int(cfg.audit_cashflow_pre_scope),
        },
        "tickers": [str(t).strip().upper() for t in tickers],
        "status_counts": status_counts,
        "ticker_results": ticker_results,
        "aggregate_curated_gold": aggregate_result,
    }
    summary_path = batch_dir / "expansion_batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["summary_json"] = str(summary_path)
    return summary


def main() -> int:
    runtime_python = print_runtime_info()
    ap = argparse.ArgumentParser(description="Run incremental ticker expansion onboarding batch.")
    ap.add_argument("--tickers", required=True, help="Comma-separated tickers (e.g., ASB,MIN)")
    ap.add_argument(
        "--python-bin",
        default=runtime_python,
        help="Python interpreter to run child scripts with.",
    )
    ap.add_argument(
        "--docs-root",
        default="/home/l4nd0/tenn/financial-engine_v2/data/asx/docs",
        help="Root docs directory containing <TICKER>/financial_performance.",
    )
    ap.add_argument(
        "--gold-root",
        default="/home/l4nd0/tenn/gold",
        help="Curated gold root directory.",
    )
    ap.add_argument(
        "--out-root",
        default="/home/l4nd0/tenn/reports/expansion_runs",
        help="Output root for expansion batches.",
    )
    ap.add_argument("--max-pdfs-per-ticker", type=int, default=8, help="Max latest PDFs to include per ticker.")
    ap.add_argument(
        "--selection-strategy",
        choices=["latest_relevance", "annual_per_year"],
        default="latest_relevance",
        help="PDF selection mode; annual_per_year enforces longitudinal annual coverage when available.",
    )
    ap.add_argument("--force-section-pass", action="store_true", help="Force section capture second pass.")
    ap.add_argument(
        "--audit-cashflow-pre-scope",
        type=int,
        default=1,
        help="Pass-through for section_capture_layer --audit-cashflow-pre-scope.",
    )
    args = ap.parse_args()

    tickers = [t.strip().upper() for t in str(args.tickers).split(",") if t.strip()]
    if not tickers:
        print("No tickers provided.", file=sys.stderr)
        return 2

    cfg = ExpansionConfig(
        repo_root=ROOT.resolve(),
        python_bin=Path(str(args.python_bin)).expanduser(),
        docs_root=Path(str(args.docs_root)).expanduser().resolve(),
        gold_root=Path(str(args.gold_root)).expanduser().resolve(),
        out_root=Path(str(args.out_root)).expanduser().resolve(),
        max_pdfs_per_ticker=int(max(1, args.max_pdfs_per_ticker)),
        selection_strategy=str(args.selection_strategy),
        force_section_pass=bool(args.force_section_pass),
        audit_cashflow_pre_scope=int(max(0, args.audit_cashflow_pre_scope)),
    )

    summary = run_batch(cfg, tickers)
    print(f"Run id: {summary['run_id']}")
    print(f"Batch dir: {summary['batch_dir']}")
    print(f"Summary: {summary['summary_json']}")
    print(f"Status counts: {summary['status_counts']}")
    agg = summary.get("aggregate_curated_gold", {})
    if agg.get("aggregated"):
        print(f"Aggregate curated-gold scorecard: {agg.get('aggregate_scorecard_json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
