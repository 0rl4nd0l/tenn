#!/usr/bin/env python3
"""
broad_extraction_test.py — Robustness test for multipass extraction across
hundreds of random ASX financial filings.

NOT an accuracy test (no ground truth). Measures:
  - Crash rate, status distribution, error classification
  - Per-metric coverage (how often each metric is non-null)
  - Structural validity (period_end, period_type, scale)
  - Sanity checks (revenue > 0, shares > 0 when present)
  - Timing: per-doc P50/P95/P99

Usage:
  python scripts/broad_extraction_test.py --count 200 --seed 42
  python scripts/broad_extraction_test.py --count 50 --resume   # pick up where left off
  python scripts/broad_extraction_test.py --count 200 --anthropic  # use Anthropic API

Requires: llama.cpp on :8001 (or --anthropic flag with ANTHROPIC_API_KEY set)
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import logging
import os
import random
import statistics
import sys
import time
import traceback
from pathlib import Path

# Add backend to path so we can import app.services
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

# Ensure extraction routes to the correct llama.cpp endpoint.
# Router mode: single server on 8001 handles both chat and extraction.
# EXTRACTION_LLAMACPP_URL is legacy; defaults to LLAMACPP_URL when unset.
if not os.environ.get("EXTRACTION_LLAMACPP_URL"):
    os.environ["EXTRACTION_LLAMACPP_URL"] = os.environ.get("LLAMACPP_URL", "http://127.0.0.1:8001")

# Auto-detect LLM_API_KEY from llama-server process args if not already set
if not os.environ.get("LLM_API_KEY"):
    import subprocess as _sp
    try:
        _ps = _sp.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5,
        )
        for _line in _ps.stdout.splitlines():
            if "llama-server" in _line and "--api-key" in _line:
                _parts = _line.split("--api-key")
                if len(_parts) > 1:
                    _key = _parts[1].strip().split()[0]
                    os.environ["LLM_API_KEY"] = _key
                    break
    except Exception:
        pass
# Suppress noisy loggers during bulk runs
for name in ("httpx", "httpcore", "urllib3", "app.services.llm"):
    logging.getLogger(name).setLevel(logging.ERROR)

METRIC_FIELDS = [
    "revenue", "ebit", "np_attributable",
    "operating_cf", "investing_cf", "financing_cf",
    "capex", "cash_end", "net_debt", "shares_outstanding",
]

DOLLAR_METRIC_FIELDS = [m for m in METRIC_FIELDS if m != "shares_outstanding"]
REVENUE_RATIO_RISK_FIELDS = [
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
]
REVENUE_RATIO_REVIEW_THRESHOLD = 10.0

DOCS_ROOT = _REPO_ROOT / "data" / "asx" / "docs"
RESULTS_DIR = _REPO_ROOT / "scripts" / "broad_test_results"

SCALE_RISK_THRESHOLDS: dict[str, dict[str, float]] = {
    "A": {
        "revenue": 1_000_000,
        "ebit": 100_000,
        "np_attributable": 100_000,
        "operating_cf": 100_000,
    },
    "H": {
        "revenue": 500_000,
        "ebit": 50_000,
        "np_attributable": 50_000,
        "operating_cf": 50_000,
    },
    "Q": {
        "revenue": 100_000,
        "ebit": 10_000,
    },
}

DEFAULT_NATIVE_SANITY_CAP = 500_000_000_000
HIGH_DENOMINATION_NATIVE_SANITY_CAPS = {
    "IDR": 10_000_000_000_000_000,
}

SCALE_TABLE_PROVENANCE_REQUIRED_FIELDS = [
    "document_id",
    "ticker",
    "source_path",
    "source_document_class",
    "status",
    "error",
    "selected_table_label",
    "selected_page_number",
    "table_index",
    "table_caption",
    "table_headers",
    "table_local_scale",
    "same_page_scale",
    "document_level_scale",
    "metric_name",
    "row_label",
    "row_ref",
    "period_column",
    "value_cell_text",
    "raw_value",
    "normalized_value",
    "scale_source",
    "metric_source_scales",
    "metric_scale_sources",
    "common_metric_source_scale_input",
    "common_metric_source_scale_output",
    "final_gate",
]


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "unknown"}:
        return None
    return text


def _first_text(*values: object) -> str | None:
    for value in values:
        text = _clean_text(value)
        if text is not None:
            return text
    return None


def _clean_page_number(value: object) -> object | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null", "unknown"}:
        return None
    return value


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _coerce_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_currency_code(raw: object) -> str:
    text = _clean_text(raw)
    return (text or "AUD").upper()


def _native_currency_sanity_cap(raw_currency: object) -> int:
    return HIGH_DENOMINATION_NATIVE_SANITY_CAPS.get(
        _normalize_currency_code(raw_currency),
        DEFAULT_NATIVE_SANITY_CAP,
    )


def _build_metric_provenance_audit(payload: dict) -> dict:
    """Build compact per-metric provenance for broad-run artifacts."""
    metrics = _as_dict(payload.get("metrics"))
    row_refs = _as_dict(payload.get("row_refs"))
    provenance = _as_dict(payload.get("provenance"))
    field_provenance = _as_dict(payload.get("field_provenance"))
    metric_source_scales = _as_dict(payload.get("metric_source_scales"))
    metric_scale_sources = _as_dict(payload.get("metric_scale_sources"))

    metric_provenance: dict[str, dict] = {}
    metrics_with_values: list[str] = []
    metrics_with_provenance: list[str] = []
    metrics_missing_provenance: list[str] = []

    for metric_name in METRIC_FIELDS:
        if metrics.get(metric_name) is None:
            continue

        metrics_with_values.append(metric_name)
        field = _as_dict(field_provenance.get(metric_name))
        row_ref = _first_text(field.get("row_ref"), row_refs.get(metric_name))
        excerpt = _clean_text(field.get("excerpt"))
        provenance_ref = _clean_text(provenance.get(metric_name))
        source = _clean_text(field.get("source"))
        table_label = _clean_text(field.get("table_label"))
        page_number = _clean_page_number(field.get("page_number"))
        page_tag = _clean_text(field.get("page_tag"))
        metric_source_scale = _first_text(
            field.get("scale"),
            metric_source_scales.get(metric_name),
        )
        metric_scale_source = _first_text(
            field.get("scale_source"),
            metric_scale_sources.get(metric_name),
        )

        missing_fields: list[str] = []
        for field_name, field_value in (
            ("row_ref", row_ref),
            ("excerpt", excerpt),
            ("source", source),
            ("table_label", table_label),
            ("page_number", page_number),
            ("provenance_reference", provenance_ref),
            ("metric_source_scale", metric_source_scale),
            ("metric_scale_source", metric_scale_source),
        ):
            if field_value is None:
                missing_fields.append(field_name)
        if not field:
            missing_fields.append("field_provenance")

        provenance_available = any(
            value is not None
            for value in (
                row_ref,
                excerpt,
                provenance_ref,
                source,
                table_label,
                page_number,
                page_tag,
            )
        )
        if provenance_available:
            metrics_with_provenance.append(metric_name)
        else:
            metrics_missing_provenance.append(metric_name)

        metric_provenance[metric_name] = {
            "value": metrics.get(metric_name),
            "row_ref": row_ref,
            "excerpt": excerpt,
            "source_snippet": excerpt or row_ref,
            "source": source,
            "table_label": table_label,
            "page_number": page_number,
            "page_tag": page_tag,
            "provenance_reference": provenance_ref,
            "field_provenance": field,
            "metric_source_scale": metric_source_scale,
            "metric_scale_source": metric_scale_source,
            "missing_fields": missing_fields,
            "provenance_available": provenance_available,
            "provenance_missing": not provenance_available,
        }

    return {
        "metric_provenance": metric_provenance,
        "metrics_with_values": metrics_with_values,
        "metrics_with_provenance": metrics_with_provenance,
        "metrics_missing_provenance": metrics_missing_provenance,
        "provenance_available": metrics_with_provenance,
        "provenance_missing": metrics_missing_provenance,
        "provenance_available_count": len(metrics_with_provenance),
        "provenance_missing_count": len(metrics_missing_provenance),
        "document_provenance_available": bool(metrics_with_provenance),
        "document_provenance_missing": bool(metrics_missing_provenance),
    }


def _risk_flag(code: str, severity: str, reason: str, **details: object) -> dict:
    flag = {
        "code": code,
        "severity": severity,
        "reason": reason,
    }
    flag.update({key: value for key, value in details.items() if value is not None})
    return flag


def _build_scale_magnitude_risk(payload: dict, *, accepted_output: bool) -> dict:
    """Build machine-readable accepted-output scale and magnitude review flags."""
    metrics = _as_dict(payload.get("metrics"))
    period_type = _clean_text(payload.get("period_type")) or "A"
    scale = (_clean_text(payload.get("scale")) or "unknown").lower()
    currency = _normalize_currency_code(payload.get("currency"))
    sanity_cap = _native_currency_sanity_cap(currency)
    flags: list[dict] = []

    non_null_dollar_metrics = {
        metric_name: _coerce_number(metrics.get(metric_name))
        for metric_name in DOLLAR_METRIC_FIELDS
        if metrics.get(metric_name) is not None
    }
    non_null_dollar_metrics = {
        metric_name: value
        for metric_name, value in non_null_dollar_metrics.items()
        if value is not None
    }

    if non_null_dollar_metrics and scale == "unknown":
        flags.append(
            _risk_flag(
                "scale_unknown_with_metrics",
                "review",
                "record has non-null dollar metrics but payload scale is unknown",
                metrics=sorted(non_null_dollar_metrics),
            )
        )

    for metric_name, value in non_null_dollar_metrics.items():
        if abs(value) > sanity_cap:
            flags.append(
                _risk_flag(
                    "metric_exceeds_native_sanity_cap",
                    "review",
                    "metric magnitude exceeds native currency sanity cap",
                    metric=metric_name,
                    value=value,
                    threshold=sanity_cap,
                    currency=currency,
                )
            )

    thresholds = SCALE_RISK_THRESHOLDS.get(period_type, SCALE_RISK_THRESHOLDS["A"])
    checked: dict[str, float] = {}
    below_threshold: dict[str, float] = {}
    for metric_name, minimum in thresholds.items():
        value = non_null_dollar_metrics.get(metric_name)
        if value is None:
            continue
        checked[metric_name] = value
        if abs(value) < minimum:
            below_threshold[metric_name] = value
    if checked and len(checked) == len(below_threshold):
        flags.append(
            _risk_flag(
                "all_checked_metrics_below_minimum",
                "review",
                "all checked metrics fall below loose minimum scale thresholds",
                metrics=below_threshold,
                period_type=period_type,
                thresholds={name: thresholds[name] for name in below_threshold},
            )
        )

    metric_source_scales = {
        metric_name: scale_value.lower()
        for metric_name, scale_value in (
            (name, _clean_text(value))
            for name, value in _as_dict(payload.get("metric_source_scales")).items()
        )
        if metric_name in non_null_dollar_metrics and scale_value
    }
    distinct_metric_scales = sorted(set(metric_source_scales.values()))
    if len(distinct_metric_scales) > 1:
        flags.append(
            _risk_flag(
                "mixed_metric_source_scales",
                "review",
                "non-null dollar metrics carry multiple source scales",
                metric_source_scales=metric_source_scales,
                distinct_scales=distinct_metric_scales,
            )
        )

    if scale != "unknown":
        mismatched_scales = {
            metric_name: metric_scale
            for metric_name, metric_scale in metric_source_scales.items()
            if metric_scale != scale
        }
        if mismatched_scales:
            flags.append(
                _risk_flag(
                    "payload_scale_differs_from_metric_source_scale",
                    "review",
                    "payload scale differs from one or more metric-local source scales",
                    payload_scale=scale,
                    metric_source_scales=mismatched_scales,
                )
            )

    missing_source_scale = sorted(
        metric_name
        for metric_name in non_null_dollar_metrics
        if metric_name not in metric_source_scales
    )
    if missing_source_scale:
        flags.append(
            _risk_flag(
                "metric_source_scale_missing",
                "info",
                "metric-local source scale is missing for non-null dollar metrics",
                metrics=missing_source_scale,
            )
        )

    revenue = non_null_dollar_metrics.get("revenue")
    if revenue is not None and abs(revenue) > 0:
        for metric_name in REVENUE_RATIO_RISK_FIELDS:
            value = non_null_dollar_metrics.get(metric_name)
            if value is None:
                continue
            ratio = abs(value) / abs(revenue)
            if ratio >= REVENUE_RATIO_REVIEW_THRESHOLD:
                flags.append(
                    _risk_flag(
                        "metric_revenue_ratio_high",
                        "review",
                        "metric magnitude is unusually high relative to revenue",
                        metric=metric_name,
                        value=value,
                        revenue=revenue,
                        ratio=round(ratio, 4),
                        threshold=REVENUE_RATIO_REVIEW_THRESHOLD,
                    )
                )

    risk_level = "none"
    if any(flag["severity"] == "review" for flag in flags):
        risk_level = "review"
    elif flags:
        risk_level = "info"

    return {
        "accepted_output": accepted_output,
        "risk_level": risk_level,
        "flag_count": len(flags),
        "flag_codes": [flag["code"] for flag in flags],
        "flags": flags,
    }


def _scale_harness_case(
    *,
    ticker: str,
    document_id: str,
    case_role: str,
    expected_document_class: str,
    expected_status_or_gate: str,
    source_path: str,
    selected_table_or_page: str,
    table_local_scale_evidence: str,
    same_page_scale_evidence: str,
    document_level_scale_evidence: str,
    forbidden_outputs: list[str],
    current_behavior_expected_or_bug: str,
    root_cause_group: str,
    source_artifacts: list[str],
) -> dict:
    return {
        "ticker": ticker,
        "document_id": document_id,
        "case_role": case_role,
        "expected_document_class": expected_document_class,
        "expected_status_or_gate": expected_status_or_gate,
        "source_path": source_path,
        "selected_table_or_page": selected_table_or_page,
        "table_local_scale_evidence": table_local_scale_evidence,
        "same_page_scale_evidence": same_page_scale_evidence,
        "document_level_scale_evidence": document_level_scale_evidence,
        "row_cell_provenance_fields_required": list(SCALE_TABLE_PROVENANCE_REQUIRED_FIELDS),
        "forbidden_outputs": forbidden_outputs,
        "current_behavior_expected_or_bug": current_behavior_expected_or_bug,
        "root_cause_group": root_cause_group,
        "source_artifacts": source_artifacts,
    }


_COUNT24_REPORT_ROOT = (
    "/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/"
    "extraction_count24_bounded_validation_v1_20260607"
)

_SCALE_TABLE_HARNESS_CASES = [
    _scale_harness_case(
        ticker="AZJ",
        document_id="488d6f1a-0180-4fca-8dcf-c4cdfc0f342e",
        case_role="scale_unknown_same_page_scale_candidate",
        expected_document_class="financial_report",
        expected_status_or_gate="validation_gate:scale_unknown",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/AZJ/financial_performance/"
            "2025-08-18_aurizon-network-pty-ltd-full-year-report_488d6f1a-0180-4fca-8dcf-c4cdfc0f342e.pdf"
        ),
        selected_table_or_page=(
            "income_statement p9, balance_sheet p11, cashflow_statement p13, "
            "highlights p16, share_capital p39"
        ),
        table_local_scale_evidence="unknown on selected tables; selected rows include $m headers in parser markdown",
        same_page_scale_evidence="millions on income, balance, cash-flow, and share-capital pages; unknown on highlights",
        document_level_scale_evidence="unknown in persisted count-24 payload and first selected-table diagnostic",
        forbidden_outputs=[
            "ok with scale=unknown",
            "same-page millions propagated to highlight rows without metric-local binding",
            "nearest-$100k rounding accepted without a source-bound policy",
        ],
        current_behavior_expected_or_bug="bug_candidate: fail-closed is correct, but same-page millions needs metric-local binding proof",
        root_cause_group="same_page_scale_candidate_not_repeated",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/diagnostic_results.json",
            "reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/provenance_capture.json",
        ],
    ),
    _scale_harness_case(
        ticker="EDU",
        document_id="ac3c9ab0-e01a-4996-95f9-6466388ddc9c",
        case_role="scale_unknown_mixed_selected_surfaces",
        expected_document_class="financial_report",
        expected_status_or_gate="validation_gate:scale_unknown",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/EDU/financial_performance/"
            "2024-02-27_2023-annual-report_ac3c9ab0-e01a-4996-95f9-6466388ddc9c.pdf"
        ),
        selected_table_or_page=(
            "income_statement p6, highlights p7, share_capital p44, "
            "balance_sheet p51, cashflow_statement p53"
        ),
        table_local_scale_evidence="unknown on selected tables",
        same_page_scale_evidence=(
            "units on selected balance and cash-flow pages; unknown on income, "
            "highlights, and share-capital selected surfaces"
        ),
        document_level_scale_evidence="unknown in persisted count-24 payload",
        forbidden_outputs=[
            "document-wide units propagated across mixed selected surfaces",
            "corporate snapshot/highlights promoted as clean formal statement evidence",
            "ok without per-metric scale_source and row/cell provenance",
        ],
        current_behavior_expected_or_bug="expected_safe_fail: mixed selected surfaces must fail closed",
        root_cause_group="mixed_selected_surfaces_fail_closed",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/diagnostic_results.json",
            "reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/provenance_capture.json",
        ],
    ),
    _scale_harness_case(
        ticker="WHC",
        document_id="9640d9f1-a45b-492d-8df5-9bad0f46431c",
        case_role="scale_unknown_parser_table_coverage_gap",
        expected_document_class="financial_report",
        expected_status_or_gate="validation_gate:scale_unknown",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/"
            "2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf"
        ),
        selected_table_or_page="DATA_MISSING: selected-table diagnostic found no selected statement tables",
        table_local_scale_evidence="DATA_MISSING: no selected statement tables",
        same_page_scale_evidence="DATA_MISSING: no selected statement pages",
        document_level_scale_evidence="unknown from first 15 cached tables",
        forbidden_outputs=[
            "scale inferred from ticker, filename, or announcement date",
            "ok without selected statement table/page provenance",
        ],
        current_behavior_expected_or_bug="expected_safe_fail: parser/table coverage gap, not a scale-binding repair",
        root_cause_group="parser_table_coverage_gap",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_selected_table_provenance_diagnostic_v1_20260607/diagnostic_results.json",
        ],
    ),
    _scale_harness_case(
        ticker="NIC",
        document_id="50398d3d-27f7-4d9e-8a26-a2d69f128a1c",
        case_role="scale_unknown_document_family_policy_gap",
        expected_document_class="DATA_MISSING: webcast-details policy audit required",
        expected_status_or_gate="validation_gate:scale_unknown",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/NIC/financial_performance/"
            "2025-08-11_half-year-results-webcast-details_50398d3d-27f7-4d9e-8a26-a2d69f128a1c.pdf"
        ),
        selected_table_or_page="DATA_MISSING: not covered by selected-table/pass3a diagnostics",
        table_local_scale_evidence="DATA_MISSING",
        same_page_scale_evidence="DATA_MISSING",
        document_level_scale_evidence="unknown in count-24 summary",
        forbidden_outputs=[
            "webcast-details title promoted to financial report without exact source review",
            "scale inferred without source text/table evidence",
        ],
        current_behavior_expected_or_bug="expected_safe_fail_pending_policy_audit",
        root_cause_group="document_family_policy_gap",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/repair_decision.json@b5537f9",
        ],
    ),
    _scale_harness_case(
        ticker="DXC",
        document_id="f8a24788-dbe0-48f7-ad41-654f2c8a3845",
        case_role="selected_table_scale_and_label_guard",
        expected_document_class="results_presentation",
        expected_status_or_gate="validation_gate:metric_label_mismatch:ebit:net_operating_income",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/DXC/financial_performance/"
            "2025-08-11_fy25-results-presentation_f8a24788-dbe0-48f7-ad41-654f2c8a3845.pdf"
        ),
        selected_table_or_page="DATA_MISSING in current artifacts; prior accepted-output audit identified selected A$000 table context",
        table_local_scale_evidence="thousands/A$000 selected-table context in prior accepted-output audit",
        same_page_scale_evidence="DATA_MISSING",
        document_level_scale_evidence="count-24 payload scale thousands",
        forbidden_outputs=[
            "net operating income accepted as canonical ebit",
            "ok without source-label compatibility for ebit",
        ],
        current_behavior_expected_or_bug="expected_safe_fail: label guard is working",
        root_cause_group="existing_truth_gate_working",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/accepted_output_audit.json",
        ],
    ),
    _scale_harness_case(
        ticker="HUB",
        document_id="419bcca8-213e-4706-8962-8e3bd8adf091",
        case_role="period_source_fail_closed_control",
        expected_document_class="half_year_financial_report_appendix4d",
        expected_status_or_gate="validation_gate:announcement_date_period_end",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/HUB/financial_performance/"
            "2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_419bcca8-213e-4706-8962-8e3bd8adf091.pdf"
        ),
        selected_table_or_page="DATA_MISSING in scale harness artifacts",
        table_local_scale_evidence="DATA_MISSING",
        same_page_scale_evidence="DATA_MISSING",
        document_level_scale_evidence="count-24 payload scale thousands, but period gate fails first",
        forbidden_outputs=[
            "period_end equal to leading announcement date accepted for half-year output",
            "scale repair used to bypass period-source mismatch",
        ],
        current_behavior_expected_or_bug="expected_safe_fail: announcement-date period guard is working",
        root_cause_group="period_source_fail_closed",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/accepted_output_audit.json",
        ],
    ),
    _scale_harness_case(
        ticker="LBL",
        document_id="551c6b84-1053-405c-a833-4ecc018e2045",
        case_role="selected_table_scale_risk_plus_period_fail_closed",
        expected_document_class="results_presentation",
        expected_status_or_gate="validation_gate:announcement_date_period_end",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/financial_performance/"
            "2026-02-20_1h-fy26-results-presentation_551c6b84-1053-405c-a833-4ecc018e2045.pdf"
        ),
        selected_table_or_page="DATA_MISSING exact row refs; prior accepted-output audit says five-year table pages were used",
        table_local_scale_evidence="A$000 on source table pages per accepted-output audit",
        same_page_scale_evidence="DATA_MISSING",
        document_level_scale_evidence="count-24 payload scale millions, but period gate fails first",
        forbidden_outputs=[
            "A$000 selected-table values persisted with payload scale millions",
            "period_end equal to leading announcement date accepted for half-year output",
        ],
        current_behavior_expected_or_bug="expected_safe_fail_now; earlier accepted output was unsafe",
        root_cause_group="selected_table_scale_binding_after_period_repair",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/accepted_output_audit.json",
        ],
    ),
    _scale_harness_case(
        ticker="CTN",
        document_id="dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39",
        case_role="period_source_mismatch_control",
        expected_document_class="appendix5b_quarterly_cash_flow_report",
        expected_status_or_gate="validation_gate:period_source_mismatch",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CTN/financial_performance/"
            "2022-04-28_quarterly-activities-appendix-5b-cash-flow-report_dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39.pdf"
        ),
        selected_table_or_page="DATA_MISSING in scale harness artifacts",
        table_local_scale_evidence="DATA_MISSING",
        same_page_scale_evidence="DATA_MISSING",
        document_level_scale_evidence="count-24 payload scale thousands, but period gate fails",
        forbidden_outputs=[
            "scale repair used to bypass period-type mismatch",
            "Q payload accepted against annual source evidence",
        ],
        current_behavior_expected_or_bug="expected_safe_fail: period/source gate is working",
        root_cause_group="period_source_fail_closed",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/root_causes.json@b5537f9",
        ],
    ),
    _scale_harness_case(
        ticker="CXO",
        document_id="36e172ec-2650-4a9f-9ef0-a4366a3b8d31",
        case_role="clean_scale_known_control",
        expected_document_class="financial_report",
        expected_status_or_gate="ok",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CXO/financial_performance/"
            "2022-10-31_quarterly-activities-and-cashflow-report-30-september-2022_36e172ec-2650-4a9f-9ef0-a4366a3b8d31.pdf"
        ),
        selected_table_or_page="DATA_MISSING in scale harness artifacts",
        table_local_scale_evidence="DATA_MISSING",
        same_page_scale_evidence="DATA_MISSING",
        document_level_scale_evidence="count-24 accepted payload scale thousands",
        forbidden_outputs=[
            "control reclassified as scale_unknown without provenance evidence",
            "control used to infer scale for other documents",
        ],
        current_behavior_expected_or_bug="expected_ok_control",
        root_cause_group="clean_scale_known_control",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            f"{_COUNT24_REPORT_ROOT}/accepted_output_audit.json",
        ],
    ),
    _scale_harness_case(
        ticker="EQR",
        document_id="aadead44-11f3-46d5-933b-6f2c8792e6f9",
        case_role="clean_noncandidate_control",
        expected_document_class="meeting_or_proxy_notice",
        expected_status_or_gate="validation_gate:source_noncandidate:meeting_or_proxy_notice",
        source_path=(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/EQR/financial_performance/"
            "2022-10-21_notice-of-annual-general-meeting-proxy-form_aadead44-11f3-46d5-933b-6f2c8792e6f9.pdf"
        ),
        selected_table_or_page="not applicable: source noncandidate",
        table_local_scale_evidence="not applicable",
        same_page_scale_evidence="not applicable",
        document_level_scale_evidence="not applicable",
        forbidden_outputs=[
            "LLM metric extraction attempted",
            "source noncandidate accepted as financial_report",
            "scale inferred for noncandidate",
        ],
        current_behavior_expected_or_bug="expected_safe_fail_control",
        root_cause_group="clean_noncandidate_control",
        source_artifacts=[
            f"{_COUNT24_REPORT_ROOT}/sample_results.json",
            "reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/failed_documents.json@b5537f9",
        ],
    ),
]


def get_scale_table_provenance_harness_cases() -> list[dict]:
    """Return fixed no-extraction scale-table provenance regression cases."""
    return copy.deepcopy(_SCALE_TABLE_HARNESS_CASES)


def build_scale_table_provenance_harness_manifest(generated_at: str | None = None) -> dict:
    """Build a fixed manifest for scale-table provenance audits.

    This manifest is intentionally static. It lets future repair work recheck
    the same evidence classes before any random sample, count-24 rerun, or
    count-32 approval.
    """
    cases = get_scale_table_provenance_harness_cases()
    generated_at = generated_at or datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "job_id": "extraction_scale_table_provenance_harness_v1_20260607",
        "generated_at": generated_at,
        "mode": "fixed_provenance_harness_no_extraction",
        "canonical_base": "07bdfe6d84eeba41c357eaf5893420ef77189625",
        "forbidden_actions": {
            "count24_rerun": True,
            "count32": True,
            "random_sample": True,
            "broad_extraction_or_backfill": True,
            "full_ticker_universe_extraction": True,
            "db_qdrant_news_memory_mutation": True,
            "source_pdf_edits": True,
            "prompt_gold_label_runtime_schema_changes": True,
        },
        "required_case_tickers": ["AZJ", "EDU", "WHC", "NIC", "DXC", "HUB", "LBL", "CTN"],
        "controls": {
            "clean_scale_known_control": "CXO",
            "clean_noncandidate_control": "EQR",
        },
        "case_count": len(cases),
        "cases": cases,
        "audit_questions": {
            "selected_table_scale_binding_required": [
                "DXC",
                "LBL",
            ],
            "selected_table_scale_binding_note": (
                "Only table-local explicit scale may bind. DXC and LBL keep this as a "
                "known selected-table risk/control; LBL also remains blocked by period evidence."
            ),
            "same_page_scale_propagation_required": [
                "AZJ",
            ],
            "same_page_scale_propagation_note": (
                "AZJ has repeated same-page millions evidence on selected statement pages, "
                "but this is not enough for a production repair until metric-local row/page binding is captured. "
                "EDU is explicitly excluded because selected surfaces are mixed."
            ),
            "must_fail_closed_mixed_or_unclean": [
                "EDU",
                "HUB",
                "LBL",
                "CTN",
            ],
            "parser_or_table_coverage_gaps": [
                "WHC",
                "AZJ",
                "EDU",
                "DXC",
            ],
            "policy_gaps": [
                "NIC webcast-details document-family policy",
                "AZJ nearest-$100k rounding policy",
            ],
            "future_sample_artifact_provenance_fields": list(SCALE_TABLE_PROVENANCE_REQUIRED_FIELDS),
        },
        "repair_decision": {
            "safe_extension_made": "harness_only",
            "production_extraction_code_repair_made": False,
            "repeated_root_cause_proven_for_production_repair": False,
            "count24_rerun_justified": False,
            "count32_status": "blocked",
            "next_safe_repair_path": (
                "Implement no production scale propagation yet. First add/capture metric-local selected-page "
                "scale provenance for AZJ and one additional same-page candidate, while keeping EDU mixed "
                "surfaces fail-closed; then consider one narrow same-page propagation repair only if two "
                "clean cases prove the same source-bound root cause."
            ),
        },
        "data_missing": [
            "Runtime row refs for count-24 accepted and failed rows are not consistently present.",
            "Exact selected table/page provenance for NIC, DXC, HUB, LBL, CTN, and CXO is not present in current artifacts.",
            "Metric-local same-page scale binding is captured for AZJ/EDU only and remains incomplete for a repeated repair.",
            "Source-bound nearest-$100k policy for AZJ remains unresolved.",
        ],
    }


def write_scale_table_provenance_harness_artifacts(output_dir: Path) -> dict[str, str]:
    """Write fixed scale-table harness artifacts without running extraction."""
    manifest = build_scale_table_provenance_harness_manifest()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "harness_manifest.json": manifest,
        "evidence_table.json": {
            "job_id": manifest["job_id"],
            "generated_at": manifest["generated_at"],
            "cases": manifest["cases"],
        },
        "root_cause_grouping.json": {
            "job_id": manifest["job_id"],
            "generated_at": manifest["generated_at"],
            "groups": {
                "same_page_scale_candidate_not_repeated": ["AZJ"],
                "mixed_selected_surfaces_fail_closed": ["EDU"],
                "parser_table_coverage_gap": ["WHC"],
                "document_family_policy_gap": ["NIC"],
                "selected_table_scale_binding_after_period_repair": ["LBL"],
                "existing_truth_gate_working": ["DXC"],
                "period_source_fail_closed": ["HUB", "CTN"],
                "clean_controls": ["CXO", "EQR"],
            },
            "audit_questions": manifest["audit_questions"],
        },
        "repair_decision.json": manifest["repair_decision"] | {
            "job_id": manifest["job_id"],
            "generated_at": manifest["generated_at"],
            "data_missing": manifest["data_missing"],
        },
    }

    written: dict[str, str] = {}
    for filename, payload in artifacts.items():
        path = output_dir / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[filename] = str(path)
    return written


def discover_pdfs() -> list[Path]:
    """Find all financial_performance PDFs across all tickers."""
    pdfs = []
    for ticker_dir in sorted(DOCS_ROOT.iterdir()):
        fp_dir = ticker_dir / "financial_performance"
        if not fp_dir.is_dir():
            continue
        for f in fp_dir.iterdir():
            if f.suffix == ".pdf" and not f.name.endswith((".docling.json", ".pymupdf.json")):
                pdfs.append(f)
    return pdfs


def _ticker_from_path(pdf_path: Path) -> str:
    """Extract ticker from path like .../BHP/financial_performance/xxx.pdf"""
    return pdf_path.parent.parent.name


def _doc_id_from_path(pdf_path: Path) -> str:
    """Extract document_id UUID from filename (last segment before .pdf)."""
    stem = pdf_path.stem
    parts = stem.rsplit("_", 1)
    return parts[-1] if len(parts) > 1 else stem


def make_llm_client(use_anthropic: bool):
    """Create an LLM client for extraction."""
    if use_anthropic:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("ERROR: --anthropic requires ANTHROPIC_API_KEY env var", file=sys.stderr)
            sys.exit(1)
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("EVAL_CLAUDE_MODEL", "claude-sonnet-4-20250514")
        client._extraction_model = model
        print(f"Using Anthropic API ({model})")
        return client
    else:
        import httpx
        base_url = os.environ.get("LLAMACPP_URL", "http://127.0.0.1:8001")
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        headers = {}
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not api_key:
            # Try reading OpenClaw gateway token
            openclaw_cfg = Path.home() / ".openclaw" / "openclaw.json"
            if openclaw_cfg.exists():
                try:
                    cfg = json.loads(openclaw_cfg.read_text())
                    api_key = cfg.get("gateway", {}).get("auth", {}).get("token", "")
                except Exception:
                    pass
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        client = httpx.Client(base_url=base_url, timeout=120.0, headers=headers)
        # Quick health check
        try:
            r = client.get("/models")
            r.raise_for_status()
        except Exception as e:
            print(f"ERROR: llama.cpp not reachable at {base_url}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Using llama.cpp at {base_url}")
        return client


def run_one(pdf_path: Path, llm_client) -> dict:
    """Run extraction on a single PDF. Returns result dict."""
    from app.services.multipass_extraction import run_multipass_extraction

    ticker = _ticker_from_path(pdf_path)
    doc_id = _doc_id_from_path(pdf_path)
    doc_metadata = {
        "document_id": doc_id,
        "ticker": ticker,
        "title": pdf_path.name,
    }

    record = {
        "pdf_path": str(pdf_path.relative_to(_REPO_ROOT)),
        "ticker": ticker,
        "document_id": doc_id,
        "status": None,
        "error": None,
        "elapsed_s": None,
        "metrics": {},
        "period_type": None,
        "period_end": None,
        "scale": None,
        "confidence": None,
        "non_null_metrics": 0,
        "table_count": None,
        "page_count": None,
        "sanity": {},
        "metric_provenance": {},
        "provenance_available": [],
        "provenance_missing": [],
        "provenance_audit": {},
        "source_provenance": {},
        "accepted_output_scale_magnitude_risk": {},
        "risk_flags": [],
        "scale_validation": None,
    }

    t0 = time.monotonic()
    try:
        result = run_multipass_extraction(
            str(pdf_path), doc_metadata, llm_client, skip_narrative=True,
        )
        elapsed = time.monotonic() - t0
        record["elapsed_s"] = round(elapsed, 2)
        record["status"] = result.status
        record["error"] = result.error

        payload = result.payload or {}
        metrics = payload.get("metrics", {})
        record["metrics"] = {k: metrics.get(k) for k in METRIC_FIELDS}
        record["period_type"] = payload.get("period_type")
        record["period_end"] = str(payload.get("period_end")) if payload.get("period_end") else None
        record["scale"] = payload.get("scale")
        record["confidence"] = payload.get("confidence_metrics")
        record["non_null_metrics"] = sum(1 for v in metrics.values() if v is not None)
        record["scale_validation"] = payload.get("scale_validation")

        provenance_audit = _build_metric_provenance_audit(payload)
        record["metric_provenance"] = provenance_audit["metric_provenance"]
        record["provenance_available"] = provenance_audit["provenance_available"]
        record["provenance_missing"] = provenance_audit["provenance_missing"]
        record["provenance_audit"] = {
            key: value
            for key, value in provenance_audit.items()
            if key != "metric_provenance"
        }
        record["source_provenance"] = {
            key: payload.get(key)
            for key in (
                "source_period_type",
                "source_period_evidence",
                "source_period_end_evidence",
                "source_period_end_binding",
                "source_document_classification",
                "source_bound",
            )
            if payload.get(key) is not None
        }
        scale_magnitude_risk = _build_scale_magnitude_risk(
            payload,
            accepted_output=result.status in ("ok", "ok_low_confidence"),
        )
        record["accepted_output_scale_magnitude_risk"] = scale_magnitude_risk
        record["risk_flags"] = scale_magnitude_risk["flag_codes"]

        # Sanity checks (only when metric is present)
        sanity = {}
        if metrics.get("revenue") is not None:
            sanity["revenue_positive"] = metrics["revenue"] > 0
        if metrics.get("shares_outstanding") is not None:
            sanity["shares_positive"] = metrics["shares_outstanding"] > 0
        if metrics.get("cash_end") is not None:
            sanity["cash_end_positive"] = metrics["cash_end"] > 0
        pe = payload.get("period_end")
        if pe:
            sanity["period_end_valid"] = pe not in (None, "None", "")
        pt = payload.get("period_type")
        if pt:
            sanity["period_type_valid"] = pt in ("A", "H", "Q")
        record["sanity"] = sanity

    except Exception as e:
        elapsed = time.monotonic() - t0
        record["elapsed_s"] = round(elapsed, 2)
        record["status"] = "exception"
        record["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)

    return record


def compute_summary(results: list[dict]) -> dict:
    """Compute aggregate stats from all results."""
    total = len(results)
    if total == 0:
        return {"total": 0}

    # Status distribution
    status_counts: dict[str, int] = {}
    for r in results:
        s = r["status"] or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    # Error classification
    error_classes: dict[str, int] = {}
    for r in results:
        err = r.get("error")
        if err:
            # Classify by prefix
            if err.startswith("pass1:"):
                cls = "pass1_failure"
            elif err.startswith("validation_gate:source_noncandidate:"):
                cls = err.removeprefix("validation_gate:")
            elif err.startswith("validation_gate:"):
                parts = err.split(":", 2)
                cls = ":".join(parts[:2])
            elif "low_confidence" in err:
                cls = "classifier_low_confidence"
            elif "timeout" in err.lower() or "sigalrm" in err.lower():
                cls = "timeout"
            elif "Exception" in (r["status"] or ""):
                cls = "python_exception"
            else:
                cls = err.split(":")[0] if ":" in err else "other"
            error_classes[cls] = error_classes.get(cls, 0) + 1

    # Metric coverage (across non-failed results)
    ok_results = [r for r in results if r["status"] in ("ok", "ok_low_confidence")]
    metric_coverage: dict[str, dict] = {}
    for m in METRIC_FIELDS:
        present = sum(1 for r in ok_results if r["metrics"].get(m) is not None)
        metric_coverage[m] = {
            "present": present,
            "total": len(ok_results),
            "rate": round(present / len(ok_results), 4) if ok_results else 0,
        }

    # Non-null metric count distribution
    nonnull_counts = [r["non_null_metrics"] for r in ok_results]
    nonnull_dist = {}
    if nonnull_counts:
        nonnull_dist = {
            "mean": round(statistics.mean(nonnull_counts), 2),
            "median": statistics.median(nonnull_counts),
            "min": min(nonnull_counts),
            "max": max(nonnull_counts),
        }

    # Timing stats
    timings = [r["elapsed_s"] for r in results if r["elapsed_s"] is not None]
    timing_stats = {}
    if timings:
        timings_sorted = sorted(timings)
        timing_stats = {
            "mean_s": round(statistics.mean(timings), 2),
            "median_s": round(statistics.median(timings), 2),
            "p95_s": round(timings_sorted[int(len(timings_sorted) * 0.95)], 2),
            "p99_s": round(timings_sorted[int(len(timings_sorted) * 0.99)], 2),
            "min_s": round(min(timings), 2),
            "max_s": round(max(timings), 2),
            "total_s": round(sum(timings), 1),
        }

    # Sanity check pass rates
    sanity_stats: dict[str, dict] = {}
    for check_name in ("revenue_positive", "shares_positive", "cash_end_positive",
                       "period_end_valid", "period_type_valid"):
        applicable = [r for r in ok_results if check_name in r.get("sanity", {})]
        passed = sum(1 for r in applicable if r["sanity"][check_name])
        sanity_stats[check_name] = {
            "passed": passed,
            "total": len(applicable),
            "rate": round(passed / len(applicable), 4) if applicable else 0,
        }

    # Ticker diversity
    tickers = set(r["ticker"] for r in results)
    period_types = {}
    for r in ok_results:
        pt = r.get("period_type") or "unknown"
        period_types[pt] = period_types.get(pt, 0) + 1

    # Scale distribution
    scales = {}
    for r in ok_results:
        sc = r.get("scale") or "unknown"
        scales[sc] = scales.get(sc, 0) + 1

    provenance_with_counts: dict[str, int] = {}
    provenance_missing_counts: dict[str, int] = {}
    documents_with_missing_provenance = 0
    documents_with_full_provenance = 0
    documents_with_any_provenance = 0
    for r in ok_results:
        audit = _as_dict(r.get("provenance_audit"))
        with_provenance = audit.get("metrics_with_provenance")
        missing_provenance = audit.get("metrics_missing_provenance")
        if not isinstance(with_provenance, list):
            with_provenance = r.get("provenance_available", [])
        if not isinstance(missing_provenance, list):
            missing_provenance = r.get("provenance_missing", [])
        if not isinstance(with_provenance, list):
            with_provenance = []
        if not isinstance(missing_provenance, list):
            missing_provenance = []

        if with_provenance:
            documents_with_any_provenance += 1
        if missing_provenance:
            documents_with_missing_provenance += 1
        elif with_provenance:
            documents_with_full_provenance += 1

        for metric_name in with_provenance:
            if metric_name in METRIC_FIELDS:
                provenance_with_counts[metric_name] = (
                    provenance_with_counts.get(metric_name, 0) + 1
                )
        for metric_name in missing_provenance:
            if metric_name in METRIC_FIELDS:
                provenance_missing_counts[metric_name] = (
                    provenance_missing_counts.get(metric_name, 0) + 1
                )

    risk_flag_distribution: dict[str, int] = {}
    risk_flagged_documents = 0
    for r in ok_results:
        flag_codes: list[str] = []
        raw_flags = r.get("risk_flags")
        if isinstance(raw_flags, list):
            for raw_flag in raw_flags:
                if isinstance(raw_flag, str):
                    flag_codes.append(raw_flag)
                elif isinstance(raw_flag, dict) and raw_flag.get("code"):
                    flag_codes.append(str(raw_flag["code"]))
        if not flag_codes:
            risk = _as_dict(r.get("accepted_output_scale_magnitude_risk"))
            for raw_flag in risk.get("flags", []):
                if isinstance(raw_flag, dict) and raw_flag.get("code"):
                    flag_codes.append(str(raw_flag["code"]))

        if flag_codes:
            risk_flagged_documents += 1
        for code in flag_codes:
            risk_flag_distribution[code] = risk_flag_distribution.get(code, 0) + 1

    return {
        "total": total,
        "status_distribution": status_counts,
        "success_rate": round(len(ok_results) / total, 4),
        "error_classification": error_classes,
        "metric_coverage": metric_coverage,
        "nonnull_metric_distribution": nonnull_dist,
        "timing": timing_stats,
        "sanity_checks": sanity_stats,
        "unique_tickers": len(tickers),
        "period_type_distribution": period_types,
        "scale_distribution": scales,
        "provenance_coverage": {
            "metrics_with_provenance": provenance_with_counts,
            "metrics_missing_provenance": provenance_missing_counts,
            "documents_with_any_provenance": documents_with_any_provenance,
            "documents_with_full_provenance": documents_with_full_provenance,
            "documents_with_missing_provenance": documents_with_missing_provenance,
        },
        "risk_flag_distribution": risk_flag_distribution,
        "risk_flagged_documents": risk_flagged_documents,
    }


def print_summary(summary: dict) -> None:
    """Print human-readable summary to console."""
    total = summary["total"]
    print(f"\n{'='*70}")
    print(f"  BROAD EXTRACTION TEST — {total} documents")
    print(f"{'='*70}\n")

    # Status
    print("STATUS DISTRIBUTION:")
    for status, count in sorted(summary["status_distribution"].items()):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {status:25s} {count:4d} ({pct:5.1f}%) {bar}")

    sr = summary["success_rate"]
    print(f"\n  Success rate: {sr:.1%}")

    # Errors
    if summary["error_classification"]:
        print(f"\nERROR CLASSIFICATION:")
        for cls, count in sorted(summary["error_classification"].items(), key=lambda x: -x[1]):
            print(f"  {cls:35s} {count:4d}")

    # Metric coverage
    print(f"\nMETRIC COVERAGE (across {summary['status_distribution'].get('ok', 0) + summary['status_distribution'].get('ok_low_confidence', 0)} successful extractions):")
    for m, stats in summary["metric_coverage"].items():
        rate = stats["rate"]
        bar = "█" * int(rate * 30)
        print(f"  {m:22s} {stats['present']:4d}/{stats['total']:4d} ({rate:5.1%}) {bar}")

    # Non-null distribution
    nd = summary.get("nonnull_metric_distribution", {})
    if nd:
        print(f"\n  Non-null metrics per doc: mean={nd['mean']:.1f}, median={nd['median']}, range=[{nd['min']},{nd['max']}]")

    # Sanity checks
    print(f"\nSANITY CHECKS:")
    for check, stats in summary["sanity_checks"].items():
        rate = stats["rate"]
        label = "PASS" if rate >= 0.95 else "WARN" if rate >= 0.80 else "FAIL"
        print(f"  {check:25s} {stats['passed']:4d}/{stats['total']:4d} ({rate:5.1%}) [{label}]")

    # Period type + scale
    print(f"\nPERIOD TYPE DISTRIBUTION:")
    for pt, count in sorted(summary.get("period_type_distribution", {}).items()):
        print(f"  {pt:5s} {count:4d}")

    print(f"\nSCALE DISTRIBUTION:")
    for sc, count in sorted(summary.get("scale_distribution", {}).items()):
        print(f"  {sc:15s} {count:4d}")

    # Timing
    ts = summary.get("timing", {})
    if ts:
        print(f"\nTIMING:")
        print(f"  Mean: {ts['mean_s']:.1f}s  Median: {ts['median_s']:.1f}s  P95: {ts['p95_s']:.1f}s  P99: {ts['p99_s']:.1f}s")
        print(f"  Range: [{ts['min_s']:.1f}s, {ts['max_s']:.1f}s]  Total: {ts['total_s']:.0f}s ({ts['total_s']/60:.1f}min)")

    print(f"\n  Unique tickers sampled: {summary['unique_tickers']}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Broad extraction robustness test")
    parser.add_argument("--count", type=int, default=200, help="Number of PDFs to sample (default: 200)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--resume", action="store_true", help="Resume from existing results file")
    parser.add_argument("--anthropic", action="store_true", help="Use Anthropic API instead of local llama.cpp")
    parser.add_argument("--output-dir", type=str, default=str(RESULTS_DIR), help="Output directory for results")
    parser.add_argument(
        "--scale-table-provenance-harness",
        action="store_true",
        help="Write the fixed no-extraction scale-table provenance harness artifacts and exit",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.scale_table_provenance_harness:
        written = write_scale_table_provenance_harness_artifacts(output_dir)
        for name, path in sorted(written.items()):
            print(f"{name}: {path}")
        return

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = output_dir / f"broad_test_{ts}.json"

    # Discover all PDFs
    print("Discovering PDFs...")
    all_pdfs = discover_pdfs()
    print(f"Found {len(all_pdfs)} financial_performance PDFs across {len(set(_ticker_from_path(p) for p in all_pdfs))} tickers")

    # Sample
    rng = random.Random(args.seed)
    sample_size = min(args.count, len(all_pdfs))
    sample = rng.sample(all_pdfs, sample_size)
    print(f"Sampled {sample_size} PDFs (seed={args.seed})")

    # Resume: load existing results and skip already-processed paths
    existing_results: list[dict] = []
    processed_paths: set[str] = set()
    if args.resume:
        # Find most recent results file
        existing_files = sorted(output_dir.glob("broad_test_*.json"), reverse=True)
        if existing_files:
            latest = existing_files[0]
            print(f"Resuming from {latest.name}")
            data = json.loads(latest.read_text())
            existing_results = data.get("results", [])
            processed_paths = {r["pdf_path"] for r in existing_results}
            results_path = latest  # overwrite same file
            print(f"  Already processed: {len(processed_paths)}")

    # Build LLM client
    llm_client = make_llm_client(args.anthropic)

    # Run extraction
    results = list(existing_results)
    remaining = [p for p in sample if str(p.relative_to(_REPO_ROOT)) not in processed_paths]
    total_remaining = len(remaining)

    if total_remaining == 0:
        print("All samples already processed. Nothing to do.")
    else:
        print(f"\nRunning extraction on {total_remaining} PDFs...")
        print(f"Estimated time: ~{total_remaining * 45 / 60:.0f} min (at ~45s/doc with llama.cpp)\n")

    for i, pdf_path in enumerate(remaining):
        rel = str(pdf_path.relative_to(_REPO_ROOT))
        ticker = _ticker_from_path(pdf_path)
        done_total = len(results)
        elapsed_total = sum(r["elapsed_s"] for r in results if r["elapsed_s"]) or 0.001
        avg_per_doc = elapsed_total / max(done_total, 1)
        eta_s = avg_per_doc * (total_remaining - i)

        print(f"[{i+1}/{total_remaining}] {ticker}/{pdf_path.name[:50]}...", end="", flush=True)

        record = run_one(pdf_path, llm_client)
        results.append(record)

        status = record["status"]
        elapsed = record["elapsed_s"] or 0
        nn = record["non_null_metrics"]
        emoji = {"ok": "OK", "ok_low_confidence": "LC", "failed": "FL", "exception": "EX"}.get(status, "??")

        print(f" [{emoji}] {elapsed:.1f}s  metrics={nn}/10  ETA={eta_s/60:.0f}min")

        # Incremental save (crash-safe)
        if (i + 1) % 5 == 0 or i == total_remaining - 1:
            summary = compute_summary(results)
            report = {
                "run_metadata": {
                    "timestamp": ts,
                    "seed": args.seed,
                    "requested_count": args.count,
                    "actual_count": len(results),
                    "backend": "anthropic" if args.anthropic else "llamacpp",
                },
                "summary": summary,
                "results": results,
            }
            results_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Final summary
    summary = compute_summary(results)
    report = {
        "run_metadata": {
            "timestamp": ts,
            "seed": args.seed,
            "requested_count": args.count,
            "actual_count": len(results),
            "backend": "anthropic" if args.anthropic else "llamacpp",
        },
        "summary": summary,
        "results": results,
    }
    results_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print_summary(summary)
    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    main()
