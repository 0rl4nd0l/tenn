import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


from app.services.multipass_extraction import (  # noqa: E402
    _find_profit_after_tax_row,
    _repair_np_attributable_from_income_statement,
    _run_pass4_reconciler,
    _validate_gate,
)


def test_profit_after_income_tax_ordinary_activities_alias_repairs_np_attributable():
    markdown = """| Item | 2025 | 2024 |
| --- | --- | --- |
| Revenue | 100 | 90 |
| Profit after income tax expense from ordinary activities | 16 | 11 |
"""
    merged_metrics = {"np_attributable": None}
    row_refs = {"np_attributable": "Profit after income tax expense from ordinary activities"}
    provenance = {
        "np_attributable": "income_statement:page_1:Profit after income tax expense from ordinary activities"
    }
    markdown_map = {"np_attributable": markdown}
    pass1_result = {"scale": "units"}

    _repair_np_attributable_from_income_statement(
        merged_metrics,
        row_refs,
        provenance,
        markdown_map,
        pass1_result,
    )

    assert merged_metrics["np_attributable"] == 16.0
    assert row_refs["np_attributable"] == "Profit after income tax expense from ordinary activities"
    assert provenance["np_attributable"] == "income_statement:deterministic:Profit after income tax expense from ordinary activities"


def test_pre_tax_and_comprehensive_income_rows_do_not_match_profit_after_tax_alias():
    rows = [
        ["", "Item", "2025", "2024", ""],
        ["", "Profit before income tax expense from ordinary activities", "25", "23", ""],
        ["", "Total comprehensive income for the year", "20", "18", ""],
    ]

    assert _find_profit_after_tax_row(rows) is None


def test_disclosure_only_nta_dividends_record_date_rows_do_not_repair_np_attributable():
    markdown = """| Item | 2025 | 2024 |
| --- | --- | --- |
| NTA per security | 1.23 | 1.20 |
| Dividends / distributions | 0.10 | 0.09 |
| Record date | 2026-01-31 | 2025-01-31 |
"""
    merged_metrics = {"np_attributable": None}
    row_refs = {"np_attributable": "NTA per security"}
    provenance = {"np_attributable": "income_statement:page_1:NTA per security"}
    markdown_map = {"np_attributable": markdown}
    pass1_result = {"scale": "units"}

    result = _repair_np_attributable_from_income_statement(
        merged_metrics,
        row_refs,
        provenance,
        markdown_map,
        pass1_result,
    )

    assert result is None
    assert merged_metrics["np_attributable"] is None


@pytest.mark.parametrize(
    "row_ref",
    [
        "NTA per security",
        "Dividends / distributions",
        "Record date for determining entitlement to the",
    ],
)
def test_disclosure_only_wrapper_rows_do_not_repair_np_attributable_for_wrapper_labels(row_ref: str):
    markdown = """| Item | 2025 | 2024 |
| --- | --- | --- |
| NTA per security | 1.23 | 1.20 |
| Dividends / distributions | 0.10 | 0.09 |
| Record date for determining entitlement to the | 2026-01-31 | 2025-01-31 |
"""
    merged_metrics = {"np_attributable": None}
    row_refs = {"np_attributable": row_ref}
    provenance = {"np_attributable": f"income_statement:page_1:{row_ref}"}
    markdown_map = {"np_attributable": markdown}
    pass1_result = {"scale": "units"}

    result = _repair_np_attributable_from_income_statement(
        merged_metrics,
        row_refs,
        provenance,
        markdown_map,
        pass1_result,
    )

    assert result is None
    assert merged_metrics["np_attributable"] is None


def test_validate_gate_still_blocks_when_only_disclosure_rows_exist():
    payload = {
        "period_end": "2025-12-31",
        "period_type": "H",
        "scale": "units",
        "currency": "AUD",
        "metrics": {
            "revenue": None,
            "ebit": None,
            "np_attributable": None,
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        },
        "confidence_metrics": 0.9,
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:insufficient_metrics:0"


def test_run_pass4_reconciler_accepts_ordinary_activities_alias():
    pass3a = [
        {
            "_source": "income_statement",
            "_page_number": 24,
            "revenue": 100,
            "ebit": 20,
            "np_attributable": None,
            "pass3_confidence": 0.9,
            "row_refs": {"np_attributable": "Profit after income tax expense from ordinary activities"},
            "_markdown": """| Item | 2025 | 2024 |
| --- | --- | --- |
| Revenue | 100 | 90 |
| Profit after income tax expense from ordinary activities | 16 | 11 |
""",
        }
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
    pass1 = {"period_type": "A", "period_end": "2025-12-31", "scale": "units"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert result["metrics"]["np_attributable"] == 16.0
    assert result["row_refs"]["np_attributable"] == "Profit after income tax expense from ordinary activities"
