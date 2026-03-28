from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import router_metrics
from app.services.router_optimizer import optimize
from app.services.router_state import collect_router_state, get_analyzer_feedback


_CODE_PATH_RE = re.compile(r"(?:^|[\s`])(?:/[\w./-]+|[\w./-]+\.(?:py|ts|tsx|js|jsx|md|json|yaml|yml))")
_PEER_COMPARE_TICKER_RE = re.compile(r"\b[A-Z]{2,6}\s+(?:vs|versus)\s+[A-Z]{2,6}\b")
_PATH_KEYS = {"repo_path", "repository_path", "file_path", "workspace_path", "path", "cwd"}
_CODING_HINT_PATTERNS = (
    re.compile(r"```"),
    re.compile(r"\bapply_patch\b"),
    re.compile(r"\bpatch\b"),
    re.compile(r"\bdiff --git\b"),
    re.compile(r"\bunified diff\b"),
    re.compile(r"\bstack trace\b"),
    re.compile(r"\btraceback\b"),
    re.compile(r"\brefactor\b"),
    re.compile(r"\brepository\b"),
    re.compile(r"\brepo\b"),
    re.compile(r"\bcode block\b"),
)
_REASONING_HINTS = (
    "financial analysis",
    "valuation",
    "rag",
    "retrieval",
    "research",
    "research question",
    "document synthesis",
    "summarize document",
    "announcement analysis",
    "earnings",
    "guidance",
    "risk summary",
    "transcript",
    "memo",
    "compare companies",
)
_ROUTER_HINTS = (
    "classify",
    "route this",
    "routing decision",
    "select queue",
    "select model",
    "which model",
)

_FINANCIAL_TASK_TYPES = {
    "earnings_analysis",
    "guidance_analysis",
    "capital_allocation",
    "balance_sheet_risk",
    "valuation_analysis",
    "peer_comparison",
    "filing_summary",
    "catalyst_detection",
    "rag_financial_synthesis",
}

_FINANCIAL_TASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "earnings_analysis": (
        "earnings",
        "results",
        "quarterly",
        "half year",
        "half-year",
        " fy ",
        "full year",
        "q1 ",
        " q1",
        "q2 ",
        " q2",
        "q3 ",
        " q3",
        "q4 ",
        " q4",
    ),
    "guidance_analysis": (
        "guidance",
        "outlook",
        "production guidance",
        "revised forecast",
        "forecast update",
    ),
    "capital_allocation": (
        "buyback",
        "dividend",
        "capital allocation",
        "capex",
        "acquisition",
        "dilution",
    ),
    "balance_sheet_risk": (
        " leverage",
        "debt ",
        " liquidity ",
        "refinancing",
        "covenant",
        "working capital",
        "debt stack",
        "cash burn",
    ),
    "valuation_analysis": (
        "valuation",
        "dcf",
        "ev/ebitda",
        "multiple",
        " intrinsic value",
        "roic",
        "discounted",
        "value ratio",
    ),
    "peer_comparison": (
        " vs ",
        "peer",
        "relative",
        " peers ",
        "peer group",
        "bhp vs rio",
    ),
    "filing_summary": (
        "summarize this filing",
        "announcement summary",
        "asx release",
        "10-k",
        "annual report",
        "transcript summary",
    ),
    "catalyst_detection": (
        "catalyst",
        "trigger",
        "upcoming event",
        "rerating",
        "inflection",
    ),
    "rag_financial_synthesis": (
        " rag ",
        "rag synthesis",
        "use documents",
        "based on filings",
        "retrieval",
        "source-backed synthesis",
        "retrieved context",
        "evidence from",
        "document-backed",
    ),
}

_DOCUMENT_HINT_MAP = {
    "document_type": {
        "10-k": "filing_summary",
        "annual report": "filing_summary",
        "transcript": "filing_summary",
        "announcement": "filing_summary",
        "asx release": "filing_summary",
    },
    "source_type": {
        "filing": "filing_summary",
        "transcript": "filing_summary",
        "announcements": "filing_summary",
    },
}


@dataclass(frozen=True)
class ModelRole:
    model_name: str
    provider: str
    base_url: str


@dataclass(frozen=True)
class ModelRoutingConfig:
    router: ModelRole
    coding: ModelRole
    reasoning: ModelRole
    deep_reasoning: ModelRole
    embedding: ModelRole
    adaptive_routing: bool
    router_strategy: str
    latency_weight: float
    throughput_weight: float
    error_weight: float
    queue_weight: float
    gpu_weight: float
    metrics_snapshot_interval: int
    queue_backlog_threshold: int
    gpu_overload_threshold: int
    short_prompt_chars: int
    deep_prompt_chars: int
    financial_short_summary_chars: int
    financial_deep_analysis_chars: int
    financial_peer_compare_chars: int
    financial_rag_deep_context_chars: int
    valuation_force_deep_reasoning: bool


@dataclass(frozen=True)
class RoutingDecision:
    selected_role: str
    policy_name: str
    model_name: str
    execution_queue: str
    task_type: str
    provider: str
    base_url: str
    financial_task_type: str | None = None
    deferred: bool = False
    gpu_utilization_percent: int | None = None
    queue_depth_at_dispatch: int = 0
    confidence: float = 1.0


def _policy_name_for_role(role_name: str) -> str:
    normalized = str(role_name or "").strip().lower()
    if normalized == "router":
        return "light"
    if normalized == "deep_reasoning":
        return "heavy"
    if normalized == "embedding":
        return "embedding"
    return "standard"


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value.strip()
    return value.split(" #", 1)[0].rstrip()


def _parse_scalar(value: str) -> Any:
    text = _strip_inline_comment(str(value or "").strip())
    if not text:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_flat_yaml(path: Path) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        normalized_key = str(key or "").strip()
        if not normalized_key:
            continue
        values[normalized_key] = _parse_scalar(value)
    return values


def _normalize_backend_base_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[: -len("/v1")]
    return normalized.rstrip("/")


def _resolve_provider_base_url(
    *,
    provider: str,
    configured_base_url: str,
    fallback_base_url: str,
) -> str:
    normalized_provider = str(provider or "").strip().lower()
    configured_text = str(configured_base_url or "").strip()

    if normalized_provider == "llamacpp":
        resolved = _normalize_backend_base_url(settings.llamacpp_url)
        if not resolved:
            raise ValueError("LLAMACPP_URL must be set when provider is 'llamacpp'")
        return resolved
    if normalized_provider == "ollama":
        resolved = _normalize_backend_base_url(settings.ollama_url)
        if not resolved:
            raise ValueError("OLLAMA_URL must be set when provider is 'ollama'")
        return resolved
    if normalized_provider == "local":
        return configured_text or str(fallback_base_url).strip()
    raise ValueError(f"Unknown backend: {provider}")


def _default_config() -> ModelRoutingConfig:
    return ModelRoutingConfig(
        router=ModelRole(
            model_name="qwen2.5-coder-14b",
            provider="llamacpp",
            base_url=settings.llamacpp_url,
        ),
        coding=ModelRole(
            model_name="qwen2.5-coder-14b",
            provider="llamacpp",
            base_url=settings.llamacpp_url,
        ),
        reasoning=ModelRole(
            model_name="qwen2.5-coder-14b",
            provider="llamacpp",
            base_url=settings.llamacpp_url,
        ),
        deep_reasoning=ModelRole(
            model_name="qwen2.5-coder-14b",
            provider="llamacpp",
            base_url=settings.llamacpp_url,
        ),
        embedding=ModelRole(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            provider="local",
            base_url="cpu://sentence-transformers",
        ),
        adaptive_routing=True,
        router_strategy="adaptive",
        latency_weight=0.4,
        throughput_weight=0.3,
        error_weight=0.2,
        queue_weight=0.1,
        gpu_weight=0.1,
        metrics_snapshot_interval=20,
        queue_backlog_threshold=50,
        gpu_overload_threshold=int(settings.gpu_utilization_threshold),
        short_prompt_chars=int(settings.routing_short_prompt_chars),
        deep_prompt_chars=3000,
        financial_short_summary_chars=400,
        financial_deep_analysis_chars=2500,
        financial_peer_compare_chars=1800,
        financial_rag_deep_context_chars=5000,
        valuation_force_deep_reasoning=True,
    )


def load_model_routing_config(path: str | Path | None = None) -> ModelRoutingConfig:
    defaults = _default_config()
    config_path = Path(path or settings.model_routing_config).expanduser().resolve()
    raw = _parse_flat_yaml(config_path)

    def _configured_value(key: str, fallback: Any) -> Any:
        value = raw.get(key)
        if value in {None, ""}:
            return fallback
        return value

    def _role(prefix: str, fallback: ModelRole) -> ModelRole:
        env_model = ""
        env_base_url = ""
        if prefix == "embedding":
            env_model = str(
                os.getenv("EMBEDDING_MODEL")
                or os.getenv("EMBED_MODEL")
                or ""
            ).strip()
            env_base_url = str(os.getenv("EMBEDDING_URL") or "").strip()
        provider = str(_configured_value(f"{prefix}_provider", fallback.provider)).strip().lower()
        configured_base_url = env_base_url or str(_configured_value(f"{prefix}_base_url", "")).strip()
        return ModelRole(
            model_name=env_model or str(_configured_value(f"{prefix}_model", fallback.model_name)).strip(),
            provider=provider,
            base_url=_resolve_provider_base_url(
                provider=provider,
                configured_base_url=configured_base_url,
                fallback_base_url=fallback.base_url,
            ),
        )

    return ModelRoutingConfig(
        router=_role("router", defaults.router),
        coding=_role("coding", defaults.coding),
        reasoning=_role("reasoning", defaults.reasoning),
        deep_reasoning=_role("deep_reasoning", defaults.deep_reasoning),
        embedding=_role("embedding", defaults.embedding),
        adaptive_routing=bool(_configured_value("adaptive_routing", defaults.adaptive_routing)),
        router_strategy=str(_configured_value("router_strategy", defaults.router_strategy)).strip().lower(),
        latency_weight=float(_configured_value("latency_weight", defaults.latency_weight)),
        throughput_weight=float(_configured_value("throughput_weight", defaults.throughput_weight)),
        error_weight=float(_configured_value("error_weight", defaults.error_weight)),
        queue_weight=float(_configured_value("queue_weight", defaults.queue_weight)),
        gpu_weight=float(_configured_value("gpu_weight", defaults.gpu_weight)),
        metrics_snapshot_interval=int(
            _configured_value("metrics_snapshot_interval", defaults.metrics_snapshot_interval)
        ),
        queue_backlog_threshold=int(
            _configured_value("queue_backlog_threshold", defaults.queue_backlog_threshold)
        ),
        gpu_overload_threshold=int(
            _configured_value("gpu_overload_threshold", defaults.gpu_overload_threshold)
        ),
        short_prompt_chars=int(_configured_value("short_prompt_chars", defaults.short_prompt_chars)),
        deep_prompt_chars=int(
            _configured_value(
                "deep_prompt_chars",
                _configured_value("long_context_chars", defaults.deep_prompt_chars),
            )
        ),
        financial_short_summary_chars=int(
            _configured_value(
                "financial_short_summary_chars",
                defaults.financial_short_summary_chars,
            )
        ),
        financial_deep_analysis_chars=int(
            _configured_value(
                "financial_deep_analysis_chars",
                defaults.financial_deep_analysis_chars,
            )
        ),
        financial_peer_compare_chars=int(
            _configured_value(
                "financial_peer_compare_chars",
                defaults.financial_peer_compare_chars,
            )
        ),
        financial_rag_deep_context_chars=int(
            _configured_value(
                "financial_rag_deep_context_chars",
                defaults.financial_rag_deep_context_chars,
            )
        ),
        valuation_force_deep_reasoning=bool(
            _configured_value(
                "valuation_force_deep_reasoning",
                defaults.valuation_force_deep_reasoning,
            )
        ),
    )


def _normalize_task_type(value: Any) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "embed": "embedding",
        "embeddings": "embedding",
        "classification": "router",
        "route": "router",
        "routing": "router",
        "code": "coding",
        "generation": "reasoning",
        "analysis": "reasoning",
        "deep_reasoning": "reasoning",
    }
    resolved = aliases.get(normalized, normalized)
    if resolved in {"embedding", "router", "coding", "reasoning"}:
        return resolved
    return None


def _normalize_financial_task_type(value: Any) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "capital": "capital_allocation",
        "earnings": "earnings_analysis",
        "guidance": "guidance_analysis",
        "valuation": "valuation_analysis",
        "peer": "peer_comparison",
        "catalyst": "catalyst_detection",
        "rag": "rag_financial_synthesis",
        "summary": "filing_summary",
        "filing": "filing_summary",
        "financial_summary": "filing_summary",
    }
    resolved = aliases.get(normalized, normalized)
    return resolved if resolved in _FINANCIAL_TASK_TYPES else None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_hint_value(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _finance_hint_task(metadata: dict[str, Any]) -> str | None:
    for key in ("financial_task_type", "analysis_type"):
        explicit = _normalize_financial_task_type(metadata.get(key))
        if explicit:
            return explicit

    for key in ("task_type", "request_type", "operation", "intent"):
        explicit = _normalize_financial_task_type(metadata.get(key))
        if explicit:
            return explicit

    document_type = _normalize_hint_value(metadata.get("document_type"))
    if document_type:
        mapped = _DOCUMENT_HINT_MAP["document_type"].get(document_type)
        if mapped:
            return mapped

    source_type = _normalize_hint_value(metadata.get("source_type"))
    if source_type:
        mapped = _DOCUMENT_HINT_MAP["source_type"].get(source_type)
        if mapped:
            return mapped

    return None


def _has_coding_hint(haystack: str) -> bool:
    return any(pattern.search(haystack) for pattern in _CODING_HINT_PATTERNS)


def _has_multi_company_hint(prompt: str, metadata: dict[str, Any]) -> bool:
    for key in ("ticker", "tickers", "company", "companies"):
        raw_value = str(metadata.get(key) or "")
        values = [item.strip() for item in re.split(r"[,;/|]", raw_value) if item.strip()]
        if len(values) > 1:
            return True
    return bool(_PEER_COMPARE_TICKER_RE.search(str(prompt or "")))


def _extract_financial_task_from_text(prompt: str, metadata: dict[str, Any]) -> str | None:
    haystack = " ".join(
        [
            str(prompt or ""),
            " ".join(f"{key}={value}" for key, value in sorted(metadata.items())),
        ]
    ).lower()

    if _to_int(metadata.get("retrieved_context_chars"), default=0) > 0:
        return "rag_financial_synthesis"
    if _to_int(metadata.get("document_count"), default=0) > 1 and any(
        token in haystack
        for token in ("retrieved", "retrieval", "context", "document", "filing", "synth")
    ):
        return "rag_financial_synthesis"
    if "filing" in haystack and any(token in haystack for token in ("summarize", "summary", "recap")):
        return "filing_summary"
    if _has_multi_company_hint(prompt, metadata) and any(
        token in haystack for token in ("compare", " vs ", " versus ", " peer", " peers ", "relative")
    ):
        return "peer_comparison"

    priority_tasks = (
        "rag_financial_synthesis",
        "peer_comparison",
        "filing_summary",
        "valuation_analysis",
    )
    for task_type in priority_tasks:
        keywords = _FINANCIAL_TASK_KEYWORDS.get(task_type, ())
        if any(token in haystack for token in keywords):
            return task_type

    for task_type, keywords in _FINANCIAL_TASK_KEYWORDS.items():
        if task_type in priority_tasks:
            continue
        if any(token in haystack for token in keywords):
            return task_type

    return None


def _is_deep_reasoning_requested(metadata: dict[str, Any]) -> bool:
    if metadata.get("deep_reasoning") is True:
        return True
    for key in ("task_type", "request_type", "operation", "intent"):
        value = str(metadata.get(key) or "").strip().lower().replace("-", "_").replace(" ", "_")
        if value == "deep_reasoning":
            return True
    return False


def _has_repo_path_hint(metadata: dict[str, Any]) -> bool:
    for key, value in metadata.items():
        if key.lower() in _PATH_KEYS and str(value or "").strip():
            return True
    return False


def _classify_request(
    prompt: str,
    metadata: dict[str, Any],
    config: ModelRoutingConfig,
) -> tuple[str, str | None]:
    for key in ("task_type", "request_type", "operation", "intent"):
        explicit = _normalize_task_type(metadata.get(key))
        if explicit:
            financial_task = _finance_hint_task(metadata)
            if not financial_task:
                financial_task = _extract_financial_task_from_text(prompt, metadata)
            return explicit, financial_task

    financial_task = _finance_hint_task(metadata)
    if not financial_task:
        financial_task = _extract_financial_task_from_text(prompt, metadata)

    prompt_text = str(prompt or "")
    haystack = " ".join(
        [
            prompt_text,
            " ".join(f"{key}={value}" for key, value in sorted(metadata.items())),
        ]
    ).lower()

    if _has_repo_path_hint(metadata):
        return "coding", financial_task
    if metadata.get("is_embedding") is True:
        return "embedding", financial_task
    if _normalize_task_type(metadata.get("task")) == "embedding":
        return "embedding", financial_task
    if _has_coding_hint(haystack) or _CODE_PATH_RE.search(prompt_text):
        return "coding", financial_task
    if any(token in haystack for token in _REASONING_HINTS):
        return "reasoning", financial_task
    if len(prompt_text.strip()) < config.short_prompt_chars and any(token in haystack for token in _ROUTER_HINTS):
        return "router", financial_task
    return "reasoning", financial_task


def _role_map(config: ModelRoutingConfig) -> dict[str, dict[str, str]]:
    return {
        "router": {
            "model_name": config.router.model_name,
            "provider": config.router.provider,
            "base_url": config.router.base_url,
            "queue": "llm_cpu",
        },
        "coding": {
            "model_name": config.coding.model_name,
            "provider": config.coding.provider,
            "base_url": config.coding.base_url,
            "queue": "llm_gpu",
        },
        "reasoning": {
            "model_name": config.reasoning.model_name,
            "provider": config.reasoning.provider,
            "base_url": config.reasoning.base_url,
            "queue": "llm_gpu",
        },
        "deep_reasoning": {
            "model_name": config.deep_reasoning.model_name,
            "provider": config.deep_reasoning.provider,
            "base_url": config.deep_reasoning.base_url,
            "queue": "llm_gpu",
        },
        "embedding": {
            "model_name": config.embedding.model_name,
            "provider": config.embedding.provider,
            "base_url": config.embedding.base_url,
            "queue": "embed",
        },
    }


def _static_decision(
    *,
    task_type: str,
    financial_task_type: str | None,
    prompt_length: int,
    deep_reasoning_requested: bool,
    config: ModelRoutingConfig,
    gpu_utilization: int | None,
    queue_depths: dict[str, int],
    roles: dict[str, dict[str, str]],
) -> RoutingDecision:
    role_name = task_type
    deferred = False
    if task_type == "reasoning":
        if deep_reasoning_requested:
            role_name = "deep_reasoning"
            deferred = True
        elif financial_task_type == "filing_summary":
            if prompt_length <= int(config.financial_short_summary_chars):
                role_name = "router"
            elif prompt_length > int(config.financial_deep_analysis_chars):
                role_name = "deep_reasoning"
                deferred = True
            else:
                role_name = "reasoning"
        elif financial_task_type == "valuation_analysis":
            if bool(config.valuation_force_deep_reasoning):
                role_name = "deep_reasoning"
                deferred = True
            else:
                role_name = "reasoning"
        elif financial_task_type in {"peer_comparison", "rag_financial_synthesis"}:
            if prompt_length >= int(config.financial_peer_compare_chars):
                role_name = "deep_reasoning"
                deferred = True
            else:
                role_name = "reasoning"
        elif financial_task_type in {
            "earnings_analysis",
            "guidance_analysis",
            "capital_allocation",
            "balance_sheet_risk",
            "catalyst_detection",
        }:
            if prompt_length >= int(config.financial_deep_analysis_chars):
                role_name = "deep_reasoning"
                deferred = True
            else:
                role_name = "reasoning"
        elif prompt_length > int(config.deep_prompt_chars):
            role_name = "deep_reasoning"
            deferred = True

    gpu_hot = gpu_utilization is not None and gpu_utilization >= int(config.gpu_overload_threshold)
    if gpu_hot and task_type == "reasoning" and role_name != "router":
        role_name = "router"
    role = dict(roles[role_name])
    deferred = deferred or (task_type == "coding" and gpu_hot)
    return RoutingDecision(
        selected_role=role_name,
        policy_name=_policy_name_for_role(role_name),
        model_name=role["model_name"],
        execution_queue=role["queue"],
        task_type=task_type,
        financial_task_type=financial_task_type,
        provider=role["provider"],
        base_url=role["base_url"],
        deferred=deferred,
        gpu_utilization_percent=gpu_utilization,
        queue_depth_at_dispatch=int(queue_depths.get(role["queue"], 0)),
        confidence=1.0,
    )


def route_request(prompt: str, metadata: dict[str, Any] | None = None) -> RoutingDecision:
    config = load_model_routing_config()
    router_metrics.configure_metrics_snapshot(interval=config.metrics_snapshot_interval)
    payload = dict(metadata or {})
    task_type, financial_task_type = _classify_request(prompt, payload, config)
    deep_reasoning_requested = task_type == "reasoning" and _is_deep_reasoning_requested(payload)
    prompt_length = len(str(prompt or ""))
    roles = _role_map(config)
    state = collect_router_state()
    feedback = None
    if task_type == "reasoning":
        feedback = get_analyzer_feedback()

    if config.router_strategy != "adaptive" or not config.adaptive_routing:
        return _static_decision(
            task_type=task_type,
            financial_task_type=financial_task_type,
            prompt_length=prompt_length,
            deep_reasoning_requested=deep_reasoning_requested,
            config=config,
            gpu_utilization=state.gpu_utilization,
            queue_depths=state.queue_depths,
            roles=roles,
        )

    decision = optimize(
        task_type=task_type,
        financial_task_type=financial_task_type,
        prompt_length=prompt_length,
        prompt=prompt,
        metadata=payload,
        deep_reasoning_requested=deep_reasoning_requested,
        router_state=state,
        metrics_history=state.model_metrics,
        model_summaries=state.model_summaries,
        task_model_summaries=state.model_task_summaries,
        config={
            "short_prompt_chars": config.short_prompt_chars,
            "deep_prompt_chars": config.deep_prompt_chars,
            "adaptive_routing": config.adaptive_routing,
            "latency_weight": config.latency_weight,
            "throughput_weight": config.throughput_weight,
            "error_weight": config.error_weight,
            "queue_weight": config.queue_weight,
            "gpu_weight": config.gpu_weight,
            "queue_backlog_threshold": config.queue_backlog_threshold,
            "gpu_overload_threshold": config.gpu_overload_threshold,
            "financial_short_summary_chars": config.financial_short_summary_chars,
            "financial_deep_analysis_chars": config.financial_deep_analysis_chars,
            "financial_peer_compare_chars": config.financial_peer_compare_chars,
            "financial_rag_deep_context_chars": config.financial_rag_deep_context_chars,
            "valuation_force_deep_reasoning": config.valuation_force_deep_reasoning,
        },
        roles=roles,
        feedback=feedback,
    )
    return RoutingDecision(
        selected_role=decision.role_name,
        policy_name=_policy_name_for_role(decision.role_name),
        model_name=decision.model_name,
        execution_queue=decision.queue,
        task_type=task_type,
        financial_task_type=financial_task_type,
        provider=decision.provider,
        base_url=decision.base_url,
        deferred=decision.deferred,
        gpu_utilization_percent=state.gpu_utilization,
        queue_depth_at_dispatch=int(state.queue_depths.get(decision.queue, 0)),
        confidence=decision.confidence,
    )
