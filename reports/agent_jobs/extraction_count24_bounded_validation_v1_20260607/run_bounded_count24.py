#!/usr/bin/env python3
"""Report-local bounded count-24 runner for the PR #309 approval packet."""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Any


JOB_ID = "extraction_count24_bounded_validation_v1_20260607"
REPO_ROOT = Path(__file__).resolve().parents[3]
FE_ROOT = REPO_ROOT / "financial-engine_v2"
DOCS_ROOT = Path(
    os.environ.get(
        "DOCS_ROOT",
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs",
    )
).resolve()
OUTPUT_DIR = Path(__file__).resolve().parent
TASK_CARD = REPO_ROOT / "docs/agent_tasks/extraction_count24_bounded_validation_v1_20260607.md"

APPROVED_HEAD = "bfe3a77ec6692d5052eefec7454461e75459f7e3"
PACKET_PREREQ_HEAD = "b67736109db2c405171ff039c3b2f071238205db"
SEED = int(os.environ.get("COUNT24_SEED", "20260602"))
COUNT = 24
REFERENCE_POOL_COUNT = 28633
REFERENCE_ORDERED_HASH = "3d99f44885fd056ac3f112d56abe95d14dd1ac9affdcd7315f860f690cdeb63f"
REFERENCE_SORTED_HASH = "e4d57b2cdb3e8583a3aeaf33fba5a2d959383500733473349771f80531629e7a"
PRIOR_COUNT16_MANIFEST = (
    REPO_ROOT
    / "reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/sample_manifest.json"
)

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
}

ALLOWED_DIR = "reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/"
ALLOWED_STATUS_PREFIXES = (
    "docs/agent_tasks/extraction_count24_bounded_validation_v1_20260607.md",
    ALLOWED_DIR,
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: str, *, cwd: Path | None = None, timeout: int = 30) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or REPO_ROOT,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": cmd,
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "elapsed_s": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "exit_code": 124,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "elapsed_s": round(time.monotonic() - started, 3),
            "timeout": True,
        }


def _json_http(url: str, *, timeout: int = 5) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_harness():
    path = FE_ROOT / "scripts" / "broad_extraction_test.py"
    spec = importlib.util.spec_from_file_location("count24_broad_extraction_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load harness: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DOCS_ROOT = DOCS_ROOT
    module._REPO_ROOT = Path("/")
    return module


def _rel(path: Path) -> str:
    return path.resolve().relative_to(Path("/")).as_posix()


def _doc_id_from_path(pdf_path: Path) -> str:
    stem = pdf_path.stem
    parts = stem.rsplit("_", 1)
    return parts[-1] if len(parts) > 1 else stem


def _ticker_from_path(pdf_path: Path) -> str:
    return pdf_path.parent.parent.name


def _source_fingerprint() -> dict[str, Any]:
    count = _run(
        f"find {DOCS_ROOT} -path '*/financial_performance/*.pdf' -type f | wc -l",
        timeout=120,
    )
    fingerprint = _run(
        "find "
        f"{DOCS_ROOT} "
        "-path '*/financial_performance/*.pdf' -type f "
        "-printf '%p\\t%s\\t%T@\\n' | sha256sum",
        timeout=240,
    )
    first_pdf = _run(
        f"find {DOCS_ROOT} -path '*/financial_performance/*.pdf' -type f | head -n 1",
        timeout=30,
    )
    return {
        "root": str(DOCS_ROOT),
        "exists": DOCS_ROOT.is_dir(),
        "financial_performance_pdf_count": int(count["stdout"] or 0)
        if str(count["stdout"]).isdigit()
        else count["stdout"],
        "fingerprint_sha256": fingerprint["stdout"].split()[0]
        if fingerprint["stdout"]
        else None,
        "first_pdf": first_pdf["stdout"],
        "commands": {
            "count": count,
            "fingerprint": fingerprint,
            "first_pdf": first_pdf,
        },
    }


def _sqlite_stats() -> dict[str, Any]:
    paths = [
        "/home/l4nd0/tenn-runtime/financial-engine_v2/data/ops/ops.db",
        "/home/l4nd0/tenn-runtime/financial-engine_v2/data/cockpit/state.db",
        str(REPO_ROOT / "financial-engine_v2/data/ops/ops.db"),
        str(REPO_ROOT / "financial-engine_v2/data/cockpit/state.db"),
    ]
    rows: list[dict[str, Any]] = []
    for item in paths:
        path = Path(item)
        if not path.exists():
            rows.append({"path": item, "exists": False})
            continue
        stat = path.stat()
        rows.append(
            {
                "path": item,
                "exists": True,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "mtime": dt.datetime.fromtimestamp(
                    stat.st_mtime, tz=dt.timezone.utc
                ).isoformat().replace("+00:00", "Z"),
            }
        )
    return {"rows": rows}


def _collect_qdrant() -> dict[str, Any]:
    qdrant: dict[str, Any] = {}
    for name in ("asx_docs", "news_chunks", "commentary_chunks"):
        data = _json_http(f"http://127.0.0.1:6333/collections/{name}")
        result = data.get("result", {}) if isinstance(data, dict) else {}
        qdrant[name] = {
            "status": result.get("status"),
            "points_count": result.get("points_count"),
            "indexed_vectors_count": result.get("indexed_vectors_count"),
            "update_queue_length": (result.get("update_queue") or {}).get("length")
            if isinstance(result.get("update_queue"), dict)
            else None,
            "raw_error": data.get("error") if isinstance(data, dict) else None,
        }
    return qdrant


def _git_status_paths(status_stdout: str) -> list[str]:
    paths: list[str] = []
    for line in status_stdout.splitlines():
        if not line:
            continue
        paths.append(line[3:] if line.startswith("?? ") else line[3:])
    return paths


def _unexpected_status_paths(status_stdout: str) -> list[str]:
    unexpected: list[str] = []
    for path in _git_status_paths(status_stdout):
        if not any(path == allowed or path.startswith(allowed) for allowed in ALLOWED_STATUS_PREFIXES):
            unexpected.append(path)
    return sorted(set(unexpected))


def _registry_state() -> dict[str, Any]:
    list_active = _run(
        "python3 scripts/agent_job_registry.py list-active --read-only",
        timeout=60,
    )
    git_common_dir = _run("git rev-parse --git-common-dir", timeout=30)
    active_root = (
        (Path(git_common_dir["stdout"]) / "tenn-agent-registry" / "active").resolve()
        if git_common_dir["stdout"]
        else None
    )
    active_files: list[str] = []
    if active_root is not None and active_root.exists():
        active_files = [str(path) for path in sorted(active_root.rglob("*")) if path.is_file()]
    return {
        "method": "list-active --read-only plus direct active-record directory inspection",
        "list_active": list_active,
        "active_root": str(active_root) if active_root is not None else None,
        "active_files": active_files,
        "read_only": True,
        "lock_acquired": False,
    }


def _collect_state() -> dict[str, Any]:
    redis_ping = _run("redis-cli ping", timeout=30)
    redis_celery = _run("redis-cli llen celery", timeout=30)
    redis_unacked_count = _run("redis-cli --scan --pattern '*unacked*' | wc -l", timeout=30)
    redis_queue_keys = _run(
        "redis-cli --scan | rg -i '(unacked|queue|rq|celery)'",
        timeout=30,
    )
    gpu_guard = _run("scripts/gpu_process_guard.sh --check", timeout=60)
    nvidia = _run("nvidia-smi", timeout=30)
    m40_query = _run(
        "nvidia-smi -i 1 "
        "--query-gpu=index,uuid,name,pci.bus_id,memory.total,memory.used,"
        "utilization.gpu,utilization.memory "
        "--format=csv,noheader,nounits",
        timeout=30,
    )
    m40_table = _run("nvidia-smi -i 1", timeout=30)
    processes = _run(
        "ps -eo pid,ppid,stat,comm,args | "
        "rg '(^| )[l]lama-server|(^| )[u]vicorn|(^| )[c]elery|(^| )[r]q|"
        "(^| )[d]ramatiq|broad_extraction|count-32|count32|backfill|ticker-universe'",
        timeout=30,
    )
    status_short = _run("git status --short --untracked-files=all")
    return {
        "generated_at": _now(),
        "repo": {
            "worktree": str(REPO_ROOT),
            "branch": _run("git branch --show-current")["stdout"] or "DETACHED",
            "head": _run("git rev-parse HEAD")["stdout"],
            "remote": _run("git remote -v")["stdout"].splitlines(),
            "status_short": status_short["stdout"].splitlines(),
            "unexpected_status_paths": _unexpected_status_paths(status_short["stdout"]),
            "head_equals_approved": _run(
                f"test $(git rev-parse HEAD) = {APPROVED_HEAD}"
            )["exit_code"]
            == 0,
            "head_contains_approved": _run(
                f"git merge-base --is-ancestor {APPROVED_HEAD} HEAD; printf '%s' $?"
            )["stdout"]
            == "0",
            "head_contains_packet_prereq": _run(
                f"git merge-base --is-ancestor {PACKET_PREREQ_HEAD} HEAD; printf '%s' $?"
            )["stdout"]
            == "0",
            "loaded_code_proof": {
                "method": "in-process import from approved detached worktree",
                "approved_head": APPROVED_HEAD,
                "runner_path": str(Path(__file__).resolve()),
                "harness_path": str(FE_ROOT / "scripts" / "broad_extraction_test.py"),
                "backend_path": str(FE_ROOT / "backend"),
                "note": (
                    "The runner imports broad_extraction_test.py from this worktree; "
                    "that harness prepends this worktree's backend path before "
                    "app.services.multipass_extraction is imported."
                ),
            },
        },
        "registry": _registry_state(),
        "runtime": {
            "backend_health": _json_http("http://127.0.0.1:8000/api/health"),
            "llamacpp_models": _json_http("http://127.0.0.1:8001/v1/models"),
            "redis_ping": redis_ping,
            "redis_celery_length": int(redis_celery["stdout"] or 0)
            if str(redis_celery["stdout"]).isdigit()
            else redis_celery["stdout"],
            "redis_unacked_key_count": int(redis_unacked_count["stdout"] or 0)
            if str(redis_unacked_count["stdout"]).isdigit()
            else redis_unacked_count["stdout"],
            "redis_queue_key_scan": redis_queue_keys["stdout"].splitlines(),
            "qdrant": _collect_qdrant(),
            "gpu_process_guard": {
                "exit_code": gpu_guard["exit_code"],
                "stdout": gpu_guard["stdout"].splitlines(),
                "stderr": gpu_guard["stderr"].splitlines(),
            },
            "nvidia_smi": {
                "exit_code": nvidia["exit_code"],
                "stdout_first_lines": nvidia["stdout"].splitlines()[:30],
                "stderr_first_lines": nvidia["stderr"].splitlines()[:30],
            },
            "gpu_telemetry_equivalent": {
                "method": "nvidia-smi -i 1 for active Tesla M40",
                "query": {
                    "exit_code": m40_query["exit_code"],
                    "stdout": m40_query["stdout"],
                    "stderr": m40_query["stderr"],
                },
                "table": {
                    "exit_code": m40_table["exit_code"],
                    "stdout_first_lines": m40_table["stdout"].splitlines()[:30],
                    "stderr_first_lines": m40_table["stderr"].splitlines()[:30],
                },
                "global_nvidia_smi_note": (
                    "Plain nvidia-smi fails on GT 1030 at 0000:25:00.0; "
                    "per-GPU telemetry for the active Tesla M40 succeeds."
                ),
            },
            "processes_matching_runtime": processes["stdout"].splitlines(),
        },
        "source_pdfs": _source_fingerprint(),
        "sqlite": _sqlite_stats(),
        "safe_env": SAFE_ENV_DEFAULTS,
    }


def _readiness_failures(state: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    repo = state["repo"]
    runtime = state["runtime"]
    source_pdfs = state["source_pdfs"]
    registry = state["registry"]
    if not repo["head_equals_approved"]:
        failures.append("HEAD is not exactly the operator-approved bfe3a77 commit")
    if not repo["head_contains_approved"]:
        failures.append("HEAD does not contain the operator-approved bfe3a77 commit")
    if not repo["head_contains_packet_prereq"]:
        failures.append("HEAD does not contain the packet prerequisite b677361 commit")
    if repo["unexpected_status_paths"]:
        failures.append("worktree has non-allowlisted dirt")
    if not source_pdfs.get("exists"):
        failures.append("source DOCS_ROOT is unavailable")
    if int(source_pdfs.get("financial_performance_pdf_count") or 0) < COUNT:
        failures.append("source financial_performance PDF count is below count-24")
    if runtime["redis_ping"]["stdout"] != "PONG":
        failures.append("redis ping did not return PONG")
    if runtime.get("redis_celery_length") != 0:
        failures.append("redis celery queue is not empty")
    if runtime.get("redis_unacked_key_count") != 0:
        failures.append("redis unacked key count is not zero")
    if registry["list_active"]["exit_code"] != 0:
        failures.append("safe read-only registry list-active failed")
    if registry.get("active_files"):
        failures.append("registry has active records")
    if runtime["gpu_process_guard"]["exit_code"] != 0:
        failures.append("gpu_process_guard failed")
    if runtime["gpu_telemetry_equivalent"]["query"]["exit_code"] != 0:
        failures.append("active GPU telemetry failed")
    if isinstance(runtime.get("llamacpp_models"), dict) and runtime["llamacpp_models"].get("error"):
        failures.append("llama.cpp /v1/models is not reachable")
    return failures


def _build_manifest(harness) -> tuple[dict[str, Any], list[Path], list[str], list[str]]:
    all_pdfs = harness.discover_pdfs()
    pool_paths = [_rel(path) for path in all_pdfs]
    sample = random.Random(SEED).sample(all_pdfs, min(COUNT, len(all_pdfs)))
    selected_ids = [_doc_id_from_path(path) for path in sample]
    first16_reference: list[str] = []
    prior: dict[str, Any] | None = None
    if PRIOR_COUNT16_MANIFEST.exists():
        prior = json.loads(PRIOR_COUNT16_MANIFEST.read_text(encoding="utf-8"))
        first16_reference = list(prior.get("selected_document_ids") or [])[:16]
    first16_selected = selected_ids[:16]
    added_docs = selected_ids[16:24]
    manifest = {
        "generated_at": _now(),
        "seed": SEED,
        "requested_count": COUNT,
        "actual_count": len(sample),
        "canonical_head": APPROVED_HEAD,
        "runner_commit": _run("git rev-parse HEAD")["stdout"],
        "docs_root": str(DOCS_ROOT),
        "candidate_pool_count": len(pool_paths),
        "candidate_pool_ordered_sha256": _hash_json(pool_paths),
        "candidate_pool_sorted_sha256": _hash_json(sorted(pool_paths)),
        "candidate_pool_reference": {
            "count": REFERENCE_POOL_COUNT,
            "ordered_sha256": REFERENCE_ORDERED_HASH,
            "sorted_sha256": REFERENCE_SORTED_HASH,
        },
        "selected_document_ids_sha256": _hash_json(selected_ids),
        "selected_document_ids": selected_ids,
        "first16_overlap_with_post_pr301_count16": len(set(first16_selected) & set(first16_reference)),
        "first16_selected_document_ids": first16_selected,
        "post_pr301_count16_selected_document_ids": first16_reference,
        "first16_exact_order_match": first16_selected == first16_reference,
        "new_documents_positions_17_24": added_docs,
        "selected_documents": [
            {
                "index": idx + 1,
                "ticker": _ticker_from_path(path),
                "document_id": _doc_id_from_path(path),
                "pdf_path": _rel(path),
                "title": path.name,
                "source_path": str(path),
                "source_document_class": "DATA_MISSING_BEFORE_EXTRACTION",
                "document_class": "DATA_MISSING_BEFORE_EXTRACTION",
                "period_type": "DATA_MISSING_BEFORE_EXTRACTION",
                "period_end": "DATA_MISSING_BEFORE_EXTRACTION",
                "scale": "DATA_MISSING_BEFORE_EXTRACTION",
                "preflight_classifier_reason": "DATA_MISSING_BEFORE_EXTRACTION",
                "selection_seed": SEED,
                "candidate_pool_ordered_sha256": _hash_json(pool_paths),
                "canonical_head": APPROVED_HEAD,
            }
            for idx, path in enumerate(sample)
        ],
    }
    return manifest, sample, pool_paths, first16_reference


def _manifest_failures(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if manifest["actual_count"] != COUNT:
        failures.append("selected manifest actual count is not 24")
    if manifest["candidate_pool_count"] != REFERENCE_POOL_COUNT:
        failures.append("candidate pool count drifted")
    if manifest["candidate_pool_ordered_sha256"] != REFERENCE_ORDERED_HASH:
        failures.append("candidate pool ordered hash drifted")
    if manifest["candidate_pool_sorted_sha256"] != REFERENCE_SORTED_HASH:
        failures.append("candidate pool sorted hash drifted")
    if manifest["first16_overlap_with_post_pr301_count16"] != 16:
        failures.append("first-16 overlap with post-PR301 count16 is not 16")
    if not manifest["first16_exact_order_match"]:
        failures.append("first-16 selected document order does not match post-PR301 count16")
    return failures


def _make_llm_client():
    harness = _load_harness()
    return harness.make_llm_client(use_anthropic=False)


def _run_one(pdf_path: Path, llm_client) -> dict[str, Any]:
    from app.services.multipass_extraction import run_multipass_extraction

    ticker = _ticker_from_path(pdf_path)
    doc_id = _doc_id_from_path(pdf_path)
    metadata = {
        "document_id": doc_id,
        "ticker": ticker,
        "title": pdf_path.name,
    }
    record: dict[str, Any] = {
        "pdf_path": _rel(pdf_path),
        "ticker": ticker,
        "document_id": doc_id,
        "title": pdf_path.name,
        "status": None,
        "error": None,
        "elapsed_s": None,
        "metrics": {},
        "period_type": None,
        "period_end": None,
        "scale": None,
        "currency": None,
        "confidence": None,
        "non_null_metrics": 0,
        "source_document_classification": None,
        "document_class": None,
        "source_bound": None,
        "risk_notes": [],
        "sanity": {},
    }
    started = time.monotonic()
    try:
        result = run_multipass_extraction(
            str(pdf_path),
            metadata,
            llm_client,
            skip_narrative=True,
        )
        payload = result.payload or {}
        metrics = payload.get("metrics") or {}
        classification = payload.get("source_document_classification")
        document_class = (
            classification.get("document_class")
            if isinstance(classification, dict)
            else None
        )
        record.update(
            {
                "elapsed_s": round(time.monotonic() - started, 2),
                "status": result.status,
                "error": result.error,
                "metrics": {name: metrics.get(name) for name in METRIC_FIELDS},
                "period_type": payload.get("period_type"),
                "period_end": str(payload.get("period_end"))
                if payload.get("period_end")
                else None,
                "scale": payload.get("scale"),
                "currency": payload.get("currency"),
                "confidence": payload.get("confidence_metrics"),
                "non_null_metrics": sum(
                    1 for value in metrics.values() if value is not None
                ),
                "source_document_classification": classification,
                "document_class": document_class,
                "source_bound": payload.get("source_bound"),
                "risk_notes": payload.get("risk_notes") or [],
            }
        )
        sanity = {}
        if metrics.get("revenue") is not None:
            sanity["revenue_positive"] = metrics["revenue"] > 0
        if metrics.get("shares_outstanding") is not None:
            sanity["shares_positive"] = metrics["shares_outstanding"] > 0
        if metrics.get("cash_end") is not None:
            sanity["cash_end_positive"] = metrics["cash_end"] > 0
        if payload.get("period_end"):
            sanity["period_end_valid"] = True
        if payload.get("period_type"):
            sanity["period_type_valid"] = payload.get("period_type") in ("A", "H", "Q")
        record["sanity"] = sanity
    except Exception as exc:
        record["elapsed_s"] = round(time.monotonic() - started, 2)
        record["status"] = "exception"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()
    return record


def _error_taxonomy_key(error: Any) -> str:
    text = str(error or "failed_without_error")
    if text.startswith("validation_gate:source_noncandidate:"):
        return text.removeprefix("validation_gate:")
    if text.startswith("validation_gate:"):
        parts = text.split(":", 2)
        return ":".join(parts[:2])
    if text.startswith("classifier_low_confidence:"):
        return text
    if "timeout" in text.lower() or "sigalrm" in text.lower():
        return "timeout"
    return text.split(":", 1)[0] if ":" in text else text


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    status_distribution: dict[str, int] = {}
    failure_taxonomy: dict[str, int] = {}
    low_confidence_taxonomy: dict[str, int] = {}
    for row in results:
        status = row.get("status") or "unknown"
        status_distribution[status] = status_distribution.get(status, 0) + 1
        if status == "failed":
            label = _error_taxonomy_key(row.get("error"))
            failure_taxonomy[label] = failure_taxonomy.get(label, 0) + 1
        if status == "ok_low_confidence":
            label = str(row.get("error") or row.get("confidence") or "low_confidence")
            low_confidence_taxonomy[label] = low_confidence_taxonomy.get(label, 0) + 1
    elapsed = [row["elapsed_s"] for row in results if row.get("elapsed_s") is not None]
    timings: dict[str, Any] = {}
    if elapsed:
        ordered = sorted(elapsed)
        timings = {
            "total_s": round(sum(elapsed), 2),
            "mean_s": round(statistics.mean(elapsed), 2),
            "median_s": round(statistics.median(elapsed), 2),
            "min_s": round(min(elapsed), 2),
            "max_s": round(max(elapsed), 2),
            "p95_s": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 2),
        }
    return {
        "total": len(results),
        "status_distribution": status_distribution,
        "ok_count": status_distribution.get("ok", 0),
        "ok_low_confidence_count": status_distribution.get("ok_low_confidence", 0),
        "failed_count": status_distribution.get("failed", 0),
        "exception_count": status_distribution.get("exception", 0),
        "failure_taxonomy": failure_taxonomy,
        "low_confidence_taxonomy": low_confidence_taxonomy,
        "unsafe_row_check": {
            "negative_revenue": [
                row["document_id"]
                for row in results
                if row.get("metrics", {}).get("revenue") is not None
                and row["metrics"]["revenue"] <= 0
            ],
            "nonpositive_shares": [
                row["document_id"]
                for row in results
                if row.get("metrics", {}).get("shares_outstanding") is not None
                and row["metrics"]["shares_outstanding"] <= 0
            ],
        },
        "timing": timings,
    }


def _leading_date(title: str) -> str | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2})_", title)
    return match.group(1) if match else None


def _accepted_output_audit(results: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in results if row.get("status") in {"ok", "ok_low_confidence"}]
    audited: list[dict[str, Any]] = []
    unsafe: list[dict[str, Any]] = []
    data_missing: list[str] = []
    for row in accepted:
        leading = _leading_date(row.get("title") or "")
        metrics = row.get("metrics") or {}
        checks = {
            "source_class_allowed": row.get("document_class") in {"financial_report", "unknown_document"},
            "period_type_present": row.get("period_type") in {"A", "H", "Q"},
            "period_end_present": bool(row.get("period_end")),
            "scale_source_bound": row.get("scale") not in {None, "unknown"},
            "half_year_period_end_not_leading_announcement_date": not (
                row.get("period_type") == "H"
                and leading is not None
                and row.get("period_end") == leading
            ),
            "revenue_positive_if_present": metrics.get("revenue") is None or metrics.get("revenue") > 0,
            "shares_positive_if_present": metrics.get("shares_outstanding") is None
            or metrics.get("shares_outstanding") > 0,
            "row_refs_or_extraction_run_id_available": False,
        }
        risks = [name for name, passed in checks.items() if not passed]
        audit_row = {
            "document_id": row.get("document_id"),
            "ticker": row.get("ticker"),
            "title": row.get("title"),
            "source_path": row.get("pdf_path"),
            "status": row.get("status"),
            "metric_fields": [name for name, value in metrics.items() if value is not None],
            "metrics": metrics,
            "period_type": row.get("period_type"),
            "period_end": row.get("period_end"),
            "scale": row.get("scale"),
            "currency": row.get("currency"),
            "confidence": row.get("confidence"),
            "source_document_class": row.get("document_class"),
            "source_bound": row.get("source_bound"),
            "risk_notes": row.get("risk_notes") or [],
            "checks": checks,
            "risk": "unsafe" if any(r != "row_refs_or_extraction_run_id_available" for r in risks) else "done_with_risk",
            "risk_reasons": risks,
            "provenance_note": (
                "The runtime row shape does not expose page/table/row refs or extraction_run_id "
                "in this report-local runner output."
            ),
        }
        audited.append(audit_row)
        if audit_row["risk"] == "unsafe":
            unsafe.append(audit_row)
        if not checks["row_refs_or_extraction_run_id_available"]:
            data_missing.append(f"{row.get('document_id')}: row refs/extraction_run_id")
    return {
        "generated_at": _now(),
        "accepted_count": len(accepted),
        "unsafe_accepted_output_count": len(unsafe),
        "accepted_documents": audited,
        "unsafe_accepted_outputs": unsafe,
        "data_missing": data_missing,
        "summary": {
            "HUB_LBL_like_half_year_guard_unsafe_ids": [
                row["document_id"]
                for row in unsafe
                if "half_year_period_end_not_leading_announcement_date" in row["risk_reasons"]
            ],
            "negative_revenue_ids": [
                row["document_id"]
                for row in unsafe
                if "revenue_positive_if_present" in row["risk_reasons"]
            ],
            "nonpositive_shares_ids": [
                row["document_id"]
                for row in unsafe
                if "shares_positive_if_present" in row["risk_reasons"]
            ],
        },
    }


def _enrich_manifest(manifest: dict[str, Any], results: list[dict[str, Any]]) -> None:
    by_id = {row["document_id"]: row for row in results}
    taxonomy: dict[str, int] = {}
    for doc in manifest.get("selected_documents", []):
        row = by_id.get(doc.get("document_id"), {})
        classification = row.get("source_document_classification")
        source_class = (
            classification.get("document_class")
            if isinstance(classification, dict)
            else None
        )
        document_class = row.get("document_class") or source_class or "DATA_MISSING"
        doc.update(
            {
                "document_class": document_class,
                "source_document_class": source_class,
                "status": row.get("status"),
                "error": row.get("error"),
                "confidence": row.get("confidence"),
                "period_type": row.get("period_type"),
                "period_end": row.get("period_end"),
                "scale": row.get("scale"),
                "preflight_classifier_reason": classification,
            }
        )
        taxonomy[document_class] = taxonomy.get(document_class, 0) + 1
    manifest["document_class_taxonomy"] = taxonomy


def _compare_rows(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> bool:
    return before != after


def _build_side_effect_audit(
    before: dict[str, Any],
    after: dict[str, Any],
    manifest: dict[str, Any],
    final_report: dict[str, Any],
    accepted_audit: dict[str, Any],
) -> dict[str, Any]:
    before_qdrant = before["runtime"]["qdrant"]
    after_qdrant = after["runtime"]["qdrant"]
    db_changed = _compare_rows(before["sqlite"]["rows"], after["sqlite"]["rows"])
    qdrant_changed = before_qdrant != after_qdrant
    source_changed = (
        before["source_pdfs"]["fingerprint_sha256"]
        != after["source_pdfs"]["fingerprint_sha256"]
    )
    queues_clean = (
        after["runtime"]["redis_celery_length"] == 0
        and after["runtime"]["redis_unacked_key_count"] == 0
    )
    return {
        "generated_at": _now(),
        "sample_scope": {
            "exactly_one_bounded_count24_sample_run": True,
            "requested_count": manifest.get("requested_count"),
            "actual_count": manifest.get("actual_count"),
            "seed": manifest.get("seed"),
            "forbidden_count32_broad_extraction_or_backfill_observed": False,
        },
        "db_files": {
            "changed": db_changed,
            "before": before["sqlite"]["rows"],
            "after": after["sqlite"]["rows"],
            "note": "Sample uses sqlite:///:memory: with AUTO_CREATE_TABLES=false.",
        },
        "qdrant": {
            "changed": qdrant_changed,
            "before": before_qdrant,
            "after": after_qdrant,
            "note": "ENABLE_QDRANT=false for the sample; Qdrant was audited read-only.",
        },
        "risk_note": {
            "mutated": False,
            "note": "No risk-note persistence route was invoked; runtime risk_notes were read from report-local payloads only.",
        },
        "queues": {
            "before_celery_length": before["runtime"]["redis_celery_length"],
            "after_celery_length": after["runtime"]["redis_celery_length"],
            "before_unacked_key_count": before["runtime"]["redis_unacked_key_count"],
            "after_unacked_key_count": after["runtime"]["redis_unacked_key_count"],
            "post_clean": queues_clean,
            "after_queue_key_scan": after["runtime"]["redis_queue_key_scan"],
        },
        "news_memory": {
            "news_route_used": False,
            "news_qdrant_points_changed": before_qdrant.get("news_chunks")
            != after_qdrant.get("news_chunks"),
            "memory_mutated": False,
        },
        "source_pdfs": {
            "source_root": str(DOCS_ROOT),
            "before_fingerprint_sha256": before["source_pdfs"]["fingerprint_sha256"],
            "after_fingerprint_sha256": after["source_pdfs"]["fingerprint_sha256"],
            "before_count": before["source_pdfs"]["financial_performance_pdf_count"],
            "after_count": after["source_pdfs"]["financial_performance_pdf_count"],
            "changed": source_changed,
        },
        "git": {
            "before_status": before["repo"]["status_short"],
            "after_status": after["repo"]["status_short"],
            "unexpected_after_status_paths": after["repo"]["unexpected_status_paths"],
        },
        "unsafe_row_check": final_report["summary"]["unsafe_row_check"],
        "accepted_output_audit": {
            "unsafe_accepted_output_count": accepted_audit["unsafe_accepted_output_count"],
            "data_missing": accepted_audit["data_missing"],
        },
        "side_effect_anomalies": {
            "db_files_changed": db_changed,
            "qdrant_changed": qdrant_changed,
            "source_pdfs_changed": source_changed,
            "queues_not_clean_after_run": not queues_clean,
            "unexpected_git_paths": after["repo"]["unexpected_status_paths"],
        },
    }


def _write_readme(
    status: dict[str, Any],
    manifest: dict[str, Any] | None,
    accepted_audit: dict[str, Any] | None,
    side_effect_audit: dict[str, Any] | None,
) -> None:
    summary = status.get("sample_results") or {}
    manifest_lines = ""
    if manifest:
        manifest_lines = f"""
## Selected Document Manifest

- seed: {manifest["seed"]}
- requested_count: {manifest["requested_count"]}
- actual_count: {manifest["actual_count"]}
- candidate_pool_count: {manifest["candidate_pool_count"]}
- candidate_pool_ordered_sha256: `{manifest["candidate_pool_ordered_sha256"]}`
- candidate_pool_sorted_sha256: `{manifest["candidate_pool_sorted_sha256"]}`
- first16_overlap_with_post_pr301_count16: {manifest["first16_overlap_with_post_pr301_count16"]}
- first16_exact_order_match: {manifest["first16_exact_order_match"]}
- selected_document_ids_sha256: `{manifest["selected_document_ids_sha256"]}`
- selected_document_ids: `{", ".join(manifest["selected_document_ids"])}`
- new_documents_positions_17_24: `{", ".join(manifest["new_documents_positions_17_24"])}`
"""
    accepted_lines = ""
    if accepted_audit:
        accepted_lines = f"""
## Accepted-Output Audit

- accepted_count: {accepted_audit["accepted_count"]}
- unsafe_accepted_output_count: {accepted_audit["unsafe_accepted_output_count"]}
- data_missing_count: {len(accepted_audit["data_missing"])}
- HUB/LBL-like half-year guard unsafe IDs: `{", ".join(accepted_audit["summary"]["HUB_LBL_like_half_year_guard_unsafe_ids"])}`
"""
    side_effect_lines = ""
    if side_effect_audit:
        side_effect_lines = f"""
## Side-Effect Audit

- DB files changed: {side_effect_audit["db_files"]["changed"]}
- Qdrant changed: {side_effect_audit["qdrant"]["changed"]}
- Risk-note mutated: {side_effect_audit["risk_note"]["mutated"]}
- News route used: {side_effect_audit["news_memory"]["news_route_used"]}
- Memory mutated: {side_effect_audit["news_memory"]["memory_mutated"]}
- Source PDFs changed: {side_effect_audit["source_pdfs"]["changed"]}
- Queues clean after run: {side_effect_audit["queues"]["post_clean"]}
"""
    readme = f"""# Count-24 Bounded Extraction Validation

Generated: {status["generated_at"]}

State: `{status["status"]}`.

Scope: exactly one bounded count-24 validation target on canonical
`{APPROVED_HEAD}`. No count-32, no broad extraction, no backfill, and no full
ticker-universe extraction.

## Result

- sample_completed: {status.get("sample_completed")}
- ok: {summary.get("ok_count", 0)}
- ok_low_confidence: {summary.get("ok_low_confidence_count", 0)}
- failed: {summary.get("failed_count", 0)}
- exceptions: {summary.get("exception_count", 0)}
- failure_taxonomy: `{json.dumps(summary.get("failure_taxonomy", {}), sort_keys=True)}`
- low_confidence_taxonomy: `{json.dumps(summary.get("low_confidence_taxonomy", {}), sort_keys=True)}`
- count24_verdict: `{status.get("count24_verdict")}`
- count32_decision: `{status.get("count32_decision")}`
{manifest_lines}
{accepted_lines}
{side_effect_lines}
## DATA_MISSING / Blockers

{chr(10).join(f"- {item}" for item in status.get("data_missing", [])) or "- none"}

## Unsafe Actions Avoided

- count-32 not run
- broad extraction not run
- backfill not run
- full ticker-universe extraction not run
- DB/Qdrant/news/memory/source-PDF/prompt/gold-label/runtime/schema/model/GPU mutation not run

## Next Recommended Prompt

{status.get("next_recommended_prompt")}
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def _blocked_status(
    reason: str,
    preflight_failures: list[str],
    manifest_failures: list[str],
    data_missing: list[str],
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    status = {
        "generated_at": _now(),
        "status": reason,
        "sample_completed": False,
        "sample_results": {},
        "preflight_failures": preflight_failures,
        "manifest_failures": manifest_failures,
        "data_missing": data_missing,
        "count24_verdict": "COUNT24_BLOCKED_BEFORE_EXTRACTION",
        "count32_decision": "blocked; count-32 requires a separate approval packet after a valid count-24",
        "explicit_scope_statement": (
            "No count-24 extraction rows were processed; no count-32, broad extraction, "
            "backfill, or full ticker-universe extraction was run."
        ),
        "next_recommended_prompt": (
            "Refresh the failed preflight gate only, then rerun the same count-24 task "
            "if and only if the operator approves the remaining DATA_MISSING or the gate is clean."
        ),
    }
    _write_json(OUTPUT_DIR / "status.json", status)
    _write_readme(status, manifest, None, None)
    print(json.dumps(status, indent=2, sort_keys=True), file=sys.stderr)
    return status


def main() -> int:
    for key, value in SAFE_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    before_state = _collect_state()
    preflight_failures = _readiness_failures(before_state)

    harness = _load_harness()
    manifest, sample, pool_paths, _first16_reference = _build_manifest(harness)
    source = before_state.get("source_pdfs") or {}
    manifest["source_pdf_count"] = source.get("financial_performance_pdf_count")
    manifest["source_pdf_fingerprint_sha256"] = source.get("fingerprint_sha256")
    _write_json(OUTPUT_DIR / "sample_manifest.json", manifest)
    manifest_failures = _manifest_failures(manifest)

    preflight = {
        "generated_at": _now(),
        "mode": "OPERATOR-APPROVED BOUNDED VALIDATION ONLY",
        "primary_lane": "Evaluation",
        "supporting_lanes": ["Financial Truth", "Query Orchestration", "Provenance"],
        "approved_head": APPROVED_HEAD,
        "loaded_commit_proof": before_state["repo"]["loaded_code_proof"],
        "readiness_failures": preflight_failures,
        "manifest_failures": manifest_failures,
        "state_before_run": before_state,
        "candidate_pool_generation": {
            "command": "import broad_extraction_test.py; set DOCS_ROOT; discover_pdfs(); hash relative paths",
            "candidate_pool_count": manifest["candidate_pool_count"],
            "candidate_pool_ordered_sha256": manifest["candidate_pool_ordered_sha256"],
            "candidate_pool_sorted_sha256": manifest["candidate_pool_sorted_sha256"],
            "pool_path_count": len(pool_paths),
        },
        "explicit_scope_statement": (
            "Preflight for exactly one bounded count-24 sample; no count-32, broad "
            "extraction, backfill, or full ticker-universe extraction."
        ),
    }
    _write_json(OUTPUT_DIR / "preflight.json", preflight)

    data_missing: list[str] = []
    if before_state["runtime"]["gpu_telemetry_equivalent"]["query"]["exit_code"] != 0:
        data_missing.append("Reliable active-GPU telemetry: nvidia-smi -i 1 failed.")
    if before_state["registry"]["list_active"]["exit_code"] != 0:
        data_missing.append("Safe read-only registry command failed.")
    if manifest_failures:
        data_missing.append("Count-24 comparability blocked by candidate pool or sample identity drift.")
    if preflight_failures or manifest_failures:
        _blocked_status(
            "blocked_before_count24_extraction",
            preflight_failures,
            manifest_failures,
            data_missing,
            manifest,
        )
        return 2

    llm_client = _make_llm_client()
    results: list[dict[str, Any]] = []
    for idx, path in enumerate(sample, start=1):
        if idx > COUNT:
            raise RuntimeError("runner attempted to process more than 24 documents")
        print(f"[{idx}/{len(sample)}] {_ticker_from_path(path)}/{path.name}", flush=True)
        row = _run_one(path, llm_client)
        results.append(row)
        print(
            "  -> "
            f"{row['status']} elapsed={row['elapsed_s']} "
            f"metrics={row['non_null_metrics']}/10 error={row['error']}",
            flush=True,
        )
        partial_report = {
            "run_metadata": {
                "timestamp": _now(),
                "seed": SEED,
                "requested_count": COUNT,
                "actual_count": len(results),
                "backend": "llamacpp",
                "docs_root": str(DOCS_ROOT),
            },
            "summary": _summary(results),
            "results": results,
        }
        _write_json(OUTPUT_DIR / "sample_results.json", partial_report)

    _enrich_manifest(manifest, results)
    final_report = {
        "run_metadata": {
            "timestamp": _now(),
            "seed": SEED,
            "requested_count": COUNT,
            "actual_count": len(results),
            "backend": "llamacpp",
            "docs_root": str(DOCS_ROOT),
        },
        "summary": _summary(results),
        "results": results,
    }
    classifications = [
        {
            "document_id": row["document_id"],
            "ticker": row["ticker"],
            "title": row["title"],
            "status": row["status"],
            "error": row["error"],
            "document_class": row.get("document_class") or "DATA_MISSING",
            "source_document_classification": row.get("source_document_classification"),
            "period_type": row.get("period_type"),
            "period_end": row.get("period_end"),
            "scale": row.get("scale"),
            "confidence": row.get("confidence"),
            "pdf_path": row.get("pdf_path"),
        }
        for row in results
    ]
    failure_taxonomy = final_report["summary"]["failure_taxonomy"]
    low_confidence_taxonomy = final_report["summary"]["low_confidence_taxonomy"]
    accepted_audit = _accepted_output_audit(results)
    _write_json(OUTPUT_DIR / "sample_manifest.json", manifest)
    _write_json(OUTPUT_DIR / "sample_results.json", final_report)
    _write_json(OUTPUT_DIR / "classification.json", {"classifications": classifications})
    _write_json(OUTPUT_DIR / "failure_taxonomy.json", failure_taxonomy)
    _write_json(OUTPUT_DIR / "low_confidence_taxonomy.json", low_confidence_taxonomy)
    _write_json(OUTPUT_DIR / "accepted_output_audit.json", accepted_audit)

    after_state = _collect_state()
    side_effect_audit = _build_side_effect_audit(
        before_state,
        after_state,
        manifest,
        final_report,
        accepted_audit,
    )
    _write_json(OUTPUT_DIR / "side_effect_audit.json", side_effect_audit)

    side_effect_anomaly = any(
        value
        for value in side_effect_audit["side_effect_anomalies"].values()
        if value not in ([], False)
    )
    summary = final_report["summary"]
    if summary["exception_count"]:
        verdict = "COUNT24_FAILED_EXCEPTIONS"
    elif side_effect_anomaly:
        verdict = "COUNT24_FAILED_SIDE_EFFECT_ANOMALY"
    elif accepted_audit["unsafe_accepted_output_count"]:
        verdict = "COUNT24_FAILED_UNSAFE_ACCEPTED_OUTPUT"
    elif summary["ok_count"] + summary["ok_low_confidence_count"] >= 12:
        verdict = "COUNT24_SUCCESS_WITH_RISK"
    else:
        verdict = "COUNT24_FAILED_LOW_ACCEPTED_COUNT"

    status = {
        "generated_at": _now(),
        "status": "completed_bounded_count24_validation",
        "mode": "OPERATOR-APPROVED BOUNDED VALIDATION ONLY",
        "repo_head": after_state["repo"]["head"],
        "sample_completed": True,
        "sample_results": summary,
        "document_class_taxonomy": manifest.get("document_class_taxonomy"),
        "run_metadata": final_report["run_metadata"],
        "side_effect_summary": {
            "db_files_changed": side_effect_audit["db_files"]["changed"],
            "qdrant_changed": side_effect_audit["qdrant"]["changed"],
            "risk_note_mutated": side_effect_audit["risk_note"]["mutated"],
            "news_route_used": side_effect_audit["news_memory"]["news_route_used"],
            "memory_mutated": side_effect_audit["news_memory"]["memory_mutated"],
            "queues_clean_after_run": side_effect_audit["queues"]["post_clean"],
            "source_pdfs_changed": side_effect_audit["source_pdfs"]["changed"],
        },
        "accepted_output_audit": {
            "accepted_count": accepted_audit["accepted_count"],
            "unsafe_accepted_output_count": accepted_audit["unsafe_accepted_output_count"],
            "data_missing_count": len(accepted_audit["data_missing"]),
        },
        "count24_verdict": verdict,
        "count32_decision": (
            "blocked; count-32 requires a separate approval packet"
            if verdict != "COUNT24_SUCCESS_WITH_RISK"
            else "not authorized; requires a separate approval packet after operator review"
        ),
        "data_missing": accepted_audit["data_missing"],
        "explicit_scope_statement": (
            "Ran exactly one bounded count-24 direct extraction validation sample; "
            "no count-32, no broad extraction, no backfill, no full ticker-universe extraction."
        ),
        "next_recommended_prompt": (
            "Review the count-24 accepted-output audit and failure taxonomy; create a separate "
            "approval packet before any count-32 or containment mutation."
        ),
    }
    _write_json(OUTPUT_DIR / "status.json", status)
    _write_readme(status, manifest, accepted_audit, side_effect_audit)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if verdict == "COUNT24_SUCCESS_WITH_RISK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
