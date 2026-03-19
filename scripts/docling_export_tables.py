#!/usr/bin/env python3
"""
Quick Docling PoC: extract tables from a financial PDF and export them.

Usage (from repo root):

  # Basic: inspect tables from a single PDF
  python3 scripts/docling_export_tables.py --pdf financial-engine_v2/data/asx/docs/10X/financial_performance/2025-12-09_financial-report-for-period-ended-30-june-2025_3f517fe5-7b78-46b5-b861-475f72e68bd1.pdf

  # Save CSVs under reports/docling_tables/
  python3 scripts/docling_export_tables.py --pdf /path/to/report.pdf --out-dir reports/docling_tables

This does not change the canonical extraction pipeline; it is a standalone helper
to inspect Docling's table detection and structure on the same PDFs.

On machines with older GPUs (e.g. Tesla M40, sm_52), PyTorch 2.10+ has no CUDA
kernels for that device. Use --cpu to force CPU and avoid "no kernel image"
errors (slower but works).
"""
import os
import sys

# Force CPU before any torch/docling import when --cpu is passed (for Tesla M40 / sm_52).
if "--cpu" in sys.argv:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

import argparse
import warnings

# Suppress noisy warnings from Docling/pydantic/requests (protected namespace, urllib3)
warnings.filterwarnings("ignore", message=".*protected namespace.*model_.*", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*urllib3.*chardet.*", category=Warning)

import logging
from pathlib import Path
from typing import Optional

try:
    from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
except Exception as _docling_import_error:  # pragma: no cover - optional dependency
    DocumentConverter = None  # type: ignore[assignment]
else:
    _docling_import_error = None  # type: ignore[assignment]

try:
    import pandas as pd  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    pd = None


LOG = logging.getLogger("docling_export_tables")
ROOT = Path(__file__).resolve().parents[1]


def _resolve_pdf(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def run(pdf_path: Path, out_dir: Optional[Path] = None) -> int:
    if DocumentConverter is None:
        print(
            "Missing dependency: docling. "
            "Install it in your environment, for example:\n"
            "  pip install docling\n"
            "or install backend/worker requirements for this repo.",
        )
        if _docling_import_error is not None:
            LOG.debug("Original import error: %s", _docling_import_error)
        return 2

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 2

    converter = DocumentConverter()
    LOG.info("Converting %s with Docling...", pdf_path)
    conv_res = converter.convert(pdf_path)

    doc = conv_res.document
    tables = list(doc.tables)
    if not tables:
        print(f"No tables detected by Docling in {pdf_path}")
        return 0

    print(f"Docling detected {len(tables)} tables in {pdf_path}")

    out_dir_resolved: Optional[Path] = None
    if out_dir is not None:
        out_dir_resolved = out_dir.resolve()
        out_dir_resolved.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem

    for idx, table in enumerate(tables, start=1):
        print(f"\n=== Table {idx} ===")
        try:
            md = table.export_to_markdown(doc=doc)
            print(md)
        except Exception as exc:
            LOG.warning("Failed to export table %d to Markdown: %s", idx, exc)

        if out_dir_resolved is not None and pd is not None:
            try:
                df = table.export_to_dataframe(doc=doc)
            except Exception as exc:  # pragma: no cover - defensive
                LOG.warning("Failed to export table %d to DataFrame: %s", idx, exc)
            else:
                csv_path = out_dir_resolved / f"{stem}-table-{idx}.csv"
                df.to_csv(csv_path, index=False)
                LOG.info("Wrote CSV for table %d to %s (shape=%s)", idx, csv_path, df.shape)

    if out_dir_resolved is not None and pd is None:
        LOG.warning(
            "pandas is not installed; CSV export was skipped. "
            "Install pandas if you want CSV outputs from Docling tables."
        )

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run Docling on a financial PDF and export detected tables for inspection.",
    )
    ap.add_argument(
        "--pdf",
        required=True,
        help="Path to a single PDF (absolute or relative to repo root).",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="Optional output directory for CSV exports (uses pandas if available).",
    )
    ap.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level for Docling run.",
    )
    ap.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU (avoids CUDA errors on older GPUs e.g. Tesla M40 sm_52). Slower but required if PyTorch has no kernel for your GPU.",
    )
    args = ap.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))

    pdf_path = _resolve_pdf(args.pdf)
    out_dir = Path(args.out_dir) if args.out_dir else None
    return run(pdf_path, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())

