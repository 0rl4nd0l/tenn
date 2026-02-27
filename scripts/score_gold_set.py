#!/usr/bin/env python3
"""Score canonical extraction output against a per-document gold set."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

DOC_ID_SUFFIX_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
SCALE_BUCKETS = (1e-9, 1e-6, 1e-3, 1.0, 1e3, 1e6, 1e9)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]
        return float(text)
    except (TypeError, ValueError):
        return None


def _norm_period(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    m = DATE_RE.search(text)
    if m:
        return str(m.group(1))
    return text


def _norm_metric(value: object) -> str:
    metric = str(value or "").strip().lower()
    alias = {
        "npat": "net_income",
        "capex": "capital_expenditure",
    }
    return alias.get(metric, metric)


def _norm_scope(value: object) -> str:
    scope = str(value or "").strip().lower()
    alias = {
        "consolidated_statement": "group",
        "consolidated": "group",
        "group": "group",
        "parent": "parent",
        "any": "any",
    }
    return alias.get(scope, scope or "unknown")


def _doc_id_from_file(file_path: object) -> str:
    stem = Path(str(file_path or "")).stem
    if not stem:
        return ""
    m = DOC_ID_SUFFIX_RE.search(stem)
    if m:
        return str(m.group(1)).lower()
    return stem


def _load_doc_map(path: Path | None) -> Dict[str, str]:
    if path is None:
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, dict):
        if isinstance(obj.get("aliases"), dict):
            return {str(k): str(v) for k, v in obj["aliases"].items()}
        return {str(k): str(v) for k, v in obj.items() if isinstance(v, (str, int, float))}
    return {}


def _load_gold_docs(gold_dir: Path) -> List[Dict[str, object]]:
    docs: List[Dict[str, object]] = []
    for path in sorted(gold_dir.rglob("*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError(f"Gold file must be JSON object: {path}")
        for key in ("doc_id", "ticker", "pdf_sha256", "published_at", "fields"):
            if key not in obj:
                raise ValueError(f"Gold file missing required field '{key}': {path}")
        fields = obj.get("fields")
        if not isinstance(fields, list):
            raise ValueError(f"Gold file fields must be list: {path}")
        for idx, fld in enumerate(fields):
            if not isinstance(fld, dict):
                raise ValueError(f"Gold field entry must be object: {path}#{idx}")
            for req in ("metric", "period_end", "period_type", "value", "unit_scale", "currency", "scope"):
                if req not in fld:
                    raise ValueError(f"Gold field missing '{req}': {path}#{idx}")
        rec = dict(obj)
        rec["_gold_file"] = str(path)
        docs.append(rec)
    return docs


def _load_canonical_rows(canonical_csv: Path, doc_alias: Dict[str, str]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with canonical_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for rec in reader:
            metric = _norm_metric(rec.get("metric_base", rec.get("metric", "")))
            if not metric:
                continue
            period_end = _norm_period(rec.get("statement_period_end", rec.get("period_end", "")))
            doc_id = _doc_id_from_file(rec.get("file", ""))
            if not doc_id:
                continue
            mapped_doc_id = str(doc_alias.get(doc_id, doc_id))
            value = _to_float(rec.get("value"))
            if value is None:
                value = _to_float(rec.get("raw_value"))
            if value is None:
                continue
            rows.append(
                {
                    "doc_id": mapped_doc_id,
                    "metric": metric,
                    "period_end": period_end,
                    "period_type": str(rec.get("statement_period", rec.get("period", ""))).strip(),
                    "value": value,
                    "unit_scale": _to_float(rec.get("unit_scale", 1.0)) or 1.0,
                    "currency": str(rec.get("currency", "")).strip().upper() or "UNKNOWN",
                    "scope": _norm_scope(rec.get("statement_scope", "")),
                    "file": str(rec.get("file", "")),
                    "raw_value": str(rec.get("raw_value", "")),
                }
            )
    return rows


def _value_tolerance(metric: str, gold_value: float, period_type: str) -> float:
    m = str(metric or "").lower()
    p = str(period_type or "").lower()
    if "pct" in m or "percent" in p:
        return 0.05
    if "ratio" in m or "_to_" in m:
        return 0.002
    return max(2.0, 0.0001 * abs(float(gold_value)))


def _choose_best_by_value(candidates: List[Dict[str, object]], gold_value: float) -> Dict[str, object] | None:
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(float(c.get("value", 0.0)) - float(gold_value)))


def _is_scale_bucket_mismatch(gold_value: float, candidate_value: float) -> bool:
    g = abs(float(gold_value))
    c = abs(float(candidate_value))
    if g == 0.0 or c == 0.0:
        return False
    ratio = c / g
    nearest = min(SCALE_BUCKETS, key=lambda s: abs(ratio - s) / max(s, 1e-12))
    if nearest == 1.0:
        return False
    rel = abs(ratio - nearest) / max(nearest, 1e-12)
    return rel <= 0.02


def _has_duplicate_collision(candidates: List[Dict[str, object]], tolerance: float) -> bool:
    if len(candidates) < 2:
        return False
    values = sorted(float(c.get("value", 0.0) or 0.0) for c in candidates)
    if not values:
        return False
    return (values[-1] - values[0]) > (2.0 * float(tolerance))


def _write_csv(path: Path, rows: List[Dict[str, object]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            out = {c: row.get(c, "") for c in columns}
            writer.writerow(out)


def score_gold_set(
    *,
    gold_dir: Path,
    canonical_csv: Path,
    out_dir: Path,
    doc_map_json: Path | None = None,
    failures_jsonl: Path | None = None,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    alias_map = _load_doc_map(doc_map_json)
    gold_docs = _load_gold_docs(gold_dir)
    canonical_rows = _load_canonical_rows(canonical_csv, alias_map)

    can_by_doc_metric: Dict[Tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    predicted_keys: set[Tuple[str, str, str, str]] = set()
    for row in canonical_rows:
        can_by_doc_metric[(str(row["doc_id"]), str(row["metric"]))].append(row)
        predicted_keys.add((str(row["doc_id"]), str(row["metric"]), str(row["period_end"]), str(row["scope"])))

    taxonomy = Counter()
    failures: List[Dict[str, object]] = []
    per_metric = defaultdict(lambda: {"gold": 0, "tp": 0, "pred": 0})
    per_doc = defaultdict(lambda: {"gold": 0, "tp": 0, "fail": 0})

    gold_doc_ids = set()
    gold_metrics = set()
    tp = 0
    total_gold = 0

    for doc in gold_docs:
        doc_id = str(doc.get("doc_id", "")).strip()
        doc_id = str(alias_map.get(doc_id, doc_id))
        gold_doc_ids.add(doc_id)
        fields = list(doc.get("fields", []))
        for field in fields:
            total_gold += 1
            metric = _norm_metric(field.get("metric", ""))
            gold_metrics.add(metric)
            period_end = _norm_period(field.get("period_end", ""))
            period_type = str(field.get("period_type", "")).strip()
            gold_value = _to_float(field.get("value"))
            gold_currency = str(field.get("currency", "")).strip().upper()
            gold_scope = _norm_scope(field.get("scope", ""))
            if gold_value is None:
                taxonomy["missing_gold_value"] += 1
                failures.append(
                    {
                        "doc_id": doc_id,
                        "metric": metric,
                        "period_end": period_end,
                        "failure_type": "missing_gold_value",
                    }
                )
                continue

            per_metric[metric]["gold"] += 1
            per_doc[doc_id]["gold"] += 1

            cands = list(can_by_doc_metric.get((doc_id, metric), []))
            if not cands:
                taxonomy["missing_extraction"] += 1
                per_doc[doc_id]["fail"] += 1
                failures.append(
                    {
                        "doc_id": doc_id,
                        "metric": metric,
                        "period_end": period_end,
                        "failure_type": "missing_extraction",
                    }
                )
                continue

            cands_period = [c for c in cands if str(c.get("period_end", "")) == period_end]
            if not cands_period:
                taxonomy["wrong_period"] += 1
                per_doc[doc_id]["fail"] += 1
                failures.append(
                    {
                        "doc_id": doc_id,
                        "metric": metric,
                        "period_end": period_end,
                        "failure_type": "wrong_period",
                        "candidate_periods": sorted({str(c.get("period_end", "")) for c in cands}),
                    }
                )
                continue

            cands_curr = [c for c in cands_period if str(c.get("currency", "")).upper() == gold_currency and gold_currency != "UNKNOWN"]
            if not cands_curr:
                taxonomy["wrong_currency"] += 1
                per_doc[doc_id]["fail"] += 1
                failures.append(
                    {
                        "doc_id": doc_id,
                        "metric": metric,
                        "period_end": period_end,
                        "failure_type": "wrong_currency",
                        "gold_currency": gold_currency,
                        "candidate_currencies": sorted({str(c.get("currency", "")) for c in cands_period}),
                    }
                )
                continue

            if gold_scope != "any":
                cands_scope = [c for c in cands_curr if _norm_scope(c.get("scope", "")) == gold_scope]
            else:
                cands_scope = cands_curr
            if not cands_scope:
                taxonomy["wrong_scope"] += 1
                per_doc[doc_id]["fail"] += 1
                failures.append(
                    {
                        "doc_id": doc_id,
                        "metric": metric,
                        "period_end": period_end,
                        "failure_type": "wrong_scope",
                        "gold_scope": gold_scope,
                        "candidate_scopes": sorted({_norm_scope(c.get("scope", "")) for c in cands_curr}),
                    }
                )
                continue

            chosen = _choose_best_by_value(cands_scope, gold_value)
            if chosen is None:
                taxonomy["missing_extraction"] += 1
                per_doc[doc_id]["fail"] += 1
                continue

            tol = _value_tolerance(metric, gold_value, period_type)
            candidate_value = float(chosen.get("value", 0.0) or 0.0)
            diff = candidate_value - float(gold_value)

            if abs(diff) <= tol:
                tp += 1
                per_metric[metric]["tp"] += 1
                per_doc[doc_id]["tp"] += 1
                continue

            if _has_duplicate_collision(cands_scope, tol):
                taxonomy["duplicate_collision"] += 1
                fail_type = "duplicate_collision"
            elif abs(abs(candidate_value) - abs(float(gold_value))) <= tol and math.copysign(1.0, candidate_value) != math.copysign(
                1.0, float(gold_value)
            ):
                taxonomy["sign_error"] += 1
                fail_type = "sign_error"
            elif _is_scale_bucket_mismatch(float(gold_value), candidate_value):
                taxonomy["wrong_unit_scale"] += 1
                fail_type = "wrong_unit_scale"
            else:
                taxonomy["wrong_value"] += 1
                fail_type = "wrong_value"

            per_doc[doc_id]["fail"] += 1
            failures.append(
                {
                    "doc_id": doc_id,
                    "metric": metric,
                    "period_end": period_end,
                    "failure_type": fail_type,
                    "gold_value": gold_value,
                    "candidate_value": candidate_value,
                    "difference": diff,
                    "tolerance": tol,
                    "candidate_file": str(chosen.get("file", "")),
                }
            )

    # Predicted positives for precision: restrict to doc+metric space in gold.
    predicted_keys_filtered = {
        k for k in predicted_keys if k[0] in gold_doc_ids and k[1] in gold_metrics
    }
    predicted_by_doc = Counter(k[0] for k in predicted_keys_filtered)
    predicted_total = int(len(predicted_keys_filtered))
    fp = max(0, predicted_total - tp)
    fn = max(0, total_gold - tp)

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / total_gold) if total_gold > 0 else 0.0
    f1 = float((2 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0

    for key in predicted_keys_filtered:
        per_metric[key[1]]["pred"] += 1

    per_metric_rows: List[Dict[str, object]] = []
    for metric in sorted(per_metric.keys()):
        g = int(per_metric[metric]["gold"])
        tpm = int(per_metric[metric]["tp"])
        pred = int(per_metric[metric]["pred"])
        pm = float(tpm / pred) if pred > 0 else 0.0
        rm = float(tpm / g) if g > 0 else 0.0
        f1m = float((2 * pm * rm) / (pm + rm)) if (pm + rm) > 0 else 0.0
        per_metric_rows.append(
            {
                "metric": metric,
                "gold_fields": g,
                "predicted": pred,
                "tp": tpm,
                "precision": round(pm, 6),
                "recall": round(rm, 6),
                "f1": round(f1m, 6),
            }
        )

    per_doc_rows: List[Dict[str, object]] = []
    doc_breakdown_rows: List[Dict[str, object]] = []
    for doc_id in sorted(per_doc.keys()):
        rec = per_doc[doc_id]
        gold_fields = int(rec["gold"])
        tp_doc = int(rec["tp"])
        predicted_doc = int(predicted_by_doc.get(doc_id, 0))
        fn_doc = max(0, gold_fields - tp_doc)
        fp_doc = max(0, predicted_doc - tp_doc)
        failures_doc = fn_doc + fp_doc
        per_doc_rows.append(
            {
                "doc_id": doc_id,
                "gold_fields": gold_fields,
                "tp": tp_doc,
                "failures": int(rec["fail"]),
                "recall": round(float(tp_doc / gold_fields) if gold_fields else 0.0, 6),
            }
        )
        doc_breakdown_rows.append(
            {
                "doc_id": doc_id,
                "gold_fields": gold_fields,
                "tp": tp_doc,
                "fp": fp_doc,
                "fn": fn_doc,
                "failures": failures_doc,
                "recall": round(float(tp_doc / gold_fields) if gold_fields else 0.0, 6),
            }
        )

    taxonomy_counts = {k: int(v) for k, v in sorted(taxonomy.items())}

    scorecard = {
        "generated_at_utc": _utc_now(),
        "gold_dir": str(gold_dir),
        "canonical_csv": str(canonical_csv),
        "totals": {
            "gold_fields": int(total_gold),
            "predicted": int(predicted_total),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        },
        "per_metric": per_metric_rows,
        "per_doc": per_doc_rows,
        "taxonomy_counts": taxonomy_counts,
        "failures_count": int(len(failures)),
    }

    scorecard_json = out_dir / "scorecard.json"
    scorecard_csv = out_dir / "scorecard.csv"
    doc_breakdown_csv = out_dir / "doc_breakdown.csv"
    taxonomy_json = out_dir / "taxonomy_counts.json"
    failures_path = failures_jsonl or (out_dir / "failures.jsonl")

    scorecard_json.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    _write_csv(
        scorecard_csv,
        per_metric_rows,
        ["metric", "gold_fields", "predicted", "tp", "precision", "recall", "f1"],
    )
    _write_csv(
        doc_breakdown_csv,
        doc_breakdown_rows,
        ["doc_id", "gold_fields", "tp", "fp", "fn", "failures", "recall"],
    )
    taxonomy_json.write_text(json.dumps(taxonomy_counts, indent=2), encoding="utf-8")

    failures_path.parent.mkdir(parents=True, exist_ok=True)
    with failures_path.open("w", encoding="utf-8") as f:
        for row in failures:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    return {
        "scorecard_json": str(scorecard_json),
        "scorecard_csv": str(scorecard_csv),
        "doc_breakdown_csv": str(doc_breakdown_csv),
        "taxonomy_json": str(taxonomy_json),
        "failures_jsonl": str(failures_path),
        **scorecard,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Score canonical extraction output against gold set labels.")
    ap.add_argument("--gold-dir", required=True, help="Directory containing gold/<TICKER>/<doc_id>.json files")
    ap.add_argument("--canonical-csv", required=True, help="Canonical CSV (canonical.csv or canonical_section_capture.csv)")
    ap.add_argument("--out-dir", required=True, help="Output directory for score artifacts")
    ap.add_argument("--doc-map-json", default="", help="Optional doc-id alias map JSON")
    ap.add_argument("--failures-jsonl", default="", help="Optional output path override for failures.jsonl")
    args = ap.parse_args()

    result = score_gold_set(
        gold_dir=Path(args.gold_dir).expanduser().resolve(),
        canonical_csv=Path(args.canonical_csv).expanduser().resolve(),
        out_dir=Path(args.out_dir).expanduser().resolve(),
        doc_map_json=(Path(args.doc_map_json).expanduser().resolve() if str(args.doc_map_json).strip() else None),
        failures_jsonl=(Path(args.failures_jsonl).expanduser().resolve() if str(args.failures_jsonl).strip() else None),
    )

    totals = result.get("totals", {})
    print(f"Gold fields: {totals.get('gold_fields', 0)}")
    print(f"Predicted: {totals.get('predicted', 0)}")
    print(f"TP/FP/FN: {totals.get('tp', 0)}/{totals.get('fp', 0)}/{totals.get('fn', 0)}")
    print(f"Precision/Recall/F1: {totals.get('precision', 0):.6f}/{totals.get('recall', 0):.6f}/{totals.get('f1', 0):.6f}")
    print(f"Output: {result['scorecard_json']}")
    print(f"Output: {result['scorecard_csv']}")
    print(f"Output: {result['doc_breakdown_csv']}")
    print(f"Output: {result['taxonomy_json']}")
    print(f"Output: {result['failures_jsonl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
