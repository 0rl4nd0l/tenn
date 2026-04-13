from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import docling_extract
from app.services.docling_extract import DoclingTable, StructuredDocument


def test_extract_structured_reads_fresh_cache(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    cached_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=2,
                caption="Cached table",
                rows=[["Metric", "Value"], ["Revenue", "100"]],
                headers=["Metric", "Value"],
            )
        ],
        sections=[{"heading": True, "text": "Cached heading", "page": 1}],
        extraction_method="docling",
        page_count=3,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    cache_path = Path(str(pdf_path) + ".docling.json")
    docling_extract._save_cache(cache_path, cached_doc)
    pdf_mtime = pdf_path.stat().st_mtime
    os.utime(cache_path, (pdf_mtime + 5, pdf_mtime + 5))

    monkeypatch.setattr(
        docling_extract,
        "_run_docling_with_timeout",
        lambda path: (_ for _ in ()).throw(
            AssertionError("docling should not run when cache is fresh")
        ),
    )

    loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert loaded == cached_doc


def test_extract_structured_reextracts_when_cache_is_corrupt(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    cache_path = Path(str(pdf_path) + ".docling.json")
    cache_path.write_text("{not valid json", encoding="utf-8")
    pdf_mtime = pdf_path.stat().st_mtime
    os.utime(cache_path, (pdf_mtime + 5, pdf_mtime + 5))

    extracted_doc = StructuredDocument(
        tables=[],
        sections=[{"heading": False, "text": "Re-extracted body", "page": 1}],
        extraction_method="docling",
        page_count=1,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    calls: list[str] = []

    def fake_run(
        path: str, timeout: int = docling_extract.DOCLING_TIMEOUT_SECONDS
    ) -> StructuredDocument:
        calls.append(path)
        return extracted_doc

    monkeypatch.setattr(docling_extract, "_run_docling_with_timeout", fake_run)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)

    loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert loaded == extracted_doc
    assert calls == [str(pdf_path)]
    assert docling_extract._load_cache(cache_path) == extracted_doc


def test_extract_structured_reextracts_when_docling_cache_is_truncated(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    stale_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=10,
                caption="Cached table",
                rows=[["Metric", "Value"], ["Revenue", "100"]],
                headers=["Metric", "Value"],
            )
        ],
        sections=[{"heading": True, "text": "Cached heading", "page": 2}],
        extraction_method="docling",
        page_count=6,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    cache_path = Path(str(pdf_path) + ".docling.json")
    docling_extract._save_cache(cache_path, stale_doc)
    pdf_mtime = pdf_path.stat().st_mtime
    os.utime(cache_path, (pdf_mtime + 5, pdf_mtime + 5))

    extracted_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=21,
                caption="Fresh cash flow",
                rows=[["Metric", "Value"], ["Cash", "2124"]],
                headers=["Metric", "Value"],
            )
        ],
        sections=[{"heading": False, "text": "Fresh body", "page": 38}],
        extraction_method="docling",
        page_count=38,
        source_pdf_page_count=38,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    calls: list[str] = []

    def fake_run(
        path: str, timeout: int = docling_extract.DOCLING_TIMEOUT_SECONDS
    ) -> StructuredDocument:
        calls.append(path)
        return extracted_doc

    monkeypatch.setattr(docling_extract, "_run_docling_with_timeout", fake_run)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 38)

    loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert loaded == extracted_doc
    assert calls == [str(pdf_path)]
    assert docling_extract._load_cache(cache_path) == extracted_doc


def test_extract_structured_reextracts_when_cache_pdf_page_metadata_mismatches(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    stale_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=38,
                caption="Cached table",
                rows=[["Metric", "Value"], ["Revenue", "100"]],
                headers=["Metric", "Value"],
            )
        ],
        sections=[{"heading": True, "text": "Cached heading", "page": 38}],
        extraction_method="docling",
        page_count=38,
        source_pdf_page_count=41,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    cache_path = Path(str(pdf_path) + ".docling.json")
    docling_extract._save_cache(cache_path, stale_doc)
    pdf_mtime = pdf_path.stat().st_mtime
    os.utime(cache_path, (pdf_mtime + 5, pdf_mtime + 5))

    extracted_doc = StructuredDocument(
        tables=[],
        sections=[{"heading": False, "text": "Fresh body", "page": 38}],
        extraction_method="docling",
        page_count=38,
        source_pdf_page_count=38,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    calls: list[str] = []

    def fake_run(
        path: str, timeout: int = docling_extract.DOCLING_TIMEOUT_SECONDS
    ) -> StructuredDocument:
        calls.append(path)
        return extracted_doc

    monkeypatch.setattr(docling_extract, "_run_docling_with_timeout", fake_run)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 38)

    loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert loaded == extracted_doc
    assert calls == [str(pdf_path)]


def test_extract_structured_uses_pymupdf_fallback_when_docling_fails(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    fallback_doc = StructuredDocument(
        tables=[],
        sections=[{"heading": False, "text": "Fallback text", "page": 1}],
        extraction_method="pymupdf_fallback",
        page_count=1,
    )

    monkeypatch.setattr(
        docling_extract,
        "_run_docling_with_timeout",
        lambda path, timeout=120: (_ for _ in ()).throw(
            TimeoutError("docling timeout")
        ),
    )
    monkeypatch.setattr(docling_extract, "_extract_pymupdf", lambda path: fallback_doc)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)

    loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert loaded == fallback_doc


def test_extract_structured_preempts_docling_for_large_pdf(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    pdf_path.touch()
    os.truncate(
        pdf_path,
        docling_extract.DOCLING_LARGE_PDF_SIZE_THRESHOLD_BYTES + 1024,
    )

    fallback_doc = StructuredDocument(
        tables=[],
        sections=[{"heading": False, "text": "Fallback text", "page": 1}],
        extraction_method="pymupdf",
        page_count=238,
    )

    monkeypatch.setattr(
        docling_extract,
        "_get_page_count_fast",
        lambda path: docling_extract.DOCLING_LARGE_PDF_PAGE_THRESHOLD,
    )
    monkeypatch.setattr(
        docling_extract,
        "_run_docling_with_timeout",
        lambda path, timeout=120: (_ for _ in ()).throw(
            AssertionError("docling should not run after large-pdf precheck")
        ),
    )
    monkeypatch.setattr(docling_extract, "_extract_pymupdf", lambda path: fallback_doc)

    loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert loaded == fallback_doc


def test_extract_structured_strict_docling_bypasses_large_pdf_precheck(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    pdf_path.touch()
    os.truncate(
        pdf_path,
        docling_extract.DOCLING_LARGE_PDF_SIZE_THRESHOLD_BYTES + 1024,
    )

    extracted_doc = StructuredDocument(
        tables=[],
        sections=[{"heading": False, "text": "Docling text", "page": 1}],
        extraction_method="docling",
        page_count=238,
        docling_version=docling_extract.DOCLING_VERSION,
    )

    monkeypatch.setattr(docling_extract, "validate_docling_environment", lambda: None)
    monkeypatch.setattr(
        docling_extract,
        "_get_page_count_fast",
        lambda path: docling_extract.DOCLING_LARGE_PDF_PAGE_THRESHOLD,
    )
    monkeypatch.setattr(
        docling_extract,
        "_run_docling_with_timeout",
        lambda path, timeout=120: extracted_doc,
    )
    monkeypatch.setattr(
        docling_extract,
        "_extract_pymupdf",
        lambda path: (_ for _ in ()).throw(
            AssertionError("strict docling should not preempt to pymupdf")
        ),
    )

    loaded = docling_extract.extract_structured(
        str(pdf_path),
        backend="docling",
        strict_backend=True,
    )

    assert loaded == extracted_doc


def test_extract_structured_strict_docling_does_not_fallback(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(docling_extract, "validate_docling_environment", lambda: None)
    monkeypatch.setattr(
        docling_extract,
        "_run_docling_with_timeout",
        lambda path, timeout=120: (_ for _ in ()).throw(
            TimeoutError("docling timeout")
        ),
    )
    monkeypatch.setattr(
        docling_extract,
        "_extract_pymupdf",
        lambda path: (_ for _ in ()).throw(
            AssertionError("strict docling must not fallback")
        ),
    )
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)

    with pytest.raises(RuntimeError, match="strict backend failed"):
        docling_extract.extract_structured(
            str(pdf_path),
            backend="docling",
            strict_backend=True,
        )


def test_pymupdf_fallback_extracts_sections_and_tables(monkeypatch):
    rows = [["Metric", "Value"], ["Revenue", "100"]]

    class FakeTable:
        def extract(self):
            return rows

    class FakePage:
        def __init__(self, text: str):
            self._text = text

        def get_text(self, mode: str) -> str:
            assert mode == "text"
            return self._text

        def find_tables(self):
            return [FakeTable()]

    class FakeDoc:
        def __init__(self):
            self.pages = [FakePage(" First page text "), FakePage("Second page text")]

        def __len__(self):
            return len(self.pages)

        def __iter__(self):
            return iter(self.pages)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(docling_extract.fitz, "open", lambda path: FakeDoc())

    loaded = docling_extract._pymupdf_fallback("/tmp/fake.pdf")

    assert loaded.extraction_method == "pymupdf_fallback"
    assert loaded.page_count == 2
    assert loaded.sections == [
        {"heading": False, "text": "First page text", "page": 1},
        {"heading": False, "text": "Second page text", "page": 2},
    ]
    assert len(loaded.tables) == 2
    assert loaded.tables[0].headers == ["Metric", "Value"]
    assert loaded.tables[0].rows == rows


def test_garbling_detected_falls_back_to_pymupdf(tmp_path, monkeypatch, caplog):
    import logging

    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    # Garbled docling result — font-encoded +3 ASCII shift pattern
    garbled_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=1,
                caption="",
                rows=[["", ""], [")LQDO GLYLGHQG", "100"], ["5HYHQXH", "200"]],
                headers=["", ""],
            ),
            DoclingTable(
                page_number=2,
                caption="",
                rows=[["", ""], ["&DVK", "300"], ["2WKHU", "400"]],
                headers=["", ""],
            ),
            DoclingTable(
                page_number=3,
                caption="",
                rows=[["", ""], ["3URSHUW\\", "500"]],
                headers=["", ""],
            ),
        ],
        sections=[],
        extraction_method="docling",
        page_count=3,
        docling_version=docling_extract.DOCLING_VERSION,
    )

    pymupdf_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=1,
                caption="",
                rows=[["Metric", "Value"], ["Revenue", "200"]],
                headers=["Metric", "Value"],
            ),
        ],
        sections=[],
        extraction_method="pymupdf",
        page_count=3,
    )

    pymupdf_calls: list[str] = []

    def fake_pymupdf(path: str) -> StructuredDocument:
        pymupdf_calls.append(path)
        return pymupdf_doc

    monkeypatch.setattr(
        docling_extract,
        "_run_docling_with_timeout",
        lambda path, timeout=120: garbled_doc,
    )
    monkeypatch.setattr(docling_extract, "_extract_pymupdf", fake_pymupdf)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 3)

    with caplog.at_level(logging.WARNING, logger="app.services.docling_extract"):
        result = docling_extract.extract_structured(str(pdf_path), backend="docling")

    assert pymupdf_calls == [str(pdf_path)], "_extract_pymupdf should be called once"
    assert result is pymupdf_doc, "Should return PyMuPDF result, not garbled Docling"
    assert any("font-garbled" in msg for msg in caplog.messages), (
        "Should log WARNING containing 'font-garbled'"
    )


def test_extract_caption_prefers_captions_list():
    table_item = SimpleNamespace(
        captions=[SimpleNamespace(text="Statement of Cash Flows")],
        caption="Older caption",
    )

    assert docling_extract._extract_caption(table_item) == "Statement of Cash Flows"
