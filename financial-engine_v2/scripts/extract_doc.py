#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.models.documents import Document  # noqa: E402


def _resolve_pdf_path(raw: str) -> Path:
    p = Path(str(raw or "")).expanduser()
    if p.is_absolute():
        return p
    return (REPO_ROOT / p).resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract one document through pass orchestrator.")
    ap.add_argument("--document-id", required=True)
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        try:
            doc_id = uuid.UUID(str(args.document_id))
        except Exception:
            raise SystemExit(f"Invalid UUID document-id: {args.document_id}")
        doc = db.query(Document).filter(Document.document_id == doc_id).first()
    finally:
        db.close()

    if doc is None:
        raise SystemExit(f"Document not found: {args.document_id}")

    pdf_path = _resolve_pdf_path(str(getattr(doc, "pdf_path", "")))
    if not pdf_path.exists():
        raise SystemExit(f"PDF path not found: {pdf_path}")

    out_dir = Path(args.out_dir).expanduser().resolve() if str(args.out_dir).strip() else (
        REPO_ROOT / "reports" / "extract_doc" / str(args.document_id)
    )

    cmd = [
        sys.executable,
        str(REPO_ROOT.parent / "scripts" / "extract_pass_orchestrator.py"),
        "--pdf",
        str(pdf_path),
        "--out-dir",
        str(out_dir),
    ]
    cp = subprocess.run(cmd)
    return int(cp.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
