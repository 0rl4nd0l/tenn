import pytest
from app.services.fact_contract import CanonicalFact, FAILURE_CODES
from app.services.synthesis_guard import verify_synthesis_claims, verify_comparisons

def test_basis_mismatch_blocks_comparison():
    fact_rc = CanonicalFact(
        metric_key="ebit",
        value=437.0,
        unit="AUD",
        scale="millions",
        basis="RC",
        period_type="A",
        period_end="2025-12-31",
        source_doc_id="doc1",
        source_page="2",
        source_span="RC EBIT $437.0m"
    )
    fact_hc = CanonicalFact(
        metric_key="np_attributable",
        value=-421.1,
        unit="AUD",
        scale="millions",
        basis="HC",
        period_type="A",
        period_end="2025-12-31",
        source_doc_id="doc1",
        source_page="2",
        source_span="Statutory Net Loss ($421.1m)"
    )
    
    issues = verify_comparisons([fact_rc, fact_hc])
    assert any(iss["code"] == FAILURE_CODES["BASIS_MISMATCH"] for iss in issues)

def test_unsupported_claim_blocking():
    fact = CanonicalFact(
        metric_key="ebit",
        value=437.0,
        unit="AUD",
        scale="millions",
        basis="RC",
        period_type="A",
        period_end="2025-12-31",
        source_doc_id="doc1",
        source_page="2",
        source_span="RC EBIT $437.0m"
    )
    
    prose = "The EBIT was 437 million. The operating cash flow was 7.1 billion."
    verified_prose, issues = verify_synthesis_claims(prose, [fact])
    
    assert "437 million" in verified_prose
    assert "[UNSUPPORTED_NUMERIC_CLAIM]" in verified_prose
    assert any(iss["code"] == FAILURE_CODES["UNSUPPORTED_NUMERIC_CLAIM"] for iss in issues)

def test_missing_source_span_blocks_narration():
    # Fact with missing source span
    fact = CanonicalFact(
        metric_key="operating_cf",
        value=7100.0,
        unit="AUD",
        scale="millions",
        basis="HC",
        period_type="A",
        period_end="2025-12-31",
        source_doc_id="doc1",
        source_page="5",
        source_span="" # MISSING
    )
    
    prose = "Operating cash flow was 7.1 billion."
    verified_prose, issues = verify_synthesis_claims(prose, [fact])
    
    assert "[UNSUPPORTED_NUMERIC_CLAIM]" in verified_prose
    assert any(iss["code"] == FAILURE_CODES["UNSUPPORTED_NUMERIC_CLAIM"] for iss in issues)

def test_viva_fy2025_regression_logic():
    # Mocking the Viva Energy failure scenario
    facts = [
        CanonicalFact("ebit", 437.0, "AUD", "millions", "RC", "A", "2025-12-31", "doc1", "2", "RC EBIT $437.0m"),
        CanonicalFact("operating_cf", 541.8, "AUD", "millions", "HC", "A", "2025-12-31", "doc1", "5", "Operating Cash Flow $541.8m"),
    ]
    
    # Claiming 7.1b OCF when fact is 541.8m
    prose = "EBIT was 437 million. Operating cash flow was 7.1 billion."
    verified_prose, issues = verify_synthesis_claims(prose, facts)
    
    assert "437 million" in verified_prose
    assert "[UNSUPPORTED_NUMERIC_CLAIM]" in verified_prose
    assert any("7.1 billion" in iss["message"] for iss in issues)
