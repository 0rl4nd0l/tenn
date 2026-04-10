from __future__ import annotations

import fcntl
import json
import os
import shlex
import subprocess
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.services import router_metrics


ROUTER_QUEUE_NAMES = ("ingest", "embed", "score", "llm_gpu", "llm_cpu")
ANALYZER_ALLOWED_ROOT = (
    Path(getattr(settings, "data_root", "./data")).expanduser().resolve()
)
ANALYZER_REPORT_PATH = (
    ANALYZER_ALLOWED_ROOT / "reports" / "system_analyzer" / "latest.json"
)
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
    if (
        not isinstance(scoring, dict)
        or not isinstance(checks, list)
        or not isinstance(drifts, list)
    ):
        return {"mode": "suppress_feedback", "penalty": 0.0}

    benchmark_missing = any(
        isinstance(drift, dict)
        and str(drift.get("kind") or "").strip().lower() == "benchmark_missing"
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
        isinstance(drift, dict)
        and str(drift.get("severity") or "").strip().lower() == "critical"
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
        if isinstance(check, dict)
        and str(check.get("result") or "").strip().lower() == "failed"
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


_EXTRACTION_ACTIVE_KEY = "tenn:extraction_active"
_EXTRACTION_ACTIVE_TTL = 1800  # 30 min safety TTL — auto-clears if process crashes
_EXTRACTION_ACTIVE_STATE_FILE = (
    Path(
        str(
            os.getenv("TENN_EXTRACTION_ACTIVE_FILE")
            or (Path(tempfile.gettempdir()) / "tenn_extraction_active.json")
        )
    )
    .expanduser()
    .resolve()
)
_EXTRACTION_ACTIVE_LOCK_FILE = _EXTRACTION_ACTIVE_STATE_FILE.with_suffix(".lock")
_EXTRACTION_ACTIVITY_LOCK = Lock()
_legacy_extraction_activity_token: str | None = None


def _now_timestamp() -> float:
    return time.time()


def _decode_redis_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value or "")


@contextmanager
def _locked_extraction_activity_file() -> Any:
    _EXTRACTION_ACTIVE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _EXTRACTION_ACTIVE_LOCK_FILE.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _read_file_extraction_tokens(now_ts: float | None = None) -> dict[str, float]:
    now_ts = _now_timestamp() if now_ts is None else now_ts
    if not _EXTRACTION_ACTIVE_STATE_FILE.exists():
        return {}
    try:
        payload = json.loads(_EXTRACTION_ACTIVE_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    tokens = payload.get("tokens") if isinstance(payload, dict) else {}
    if not isinstance(tokens, dict):
        return {}

    active: dict[str, float] = {}
    for token, raw_expiry in tokens.items():
        try:
            expiry = float(raw_expiry)
        except (TypeError, ValueError):
            continue
        if expiry > now_ts:
            active[str(token)] = expiry
    return active


def _write_file_extraction_tokens(tokens: dict[str, float]) -> None:
    if not tokens:
        try:
            _EXTRACTION_ACTIVE_STATE_FILE.unlink()
        except FileNotFoundError:
            pass
        return

    _EXTRACTION_ACTIVE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"tokens": tokens}
    _EXTRACTION_ACTIVE_STATE_FILE.write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )


def _register_file_extraction_token(token: str, expiry_ts: float) -> None:
    now_ts = _now_timestamp()
    with _locked_extraction_activity_file():
        tokens = _read_file_extraction_tokens(now_ts)
        tokens[str(token)] = float(expiry_ts)
        _write_file_extraction_tokens(tokens)


def _clear_file_extraction_token(token: str) -> None:
    now_ts = _now_timestamp()
    with _locked_extraction_activity_file():
        tokens = _read_file_extraction_tokens(now_ts)
        tokens.pop(str(token), None)
        _write_file_extraction_tokens(tokens)


def _file_extraction_active() -> bool:
    now_ts = _now_timestamp()
    with _locked_extraction_activity_file():
        tokens = _read_file_extraction_tokens(now_ts)
        _write_file_extraction_tokens(tokens)
        return bool(tokens)


def _redis_extraction_tokens(
    client: Any, *, now_ts: float | None = None
) -> dict[str, float]:
    now_ts = _now_timestamp() if now_ts is None else now_ts
    try:
        raw_tokens = client.hgetall(_EXTRACTION_ACTIVE_KEY)
    except Exception:
        return {}

    if not isinstance(raw_tokens, dict):
        return {}

    active: dict[str, float] = {}
    stale: list[str] = []
    for raw_token, raw_expiry in raw_tokens.items():
        token = _decode_redis_value(raw_token).strip()
        if not token:
            continue
        try:
            expiry = float(_decode_redis_value(raw_expiry).strip())
        except ValueError:
            stale.append(token)
            continue
        if expiry > now_ts:
            active[token] = expiry
        else:
            stale.append(token)

    if stale:
        try:
            client.hdel(_EXTRACTION_ACTIVE_KEY, *stale)
        except Exception:
            pass
    if not active:
        try:
            client.delete(_EXTRACTION_ACTIVE_KEY)
        except Exception:
            pass
    return active


def register_extraction_activity(
    *,
    redis_url: str | None = None,
    ttl_seconds: int | None = None,
) -> str:
    ttl = max(int(ttl_seconds or _EXTRACTION_ACTIVE_TTL), 1)
    token = uuid4().hex
    expiry_ts = _now_timestamp() + ttl
    client = _build_redis_client(redis_url)
    if client is not None:
        try:
            _redis_extraction_tokens(client, now_ts=_now_timestamp())
            client.hset(_EXTRACTION_ACTIVE_KEY, token, expiry_ts)
            client.expire(_EXTRACTION_ACTIVE_KEY, ttl)
        except Exception:
            pass
    _register_file_extraction_token(token, expiry_ts)
    return token


def clear_extraction_activity(token: str, *, redis_url: str | None = None) -> None:
    token = str(token or "").strip()
    if not token:
        return
    client = _build_redis_client(redis_url)
    if client is not None:
        try:
            client.hdel(_EXTRACTION_ACTIVE_KEY, token)
            if not _redis_extraction_tokens(client, now_ts=_now_timestamp()):
                client.delete(_EXTRACTION_ACTIVE_KEY)
        except Exception:
            pass
    _clear_file_extraction_token(token)


@contextmanager
def extraction_activity(*, redis_url: str | None = None) -> Any:
    token = register_extraction_activity(redis_url=redis_url)
    try:
        yield token
    finally:
        clear_extraction_activity(token, redis_url=redis_url)


def set_extraction_active(active: bool, *, redis_url: str | None = None) -> None:
    """Signal whether a GPU-bound extraction is currently running.

    Uses a Redis key so that other processes (e.g. the chat FastAPI server)
    can detect extraction and route chat to the cloud API instead of
    competing for the single llama.cpp VRAM slot.
    """
    global _legacy_extraction_activity_token

    with _EXTRACTION_ACTIVITY_LOCK:
        if active:
            if _legacy_extraction_activity_token is None:
                _legacy_extraction_activity_token = register_extraction_activity(
                    redis_url=redis_url
                )
            return
        if _legacy_extraction_activity_token is None:
            return
        clear_extraction_activity(
            _legacy_extraction_activity_token,
            redis_url=redis_url,
        )
        _legacy_extraction_activity_token = None


def is_extraction_active(*, redis_url: str | None = None) -> bool:
    """Check whether an extraction is currently running (via Redis)."""
    client = _build_redis_client(redis_url)
    if client is not None:
        try:
            if _redis_extraction_tokens(client, now_ts=_now_timestamp()):
                return True
        except Exception:
            pass
    return _file_extraction_active()


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
        active.update(
            {queue_name: int(count) for queue_name, count in _active_tasks.items()}
        )
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
