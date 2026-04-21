from __future__ import annotations

import atexit
import json
import logging
import os
from collections import defaultdict, deque
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock, Thread
from time import time
from typing import Any

from app.core.config import settings


DEFAULT_MAX_ENTRIES_PER_MODEL = 1000
DEFAULT_SUMMARY_WINDOW = 50
DEFAULT_METRICS_SNAPSHOT_INTERVAL = 20


_LOGGER = logging.getLogger(__name__)


def _default_reports_dir() -> Path:
    candidates = [
        Path(getattr(settings, "data_root", "/data")).expanduser().resolve() / "reports",
        Path(__file__).resolve().parents[2] / "reports",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if os.access(candidate, os.W_OK | os.X_OK):
                return candidate
        except OSError:
            continue
    return candidates[0]


_REPORTS_DIR = _default_reports_dir()
_DEFAULT_SNAPSHOT_PATH = _REPORTS_DIR / "router_metrics_snapshot.json"

_METRICS_LOCK = Lock()
_metrics_history: dict[str, deque[dict[str, Any]]] = defaultdict(
    lambda: deque(maxlen=DEFAULT_MAX_ENTRIES_PER_MODEL)
)
_metrics_summaries: dict[str, dict[str, float | str]] = {}
_metrics_task_history: dict[str, dict[str, deque[dict[str, Any]]]] = defaultdict(
    lambda: defaultdict(lambda: deque(maxlen=DEFAULT_MAX_ENTRIES_PER_MODEL))
)
_metrics_task_summaries: dict[str, dict[str, dict[str, float | str]]] = {}
_snapshot_path: Path = _DEFAULT_SNAPSHOT_PATH
_snapshot_interval = DEFAULT_METRICS_SNAPSHOT_INTERVAL
_snapshot_request_count = 0


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _resolve_snapshot_path(path: str | Path | None = None) -> Path:
    return Path(str(path or _snapshot_path)).expanduser().resolve()


def _normalize_snapshot_summary(metrics: dict[str, Any]) -> dict[str, float]:
    if not isinstance(metrics, dict):
        return {}
    sample_count = int(_coerce_float(metrics.get("sample_count")))
    if sample_count < 0:
        sample_count = 0
    return {
        "avg_latency_seconds": _coerce_float(metrics.get("avg_latency_seconds")),
        "avg_tokens_per_second": _coerce_float(metrics.get("avg_tokens_per_second")),
        "error_rate": _coerce_float(metrics.get("error_rate")),
        "timeout_rate": _coerce_float(metrics.get("timeout_rate")),
        "sample_size": float(sample_count),
    }


def _snapshot_payload() -> dict[str, Any]:
    with _METRICS_LOCK:
        models = {
            model_name: {
                "avg_latency_seconds": float(summary.get("avg_latency_seconds", 0.0)),
                "avg_tokens_per_second": float(summary.get("avg_tokens_per_second", 0.0)),
                "error_rate": float(summary.get("error_rate", 0.0)),
                "timeout_rate": float(summary.get("timeout_rate", 0.0)),
                "sample_count": int(float(summary.get("sample_size", 0.0))),
            }
            for model_name, summary in _metrics_summaries.items()
            if summary
        }
        task_summaries = {
            model_name: {
                task_name: {
                    "avg_latency_seconds": float(task_summary.get("avg_latency_seconds", 0.0)),
                    "avg_tokens_per_second": float(task_summary.get("avg_tokens_per_second", 0.0)),
                    "error_rate": float(task_summary.get("error_rate", 0.0)),
                    "timeout_rate": float(task_summary.get("timeout_rate", 0.0)),
                    "sample_count": int(float(task_summary.get("sample_size", 0.0))),
                }
                for task_name, task_summary in task_map.items()
            }
            for model_name, task_map in _metrics_task_summaries.items()
            if task_map
        }
    return {
        "models": models,
        "financial_tasks": task_summaries,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def _flush_snapshot_async() -> None:
    path = _resolve_snapshot_path(_snapshot_path)
    try:
        save_metrics_snapshot(snapshot_path=path)
    except Exception:
        _LOGGER.exception("Failed to flush metrics snapshot to %s", path)


def _schedule_snapshot_save() -> None:
    global _snapshot_request_count
    should_save = False
    with _METRICS_LOCK:
        _snapshot_request_count += 1
        if _snapshot_interval > 0 and _snapshot_request_count >= _snapshot_interval:
            _snapshot_request_count = 0
            should_save = True

    if should_save:
        Thread(target=_flush_snapshot_async, daemon=True).start()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        suffix=".tmp",
    )
    temp_path = Path(handle.name)
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        temp_path.replace(path)
    except OSError as exc:
        _LOGGER.warning("Failed to write metrics snapshot to %s: %s", path, exc)
        raise
    finally:
        with suppress(Exception):
            if not handle.closed:
                handle.close()
        with suppress(Exception):
            if temp_path.exists():
                temp_path.unlink()


def load_metrics_snapshot(
    snapshot_path: str | Path | None = None,
) -> dict[str, dict[str, float]]:
    path = _resolve_snapshot_path(snapshot_path)
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _LOGGER.warning("Ignoring corrupted router metrics snapshot %s: %s", path, exc)
        return {}

    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, dict):
        _LOGGER.warning("Ignoring invalid router metrics snapshot shape in %s", path)
        return {}

    raw_task_summaries = payload.get("financial_tasks") if isinstance(payload, dict) else None
    if not isinstance(raw_task_summaries, dict):
        raw_task_summaries = {}

    normalized: dict[str, dict[str, float]] = {}
    for model_name, metrics in raw_models.items():
        if not isinstance(model_name, str):
            continue
        values = _normalize_snapshot_summary(metrics)
        if not values:
            continue
        normalized[model_name.strip()] = values

    if not normalized:
        return {}

    normalized_task_summaries: dict[str, dict[str, dict[str, float]]] = {}
    for model_name, task_map in raw_task_summaries.items():
        if not isinstance(model_name, str) or not isinstance(task_map, dict):
            continue
        task_normalized = {}
        for task_name, metrics in task_map.items():
            if not isinstance(task_name, str) or not isinstance(metrics, dict):
                continue
            values = _normalize_snapshot_summary(metrics)
            if not values:
                continue
            task_normalized[task_name.strip()] = values
        if task_normalized:
            normalized_task_summaries[str(model_name).strip()] = task_normalized

    with _METRICS_LOCK:
        _metrics_history.clear()
        _metrics_summaries.clear()
        _metrics_task_history.clear()
        _metrics_task_summaries.clear()
        _metrics_summaries.update(normalized)
        _metrics_task_summaries.update(normalized_task_summaries)

    return normalized


def load_task_metrics_snapshot(
    snapshot_path: str | Path | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    path = _resolve_snapshot_path(snapshot_path)
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_task_summaries = payload.get("financial_tasks") if isinstance(payload, dict) else None
    if not isinstance(raw_task_summaries, dict):
        return {}

    normalized_task_summaries: dict[str, dict[str, dict[str, float]]] = {}
    for model_name, task_map in raw_task_summaries.items():
        if not isinstance(model_name, str) or not isinstance(task_map, dict):
            continue
        task_normalized = {}
        for task_name, metrics in task_map.items():
            if not isinstance(task_name, str) or not isinstance(metrics, dict):
                continue
            values = _normalize_snapshot_summary(metrics)
            if not values:
                continue
            task_normalized[task_name.strip()] = values
        if task_normalized:
            normalized_task_summaries[model_name.strip()] = task_normalized
    return normalized_task_summaries


def save_metrics_snapshot(
    snapshot_path: str | Path | None = None,
) -> None:
    path = _resolve_snapshot_path(snapshot_path)
    payload = _snapshot_payload()
    try:
        _write_json_atomic(path, payload)
    except Exception:
        _LOGGER.exception("Failed to save router metrics snapshot to %s", path)


def configure_metrics_snapshot(
    *,
    interval: int | None = None,
    snapshot_path: str | Path | None = None,
) -> None:
    global _snapshot_interval, _snapshot_path
    resolved_path = _resolve_snapshot_path(snapshot_path)
    with _METRICS_LOCK:
        _snapshot_path = resolved_path
        if interval is None:
            return
        try:
            parsed = int(interval)
        except (TypeError, ValueError):
            return
        _snapshot_interval = max(parsed, 0)


def _summarize_entries(
    entries: list[dict[str, Any]] | deque[dict[str, Any]],
    *,
    limit: int = DEFAULT_SUMMARY_WINDOW,
) -> dict[str, float | str]:
    window = list(entries)
    if limit > 0:
        window = window[-limit:]
    if not window:
        return {}

    successes = [entry for entry in window if entry.get("success", True)]
    timeout_failures = [
        entry
        for entry in window
        if str(entry.get("failure_reason") or "").strip().lower() == "timeout"
    ]
    avg_latency = sum(float(entry.get("latency_seconds") or 0.0) for entry in window) / len(window)
    avg_tps = sum(float(entry.get("tokens_per_second") or 0.0) for entry in window) / len(window)
    avg_tokens = sum(float(entry.get("tokens_generated") or 0.0) for entry in window) / len(window)
    avg_queue_depth = sum(float(entry.get("queue_depth_at_dispatch") or 0.0) for entry in window) / len(window)
    gpu_values = [float(entry["gpu_utilization"]) for entry in window if entry.get("gpu_utilization") is not None]
    summary: dict[str, float | str] = {
        "sample_size": float(len(window)),
        "avg_latency": avg_latency,
        "avg_latency_seconds": avg_latency,
        "avg_tokens_per_second": avg_tps,
        "avg_tokens_generated": avg_tokens,
        "avg_queue_depth_at_dispatch": avg_queue_depth,
        "error_rate": 1.0 - (len(successes) / len(window)),
        "timeout_rate": len(timeout_failures) / len(window),
        "last_queue_name": str(window[-1].get("queue_name") or ""),
    }
    if gpu_values:
        summary["avg_gpu_utilization"] = sum(gpu_values) / len(gpu_values)
    return summary


def record(
    *,
    model_name: str,
    task_type: str,
    financial_task_type: str | None = None,
    latency_seconds: float,
    tokens_generated: int,
    tokens_per_second: float,
    queue_name: str,
    gpu_utilization: int | None,
    prompt_length: int = 0,
    model_confidence: float = 1.0,
    queue_depth_at_dispatch: int = 0,
    timestamp: float | None = None,
    success: bool = True,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    entry = {
        "model_name": str(model_name or "").strip(),
        "task_type": str(task_type or "").strip(),
        "financial_task_type": str(financial_task_type or "").strip() or None,
        "latency_seconds": max(float(latency_seconds or 0.0), 0.0),
        "tokens_generated": max(int(tokens_generated or 0), 0),
        "tokens_per_second": max(float(tokens_per_second or 0.0), 0.0),
        "queue_name": str(queue_name or "").strip(),
        "gpu_utilization": None if gpu_utilization is None else int(gpu_utilization),
        "prompt_length": max(int(prompt_length or 0), 0),
        "model_confidence": min(max(float(model_confidence or 0.0), 0.0), 1.0),
        "queue_depth_at_dispatch": max(int(queue_depth_at_dispatch or 0), 0),
        "timestamp": float(timestamp if timestamp is not None else time()),
        "success": bool(success),
        "failure_reason": str(failure_reason or "").strip().lower(),
    }
    if not entry["model_name"]:
        raise ValueError("model_name is required")

    with _METRICS_LOCK:
        _metrics_history[entry["model_name"]].append(entry)
        _metrics_summaries[entry["model_name"]] = _summarize_entries(
            _metrics_history[entry["model_name"]]
        )
        resolved_task_type = str(entry.get("financial_task_type") or "").strip()
        if resolved_task_type:
            _metrics_task_history[entry["model_name"]][resolved_task_type].append(entry)
            _metrics_task_summaries[entry["model_name"]] = dict(
                _metrics_task_summaries.get(entry["model_name"]) or {}
            )
            _metrics_task_summaries[entry["model_name"]][resolved_task_type] = _summarize_entries(
                _metrics_task_history[entry["model_name"]][resolved_task_type]
            )

    _schedule_snapshot_save()
    return dict(entry)


def get_metrics_history() -> dict[str, list[dict[str, Any]]]:
    with _METRICS_LOCK:
        return {
            model_name: [dict(entry) for entry in entries]
            for model_name, entries in _metrics_history.items()
        }


def get_model_summaries() -> dict[str, dict[str, float | str]]:
    with _METRICS_LOCK:
        return {model_name: dict(summary) for model_name, summary in _metrics_summaries.items()}


def get_model_task_summaries() -> dict[str, dict[str, dict[str, float | str]]]:
    with _METRICS_LOCK:
        return {
            model_name: {
                task_name: dict(task_summary)
                for task_name, task_summary in task_map.items()
            }
            for model_name, task_map in _metrics_task_summaries.items()
        }


def get_model_summary(model_name: str) -> dict[str, float | str]:
    with _METRICS_LOCK:
        return dict(_metrics_summaries.get(str(model_name or "").strip()) or {})


def summarize_metrics(
    metrics_history: dict[str, list[dict[str, Any]]] | None,
    model_name: str,
    financial_task_type: str | None = None,
    *,
    limit: int = DEFAULT_SUMMARY_WINDOW,
) -> dict[str, float]:
    if financial_task_type:
        task_key = str(financial_task_type or "").strip()
        if task_key:
            with _METRICS_LOCK:
                task_entries = list(_metrics_task_history.get(model_name, {}).get(task_key, []))
                if task_entries:
                    return {
                        key: value
                        for key, value in _summarize_entries(task_entries, limit=limit).items()
                        if isinstance(value, (int, float))
                    }

    entries = list((metrics_history or {}).get(model_name, []))
    return {
        key: value
        for key, value in _summarize_entries(entries, limit=limit).items()
        if isinstance(value, (int, float))
    }


def reset_metrics_history() -> None:
    global _snapshot_request_count
    with _METRICS_LOCK:
        _metrics_history.clear()
        _metrics_summaries.clear()
        _metrics_task_history.clear()
        _metrics_task_summaries.clear()
        _snapshot_request_count = 0


def _persist_on_exit() -> None:
    try:
        save_metrics_snapshot()
    except Exception:
        _LOGGER.exception("Unable to persist router metrics snapshot on process exit")


atexit.register(_persist_on_exit)
