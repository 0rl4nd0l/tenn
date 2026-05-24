from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.asx_appendix5b_parser import DATA_MISSING, parse_appendix5b_tables


@dataclass
class Table:
    page_number: int
    caption: str
    rows: list[list[str]]
    headers: list[str]


def _appendix5b_table(rows: list[list[str]]) -> Table:
    headers = ["Item", "Description", "Current quarter $A'000", "Year to date $A'000"]
    return Table(
        page_number=12,
        caption="Appendix 5B Mining exploration entity quarterly cash flow report",
        rows=[headers, *rows],
        headers=headers,
    )


def test_extracts_current_quarter_metrics_with_evidence() -> None:
    result = parse_appendix5b_tables(
        [
            _appendix5b_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "1,154", "5,308"],
                    ["2.6", "Net cash from / (used in) investing activities", "(2,656)", "(7,000)"],
                    ["3.10", "Net cash from / (used in) financing activities", "(5)", "(15)"],
                    ["4.6", "Cash and cash equivalents at end of period", "21,978", "21,978"],
                ]
            )
        ]
    )

    assert result.document_type == "appendix_5b"
    assert result.status == "parsed"

    metrics = result.metric_map()
    assert metrics["operating_cf"].value == Decimal("1154")
    assert metrics["investing_cf"].value == Decimal("-2656")
    assert metrics["financing_cf"].value == Decimal("-5")
    assert metrics["cash_end"].value == Decimal("21978")

    ocf = metrics["operating_cf"]
    assert ocf.currency == "AUD"
    assert ocf.scale == "thousands"
    assert ocf.column_role == "current_quarter"
    assert ocf.period_label == "Current quarter $A'000"
    assert ocf.trust_status == "candidate"
    assert ocf.evidence.page == 12
    assert ocf.evidence.line_item == "1.9"
    assert ocf.evidence.row_label == "1.9 | Net cash from / (used in) operating activities"
    assert ocf.evidence.column_label == "Current quarter $A'000"


def test_preserves_year_to_date_without_conflating_current_quarter() -> None:
    result = parse_appendix5b_tables(
        [
            _appendix5b_table(
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


def test_inherits_appendix5b_header_context_for_fragmented_numeric_headers() -> None:
    header_table = Table(
        page_number=12,
        caption="Appendix 5B Mining exploration entity quarterly cash flow report",
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
        page_number=12,
        caption="",
        rows=[
            ["3.10", "Net cash from / (used in) financing activities", "869", "869"],
        ],
        headers=["0", "1", "2", "3"],
    )

    result = parse_appendix5b_tables([header_table, fragmented_table])

    financing = result.metric_map()["financing_cf"]
    assert financing.value == Decimal("869")
    assert financing.currency == "AUD"
    assert financing.scale == "thousands"
    assert financing.column_role == "current_quarter"
    assert financing.period_label == "Current quarter $A'000"
    assert financing.evidence.column_label == "Current quarter $A'000"

    ytd_financing = result.metric_map(column_role="year_to_date")["financing_cf"]
    assert ytd_financing.period_label == "Year to date (6 months) $A'000"


def test_absent_lines_are_data_missing_not_zero() -> None:
    result = parse_appendix5b_tables(
        [
            _appendix5b_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "1", "4"],
                ]
            )
        ]
    )

    missing = result.missing_map()
    assert missing["investing_cf"].status == DATA_MISSING
    assert missing["investing_cf"].failure_reason == (
        "DATA_MISSING: current_quarter Appendix 5B line value not found"
    )
    assert result.metric_map()["operating_cf"].value == Decimal("1")
    assert "investing_cf" not in result.metric_map()


def test_uses_reconciliation_row_only_when_primary_line_value_missing() -> None:
    result = parse_appendix5b_tables(
        [
            _appendix5b_table(
                [
                    ["1.9", "Net cash from / (used in) operating activities", "(63)", "(63)"],
                    ["2.6", "Net cash from / (used in) investing activities", "-", "-"],
                    ["3.10", "Net cash from / (used in) financing activities", "-", "-"],
                    ["4.3", "Net cash from / (used in) investing activities (item 2.6 above)", "(5)", "(5)"],
                    ["4.6", "Cash and cash equivalents at end of period", "290", "290"],
                ]
            )
        ]
    )

    investing = result.metric_map()["investing_cf"]
    assert investing.value == Decimal("-5")
    assert investing.evidence.line_item == "4.3"
    assert investing.evidence.row_label == (
        "4.3 | Net cash from / (used in) investing activities (item 2.6 above)"
    )

    ytd_investing = result.metric_map(column_role="year_to_date")["investing_cf"]
    assert ytd_investing.value == Decimal("-5")
    assert ytd_investing.evidence.line_item == "4.3"


def test_reconciliation_row_does_not_duplicate_primary_line_candidate() -> None:
    result = parse_appendix5b_tables(
        [
            _appendix5b_table(
                [
                    ["2.6", "Net cash from / (used in) investing activities", "(624)", "(624)"],
                    ["4.3", "Net cash from / (used in) investing activities (item 2.6 above)", "(624)", "(624)"],
                ]
            )
        ]
    )

    current_investing = [
        candidate
        for candidate in result.candidates
        if candidate.metric_name == "investing_cf"
        and candidate.column_role == "current_quarter"
    ]
    assert len(current_investing) == 1
    assert current_investing[0].value == Decimal("-624")
    assert current_investing[0].evidence.line_item == "2.6"


def test_capex_sums_explicit_appendix5b_subitems_with_component_evidence() -> None:
    result = parse_appendix5b_tables(
        [
            _appendix5b_table(
                [
                    ["2.1(c)", "Payments to acquire property, plant and equipment", "(2,331)", "(5,000)"],
                    ["2.1(d)", "Payments for exploration and evaluation", "(23)", "(100)"],
                    ["1.9", "Net cash from / (used in) operating activities", "1,154", "5,308"],
                    ["2.6", "Net cash from / (used in) investing activities", "(2,656)", "(7,000)"],
                    ["3.10", "Net cash from / (used in) financing activities", "(5)", "(15)"],
                    ["4.6", "Cash and cash equivalents at end of period", "21,978", "21,978"],
                ]
            )
        ]
    )

    capex = result.metric_map()["capex"]
    assert capex.value == Decimal("-2354")
    assert capex.raw_value == "(2,331) + (23)"
    assert capex.evidence.line_item == "2.1(c)"
    assert [ev.line_item for ev in capex.component_evidence] == ["2.1(c)", "2.1(d)"]


def test_non_appendix5b_returns_not_applicable() -> None:
    result = parse_appendix5b_tables(
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
