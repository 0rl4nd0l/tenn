from __future__ import annotations

import datetime
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Actions that require the extraction LLM endpoint to be reachable.
EXTRACTION_ACTION_IDS: frozenset[str] = frozenset({
    "update_ticker_financials",
    "rebuild_ticker_financials",
    "metric_extraction",
    "full_history",
    "resume_pending",
    "asx_enrichment_sweep",
    "asx_enrichment_chunked",
})

# Actions where extraction only runs when process_documents=True (not default).
_CONDITIONAL_EXTRACTION_IDS: frozenset[str] = frozenset({
    "full_history",
    "resume_pending",
    "asx_enrichment_sweep",
    "asx_enrichment_chunked",
})


def check_extraction_endpoint(
    action_id: str,
    args: dict[str, Any],
    *,
    auto_load_model: bool = True,
    timeout: float = 5.0,
) -> tuple[bool, str]:
    """Pre-flight check that the extraction LLM endpoint is reachable.

    Returns ``(ok, message)``.  If *ok* is False the action should not proceed.
    When *ok* is True, *message* may contain informational status (e.g. auto-load).
    """
    if action_id not in EXTRACTION_ACTION_IDS:
        return True, ""

    # Conditional actions only need extraction when process_documents is True.
    if action_id in _CONDITIONAL_EXTRACTION_IDS and not args.get("process_documents", False):
        return True, ""

    # update_ticker_financials defaults process_documents=True; skip only if explicitly False.
    if action_id == "update_ticker_financials" and args.get("process_documents") is False:
        return True, ""

    # Resolve extraction URL (lazy import to avoid circular deps).
    extraction_url = (
        os.getenv("EXTRACTION_LLAMACPP_URL", "").strip().rstrip("/")
        or os.getenv("LLAMACPP_URL", "http://127.0.0.1:8001").strip().rstrip("/")
    )
    # Strip /v1 suffix if present (consistency with backend normalization).
    if extraction_url.endswith("/v1"):
        extraction_url = extraction_url[:-3]

    expected_model = (
        os.getenv("EXTRACT_MODEL", "").strip()
        or "qwen2.5-14b-instruct"
    )

    # Ping /v1/models.
    import urllib.error
    import urllib.request
    models_url = f"{extraction_url}/v1/models"
    try:
        with urllib.request.urlopen(models_url, timeout=timeout) as resp:
            import json
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError) as exc:
        return False, (
            f"Extraction endpoint unreachable at {extraction_url} ({exc}). "
            "Start llama-server before running extraction actions."
        )
    except Exception as exc:
        return False, f"Extraction endpoint check failed: {exc}"

    # Check if the expected extraction model is loaded.
    models = data.get("data", [])
    model_stem = expected_model.lower()

    def _is_loaded(entry: dict) -> bool:
        status = entry.get("status")
        if isinstance(status, dict):
            return status.get("value") == "loaded"
        return True  # single-model mode has no status field → model is loaded

    loaded_names = [
        entry.get("id", "") for entry in models if _is_loaded(entry)
    ]
    already_loaded = any(model_stem in name.lower() for name in loaded_names)

    if already_loaded:
        loaded_match = next(n for n in loaded_names if model_stem in n.lower())
        return True, f"Extraction ready: {loaded_match} on {extraction_url}"

    # Find the full model name from the router's model list (loaded + unloaded).
    all_names = [entry.get("id", "") for entry in models]
    matching_name = next((n for n in all_names if model_stem in n.lower()), None)

    if not auto_load_model or not matching_name:
        return False, (
            f"Extraction model '{expected_model}' not loaded. "
            f"Loaded: {loaded_names or '(none)'}. "
            f"Available: {all_names or '(none)'}. Load the model before running extraction."
        )

    # Attempt auto-load via llama.cpp router API.
    logger.info("Auto-loading extraction model '%s' (as '%s') on %s", expected_model, matching_name, extraction_url)
    try:
        from cockpit.integrations.llamacpp_manager import load_model_api
        parsed = urlparse(extraction_url)
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 8001)
        api_key = (
            os.getenv("LLM_API_KEY")
            or os.getenv("LLAMA_SERVER_API_KEY")
            or os.getenv("LLAMACPP_API_KEY")
            or "local-openai-key"
        )
        ok = load_model_api(host, port, matching_name, api_key=api_key, timeout=120.0)
        if ok:
            return True, f"Auto-loaded extraction model '{matching_name}' on {extraction_url}"
        return False, f"Failed to auto-load extraction model '{matching_name}' on {extraction_url}"
    except Exception as exc:
        return False, f"Auto-load failed: {exc}"


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
