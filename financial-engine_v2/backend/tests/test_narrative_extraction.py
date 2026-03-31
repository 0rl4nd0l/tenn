"""
Tests for Phase 1 narrative extraction changes:
1. ok_narrative_only status when Pass 1 fails but Pass 3b succeeds
2. announcement_type classification and persistence
3. simple_chunk_overlap produces overlapping chunks
4. _extract_risk_items now yields guidance_summary + material_changes
5. report_generator includes material_changes in risk block
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# 1. Ungated Pass 3b — ok_narrative_only status
# ---------------------------------------------------------------------------

def test_low_confidence_classifier_still_runs_narrative_extraction():
    """When Pass 1 returns low confidence, Pass 3b should still run and
    produce ok_narrative_only status if narrative fields are populated."""
    from app.services.multipass_extraction import run_multipass_extraction
    from app.services.docling_extract import StructuredDocument

    fake_doc = StructuredDocument(
        tables=[],
        sections=[
            {"text": "The company faces significant regulatory risk from new mining legislation.", "heading": False, "page": 0},
            {"text": "Management expects revenue growth of 15-20% driven by expansion into renewable energy.", "heading": False, "page": 1},
        ],
        extraction_method="pymupdf",
        page_count=2,
        docling_version="test",
    )

    # Pass 1: low confidence (simulates non-financial announcement)
    pass1_response = {
        "report_type": None,
        "period_end": None,
        "currency": "AUD",
        "scale": "unknown",
        "classifier_confidence": 0.25,
    }

    # Pass 3b: successful narrative extraction
    pass3b_response = {
        "risk_summary": "Significant regulatory risk from new mining legislation",
        "risk_bullets": ["New mining regulations may increase compliance costs"],
        "guidance_summary": "Revenue growth 15-20% from renewable energy expansion",
        "material_changes": None,
        "confidence_narrative": 0.8,
    }

    with patch("app.services.docling_extract.extract_structured", return_value=fake_doc), \
         patch("app.services.multipass_extraction._llm_json_call") as mock_llm:
        # First call = Pass 1, second call = Pass 3b
        mock_llm.side_effect = [pass1_response, pass3b_response]
        result = run_multipass_extraction("/tmp/fake.pdf", {"title": "Director Change", "ticker": "ABC"}, None)

    assert result.status == "ok_narrative_only"
    assert result.payload["risk_summary"] == "Significant regulatory risk from new mining legislation"
    assert result.payload["guidance_summary"] == "Revenue growth 15-20% from renewable energy expansion"
    assert "classifier_low_confidence" in result.error


def test_low_confidence_with_no_narrative_returns_failed():
    """When Pass 1 fails AND Pass 3b finds nothing, status should be 'failed'."""
    from app.services.multipass_extraction import run_multipass_extraction
    from app.services.docling_extract import StructuredDocument

    fake_doc = StructuredDocument(
        tables=[],
        sections=[{"text": "Page intentionally left blank.", "heading": False, "page": 0}],
        extraction_method="pymupdf",
        page_count=1,
        docling_version="test",
    )

    pass1_response = {
        "report_type": None, "period_end": None, "currency": "AUD",
        "scale": "unknown", "classifier_confidence": 0.1,
    }
    pass3b_response = {
        "risk_summary": None, "risk_bullets": None,
        "guidance_summary": None, "material_changes": None,
        "confidence_narrative": 0.1,
    }

    with patch("app.services.docling_extract.extract_structured", return_value=fake_doc), \
         patch("app.services.multipass_extraction._llm_json_call") as mock_llm:
        mock_llm.side_effect = [pass1_response, pass3b_response]
        result = run_multipass_extraction("/tmp/fake.pdf", {"title": "Empty doc"}, None)

    assert result.status == "failed"
    assert "classifier_low_confidence" in result.error


def test_low_confidence_skip_narrative_skips_pass3b():
    """When skip_narrative=True, even the fallback path should not call Pass 3b."""
    from app.services.multipass_extraction import run_multipass_extraction
    from app.services.docling_extract import StructuredDocument

    fake_doc = StructuredDocument(
        tables=[],
        sections=[{"text": "Some prose here.", "heading": False, "page": 0}],
        extraction_method="pymupdf",
        page_count=1,
        docling_version="test",
    )

    pass1_response = {
        "report_type": None, "period_end": None, "currency": "AUD",
        "scale": "unknown", "classifier_confidence": 0.2,
    }

    with patch("app.services.docling_extract.extract_structured", return_value=fake_doc), \
         patch("app.services.multipass_extraction._llm_json_call") as mock_llm:
        mock_llm.side_effect = [pass1_response]  # only Pass 1, no Pass 3b
        result = run_multipass_extraction(
            "/tmp/fake.pdf", {"title": "Test"}, None, skip_narrative=True,
        )

    assert result.status == "failed"
    # Only 1 LLM call (Pass 1), not 2
    assert mock_llm.call_count == 1


def test_narrative_only_payload_has_null_metrics():
    """ok_narrative_only should have all financial metrics as None."""
    from app.services.multipass_extraction import run_multipass_extraction, METRIC_FIELDS
    from app.services.docling_extract import StructuredDocument

    fake_doc = StructuredDocument(
        tables=[],
        sections=[{"text": "The board announces a new strategic partnership.", "heading": False, "page": 0}],
        extraction_method="pymupdf",
        page_count=1,
        docling_version="test",
    )

    pass1_response = {
        "report_type": None, "period_end": None, "currency": "AUD",
        "scale": "unknown", "classifier_confidence": 0.3,
    }
    pass3b_response = {
        "risk_summary": "Partnership introduces counterparty risk",
        "risk_bullets": None, "guidance_summary": None,
        "material_changes": "New strategic partnership announced",
        "confidence_narrative": 0.7,
    }

    with patch("app.services.docling_extract.extract_structured", return_value=fake_doc), \
         patch("app.services.multipass_extraction._llm_json_call") as mock_llm:
        mock_llm.side_effect = [pass1_response, pass3b_response]
        result = run_multipass_extraction("/tmp/fake.pdf", {"title": "Partnership"}, None)

    assert result.status == "ok_narrative_only"
    for m in METRIC_FIELDS:
        assert result.payload.get(m) is None, f"metric {m} should be None for narrative-only"


# ---------------------------------------------------------------------------
# 2. Pass 3b context window increased to 8K
# ---------------------------------------------------------------------------

def test_pass3b_uses_8k_context_window():
    """Pass 3b should concatenate up to 8000 chars of prose, not 4000."""
    from app.services.multipass_extraction import _run_pass3b_narrative_extractor

    # Create sections totalling ~6000 chars (would be truncated at old 4K limit)
    sections = [{"text": "A" * 3000}, {"text": "B" * 3000}]

    with patch("app.services.multipass_extraction._llm_json_call") as mock_llm:
        mock_llm.return_value = {
            "risk_summary": None, "risk_bullets": None,
            "guidance_summary": None, "material_changes": None,
            "confidence_narrative": 0.5,
        }
        _run_pass3b_narrative_extractor(sections, None)

    # The prompt should contain the full 6000 chars (not truncated to 4000)
    prompt_arg = mock_llm.call_args[0][0]
    assert "B" * 100 in prompt_arg, "Second section should be present (not truncated at 4K)"


# ---------------------------------------------------------------------------
# 3. announcement_type classification
# ---------------------------------------------------------------------------

def test_classify_announcement_financial_by_subtype():
    from app.services.announcement_importance import classify_announcement
    result = classify_announcement(
        title="Appendix 4C - Quarterly Cash Flow Report",
        doc_class="quarterly",
        doc_subtype="4C",
        pdf_excerpt=None,
    )
    assert result["label"] == "financial_performance"
    assert result["score"] >= 3  # structural hit


def test_classify_announcement_ops_by_title():
    from app.services.announcement_importance import classify_announcement
    result = classify_announcement(
        title="Quarterly Activities Report",
        doc_class="quarterly",
        doc_subtype="other",
        pdf_excerpt=None,
    )
    assert result["label"] in ("financial_performance", "operations_projects")


def test_classify_announcement_governance():
    from app.services.announcement_importance import classify_announcement
    result = classify_announcement(
        title="Appointment of Director",
        doc_class=None,
        doc_subtype=None,
        pdf_excerpt=None,
    )
    assert result["label"] == "management_and_governance"


def test_classify_announcement_investor_comms():
    from app.services.announcement_importance import classify_announcement
    result = classify_announcement(
        title="Investor Presentation - Annual General Meeting",
        doc_class=None,
        doc_subtype=None,
        pdf_excerpt=None,
    )
    assert result["label"] == "investor_communications"


def test_classify_announcement_other_fallback():
    from app.services.announcement_importance import classify_announcement
    result = classify_announcement(
        title="Miscellaneous Document",
        doc_class=None,
        doc_subtype=None,
        pdf_excerpt=None,
    )
    assert result["label"] == "other"


# ---------------------------------------------------------------------------
# 4. simple_chunk_overlap
# ---------------------------------------------------------------------------

def test_simple_chunk_overlap_produces_overlapping_chunks():
    from app.services.structured_chunking import simple_chunk_overlap
    text = "A" * 500 + "B" * 500 + "C" * 500  # 1500 chars total
    chunks = simple_chunk_overlap(text, max_chars=1000, overlap=100)

    assert len(chunks) == 2
    # Second chunk should start 100 chars before the end of the first
    # First chunk: 0..1000, second chunk: 900..1500
    assert chunks[1][:100] == chunks[0][-100:]


def test_simple_chunk_overlap_single_chunk():
    from app.services.structured_chunking import simple_chunk_overlap
    chunks = simple_chunk_overlap("short text", max_chars=1400)
    assert len(chunks) == 1
    assert chunks[0] == "short text"


def test_simple_chunk_overlap_empty():
    from app.services.structured_chunking import simple_chunk_overlap
    assert simple_chunk_overlap("") == []
    assert simple_chunk_overlap(None) == []


def test_simple_chunk_overlap_default_overlap():
    """Default overlap should be 150 chars (OVERLAP_CHARS constant)."""
    from app.services.structured_chunking import simple_chunk_overlap, OVERLAP_CHARS
    text = "X" * 3000
    chunks = simple_chunk_overlap(text, max_chars=1400)
    # With 1400 max and 150 overlap: chunk boundaries at 0-1400, 1250-2650, 2500-3000
    assert len(chunks) == 3
    assert OVERLAP_CHARS == 150


# ---------------------------------------------------------------------------
# 5. risk_module extracts guidance + material_changes
# ---------------------------------------------------------------------------

def test_extract_risk_items_includes_guidance_and_material_changes():
    from app.services.analysis.risk_module import _extract_risk_items

    risk_note = {
        "risk_summary": "Regulatory risk from new legislation",
        "risk_bullets": ["Mining tax increase", "Environmental compliance"],
        "guidance_summary": "Revenue growth 15-20% expected in FY26",
        "material_changes": "Acquired subsidiary in renewable sector",
    }
    items = _extract_risk_items(risk_note)

    source_types = {item["source_type"] for item in items}
    assert "risk_bullet" in source_types
    assert "risk_summary" in source_types
    assert "guidance_summary" in source_types
    assert "material_changes" in source_types
    assert len(items) == 5  # 2 bullets + 1 summary + 1 guidance + 1 material


def test_extract_risk_items_handles_missing_guidance():
    from app.services.analysis.risk_module import _extract_risk_items

    risk_note = {
        "risk_summary": "Some risk",
        "risk_bullets": [],
        "guidance_summary": None,
        "material_changes": "",
    }
    items = _extract_risk_items(risk_note)
    source_types = {item["source_type"] for item in items}
    assert "guidance_summary" not in source_types
    assert "material_changes" not in source_types
    assert len(items) == 1  # just risk_summary


# ---------------------------------------------------------------------------
# 6. report_generator includes material_changes in risk block
# ---------------------------------------------------------------------------

def test_format_risk_block_includes_material_changes():
    from app.services.analysis.report_generator import _format_risk_block

    risk_notes = [
        {
            "risk_summary": "Operational risk from supply chain disruption",
            "risk_bullets": ["Shipping delays"],
            "guidance_summary": "FY26 revenue guidance maintained at $2B",
            "material_changes": "Divested underperforming coal assets",
        }
    ]
    block = _format_risk_block(risk_notes)

    assert "Operational risk" in block
    assert "Shipping delays" in block
    assert "FY26 revenue guidance" in block
    assert "Divested underperforming coal assets" in block
    assert "Material changes:" in block


def test_format_risk_block_omits_empty_material_changes():
    from app.services.analysis.report_generator import _format_risk_block

    risk_notes = [
        {
            "risk_summary": "Some risk",
            "risk_bullets": [],
            "guidance_summary": None,
            "material_changes": "",
        }
    ]
    block = _format_risk_block(risk_notes)
    assert "Material changes:" not in block


# ---------------------------------------------------------------------------
# 7. Pipeline integration: announcement_type in Qdrant payload
# ---------------------------------------------------------------------------

def test_qdrant_payload_includes_announcement_type(monkeypatch):
    """process_document should include announcement_type in Qdrant point payload."""
    import uuid
    from app.services.pipeline import process_document
    from app.services.multipass_extraction import MultipassResult

    captured_points: list[dict] = []
    doc_id = uuid.uuid4()

    class DummyDoc:
        document_id = doc_id
        ticker = "XYZ"
        doc_class = "quarterly"
        doc_subtype = "4C"
        title = "Appendix 4C Quarterly Cash Flow"
        pdf_path = "/tmp/test.pdf"
        source_url = "https://example.com/test.pdf"
        announcement_type = None

    class DummyQuery:
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return DummyDoc()

    class DummySession:
        def query(self, model):
            return DummyQuery()
        def add(self, obj):
            pass
        def commit(self):
            pass
        def close(self):
            pass

    fake_result = MultipassResult(
        status="ok",
        payload={
            "period_type": "Q", "period_end": "2024-12-31", "period_start": "2024-10-01",
            "confidence_metrics": 0.9,
            "risk_summary": None, "risk_bullets": None,
            "guidance_summary": None, "material_changes": None,
            "confidence_narrative": 0.0, "provenance": {},
            "metrics": {"revenue": 1000000},
            "scale": "thousands", "currency": "AUD",
            "scale_validation": "pass",
        },
        sections=[{"text": "Test content for chunking into vectors", "heading": False}],
    )

    monkeypatch.setattr("app.services.pipeline.SessionLocal", lambda: DummySession())
    monkeypatch.setattr("app.services.pipeline.settings.enable_extraction", True)
    monkeypatch.setattr("app.services.pipeline.settings.enable_embeddings", True)
    monkeypatch.setattr("app.services.pipeline.settings.enable_qdrant", True)
    monkeypatch.setattr("app.services.pipeline.settings.qdrant_collection", "test_coll")
    monkeypatch.setattr("app.services.pipeline.run_multipass_extraction", lambda *a, **kw: fake_result)
    monkeypatch.setattr("app.services.pipeline._resolve_pdf_path", lambda p: p)

    def fake_embed(chunks, **kw):
        return [[0.1] * 768 for _ in chunks]
    monkeypatch.setattr("app.services.pipeline._embed_chunks", fake_embed)

    def fake_ensure(client, name, dim):
        pass
    monkeypatch.setattr("app.services.pipeline.ensure_collection", fake_ensure)

    def fake_delete(client, coll, doc_id_str):
        pass
    monkeypatch.setattr("app.services.pipeline.delete_points_for_document", fake_delete)

    def fake_upsert(client, coll, points):
        captured_points.extend(points)
        return {"written_points": len(points)}
    monkeypatch.setattr("app.services.pipeline.upsert_points", fake_upsert)

    monkeypatch.setattr("app.services.pipeline.validate_payload", lambda p: (True, None))

    process_document(doc_id)

    assert len(captured_points) >= 1
    payload = captured_points[0]["payload"]
    assert "announcement_type" in payload
    assert payload["announcement_type"] == "financial_performance"
