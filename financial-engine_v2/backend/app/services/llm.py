from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.embeddings import embed_texts_batched
from app.services.llamacpp_runtime import (
    generate_json_llamacpp,
    resolve_llm_runtime_config,
)
from app.services import router_metrics, router_state
from app.services.router import RoutingDecision, load_model_routing_config, route_request


logger = logging.getLogger(__name__)


def _log_route(operation: str, decision: RoutingDecision, payload_size: int) -> None:
    logger.info(
        "llm_route operation=%s task_type=%s queue=%s model=%s provider=%s deferred=%s confidence=%s payload_size=%s gpu_util=%s",
        operation,
        decision.task_type,
        decision.execution_queue,
        decision.model_name,
        decision.provider,
        decision.deferred,
        f"{decision.confidence:.3f}",
        payload_size,
        decision.gpu_utilization_percent,
    )


def _normalize_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return dict(value[0])
    raise RuntimeError(f"Model response is not a JSON object: {type(value).__name__}")


def _unwrap_generation_result(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(value, dict) and "payload" in value:
        payload = _normalize_json_object(value.get("payload"))
        metadata = value.get("metrics")
        return payload, dict(metadata) if isinstance(metadata, dict) else {}
    return _normalize_json_object(value), {}


def _resolve_tokens_generated(payload: dict[str, Any], metrics: dict[str, Any]) -> int:
    for key in ("tokens_generated", "completion_tokens", "eval_count"):
        value = metrics.get(key)
        if value is None:
            continue
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            continue

    try:
        serialized = json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError):
        serialized = str(payload)
    return max(len(serialized) // 4, 1)


def get_routing_decision(prompt: str, metadata: dict[str, Any] | None = None) -> RoutingDecision:
    return route_request(prompt, metadata)


def _resolve_runtime_from_metadata(metadata: dict[str, Any] | None) -> tuple[str, str]:
    payload = dict(metadata or {})
    return resolve_llm_runtime_config(
        base_url=payload.get("requested_base_url") or payload.get("llm_url"),
        model=payload.get("requested_model") or payload.get("llm_model"),
    )


def _should_force_llamacpp(metadata: dict[str, Any] | None) -> bool:
    payload = dict(metadata or {})
    if str(payload.get("component") or "").strip().lower() == "commentary_memo_extractor":
        return True
    return any(
        str(payload.get(key) or "").strip()
        for key in ("requested_base_url", "requested_model", "llm_url", "llm_model")
    )


def _effective_llamacpp_decision(
    decision: RoutingDecision,
    *,
    base_url: str,
    model_name: str,
) -> RoutingDecision:
    return RoutingDecision(
        model_name=model_name,
        execution_queue=decision.execution_queue,
        task_type=decision.task_type,
        financial_task_type=decision.financial_task_type,
        provider="llamacpp",
        base_url=base_url,
        deferred=decision.deferred,
        gpu_utilization_percent=decision.gpu_utilization_percent,
        confidence=decision.confidence,
    )


def _resolved_model_name_for_metrics(
    decision: RoutingDecision,
    metadata: dict[str, Any] | None,
) -> str:
    if decision.provider != "llamacpp":
        return decision.model_name
    _, resolved_model = _resolve_runtime_from_metadata(metadata)
    return resolved_model


def _failure_reason(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return f"http_{exc.response.status_code}"
    return exc.__class__.__name__.strip().lower()


def _should_retry_with_fallback(
    decision: RoutingDecision,
    metadata: dict[str, Any] | None,
    exc: Exception,
    *,
    attempted_fallback: bool,
) -> bool:
    if attempted_fallback or _should_force_llamacpp(metadata):
        return False
    if decision.task_type not in {"reasoning", "coding"}:
        return False
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.HTTPError)


def _fallback_decision_for_failure(
    decision: RoutingDecision,
    metadata: dict[str, Any] | None,
) -> RoutingDecision:
    config = load_model_routing_config()
    if decision.task_type == "reasoning":
        if decision.model_name != config.router.model_name:
            return RoutingDecision(
                model_name=config.router.model_name,
                execution_queue="llm_cpu",
                task_type=decision.task_type,
                financial_task_type=decision.financial_task_type,
                provider=config.router.provider,
                base_url=config.router.base_url,
                deferred=True,
                gpu_utilization_percent=decision.gpu_utilization_percent,
                queue_depth_at_dispatch=decision.queue_depth_at_dispatch,
                confidence=min(decision.confidence, 0.75),
            )
        resolved_base_url, resolved_model = _resolve_runtime_from_metadata(metadata)
        return RoutingDecision(
            model_name=resolved_model,
            execution_queue="llm_cpu",
            task_type=decision.task_type,
            financial_task_type=decision.financial_task_type,
            provider="llamacpp",
            base_url=resolved_base_url,
            deferred=True,
            gpu_utilization_percent=decision.gpu_utilization_percent,
            queue_depth_at_dispatch=decision.queue_depth_at_dispatch,
            confidence=min(decision.confidence, 0.75),
        )
    if decision.task_type == "coding":
        return RoutingDecision(
            model_name=config.coding.model_name,
            execution_queue="llm_gpu",
            task_type=decision.task_type,
            financial_task_type=decision.financial_task_type,
            provider=config.coding.provider,
            base_url=config.coding.base_url,
            deferred=True,
            gpu_utilization_percent=decision.gpu_utilization_percent,
            queue_depth_at_dispatch=decision.queue_depth_at_dispatch,
            confidence=min(decision.confidence, 0.8),
        )
    return decision


def _execute_generate_json(
    decision: RoutingDecision,
    *,
    prompt: str,
    metadata: dict[str, Any] | None,
    timeout: float | None,
    client: Optional[httpx.Client],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    resolved_base_url, resolved_model = _resolve_runtime_from_metadata(metadata)
    effective_timeout = float(
        timeout
        if timeout not in (None, 0, 0.0)
        else getattr(settings, "llamacpp_timeout_seconds", 120.0)
    )
    effective_timeout = max(effective_timeout, 1.0)
    effective_decision = _effective_llamacpp_decision(
        decision,
        base_url=resolved_base_url,
        model_name=resolved_model,
    )
    _log_route("generate_json", effective_decision, len(str(prompt or "")))
    resolved_model_name = resolved_model
    payload = generate_json_llamacpp(
        base_url=resolved_base_url,
        model=resolved_model,
        prompt=prompt,
        timeout=effective_timeout,
        client=client,
        include_metadata=True,
    )

    normalized_payload, metrics = _unwrap_generation_result(payload)
    return normalized_payload, metrics, resolved_model_name


def embed_texts(
    texts: list[str],
    *,
    metadata: dict[str, Any] | None = None,
    timeout: float = 180.0,
    client: Optional[httpx.Client] = None,
) -> list[list[float]]:
    decision = route_request(
        "\n".join(texts[:3]),
        {
            **dict(metadata or {}),
            "task_type": "embedding",
            "text_count": len(texts),
        },
    )
    requested_model = (
        str((metadata or {}).get("requested_model") or "").strip()
        or str((metadata or {}).get("embedding_model") or "").strip()
        or decision.model_name
    )
    _log_route("embed", decision, len(texts))
    return embed_texts_batched(
        texts,
        llm_url=decision.base_url,
        model=requested_model,
    )


def generate_json(
    prompt: str,
    *,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    decision = route_request(prompt, metadata)
    attempted_fallback = False

    while True:
        active_decision = decision
        router_state.mark_task_started(active_decision.execution_queue)
        started_at = perf_counter()

        try:
            normalized_payload, metrics, resolved_model_name = _execute_generate_json(
                active_decision,
                prompt=prompt,
                metadata=metadata,
                timeout=timeout,
                client=client,
            )
            latency_seconds = max(perf_counter() - started_at, 0.0)
            tokens_generated = _resolve_tokens_generated(normalized_payload, metrics)
            tokens_per_second = (tokens_generated / latency_seconds) if latency_seconds > 0 else 0.0
            recorded_model_name = str(metrics.get("model_name") or resolved_model_name).strip()
            router_metrics.record(
                model_name=recorded_model_name,
                task_type=active_decision.task_type,
                financial_task_type=active_decision.financial_task_type,
                latency_seconds=latency_seconds,
                tokens_generated=tokens_generated,
                tokens_per_second=tokens_per_second,
                queue_name=active_decision.execution_queue,
                gpu_utilization=active_decision.gpu_utilization_percent,
                prompt_length=len(str(prompt or "")),
                model_confidence=active_decision.confidence,
                queue_depth_at_dispatch=active_decision.queue_depth_at_dispatch,
                success=True,
            )
            logger.info(
                "llm_request_complete model=%s latency=%.3f tokens=%s tps=%.3f task_type=%s queue=%s",
                recorded_model_name,
                latency_seconds,
                tokens_generated,
                tokens_per_second,
                active_decision.task_type,
                active_decision.execution_queue,
            )
            return normalized_payload
        except Exception as exc:
            router_metrics.record(
                model_name=_resolved_model_name_for_metrics(active_decision, metadata),
                task_type=active_decision.task_type,
                financial_task_type=active_decision.financial_task_type,
                latency_seconds=max(perf_counter() - started_at, 0.0),
                tokens_generated=0,
                tokens_per_second=0.0,
                queue_name=active_decision.execution_queue,
                gpu_utilization=active_decision.gpu_utilization_percent,
                prompt_length=len(str(prompt or "")),
                model_confidence=active_decision.confidence,
                queue_depth_at_dispatch=active_decision.queue_depth_at_dispatch,
                success=False,
                failure_reason=_failure_reason(exc),
            )
            if _should_retry_with_fallback(
                active_decision,
                metadata,
                exc,
                attempted_fallback=attempted_fallback,
            ):
                fallback_decision = _fallback_decision_for_failure(active_decision, metadata)
                if fallback_decision != active_decision:
                    attempted_fallback = True
                    decision = fallback_decision
                    continue
            raise
        finally:
            router_state.mark_task_finished(active_decision.execution_queue)
