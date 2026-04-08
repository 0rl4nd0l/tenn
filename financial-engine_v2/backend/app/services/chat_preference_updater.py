from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.services.chat_preferences import SCHEMA_VERSION


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def update_preferences(
    *,
    quality_turns: list[dict[str, Any]],
    current_prefs: dict[str, Any] | None,
    min_sample_count: int = 10,
) -> dict[str, Any]:
    """
    Build new chat preferences from accumulated quality-scored turns.

    Args:
        quality_turns: List of turn records with composite_metric, retrieval_params, router_role, etc.
        current_prefs: Existing chat_preferences.json content, or None.
        min_sample_count: Minimum turns per task type before trusting preference.

    Returns:
        New preferences dict (immutable pattern — does not mutate current_prefs).
    """
    existing_retrieval = dict((current_prefs or {}).get("retrieval_preferences", {}))
    existing_router = dict((current_prefs or {}).get("router_preferences", {}))
    existing_weights = dict((current_prefs or {}).get("metric_weights", {}))

    # Group turns by financial_task_type
    task_turns: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for turn in quality_turns:
        task_type = str(turn.get("financial_task_type") or "").strip()
        if task_type:
            task_turns[task_type].append(turn)

    now = _utc_now()

    # Update retrieval preferences
    for task_type, turns in task_turns.items():
        if len(turns) < min_sample_count:
            continue

        # Group by retrieval params, compute avg composite metric
        param_groups: dict[str, tuple[dict[str, Any], list[float]]] = {}
        for turn in turns:
            params = turn.get("retrieval_params", {})
            if not params:
                continue
            # Serialize params as key
            top_k = params.get("top_k", 10)
            commentary_weight = params.get("commentary_weight", 0.25)
            key = f"tk{top_k}_cw{commentary_weight}"

            if key not in param_groups:
                param_groups[key] = (params, [])
            param_groups[key][1].append(float(turn.get("composite_metric", 0.0)))

        # Pick params with highest avg composite metric
        if param_groups:
            best_key = max(
                param_groups,
                key=lambda k: sum(param_groups[k][1]) / len(param_groups[k][1]),
            )
            best_params, best_metrics = param_groups[best_key]
            best_avg = sum(best_metrics) / len(best_metrics)
            best_sample_count = len(best_metrics)

            prev_sample_count = 0
            if task_type in existing_retrieval:
                prev_sample_count = int(
                    existing_retrieval[task_type].get("sample_count", 0)
                )

            existing_retrieval[task_type] = {
                "top_k": int(best_params.get("top_k", 10)),
                "commentary_weight": float(best_params.get("commentary_weight", 0.25)),
                "avg_composite_metric": round(best_avg, 4),
                "sample_count": prev_sample_count + best_sample_count,
                "last_updated": now,
            }

    # Update router preferences
    for task_type, turns in task_turns.items():
        if len(turns) < min_sample_count:
            continue

        # Group by router_role, compute avg composite metric
        role_groups: dict[str, list[float]] = defaultdict(list)
        for turn in turns:
            role = str(turn.get("router_role") or "").strip()
            if role:
                role_groups[role].append(float(turn.get("composite_metric", 0.0)))

        if role_groups:
            best_role = max(
                role_groups, key=lambda r: sum(role_groups[r]) / len(role_groups[r])
            )
            best_avg = sum(role_groups[best_role]) / len(role_groups[best_role])
            best_sample_count = len(role_groups[best_role])

            prev_sample_count = 0
            if task_type in existing_router:
                prev_sample_count = int(
                    existing_router[task_type].get("sample_count", 0)
                )

            existing_router[task_type] = {
                "preferred_role": best_role,
                "avg_composite_metric": round(best_avg, 4),
                "sample_count": prev_sample_count + best_sample_count,
                "last_updated": now,
            }

    # Update metric weights (adaptive learning placeholder)
    # TODO: implement Thompson sampling or perturbation method
    # For now: preserve existing weights or use defaults
    metric_weights = existing_weights or {
        "w_retrieval": 0.4,
        "w_confidence": 0.35,
        "w_coherence": 0.25,
        "sample_count": 0,
        "last_updated": now,
    }
    if quality_turns:
        metric_weights["sample_count"] = int(
            metric_weights.get("sample_count", 0)
        ) + len(quality_turns)
        metric_weights["last_updated"] = now

    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now,
        "source_session_id": str(
            quality_turns[-1].get("session_id", "") if quality_turns else ""
        ),
        "metric_weights": metric_weights,
        "retrieval_preferences": existing_retrieval,
        "router_preferences": existing_router,
        "min_sample_count": min_sample_count,
    }
