#!/usr/bin/env python3
"""Reconcile user-provided metric-period table rows against extracted evidence rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_MAPPED_METRICS = [
    "cash_and_equivalents",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_equity",
    "total_liabilities",
]

EXTRACTED_FIELDS = [
    "extracted_value_raw",
    "inferred_scale_to_millions",
    "extracted_value_millions",
    "abs_diff_millions",
    "pct_diff",
    "extracted_file",
    "extracted_page_number",
    "extracted_line_no",
    "evidence_screenshot_snippet",
    "evidence_screenshot_page",
    "evidence_screenshot_snippet_abs",
    "evidence_screenshot_page_abs",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile user table rows against extracted evidence manifest rows."
    )
    parser.add_argument(
        "--user-template-csv",
        required=True,
        help="CSV containing user table rows and expected comparison columns.",
    )
    parser.add_argument(
        "--evidence-csv",
        required=True,
        help="Evidence manifest CSV (from export_canonical_metric_evidence_pack.py).",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory for comparison artifacts.",
    )
    parser.add_argument(
        "--mapped-metrics",
        default=",".join(DEFAULT_MAPPED_METRICS),
        help="Comma-separated mapped metrics to compare.",
    )
    parser.add_argument(
        "--match-pct-threshold",
        type=float,
        default=0.01,
        help="Maximum relative error to mark match (default: 0.01 = 1%%).",
    )
    parser.add_argument(
        "--ticker",
        default="EVN",
        help="Ticker label for extracted-only extra rows when evidence ticker is missing.",
    )
    parser.add_argument(
        "--output-prefix",
        default="evn_user_table_vs_extracted",
        help="Output filename prefix.",
    )
    parser.add_argument(
        "--run-dir",
        default="",
        help="Optional run dir path to include in summary JSON/MD.",
    )
    return parser.parse_args()


def parse_mapped_metrics(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_extracted_rows(
    evidence_csv: Path, mapped_metrics: Iterable[str]
) -> Dict[Tuple[str, str], Dict[str, str]]:
    mapped_set = set(mapped_metrics)
    out: Dict[Tuple[str, str], Dict[str, str]] = {}
    with evidence_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            metric = (row.get("metric_base") or "").strip()
            period = (row.get("statement_period_end") or "").strip()
            if not metric or not period or metric not in mapped_set:
                continue
            key = (metric, period)
            if key in out:
                raise RuntimeError(
                    f"Duplicate evidence key for {metric} @ {period} in {evidence_csv}"
                )
            out[key] = row
    return out


def infer_millions(raw_value: float, user_value_m: float) -> Tuple[str, float, float]:
    candidates = [
        ("x1", 1.0),
        ("x1e3", 1_000.0),
        ("x1e6", 1_000_000.0),
        ("x1e9", 1_000_000_000.0),
    ]
    best_label = ""
    best_value = 0.0
    best_abs = math.inf
    for label, divisor in candidates:
        value_m = raw_value / divisor
        abs_diff = abs(value_m - user_value_m)
        if abs_diff < best_abs:
            best_label = label
            best_value = value_m
            best_abs = abs_diff
    return best_label, best_value, best_abs


def resolve_abs_path(evidence_root: Path, relative_path: str) -> str:
    relative_path = relative_path.strip()
    if not relative_path:
        return ""
    return str((evidence_root / relative_path).resolve())


def reconcile(
    user_template_csv: Path,
    extracted_rows: Dict[Tuple[str, str], Dict[str, str]],
    mapped_metrics: List[str],
    match_pct_threshold: float,
    evidence_root: Path,
) -> Tuple[List[str], List[Dict[str, str]], set]:
    mapped_set = set(mapped_metrics)
    used_keys: set = set()
    comparison_rows: List[Dict[str, str]] = []

    with user_template_csv.open(newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        for src in reader:
            row = dict(src)
            metric = (row.get("mapped_metric_base") or "").strip()
            period = (row.get("statement_period_end") or "").strip()
            user_metric_label = (row.get("user_metric_label") or "").strip()

            for field in EXTRACTED_FIELDS:
                row[field] = ""

            if metric not in mapped_set:
                row["status"] = "not_compared"
                comparison_rows.append(row)
                continue

            # Skip stale extracted-only rows from prior comparison files.
            if not user_metric_label:
                continue

            if not period:
                row["status"] = "not_compared"
                comparison_rows.append(row)
                continue

            key = (metric, period)
            extracted = extracted_rows.get(key)
            if extracted is None:
                row["status"] = "missing_in_extraction"
                comparison_rows.append(row)
                continue

            used_keys.add(key)

            raw_value = float(extracted.get("value") or 0.0)
            user_value = float(row.get("user_value_millions") or 0.0)
            scale_label, extracted_m, abs_diff = infer_millions(raw_value, user_value)
            pct_diff = (
                abs_diff / abs(user_value)
                if user_value
                else (0.0 if abs_diff == 0.0 else math.inf)
            )

            row["extracted_value_raw"] = f"{raw_value}"
            row["inferred_scale_to_millions"] = scale_label
            row["extracted_value_millions"] = f"{extracted_m}"
            row["abs_diff_millions"] = f"{abs_diff}"
            row["pct_diff"] = f"{pct_diff}"
            row["status"] = "match" if pct_diff <= match_pct_threshold else "mismatch"

            row["extracted_file"] = extracted.get("file") or ""
            if extracted.get("page_number"):
                row["extracted_page_number"] = f"{float(extracted['page_number']):.1f}"
            if extracted.get("line_no"):
                row["extracted_line_no"] = f"{float(extracted['line_no']):.1f}"

            snippet_rel = extracted.get("screenshot_snippet") or ""
            page_rel = extracted.get("screenshot_page") or ""
            row["evidence_screenshot_snippet"] = snippet_rel
            row["evidence_screenshot_page"] = page_rel
            row["evidence_screenshot_snippet_abs"] = resolve_abs_path(
                evidence_root, snippet_rel
            )
            row["evidence_screenshot_page_abs"] = resolve_abs_path(
                evidence_root, page_rel
            )

            comparison_rows.append(row)

    return fieldnames, comparison_rows, used_keys


def build_extra_row(
    fieldnames: List[str],
    metric: str,
    period: str,
    extracted: Dict[str, str],
    ticker_fallback: str,
    evidence_root: Path,
) -> Dict[str, str]:
    row = {field: "" for field in fieldnames}
    row["ticker"] = extracted.get("ticker") or ticker_fallback
    row["mapped_metric_base"] = metric
    row["statement_period_end"] = period
    row["status"] = "extra_in_extraction_or_period_mismatch"
    row["extracted_value_raw"] = f"{float(extracted.get('value') or 0.0)}"
    row["extracted_file"] = extracted.get("file") or ""

    if extracted.get("page_number"):
        row["extracted_page_number"] = f"{float(extracted['page_number']):.1f}"
    if extracted.get("line_no"):
        row["extracted_line_no"] = f"{float(extracted['line_no']):.1f}"

    snippet_rel = extracted.get("screenshot_snippet") or ""
    page_rel = extracted.get("screenshot_page") or ""
    row["evidence_screenshot_snippet"] = snippet_rel
    row["evidence_screenshot_page"] = page_rel
    row["evidence_screenshot_snippet_abs"] = resolve_abs_path(evidence_root, snippet_rel)
    row["evidence_screenshot_page_abs"] = resolve_abs_path(evidence_root, page_rel)
    return row


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    user_template_csv = Path(args.user_template_csv).resolve()
    evidence_csv = Path(args.evidence_csv).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    mapped_metrics = parse_mapped_metrics(args.mapped_metrics)
    mapped_set = set(mapped_metrics)
    evidence_root = evidence_csv.parent
    extracted_rows = load_extracted_rows(evidence_csv, mapped_metrics)

    fieldnames, comparison_rows, used_keys = reconcile(
        user_template_csv=user_template_csv,
        extracted_rows=extracted_rows,
        mapped_metrics=mapped_metrics,
        match_pct_threshold=args.match_pct_threshold,
        evidence_root=evidence_root,
    )

    for (metric, period), extracted in sorted(extracted_rows.items()):
        if (metric, period) in used_keys:
            continue
        comparison_rows.append(
            build_extra_row(
                fieldnames=fieldnames,
                metric=metric,
                period=period,
                extracted=extracted,
                ticker_fallback=args.ticker,
                evidence_root=evidence_root,
            )
        )

    overlap_rows = [
        row for row in comparison_rows if (row.get("mapped_metric_base") or "") in mapped_set
    ]

    comparison_csv = out_dir / f"{args.output_prefix}_comparison.csv"
    overlap_only_csv = out_dir / f"{args.output_prefix}_overlap_only.csv"
    overlap_ss_csv = out_dir / f"{args.output_prefix}_overlap_with_screenshots.csv"
    overlap_ss_abs_csv = out_dir / f"{args.output_prefix}_overlap_with_screenshots_abs.csv"
    summary_json = out_dir / "comparison_summary.json"
    summary_md = out_dir / "comparison_summary.md"

    write_csv(comparison_csv, fieldnames, comparison_rows)
    write_csv(overlap_only_csv, fieldnames, overlap_rows)
    write_csv(overlap_ss_csv, fieldnames, overlap_rows)
    write_csv(overlap_ss_abs_csv, fieldnames, overlap_rows)

    full_counts = Counter(row.get("status") or "" for row in comparison_rows)
    overlap_counts = Counter(row.get("status") or "" for row in overlap_rows)
    run_dir = args.run_dir.strip() or str(out_dir.parent)
    summary = {
        "run_dir": run_dir,
        "evidence_csv": str(evidence_csv),
        "comparison_csv": str(comparison_csv),
        "overlap_csv": str(overlap_ss_abs_csv),
        "full_status_counts": dict(full_counts),
        "overlap_status_counts": dict(overlap_counts),
        "mapped_metrics": mapped_metrics,
    }
    summary_json.write_text(json.dumps(summary, indent=2) + "\n")
    summary_md.write_text(
        "# EVN Comparison Summary\n\n"
        f"- run_dir: `{summary['run_dir']}`\n"
        f"- evidence_csv: `{summary['evidence_csv']}`\n"
        f"- comparison_csv: `{summary['comparison_csv']}`\n"
        f"- overlap_csv: `{summary['overlap_csv']}`\n"
        f"- full_status_counts: `{summary['full_status_counts']}`\n"
        f"- overlap_status_counts: `{summary['overlap_status_counts']}`\n"
        f"- mapped_metrics: `{', '.join(mapped_metrics)}`\n"
    )

    print(f"Wrote: {comparison_csv}")
    print(f"Wrote: {overlap_only_csv}")
    print(f"Wrote: {overlap_ss_csv}")
    print(f"Wrote: {overlap_ss_abs_csv}")
    print(f"Wrote: {summary_json}")
    print(f"Wrote: {summary_md}")
    print(f"full_counts {dict(full_counts)}")
    print(f"overlap_counts {dict(overlap_counts)}")


if __name__ == "__main__":
    main()
