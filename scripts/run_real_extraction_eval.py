#!/usr/bin/env python3
"""Run real ASX extraction evaluation against a gold corpus.

This script intentionally evaluates dataset and extraction outputs only.
It does not modify extraction logic, pipeline stages, or database schema.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FINANCIAL_ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
BACKEND_ROOT = FINANCIAL_ENGINE_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.multipass_extraction import run_multipass_extraction


DEFAULT_DATASET_DIR = FINANCIAL_ENGINE_ROOT / "data" / "extraction_gold_real"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "extraction_real_eval_summary.md"
DEFAULT_RESULTS_JSON = REPO_ROOT / "reports" / "extraction_real_eval_results.json"
DEFAULT_LOCAL_LLAMACPP_API_KEY = "local-openai-key"

CONTEXT_FIELDS = ("period_type", "period_end", "currency", "scale")
SUPPORTED_METRICS = ("revenue", "operating_cash_flow", "net_debt")
METRIC_KEY_MAP = {
    "revenue": "revenue",
    "operating_cash_flow": "operating_cf",
    "net_debt": "net_debt",
}


@dataclass(frozen=True)
class GoldDocument:
    document_id: str
    source_file: str
    period_type: str
    period_end: str
    currency: str
    scale: str
    metrics: dict[str, float | None]
    expected_trust: str


def _discover_local_llamacpp_api_key() -> str:
    try:
        proc = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""

    for line in proc.stdout.splitlines():
        if "llama-server" not in line or "--api-key" not in line:
            continue
        _, _, tail = line.partition("--api-key")
        candidate = tail.strip().split(maxsplit=1)[0]
        if candidate:
            return candidate
    return ""


def _persist_local_llm_api_key() -> str:
    existing = str(os.environ.get("LLM_API_KEY") or "").strip()
    if existing:
        return existing

    fallback_key = _discover_local_llamacpp_api_key()
    if not fallback_key:
        fallback_key = DEFAULT_LOCAL_LLAMACPP_API_KEY

    os.environ["LLM_API_KEY"] = fallback_key
    return fallback_key


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multipass extraction over real gold documents and score results.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Directory containing gold corpus JSON files.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        default=DEFAULT_RESULTS_JSON,
        help="Detailed JSON results output path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of documents to run (0 = all).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Relative numeric tolerance for metric comparisons.",
    )
    return parser.parse_args()


def _load_gold_document(path: Path) -> GoldDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"gold file must be a JSON object: {path}")

    missing = [
        key
        for key in (
            "document_id",
            "source_file",
            "period_type",
            "period_end",
            "currency",
            "scale",
            "metrics",
            "expected_trust",
        )
        if key not in payload
    ]
    if missing:
        raise ValueError(f"missing required fields in {path}: {', '.join(missing)}")

    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, dict):
        raise ValueError(f"metrics must be an object in {path}")

    metrics: dict[str, float | None] = {}
    for metric_name, metric_value in metrics_raw.items():
        if metric_name not in SUPPORTED_METRICS:
            raise ValueError(
                f"unsupported metric '{metric_name}' in {path}; "
                f"supported={SUPPORTED_METRICS}"
            )
        if metric_value is None:
            metrics[metric_name] = None
            continue
        if isinstance(metric_value, bool) or not isinstance(metric_value, (int, float)):
            raise ValueError(
                f"metric '{metric_name}' must be numeric or null in {path}, "
                f"got {type(metric_value)}"
            )
        metrics[metric_name] = float(metric_value)

    expected_trust = str(payload.get("expected_trust") or "").strip().lower()
    if expected_trust not in {"trusted", "abstain", "quarantine"}:
        raise ValueError(f"invalid expected_trust '{expected_trust}' in {path}")

    period_type = str(payload.get("period_type") or "").strip().upper()
    if period_type not in {"A", "H", "Q"}:
        raise ValueError(f"period_type must be one of A/H/Q in {path}")

    currency = str(payload.get("currency") or "").strip().upper()
    if not currency:
        raise ValueError(f"currency must be non-empty in {path}")

    scale = str(payload.get("scale") or "").strip().lower()
    if scale not in {"units", "thousands", "millions"}:
        raise ValueError(f"scale must be units|thousands|millions in {path}")

    return GoldDocument(
        document_id=str(payload.get("document_id")),
        source_file=str(payload.get("source_file")),
        period_type=period_type,
        period_end=str(payload.get("period_end")),
        currency=currency,
        scale=scale,
        metrics=metrics,
        expected_trust=expected_trust,
    )


def _load_dataset(dataset_dir: Path) -> list[GoldDocument]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"dataset directory not found: {dataset_dir}")

    docs = [_load_gold_document(path) for path in sorted(dataset_dir.glob("*.json"))]
    if not docs:
        raise ValueError(f"no dataset files found in {dataset_dir}")
    return docs


def _resolve_source_path(source_file: str) -> Path:
    candidate = Path(source_file)
    if candidate.is_absolute():
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"source file does not exist: {candidate}")

    by_engine_root = FINANCIAL_ENGINE_ROOT / candidate
    if by_engine_root.exists():
        return by_engine_root

    by_repo_root = REPO_ROOT / candidate
    if by_repo_root.exists():
        return by_repo_root

    raise FileNotFoundError(
        f"could not resolve source_file '{source_file}' relative to {FINANCIAL_ENGINE_ROOT}"
    )


def _extract_ticker_from_source(source_path: Path) -> str:
    parts = list(source_path.parts)
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "UNKNOWN"


def _normalize_context_value(field: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if field in {"period_type", "currency"}:
        return text.upper()
    if field == "scale":
        return text.lower()
    if field == "period_end":
        return text[:10]
    return text


def _context_expectations(doc: GoldDocument) -> dict[str, str]:
    return {
        "period_type": doc.period_type,
        "period_end": doc.period_end,
        "currency": doc.currency,
        "scale": doc.scale,
    }


def _coerce_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped.replace(",", ""))
        except ValueError:
            return None
    return None


def _compare_metric(
    expected: float | None,
    actual: float | None,
    tolerance: float,
) -> tuple[str, str]:
    if expected is None:
        if actual is None:
            return "abstain", "gold expects abstention (null); extractor returned null"
        return "wrong", f"gold expects null but extractor returned {actual:.6g}"

    if actual is None:
        return "missing", "extractor returned null for required metric"

    allowed_delta = max(abs(expected) * tolerance, 1.0)
    delta = abs(actual - expected)
    if delta <= allowed_delta:
        return (
            "correct",
            f"within tolerance (delta={delta:.6g}, allowed={allowed_delta:.6g})",
        )
    return (
        "wrong",
        f"outside tolerance (delta={delta:.6g}, allowed={allowed_delta:.6g})",
    )


def _derive_trust(
    context_ok: bool, metric_results: dict[str, dict[str, Any]]
) -> tuple[str, list[str]]:
    if not context_ok:
        return "quarantine", ["context_mismatch"]

    if not metric_results:
        return "abstain", ["no_gold_metrics"]

    blockers: list[str] = []
    saw_abstain = False
    for metric_name, result in metric_results.items():
        status = str(result.get("status") or "")
        if status in {"wrong", "missing"}:
            blockers.append(f"{metric_name}:{status}")
        elif status == "abstain":
            saw_abstain = True
            blockers.append(f"{metric_name}:abstain")

    if blockers:
        return "abstain", blockers
    if saw_abstain:
        return "abstain", ["metric_abstain"]
    return "trusted", []


def _evaluate_document(
    doc: GoldDocument,
    *,
    tolerance: float,
) -> dict[str, Any]:
    _persist_local_llm_api_key()
    source_path = _resolve_source_path(doc.source_file)
    ticker = _extract_ticker_from_source(source_path)
    metadata = {
        "document_id": doc.document_id,
        "ticker": ticker,
        "title": source_path.name,
    }

    extraction_error = None
    try:
        extraction_result = run_multipass_extraction(
            str(source_path),
            metadata,
            llm_client=None,
            skip_narrative=True,
        )
        payload = (
            extraction_result.payload
            if isinstance(extraction_result.payload, dict)
            else {}
        )
        extraction_status = str(getattr(extraction_result, "status", "failed"))
        extraction_error = getattr(extraction_result, "error", None)
    except Exception as exc:  # noqa: BLE001
        payload = {}
        extraction_status = "failed"
        extraction_error = str(exc)

    expected_context = _context_expectations(doc)
    actual_context: dict[str, str | None] = {}
    context_mismatches: list[str] = []
    for field in CONTEXT_FIELDS:
        expected_value = _normalize_context_value(field, expected_context[field])
        actual_value = _normalize_context_value(field, payload.get(field))
        actual_context[field] = actual_value
        if expected_value != actual_value:
            context_mismatches.append(
                f"{field}: expected={expected_value!r} actual={actual_value!r}"
            )
    context_ok = not context_mismatches

    payload_metrics = (
        payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    )
    metric_results: dict[str, dict[str, Any]] = {}
    for metric_name, expected_value in doc.metrics.items():
        extraction_key = METRIC_KEY_MAP[metric_name]
        actual_value = _coerce_numeric(payload_metrics.get(extraction_key))
        status, reason = _compare_metric(expected_value, actual_value, tolerance)
        metric_results[metric_name] = {
            "status": status,
            "expected": expected_value,
            "actual": actual_value,
            "reason": reason,
            "source_metric_key": extraction_key,
        }

    trust_outcome, trust_triggers = _derive_trust(context_ok, metric_results)
    trust_matches_expected = trust_outcome == doc.expected_trust

    mismatches = []
    mismatches.extend(context_mismatches)
    for metric_name, result in metric_results.items():
        if result["status"] != "correct":
            mismatches.append(f"metric:{metric_name}:{result['reason']}")
    if not trust_matches_expected:
        mismatches.append(
            f"trust: expected={doc.expected_trust} actual={trust_outcome}"
        )
    if extraction_error:
        mismatches.append(f"extraction_error:{extraction_error}")

    return {
        "document_id": doc.document_id,
        "source_file": doc.source_file,
        "source_path": str(source_path),
        "period_type": doc.period_type,
        "period_end": doc.period_end,
        "expected_trust": doc.expected_trust,
        "extraction_status": extraction_status,
        "extraction_error": extraction_error,
        "context_correct": context_ok,
        "context_expected": expected_context,
        "context_actual": actual_context,
        "context_mismatches": context_mismatches,
        "metric_results": metric_results,
        "trust_outcome": trust_outcome,
        "trust_triggers": trust_triggers,
        "trust_matches_expected": trust_matches_expected,
        "mismatch_reasons": mismatches,
    }


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    trust_distribution = {"trusted": 0, "abstain": 0, "quarantine": 0}
    metric_status_counts = {"correct": 0, "wrong": 0, "missing": 0, "abstain": 0}
    per_metric_failure_counts: dict[str, dict[str, int]] = {
        metric: {"wrong": 0, "missing": 0, "abstain": 0} for metric in SUPPORTED_METRICS
    }

    total_metric_checks = 0
    context_correct_count = 0
    trust_match_count = 0

    for result in results:
        trust = result["trust_outcome"]
        trust_distribution[trust] = trust_distribution.get(trust, 0) + 1
        if result["context_correct"]:
            context_correct_count += 1
        if result["trust_matches_expected"]:
            trust_match_count += 1

        for metric_name, metric_result in result["metric_results"].items():
            status = metric_result["status"]
            total_metric_checks += 1
            metric_status_counts[status] = metric_status_counts.get(status, 0) + 1
            if status != "correct":
                per_metric_failure_counts.setdefault(
                    metric_name,
                    {"wrong": 0, "missing": 0, "abstain": 0},
                )
                if status in {"wrong", "missing", "abstain"}:
                    per_metric_failure_counts[metric_name][status] += 1

    correct_count = metric_status_counts.get("correct", 0)
    accuracy = (correct_count / total_metric_checks) if total_metric_checks else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(results),
        "context_correct_documents": context_correct_count,
        "context_accuracy": (context_correct_count / len(results) if results else 0.0),
        "total_metric_checks": total_metric_checks,
        "metric_status_counts": metric_status_counts,
        "total_accuracy": accuracy,
        "trust_distribution": trust_distribution,
        "trust_matches_expected": trust_match_count,
        "per_metric_failure_counts": per_metric_failure_counts,
    }


def _build_report_markdown(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    dataset_dir: Path,
) -> str:
    lines: list[str] = []
    lines.append("# Extraction Real Eval Summary")
    lines.append("")
    lines.append(f"- Generated: {summary['generated_at']}")
    lines.append(f"- Dataset: `{dataset_dir}`")
    lines.append(f"- Documents: {summary['total_documents']}")
    lines.append("")
    lines.append("## Total Accuracy")
    lines.append("")
    lines.append(
        "- Metric accuracy: "
        f"{summary['total_accuracy'] * 100:.2f}% "
        f"({summary['metric_status_counts'].get('correct', 0)}/"
        f"{summary['total_metric_checks']})"
    )
    lines.append(
        "- Context accuracy: "
        f"{summary['context_accuracy'] * 100:.2f}% "
        f"({summary['context_correct_documents']}/{summary['total_documents']})"
    )
    lines.append(
        "- Trust matches expected: "
        f"{summary['trust_matches_expected']}/{summary['total_documents']}"
    )
    lines.append("")
    lines.append("## Trust Distribution")
    lines.append("")
    lines.append("| Trust outcome | Count |")
    lines.append("| --- | ---: |")
    for trust in ("trusted", "abstain", "quarantine"):
        lines.append(f"| {trust} | {summary['trust_distribution'].get(trust, 0)} |")
    lines.append("")
    lines.append("## Per-Metric Failure Counts")
    lines.append("")
    lines.append("| Metric | Wrong | Missing | Abstain |")
    lines.append("| --- | ---: | ---: | ---: |")
    for metric in SUPPORTED_METRICS:
        counts = summary["per_metric_failure_counts"].get(
            metric,
            {"wrong": 0, "missing": 0, "abstain": 0},
        )
        lines.append(
            f"| {metric} | {counts['wrong']} | {counts['missing']} | {counts['abstain']} |"
        )
    lines.append("")
    lines.append("## Per-Document Breakdown")
    lines.append("")
    lines.append(
        "| Document | Period | Context | Trust (actual / expected) | Metric statuses | Mismatch reasons |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for result in results:
        period = f"{result['period_type']} {result['period_end']}"
        context = "ok" if result["context_correct"] else "mismatch"
        trust = f"{result['trust_outcome']} / {result['expected_trust']}"
        metric_statuses = ", ".join(
            f"{name}:{item['status']}"
            for name, item in result["metric_results"].items()
        )
        mismatch = (
            "; ".join(result["mismatch_reasons"]) if result["mismatch_reasons"] else "-"
        )
        lines.append(
            f"| {result['document_id']} | {period} | {context} | {trust} | "
            f"{metric_statuses} | {mismatch} |"
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = _parse_args()
    dataset_dir = args.dataset_dir
    report_path = args.report_path
    results_json = args.results_json

    gold_docs = _load_dataset(dataset_dir)
    if args.limit > 0:
        gold_docs = gold_docs[: args.limit]

    results: list[dict[str, Any]] = []
    for index, doc in enumerate(gold_docs, start=1):
        print(f"[{index}/{len(gold_docs)}] evaluating {doc.document_id}")
        results.append(
            _evaluate_document(
                doc,
                tolerance=max(float(args.tolerance), 0.0),
            )
        )

    summary = _summarize(results)
    output_payload = {
        "dataset_dir": str(dataset_dir),
        "summary": summary,
        "documents": results,
    }

    results_json.parent.mkdir(parents=True, exist_ok=True)
    results_json.write_text(
        json.dumps(output_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _build_report_markdown(summary, results, dataset_dir=dataset_dir),
        encoding="utf-8",
    )

    print("\nPer-document results:")
    for result in results:
        metric_summary = ", ".join(
            f"{name}:{entry['status']}"
            for name, entry in result["metric_results"].items()
        )
        print(
            f"- {result['document_id']}: "
            f"context={'ok' if result['context_correct'] else 'mismatch'}, "
            f"trust={result['trust_outcome']} (expected={result['expected_trust']}), "
            f"metrics=[{metric_summary}]"
        )
        for reason in result["mismatch_reasons"]:
            print(f"  reason: {reason}")

    print("\nSummary:")
    print(
        f"- Metric accuracy: {summary['total_accuracy'] * 100:.2f}% "
        f"({summary['metric_status_counts'].get('correct', 0)}/"
        f"{summary['total_metric_checks']})"
    )
    print(
        f"- Trust distribution: trusted={summary['trust_distribution'].get('trusted', 0)}, "
        f"abstain={summary['trust_distribution'].get('abstain', 0)}, "
        f"quarantine={summary['trust_distribution'].get('quarantine', 0)}"
    )
    print(f"- Wrote detailed JSON: {results_json}")
    print(f"- Wrote markdown report: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
