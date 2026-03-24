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


# ---------------------------------------------------------------------------
# Pass 3a — Period column disambiguation (B2)
# ---------------------------------------------------------------------------

def test_pass3a_prompt_contains_column_selection_instruction():
    """_PASS3A_PROMPT must instruct the LLM to select the period_end column."""
    from app.services.multipass_extraction import _PASS3A_PROMPT
    prompt_lower = _PASS3A_PROMPT.lower()
    assert "prior" in prompt_lower, "Prompt must explicitly mention prior-period columns"
    assert "comparative" in prompt_lower, "Prompt must explicitly mention comparative columns"
    assert "period_end" in _PASS3A_PROMPT or "{period_end}" in _PASS3A_PROMPT, (
        "Prompt must reference period_end for column selection"
    )


def test_pass3a_prompt_includes_period_end_for_column_selection():
    """The assembled prompt sent to the LLM must contain the period_end date
    and a column-selection instruction."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Income Statement",
        rows=[["", "H1 2025", "H1 2024"],
              ["Revenue", "485,630", "390,200"],
              ["EBIT", "31,284", "22,100"]],
        headers=["", "H1 2025", "H1 2024"],
    )
    labelled = {"cashflow_statement": None, "income_statement": table,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2025-06-30",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {"revenue": 485630, "ebit": 31284, "np_attributable": None,
                "period_col": "H1 2025",
                "pass3_confidence": 0.9, "row_refs": {}}

    captured_prompts = []
    def capture_llm_call(prompt, llm_client, max_tokens=512):
        captured_prompts.append(prompt)
        return mock_raw

    with patch("app.services.multipass_extraction._llm_json_call", side_effect=capture_llm_call):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert captured_prompts, "LLM must have been called"
    prompt = captured_prompts[0]
    assert "2025-06-30" in prompt, "period_end date must appear in the prompt for column selection"
    assert "prior" in prompt.lower() or "comparative" in prompt.lower(), (
        "Prompt must warn against prior-period column extraction"
    )
    assert "period_col" in results[0], (
        "period_col decision record must be propagated through to the result dict"
    )


# ---------------------------------------------------------------------------
# Docling adaptive timeout (B3)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pass 4 — net_debt derivation (B4)
# ---------------------------------------------------------------------------

def test_pass4_reconciler_derives_net_debt_from_total_debt():
    """Reconciler must derive net_debt = total_debt - cash_end when net_debt is null."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 500_000_000, "investing_cf": None, "financing_cf": None,
            "cash_end": 200_000_000, "capex": None,
            "pass3_confidence": 0.9, "row_refs": {},
        },
        {
            "_source": "balance_sheet",
            "net_debt": None, "total_debt": 800_000_000, "shares_outstanding": None,
            "pass3_confidence": 0.8, "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None, "risk_bullets": None,
        "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 600_000_000, (
        "net_debt must be derived as total_debt(800M) - cash_end(200M) = 600M"
    )
    assert "derived:balance_sheet" in payload["provenance"].get("net_debt", ""), (
        "provenance must record that net_debt was derived"
    )


def test_pass4_reconciler_skips_derivation_when_net_debt_already_extracted():
    """Explicitly extracted net_debt must not be overwritten by derivation."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 100_000_000, "investing_cf": None, "financing_cf": None,
            "cash_end": 50_000_000, "capex": None,
            "pass3_confidence": 0.9, "row_refs": {},
        },
        {
            "_source": "balance_sheet",
            "net_debt": 300_000_000, "total_debt": 999_000_000, "shares_outstanding": None,
            "pass3_confidence": 0.9, "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None, "risk_bullets": None,
        "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 300_000_000, (
        "Explicitly extracted net_debt(300M) must not be overwritten by total_debt(999M)-cash_end"
    )


def test_pass4_reconciler_skips_derivation_when_cash_end_missing():
    """Derivation must not run when cash_end is not available."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "balance_sheet",
            "net_debt": None, "total_debt": 500_000_000, "shares_outstanding": 100_000_000,
            "pass3_confidence": 0.7, "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None, "risk_bullets": None,
        "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None, (
        "net_debt must remain null when cash_end is unavailable — cannot derive safely"
    )


def test_compute_docling_timeout_floor():
    """Short PDFs must never drop below the 120s floor."""
    from app.services.docling_extract import _compute_docling_timeout
    # 10 pages × 4 = 40s — below the floor, so we expect 120s
    assert _compute_docling_timeout(10) == 120


def test_compute_docling_timeout_scales():
    """Mid-sized PDFs must scale proportionally when above the floor."""
    from app.services.docling_extract import _compute_docling_timeout
    # 50 pages × 4 = 200s — above floor, below cap
    assert _compute_docling_timeout(50) == 200


def test_compute_docling_timeout_cap():
    """Very large PDFs must not exceed the 300s ceiling."""
    from app.services.docling_extract import _compute_docling_timeout
    # 100 pages × 4 = 400s — exceeds cap
    assert _compute_docling_timeout(100) == 300


# ---------------------------------------------------------------------------
# Pass 2 — footnote table scoring guard (B5)
# ---------------------------------------------------------------------------

def test_pass2_header_bonus_beats_footnote_keyword_count():
    """
    An explicitly-labeled income statement must beat a footnote table that has
    more raw keyword matches, because the header bonus (+10) outweighs higher
    incidental keyword density in notes sections.

    Scenario: "Notes to the Financial Statements" table has 4 keyword matches
    (revenue, profit, ebit, net profit) from discussion of accounting policies.
    "Statement of Profit or Loss" table has only 2 raw matches but earns +10
    header bonus → total 12 vs 4. Statement wins.
    """
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    footnote_table = DoclingTable(
        page_number=10,
        caption="Notes to the Financial Statements",
        rows=[
            ["Note 3 — Revenue Recognition", ""],
            ["revenue is recognised on transfer of control", ""],
            ["profit attributable to ordinary shareholders", ""],
            ["ebit excludes lease finance costs", ""],
            ["net profit after tax allocated to members", ""],
        ],
        headers=["Description", ""],
    )
    statement_table = DoclingTable(
        page_number=4,
        caption="Statement of Profit or Loss",
        rows=[
            ["Revenue", "485,630"],
            ["Operating expenses", "(454,346)"],
        ],
        headers=["", "H1 FY26 $'000"],
    )

    result = _run_pass2_locator([footnote_table, statement_table])

    assert result["income_statement"] is statement_table, (
        "Explicitly-labeled income statement must win over footnote table "
        "even when footnote has higher raw keyword count. "
        f"Got: {result['income_statement'].caption!r}"
    )


# ---------------------------------------------------------------------------
# period_start derivation (B6)
# ---------------------------------------------------------------------------

def test_derive_period_start_annual():
    """Annual period: period_start = period_end − 12 months + 1 day."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2024, 6, 30), "A")
    assert result == date(2023, 7, 1), f"Expected 2023-07-01, got {result}"


def test_derive_period_start_half_year():
    """Half-year period: period_start = period_end − 6 months + 1 day."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2025, 12, 31), "H")
    assert result == date(2025, 7, 1), f"Expected 2025-07-01, got {result}"


def test_derive_period_start_quarterly():
    """Quarterly period: period_start = period_end − 3 months + 1 day."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2024, 9, 30), "Q")
    assert result == date(2024, 7, 1), f"Expected 2024-07-01, got {result}"


def test_derive_period_start_september_annual():
    """Annual period ending Sept 30 (e.g. NAB): period_start = Oct 1 prior year."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2024, 9, 30), "A")
    assert result == date(2023, 10, 1), f"Expected 2023-10-01, got {result}"


def test_derive_period_start_returns_none_for_missing_inputs():
    """None period_end or unrecognised period_type must return None — never guess."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    assert _derive_period_start(None, "A") is None
    assert _derive_period_start(date(2024, 12, 31), None) is None
    assert _derive_period_start(date(2024, 12, 31), "X") is None
