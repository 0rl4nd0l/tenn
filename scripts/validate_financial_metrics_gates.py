#!/usr/bin/env python3
"""Validate extracted financial metrics files against hard ingestion gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

_CURRENCY_OPTIONAL_METRICS = {
    "eps",
    "shares_outstanding",
    "growth_pct",
    "gross_margin_pct",
    "operating_margin_pct",
    "roic_pct",
    "impairment_expense",
}


def _entity_key(row: Dict[str, object]) -> str:
    company = str(row.get("company", "")).strip()
    if company:
        return company
    file_path = str(row.get("file", "")).strip()
    if "/docs/" in file_path:
        parts = Path(file_path).parts
        if "docs" in parts:
            idx = parts.index("docs")
            if idx + 1 < len(parts):
                return str(parts[idx + 1]).strip()
    return "unknown"


def _flow_duration_group_key(row: Dict[str, object]) -> str:
    try:
        months = int(row.get("reporting_period_months", 0) or 0)
    except (TypeError, ValueError):
        months = 0
    if months > 0:
        return f"{months}m"
    cadence = str(row.get("reporting_cadence", "")).strip().lower()
    if cadence in {"quarterly", "half_yearly", "annual"}:
        return cadence
    return ""


def _key(row: Dict[str, object]) -> Tuple[str, str, str, str, str, str, str, str]:
    metric_base = str(row.get("metric_base", "")).strip().lower() or str(row.get("metric", "")).strip().lower()
    period = str(row.get("statement_period_end", "")).strip() or str(row.get("period_end_date", "")).strip()
    statement_family = str(row.get("statement_family", "")).strip().lower()
    definition_scope = str(row.get("definition_scope", "")).strip().lower() or "reported"
    value_type = str(row.get("value_type", "")).strip().lower()
    balance_position = str(row.get("balance_position", "")).strip().lower()
    return (
        _entity_key(row),
        metric_base,
        period,
        statement_family,
        definition_scope,
        value_type,
        balance_position,
        _flow_duration_group_key(row),
    )


def _norm_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.15g}"
    return str(value).strip()


def _currency_required(row: Dict[str, object]) -> bool:
    metric = str(row.get("metric", "")).strip().lower()
    value_type = str(row.get("value_type", "")).strip().lower()
    if metric in _CURRENCY_OPTIONAL_METRICS:
        return False
    if metric.endswith("_pct"):
        return False
    if value_type in {"percent", "text"}:
        return False
    return True


def build_report(rows: Sequence[Dict[str, object]], max_sample: int) -> Dict[str, object]:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    empty_currency_rows: List[Dict[str, object]] = []
    low_conf_rows: List[Dict[str, object]] = []

    for row in rows:
        key = _key(row)
        grouped.setdefault(key, []).append(row)

        if _currency_required(row) and not str(row.get("currency", "")).strip():
            empty_currency_rows.append(row)
        try:
            conf = float(row.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        if conf < 0.85:
            low_conf_rows.append(row)

    duplicate_groups = [
        {
            "entity": k[0],
            "metric_base": k[1],
            "statement_period_end": k[2],
            "statement_family": k[3],
            "definition_scope": k[4],
            "value_type": k[5],
            "balance_position": k[6],
            "flow_duration": k[7],
            "count": len(v),
        }
        for k, v in grouped.items()
        if len(v) > 1
    ]
    conflict_groups = []
    for k, v in grouped.items():
        values = sorted({_norm_value(row.get("value")) for row in v})
        if len(values) > 1:
            conflict_groups.append(
                {
                    "metric_base": k[1],
                    "period": k[2],
                    "entity": k[0],
                    "statement_family": k[3],
                    "definition_scope": k[4],
                    "distinct_values": values,
                    "count": len(v),
                }
            )

    total_rows = len(rows)
    unique_keys = len(grouped)
    duplicates = total_rows - unique_keys
    conflicts = len(conflict_groups)
    empty_currency = len(empty_currency_rows)
    low_conf = len(low_conf_rows)

    report = {
        "total_rows": total_rows,
        "unique_metric_period_keys": unique_keys,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "empty_currency": empty_currency,
        "low_confidence_rows": low_conf,
        "gate_pass": duplicates == 0 and conflicts == 0 and empty_currency == 0,
        "failed_gates": [
            gate
            for gate, failed in (
                ("duplicates", duplicates > 0),
                ("conflicts", conflicts > 0),
                ("empty_currency", empty_currency > 0),
            )
            if failed
        ],
        "sample_duplicate_groups": duplicate_groups[:max_sample],
        "sample_conflict_groups": conflict_groups[:max_sample],
        "sample_empty_currency_rows": [
            {
                "metric": str(r.get("metric", "")),
                "period": str(r.get("period", "")),
                "value": r.get("value"),
                "line_no": r.get("line_no"),
                "file": r.get("file"),
            }
            for r in empty_currency_rows[:max_sample]
        ],
    }
    return report


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hard gate validator for financial metrics JSON.")
    parser.add_argument("input_json", help="Path to financial metrics JSON (array of rows).")
    parser.add_argument("--out-json", default="", help="Optional output path for full JSON report.")
    parser.add_argument("--max-sample", type=int, default=20, help="Max sample items per gate bucket.")
    args = parser.parse_args(argv)

    input_path = Path(args.input_json).expanduser().resolve()
    if not input_path.exists():
        print(f"[validate_financial_metrics_gates] File not found: {input_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[validate_financial_metrics_gates] Invalid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, list):
        print("[validate_financial_metrics_gates] Expected a top-level JSON array.", file=sys.stderr)
        return 2

    rows = [row for row in data if isinstance(row, dict)]
    report = build_report(rows, max_sample=max(1, args.max_sample))
    report["input_file"] = str(input_path)
    report["rows_skipped_non_object"] = len(data) - len(rows)

    if args.out_json:
        out_path = Path(args.out_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[validate_financial_metrics_gates] Wrote report: {out_path}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["gate_pass"]:
        print(
            "[validate_financial_metrics_gates] Gate failure: "
            + ", ".join(report["failed_gates"]),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
