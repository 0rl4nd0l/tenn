#!/usr/bin/env python3
"""No-write metric-local same-page scale provenance capture.

This runner reads fixed report artifacts and existing parser-cache JSON. It does
not run count-24, count-32, sample selection, broad extraction, backfill,
Docling/PyMuPDF parsing, LLM extraction, DB writes, Qdrant, Redis, news, source
PDF edits, prompt edits, schema edits, or runtime/service changes.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


JOB_ID = "extraction_metric_local_same_page_scale_provenance_v1_20260608"
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__file__).resolve().parent

HARNESS_DIR = REPO_ROOT / "reports" / "agent_jobs" / (
    "extraction_scale_table_provenance_harness_v1_20260607"
)
PASS3A_CAPTURE = REPO_ROOT / "reports" / "agent_jobs" / (
    "extraction_azj_edu_pass3a_provenance_capture_v1_20260607"
) / "provenance_capture.json"
SELECTED_TABLE_DIAGNOSTIC = REPO_ROOT / "reports" / "agent_jobs" / (
    "extraction_selected_table_provenance_diagnostic_v1_20260607"
) / "diagnostic_results.json"

COUNT24_REPORT_DIR = Path(
    "/home/l4nd0/tenn-count24-bounded-validation-v1-20260607"
) / "reports" / "agent_jobs" / "extraction_count24_bounded_validation_v1_20260607"
COUNT24_SAMPLE_RESULTS = COUNT24_REPORT_DIR / "sample_results.json"
ACCEPTED_OUTPUT_AUDIT = COUNT24_REPORT_DIR / "accepted_output_audit.json"
COUNT24_CACHE_ROOT = Path(
    "/home/l4nd0/tenn-count24-bounded-validation-v1-20260607"
) / "financial-engine_v2" / "data" / "reports" / "extraction_cache" / (
    "docling_extract"
)

TARGET_TICKERS = ("AZJ", "EDU", "CXO")
MISSING = "DATA_MISSING"

SCALE_PATTERNS = (
    (re.compile(r"\$A?\s*['`\u2019]?\s*000\b", re.IGNORECASE), "thousands"),
    (re.compile(r"\$\s*['`\u2019]\s*000\b", re.IGNORECASE), "thousands"),
    (re.compile(r"\bA?\$?\s*000s\b", re.IGNORECASE), "thousands"),
    (re.compile(r"\bthousands?\b", re.IGNORECASE), "thousands"),
    (re.compile(r"\$A?\s*m\b", re.IGNORECASE), "millions"),
    (re.compile(r"\bmillions?\b", re.IGNORECASE), "millions"),
)
RAW_DOLLAR_RE = re.compile(r"(?<!['`\u2019]000)\b\$A?\b|\bAUD\b", re.IGNORECASE)

METRIC_FIELDS = (
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _clean_text(value: Any, max_len: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text[:max_len]


def _detect_scale_from_text(text: str) -> str:
    for pattern, scale in SCALE_PATTERNS:
        if pattern.search(text):
            return scale
    if RAW_DOLLAR_RE.search(text):
        return "units"
    return "unknown"


def _scale_snippets(text: str, max_items: int = 6) -> list[str]:
    snippets: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_text(raw_line, 220)
        if not line:
            continue
        if (
            any(pattern.search(line) for pattern, _ in SCALE_PATTERNS)
            or RAW_DOLLAR_RE.search(line)
            or "rounded" in line.lower()
            or "nearest $100,000" in line.lower()
        ):
            snippets.append(line)
        if len(snippets) >= max_items:
            break
    return snippets


def _load_if_present(path: Path) -> Any:
    if not path.exists():
        return None
    return _load_json(path)


def _sample_by_doc_id() -> dict[str, dict[str, Any]]:
    payload = _load_if_present(COUNT24_SAMPLE_RESULTS) or {}
    return {
        str(row.get("document_id")): row
        for row in payload.get("results", [])
        if isinstance(row, dict) and row.get("document_id")
    }


def _accepted_by_doc_id() -> dict[str, dict[str, Any]]:
    payload = _load_if_present(ACCEPTED_OUTPUT_AUDIT) or {}
    return {
        str(row.get("document_id")): row
        for row in payload.get("accepted_documents", [])
        if isinstance(row, dict) and row.get("document_id")
    }


def _pass3a_by_ticker() -> dict[str, dict[str, Any]]:
    payload = _load_if_present(PASS3A_CAPTURE) or {}
    return {
        str(row.get("ticker")): row
        for row in payload.get("documents", [])
        if isinstance(row, dict) and row.get("ticker") in TARGET_TICKERS
    }


def _diagnostic_by_ticker() -> dict[str, dict[str, Any]]:
    payload = _load_if_present(SELECTED_TABLE_DIAGNOSTIC) or {}
    return {
        str(row.get("ticker")): row
        for row in payload.get("documents", [])
        if isinstance(row, dict) and row.get("ticker") in TARGET_TICKERS
    }


def _page_text_by_page(sections: list[dict[str, Any]]) -> dict[int, str]:
    pages: dict[int, list[str]] = {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        try:
            page = int(section.get("page") or 0)
        except (TypeError, ValueError):
            continue
        text = str(section.get("text") or "")
        if text:
            pages.setdefault(page, []).append(text)
    return {page: "\n".join(parts) for page, parts in pages.items()}


def _table_text(table: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.extend(str(cell or "") for cell in table.get("headers", []))
    for row in table.get("rows", []):
        if isinstance(row, list):
            parts.extend(str(cell or "") for cell in row)
    return "\n".join(parts)


def _brief_rows(rows: list[Any], limit: int = 4) -> list[list[str]]:
    output: list[list[str]] = []
    for row in rows[:limit]:
        if isinstance(row, list):
            output.append([_clean_text(cell, 120) for cell in row[:4]])
    return output


def _cache_path_for_doc(doc_id: str, title: str | None) -> Path | None:
    direct = sorted(COUNT24_CACHE_ROOT.glob(f"*{doc_id}*.json"))
    if direct:
        return direct[0]
    if title:
        stem = Path(title).stem[:84]
        title_matches = sorted(COUNT24_CACHE_ROOT.glob(f"*{stem}*.json"))
        if title_matches:
            return title_matches[0]
    return None


def _cache_table_audit(case: dict[str, Any], sample_row: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(case.get("document_id") or "")
    title = str(sample_row.get("title") or Path(str(case.get("source_path") or "")).name)
    cache_path = _cache_path_for_doc(doc_id, title)
    if cache_path is None or not cache_path.exists():
        return {
            "cache_path": MISSING,
            "cache_path_exists": False,
            "candidate_tables": [],
            "data_missing": ["parser_cache_json"],
        }

    payload = _load_json(cache_path)
    pages = _page_text_by_page(payload.get("sections", []))
    candidate_tables: list[dict[str, Any]] = []
    for index, table in enumerate(payload.get("tables", [])):
        if not isinstance(table, dict):
            continue
        table_text = _table_text(table)
        table_scale = _detect_scale_from_text(table_text)
        page_number = int(table.get("page_number") or 0)
        same_page_text = pages.get(page_number, "")
        same_page_scale = _detect_scale_from_text(same_page_text)
        lower = table_text.lower()
        relevant = (
            table_scale == "thousands"
            or "cash flow" in lower
            or "operating activities" in lower
            or "appendix 5b" in lower
        )
        if not relevant:
            continue
        candidate_tables.append(
            {
                "table_index": index,
                "page_number": page_number,
                "caption": _clean_text(table.get("caption")),
                "headers": [_clean_text(cell, 160) for cell in table.get("headers", [])],
                "row_count": len(table.get("rows", [])),
                "head_rows": _brief_rows(table.get("rows", [])),
                "table_local_scale": table_scale,
                "same_page_scale": same_page_scale,
                "same_page_scale_snippets": _scale_snippets(same_page_text),
            }
        )

    return {
        "cache_path": str(cache_path),
        "cache_path_exists": True,
        "candidate_tables": candidate_tables[:10],
        "data_missing": [],
    }


def _selected_table_summary(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "table_index": table.get("table_index"),
        "page_number": table.get("page_number"),
        "caption": _clean_text(table.get("caption")),
        "headers": [_clean_text(cell, 160) for cell in table.get("headers", [])],
        "head_rows": table.get("head_rows") or table.get("first_rows") or [],
        "table_local_scale": table.get("table_local_scale", MISSING),
        "same_page_scale": table.get("same_page_scale")
        or table.get("same_page_text_scale")
        or MISSING,
        "same_page_scale_snippets": table.get("same_page_scale_snippets")
        or table.get("same_page_scale_evidence_snippets")
        or [],
    }


def _metric_trace_summary(
    metric_trace: dict[str, Any],
    selected_tables: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for metric in METRIC_FIELDS:
        trace = metric_trace.get(metric, {})
        source_table = trace.get("source_table", MISSING)
        selected_table = (
            selected_tables.get(source_table)
            if isinstance(source_table, str)
            else None
        )
        selected_summary = (
            _selected_table_summary(selected_table)
            if isinstance(selected_table, dict)
            else None
        )
        output[metric] = {
            "final_value": trace.get("final_value"),
            "source_table": source_table,
            "page_number": trace.get("page_number", MISSING),
            "runtime_row_ref": trace.get("runtime_row_ref", MISSING),
            "runtime_source_scale": trace.get("runtime_source_scale", MISSING),
            "runtime_scale_source": trace.get("runtime_scale_source", MISSING),
            "selected_row": trace.get("selected_row", [MISSING]),
            "selected_value_cells": trace.get("selected_value_cells", [MISSING]),
            "selected_table_page_scale": selected_summary,
        }
    return output


def _azj_or_edu_capture(
    ticker: str,
    case: dict[str, Any],
    pass3a_row: dict[str, Any],
    diagnostic_row: dict[str, Any],
) -> dict[str, Any]:
    selected_tables = pass3a_row.get("selected_tables", {})
    return {
        "ticker": ticker,
        "document_id": case.get("document_id"),
        "source_path": case.get("source_path"),
        "expected_document_class": case.get("expected_document_class"),
        "expected_status_or_gate": case.get("expected_status_or_gate"),
        "current_behavior_expected_or_bug": case.get("current_behavior_expected_or_bug"),
        "final_gate": pass3a_row.get("final_gate", {}),
        "count24_summary": pass3a_row.get("count24_summary", {}),
        "selected_tables": {
            label: _selected_table_summary(table)
            for label, table in selected_tables.items()
            if isinstance(table, dict)
        },
        "metric_local_rows": _metric_trace_summary(
            pass3a_row.get("metric_trace", {}),
            selected_tables,
        ),
        "common_metric_source_scale_trace": pass3a_row.get(
            "common_metric_source_scale_trace",
            {MISSING: MISSING},
        ),
        "document_level_scale_markers": pass3a_row.get(
            "document_level_scale_markers",
            {MISSING: MISSING},
        ),
        "diagnostic_final_payload_scale_decision": diagnostic_row.get(
            "final_payload_scale_decision",
            {MISSING: MISSING},
        ),
        "diagnostic_data_missing": diagnostic_row.get("data_missing", []),
        "repair_classification": (
            "clean_same_page_propagation_candidate"
            if ticker == "AZJ"
            else "fail_closed_mixed_selected_surfaces"
        ),
    }


def _cxo_capture(case: dict[str, Any], sample_row: dict[str, Any]) -> dict[str, Any]:
    accepted_row = _accepted_by_doc_id().get(str(case.get("document_id")), {})
    cache_audit = _cache_table_audit(case, sample_row)
    return {
        "ticker": "CXO",
        "document_id": case.get("document_id"),
        "source_path": case.get("source_path"),
        "expected_document_class": case.get("expected_document_class"),
        "expected_status_or_gate": case.get("expected_status_or_gate"),
        "current_behavior_expected_or_bug": case.get("current_behavior_expected_or_bug"),
        "count24_summary": sample_row,
        "accepted_output_audit": {
            "status": accepted_row.get("status", MISSING),
            "scale": accepted_row.get("scale", MISSING),
            "source_document_class": accepted_row.get("source_document_class", MISSING),
            "checks": accepted_row.get("checks", {}),
            "risk_reasons": accepted_row.get("risk_reasons", []),
            "provenance_note": accepted_row.get("provenance_note", MISSING),
        },
        "cache_table_scale_evidence": cache_audit,
        "metric_local_rows": {
            metric: {
                "final_value": sample_row.get("metrics", {}).get(metric),
                "runtime_row_ref": MISSING,
                "runtime_source_scale": MISSING,
                "runtime_scale_source": MISSING,
                "selected_table_page_scale": MISSING,
            }
            for metric in METRIC_FIELDS
        },
        "common_metric_source_scale_trace": MISSING,
        "repair_classification": (
            "clean_scale_known_control_not_second_same_page_root_cause"
        ),
        "data_missing": [
            "runtime_row_refs",
            "runtime_metric_source_scales",
            "runtime_metric_scale_sources",
            "runtime_common_metric_source_scale_trace",
            "runtime_selected_table_for_accepted_metrics",
        ],
    }


def _case_candidate_audit(
    harness_cases: list[dict[str, Any]],
    pass3a_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case in harness_cases:
        ticker = str(case.get("ticker"))
        root_group = str(case.get("root_cause_group") or "")
        selected = False
        classification = "not_same_page_candidate"
        reason = "Harness class is not a same-page propagation candidate."
        if ticker == "AZJ":
            selected = True
            classification = "primary_same_page_candidate"
            reason = (
                "Selected formal statement pages have same-page millions evidence; "
                "metric source scale fields are still missing."
            )
        elif ticker == "EDU":
            classification = "fail_closed_mixed_surfaces"
            reason = "Selected surfaces are mixed/unclean and must fail closed."
        elif ticker == "CXO":
            classification = "clean_control_not_repair_case"
            reason = (
                "Accepted control has scale=thousands, but current artifacts do "
                "not expose runtime selected table/row refs for metric-local proof."
            )
        elif "parser" in root_group:
            classification = "parser_or_table_coverage_gap"
            reason = "Coverage gap precedes any same-page propagation repair."
        elif "selected_table" in root_group:
            classification = "selected_table_scale_binding_case"
            reason = "Harness class requires explicit table-local scale binding."
        elif "mixed" in root_group:
            classification = "fail_closed_mixed_surfaces"
            reason = "Mixed selected surfaces must fail closed."

        cases.append(
            {
                "ticker": ticker,
                "document_id": case.get("document_id"),
                "expected_document_class": case.get("expected_document_class"),
                "expected_status_or_gate": case.get("expected_status_or_gate"),
                "root_cause_group": root_group,
                "same_page_candidate": selected,
                "classification": classification,
                "reason": reason,
                "has_pass3a_metric_local_capture": ticker in pass3a_rows,
                "current_behavior_expected_or_bug": case.get(
                    "current_behavior_expected_or_bug"
                ),
            }
        )
    return {
        "job_id": JOB_ID,
        "generated_at": _now(),
        "mode": "no_write_existing_artifact_candidate_audit",
        "candidate_count": sum(1 for row in cases if row["same_page_candidate"]),
        "cases": cases,
        "second_candidate_decision": {
            "status": MISSING,
            "reason": (
                "No second clean same-page failure case with metric-local row refs, "
                "metric_source_scales, metric_scale_sources, selected table/page, "
                "and common-scale trace exists in current artifacts."
            ),
        },
    }


def _repair_decision(data_missing: list[str]) -> dict[str, Any]:
    return {
        "job_id": JOB_ID,
        "generated_at": _now(),
        "safe_extension_made": "report_only_metric_local_provenance_capture",
        "production_extraction_code_repair_made": False,
        "repeated_root_cause_proven_for_production_repair": False,
        "root_cause_decision": (
            "AZJ proves a clean same-page scale-propagation candidate, but the "
            "fixed harness and current artifacts do not provide a second clean "
            "same-page failure with metric-local row/page/source-scale trace. "
            "EDU remains mixed and fail-closed; CXO is a clean scale-known "
            "control, not a failed same-page propagation case."
        ),
        "count24_rerun_justified": False,
        "count32_status": "blocked",
        "fix_made": "none",
        "data_missing": data_missing,
        "next_safe_repair_path": (
            "Do not patch production scale propagation yet. First capture exact "
            "runtime metric-local provenance for one additional clean same-page "
            "candidate or accepted control using an approved no-write route that "
            "records row_refs, selected table/page, table-local scale, same-page "
            "scale, metric_source_scales, metric_scale_sources, and common-scale "
            "input/output."
        ),
        "next_prompt": (
            "/goal Build an exact-doc no-write runtime provenance capture for "
            "CXO plus one additional clean scale-known control from the fixed "
            "scale-table harness, without running count-24, count-32, random "
            "samples, broad extraction, backfill, DB/Qdrant/news/memory writes, "
            "source-PDF edits, prompt/gold/runtime/schema changes, or truth-gate "
            "loosening. Capture row_refs, selected table/page, row/cell text, "
            "table-local scale, same-page scale, document-level scale, "
            "metric_source_scales, metric_scale_sources, and "
            "_common_metric_source_scale input/output. Implement no production "
            "repair unless two clean cases prove the same source-bound root cause."
        ),
    }


def _status(data_missing: list[str]) -> dict[str, Any]:
    return {
        "job_id": JOB_ID,
        "state": "DONE_WITH_RISK",
        "generated_at": _now(),
        "mode": "report_only_no_write_existing_artifacts",
        "no_write_statement": {
            "count24_rerun": False,
            "count32": False,
            "random_sample": False,
            "broad_extraction_or_backfill": False,
            "db_qdrant_redis_news_memory_mutation": False,
            "source_pdf_edits": False,
            "prompt_gold_runtime_schema_changes": False,
            "production_extraction_code_repair": False,
        },
        "data_missing": data_missing,
        "artifacts": [
            str(OUTPUT_DIR / "case_candidate_audit.json"),
            str(OUTPUT_DIR / "provenance_capture.json"),
            str(OUTPUT_DIR / "repair_decision.json"),
            str(OUTPUT_DIR / "README.md"),
        ],
    }


def _readme() -> str:
    return """# Metric-Local Same-Page Scale Provenance Capture

State: DONE_WITH_RISK

## Objective

Build a no-write metric-local same-page scale provenance capture for AZJ plus
one additional clean same-page candidate from the fixed scale-table harness.

## Verdict

No production extraction repair was made.

AZJ remains the only clean same-page scale-propagation candidate in current
artifacts. Its selected formal statement pages carry same-page `$m` evidence,
but runtime metric source scale fields are missing and the common-scale trace
returns `unknown`.

EDU remains fail-closed because selected surfaces are mixed/unclean.

CXO is a clean scale-known control. Parser-cache tables show explicit `$A'000`
scale evidence on the quarterly cash-flow pages, but current accepted-output
artifacts do not expose runtime selected table/row refs, metric source scales,
metric scale source labels, or common-scale trace. CXO therefore cannot serve
as the second same-root repair proof.

## Artifacts

- `case_candidate_audit.json`
- `provenance_capture.json`
- `repair_decision.json`
- `status.json`
- `validation.json`

## Count-24 / Count-32 Decision

Count-24 rerun is not justified.

Count-32 remains blocked.

## DATA_MISSING

- Second clean same-page failure with metric-local row/page/source-scale trace.
- Runtime row refs for accepted CXO metrics.
- Runtime metric source scales for accepted CXO metrics.
- Runtime metric scale source labels for accepted CXO metrics.
- Runtime common-scale input/output trace for accepted CXO metrics.

## Unsafe Actions Avoided

- No count-24 rerun.
- No count-32.
- No random sample.
- No broad extraction/backfill.
- No full ticker-universe extraction.
- No DB/Qdrant/Redis/news/memory mutation.
- No source PDF edits.
- No prompt/gold-label/runtime/schema/model/GPU changes.
- No broad scale inference.
- No truth gate loosening.

## Next Prompt

```text
/goal Build an exact-doc no-write runtime provenance capture for CXO plus one additional clean scale-known control from the fixed scale-table harness, without running count-24, count-32, random samples, broad extraction, backfill, DB/Qdrant/news/memory writes, source-PDF edits, prompt/gold/runtime/schema changes, or truth-gate loosening. Capture row_refs, selected table/page, row/cell text, table-local scale, same-page scale, document-level scale, metric_source_scales, metric_scale_sources, and _common_metric_source_scale input/output. Implement no production repair unless two clean cases prove the same source-bound root cause.
```
"""


def main() -> None:
    harness = _load_json(HARNESS_DIR / "harness_manifest.json")
    cases = harness.get("cases", [])
    case_by_ticker = {
        str(case.get("ticker")): case
        for case in cases
        if isinstance(case, dict) and case.get("ticker")
    }
    pass3a_rows = _pass3a_by_ticker()
    diagnostic_rows = _diagnostic_by_ticker()
    sample_rows = _sample_by_doc_id()

    data_missing = [
        "second_clean_same_page_case_with_metric_local_trace",
        "runtime_row_refs_for_cxo_accepted_metrics",
        "runtime_metric_source_scales_for_cxo",
        "runtime_metric_scale_sources_for_cxo",
        "runtime_common_metric_source_scale_trace_for_cxo",
    ]

    candidate_audit = _case_candidate_audit(cases, pass3a_rows)
    provenance_capture = {
        "job_id": JOB_ID,
        "generated_at": _now(),
        "mode": "no_write_existing_artifact_capture",
        "source_artifacts": {
            "harness_manifest": str(HARNESS_DIR / "harness_manifest.json"),
            "pass3a_capture": str(PASS3A_CAPTURE),
            "selected_table_diagnostic": str(SELECTED_TABLE_DIAGNOSTIC),
            "count24_sample_results": str(COUNT24_SAMPLE_RESULTS),
            "accepted_output_audit": str(ACCEPTED_OUTPUT_AUDIT),
        },
        "documents": {
            "AZJ": _azj_or_edu_capture(
                "AZJ",
                case_by_ticker["AZJ"],
                pass3a_rows.get("AZJ", {}),
                diagnostic_rows.get("AZJ", {}),
            ),
            "EDU": _azj_or_edu_capture(
                "EDU",
                case_by_ticker["EDU"],
                pass3a_rows.get("EDU", {}),
                diagnostic_rows.get("EDU", {}),
            ),
            "CXO": _cxo_capture(
                case_by_ticker["CXO"],
                sample_rows.get(str(case_by_ticker["CXO"].get("document_id")), {}),
            ),
        },
        "second_candidate_decision": candidate_audit["second_candidate_decision"],
        "data_missing": data_missing,
    }

    _write_json(OUTPUT_DIR / "case_candidate_audit.json", candidate_audit)
    _write_json(OUTPUT_DIR / "provenance_capture.json", provenance_capture)
    _write_json(OUTPUT_DIR / "repair_decision.json", _repair_decision(data_missing))
    _write_json(OUTPUT_DIR / "status.json", _status(data_missing))
    (OUTPUT_DIR / "README.md").write_text(_readme(), encoding="utf-8")


if __name__ == "__main__":
    main()
