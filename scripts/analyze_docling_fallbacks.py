#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

try:
    from scripts.extractor_fallback_policy import should_fallback
except Exception:
    from extractor_fallback_policy import should_fallback


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT / "reports" / "pipeline_diagnostics.json"
DEFAULT_OUTPUT_PATH = ROOT / "reports" / "docling_fallback_analysis.json"
FALLBACK_REASON_BUCKETS = (
    "no_rows",
    "no_context_rows",
    "financial_consistency_failed",
    "other",
    "no_fallback",
)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _sorted_counts(counter: Counter[str]) -> Dict[str, int]:
    return {key: counter[key] for key in sorted(counter, key=lambda item: (-counter[item], item))}


def _fallback_bucket(reason: Any) -> str:
    normalized = str(reason or "").strip()
    if normalized in FALLBACK_REASON_BUCKETS:
        return normalized
    return "other"


def load_pipeline_diagnostics(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise RuntimeError("pipeline diagnostics payload must be a JSON object")
    return payload


def build_docling_fallback_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    documents = list(payload.get("documents", []) or [])
    fallback_reason_counts: Counter[str] = Counter()
    fallback_suppression_reason_counts: Counter[str] = Counter()
    rejection_reason_counts: Counter[str] = Counter()
    fallback_documents: List[Dict[str, Any]] = []
    total_docling_rows = 0
    documents_with_consistency_failure = 0
    documents_with_metric_missing = 0
    documents_with_high_conflicts = 0
    fallback_suppressed_count = 0

    for document in documents:
        if bool(document.get("fallback_suppressed", False)):
            fallback_suppressed_count += 1
            suppression_reason = str(document.get("fallback_suppression_reason", "") or "").strip()
            if suppression_reason:
                fallback_suppression_reason_counts[suppression_reason] += 1

        if not bool(document.get("fallback_triggered", False)):
            continue

        rejection_reasons = dict(document.get("rejection_reasons", {}) or {})
        raw_fallback_reason = str(document.get("fallback_reason", "") or "").strip()
        docling_rows = _safe_int(document.get("docling_row_count_before_filtering"))
        context_rows = _safe_int(document.get("context_rows"))
        tsr_tables_processed = _safe_int(document.get("tsr_tables_processed"))
        consistency_failures = 0
        diagnostics = document.get("diagnostics", {})
        if isinstance(diagnostics, dict):
            consistency_failures = _safe_int(diagnostics.get("consistency_failures"))
        financial_consistency_failed = (
            raw_fallback_reason == "financial_consistency_failed" or consistency_failures > 0
        )
        critical_metrics_missing = raw_fallback_reason == "critical_metrics_missing"
        fallback = should_fallback(
            docling_rows=docling_rows,
            context_rows=context_rows,
            tsr_tables=tsr_tables_processed,
            critical_metrics_missing=critical_metrics_missing,
            consistency_failed=financial_consistency_failed,
        )
        if fallback:
            if docling_rows == 0:
                reason = "no_rows"
            elif context_rows == 0 and tsr_tables_processed == 0:
                reason = "no_context_rows"
            elif financial_consistency_failed:
                reason = "financial_consistency_failed"
            else:
                reason = "other"
        else:
            reason = "no_fallback"
        fallback_reason = _fallback_bucket(reason)

        fallback_reason_counts[fallback_reason] += 1
        total_docling_rows += docling_rows
        if financial_consistency_failed:
            documents_with_consistency_failure += 1
        if critical_metrics_missing:
            documents_with_metric_missing += 1
        if _safe_int(rejection_reasons.get("canonical_conflict_same_period")) >= 10:
            documents_with_high_conflicts += 1

        for reason, count in rejection_reasons.items():
            rejection_reason_counts[str(reason)] += _safe_int(count)

        fallback_documents.append(
            {
                "ticker": str(document.get("ticker", "")).strip(),
                "document": str(document.get("document", "")).strip(),
                "fallback_reason": fallback_reason,
                "reported_fallback_reason": raw_fallback_reason,
                "docling_row_count_before_filtering": docling_rows,
                "rejection_reasons": {str(key): _safe_int(value) for key, value in rejection_reasons.items()},
                "context_rows": context_rows,
                "rejected_rows": _safe_int(document.get("rejected_rows")),
                "tsr_tables_processed": tsr_tables_processed,
            }
        )

    for bucket in FALLBACK_REASON_BUCKETS:
        fallback_reason_counts.setdefault(bucket, 0)

    fallback_documents.sort(key=lambda item: (item["ticker"], item["document"]))
    fallback_documents_total = len(fallback_documents)
    average_docling_rows = 0.0
    if fallback_documents_total > 0:
        average_docling_rows = total_docling_rows / float(fallback_documents_total)

    return {
        "fallback_documents_total": fallback_documents_total,
        "fallback_reason_counts": {bucket: fallback_reason_counts[bucket] for bucket in FALLBACK_REASON_BUCKETS},
        "fallback_suppressed_count": fallback_suppressed_count,
        "fallback_suppression_reason_counts": _sorted_counts(fallback_suppression_reason_counts),
        "top_rejection_reasons": _sorted_counts(rejection_reason_counts),
        "average_docling_row_count_before_filtering": average_docling_rows,
        "documents_with_consistency_failure": documents_with_consistency_failure,
        "documents_with_metric_missing": documents_with_metric_missing,
        "documents_with_high_conflicts": documents_with_high_conflicts,
        "documents": fallback_documents,
    }


def write_docling_fallback_analysis(out_path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis = build_docling_fallback_analysis(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    return analysis


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze Docling fallback documents from pipeline diagnostics.")
    ap.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Pipeline diagnostics JSON path")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Fallback analysis JSON output path")
    args = ap.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = load_pipeline_diagnostics(input_path)
    analysis = write_docling_fallback_analysis(output_path, payload)
    print(
        f"Wrote {output_path} "
        f"(fallback_documents_total={_safe_int(analysis.get('fallback_documents_total'))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
