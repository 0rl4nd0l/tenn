from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.services.asx_appendix4c_parser import DATA_MISSING, parse_appendix4c_tables


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
PRODUCTION_ROUTING_PATHS = [
    BACKEND_ROOT / "app" / "services" / "multipass_extraction.py",
    BACKEND_ROOT / "app" / "services" / "method_isolated_extraction.py",
    BACKEND_ROOT / "app" / "services" / "pipeline.py",
    BACKEND_ROOT / "app" / "services" / "docling_extract.py",
]


@dataclass
class Table:
    page_number: int
    caption: str
    rows: list[list[str]]
    headers: list[str]


def _appendix4c_table(rows: list[list[str]], headers: list[str] | None = None) -> Table:
    resolved_headers = headers or [
        "Item",
        "Description",
        "Current quarter $A'000",
        "Year to date $A'000",
    ]
    return Table(
        page_number=5,
        caption="Appendix 4C Quarterly cash flow report Rule 4.7B",
        rows=[resolved_headers, *rows],
        headers=resolved_headers,
    )


def test_extracts_explicit_appendix4c_cash_flow_candidates_with_evidence() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["1.1", "Receipts from customers", "1,250", "2,750"],
                    ["1.9", "Net cash from / (used in) operating activities", "(450)", "(900)"],
                    ["2.6", "Net cash from / (used in) investing activities", "(624)", "(700)"],
                    ["3.10", "Net cash from / (used in) financing activities", "869", "869"],
                    ["4.6", "Cash and cash equivalents at end of period", "702", "702"],
                ]
            )
        ]
    )

    assert result.document_type == "appendix_4c"
    assert result.status == "parsed"
    assert result.canonical_write is False

    metrics = result.metric_map()
    assert metrics["operating_cf"].value == Decimal("-450")
    assert metrics["investing_cf"].value == Decimal("-624")
    assert metrics["financing_cf"].value == Decimal("869")
    assert metrics["cash_end"].value == Decimal("702")

    operating = metrics["operating_cf"]
    assert operating.currency == "AUD"
    assert operating.scale == "thousands"
    assert operating.column_role == "current_quarter"
    assert operating.period_label == "Current quarter $A'000"
    assert operating.status == "candidate"
    assert operating.canonical_write is False
    assert operating.evidence.page == 5
    assert operating.evidence.line_item == "1.9"
    assert operating.evidence.row_label == "1.9 | Net cash from / (used in) operating activities"
    assert operating.evidence.column_label == "Current quarter $A'000"


def test_receipts_are_review_only_and_not_revenue() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["1.1", "Receipts from customers", "1,250", "2,750"],
                    ["1.9", "Net cash from / (used in) operating activities", "(450)", "(900)"],
                ]
            )
        ]
    )

    receipts = result.metric_map()["cash_receipts"]
    assert receipts.status == "review_only"
    assert receipts.trust_status == "review_only"
    assert receipts.canonical_write is False
    assert receipts.evidence.line_item == "1.1"
    assert "not revenue" in receipts.warnings[0]
    assert "revenue" not in result.metric_map()


def test_preserves_year_to_date_without_conflating_current_quarter() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "", "5,308"],
                    ["2.6", "Net cash from / (used in) investing activities", "(2,656)", "(7,000)"],
                    ["3.10", "Net cash from / (used in) financing activities", "(5)", "(15)"],
                    ["4.6", "Cash and cash equivalents at end of period", "21,978", "21,978"],
                ]
            )
        ]
    )

    assert "operating_cf" not in result.metric_map()
    assert result.missing_map()["operating_cf"].status == DATA_MISSING

    ytd_metrics = result.metric_map(column_role="year_to_date")
    assert ytd_metrics["operating_cf"].value == Decimal("5308")
    assert ytd_metrics["operating_cf"].period_label == "Year to date $A'000"


def test_absent_lines_are_data_missing_not_zero() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "1", "4"],
                ]
            )
        ]
    )

    missing = result.missing_map()
    assert missing["investing_cf"].status == DATA_MISSING
    assert missing["investing_cf"].failure_reason == (
        "DATA_MISSING: current_quarter Appendix 4C line value not found"
    )
    assert result.metric_map()["operating_cf"].value == Decimal("1")
    assert "investing_cf" not in result.metric_map()


def test_detects_usd_thousand_header_without_runtime_or_llm() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "11", "44"],
                ],
                headers=["Item", "Description", "Current quarter $USD'000", "Year to date $USD'000"],
            )
        ]
    )

    operating = result.metric_map()["operating_cf"]
    assert operating.currency == "USD"
    assert operating.scale == "thousands"


def test_inherits_header_context_for_fragmented_numeric_headers() -> None:
    header_table = Table(
        page_number=4,
        caption="Appendix 4C Quarterly cash flow report Rule 4.7B",
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date (6 months) $A'000",
            ]
        ],
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date (6 months) $A'000",
        ],
    )
    fragmented_table = Table(
        page_number=5,
        caption="",
        rows=[
            ["3.10", "Net cash from / (used in) financing activities", "869", "869"],
        ],
        headers=["0", "1", "2", "3"],
    )

    result = parse_appendix4c_tables([header_table, fragmented_table])

    financing = result.metric_map()["financing_cf"]
    assert financing.value == Decimal("869")
    assert financing.currency == "AUD"
    assert financing.scale == "thousands"
    assert financing.column_role == "current_quarter"
    assert financing.period_label == "Current quarter $A'000"
    assert financing.evidence.column_label == "Current quarter $A'000"

    ytd_financing = result.metric_map(column_role="year_to_date")["financing_cf"]
    assert ytd_financing.period_label == "Year to date (6 months) $A'000"


def test_uses_5_5_cash_end_when_4_6_is_absent() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["5.5", "Cash and cash equivalents at end of quarter", "702", "702"],
                ]
            )
        ]
    )

    cash_end = result.metric_map()["cash_end"]
    assert cash_end.value == Decimal("702")
    assert cash_end.evidence.line_item == "5.5"


def test_non_appendix4c_returns_not_applicable() -> None:
    result = parse_appendix4c_tables(
        [
            Table(
                page_number=3,
                caption="Consolidated statement of profit or loss",
                rows=[["Revenue", "100"], ["Profit", "20"]],
                headers=["Metric", "$m"],
            )
        ]
    )

    assert result.status == "not_applicable"
    assert result.document_type == "unknown"
    assert result.candidates == []
    assert result.missing == []


def test_appendix5b_is_not_parsed_as_appendix4c() -> None:
    result = parse_appendix4c_tables(
        [
            Table(
                page_number=3,
                caption="Appendix 5B Mining exploration entity quarterly cash flow report",
                rows=[["1.9", "Net cash from / (used in) operating activities", "100"]],
                headers=["Item", "Description", "Current quarter $A'000"],
            )
        ]
    )

    assert result.status == "not_applicable"
    assert result.document_type == "unknown"


def test_to_dict_keeps_report_local_canonical_write_false() -> None:
    result = parse_appendix4c_tables(
        [
            _appendix4c_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "(450)", "(900)"],
                ]
            )
        ]
    )

    payload = result.to_dict()
    assert payload["canonical_write"] is False
    assert payload["candidates"][0]["canonical_write"] is False


def test_production_routing_files_do_not_import_appendix4c_parser() -> None:
    for path in PRODUCTION_ROUTING_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "asx_appendix4c_parser" not in source, path
