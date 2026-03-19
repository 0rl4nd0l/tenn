#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.runtime_python import resolve_python


TAIL_LINES = 20


def _output_root() -> Path:
    return ROOT / "reports" / "parallel_extraction"


def collect_pdfs(pdf_dir: Path) -> List[Path]:
    root = Path(pdf_dir).resolve()
    return sorted(
        (pdf.resolve() for pdf in root.rglob("*") if pdf.is_file() and pdf.suffix.lower() == ".pdf"),
        key=lambda pdf: str(pdf),
    )


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-.")
    return slug or "document"


def _output_dir_for_pdf(pdf_path: Path) -> Path:
    pdf = Path(pdf_path).resolve()
    digest = hashlib.sha1(str(pdf).encode("utf-8")).hexdigest()[:12]
    slug = f"{_safe_slug(pdf.stem)}_{digest}"
    try:
        relative_parent = pdf.relative_to(ROOT).parent
        return _output_root() / relative_parent / slug
    except ValueError:
        return _output_root() / "external" / slug


def _output_paths_for_pdf(pdf_path: Path) -> Dict[str, Path]:
    output_dir = _output_dir_for_pdf(pdf_path)
    return {
        "output_dir": output_dir,
        "out_csv": output_dir / "canonical.csv",
        "out_json": output_dir / "canonical.json",
        "out_all_variants_json": output_dir / "all_variants.json",
        "out_primary_csv": output_dir / "primary.csv",
        "out_primary_json": output_dir / "primary.json",
        "out_all_datapoints_json": output_dir / "all_datapoints.json",
        "out_coverage_enhanced_json": output_dir / "coverage_enhanced.json",
        "out_coverage_backfill_audit_json": output_dir / "coverage_backfill_audit.json",
        "out_context_csv": output_dir / "context.csv",
        "out_context_json": output_dir / "context.json",
        "out_rejected_json": output_dir / "rejected.json",
        "out_blocks_json": output_dir / "blocks.json",
        "out_document_diagnostics_json": output_dir / "document_diagnostics.json",
        "out_high_csv": output_dir / "high.csv",
        "out_high_json": output_dir / "high.json",
        "out_sqlite": output_dir / "financial_metrics.sqlite",
    }


def _tail_lines(text: str, limit: int = TAIL_LINES) -> List[str]:
    if not text:
        return []
    return str(text).splitlines()[-limit:]


def _build_extract_command(pdf_path: Path, output_paths: Dict[str, Path]) -> List[str]:
    return [
        resolve_python(),
        str(ROOT / "scripts" / "extract_financial_metrics.py"),
        "--pdf",
        str(Path(pdf_path).resolve()),
        "--out-csv",
        str(output_paths["out_csv"]),
        "--out-json",
        str(output_paths["out_json"]),
        "--out-all-variants-json",
        str(output_paths["out_all_variants_json"]),
        "--out-primary-csv",
        str(output_paths["out_primary_csv"]),
        "--out-primary-json",
        str(output_paths["out_primary_json"]),
        "--out-all-datapoints-json",
        str(output_paths["out_all_datapoints_json"]),
        "--out-coverage-enhanced-json",
        str(output_paths["out_coverage_enhanced_json"]),
        "--out-coverage-backfill-audit-json",
        str(output_paths["out_coverage_backfill_audit_json"]),
        "--out-context-csv",
        str(output_paths["out_context_csv"]),
        "--out-context-json",
        str(output_paths["out_context_json"]),
        "--out-rejected-json",
        str(output_paths["out_rejected_json"]),
        "--out-blocks-json",
        str(output_paths["out_blocks_json"]),
        "--out-document-diagnostics-json",
        str(output_paths["out_document_diagnostics_json"]),
        "--out-high-csv",
        str(output_paths["out_high_csv"]),
        "--out-high-json",
        str(output_paths["out_high_json"]),
        "--out-sqlite",
        str(output_paths["out_sqlite"]),
    ]


def run_pdf_extraction(pdf_path: Path) -> Dict[str, object]:
    pdf = Path(pdf_path).resolve()
    output_paths = _output_paths_for_pdf(pdf)
    output_dir = output_paths["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = _build_extract_command(pdf, output_paths)

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "pdf_path": str(pdf),
            "output_dir": str(output_dir),
            "returncode": -1,
            "stdout_tail": [],
            "stderr_tail": [str(exc)],
        }

    return {
        "pdf_path": str(pdf),
        "output_dir": str(output_dir),
        "returncode": int(completed.returncode),
        "stdout_tail": _tail_lines(completed.stdout),
        "stderr_tail": _tail_lines(completed.stderr),
    }


def run_parallel_extraction(
    pdfs: Sequence[Path],
    max_workers: int = 4,
    worker_fn: Optional[Callable[[Path], Dict[str, object]]] = None,
    executor_cls: Optional[type] = None,
    printer: Optional[Callable[[str], None]] = None,
) -> Dict[str, object]:
    worker = worker_fn or run_pdf_extraction
    executor_type = executor_cls or concurrent.futures.ProcessPoolExecutor
    emit = printer or print
    pdf_list = [Path(pdf).resolve() for pdf in pdfs]
    total = len(pdf_list)
    worker_count = max(1, min(int(max_workers), total)) if total else max(1, int(max_workers))
    results: List[Dict[str, object]] = []
    failures: List[Dict[str, object]] = []
    summary: Dict[str, object] = {
        "total": total,
        "succeeded": 0,
        "failed": 0,
        "max_workers": worker_count,
        "results": results,
        "failures": failures,
    }
    if not pdf_list:
        return summary

    emit(f"[queue] {total} PDF(s) enqueued with max_workers={worker_count}")
    with executor_type(max_workers=worker_count) as executor:
        future_to_pdf = {executor.submit(worker, pdf): pdf for pdf in pdf_list}
        processed = 0
        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf = future_to_pdf[future]
            processed += 1
            try:
                result = future.result()
            except Exception as exc:
                failure = {
                    "pdf_path": str(pdf),
                    "output_dir": "",
                    "returncode": -1,
                    "stdout_tail": [],
                    "stderr_tail": [str(exc)],
                }
                summary["failed"] = int(summary["failed"]) + 1
                failures.append(failure)
                emit(f"[worker] failed {pdf.name}: {exc}")
            else:
                results.append(result)
                if int(result.get("returncode", -1)) == 0:
                    summary["succeeded"] = int(summary["succeeded"]) + 1
                else:
                    summary["failed"] = int(summary["failed"]) + 1
                    failures.append(result)
                    stderr_tail = list(result.get("stderr_tail", []) or [])
                    detail = f": {stderr_tail[-1]}" if stderr_tail else ""
                    emit(f"[worker] failed {pdf.name}{detail}")
            emit(f"[progress] {processed} / {total} PDFs completed")

    results.sort(key=lambda row: str(row.get("pdf_path", "")))
    failures.sort(key=lambda row: str(row.get("pdf_path", "")))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Run extract_financial_metrics.py across PDFs in parallel")
    ap.add_argument("--pdf-dir", required=True, help="Directory containing PDFs or a ticker folder to scan recursively")
    ap.add_argument("--max-workers", type=int, default=4, help="Maximum concurrent extraction workers (default: 4)")
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir).resolve()
    if not pdf_dir.exists():
        print(f"PDF directory not found: {pdf_dir}", file=sys.stderr)
        return 2
    if not pdf_dir.is_dir():
        print(f"PDF directory is not a directory: {pdf_dir}", file=sys.stderr)
        return 2
    if int(args.max_workers) < 1:
        print("--max-workers must be >= 1", file=sys.stderr)
        return 2

    pdfs = collect_pdfs(pdf_dir)
    if not pdfs:
        print(f"No PDF files found in: {pdf_dir}", file=sys.stderr)
        return 2

    summary = run_parallel_extraction(pdfs, max_workers=int(args.max_workers))
    print(
        "[summary] "
        f"processed={summary['total']} "
        f"succeeded={summary['succeeded']} "
        f"failed={summary['failed']}"
    )
    return 0 if int(summary["failed"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
