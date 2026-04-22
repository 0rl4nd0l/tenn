#!/usr/bin/env python3
"""Run a bounded Docling page-batch timing experiment for one real-gold PDF."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.llamacpp_runtime import resolve_extraction_runtime_config
from app.services.method_isolated_extraction import run_method_isolated_extraction
from app.services.docling_extract import (
    DOCLING_PAGE_BATCH_PROFILE_BATCH_SIZE_ENV,
    DOCLING_PAGE_BATCH_PROFILE_PATH_ENV,
    DOCLING_PAGE_BATCH_PROFILE_TARGET_ENV,
)


DEFAULT_DOC_ID = "bhp_a_2025-06-30"
DEFAULT_DATASET_DIR = REPO_ROOT / "financial-engine_v2" / "data" / "extraction_gold_real"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports" / "extraction_perf" / "docling_page_batch"
EXPECTED_RUNTIME_ID = "http://127.0.0.1:8001"
EXPECTED_REQUESTED_METHOD = "docling"
EXPECTED_ACTUAL_METHOD = "docling_gpu"


@dataclass(frozen=True)
class GpuSnapshot:
    name: str
    memory_total_mb: int
    memory_used_mb: int
    memory_free_mb: int
    utilization_gpu_pct: int
    temperature_c: int
    processes: list[dict[str, str]]


class InMemoryObserver:
    """Minimal observer for high-resolution stage timing in one process."""

    def __init__(self) -> None:
        self.actual_method: str | None = None
        self.events: list[dict[str, Any]] = []

    def set_actual_method(self, actual_method: str | None) -> None:
        text = str(actual_method or "").strip()
        if text:
            self.actual_method = text

    def emit(
        self,
        stage: str,
        status: str,
        message: str,
        *,
        warning_code: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.events.append(
            {
                "stage": stage,
                "status": status,
                "message": message,
                "warning_code": warning_code,
                "error_code": error_code,
                "details": dict(details or {}),
                "ts": time.perf_counter(),
            }
        )
        return {}

    def stage_elapsed_seconds(self, stage: str) -> float | None:
        start_ts = None
        for event in self.events:
            if event["stage"] != stage:
                continue
            if event["status"] == "running":
                start_ts = float(event["ts"])
                continue
            if (
                start_ts is not None
                and event["status"] in {"succeeded", "failed", "blocked", "skipped"}
            ):
                return float(event["ts"]) - start_ts
        return None


def _run_cmd(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def read_gpu_snapshot() -> GpuSnapshot:
    gpu_line = _run_cmd(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
    ).splitlines()[0]
    parts = [part.strip() for part in gpu_line.split(",")]
    process_lines = _run_cmd(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader",
        ]
    ).splitlines()
    processes: list[dict[str, str]] = []
    for line in process_lines:
        text = line.strip()
        if not text:
            continue
        segs = [seg.strip() for seg in text.split(",")]
        if len(segs) < 3:
            continue
        processes.append(
            {"pid": segs[0], "process_name": segs[1], "used_memory": segs[2]}
        )
    return GpuSnapshot(
        name=parts[0],
        memory_total_mb=int(parts[1]),
        memory_used_mb=int(parts[2]),
        memory_free_mb=int(parts[3]),
        utilization_gpu_pct=int(parts[4]),
        temperature_c=int(parts[5]),
        processes=processes,
    )


def load_fixture(dataset_dir: Path, doc_id: str) -> dict[str, Any]:
    fixture_path = dataset_dir / f"{doc_id}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture_path}")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"fixture payload is not an object: {fixture_path}")
    return payload


def resolve_source_path(source_file: str) -> Path:
    source = Path(source_file)
    if source.is_absolute():
        if not source.exists():
            raise FileNotFoundError(f"source PDF not found: {source}")
        return source
    for base in (REPO_ROOT, REPO_ROOT / "financial-engine_v2"):
        candidate = base / source
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"source PDF not found in repo roots: {source_file}"
    )


def ticker_from_pdf_path(pdf_path: Path) -> str:
    parts = list(pdf_path.parts)
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return str(parts[idx + 1]).upper()
    return "UNKNOWN"


def clear_parser_cache(pdf_path: Path) -> list[str]:
    removed: list[str] = []
    for suffix in (".docling.json", ".pymupdf.json"):
        cache_path = Path(str(pdf_path) + suffix)
        if cache_path.exists():
            cache_path.unlink()
            removed.append(str(cache_path))
    return removed


def concentration_label(page_batches: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    valid = [
        batch
        for batch in page_batches
        if not str(batch.get("error") or "").strip()
    ]
    if not valid:
        return "unknown", {"reason": "no valid page-batch rows"}
    total = sum(float(batch["elapsed_seconds"]) for batch in valid)
    if total <= 0:
        return "unknown", {"reason": "zero total elapsed batch seconds"}
    top_n = max(1, math.ceil(len(valid) * 0.2))
    top = sorted(valid, key=lambda item: float(item["elapsed_seconds"]), reverse=True)[
        :top_n
    ]
    top_elapsed = sum(float(item["elapsed_seconds"]) for item in top)
    share = top_elapsed / total
    label = "concentrated" if share >= 0.5 else "evenly_distributed"
    return label, {
        "top_batch_count": top_n,
        "top_elapsed_seconds": round(top_elapsed, 6),
        "top_share_ratio": round(share, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bounded Docling page-batch timing experiment for one real-gold document.",
    )
    parser.add_argument("--document-id", default=DEFAULT_DOC_ID)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--min-free-vram-mb", type=int, default=3500)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    started_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{args.document_id}_{started_utc}.json"
    page_batch_profile_path = output_dir / f"{args.document_id}_{started_utc}.page_batches.json"

    gpu_before = read_gpu_snapshot()
    if gpu_before.memory_free_mb < int(args.min_free_vram_mb):
        blocked = {
            "status": "blocked",
            "reason": "insufficient_vram_headroom",
            "required_free_mb": int(args.min_free_vram_mb),
            "observed_free_mb": gpu_before.memory_free_mb,
            "gpu_before": gpu_before.__dict__,
        }
        report_path.write_text(json.dumps(blocked, indent=2), encoding="utf-8")
        print(f"BLOCKED: VRAM free {gpu_before.memory_free_mb} MiB < required {args.min_free_vram_mb} MiB")
        print(f"REPORT: {report_path}")
        return 2

    fixture = load_fixture(Path(args.dataset_dir), str(args.document_id))
    source_path = resolve_source_path(str(fixture["source_file"]))
    ticker = ticker_from_pdf_path(source_path)
    cache_removed = clear_parser_cache(source_path)

    os.environ.setdefault("LLM_API_KEY", "local-openai-key")
    os.environ[DOCLING_PAGE_BATCH_PROFILE_PATH_ENV] = str(page_batch_profile_path)
    os.environ[DOCLING_PAGE_BATCH_PROFILE_TARGET_ENV] = source_path.name
    os.environ[DOCLING_PAGE_BATCH_PROFILE_BATCH_SIZE_ENV] = str(int(args.batch_size))

    runtime_id, model_id = resolve_extraction_runtime_config()

    metadata = {
        "document_id": str(args.document_id),
        "ticker": ticker,
        "title": source_path.name,
    }
    observer = InMemoryObserver()

    total_started = time.perf_counter()
    result = run_method_isolated_extraction(
        str(source_path),
        metadata,
        None,
        requested_method=EXPECTED_REQUESTED_METHOD,
        strict_method=True,
        skip_narrative=True,
        observer=observer,
    )
    total_doc_seconds = time.perf_counter() - total_started

    if not page_batch_profile_path.exists():
        raise RuntimeError(
            f"expected page-batch profile was not produced: {page_batch_profile_path}"
        )
    page_batch_profile = json.loads(
        page_batch_profile_path.read_text(encoding="utf-8")
    )

    payload = result.payload if isinstance(result.payload, dict) else {}
    method_provenance = payload.get("_method_provenance", {})
    if not isinstance(method_provenance, dict):
        method_provenance = {}

    parser_elapsed = observer.stage_elapsed_seconds("parser")
    page_batches = page_batch_profile.get("page_batches", [])
    if not isinstance(page_batches, list):
        page_batches = []
    distribution_label, distribution_stats = concentration_label(page_batches)

    invariants = {
        "requested_method": method_provenance.get("requested_method"),
        "strict_method": method_provenance.get("strict_method"),
        "actual_method": method_provenance.get("actual_method"),
        "runtime_id": method_provenance.get("runtime_id"),
        "fallback_used": method_provenance.get("fallback_used"),
    }
    expected_invariants = {
        "requested_method": EXPECTED_REQUESTED_METHOD,
        "strict_method": True,
        "actual_method": EXPECTED_ACTUAL_METHOD,
        "runtime_id": EXPECTED_RUNTIME_ID,
        "fallback_used": False,
    }
    invariant_ok = all(invariants.get(key) == value for key, value in expected_invariants.items())

    gpu_after = read_gpu_snapshot()
    report = {
        "status": "ok" if invariant_ok else "failed_invariants",
        "document_id": str(args.document_id),
        "source_pdf": str(source_path),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_config": {
            "resolved_runtime_id": runtime_id,
            "resolved_model_id": model_id,
        },
        "timing": {
            "total_doc_seconds": round(total_doc_seconds, 6),
            "parser_seconds": round(parser_elapsed, 6)
            if parser_elapsed is not None
            else None,
            "docling_convert_seconds": page_batch_profile.get("docling_convert_seconds"),
            "table_loop_seconds": page_batch_profile.get("table_loop_seconds"),
            "section_loop_seconds": page_batch_profile.get("section_loop_seconds"),
        },
        "page_batch_profile": {
            "batch_size": page_batch_profile.get("batch_size"),
            "page_count": page_batch_profile.get("page_count"),
            "page_batch_error": page_batch_profile.get("page_batch_error"),
            "page_batches": page_batches,
            "distribution": distribution_label,
            "distribution_stats": distribution_stats,
        },
        "method_provenance": method_provenance,
        "expected_invariants": expected_invariants,
        "observed_invariants": invariants,
        "invariants_ok": invariant_ok,
        "result_status": getattr(result, "status", None),
        "result_error": getattr(result, "error", None),
        "cache_removed": cache_removed,
        "gpu_before": gpu_before.__dict__,
        "gpu_after": gpu_after.__dict__,
        "observer_events": observer.events,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"REPORT: {report_path}")
    print(f"PAGE_BATCH_PROFILE: {page_batch_profile_path}")
    print(f"INVARIANTS_OK: {invariant_ok}")
    print(f"DISTRIBUTION: {distribution_label}")
    return 0 if invariant_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
