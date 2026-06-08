#!/usr/bin/env python3
"""Exact-doc no-write provenance capture for CXO plus NSR.

This runner deliberately avoids run_multipass_extraction(), extract_structured(),
count runners, service startup, DB/Qdrant/news/memory paths, and cache writes. It
uses the in-memory PyMuPDF helper plus deterministic multipass helpers only.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JOB_ID = "extraction_cxo_runtime_provenance_capture_v1_20260608"
REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
COUNT24_RESULTS = (
    REPO_ROOT
    / "reports"
    / "agent_jobs"
    / "extraction_count24_bounded_validation_v1_20260607"
    / "sample_results.json"
)
HARNESS_MANIFEST = (
    REPO_ROOT
    / "reports"
    / "agent_jobs"
    / "extraction_regression_consolidation_after_count24_v1_20260607"
    / "harness_manifest.json"
)
CACHE_DIRS = [
    REPO_ROOT
    / "financial-engine_v2"
    / "data"
    / "reports"
    / "extraction_cache"
    / "docling_extract",
    Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/extraction_cache/docling_extract"),
    Path("/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/data/reports/extraction_cache/docling_extract"),
]

TARGET_DOC_IDS = {
    "control_CXO_36e172ec": "36e172ec-2650-4a9f-9ef0-a4366a3b8d31",
    "control_NSR_f2240712": "f2240712-9dde-41e0-88fa-29c1a0080dab",
}

METRIC_ROW_HINTS = {
    "revenue": ("revenue", "sales", "income"),
    "ebit": ("ebit", "operating profit", "profit before", "earnings before"),
    "np_attributable": (
        "net profit",
        "profit after",
        "profit/(loss)",
        "loss after",
        "comprehensive income",
    ),
    "operating_cf": ("operating activities", "operating cash", "receipts", "payments"),
    "investing_cf": ("investing activities", "investments", "exploration"),
    "financing_cf": ("financing activities", "borrowings", "equity", "finance"),
    "capex": ("capital expenditure", "property", "plant", "equipment", "exploration"),
    "cash_end": ("cash and cash equivalents", "cash at end", "cash balance"),
    "net_debt": ("net debt", "borrowings", "debt"),
    "shares_outstanding": ("shares", "ordinary shares", "share capital"),
}


def _install_dependency_shims() -> None:
    observer_mod = types.ModuleType("app.services.extraction_run_observability")

    class ExtractionRunObserver:  # pragma: no cover - import shim only
        pass

    observer_mod.ExtractionRunObserver = ExtractionRunObserver
    sys.modules["app.services.extraction_run_observability"] = observer_mod

    prompt_mod = types.ModuleType("app.services.prompt_registry")
    registry: dict[str, Any] = {}

    class PromptBundle:  # pragma: no cover - not used by this runner
        def __init__(
            self,
            id: str,
            pass1: str,
            pass3a: str,
            pass3b: str,
            description: str = "",
        ) -> None:
            self.id = id
            self.pass1 = pass1
            self.pass3a = pass3a
            self.pass3b = pass3b
            self.description = description

        def compute_hash(self) -> str:
            material = "\n".join([self.pass1, self.pass3a, self.pass3b])
            return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def register_bundle(bundle: PromptBundle) -> None:
        registry[bundle.id] = bundle

    def resolve(bundle_id: str | None = None) -> PromptBundle:
        return registry[bundle_id or "default"]

    prompt_mod.PromptBundle = PromptBundle
    prompt_mod.register_bundle = register_bundle
    prompt_mod.resolve = resolve
    sys.modules["app.services.prompt_registry"] = prompt_mod


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _clean_cell(value: Any, max_len: int = 160) -> str:
    text = " ".join(str(value or "").split())
    return text[:max_len]


def _brief_rows(rows: list[list[str]], limit: int = 8) -> list[list[str]]:
    return [[_clean_cell(cell, 100) for cell in row[:8]] for row in rows[:limit]]


def _page_text_by_page(sections: list[dict[str, Any]]) -> dict[int, str]:
    page_text: dict[int, list[str]] = {}
    for section in sections:
        try:
            page = int(section.get("page") or 0)
        except (AttributeError, TypeError, ValueError):
            continue
        text = str(section.get("text") or "")
        if text:
            page_text.setdefault(page, []).append(text)
    return {page: "\n".join(parts) for page, parts in page_text.items()}


def _detect_scale_from_text(mx: Any, text: str) -> str:
    for pattern, scale in mx._SCALE_PATTERNS:
        if mx._re.search(pattern, text, mx._re.IGNORECASE):
            return scale
    if mx._RAW_DOLLAR_UNIT_RE.search(text):
        return "units"
    return "unknown"


def _scale_evidence_snippets(mx: Any, text: str, max_items: int = 6) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_cell(raw_line, 220)
        if not line:
            continue
        if (
            any(
                mx._re.search(pattern, line, mx._re.IGNORECASE)
                for pattern, _ in mx._SCALE_PATTERNS
            )
            or mx._RAW_DOLLAR_UNIT_RE.search(line)
            or "rounded" in line.lower()
        ):
            lines.append(line)
        if len(lines) >= max_items:
            break
    return lines


def _find_cache_paths(document_id: str) -> list[str]:
    matches: list[str] = []
    for cache_dir in CACHE_DIRS:
        if not cache_dir.is_dir():
            continue
        for path in sorted(cache_dir.glob(f"*{document_id}*.json")):
            matches.append(str(path))
    return matches


def _count24_by_doc() -> dict[str, dict[str, Any]]:
    raw = _load_json(COUNT24_RESULTS)
    return {
        str(row.get("document_id")): row
        for row in raw.get("results", [])
        if isinstance(row, dict) and row.get("document_id")
    }


def _harness_cases_by_id() -> dict[str, dict[str, Any]]:
    raw = _load_json(HARNESS_MANIFEST)
    return {
        str(row.get("case_id")): row
        for row in raw.get("cases", [])
        if isinstance(row, dict) and row.get("case_id")
    }


def _clean_scale_control_candidates(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for case in cases.values():
        expected = case.get("expected_fail_closed_reason_or_metrics")
        if not isinstance(expected, dict):
            continue
        if case.get("expected_gate_or_status") != "ok":
            continue
        if expected.get("scale") != "thousands":
            continue
        candidates.append(
            {
                "case_id": case.get("case_id"),
                "ticker": case.get("ticker"),
                "document_id": case.get("document_id"),
                "expected_classification": case.get("expected_classification"),
                "period_type": expected.get("period_type"),
                "period_end": expected.get("period_end"),
                "scale": expected.get("scale"),
                "non_null_metrics": expected.get("non_null_metrics"),
            }
        )
    return sorted(
        candidates,
        key=lambda item: (
            item["case_id"] != "control_NSR_f2240712",
            item.get("expected_classification") != "financial_report",
            -(int(item.get("non_null_metrics") or 0)),
            str(item.get("case_id")),
        ),
    )


def _source_pdf_stat(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "mode": oct(stat.st_mode & 0o777),
    }


def _selected_table_summary(
    mx: Any,
    label: str,
    table: Any,
    page_text: dict[int, str],
) -> dict[str, Any]:
    rows = getattr(table, "rows", []) or []
    page_number = int(getattr(table, "page_number", 0) or 0)
    same_page_text = page_text.get(page_number, "")
    table_local_scale = mx._detect_scale_from_table(table)
    return {
        "label": label,
        "table_index": getattr(table, "index_in_doc", None),
        "page_number": page_number,
        "caption": _clean_cell(getattr(table, "caption", "")),
        "headers": [_clean_cell(cell, 120) for cell in getattr(table, "headers", [])],
        "row_count": len(rows),
        "first_rows": _brief_rows(rows),
        "table_local_scale": table_local_scale,
        "same_page_scale": _detect_scale_from_text(mx, same_page_text),
        "same_page_scale_evidence_snippets": _scale_evidence_snippets(mx, same_page_text),
        "metric_schema": list(mx._METRIC_SCHEMA_BY_TABLE.get(label, mx.METRIC_FIELDS)),
    }


def _metric_candidate_rows(mx: Any, metric: str, table: Any) -> list[dict[str, Any]]:
    hints = METRIC_ROW_HINTS.get(metric, ())
    rows = getattr(table, "rows", []) or []
    matches: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        cells = [_clean_cell(cell, 120) for cell in row]
        row_text = " ".join(cells).lower()
        if not any(hint in row_text for hint in hints):
            continue
        matches.append(
            {
                "row_index": index,
                "row_label": cells[0] if cells else "",
                "cells": cells[:8],
            }
        )
        if len(matches) >= 6:
            break
    return matches


def _per_metric_capture(
    mx: Any,
    metrics: dict[str, Any],
    selected_tables: dict[str, Any],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for metric in mx.METRIC_FIELDS:
        candidate_tables: list[dict[str, Any]] = []
        for label in mx.SOURCE_PRIORITY:
            table = selected_tables.get(label)
            if table is None:
                continue
            schema = mx._METRIC_SCHEMA_BY_TABLE.get(label, mx.METRIC_FIELDS)
            if metric not in schema:
                continue
            candidate_tables.append(
                {
                    "label": label,
                    "page_number": getattr(table, "page_number", None),
                    "table_index": getattr(table, "index_in_doc", None),
                    "table_local_scale": mx._detect_scale_from_table(table),
                    "candidate_row_cell_text": _metric_candidate_rows(mx, metric, table),
                }
            )
        output[metric] = {
            "final_metric_value_from_count24_summary": metrics.get(metric),
            "runtime_row_ref": "DATA_MISSING_NO_PASS3A_DEBUG_CAPTURE",
            "runtime_metric_source_scale": "DATA_MISSING_NO_PASS3A_DEBUG_CAPTURE",
            "runtime_metric_scale_source": "DATA_MISSING_NO_PASS3A_DEBUG_CAPTURE",
            "candidate_selected_tables_for_metric": candidate_tables,
        }
    return output


def _common_scale_trace(mx: Any, count24_row: dict[str, Any]) -> dict[str, Any]:
    metrics = count24_row.get("metrics") if isinstance(count24_row.get("metrics"), dict) else {}
    fallback = count24_row.get("scale") or "unknown"
    input_payload = {
        "metrics": metrics,
        "metric_source_scales": {},
    }
    return {
        "input_kind": "count24_summary_without_pass3a_metric_source_scales",
        "input_payload": input_payload,
        "fallback": fallback,
        "output": mx._common_metric_source_scale(input_payload, fallback),
        "actual_runtime_input_output": "DATA_MISSING_NO_PASS3A_DEBUG_CAPTURE",
    }


def _capture_document(
    mx: Any,
    dx: Any,
    target: dict[str, Any],
    count24_row: dict[str, Any],
) -> dict[str, Any]:
    source_path = Path(str(target.get("source_path") or ""))
    before_pdf_stat = _source_pdf_stat(source_path)
    cache_before = _find_cache_paths(str(target["document_id"]))
    doc_payload: dict[str, Any] = {
        "case_id": target["case_id"],
        "ticker": target["ticker"],
        "document_id": target["document_id"],
        "title": target.get("title"),
        "source_path": str(source_path),
        "expected": target.get("expected_fail_closed_reason_or_metrics"),
        "harness_expected_classification": target.get("expected_classification"),
        "harness_expected_gate_or_status": target.get("expected_gate_or_status"),
        "source_pdf_before": before_pdf_stat,
        "parser_cache_before": cache_before,
        "count24_summary": {
            "status": count24_row.get("status"),
            "error": count24_row.get("error"),
            "period_type": count24_row.get("period_type"),
            "period_end": count24_row.get("period_end"),
            "scale": count24_row.get("scale"),
            "currency": count24_row.get("currency"),
            "confidence": count24_row.get("confidence"),
            "non_null_metrics": count24_row.get("non_null_metrics"),
            "metrics": count24_row.get("metrics"),
            "source_bound": count24_row.get("source_bound"),
            "source_document_classification": count24_row.get(
                "source_document_classification"
            ),
            "persisted_row_refs": count24_row.get("row_refs", "DATA_MISSING"),
            "persisted_metric_source_scales": count24_row.get(
                "metric_source_scales",
                "DATA_MISSING",
            ),
            "persisted_metric_scale_sources": count24_row.get(
                "metric_scale_sources",
                "DATA_MISSING",
            ),
        },
        "no_write_runtime_route": {
            "called_run_multipass_extraction": False,
            "called_extract_structured_public_cache_wrapper": False,
            "called_pass3a_llm_extractor": False,
            "called_private_in_memory_pymupdf_helper": False,
            "reason": (
                "Public parser/runtime path writes parser cache on cache miss; "
                "this runner uses private in-memory parser helper only."
            ),
        },
        "data_missing": [],
    }
    if not before_pdf_stat.get("exists"):
        doc_payload["capture_status"] = "DATA_MISSING"
        doc_payload["data_missing"].append("source_pdf")
        return doc_payload

    structured_doc = dx._extract_pymupdf(str(source_path))
    doc_payload["no_write_runtime_route"]["called_private_in_memory_pymupdf_helper"] = True
    for index, table in enumerate(structured_doc.tables):
        setattr(table, "index_in_doc", index)

    page_text = _page_text_by_page(structured_doc.sections)
    first_page_text = page_text.get(1, "")
    document_scale_from_tables = mx._detect_scale_from_tables(structured_doc.tables)
    document_scale_from_first_page_text = _detect_scale_from_text(mx, first_page_text)
    labelled = mx._run_pass2_locator(structured_doc.tables)
    selected_tables = {
        label: table
        for label, table in labelled.items()
        if label != "unmatched" and table is not None
    }
    selected_table_summaries = {
        label: _selected_table_summary(mx, label, table, page_text)
        for label, table in selected_tables.items()
    }
    metrics = count24_row.get("metrics") if isinstance(count24_row.get("metrics"), dict) else {}
    doc_payload.update(
        {
            "capture_status": "partial_no_write_capture",
            "parser_capture": {
                "method": structured_doc.extraction_method,
                "page_count": structured_doc.page_count,
                "table_count": len(structured_doc.tables),
                "section_count": len(structured_doc.sections),
            },
            "document_level_scale": {
                "from_tables": document_scale_from_tables,
                "from_first_page_text": document_scale_from_first_page_text,
                "count24_final_scale": count24_row.get("scale"),
            },
            "selected_tables": selected_table_summaries,
            "per_metric_runtime_provenance": _per_metric_capture(
                mx,
                metrics,
                selected_tables,
            ),
            "common_metric_source_scale_trace": _common_scale_trace(mx, count24_row),
        }
    )
    if not cache_before:
        doc_payload["data_missing"].append("existing_parser_cache_json")
    doc_payload["data_missing"].extend(
        [
            "full_pass3a_llm_outputs",
            "runtime_row_refs",
            "runtime_metric_source_scales",
            "runtime_metric_scale_sources",
            "debug_capture_full_payload",
        ]
    )

    doc_payload["source_pdf_after"] = _source_pdf_stat(source_path)
    doc_payload["parser_cache_after"] = _find_cache_paths(str(target["document_id"]))
    doc_payload["no_write_evidence"] = {
        "source_pdf_stat_unchanged": (
            doc_payload["source_pdf_before"] == doc_payload["source_pdf_after"]
        ),
        "parser_cache_paths_unchanged": (
            doc_payload["parser_cache_before"] == doc_payload["parser_cache_after"]
        ),
    }
    return doc_payload


def main() -> int:
    sys.path.insert(0, str(BACKEND_ROOT))
    _install_dependency_shims()
    from app.services import docling_extract as dx
    from app.services import multipass_extraction as mx

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cases = _harness_cases_by_id()
    count24 = _count24_by_doc()
    clean_candidates = _clean_scale_control_candidates(cases)
    target_cases = []
    for case_id, document_id in TARGET_DOC_IDS.items():
        case = cases.get(case_id)
        if not case:
            raise RuntimeError(f"missing harness case {case_id}")
        if case.get("document_id") != document_id:
            raise RuntimeError(f"unexpected document_id for {case_id}: {case.get('document_id')}")
        target_cases.append(case)

    documents = [
        _capture_document(mx, dx, target, count24.get(str(target["document_id"]), {}))
        for target in target_cases
    ]
    shared_capture_gap = all(
        "runtime_metric_source_scales" in doc.get("data_missing", [])
        for doc in documents
    )
    shared_source_bound_root_cause = False
    common_trace = {
        str(doc["document_id"]): doc.get("common_metric_source_scale_trace", {})
        for doc in documents
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    output = {
        "job_id": JOB_ID,
        "generated_at": generated_at,
        "state": "DONE_WITH_RISK",
        "scope": "exact_doc_no_write_runtime_provenance_capture_for_cxo_plus_nsr",
        "runner_mode": "private_in_memory_pymupdf_plus_persisted_count24_summary_no_pass3a",
        "control_selection": {
            "selected": ["control_CXO_36e172ec", "control_NSR_f2240712"],
            "clean_scale_control_candidates": clean_candidates,
            "why_nsr": (
                "Live harness contains the recommended NSR case as an ok "
                "financial_report clean scale-known control with thousands scale "
                "and 8 non-null metrics; no cleaner financial_report control was "
                "identified for this exact-doc capture."
            ),
        },
        "forbidden_actions_observed": {
            "count24_rerun": False,
            "count32_run": False,
            "random_sample_run": False,
            "broad_extraction_or_backfill_run": False,
            "run_multipass_extraction_call": False,
            "public_extract_structured_cache_wrapper_call": False,
            "pass3a_llm_call": False,
            "db_qdrant_redis_news_memory_mutation": False,
            "source_pdf_edit": False,
            "prompt_gold_label_runtime_schema_config_change": False,
            "service_start": False,
            "github_mutation": False,
            "production_repair": False,
        },
        "documents": documents,
        "common_metric_source_scale_trace": common_trace,
        "root_cause_assessment": {
            "two_cases_shared_source_bound_production_root_cause": (
                shared_source_bound_root_cause
            ),
            "shared_capture_evidence_gap": shared_capture_gap,
            "assessment": (
                "Both exact docs are clean accepted count24 controls, but the "
                "available persisted summaries omit runtime pass3a row refs and "
                "metric source-scale fields, and no existing parser cache was "
                "available. This is a no-write capture evidence gap, not proof "
                "of a shared source-bound production extraction defect."
            ),
        },
        "production_repair": {
            "implemented": False,
            "why": (
                "The two clean controls did not prove the same source-bound "
                "production root cause. Missing pass3a provenance is an evidence "
                "availability gap under the no-write constraints."
            ),
        },
        "data_missing": sorted(
            {
                item
                for doc in documents
                for item in doc.get("data_missing", [])
            }
        ),
    }
    _write_json(REPORT_DIR / "runtime_provenance_capture.json", output)
    _write_json(REPORT_DIR / "common_metric_source_scale_trace.json", common_trace)
    _write_json(
        REPORT_DIR / "status.json",
        {
            "job_id": JOB_ID,
            "generated_at": generated_at,
            "state": "DONE_WITH_RISK",
            "task_card": (
                "docs/agent_tasks/"
                "extraction_cxo_runtime_provenance_capture_v1_20260608.md"
            ),
            "report_path": (
                "reports/agent_jobs/"
                "extraction_cxo_runtime_provenance_capture_v1_20260608/README.md"
            ),
            "exact_docs_used": [
                {
                    "case_id": doc["case_id"],
                    "ticker": doc["ticker"],
                    "document_id": doc["document_id"],
                    "source_path": doc["source_path"],
                }
                for doc in documents
            ],
            "two_cases_shared_source_bound_production_root_cause": (
                shared_source_bound_root_cause
            ),
            "shared_capture_evidence_gap": shared_capture_gap,
            "production_repair_implemented": False,
            "data_missing": output["data_missing"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
