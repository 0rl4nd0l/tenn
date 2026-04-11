"""
Extraction capability guards — regression protections for OCF/capex pipeline.

These tests protect against silent removal of cash-flow extraction capability
from the backend LLM extraction path (extraction.py → pipeline.py → DB).

They do NOT test the script-based PDF layout extraction pipeline
(scripts/extract_financial_metrics.py, cashflow_layout_adapter.py) — that
path has its own test suite in scripts/test_cashflow_*.py.

Background on the dual extraction architecture:
  1. Backend LLM path: build_prompt() → Ollama JSON → _upsert_financial_rows()
     Handles: operating_cf, capex, investing_cf, financing_cf, cash_end, net_debt
  2. Script layout path: extract_financial_metrics.py → cashflow_layout_adapter.py
     More precise, handles multi-column/multi-page cash flow table layouts.
     Currently on main branch only; NOT present in cloud/session-20260319.
     See: test_cashflow_layout_adapter.py (skipped in this branch).

These guards ensure path (1) cannot regress silently.
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Guard A — Extraction prompt schema declares all cash-flow fields
# ---------------------------------------------------------------------------

def test_extraction_prompt_declares_cashflow_metrics():
    """
    Pass 3a in multipass_extraction must declare all 10 metric fields
    in its per-table extraction schema. Replaces the old extraction.py guard.

    If this fails: a metric was dropped from METRIC_FIELDS in
    multipass_extraction.py. Restore it and update _upsert_financial_rows.
    """
    from app.services.multipass_extraction import METRIC_FIELDS

    required = {
        "revenue", "ebit", "np_attributable",
        "operating_cf", "investing_cf", "financing_cf",
        "capex", "cash_end", "net_debt", "shares_outstanding",
    }
    missing = required - set(METRIC_FIELDS)
    assert not missing, (
        f"multipass_extraction.METRIC_FIELDS is missing: {sorted(missing)}\n"
        "Restore the field in METRIC_FIELDS and in _upsert_financial_rows."
    )


# ---------------------------------------------------------------------------
# Guard B — DB model declares all cash-flow columns
# ---------------------------------------------------------------------------

def test_asx_periodic_financials_model_has_cashflow_columns():
    """
    The ASXPeriodicFinancial SQLAlchemy model must contain all cash-flow
    columns. If this fails, a column was dropped or renamed in the model
    (and likely in the migration too).

    Fix: restore the column in asx_financials.py and add an Alembic migration.
    """
    from sqlalchemy import inspect as sa_inspect
    from app.models.asx_financials import ASXPeriodicFinancial

    mapper = sa_inspect(ASXPeriodicFinancial)
    col_names = {col.key for col in mapper.mapper.columns}

    required = {"operating_cf", "investing_cf", "financing_cf", "capex", "cash_end", "net_debt"}
    missing = required - col_names
    assert not missing, (
        f"ASXPeriodicFinancial model is missing columns: {sorted(missing)}\n"
        "Restore in asx_financials.py and create an Alembic migration."
    )


def test_asx_structured_models_have_created_at():
    """created_at must exist for parity with extraction_runs monitoring queries."""
    from sqlalchemy import inspect as sa_inspect
    from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote

    for model in (ASXPeriodicFinancial, ASXRiskNote):
        names = {col.key for col in sa_inspect(model).mapper.columns}
        assert "created_at" in names, f"{model.__name__} must declare created_at"


# ---------------------------------------------------------------------------
# Guard C — Pipeline upsert field list includes all cash-flow fields
# ---------------------------------------------------------------------------

def test_pipeline_upsert_field_list_includes_cashflow_fields():
    """
    _upsert_financial_rows() must iterate over all cash-flow fields when
    writing to the DB. If this fails, a field was removed from the for-loop
    and extractions will silently stop being persisted.

    Detection strategy: parse the source of _upsert_financial_rows and assert
    the field name strings appear in the source literal.
    """
    import inspect
    from app.services.pipeline import _upsert_financial_rows

    source = inspect.getsource(_upsert_financial_rows)

    required_fields = ["operating_cf", "investing_cf", "financing_cf", "capex", "cash_end", "net_debt"]
    missing = [f for f in required_fields if f'"{f}"' not in source and f"'{f}'" not in source]
    assert not missing, (
        f"_upsert_financial_rows is missing field(s): {missing}\n"
        "These fields must appear in the for-loop field list in pipeline.py. "
        "Absent fields are extracted by the LLM but never written to the DB."
    )


# ---------------------------------------------------------------------------
# Guard D — Backend does not depend on camelot
# ---------------------------------------------------------------------------

def test_backend_does_not_depend_on_camelot():
    """
    The backend must NOT list camelot as a dependency. Camelot is used only
    in the script-based PDF layout pipeline (scripts/), which runs in an
    isolated venv (.venv_main/) separate from the backend.

    If camelot were added here it would introduce a heavy optional dependency
    with platform-specific native libs (ghostscript, opencv) into the backend
    container image.

    The backend's PDF extraction uses docling.
    """
    req_file = Path(__file__).resolve().parent.parent / "requirements.txt"
    assert req_file.exists(), f"Backend requirements.txt not found at {req_file}"

    content = req_file.read_text(encoding="utf-8")
    lines = [line.strip().lower() for line in content.splitlines() if line.strip()]

    camelot_lines = [line for line in lines if line.startswith("camelot")]
    assert not camelot_lines, (
        f"camelot found in backend requirements: {camelot_lines}\n"
        "camelot belongs only in the scripts/.venv_main/ environment, not the backend."
    )

    docling_lines = [line for line in lines if "docling" in line]
    assert docling_lines, (
        "docling not found in backend requirements.txt. "
        "The backend uses docling for PDF table extraction; ensure it stays present."
    )


# ---------------------------------------------------------------------------
# Guard E — Cashflow layout modules must be present in scripts/
# ---------------------------------------------------------------------------

def test_cashflow_layout_modules_present():
    """
    Regression guard: cashflow_layout_adapter.py, section_capture_layer.py, and
    cashflow_table_fallback.py must all be present in scripts/.

    If this fails, the layout modules were lost (e.g., branch diverged from main
    again). Restore with:
        git checkout main -- cashflow_layout_adapter.py section_capture_layer.py \\
            cashflow_table_fallback.py balance_sheet_forensic_analysis.py
        cp <each file> scripts/
    """
    scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
    required = [
        "cashflow_layout_adapter.py",
        "section_capture_layer.py",
        "cashflow_table_fallback.py",
    ]
    missing = [f for f in required if not (scripts_dir / f).exists()]
    assert not missing, (
        f"Layout modules missing from scripts/: {missing}. "
        "Restore from main branch — see docstring for commands."
    )


# ---------------------------------------------------------------------------
# Guard F — docling_extract module is present and importable
# ---------------------------------------------------------------------------

def test_docling_extract_module_importable():
    """
    services/docling_extract.py must exist and be importable.
    If this fails: the module was deleted or has a syntax error.
    Fix: restore docling_extract.py and verify `from app.services.docling_extract import extract_structured`.
    """
    try:
        from app.services.docling_extract import extract_structured  # noqa: F401
    except ImportError as e:
        raise AssertionError(
            f"Cannot import extract_structured from docling_extract: {e}\n"
            "Ensure docling_extract.py exists in app/services/."
        ) from e


# ---------------------------------------------------------------------------
# Guard G — Validation gate rejects missing period_end
# ---------------------------------------------------------------------------

def test_validation_gate_rejects_missing_period_end():
    """
    _validate_gate() must return status='failed' when period_end is None.
    If this fails: the gate was weakened and bad extractions will reach the DB.
    """
    from app.services.multipass_extraction import _validate_gate

    payload = {
        "period_type": "H",
        "period_end": None,
        "metrics": {"operating_cf": 1000, "revenue": 2000, "cash_end": 500},
        "confidence_metrics": 0.9,
    }
    status, error = _validate_gate(payload)
    assert status == "failed", f"Expected 'failed', got '{status}'"
    assert error is not None


# ---------------------------------------------------------------------------
# Guard H — Validation gate rejects fewer than 3 non-null metrics
# ---------------------------------------------------------------------------

def test_validation_gate_rejects_insufficient_metrics():
    """
    _validate_gate() must return status='failed' when fewer than 3 metrics are non-null.
    If this fails: sparse extractions will pollute the financial history table.
    """
    from app.services.multipass_extraction import _validate_gate

    payload = {
        "period_type": "H",
        "period_end": "2024-12-31",
        "metrics": {"operating_cf": 1000, "revenue": None, "cash_end": None,
                    "ebit": None, "np_attributable": None, "investing_cf": None,
                    "financing_cf": None, "capex": None, "net_debt": None,
                    "shares_outstanding": None},
        "confidence_metrics": 0.9,
    }
    status, error = _validate_gate(payload)
    assert status == "failed", f"Expected 'failed', got '{status}'"
