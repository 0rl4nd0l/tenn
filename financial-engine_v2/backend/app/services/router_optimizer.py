from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import router_metrics
from app.services.router_state import RouterState


HIGH_COMPLEXITY_KEYWORDS = (
    "compare",
    "compare capital allocation paths",
    "valuation sensitivity",
    "scenario analysis",
    "refinancing risk",
    "tradeoffs",
    "tradeoff",
    "valuation",
    "multi-step",
    "multi step",
    "deep analysis",
    "financial model",
    "investment thesis",
    "base case",
    "bull case",
    "bear case",
    "synthesised",
    "synthesized",
    "peer comparison",
)
LOW_COMPLEXITY_KEYWORDS = (
    "summarize",
    "short",
    "recap",
    "extract",
    "key facts",
    "headline",
)
LOW_COMPLEXITY_MAX_CHARS = 180
LOW_COMPLEXITY_MAX_WORDS = 24
HIGH_ERROR_RATE_THRESHOLD = 0.2
HIGH_TIMEOUT_RATE_THRESHOLD = 0.1
HIGH_LATENCY_SECONDS = 30.0
MIN_DEGRADATION_SAMPLE_SIZE = 5.0

_BENCHMARK_CACHE: dict[str, Any] = {
    "path": None,
    "mtime": None,
    "data": {},
}


def _load_snapshot_baseline() -> dict[str, dict[str, Any]]:
    try:
        return {
            model_name: {
                "avg_latency_seconds": float(metrics.get("avg_latency_seconds", 0.0)),
                "avg_tokens_per_second": float(metrics.get("avg_tokens_per_second", 0.0)),
                "error_rate": float(metrics.get("error_rate", 0.0)),
                "timeout_rate": float(metrics.get("timeout_rate", 0.0)),
                "sample_size": float(metrics.get("sample_size", metrics.get("sample_count", 0.0))),
            }
            for model_name, metrics in router_metrics.load_metrics_snapshot().items()
            if isinstance(model_name, str) and isinstance(metrics, dict)
        }
    except Exception:
        return {}


def _load_snapshot_task_baseline() -> dict[str, dict[str, dict[str, Any]]]:
    try:
        return {
            model_name: {
                task_name: {
                    "avg_latency_seconds": float(metrics.get("avg_latency_seconds", 0.0)),
                    "avg_tokens_per_second": float(metrics.get("avg_tokens_per_second", 0.0)),
                    "error_rate": float(metrics.get("error_rate", 0.0)),
                    "timeout_rate": float(metrics.get("timeout_rate", 0.0)),
                    "sample_size": float(metrics.get("sample_size", metrics.get("sample_count", 0.0))),
                }
                for task_name, metrics in task_map.items()
                if isinstance(task_name, str) and isinstance(metrics, dict)
            }
            for model_name, task_map in router_metrics.load_task_metrics_snapshot().items()
            if isinstance(model_name, str) and isinstance(task_map, dict)
        }
    except Exception:
        return {}


_SNAPSHOT_BASELINE_SUMMARIES = _load_snapshot_baseline()
_SNAPSHOT_BASELINE_TASK_SUMMARIES = _load_snapshot_task_baseline()


@dataclass(frozen=True)
class OptimalModelDecision:
    model_name: str
    provider: str
    base_url: str
    queue: str
    confidence: float
    deferred: bool = False


def _benchmark_report_path() -> Path:
    path = Path(getattr(settings, "data_root", "/data")) / "reports" / "model_benchmark.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def _load_benchmark_metrics() -> dict[str, dict[str, Any]]:
    path = _benchmark_report_path()
    if not path.exists():
        return {}

    try:
        stat = path.stat()
    except OSError:
        return {}

    cache_hit = (
        _BENCHMARK_CACHE.get("path") == str(path)
        and _BENCHMARK_CACHE.get("mtime") == stat.st_mtime
    )
    if cache_hit:
        return dict(_BENCHMARK_CACHE.get("data") or {})

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, dict):
        return {}

    normalized = {
        str(model_name).strip(): dict(metrics)
        for model_name, metrics in raw_models.items()
        if isinstance(metrics, dict)
    }
    _BENCHMARK_CACHE.update(
        {
            "path": str(path),
            "mtime": stat.st_mtime,
            "data": dict(normalized),
        }
    )
    return normalized


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _metadata_int(metadata: dict[str, Any] | None, key: str, default: int = 0) -> int:
    return _to_int((metadata or {}).get(key), default=default)


def detect_complexity(prompt: str, metadata: dict[str, Any] | None = None) -> str:
    payload = dict(metadata or {})
    explicit = str(payload.get("complexity") or payload.get("semantic_complexity") or "").strip().lower()
    if explicit in {"low", "medium", "high"}:
        return explicit
    if payload.get("deep_reasoning") is True:
        return "high"

    prompt_text = str(prompt or "").strip()
    prompt_text_lower = prompt_text.lower()
    haystack = " ".join(
        [
            prompt_text,
            " ".join(f"{key}={value}" for key, value in sorted(payload.items())),
        ]
    ).lower()

    if any(keyword in haystack for keyword in HIGH_COMPLEXITY_KEYWORDS):
        return "high"

    if _metadata_int(metadata, "document_count", default=1) > 1 and "filing" in haystack:
        return "high"

    word_count = len(prompt_text.split())
    if (
        prompt_text
        and len(prompt_text) <= LOW_COMPLEXITY_MAX_CHARS
        and word_count <= LOW_COMPLEXITY_MAX_WORDS
        and "\n" not in prompt_text
        and any(keyword in prompt_text_lower for keyword in LOW_COMPLEXITY_KEYWORDS)
    ):
        return "low"
    return "medium"


def _normalized_metric(value: float | int | None, *, neutral: float, scale: float) -> float:
    if value is None:
        return neutral
    numeric = max(float(value), 0.0)
    if scale <= 0:
        return neutral
    return min(numeric / scale, 1.0)


def _normalize_financial_task_type(metadata: dict[str, Any] | None) -> str | None:
    financial = str((metadata or {}).get("financial_task_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if financial in {
        "earnings_analysis",
        "guidance_analysis",
        "capital_allocation",
        "balance_sheet_risk",
        "valuation_analysis",
        "peer_comparison",
        "filing_summary",
        "catalyst_detection",
        "rag_financial_synthesis",
    }:
        return financial
    return None


def _looks_multi_company(prompt: str, metadata: dict[str, Any] | None) -> bool:
    prompt_text = str(prompt or "").lower()
    if " vs " in f" {prompt_text} " or " versus " in prompt_text:
        return True
    tickers = str((metadata or {}).get("ticker") or "").replace(",", " ").split()
    if len(tickers) > 1:
        return True
    companies = str((metadata or {}).get("company") or "").replace(",", " ").split()
    if len(companies) > 1:
        return True
    return False


def _should_use_rag_deep_model(prompt: str, metadata: dict[str, Any] | None, config: dict[str, Any]) -> bool:
    haystack = str(prompt or "").lower()
    context_chars = _metadata_int(metadata, "retrieved_context_chars", default=0)
    document_count = _metadata_int(metadata, "document_count", default=0)
    if context_chars >= int(
        config.get("financial_rag_deep_context_chars", 5000)
    ):
        return True
    if document_count >= 3:
        return True
    if document_count >= 2 and any(
        token in haystack
        for token in (
            "multiple filings",
            "cross-document",
            "cross document",
            "synthesized view",
            "source-backed synthesis",
        )
    ):
        return True
    return False


def _preferred_role_name(
    task_type: str,
    financial_task_type: str | None,
    prompt: str,
    prompt_length: int,
    deep_reasoning_requested: bool,
    metadata: dict[str, Any] | None,
    complexity: str,
    config: dict[str, Any],
) -> str:
    prompt_haystack = str(prompt or "").lower()

    if task_type in {"embedding", "router", "coding"}:
        return task_type
    if deep_reasoning_requested:
        return "deep_reasoning"

    if financial_task_type == "filing_summary":
        if prompt_length <= int(config.get("financial_short_summary_chars", 400)) and complexity != "high":
            return "router"
        if prompt_length > int(config.get("financial_deep_analysis_chars", 2500)):
            return "deep_reasoning"
        if complexity == "high":
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "valuation_analysis":
        if config.get("valuation_force_deep_reasoning", True):
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "peer_comparison":
        if _looks_multi_company(prompt, metadata):
            return "deep_reasoning"
        if prompt_length >= int(config.get("financial_peer_compare_chars", 1800)) or complexity == "high":
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "rag_financial_synthesis":
        if _should_use_rag_deep_model(prompt, metadata, config):
            return "deep_reasoning"
        if complexity == "high":
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "earnings_analysis":
        if prompt_length > int(config.get("financial_deep_analysis_chars", 2500)) or any(
            token in prompt_haystack for token in ("multi-period", "multi period", "multi-step", "multi step")
        ):
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "guidance_analysis":
        if prompt_length > int(config.get("financial_deep_analysis_chars", 2500)) or any(
            token in prompt_haystack
            for token in ("cross-period", "cross period", "multiple filings", "multi-document", "multi document")
        ):
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "capital_allocation":
        if prompt_length > int(config.get("financial_deep_analysis_chars", 2500)) or any(
            token in prompt_haystack
            for token in ("tradeoff", "tradeoffs", "board-level", "board level", "compare capital allocation paths")
        ):
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "balance_sheet_risk":
        if prompt_length > int(config.get("financial_deep_analysis_chars", 2500)) or any(
            token in prompt_haystack for token in ("debt stack", "refinancing", "covenant")
        ):
            return "deep_reasoning"
        return "reasoning"

    if financial_task_type == "catalyst_detection":
        return "reasoning"

    if deep_reasoning_requested or prompt_length > int(config["deep_prompt_chars"]):
        return "deep_reasoning"
    if complexity == "low" or prompt_length < int(config["short_prompt_chars"]):
        return "router"
    return "reasoning"


def _candidate_role_names(
    task_type: str,
    preferred_role: str,
    financial_task_type: str | None,
) -> list[str]:
    if task_type in {"embedding", "router", "coding"}:
        return [preferred_role]
    if financial_task_type:
        if preferred_role == "deep_reasoning":
            return ["deep_reasoning", "reasoning"]
        if preferred_role == "reasoning":
            if financial_task_type == "filing_summary":
                return ["reasoning", "router"]
            return ["reasoning"]
        if preferred_role == "router":
            if financial_task_type == "filing_summary":
                return ["router", "reasoning"]
            return ["router"]
    if preferred_role == "deep_reasoning":
        return ["deep_reasoning", "reasoning"]
    if preferred_role == "reasoning":
        return ["reasoning", "router"]
    return ["router", "reasoning"]


def _build_candidate(
    role_name: str,
    preferred_role: str,
    roles: dict[str, dict[str, str]],
) -> dict[str, Any]:
    role = dict(roles[role_name])
    return {
        "role_name": role_name,
        "model_name": str(role["model_name"]).strip(),
        "provider": str(role["provider"]).strip(),
        "base_url": str(role["base_url"]).strip(),
        "queue": str(role["queue"]).strip(),
        "preferred_role": preferred_role,
    }


def _resolve_model_summary(
    model_name: str,
    financial_task_type: str | None,
    *,
    metrics_history: dict[str, list[dict[str, Any]]] | None,
    model_summaries: dict[str, dict[str, Any]] | None,
    task_model_summaries: dict[str, dict[str, dict[str, Any]]] | None,
    snapshot_summaries: dict[str, dict[str, Any]] | None,
    snapshot_task_summaries: dict[str, dict[str, dict[str, Any]]] | None,
    benchmark_metrics: dict[str, dict[str, Any]],
) -> dict[str, float]:
    def _to_float_dict(values: dict[str, Any]) -> dict[str, float]:
        return {
            key: float(value)
            for key, value in values.items()
            if isinstance(value, (int, float))
        }

    def _has_sufficient_samples(values: dict[str, float]) -> bool:
        sample_size = float(values.get("sample_size", values.get("sample_count", 0.0)) or 0.0)
        return sample_size >= MIN_DEGRADATION_SAMPLE_SIZE

    global_summary = _to_float_dict(dict((model_summaries or {}).get(model_name) or {}))
    live_task_summary = {}
    if financial_task_type:
        live_task_summary = dict(
            (task_model_summaries or {})
            .get(model_name, {})
            .get(financial_task_type, {})
        )
    task_summary = _to_float_dict(live_task_summary)
    task_summary_has_evidence = _has_sufficient_samples(task_summary)
    global_summary_has_evidence = _has_sufficient_samples(global_summary)
    if task_summary_has_evidence and global_summary_has_evidence:
        weight = min(task_summary.get("sample_size", task_summary.get("sample_count", 0.0)), 20.0) / 20.0
        combined = {
            key: (global_summary.get(key, 0.0) * (1.0 - weight))
            + (task_summary.get(key, 0.0) * weight)
            for key in {"avg_latency_seconds", "avg_tokens_per_second", "error_rate", "timeout_rate"}
            if key in global_summary or key in task_summary
        }
        combined["sample_size"] = max(
            task_summary.get("sample_size", task_summary.get("sample_count", 0.0)),
            global_summary.get("sample_size", global_summary.get("sample_count", 0.0)),
        )
        return combined
    if task_summary_has_evidence:
        return task_summary
    if global_summary_has_evidence:
        return global_summary

    if financial_task_type:
        task_snapshot = dict(
            (snapshot_task_summaries or {})
            .get(model_name, {})
            .get(financial_task_type, {})
        )
        task_snapshot_summary = _to_float_dict(task_snapshot)
        if _has_sufficient_samples(task_snapshot_summary):
            return task_snapshot_summary

    snapshot_summary = dict((snapshot_summaries or {}).get(model_name) or {})
    snapshot_summary_values = _to_float_dict(snapshot_summary)
    if _has_sufficient_samples(snapshot_summary_values):
        return snapshot_summary_values

    summary = router_metrics.summarize_metrics(
        metrics_history, model_name, financial_task_type=financial_task_type
    )
    if _has_sufficient_samples(summary):
        return summary

    benchmark = dict(benchmark_metrics.get(model_name) or {})
    latency = benchmark.get("latency_seconds")
    throughput = benchmark.get("tokens_per_second")
    error_rate = benchmark.get("error_rate")
    if latency is None and throughput is None and error_rate is None:
        return {}
    return {
        "avg_latency": float(latency or 0.0),
        "avg_latency_seconds": float(latency or 0.0),
        "avg_tokens_per_second": float(throughput or 0.0),
        "error_rate": float(error_rate or 0.0),
        "timeout_rate": float(benchmark.get("timeout_rate") or 0.0),
        "sample_size": 0.0,
    }


def score_model(
    model_name: str,
    state: RouterState,
    metrics: dict[str, Any] | None,
    *,
    queue_name: str,
    config: dict[str, Any] | None = None,
) -> dict[str, float]:
    summary = dict(metrics or {})
    cfg = dict(config or {})
    sample_size = float(summary.get("sample_size", summary.get("sample_count", 0.0)) or 0.0)
    use_live_metrics = sample_size >= MIN_DEGRADATION_SAMPLE_SIZE
    latency_weight = float(cfg.get("latency_weight", 0.4))
    throughput_weight = float(cfg.get("throughput_weight", 0.3))
    error_weight = float(cfg.get("error_weight", 0.2))
    queue_weight = float(cfg.get("queue_weight", 0.1))
    gpu_weight = float(cfg.get("gpu_weight", 0.1))

    latency_score = 1.0 - _normalized_metric(
        summary.get("avg_latency_seconds", summary.get("avg_latency")) if use_live_metrics else None,
        neutral=0.5,
        scale=20.0,
    )
    throughput_score = _normalized_metric(
        summary.get("avg_tokens_per_second") if use_live_metrics else None,
        neutral=0.5,
        scale=80.0,
    )
    error_rate_score = 1.0 - _normalized_metric(
        summary.get("error_rate") if use_live_metrics else None,
        neutral=0.8,
        scale=1.0,
    )
    timeout_rate_score = 1.0 - _normalized_metric(
        summary.get("timeout_rate") if use_live_metrics else None,
        neutral=0.85,
        scale=1.0,
    )

    queue_depth = int(state.queue_depths.get(queue_name, 0)) + int(state.active_tasks.get(queue_name, 0))
    queue_pressure_score = 1.0 - _normalized_metric(
        queue_depth,
        neutral=1.0,
        scale=max(float(cfg.get("queue_backlog_threshold", 50)), 1.0),
    )

    gpu_pressure_score = 1.0
    if queue_name == "llm_gpu":
        gpu_pressure_score = 1.0 - _normalized_metric(
            state.gpu_utilization,
            neutral=1.0,
            scale=max(float(cfg.get("gpu_overload_threshold", 95)), 1.0),
        )

    total_weight = latency_weight + throughput_weight + error_weight + queue_weight + gpu_weight
    if total_weight <= 0:
        total_weight = 1.0

    weighted_sum = (
        (latency_weight * latency_score)
        + (throughput_weight * throughput_score)
        + (error_weight * error_rate_score)
        + (error_weight * timeout_rate_score)
        + (queue_weight * queue_pressure_score)
        + (gpu_weight * gpu_pressure_score)
    ) / (total_weight + error_weight)

    if use_live_metrics:
        error_rate = float(summary.get("error_rate") or 0.0)
        timeout_rate = float(summary.get("timeout_rate") or 0.0)
        if error_rate > HIGH_ERROR_RATE_THRESHOLD:
            weighted_sum -= 0.45
        if timeout_rate > HIGH_TIMEOUT_RATE_THRESHOLD:
            weighted_sum -= 0.3

    return {
        "latency_score": max(latency_score, 0.0),
        "throughput_score": max(throughput_score, 0.0),
        "error_rate_score": max(error_rate_score, 0.0),
        "timeout_rate_score": max(timeout_rate_score, 0.0),
        "queue_pressure_score": max(queue_pressure_score, 0.0),
        "gpu_pressure_score": max(gpu_pressure_score, 0.0),
        "final_score": max(min(weighted_sum, 1.0), 0.0),
    }


def _candidate_fit_adjustment(role_name: str, preferred_role: str, complexity: str) -> float:
    adjustment = 0.0
    if role_name == preferred_role:
        adjustment += 0.18
    elif role_name == "router":
        adjustment -= 0.08
    else:
        adjustment -= 0.04

    if complexity == "high":
        if role_name == "deep_reasoning":
            adjustment += 0.08
        if role_name == "router":
            adjustment -= 0.12
    elif complexity == "low":
        if role_name == "router":
            adjustment += 0.1
        if role_name == "deep_reasoning":
            adjustment -= 0.15
    return adjustment


def _performance_degraded(
    summary: dict[str, float],
    benchmark: dict[str, Any],
) -> bool:
    if not summary:
        return False
    sample_size = float(summary.get("sample_size", summary.get("sample_count", 0.0)) or 0.0)
    if sample_size < MIN_DEGRADATION_SAMPLE_SIZE:
        return False
    error_rate = float(summary.get("error_rate") or 0.0)
    if error_rate >= HIGH_ERROR_RATE_THRESHOLD:
        return True
    timeout_rate = float(summary.get("timeout_rate") or 0.0)
    if timeout_rate >= HIGH_TIMEOUT_RATE_THRESHOLD:
        return True

    avg_latency = float(summary.get("avg_latency_seconds") or 0.0)
    if avg_latency >= HIGH_LATENCY_SECONDS:
        return True

    benchmark_latency = benchmark.get("latency_seconds")
    if benchmark_latency is None:
        return False
    try:
        return avg_latency >= float(benchmark_latency) * 1.75
    except (TypeError, ValueError):
        return False


def _fallback_candidate(
    preferred_role: str,
    roles: dict[str, dict[str, str]],
) -> dict[str, Any]:
    return _build_candidate("router", preferred_role, roles)


def _needs_hard_router_fallback(
    preferred_summary: dict[str, float],
    *,
    gpu_hot: bool,
    gpu_queue_hot: bool,
) -> bool:
    if gpu_hot or gpu_queue_hot:
        return True
    if not preferred_summary:
        return False
    sample_size = float(
        preferred_summary.get("sample_size", preferred_summary.get("sample_count", 0.0)) or 0.0
    )
    if sample_size < MIN_DEGRADATION_SAMPLE_SIZE:
        return False
    if float(preferred_summary.get("error_rate") or 0.0) > HIGH_ERROR_RATE_THRESHOLD:
        return True
    if float(preferred_summary.get("timeout_rate") or 0.0) > HIGH_TIMEOUT_RATE_THRESHOLD:
        return True
    return False


def _financial_pressure_fallback(
    preferred_role: str,
    financial_task_type: str | None,
    *,
    gpu_hot: bool,
    gpu_queue_hot: bool,
    roles: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if preferred_role == "router":
        return _build_candidate("router", preferred_role, roles)
    if not (gpu_hot or gpu_queue_hot):
        return _build_candidate(preferred_role, preferred_role, roles)
    if financial_task_type == "valuation_analysis":
        return _build_candidate("reasoning", preferred_role, roles)
    if financial_task_type == "catalyst_detection":
        return _build_candidate("router", preferred_role, roles)
    if financial_task_type == "rag_financial_synthesis":
        return _build_candidate("reasoning", preferred_role, roles)
    if financial_task_type == "peer_comparison" and preferred_role == "deep_reasoning":
        return _build_candidate("reasoning", preferred_role, roles)
    return _build_candidate("router", preferred_role, roles)


def _degraded_model_fallback(
    preferred_role: str,
    financial_task_type: str | None,
    roles: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if preferred_role == "router":
        return _build_candidate("router", preferred_role, roles)
    if financial_task_type in {"valuation_analysis", "rag_financial_synthesis"}:
        return _build_candidate("reasoning", preferred_role, roles)
    if financial_task_type == "peer_comparison" and preferred_role == "deep_reasoning":
        return _build_candidate("reasoning", preferred_role, roles)
    return _build_candidate("router", preferred_role, roles)


def _normalize_feedback(feedback: dict[str, Any] | None) -> dict[str, float | str]:
    payload = dict(feedback or {})
    mode = str(payload.get("mode") or "no_op").strip().lower()
    if mode not in {"no_op", "degrade_model", "prefer_fallback", "suppress_feedback"}:
        mode = "no_op"
    try:
        penalty = float(payload.get("penalty", 0.0))
    except (TypeError, ValueError):
        penalty = 0.0
    return {
        "mode": mode,
        "penalty": max(0.0, min(penalty, 1.0)),
    }


def optimize(
    *,
    task_type: str,
    financial_task_type: str | None,
    prompt_length: int,
    prompt: str,
    metadata: dict[str, Any] | None,
    deep_reasoning_requested: bool,
    router_state: RouterState,
    metrics_history: dict[str, list[dict[str, Any]]] | None,
    model_summaries: dict[str, dict[str, Any]] | None,
    task_model_summaries: dict[str, dict[str, dict[str, float | str]]] | None,
    config: dict[str, Any],
    roles: dict[str, dict[str, str]],
    feedback: dict[str, Any] | None = None,
) -> OptimalModelDecision:
    complexity = detect_complexity(prompt, metadata)
    resolved_financial_task_type = financial_task_type or _normalize_financial_task_type(metadata)
    preferred_role = _preferred_role_name(
        task_type,
        resolved_financial_task_type,
        prompt,
        prompt_length,
        deep_reasoning_requested,
        metadata=metadata,
        complexity=complexity,
        config=config,
    )
    resolved_feedback = _normalize_feedback(feedback)
    feedback_mode = str(resolved_feedback.get("mode") or "no_op")
    feedback_penalty = float(resolved_feedback.get("penalty") or 0.0)
    role_names = _candidate_role_names(task_type, preferred_role, resolved_financial_task_type)
    primary = _build_candidate(preferred_role, preferred_role, roles)

    gpu_hot = (
        router_state.gpu_utilization is not None
        and router_state.gpu_utilization >= int(config["gpu_overload_threshold"])
    )
    gpu_queue_depth = int(router_state.queue_depths.get("llm_gpu", 0)) + int(
        router_state.active_tasks.get("llm_gpu", 0)
    )
    gpu_queue_hot = gpu_queue_depth >= int(config["queue_backlog_threshold"])

    if task_type in {"embedding", "router"}:
        return OptimalModelDecision(
            model_name=primary["model_name"],
            provider=primary["provider"],
            base_url=primary["base_url"],
            queue=primary["queue"],
            confidence=0.99,
            deferred=False,
        )

    if task_type == "coding":
        return OptimalModelDecision(
            model_name=primary["model_name"],
            provider=primary["provider"],
            base_url=primary["base_url"],
            queue=primary["queue"],
            confidence=0.99,
            deferred=bool(gpu_hot or gpu_queue_hot),
        )

    benchmark_metrics = _load_benchmark_metrics()
    preferred_summary = _resolve_model_summary(
        primary["model_name"],
        resolved_financial_task_type,
        metrics_history=metrics_history,
        model_summaries=model_summaries,
        task_model_summaries=task_model_summaries,
        snapshot_summaries=_SNAPSHOT_BASELINE_SUMMARIES,
        snapshot_task_summaries=_SNAPSHOT_BASELINE_TASK_SUMMARIES,
        benchmark_metrics=benchmark_metrics,
    )
    if preferred_role != "router" and _needs_hard_router_fallback(
        preferred_summary,
        gpu_hot=gpu_hot,
        gpu_queue_hot=gpu_queue_hot,
    ):
        fallback = _fallback_candidate(preferred_role, roles)
        return OptimalModelDecision(
            model_name=fallback["model_name"],
            provider=fallback["provider"],
            base_url=fallback["base_url"],
            queue=fallback["queue"],
            confidence=0.84 if gpu_hot or gpu_queue_hot else 0.8,
            deferred=True,
        )
    if preferred_role != "router" and _performance_degraded(
        preferred_summary,
        dict(benchmark_metrics.get(primary["model_name"]) or {}),
    ):
        fallback = _degraded_model_fallback(
            preferred_role,
            resolved_financial_task_type,
            roles=roles,
        )
        return OptimalModelDecision(
            model_name=fallback["model_name"],
            provider=fallback["provider"],
            base_url=fallback["base_url"],
            queue=fallback["queue"],
            confidence=0.8,
            deferred=preferred_role == "deep_reasoning" and fallback["role_name"] != "router",
        )

    feedback_fallback = None
    if feedback_mode == "prefer_fallback" and preferred_role != "router":
        feedback_fallback = _degraded_model_fallback(
            preferred_role,
            resolved_financial_task_type,
            roles=roles,
        )
        if len(role_names) == 1 and feedback_fallback["role_name"] != preferred_role:
            return OptimalModelDecision(
                model_name=feedback_fallback["model_name"],
                provider=feedback_fallback["provider"],
                base_url=feedback_fallback["base_url"],
                queue=feedback_fallback["queue"],
                confidence=min(0.7 + feedback_penalty, 0.9),
                deferred=preferred_role == "deep_reasoning" and feedback_fallback["role_name"] != "router",
            )

    if len(role_names) == 1:
        return OptimalModelDecision(
            model_name=primary["model_name"],
            provider=primary["provider"],
            base_url=primary["base_url"],
            queue=primary["queue"],
            confidence=0.99,
            deferred=preferred_role == "deep_reasoning",
        )

    candidates = [_build_candidate(role_name, preferred_role, roles) for role_name in role_names]
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        summary = _resolve_model_summary(
            candidate["model_name"],
            resolved_financial_task_type,
            metrics_history=metrics_history,
            model_summaries=model_summaries,
            task_model_summaries=task_model_summaries,
            snapshot_summaries=_SNAPSHOT_BASELINE_SUMMARIES,
            snapshot_task_summaries=_SNAPSHOT_BASELINE_TASK_SUMMARIES,
            benchmark_metrics=benchmark_metrics,
        )
        component_scores = score_model(
            candidate["model_name"],
            router_state,
            summary,
            queue_name=candidate["queue"],
            config=config,
        )
        score = component_scores["final_score"]
        score += _candidate_fit_adjustment(candidate["role_name"], preferred_role, complexity)

        benchmark = dict(benchmark_metrics.get(candidate["model_name"]) or {})
        if _performance_degraded(summary, benchmark):
            score -= 0.25
        if candidate["queue"] == "llm_gpu" and complexity == "low":
            score -= 0.08
        if candidate["role_name"] == "router" and complexity == "high":
            score -= 0.05
        if feedback_mode == "degrade_model" and candidate["role_name"] == preferred_role:
            score *= max(0.0, 1.0 - feedback_penalty)
        elif feedback_mode == "prefer_fallback" and feedback_fallback is not None:
            if candidate["role_name"] == feedback_fallback["role_name"]:
                score += feedback_penalty
            elif candidate["role_name"] == preferred_role and feedback_fallback["role_name"] != preferred_role:
                score *= max(0.0, 1.0 - min(feedback_penalty, 0.5))

        scored.append((score, candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_score, top_candidate = scored[0]
    next_score = scored[1][0] if len(scored) > 1 else top_score
    confidence = min(max(0.5 + max(top_score - next_score, 0.0) / 1.5, 0.5), 0.99)

    return OptimalModelDecision(
        model_name=top_candidate["model_name"],
        provider=top_candidate["provider"],
        base_url=top_candidate["base_url"],
        queue=top_candidate["queue"],
        confidence=confidence,
        deferred=preferred_role == "deep_reasoning" and top_candidate["role_name"] != "router",
    )
