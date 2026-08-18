#!/usr/bin/env python3
"""
Summarise financial metric coverage by source_mode from canonical JSON.

Usage:
  python scripts/report_financial_metrics_source_modes.py --canonical-json reports/financial_metrics_run/canonical.json --out-json reports/financial_metrics_run/source_mode_report.json
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from scripts.reporting.offline_artifact_authority import (
        artifact_record,
        build_authority_metadata,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct `python scripts/...` runs
    from reporting.offline_artifact_authority import (
        artifact_record,
        build_authority_metadata,
    )


def load_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Canonical JSON not found: {path}")
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}, got {type(data)}")
    return data


def key_for_row(row: Dict[str, Any]) -> Tuple[str, str]:
    metric = str(row.get("metric", ""))
    period = str(row.get("statement_period_end", ""))
    return metric, period


def build_source_mode_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Group by (metric, period_end) so we can see overlap across source_modes.
    by_key: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for r in rows:
        key = key_for_row(r)
        source_mode = str(r.get("source_mode", "unknown"))
        by_key[key][source_mode] += 1

    # Aggregate per source_mode and overlaps.
    per_source_mode: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"unique_keys": 0, "total_rows": 0})
    overlap_stats: Dict[str, int] = {
        "keys_with_multiple_source_modes": 0,
        "keys_where_docling_and_bbox_both_present": 0,
    }

    for (metric, period), counts_by_mode in by_key.items():
        modes = list(counts_by_mode.keys())
        if len(modes) > 1:
            overlap_stats["keys_with_multiple_source_modes"] += 1
            if "docling_table" in modes and "table_bbox" in modes:
                overlap_stats["keys_where_docling_and_bbox_both_present"] += 1

        for mode, count in counts_by_mode.items():
            per_source_mode[mode]["unique_keys"] += 1
            per_source_mode[mode]["total_rows"] += count

    return {
        "per_source_mode": per_source_mode,
        "overlap": overlap_stats,
        "total_unique_metric_period_keys": len(by_key),
    }


def attach_authority_metadata(report: Dict[str, Any], *, canonical_path: Path, out_path: Path) -> Dict[str, Any]:
    enriched = dict(report)
    enriched["authority"] = build_authority_metadata(
        artifact_type="financial_metric_source_mode_report",
        producer="scripts/report_financial_metrics_source_modes.py",
        lane="Evaluation",
        source_artifacts=[
            artifact_record(canonical_path, "report_local_selected_metric_rows"),
        ],
        output_artifacts=[
            artifact_record(out_path, "source_mode_report_json"),
        ],
        extra={
            "input_label": "canonical_json_report_local",
            "row_set_authority": "report_local_only",
        },
    )
    return enriched


def main() -> int:
    ap = argparse.ArgumentParser(description="Report financial metrics coverage by source_mode.")
    ap.add_argument("--canonical-json", required=True, help="Path to canonical.json from extract_financial_metrics.py")
    ap.add_argument("--out-json", required=True, help="Where to write the source_mode summary JSON")
    args = ap.parse_args()

    canonical_path = Path(args.canonical_json)
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_rows(canonical_path)
    report = attach_authority_metadata(
        build_source_mode_report(rows),
        canonical_path=canonical_path,
        out_path=out_path,
    )

    with out_path.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote source_mode report to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
