#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "ground_truth" / "ground_truth_draft.json"
DEFAULT_RUN_ROOT = REPO_ROOT / "reports" / "pdf_ground_truth_generation" / "runs"
DOCLING_VENV_DEFAULT = REPO_ROOT / ".venv_docling"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.evaluation.normalizer import canonical_metric_keys, metric_coverage_rate, rows_to_canonical_metrics


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_benchmark_module():
    module_path = REPO_ROOT / "scripts" / "benchmark_pdf_extraction.py"
    spec = importlib.util.spec_from_file_location("benchmark_pdf_extraction_module", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("unable_to_load_benchmark_pdf_extraction")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _iter_pdfs(pdf_dir: Path) -> list[Path]:
    return sorted(path for path in pdf_dir.rglob("*.pdf") if path.is_file())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate draft ground truth from best-available extraction method.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", action="append", help="PDF path to process. May be repeated.")
    input_group.add_argument("--pdf-dir", help="Directory containing PDFs.")
    parser.add_argument(
        "--methods",
        default="",
        help="Comma-separated method names. Defaults to benchmarkable structured extractors.",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON for generated ground-truth drafts.",
    )
    parser.add_argument(
        "--run-root",
        default=str(DEFAULT_RUN_ROOT),
        help="Directory for per-method intermediate artifacts.",
    )
    parser.add_argument(
        "--docling-venv",
        default=str(DOCLING_VENV_DEFAULT),
        help="Docling venv path for Docling-backed methods.",
    )
    parser.add_argument(
        "--create-docling-venv",
        action="store_true",
        help="Create the Docling venv if missing.",
    )
    parser.add_argument(
        "--docling-cpu",
        action="store_true",
        help="Force CPU mode for Docling extraction.",
    )
    parser.add_argument(
        "--subprocess-timeout-sec",
        type=float,
        default=0.0,
        help="Optional timeout for subprocess-backed methods.",
    )
    return parser.parse_args()


def _default_method_selection(method_map: dict[str, Any]) -> dict[str, Any]:
    allowed_categories = {
        "financial_metrics_extractor",
        "llm_extractor",
        "ocr_candidate_extractor",
    }
    return {
        name: spec
        for name, spec in method_map.items()
        if bool(getattr(spec, "benchmarkable", False)) and str(getattr(spec, "category", "")) in allowed_categories
    }


def _run_candidate_method(
    spec: Any,
    method_name: str,
    pdf_path: Path,
    run_root: Path,
    *,
    docling_venv: str,
    create_docling_venv: bool,
    docling_cpu: bool,
    subprocess_timeout_sec: float | None,
) -> dict[str, Any]:
    method_run_dir = run_root / method_name
    method_run_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        payload = spec.runner(
            pdf_path,
            run_dir=method_run_dir,
            docling_venv_path=docling_venv,
            docling_create_venv=create_docling_venv,
            docling_cpu=docling_cpu,
            subprocess_timeout_sec=subprocess_timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        payload = {
            "status": "failed",
            "error": f"timeout_after_{exc.timeout}_seconds",
            "normalized_metrics": [],
        }
    except Exception as exc:
        payload = {
            "status": "failed",
            "error": str(exc),
            "normalized_metrics": [],
        }

    runtime_seconds = round(time.perf_counter() - started, 6)
    normalized_rows = list(payload.get("normalized_metrics") or [])
    canonical_metrics = rows_to_canonical_metrics(normalized_rows)
    coverage = metric_coverage_rate(canonical_metrics)
    return {
        "name": method_name,
        "status": str(payload.get("status") or "failed"),
        "runtime_seconds": runtime_seconds,
        "coverage_count": len(canonical_metrics),
        "coverage_rate": round(coverage, 6),
        "metrics": canonical_metrics,
        "error": str(payload.get("error") or ""),
    }


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, float, float]:
    status_ok = 1 if str(candidate.get("status")).lower() in {"ok", "success"} else 0
    coverage_count = int(candidate.get("coverage_count") or 0)
    coverage_rate = float(candidate.get("coverage_rate") or 0.0)
    runtime_seconds = float(candidate.get("runtime_seconds") or 0.0)
    return (
        status_ok,
        coverage_count,
        coverage_rate,
        -runtime_seconds,
    )


def main() -> int:
    args = _parse_args()
    benchmark_module = _load_benchmark_module()
    method_map = dict(benchmark_module._method_map())

    if str(args.methods).strip():
        requested = {name.strip() for name in str(args.methods).split(",") if name.strip()}
        selected_methods = {name: spec for name, spec in method_map.items() if name in requested}
    else:
        selected_methods = _default_method_selection(method_map)
    if not selected_methods:
        raise SystemExit("No methods selected for ground-truth generation.")

    if args.pdf:
        pdfs = [Path(value).expanduser().resolve() for value in args.pdf]
    else:
        pdfs = _iter_pdfs(Path(args.pdf_dir).expanduser().resolve())
    if not pdfs:
        raise SystemExit("No PDFs found.")
    for pdf in pdfs:
        if not pdf.exists() or not pdf.is_file():
            raise SystemExit(f"Invalid PDF path: {pdf}")

    out_json = Path(args.out_json).expanduser().resolve()
    run_root = Path(args.run_root).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)

    documents: list[dict[str, Any]] = []
    timeout_value = float(args.subprocess_timeout_sec or 0.0) or None

    for pdf in pdfs:
        doc_id = str(benchmark_module._doc_id_from_path(pdf))
        doc_run_root = run_root / doc_id
        doc_run_root.mkdir(parents=True, exist_ok=True)

        candidates: list[dict[str, Any]] = []
        for method_name, spec in selected_methods.items():
            candidates.append(
                _run_candidate_method(
                    spec,
                    method_name,
                    pdf,
                    doc_run_root,
                    docling_venv=str(args.docling_venv),
                    create_docling_venv=bool(args.create_docling_venv),
                    docling_cpu=bool(args.docling_cpu),
                    subprocess_timeout_sec=timeout_value,
                )
            )

        best = max(candidates, key=_candidate_sort_key)
        documents.append(
            {
                "pdf": str(pdf),
                "doc_id": doc_id,
                "status": "REQUIRES_REVIEW",
                "selected_method": best["name"],
                "metrics": dict(best.get("metrics") or {}),
                "candidate_methods": [
                    {
                        "name": candidate["name"],
                        "status": candidate["status"],
                        "coverage_count": candidate["coverage_count"],
                        "coverage_rate": candidate["coverage_rate"],
                        "runtime_seconds": candidate["runtime_seconds"],
                        "error": candidate["error"],
                    }
                    for candidate in sorted(candidates, key=_candidate_sort_key, reverse=True)
                ],
            }
        )

    report = {
        "status": "REQUIRES_REVIEW",
        "generated_at_utc": utc_now(),
        "inputs": {
            "pdf_count": len(pdfs),
            "pdfs": [str(pdf) for pdf in pdfs],
            "methods": sorted(selected_methods.keys()),
            "canonical_metric_keys": list(canonical_metric_keys()),
        },
        "documents": documents,
    }
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": "REQUIRES_REVIEW", "out_json": str(out_json), "documents": len(documents)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
