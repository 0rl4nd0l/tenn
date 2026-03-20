"""Unit tests for deterministic forced-OCR policy."""

from __future__ import annotations

from pathlib import Path

from services.extraction.ocr_policy import (
    OcrPolicySignals,
    apply_force_full_page_ocr_to_pipeline,
    count_numeric_canonical_rows,
    decide_forced_ocr,
    pdf_page_count,
)


class TestCountNumericCanonicalRows:
    def test_counts_float_like_values(self) -> None:
        rows = [
            {"value": "1,234.5"},
            {"value": "(100)"},
            {"value": ""},
            {"value": "n/a"},
        ]
        assert count_numeric_canonical_rows(rows) == 2

    def test_empty(self) -> None:
        assert count_numeric_canonical_rows([]) == 0


class TestDecideForcedOcr:
    def test_user_requested_skips(self) -> None:
        s = OcrPolicySignals(
            text_layer_chars=10,
            pdf_page_count=10,
            docling_row_count_before_filtering=0,
            tsr_tables_processed=0,
            canonical_numeric_rows=0,
            context_row_count=0,
        )
        out = decide_forced_ocr(s, user_requested_docling_ocr=True)
        assert out["forced"] is False
        assert out["skipped_reason"] == "user_requested_docling_ocr"

    def test_policy_disabled(self) -> None:
        s = OcrPolicySignals(
            text_layer_chars=10,
            pdf_page_count=10,
            docling_row_count_before_filtering=0,
            tsr_tables_processed=0,
            canonical_numeric_rows=0,
            context_row_count=0,
        )
        out = decide_forced_ocr(s, policy_disabled=True)
        assert out["forced"] is False
        assert out["skipped_reason"] == "policy_disabled"

    def test_sufficient_numeric_never_forces(self) -> None:
        s = OcrPolicySignals(
            text_layer_chars=50,
            pdf_page_count=1,
            docling_row_count_before_filtering=100,
            tsr_tables_processed=2,
            canonical_numeric_rows=3,
            context_row_count=0,
        )
        out = decide_forced_ocr(s)
        assert out["forced"] is False
        assert out["skipped_reason"] == "sufficient_numeric_canonical_rows"

    def test_low_density_forces(self) -> None:
        s = OcrPolicySignals(
            text_layer_chars=100,
            pdf_page_count=10,
            docling_row_count_before_filtering=0,
            tsr_tables_processed=0,
            canonical_numeric_rows=0,
            context_row_count=5,
        )
        out = decide_forced_ocr(s, chars_per_page_scanned_like=200.0)
        assert out["forced"] is True
        assert "low_text_layer_density" in out["reasons"]

    def test_empty_structure_and_candidates_forces(self) -> None:
        s = OcrPolicySignals(
            text_layer_chars=5000,
            pdf_page_count=5,
            docling_row_count_before_filtering=0,
            tsr_tables_processed=0,
            canonical_numeric_rows=0,
            context_row_count=0,
        )
        out = decide_forced_ocr(s, chars_per_page_scanned_like=1.0, min_text_layer_chars=1)
        assert out["forced"] is True
        assert "empty_docling_structure_and_empty_candidates" in out["reasons"]

    def test_docling_rows_but_no_canonical_forces(self) -> None:
        s = OcrPolicySignals(
            text_layer_chars=5000,
            pdf_page_count=5,
            docling_row_count_before_filtering=12,
            tsr_tables_processed=1,
            canonical_numeric_rows=0,
            context_row_count=3,
        )
        out = decide_forced_ocr(s, chars_per_page_scanned_like=1.0, min_text_layer_chars=1)
        assert out["forced"] is True
        assert "zero_numeric_rows_despite_docling_rows" in out["reasons"]

    def test_mapping_input_equivalent(self) -> None:
        out = decide_forced_ocr(
            {
                "text_layer_chars": 100,
                "pdf_page_count": 10,
                "docling_row_count_before_filtering": 0,
                "tsr_tables_processed": 0,
                "canonical_numeric_rows": 0,
                "context_row_count": 0,
            },
            chars_per_page_scanned_like=200.0,
        )
        assert out["forced"] is True


class TestApplyForceFullPageOcr:
    def test_noop_when_disabled(self) -> None:
        class PO:
            pass

        assert apply_force_full_page_ocr_to_pipeline(PO(), False) is False

    def test_sets_pipeline_attr_when_present(self) -> None:
        class PO:
            force_full_page_ocr = False

        po = PO()
        assert apply_force_full_page_ocr_to_pipeline(po, True) is True
        assert po.force_full_page_ocr is True

    def test_sets_nested_ocr_options_when_present(self) -> None:
        class OO:
            force_full_page_ocr = False

        class PO:
            ocr_options: OO

        po = PO()
        po.ocr_options = OO()
        assert apply_force_full_page_ocr_to_pipeline(po, True) is True
        assert po.ocr_options.force_full_page_ocr is True


def test_pdf_page_count_missing_file_returns_one(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pdf"
    assert pdf_page_count(missing) == 1
