from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import settings
from app.services import router_metrics


ROUTER_QUEUE_NAMES = ("ingest", "embed", "score", "llm_gpu", "llm_cpu")
ANALYZER_ALLOWED_ROOT = Path(getattr(settings, "data_root", "./data")).expanduser().resolve()
ANALYZER_REPORT_PATH = ANALYZER_ALLOWED_ROOT / "reports" / "system_analyzer" / "latest.json"
ANALYZER_SCORE_THRESHOLD = 0.45
ANALYZER_FALLBACK_PENALTY = 0.35

_ACTIVE_TASKS_LOCK = Lock()
_active_tasks: Counter[str] = Counter()


@dataclass(frozen=True)
class RouterState:
    gpu_utilization: int | None
    queue_depths: dict[str, int]
    active_tasks: dict[str, int]
    model_metrics: dict[str, list[dict[str, Any]]]
    model_summaries: dict[str, dict[str, float | str]] = field(default_factory=dict)
    model_task_summaries: dict[str, dict[str, dict[str, float | str]]] = field(
        default_factory=dict
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_generated_at(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _bounded_penalty(value: Any, default: float = 0.0) -> float:
    numeric = _coerce_float(value)
    if numeric is None:
        numeric = default
    return max(0.0, min(float(numeric), 1.0))


def _resolve_analyzer_path(
    path: str | Path | None = None,
    *,
    allowed_root: str | Path | None = None,
) -> Path:
    resolved_path = Path(path or ANALYZER_REPORT_PATH).expanduser().resolve()
    resolved_root = Path(allowed_root or ANALYZER_ALLOWED_ROOT).expanduser().resolve()
    resolved_path.relative_to(resolved_root)
    return resolved_path


def load_analyzer_report(
    path: str | Path | None = None,
    *,
    allowed_root: str | Path | None = None,
    max_age_seconds: int | None = None,
) -> Any | None:
    try:
        report_path = _resolve_analyzer_path(path, allowed_root=allowed_root)
        if not report_path.exists():
            return None

        payload = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return payload

        generated_at = _parse_generated_at(payload.get("generated_at"))
        if generated_at is None:
            return payload

        max_age = max(
            1,
            int(
                max_age_seconds
                if max_age_seconds is not None
                else getattr(settings, "analyzer_max_age_seconds", 600)
            ),
        )
        age_seconds = max((_utc_now() - generated_at).total_seconds(), 0.0)
        if age_seconds > float(max_age):
            return None
        return payload
    except Exception:
        return None


def reduce_analyzer_feedback(report: Any) -> dict[str, float | str]:
    if report is None:
        return {"mode": "no_op", "penalty": 0.0}
    if not isinstance(report, dict):
        return {"mode": "suppress_feedback", "penalty": 0.0}

    scoring = report.get("scoring")
    checks = report.get("checks")
    drifts = report.get("drifts")
    if not isinstance(scoring, dict) or not isinstance(checks, list) or not isinstance(drifts, list):
        return {"mode": "suppress_feedback", "penalty": 0.0}

    benchmark_missing = any(
        isinstance(drift, dict) and str(drift.get("kind") or "").strip().lower() == "benchmark_missing"
        for drift in drifts
    ) or any(
        isinstance(check, dict)
        and str(check.get("name") or "").strip().lower() == "benchmark_runtime"
        and str(check.get("result") or "").strip().lower() == "failed"
        and "missing" in str(check.get("details") or "").strip().lower()
        for check in checks
    )
    if benchmark_missing:
        return {"mode": "suppress_feedback", "penalty": 0.0}

    if any(
        isinstance(drift, dict) and str(drift.get("severity") or "").strip().lower() == "critical"
        for drift in drifts
    ):
        return {"mode": "prefer_fallback", "penalty": ANALYZER_FALLBACK_PENALTY}

    overall_score = _coerce_float(scoring.get("overall_score"))
    if overall_score is not None and overall_score < ANALYZER_SCORE_THRESHOLD:
        penalty = min(
            max((ANALYZER_SCORE_THRESHOLD - float(overall_score)) + 0.2, 0.2),
            0.6,
        )
        return {"mode": "degrade_model", "penalty": round(penalty, 3)}

    failed_checks = [
        check
        for check in checks
        if isinstance(check, dict) and str(check.get("result") or "").strip().lower() == "failed"
    ]
    if failed_checks:
        weighted_failures = sum(
            1.0
            for check in failed_checks
            if str(check.get("severity") or "").strip().lower() in {"high", "critical"}
        )
        penalty = min(0.15 + (0.1 * max(weighted_failures, 1.0)), 0.4)
        return {"mode": "degrade_model", "penalty": round(penalty, 3)}

    return {"mode": "no_op", "penalty": 0.0}


def get_analyzer_feedback(
    path: str | Path | None = None,
    *,
    allowed_root: str | Path | None = None,
    max_age_seconds: int | None = None,
) -> dict[str, float | str]:
    if not bool(getattr(settings, "router_feedback_enabled", True)):
        return {"mode": "no_op", "penalty": 0.0}

    feedback = reduce_analyzer_feedback(
        load_analyzer_report(
            path,
            allowed_root=allowed_root,
            max_age_seconds=max_age_seconds,
        )
    )
    return {
        "mode": str(feedback.get("mode") or "no_op"),
        "penalty": _bounded_penalty(feedback.get("penalty"), default=0.0),
    }


def _gpu_utilization_percent() -> int | None:
    override = str(os.getenv("GPU_UTILIZATION_OVERRIDE") or "").strip()
    if override:
        try:
            return int(float(override))
        except ValueError:
            return None

    command = str(settings.gpu_utilization_command or "").strip()
    if not command:
        return None

    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return None

    if result.returncode != 0:
        return None

    values: list[int] = []
    for line in str(result.stdout or "").splitlines():
        cleaned = line.strip().rstrip("%")
        if not cleaned:
            continue
        try:
            values.append(int(float(cleaned)))
        except ValueError:
            continue
    if not values:
        return None
    return max(values)


def _build_redis_client(redis_url: str | None = None) -> Any:
    resolved_url = str(redis_url or settings.celery_broker_url or "").strip()
    if not resolved_url.lower().startswith(("redis://", "rediss://", "unix://")):
        return None
    try:
        from redis import Redis

        return Redis.from_url(
            resolved_url,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            decode_responses=False,
        )
    except Exception:
        return None


def _collect_queue_depths(client: Any) -> dict[str, int]:
    depths = {queue_name: 0 for queue_name in ROUTER_QUEUE_NAMES}
    if client is None:
        return depths

    for queue_name in ROUTER_QUEUE_NAMES:
        try:
            depths[queue_name] = max(int(client.llen(queue_name)), 0)
        except Exception:
            depths[queue_name] = 0
    return depths


def mark_task_started(queue_name: str) -> None:
    queue = str(queue_name or "").strip()
    if not queue:
        return
    with _ACTIVE_TASKS_LOCK:
        _active_tasks[queue] += 1


def mark_task_finished(queue_name: str) -> None:
    queue = str(queue_name or "").strip()
    if not queue:
        return
    with _ACTIVE_TASKS_LOCK:
        current = int(_active_tasks.get(queue, 0))
        if current <= 1:
            _active_tasks.pop(queue, None)
            return
        _active_tasks[queue] = current - 1


def get_active_tasks() -> dict[str, int]:
    with _ACTIVE_TASKS_LOCK:
        active = {queue_name: 0 for queue_name in ROUTER_QUEUE_NAMES}
        active.update({queue_name: int(count) for queue_name, count in _active_tasks.items()})
        return active


def reset_runtime_state() -> None:
    with _ACTIVE_TASKS_LOCK:
        _active_tasks.clear()


def collect_router_state(redis_url: str | None = None) -> RouterState:
    client = _build_redis_client(redis_url)
    return RouterState(
        gpu_utilization=_gpu_utilization_percent(),
        queue_depths=_collect_queue_depths(client),
        active_tasks=get_active_tasks(),
        model_metrics=router_metrics.get_metrics_history(),
        model_summaries=router_metrics.get_model_summaries(),
        model_task_summaries=router_metrics.get_model_task_summaries(),
    )
