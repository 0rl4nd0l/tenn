#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict


def load_report(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"report at {path} is not a JSON object")
    return data


def normalized_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    src = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    keys = ("cases", "scored", "failures", "hits", "hit_rate", "hit_at_k", "mrr")
    return {k: src.get(k) for k in keys}


def case_snapshot(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in report.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        if not row.get("has_expectations", False):
            continue
        case_id = str(row.get("id", "")).strip()
        if not case_id:
            continue
        item: Dict[str, Any] = {
            "hit": bool(row.get("hit", False)),
            "first_match_rank": row.get("first_match_rank"),
        }
        top = row.get("top_result")
        if isinstance(top, dict):
            file_path = str(top.get("file", "")).strip()
            if file_path:
                item["top_file"] = Path(file_path).name
        out[case_id] = item
    return out


def build_snapshot(news_report: Path, company_report: Path, reference_report: Path) -> Dict[str, Any]:
    news = load_report(news_report)
    company = load_report(company_report)
    reference = load_report(reference_report)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema_version": 1,
        "created_at_utc": now,
        "source_reports": {
            "news": str(news_report),
            "company": str(company_report),
            "reference": str(reference_report),
        },
        "reports": {
            "news": {
                "summary": normalized_summary(news),
                "cases": case_snapshot(news),
            },
            "company": {
                "summary": normalized_summary(company),
                "cases": case_snapshot(company),
            },
            "reference": {
                "summary": normalized_summary(reference),
                "cases": case_snapshot(reference),
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a canonical eval baseline snapshot from current report JSONs.")
    ap.add_argument("--news-report", default="reports/news_eval_report.json")
    ap.add_argument("--company-report", default="reports/company_eval_report_v2.json")
    ap.add_argument("--reference-report", default="reports/eval_queries_report.json")
    ap.add_argument(
        "--out",
        required=True,
        help="Destination JSON path for dated baseline snapshot.",
    )
    ap.add_argument(
        "--latest-out",
        default="reports/baselines/canonical_eval_baseline_latest.json",
        help="Optional path to also write/update latest baseline pointer file.",
    )
    args = ap.parse_args()

    out_path = Path(args.out).expanduser()
    latest_path = Path(args.latest_out).expanduser() if args.latest_out else None

    snapshot = build_snapshot(
        news_report=Path(args.news_report).expanduser(),
        company_report=Path(args.company_report).expanduser(),
        reference_report=Path(args.reference_report).expanduser(),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"baseline_json={out_path}")

    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        print(f"latest_baseline_json={latest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
