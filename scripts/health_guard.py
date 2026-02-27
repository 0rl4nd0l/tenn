#!/usr/bin/env python3
"""
Health gate utilities for heavyweight ingestion/extraction jobs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


VALID_STATUSES = {"healthy", "warning", "degraded"}


def _degraded_snapshot(path: Path, reason: str) -> Dict[str, Any]:
    return {
        "overall_status": "degraded",
        "_health_guard": {
            "path": str(path),
            "reason": reason,
        },
    }


def load_health_snapshot(path: str) -> Dict[str, Any]:
    resolved = Path(str(path or "").strip() or "reports/research_engine_health.json").expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        print(
            f"[health-guard] warning: health snapshot missing: {resolved}; allowing execution.",
            file=sys.stderr,
        )
        return {
            "overall_status": "missing",
            "_health_guard": {
                "missing": True,
                "path": str(resolved),
            },
        }
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return _degraded_snapshot(resolved, "invalid_json")
    if not isinstance(payload, dict):
        return _degraded_snapshot(resolved, "invalid_schema_non_object")

    status = str(payload.get("overall_status") or "").strip().lower()
    if status not in VALID_STATUSES:
        return _degraded_snapshot(resolved, "invalid_schema_missing_overall_status")
    return payload


def get_overall_status(snapshot: Dict[str, Any]) -> str:
    if not isinstance(snapshot, dict):
        return "degraded"
    guard_meta = snapshot.get("_health_guard")
    if isinstance(guard_meta, dict) and bool(guard_meta.get("missing")):
        return "missing"
    status = str(snapshot.get("overall_status") or "").strip().lower()
    if status in VALID_STATUSES:
        return status
    return "degraded"


def assert_healthy(snapshot: Dict[str, Any], allow_warning: bool) -> None:
    status = get_overall_status(snapshot)
    if status == "missing":
        return
    if status == "degraded":
        raise RuntimeError("Health gate blocked execution: system degraded")
    if status == "warning" and not bool(allow_warning):
        raise RuntimeError("Health gate blocked execution: system warning state")
