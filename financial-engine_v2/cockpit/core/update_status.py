from __future__ import annotations


def normalize_update_status(status: str | None) -> str:
    raw = str(status or "").strip().lower()
    if raw == "completed":
        return "success"
    return raw or "unknown"


def is_successful_update_status(status: str | None) -> bool:
    return normalize_update_status(status) == "success"

