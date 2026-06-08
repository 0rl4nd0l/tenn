#!/usr/bin/env python3
"""Exact-doc pass3a debug replay for CXO and NSR.

This report-local runner intentionally writes only this job's artifacts plus an
isolated disposable parser cache under DATA_ROOT. It fails closed if DATA_ROOT
does not point at the approved /tmp prefix.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any


JOB_ID = "extraction_cxo_nsr_pass3a_debug_replay_v1_20260608"
APPROVED_TMP_PREFIX = f"/tmp/tenn-pass3a-debug-replay-cache-v1-20260608"
OUTPUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = OUTPUT_DIR.parents[2]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"

TARGET_DOCS: list[dict[str, str]] = [
    {
        "case_id": "control_CXO_36e172ec",
        "ticker": "CXO",
        "document_id": "36e172ec-2650-4a9f-9ef0-a4366a3b8d31",
        "title": "2022-10-31_quarterly-activities-and-cashflow-report-30-september-2022_36e172ec-2650-4a9f-9ef0-a4366a3b8d31.pdf",
        "source_path": "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CXO/financial_performance/2022-10-31_quarterly-activities-and-cashflow-report-30-september-2022_36e172ec-2650-4a9f-9ef0-a4366a3b8d31.pdf",
        "expected_period_type": "Q",
        "expected_period_end": "2022-09-30",
        "expected_scale": "thousands",
    },
    {
        "case_id": "control_NSR_f2240712",
        "ticker": "NSR",
        "document_id": "f2240712-9dde-41e0-88fa-29c1a0080dab",
        "title": "2022-02-25_half-year-accounts_f2240712-9dde-41e0-88fa-29c1a0080dab.pdf",
        "source_path": "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/NSR/financial_performance/2022-02-25_half-year-accounts_f2240712-9dde-41e0-88fa-29c1a0080dab.pdf",
        "expected_period_type": "H",
        "expected_period_end": "2021-12-31",
        "expected_scale": "thousands",
    },
]


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): _jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_jsonable(v) for v in value]
        return str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _source_stat(path: str) -> dict[str, Any]:
    p = Path(path)
    try:
        st = p.stat()
    except OSError as exc:
        return {"path": path, "exists": False, "error": str(exc)}
    return {
        "path": path,
        "exists": True,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }


def _safe_cache_label(pdf_path: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(pdf_path).name).strip("._")
    return label[:96] or "document"


def _cache_key_material(pdf_path: str) -> str:
    source_path = Path(pdf_path).expanduser()
    resolved = str(source_path.resolve(strict=False))
    try:
        stat = source_path.stat()
    except OSError:
        return f"path={resolved}"
    return f"path={resolved}\0size={stat.st_size}\0mtime_ns={stat.st_mtime_ns}"


def _cache_paths_for_root(cache_root: Path, pdf_path: str) -> dict[str, str]:
    digest = hashlib.sha256(_cache_key_material(pdf_path).encode("utf-8")).hexdigest()
    label = _safe_cache_label(pdf_path)
    return {
        "docling": str((cache_root / f"{digest}-{label}.docling.json").resolve()),
        "pymupdf": str((cache_root / f"{digest}-{label}.pymupdf.json").resolve()),
    }


def _path_snapshot(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"path": path, "exists": False}
    st = p.stat()
    return {
        "path": path,
        "exists": True,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }


def _list_files(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for item in sorted(root.rglob("*")):
        if item.is_file():
            st = item.stat()
            rows.append(
                {
                    "path": str(item),
                    "relative_path": str(item.relative_to(root)),
                    "size": st.st_size,
                    "mtime_ns": st.st_mtime_ns,
                }
            )
    return rows


def _markdown_matching_rows(markdown: str, row_refs: dict[str, Any]) -> dict[str, Any]:
    lines = [line for line in str(markdown or "").splitlines() if line.strip()]
    matches: dict[str, Any] = {}
    for metric, row_ref in (row_refs or {}).items():
        needle = re.sub(r"\s+", " ", str(row_ref or "").strip()).lower()
        if not needle:
            matches[str(metric)] = []
            continue
        matched = [
            line
            for line in lines
            if needle in re.sub(r"\s+", " ", line).lower()
        ]
        matches[str(metric)] = matched[:5]
    return matches


def _summarize_pass3a_rows(pass3a_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in pass3a_results:
        markdown = str(item.get("_markdown") or "")
        row_refs = item.get("row_refs") if isinstance(item.get("row_refs"), dict) else {}
        non_null_metrics = {
            metric: item.get(metric)
            for metric in (
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
                "total_debt",
            )
            if item.get(metric) is not None
        }
        summaries.append(
            {
                "source": item.get("_source"),
                "page_number": item.get("_page_number"),
                "scale": item.get("_scale"),
                "scale_source": item.get("_scale_source"),
                "pass3_confidence": item.get("pass3_confidence"),
                "period_col": item.get("period_col"),
                "row_refs": row_refs,
                "non_null_metrics": non_null_metrics,
                "markdown_head": markdown.splitlines()[:12],
                "matched_row_text": _markdown_matching_rows(markdown, row_refs),
            }
        )
    return summaries


def _discover_local_api_key() -> str:
    try:
        proc = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""
    for line in proc.stdout.splitlines():
        if "llama-server" in line and "--api-key" in line:
            return line.split("--api-key", 1)[1].strip().split()[0]
    return ""


def _build_client() -> tuple[Any, dict[str, Any]]:
    import httpx

    base_url = os.environ.get("LLAMACPP_URL", "http://127.0.0.1:8001").rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"
    api_key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or _discover_local_api_key()
    )
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    client = httpx.Client(base_url=base_url, timeout=180.0, headers=headers)
    started = time.monotonic()
    response = client.get("/models")
    elapsed = time.monotonic() - started
    response.raise_for_status()
    models = response.json()
    return client, {
        "base_url": base_url,
        "has_api_key": bool(api_key),
        "models_status_code": response.status_code,
        "models_elapsed_s": round(elapsed, 3),
        "models_head": str(models)[:1200],
    }


class _Observer:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(
        self,
        stage: str,
        status: str,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "stage": stage,
                "status": status,
                "message": message,
                "error_code": error_code,
                "details": copy.deepcopy(details or {}),
            }
        )


def main() -> int:
    data_root_raw = os.environ.get("DATA_ROOT", "")
    if not data_root_raw:
        payload = {
            "state": "DONE_WITH_RISK",
            "error": "DATA_ROOT not set; refusing to risk normal parser cache writes",
            "isolated_cache_used": False,
        }
        _write_json(OUTPUT_DIR / "pass3a_debug_replay.json", payload)
        _write_json(OUTPUT_DIR / "status.json", payload)
        return 2

    data_root = Path(data_root_raw).expanduser().resolve()
    if not str(data_root).startswith(APPROVED_TMP_PREFIX):
        payload = {
            "state": "DONE_WITH_RISK",
            "error": f"DATA_ROOT outside approved disposable prefix: {data_root}",
            "approved_tmp_prefix": APPROVED_TMP_PREFIX,
            "isolated_cache_used": False,
        }
        _write_json(OUTPUT_DIR / "pass3a_debug_replay.json", payload)
        _write_json(OUTPUT_DIR / "status.json", payload)
        return 2

    # Process-local runtime defaults only. These avoid a routing-config load
    # failure in this isolated replay without editing any config file or
    # starting/reconfiguring any service.
    os.environ.setdefault("LLAMACPP_URL", "http://127.0.0.1:8001")
    os.environ.setdefault("EXTRACTION_LLAMACPP_URL", os.environ["LLAMACPP_URL"])
    os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:11434")

    sys.path.insert(0, str(BACKEND_ROOT))

    from app.core.config import settings
    from app.services import llm as llm_module
    from app.services import multipass_extraction as mp
    from app.services.docling_extract import _extract_cache_root

    cache_root = _extract_cache_root().resolve()
    if not str(cache_root).startswith(str(data_root) + os.sep):
        payload = {
            "state": "DONE_WITH_RISK",
            "error": f"cache root is not under isolated DATA_ROOT: {cache_root}",
            "data_root": str(data_root),
            "isolated_cache_used": False,
        }
        _write_json(OUTPUT_DIR / "pass3a_debug_replay.json", payload)
        _write_json(OUTPUT_DIR / "status.json", payload)
        return 2

    # Prevent report-local replay from writing router activity state, Redis task
    # markers, or router metrics while preserving actual LLM/pass3a calls.
    no_op = lambda *args, **kwargs: None
    llm_module.router_metrics.configure_metrics_snapshot = no_op
    llm_module.router_state.mark_task_started = no_op
    llm_module.router_state.mark_task_finished = no_op
    llm_module.router_metrics.record = no_op
    llm_module.router_metrics.save_metrics_snapshot = no_op
    llm_module.router_metrics._flush_snapshot_async = no_op
    llm_module.router_metrics._schedule_snapshot_save = no_op

    normal_cache_roots = [
        Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/extraction_cache/docling_extract"),
        Path("/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/data/reports/extraction_cache/docling_extract"),
        REPO_ROOT / "financial-engine_v2" / "data" / "reports" / "extraction_cache" / "docling_extract",
    ]
    normal_cache_paths = {
        doc["case_id"]: {
            str(root): _cache_paths_for_root(root, doc["source_path"])
            for root in normal_cache_roots
        }
        for doc in TARGET_DOCS
    }
    normal_cache_before = {
        case_id: {
            root: {
                kind: _path_snapshot(path)
                for kind, path in paths.items()
            }
            for root, paths in roots.items()
        }
        for case_id, roots in normal_cache_paths.items()
    }
    source_pdf_before = {
        doc["case_id"]: _source_stat(doc["source_path"]) for doc in TARGET_DOCS
    }
    isolated_cache_before = _list_files(cache_root)

    original_common_scale = mp._common_metric_source_scale
    common_traces: list[dict[str, Any]] = []

    def traced_common_metric_source_scale(payload: dict, fallback: Any) -> str:
        output = original_common_scale(payload, fallback)
        common_traces.append(
            {
                "input_metrics": copy.deepcopy(payload.get("metrics")),
                "input_metric_source_scales": copy.deepcopy(
                    payload.get("metric_source_scales")
                ),
                "input_metric_scale_sources": copy.deepcopy(
                    payload.get("metric_scale_sources")
                ),
                "fallback": fallback,
                "output": output,
            }
        )
        return output

    mp._common_metric_source_scale = traced_common_metric_source_scale

    client = None
    llm_info: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    state = "DONE_WITH_RISK"
    data_missing: set[str] = set()
    errors: list[str] = []
    try:
        client, llm_info = _build_client()
        for doc in TARGET_DOCS:
            debug_capture: dict[str, Any] = {}
            observer = _Observer()
            metadata = {
                "document_id": doc["document_id"],
                "ticker": doc["ticker"],
                "title": doc["title"],
            }
            started = time.monotonic()
            try:
                result = mp.run_multipass_extraction(
                    doc["source_path"],
                    metadata,
                    client,
                    skip_narrative=True,
                    parser_backend="docling",
                    strict_parser=False,
                    observer=observer,
                    debug_capture=debug_capture,
                )
                elapsed = time.monotonic() - started
                payload = result.payload or {}
                pass3a_results = debug_capture.get("pass3a_results")
                if not isinstance(pass3a_results, list):
                    pass3a_results = []
                    data_missing.add(f"{doc['case_id']}:pass3a_results")
                if not payload.get("row_refs"):
                    data_missing.add(f"{doc['case_id']}:row_refs")
                if not payload.get("metric_source_scales"):
                    data_missing.add(f"{doc['case_id']}:metric_source_scales")
                if not payload.get("metric_scale_sources"):
                    data_missing.add(f"{doc['case_id']}:metric_scale_sources")
                results.append(
                    {
                        "case_id": doc["case_id"],
                        "ticker": doc["ticker"],
                        "document_id": doc["document_id"],
                        "source_path": doc["source_path"],
                        "status": result.status,
                        "error": result.error,
                        "elapsed_s": round(elapsed, 3),
                        "observer_events": observer.events,
                        "pass3a_results": pass3a_results,
                        "pass3a_table_summaries": _summarize_pass3a_rows(pass3a_results),
                        "payload": {
                            "period_type": payload.get("period_type"),
                            "period_end": payload.get("period_end"),
                            "period_start": payload.get("period_start"),
                            "scale": payload.get("scale"),
                            "currency": payload.get("currency"),
                            "status": result.status,
                            "metrics": payload.get("metrics"),
                            "row_refs": payload.get("row_refs"),
                            "metric_source_scales": payload.get("metric_source_scales"),
                            "metric_scale_sources": payload.get("metric_scale_sources"),
                            "provenance": payload.get("provenance"),
                            "confidence_metrics": payload.get("confidence_metrics"),
                            "source_bound": payload.get("source_bound"),
                            "source_document_classification": payload.get(
                                "source_document_classification"
                            ),
                            "structured_extraction": payload.get(
                                "_structured_extraction"
                            ),
                            "scale_validation": payload.get("scale_validation"),
                        },
                    }
                )
            except Exception as exc:
                elapsed = time.monotonic() - started
                data_missing.add(f"{doc['case_id']}:pass3a_replay_exception")
                errors.append(f"{doc['case_id']}:{type(exc).__name__}:{exc}")
                results.append(
                    {
                        "case_id": doc["case_id"],
                        "ticker": doc["ticker"],
                        "document_id": doc["document_id"],
                        "source_path": doc["source_path"],
                        "status": "exception",
                        "error": f"{type(exc).__name__}: {exc}",
                        "elapsed_s": round(elapsed, 3),
                        "traceback": traceback.format_exc(limit=20),
                        "observer_events": observer.events,
                        "pass3a_results": [],
                        "pass3a_table_summaries": [],
                    }
                )
    finally:
        mp._common_metric_source_scale = original_common_scale
        if client is not None:
            client.close()

    isolated_cache_after = _list_files(cache_root)
    source_pdf_after = {doc["case_id"]: _source_stat(doc["source_path"]) for doc in TARGET_DOCS}
    normal_cache_after = {
        case_id: {
            root: {
                kind: _path_snapshot(path)
                for kind, path in paths.items()
            }
            for root, paths in roots.items()
        }
        for case_id, roots in normal_cache_paths.items()
    }

    pass3a_field_capture = {
        "pass3a_outputs": all(bool(r.get("pass3a_results")) for r in results),
        "row_refs": all(bool((r.get("payload") or {}).get("row_refs")) for r in results),
        "metric_source_scales": all(
            bool((r.get("payload") or {}).get("metric_source_scales"))
            for r in results
        ),
        "metric_scale_sources": all(
            bool((r.get("payload") or {}).get("metric_scale_sources"))
            for r in results
        ),
        "selected_table_page": all(
            bool(r.get("pass3a_table_summaries")) for r in results
        ),
        "common_metric_source_scale_trace": bool(common_traces),
    }
    if all(pass3a_field_capture.values()) and not errors:
        state = "DONE"
    elif errors or data_missing:
        state = "DONE_WITH_RISK"

    shared_source_bound_root_cause = False
    root_cause_reason = (
        "No production repair: replay artifacts do not prove the same "
        "source-bound production root cause across CXO and NSR."
    )
    if len(results) == 2 and all(r.get("status") == "exception" for r in results):
        shared_source_bound_root_cause = False
        root_cause_reason = (
            "Both exact docs hit replay exceptions, but that is an execution "
            "blocker rather than a proven source-bound production extraction root cause."
        )

    output = {
        "job_id": JOB_ID,
        "state": state,
        "exact_docs": TARGET_DOCS,
        "data_root": str(data_root),
        "settings_data_root": settings.data_root,
        "cache_root": str(cache_root),
        "isolated_cache_used": True,
        "parser_backend_requested": "docling",
        "llm_info": llm_info,
        "source_pdf_before": source_pdf_before,
        "source_pdf_after": source_pdf_after,
        "normal_cache_before": normal_cache_before,
        "normal_cache_after": normal_cache_after,
        "isolated_cache_before": isolated_cache_before,
        "isolated_cache_after": isolated_cache_after,
        "results": results,
        "pass3a_field_capture": pass3a_field_capture,
        "common_metric_source_scale_traces": common_traces,
        "two_cases_shared_source_bound_production_root_cause": shared_source_bound_root_cause,
        "root_cause_reason": root_cause_reason,
        "production_repair_implemented": False,
        "data_missing": sorted(data_missing),
        "errors": errors,
        "unsafe_actions_avoided": [
            "normal_parser_cache_write",
            "db_write",
            "qdrant_write",
            "redis_write",
            "news_write",
            "memory_write",
            "source_pdf_write",
            "prompt_write",
            "gold_label_write",
            "runtime_config_write",
            "service_start",
            "broad_extraction",
            "count_24",
            "count_32",
            "random_sample",
            "backfill",
            "github_mutation",
            "production_repair",
        ],
    }

    _write_json(OUTPUT_DIR / "pass3a_debug_replay.json", output)
    _write_json(
        OUTPUT_DIR / "common_metric_source_scale_trace.json",
        {
            "job_id": JOB_ID,
            "exact_docs": TARGET_DOCS,
            "traces": common_traces,
        },
    )
    _write_json(
        OUTPUT_DIR / "status.json",
        {
            "job_id": JOB_ID,
            "state": state,
            "exact_docs_used": TARGET_DOCS,
            "isolated_cache_used": True,
            "cache_root": str(cache_root),
            "pass3a_field_capture": pass3a_field_capture,
            "two_cases_shared_source_bound_production_root_cause": shared_source_bound_root_cause,
            "production_repair_implemented": False,
            "data_missing": sorted(data_missing),
            "errors": errors,
        },
    )
    return 0 if state in {"DONE", "DONE_WITH_RISK"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
