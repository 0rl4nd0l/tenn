#!/usr/bin/env python3
"""Run the strict 4-doc Docling control against a dedicated extraction runtime.

This is an opt-in operations harness. It does not change production defaults:
it sets EXTRACTION_LLAMACPP_URL before importing backend code, verifies that the
endpoint is not the shared :8001 lane, then uses the existing real-gold
evaluation functions from app.main.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
FINANCIAL_ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(FINANCIAL_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(FINANCIAL_ENGINE_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_DOC_IDS = (
    "bhp_a_2025-06-30",
    "bhp_a_2021-06-30_difficult",
    "rio_a_2024-12-31",
    "tls_h_2025-12-31",
)
CANONICAL_10_DOC_IDS = (
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
DEFAULT_EXTRACTION_URL = "http://127.0.0.1:8002"
DEFAULT_SHARED_URL = "http://127.0.0.1:8001"
DEFAULT_MODEL_PATH = "/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_ALIAS = "qwen2.5-14b-instruct"
DEFAULT_RESULTS_JSON = (
    REPO_ROOT / "reports" / "extraction_runtime" / "isolated_docling_control.json"
)
DEFAULT_REPORT_MD = (
    REPO_ROOT / "reports" / "extraction_runtime" / "isolated_docling_control.md"
)
DEFAULT_RUNTIME_LOG = (
    REPO_ROOT / "reports" / "extraction_runtime" / "llama_extraction_8002.log"
)
DEFAULT_EXTRACTION_LOCK = Path("/tmp/llama-extraction-server.lock")
_TERMINAL_STAGE_STATUSES = {"succeeded", "failed", "blocked", "skipped"}


class _InMemoryStageObserver:
    """Capture extraction observer timings without writing backend run-status files."""

    def __init__(
        self,
        *,
        document_id: str,
        requested_method: str,
        strict_method: bool,
    ) -> None:
        self.document_id = document_id
        self.requested_method = requested_method
        self.strict_method = bool(strict_method)
        self.actual_method: str | None = None
        self.started_at = time.perf_counter()
        self._stage_started_at: dict[str, float] = {}
        self.stage_timings_seconds: dict[str, float] = {}
        self.events: list[dict[str, Any]] = []

    def set_actual_method(self, actual_method: str | None) -> None:
        self.actual_method = str(actual_method or "").strip() or self.actual_method

    def emit(
        self,
        stage: str,
        status: str,
        message: str,
        *,
        warning_code: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.perf_counter()
        stage_key = str(stage or "").strip()
        status_key = str(status or "").strip()
        if status_key == "running":
            self._stage_started_at.setdefault(stage_key, now)
        elif status_key in _TERMINAL_STAGE_STATUSES:
            started = self._stage_started_at.pop(stage_key, None)
            elapsed = 0.0 if started is None else max(now - started, 0.0)
            self.stage_timings_seconds[stage_key] = (
                self.stage_timings_seconds.get(stage_key, 0.0) + elapsed
            )

        event = {
            "document_id": self.document_id,
            "requested_method": self.requested_method,
            "actual_method": self.actual_method,
            "strict_method": self.strict_method,
            "stage": stage_key,
            "status": status_key,
            "elapsed_since_observer_start_seconds": round(
                max(now - self.started_at, 0.0), 6
            ),
            "message": str(message or ""),
            "warning_code": warning_code,
            "error_code": error_code,
            "details": dict(details or {}),
        }
        self.events.append(event)
        return event

    def final_summary(self, summary: dict[str, Any]) -> dict[str, Any]:
        return {"final_summary": dict(summary or {})}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the strict Docling 4-doc control with EXTRACTION_LLAMACPP_URL "
            "pinned to a dedicated llama.cpp endpoint."
        )
    )
    parser.add_argument(
        "--extraction-url",
        default=os.environ.get("EXTRACTION_LLAMACPP_URL", DEFAULT_EXTRACTION_URL),
        help="Dedicated extraction llama.cpp base URL. Must resolve to port 8002.",
    )
    parser.add_argument(
        "--shared-url",
        default=(
            os.environ.get("LLAMACPP_URL")
            or os.environ.get("LLM_URL")
            or DEFAULT_SHARED_URL
        ),
        help="Shared chat/router llama.cpp base URL. Used only for isolation checks.",
    )
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", "local-openai-key"))
    parser.add_argument("--extract-model", default=os.environ.get("EXTRACT_MODEL", DEFAULT_MODEL_ALIAS))
    parser.add_argument("--model-path", default=os.environ.get("EXTRACTION_SERVER_MODEL", DEFAULT_MODEL_PATH))
    parser.add_argument("--model-alias", default=os.environ.get("EXTRACTION_SERVER_ALIAS", DEFAULT_MODEL_ALIAS))
    parser.add_argument("--ctx-size", type=int, default=int(os.environ.get("EXTRACTION_SERVER_CTX_SIZE", "16384")))
    parser.add_argument("--startup-timeout-seconds", type=float, default=240.0)
    parser.add_argument("--min-vram-free-mb", type=int, default=9000)
    parser.add_argument("--start-runtime", action="store_true", help="Start scripts/run_extraction_server.sh when :8002 is not healthy.")
    parser.add_argument("--stop-runtime", action="store_true", help="Stop only the extraction runtime process started by this script.")
    parser.add_argument(
        "--disable-prompt-cache",
        action="store_true",
        help=(
            "When this script starts the dedicated runtime, set llama.cpp "
            "LLAMA_ARG_CACHE_RAM=0 and LLAMA_ARG_CACHE_PROMPT=false."
        ),
    )
    parser.add_argument("--runtime-log", type=Path, default=DEFAULT_RUNTIME_LOG)
    parser.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS_JSON)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--doc-id", action="append", dest="doc_ids", help="Document id to include. Defaults to the strict 4-doc control set.")
    parser.add_argument(
        "--capture-payload",
        action="store_true",
        help="Include each raw extraction payload in the JSON artifact for diagnostics.",
    )
    parser.add_argument(
        "--use-source-pdfs",
        action="store_true",
        help=(
            "Use source PDFs in place. Default copies PDFs to a temporary "
            "directory so Docling cache reads are impossible."
        ),
    )
    return parser.parse_args()


def _normalize_url(raw: str) -> str:
    text = str(raw or "").strip().rstrip("/")
    if text.endswith("/v1"):
        text = text[: -len("/v1")]
    return text.rstrip("/")


def _url_port(raw: str) -> int | None:
    parsed = urlparse(_normalize_url(raw))
    return parsed.port


def _url_host(raw: str) -> str:
    return str(urlparse(_normalize_url(raw)).hostname or "").strip().lower()


def _same_endpoint(left: str, right: str) -> bool:
    return (_url_host(left), _url_port(left)) == (_url_host(right), _url_port(right))


def _http_ok(url: str, *, api_key: str, timeout: float = 5.0) -> bool:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    req = urlrequest.Request(url, headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            return 200 <= int(response.status) < 300
    except Exception:
        return False


def _port_open(host: str, port: int, *, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _run(
    cmd: list[str],
    *,
    check: bool = False,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def _redact_cmdline(cmdline: str) -> str:
    parts = str(cmdline or "").split()
    redacted: list[str] = []
    skip_next = False
    for part in parts:
        if skip_next:
            redacted.append("<redacted>")
            skip_next = False
            continue
        if part.startswith("--api-key="):
            redacted.append("--api-key=<redacted>")
            continue
        if part.startswith("--api-key-file="):
            redacted.append("--api-key-file=<redacted>")
            continue
        redacted.append(part)
        if part in {"--api-key", "--api-key-file"}:
            skip_next = True
    return " ".join(redacted)


def _read_pid_env(pid: int, names: tuple[str, ...]) -> dict[str, str | None]:
    wanted = set(names)
    values: dict[str, str | None] = {name: None for name in names}
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return values
    for item in raw.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key_raw, value_raw = item.split(b"=", 1)
        key = key_raw.decode("utf-8", errors="replace")
        if key in wanted:
            values[key] = value_raw.decode("utf-8", errors="replace")
    return values


def _prompt_cache_controls_for_pid(pid: int, cmdline: str) -> dict[str, Any]:
    parts = str(cmdline or "").split()
    cache_ram_arg: str | None = None
    cache_prompt_arg: str | None = None
    for index, part in enumerate(parts):
        if part == "--cache-ram" and index + 1 < len(parts):
            cache_ram_arg = parts[index + 1]
        elif part.startswith("--cache-ram="):
            cache_ram_arg = part.split("=", 1)[1]
        elif part in {"--cache-prompt", "--no-cache-prompt"}:
            cache_prompt_arg = part
    env_values = _read_pid_env(
        pid,
        ("LLAMA_ARG_CACHE_RAM", "LLAMA_ARG_CACHE_PROMPT"),
    )
    cache_ram = cache_ram_arg if cache_ram_arg is not None else env_values.get("LLAMA_ARG_CACHE_RAM")
    cache_prompt = (
        cache_prompt_arg
        if cache_prompt_arg is not None
        else env_values.get("LLAMA_ARG_CACHE_PROMPT")
    )
    disabled = str(cache_ram or "").strip() == "0" or str(cache_prompt or "").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    } or cache_prompt_arg == "--no-cache-prompt"
    return {
        "cmdline_cache_ram": cache_ram_arg,
        "cmdline_cache_prompt": cache_prompt_arg,
        "env_LLAMA_ARG_CACHE_RAM": env_values.get("LLAMA_ARG_CACHE_RAM"),
        "env_LLAMA_ARG_CACHE_PROMPT": env_values.get("LLAMA_ARG_CACHE_PROMPT"),
        "disabled_by_runtime_config": disabled,
    }


def _gpu_guard_json() -> dict[str, Any]:
    proc = _run(["scripts/gpu_process_guard.sh", "--json"], timeout=10.0)
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or proc.stdout.strip(), "returncode": proc.returncode}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": "gpu_process_guard returned non-JSON output", "raw": proc.stdout}
    return payload if isinstance(payload, dict) else {"raw": payload}


def _vram_free_mb() -> int | None:
    proc = _run(
        [
            "nvidia-smi",
            "--query-gpu=memory.free",
            "--format=csv,noheader,nounits",
        ],
        timeout=10.0,
    )
    if proc.returncode != 0:
        return None
    text = proc.stdout.strip().splitlines()[0].strip() if proc.stdout.strip() else ""
    try:
        return int(text)
    except ValueError:
        return None


def _pids_for_port(port: int) -> list[int]:
    proc = _run(["pgrep", "-af", rf"llama-server.*--port {port}\b"], timeout=10.0)
    if proc.returncode not in {0, 1}:
        return []
    pids: list[int] = []
    for line in proc.stdout.splitlines():
        first = line.split(maxsplit=1)[0]
        try:
            pids.append(int(first))
        except ValueError:
            continue
    return pids


def _cmdline_for_pid(pid: int) -> str:
    proc = _run(["ps", "-p", str(pid), "-o", "args="], timeout=10.0)
    return _redact_cmdline(proc.stdout.strip()) if proc.returncode == 0 else ""


def _runtime_status(endpoint: str, *, api_key: str) -> dict[str, Any]:
    port = _url_port(endpoint)
    if port is None:
        raise RuntimeError(f"runtime endpoint has no port: {endpoint}")
    pids = _pids_for_port(port)
    cmdlines = {str(pid): _cmdline_for_pid(pid) for pid in pids}
    return {
        "endpoint": endpoint,
        "port": port,
        "healthy": _http_ok(f"{endpoint}/health", api_key=api_key),
        "pids": pids,
        "cmdlines": cmdlines,
        "prompt_cache_controls": {
            str(pid): _prompt_cache_controls_for_pid(pid, cmdlines.get(str(pid), ""))
            for pid in pids
        },
    }


def _runtime_launch_env(args: argparse.Namespace, endpoint: str) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "EXTRACTION_SERVER_HOST": _url_host(endpoint) or "127.0.0.1",
            "EXTRACTION_SERVER_PORT": "8002",
            "EXTRACTION_SERVER_MODEL": str(args.model_path),
            "EXTRACTION_SERVER_ALIAS": str(args.model_alias),
            "EXTRACTION_SERVER_CTX_SIZE": str(args.ctx_size),
            "LLM_API_KEY": str(args.api_key or "local-openai-key"),
        }
    )
    if bool(getattr(args, "disable_prompt_cache", False)):
        env["LLAMA_ARG_CACHE_RAM"] = "0"
        env["LLAMA_ARG_CACHE_PROMPT"] = "false"
    return env


def _runtime_has_disabled_prompt_cache(status: dict[str, Any]) -> bool:
    controls = status.get("prompt_cache_controls")
    if not isinstance(controls, dict):
        return False
    return any(
        bool(control.get("disabled_by_runtime_config"))
        for control in controls.values()
        if isinstance(control, dict)
    )


def _start_extraction_runtime(args: argparse.Namespace, endpoint: str) -> int:
    port = _url_port(endpoint)
    if port != 8002:
        raise RuntimeError(f"extraction runtime must use canonical port 8002, got {port}")

    guard = _run(["scripts/gpu_process_guard.sh", "--check"], timeout=10.0)
    if guard.returncode != 0:
        raise RuntimeError(
            "gpu_process_guard failed before runtime start "
            f"(exit={guard.returncode})"
        )

    free_mb = _vram_free_mb()
    if free_mb is not None and free_mb < int(args.min_vram_free_mb):
        raise RuntimeError(
            f"insufficient VRAM for isolated extraction runtime: "
            f"free={free_mb}MB required={args.min_vram_free_mb}MB"
        )

    args.runtime_log.parent.mkdir(parents=True, exist_ok=True)
    env = _runtime_launch_env(args, endpoint)
    log_handle = args.runtime_log.open("ab")
    proc = subprocess.Popen(
        ["bash", "scripts/run_extraction_server.sh"],
        cwd=REPO_ROOT,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    log_handle.close()
    return int(proc.pid)


def _ensure_runtime(args: argparse.Namespace, endpoint: str) -> tuple[str, int | None]:
    status = _runtime_status(endpoint, api_key=args.api_key)
    if status["healthy"]:
        if bool(getattr(args, "disable_prompt_cache", False)) and not _runtime_has_disabled_prompt_cache(status):
            raise RuntimeError(
                "isolated extraction runtime is healthy but prompt cache is not "
                "disabled by observable runtime config; stop it before rerunning "
                "with --start-runtime --disable-prompt-cache"
            )
        return "reused", None

    port = int(status["port"])
    if _port_open(_url_host(endpoint) or "127.0.0.1", port):
        raise RuntimeError(
            f"port {port} is open but {endpoint}/health is not healthy; refusing stale runtime"
        )
    if not args.start_runtime:
        raise RuntimeError(
            f"isolated extraction runtime is not healthy at {endpoint}; "
            "start it first or rerun with --start-runtime"
        )

    started_pid = _start_extraction_runtime(args, endpoint)
    deadline = time.monotonic() + max(float(args.startup_timeout_seconds), 1.0)
    while time.monotonic() < deadline:
        if _http_ok(f"{endpoint}/health", api_key=args.api_key):
            return "started", started_pid
        if started_pid and not _pid_alive(started_pid):
            raise RuntimeError(
                f"extraction runtime exited during startup; see {args.runtime_log}"
            )
        time.sleep(2)
    raise RuntimeError(
        f"extraction runtime did not become healthy within "
        f"{args.startup_timeout_seconds:.0f}s; see {args.runtime_log}"
    )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_started_runtime(pid: int | None) -> dict[str, Any]:
    if not pid:
        return {"stopped": False, "reason": "no_started_pid"}
    if not _pid_alive(pid):
        _remove_lock_for_pid(pid)
        return {"stopped": False, "reason": "already_exited", "pid": pid}
    try:
        os.kill(pid, 15)
    except OSError as exc:
        return {"stopped": False, "reason": str(exc), "pid": pid}
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            _remove_lock_for_pid(pid)
            return {"stopped": True, "pid": pid, "signal": "TERM"}
        time.sleep(1)
    try:
        os.kill(pid, 9)
    except OSError:
        pass
    _remove_lock_for_pid(pid)
    return {"stopped": True, "pid": pid, "signal": "KILL"}


def _remove_lock_for_pid(pid: int) -> None:
    try:
        text = DEFAULT_EXTRACTION_LOCK.read_text(encoding="utf-8").strip()
    except OSError:
        return
    if text == str(pid):
        try:
            DEFAULT_EXTRACTION_LOCK.unlink()
        except OSError:
            pass


def _remove_stale_lock(pid: int) -> None:
    if not _pid_alive(pid):
        _remove_lock_for_pid(pid)


@contextmanager
def _capture_llm_request_timings(document_id: str):
    from app.services import llm as llm_service

    rows: list[dict[str, Any]] = []
    rows_lock = threading.Lock()
    next_call_index = 0
    original_generate_json = llm_service.generate_json

    def timed_generate_json(prompt: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal next_call_index
        with rows_lock:
            next_call_index += 1
            call_index = next_call_index
        started_at = time.perf_counter()
        error_text: str | None = None
        try:
            return original_generate_json(prompt, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            error_text = str(exc)
            raise
        finally:
            metadata = kwargs.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            row = {
                "document_id": document_id,
                "call_index": call_index,
                "component": str(metadata.get("component") or ""),
                "task_type": str(metadata.get("task_type") or ""),
                "requested_model": str(metadata.get("requested_model") or ""),
                "prompt_chars": len(str(prompt or "")),
                "elapsed_seconds": round(
                    max(time.perf_counter() - started_at, 0.0), 6
                ),
                "error": error_text,
            }
            with rows_lock:
                rows.append(row)

    llm_service.generate_json = timed_generate_json
    try:
        yield rows
    finally:
        llm_service.generate_json = original_generate_json


def _rounded_timing_map(values: dict[str, float]) -> dict[str, float]:
    return {
        str(key): round(max(float(value or 0.0), 0.0), 6)
        for key, value in values.items()
    }


def _observer_stage_timings(observer: _InMemoryStageObserver) -> dict[str, float]:
    raw = observer.stage_timings_seconds
    return _rounded_timing_map(
        {
            "runtime_env_check": raw.get("env_check", 0.0),
            "docling_parse_layout": raw.get("parser", 0.0),
            "pass1_classifier": raw.get("pass1_classifier", 0.0),
            "pass2_locator": raw.get("pass2_locator", 0.0),
            "pass3a_metrics": raw.get("pass3a_metrics", 0.0),
            "pass3b_narrative": raw.get("pass3b_narrative", 0.0),
            "pass4_reconciliation": raw.get("pass4_reconciliation", 0.0),
            "validation": raw.get("validation", 0.0),
            "llm_request_response_wall": (
                raw.get("pass1_classifier", 0.0)
                + raw.get("pass3a_metrics", 0.0)
                + raw.get("pass3b_narrative", 0.0)
            ),
            "normalization_reconciliation_validation": (
                raw.get("pass4_reconciliation", 0.0) + raw.get("validation", 0.0)
            ),
        }
    )


def _prepare_docs(doc_ids: tuple[str, ...], *, use_source_pdfs: bool):
    from app import main as main_app

    docs_by_id = {doc.document_id: doc for doc in main_app._load_real_gold_dataset(main_app.REAL_GOLD_DATASET_DIR)}
    missing = [doc_id for doc_id in doc_ids if doc_id not in docs_by_id]
    if missing:
        raise RuntimeError(f"missing real-gold docs: {', '.join(missing)}")
    selected = [docs_by_id[doc_id] for doc_id in doc_ids]
    if use_source_pdfs:
        return selected, None

    temp_dir = tempfile.TemporaryDirectory(prefix="tenn-isolated-docling-")
    temp_root = Path(temp_dir.name)
    copied = []
    for doc in selected:
        source = main_app._resolve_real_gold_source_path(doc.source_file)
        target = temp_root / source.name
        shutil.copy2(source, target)
        copied.append(replace(doc, source_file=str(target)))
    return copied, temp_dir


def _evaluate_real_gold_document_with_payload(
    doc: Any,
    *,
    tolerance: float,
    method: str,
    strict_method: bool,
) -> dict[str, Any]:
    from app import main as main_app
    from app.services.extraction_gold_eval import evaluate_real_gold_fixture
    from app.services.method_isolated_extraction import run_method_isolated_extraction
    from app.services.router_state import extraction_activity

    main_app._persist_local_llm_api_key()
    source_candidate = Path(str(doc.source_file))
    source_path = (
        source_candidate
        if source_candidate.is_absolute()
        else main_app._resolve_real_gold_source_path(doc.source_file)
    )
    metadata = {
        "document_id": doc.document_id,
        "ticker": main_app._extract_ticker_from_source_path(source_path),
        "title": source_path.name,
    }
    observer = _InMemoryStageObserver(
        document_id=doc.document_id,
        requested_method=method,
        strict_method=strict_method,
    )
    stage_timing_seconds: dict[str, float] = {}
    llm_request_timings: list[dict[str, Any]] = []
    captured_llm_timings_ref: list[dict[str, Any]] = []

    extraction_error = None
    extraction_started_at = time.perf_counter()
    try:
        with _capture_llm_request_timings(doc.document_id) as captured_llm_timings:
            captured_llm_timings_ref = captured_llm_timings
            with extraction_activity(
                metadata={
                    "document_id": doc.document_id,
                    "requested_method": method,
                    "strict_method": strict_method,
                    "ticker": metadata["ticker"],
                    "title": metadata["title"],
                }
            ):
                extraction_result = run_method_isolated_extraction(
                    str(source_path),
                    metadata,
                    None,
                    requested_method=method,
                    strict_method=strict_method,
                    skip_narrative=True,
                    observer=observer,
                )
            llm_request_timings = [dict(row) for row in captured_llm_timings]
        payload = (
            extraction_result.payload
            if isinstance(extraction_result.payload, dict)
            else {}
        )
        extraction_status = str(getattr(extraction_result, "status", "failed"))
        extraction_error = getattr(extraction_result, "error", None)
    except Exception as exc:  # noqa: BLE001
        llm_request_timings = [dict(row) for row in captured_llm_timings_ref]
        payload = {}
        extraction_status = "failed"
        extraction_error = str(exc)
    stage_timing_seconds["extraction_total"] = round(
        max(time.perf_counter() - extraction_started_at, 0.0), 6
    )
    stage_timing_seconds.update(_observer_stage_timings(observer))
    stage_timing_seconds["llm_request_response_cumulative"] = round(
        sum(float(row.get("elapsed_seconds") or 0.0) for row in llm_request_timings),
        6,
    )

    normalization_started_at = time.perf_counter()
    expected_context = {
        "period_type": doc.period_type,
        "period_end": doc.period_end,
        "currency": doc.currency,
        "scale": doc.scale,
    }
    actual_context: dict[str, str | None] = {}
    context_mismatches: list[str] = []
    for field in main_app.REAL_GOLD_CONTEXT_FIELDS:
        expected_value = main_app._normalize_real_gold_context(
            field, expected_context[field]
        )
        actual_value = main_app._normalize_real_gold_context(field, payload.get(field))
        actual_context[field] = actual_value
        if expected_value != actual_value:
            context_mismatches.append(
                f"{field}: expected={expected_value!r} actual={actual_value!r}"
            )

    raw_metrics = (
        payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    )
    normalized_metrics: dict[str, Any] = {}
    for metric_name, source_metric_key in main_app.REAL_GOLD_METRIC_KEY_MAP.items():
        normalized_metrics[metric_name] = raw_metrics.get(source_metric_key)

    evaluation_payload = dict(payload)
    evaluation_payload["metrics"] = normalized_metrics
    method_provenance = payload.get("_method_provenance")
    method_provenance = method_provenance if isinstance(method_provenance, dict) else {}
    stage_timing_seconds["eval_payload_normalization"] = round(
        max(time.perf_counter() - normalization_started_at, 0.0), 6
    )
    stage_timing_seconds["normalization"] = round(
        stage_timing_seconds.get("normalization_reconciliation_validation", 0.0)
        + stage_timing_seconds.get("eval_payload_normalization", 0.0),
        6,
    )

    scoring_started_at = time.perf_counter()
    evaluation = evaluate_real_gold_fixture(
        main_app._build_real_gold_fixture(doc, tolerance),
        evaluation_payload,
    )
    metric_results: dict[str, dict[str, Any]] = {}
    metric_status_counts = {"correct": 0, "wrong": 0, "missing": 0, "abstain": 0}
    for metric in evaluation.metrics:
        metric_results[metric.metric] = {
            "status": metric.status.value,
            "expected": metric.expected,
            "actual": metric.actual,
            "reason": metric.reason,
            "source_metric_key": main_app.REAL_GOLD_METRIC_KEY_MAP.get(
                metric.metric, metric.metric
            ),
        }
        if metric.status.value in metric_status_counts:
            metric_status_counts[metric.status.value] += 1

    failed_metric_count = (
        metric_status_counts["wrong"]
        + metric_status_counts["missing"]
        + metric_status_counts["abstain"]
    )
    mismatch_reasons: list[str] = [*context_mismatches]
    for metric_name, result in metric_results.items():
        if result["status"] != "correct":
            mismatch_reasons.append(f"metric:{metric_name}:{result['reason']}")
    if evaluation.trust_matches_expected is False:
        mismatch_reasons.append(
            f"trust: expected={doc.expected_trust} actual={evaluation.trust.value}"
        )
    if extraction_error:
        mismatch_reasons.append(f"extraction_error:{extraction_error}")
    stage_timing_seconds["real_gold_scoring_eval"] = round(
        max(time.perf_counter() - scoring_started_at, 0.0), 6
    )

    return {
        "document_id": doc.document_id,
        "source_file": doc.source_file,
        "source_path": str(source_path),
        "source_basename": source_path.name,
        "ticker": metadata["ticker"],
        "period_type": doc.period_type,
        "period_end": doc.period_end,
        "expected_trust": doc.expected_trust,
        "extraction_status": extraction_status,
        "extraction_error": extraction_error,
        "context_correct": evaluation.context_ok,
        "context_expected": expected_context,
        "context_actual": actual_context,
        "context_mismatches": context_mismatches,
        "metric_results": metric_results,
        "metric_status_counts": metric_status_counts,
        "correct_metric_count": metric_status_counts["correct"],
        "wrong_metric_count": metric_status_counts["wrong"],
        "missing_metric_count": metric_status_counts["missing"],
        "abstained_metric_count": metric_status_counts["abstain"],
        "failed_metric_count": failed_metric_count,
        "trust_outcome": evaluation.trust.value,
        "trust_triggers": evaluation.trust_triggers,
        "trust_matches_expected": evaluation.trust_matches_expected,
        "review_session_id": None,
        "review_item_count": 0,
        "review_reason": None,
        "mismatch_reasons": mismatch_reasons,
        "method_provenance": method_provenance,
        "stage_timing_seconds": stage_timing_seconds,
        "stage_events": observer.events,
        "llm_request_timings": llm_request_timings,
        "raw_payload": payload,
    }


def _run_control(args: argparse.Namespace, endpoint: str) -> dict[str, Any]:
    os.environ["EXTRACTION_LLAMACPP_URL"] = endpoint
    os.environ["EXTRACT_MODEL"] = str(args.extract_model)
    os.environ["LLM_API_KEY"] = str(args.api_key or "local-openai-key")

    from app import main as main_app

    doc_ids = tuple(args.doc_ids or DEFAULT_DOC_IDS)
    staging_started_at = time.perf_counter()
    docs, temp_dir = _prepare_docs(doc_ids, use_source_pdfs=bool(args.use_source_pdfs))
    pdf_temp_staging_seconds = round(
        max(time.perf_counter() - staging_started_at, 0.0), 6
    )
    temp_root = getattr(temp_dir, "name", None)
    started = time.perf_counter()
    cleanup_seconds = 0.0
    try:
        results = []
        for doc in docs:
            doc_started = time.perf_counter()
            if args.capture_payload:
                result = _evaluate_real_gold_document_with_payload(
                    doc,
                    tolerance=max(float(args.tolerance), 0.0),
                    method="docling",
                    strict_method=True,
                )
            else:
                result = main_app._evaluate_real_gold_document(
                    doc,
                    tolerance=max(float(args.tolerance), 0.0),
                    method="docling",
                    strict_method=True,
                )
            result = dict(result)
            result["timing"] = {
                "elapsed_seconds": round(time.perf_counter() - doc_started, 3)
            }
            results.append(result)
    finally:
        if temp_dir is not None:
            cleanup_started_at = time.perf_counter()
            temp_dir.cleanup()
            cleanup_seconds = round(
                max(time.perf_counter() - cleanup_started_at, 0.0), 6
            )

    elapsed = time.perf_counter() - started
    summary = main_app._summarize_real_gold_results(results)
    return {
        "doc_ids": list(doc_ids),
        "used_temp_pdf_copies": not bool(args.use_source_pdfs),
        "temp_pdf_root": temp_root,
        "cache_hit": False if not bool(args.use_source_pdfs) else None,
        "wall_time_seconds": round(elapsed, 3),
        "stage_timing_seconds": {
            "pdf_temp_staging": pdf_temp_staging_seconds,
            "cleanup": cleanup_seconds,
        },
        "summary": summary,
        "documents": results,
    }


def _metric_status(result: dict[str, Any], metric: str) -> str:
    metric_result = (result.get("metric_results") or {}).get(metric) or {}
    return str(metric_result.get("status") or "")


def _derive_acceptance(payload: dict[str, Any]) -> dict[str, Any]:
    control = payload.get("control") if isinstance(payload.get("control"), dict) else {}
    docs = control.get("documents") if isinstance(control.get("documents"), list) else []
    doc_ids = control.get("doc_ids") if isinstance(control.get("doc_ids"), list) else []
    if not doc_ids:
        doc_ids = [str(doc.get("document_id") or "") for doc in docs]
    doc_id_set = {str(doc_id) for doc_id in doc_ids}
    if len(doc_ids) == len(DEFAULT_DOC_IDS) and doc_id_set == set(DEFAULT_DOC_IDS):
        acceptance_profile = "strict4"
    elif len(doc_ids) == len(CANONICAL_10_DOC_IDS) and doc_id_set == set(CANONICAL_10_DOC_IDS):
        acceptance_profile = "canonical10"
    else:
        acceptance_profile = "custom"
    runtime_endpoint = str(payload.get("runtime", {}).get("endpoint") or "")
    all_runtime_ids = []
    for doc in docs:
        provenance = doc.get("method_provenance") or {}
        all_runtime_ids.append(str(provenance.get("runtime_id") or ""))

    operating_cf_correct = all(
        _metric_status(doc, "operating_cash_flow") == "correct" for doc in docs
    )
    tls = next((doc for doc in docs if doc.get("document_id") == "tls_h_2025-12-31"), {})
    tls_revenue_correct = _metric_status(tls, "revenue") == "correct"
    requested_docling = all(
        (doc.get("method_provenance") or {}).get("requested_method") == "docling"
        for doc in docs
    )
    strict_method = all(
        bool((doc.get("method_provenance") or {}).get("strict_method")) for doc in docs
    )
    actual_docling_gpu = all(
        (doc.get("method_provenance") or {}).get("actual_method") == "docling_gpu"
        for doc in docs
    )
    fallback_used = any(
        bool((doc.get("method_provenance") or {}).get("fallback_used")) for doc in docs
    )
    timeout_event = any(
        "timeout" in str(doc.get("extraction_error") or "").lower()
        or "exceeded" in str(doc.get("extraction_error") or "").lower()
        for doc in docs
    )
    summary = payload.get("control", {}).get("summary") or {}
    docs_completed = int(summary.get("total_documents") or 0)
    failed_documents = int(summary.get("failed_documents") or 0)
    context_correct = int(summary.get("context_correct_documents") or 0)
    total_metric_checks = int(summary.get("total_metric_checks") or 0)
    metric_status_counts = (
        summary.get("metric_status_counts")
        if isinstance(summary.get("metric_status_counts"), dict)
        else {}
    )
    correct_metrics = int(metric_status_counts.get("correct") or 0)
    wrong_metrics = int(metric_status_counts.get("wrong") or 0)
    missing_metrics = int(metric_status_counts.get("missing") or 0)
    abstain_metrics = int(metric_status_counts.get("abstain") or 0)
    trusted_count = int((summary.get("trust_distribution") or {}).get("trusted") or 0)
    trust_matches = int(summary.get("trust_matches_expected") or 0)
    isolated_endpoint_used = bool(runtime_endpoint) and all(
        runtime_id == runtime_endpoint for runtime_id in all_runtime_ids
    )
    shared_runtime_avoided = bool(payload.get("isolation", {}).get("shared_runtime_avoided"))

    common_gate = all(
        (
            requested_docling,
            strict_method,
            actual_docling_gpu,
            not fallback_used,
            control.get("cache_hit") is False,
            not timeout_event,
            isolated_endpoint_used,
            shared_runtime_avoided,
        )
    )
    metric_gate = all(
        (
            total_metric_checks > 0,
            correct_metrics == total_metric_checks,
            wrong_metrics == 0,
            missing_metrics == 0,
            abstain_metrics == 0,
        )
    )
    if acceptance_profile == "canonical10":
        passed = all(
            (
                docs_completed == 10,
                failed_documents == 0,
                context_correct == 10,
                total_metric_checks == 24,
                correct_metrics == 24,
                trusted_count == 10,
                trust_matches == 10,
                metric_gate,
                common_gate,
            )
        )
    elif acceptance_profile == "strict4":
        passed = all(
            (
                docs_completed == 4,
                trusted_count == 4,
                trust_matches == 4,
                operating_cf_correct,
                tls_revenue_correct,
                common_gate,
            )
        )
    else:
        passed = all(
            (
                docs_completed == len(doc_ids),
                failed_documents == 0,
                context_correct == docs_completed,
                trust_matches == docs_completed,
                metric_gate,
                common_gate,
            )
        )
    return {
        "passed": passed,
        "acceptance_profile": acceptance_profile,
        "docs_completed": docs_completed,
        "failed_documents": failed_documents,
        "context_correct_documents": context_correct,
        "total_metric_checks": total_metric_checks,
        "metric_status_counts": dict(metric_status_counts),
        "metric_gate_passed": metric_gate,
        "trusted_count": trusted_count,
        "trust_matches_expected": trust_matches,
        "operating_cash_flow_correct_all": operating_cf_correct,
        "tls_revenue_correct": tls_revenue_correct,
        "requested_method_docling_all": requested_docling,
        "strict_method_all": strict_method,
        "actual_method_docling_gpu_all": actual_docling_gpu,
        "fallback_used": fallback_used,
        "cache_hit": payload.get("control", {}).get("cache_hit"),
        "timeout_event": timeout_event,
        "isolated_endpoint_used": isolated_endpoint_used,
        "shared_runtime_avoided": shared_runtime_avoided,
        "runtime_ids": all_runtime_ids,
    }


def _prompt_cache_provenance(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    runtime_after = payload.get("runtime_after")
    runtime_after = runtime_after if isinstance(runtime_after, dict) else {}
    controls = runtime_after.get("prompt_cache_controls")
    controls = controls if isinstance(controls, dict) else {}
    try:
        log_text = args.runtime_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log_text = ""
    log_enabled = "prompt cache is enabled" in log_text
    log_updates = log_text.count("updating prompt cache")
    disabled_by_config = any(
        bool(control.get("disabled_by_runtime_config"))
        for control in controls.values()
        if isinstance(control, dict)
    )
    disabled_requested = bool(getattr(args, "disable_prompt_cache", False))
    return {
        "requested_mode": "disabled" if disabled_requested else "record_only",
        "runtime_log": str(args.runtime_log),
        "disabled_by_runtime_config": disabled_by_config,
        "log_prompt_cache_enabled": log_enabled,
        "log_prompt_cache_update_count": log_updates,
        "log_disable_hint_present": "use `--cache-ram 0` to disable the prompt cache" in log_text,
        "runtime_controls": controls,
        "timing_classification": (
            "prompt_cache_disabled"
            if disabled_requested and disabled_by_config and not log_enabled and log_updates == 0
            else "cache_contaminated"
            if log_enabled or log_updates > 0
            else "prompt_cache_recorded_unverified"
        ),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    acceptance = payload["acceptance"]
    lines = [
        "# Isolated Docling Control",
        "",
        f"- Verdict: {'PASS' if acceptance['passed'] else 'REJECT'}",
        f"- Runtime endpoint: `{payload['runtime']['endpoint']}`",
        f"- Runtime PID(s): `{payload['runtime'].get('pids')}`",
        f"- Shared runtime avoided: `{acceptance['shared_runtime_avoided']}`",
        f"- Wall time: `{payload['control']['wall_time_seconds']}s`",
        "",
        "## Acceptance",
        "",
    ]
    for key, value in acceptance.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Documents", ""])
    lines.append("| Document | Trust | Trust match | Revenue | OCF | Net debt | Actual method | Fallback | Error |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for doc in payload["control"]["documents"]:
        provenance = doc.get("method_provenance") or {}
        lines.append(
            "| {document_id} | {trust} | {trust_match} | {revenue} | {ocf} | "
            "{net_debt} | {actual_method} | {fallback} | {error} |".format(
                document_id=doc.get("document_id"),
                trust=doc.get("trust_outcome"),
                trust_match=doc.get("trust_matches_expected"),
                revenue=_metric_status(doc, "revenue"),
                ocf=_metric_status(doc, "operating_cash_flow"),
                net_debt=_metric_status(doc, "net_debt"),
                actual_method=provenance.get("actual_method"),
                fallback=provenance.get("fallback_used"),
                error=str(doc.get("extraction_error") or ""),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    extraction_url = _normalize_url(args.extraction_url)
    shared_url = _normalize_url(args.shared_url)
    if not extraction_url:
        raise SystemExit("EXTRACTION_LLAMACPP_URL / --extraction-url is required")
    if _url_port(extraction_url) != 8002:
        raise SystemExit(
            f"Refusing non-canonical extraction runtime port: {extraction_url}"
        )
    if _same_endpoint(extraction_url, shared_url) or _url_port(extraction_url) == 8001:
        raise SystemExit(
            "Refusing shared runtime: extraction endpoint must differ from LLAMACPP_URL/:8001"
        )

    os.environ["EXTRACTION_LLAMACPP_URL"] = extraction_url
    os.environ["EXTRACT_MODEL"] = str(args.extract_model)

    runtime_lease_started_at = time.perf_counter()
    mode, started_pid = _ensure_runtime(args, extraction_url)
    runtime_lease_acquire_seconds = round(
        max(time.perf_counter() - runtime_lease_started_at, 0.0), 6
    )
    runtime_before = _runtime_status(extraction_url, api_key=args.api_key)
    shared_before = _runtime_status(shared_url, api_key=args.api_key)
    payload: dict[str, Any] = {
        "generated_at_epoch": time.time(),
        "execution_mode": "isolated_docling_control",
        "runtime": {
            **runtime_before,
            "lease_mode": mode,
            "started_pid": started_pid,
            "launch_model_path": str(args.model_path),
            "launch_model_alias": str(args.model_alias),
            "launch_ctx_size": int(args.ctx_size),
            "launch_flags_expected": [
                "--ctx-size",
                str(args.ctx_size),
                "--batch-size",
                "1024",
                "--ubatch-size",
                "512",
                "--n-gpu-layers",
                "999",
                "--main-gpu",
                "0",
                "--threads",
                "4",
                "--parallel",
                "1",
            ],
            "prompt_cache_requested_mode": (
                "disabled" if args.disable_prompt_cache else "record_only"
            ),
        },
        "run_stage_timing_seconds": {
            "runtime_lease_acquire": runtime_lease_acquire_seconds,
            "subprocess_startup": runtime_lease_acquire_seconds
            if mode == "started"
            else 0.0,
        },
        "shared_runtime": shared_before,
        "isolation": {
            "shared_runtime_endpoint": shared_url,
            "extraction_runtime_endpoint": extraction_url,
            "shared_runtime_avoided": not _same_endpoint(extraction_url, shared_url),
            "no_silent_fallback_to_shared": True,
            "control_plane_probe_during_extraction": False,
        },
        "gpu_before": _gpu_guard_json(),
    }
    stop_status: dict[str, Any] | None = None
    try:
        payload["control"] = _run_control(args, extraction_url)
        payload["runtime_after"] = _runtime_status(extraction_url, api_key=args.api_key)
        payload["gpu_after"] = _gpu_guard_json()
        payload["prompt_cache"] = _prompt_cache_provenance(args, payload)
        payload["acceptance"] = _derive_acceptance(payload)
    finally:
        if args.stop_runtime and mode == "started":
            stop_status = _terminate_started_runtime(started_pid)
    if stop_status is not None:
        payload["runtime_stop"] = stop_status

    args.results_json.parent.mkdir(parents=True, exist_ok=True)
    args.results_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    _write_report(args.report_path, payload)
    print(json.dumps(payload["acceptance"], indent=2, default=str))
    print(f"results_json={args.results_json}")
    print(f"report_path={args.report_path}")
    return 0 if payload["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
