#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.method_isolated_extraction import run_method_isolated_extraction
from app.services.pipeline import _coerce_uuid, _resolve_pdf_path


def run_for_method(method: str) -> int:
    parser = argparse.ArgumentParser(
        description=f"Run strict {method} extraction for one document."
    )
    parser.add_argument("document_id", help="Backend document UUID")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        doc_uuid = _coerce_uuid(args.document_id)
        document = db.query(Document).filter(Document.document_id == doc_uuid).first()
        if document is None:
            raise SystemExit(f"document not found: {args.document_id}")

        result = run_method_isolated_extraction(
            _resolve_pdf_path(document.pdf_path),
            {
                "document_id": str(document.document_id),
                "ticker": str(document.ticker or ""),
                "title": str(document.title or ""),
            },
            None,
            requested_method=method,
            strict_method=True,
        )
        print(
            json.dumps(
                {
                    "document_id": str(document.document_id),
                    "status": result.status,
                    "error": result.error,
                    "payload": result.payload,
                },
                indent=2,
                default=str,
            )
        )
        return 0 if result.status in {"ok", "ok_low_confidence"} else 1
    finally:
        db.close()
