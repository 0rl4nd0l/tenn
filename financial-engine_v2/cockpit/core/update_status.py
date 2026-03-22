from __future__ import annotations

_SUCCESS_ALIASES = {"success", "completed"}


def normalize_update_status(status: str) -> str:
    """Normalise legacy 'completed' to canonical 'success'; lowercase everything else."""
    s = str(status).lower()
    if s == "completed":
        return "success"
    return s


def is_successful_update_status(status: str) -> bool:
    """Return True if the status string represents a successful update."""
    return normalize_update_status(status) == "success"
