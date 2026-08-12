from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import docling_extract
from app.services.docling_extract import (
    DoclingTable,
    ExtractionTimeoutError,
    StructuredDocument,
)


@pytest.fixture(autouse=True)
def isolated_extract_cache_root(tmp_path, monkeypatch):
    monkeypatch.setattr(docling_extract.settings, "data_root", str(tmp_path / "data"))


def _test_cache_path(pdf_path: Path, cache_suffix: str) -> Path:
    cache_path = docling_extract._cache_path_for_pdf(str(pdf_path), cache_suffix)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    return cache_path


class FakeOpenabilityRunner:
    def __init__(self, *, fail_render: bool = False, fail_ocr: bool = False):
        self.fail_render = fail_render
        self.fail_ocr = fail_ocr
        self.calls: list[list[str]] = []

    def run(self, args: list[str], *, timeout: int = 120):
        self.calls.append(args)
        if args[0] == "pdftoppm":
            if self.fail_render:
                return docling_extract.OpenabilityCommandResult(
                    args=args,
                    returncode=1,
                    stdout="",
                    stderr="render failed",
                )
            page = args[2]
            prefix = Path(args[-1])
            (prefix.parent / f"{prefix.name}-{page}.png").write_text(
                "fake image",
                encoding="utf-8",
            )
            return docling_extract.OpenabilityCommandResult(
                args=args,
                returncode=0,
                stdout="",
                stderr="",
            )
        if args[0] == "tesseract":
            if self.fail_ocr:
                return docling_extract.OpenabilityCommandResult(
                    args=args,
                    returncode=1,
                    stdout="",
                    stderr="ocr failed",
                )
            return docling_extract.OpenabilityCommandResult(
                args=args,
                returncode=0,
                stdout=_openability_tsv_fixture(),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {args}")


def _openability_tsv_fixture() -> str:
    lines = [
        ("Consolidated statement of cash flows", 95),
        ("For the year ended 30 June 2022", 94),
        ("$000 $000", 93),
        ("Net cash from operating activities 2,529,823", 92),
    ]
    rows = [
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\t"
        "top\twidth\theight\tconf\ttext"
    ]
    for line_number, (line, confidence) in enumerate(lines, start=1):
        for word_number, word in enumerate(line.split(), start=1):
            rows.append(
                f"5\t1\t1\t1\t{line_number}\t{word_number}\t"
                f"{10 + word_number * 20}\t{line_number * 30}\t18\t12\t"
                f"{confidence}\t{word}"
            )
    return "\n".join(rows)


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
                raw_header_rows=[["Metric", "Value"]],
            )
        ],
        sections=[{"heading": True, "text": "Cached heading", "page": 1}],
        extraction_method="docling",
        page_count=3,
        docling_version=docling_extract.DOCLING_VERSION,
    )
    cache_path = _test_cache_path(pdf_path, ".docling.json")
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


def test_pymupdf_legacy_cache_without_raw_headers_is_reextracted(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    cache_path = _test_cache_path(pdf_path, ".pymupdf.json")
    cache_path.write_text(
        json.dumps(
            {
                "extraction_method": "pymupdf",
                "page_count": 1,
                "tables": [
                    {
                        "page_number": 1,
                        "caption": "Legacy table",
                        "headers": ["", "Current", "Prior"],
                        "rows": [["Revenue", "100", "90"]],
                    }
                ],
                "sections": [],
            }
        ),
        encoding="utf-8",
    )
    pdf_mtime = pdf_path.stat().st_mtime
    os.utime(cache_path, (pdf_mtime + 5, pdf_mtime + 5))
    refreshed_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=1,
                caption="Refreshed table",
                headers=["", "31 Dec 2025", "31 Dec 2024"],
                raw_header_rows=[["", "31 Dec 2025", "31 Dec 2024"]],
                rows=[["Revenue", "100", "90"]],
            )
        ],
        extraction_method="pymupdf",
        page_count=1,
    )
    extraction_calls: list[str] = []
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)
    monkeypatch.setattr(
        docling_extract,
        "_extract_pymupdf",
        lambda path: extraction_calls.append(path) or refreshed_doc,
    )

    loaded = docling_extract.extract_structured(str(pdf_path), backend="pymupdf")

    assert loaded == refreshed_doc
    assert extraction_calls == [str(pdf_path)]


def test_pymupdf_current_cache_with_raw_headers_is_reused(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    cached_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=1,
                caption="Current table",
                headers=["", "31 Dec 2025", "31 Dec 2024"],
                raw_header_rows=[["", "31 Dec 2025", "31 Dec 2024"]],
                rows=[["Revenue", "100", "90"]],
            )
        ],
        extraction_method="pymupdf",
        page_count=1,
    )
    cache_path = _test_cache_path(pdf_path, ".pymupdf.json")
    docling_extract._save_cache(cache_path, cached_doc)
    pdf_mtime = pdf_path.stat().st_mtime
    os.utime(cache_path, (pdf_mtime + 5, pdf_mtime + 5))
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)
    monkeypatch.setattr(
        docling_extract,
        "_extract_pymupdf",
        lambda path: (_ for _ in ()).throw(
            AssertionError("PyMuPDF should not run for a valid current cache")
        ),
    )

    loaded = docling_extract.extract_structured(str(pdf_path), backend="pymupdf")

    assert loaded == cached_doc


def test_pymupdf_external_header_is_preserved_and_combined_with_unit_row():
    table = SimpleNamespace(
        header=SimpleNamespace(
            external=True,
            names=["", "", "31 December 2025", "31 December 2024"],
        )
    )
    rows = [
        ["", "Note", "US$m", "US$m"],
        ["Operating sales revenue", "2", "8,439", "7,638"],
    ]

    headers, raw_header_rows = docling_extract._pymupdf_table_header_evidence(
        table, rows
    )

    assert raw_header_rows == [
        ["", "", "31 December 2025", "31 December 2024"],
        ["", "Note", "US$m", "US$m"],
    ]
    assert headers == [
        "",
        "Note",
        "31 December 2025 US$m",
        "31 December 2024 US$m",
    ]


def test_pymupdf_external_header_does_not_consume_first_data_row():
    table = SimpleNamespace(
        header=SimpleNamespace(
            external=True,
            names=["", "30 JUNE 2025 US$M", "30 JUNE 2024 US$M"],
        )
    )
    rows = [
        ["Operating activities", "", ""],
        ["Net cash flows from operating activities", "1,756", "1,212"],
    ]

    headers, raw_header_rows = docling_extract._pymupdf_table_header_evidence(
        table, rows
    )

    assert headers == ["", "30 JUNE 2025 US$M", "30 JUNE 2024 US$M"]
    assert raw_header_rows == [
        ["", "30 JUNE 2025 US$M", "30 JUNE 2024 US$M"]
    ]


def test_openability_diagnostics_default_off_does_not_run(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    parsed_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=1,
                caption="For personal use only",
                rows=[["", ""], ["", ""]],
                headers=["", ""],
            )
        ],
        sections=[{"heading": False, "text": "For personal use only", "page": 1}],
        extraction_method="pymupdf",
        page_count=1,
        source_pdf_page_count=1,
    )

    monkeypatch.setattr(docling_extract, "_extract_pymupdf", lambda path: parsed_doc)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)
    monkeypatch.setattr(
        docling_extract,
        "_build_openability_diagnostics",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("openability diagnostics should be opt-in")
        ),
    )

    loaded = docling_extract.extract_structured(str(pdf_path), backend="pymupdf")

    assert loaded.parser_diagnostics == {}


def test_openability_diagnostics_round_trips_without_changing_tables(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    parsed_doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=1,
                caption="For personal use only",
                rows=[["", ""], ["", ""]],
                headers=["", ""],
            )
        ],
        sections=[{"heading": False, "text": "For personal use only", "page": 1}],
        extraction_method="pymupdf",
        page_count=1,
        source_pdf_page_count=1,
    )
    runner = FakeOpenabilityRunner()

    monkeypatch.setattr(docling_extract, "_extract_pymupdf", lambda path: parsed_doc)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)

    loaded = docling_extract.extract_structured(
        str(pdf_path),
        backend="pymupdf",
        openability_diagnostics=True,
        openability_pages=[1],
        openability_runner=runner,
    )

    assert loaded.tables == parsed_doc.tables
    assert loaded.sections == parsed_doc.sections
    diagnostic = loaded.parser_diagnostics["openability"]
    assert diagnostic["provenance_only"] is True
    assert diagnostic["feeds_canonical_output"] is False
    assert diagnostic["canonical_output_changed"] is False
    assert diagnostic["summary"]["classification"] == "ocr_openability_provenance_gap"
    assert diagnostic["summary"]["canonical_repair_ready"] is False
    assert diagnostic["ocr_records"][0]["statement_label"] == "cashflow_statement"
    assert diagnostic["ocr_records"][0]["period_phrases"] == [
        "For the year ended 30 June 2022"
    ]
    assert diagnostic["ocr_records"][0]["scale_phrases"] == ["$000"]
    assert diagnostic["ocr_records"][0]["row_candidates"] == [
        {
            "source_text": "Net cash from operating activities 2,529,823",
            "candidate_value_text": "2,529,823",
            "value_text_candidates": ["2,529,823"],
                "candidate_value_quality": "financial_amount",
                "source_region": {
                    "left": 130,
                    "top": 120,
                    "right": 148,
                    "bottom": 132,
                },
                "source_row": 4,
                "source_cell": [6],
            "recognition_confidence": 92.0,
        }
    ]

    payload_text = json.dumps(diagnostic)
    assert "accepted_metrics" not in payload_text
    assert "normalized_value" not in payload_text

    cache_doc = docling_extract._load_cache(
        docling_extract._cache_path_for_pdf(str(pdf_path), ".pymupdf.json")
    )
    assert cache_doc.tables == parsed_doc.tables
    assert cache_doc.parser_diagnostics["openability"] == diagnostic


def test_openability_diagnostics_rebuilds_when_cached_pages_mismatch(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    old_mtime = time.time() - 10
    os.utime(pdf_path, (old_mtime, old_mtime))

    extract_calls = []

    def _make_doc() -> StructuredDocument:
        return StructuredDocument(
            tables=[
                DoclingTable(
                    page_number=1,
                    caption="For personal use only",
                    rows=[["", ""], ["", ""]],
                    headers=["", ""],
                ),
                DoclingTable(
                    page_number=2,
                    caption="For personal use only",
                    rows=[["", ""], ["", ""]],
                    headers=["", ""],
                ),
            ],
            sections=[
                {"heading": False, "text": "For personal use only", "page": 1},
                {"heading": False, "text": "For personal use only", "page": 2},
            ],
            extraction_method="pymupdf",
            page_count=2,
            source_pdf_page_count=2,
        )

    def _extract(path: str) -> StructuredDocument:
        extract_calls.append(path)
        return _make_doc()

    runner = FakeOpenabilityRunner()
    monkeypatch.setattr(docling_extract, "_extract_pymupdf", _extract)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 2)

    first = docling_extract.extract_structured(
        str(pdf_path),
        backend="pymupdf",
        openability_diagnostics=True,
        openability_pages=[1],
        openability_runner=runner,
    )
    assert first.parser_diagnostics["openability"]["diagnostic_pages"] == [1]

    second = docling_extract.extract_structured(
        str(pdf_path),
        backend="pymupdf",
        openability_diagnostics=True,
        openability_pages=[2],
        openability_runner=runner,
    )

    assert extract_calls == [str(pdf_path)]
    assert second.parser_diagnostics["openability"]["diagnostic_pages"] == [2]
    assert [
        args[2] for args in runner.calls if args and args[0] == "pdftoppm"
    ] == ["1", "2"]
    cache_doc = docling_extract._load_cache(
        docling_extract._cache_path_for_pdf(str(pdf_path), ".pymupdf.json")
    )
    assert cache_doc.parser_diagnostics["openability"]["diagnostic_pages"] == [2]


def test_openability_classification_uses_statement_pages_not_scale_note_noise(
    monkeypatch,
):
    doc = StructuredDocument(
        tables=[
            DoclingTable(
                page_number=57,
                caption="For personal use only",
                rows=[["", ""], ["", ""]],
                headers=["", ""],
            ),
            DoclingTable(
                page_number=61,
                caption="",
                rows=[["only", ""], ["use", "personal"]],
                headers=["only", ""],
            ),
        ],
        sections=[],
        extraction_method="pymupdf",
        page_count=61,
        source_pdf_page_count=61,
    )

    monkeypatch.setattr(
        docling_extract,
        "_run_openability_ocr_for_pages",
        lambda pdf_path, pages, runner=None: [
            {
                "page": 57,
                "source": "openability_ocr",
                "statement_label": "income_statement",
                "statement_evidence_found": True,
                "period_phrases": ["For the year ended 30 June 2022"],
                "scale_phrases": ["$000"],
                "row_candidates": [
                    {
                        "source_text": "Revenue 4,920,102",
                        "candidate_value_text": "4,920,102",
                        "value_text_candidates": ["4,920,102"],
                        "candidate_value_quality": "financial_amount",
                    }
                ],
                "row_candidate_count": 1,
                "verdict": "PROVENANCE_CAPTURED",
            },
            {
                "page": 61,
                "source": "openability_ocr",
                "statement_label": None,
                "statement_evidence_found": False,
                "period_phrases": ["For the year ended 30 June 2022"],
                "scale_phrases": ["rounded to the nearest thousand"],
                "row_candidates": [],
                "row_candidate_count": 0,
                "verdict": "DATA_MISSING",
            },
        ],
    )

    diagnostic = docling_extract._build_openability_diagnostics(
        pdf_path="/tmp/fake.pdf",
        doc=doc,
        pages=[57, 61],
        runner=FakeOpenabilityRunner(),
    )

    summary = diagnostic["summary"]
    assert summary["parser_all_diagnostic_pages_empty"] is False
    assert summary["parser_tables_present_but_cells_missing"] is True
    assert summary["parser_statement_page_table_count"] == 1
    assert summary["parser_statement_page_nonempty_cell_count"] == 0
    assert summary["classification"] == "ocr_openability_provenance_gap"


def test_openability_ocr_failure_stays_data_missing():
    records = docling_extract._run_openability_ocr_for_pages(
        "/tmp/nonexistent.pdf",
        [1],
        runner=FakeOpenabilityRunner(fail_render=True),
    )

    assert records == [
        {
            "page": 1,
            "source": "openability_ocr",
            "statement_evidence_found": False,
            "verdict": "DATA_MISSING",
            "error": "pdftoppm_failed",
            "stderr": "render failed",
        }
    ]


def test_openability_diagnostics_reject_unbounded_page_request():
    doc = StructuredDocument(page_count=20, source_pdf_page_count=20)

    with pytest.raises(ValueError, match="exceeds"):
        docling_extract._build_openability_diagnostics(
            pdf_path="/tmp/nonexistent.pdf",
            doc=doc,
            pages=list(range(1, docling_extract.OPENABILITY_DIAGNOSTIC_MAX_PAGES + 2)),
            runner=FakeOpenabilityRunner(),
        )


def test_openability_text_parser_preserves_source_text_only():
    parsed = docling_extract._parse_openability_text(
        57,
        "Consolidated statement of comprehensive income\n"
        "For the year ended 30 June 2022\n"
        "$000\n"
        "Revenue 4,920,102\n",
        source="test",
    )

    assert parsed["statement_label"] == "income_statement"
    assert parsed["period_phrases"] == ["For the year ended 30 June 2022"]
    assert parsed["scale_phrases"] == ["$000"]
    assert parsed["row_candidates"] == [
        {
            "source_text": "Revenue 4,920,102",
            "candidate_value_text": "4,920,102",
            "value_text_candidates": ["4,920,102"],
            "candidate_value_quality": "financial_amount",
        }
    ]
    assert "normalized_value" not in json.dumps(parsed)


def test_openability_text_parser_preserves_terminal_amount_after_note_refs():
    parsed = docling_extract._parse_openability_text(
        57,
        "Revenue 2.1 4,920,102\n"
        "Net cash from operating activities 3.4 2,529,823\n",
        source="test",
    )

    assert parsed["row_candidates"] == [
        {
            "source_text": "Revenue 2.1 4,920,102",
            "candidate_value_text": "4,920,102",
            "value_text_candidates": ["2.1", "4,920,102"],
            "candidate_value_quality": "financial_amount",
        },
        {
            "source_text": "Net cash from operating activities 3.4 2,529,823",
            "candidate_value_text": "2,529,823",
            "value_text_candidates": ["3.4", "2,529,823"],
            "candidate_value_quality": "financial_amount",
        },
    ]


def test_openability_text_parser_uses_first_current_period_amount_before_comparative():
    parsed = docling_extract._parse_openability_text(
        57,
        "Revenue 2.1 4,920,102 1,556,976\n",
        source="test",
    )

    assert parsed["row_candidates"] == [
        {
            "source_text": "Revenue 2.1 4,920,102 1,556,976",
            "candidate_value_text": "4,920,102",
            "value_text_candidates": ["2.1", "4,920,102", "1,556,976"],
            "candidate_value_quality": "financial_amount",
        }
    ]


def test_openability_tsv_retains_region_row_cell_and_confidence():
    text, provenance = docling_extract._parse_openability_tsv(
        _openability_tsv_fixture()
    )
    parsed = docling_extract._parse_openability_text(
        1,
        text,
        source="test",
        line_provenance=provenance,
    )

    candidate = parsed["row_candidates"][0]
    assert candidate["source_region"] == {
        "left": 130,
        "top": 120,
        "right": 148,
        "bottom": 132,
    }
    assert candidate["source_row"] == 4
    assert candidate["source_cell"] == [6]
    assert candidate["recognition_confidence"] == 92


def test_openability_tsv_selects_amount_after_year_with_cell_local_provenance():
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    rows = [
        "5\t1\t1\t1\t1\t1\t10\t20\t60\t12\t96\tRevenue",
        "5\t1\t1\t1\t1\t2\t80\t20\t35\t12\t95\t2025",
        "5\t1\t1\t1\t1\t3\t125\t20\t80\t12\t94\t4,920,102",
        "5\t1\t1\t1\t1\t4\t215\t20\t80\t12\t93\t1,556,976",
    ]
    text, provenance = docling_extract._parse_openability_tsv(
        "\n".join([header, *rows])
    )

    parsed = docling_extract._parse_openability_text(
        1,
        text,
        source="test",
        line_provenance=provenance,
    )

    candidate = parsed["row_candidates"][0]
    assert candidate["candidate_value_text"] == "4,920,102"
    assert candidate["source_region"] == {
        "left": 125,
        "top": 20,
        "right": 205,
        "bottom": 32,
    }
    assert candidate["source_cell"] == [3]
    assert candidate["recognition_confidence"] == 94


def test_openability_tsv_binds_first_duplicate_amount_to_its_ocr_cell():
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    rows = [
        "5\t1\t1\t1\t1\t1\t10\t20\t60\t12\t96\tRevenue",
        "5\t1\t1\t1\t1\t2\t80\t20\t80\t12\t94\t4,920,102",
        "5\t1\t1\t1\t1\t3\t170\t20\t80\t12\t91\t4,920,102",
    ]
    text, provenance = docling_extract._parse_openability_tsv(
        "\n".join([header, *rows])
    )

    parsed = docling_extract._parse_openability_text(
        1,
        text,
        source="test",
        line_provenance=provenance,
    )

    candidate = parsed["row_candidates"][0]
    assert candidate["candidate_value_text"] == "4,920,102"
    assert candidate["source_region"] == {
        "left": 80,
        "top": 20,
        "right": 160,
        "bottom": 32,
    }
    assert candidate["source_cell"] == [2]
    assert candidate["recognition_confidence"] == 94


def test_openability_tsv_binds_amount_inside_punctuated_ocr_word():
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    rows = [
        "5\t1\t1\t1\t1\t1\t10\t20\t60\t12\t96\tRevenue",
        "5\t1\t1\t1\t1\t2\t80\t20\t80\t12\t94\t4,920,102*",
    ]
    text, provenance = docling_extract._parse_openability_tsv(
        "\n".join([header, *rows])
    )

    parsed = docling_extract._parse_openability_text(
        1,
        text,
        source="test",
        line_provenance=provenance,
    )

    candidate = parsed["row_candidates"][0]
    assert candidate["candidate_value_text"] == "4,920,102"
    assert candidate["candidate_value_quality"] == "financial_amount"
    assert candidate["source_region"] == {
        "left": 80,
        "top": 20,
        "right": 160,
        "bottom": 32,
    }
    assert candidate["source_cell"] == [2]
    assert candidate["recognition_confidence"] == 94


def test_docling_table_retains_structured_ocr_source_candidates():
    candidate = {
        "page_number": 1,
        "source_region": {"left": 30, "top": 120, "right": 148, "bottom": 132},
        "source_row": 4,
        "source_cell": [1, 2, 3, 4, 5, 6],
        "source_text": "Revenue 4,920,102",
        "candidate_value_text": "4,920,102",
        "recognition_confidence": 92.0,
    }

    table = DoclingTable(
        page_number=1,
        caption="OCR statement",
        rows=[["Revenue", "4,920,102"]],
        headers=["Source row", "Value"],
        ocr_source_candidates=[candidate],
    )

    assert table.ocr_source_candidates == [candidate]


def test_openability_low_confidence_and_conflicting_rows_fail_closed():
    low_confidence = docling_extract._parse_openability_text(
        1,
        "Revenue 4,920,102",
        source="test",
        line_provenance=[
            {
                "source_region": {"left": 1, "top": 2, "right": 3, "bottom": 4},
                "source_row": 1,
                "source_cell": [1, 2],
                "recognition_confidence": 79,
            }
        ],
    )
    assert (
        low_confidence["row_candidates"][0]["candidate_value_quality"]
        == "low_confidence"
    )

    parsed = docling_extract._parse_openability_text(
        1,
        "Revenue 4,920,102\nRevenue 4,920,192",
        source="test",
        line_provenance=[
            {
                "source_region": {"left": 1, "top": 2, "right": 3, "bottom": 4},
                "source_row": 1,
                "source_cell": [1, 2],
                "recognition_confidence": 79,
            },
            {
                "source_region": {"left": 1, "top": 5, "right": 3, "bottom": 7},
                "source_row": 2,
                "source_cell": [1, 2],
                "recognition_confidence": 99,
            },
        ],
    )

    assert {
        candidate["candidate_value_quality"]
        for candidate in parsed["row_candidates"]
    } == {"conflicting_recognition"}


def test_extract_structured_reextracts_when_cache_is_corrupt(tmp_path, monkeypatch):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    cache_path = _test_cache_path(pdf_path, ".docling.json")
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
    cache_path = _test_cache_path(pdf_path, ".docling.json")
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
    cache_path = _test_cache_path(pdf_path, ".docling.json")
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


def test_pymupdf_fallback_cache_uses_data_root_when_source_dir_read_only(
    tmp_path, monkeypatch
):
    source_dir = tmp_path / "readonly-source"
    source_dir.mkdir()
    pdf_path = source_dir / "report.pdf"
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

    source_dir.chmod(0o555)
    try:
        loaded = docling_extract.extract_structured(str(pdf_path), backend="docling")
    finally:
        source_dir.chmod(0o755)

    cache_path = docling_extract._pymupdf_cache_path(str(pdf_path))
    source_sidecar = Path(str(pdf_path) + ".pymupdf.json")
    assert loaded == fallback_doc
    assert cache_path.exists()
    assert cache_path.relative_to(docling_extract._extract_cache_root())
    assert not source_sidecar.exists()


def test_pymupdf_backend_cache_does_not_create_source_pdf_sidecar(
    tmp_path, monkeypatch
):
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    pymupdf_doc = StructuredDocument(
        tables=[],
        sections=[{"heading": False, "text": "PyMuPDF text", "page": 1}],
        extraction_method="pymupdf",
        page_count=1,
    )

    monkeypatch.setattr(docling_extract, "_extract_pymupdf", lambda path: pymupdf_doc)
    monkeypatch.setattr(docling_extract, "_get_page_count_fast", lambda path: 1)

    loaded = docling_extract.extract_structured(str(pdf_path), backend="pymupdf")

    cache_path = docling_extract._pymupdf_cache_path(str(pdf_path))
    assert loaded == pymupdf_doc
    assert cache_path.exists()
    assert cache_path.relative_to(docling_extract._extract_cache_root())
    assert not Path(str(pdf_path) + ".pymupdf.json").exists()


def test_extraction_cache_path_cannot_escape_cache_root(tmp_path):
    cache_path = docling_extract._cache_path_for_pdf(
        str(tmp_path / ".." / "source" / "report.pdf"),
        ".pymupdf.json",
    )

    assert cache_path.relative_to(docling_extract._extract_cache_root())


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
    seen_timeout: list[int] = []

    def fake_run(path: str, timeout: int = 120) -> StructuredDocument:
        seen_timeout.append(timeout)
        return extracted_doc

    monkeypatch.setattr(docling_extract, "_run_docling_with_timeout", fake_run)
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
    assert seen_timeout == [docling_extract.DOCLING_TIMEOUT_MAX_STRICT]


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


def test_run_docling_with_timeout_raises_extraction_timeout_error_on_slow_runner():
    """A slow docling runner must raise ExtractionTimeoutError, not TimeoutError.

    The timeout must fire without relying on SIGALRM (which is main-thread-only
    and incompatible with FastAPI worker-thread execution).
    """

    def slow_runner(path: str) -> StructuredDocument:
        time.sleep(0.5)
        return StructuredDocument()

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with pytest.raises(ExtractionTimeoutError) as exc_info:
            docling_extract._run_docling_with_timeout(
                "/fake/path.pdf",
                timeout=0.05,
                runner=slow_runner,
                executor=executor,
            )
        assert "/fake/path.pdf" in str(exc_info.value)
    finally:
        executor.shutdown(wait=False)


def test_run_docling_with_timeout_returns_runner_result_on_success():
    expected = StructuredDocument(page_count=7, extraction_method="docling")

    def fast_runner(path: str) -> StructuredDocument:
        return expected

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        result = docling_extract._run_docling_with_timeout(
            "/fake/path.pdf",
            timeout=5.0,
            runner=fast_runner,
            executor=executor,
        )
        assert result is expected
    finally:
        executor.shutdown(wait=False)


def test_run_docling_with_timeout_propagates_runner_exception():
    """Non-timeout errors from the runner must propagate (not be swallowed)."""

    class DoclingBoom(RuntimeError):
        pass

    def boom_runner(path: str) -> StructuredDocument:
        raise DoclingBoom("pipeline exploded")

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with pytest.raises(DoclingBoom, match="pipeline exploded"):
            docling_extract._run_docling_with_timeout(
                "/fake/path.pdf",
                timeout=5.0,
                runner=boom_runner,
                executor=executor,
            )
    finally:
        executor.shutdown(wait=False)
