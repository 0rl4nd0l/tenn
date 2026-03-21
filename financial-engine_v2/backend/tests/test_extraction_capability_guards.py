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
    The LLM extraction prompt must declare operating_cf and capex as extractable
    metrics with the expected type annotation.

    If this fails, a field was renamed, typo'd, or dropped from the prompt schema.
    Fix: restore the field in extraction.py:build_prompt() and confirm the LLM
    output parser and _upsert_financial_rows both use the same name.
    """
    from app.services.extraction import build_prompt

    prompt = build_prompt("")

    required = {
        '"operating_cf": "number|null"',
        '"investing_cf": "number|null"',
        '"financing_cf": "number|null"',
        '"capex": "number|null"',
        '"cash_end": "number|null"',
        '"net_debt": "number|null"',
    }
    missing = {fragment for fragment in required if fragment not in prompt}
    assert not missing, (
        "Extraction prompt is missing required cash-flow schema fields.\n"
        f"Missing: {sorted(missing)}\n"
        "Update build_prompt() in extraction.py or fix this test if the field "
        "was intentionally renamed (update both prompt and _upsert_financial_rows)."
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
# Guard E — Incomplete migration: cashflow_layout_adapter not yet merged
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=False,
    reason=(
        "INCOMPLETE MIGRATION — cashflow_layout_adapter.py and section_capture_layer.py "
        "exist on main and in the script-test suite but are not present in this branch "
        "(cloud/session-20260319). The merge commit 41476da1 had no effect. "
        "Until these are merged, multi-column/multi-page capex reconstruction and "
        "section continuation indexing are unavailable. "
        "Resolution: merge main → cloud/session-20260319 or cherry-pick "
        "commits 710fe968 and af7f8e57. "
        "This xfail documents the gap; it does not block CI."
    ),
)
def test_cashflow_layout_adapter_present():
    """
    cashflow_layout_adapter.py must be present in the scripts/ directory.
    This test is xfail because the module is on main but not yet merged
    into this branch. It will start passing once the merge is complete.
    """
    scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
    adapter_path = scripts_dir / "cashflow_layout_adapter.py"
    assert adapter_path.exists(), (
        f"cashflow_layout_adapter.py missing at {adapter_path}. "
        "See xfail reason above for resolution steps."
    )
