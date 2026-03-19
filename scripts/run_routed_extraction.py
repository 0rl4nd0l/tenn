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
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "routed_extraction_report.json"
DEFAULT_RUN_ROOT = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "routed_runs"
DEFAULT_GROUND_TRUTH = REPO_ROOT / "data" / "ground_truth"
DEFAULT_DOCLING_VENV = REPO_ROOT / ".venv_docling"
PDFTOTEXT_EXTRACTOR = "financial_metrics_pdftotext"
DOCLING_EXTRACTOR = "financial_metrics_docling"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.evaluation.confidence import CONFIDENCE_THRESHOLD, MIN_COVERAGE, compute_confidence, fallback_reasons, metric_coverage
from services.evaluation.anomaly import detect_anomalies
from services.extraction.router import select_extractor_with_reason


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _doc_id_from_path(pdf_path: Path) -> str:
    stem = pdf_path.stem.lower()
    if len(stem) >= 36 and stem[-36:].count("-") == 4:
        return stem[-36:]
    return stem


def _iter_pdfs(pdf_dir: Path) -> list[Path]:
    return sorted(path for path in pdf_dir.rglob("*.pdf") if path.is_file())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run routed extraction with pdftotext probe and conditional Docling execution.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", action="append", help="PDF path to process. May be repeated.")
    input_group.add_argument("--pdf-dir", help="Directory containing PDFs.")
    parser.add_argument(
        "--ground-truth",
        default=str(DEFAULT_GROUND_TRUTH),
        help="Ground-truth path passed through to benchmark runs.",
    )
    parser.add_argument(
        "--docling-venv",
        default=str(DEFAULT_DOCLING_VENV),
        help="Docling venv path.",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_OUT_JSON),
        help="Routed extraction output path.",
    )
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help="Run root for intermediate benchmark artifacts.",
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


def _run_benchmark_for_pdf(
    *,
    pdf: Path,
    methods: str,
    ground_truth: Path,
    docling_venv: Path,
    out_json: Path,
    run_root: Path,
    subprocess_timeout_sec: float,
    create_docling_venv: bool,
    docling_cpu: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "benchmark_pdf_extraction.py"),
        "--pdf",
        str(pdf),
        "--methods",
        methods,
        "--ground-truth",
        str(ground_truth),
        "--docling-venv",
        str(docling_venv),
        "--subprocess-timeout-sec",
        str(subprocess_timeout_sec),
        "--out-json",
        str(out_json),
        "--run-root",
        str(run_root),
    ]
    if create_docling_venv:
        command.append("--create-docling-venv")
    if docling_cpu:
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
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or f"benchmark_failed_for_{pdf}")
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    return payload, {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _document_diagnostics(method_results: Mapping[str, Any]) -> dict[str, Any]:
    for method_name in (PDFTOTEXT_EXTRACTOR, DOCLING_EXTRACTOR):
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


def main() -> int:
    args = _parse_args()
    ground_truth = Path(args.ground_truth).expanduser().resolve()
    docling_venv = Path(args.docling_venv).expanduser().resolve()
    run_root = Path(args.run_root).expanduser().resolve()
    out_json = Path(args.out_json).expanduser().resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if args.pdf:
        pdfs = [Path(value).expanduser().resolve() for value in args.pdf]
    else:
        pdfs = _iter_pdfs(Path(args.pdf_dir).expanduser().resolve())
    if not pdfs:
        raise SystemExit("No PDFs found for routed extraction.")
    for pdf in pdfs:
        if not pdf.exists() or not pdf.is_file():
            raise SystemExit(f"Invalid PDF path: {pdf}")

    documents: list[dict[str, Any]] = []
    probe_runs = 0
    docling_runs = 0
    fallback_count = 0
    selected_confidences: list[float] = []
    selected_accuracies: list[float] = []

    for pdf in pdfs:
        doc_id = _doc_id_from_path(pdf)
        doc_run_root = run_root / doc_id
        probe_json = doc_run_root / "probe_benchmark.json"
        probe_run_root = doc_run_root / "probe_runs"

        probe_payload, probe_meta = _run_benchmark_for_pdf(
            pdf=pdf,
            methods=PDFTOTEXT_EXTRACTOR,
            ground_truth=ground_truth,
            docling_venv=docling_venv,
            out_json=probe_json,
            run_root=probe_run_root,
            subprocess_timeout_sec=float(args.subprocess_timeout_sec),
            create_docling_venv=bool(args.create_docling_venv),
            docling_cpu=bool(args.docling_cpu),
        )
        probe_runs += 1

        probe_document = dict((probe_payload.get("documents") or [{}])[0] or {})
        probe_methods = dict(probe_document.get("methods") or {})
        probe_method_payload = dict(probe_methods.get(PDFTOTEXT_EXTRACTOR) or {})
        diagnostics = _document_diagnostics(probe_methods)
        routing_hint = select_extractor_with_reason(diagnostics, probe_methods)
        probe_confidence = compute_confidence(probe_method_payload)
        probe_anomaly = detect_anomalies(probe_method_payload)
        probe_coverage = metric_coverage(probe_method_payload)
        reasons = fallback_reasons(
            probe_method_payload,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            min_coverage=MIN_COVERAGE,
        )
        fallback_triggered = bool(reasons)
        fallback_reason = ",".join(reasons)
        selected_method = PDFTOTEXT_EXTRACTOR
        selected_payload: dict[str, Any] = dict(probe_method_payload)
        selected_confidence = probe_confidence
        selected_anomaly = probe_anomaly
        selected_meta: dict[str, Any] = {
            "selected_from_probe": True,
            "probe_run": probe_meta,
            "routing_hint": routing_hint,
            "probe_confidence": probe_confidence,
            "probe_anomaly": probe_anomaly,
            "probe_coverage": probe_coverage,
        }
        docling_confidence: float | None = None
        docling_anomaly: dict[str, Any] | None = None

        if fallback_triggered:
            fallback_count += 1
            docling_runs += 1
            selected_json = doc_run_root / "selected_benchmark.json"
            selected_run_root = doc_run_root / "selected_runs"
            selected_benchmark_payload, selected_benchmark_meta = _run_benchmark_for_pdf(
                pdf=pdf,
                methods=DOCLING_EXTRACTOR,
                ground_truth=ground_truth,
                docling_venv=docling_venv,
                out_json=selected_json,
                run_root=selected_run_root,
                subprocess_timeout_sec=float(args.subprocess_timeout_sec),
                create_docling_venv=bool(args.create_docling_venv),
                docling_cpu=bool(args.docling_cpu),
            )
            selected_document = dict((selected_benchmark_payload.get("documents") or [{}])[0] or {})
            selected_methods = dict(selected_document.get("methods") or {})
            docling_payload = dict(selected_methods.get(DOCLING_EXTRACTOR) or {})
            docling_confidence = compute_confidence(docling_payload)
            docling_anomaly = detect_anomalies(docling_payload)
            if docling_confidence > selected_confidence:
                selected_method = DOCLING_EXTRACTOR
                selected_payload = docling_payload
                selected_confidence = docling_confidence
                selected_anomaly = docling_anomaly
            selected_meta = {
                "selected_from_probe": selected_method == PDFTOTEXT_EXTRACTOR,
                "probe_run": probe_meta,
                "selected_run": selected_benchmark_meta,
                "routing_hint": routing_hint,
                "probe_confidence": probe_confidence,
                "docling_confidence": docling_confidence,
                "probe_anomaly": probe_anomaly,
                "docling_anomaly": docling_anomaly,
                "probe_coverage": probe_coverage,
            }

        selected_score = dict(selected_payload.get("score") or {})
        selected_accuracy = None
        if str(selected_score.get("status") or "") == "SUCCESS":
            aggregate = selected_score.get("aggregate")
            if isinstance(aggregate, Mapping):
                selected_accuracy = float(aggregate.get("accuracy") or 0.0)
                selected_accuracies.append(selected_accuracy)
        selected_confidences.append(float(selected_confidence))

        documents.append(
            {
                "pdf": str(pdf),
                "doc_id": doc_id,
                "selected_method": selected_method,
                "routing_reason": str((routing_hint or {}).get("reason") or ""),
                "classifier": (routing_hint or {}).get("classifier"),
                "confidence": round(float(selected_confidence), 6),
                "fallback_triggered": fallback_triggered,
                "fallback_reason": fallback_reason,
                "confidence_threshold": CONFIDENCE_THRESHOLD,
                "min_coverage": MIN_COVERAGE,
                "anomaly": selected_anomaly,
                "metrics": dict(selected_payload.get("canonical_metrics") or {}),
                "score": selected_score,
                "selected_accuracy": selected_accuracy,
                "status": str(selected_payload.get("status") or "failed"),
                "runtime_seconds": selected_payload.get("runtime_seconds"),
                "routing_metadata": selected_meta,
            }
        )

    output = {
        "status": "SUCCESS",
        "generated_at_utc": utc_now(),
        "inputs": {
            "pdf_count": len(pdfs),
            "pdfs": [str(pdf) for pdf in pdfs],
            "ground_truth": str(ground_truth),
            "docling_venv": str(docling_venv),
        },
        "summary": {
            "documents_total": len(documents),
            "probe_runs": probe_runs,
            "docling_runs": docling_runs,
            "docling_run_rate": round(float(docling_runs) / float(max(1, len(documents))), 6),
            "fallback_count": fallback_count,
            "fallback_rate": round(float(fallback_count) / float(max(1, len(documents))), 6),
            "confidence_distribution": _confidence_distribution(selected_confidences),
            "accuracy_with_fallback": round(sum(selected_accuracies) / float(len(selected_accuracies)), 6) if selected_accuracies else 0.0,
        },
        "documents": documents,
    }
    out_json.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"status": "SUCCESS", "out_json": str(out_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
