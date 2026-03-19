#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "pdf_extraction_benchmark" / "orchestrator" / "full_pipeline_report.json"
DEFAULT_GROUND_TRUTH = REPO_ROOT / "data" / "ground_truth"
DEFAULT_DOCLING_VENV = REPO_ROOT / ".venv_docling"
DEFAULT_METHODS = "financial_metrics_pdftotext,financial_metrics_docling"

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.orchestrator.pipeline_orchestrator import PipelineOrchestrator


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _default_pdf_dirs() -> str:
    base = REPO_ROOT / "financial-engine_v2" / "data" / "asx" / "docs"
    candidates = [
        base / "SEG" / "financial_performance",
        base / "SMS" / "investor_communications",
        base / "GCI" / "other",
    ]
    return ",".join(str(path) for path in candidates if path.exists())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full financial PDF orchestration pipeline.")
    parser.add_argument(
        "--pdf-dirs",
        default=_default_pdf_dirs(),
        help="Comma-separated PDF directories, e.g. dir1,dir2,dir3",
    )
    parser.add_argument(
        "--ground-truth",
        default=str(DEFAULT_GROUND_TRUTH),
        help="Ground truth path.",
    )
    parser.add_argument(
        "--docling-venv",
        default=str(DEFAULT_DOCLING_VENV),
        help="Docling venv path.",
    )
    parser.add_argument(
        "--mode",
        default="batch",
        help="Mode: batch|single|routed|evaluation_only",
    )
    parser.add_argument(
        "--methods",
        default=DEFAULT_METHODS,
        help="Extraction methods for full benchmark.",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_OUT_JSON),
        help="Output report JSON path.",
    )
    parser.add_argument(
        "--subprocess-timeout-sec",
        type=float,
        default=20.0,
        help="Subprocess timeout for extractor calls.",
    )
    parser.add_argument(
        "--min-documents",
        type=int,
        default=10,
        help="Minimum documents required in batch mode.",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=12,
        help="Maximum sampled documents in batch mode.",
    )
    parser.add_argument(
        "--enable-fallback",
        action="store_true",
        default=True,
        help="Enable fallback control.",
    )
    parser.add_argument(
        "--enable-anomaly-detection",
        action="store_true",
        default=True,
        help="Enable anomaly detection integration.",
    )
    parser.add_argument(
        "--docling-cpu",
        action="store_true",
        help="Force docling CPU mode.",
    )
    parser.add_argument(
        "--create-docling-venv",
        action="store_true",
        help="Create docling venv if missing.",
    )
    parser.add_argument(
        "--full-benchmark-json",
        default="",
        help="Evaluation-only mode input: full benchmark JSON path.",
    )
    parser.add_argument(
        "--routed-json",
        default="",
        help="Evaluation-only mode input: routed extraction JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    pdf_dirs = _split_csv(args.pdf_dirs)
    if not pdf_dirs and str(args.mode).strip().lower() != "evaluation_only":
        raise SystemExit("missing_pdf_dirs")

    config: dict[str, Any] = {
        "mode": args.mode,
        "pdf_dirs": pdf_dirs,
        "ground_truth": str(Path(args.ground_truth).expanduser().resolve()),
        "docling_venv": str(Path(args.docling_venv).expanduser().resolve()),
        "enable_fallback": bool(args.enable_fallback),
        "enable_anomaly_detection": bool(args.enable_anomaly_detection),
        "subprocess_timeout_sec": float(args.subprocess_timeout_sec),
        "methods": str(args.methods),
        "min_documents": int(args.min_documents),
        "max_documents": int(args.max_documents),
        "docling_cpu": bool(args.docling_cpu),
        "create_docling_venv": bool(args.create_docling_venv),
    }
    if str(args.full_benchmark_json).strip():
        config["full_benchmark_json"] = str(Path(args.full_benchmark_json).expanduser().resolve())
    if str(args.routed_json).strip():
        config["routed_json"] = str(Path(args.routed_json).expanduser().resolve())

    orchestrator = PipelineOrchestrator(repo_root=REPO_ROOT)
    report = orchestrator.run(config)

    out_json = Path(args.out_json).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "out_json": str(out_json),
                "documents_total": int(report.get("documents_total") or 0),
                "mode": str(report.get("mode") or ""),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
