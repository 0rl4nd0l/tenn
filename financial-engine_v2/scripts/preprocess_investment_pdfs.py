#!/usr/bin/env python3
"""Stage 1+2 preprocessing for local investment PDF corpora.

Outputs:
1) cleaned extraction artifacts (per-document .txt + manifest)
2) semantic chunks ready for embedding (JSONL with attribution)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import fitz


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(text: str) -> str:
    value = str(text or "").replace("\r", "\n")
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pdf_text_pymupdf(pdf_path: Path) -> tuple[str, int]:
    with fitz.open(pdf_path) as doc:
        pages = [page.get_text("text") for page in doc]
    return clean_text("\n".join(pages)), len(pages)


def extract_pdf_text_pdftotext(pdf_path: Path) -> str:
    cp = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return clean_text(cp.stdout)


def token_count_est(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+", str(text or "")))


def chunk_text(text: str, max_chars: int = 1200, overlap_words: int = 60) -> list[str]:
    words = str(text or "").split()
    if not words:
        return []

    chunks: list[str] = []
    i = 0
    while i < len(words):
        out: list[str] = []
        chars = 0
        j = i
        while j < len(words):
            w = words[j]
            add = len(w) + (1 if out else 0)
            if chars + add > max_chars and out:
                break
            out.append(w)
            chars += add
            j += 1
        chunks.append(" ".join(out))
        if j >= len(words):
            break
        i = max(i + 1, j - overlap_words)
    return chunks


@dataclass(frozen=True)
class DocRecord:
    doc_id: str
    source_file_name: str
    source_path: str
    source_sha256: str
    page_count: int
    text_path: str
    text_chars: int
    extracted_at_utc: str


def iter_pdfs(pdf_root: Path) -> Iterable[Path]:
    for path in sorted(pdf_root.rglob("*.pdf")):
        if path.is_file():
            yield path


def doc_id_for(path: Path, file_hash: str) -> str:
    raw = f"{path.name}:{file_hash}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _token_set(text: str) -> set[str]:
    return {tok.lower() for tok in re.findall(r"[A-Za-z0-9_]+", str(text or ""))}


def compare_extraction_accuracy_for_pdf(pdf_path: Path) -> dict:
    pymupdf_text, page_count = extract_pdf_text_pymupdf(pdf_path)
    row = {
        "file": str(pdf_path.resolve()),
        "page_count": page_count,
        "pymupdf_chars": len(pymupdf_text),
        "pdftotext_chars": 0,
        "token_overlap_jaccard": 0.0,
        "status": "ok",
        "error": "",
    }

    try:
        pdftotext_text = extract_pdf_text_pdftotext(pdf_path)
    except Exception as exc:
        row["status"] = "pdftotext_failed"
        row["error"] = str(exc)
        return row

    row["pdftotext_chars"] = len(pdftotext_text)
    a = _token_set(pymupdf_text)
    b = _token_set(pdftotext_text)
    union = a.union(b)
    overlap = a.intersection(b)
    row["token_overlap_jaccard"] = float(len(overlap) / len(union)) if union else 1.0
    return row


def compare_extraction_accuracy(pdf_dir: Path, out_dir: Path) -> dict:
    pdfs = list(iter_pdfs(pdf_dir))
    rows = [compare_extraction_accuracy_for_pdf(path) for path in pdfs]

    successful = [r for r in rows if r["status"] == "ok"]
    avg_jaccard = sum(float(r["token_overlap_jaccard"]) for r in successful) / len(successful) if successful else 0.0

    report = {
        "status": "success",
        "pdf_dir": str(pdf_dir.resolve()),
        "documents": len(rows),
        "successful_comparisons": len(successful),
        "avg_token_overlap_jaccard": round(avg_jaccard, 6),
        "rows": rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "extraction_accuracy_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run(
    pdf_dir: Path,
    out_dir: Path,
    max_chars: int,
    overlap_words: int,
    extraction_backend: str = "pymupdf",
) -> dict:
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    if extraction_backend not in {"pymupdf", "pdftotext"}:
        raise ValueError("extraction_backend must be one of: pymupdf, pdftotext")
    if extraction_backend == "pdftotext" and shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext backend requested but binary is not available in PATH")

    extracted_dir = out_dir / "extracted_text"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    docs: list[DocRecord] = []
    chunks: list[dict] = []
    run_id = hashlib.sha1(f"{pdf_dir}:{utc_now()}".encode("utf-8")).hexdigest()[:16]

    for pdf_path in iter_pdfs(pdf_dir):
        source_hash = sha256_file(pdf_path)
        doc_id = doc_id_for(pdf_path, source_hash)

        if extraction_backend == "pymupdf":
            text, page_count = extract_pdf_text_pymupdf(pdf_path)
        else:
            text = extract_pdf_text_pdftotext(pdf_path)
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)

        txt_path = extracted_dir / f"{doc_id}.txt"
        txt_path.write_text(text, encoding="utf-8")

        extracted_at = utc_now()
        docs.append(
            DocRecord(
                doc_id=doc_id,
                source_file_name=pdf_path.name,
                source_path=str(pdf_path.resolve()),
                source_sha256=source_hash,
                page_count=page_count,
                text_path=str(txt_path.resolve()),
                text_chars=len(text),
                extracted_at_utc=extracted_at,
            )
        )

        for idx, chunk in enumerate(chunk_text(text, max_chars=max_chars, overlap_words=overlap_words)):
            chunk_id = hashlib.sha256(f"{doc_id}:{idx}:{chunk}".encode("utf-8")).hexdigest()[:24]
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "text": chunk,
                    "token_count_est": token_count_est(chunk),
                    "source_file_name": pdf_path.name,
                    "source_path": str(pdf_path.resolve()),
                    "source_sha256": source_hash,
                    "page_start": None,
                    "page_end": None,
                    "section": "fulltext_context",
                    "corpus": "reference",
                    "framework_family": "unknown",
                    "attribution": {
                        "extraction_method": extraction_backend,
                        "pipeline_version": "preprocess_investment_pdfs_v1",
                        "run_id": run_id,
                        "extracted_at_utc": extracted_at,
                    },
                }
            )

    docs_manifest = out_dir / "extraction_manifest.jsonl"
    write_jsonl(docs_manifest, [d.__dict__ for d in docs])

    chunks_manifest = out_dir / "semantic_chunks.jsonl"
    write_jsonl(chunks_manifest, chunks)

    summary = {
        "status": "success",
        "run_id": run_id,
        "pdf_dir": str(pdf_dir.resolve()),
        "out_dir": str(out_dir.resolve()),
        "extraction_backend": extraction_backend,
        "documents": len(docs),
        "chunks": len(chunks),
        "manifest_files": {
            "extraction_manifest": str(docs_manifest.resolve()),
            "semantic_chunks": str(chunks_manifest.resolve()),
        },
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Preprocess investment PDFs into cleaned text + semantic chunks")
    ap.add_argument("--pdf-dir", required=True, help="Folder containing source PDFs")
    ap.add_argument("--out-dir", default="reports/investment_preprocess", help="Output folder")
    ap.add_argument("--max-chars", type=int, default=1200)
    ap.add_argument("--overlap-words", type=int, default=60)
    ap.add_argument(
        "--extraction-backend",
        choices=["pymupdf", "pdftotext"],
        default="pymupdf",
        help="PDF text extraction backend",
    )
    ap.add_argument(
        "--compare-pdftotext-accuracy",
        action="store_true",
        help="Write extraction_accuracy_report.json with token overlap metrics between PyMuPDF and pdftotext",
    )
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    summary = run(
        pdf_dir=pdf_dir,
        out_dir=out_dir,
        max_chars=int(args.max_chars),
        overlap_words=int(args.overlap_words),
        extraction_backend=str(args.extraction_backend),
    )

    if bool(args.compare_pdftotext_accuracy):
        report = compare_extraction_accuracy(pdf_dir=pdf_dir, out_dir=out_dir)
        summary["accuracy_report"] = str((out_dir / "extraction_accuracy_report.json").resolve())
        summary["avg_token_overlap_jaccard"] = report["avg_token_overlap_jaccard"]

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
