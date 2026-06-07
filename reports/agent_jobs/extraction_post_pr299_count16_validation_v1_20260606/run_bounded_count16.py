#!/usr/bin/env python3
"""Report-local bounded count-16 runner for post-PR #299 validation."""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import random
import statistics
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Any


JOB_ID = "extraction_post_pr299_count16_validation_v1_20260606"
REPO_ROOT = Path(__file__).resolve().parents[3]
FE_ROOT = REPO_ROOT / "financial-engine_v2"
DOCS_ROOT = Path(os.environ.get("DOCS_ROOT", "/data/asx/docs")).resolve()
OUTPUT_DIR = Path(__file__).resolve().parent
SEED = int(os.environ.get("COUNT16_SEED", "20260602"))
COUNT = 16
PR299_COMMIT = "9436d1d32de0da5423b8edcfc7efc883ccac3fd6"
PHASE1_COMMIT = "9c9107bbbbac6a2971b57d9df5473aa870bb4b28"
PRIOR_POST_PR297_MANIFEST = Path(
    "/home/l4nd0/tenn-post-pr297-count16-validation-v1-20260605/"
    "reports/agent_jobs/extraction_post_pr297_count16_validation_v1_20260605/"
    "sample_manifest.json"
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


def _load_harness():
    path = FE_ROOT / "scripts" / "broad_extraction_test.py"
    spec = importlib.util.spec_from_file_location("post_pr299_broad_extraction_test", path)
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


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_prior_manifest() -> dict[str, Any] | None:
    if not PRIOR_POST_PR297_MANIFEST.exists():
        return None
    return json.loads(PRIOR_POST_PR297_MANIFEST.read_text(encoding="utf-8"))


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
        timeout=180,
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
        "/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/data/ops/ops.db",
        "/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/data/cockpit/state.db",
    ]
    quoted = " ".join(paths)
    stat_result = _run(f"stat -c '%n\\t%s\\t%Y\\t%y' {quoted}", timeout=30)
    rows: list[dict[str, Any]] = []
    for line in stat_result["stdout"].splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            parts = line.split("\\t", 3)
        if len(parts) == 4:
            rows.append(
                {
                    "path": parts[0],
                    "size": int(parts[1]),
                    "mtime_epoch": int(parts[2]),
                    "mtime": parts[3],
                }
            )
    return {"rows": rows, "command": stat_result}


def _collect_state() -> dict[str, Any]:
    redis_celery = _run("redis-cli llen celery", timeout=30)
    redis_unacked_count = _run("redis-cli --scan --pattern '*unacked*' | wc -l", timeout=30)
    redis_queue_keys = _run(
        "redis-cli --scan | rg -i '(unacked|queue|rq|celery)'",
        timeout=30,
    )
    gpu_guard = _run("scripts/gpu_process_guard.sh --check", timeout=60)
    nvidia = _run("nvidia-smi", timeout=30)
    processes = _run(
        "ps -eo pid,ppid,stat,comm,args | "
        "rg '(^| )[l]lama-server|(^| )[u]vicorn|(^| )[c]elery|(^| )[r]q|(^| )[d]ramatiq'",
        timeout=30,
    )
    registry = _run("python3 scripts/agent_job_registry.py list-active --repo-root .", timeout=30)
    registry_json: Any
    try:
        registry_json = json.loads(registry["stdout"]) if registry["stdout"].startswith("{") else None
    except json.JSONDecodeError:
        registry_json = None
    return {
        "generated_at": _now(),
        "repo": {
            "worktree": str(REPO_ROOT),
            "branch": _run("git branch --show-current")["stdout"],
            "head": _run("git rev-parse HEAD")["stdout"],
            "head_contains_pr299": _run(
                f"git merge-base --is-ancestor {PR299_COMMIT} HEAD; printf '%s' $?"
            )["stdout"]
            == "0",
            "head_contains_phase1": _run(
                f"git merge-base --is-ancestor {PHASE1_COMMIT} HEAD; printf '%s' $?"
            )["stdout"]
            == "0",
            "status_short": _run("git status --short --untracked-files=all")[
                "stdout"
            ].splitlines(),
        },
        "registry": {
            "command": registry,
            "parsed": registry_json,
            "active_jobs": registry_json.get("active_jobs")
            if isinstance(registry_json, dict)
            else "DATA_MISSING",
            "read_only": registry_json.get("read_only")
            if isinstance(registry_json, dict)
            else "DATA_MISSING",
            "lock_acquired": registry_json.get("lock_acquired")
            if isinstance(registry_json, dict)
            else "DATA_MISSING",
        },
        "runtime": {
            "backend_health": _json_http("http://127.0.0.1:8000/api/health"),
            "llamacpp_models": _json_http("http://127.0.0.1:8001/v1/models"),
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
                "stdout_first_lines": nvidia["stdout"].splitlines()[:20],
                "stderr_first_lines": nvidia["stderr"].splitlines()[:20],
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
    if not repo["head_contains_pr299"]:
        failures.append("HEAD does not contain PR299 merge commit")
    if not repo["head_contains_phase1"]:
        failures.append("HEAD does not contain Phase 1 taxonomy repair commit")
    if int(source_pdfs.get("financial_performance_pdf_count") or 0) < COUNT:
        failures.append("source financial_performance PDF count is below sample count")
    if runtime.get("redis_celery_length") != 0:
        failures.append("redis celery queue is not empty")
    if runtime.get("redis_unacked_key_count") != 0:
        failures.append("redis unacked key count is not zero")
    if runtime["gpu_process_guard"]["exit_code"] != 0:
        failures.append("gpu_process_guard failed")
    if isinstance(registry.get("active_jobs"), list) and registry["active_jobs"]:
        failures.append("registry has active jobs")
    if isinstance(runtime.get("llamacpp_models"), dict) and runtime["llamacpp_models"].get("error"):
        failures.append("llama.cpp /v1/models is not reachable")
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
    except Exception as exc:  # pragma: no cover - runtime artifact path
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


def _build_manifest(sample: list[Path], pool_paths: list[str]) -> dict[str, Any]:
    prior = _load_prior_manifest()
    selected_ids = [_doc_id_from_path(path) for path in sample]
    comparability: dict[str, Any]
    if prior is None:
        comparability = {
            "assessment": "DATA_MISSING: prior post-PR297 manifest was not found",
            "prior_manifest_path": str(PRIOR_POST_PR297_MANIFEST),
        }
    else:
        prior_ids = set(prior.get("selected_document_ids") or [])
        selected_set = set(selected_ids)
        same_pool = (
            prior.get("candidate_pool_ordered_sha256") == _hash_json(pool_paths)
            and prior.get("candidate_pool_sorted_sha256") == _hash_json(sorted(pool_paths))
        )
        comparability = {
            "assessment": "FULL_AGAINST_POST_PR297_SAMPLE"
            if same_pool and len(selected_set & prior_ids) == len(selected_ids)
            else "PARTIAL_AGAINST_POST_PR297_SAMPLE",
            "prior_manifest_path": str(PRIOR_POST_PR297_MANIFEST),
            "prior_seed": prior.get("seed"),
            "same_seed": prior.get("seed") == SEED,
            "same_candidate_pool_hashes": same_pool,
            "selected_overlap_count": len(selected_set & prior_ids),
            "selected_overlap_ids": sorted(selected_set & prior_ids),
            "prior_selected_document_ids": prior.get("selected_document_ids"),
        }
    return {
        "generated_at": _now(),
        "seed": SEED,
        "requested_count": COUNT,
        "actual_count": len(sample),
        "docs_root": str(DOCS_ROOT),
        "candidate_pool_count": len(pool_paths),
        "candidate_pool_ordered_sha256": _hash_json(pool_paths),
        "candidate_pool_sorted_sha256": _hash_json(sorted(pool_paths)),
        "selected_document_ids": selected_ids,
        "selected_documents": [
            {
                "index": idx + 1,
                "ticker": _ticker_from_path(path),
                "document_id": _doc_id_from_path(path),
                "pdf_path": _rel(path),
                "title": path.name,
            }
            for idx, path in enumerate(sample)
        ],
        "comparability_to_post_pr297_count16": comparability,
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
            }
        )
        taxonomy[document_class] = taxonomy.get(document_class, 0) + 1
    manifest["document_class_taxonomy"] = taxonomy


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_readme(
    manifest: dict[str, Any],
    final_report: dict[str, Any],
    side_effect_audit: dict[str, Any],
    status: dict[str, Any],
) -> None:
    summary = final_report["summary"]
    readme = f"""# Post-PR299 Count-16 Extraction Validation

Generated: {status["generated_at"]}

Scope: exactly one bounded count-16 sample on HEAD
`{status["repo_head"]}`. No broad extraction, no backfill, no count-24/count-32,
and no full ticker-universe extraction.

## Result

- ok: {summary["ok_count"]}
- ok_low_confidence: {summary["ok_low_confidence_count"]}
- failed: {summary["failed_count"]}
- exception_count: {summary["exception_count"]}
- failure_taxonomy: `{json.dumps(summary["failure_taxonomy"], sort_keys=True)}`
- low_confidence_taxonomy: `{json.dumps(summary["low_confidence_taxonomy"], sort_keys=True)}`
- unsafe_row_check: `{json.dumps(summary["unsafe_row_check"], sort_keys=True)}`

## Manifest

- seed: {manifest["seed"]}
- candidate_pool_count: {manifest["candidate_pool_count"]}
- candidate_pool_ordered_sha256: `{manifest["candidate_pool_ordered_sha256"]}`
- candidate_pool_sorted_sha256: `{manifest["candidate_pool_sorted_sha256"]}`
- selected_document_ids: `{", ".join(manifest["selected_document_ids"])}`
- document_class_taxonomy: `{json.dumps(manifest.get("document_class_taxonomy", {}), sort_keys=True)}`
- post-PR297 comparability: `{manifest["comparability_to_post_pr297_count16"]["assessment"]}`

## Side Effects

- DB files changed: {side_effect_audit["db_files"]["changed"]}
- Qdrant changed: {side_effect_audit["qdrant"]["changed"]}
- Queues clean after run: {side_effect_audit["queues"]["post_clean"]}
- News route used: false
- Memory mutated: false
- Source PDFs changed: {side_effect_audit["source_pdfs"]["changed"]}

## Count-24 Decision

Count-24 is not authorized by this report. See `status.json` for the
recommendation reason.

## DATA_MISSING

{chr(10).join(f"- {item}" for item in status["data_missing"])}
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def _compare_rows(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> bool:
    return before != after


def _build_side_effect_audit(
    before: dict[str, Any],
    after: dict[str, Any],
    manifest: dict[str, Any],
    final_report: dict[str, Any],
) -> dict[str, Any]:
    before_qdrant = before["runtime"]["qdrant"]
    after_qdrant = after["runtime"]["qdrant"]
    return {
        "generated_at": _now(),
        "sample_scope": {
            "exactly_one_bounded_count16_sample_run": True,
            "requested_count": manifest.get("requested_count"),
            "actual_count": manifest.get("actual_count"),
            "seed": manifest.get("seed"),
            "forbidden_broad_extraction_or_backfill_observed": False,
        },
        "db_files": {
            "changed": _compare_rows(before["sqlite"]["rows"], after["sqlite"]["rows"]),
            "before": before["sqlite"]["rows"],
            "after": after["sqlite"]["rows"],
            "note": (
                "Sample uses sqlite:///:memory: with AUTO_CREATE_TABLES=false; "
                "DB file stats are audited for unexpected side effects."
            ),
        },
        "qdrant": {
            "changed": before_qdrant != after_qdrant,
            "before": before_qdrant,
            "after": after_qdrant,
            "note": "ENABLE_QDRANT=false for the sample; Qdrant was audited read-only.",
        },
        "queues": {
            "before_celery_length": before["runtime"]["redis_celery_length"],
            "after_celery_length": after["runtime"]["redis_celery_length"],
            "before_unacked_key_count": before["runtime"]["redis_unacked_key_count"],
            "after_unacked_key_count": after["runtime"]["redis_unacked_key_count"],
            "post_clean": after["runtime"]["redis_celery_length"] == 0
            and after["runtime"]["redis_unacked_key_count"] == 0,
            "after_queue_key_scan": after["runtime"]["redis_queue_key_scan"],
        },
        "news_memory": {
            "news_route_used": False,
            "news_qdrant_points_changed": before_qdrant.get("news_chunks")
            != after_qdrant.get("news_chunks"),
            "memory_mutated": False,
            "note": "No memory or news write path was invoked by the runner.",
        },
        "source_pdfs": {
            "source_root": str(DOCS_ROOT),
            "before_fingerprint_sha256": before["source_pdfs"]["fingerprint_sha256"],
            "after_fingerprint_sha256": after["source_pdfs"]["fingerprint_sha256"],
            "before_count": before["source_pdfs"]["financial_performance_pdf_count"],
            "after_count": after["source_pdfs"]["financial_performance_pdf_count"],
            "changed": before["source_pdfs"]["fingerprint_sha256"]
            != after["source_pdfs"]["fingerprint_sha256"],
        },
        "unsafe_row_check": final_report["summary"]["unsafe_row_check"],
    }


def main() -> int:
    for key, value in SAFE_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    before_state = _collect_state()
    readiness_failures = _readiness_failures(before_state)
    preflight = {
        "generated_at": _now(),
        "mode": "BOUNDED VALIDATION ONLY",
        "primary_lane": "Evaluation",
        "supporting_lanes": ["Financial Truth", "Query Orchestration", "Provenance"],
        "readiness_failures": readiness_failures,
        "state_before_run": before_state,
        "explicit_scope_statement": (
            "Preflight for exactly one bounded count-16 sample; no broad "
            "extraction, backfill, count-24/count-32, or full ticker extraction."
        ),
    }
    _write_json(OUTPUT_DIR / "preflight.json", preflight)
    if readiness_failures:
        status = {
            "generated_at": _now(),
            "status": "blocked_by_runtime_preflight",
            "readiness_failures": readiness_failures,
            "sample_completed": False,
            "data_missing": [],
        }
        _write_json(OUTPUT_DIR / "status.json", status)
        print(json.dumps(status, indent=2, sort_keys=True), file=sys.stderr)
        return 2

    harness = _load_harness()
    all_pdfs = harness.discover_pdfs()
    pool_paths = [_rel(path) for path in all_pdfs]
    sample = random.Random(SEED).sample(all_pdfs, min(COUNT, len(all_pdfs)))
    manifest = _build_manifest(sample, pool_paths)
    _write_json(OUTPUT_DIR / "sample_manifest.json", manifest)

    llm_client = _make_llm_client()
    results: list[dict[str, Any]] = []
    for idx, path in enumerate(sample, start=1):
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
    _write_json(OUTPUT_DIR / "sample_manifest.json", manifest)
    _write_json(OUTPUT_DIR / "sample_results.json", final_report)
    _write_json(OUTPUT_DIR / "classification.json", {"classifications": classifications})

    after_state = _collect_state()
    side_effect_audit = _build_side_effect_audit(
        before_state,
        after_state,
        manifest,
        final_report,
    )
    _write_json(OUTPUT_DIR / "side_effect_audit.json", side_effect_audit)

    data_missing: list[str] = []
    if before_state["runtime"]["nvidia_smi"]["exit_code"] != 0:
        data_missing.append("Reliable GPU memory telemetry: nvidia-smi failed.")
    if before_state["registry"]["read_only"] is not True:
        data_missing.append(
            "Safe read-only registry proof: local list-active command used read_only=false."
        )
    if manifest["comparability_to_post_pr297_count16"]["assessment"].startswith("PARTIAL"):
        data_missing.append("Full post-PR297 comparability is incomplete.")

    failed = final_report["summary"]["failed_count"]
    low_conf = final_report["summary"]["ok_low_confidence_count"]
    unsafe = final_report["summary"]["unsafe_row_check"]
    if unsafe["negative_revenue"] or unsafe["nonpositive_shares"]:
        recommendation = {
            "decision": "NEEDS_ACCEPTED_OUTPUT_AUDIT",
            "reason": "Unsafe accepted-row checks found nonpositive canonical values.",
        }
    elif failed:
        recommendation = {
            "decision": "NEEDS_FAILURE_TAXONOMY",
            "reason": "Failed rows remain after the bounded count-16 sample.",
        }
    elif low_conf:
        recommendation = {
            "decision": "NEEDS_LOW_CONFIDENCE_AUDIT",
            "reason": "No hard failures, but ok_low_confidence rows remain.",
        }
    else:
        recommendation = {
            "decision": "READY_FOR_COUNT24_APPROVAL_PACKET",
            "reason": "No failures, suspicious low-confidence rows, or unsafe accepted rows.",
        }

    status = {
        "generated_at": _now(),
        "status": "completed_bounded_validation_sample",
        "mode": "BOUNDED VALIDATION ONLY",
        "repo_head": after_state["repo"]["head"],
        "sample_completed": True,
        "sample_results": final_report["summary"],
        "document_class_taxonomy": manifest.get("document_class_taxonomy"),
        "run_metadata": final_report["run_metadata"],
        "side_effect_summary": {
            "db_files_changed": side_effect_audit["db_files"]["changed"],
            "qdrant_changed": side_effect_audit["qdrant"]["changed"],
            "queues_clean_after_run": side_effect_audit["queues"]["post_clean"],
            "source_pdfs_changed": side_effect_audit["source_pdfs"]["changed"],
        },
        "count24_recommendation": {
            "justified": recommendation["decision"] == "READY_FOR_COUNT24_APPROVAL_PACKET",
            "reason": recommendation["reason"],
        },
        "next_phase_recommendation": recommendation,
        "data_missing": data_missing,
        "explicit_scope_statement": (
            "Ran exactly one bounded count-16 direct extraction validation sample; "
            "no broad extraction, no backfill, no count-24/count-32, no full "
            "ticker-universe extraction."
        ),
    }
    _write_json(OUTPUT_DIR / "status.json", status)
    _write_readme(manifest, final_report, side_effect_audit, status)
    print(json.dumps(final_report["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
