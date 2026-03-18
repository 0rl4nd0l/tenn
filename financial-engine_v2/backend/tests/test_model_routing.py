from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import router, router_optimizer
from app.services.router_state import ROUTER_QUEUE_NAMES, RouterState, get_analyzer_feedback


ROUTING_PROMPT = (
    "Provide a detailed filing summary that explains the balance sheet position and medium-term "
    "implications for investors."
)
ROUTING_METADATA = {
    "task_type": "reasoning",
    "financial_task_type": "filing_summary",
}


def _queue_map() -> dict[str, int]:
    return {queue_name: 0 for queue_name in ROUTER_QUEUE_NAMES}


def _router_state() -> RouterState:
    return RouterState(
        gpu_utilization=10,
        queue_depths=_queue_map(),
        active_tasks=_queue_map(),
        model_metrics={},
        model_summaries={},
        model_task_summaries={},
    )


def _write_model_routing_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "router_model: cpu-router",
                "router_provider: llamacpp",
                "router_base_url: http://router.local",
                "coding_model: code-gpu",
                "coding_provider: llamacpp",
                "coding_base_url: http://code.local",
                "reasoning_model: reasoning-gpu",
                "reasoning_provider: llamacpp",
                "reasoning_base_url: http://reasoning.local",
                "deep_reasoning_model: deep-gpu",
                "deep_reasoning_provider: llamacpp",
                "deep_reasoning_base_url: http://deep.local",
                "embedding_model: embed-local",
                "embedding_provider: local",
                "embedding_base_url: cpu://embed",
                "adaptive_routing: true",
                "router_strategy: adaptive",
                "metrics_snapshot_interval: 0",
                "short_prompt_chars: 20",
                "deep_prompt_chars: 1000",
                "financial_short_summary_chars: 10",
                "financial_deep_analysis_chars: 1000",
                "financial_peer_compare_chars: 2000",
                "financial_rag_deep_context_chars: 5000",
                "queue_backlog_threshold: 50",
                "gpu_overload_threshold: 95",
                "valuation_force_deep_reasoning: true",
            ]
        ),
        encoding="utf-8",
    )


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _feedback_from_artifact(path: Path, root: Path):
    return lambda: get_analyzer_feedback(
        path=path,
        allowed_root=root,
        max_age_seconds=600,
    )


def _route_with_feedback(monkeypatch: pytest.MonkeyPatch, feedback_fn) -> router.RoutingDecision:
    monkeypatch.setattr(router, "get_analyzer_feedback", feedback_fn)
    return router.route_request(ROUTING_PROMPT, ROUTING_METADATA)


@pytest.fixture
def routing_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_path = tmp_path / "config" / "model_routing.yaml"
    _write_model_routing_config(config_path)

    monkeypatch.setattr(settings, "model_routing_config", str(config_path), raising=False)
    monkeypatch.setattr(settings, "router_feedback_enabled", True, raising=False)
    monkeypatch.setattr(settings, "analyzer_max_age_seconds", 600, raising=False)
    monkeypatch.setattr(settings, "gpu_utilization_threshold", 95, raising=False)
    monkeypatch.setattr(settings, "routing_short_prompt_chars", 20, raising=False)
    monkeypatch.setattr(settings, "llamacpp_url", "http://reasoning.local", raising=False)

    monkeypatch.setattr(router, "collect_router_state", lambda: _router_state())
    monkeypatch.setattr(router.router_metrics, "configure_metrics_snapshot", lambda interval: None)
    monkeypatch.setattr(router_optimizer, "_load_benchmark_metrics", lambda: {})
    monkeypatch.setattr(router_optimizer, "_SNAPSHOT_BASELINE_SUMMARIES", {}, raising=False)
    monkeypatch.setattr(router_optimizer, "_SNAPSHOT_BASELINE_TASK_SUMMARIES", {}, raising=False)
    return tmp_path


def test_missing_analyzer_keeps_routing_identical(
    routing_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _route_with_feedback(monkeypatch, lambda: {"mode": "no_op", "penalty": 0.0})
    missing_path = routing_env / "reports" / "system_analyzer" / "latest.json"

    decision = _route_with_feedback(
        monkeypatch,
        _feedback_from_artifact(missing_path, routing_env),
    )

    assert decision == baseline


def test_stale_analyzer_keeps_routing_identical(
    routing_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _route_with_feedback(monkeypatch, lambda: {"mode": "no_op", "penalty": 0.0})
    report_path = routing_env / "reports" / "system_analyzer" / "latest.json"
    _write_report(
        report_path,
        {
            "generated_at": (datetime.now(timezone.utc) - timedelta(seconds=601)).isoformat(),
            "checks": [],
            "drifts": [],
            "scoring": {"overall_score": 0.05},
        },
    )

    decision = _route_with_feedback(
        monkeypatch,
        _feedback_from_artifact(report_path, routing_env),
    )

    assert decision == baseline


def test_malformed_analyzer_keeps_routing_identical(
    routing_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _route_with_feedback(monkeypatch, lambda: {"mode": "no_op", "penalty": 0.0})
    report_path = routing_env / "reports" / "system_analyzer" / "latest.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("{not-json", encoding="utf-8")

    decision = _route_with_feedback(
        monkeypatch,
        _feedback_from_artifact(report_path, routing_env),
    )

    assert decision == baseline


def test_low_score_analyzer_degrades_reasoning_priority(
    routing_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = _route_with_feedback(monkeypatch, lambda: {"mode": "no_op", "penalty": 0.0})
    report_path = routing_env / "reports" / "system_analyzer" / "latest.json"
    _write_report(
        report_path,
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks": [{"name": "backend_health", "result": "passed", "severity": "high"}],
            "drifts": [],
            "scoring": {"overall_score": 0.05},
        },
    )

    decision = _route_with_feedback(
        monkeypatch,
        _feedback_from_artifact(report_path, routing_env),
    )

    assert baseline.model_name == "reasoning-gpu"
    assert baseline.execution_queue == "llm_gpu"
    assert decision.model_name == "cpu-router"
    assert decision.execution_queue == "llm_cpu"


def test_critical_drift_prefers_fallback(
    routing_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = routing_env / "reports" / "system_analyzer" / "latest.json"
    _write_report(
        report_path,
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks": [],
            "drifts": [{"kind": "write_path_violation", "severity": "critical"}],
            "scoring": {"overall_score": 0.92},
        },
    )

    decision = _route_with_feedback(
        monkeypatch,
        _feedback_from_artifact(report_path, routing_env),
    )

    assert decision.model_name == "cpu-router"
    assert decision.execution_queue == "llm_cpu"
