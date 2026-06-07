#!/usr/bin/env python3
"""No-write exact-doc Pass 3a provenance capture for AZJ and EDU.

The runner reads count-24 artifacts and cached parser JSON from the count-24
worktree, then patches the parser call in memory so multipass extraction uses
the selected cached document. It does not run sample selection, backfill,
database upserts, Qdrant, Redis, news, prompt edits, source-PDF edits, or parser
cache writes.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


JOB_ID = "extraction_azj_edu_pass3a_provenance_capture_v1_20260607"
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
OUTPUT_DIR = Path(__file__).resolve().parent
COUNT24_ROOT = Path(
    "/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs"
)
COUNT24_RESULTS = (
    COUNT24_ROOT
    / "extraction_count24_bounded_validation_v1_20260607"
    / "sample_results.json"
)
COUNT24_MANIFEST = (
    COUNT24_ROOT
    / "extraction_count24_bounded_validation_v1_20260607"
    / "sample_manifest.json"
)
SCALE_EVIDENCE = (
    COUNT24_ROOT
    / "extraction_scale_table_source_evidence_after_count24_v1_20260607"
    / "source_evidence.json"
)
DIAGNOSTIC_RESULTS = (
    REPO_ROOT
    / "reports"
    / "agent_jobs"
    / "extraction_selected_table_provenance_diagnostic_v1_20260607"
    / "diagnostic_results.json"
)
COUNT24_CACHE_ROOT = (
    Path("/home/l4nd0/tenn-count24-bounded-validation-v1-20260607")
    / "financial-engine_v2"
    / "data"
    / "reports"
    / "extraction_cache"
    / "docling_extract"
)

TARGETS = {
    "488d6f1a-0180-4fca-8dcf-c4cdfc0f342e": "AZJ",
    "ac3c9ab0-e01a-4996-95f9-6466388ddc9c": "EDU",
}

SAFE_ENV_DEFAULTS = {
    "DATABASE_URL": "sqlite:///:memory:",
    "TASK_MODE": "sync",
    "AUTO_CREATE_TABLES": "false",
    "ENABLE_EMBEDDINGS": "false",
    "ENABLE_QDRANT": "false",
    "OLLAMA_URL": "http://127.0.0.1:11434",
    "LLAMACPP_URL": "http://127.0.0.1:8001",
    "EXTRACTION_LLAMACPP_URL": "http://127.0.0.1:8001",
    "LLM_API_KEY": "local-openai-key",
    "EXTRACT_MODEL": "model:qwen2.5-14b-instruct",
    "EXTRACTION_SKIP_NARRATIVE": "1",
    "EXTRACTION_PARALLEL": "0",
}

METRIC_FIELDS = [
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
]


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


def _all_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_all_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_all_dicts(child))
    return found


def _records_by_doc(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = _load_json(path)
    records: dict[str, dict[str, Any]] = {}
    for row in _all_dicts(payload):
        doc_id = row.get("document_id")
        if doc_id in TARGETS and doc_id not in records:
            records[doc_id] = row
    return records


def _diagnostic_by_doc() -> dict[str, dict[str, Any]]:
    payload = _load_json(DIAGNOSTIC_RESULTS)
    return {
        row["document_id"]: row
        for row in payload.get("documents", [])
        if row.get("document_id") in TARGETS
    }


def _source_path_from_records(doc_id: str, records: list[dict[str, dict[str, Any]]]) -> str:
    for mapping in records:
        row = mapping.get(doc_id, {})
        source_path = row.get("source_path") or row.get("pdf_path")
        if source_path:
            text = str(source_path)
            if text.startswith("mnt/"):
                return "/" + text
            return text
    return "DATA_MISSING"


def _cache_path_for_doc(doc_id: str, title: str, diagnostic_row: dict[str, Any]) -> Path | None:
    cache_path = diagnostic_row.get("cache_path")
    if cache_path:
        candidate = COUNT24_CACHE_ROOT / Path(str(cache_path)).name
        if candidate.exists():
            return candidate
    matches = sorted(COUNT24_CACHE_ROOT.glob(f"*{doc_id}*.json"))
    if matches:
        return matches[0]
    title_matches = sorted(COUNT24_CACHE_ROOT.glob(f"*{Path(title).stem[:64]}*.json"))
    return title_matches[0] if title_matches else None


def _section_text_by_page(sections: list[dict[str, Any]]) -> dict[int, str]:
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


def _scale_snippets(mx: Any, text: str, max_items: int = 6) -> list[str]:
    snippets: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_text(raw_line, 220)
        if not line:
            continue
        if (
            any(mx._re.search(pattern, line, mx._re.IGNORECASE) for pattern, _ in mx._SCALE_PATTERNS)
            or mx._RAW_DOLLAR_UNIT_RE.search(line)
            or "nearest $100,000" in line.lower()
            or "rounded" in line.lower()
        ):
            snippets.append(line)
        if len(snippets) >= max_items:
            break
    return snippets


def _detect_scale_from_text(mx: Any, text: str) -> str:
    for pattern, scale in mx._SCALE_PATTERNS:
        if mx._re.search(pattern, text, mx._re.IGNORECASE):
            return scale
    if mx._RAW_DOLLAR_UNIT_RE.search(text):
        return "units"
    return "unknown"


def _headers_for_table(table: Any) -> list[str]:
    return [_clean_text(cell, 120) for cell in getattr(table, "headers", [])]


def _table_head_rows(table: Any, limit: int = 6) -> list[list[str]]:
    rows = getattr(table, "rows", []) or []
    return [[_clean_text(cell, 100) for cell in row[:8]] for row in rows[:limit]]


def _markdown_rows_for_ref(markdown: str, row_ref: Any) -> list[str]:
    ref = _clean_text(row_ref, 160)
    if not ref or ref == "unknown":
        return []
    normalized_ref = re.sub(r"\s+", " ", ref).lower()
    rows: list[str] = []
    for raw in markdown.splitlines():
        line = _clean_text(raw, 500)
        if not line or set(line.replace("|", "").strip()) <= {"-"}:
            continue
        normalized_line = re.sub(r"\s+", " ", line).lower()
        if normalized_ref in normalized_line:
            rows.append(line)
    return rows[:3]


def _value_cells_from_rows(rows: list[str]) -> list[list[str]]:
    out: list[list[str]] = []
    for row in rows:
        cells = [_clean_text(cell, 100) for cell in row.strip("|").split("|")]
        out.append(cells[1:] if len(cells) > 1 else cells)
    return out


def _llm_phase(prompt: str) -> str:
    if "Table type:" in prompt and "Table (markdown):" in prompt:
        return "pass3a"
    if "financial report classifier" in prompt.lower() or "report_type" in prompt:
        return "pass1"
    if "financial narrative extractor" in prompt.lower():
        return "pass3b"
    return "unknown"


def _llm_table_type(prompt: str) -> str | None:
    match = re.search(r"Table type:\s*([A-Za-z0-9_ -]+)", prompt)
    return match.group(1).strip() if match else None


@contextmanager
def _patched_cached_parser(docling_extract: Any, structured_doc: Any):
    original_extract = docling_extract.extract_structured
    original_save = getattr(docling_extract, "_save_cache", None)

    def _no_write_save(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("no_write_cache_save_blocked")

    def _return_cached(*_args: Any, **_kwargs: Any) -> Any:
        return structured_doc

    docling_extract.extract_structured = _return_cached
    if original_save is not None:
        docling_extract._save_cache = _no_write_save
    try:
        yield
    finally:
        docling_extract.extract_structured = original_extract
        if original_save is not None:
            docling_extract._save_cache = original_save


@contextmanager
def _captured_llm_calls(mx: Any):
    original = mx._llm_json_call
    calls: list[dict[str, Any]] = []

    def _wrapped(prompt: str, llm_client: Any, max_tokens: int = 512, *, model_override: str | None = None) -> dict[str, Any]:
        started = time.monotonic()
        phase = _llm_phase(prompt)
        table_type = _llm_table_type(prompt)
        try:
            result = original(
                prompt,
                llm_client,
                max_tokens=max_tokens,
                model_override=model_override,
            )
            calls.append(
                {
                    "phase": phase,
                    "table_type": table_type,
                    "status": "ok",
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "max_tokens": max_tokens,
                    "prompt_chars": len(prompt),
                    "raw_output": result,
                }
            )
            return result
        except Exception as exc:
            calls.append(
                {
                    "phase": phase,
                    "table_type": table_type,
                    "status": "failed",
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "max_tokens": max_tokens,
                    "prompt_chars": len(prompt),
                    "error": str(exc),
                }
            )
            raise

    mx._llm_json_call = _wrapped
    try:
        yield calls
    finally:
        mx._llm_json_call = original


def _selected_table_report(mx: Any, structured_doc: Any) -> dict[str, dict[str, Any]]:
    labelled = mx._run_pass2_locator(structured_doc.tables)
    page_text = _section_text_by_page(structured_doc.sections)
    report: dict[str, dict[str, Any]] = {}
    for table_type, table in labelled.items():
        if table_type == "unmatched" or table is None:
            continue
        page = getattr(table, "page_number", None)
        same_page_text = page_text.get(int(page), "") if page is not None else ""
        report[table_type] = {
            "page_number": page,
            "headers": _headers_for_table(table),
            "table_local_scale": mx._detect_scale_from_table(table),
            "same_page_scale": _detect_scale_from_text(mx, same_page_text),
            "same_page_scale_snippets": _scale_snippets(mx, same_page_text),
            "caption": _clean_text(getattr(table, "caption", ""), 220),
            "head_rows": _table_head_rows(table),
        }
    return report


def _metric_source_trace(payload: dict[str, Any], pass3a_results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    row_refs = payload.get("row_refs") if isinstance(payload.get("row_refs"), dict) else {}
    metric_source_scales = (
        payload.get("metric_source_scales")
        if isinstance(payload.get("metric_source_scales"), dict)
        else {}
    )
    metric_scale_sources = (
        payload.get("metric_scale_sources")
        if isinstance(payload.get("metric_scale_sources"), dict)
        else {}
    )
    markdown_by_metric = {}
    for extraction in pass3a_results:
        markdown = str(extraction.get("_markdown") or "")
        source = extraction.get("_source")
        for metric in METRIC_FIELDS:
            if metric not in extraction or extraction.get(metric) is None:
                continue
            row_ref = extraction.get("row_refs", {}).get(metric)
            selected_rows = _markdown_rows_for_ref(markdown, row_ref)
            markdown_by_metric[metric] = {
                "source_table": source,
                "page_number": extraction.get("_page_number"),
                "row_ref": row_ref or "DATA_MISSING",
                "selected_markdown_rows": selected_rows or ["DATA_MISSING"],
                "selected_value_cells": _value_cells_from_rows(selected_rows)
                if selected_rows
                else ["DATA_MISSING"],
            }

    trace = {}
    for metric in METRIC_FIELDS:
        trace[metric] = {
            "final_value": metrics.get(metric),
            "runtime_row_ref": row_refs.get(metric, "DATA_MISSING"),
            "runtime_source_scale": metric_source_scales.get(metric, "DATA_MISSING"),
            "runtime_scale_source": metric_scale_sources.get(metric, "DATA_MISSING"),
            "selected_row": markdown_by_metric.get(metric, {}).get(
                "selected_markdown_rows", ["DATA_MISSING"]
            ),
            "selected_value_cells": markdown_by_metric.get(metric, {}).get(
                "selected_value_cells", ["DATA_MISSING"]
            ),
            "source_table": markdown_by_metric.get(metric, {}).get(
                "source_table", "DATA_MISSING"
            ),
            "page_number": markdown_by_metric.get(metric, {}).get(
                "page_number", "DATA_MISSING"
            ),
        }
    return trace


def _common_scale_trace(mx: Any, payload: dict[str, Any]) -> dict[str, Any]:
    fallback = payload.get("scale", "unknown")
    before = {
        "metrics": payload.get("metrics"),
        "metric_source_scales": payload.get("metric_source_scales"),
        "fallback_scale": fallback,
    }
    return {
        "input": before,
        "output": mx._common_metric_source_scale(payload, fallback),
    }


def _run_doc(doc_id: str, records: list[dict[str, dict[str, Any]]], llm_client: Any) -> dict[str, Any]:
    import app.services.docling_extract as docling_extract
    import app.services.multipass_extraction as mx
    from app.services.multipass_extraction import run_multipass_extraction

    diagnostics = _diagnostic_by_doc()
    diagnostic_row = diagnostics[doc_id]
    ticker = TARGETS[doc_id]
    title = str(diagnostic_row.get("title") or records[0].get(doc_id, {}).get("title") or "")
    source_path = _source_path_from_records(doc_id, records)
    cache_path = _cache_path_for_doc(doc_id, title, diagnostic_row)

    base: dict[str, Any] = {
        "document_id": doc_id,
        "ticker": ticker,
        "title": title,
        "source_path": source_path,
        "source_path_exists": Path(source_path).exists() if source_path != "DATA_MISSING" else False,
        "cache_path": str(cache_path) if cache_path else "DATA_MISSING",
        "cache_path_exists": bool(cache_path and cache_path.exists()),
        "count24_summary": records[0].get(doc_id, {}),
        "count24_manifest": records[1].get(doc_id, {}),
        "prior_scale_evidence": records[2].get(doc_id, {}),
        "prior_selected_table_diagnostic": {
            "selected_tables": diagnostic_row.get("selected_tables", {}),
            "data_missing": diagnostic_row.get("data_missing", []),
            "final_payload_scale_decision": diagnostic_row.get("final_payload_scale_decision"),
        },
    }

    if not cache_path or not cache_path.exists():
        base["status"] = "blocked"
        base["error"] = "DATA_MISSING: parser cache JSON unavailable"
        return base
    if source_path == "DATA_MISSING" or not Path(source_path).exists():
        base["status"] = "blocked"
        base["error"] = "DATA_MISSING: source PDF unavailable"
        return base

    structured_doc = docling_extract._load_cache(cache_path)
    selected_tables = _selected_table_report(mx, structured_doc)
    metadata = {"document_id": doc_id, "ticker": ticker, "title": title}
    debug_capture: dict[str, Any] = {}
    started = time.monotonic()

    with _patched_cached_parser(docling_extract, structured_doc):
        with _captured_llm_calls(mx) as llm_calls:
            result = run_multipass_extraction(
                source_path,
                metadata,
                llm_client,
                skip_narrative=True,
                parser_backend="pymupdf",
                strict_parser=False,
                debug_capture=debug_capture,
            )

    payload = result.payload or {}
    pass3a_results = debug_capture.get("pass3a_results") or []
    pass3a_raw = [call for call in llm_calls if call.get("phase") == "pass3a"]
    base.update(
        {
            "status": result.status,
            "error": result.error,
            "elapsed_s": round(time.monotonic() - started, 3),
            "parser_source": "cached_structured_document_from_count24_worktree",
            "parser_cache": {
                "extraction_method": structured_doc.extraction_method,
                "page_count": structured_doc.page_count,
                "source_pdf_page_count": structured_doc.source_pdf_page_count,
                "table_count": len(structured_doc.tables),
                "section_count": len(structured_doc.sections),
            },
            "selected_tables": selected_tables,
            "document_level_scale_markers": {
                "table_header_scale": mx._detect_scale_from_tables(structured_doc.tables),
                "early_source_text_scale": _detect_scale_from_text(
                    mx,
                    mx._early_period_source_text(structured_doc.sections)
                    or " ".join(
                        str(section.get("text") or "")
                        for section in structured_doc.sections[:3]
                        if isinstance(section, dict)
                    ),
                ),
            },
            "pass3a_results": pass3a_results,
            "pass3a_raw_llm_outputs": pass3a_raw or "DATA_MISSING",
            "pass3a_llm_call_summary": [
                {
                    "phase": call.get("phase"),
                    "table_type": call.get("table_type"),
                    "status": call.get("status"),
                    "elapsed_s": call.get("elapsed_s"),
                    "prompt_chars": call.get("prompt_chars"),
                    "error": call.get("error"),
                }
                for call in llm_calls
            ],
            "metric_trace": _metric_source_trace(payload, pass3a_results),
            "common_metric_source_scale_trace": _common_scale_trace(mx, payload),
            "final_gate": {
                "status": result.status,
                "error": result.error,
                "payload_scale": payload.get("scale"),
                "scale_validation": payload.get("scale_validation"),
                "confidence_metrics": payload.get("confidence_metrics"),
                "non_null_metrics": len(
                    [
                        value
                        for value in (payload.get("metrics") or {}).values()
                        if value is not None
                    ]
                )
                if isinstance(payload.get("metrics"), dict)
                else 0,
            },
        }
    )
    return base


def _assess_repeated_path(documents: list[dict[str, Any]]) -> dict[str, Any]:
    azj = next((doc for doc in documents if doc.get("ticker") == "AZJ"), {})
    edu = next((doc for doc in documents if doc.get("ticker") == "EDU"), {})

    azj_scales = set()
    edu_scales = set()
    for doc, sink in ((azj, azj_scales), (edu, edu_scales)):
        for table in (doc.get("selected_tables") or {}).values():
            scale = table.get("same_page_scale")
            if scale and scale != "unknown":
                sink.add(scale)
    azj_runtime_scales = {
        str(v)
        for v in (
            azj.get("common_metric_source_scale_trace", {})
            .get("input", {})
            .get("metric_source_scales")
            or {}
        ).values()
        if str(v) != "unknown"
    }
    edu_runtime_scales = {
        str(v)
        for v in (
            edu.get("common_metric_source_scale_trace", {})
            .get("input", {})
            .get("metric_source_scales")
            or {}
        ).values()
        if str(v) != "unknown"
    }

    same_runtime_source_scale = (
        len(azj_runtime_scales) == 1
        and azj_runtime_scales == edu_runtime_scales
        and bool(azj_runtime_scales)
    )
    same_same_page_scale = len(azj_scales) == 1 and azj_scales == edu_scales and bool(azj_scales)

    if same_runtime_source_scale or same_same_page_scale:
        decision = "NEEDS_ONE_TARGETED_REPAIR"
    elif any(doc.get("status") in {None, "blocked"} for doc in documents):
        decision = "BLOCKED_BY_PROVENANCE_DATA_MISSING"
    else:
        decision = "NEEDS_SCALE_TABLE_HARNESS"

    return {
        "same_root_cause_proven": bool(same_runtime_source_scale or same_same_page_scale),
        "azj_same_page_scales": sorted(azj_scales),
        "edu_same_page_scales": sorted(edu_scales),
        "azj_runtime_metric_source_scales": sorted(azj_runtime_scales),
        "edu_runtime_metric_source_scales": sorted(edu_runtime_scales),
        "same_runtime_source_scale": same_runtime_source_scale,
        "same_same_page_scale": same_same_page_scale,
        "decision": decision,
        "reason": (
            "AZJ and EDU share a source-scale propagation path."
            if same_runtime_source_scale or same_same_page_scale
            else "AZJ and EDU did not prove the same source-scale propagation path."
        ),
    }


def main() -> int:
    for key, value in SAFE_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)
    sys.path.insert(0, str(BACKEND_ROOT))

    import httpx

    count24_records = _records_by_doc(COUNT24_RESULTS)
    manifest_records = _records_by_doc(COUNT24_MANIFEST)
    scale_records = _records_by_doc(SCALE_EVIDENCE)
    records = [count24_records, manifest_records, scale_records]

    output: dict[str, Any] = {
        "job_id": JOB_ID,
        "generated_at": _now(),
        "no_write_statement": {
            "count24_rerun": False,
            "count32_run": False,
            "random_sample_run": False,
            "broad_extraction_or_backfill_run": False,
            "db_qdrant_redis_news_memory_mutation": False,
            "source_pdf_edit": False,
            "parser_cache_write": False,
            "prompt_gold_schema_runtime_model_gpu_config_change": False,
        },
        "artifact_inputs": {
            "count24_results": str(COUNT24_RESULTS),
            "count24_manifest": str(COUNT24_MANIFEST),
            "scale_evidence": str(SCALE_EVIDENCE),
            "diagnostic_results": str(DIAGNOSTIC_RESULTS),
            "count24_cache_root": str(COUNT24_CACHE_ROOT),
        },
        "safe_env_defaults": SAFE_ENV_DEFAULTS,
        "documents": [],
    }

    with httpx.Client(timeout=300.0) as llm_client:
        for doc_id in TARGETS:
            output["documents"].append(_run_doc(doc_id, records, llm_client))

    output["repeated_path_assessment"] = _assess_repeated_path(output["documents"])
    _write_json(OUTPUT_DIR / "provenance_capture.json", output)

    status = {
        "job_id": JOB_ID,
        "state": "DONE_WITH_RISK"
        if output["repeated_path_assessment"]["decision"] != "NEEDS_ONE_TARGETED_REPAIR"
        else "DONE",
        "final_decision": output["repeated_path_assessment"]["decision"],
        "same_root_cause_proven": output["repeated_path_assessment"][
            "same_root_cause_proven"
        ],
        "no_count24_count32_backfill_random_sample_run": True,
        "documents": {
            doc["ticker"]: {
                "status": doc.get("status"),
                "error": doc.get("error"),
                "payload_scale": doc.get("final_gate", {}).get("payload_scale"),
                "scale_validation": doc.get("final_gate", {}).get("scale_validation"),
            }
            for doc in output["documents"]
        },
        "generated_at": output["generated_at"],
    }
    _write_json(OUTPUT_DIR / "status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
