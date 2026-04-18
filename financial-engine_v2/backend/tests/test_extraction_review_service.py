from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.services import extraction_review as review

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency in restricted envs
    Image = None


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def test_build_review_item_includes_provenance_and_snippet(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "line_crop",
            "evidence_quality": "precise",
            "status": "ok",
            "image_path": "reports/extraction_review/snippets/test.png",
            "ascii_preview": "preview",
            "matched_text": "Revenue from contracts with customers",
            "page_number": 7,
            "reason": None,
        },
    )

    document = SimpleNamespace(
        document_id="doc-123",
        ticker="BHP",
        title="Annual Report",
        pdf_path=str(pdf_path),
    )
    run = SimpleNamespace(
        run_id="run-123",
        structured_json={
            "period_end": "2024-06-30",
            "period_type": "A",
            "currency": "AUD",
            "scale": "millions",
            "confidence_metrics": 0.92,
            "metrics": {"revenue": 12345.0},
            "provenance": {
                "revenue": "income_statement:page_7:Revenue from contracts with customers"
            },
            "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
        },
    )

    item = review.build_review_item(None, document, run, "revenue")

    assert item is not None
    assert item["metric_name"] == "revenue"
    assert item["document_id"] == "doc-123"
    assert item["page_number"] == 7
    assert item["metric_value"] == 12345.0
    assert item["matched_text"] == "Revenue from contracts with customers"
    assert item["evidence_quality"] == "precise"
    assert item["provenance_status"] == "precise"
    assert item["snippet"]["kind"] == "line_crop"
    assert item["snippet"]["evidence_quality"] == "precise"


def test_build_review_item_includes_method_provenance_and_gold_expected(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "gold.json").write_text(
        """
        {
          "document_id": "gold-qbe",
          "source_file": "data/asx/docs/QBE/report.pdf",
          "period_type": "H",
          "period_end": "2025-06-30",
          "currency": "USD",
          "scale": "millions",
          "metrics": {"revenue": 10875000000},
          "expected_trust": "trusted"
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(review, "REAL_GOLD_REVIEW_DIR", gold_dir)
    review._load_real_gold_by_source.cache_clear()
    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "text_only",
            "evidence_quality": "missing",
            "status": "ok",
            "image_path": None,
            "ascii_preview": None,
            "matched_text": "Revenue",
            "page_number": 7,
            "reason": None,
        },
    )

    document = SimpleNamespace(
        document_id="doc-123",
        ticker="QBE",
        title="Half Year Report",
        pdf_path="data/asx/docs/QBE/report.pdf",
    )
    run = SimpleNamespace(
        run_id="run-123",
        structured_json={
            "period_end": "2025-06-30",
            "period_type": "H",
            "currency": "USD",
            "scale": "millions",
            "confidence_metrics": 0.88,
            "metrics": {"revenue": 107.0},
            "provenance": {"revenue": "income_statement:page_7:Revenue"},
            "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
            "_method_provenance": {
                "requested_method": "docling",
                "actual_method": "docling",
                "strict_method": True,
                "parser_id": "docling",
                "model_id": "qwen2.5-14b-instruct",
                "runtime_id": "http://127.0.0.1:8001",
                "fallback_used": False,
                "error_stage": None,
                "warnings": [],
            },
        },
    )

    item = review.build_review_item(None, document, run, "revenue")

    assert item is not None
    assert item["requested_method"] == "docling"
    assert item["actual_method"] == "docling"
    assert item["method_provenance"] == "docling"
    assert item["strict_method"] is True
    assert item["gold_document_id"] == "gold-qbe"
    assert item["gold_expected_trust"] == "trusted"
    assert item["expected_value"] == 10875000000


def test_build_review_item_exposes_optional_visual_verification_fields(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "line_crop",
            "evidence_quality": "precise",
            "status": "ok",
            "image_path": "reports/extraction_review/snippets/test.png",
            "image_url": "/api/extraction-review/snippets/test.png",
            "ascii_preview": None,
            "matched_text": "Net cash from operating activities",
            "page_number": 3,
            "reason": None,
        },
    )

    document = SimpleNamespace(
        document_id="doc-123",
        ticker="BHP",
        title="Quarterly Report",
        pdf_path=str(pdf_path),
    )
    run = SimpleNamespace(
        run_id="run-456",
        structured_json={
            "period_end": "2024-09-30",
            "period_type": "Q",
            "period_col": "Sep 2024",
            "metrics": {"operating_cf": 321.0},
            "row_refs": {"operating_cf": "Net cash from operating activities"},
            "provenance": {
                "operating_cf": "cashflow_statement:page_3:Net cash from operating activities"
            },
            "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
            "_method_provenance": {"actual_method": "docling"},
        },
    )

    item = review.build_review_item(None, document, run, "operating_cf")

    assert item is not None
    assert item["image_url"] == "/api/extraction-review/snippets/test.png"
    assert item["image_path"] == "reports/extraction_review/snippets/test.png"
    assert item["evidence_quality"] == "precise"
    assert item["row_refs"] == {"operating_cf": "Net cash from operating activities"}
    assert item["table_type"] == "cashflow_statement"
    assert item["period_col"] == "Sep 2024"


def test_build_review_item_maps_real_gold_operating_cash_flow_alias(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "gold.json").write_text(
        """
        {
          "document_id": "gold-qbe",
          "source_file": "data/asx/docs/QBE/report.pdf",
          "period_type": "H",
          "period_end": "2025-06-30",
          "currency": "USD",
          "scale": "millions",
          "metrics": {"operating_cash_flow": 1756000000},
          "expected_trust": "trusted"
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(review, "REAL_GOLD_REVIEW_DIR", gold_dir)
    review._load_real_gold_by_source.cache_clear()
    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "line_crop",
            "evidence_quality": "precise",
            "status": "ok",
            "image_path": None,
            "ascii_preview": None,
            "matched_text": "Net cash from operating activities",
            "page_number": 3,
            "reason": None,
        },
    )

    document = SimpleNamespace(
        document_id="doc-123",
        ticker="QBE",
        title="Half Year Report",
        pdf_path="data/asx/docs/QBE/report.pdf",
    )
    run = SimpleNamespace(
        run_id="run-456",
        status="ok_low_confidence",
        structured_json={
            "period_end": "2025-06-30",
            "period_type": "H",
            "metrics": {"operating_cf": 1756.0},
            "provenance": {
                "operating_cf": "cashflow_statement:page_3:Net cash from operating activities"
            },
            "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
        },
    )

    item = review.build_review_item(None, document, run, "operating_cf")

    assert item is not None
    assert item["gold_document_id"] == "gold-qbe"
    assert item["expected_value"] == 1756000000


def test_create_review_session_from_payload_reuses_existing_review_schema(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(review, "SESSIONS_ROOT", tmp_path / "sessions")

    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "line_crop",
            "evidence_quality": "precise",
            "status": "ok",
            "image_path": "reports/extraction_review/snippets/test.png",
            "image_url": "/api/extraction-review/snippets/test.png",
            "ascii_preview": "preview",
            "matched_text": "Revenue from contracts with customers",
            "page_number": 7,
            "reason": None,
        },
    )

    session = review.create_review_session_from_payload(
        document_id="gold-doc-1",
        ticker="QBE",
        title="QBE Report",
        pdf_path=str(pdf_path),
        status="ok_low_confidence",
        payload={
            "period_end": "2025-06-30",
            "period_type": "H",
            "currency": "USD",
            "scale": "millions",
            "confidence_metrics": 0.42,
            "metrics": {"revenue": 10875.0},
            "provenance": {
                "revenue": "income_statement:page_7:Revenue from contracts with customers"
            },
            "_method_provenance": {
                "requested_method": "docling",
                "actual_method": "docling",
                "strict_method": True,
            },
        },
        run_id="real-gold-qbe-review",
    )

    assert session["session_status"] == "real_gold_eval"
    assert session["diagnostics"]["code"] == "real_gold_eval"
    assert session["document_ids"] == ["gold-doc-1"]
    assert session["run_ids"] == ["real-gold-qbe-review"]
    assert session["summary"]["total"] == 1
    assert session["items"][0]["run_id"] == "real-gold-qbe-review"
    assert session["items"][0]["image_url"] == "/api/extraction-review/snippets/test.png"


def test_create_review_session_from_payload_persists_round_trip_session(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    sessions_root = tmp_path / "sessions"
    monkeypatch.setattr(review, "SESSIONS_ROOT", sessions_root)

    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "line_crop",
            "evidence_quality": "precise",
            "status": "ok",
            "image_path": "reports/extraction_review/snippets/test.png",
            "image_url": "/api/extraction-review/snippets/test.png",
            "ascii_preview": "preview",
            "matched_text": "Revenue from contracts with customers",
            "page_number": 7,
            "reason": None,
        },
    )

    session = review.create_review_session_from_payload(
        document_id="gold-doc-2",
        ticker="QBE",
        title="QBE Report",
        pdf_path=str(pdf_path),
        status="ok_low_confidence",
        payload={
            "period_end": "2025-06-30",
            "period_type": "H",
            "currency": "USD",
            "scale": "millions",
            "confidence_metrics": 0.42,
            "metrics": {"revenue": 10875.0},
            "provenance": {
                "revenue": "income_statement:page_7:Revenue from contracts with customers"
            },
        },
        run_id="real-gold-qbe-roundtrip",
        diagnostics={
            "code": "real_gold_eval",
            "message": "Generated from /api/extraction-eval/real-gold.",
            "expected_trust": "trusted",
        },
    )

    loaded = review.load_review_session(session["session_id"])

    assert loaded["session_id"] == session["session_id"]
    assert loaded["session_status"] == "real_gold_eval"
    assert loaded["diagnostics"]["expected_trust"] == "trusted"
    assert loaded["run_ids"] == ["real-gold-qbe-roundtrip"]
    assert loaded["summary"]["total"] == 1
    assert loaded["documents"][0]["review_ready"] is True
    assert loaded["documents"][0]["reason"] == "reviewable"
    assert loaded["items"][0]["metric_name"] == "revenue"
    assert (
        sessions_root / f"{session['session_id']}.json"
    ).exists()


def test_build_metric_snippet_returns_text_fallback_when_bbox_unavailable(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "missing.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        review,
        "_parse_bbox_lines",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("pdftotext unavailable")
        ),
    )

    snippet = review.build_metric_snippet(
        item_id="run-1:revenue",
        pdf_path=pdf_path,
        page_number=5,
        evidence_text="Revenue",
    )

    assert snippet["kind"] == "text_only"
    assert snippet["evidence_quality"] == "missing"
    assert snippet["status"] == "bbox_unavailable"
    assert snippet["matched_text"] == "Revenue"
    assert "pdftotext unavailable" in snippet["reason"]


def test_build_review_item_marks_page_preview_only_as_approximate(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "page_preview",
            "evidence_quality": "approximate",
            "status": "ok",
            "image_path": "reports/extraction_review/snippets/page.png",
            "image_url": "/api/extraction-review/snippets/page.png",
            "ascii_preview": None,
            "matched_text": "unknown",
            "page_number": 11,
            "reason": None,
        },
    )

    document = SimpleNamespace(
        document_id="doc-123",
        ticker="BHP",
        title="Quarterly Report",
        pdf_path=str(pdf_path),
    )
    run = SimpleNamespace(
        run_id="run-789",
        structured_json={
            "period_end": "2024-09-30",
            "period_type": "Q",
            "metrics": {"cash": 500.0},
            "provenance": {"cash": "balance_sheet:page_11:unknown"},
            "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
            "_method_provenance": {"actual_method": "docling"},
        },
    )

    item = review.build_review_item(None, document, run, "cash")

    assert item is not None
    assert item["image_url"] == "/api/extraction-review/snippets/page.png"
    assert item["evidence_quality"] == "approximate"
    assert item["snippet"]["evidence_quality"] == "approximate"


def test_evidence_quality_for_snippet_marks_page_preview_as_approximate() -> None:
    snippet = {
        "kind": "page_preview",
        "image_path": "reports/extraction_review/snippets/page.png",
        "matched_text": "unknown",
    }

    assert review._evidence_quality_for_snippet(snippet) == "approximate"


def test_evidence_quality_for_snippet_marks_full_page_with_bbox_as_precise() -> None:
    snippet = {
        "kind": "page_preview",
        "image_url": "/api/extraction-review/snippets/page.png",
        "matched_text": "Revenue from contracts with customers",
        "bbox": [10, 10, 100, 20],
    }

    assert review._evidence_quality_for_snippet(snippet) == "precise"


def test_evidence_quality_for_snippet_marks_missing_image_as_missing() -> None:
    snippet = {
        "kind": "text_only",
        "image_path": None,
        "image_url": None,
        "matched_text": "Revenue",
    }

    assert review._evidence_quality_for_snippet(snippet) == "missing"


def test_create_review_session_returns_diagnostics_for_zero_metric_run(
    monkeypatch, tmp_path
) -> None:
    session = _make_session()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    doc_id = uuid4()
    run_id = uuid4()

    try:
        session.add(
            Document(
                document_id=doc_id,
                ticker="BHP",
                exchange="ASX",
                doc_class="annual",
                doc_subtype="report",
                published_at=None,
                period_end=None,
                title="Annual Report",
                source_url=f"https://example.com/{doc_id}",
                pdf_path=str(pdf_path),
                pdf_sha256="abc123",
            )
        )
        session.add(
            ExtractionRun(
                run_id=run_id,
                document_id=doc_id,
                extractor_version="v1",
                model_name="qwen-test",
                prompt_hash="hash-1",
                status="ok",
                confidence_overall=0.7,
                structured_json={
                    "period_end": "2024-06-30",
                    "period_type": "A",
                    "currency": "AUD",
                    "scale": "millions",
                    "confidence_metrics": 0.7,
                    "metrics": {"revenue": None, "ebit": None},
                    "provenance": {},
                    "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
                    "_method_provenance": {
                        "requested_method": "docling",
                        "actual_method": "docling",
                        "strict_method": True,
                    },
                },
            )
        )
        session.commit()

        review_session = review.create_review_session(
            session,
            [],
            run_ids=[str(run_id)],
        )

        assert review_session["items"] == []
        assert review_session["documents"][0]["review_ready"] is False
        assert review_session["documents"][0]["reason"] == "persisted_but_no_metrics"
        assert review_session["documents"][0]["metrics_count"] == 0
        assert review_session["documents"][0]["requested_method"] == "docling"
    finally:
        session.close()


@pytest.mark.skipif(Image is None, reason="Pillow not installed")
def test_build_metric_snippet_creates_line_crop_with_ascii_preview(
    monkeypatch, tmp_path
) -> None:
    page_png = tmp_path / "page.png"
    Image.new("RGB", (320, 180), color=(255, 255, 255)).save(page_png)
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        review,
        "_parse_bbox_lines",
        lambda *_args, **_kwargs: [
            {
                "page": 3,
                "line_no_on_page": 12,
                "text": "Revenue from contracts with customers",
                "bbox": [40.0, 50.0, 180.0, 70.0],
            }
        ],
    )
    monkeypatch.setattr(
        review, "_render_page_image", lambda *_args, **_kwargs: page_png
    )
    monkeypatch.setattr(review, "SNIPPETS_ROOT", tmp_path / "snippets")

    snippet = review.build_metric_snippet(
        item_id="run-1:revenue",
        pdf_path=pdf_path,
        page_number=3,
        evidence_text="Revenue from contracts with customers",
    )

    assert snippet["kind"] == "page_preview"
    assert snippet["evidence_quality"] == "precise"
    assert snippet["status"] == "ok"
    assert snippet["image_name"].endswith("_page_highlight.png")
    assert snippet["bbox"] == [40.0, 50.0, 180.0, 70.0]


@pytest.mark.skipif(Image is None, reason="Pillow not installed")
def test_build_metric_snippet_renders_real_pdf_without_poppler(
    monkeypatch, tmp_path
) -> None:
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 120), "Revenue from contracts with customers", fontsize=14)
    document.save(pdf_path)
    document.close()

    monkeypatch.setattr(review, "SNIPPETS_ROOT", tmp_path / "snippets")
    snippet = review.build_metric_snippet(
        item_id="run-1:revenue",
        pdf_path=pdf_path,
        page_number=1,
        evidence_text="Revenue from contracts with customers",
    )

    assert snippet["status"] == "ok"
    assert snippet["kind"] == "page_preview"
    assert snippet["bbox"] is not None
    assert snippet["evidence_quality"] == "precise"
    assert snippet["image_path"]
    assert snippet["image_url"]
    assert snippet["matched_text"]
    output_path = review.PROJECT_ROOT / str(snippet["image_path"])
    assert output_path.exists()


def test_submit_review_decision_updates_wrong_queue_snapshot(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(review, "SESSIONS_ROOT", tmp_path / "sessions")
    monkeypatch.setattr(
        review, "ERROR_QUEUE_PATH", tmp_path / "wrong_metric_queue.json"
    )

    session = {
        "session_id": "session-1",
        "items": [
            {
                "item_id": "run-1:revenue",
                "document_id": "doc-1",
                "ticker": "BHP",
                "metric_name": "revenue",
                "extracted_value": 123.0,
                "page_number": 7,
                "review_status": "pending",
                "reviewed_at": None,
                "expected_value": None,
                "reviewer_note": "",
                "evidence_reference": "income_statement:page_7:Revenue",
                "file_path": "data/asx/docs/BHP/report.pdf",
            }
        ],
    }
    review.save_review_session(session)

    wrong = review.submit_review_decision(
        "session-1",
        item_id="run-1:revenue",
        status="wrong",
        expected_value="125.0",
        reviewer_note="Column shifted",
    )
    queue = review.get_error_queue()

    assert wrong["item"]["review_status"] == "wrong"
    assert queue["count"] == 1
    assert queue["items"][0]["expected_value"] == "125.0"
    assert queue["items"][0]["reviewer_note"] == "Column shifted"

    review.submit_review_decision(
        "session-1",
        item_id="run-1:revenue",
        status="approved",
        reviewer_note="fixed on re-check",
    )
    queue_after = review.get_error_queue()
    assert queue_after["count"] == 0


def test_create_review_session_uses_requested_run_id(monkeypatch, tmp_path) -> None:
    session = _make_session()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    doc_id = uuid4()
    older_run_id = uuid4()
    newer_run_id = uuid4()

    monkeypatch.setattr(
        review,
        "build_metric_snippet",
        lambda **_: {
            "kind": "text_only",
            "status": "ok",
            "image_path": None,
            "ascii_preview": None,
            "matched_text": "Revenue",
            "page_number": 5,
            "reason": None,
        },
    )

    try:
        session.add(
            Document(
                document_id=doc_id,
                ticker="BHP",
                exchange="ASX",
                doc_class="annual",
                doc_subtype="report",
                published_at=None,
                period_end=None,
                title="Annual Report",
                source_url=f"https://example.com/{doc_id}",
                pdf_path=str(pdf_path),
                pdf_sha256="abc123",
            )
        )
        session.add_all(
            [
                ExtractionRun(
                    run_id=older_run_id,
                    document_id=doc_id,
                    extractor_version="v1",
                    model_name="qwen-old",
                    prompt_hash="hash-1",
                    status="ok",
                    confidence_overall=0.7,
                    structured_json={
                        "period_end": "2024-06-30",
                        "period_type": "A",
                        "currency": "AUD",
                        "scale": "millions",
                        "confidence_metrics": 0.7,
                        "metrics": {"revenue": 111.0},
                        "provenance": {"revenue": "income_statement:page_5:Revenue"},
                        "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
                    },
                ),
                ExtractionRun(
                    run_id=newer_run_id,
                    document_id=doc_id,
                    extractor_version="v2",
                    model_name="qwen-new",
                    prompt_hash="hash-2",
                    status="ok",
                    confidence_overall=0.9,
                    structured_json={
                        "period_end": "2024-06-30",
                        "period_type": "A",
                        "currency": "AUD",
                        "scale": "millions",
                        "confidence_metrics": 0.9,
                        "metrics": {"revenue": 222.0},
                        "provenance": {"revenue": "income_statement:page_5:Revenue"},
                        "_reproducibility": {"resolved_pdf_path": str(pdf_path)},
                    },
                ),
            ]
        )
        session.commit()

        review_session = review.create_review_session(
            session,
            [],
            run_ids=[str(older_run_id)],
        )

        assert review_session["run_ids"] == [str(older_run_id)]
        assert review_session["documents"][0]["run_id"] == str(older_run_id)
        assert review_session["items"][0]["run_id"] == str(older_run_id)
        assert review_session["items"][0]["extracted_value"] == 111.0
    finally:
        session.close()


def test_list_review_runs_returns_recent_runs_for_ticker(tmp_path) -> None:
    session = _make_session()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    bhp_doc_id = uuid4()
    rio_doc_id = uuid4()
    bhp_run_id = uuid4()
    rio_run_id = uuid4()

    try:
        session.add_all(
            [
                Document(
                    document_id=bhp_doc_id,
                    ticker="BHP",
                    exchange="ASX",
                    doc_class="annual",
                    doc_subtype="report",
                    published_at=None,
                    period_end=None,
                    title="BHP Annual Report",
                    source_url=f"https://example.com/{bhp_doc_id}",
                    pdf_path=str(pdf_path),
                    pdf_sha256="bhp123",
                ),
                Document(
                    document_id=rio_doc_id,
                    ticker="RIO",
                    exchange="ASX",
                    doc_class="quarterly",
                    doc_subtype="cashflow",
                    published_at=None,
                    period_end=None,
                    title="RIO Quarterly",
                    source_url=f"https://example.com/{rio_doc_id}",
                    pdf_path=str(pdf_path),
                    pdf_sha256="rio123",
                ),
                ExtractionRun(
                    run_id=bhp_run_id,
                    document_id=bhp_doc_id,
                    extractor_version="v1",
                    model_name="qwen-bhp",
                    prompt_hash="hash-bhp",
                    status="ok_low_confidence",
                    confidence_overall=0.42,
                    structured_json={"metrics": {"revenue": 111.0, "net_debt": None}},
                ),
                ExtractionRun(
                    run_id=rio_run_id,
                    document_id=rio_doc_id,
                    extractor_version="v1",
                    model_name="qwen-rio",
                    prompt_hash="hash-rio",
                    status="failed",
                    confidence_overall=None,
                    error="bad extraction",
                    structured_json={"metrics": {"revenue": 333.0}},
                ),
            ]
        )
        session.commit()

        payload = review.list_review_runs(session, ticker="BHP", limit=10)

        assert payload["ticker"] == "BHP"
        assert payload["count"] == 1
        assert payload["items"][0]["run_id"] == str(bhp_run_id)
        assert payload["items"][0]["metrics_count"] == 1
        assert payload["items"][0]["model_name"] == "qwen-bhp"
    finally:
        session.close()
