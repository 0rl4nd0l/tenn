from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any

# Actions that cannot safely run concurrently with each other.
# Each group is a set of mutually-exclusive action IDs.
_CONFLICT_GROUPS: list[set[str]] = [
    # Heavy ASX enrichment / full-history jobs all touch the same DB rows.
    {
        "full_history",
        "resume_pending",
        "asx_enrichment_sweep",
        "asx_enrichment_chunked",
        "rebuild_ticker_financials",
    },
    # Daily marketindex and market-wide ingest share the announcements table.
    {
        "daily_marketindex",
        "daily_asx_marketwide",
    },
]


def conflicting_action_ids(action_id: str) -> set[str]:
    """
    Return the set of action IDs (including action_id itself) that conflict
    with the given action_id and must not run concurrently.
    """
    for group in _CONFLICT_GROUPS:
        if action_id in group:
            return set(group)
    # An action always conflicts with itself.
    return {action_id}


def find_conflicting_job(
    action_id: str,
    jobs: list[dict[str, Any]],
    *,
    now_utc: datetime.datetime,
    stale_after_hours: float = 24.0,
) -> dict[str, Any] | None:
    """
    Scan a list of job records for a non-stale running job that conflicts
    with action_id.

    A job is considered stale (and ignored) if it has been in 'running' state
    for longer than stale_after_hours without ending.

    Returns the first non-stale conflicting job dict, or None.
    """
    conflict_ids = conflicting_action_ids(action_id)
    stale_cutoff = now_utc - datetime.timedelta(hours=stale_after_hours)

    for job in jobs:
        if job.get("status") != "running":
            continue
        if job.get("action_id") not in conflict_ids:
            continue
        started_raw = job.get("started_at")
        if not started_raw:
            continue
        try:
            started = datetime.datetime.fromisoformat(
                str(started_raw).replace("Z", "+00:00")
            )
            if started.tzinfo is None:
                started = started.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
        if started < stale_cutoff:
            # Stale — ignore
            continue
        return job

    return None


# Flags that may point to output report paths.
_REPORT_FLAG_RE = re.compile(r"--\S*report\S*", re.IGNORECASE)


def extract_report_paths(
    action_id: str,
    command: list[str],
    repo_root: Path,
) -> list[Path]:
    """
    Scan a command list for --*report* flags and return the paths they point to
    (resolved relative to repo_root).

    e.g. ["python", "script.py", "--daily-report", "reports/x.json"]
         → [repo_root / "reports/x.json"]
    """
    paths: list[Path] = []
    for i, token in enumerate(command):
        if _REPORT_FLAG_RE.match(token) and i + 1 < len(command):
            candidate = command[i + 1]
            # Skip if the next token looks like a flag
            if not candidate.startswith("-"):
                paths.append(repo_root / candidate)
    return paths


def evaluate_quality_gate(
    action_id: str,
    reports: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Evaluate post-run quality gate conditions for action_id given its report files.

    Parameters
    ----------
    action_id:
        The action that was run.
    reports:
        Dict mapping report filename → parsed JSON content.

    Returns
    -------
    (passed, reasons) where reasons lists any failing conditions.
    """
    reasons: list[str] = []

    if action_id == "update_ticker_financials":
        for name, report in reports.items():
            after = report.get("after", {})
            rows = after.get("rows")
            if rows is not None and int(rows) == 0:
                reasons.append(f"{name}: after.rows is 0 — no financial rows written")

    elif action_id == "daily_marketindex":
        for name, report in reports.items():
            gate = report.get("quality_gate", {})
            if gate.get("passed") is False:
                reasons.append(f"{name}: quality_gate.passed is False")

    elif action_id == "asx_enrichment_sweep":
        for name, report in reports.items():
            totals = report.get("totals", {})
            days = totals.get("days_completed")
            if days is not None and int(days) == 0:
                reasons.append(f"{name}: totals.days_completed is 0 — no days processed")

    passed = len(reasons) == 0
    return passed, reasons
