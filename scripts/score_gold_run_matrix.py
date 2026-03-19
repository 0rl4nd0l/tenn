#!/usr/bin/env python3
"""Aggregate per-ticker gold scorecards into one acceptance report."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _infer_ticker(scorecard: Dict[str, object], scorecard_path: Path) -> str:
    gold_dir = str(scorecard.get("gold_dir", "")).strip()
    if gold_dir:
        name = Path(gold_dir).name.strip().upper()
        if name:
            return name
    parent = scorecard_path.parent.name.strip().upper()
    if parent:
        return parent
    return scorecard_path.stem.strip().upper()


def _write_csv(path: Path, rows: List[Dict[str, object]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def aggregate_scorecards(scorecard_paths: List[Path], out_dir: Path) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not scorecard_paths:
        raise ValueError("At least one scorecard path is required")

    per_ticker = []
    totals = {"gold_fields": 0, "predicted": 0, "tp": 0, "fp": 0, "fn": 0}
    taxonomy_agg: Dict[str, int] = {}
    metric_agg: Dict[str, Dict[str, int]] = {}

    for path in scorecard_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        ticker = _infer_ticker(payload, path)
        t = payload.get("totals", {})
        row = {
            "ticker": ticker,
            "scorecard_json": str(path),
            "gold_fields": _to_int(t.get("gold_fields")),
            "predicted": _to_int(t.get("predicted")),
            "tp": _to_int(t.get("tp")),
            "fp": _to_int(t.get("fp")),
            "fn": _to_int(t.get("fn")),
            "precision": _to_float(t.get("precision")),
            "recall": _to_float(t.get("recall")),
            "f1": _to_float(t.get("f1")),
        }
        per_ticker.append(row)
        for key in totals:
            totals[key] += int(row[key])

        tax = payload.get("taxonomy_counts", {})
        if isinstance(tax, dict):
            for k, v in tax.items():
                taxonomy_agg[str(k)] = int(taxonomy_agg.get(str(k), 0)) + int(_to_int(v))

        metrics = payload.get("per_metric", [])
        if isinstance(metrics, list):
            for rec in metrics:
                metric = str(rec.get("metric", "")).strip().lower()
                if not metric:
                    continue
                if metric not in metric_agg:
                    metric_agg[metric] = {"gold_fields": 0, "predicted": 0, "tp": 0}
                metric_agg[metric]["gold_fields"] += _to_int(rec.get("gold_fields"))
                metric_agg[metric]["predicted"] += _to_int(rec.get("predicted"))
                metric_agg[metric]["tp"] += _to_int(rec.get("tp"))

    precision = (totals["tp"] / (totals["tp"] + totals["fp"])) if (totals["tp"] + totals["fp"]) else 0.0
    recall = (totals["tp"] / totals["gold_fields"]) if totals["gold_fields"] else 0.0
    f1 = ((2.0 * precision * recall) / (precision + recall)) if (precision + recall) else 0.0
    wrong_period_rate = (taxonomy_agg.get("wrong_period", 0) / totals["gold_fields"]) if totals["gold_fields"] else 0.0
    wrong_currency_rate = (taxonomy_agg.get("wrong_currency", 0) / totals["gold_fields"]) if totals["gold_fields"] else 0.0

    gates = {
        "precision_gte_0_97": {"threshold": 0.97, "actual": round(precision, 6), "pass": precision >= 0.97},
        "recall_gte_0_90": {"threshold": 0.90, "actual": round(recall, 6), "pass": recall >= 0.90},
        "wrong_period_rate_lte_0_01": {
            "threshold": 0.01,
            "actual": round(wrong_period_rate, 6),
            "pass": wrong_period_rate <= 0.01,
        },
        "wrong_currency_rate_lte_0_01": {
            "threshold": 0.01,
            "actual": round(wrong_currency_rate, 6),
            "pass": wrong_currency_rate <= 0.01,
        },
    }

    metric_rows: List[Dict[str, object]] = []
    for metric in sorted(metric_agg.keys()):
        rec = metric_agg[metric]
        pm = (rec["tp"] / rec["predicted"]) if rec["predicted"] else 0.0
        rm = (rec["tp"] / rec["gold_fields"]) if rec["gold_fields"] else 0.0
        f1m = ((2.0 * pm * rm) / (pm + rm)) if (pm + rm) else 0.0
        metric_rows.append(
            {
                "metric": metric,
                "gold_fields": rec["gold_fields"],
                "predicted": rec["predicted"],
                "tp": rec["tp"],
                "precision": round(pm, 6),
                "recall": round(rm, 6),
                "f1": round(f1m, 6),
            }
        )

    taxonomy_rows = [
        {"failure_type": k, "count": int(v)}
        for k, v in sorted(taxonomy_agg.items(), key=lambda item: (-int(item[1]), str(item[0])))
    ]

    aggregate = {
        "generated_at_utc": _utc_now(),
        "input_scorecards": [str(p) for p in scorecard_paths],
        "per_ticker": sorted(per_ticker, key=lambda r: str(r["ticker"])),
        "totals": {
            **totals,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        },
        "taxonomy_counts": {k: int(v) for k, v in sorted(taxonomy_agg.items())},
        "gates": gates,
    }

    aggregate_json = out_dir / "aggregate_scorecard.json"
    metric_csv = out_dir / "aggregate_metric_family.csv"
    taxonomy_csv = out_dir / "aggregate_taxonomy.csv"
    ticker_csv = out_dir / "aggregate_ticker_scores.csv"

    aggregate_json.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    _write_csv(
        metric_csv,
        metric_rows,
        ["metric", "gold_fields", "predicted", "tp", "precision", "recall", "f1"],
    )
    _write_csv(taxonomy_csv, taxonomy_rows, ["failure_type", "count"])
    _write_csv(
        ticker_csv,
        sorted(per_ticker, key=lambda r: str(r["ticker"])),
        ["ticker", "gold_fields", "predicted", "tp", "fp", "fn", "precision", "recall", "f1", "scorecard_json"],
    )

    return {
        "aggregate_scorecard_json": str(aggregate_json),
        "aggregate_metric_family_csv": str(metric_csv),
        "aggregate_taxonomy_csv": str(taxonomy_csv),
        "aggregate_ticker_scores_csv": str(ticker_csv),
        "aggregate": aggregate,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate per-ticker gold scorecards.")
    ap.add_argument("--scorecard", action="append", default=[], help="Path to scorecard.json (repeatable).")
    ap.add_argument(
        "--scorecards",
        default="",
        help="Comma-separated scorecard.json paths (optional alternative to repeated --scorecard).",
    )
    ap.add_argument("--out-dir", required=True, help="Output directory for aggregate artifacts.")
    args = ap.parse_args()

    paths = [Path(p).expanduser().resolve() for p in args.scorecard if str(p).strip()]
    if str(args.scorecards).strip():
        for p in str(args.scorecards).split(","):
            if str(p).strip():
                paths.append(Path(p).expanduser().resolve())
    unique_paths = sorted({p for p in paths})
    result = aggregate_scorecards(unique_paths, Path(args.out_dir).expanduser().resolve())

    totals = result["aggregate"]["totals"]
    print(f"Scorecards: {len(unique_paths)}")
    print(f"Aggregate TP/FP/FN: {totals['tp']}/{totals['fp']}/{totals['fn']}")
    print(
        "Aggregate Precision/Recall/F1: "
        f"{totals['precision']:.6f}/{totals['recall']:.6f}/{totals['f1']:.6f}"
    )
    print(f"Output: {result['aggregate_scorecard_json']}")
    print(f"Output: {result['aggregate_metric_family_csv']}")
    print(f"Output: {result['aggregate_taxonomy_csv']}")
    print(f"Output: {result['aggregate_ticker_scores_csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
