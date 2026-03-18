from __future__ import annotations

import json
import subprocess
from pathlib import Path

import fitz

from preprocess_investment_pdfs import compare_extraction_accuracy_for_pdf, run


def _make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_run_writes_cleaned_text_and_chunks(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "pdfs"
    out_dir = tmp_path / "out"
    pdf_dir.mkdir(parents=True)

    _make_pdf(pdf_dir / "valuation_notes.pdf", "Valuation methods include DCF and multiples.\n\nRisk and margin of safety.")

    summary = run(pdf_dir=pdf_dir, out_dir=out_dir, max_chars=80, overlap_words=3)

    assert summary["status"] == "success"
    assert summary["documents"] == 1
    assert summary["chunks"] >= 1

    extraction_manifest = out_dir / "extraction_manifest.jsonl"
    chunks_manifest = out_dir / "semantic_chunks.jsonl"
    assert extraction_manifest.exists()
    assert chunks_manifest.exists()

    doc_rows = [json.loads(line) for line in extraction_manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunk_rows = [json.loads(line) for line in chunks_manifest.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert len(doc_rows) == 1
    assert doc_rows[0]["source_file_name"] == "valuation_notes.pdf"
    assert Path(doc_rows[0]["text_path"]).exists()

    assert len(chunk_rows) >= 1
    first = chunk_rows[0]
    assert first["doc_id"] == doc_rows[0]["doc_id"]
    assert first["source_sha256"] == doc_rows[0]["source_sha256"]
    assert first["attribution"]["extraction_method"] == "pymupdf"


def test_compare_extraction_accuracy_for_pdf_with_mocked_pdftotext(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "tech_analysis.pdf"
    _make_pdf(pdf_path, "Technical analysis uses trend and volume confirmation.")

    def _fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="Technical analysis uses trend and volume confirmation.", stderr="")

    monkeypatch.setattr("preprocess_investment_pdfs.subprocess.run", _fake_run)

    result = compare_extraction_accuracy_for_pdf(pdf_path)

    assert result["status"] == "ok"
    assert result["pdftotext_chars"] > 0
    assert result["token_overlap_jaccard"] >= 0.99
