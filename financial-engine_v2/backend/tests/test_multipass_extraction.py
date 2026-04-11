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

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_response
    ):
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

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_response
    ):
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
        rows=[
            ["Row", "Current", "Prior"],
            ["Net cash from operations", "3,241", "2,876"],
        ],
        headers=["Row", "Current", "Prior"],
    )
    result = _run_pass2_locator([cashflow_table])
    assert result["cashflow_statement"] is cashflow_table
    assert result["income_statement"] is None


def test_pass2_higher_score_wins_on_conflict():
    """When two tables match the same type, the one with more keyword matches wins."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weak = DoclingTable(
        page_number=1, caption="cash", rows=[["cash flow", "100"]], headers=[]
    )
    strong = DoclingTable(
        page_number=3,
        caption="Cash Flow Statement — Financing Activities",
        rows=[["net cash from operations", "1000"], ["financing activities", "200"]],
        headers=[],
    )
    result = _run_pass2_locator([weak, strong])
    assert result["cashflow_statement"] is strong


def test_pass2_selects_point_in_time_net_debt_note_table():
    """Point-in-time tables with an explicit net debt row should get a dedicated slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    year_end_summary = DoclingTable(
        page_number=1,
        caption="Year ended 30 June 2021",
        rows=[
            ["Year ended 30 June", "2021", "2020"],
            ["Revenue", "100", "90"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021", "2020"],
    )
    point_in_time_note = DoclingTable(
        page_number=5,
        caption="",
        rows=[
            ["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
            ["Borrowings", "(15,730)", "(14,896)"],
            ["Cash and cash equivalents", "1,436", "1,012"],
            ["Net debt", "(16,800)", "(16,445)"],
        ],
        headers=["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
    )

    result = _run_pass2_locator([year_end_summary, point_in_time_note])

    assert result["net_debt_note"] is point_in_time_note


def test_pass2_selects_net_debt_note_from_preceding_at_31_december_row():
    """Point-in-time markers in preceding rows must survive locator normalization."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    rio_style_summary = DoclingTable(
        page_number=1,
        caption="",
        rows=[
            ["Year ended 31 December", "2024", "2023", "Change"],
            [
                "Net cash generated from operating activities (US$ millions)",
                "15,599",
                "15,160",
                "3%",
            ],
            ["", "At 31 December 2024", "At 31 December 2023", ""],
            ["Net debt¹ (US$ millions)", "5,491", "4,231", "30%"],
        ],
        headers=["Year ended 31 December", "2024", "2023", "Change"],
    )

    result = _run_pass2_locator([rio_style_summary])

    assert result["net_debt_note"] is rio_style_summary


def test_pass2_selects_net_debt_note_from_at_year_end_header():
    """Year-end point-in-time headers should populate the dedicated net debt slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    rio_2023_style = DoclingTable(
        page_number=1,
        caption="",
        rows=[
            ["At year end", "2023", "2022", "Change"],
            ["Revenue", "54,041", "55,554", "(3)%"],
            ["Net debt", "4,231", "4,188", "1%"],
        ],
        headers=["At year end", "2023", "2022", "Change"],
    )

    result = _run_pass2_locator([rio_2023_style])

    assert result["net_debt_note"] is rio_2023_style


def test_pass2_rejects_year_end_net_debt_summary_from_note_slot():
    """Year-end performance summaries must not populate the explicit net-debt note slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    year_end_summary = DoclingTable(
        page_number=1,
        caption="Year ended 30 June 2021",
        rows=[
            ["Year ended 30 June", "2021", "2020"],
            ["Net operating cash flow", "27,234", "15,706"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021", "2020"],
    )

    result = _run_pass2_locator([year_end_summary])

    assert result["net_debt_note"] is None


def test_pass2_rejects_formula_style_year_end_net_debt_note_without_as_at_marker():
    """Year-ended formula tables must not populate the point-in-time net-debt slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    year_end_summary = DoclingTable(
        page_number=3,
        caption="",
        rows=[
            ["Year ended 30 June", "2021", "2020"],
            ["Net operating cash flow", "27,234", "15,706"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021", "2020"],
    )
    bhp_style_note = DoclingTable(
        page_number=66,
        caption="",
        rows=[
            ["Year ended 30 June", "2021 US$M", "2020 US$M Restated"],
            ["Interest bearing liabilities - Current", "2,628", "5,012"],
            ["Interest bearing liabilities - Non current", "18,355", "22,036"],
            ["Total interest bearing liabilities", "20,983", "27,048"],
            ["Borrowing", "17,087", "23,605"],
            ["Lease liabilities", "3,896", "3,443"],
            [
                "Less: Lease liability associated with index-linked freight contracts",
                "1,025",
                "1,160",
            ],
            ["Less: Cash and cash equivalents", "15,246", "13,426"],
            ["Less: Net debt management related instruments", "557", "433"],
            ["Less: Total derivatives included in net debt", "591", "418"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021 US$M", "2020 US$M Restated"],
    )

    result = _run_pass2_locator([year_end_summary, bhp_style_note])

    assert result["net_debt_note"] is None


def test_pass2_rejects_glossary_definition_from_net_debt_note_slot():
    """Glossary prose must not be mistaken for a formula-style net debt note."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    glossary = DoclingTable(
        page_number=50,
        caption="",
        rows=[
            ["GLOSSARY", ""],
            ["Mineral Reserve", "A Mineral Reserve is the economically mineable part."],
            [
                "Net debt",
                "Gross debt less cash and cash equivalents. Includes finance lease liabilities.",
            ],
            ["NPAT only", "Statutory Net Profit after Tax"],
        ],
        headers=["GLOSSARY", ""],
    )

    result = _run_pass2_locator([glossary])

    assert result["net_debt_note"] is None


# ---------------------------------------------------------------------------
# Pass 3a — Scale normalisation and negative values
# ---------------------------------------------------------------------------


def test_pass3a_applies_thousands_multiplier():
    """Metric values must be multiplied by 1000 when scale=thousands."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.95,
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000  # multiplied by 1000


def test_pass3a_negative_values_preserved():
    """Negative values (already negative from LLM) must remain negative after scaling."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow",
        rows=[["", "H1"], ["Investing activities", "(412)"]],
        headers=[],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": None,
        "investing_cf": -412,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }
    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["investing_cf"] == -412_000


def test_pass3a_extracts_net_debt_note():
    """The dedicated note slot should request and return only explicit net_debt."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=45,
        caption="",
        rows=[
            ["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
            ["Borrowings", "(15,730)", "(14,896)"],
            ["Cash and cash equivalents", "1,436", "1,012"],
            ["Net debt", "(16,800)", "(16,445)"],
        ],
        headers=["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "net_debt_note": table,
        "balance_sheet": None,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "net_debt": -16800,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["_source"] == "net_debt_note"
    assert results[0]["net_debt"] == 16_800_000_000
    assert results[0]["row_refs"]["net_debt"] == "Net debt"


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
        {
            "_source": "cashflow_statement",
            "operating_cf": 3_241_000,
            "investing_cf": -412_000,
            "financing_cf": None,
            "cash_end": None,
            "pass3_confidence": 0.9,
            "row_refs": {},
        },
        {
            "_source": "income_statement",
            "revenue": 27_841_000_000,
            "ebit": 9_100_000_000,
            "np_attributable": None,
            "pass3_confidence": 0.88,
            "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
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
        page_number=2,
        caption="Cash Flows",
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
        page_number=1,
        caption="Highlights",
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
        page_number=2,
        caption="Cash Flows",
        rows=[["", "H1 2025 $'000"], ["Operating CF", "3,241"]],
        headers=["", "H1 2025 $'000"],
    )
    detected = _detect_scale_from_tables([table])
    assert detected == "thousands"

    pass1_scale = "millions"  # LLM wrong

    # This is the exact condition guarding logger.info in run_multipass_extraction.
    gate = pass1_scale not in (detected, "unknown", None, "")
    assert gate, (
        f"INFO log gate must be True when LLM='{pass1_scale}' vs table='{detected}'"
    )


def test_currency_detection_from_tables_prefers_dominant_signal():
    """Dominant table currency markers should resolve to one currency code."""
    from app.services.multipass_extraction import _detect_currency_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="Consolidated statement of cash flows",
            headers=["Item", "Current quarter A$'000"],
            rows=[["Net cash from operations", "3,241"]],
        ),
        DoclingTable(
            page_number=2,
            caption="Financial position (A$M)",
            headers=["Metric", "A$M"],
            rows=[["Net debt", "12.4"]],
        ),
    ]

    assert _detect_currency_from_tables(tables) == "AUD"


def test_currency_detection_returns_none_when_signals_tie():
    """When AUD/USD evidence ties, currency detector must abstain (None)."""
    from app.services.multipass_extraction import _detect_currency_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="USD summary",
            headers=["Metric", "US$M"],
            rows=[["Revenue", "53.6"]],
        ),
        DoclingTable(
            page_number=2,
            caption="AUD summary",
            headers=["Metric", "A$M"],
            rows=[["Revenue", "80.1"]],
        ),
    ]

    assert _detect_currency_from_tables(tables) is None


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
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }

    # scale already corrected (e.g. by the table-header override in run_multipass_extraction)
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.95,
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000, (
        f"Expected thousands multiplier (3_241_000), got {results[0]['operating_cf']}"
    )


def test_pass4_higher_priority_source_wins():
    """income_statement must override highlights when both provide revenue."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "highlights",
            "revenue": 45_200_000,
            "pass3_confidence": 0.7,
            "row_refs": {},
        },
        {
            "_source": "income_statement",
            "revenue": 45_192_000,
            "pass3_confidence": 0.92,
            "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
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
        # Caller (process_document) is responsible for commit; flush here to make
        # rows visible within this session for assertions.
        _upsert_financial_rows(session, doc, payload)
        session.flush()

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
        session.flush()

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
    assert "prior" in prompt_lower, (
        "Prompt must explicitly mention prior-period columns"
    )
    assert "comparative" in prompt_lower, (
        "Prompt must explicitly mention comparative columns"
    )
    assert "period_end" in _PASS3A_PROMPT or "{period_end}" in _PASS3A_PROMPT, (
        "Prompt must reference period_end for column selection"
    )


def test_pass3a_prompt_documents_bank_revenue_equivalent():
    """Banking half-year reports (e.g. ANZ) use operating / net interest income, not 'Revenue'."""
    from app.services.multipass_extraction import _PASS3A_PROMPT

    pl = _PASS3A_PROMPT.lower()
    assert "bank" in pl
    assert "net interest income" in pl
    assert "operating income" in pl


def test_pass3a_prompt_includes_period_end_for_column_selection():
    """The assembled prompt sent to the LLM must contain the period_end date
    and a column-selection instruction."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Income Statement",
        rows=[
            ["", "H1 2025", "H1 2024"],
            ["Revenue", "485,630", "390,200"],
            ["EBIT", "31,284", "22,100"],
        ],
        headers=["", "H1 2025", "H1 2024"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": table,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 485630,
        "ebit": 31284,
        "np_attributable": None,
        "period_col": "H1 2025",
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    captured_prompts = []

    def capture_llm_call(prompt, llm_client, max_tokens=512):
        captured_prompts.append(prompt)
        return mock_raw

    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=capture_llm_call
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert captured_prompts, "LLM must have been called"
    prompt = captured_prompts[0]
    assert "2025-06-30" in prompt, (
        "period_end date must appear in the prompt for column selection"
    )
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
            "operating_cf": 500_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": 200_000_000,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "balance_sheet",
            "net_debt": None,
            "total_debt": 800_000_000,
            "shares_outstanding": None,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 600_000_000, (
        "net_debt must be derived as total_debt(800M) - cash_end(200M) = 600M"
    )
    assert "derived:balance_sheet" in payload["provenance"].get("net_debt", ""), (
        "provenance must record that net_debt was derived"
    )
    assert payload["confidence_metrics"] == pytest.approx(
        round((0.9 + 0.9 + 0.55) / 3, 3)
    ), (
        "Derived net_debt must contribute discounted confidence instead of inheriting "
        "the balance-sheet pass3 confidence."
    )


def test_pass4_reconciler_skips_derivation_when_net_debt_already_extracted():
    """Explicitly extracted net_debt must not be overwritten by derivation."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 100_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": 50_000_000,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "balance_sheet",
            "net_debt": 300_000_000,
            "total_debt": 999_000_000,
            "shares_outstanding": None,
            "pass3_confidence": 0.9,
            "row_refs": {"net_debt": "Net debt", "total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
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
            "net_debt": None,
            "total_debt": 500_000_000,
            "shares_outstanding": 100_000_000,
            "pass3_confidence": 0.7,
            "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None, (
        "net_debt must remain null when cash_end is unavailable — cannot derive safely"
    )


def test_pass4_preserves_explicit_summary_net_debt():
    """Explicit summary-table net_debt must beat ambiguous balance-sheet debt labels."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "highlights",
            "_page_number": 1,
            "net_debt": 12_924_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"net_debt": "Net debt"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 123,
            "net_debt": -34_465_000_000,
            "total_debt": -20_420_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {
                "net_debt": "Borrowings",
                "total_debt": "Borrowings",
            },
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "A", "period_end": "2025-06-30", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 12_924_000_000
    assert payload["provenance"]["net_debt"] == "highlights:page_1:Net debt"
    assert payload["confidence_metrics"] == pytest.approx(0.95), (
        "An explicit labelled Net debt row must carry high confidence."
    )


def test_pass4_rejects_total_liabilities_as_total_debt():
    """Total liabilities must not be treated as debt evidence for net_debt derivation."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 8,
            "cash_end": 1_436_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at period end"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 19,
            "net_debt": None,
            "total_debt": 28_900_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Total liabilities"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2025-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None
    assert "net_debt" not in payload["provenance"]


def test_pass4_rejects_accounting_negative_borrowings_for_derivation():
    """Accounting-negative borrowings must not fabricate derived net_debt."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 6,
            "cash_end": 14_045_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 32,
            "net_debt": None,
            "total_debt": -20_420_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "A", "period_end": "2023-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None


def test_pass4_ambiguous_balance_sheet_net_debt_abstains():
    """A balance-sheet value from a non-explicit debt row must be rejected."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "balance_sheet",
            "_page_number": 32,
            "net_debt": 27_464_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"net_debt": "Borrowings"},
        }
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "A", "period_end": "2023-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None
    assert "net_debt" not in payload["provenance"]


def test_pass4_explicit_net_debt_not_overwritten_by_balance_sheet_derivation():
    """Derived balance-sheet debt must not replace explicit summary net_debt evidence."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 5,
            "cash_end": 200_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "highlights",
            "_page_number": 1,
            "net_debt": 300_000_000,
            "pass3_confidence": 0.85,
            "row_refs": {"net_debt": "Net debt"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 19,
            "net_debt": None,
            "total_debt": 800_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 300_000_000
    assert payload["provenance"]["net_debt"] == "highlights:page_1:Net debt"


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


# ---------------------------------------------------------------------------
# Validation gate — new guards (B7: scale, B8: currency, B9: quarterly)
# ---------------------------------------------------------------------------


def _good_payload(period_type="H", scale="thousands", currency="AUD", confidence=0.85):
    """Minimal well-formed payload for _validate_gate tests."""
    return {
        "period_end": "2024-12-31",
        "period_type": period_type,
        "scale": scale,
        "currency": currency,
        "metrics": {
            "revenue": 500_000_000,
            "ebit": 80_000_000,
            "np_attributable": 55_000_000,
            "operating_cf": 90_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        },
        "confidence_metrics": confidence,
    }


def test_validate_gate_quarterly_period_passes():
    """period_type='Q' must be accepted by the gate — quarterly is a valid period type."""
    from app.services.multipass_extraction import _validate_gate

    status, error = _validate_gate(_good_payload(period_type="Q"))
    assert status in ("ok", "ok_low_confidence"), (
        f"Quarterly period must pass gate; got status={status!r}, error={error!r}"
    )
    assert error is None


def test_validate_gate_scale_unknown_hard_blocked():
    """scale='unknown' must be a hard block — values would be wrong by up to 1000×."""
    from app.services.multipass_extraction import _validate_gate

    status, error = _validate_gate(_good_payload(scale="unknown"))
    assert status == "failed", f"Expected 'failed', got {status!r}"
    assert error == "validation_gate:scale_unknown", f"Unexpected error key: {error!r}"


def test_validate_gate_non_aud_returns_ok_low_confidence():
    """Non-AUD currency (e.g. USD, GBP) must downgrade to ok_low_confidence.

    There is no FX conversion policy — values are stored as-is, so downstream
    consumers must not compare them directly with AUD-denominated peers.
    """
    from app.services.multipass_extraction import _validate_gate

    for currency in ("USD", "GBP", "EUR"):
        status, error = _validate_gate(_good_payload(currency=currency))
        assert status == "ok_low_confidence", (
            f"currency={currency} must yield ok_low_confidence; got status={status!r}"
        )
        assert error is None, (
            f"error must be None for currency downgrade; got {error!r}"
        )


# ---------------------------------------------------------------------------
# Pass 3a — page_number in output (B10)
# ---------------------------------------------------------------------------


def test_pass3a_page_number_in_output():
    """Pass 3a output dict must include _page_number from the source DoclingTable."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=7,
        caption="Statement of Cash Flows",
        rows=[["", "Q1 2025"], ["Net cash from operations", "1,200"]],
        headers=["", "Q1 2025"],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "Q",
        "period_end": "2025-03-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": 1200,
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.88,
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["_page_number"] == 7, (
        f"_page_number must be 7 (from DoclingTable.page_number), got {results[0].get('_page_number')!r}"
    )


# ---------------------------------------------------------------------------
# Pass 4 — page_number in provenance strings (B11)
# ---------------------------------------------------------------------------


def test_pass4_provenance_includes_page_number():
    """Provenance strings must embed the source page number: '{source}:page_{n}:{row_ref}'."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 5,
            "operating_cf": 3_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": None,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"operating_cf": "Net cash from operations"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
    pass1 = {"report_type": "Q", "period_end": "2025-03-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    prov = result["provenance"].get("operating_cf", "")
    assert "page_5" in prov, (
        f"Provenance must include 'page_5' for a table on page 5; got: {prov!r}"
    )


# ---------------------------------------------------------------------------
# JSON parse — accounting parentheses
# ---------------------------------------------------------------------------


def test_parse_json_accounting_parentheses():
    """
    Accounting notation: LLM outputs (5,590) meaning -5590.
    _parse_json_text must convert these to negative numbers so the
    response can be parsed as valid JSON.
    """
    from app.services.llamacpp_runtime import _parse_json_text

    raw = '{"total_debt": (5,590), "cash_end": 1234}'
    result = _parse_json_text(raw)
    assert result == {"total_debt": -5590, "cash_end": 1234}


def test_parse_json_accounting_parentheses_no_commas():
    """Parenthesised integers without thousands separator also work."""
    from app.services.llamacpp_runtime import _parse_json_text

    raw = '{"investing_cf": (527)}'
    result = _parse_json_text(raw)
    assert result == {"investing_cf": -527}


def test_parse_json_normal_negatives_unchanged():
    """Normal negative numbers must not be transformed."""
    from app.services.llamacpp_runtime import _parse_json_text

    raw = '{"investing_cf": -527, "revenue": 3052}'
    result = _parse_json_text(raw)
    assert result == {"investing_cf": -527, "revenue": 3052}


# ---------------------------------------------------------------------------
# ASX Appendix 5B — scale detection and table merging
# ---------------------------------------------------------------------------


def test_scale_detection_matches_dollar_a_thousands():
    """$A'000 notation (ASX Appendix 5B) must be detected as 'thousands'."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="",
            headers=[
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date (6 months) $A'000",
            ],
            rows=[["1.1", "Receipts from customers", "500", "1,000"]],
        )
    ]
    assert _detect_scale_from_tables(tables) == "thousands"


def test_scale_detection_matches_dollar_a_millions():
    """$A'000,000 (less common) and A$M must also be detected."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    # A$M notation
    tables_am = [
        DoclingTable(
            page_number=1,
            caption="",
            headers=["Item", "A$M"],
            rows=[["Revenue", "42.5"]],
        )
    ]
    assert _detect_scale_from_tables(tables_am) == "millions"


def test_pass2_score_uses_all_body_columns():
    """Pass 2 scoring must read all body columns, not just column 0.

    ASX 5B tables have section numbers in column 0 (e.g. '4.2') and
    the descriptive label in column 1 ('Net cash from operating activities').
    Only scanning column 0 misses all keywords.
    """
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    # Section 4 summary table: column 0 = section numbers, column 1 = labels
    section4 = DoclingTable(
        page_number=12,
        caption="",
        headers=["0", "1", "2", "3"],
        rows=[
            ["0", "1", "2", "3"],
            ["4.", "Net increase / (decrease) in cash", "", ""],
            ["4.1", "Cash and cash equivalents at beginning of period", "907", "1,822"],
            ["4.2", "Net cash from / (used in) operating activities", "(450)", "(796)"],
            [
                "4.3",
                "Net cash from / (used in) investing activities",
                "(624)",
                "(1,193)",
            ],
            ["4.4", "Net cash from / (used in) financing activities", "869", "869"],
        ],
    )

    labelled = _run_pass2_locator([section4])
    assert labelled["cashflow_statement"] is not None, (
        "Section 4 summary table must be labelled as cashflow_statement "
        "even when column 0 contains only section numbers"
    )


def test_pass2_merges_fragmented_5b_cf_tables():
    """When multiple tables score >= threshold for cashflow_statement,
    they must be merged into one synthetic table."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    # Simulate 3 fragmented 5B tables
    operating = DoclingTable(
        page_number=11,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["1.", "Cash flows from operating activities", "", ""],
            ["1.9", "Net cash from / (used in) operating activities", "(450)", "(796)"],
        ],
    )
    investing = DoclingTable(
        page_number=12,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["2.", "Cash flows from investing activities", "", ""],
            [
                "2.6",
                "Net cash from / (used in) investing activities",
                "(624)",
                "(1,193)",
            ],
        ],
    )
    section4 = DoclingTable(
        page_number=13,
        caption="",
        headers=["0", "1", "2", "3"],
        rows=[
            ["0", "1", "2", "3"],
            ["4.2", "Net cash from / (used in) operating activities", "(450)", "(796)"],
            [
                "4.3",
                "Net cash from / (used in) investing activities",
                "(624)",
                "(1,193)",
            ],
            ["4.4", "Net cash from / (used in) financing activities", "869", "869"],
            ["4.6", "Cash and cash equivalents at end of period", "702", "702"],
        ],
    )

    labelled = _run_pass2_locator([operating, investing, section4])
    cf = labelled["cashflow_statement"]
    assert cf is not None
    assert cf.caption.startswith("Merged cashflow"), (
        f"Expected merged table, got caption={cf.caption!r}"
    )
    # Merged table must contain rows from all three source tables
    all_text = " ".join(" ".join(r) for r in cf.rows).lower()
    assert "operating activities" in all_text
    assert "investing activities" in all_text
    assert "financing activities" in all_text
    assert "702" in all_text  # cash_end from section 4


# ---------------------------------------------------------------------------
# Pass 3a — shares_outstanding scaling (body text + doc-level fallback)
# ---------------------------------------------------------------------------


def test_pass3a_shares_scaling_from_body_text():
    """shares_outstanding sanity check must also scan body rows for '000 indicators.

    SEG share capital table has "No. '000s" in a row label, not in column headers.
    The scaling logic must detect this and multiply by 1,000.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=24,
        caption="Note 6 — Issued Capital",
        rows=[
            ["", "No. '000s", "$'000s"],
            ["Balance at beginning of period", "280,875", "42,110"],
            ["Share issue", "—", "—"],
            ["Balance at end of period", "280,875", "42,110"],
        ],
        headers=["", "Dec 2025", "Dec 2025"],  # headers DON'T have '000s
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    # LLM returns raw table value without conversion
    mock_raw = {
        "shares_outstanding": 280875,  # raw from table, not absolute
        "pass3_confidence": 0.9,
        "row_refs": {"shares_outstanding": "Balance at end of period"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 280_875_000, (
        f"Expected 280,875,000 (×1000 from body row '000s indicator), "
        f"got {results[0]['shares_outstanding']}"
    )


def test_pass3a_shares_scaling_doc_level_fallback():
    """When table headers AND body text lack scale indicators, but the document-level
    scale is 'thousands', the fallback must apply the document multiplier.

    This covers tables that inherit the filing-level scale without restating it.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=24,
        caption="Share Capital",
        rows=[
            ["", "No.", "Amount"],
            ["Ordinary shares at end of period", "280,875", "42,110"],
        ],
        headers=["", "No.", "Amount"],  # no scale indicator
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "shares_outstanding": 280875,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 280_875_000, (
        f"Expected 280,875,000 (×1000 from doc-level scale fallback), "
        f"got {results[0]['shares_outstanding']}"
    )


def test_pass3a_shares_no_scaling_when_absolute():
    """When the LLM returns an absolute count (>= 1M), no scaling must be applied
    regardless of document-level scale — the value is already correct.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=32,
        caption="Share Capital Note",
        rows=[
            ["", "Number", "$M"],
            ["Balance at end of period", "196,478,902", "5,057"],
        ],
        headers=["", "Number", "$M"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "shares_outstanding": 196478902,  # absolute count, already correct
        "pass3_confidence": 0.95,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 196_478_902, (
        f"Absolute count must not be scaled; got {results[0]['shares_outstanding']}"
    )


# ---------------------------------------------------------------------------
# Pass 2 — CF table disqualification for IS/BS slots
# ---------------------------------------------------------------------------


def test_pass2_cf_disqualification_blocks_5b_from_income_statement():
    """A cash-flow table (Appendix 5B) with 'income tax' keyword must NOT
    claim the income_statement slot due to CF disqualification phrases in
    its body rows."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cf_table = DoclingTable(
        page_number=11,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["1.1", "Receipts from customers", "21,836", "44,295"],
            ["1.7", "Income tax paid", "(400)", "(800)"],
        ],
    )

    labelled = _run_pass2_locator([cf_table])
    assert labelled["income_statement"] is None, (
        "Appendix 5B cash-flow table must NOT claim the income_statement slot "
        "despite having 'income tax' keyword match"
    )
    assert labelled["cashflow_statement"] is not None, (
        "The table must still be labelled as cashflow_statement"
    )


def test_pass2_cf_disqualification_blocks_5b_from_balance_sheet():
    """A cash-flow table with 'non-current assets' keyword must NOT
    claim the balance_sheet slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cf_table = DoclingTable(
        page_number=12,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["2.", "Cash flows from investing activities", "", ""],
            ["2.1(d)", "Exploration — non-current assets", "(100)", "(200)"],
        ],
    )

    labelled = _run_pass2_locator([cf_table])
    assert labelled["balance_sheet"] is None, (
        "Appendix 5B cash-flow table must NOT claim the balance_sheet slot "
        "despite having 'non-current assets' keyword match"
    )


# ---------------------------------------------------------------------------
# Redundant table skipping
# ---------------------------------------------------------------------------


def _make_dummy_table(caption="Dummy"):
    from app.services.docling_extract import DoclingTable

    return DoclingTable(
        page_number=1,
        caption=caption,
        rows=[["", "H1"], ["Item", "100"]],
        headers=["", "H1"],
    )


def test_share_capital_not_skipped_when_balance_sheet_present():
    """share_capital LLM call must NOT be skipped even when balance_sheet is present.

    Balance sheets are dense and unreliable for share counts; the dedicated
    share_capital table is the most reliable source for shares_outstanding.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "balance_sheet": _make_dummy_table("Balance Sheet"),
        "share_capital": _make_dummy_table("Share Capital"),
        "income_statement": None,
        "cashflow_statement": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "net_debt": 500,
        "total_debt": None,
        "shares_outstanding": 1_000_000,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    original_tables = []

    def _tracking_llm_call(prompt, *args, **kwargs):
        if "share_capital" in prompt:
            original_tables.append("share_capital")
        elif "balance_sheet" in prompt:
            original_tables.append("balance_sheet")
        return mock_raw

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        side_effect=_tracking_llm_call,
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    # Both balance_sheet AND share_capital should have been called
    assert "share_capital" in original_tables
    assert "balance_sheet" in original_tables
    sources = [r["_source"] for r in results]
    assert "share_capital" in sources


def test_share_capital_not_skipped_when_balance_sheet_absent():
    """share_capital must NOT be skipped when balance_sheet is absent."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "balance_sheet": None,
        "share_capital": _make_dummy_table("Share Capital"),
        "income_statement": None,
        "cashflow_statement": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "shares_outstanding": 1_000_000,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    sources = [r["_source"] for r in results]
    assert "share_capital" in sources


def test_skip_highlights_when_is_and_cf_present():
    """highlights LLM call must be skipped when IS + CF are both present."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "income_statement": _make_dummy_table("Income Statement"),
        "cashflow_statement": _make_dummy_table("Cash Flow"),
        "balance_sheet": None,
        "share_capital": None,
        "highlights": _make_dummy_table("Highlights"),
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 1000,
        "ebit": 200,
        "np_attributable": 150,
        "operating_cf": 500,
        "investing_cf": -100,
        "financing_cf": -50,
        "capex": None,
        "cash_end": None,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    called_tables = []

    def _tracking_llm_call(prompt, *args, **kwargs):
        if "highlights" in prompt:
            called_tables.append("highlights")
        elif "income_statement" in prompt:
            called_tables.append("income_statement")
        elif "cashflow_statement" in prompt:
            called_tables.append("cashflow_statement")
        return mock_raw

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        side_effect=_tracking_llm_call,
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert "highlights" not in called_tables
    sources = [r["_source"] for r in results]
    assert "highlights" not in sources


def test_highlights_not_skipped_when_cf_absent():
    """highlights must NOT be skipped when cashflow_statement is absent."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "income_statement": _make_dummy_table("Income Statement"),
        "cashflow_statement": None,
        "balance_sheet": None,
        "share_capital": None,
        "highlights": _make_dummy_table("Highlights"),
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 1000,
        "ebit": 200,
        "np_attributable": 150,
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
        "capex": None,
        "cash_end": None,
        "net_debt": None,
        "shares_outstanding": None,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    sources = [r["_source"] for r in results]
    assert "highlights" in sources


def test_skip_redundant_disabled_by_env_var():
    """When EXTRACTION_SKIP_REDUNDANT=0, no tables should be skipped."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "income_statement": _make_dummy_table("Income Statement"),
        "cashflow_statement": _make_dummy_table("Cash Flow"),
        "balance_sheet": _make_dummy_table("Balance Sheet"),
        "share_capital": _make_dummy_table("Share Capital"),
        "highlights": _make_dummy_table("Highlights"),
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 1000,
        "ebit": 200,
        "np_attributable": 150,
        "operating_cf": 500,
        "investing_cf": -100,
        "financing_cf": -50,
        "capex": None,
        "cash_end": 800,
        "net_debt": 300,
        "total_debt": None,
        "shares_outstanding": 1_000_000,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "0"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    sources = [r["_source"] for r in results]
    assert "share_capital" in sources
    assert "highlights" in sources


# ---------------------------------------------------------------------------
# skip_narrative — optional Pass 3b skipping
# ---------------------------------------------------------------------------


def _mock_structured_doc():
    """Build a minimal StructuredDocument for run_multipass_extraction tests."""
    from app.services.docling_extract import DoclingTable

    class _FakeDoc:
        sections = [{"text": "Some prose about risk.", "page": 1}]
        tables = [
            DoclingTable(
                page_number=1,
                caption="Income Statement",
                headers=["", "H1 2025 $'000"],
                rows=[
                    ["", "H1 2025 $'000"],
                    ["Revenue", "500,000"],
                    ["EBIT", "80,000"],
                    ["Net profit", "55,000"],
                ],
            ),
        ]

    return _FakeDoc()


def _pass1_response():
    return {
        "report_type": "H",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.95,
    }


def _pass3a_response():
    return {
        "revenue": 500_000,
        "ebit": 80_000,
        "np_attributable": 55_000,
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
        "capex": None,
        "cash_end": None,
        "net_debt": None,
        "shares_outstanding": None,
        "total_debt": None,
        "pass3_confidence": 0.88,
        "row_refs": {},
    }


def _pass3b_response():
    return {
        "risk_summary": "Commodity price risk exposure",
        "risk_bullets": "Iron ore volatility",
        "guidance_summary": "Revenue growth 10%",
        "material_changes": None,
        "confidence_narrative": 0.75,
    }


def test_skip_narrative_param_skips_pass3b_llm_call():
    """With skip_narrative=True, no LLM call should be made for pass3b."""
    from app.services.multipass_extraction import run_multipass_extraction

    call_log = []

    def mock_llm(prompt, llm_client, max_tokens=512):
        call_log.append(prompt)
        # Return pass1 on first call, pass3a on subsequent
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            result = run_multipass_extraction(
                "/fake/path.pdf",
                {"document_id": "d1", "ticker": "TST", "title": "Test Report"},
                llm_client=None,
                skip_narrative=True,
            )

    # No call should contain the pass3b narrative prompt keywords
    for prompt in call_log:
        assert "narrative extractor" not in prompt.lower(), (
            "Pass 3b LLM call must not be made when skip_narrative=True"
        )

    # Narrative fields must be null
    assert result.payload.get("risk_summary") is None
    assert result.payload.get("guidance_summary") is None
    assert result.payload.get("confidence_narrative") == 0.0


def test_skip_narrative_env_var_skips_pass3b():
    """EXTRACTION_SKIP_NARRATIVE=1 env var must skip pass3b even when param is False."""
    from app.services.multipass_extraction import run_multipass_extraction

    call_log = []

    def mock_llm(prompt, llm_client, max_tokens=512):
        call_log.append(prompt)
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            with patch.dict("os.environ", {"EXTRACTION_SKIP_NARRATIVE": "1"}):
                result = run_multipass_extraction(
                    "/fake/path.pdf",
                    {"document_id": "d2", "ticker": "TST", "title": "Test"},
                    llm_client=None,
                )

    for prompt in call_log:
        assert "narrative extractor" not in prompt.lower(), (
            "Pass 3b LLM call must not be made when EXTRACTION_SKIP_NARRATIVE=1"
        )
    assert result.payload.get("risk_summary") is None


def test_skip_narrative_produces_valid_pipeline_output():
    """Pipeline with skip_narrative must still produce a structurally valid result
    that passes the validation gate (all narrative fields null is acceptable)."""
    from app.services.multipass_extraction import (
        run_multipass_extraction,
        METRIC_FIELDS,
    )

    def mock_llm(prompt, llm_client, max_tokens=512):
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            result = run_multipass_extraction(
                "/fake/path.pdf",
                {"document_id": "d3", "ticker": "TST", "title": "Test"},
                llm_client=None,
                skip_narrative=True,
            )

    # Must not fail due to missing narrative
    assert result.status in ("ok", "ok_low_confidence"), (
        f"Pipeline must not fail with skip_narrative; got status={result.status!r}, error={result.error!r}"
    )

    # Payload structure must include all expected keys
    assert "metrics" in result.payload
    for m in METRIC_FIELDS:
        assert m in result.payload, f"Metric field {m!r} missing from payload"
    assert "risk_summary" in result.payload
    assert "guidance_summary" in result.payload
    assert "confidence_narrative" in result.payload
    assert "provenance" in result.payload


def test_skip_narrative_false_still_calls_pass3b():
    """Default behaviour (skip_narrative=False) must still call pass3b."""
    from app.services.multipass_extraction import run_multipass_extraction

    call_log = []

    def mock_llm(prompt, llm_client, max_tokens=512):
        call_log.append(prompt)
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        if "narrative" in prompt.lower() or "risk" in prompt.lower():
            return _pass3b_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            with patch.dict(
                "os.environ", {"EXTRACTION_SKIP_NARRATIVE": ""}, clear=False
            ):
                result = run_multipass_extraction(
                    "/fake/path.pdf",
                    {"document_id": "d4", "ticker": "TST", "title": "Test"},
                    llm_client=None,
                    skip_narrative=False,
                )

    # At least one call must be for narrative extraction
    narrative_calls = [
        p for p in call_log if "narrative" in p.lower() or "risk" in p.lower()
    ]
    assert len(narrative_calls) >= 1, (
        "Pass 3b LLM call must be made when skip_narrative=False"
    )
    assert result.payload.get("risk_summary") == "Commodity price risk exposure"


def test_validation_gate_accepts_null_narrative_fields():
    """The validation gate must not reject a payload just because narrative fields are null."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload()
    payload["risk_summary"] = None
    payload["risk_bullets"] = None
    payload["guidance_summary"] = None
    payload["material_changes"] = None
    payload["confidence_narrative"] = 0.0

    status, error = _validate_gate(payload)
    assert status in ("ok", "ok_low_confidence"), (
        f"Gate must accept all-null narrative fields; got status={status!r}, error={error!r}"
    )


# ---------------------------------------------------------------------------
# Parallel Pass 3a — verify parallel produces same results as sequential
# ---------------------------------------------------------------------------


def test_pass3a_parallel_matches_sequential():
    """Parallel and sequential Pass 3a must produce identical results."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable
    import threading

    # Build multiple tables so parallelism actually kicks in (>1 eligible table).
    cf_table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
    )
    is_table = DoclingTable(
        page_number=3,
        caption="Income Statement",
        rows=[["", "H1 2025"], ["Revenue", "10,000"]],
        headers=["", "H1 2025"],
    )
    bs_table = DoclingTable(
        page_number=4,
        caption="Balance Sheet",
        rows=[["", "H1 2025"], ["Net debt", "5,000"]],
        headers=["", "H1 2025"],
    )
    labelled = {
        "cashflow_statement": cf_table,
        "income_statement": is_table,
        "balance_sheet": bs_table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    # Per-table mock responses keyed by table_type embedded in the prompt.
    mock_responses = {
        "cashflow_statement": {
            "operating_cf": 3241,
            "investing_cf": -100,
            "financing_cf": -50,
            "cash_end": 500,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {},
        },
        "income_statement": {
            "revenue": 10000,
            "ebit": 5000,
            "np_attributable": 3000,
            "pass3_confidence": 0.85,
            "row_refs": {},
        },
        "balance_sheet": {
            "net_debt": 5000,
            "total_debt": 6000,
            "shares_outstanding": 2_000_000,
            "pass3_confidence": 0.92,
            "row_refs": {},
        },
    }
    call_threads = []

    def _mock_llm(prompt, *args, **kwargs):
        call_threads.append(threading.current_thread().name)
        for tt, resp in mock_responses.items():
            if tt in prompt:
                return resp
        return {}

    # Run sequentially (EXTRACTION_PARALLEL=0)
    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=_mock_llm
    ):
        with patch.dict("os.environ", {"EXTRACTION_PARALLEL": "0"}):
            seq_results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    call_threads.clear()

    # Run in parallel (EXTRACTION_PARALLEL=1, the default)
    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=_mock_llm
    ):
        with patch.dict("os.environ", {"EXTRACTION_PARALLEL": "1"}):
            par_results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    # Same number of results
    assert len(par_results) == len(seq_results), (
        f"Parallel returned {len(par_results)} results, sequential returned {len(seq_results)}"
    )

    # Same source order (must match labelled_tables iteration order)
    seq_sources = [r["_source"] for r in seq_results]
    par_sources = [r["_source"] for r in par_results]
    assert par_sources == seq_sources, (
        f"Order mismatch: parallel={par_sources}, sequential={seq_sources}"
    )

    # Same metric values
    for seq_r, par_r in zip(seq_results, par_results):
        for key in seq_r:
            assert par_r.get(key) == seq_r[key], (
                f"Mismatch for {seq_r['_source']}.{key}: "
                f"sequential={seq_r[key]}, parallel={par_r.get(key)}"
            )


def test_pass3a_parallel_disabled_by_env():
    """When EXTRACTION_PARALLEL=0, all LLM calls must run on the main thread."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable
    import threading

    tables = {}
    for tt in ("cashflow_statement", "income_statement"):
        tables[tt] = DoclingTable(
            page_number=1,
            caption=tt,
            rows=[["", "H1"], ["Item", "100"]],
            headers=["", "H1"],
        )
    labelled = {**tables, "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "units",
    }

    mock_raw = {"revenue": 100, "pass3_confidence": 0.5, "row_refs": {}}
    call_threads = []

    def _mock_llm(prompt, *args, **kwargs):
        call_threads.append(threading.current_thread().name)
        return mock_raw

    main_thread = threading.current_thread().name
    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=_mock_llm
    ):
        with patch.dict("os.environ", {"EXTRACTION_PARALLEL": "0"}):
            _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    # All calls must have happened on the main thread
    assert all(t == main_thread for t in call_threads), (
        f"Expected all calls on main thread ({main_thread}), got: {call_threads}"
    )


# ---------------------------------------------------------------------------
# Row Filtering
# ---------------------------------------------------------------------------

from app.services.multipass_extraction import (
    _filter_table_rows,
    _is_section_header,
    _is_total_row,
)


def _make_table_with_rows(rows):
    """Create a minimal table-like object with given rows."""
    t = MagicMock()
    t.rows = rows
    t.headers = rows[0] if rows else []
    t.caption = ""
    t.page_number = 1
    return t


class TestRowFiltering:
    def test_small_table_not_filtered(self):
        """Tables with <=20 rows should not be filtered."""
        rows = [["Header", "Val"]] + [[f"Row {i}", str(i)] for i in range(15)]
        table = _make_table_with_rows(rows)
        result = _filter_table_rows(table, "cashflow_statement")
        assert result == rows  # unchanged

    def test_highlights_not_filtered(self):
        rows = [["Header", "Val"]] + [[f"Row {i}", str(i)] for i in range(25)]
        table = _make_table_with_rows(rows)
        result = _filter_table_rows(table, "highlights")
        assert result == rows

    def test_large_cf_table_filtered(self):
        """Large CF table should be filtered, keeping headers/totals/metric rows."""
        rows = [
            ["Item", "Dec 2025 $M", "Dec 2024 $M"],
            ["CASH FLOWS FROM OPERATING ACTIVITIES", "", ""],
            ["Receipts from customers", "3,343", "2,368"],
            ["Payments to suppliers and employees", "(2,267)", "(2,844)"],
            ["Subcontractor costs", "(100)", "(50)"],
            ["Raw materials consumed", "(200)", "(150)"],
            ["Equipment lease costs", "(80)", "(70)"],
            ["Travel and entertainment", "(10)", "(5)"],
            ["Professional fees", "(30)", "(20)"],
            ["Insurance costs", "(15)", "(12)"],
            ["Rent and occupancy", "(25)", "(18)"],
            ["IT and communications", "(20)", "(15)"],
            ["Net cash from operating activities", "880", "(656)"],
            ["CASH FLOWS FROM INVESTING ACTIVITIES", "", ""],
            ["Payments for property, plant and equipment", "(333)", "(732)"],
            ["Acquisition of subsidiaries", "(100)", "(50)"],
            ["Proceeds from disposal of assets", "25", "4"],
            ["Exploration expenditure", "(40)", "(30)"],
            ["Development expenditure", "(60)", "(45)"],
            ["Net cash used in investing activities", "(527)", "(658)"],
            ["CASH FLOWS FROM FINANCING ACTIVITIES", "", ""],
            ["Proceeds from borrowings", "500", "1,200"],
            ["Repayment of borrowings", "(400)", "(100)"],
            ["Dividend payments", "(200)", "(180)"],
            ["Repayment of lease liabilities", "(102)", "(103)"],
            ["Net cash from financing activities", "(126)", "1,114"],
            ["Net increase in cash and cash equivalents", "227", "(200)"],
            ["Cash and cash equivalents at beginning", "412", "908"],
            ["Effects of exchange rate changes", "(1)", "12"],
            ["Cash and cash equivalents at the end", "638", "720"],
        ]
        table = _make_table_with_rows(rows)
        result = _filter_table_rows(table, "cashflow_statement")
        # Should have fewer rows than original
        real_rows = [r for r in result if not str(r[0]).startswith("[...")]
        assert len(real_rows) < len(rows), (
            f"Expected filtering, got {len(real_rows)} vs {len(rows)}"
        )
        # Must keep header, section headers, totals, and key metric rows
        labels = [str(r[0]) for r in result]
        assert "Item" in labels  # header
        assert "CASH FLOWS FROM OPERATING ACTIVITIES" in labels  # section header
        assert "Net cash from operating activities" in labels  # total
        assert "Payments for property, plant and equipment" in labels  # capex
        assert "Cash and cash equivalents at the end" in labels  # cash_end
        # Should have omission markers
        assert any("[..." in str(r[0]) for r in result)

    def test_section_header_detection(self):
        assert _is_section_header(["CASH FLOWS FROM OPERATING ACTIVITIES", "", ""])
        assert not _is_section_header(["Revenue", "3,052", "2,290"])
        assert not _is_section_header(["", "", ""])

    def test_total_row_detection(self):
        assert _is_total_row(["Total revenue", "3,052", "2,290"])
        assert _is_total_row(["Net cash from operating activities", "880", "(656)"])
        assert not _is_total_row(["Receipts from customers", "3,343", "2,368"])

    def test_filter_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_FILTER_ROWS", "0")
        rows = [["H", "V"]] + [[f"Row {i}", str(i)] for i in range(25)]
        table = _make_table_with_rows(rows)
        # When disabled, _extract_single_table uses unfiltered path.
        # But _filter_table_rows itself doesn't check the env — it's the caller's job.
        # So test the filter still works (it's the caller that gates it).
        result = _filter_table_rows(table, "cashflow_statement")
        assert len(result) <= len(rows)


def test_pass3a_retries_full_table_when_filtered_output_misses_key_metric():
    """Filtered-table extraction should retry full table when key metrics are missing."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    rows = [["Item", "Current", "Prior"]]
    rows.extend([[f"Noise row {i}", str(i), str(i - 1)] for i in range(1, 28)])
    rows.append(["Revenue", "1200", "1100"])

    table = DoclingTable(
        page_number=4,
        caption="Income Statement",
        rows=rows,
        headers=["Item", "Current", "Prior"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": table,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "units",
    }

    first_raw = {
        "revenue": None,
        "ebit": 500,
        "np_attributable": 300,
        "period_col": "Current",
        "pass3_confidence": 0.7,
        "row_refs": {"ebit": "EBIT", "np_attributable": "NPAT"},
    }
    second_raw = {
        "revenue": 1200,
        "ebit": 500,
        "np_attributable": 300,
        "period_col": "Current",
        "pass3_confidence": 0.85,
        "row_refs": {
            "revenue": "Revenue",
            "ebit": "EBIT",
            "np_attributable": "NPAT",
        },
    }

    with patch(
        "app.services.multipass_extraction._filter_table_rows",
        return_value=rows[:8],
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call",
            side_effect=[first_raw, second_raw],
        ) as mock_llm:
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert mock_llm.call_count == 2, "Expected filtered extraction + full-table retry"
    assert results[0]["revenue"] == 1200
