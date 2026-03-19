#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "batch_benchmark_report.json"
DEFAULT_BENCHMARK_JSON = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "batch_full_benchmark.json"
DEFAULT_RUN_ROOT = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "batch_runs"
DEFAULT_GROUND_TRUTH = REPO_ROOT / "data" / "ground_truth"
DEFAULT_METHODS = "financial_metrics_pdftotext,financial_metrics_docling"
DEFAULT_DOCLING_VENV = REPO_ROOT / ".venv_docling"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.evaluation.anomaly import detect_anomalies
from services.evaluation.confidence import CONFIDENCE_THRESHOLD, MIN_COVERAGE, compute_confidence, fallback_reasons
from services.extraction.router import DOCLING_EXTRACTOR, select_extractor_with_reason


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _score_accuracy(method_payload: Mapping[str, Any] | None) -> float | None:
    if not isinstance(method_payload, Mapping):
        return None
    score = method_payload.get("score")
    if not isinstance(score, Mapping):
        return None
    if str(score.get("status") or "") != "SUCCESS":
        return None
    aggregate = score.get("aggregate")
    if not isinstance(aggregate, Mapping):
        return None
    return _safe_float(aggregate.get("accuracy"))


def _document_diagnostics(method_results: Mapping[str, Any]) -> dict[str, Any]:
    for method_name in ("financial_metrics_pdftotext", "financial_metrics_docling"):
        payload = method_results.get(method_name)
        if not isinstance(payload, Mapping):
            continue
        diagnostics = payload.get("document_diagnostics")
        if isinstance(diagnostics, list) and diagnostics and isinstance(diagnostics[0], Mapping):
            return dict(diagnostics[0])
    return {}


def _confidence_distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "p50": 0.0,
        }
    ordered = sorted(float(value) for value in values)
    count = len(ordered)
    p50 = ordered[count // 2] if count % 2 == 1 else (ordered[(count // 2) - 1] + ordered[count // 2]) / 2.0
    return {
        "count": count,
        "min": round(ordered[0], 6),
        "max": round(ordered[-1], 6),
        "mean": round(sum(ordered) / float(count), 6),
        "p50": round(p50, 6),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch benchmark and evaluate deterministic extraction routing.")
    parser.add_argument("--pdf-dir", required=True, help="Directory of PDFs.")
    parser.add_argument(
        "--ground-truth",
        default=str(DEFAULT_GROUND_TRUTH),
        help="Ground-truth JSON file or directory.",
    )
    parser.add_argument(
        "--methods",
        default=DEFAULT_METHODS,
        help="Benchmark methods passed to benchmark_pdf_extraction.py.",
    )
    parser.add_argument(
        "--docling-venv",
        default=str(DEFAULT_DOCLING_VENV),
        help="Docling venv path.",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_OUT_JSON),
        help="Batch output JSON path.",
    )
    parser.add_argument(
        "--benchmark-json",
        default=str(DEFAULT_BENCHMARK_JSON),
        help="Full benchmark output JSON path.",
    )
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help="Benchmark run root path.",
    )
    parser.add_argument(
        "--subprocess-timeout-sec",
        type=float,
        default=30.0,
        help="Timeout passed to benchmark subprocess-backed extractors.",
    )
    parser.add_argument(
        "--create-docling-venv",
        action="store_true",
        help="Create docling venv if missing.",
    )
    parser.add_argument(
        "--docling-cpu",
        action="store_true",
        help="Force CPU mode for Docling.",
    )
    return parser.parse_args()


def _run_full_benchmark(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    benchmark_json = Path(args.benchmark_json).expanduser().resolve()
    run_root = Path(args.run_root).expanduser().resolve()
    benchmark_json.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "benchmark_pdf_extraction.py"),
        "--pdf-dir",
        str(Path(args.pdf_dir).expanduser().resolve()),
        "--methods",
        str(args.methods),
        "--ground-truth",
        str(Path(args.ground_truth).expanduser().resolve()),
        "--docling-venv",
        str(Path(args.docling_venv).expanduser().resolve()),
        "--subprocess-timeout-sec",
        str(float(args.subprocess_timeout_sec)),
        "--out-json",
        str(benchmark_json),
        "--run-root",
        str(run_root),
    ]
    if bool(args.create_docling_venv):
        command.append("--create-docling-venv")
    if bool(args.docling_cpu):
        command.append("--docling-cpu")

    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or "batch_benchmark_failed")
    payload = json.loads(benchmark_json.read_text(encoding="utf-8"))
    return payload, {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "benchmark_json": str(benchmark_json),
    }


def _routing_eval(benchmark_payload: Mapping[str, Any]) -> dict[str, Any]:
    documents = list(benchmark_payload.get("documents") or [])
    routed_documents: list[dict[str, Any]] = []
    full_accuracy_total = 0.0
    full_accuracy_count = 0
    routed_accuracy_total = 0.0
    routed_accuracy_count = 0
    full_docling_runs = 0
    routed_docling_runs = 0
    full_extractor_runs = 0
    routed_extractor_runs = 0
    fallback_count = 0
    fallback_due_to_anomaly_count = 0
    anomaly_count = 0
    high_severity_anomaly_count = 0
    selected_confidences: list[float] = []

    for document in documents:
        if not isinstance(document, Mapping):
            continue
        method_results = dict(document.get("methods") or {})
        full_extractor_runs += len(method_results)
        if DOCLING_EXTRACTOR in method_results:
            full_docling_runs += 1

        diagnostics = _document_diagnostics(method_results)
        routing_hint = select_extractor_with_reason(diagnostics, method_results)
        pdftotext_payload = method_results.get("financial_metrics_pdftotext")
        if not isinstance(pdftotext_payload, Mapping):
            pdftotext_payload = {}
        docling_payload = method_results.get(DOCLING_EXTRACTOR)

        selected_method = "financial_metrics_pdftotext"
        selected_payload: Mapping[str, Any] = pdftotext_payload
        probe_confidence = compute_confidence(dict(pdftotext_payload))
        selected_confidence = probe_confidence
        probe_anomaly = detect_anomalies(dict(pdftotext_payload))
        selected_anomaly = probe_anomaly
        reasons = fallback_reasons(
            pdftotext_payload,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            min_coverage=MIN_COVERAGE,
        )
        fallback_triggered = bool(reasons)
        fallback_reason = ",".join(reasons)
        if fallback_triggered and "financial_anomaly" in reasons:
            fallback_due_to_anomaly_count += 1
        docling_confidence = None
        docling_anomaly = None
        routed_extractor_runs += 1

        if fallback_triggered:
            fallback_count += 1
            if isinstance(docling_payload, Mapping):
                routed_extractor_runs += 1
                routed_docling_runs += 1
                docling_confidence = compute_confidence(dict(docling_payload))
                docling_anomaly = detect_anomalies(dict(docling_payload))
                if docling_confidence > selected_confidence:
                    selected_method = DOCLING_EXTRACTOR
                    selected_payload = docling_payload
                    selected_confidence = docling_confidence
                    selected_anomaly = docling_anomaly

        if bool(selected_anomaly.get("has_anomaly")):
            anomaly_count += 1
            if str(selected_anomaly.get("severity") or "").lower() == "high":
                high_severity_anomaly_count += 1

        selected_confidences.append(float(selected_confidence))
        routed_accuracy = _score_accuracy(selected_payload)
        if routed_accuracy is not None:
            routed_accuracy_total += routed_accuracy
            routed_accuracy_count += 1

        method_accuracies = []
        for payload in method_results.values():
            if not isinstance(payload, Mapping):
                continue
            accuracy = _score_accuracy(payload)
            if accuracy is not None:
                method_accuracies.append(accuracy)
        full_accuracy = max(method_accuracies) if method_accuracies else None
        if full_accuracy is not None:
            full_accuracy_total += full_accuracy
            full_accuracy_count += 1

        routed_documents.append(
            {
                "pdf": str(document.get("pdf") or ""),
                "doc_id": str(document.get("doc_id") or ""),
                "selected_method": selected_method,
                "routing_reason": str((routing_hint or {}).get("reason") or ""),
                "classifier": (routing_hint or {}).get("classifier"),
                "confidence": round(float(selected_confidence), 6),
                "fallback_triggered": fallback_triggered,
                "fallback_reason": fallback_reason,
                "probe_confidence": round(float(probe_confidence), 6),
                "docling_confidence": round(float(docling_confidence), 6) if docling_confidence is not None else None,
                "probe_anomaly": probe_anomaly,
                "docling_anomaly": docling_anomaly,
                "anomaly": selected_anomaly,
                "selected_accuracy": routed_accuracy,
                "oracle_accuracy": full_accuracy,
                "ground_truth_status": str(document.get("ground_truth_status") or "DATA_MISSING"),
            }
        )

    full_benchmark_accuracy = round(full_accuracy_total / float(full_accuracy_count), 6) if full_accuracy_count > 0 else 0.0
    routed_accuracy = round(routed_accuracy_total / float(routed_accuracy_count), 6) if routed_accuracy_count > 0 else 0.0
    docling_compute_reduction = 0.0
    if full_docling_runs > 0:
        docling_compute_reduction = round(
            float(full_docling_runs - routed_docling_runs) / float(full_docling_runs),
            6,
        )
    total_compute_reduction = 0.0
    if full_extractor_runs > 0:
        total_compute_reduction = round(
            float(full_extractor_runs - routed_extractor_runs) / float(full_extractor_runs),
            6,
        )
    fallback_rate = round(float(fallback_count) / float(max(1, len(routed_documents))), 6)
    anomaly_rate = round(float(anomaly_count) / float(max(1, len(routed_documents))), 6)
    fallback_due_to_anomaly_rate = round(float(fallback_due_to_anomaly_count) / float(max(1, len(routed_documents))), 6)

    return {
        "full_benchmark_accuracy": full_benchmark_accuracy,
        "routed_accuracy": routed_accuracy,
        "accuracy_with_fallback": routed_accuracy,
        "compute_reduction": docling_compute_reduction,
        "docling_runs_full": full_docling_runs,
        "docling_runs_routed": routed_docling_runs,
        "extractor_runs_full": full_extractor_runs,
        "extractor_runs_routed": routed_extractor_runs,
        "extractor_run_reduction": total_compute_reduction,
        "fallback_rate": fallback_rate,
        "fallback_count": fallback_count,
        "anomaly_rate": anomaly_rate,
        "high_severity_anomalies": high_severity_anomaly_count,
        "fallback_due_to_anomaly_rate": fallback_due_to_anomaly_rate,
        "confidence_distribution": _confidence_distribution(selected_confidences),
        "documents_scored_full": full_accuracy_count,
        "documents_scored_routed": routed_accuracy_count,
        "documents": routed_documents,
    }


def main() -> int:
    args = _parse_args()
    benchmark_payload, benchmark_run = _run_full_benchmark(args)
    routing_eval = _routing_eval(benchmark_payload)

    out_json = Path(args.out_json).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "status": "SUCCESS",
        "generated_at_utc": utc_now(),
        "inputs": {
            "pdf_dir": str(Path(args.pdf_dir).expanduser().resolve()),
            "ground_truth": str(Path(args.ground_truth).expanduser().resolve()),
            "methods": [part.strip() for part in str(args.methods).split(",") if part.strip()],
            "docling_venv": str(Path(args.docling_venv).expanduser().resolve()),
        },
        "summary": {
            "documents_total": len(list(benchmark_payload.get("documents") or [])),
            "ground_truth_status": str(benchmark_payload.get("ground_truth_status") or "DATA_MISSING"),
            "per_method": dict((benchmark_payload.get("summary") or {}).get("per_method") or {}),
            "routing_evaluation": routing_eval,
        },
        "method_comparison": dict(benchmark_payload.get("method_comparison") or {}),
        "documents": list(benchmark_payload.get("documents") or []),
        "routing_documents": routing_eval.get("documents", []),
        "benchmark_run": benchmark_run,
    }
    out_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"status": "SUCCESS", "out_json": str(out_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
