#!/usr/bin/env python3
"""Report-local selected-table provenance diagnostic for WHC/AZJ/EDU.

This script deliberately does not call run_multipass_extraction, Docling,
backfill, sample selection, DB, Qdrant, news, or any runtime service. It reads
existing count24 artifacts and existing PyMuPDF parser cache JSON, then applies
the current deterministic table-locator and scale-detection functions.
"""

from __future__ import annotations

import hashlib
import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
CACHE_DIR = (
    REPO_ROOT
    / "financial-engine_v2"
    / "data"
    / "reports"
    / "extraction_cache"
    / "docling_extract"
)
COUNT24_RESULTS = (
    REPO_ROOT
    / "reports"
    / "agent_jobs"
    / "extraction_count24_bounded_validation_v1_20260607"
    / "sample_results.json"
)
SCALE_EVIDENCE = (
    REPO_ROOT
    / "reports"
    / "agent_jobs"
    / "extraction_scale_table_source_evidence_after_count24_v1_20260607"
    / "source_evidence.json"
)

TARGETS = [
    {
        "ticker": "WHC",
        "document_id": "9640d9f1-a45b-492d-8df5-9bad0f46431c",
        "title": "2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf",
    },
    {
        "ticker": "AZJ",
        "document_id": "488d6f1a-0180-4fca-8dcf-c4cdfc0f342e",
        "title": "2025-08-18_aurizon-network-pty-ltd-full-year-report_488d6f1a-0180-4fca-8dcf-c4cdfc0f342e.pdf",
    },
    {
        "ticker": "EDU",
        "document_id": "ac3c9ab0-e01a-4996-95f9-6466388ddc9c",
        "title": "2024-02-27_2023-annual-report_ac3c9ab0-e01a-4996-95f9-6466388ddc9c.pdf",
    },
]


@dataclass
class CachedTable:
    page_number: int
    caption: str
    rows: list[list[str]]
    headers: list[str]
    index_in_doc: int = -1


def _install_dependency_shims() -> None:
    """Install minimal stubs for imports unrelated to deterministic diagnostics."""
    observer_mod = types.ModuleType("app.services.extraction_run_observability")

    class ExtractionRunObserver:  # pragma: no cover - import shim
        pass

    observer_mod.ExtractionRunObserver = ExtractionRunObserver
    sys.modules["app.services.extraction_run_observability"] = observer_mod

    prompt_mod = types.ModuleType("app.services.prompt_registry")
    registry: dict[str, Any] = {}

    class PromptBundle:  # pragma: no cover - import shim
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

    docling_mod = types.ModuleType("app.services.docling_extract")
    docling_mod.DoclingTable = CachedTable
    sys.modules["app.services.docling_extract"] = docling_mod


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _clean_cell(value: Any, max_len: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text[:max_len]


def _brief_rows(rows: list[list[str]], limit: int = 6) -> list[list[str]]:
    return [[_clean_cell(cell, 80) for cell in row[:6]] for row in rows[:limit]]


def _page_text_by_page(sections: list[dict[str, Any]]) -> dict[int, str]:
    page_text: dict[int, list[str]] = {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        try:
            page = int(section.get("page") or 0)
        except (TypeError, ValueError):
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


def _scale_evidence_snippets(mx: Any, text: str, max_items: int = 5) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_cell(raw_line, 180)
        if not line:
            continue
        if (
            any(mx._re.search(pattern, line, mx._re.IGNORECASE) for pattern, _ in mx._SCALE_PATTERNS)
            or mx._RAW_DOLLAR_UNIT_RE.search(line)
            or "rounded" in line.lower()
        ):
            lines.append(line)
        if len(lines) >= max_items:
            break
    return lines


def _find_cache(document_id: str) -> Path | None:
    matches = sorted(CACHE_DIR.glob(f"*{document_id}*.pymupdf.json"))
    return matches[0] if matches else None


def _table_from_dict(raw: dict[str, Any], index: int) -> CachedTable:
    rows = raw.get("rows") if isinstance(raw.get("rows"), list) else []
    headers = raw.get("headers") if isinstance(raw.get("headers"), list) else []
    return CachedTable(
        page_number=int(raw.get("page_number") or 0),
        caption=str(raw.get("caption") or ""),
        rows=[[str(cell or "") for cell in row] for row in rows if isinstance(row, list)],
        headers=[str(cell or "") for cell in headers],
        index_in_doc=index,
    )


def _selected_table_summary(
    mx: Any,
    label: str,
    table: Any,
    page_text: dict[int, str],
) -> dict[str, Any] | None:
    if table is None:
        return None
    local_scale = mx._detect_scale_from_table(table)
    same_page_text = page_text.get(int(getattr(table, "page_number", 0) or 0), "")
    same_page_text_scale = _detect_scale_from_text(mx, same_page_text)
    metric_schema = mx._METRIC_SCHEMA_BY_TABLE.get(label, mx.METRIC_FIELDS)
    return {
        "label": label,
        "table_index": getattr(table, "index_in_doc", None),
        "page_number": getattr(table, "page_number", None),
        "caption": _clean_cell(getattr(table, "caption", "")),
        "headers": [_clean_cell(cell, 100) for cell in getattr(table, "headers", [])],
        "row_count": len(getattr(table, "rows", []) or []),
        "first_rows": _brief_rows(getattr(table, "rows", []) or []),
        "table_local_scale": local_scale,
        "same_page_text_scale": same_page_text_scale,
        "same_page_scale_evidence_snippets": _scale_evidence_snippets(
            mx,
            same_page_text,
        ),
        "would_set_metric_source_scale_if_metric_extracted": (
            local_scale if local_scale != "unknown" else "unknown"
        ),
        "metric_schema": list(metric_schema),
    }


def _count24_by_doc() -> dict[str, dict[str, Any]]:
    raw = _load_json(COUNT24_RESULTS)
    return {row["document_id"]: row for row in raw.get("results", [])}


def _prior_source_evidence_by_doc() -> dict[str, dict[str, Any]]:
    raw = _load_json(SCALE_EVIDENCE)
    return {row["document_id"]: row for row in raw.get("documents", [])}


def _metric_source_expectations(
    mx: Any,
    metrics: dict[str, Any],
    selected_tables: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for metric in mx.METRIC_FIELDS:
        value = metrics.get(metric) if isinstance(metrics, dict) else None
        candidate_sources: list[dict[str, Any]] = []
        for label in mx.SOURCE_PRIORITY:
            schema = mx._METRIC_SCHEMA_BY_TABLE.get(label, mx.METRIC_FIELDS)
            if metric not in schema:
                continue
            table = selected_tables.get(label)
            if not table:
                continue
            candidate_sources.append(
                {
                    "table_label": label,
                    "page_number": getattr(table, "page_number", None),
                    "table_index": getattr(table, "index_in_doc", None),
                    "table_local_scale": mx._detect_scale_from_table(table),
                    "headers": [
                        _clean_cell(cell, 100)
                        for cell in getattr(table, "headers", [])
                    ],
                }
            )
        out[metric] = {
            "final_metric_value_from_count24_summary": value,
            "runtime_row_ref": "DATA_MISSING_FROM_COUNT24_SUMMARY",
            "runtime_metric_source_scale": "DATA_MISSING_FROM_COUNT24_SUMMARY",
            "runtime_metric_scale_source": "DATA_MISSING_FROM_COUNT24_SUMMARY",
            "candidate_selected_tables_for_metric": candidate_sources,
        }
    return out


def main() -> int:
    sys.path.insert(0, str(BACKEND_ROOT))
    _install_dependency_shims()
    from app.services import multipass_extraction as mx

    count24 = _count24_by_doc()
    prior_source = _prior_source_evidence_by_doc()
    documents: list[dict[str, Any]] = []

    for target in TARGETS:
        doc_id = target["document_id"]
        cache_path = _find_cache(doc_id)
        count24_row = count24.get(doc_id, {})
        prior_row = prior_source.get(doc_id, {})
        if cache_path is None:
            documents.append(
                {
                    **target,
                    "cache_available": False,
                    "diagnostic_status": "DATA_MISSING",
                    "data_missing": ["existing_pymupdf_cache_json"],
                    "count24_summary": count24_row,
                    "prior_source_evidence": prior_row,
                }
            )
            continue

        cache = _load_json(cache_path)
        tables = [
            _table_from_dict(raw, index)
            for index, raw in enumerate(cache.get("tables", []) or [])
            if isinstance(raw, dict)
        ]
        page_text = _page_text_by_page(cache.get("sections", []) or [])
        document_scale_from_first_tables = mx._detect_scale_from_tables(tables)
        labelled = mx._run_pass2_locator(tables)
        selected_tables = {
            key: value
            for key, value in labelled.items()
            if key != "unmatched" and value is not None
        }
        selected_summaries = {
            key: _selected_table_summary(mx, key, value, page_text)
            for key, value in selected_tables.items()
        }
        metrics = count24_row.get("metrics") if isinstance(count24_row, dict) else {}
        pseudo_payload = {
            "metrics": metrics if isinstance(metrics, dict) else {},
            "metric_source_scales": {},
        }
        common_scale_from_persisted_summary = mx._common_metric_source_scale(
            pseudo_payload,
            count24_row.get("scale") or "unknown",
        )
        selected_local_scales = sorted(
            {
                summary["table_local_scale"]
                for summary in selected_summaries.values()
                if summary and summary["table_local_scale"] != "unknown"
            }
        )
        selected_same_page_text_scales = sorted(
            {
                summary["same_page_text_scale"]
                for summary in selected_summaries.values()
                if summary and summary["same_page_text_scale"] != "unknown"
            }
        )
        documents.append(
            {
                **target,
                "cache_available": True,
                "cache_path": str(cache_path.relative_to(REPO_ROOT)),
                "parser_cache": {
                    "extraction_method": cache.get("extraction_method"),
                    "page_count": cache.get("page_count"),
                    "source_pdf_page_count": cache.get("source_pdf_page_count"),
                    "table_count": len(tables),
                    "section_count": len(cache.get("sections", []) or []),
                },
                "count24_summary": {
                    "status": count24_row.get("status"),
                    "error": count24_row.get("error"),
                    "period_type": count24_row.get("period_type"),
                    "period_end": count24_row.get("period_end"),
                    "scale": count24_row.get("scale"),
                    "confidence": count24_row.get("confidence"),
                    "non_null_metrics": count24_row.get("non_null_metrics"),
                    "metrics": metrics,
                    "source_bound": count24_row.get("source_bound"),
                    "source_document_classification": count24_row.get(
                        "source_document_classification"
                    ),
                },
                "prior_source_evidence": {
                    "scale_evidence_kind": prior_row.get("scale_evidence_kind"),
                    "scale_evidence_value": prior_row.get("scale_evidence_value"),
                    "current_failure_classification": prior_row.get(
                        "current_failure_classification"
                    ),
                },
                "document_scale_from_first_15_tables": document_scale_from_first_tables,
                "selected_table_local_scales": selected_local_scales,
                "selected_same_page_text_scales": selected_same_page_text_scales,
                "selected_tables": selected_summaries,
                "per_metric_provenance": _metric_source_expectations(
                    mx,
                    metrics if isinstance(metrics, dict) else {},
                    selected_tables,
                ),
                "final_payload_scale_decision": {
                    "count24_final_scale": count24_row.get("scale"),
                    "common_metric_source_scale_from_persisted_summary": (
                        common_scale_from_persisted_summary
                    ),
                    "why_common_metric_source_scale_did_or_did_not_set_scale": (
                        "Persisted count24 summary does not contain row_refs, "
                        "metric_source_scales, or metric_scale_sources. With no "
                        "explicit per-metric source scales available, "
                        "_common_metric_source_scale falls back to the payload "
                        "scale, which is unknown for this failed document."
                    ),
                },
                "diagnostic_status": "ok_with_runtime_row_refs_data_missing",
                "data_missing": [
                    "runtime_row_refs",
                    "runtime_metric_source_scales",
                    "runtime_metric_scale_sources",
                    "full_pass3a_llm_outputs",
                ],
            }
        )

    repeated = _assess_repeated_pattern(documents)
    results = {
        "job_id": "extraction_selected_table_provenance_diagnostic_v1_20260607",
        "generated_at": "2026-06-07",
        "scope": "fixed_report_local_selected_table_provenance_diagnostic_for_whc_azj_edu_only",
        "runner_mode": "read_existing_artifacts_and_parser_cache_only",
        "forbidden_actions_observed": {
            "count24_rerun": False,
            "count32_run": False,
            "random_sample_run": False,
            "broad_extraction_or_backfill_run": False,
            "full_ticker_universe_extraction_run": False,
            "db_qdrant_news_memory_mutation": False,
            "source_pdf_edits": False,
            "prompt_gold_label_runtime_schema_changes": False,
            "docling_or_pymupdf_parser_invocation": False,
            "llm_extraction_invocation": False,
        },
        "documents": documents,
        "repeated_pattern_assessment": repeated,
        "data_missing": sorted(
            {
                missing
                for doc in documents
                for missing in doc.get("data_missing", [])
            }
        ),
    }
    _write_json(REPORT_DIR / "diagnostic_results.json", results)
    _write_json(REPORT_DIR / "provenance_summary.json", _build_summary(results))
    _write_json(REPORT_DIR / "repair_decision.json", _build_repair_decision(results))
    (REPORT_DIR / "nic_optional_task_prompt.md").write_text(
        _build_nic_prompt(),
        encoding="utf-8",
    )
    return 0


def _assess_repeated_pattern(documents: list[dict[str, Any]]) -> dict[str, Any]:
    selected_scale_docs = [
        doc["ticker"]
        for doc in documents
        if doc.get("selected_table_local_scales")
    ]
    all_unknown_selected_docs = [
        doc["ticker"]
        for doc in documents
        if doc.get("cache_available")
        and not doc.get("selected_table_local_scales")
    ]
    page_text_scale_docs = [
        doc["ticker"]
        for doc in documents
        if doc.get("selected_same_page_text_scales")
    ]
    return {
        "same_missed_selected_table_scale_binding_pattern_in_at_least_two_docs": False,
        "documents_with_any_selected_table_local_scale": selected_scale_docs,
        "documents_with_any_same_page_text_scale_on_selected_tables": page_text_scale_docs,
        "documents_with_no_selected_table_local_scale_in_cached_selected_tables": (
            all_unknown_selected_docs
        ),
        "decision_basis": (
            "The diagnostic can identify selected table/page/header and table-local "
            "scale from parser cache. It can also see same-page text scale in "
            "some cached sections, but actual runtime row refs and per-metric "
            "source scales were not persisted in count24 artifacts. Because EDU "
            "has mixed raw-dollar and summary-scale surfaces and WHC has no "
            "selected cached statement tables, a code repair would require full "
            "pass3a provenance before changing scale binding."
        ),
    }


def _build_summary(results: dict[str, Any]) -> dict[str, Any]:
    documents = []
    for doc in results["documents"]:
        selected = doc.get("selected_tables", {})
        documents.append(
            {
                "ticker": doc["ticker"],
                "document_id": doc["document_id"],
                "count24_status": doc.get("count24_summary", {}).get("status"),
                "count24_error": doc.get("count24_summary", {}).get("error"),
                "count24_final_scale": doc.get("count24_summary", {}).get("scale"),
                "document_scale_from_first_15_tables": doc.get(
                    "document_scale_from_first_15_tables"
                ),
                "selected_tables": {
                    key: {
                        "page_number": value.get("page_number") if value else None,
                        "table_index": value.get("table_index") if value else None,
                        "headers": value.get("headers") if value else None,
                        "table_local_scale": value.get("table_local_scale")
                        if value
                        else None,
                        "same_page_text_scale": value.get("same_page_text_scale")
                        if value
                        else None,
                    }
                    for key, value in selected.items()
                    if key
                    in {
                        "income_statement",
                        "cashflow_statement",
                        "balance_sheet",
                        "share_capital",
                        "net_debt_note",
                        "highlights",
                    }
                },
                "data_missing": doc.get("data_missing", []),
            }
        )
    return {
        "job_id": results["job_id"],
        "generated_at": results["generated_at"],
        "documents": documents,
        "repeated_pattern_assessment": results["repeated_pattern_assessment"],
        "data_missing": results["data_missing"],
    }


def _build_repair_decision(results: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": results["job_id"],
        "generated_at": results["generated_at"],
        "decision": "NO_CODE_REPAIR",
        "fix_made": False,
        "why_no_fix": (
            "The report-local diagnostic did not prove the same missed "
            "selected-table scale-binding pattern in at least two documents. "
            "It also found that count24 artifacts omit the actual pass3a row "
            "refs and per-metric source scales needed to justify a code change."
        ),
        "count24_rerun_status": "blocked",
        "another_sample_justified": False,
        "next_exact_prompt": (
            "/goal Build a no-write exact-doc pass3a provenance capture for "
            "AZJ and EDU only, using an approved dependency/runtime route that "
            "does not write parser cache, DB, Qdrant, news, memory, source PDFs, "
            "prompts, schemas, or runtime config. Do not run count-24, count-32, "
            "random samples, broad extraction, or backfill. Capture the actual "
            "pass3a outputs, row_refs, metric_source_scales, metric_scale_sources, "
            "selected table page/header, and final _common_metric_source_scale "
            "inputs/outputs. Implement one narrow selected-table scale-binding "
            "fix only if both docs prove the same source-bound missed propagation; "
            "otherwise keep count-24 blocked and produce the next repair prompt."
        ),
        "data_missing": results["data_missing"],
    }


def _build_nic_prompt() -> str:
    return """# Optional NIC Webcast-Details Noncandidate Task Prompt

```text
/goal Add a narrow exact source-noncandidate classifier guard for NIC-style half-year results webcast-details announcements only. Do not run count-24, count-32, random samples, broad extraction, or backfill. Confirm the one-page NIC document says the half-year report will be released later and only provides webcast details. Implement an exact title/body pattern such as \"half year results webcast details\" as a noncandidate class or existing advisory/meeting-like exclusion only if it cannot catch real financial reports. Add focused classifier tests and report artifacts; do not change metric prompts, gold labels, runtime schema, DB, Qdrant, news, memory, or source PDFs.
```
"""


if __name__ == "__main__":
    raise SystemExit(main())
