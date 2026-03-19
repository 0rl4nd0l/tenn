#!/usr/bin/env python3
"""
Export a PDF into plain text using Docling (docling venv only).

This script is intended to be executed via a Docling subprocess runner
(see `services/extraction/docling_runner.py`), so that Docling is not imported
into the main extraction process.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Export document text via Docling")
    ap.add_argument("--pdf", required=True, help="Path to a single PDF (absolute recommended).")
    ap.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU mode (CUDA disabled).",
    )
    ap.add_argument(
        "--docling-ocr",
        action="store_true",
        help="Enable Docling OCR (for scanned/image-only PDFs).",
    )
    ap.add_argument("--log-level", default="ERROR", help="Docling/RapidOCR logging verbosity.")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()

    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    # Import Docling only inside the subprocess environment.
    try:
        from docling.datamodel.base_models import InputFormat  # type: ignore[import-not-found]
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore[import-not-found]
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
        from docling.datamodel.pipeline_options import PdfFormatOption  # type: ignore[import-not-found]
    except Exception as e:  # pragma: no cover
        print(f"docling import failed: {e}", file=sys.stderr)
        return 1

    try:
        pipeline_options = PdfPipelineOptions(do_ocr=bool(args.docling_ocr), do_table_structure=False)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
        conv_res = converter.convert(str(pdf_path))
        doc = conv_res.document

        # Use plain-text export for evidence matching (label/value proximity).
        text = doc.export_to_text()
        if not isinstance(text, str):
            print("doc.export_to_text() returned non-string", file=sys.stderr)
            return 1
        # Fail-open is not desired here: if conversion yields nothing, emit nothing.
        sys.stdout.write(text or "")
        return 0
    except Exception as e:
        print(f"docling_export_document_text failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

