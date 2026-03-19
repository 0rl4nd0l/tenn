from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import PROJECT_ROOT, settings
from app.services import router_metrics, router_optimizer
from app.services.router import load_model_routing_config


DATA_MISSING = "DATA_MISSING"
UNVERIFIED = "Unverified"
DEFAULT_LOOP_MODE = "recommend"
ALLOWED_LOOP_MODES = ("recommend", "prepare_patch", "apply_gated")
DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CHECK_TIMEOUT_SECONDS = 5.0
DEFAULT_WATCHDOG_SECONDS = 45.0
DEFAULT_BENCHMARK_MAX_AGE_HOURS = 168.0
MIN_METRICS_SAMPLE_SIZE = int(getattr(router_optimizer, "MIN_DEGRADATION_SAMPLE_SIZE", 5.0) or 5)
CANONICAL_DATA_ROOT = Path("/data")
ARTIFACT_ROOT = CANONICAL_DATA_ROOT / "reports" / "system_analyzer"
PATCH_ROOT = ARTIFACT_ROOT / "patch_candidates"
EXPECTED_BENCHMARK_PATH = CANONICAL_DATA_ROOT / "reports" / "model_benchmark.json"
LEGACY_BENCHMARK_PATH = PROJECT_ROOT / "reports" / "model_benchmark.json"
SOURCE_SCAN_PATHS = (
    PROJECT_ROOT / "backend" / "app" / "main.py",
    PROJECT_ROOT / "backend" / "app" / "services" / "router_metrics.py",
    PROJECT_ROOT / "backend" / "app" / "services" / "router_optimizer.py",
    PROJECT_ROOT / "backend" / "app" / "services" / "rag.py",
    PROJECT_ROOT / "backend" / "app" / "services" / "llm.py",
    PROJECT_ROOT / "scripts" / "benchmark_models.py",
    PROJECT_ROOT.parent / "docs" / "architecture" / "model-routing.md",
    PROJECT_ROOT.parent / "docs" / "architecture" / "07_rag_contract.md",
    PROJECT_ROOT.parent / "docs" / "ops" / "system_functionality_limits.md",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def validate_artifact_path(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        raise ValueError("Analyzer artifact paths must be absolute and rooted under the data root.")
    allowed_root = CANONICAL_DATA_ROOT.resolve()
    resolved_root = resolved.resolve()
    resolved_root.relative_to(allowed_root)
    return resolved


def build_artifact_paths(run_id: str) -> dict[str, str]:
    safe_run_id = str(run_id or "").strip() or "run"
    paths = {
        "latest_report": str(validate_artifact_path(ARTIFACT_ROOT / "latest.json")),
        "history_report": str(validate_artifact_path(ARTIFACT_ROOT / f"{safe_run_id}.json")),
        "patch_candidate": str(validate_artifact_path(PATCH_ROOT / f"{safe_run_id}.json")),
    }
    return paths


def _write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    resolved = validate_artifact_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    handle = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(resolved.parent),
        suffix=".tmp",
    )
    temp_path = Path(handle.name)
    try:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        temp_path.replace(resolved)
    finally:
        if not handle.closed:
            handle.close()
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _read_json(path: str | Path) -> dict[str, Any] | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_source_map() -> dict[str, str]:
    return {str(path.relative_to(PROJECT_ROOT.parent)): _read_text(path) for path in SOURCE_SCAN_PATHS}


def _run_check(
    name: str,
    check_fn: Callable[[], dict[str, Any]],
    *,
    timeout_seconds: float,
    deadline: float,
) -> dict[str, Any]:
    if monotonic() >= deadline:
        return {
            "name": name,
            "result": "failed",
            "severity": "high",
            "details": "watchdog exceeded before check execution",
        }

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(check_fn)
        remaining = max(0.0, min(timeout_seconds, deadline - monotonic()))
        try:
            payload = future.result(timeout=remaining)
        except FutureTimeoutError:
            return {
                "name": name,
                "result": "failed",
                "severity": "high",
                "details": f"check timeout after {remaining:.2f}s",
            }
        except Exception as exc:
            return {
                "name": name,
                "result": "failed",
                "severity": "high",
                "details": str(exc),
            }

    result = dict(payload or {})
    result.setdefault("name", name)
    result.setdefault("result", UNVERIFIED)
    result.setdefault("severity", "medium")
    result.setdefault("details", "")
    return result


def _normalize_base_url(raw: str) -> str:
    return str(raw or "").strip().rstrip("/")


def _strip_v1(raw: str) -> str:
    normalized = _normalize_base_url(raw)
    return normalized[:-3] if normalized.endswith("/v1") else normalized


def _http_json(
    url: str,
    *,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
) -> tuple[str, Any]:
    request = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(str(exc)) from exc
    return "passed", payload


def _backend_headers() -> dict[str, str]:
    configured_key = str(getattr(settings, "local_api_key", "") or "").strip()
    if not configured_key:
        return {}
    return {"X-API-Key": configured_key}


def _parse_generated_at(payload: dict[str, Any] | None) -> datetime | None:
    if not isinstance(payload, dict):
        return None
    text = str(payload.get("generated_at") or "").strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _hours_since(timestamp: datetime | None) -> float | str:
    if timestamp is None:
        return DATA_MISSING
    return max((_utc_now() - timestamp).total_seconds() / 3600.0, 0.0)


def _benchmark_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload is None:
        return {
            "path": str(path),
            "present": False,
            "freshness_hours": DATA_MISSING,
            "complete": False,
            "roles_present": [],
        }
    models = payload.get("models") if isinstance(payload, dict) else None
    roles_present: set[str] = set()
    if isinstance(models, dict):
        for metrics in models.values():
            if isinstance(metrics, dict):
                roles_present.update(str(role) for role in (metrics.get("roles") or []) if str(role).strip())
    generated_at = _parse_generated_at(payload)
    required_roles = {"router", "coding", "reasoning", "deep_reasoning"}
    return {
        "path": str(path),
        "present": True,
        "freshness_hours": _hours_since(generated_at),
        "complete": required_roles.issubset(roles_present),
        "roles_present": sorted(roles_present),
        "generated_at": generated_at.isoformat() if generated_at is not None else DATA_MISSING,
        "payload": payload,
    }


def _benchmark_report_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime_report = snapshot.get("benchmark_runtime")
    if isinstance(runtime_report, dict) and runtime_report.get("present"):
        payload = runtime_report.get("payload")
        if isinstance(payload, dict):
            return payload
    return {}


def _metrics_snapshot() -> dict[str, dict[str, Any]]:
    try:
        return router_metrics.load_metrics_snapshot()
    except Exception:
        return {}


def _docker_status(timeout_seconds: float) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return {"result": UNVERIFIED, "entries": DATA_MISSING}
    if result.returncode != 0:
        return {"result": UNVERIFIED, "entries": DATA_MISSING}
    entries = []
    for line in str(result.stdout or "").splitlines():
        name, _, status = line.partition("\t")
        entries.append({"name": name.strip(), "status": status.strip()})
    return {"result": "passed", "entries": entries}


def _gpu_probe(timeout_seconds: float) -> dict[str, Any]:
    command = str(getattr(settings, "gpu_utilization_command", "") or "").strip()
    if not command:
        return {"result": UNVERIFIED, "details": "gpu_utilization_command missing"}
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return {"result": UNVERIFIED, "details": "GPU probe unavailable"}
    if result.returncode != 0:
        return {"result": UNVERIFIED, "details": "GPU probe returned non-zero"}
    values = [line.strip() for line in str(result.stdout or "").splitlines() if line.strip()]
    return {
        "result": "passed" if values else UNVERIFIED,
        "details": values if values else "No GPU utilization rows returned",
    }


def _ollama_should_be_checked(config: Any) -> bool:
    roles = []
    for role_name in ("router", "coding", "reasoning", "deep_reasoning"):
        role = getattr(config, role_name, None)
        provider = str(getattr(role, "provider", "") or "").strip().lower()
        roles.append(provider)
    if "ollama" in roles:
        return True
    explicit = str(os.getenv("OLLAMA_URL") or "").strip()
    return bool(explicit)


def collect_runtime_snapshot(
    *,
    backend_base_url: str = DEFAULT_BACKEND_BASE_URL,
    timeout_seconds: float = DEFAULT_CHECK_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    config = load_model_routing_config()
    snapshot: dict[str, Any] = {
        "collected_at": _iso_now(),
        "loop_mode_default": DEFAULT_LOOP_MODE,
        "artifact_root": str(ARTIFACT_ROOT),
        "backend_base_url": _normalize_base_url(backend_base_url),
        "router_config": {
            "router": vars(config.router),
            "coding": vars(config.coding),
            "reasoning": vars(config.reasoning),
            "deep_reasoning": vars(config.deep_reasoning),
            "embedding": vars(config.embedding),
        },
        "rag_config": {
            "qdrant_url": str(settings.qdrant_url),
            "qdrant_collection": str(settings.qdrant_collection),
            "enable_qdrant": bool(settings.enable_qdrant),
            "enable_embeddings": bool(settings.enable_embeddings),
            "docs_root": str(settings.docs_root),
        },
        "artifact_paths": build_artifact_paths("latest"),
    }

    health_url = f"{snapshot['backend_base_url']}/api/health"
    system_status_url = f"{snapshot['backend_base_url']}/api/system/status"
    headers = _backend_headers()

    try:
        _, health_payload = _http_json(health_url, timeout_seconds=timeout_seconds, headers=headers)
        snapshot["backend_health"] = {"result": "passed", "payload": health_payload}
    except Exception as exc:
        snapshot["backend_health"] = {"result": UNVERIFIED, "payload": DATA_MISSING, "details": str(exc)}

    try:
        _, system_status_payload = _http_json(system_status_url, timeout_seconds=timeout_seconds, headers=headers)
        snapshot["backend_system_status"] = {"result": "passed", "payload": system_status_payload}
    except Exception as exc:
        snapshot["backend_system_status"] = {"result": UNVERIFIED, "payload": DATA_MISSING, "details": str(exc)}

    llm_base_url = _strip_v1(str(settings.llamacpp_url))
    llm_model = str(config.reasoning.model_name)
    try:
        snapshot["llamacpp"] = {
            "result": "passed",
            "base_url": llm_base_url,
            "model": llm_model,
            "models": _http_json(f"{llm_base_url}/v1/models", timeout_seconds=timeout_seconds)[1],
        }
    except Exception as exc:
        snapshot["llamacpp"] = {
            "result": UNVERIFIED,
            "base_url": llm_base_url,
            "model": llm_model,
            "models": DATA_MISSING,
            "details": str(exc),
        }

    if _ollama_should_be_checked(config):
        ollama_base_url = _normalize_base_url(str(os.getenv("OLLAMA_URL") or settings.ollama_url))
        try:
            _, payload = _http_json(f"{ollama_base_url}/api/tags", timeout_seconds=timeout_seconds)
            snapshot["ollama"] = {
                "result": "passed",
                "base_url": ollama_base_url,
                "models": payload,
            }
        except Exception as exc:
            snapshot["ollama"] = {
                "result": UNVERIFIED,
                "base_url": ollama_base_url,
                "models": DATA_MISSING,
                "details": str(exc),
            }
    else:
        snapshot["ollama"] = {
            "result": UNVERIFIED,
            "base_url": str(settings.ollama_url),
            "models": DATA_MISSING,
            "details": "No configured Ollama provider role or explicit OLLAMA_URL.",
        }

    snapshot["docker"] = _docker_status(timeout_seconds)
    snapshot["gpu_probe"] = _gpu_probe(timeout_seconds)
    snapshot["benchmark_runtime"] = _benchmark_summary(EXPECTED_BENCHMARK_PATH)
    snapshot["benchmark_legacy"] = _benchmark_summary(LEGACY_BENCHMARK_PATH)
    snapshot["metrics_snapshot"] = _metrics_snapshot()
    return snapshot


def detect_write_path_drifts(source_map: dict[str, str]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    for path, text in source_map.items():
        if ' / "reports"' in text or '/ "reports" / ' in text:
            details = "repo-local reports path detected"
            if "runtime_embedding_model.txt" in text:
                details = "repo-local runtime_embedding_model.txt write detected"
            elif "router_metrics_snapshot.json" in text:
                details = "repo-local router metrics snapshot path detected"
            elif "model_benchmark.json" in text:
                details = "repo-local benchmark output path detected"
            drifts.append(
                {
                    "kind": "write_path_violation",
                    "severity": "critical",
                    "path": path,
                    "details": details,
                }
            )
    return drifts


def detect_benchmark_path_drifts(source_map: dict[str, str]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    optimizer_source = source_map.get("financial-engine_v2/backend/app/services/router_optimizer.py", "")
    benchmark_source = source_map.get("financial-engine_v2/scripts/benchmark_models.py", "")
    doc_source = source_map.get("docs/architecture/model-routing.md", "")
    if "/data/reports/model_benchmark.json" in optimizer_source and 'ROOT / "reports" / "model_benchmark.json"' in benchmark_source:
        drifts.append(
            {
                "kind": "benchmark_path_mismatch",
                "severity": "high",
                "path": "financial-engine_v2/backend/app/services/router_optimizer.py",
                "details": "optimizer loads /data/reports/model_benchmark.json while benchmark script defaults to project reports/model_benchmark.json",
            }
        )
    if "reports/model_benchmark.json" in doc_source and "/data/reports/model_benchmark.json" in optimizer_source:
        drifts.append(
            {
                "kind": "doc_code_drift",
                "severity": "medium",
                "path": "docs/architecture/model-routing.md",
                "details": "documentation benchmark path differs from optimizer runtime path",
            }
        )
    return drifts


def detect_router_chain_drifts(
    config: Any,
    *,
    reasoning_fallback: Any | None = None,
    coding_fallback: Any | None = None,
) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    if reasoning_fallback is None:
        llm_source = _read_text(PROJECT_ROOT / "backend" / "app" / "services" / "llm.py")
        reasoning_ok = (
            'if decision.task_type == "reasoning"' in llm_source
            and 'model_name=config.router.model_name' in llm_source
            and 'execution_queue="llm_cpu"' in llm_source
        )
    else:
        reasoning_ok = (
            str(getattr(reasoning_fallback, "model_name", "")) == str(config.router.model_name)
            and str(getattr(reasoning_fallback, "provider", "")) == str(config.router.provider)
            and str(getattr(reasoning_fallback, "base_url", "")) == str(config.router.base_url)
            and str(getattr(reasoning_fallback, "execution_queue", "")) == "llm_cpu"
        )
    if coding_fallback is None:
        llm_source = _read_text(PROJECT_ROOT / "backend" / "app" / "services" / "llm.py")
        coding_ok = (
            'if decision.task_type == "coding"' in llm_source
            and 'model_name=config.coding.model_name' in llm_source
            and 'execution_queue="llm_gpu"' in llm_source
        )
    else:
        coding_ok = (
            str(getattr(coding_fallback, "model_name", "")) == str(config.coding.model_name)
            and str(getattr(coding_fallback, "provider", "")) == str(config.coding.provider)
            and str(getattr(coding_fallback, "base_url", "")) == str(config.coding.base_url)
            and str(getattr(coding_fallback, "execution_queue", "")) == "llm_gpu"
        )

    if not reasoning_ok:
        drifts.append(
            {
                "kind": "router_chain_mismatch",
                "severity": "high",
                "path": "financial-engine_v2/backend/app/services/llm.py",
                "details": "reasoning fallback does not resolve to configured router role on llm_cpu",
            }
        )

    if not coding_ok:
        drifts.append(
            {
                "kind": "router_chain_mismatch",
                "severity": "high",
                "path": "financial-engine_v2/backend/app/services/llm.py",
                "details": "coding fallback does not resolve to configured coding role on llm_gpu",
            }
        )

    return drifts


def _detect_rag_doc_drift(source_map: dict[str, str]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    doc_source = source_map.get("docs/architecture/07_rag_contract.md", "")
    rag_source = source_map.get("financial-engine_v2/backend/app/services/rag.py", "")
    main_source = source_map.get("financial-engine_v2/backend/app/main.py", "")
    if "Missing collection" in doc_source and "ensure_collection(client, settings.qdrant_collection" in rag_source:
        drifts.append(
            {
                "kind": "doc_code_drift",
                "severity": "medium",
                "path": "docs/architecture/07_rag_contract.md",
                "details": "RAG docs describe missing collection as fail-fast while query path can create collection via ensure_collection",
            }
        )
    if "startup validation fails" in doc_source and "WARNING: qdrant collection" in main_source:
        drifts.append(
            {
                "kind": "doc_code_drift",
                "severity": "medium",
                "path": "docs/architecture/07_rag_contract.md",
                "details": "RAG docs describe missing collection startup failure while startup path currently warns and continues",
            }
        )
    return drifts


def _detect_low_sample_doc_drift(source_map: dict[str, str]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    doc_source = source_map.get("docs/architecture/model-routing.md", "")
    if "sample_size" not in doc_source and "MIN_DEGRADATION_SAMPLE_SIZE" in _read_text(PROJECT_ROOT / "backend" / "app" / "services" / "router_optimizer.py"):
        drifts.append(
            {
                "kind": "doc_claim_missing",
                "severity": "low",
                "path": "docs/architecture/model-routing.md",
                "details": f"low-sample degradation threshold is implemented as {MIN_METRICS_SAMPLE_SIZE} but not documented",
            }
        )
    return drifts


def validate_rag_guardrails(source_map: dict[str, str]) -> dict[str, Any]:
    rag_source = source_map.get("financial-engine_v2/backend/app/services/rag.py", "")
    test_source = _read_text(PROJECT_ROOT / "backend" / "tests" / "test_rag_payload_guardrails.py")
    has_strict_first = "_build_query_filter" in rag_source and "query_filter" in rag_source
    has_fallback = "used_ticker_fallback = True" in rag_source and "points = client.search(" in rag_source
    has_test = "test_query_rag_extracts_ticker_applies_filter_and_retries_without_filter" in test_source
    if has_strict_first and has_fallback and has_test:
        return {
            "name": "rag_ticker_filter",
            "result": "passed",
            "severity": "high",
            "details": "strict-first ticker filter with retry-without-filter path detected in code and targeted test",
        }
    return {
        "name": "rag_ticker_filter",
        "result": "failed",
        "severity": "high",
        "details": "strict-first ticker filter with fallback could not be fully verified from code/test surface",
    }


def detect_drifts(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    source_map = _load_source_map()
    config = load_model_routing_config()
    drifts: list[dict[str, Any]] = []
    drifts.extend(detect_write_path_drifts(source_map))
    drifts.extend(detect_benchmark_path_drifts(source_map))
    drifts.extend(detect_router_chain_drifts(config))
    drifts.extend(_detect_rag_doc_drift(source_map))
    drifts.extend(_detect_low_sample_doc_drift(source_map))

    runtime_benchmark = snapshot.get("benchmark_runtime")
    if isinstance(runtime_benchmark, dict):
        freshness = runtime_benchmark.get("freshness_hours", DATA_MISSING)
        if runtime_benchmark.get("present") and isinstance(freshness, (int, float)) and freshness > DEFAULT_BENCHMARK_MAX_AGE_HOURS:
            drifts.append(
                {
                    "kind": "benchmark_stale",
                    "severity": "medium",
                    "path": str(EXPECTED_BENCHMARK_PATH),
                    "details": f"runtime benchmark is stale at {freshness:.2f} hours",
                }
            )
        if runtime_benchmark.get("present") and not runtime_benchmark.get("complete"):
            drifts.append(
                {
                    "kind": "benchmark_incomplete",
                    "severity": "medium",
                    "path": str(EXPECTED_BENCHMARK_PATH),
                    "details": "runtime benchmark is missing one or more required routed roles",
                }
            )
        if not runtime_benchmark.get("present"):
            drifts.append(
                {
                    "kind": "benchmark_missing",
                    "severity": "medium",
                    "path": str(EXPECTED_BENCHMARK_PATH),
                    "details": "runtime benchmark artifact missing",
                }
            )
    return drifts


def _severity_score(severity: str) -> float:
    return {
        "critical": 1.0,
        "high": 0.7,
        "medium": 0.4,
        "low": 0.2,
    }.get(str(severity or "").strip().lower(), 0.4)


def _normalize_pass_ratio(checks: list[dict[str, Any]]) -> float:
    if not checks:
        return 0.5
    passed = sum(1 for check in checks if check.get("result") == "passed")
    return passed / len(checks)


def _metrics_aggregate(metrics_snapshot: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not metrics_snapshot:
        return {
            "avg_latency_seconds": DATA_MISSING,
            "avg_tokens_per_second": DATA_MISSING,
            "error_rate": DATA_MISSING,
            "timeout_rate": DATA_MISSING,
            "sample_count": DATA_MISSING,
        }
    eligible = []
    for metrics in metrics_snapshot.values():
        if not isinstance(metrics, dict):
            continue
        sample_count = int(float(metrics.get("sample_size", metrics.get("sample_count", 0.0)) or 0.0))
        if sample_count < MIN_METRICS_SAMPLE_SIZE:
            continue
        eligible.append(metrics)
    if not eligible:
        return {
            "avg_latency_seconds": DATA_MISSING,
            "avg_tokens_per_second": DATA_MISSING,
            "error_rate": DATA_MISSING,
            "timeout_rate": DATA_MISSING,
            "sample_count": DATA_MISSING,
        }
    return {
        "avg_latency_seconds": sum(float(item.get("avg_latency_seconds", 0.0)) for item in eligible) / len(eligible),
        "avg_tokens_per_second": sum(float(item.get("avg_tokens_per_second", 0.0)) for item in eligible) / len(eligible),
        "error_rate": sum(float(item.get("error_rate", 0.0)) for item in eligible) / len(eligible),
        "timeout_rate": sum(float(item.get("timeout_rate", 0.0)) for item in eligible) / len(eligible),
        "sample_count": sum(int(float(item.get("sample_size", item.get("sample_count", 0.0)) or 0.0)) for item in eligible),
    }


def _bounded_signal(name: str, value: float | str, *, invert: bool = False) -> dict[str, Any]:
    if isinstance(value, str):
        return {"name": name, "value": value, "normalized": DATA_MISSING}
    bounded = max(0.0, min(float(value), 1.0))
    normalized = 1.0 - bounded if invert else bounded
    return {"name": name, "value": float(value), "normalized": normalized}


def compute_scorecard(
    *,
    checks: list[dict[str, Any]],
    drifts: list[dict[str, Any]],
    metrics_snapshot: dict[str, dict[str, Any]],
    benchmark_report: dict[str, Any],
) -> dict[str, Any]:
    metrics = _metrics_aggregate(metrics_snapshot)
    benchmark_models = benchmark_report.get("models") if isinstance(benchmark_report, dict) else None
    benchmark_present = isinstance(benchmark_models, dict) and bool(benchmark_models)

    drift_value = 0.0
    if drifts:
        drift_value = min(sum(_severity_score(drift.get("severity", "medium")) for drift in drifts) / max(len(drifts), 1), 1.0)

    error_rate = metrics["error_rate"]
    timeout_rate = metrics["timeout_rate"]
    latency_seconds = metrics["avg_latency_seconds"]
    tokens_per_second = metrics["avg_tokens_per_second"]

    latency_signal = DATA_MISSING if isinstance(latency_seconds, str) else min(float(latency_seconds) / 30.0, 1.0)
    throughput_signal = DATA_MISSING if isinstance(tokens_per_second, str) else min(float(tokens_per_second) / 100.0, 1.0)
    timeout_error_signal = DATA_MISSING
    if not isinstance(error_rate, str) and not isinstance(timeout_rate, str):
        timeout_error_signal = min((float(error_rate) + float(timeout_rate)) / 2.0, 1.0)

    signals = [
        _bounded_signal("correctness", _normalize_pass_ratio([check for check in checks if check.get("name") != "restart_loops"])),
        _bounded_signal("reliability", _normalize_pass_ratio([check for check in checks if check.get("severity") in {"high", "critical"}])),
        _bounded_signal("latency", latency_signal, invert=True),
        _bounded_signal("throughput", throughput_signal),
        {"name": "fallback_frequency", "value": DATA_MISSING, "normalized": DATA_MISSING},
        _bounded_signal("timeout_error_rate", timeout_error_signal, invert=True),
        _bounded_signal("drift_severity", drift_value, invert=True),
        {"name": "benchmark_present", "value": 1.0 if benchmark_present else DATA_MISSING, "normalized": 1.0 if benchmark_present else DATA_MISSING},
    ]

    weights = {
        "correctness": 0.28,
        "reliability": 0.22,
        "latency": 0.14,
        "throughput": 0.10,
        "fallback_frequency": 0.10,
        "timeout_error_rate": 0.10,
        "drift_severity": 0.06,
    }

    weighted_total = 0.0
    active_weight = 0.0
    for signal in signals:
        normalized = signal.get("normalized")
        if isinstance(normalized, str):
            continue
        weight = weights.get(signal["name"], 0.0)
        active_weight += weight
        weighted_total += weight * float(normalized)

    overall = weighted_total / active_weight if active_weight > 0 else 0.0
    return {
        "overall_score": round(overall, 4),
        "signals": signals,
        "weights": weights,
        "thresholds": {
            "min_metrics_sample_size": MIN_METRICS_SAMPLE_SIZE,
            "benchmark_max_age_hours": DEFAULT_BENCHMARK_MAX_AGE_HOURS,
        },
        "metrics_snapshot_used": metrics,
    }


def _check_backend_health(snapshot: dict[str, Any]) -> dict[str, Any]:
    backend_health = snapshot.get("backend_health", {})
    if backend_health.get("result") == "passed":
        payload = backend_health.get("payload")
        if isinstance(payload, dict) and str(payload.get("status")) == "ok":
            return {"name": "backend_health", "result": "passed", "severity": "high", "details": "backend /api/health reachable"}
        return {"name": "backend_health", "result": "failed", "severity": "high", "details": "backend /api/health payload unexpected"}
    return {"name": "backend_health", "result": UNVERIFIED, "severity": "high", "details": backend_health.get("details", "")}


def _check_ollama(snapshot: dict[str, Any]) -> dict[str, Any]:
    ollama = snapshot.get("ollama", {})
    if ollama.get("result") == "passed":
        return {"name": "ollama_reachable", "result": "passed", "severity": "high", "details": "Ollama reachable and model list available"}
    details = str(ollama.get("details") or "")
    result = UNVERIFIED if "No configured Ollama provider role" in details else "failed"
    return {"name": "ollama_reachable", "result": result, "severity": "high", "details": details or "Ollama model list unavailable"}


def _check_llamacpp(snapshot: dict[str, Any]) -> dict[str, Any]:
    llamacpp = snapshot.get("llamacpp", {})
    if llamacpp.get("result") == "passed":
        return {"name": "llamacpp_reachable", "result": "passed", "severity": "critical", "details": "llama.cpp reachable and model list available"}
    return {"name": "llamacpp_reachable", "result": UNVERIFIED, "severity": "critical", "details": str(llamacpp.get("details") or "")}


def _check_gpu_offload(snapshot: dict[str, Any]) -> dict[str, Any]:
    gpu_probe = snapshot.get("gpu_probe", {})
    if gpu_probe.get("result") == "passed":
        return {"name": "llamacpp_gpu_offload", "result": UNVERIFIED, "severity": "critical", "details": "GPU telemetry available, but llama.cpp offload remains Unverified without explicit runtime probe"}
    return {"name": "llamacpp_gpu_offload", "result": UNVERIFIED, "severity": "critical", "details": str(gpu_probe.get("details") or "GPU telemetry unavailable")}


def _check_restart_loops(snapshot: dict[str, Any]) -> dict[str, Any]:
    docker = snapshot.get("docker", {})
    entries = docker.get("entries")
    if not isinstance(entries, list):
        return {"name": "restart_loops", "result": UNVERIFIED, "severity": "high", "details": "Docker status unavailable"}
    restarting = [entry for entry in entries if "Restarting" in str(entry.get("status") or "")]
    if restarting:
        return {"name": "restart_loops", "result": "failed", "severity": "high", "details": f"restart loops inferred for {len(restarting)} container(s)"}
    return {"name": "restart_loops", "result": "passed", "severity": "high", "details": "No restart loop inferred from docker ps status"}


def _check_benchmark(snapshot: dict[str, Any]) -> dict[str, Any]:
    benchmark = snapshot.get("benchmark_runtime", {})
    if not benchmark.get("present"):
        return {"name": "benchmark_runtime", "result": "failed", "severity": "medium", "details": "Runtime benchmark artifact missing"}
    if not benchmark.get("complete"):
        return {"name": "benchmark_runtime", "result": "failed", "severity": "medium", "details": "Runtime benchmark artifact incomplete"}
    freshness = benchmark.get("freshness_hours", DATA_MISSING)
    if isinstance(freshness, (int, float)) and freshness > DEFAULT_BENCHMARK_MAX_AGE_HOURS:
        return {"name": "benchmark_runtime", "result": "failed", "severity": "medium", "details": f"Runtime benchmark stale at {freshness:.2f} hours"}
    return {"name": "benchmark_runtime", "result": "passed", "severity": "medium", "details": "Runtime benchmark present and complete"}


def _check_router_chain(snapshot: dict[str, Any], drifts: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches = [drift for drift in drifts if drift.get("kind") == "router_chain_mismatch"]
    if mismatches:
        return {"name": "router_chain", "result": "failed", "severity": "high", "details": mismatches[0]["details"]}
    return {"name": "router_chain", "result": "passed", "severity": "high", "details": "Configured fallback chain matches implementation"}


def _check_low_sample_threshold(drifts: list[dict[str, Any]]) -> dict[str, Any]:
    missing_docs = [drift for drift in drifts if drift.get("kind") == "doc_claim_missing"]
    if missing_docs:
        return {"name": "low_sample_threshold", "result": UNVERIFIED, "severity": "medium", "details": missing_docs[0]["details"]}
    return {"name": "low_sample_threshold", "result": "passed", "severity": "medium", "details": f"low-sample threshold resolved at {MIN_METRICS_SAMPLE_SIZE}"}


def _check_data_write_policy(drifts: list[dict[str, Any]]) -> dict[str, Any]:
    violations = [drift for drift in drifts if drift.get("kind") == "write_path_violation"]
    if violations:
        return {"name": "data_write_policy", "result": "failed", "severity": "critical", "details": f"{len(violations)} non-/data runtime write target(s) detected"}
    return {"name": "data_write_policy", "result": "passed", "severity": "critical", "details": "No non-/data runtime write target detected in scanned surface"}


def build_checks(snapshot: dict[str, Any], drifts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_map = _load_source_map()
    return [
        _check_backend_health(snapshot),
        _check_ollama(snapshot),
        _check_llamacpp(snapshot),
        _check_gpu_offload(snapshot),
        _check_restart_loops(snapshot),
        _check_benchmark(snapshot),
        _check_router_chain(snapshot, drifts),
        _check_low_sample_threshold(drifts),
        validate_rag_guardrails(source_map),
        _check_data_write_policy(drifts),
    ]


def plan_optimizer_actions(report: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    drifts = list(report.get("drifts") or [])
    checks = list(report.get("checks") or [])

    if any(drift.get("kind") == "write_path_violation" for drift in drifts):
        actions.append(
            {
                "class": "code_patch_candidate",
                "summary": "Move analyzer-adjacent runtime report paths to /data and remove repo-local report writes.",
                "gated": True,
                "target_files": [
                    "financial-engine_v2/backend/app/main.py",
                    "financial-engine_v2/backend/app/services/router_metrics.py",
                    "financial-engine_v2/scripts/benchmark_models.py",
                ],
            }
        )

    if any(drift.get("kind") in {"benchmark_missing", "benchmark_stale", "benchmark_incomplete"} for drift in drifts):
        actions.append(
            {
                "class": "benchmark_action",
                "summary": "Regenerate routed benchmark and place canonical artifact under /data/reports/model_benchmark.json.",
                "gated": False,
                "validation": ["python3 financial-engine_v2/scripts/benchmark_models.py --output /data/reports/model_benchmark.json"],
            }
        )

    if any(check.get("name") == "router_chain" and check.get("result") == "failed" for check in checks):
        actions.append(
            {
                "class": "config_recommendation",
                "summary": "Reconcile configured role map with llm fallback chain before enabling any optimizer-generated patch flow.",
                "gated": False,
                "target_files": [
                    "financial-engine_v2/backend/app/config/model_routing.yaml",
                    "financial-engine_v2/backend/app/services/llm.py",
                ],
            }
        )

    doc_drifts = [drift for drift in drifts if drift.get("kind") == "doc_code_drift"]
    if doc_drifts:
        actions.append(
            {
                "class": "doc_correction_candidate",
                "summary": "Update machine-checkable docs to match current benchmark, RAG, and runtime path behavior.",
                "gated": False,
                "target_files": sorted({str(drift.get("path") or "") for drift in doc_drifts if str(drift.get("path") or "").strip()}),
            }
        )

    if not actions:
        actions.append({"class": "no_op", "summary": "No optimizer action recommended.", "gated": False})

    return actions


def _default_scoring_engine(
    checks: list[dict[str, Any]],
    drifts: list[dict[str, Any]],
    metrics_snapshot: dict[str, dict[str, Any]],
    benchmark_report: dict[str, Any],
) -> dict[str, Any]:
    return compute_scorecard(
        checks=checks,
        drifts=drifts,
        metrics_snapshot=metrics_snapshot,
        benchmark_report=benchmark_report,
    )


def run_analyzer_loop(
    *,
    mode: str = DEFAULT_LOOP_MODE,
    backend_base_url: str = DEFAULT_BACKEND_BASE_URL,
    write_report: bool = True,
    timeout_seconds: float = DEFAULT_CHECK_TIMEOUT_SECONDS,
    watchdog_seconds: float = DEFAULT_WATCHDOG_SECONDS,
    allow_apply_gated: bool = False,
    snapshot_collector: Callable[[], dict[str, Any]] | None = None,
    drift_detector: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
    scoring_engine: Callable[[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]], dict[str, Any]] | None = None,
    planner: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    selected_mode = str(mode or DEFAULT_LOOP_MODE).strip().lower()
    if selected_mode not in ALLOWED_LOOP_MODES:
        selected_mode = DEFAULT_LOOP_MODE

    run_id = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    artifact_paths = build_artifact_paths(run_id)
    deadline = monotonic() + max(float(watchdog_seconds or DEFAULT_WATCHDOG_SECONDS), 1.0)
    report: dict[str, Any] = {
        "status": "ok",
        "generated_at": _iso_now(),
        "run_id": run_id,
        "loop_mode": selected_mode,
        "safe_state": DEFAULT_LOOP_MODE,
        "states_completed": [],
        "checks": [],
        "drifts": [],
        "snapshot": {},
        "optimizer": {
            "auto_apply": False,
            "allow_apply_gated": bool(allow_apply_gated and selected_mode == "apply_gated"),
            "actions": [],
        },
        "artifacts": artifact_paths,
        "errors": [],
    }

    active_snapshot_collector = snapshot_collector or (
        lambda: collect_runtime_snapshot(
            backend_base_url=backend_base_url,
            timeout_seconds=max(0.5, min(timeout_seconds / 5.0, 1.0)),
        )
    )
    active_drift_detector = drift_detector or detect_drifts
    active_scoring_engine = scoring_engine or _default_scoring_engine
    active_planner = planner or plan_optimizer_actions

    snapshot_result = _run_check(
        "observe",
        lambda: {
            "result": "passed",
            "severity": "high",
            "details": "",
            "snapshot": active_snapshot_collector(),
        },
        timeout_seconds=timeout_seconds,
        deadline=deadline,
    )
    if snapshot_result["result"] == "failed":
        report["status"] = "partial"
        report["checks"].append(snapshot_result)
        report["errors"].append(snapshot_result["details"])
    else:
        report["snapshot"] = dict(snapshot_result.get("snapshot") or {})
        report["states_completed"].append("observe")

    if report["snapshot"]:
        drift_result = _run_check(
            "validate",
            lambda: {"name": "validate", "result": "passed", "severity": "high", "details": ""},
            timeout_seconds=timeout_seconds,
            deadline=deadline,
        )
        if drift_result["result"] == "failed":
            report["status"] = "partial"
            report["checks"].append(drift_result)
            report["errors"].append(drift_result["details"])
        else:
            report["drifts"] = active_drift_detector(report["snapshot"])
            report["states_completed"].append("validate")
            report["checks"].extend(build_checks(report["snapshot"], report["drifts"]))

    metrics_snapshot = report["snapshot"].get("metrics_snapshot", {}) if report["snapshot"] else {}
    benchmark_report = _benchmark_report_payload(report["snapshot"]) if report["snapshot"] else {}
    report["scoring"] = active_scoring_engine(report["checks"], report["drifts"], metrics_snapshot, benchmark_report)
    report["states_completed"].append("score")

    report["optimizer"]["actions"] = active_planner(report)
    report["states_completed"].append("recommend")

    if selected_mode in {"prepare_patch", "apply_gated"}:
        report["states_completed"].append("prepare_patch")
    if selected_mode == "apply_gated":
        report["states_completed"].append("apply_gated")
        report["optimizer"]["auto_apply"] = False
        if not allow_apply_gated:
            report["status"] = "partial"
            report["errors"].append("apply_gated requested without explicit approval; stayed in recommend safe-state")

    if write_report:
        try:
            _write_json_atomic(artifact_paths["history_report"], report)
            _write_json_atomic(artifact_paths["latest_report"], report)
            if selected_mode in {"prepare_patch", "apply_gated"}:
                patch_payload = {
                    "generated_at": report["generated_at"],
                    "run_id": run_id,
                    "mode": selected_mode,
                    "auto_apply": False,
                    "actions": [
                        action
                        for action in report["optimizer"]["actions"]
                        if action.get("class") == "code_patch_candidate"
                    ],
                }
                _write_json_atomic(artifact_paths["patch_candidate"], patch_payload)
        except Exception as exc:
            report["status"] = "partial"
            report["errors"].append(f"artifact persistence failed: {exc}")

    return report
