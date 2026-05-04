#!/usr/bin/env python3
"""Run the guarded Docling runtime --parallel 2 experiment.

This operations driver keeps extraction semantics unchanged. It only controls
the dedicated :8002 llama.cpp runtime and the document-level eval harness.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urlrequest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_SCRIPT = REPO_ROOT / "scripts" / "run_isolated_docling_control.py"
BASELINE_DIR = (
    REPO_ROOT / "reports" / "docling_runtime_stage_attribution_20260504T021346Z"
)
DOC_IDS = (
    "bhp_a_2021-06-30_difficult",
    "bhp_a_2025-06-30",
    "eqr_q_2025-12-31",
    "gre_q_2024-12-31",
    "gre_q_2025-09-30",
    "min_h_2025-12-31",
    "qbe_h_2025-06-30",
    "rio_a_2023-12-31",
    "rio_a_2024-12-31",
    "tls_h_2025-12-31",
)

spec = importlib.util.spec_from_file_location("run_isolated_docling_control", CONTROL_SCRIPT)
assert spec is not None and spec.loader is not None
control = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = control
spec.loader.exec_module(control)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Docling parallel-2 runtime knob cells and assemble report artifacts."
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR)
    parser.add_argument("--extraction-url", default="http://127.0.0.1:8002")
    parser.add_argument("--shared-url", default="http://127.0.0.1:8001")
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", "local-openai-key"))
    parser.add_argument("--server-parallel", type=int, default=2)
    parser.add_argument("--max-client-concurrency", type=int, default=2)
    parser.add_argument("--cell-timeout-seconds", type=float, default=7200.0)
    parser.add_argument("--child-timeout-seconds", type=float, default=1800.0)
    parser.add_argument("--skip-cell-b", action="store_true")
    parser.add_argument("--skip-cell-c", action="store_true")
    parser.add_argument("--keep-runtime", action="store_true")
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _run_capture(cmd: list[str], *, timeout: float = 30.0) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": _redact_command(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "started_epoch": round(started, 6),
        "ended_epoch": round(time.time(), 6),
    }


def _redact_command(cmd: list[str]) -> str:
    redacted: list[str] = []
    skip = False
    for part in cmd:
        if skip:
            redacted.append("<redacted>")
            skip = False
            continue
        if part in {"--api-key", "--api-key-file"}:
            redacted.append(part)
            skip = True
            continue
        if part.startswith("--api-key="):
            redacted.append("--api-key=<redacted>")
            continue
        redacted.append(part)
    return shlex.join(redacted)


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    env["EXTRACTION_LLAMACPP_URL"] = "http://127.0.0.1:8002"
    env["EXTRACTION_SERVER_PARALLEL"] = "2"
    env["LLAMA_SERVER_MMAP"] = "0"
    env["LLAMA_ARG_CACHE_RAM"] = "0"
    env["LLAMA_ARG_CACHE_PROMPT"] = "false"
    env["LLM_API_KEY"] = env.get("LLM_API_KEY", "local-openai-key")
    return env


def _stop_runtime_pids(endpoint: str, *, api_key: str) -> list[dict[str, Any]]:
    status = control._runtime_status(endpoint, api_key=api_key)
    records: list[dict[str, Any]] = []
    for pid in status.get("pids") or []:
        records.append(control._terminate_started_runtime(int(pid)))
    return records


def _ensure_runtime_ready_for_parallel2(args: argparse.Namespace) -> dict[str, Any]:
    endpoint = control._normalize_url(args.extraction_url)
    status = control._runtime_status(endpoint, api_key=args.api_key)
    prompt_disabled = control._runtime_has_disabled_prompt_cache(status)
    parallel_ok = control._runtime_has_server_parallel(status, int(args.server_parallel))
    restart: dict[str, Any] = {
        "initial_status": status,
        "stopped_existing_runtime": False,
        "stop_records": [],
        "reason": None,
    }
    if status.get("healthy") and parallel_ok and prompt_disabled:
        restart["reason"] = "existing_runtime_already_parallel2_prompt_cache_disabled"
        return restart
    if status.get("healthy") or status.get("pids"):
        restart["stopped_existing_runtime"] = True
        restart["reason"] = "runtime_config_mismatch_or_prompt_cache_not_disabled"
        restart["stop_records"] = _stop_runtime_pids(endpoint, api_key=args.api_key)
        time.sleep(2)
    return restart


def _control_cmd(
    *,
    args: argparse.Namespace,
    results_json: Path,
    report_path: Path,
    runtime_log: Path,
    doc_ids: tuple[str, ...] = DOC_IDS,
    start_runtime: bool = False,
) -> list[str]:
    cmd = [
        sys.executable,
        str(CONTROL_SCRIPT),
        "--extraction-url",
        args.extraction_url,
        "--shared-url",
        args.shared_url,
        "--server-parallel",
        str(args.server_parallel),
        "--disable-prompt-cache",
        "--capture-payload",
        "--results-json",
        str(results_json),
        "--report-path",
        str(report_path),
        "--runtime-log",
        str(runtime_log),
    ]
    if start_runtime:
        cmd.append("--start-runtime")
    for doc_id in doc_ids:
        cmd.extend(["--doc-id", doc_id])
    return cmd


def _run_cell_b(args: argparse.Namespace, report_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any] | None:
    results_json = report_dir / "cell_b_server_parallel2_serial_client.json"
    if args.skip_cell_b:
        if results_json.exists():
            payload = _read_json(results_json)
            payload["experiment_cell"] = "server_parallel_2_serial_client"
            return payload
        return None
    report_path = report_dir / "cell_b_server_parallel2_serial_client.md"
    runtime_log = report_dir / "llama_extraction_8002_parallel2.log"
    cmd = _control_cmd(
        args=args,
        results_json=results_json,
        report_path=report_path,
        runtime_log=runtime_log,
        start_runtime=True,
    )
    record = _run_capture(cmd, timeout=float(args.cell_timeout_seconds))
    commands.append(record)
    payload = _read_json(results_json) if results_json.exists() else {"error": "missing cell B JSON"}
    payload["experiment_cell"] = "server_parallel_2_serial_client"
    return payload


def _run_cell_c(args: argparse.Namespace, report_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any] | None:
    if args.skip_cell_c:
        return None
    endpoint = control._normalize_url(args.extraction_url)
    before = control._runtime_status(endpoint, api_key=args.api_key)
    if not before.get("healthy"):
        runtime_args = argparse.Namespace(
            api_key=args.api_key,
            start_runtime=True,
            disable_prompt_cache=True,
            model_path=control.DEFAULT_MODEL_PATH,
            model_alias=control.DEFAULT_MODEL_ALIAS,
            ctx_size=16384,
            server_parallel=args.server_parallel,
            min_vram_free_mb=9000,
            runtime_log=report_dir / "llama_extraction_8002_parallel2.log",
            startup_timeout_seconds=240.0,
        )
        control._ensure_runtime(runtime_args, endpoint)
        before = control._runtime_status(endpoint, api_key=args.api_key)
    if not control._runtime_has_server_parallel(before, int(args.server_parallel)):
        raise RuntimeError("Cell C runtime is not using requested --parallel 2")

    child_dir = report_dir / "cell_c_docs"
    child_dir.mkdir(parents=True, exist_ok=True)
    runtime_log = report_dir / "llama_extraction_8002_parallel2.log"
    env = _base_env()
    max_workers = min(max(int(args.max_client_concurrency), 1), 2)
    pending = list(DOC_IDS)
    active: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []
    fail_fast: dict[str, Any] = {"triggered": False}
    cell_started = time.time()
    cell_deadline = time.monotonic() + float(args.cell_timeout_seconds)

    def active_doc_ids() -> list[str]:
        return [str(item["doc_id"]) for item in active]

    def sample_health(event: str, doc_id: str | None = None) -> dict[str, Any]:
        row = _sample_request_health(
            endpoint=endpoint,
            api_key=args.api_key,
            cell="server_parallel_2_two_doc_concurrent_client",
            event=event,
            doc_id=doc_id,
            active_doc_ids=active_doc_ids(),
        )
        health_rows.append(row)
        return row

    def fail_fast_if_runtime_unhealthy() -> bool:
        nonlocal fail_fast
        if fail_fast.get("triggered"):
            return True
        gate = _runtime_health_gate({"request_health_timeline": health_rows})
        if gate.get("passed"):
            return False
        fail_fast = {
            "triggered": True,
            "triggered_at_epoch": round(time.time(), 6),
            "triggered_at_utc": _iso_utc(),
            "reason": "active_runtime_health_gate_failed",
            "gate": gate,
        }
        pending.clear()
        for item in active:
            proc = item["proc"]
            if proc.poll() is None:
                proc.kill()
        return True

    def start_child(doc_id: str, index: int) -> bool:
        safe_doc = doc_id.replace("/", "_")
        result_path = child_dir / f"{index:02d}_{safe_doc}.json"
        report_path = child_dir / f"{index:02d}_{safe_doc}.md"
        stdout_path = child_dir / f"{index:02d}_{safe_doc}.stdout.log"
        stderr_path = child_dir / f"{index:02d}_{safe_doc}.stderr.log"
        cmd = _control_cmd(
            args=args,
            results_json=result_path,
            report_path=report_path,
            runtime_log=runtime_log,
            doc_ids=(doc_id,),
            start_runtime=False,
        )
        sample_health("before_child_start", doc_id)
        if fail_fast_if_runtime_unhealthy():
            return False
        stdout_handle = stdout_path.open("w", encoding="utf-8")
        stderr_handle = stderr_path.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        active.append(
            {
                "doc_id": doc_id,
                "cmd": cmd,
                "proc": proc,
                "stdout_handle": stdout_handle,
                "stderr_handle": stderr_handle,
                "stdout_path": stdout_path,
                "stderr_path": stderr_path,
                "result_path": result_path,
                "report_path": report_path,
                "started_epoch": time.time(),
            }
        )
        return True

    next_index = 1
    while pending or active:
        while pending and len(active) < max_workers and not fail_fast.get("triggered"):
            if not start_child(pending.pop(0), next_index):
                break
            next_index += 1
        if active:
            sample_health("poll")
            fail_fast_if_runtime_unhealthy()
        completed: list[dict[str, Any]] = []
        for item in active:
            proc = item["proc"]
            returncode = proc.poll()
            if returncode is None:
                if time.monotonic() > cell_deadline:
                    proc.kill()
                    returncode = proc.wait(timeout=10)
                else:
                    continue
            item["stdout_handle"].close()
            item["stderr_handle"].close()
            item["returncode"] = int(returncode)
            item["ended_epoch"] = time.time()
            item["cmd_redacted"] = _redact_command(item["cmd"])
            completed.append(item)
        if completed:
            for item in completed:
                active.remove(item)
                record = {
                    "doc_id": item["doc_id"],
                    "cmd": item["cmd_redacted"],
                    "returncode": item["returncode"],
                    "stdout_path": str(item["stdout_path"]),
                    "stderr_path": str(item["stderr_path"]),
                    "result_path": str(item["result_path"]),
                    "started_epoch": round(float(item["started_epoch"]), 6),
                    "ended_epoch": round(float(item["ended_epoch"]), 6),
                }
                records.append(record)
                commands.append(record)
                sample_health("after_child_end", str(item["doc_id"]))
        else:
            time.sleep(1)
        if time.monotonic() > cell_deadline and active:
            for item in active:
                item["proc"].kill()
            break

    cell_ended = time.time()
    documents: list[dict[str, Any]] = []
    missing: list[str] = []
    for doc_id in DOC_IDS:
        record = next((row for row in records if row["doc_id"] == doc_id), None)
        if not record:
            missing.append(doc_id)
            continue
        result_path = Path(record["result_path"])
        if not result_path.exists():
            missing.append(doc_id)
            continue
        child_payload = _read_json(result_path)
        child_docs = child_payload.get("control", {}).get("documents") or []
        if not child_docs:
            missing.append(doc_id)
            continue
        documents.append(child_docs[0])

    payload: dict[str, Any] = {
        "generated_at_epoch": time.time(),
        "execution_mode": "isolated_docling_control_two_doc_concurrent_client",
        "experiment_cell": "server_parallel_2_two_doc_concurrent_client",
        "runtime": before,
        "runtime_after": control._runtime_status(endpoint, api_key=args.api_key),
        "shared_runtime": control._runtime_status(args.shared_url, api_key=args.api_key),
        "isolation": {
            "shared_runtime_endpoint": args.shared_url,
            "extraction_runtime_endpoint": endpoint,
            "shared_runtime_avoided": not control._same_endpoint(endpoint, args.shared_url),
            "no_silent_fallback_to_shared": True,
            "control_plane_probe_during_extraction": False,
        },
        "gpu_before": control._gpu_guard_json(),
        "gpu_after": control._gpu_guard_json(),
        "fail_fast": fail_fast,
        "request_health_timeline": health_rows,
        "control": {
            "doc_ids": list(DOC_IDS),
            "used_temp_pdf_copies": True,
            "temp_pdf_root": None,
            "cache_hit": False,
            "wall_time_seconds": round(max(cell_ended - cell_started, 0.0), 3),
            "stage_timing_seconds": _aggregate_global_stage_timing(documents),
            "summary": _summarize_documents(documents),
            "documents": documents,
            "missing_documents": missing,
            "child_processes": records,
            "max_client_concurrency": max_workers,
        },
    }
    payload["prompt_cache"] = _prompt_cache_from_runtime_log(args, runtime_log, payload)
    payload["acceptance"] = control._derive_acceptance(payload)
    payload["runtime_health_gate"] = _runtime_health_gate(payload)
    payload["partial_payload_gate"] = {
        "passed": not bool(_partial_payload_after_timeout_rows(payload)),
        "rows": _partial_payload_after_timeout_rows(payload),
    }
    _write_json(report_dir / "cell_c_server_parallel2_two_doc_concurrent_client.json", payload)
    control._write_report(
        report_dir / "cell_c_server_parallel2_two_doc_concurrent_client.md",
        payload,
    )
    return payload


def _prompt_cache_from_runtime_log(
    args: argparse.Namespace, runtime_log: Path, payload: dict[str, Any]
) -> dict[str, Any]:
    namespace = argparse.Namespace(
        runtime_log=runtime_log,
        disable_prompt_cache=True,
    )
    return control._prompt_cache_provenance(namespace, payload)


def _summarize_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    metric_counts: Counter[str] = Counter()
    trust_counts: Counter[str] = Counter()
    total_metric_checks = 0
    for doc in documents:
        counts = doc.get("metric_status_counts")
        counts = counts if isinstance(counts, dict) else {}
        for key in ("correct", "wrong", "missing", "abstain"):
            value = int(counts.get(key) or 0)
            metric_counts[key] += value
            total_metric_checks += value
        trust_counts[str(doc.get("trust_outcome") or "")] += 1
    return {
        "total_documents": len(documents),
        "failed_documents": sum(1 for doc in documents if doc.get("extraction_status") == "failed"),
        "context_correct_documents": sum(1 for doc in documents if bool(doc.get("context_correct"))),
        "total_metric_checks": total_metric_checks,
        "metric_status_counts": dict(metric_counts),
        "trust_distribution": dict(trust_counts),
        "trust_matches_expected": sum(1 for doc in documents if bool(doc.get("trust_matches_expected"))),
    }


def _aggregate_global_stage_timing(documents: list[dict[str, Any]]) -> dict[str, float]:
    totals: Counter[str] = Counter()
    for doc in documents:
        timings = doc.get("stage_timing_seconds")
        timings = timings if isinstance(timings, dict) else {}
        totals["pdf_temp_staging"] += 0.0
        totals["cleanup"] += 0.0
        for key, value in timings.items():
            try:
                totals[str(key)] += float(value or 0.0)
            except (TypeError, ValueError):
                continue
    return {key: round(value, 6) for key, value in totals.items()}


REQUEST_TIMEOUT_MARKERS = ("timeout", "timed out", "deadline exceeded")
REQUEST_HEALTH_TIMELINE_FIELDS = [
    "cell",
    "epoch",
    "iso_utc",
    "event",
    "doc_id",
    "active",
    "active_doc_ids",
    "port_open",
    "health_ok",
    "health_http_status",
    "health_probe_state",
    "runtime_pids",
    "slots_http_status",
    "slots_probe_state",
    "slots_snapshot",
]


def _is_request_timeout_error(error: Any) -> bool:
    text = str(error or "").lower()
    return any(marker in text for marker in REQUEST_TIMEOUT_MARKERS)


def _iso_utc(epoch: float | None = None) -> str:
    return datetime.fromtimestamp(epoch or time.time(), timezone.utc).isoformat()


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _probe_http_text(
    url: str,
    *,
    api_key: str,
    timeout: float,
) -> tuple[int | None, str, str]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    request = urlrequest.Request(url, headers=headers)
    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            status = int(response.status)
            state = "ok" if 200 <= status < 300 else f"http_{status}"
            return status, body.replace("\n", " ")[:1000], state
    except Exception as exc:  # noqa: BLE001
        text = f"{type(exc).__name__}: {str(exc)[:300]}"
        state = "timeout" if _is_request_timeout_error(text) else "error"
        return None, text, state


def _sample_request_health(
    *,
    endpoint: str,
    api_key: str,
    cell: str,
    event: str,
    doc_id: str | None = None,
    active_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    endpoint = control._normalize_url(endpoint)
    port = control._url_port(endpoint)
    host = control._url_host(endpoint) or "127.0.0.1"
    active_docs = [str(item) for item in (active_doc_ids or []) if item]
    epoch = time.time()
    health_status, _health_body, health_state = _probe_http_text(
        f"{endpoint}/health",
        api_key=api_key,
        timeout=1.0,
    )
    slots_status, slots_body, slots_state = _probe_http_text(
        f"{endpoint}/slots",
        api_key=api_key,
        timeout=2.0,
    )
    return {
        "cell": cell,
        "epoch": round(epoch, 6),
        "iso_utc": _iso_utc(epoch),
        "event": event,
        "doc_id": doc_id or "",
        "active": bool(active_docs),
        "active_doc_ids": json.dumps(active_docs),
        "port_open": (
            control._port_open(host, int(port), timeout=0.5) if port is not None else False
        ),
        "health_ok": health_status is not None and 200 <= health_status < 300,
        "health_http_status": health_status,
        "health_probe_state": health_state,
        "runtime_pids": json.dumps(control._pids_for_port(int(port)) if port else []),
        "slots_http_status": slots_status,
        "slots_probe_state": slots_state,
        "slots_snapshot": slots_body,
    }


def _request_health_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    rows = payload.get("request_health_timeline")
    return [dict(row) for row in rows] if isinstance(rows, list) else []


def _runtime_health_gate(payload: dict[str, Any] | None) -> dict[str, Any]:
    rows = _request_health_rows(payload)
    active_rows = [row for row in rows if _boolish(row.get("active"))]
    health_false_rows = [row for row in active_rows if not _boolish(row.get("health_ok"))]
    port_open_health_false_rows = [
        row for row in health_false_rows if _boolish(row.get("port_open"))
    ]
    slots_timeout_rows = [
        row
        for row in active_rows
        if str(row.get("slots_probe_state") or "").strip().lower() == "timeout"
    ]
    failure_classes: list[str] = []
    if health_false_rows:
        failure_classes.append("failure_mode_classified_runtime_health")
    if slots_timeout_rows:
        failure_classes.append("failure_mode_classified_slots_timeout")
    passed = not failure_classes
    return {
        "status": "pass" if passed else "fail",
        "passed": passed,
        "active_sample_count": len(active_rows),
        "health_false_count": len(health_false_rows),
        "port_open_health_false_count": len(port_open_health_false_rows),
        "slots_timeout_count": len(slots_timeout_rows),
        "failure_classes": failure_classes,
        "first_port_open_health_false_utc": (
            port_open_health_false_rows[0].get("iso_utc")
            if port_open_health_false_rows
            else None
        ),
        "first_health_false_utc": (
            health_false_rows[0].get("iso_utc") if health_false_rows else None
        ),
        "first_slots_timeout_utc": (
            slots_timeout_rows[0].get("iso_utc") if slots_timeout_rows else None
        ),
    }


def _llm_request_timeout_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    rows: list[dict[str, Any]] = []
    for doc in payload.get("control", {}).get("documents") or []:
        doc_id = doc.get("document_id")
        for call in doc.get("llm_request_timings") or []:
            if not _is_request_timeout_error(call.get("error")):
                continue
            row = dict(call)
            row["document_id"] = doc_id or row.get("document_id")
            rows.append(row)
    return rows


def _partial_payload_after_timeout_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    timeout_docs = {
        str(row.get("document_id"))
        for row in _llm_request_timeout_rows(payload)
        if row.get("document_id")
    }
    rows: list[dict[str, Any]] = []
    for doc in payload.get("control", {}).get("documents") or []:
        doc_id = str(doc.get("document_id") or "")
        if doc_id not in timeout_docs:
            continue
        scoring_fields_present = any(
            key in doc
            for key in (
                "metric_results",
                "metric_status_counts",
                "trust_outcome",
                "context_actual",
            )
        )
        raw_payload_present = bool(doc.get("raw_payload"))
        if scoring_fields_present or raw_payload_present:
            rows.append(
                {
                    "document_id": doc_id,
                    "extraction_status": doc.get("extraction_status"),
                    "has_metric_results": "metric_results" in doc,
                    "has_trust_outcome": "trust_outcome" in doc,
                    "has_raw_payload": raw_payload_present,
                }
            )
    return rows


def _cell_gate(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {"status": "skipped"}
    acceptance = payload.get("acceptance") or {}
    summary = payload.get("control", {}).get("summary") or {}
    metric_counts = summary.get("metric_status_counts") or {}
    runtime_ids = acceptance.get("runtime_ids") or []
    request_timeout_rows = _llm_request_timeout_rows(payload)
    runtime_health = _runtime_health_gate(payload)
    partial_timeout_rows = _partial_payload_after_timeout_rows(payload)
    timeout_event = bool(acceptance.get("timeout_event")) or bool(request_timeout_rows)
    failure_classes: list[str] = []
    if timeout_event:
        failure_classes.append("failure_mode_classified_request_timeout")
    failure_classes.extend(runtime_health.get("failure_classes") or [])
    if partial_timeout_rows:
        failure_classes.append("failure_mode_classified_partial_payload")
    passed = (
        bool(acceptance.get("passed"))
        and not timeout_event
        and bool(runtime_health.get("passed"))
        and not partial_timeout_rows
    )
    return {
        "status": "pass" if passed else "fail",
        "passed": passed,
        "acceptance_passed_before_runtime_health_gate": bool(acceptance.get("passed")),
        "metrics": {
            "correct": int(metric_counts.get("correct") or 0),
            "total": int(summary.get("total_metric_checks") or 0),
            "wrong": int(metric_counts.get("wrong") or 0),
            "missing": int(metric_counts.get("missing") or 0),
            "abstain": int(metric_counts.get("abstain") or 0),
        },
        "trust": {
            "trusted_count": int((summary.get("trust_distribution") or {}).get("trusted") or 0),
            "trust_matches_expected": int(summary.get("trust_matches_expected") or 0),
            "total_documents": int(summary.get("total_documents") or 0),
        },
        "context": {
            "context_correct_documents": int(summary.get("context_correct_documents") or 0),
            "total_documents": int(summary.get("total_documents") or 0),
        },
        "no_fallback": not bool(acceptance.get("fallback_used")),
        "no_extraction_output_cache": acceptance.get("cache_hit") is False,
        "no_timeout": not timeout_event,
        "request_timeouts": {
            "count": len(request_timeout_rows),
            "documents": sorted(
                {
                    str(row.get("document_id"))
                    for row in request_timeout_rows
                    if row.get("document_id")
                }
            ),
        },
        "runtime_health": runtime_health,
        "partial_payload_after_timeout": {
            "passed": not bool(partial_timeout_rows),
            "count": len(partial_timeout_rows),
            "documents": sorted(
                {
                    str(row.get("document_id"))
                    for row in partial_timeout_rows
                    if row.get("document_id")
                }
            ),
        },
        "failure_classes": failure_classes,
        "all_runtime_ids": runtime_ids,
        "all_docs_on_extraction_runtime": all(
            runtime_id == "http://127.0.0.1:8002" for runtime_id in runtime_ids
        ),
        "shared_runtime_avoided": bool(acceptance.get("shared_runtime_avoided")),
        "prompt_cache_timing_classification": (
            payload.get("prompt_cache", {}).get("timing_classification")
        ),
    }


def _llm_intervals(payload: dict[str, Any], cell: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for doc in payload.get("control", {}).get("documents") or []:
        for call in doc.get("llm_request_timings") or []:
            if "started_epoch" not in call or "ended_epoch" not in call:
                continue
            row = dict(call)
            row["cell"] = cell
            rows.append(row)
    return rows


def _annotate_overlap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for row in rows:
        start = float(row.get("started_epoch") or 0.0)
        end = float(row.get("ended_epoch") or 0.0)
        doc_id = str(row.get("document_id") or "")
        overlaps = [
            other
            for other in rows
            if other is not row
            and float(other.get("started_epoch") or 0.0) < end
            and float(other.get("ended_epoch") or 0.0) > start
        ]
        other_doc_overlaps = [
            other for other in overlaps if str(other.get("document_id") or "") != doc_id
        ]
        annotated_row = dict(row)
        annotated_row["overlap_count"] = len(overlaps)
        annotated_row["other_doc_overlap_count"] = len(other_doc_overlaps)
        annotated_row["has_other_doc_overlap"] = bool(other_doc_overlaps)
        annotated.append(annotated_row)
    return annotated


def _union_seconds(rows: list[dict[str, Any]]) -> float:
    intervals = sorted(
        (
            float(row.get("started_epoch") or 0.0),
            float(row.get("ended_epoch") or 0.0),
        )
        for row in rows
        if row.get("started_epoch") is not None and row.get("ended_epoch") is not None
    )
    if not intervals:
        return 0.0
    total = 0.0
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += max(current_end - current_start, 0.0)
            current_start, current_end = start, end
    total += max(current_end - current_start, 0.0)
    return round(total, 6)


def _stage_totals(payload: dict[str, Any] | None) -> dict[str, float]:
    if payload is None:
        return {}
    totals: Counter[str] = Counter()
    run_stage = payload.get("run_stage_timing_seconds")
    if isinstance(run_stage, dict):
        for key, value in run_stage.items():
            totals[str(key)] += float(value or 0.0)
    control_payload = payload.get("control", {})
    global_stage = control_payload.get("stage_timing_seconds")
    if isinstance(global_stage, dict):
        for key, value in global_stage.items():
            totals[str(key)] += float(value or 0.0)
    for doc in control_payload.get("documents") or []:
        timings = doc.get("stage_timing_seconds")
        if not isinstance(timings, dict):
            continue
        mapping = {
            "docling_parse_layout": timings.get("docling_parse_layout"),
            "llm_request_response_wall": timings.get("llm_request_response_wall"),
            "llm_request_response_cumulative": timings.get("llm_request_response_cumulative"),
            "deterministic_table_locator": timings.get("pass2_locator"),
            "normalization": timings.get("normalization"),
            "real_gold_scoring_eval": timings.get("real_gold_scoring_eval"),
        }
        for key, value in mapping.items():
            totals[key] += float(value or 0.0)
    return {key: round(value, 6) for key, value in totals.items()}


def _baseline_stage_totals(baseline_dir: Path) -> dict[str, float]:
    path = baseline_dir / "per_stage_timing.csv"
    if not path.exists():
        return {}
    totals: dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                totals[str(row["stage"])] = float(row["total_seconds"])
            except (KeyError, TypeError, ValueError):
                continue
    return totals


def _baseline_wall_seconds(baseline_dir: Path) -> float | None:
    source = baseline_dir / "stage_attribution_canonical10.json"
    if source.exists():
        payload = _read_json(source)
        value = payload.get("control", {}).get("wall_time_seconds")
        if value is not None:
            return float(value)
    summary = baseline_dir / "performance_summary.md"
    if not summary.exists():
        return None
    for line in summary.read_text(encoding="utf-8").splitlines():
        if "Wall time:" not in line:
            continue
        text = line.split("`", 2)[1].rstrip("s")
        try:
            return float(text)
        except (IndexError, ValueError):
            return None
    return None


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _per_doc_rows(cell: str, payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    rows: list[dict[str, Any]] = []
    for doc in payload.get("control", {}).get("documents") or []:
        timings = doc.get("stage_timing_seconds")
        timings = timings if isinstance(timings, dict) else {}
        provenance = doc.get("method_provenance") or {}
        rows.append(
            {
                "cell": cell,
                "document_id": doc.get("document_id"),
                "elapsed_seconds": (doc.get("timing") or {}).get("elapsed_seconds"),
                "docling_parse_layout_seconds": timings.get("docling_parse_layout"),
                "llm_request_response_wall_seconds": timings.get("llm_request_response_wall"),
                "llm_request_response_cumulative_seconds": timings.get("llm_request_response_cumulative"),
                "pass1_classifier_seconds": timings.get("pass1_classifier"),
                "pass3a_metrics_seconds": timings.get("pass3a_metrics"),
                "pass2_locator_seconds": timings.get("pass2_locator"),
                "normalization_seconds": timings.get("normalization"),
                "real_gold_scoring_eval_seconds": timings.get("real_gold_scoring_eval"),
                "llm_call_count": len(doc.get("llm_request_timings") or []),
                "correct_metric_count": doc.get("correct_metric_count"),
                "failed_metric_count": doc.get("failed_metric_count"),
                "trust_outcome": doc.get("trust_outcome"),
                "trust_expected": doc.get("expected_trust"),
                "trust_matches_expected": doc.get("trust_matches_expected"),
                "context_correct": doc.get("context_correct"),
                "actual_method": provenance.get("actual_method"),
                "fallback_used": provenance.get("fallback_used"),
                "cache_hit": payload.get("control", {}).get("cache_hit"),
                "timeout_hit": _is_request_timeout_error(doc.get("extraction_error"))
                or any(
                    _is_request_timeout_error(call.get("error"))
                    for call in doc.get("llm_request_timings") or []
                ),
                "runtime_id": provenance.get("runtime_id"),
                "extraction_error": doc.get("extraction_error"),
            }
        )
    return rows


def _build_matrix(
    *,
    baseline_dir: Path,
    cell_b: dict[str, Any] | None,
    cell_c: dict[str, Any] | None,
    concurrency_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_wall = _baseline_wall_seconds(baseline_dir)
    baseline_stages = _baseline_stage_totals(baseline_dir)
    cells: dict[str, Any] = {
        "baseline_reference": {
            "wall_time_seconds": baseline_wall,
            "stage_totals_seconds": baseline_stages,
            "source": str(baseline_dir),
            "verdict": "clean_baseline_reused",
        }
    }
    fastest_clean_baseline = baseline_wall
    for name, payload in (
        ("server_parallel_2_serial_client", cell_b),
        ("server_parallel_2_two_doc_concurrent_client", cell_c),
    ):
        if payload is None:
            cells[name] = {"verdict": "skipped"}
            continue
        wall = float(payload.get("control", {}).get("wall_time_seconds") or 0.0)
        gate = _cell_gate(payload)
        improvement = None
        if fastest_clean_baseline:
            improvement = round((fastest_clean_baseline - wall) / fastest_clean_baseline, 6)
        cell_rows = [row for row in concurrency_rows if row.get("cell") == name]
        actual_other_doc_overlap = any(row.get("has_other_doc_overlap") for row in cell_rows)
        if not gate.get("passed"):
            failure_classes = set(gate.get("failure_classes") or [])
            if failure_classes & {
                "failure_mode_classified_request_timeout",
                "failure_mode_classified_runtime_health",
                "failure_mode_classified_slots_timeout",
                "failure_mode_classified_partial_payload",
            }:
                verdict = "candidate_invalidated_by_health_failfast"
            else:
                verdict = "candidate_regressed_correctness"
        elif improvement is not None and improvement >= 0.05:
            verdict = "candidate_faster_no_regression"
        else:
            verdict = "candidate_no_material_gain"
        cells[name] = {
            "wall_time_seconds": wall,
            "wall_delta_seconds_vs_baseline": (
                round(wall - fastest_clean_baseline, 6)
                if fastest_clean_baseline is not None
                else None
            ),
            "wall_improvement_fraction_vs_baseline": improvement,
            "materiality_threshold_fraction": 0.05,
            "stage_totals_seconds": _stage_totals(payload),
            "llm_interval_union_seconds": _union_seconds(cell_rows),
            "actual_other_doc_llm_overlap": actual_other_doc_overlap,
            "gate": gate,
            "verdict": verdict,
        }
    return {
        "materiality_rule": "candidate must beat fastest clean baseline by at least 5% wall time and preserve all gates",
        "fastest_clean_baseline_wall_seconds": fastest_clean_baseline,
        "cells": cells,
    }


def _write_reports(
    *,
    args: argparse.Namespace,
    report_dir: Path,
    baseline_dir: Path,
    audit: dict[str, Any],
    cell_b: dict[str, Any] | None,
    cell_c: dict[str, Any] | None,
    commands: list[dict[str, Any]],
) -> None:
    concurrency_rows = _annotate_overlap(
        _llm_intervals(cell_b or {}, "server_parallel_2_serial_client")
        + _llm_intervals(cell_c or {}, "server_parallel_2_two_doc_concurrent_client")
    )
    matrix = _build_matrix(
        baseline_dir=baseline_dir,
        cell_b=cell_b,
        cell_c=cell_c,
        concurrency_rows=concurrency_rows,
    )
    _write_json(report_dir / "performance_matrix.json", matrix)
    _write_json(
        report_dir / "correctness_gate.json",
        {
            "baseline_reference": _read_json(baseline_dir / "correctness_gate.json"),
            "server_parallel_2_serial_client": _cell_gate(cell_b),
            "server_parallel_2_two_doc_concurrent_client": _cell_gate(cell_c),
        },
    )
    _write_json(
        report_dir / "runtime_provenance.json",
        {
            "audit": audit,
            "server_parallel_2_serial_client": (cell_b or {}).get("runtime"),
            "server_parallel_2_serial_client_after": (cell_b or {}).get("runtime_after"),
            "server_parallel_2_two_doc_concurrent_client": (cell_c or {}).get("runtime"),
            "server_parallel_2_two_doc_concurrent_client_after": (cell_c or {}).get("runtime_after"),
            "shared_runtime": (cell_c or cell_b or {}).get("shared_runtime"),
        },
    )
    _write_json(
        report_dir / "prompt_cache_provenance.json",
        {
            "server_parallel_2_serial_client": (cell_b or {}).get("prompt_cache"),
            "server_parallel_2_two_doc_concurrent_client": (cell_c or {}).get("prompt_cache"),
        },
    )
    _write_json(
        report_dir / "gpu_preflight.json",
        {
            "preflight": audit.get("gpu_preflight"),
            "server_parallel_2_serial_client_before": (cell_b or {}).get("gpu_before"),
            "server_parallel_2_serial_client_after": (cell_b or {}).get("gpu_after"),
            "server_parallel_2_two_doc_concurrent_client_before": (cell_c or {}).get("gpu_before"),
            "server_parallel_2_two_doc_concurrent_client_after": (cell_c or {}).get("gpu_after"),
        },
    )
    _write_csv(
        report_dir / "per_doc_timing.csv",
        _per_doc_rows("server_parallel_2_serial_client", cell_b)
        + _per_doc_rows("server_parallel_2_two_doc_concurrent_client", cell_c),
        [
            "cell",
            "document_id",
            "elapsed_seconds",
            "docling_parse_layout_seconds",
            "llm_request_response_wall_seconds",
            "llm_request_response_cumulative_seconds",
            "pass1_classifier_seconds",
            "pass3a_metrics_seconds",
            "pass2_locator_seconds",
            "normalization_seconds",
            "real_gold_scoring_eval_seconds",
            "llm_call_count",
            "correct_metric_count",
            "failed_metric_count",
            "trust_outcome",
            "trust_expected",
            "trust_matches_expected",
            "context_correct",
            "actual_method",
            "fallback_used",
            "cache_hit",
            "timeout_hit",
            "runtime_id",
            "extraction_error",
        ],
    )
    stage_rows: list[dict[str, Any]] = []
    baseline_stages = _baseline_stage_totals(baseline_dir)
    for cell, payload in (
        ("baseline_reference", None),
        ("server_parallel_2_serial_client", cell_b),
        ("server_parallel_2_two_doc_concurrent_client", cell_c),
    ):
        totals = baseline_stages if cell == "baseline_reference" else _stage_totals(payload)
        wall = (
            _baseline_wall_seconds(baseline_dir)
            if cell == "baseline_reference"
            else (payload or {}).get("control", {}).get("wall_time_seconds")
        )
        for stage, seconds in sorted(totals.items()):
            baseline_seconds = baseline_stages.get(stage)
            stage_rows.append(
                {
                    "cell": cell,
                    "stage": stage,
                    "total_seconds": seconds,
                    "wall_percent": (
                        round((float(seconds) / float(wall)) * 100.0, 6)
                        if wall
                        else None
                    ),
                    "delta_seconds_vs_baseline": (
                        round(float(seconds) - float(baseline_seconds), 6)
                        if cell != "baseline_reference" and baseline_seconds is not None
                        else None
                    ),
                }
            )
    _write_csv(
        report_dir / "per_stage_timing.csv",
        stage_rows,
        ["cell", "stage", "total_seconds", "wall_percent", "delta_seconds_vs_baseline"],
    )
    if concurrency_rows:
        _write_csv(
            report_dir / "concurrency_timeline.csv",
            concurrency_rows,
            [
                "cell",
                "document_id",
                "call_index",
                "started_epoch",
                "ended_epoch",
                "elapsed_seconds",
                "component",
                "task_type",
                "prompt_chars",
                "overlap_count",
                "other_doc_overlap_count",
                "has_other_doc_overlap",
                "error",
            ],
        )
    health_rows = _request_health_rows(cell_b) + _request_health_rows(cell_c)
    if health_rows:
        _write_csv(
            report_dir / "request_health_timeline.csv",
            health_rows,
            REQUEST_HEALTH_TIMELINE_FIELDS,
        )
    commands_text = "\n".join(row.get("cmd", "") for row in commands if row.get("cmd"))
    (report_dir / "commands_run.txt").write_text(commands_text.rstrip() + "\n", encoding="utf-8")
    _write_notes(report_dir, args, audit, matrix, concurrency_rows)
    if any(
        cell.get("verdict", "").startswith("candidate_regressed")
        or cell.get("verdict", "").startswith("candidate_invalidated")
        for cell in matrix.get("cells", {}).values()
        if isinstance(cell, dict)
    ):
        (report_dir / "failure_taxonomy.md").write_text(
            "# Failure Taxonomy\n\nA candidate failed one or more correctness gates. See correctness_gate.json and raw cell JSON artifacts.\n",
            encoding="utf-8",
        )


def _write_notes(
    report_dir: Path,
    args: argparse.Namespace,
    audit: dict[str, Any],
    matrix: dict[str, Any],
    concurrency_rows: list[dict[str, Any]],
) -> None:
    c_cell = matrix.get("cells", {}).get("server_parallel_2_two_doc_concurrent_client", {})
    actual_concurrency = any(
        row.get("cell") == "server_parallel_2_two_doc_concurrent_client"
        and row.get("has_other_doc_overlap")
        for row in concurrency_rows
    )
    summary_lines = [
        "# Docling Runtime Parallel 2 Experiment",
        "",
        "## Verdict",
        "",
        f"- Cell B: `{matrix['cells'].get('server_parallel_2_serial_client', {}).get('verdict')}`",
        f"- Cell C: `{c_cell.get('verdict')}`",
        f"- Actual concurrent cross-document LLM requests: `{actual_concurrency}`",
        "",
        "## Contract Scope",
        "",
        "- Lane: Financial Truth.",
        "- Execution mode: AUDIT -> SAFE EXTENSION.",
        "- Runtime knob tested: dedicated `:8002` llama.cpp `--parallel 2`.",
        "- Extraction semantics, prompts, gold labels, metric normalization, trust semantics, parser defaults, and shared `:8001` routing were not changed.",
        "",
        "## Timing",
        "",
        f"- Fastest clean baseline wall: `{matrix.get('fastest_clean_baseline_wall_seconds')}s`.",
        f"- Cell C wall: `{c_cell.get('wall_time_seconds')}s`.",
        f"- Cell C improvement fraction: `{c_cell.get('wall_improvement_fraction_vs_baseline')}`.",
        "",
        "## DATA_MISSING",
        "",
        "- Baseline LLM absolute request intervals are unavailable because the prior artifact predates interval timestamp capture.",
        "- Server-side llama.cpp slot assignment timing is inferred from client request overlap and wall time; llama.cpp did not emit per-slot CSV telemetry into this harness.",
    ]
    (report_dir / "performance_summary.md").write_text(
        "\n".join(summary_lines).rstrip() + "\n",
        encoding="utf-8",
    )
    harness_lines = [
        "# Harness Notes",
        "",
        f"- Worktree audit: `{audit.get('git_status_short')}`",
        f"- Existing runtime action: `{audit.get('runtime_restart', {}).get('reason')}`",
        f"- Max client concurrency requested: `{args.max_client_concurrency}`.",
        f"- Max client concurrency enforced: `2`.",
        f"- Actual cross-document LLM overlap observed: `{actual_concurrency}`.",
        "- The existing serial control harness cannot create two document jobs concurrently; Cell C uses separate child processes capped at two active documents.",
    ]
    (report_dir / "harness_notes.md").write_text(
        "\n".join(harness_lines).rstrip() + "\n",
        encoding="utf-8",
    )
    c_gate = c_cell.get("gate") if isinstance(c_cell.get("gate"), dict) else {}
    health_gate = (
        c_gate.get("runtime_health") if isinstance(c_gate.get("runtime_health"), dict) else {}
    )
    timeout_gate = (
        c_gate.get("request_timeouts") if isinstance(c_gate.get("request_timeouts"), dict) else {}
    )
    partial_gate = (
        c_gate.get("partial_payload_after_timeout")
        if isinstance(c_gate.get("partial_payload_after_timeout"), dict)
        else {}
    )
    failfast_lines = [
        "# Health Fail-Fast Summary",
        "",
        "## Lane Classification",
        "",
        "Lane: Financial Truth. Execution mode: AUDIT -> SAFE EXTENSION.",
        "",
        "## Guardrail Added",
        "",
        "- Parallel2 candidate gates now invalidate timing comparisons on captured LLM request timeouts, active runtime health failure, `/slots` probe timeouts, or partial payloads after LLM timeout.",
        "- Cell C captures `request_health_timeline.csv` rows during active child extraction.",
        "- Production extraction semantics are unchanged.",
        "",
        "## Cell C Gate",
        "",
        f"- Status: `{c_gate.get('status')}`.",
        f"- Failure classes: `{c_gate.get('failure_classes')}`.",
        f"- Request timeouts: `{timeout_gate.get('count')}`.",
        f"- Active health samples: `{health_gate.get('active_sample_count')}`.",
        f"- Port-open/health-false samples: `{health_gate.get('port_open_health_false_count')}`.",
        f"- `/slots` timeout samples: `{health_gate.get('slots_timeout_count')}`.",
        f"- Partial payload after timeout documents: `{partial_gate.get('documents')}`.",
        "",
        "## DATA_MISSING",
        "",
        "- Slot/task-to-document mapping remains unresolved unless future llama.cpp telemetry exposes a stable server task id to client document id join key.",
    ]
    (report_dir / "health_failfast_summary.md").write_text(
        "\n".join(failfast_lines).rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    if int(args.server_parallel) != 2:
        raise SystemExit("This guarded experiment only supports --server-parallel 2")
    if int(args.max_client_concurrency) > 2:
        raise SystemExit("--max-client-concurrency must not exceed 2")
    os.environ["EXTRACTION_SERVER_PARALLEL"] = "2"
    os.environ["LLAMA_SERVER_MMAP"] = "0"
    os.environ["LLAMA_ARG_CACHE_RAM"] = "0"
    os.environ["LLAMA_ARG_CACHE_PROMPT"] = "false"
    report_dir = args.output_dir or (
        REPO_ROOT / "reports" / f"docling_runtime_knob_parallel2_{_utc_stamp()}"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    commands: list[dict[str, Any]] = []
    audit: dict[str, Any] = {
        "started_at": _utc_stamp(),
        "baseline_dir": str(args.baseline_dir),
        "git_status_short": _run_capture(["git", "status", "--short", "--branch"])["stdout"].strip(),
        "previous_milestone_files_status": _run_capture(
            [
                "git",
                "status",
                "--short",
                "scripts/run_isolated_docling_control.py",
                "scripts/test_run_isolated_docling_control.py",
            ]
        )["stdout"].strip(),
        "gpu_preflight_check": _run_capture(["scripts/gpu_process_guard.sh", "--check"]),
        "gpu_preflight": control._gpu_guard_json(),
    }
    if audit["gpu_preflight_check"]["returncode"] != 0:
        _write_json(report_dir / "gpu_preflight.json", audit)
        raise SystemExit("blocked_vram_preflight")
    audit["runtime_restart"] = _ensure_runtime_ready_for_parallel2(args)
    cell_b = _run_cell_b(args, report_dir, commands)
    cell_c = _run_cell_c(args, report_dir, commands)
    if not args.keep_runtime:
        stop_records = _stop_runtime_pids(args.extraction_url, api_key=args.api_key)
        audit["final_runtime_stop_records"] = stop_records
    _write_json(report_dir / "audit.json", audit)
    _write_reports(
        args=args,
        report_dir=report_dir,
        baseline_dir=args.baseline_dir,
        audit=audit,
        cell_b=cell_b,
        cell_c=cell_c,
        commands=commands,
    )
    print(f"report_dir={report_dir}")
    print(json.dumps(_read_json(report_dir / "performance_matrix.json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
