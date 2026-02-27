#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"failed to load JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object at {path}")
    return data


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def index_results_by_id(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in report.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("id", "")).strip()
        if not case_id:
            continue
        out[case_id] = row
    return out


def append_failure(failures: List[str], message: str) -> None:
    failures.append(message)
    print(f"[fail] {message}")


def compare_report(
    name: str,
    current: Dict[str, Any],
    baseline_entry: Dict[str, Any],
    mrr_tolerance: float,
    rank_slack: int,
    failures: List[str],
) -> None:
    current_summary = current.get("summary", {}) if isinstance(current.get("summary"), dict) else {}
    baseline_summary = (
        baseline_entry.get("summary", {}) if isinstance(baseline_entry.get("summary"), dict) else {}
    )

    current_scored = safe_int(current_summary.get("scored"))
    current_hits = safe_int(current_summary.get("hits"))
    current_failures = safe_int(current_summary.get("failures"))

    if current_failures != 0:
        append_failure(failures, f"{name}: failures={current_failures}, expected 0")
    if current_hits != current_scored:
        append_failure(
            failures,
            f"{name}: hits/scored mismatch ({current_hits}/{current_scored}), expected perfect recall",
        )

    baseline_hit_rate = baseline_summary.get("hit_rate")
    if baseline_hit_rate is not None:
        current_hit_rate = safe_float(current_summary.get("hit_rate"))
        if current_hit_rate + 1e-12 < safe_float(baseline_hit_rate):
            append_failure(
                failures,
                f"{name}: hit_rate regressed ({current_hit_rate:.4f} < {safe_float(baseline_hit_rate):.4f})",
            )

    baseline_mrr = baseline_summary.get("mrr")
    if baseline_mrr is not None:
        current_mrr = safe_float(current_summary.get("mrr"))
        target_mrr = safe_float(baseline_mrr)
        if current_mrr + mrr_tolerance + 1e-12 < target_mrr:
            append_failure(
                failures,
                (
                    f"{name}: mrr regressed ({current_mrr:.4f} < {target_mrr:.4f}) "
                    f"beyond tolerance {mrr_tolerance:.4f}"
                ),
            )

    baseline_cases = baseline_entry.get("cases", {})
    if not isinstance(baseline_cases, dict):
        return
    current_cases = index_results_by_id(current)

    for case_id in sorted(baseline_cases.keys()):
        expected = baseline_cases.get(case_id)
        if not isinstance(expected, dict):
            continue
        row = current_cases.get(case_id)
        if row is None:
            append_failure(failures, f"{name}:{case_id}: missing from current report")
            continue

        expect_hit = bool(expected.get("hit", False))
        got_hit = bool(row.get("hit", False))
        if expect_hit and not got_hit:
            append_failure(failures, f"{name}:{case_id}: expected hit=True but got hit=False")
            continue

        expected_rank = expected.get("first_match_rank")
        if expected_rank is None:
            continue
        got_rank = row.get("first_match_rank")
        if got_rank is None:
            append_failure(failures, f"{name}:{case_id}: expected rank but got none")
            continue

        got_rank_i = safe_int(got_rank, default=-1)
        expected_rank_i = safe_int(expected_rank, default=-1)
        if got_rank_i <= 0 or expected_rank_i <= 0:
            append_failure(
                failures,
                f"{name}:{case_id}: invalid rank values expected={expected_rank} got={got_rank}",
            )
            continue
        if got_rank_i > expected_rank_i + rank_slack:
            append_failure(
                failures,
                (
                    f"{name}:{case_id}: rank regressed from <= {expected_rank_i + rank_slack} "
                    f"to {got_rank_i} (baseline={expected_rank_i}, slack={rank_slack})"
                ),
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate canonical eval reports against a baseline snapshot.")
    ap.add_argument(
        "--baseline",
        default="reports/baselines/canonical_eval_baseline_latest.json",
        help="Baseline snapshot JSON path.",
    )
    ap.add_argument("--news-report", default="reports/news_eval_report.json")
    ap.add_argument("--company-report", default="reports/company_eval_report_v2.json")
    ap.add_argument("--reference-report", default="reports/eval_queries_report.json")
    ap.add_argument(
        "--mrr-tolerance",
        type=float,
        default=0.0,
        help="Allowed absolute MRR drop versus baseline.",
    )
    ap.add_argument(
        "--rank-slack",
        type=int,
        default=0,
        help="Allowed rank worsening per case (0 means no per-case rank regression).",
    )
    args = ap.parse_args()

    baseline_path = Path(args.baseline).expanduser()
    if not baseline_path.exists():
        print(f"[fail] baseline file not found: {baseline_path}", file=sys.stderr)
        return 2

    baseline = load_json(baseline_path)
    reports_node = baseline.get("reports", {})
    if not isinstance(reports_node, dict):
        print(f"[fail] invalid baseline format in {baseline_path}: missing 'reports' object", file=sys.stderr)
        return 2

    current_reports = {
        "news": load_json(Path(args.news_report).expanduser()),
        "company": load_json(Path(args.company_report).expanduser()),
        "reference": load_json(Path(args.reference_report).expanduser()),
    }

    failures: List[str] = []
    for name, current_report in current_reports.items():
        baseline_entry = reports_node.get(name)
        if not isinstance(baseline_entry, dict):
            append_failure(failures, f"{name}: missing baseline entry")
            continue
        compare_report(
            name=name,
            current=current_report,
            baseline_entry=baseline_entry,
            mrr_tolerance=max(0.0, float(args.mrr_tolerance)),
            rank_slack=max(0, int(args.rank_slack)),
            failures=failures,
        )

    if failures:
        print(f"[result] FAIL: {len(failures)} regression checks failed.")
        return 1

    print("[result] PASS: canonical regression checks satisfied baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
