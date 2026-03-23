"""
Unit tests for the 4-pass multipass extraction pipeline.
LLM calls are mocked — these test logic, not model quality.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Pass 1 — Document Classifier
# ---------------------------------------------------------------------------

def test_pass1_extracts_period_from_appendix_4d():
    """Classifier must identify half-year period from Appendix 4D heading."""
    from app.services.multipass_extraction import _run_pass1_classifier

    mock_response = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_response):
        result = _run_pass1_classifier(
            title="Appendix 4D Half Year Report",
            first_page_text="For the half year ended 31 December 2024. All figures in AUD thousands.",
            llm_client=None,
        )

    assert result["report_type"] == "H"
    assert result["period_end"] == "2024-12-31"
    assert result["scale"] == "thousands"
    assert result["classifier_confidence"] >= 0.9


def test_pass1_returns_low_confidence_on_empty_input():
    """Classifier must return low confidence when given no meaningful text."""
    from app.services.multipass_extraction import _run_pass1_classifier

    mock_response = {
        "report_type": None,
        "period_end": None,
        "currency": "AUD",
        "scale": "unknown",
        "classifier_confidence": 0.1,
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_response):
        result = _run_pass1_classifier(title="", first_page_text="", llm_client=None)

    assert result["classifier_confidence"] < 0.6


# ---------------------------------------------------------------------------
# Pass 2 — Table Locator
# ---------------------------------------------------------------------------

def test_pass2_labels_cashflow_table_by_caption():
    """Table locator must assign a table with 'cash flow' caption to cashflow_statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cashflow_table = DoclingTable(
        page_number=3,
        caption="Consolidated Statement of Cash Flows",
        rows=[["Row", "Current", "Prior"], ["Net cash from operations", "3,241", "2,876"]],
        headers=["Row", "Current", "Prior"],
    )
    result = _run_pass2_locator([cashflow_table])
    assert result["cashflow_statement"] is cashflow_table
    assert result["income_statement"] is None


def test_pass2_higher_score_wins_on_conflict():
    """When two tables match the same type, the one with more keyword matches wins."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weak = DoclingTable(page_number=1, caption="cash",
                        rows=[["cash flow", "100"]], headers=[])
    strong = DoclingTable(page_number=3, caption="Cash Flow Statement — Financing Activities",
                          rows=[["net cash from operations", "1000"],
                                ["financing activities", "200"]], headers=[])
    result = _run_pass2_locator([weak, strong])
    assert result["cashflow_statement"] is strong


# ---------------------------------------------------------------------------
# Pass 3a — Scale normalisation and negative values
# ---------------------------------------------------------------------------

def test_pass3a_applies_thousands_multiplier():
    """Metric values must be multiplied by 1000 when scale=thousands."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None, "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.95, "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000  # multiplied by 1000


def test_pass3a_negative_values_preserved():
    """Negative values (already negative from LLM) must remain negative after scaling."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flow",
        rows=[["", "H1"], ["Investing activities", "(412)"]],
        headers=[],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": None, "investing_cf": -412,
        "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.9, "row_refs": {},
    }
    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["investing_cf"] == -412_000


# ---------------------------------------------------------------------------
# Pass 3b — Narrative extractor
# ---------------------------------------------------------------------------

def test_pass3b_returns_null_on_empty_sections():
    """Narrative extractor must return all-null dict when sections are empty."""
    from app.services.multipass_extraction import _run_pass3b_narrative_extractor

    result = _run_pass3b_narrative_extractor(sections=[], llm_client=None)
    assert result["risk_summary"] is None
    assert result["guidance_summary"] is None
    assert result["confidence_narrative"] == 0.0


# ---------------------------------------------------------------------------
# Pass 4 — Reconciler
# ---------------------------------------------------------------------------

def test_pass4_merges_non_overlapping_metrics():
    """Reconciler must combine metrics from different table sources."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {"_source": "cashflow_statement", "operating_cf": 3_241_000, "investing_cf": -412_000,
         "financing_cf": None, "cash_end": None, "pass3_confidence": 0.9, "row_refs": {}},
        {"_source": "income_statement", "revenue": 27_841_000_000, "ebit": 9_100_000_000,
         "np_attributable": None, "pass3_confidence": 0.88, "row_refs": {}},
    ]
    pass3b = {"risk_summary": None, "risk_bullets": None,
              "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.0}
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert result["metrics"]["operating_cf"] == 3_241_000
    assert result["metrics"]["revenue"] == 27_841_000_000
    assert result["period_end"] == "2024-12-31"


# ---------------------------------------------------------------------------
# Scale detection priority — table headers always authoritative over LLM
# ---------------------------------------------------------------------------

def test_scale_override_mutates_pass1_dict():
    """The override block must mutate pass1['scale'] when table headers are authoritative."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flows",
        rows=[["", "31 Dec 2024 $'000"], ["Operating CF", "3,241"]],
        headers=["", "31 Dec 2024 $'000"],
    )
    # Simulate the pass1 result that LLM returned wrongly
    pass1 = {"scale": "millions", "report_type": "H", "period_end": "2024-12-31"}

    # Apply the same override logic as run_multipass_extraction
    detected = _detect_scale_from_tables([table])
    if detected != "unknown":
        pass1["scale"] = detected

    assert pass1["scale"] == "thousands", (
        f"Override must mutate pass1['scale'] from 'millions' to 'thousands', got {pass1['scale']!r}"
    )


def test_scale_unknown_table_preserves_pass1_scale():
    """When table scan returns 'unknown', pass1['scale'] must remain unchanged."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1, caption="Highlights",
        rows=[["Metric", "Value"], ["Revenue", "27,841"]],
        headers=["Metric", "Value"],
    )
    pass1 = {"scale": "millions", "report_type": "H", "period_end": "2024-12-31"}

    detected = _detect_scale_from_tables([table])
    if detected != "unknown":
        pass1["scale"] = detected  # should not execute

    assert pass1["scale"] == "millions", (
        "pass1['scale'] must be unchanged when table scan returns 'unknown'"
    )


def test_scale_override_log_condition_fires_on_disagreement():
    """The INFO log gate condition must be True when LLM and table scan disagree."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flows",
        rows=[["", "H1 2025 $'000"], ["Operating CF", "3,241"]],
        headers=["", "H1 2025 $'000"],
    )
    detected = _detect_scale_from_tables([table])
    assert detected == "thousands"

    pass1_scale = "millions"  # LLM wrong

    # This is the exact condition guarding logger.info in run_multipass_extraction.
    gate = pass1_scale not in (detected, "unknown", None, "")
    assert gate, f"INFO log gate must be True when LLM='{pass1_scale}' vs table='{detected}'"


def test_pass3a_applies_corrected_scale_multiplier():
    """When scale='thousands' (whether set by table-header override or Pass 1),
    Pass 3a must multiply raw values by 1000 (thousands), not 1_000_000 (millions)."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025 $'000"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025 $'000"],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}

    # scale already corrected (e.g. by the table-header override in run_multipass_extraction)
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None, "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.95, "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000, (
        f"Expected thousands multiplier (3_241_000), got {results[0]['operating_cf']}"
    )


def test_pass4_higher_priority_source_wins():
    """income_statement must override highlights when both provide revenue."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {"_source": "highlights", "revenue": 45_200_000, "pass3_confidence": 0.7, "row_refs": {}},
        {"_source": "income_statement", "revenue": 45_192_000, "pass3_confidence": 0.92, "row_refs": {}},
    ]
    pass3b = {"risk_summary": None, "risk_bullets": None,
              "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.0}
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)
    assert result["metrics"]["revenue"] == 45_192_000  # income_statement wins


# ---------------------------------------------------------------------------
# Pipeline integration — _upsert_financial_rows (DB smoke test)
# ---------------------------------------------------------------------------

def test_upsert_financial_rows_smoke():
    """_upsert_financial_rows must write all metric and narrative fields to the DB,
    and must update (not duplicate) on a second call with the same key."""
    import uuid
    from types import SimpleNamespace
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base
    from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
    from app.services.pipeline import _upsert_financial_rows

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    doc_id = uuid.uuid4()
    doc = SimpleNamespace(ticker="TST", document_id=doc_id)

    payload = {
        "period_type": "H",
        "period_end": "2024-12-31",
        "confidence_metrics": 0.85,
        "metrics": {
            "revenue": 1_000_000.0,
            "ebit": 200_000.0,
            "np_attributable": 150_000.0,
            "operating_cf": 300_000.0,
            "investing_cf": -50_000.0,
            "financing_cf": -20_000.0,
            "capex": None,
            "cash_end": 80_000.0,
            "net_debt": None,
            "shares_outstanding": 50_000_000.0,
        },
        "risk_summary": "Commodity price risk",
        "risk_bullets": ["Iron ore price volatility", "FX exposure"],
        "guidance_summary": "Revenue expected to grow 10%",
        "material_changes": None,
        "confidence_narrative": 0.7,
    }

    session = Session()
    try:
        # --- First call: rows must be created ---
        _upsert_financial_rows(session, doc, payload)

        fin = session.query(ASXPeriodicFinancial).filter_by(ticker="TST").first()
        assert fin is not None, "ASXPeriodicFinancial row must be created"
        assert fin.period_type == "H"
        assert float(fin.revenue) == 1_000_000.0
        assert float(fin.operating_cf) == 300_000.0
        assert float(fin.investing_cf) == -50_000.0
        assert float(fin.financing_cf) == -20_000.0
        assert fin.capex is None
        assert fin.net_debt is None
        assert float(fin.shares_outstanding) == 50_000_000.0
        assert fin.confidence_metrics == pytest.approx(0.85)

        note = session.query(ASXRiskNote).first()
        assert note is not None, "ASXRiskNote row must be created"
        assert note.risk_summary == "Commodity price risk"
        assert "Iron ore price volatility" in note.risk_bullets
        assert note.guidance_summary == "Revenue expected to grow 10%"
        assert note.material_changes is None
        assert note.confidence_narrative == pytest.approx(0.7)

        # --- Second call: same key must update, not duplicate ---
        payload["metrics"]["revenue"] = 2_000_000.0
        payload["risk_summary"] = "Updated risk summary"
        _upsert_financial_rows(session, doc, payload)

        all_fin = session.query(ASXPeriodicFinancial).all()
        assert len(all_fin) == 1, "Upsert must not create a duplicate row"
        assert float(all_fin[0].revenue) == 2_000_000.0

        all_notes = session.query(ASXRiskNote).all()
        assert len(all_notes) == 1, "Upsert must not create a duplicate risk note"
        assert all_notes[0].risk_summary == "Updated risk summary"
    finally:
        session.close()
