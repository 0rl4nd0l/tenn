from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


HEAVY_ACTION_CONFLICT_GROUPS: tuple[set[str], ...] = (
    {
        "full_history",
        "update_ticker_financials",
        "rebuild_ticker_financials",
        "daily_marketindex",
        "daily_asx_marketwide",
        "asx_enrichment_sweep",
        "resume_pending",
        "recover_headed",
    },
)

REPORT_FLAGS = {"--report", "--daily-report", "--download-report", "--rollup-report"}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _get(payload: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    node: Any = payload
    for key in path:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
    return node if node is not None else default


def _parse_iso_utc(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def conflicting_action_ids(action_id: str) -> set[str]:
    out = {str(action_id or "").strip()}
    for group in HEAVY_ACTION_CONFLICT_GROUPS:
        if action_id in group:
            out.update(group)
    return out


def find_conflicting_job(
    action_id: str,
    jobs: list[dict[str, Any]],
    *,
    current_job_id: str | None = None,
    now_utc: datetime | None = None,
    stale_after_hours: int = 24,
) -> dict[str, Any] | None:
    now = now_utc or datetime.now(timezone.utc)
    stale_window = timedelta(hours=max(1, int(stale_after_hours)))
    conflicts = conflicting_action_ids(action_id)

    for row in jobs:
        if not isinstance(row, dict):
            continue
        row_job_id = str(row.get("job_id") or "").strip()
        if current_job_id and row_job_id == str(current_job_id):
            continue

        row_action = str(row.get("action_id") or "").strip()
        if row_action not in conflicts:
            continue

        status = str(row.get("status") or "").strip().lower()
        if status not in {"queued", "running"}:
            continue
        if str(row.get("ended_at") or "").strip():
            continue

        started_at = _parse_iso_utc(str(row.get("started_at") or ""))
        if started_at is not None and now - started_at > stale_window:
            continue

        return {
            "job_id": row_job_id or "unknown",
            "action_id": row_action or "unknown",
            "status": status or "unknown",
            "started_at": str(row.get("started_at") or ""),
        }
    return None


def extract_report_paths(action_id: str, command: list[str], repo_root: Path) -> list[Path]:
    out: list[Path] = []
    for idx, token in enumerate(command):
        if token not in REPORT_FLAGS:
            continue
        if idx + 1 >= len(command):
            continue
        raw = str(command[idx + 1]).strip()
        if not raw or raw.startswith("--"):
            continue
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        out.append(path)

    if action_id == "recover_headed":
        out.append((repo_root / "reports" / "marketindex_headed_recovery_report.json").resolve())

    dedup: list[Path] = []
    seen: set[str] = set()
    for p in out:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(p)
    return dedup


def load_json_reports(paths: list[Path]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    reports: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for path in paths:
        if not path.exists():
            missing.append(str(path))
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            missing.append(str(path))
            continue
        if isinstance(payload, dict):
            reports[str(path)] = payload
        else:
            missing.append(str(path))
    return reports, missing


def evaluate_quality_gate(action_id: str, reports: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
    if not reports:
        return False, ["no report JSON found for quality gate"]

    reasons: list[str] = []
    primary = next(iter(reports.values()))
    status = str(primary.get("status") or "").strip().lower()
    if status and status != "success":
        reasons.append(f"report status is '{status}'")

    if action_id == "update_ticker_financials":
        after_rows = _as_int(_get(primary, ("after", "rows"), 0), default=0)
        if after_rows <= 0:
            reasons.append("after.rows is 0")

    elif action_id == "daily_marketindex":
        skip_download = bool(_get(primary, ("settings", "skip_download"), False))
        if not skip_download:
            download_report = None
            for payload in reports.values():
                if "quality_gate" in payload and ("downloaded" in payload or "success_ratio" in payload):
                    download_report = payload
                    break
            if download_report is None:
                reasons.append("download report missing for quality gate")
            else:
                passed = bool(_get(download_report, ("quality_gate", "passed"), False))
                if not passed:
                    reasons.append("download quality_gate.passed is false")
                downloaded = _as_int(_get(download_report, ("downloaded",), 0))
                min_download = _as_int(_get(download_report, ("quality_gate", "min_download_count"), 1), default=1)
                if downloaded < max(1, min_download):
                    reasons.append(
                        f"downloaded={downloaded} is below minimum expected {max(1, min_download)}"
                    )

    elif action_id == "asx_enrichment_sweep":
        days_completed = _as_int(_get(primary, ("totals", "days_completed"), 0))
        if days_completed <= 0:
            reasons.append("totals.days_completed is 0")
        total_errors = _as_int(_get(primary, ("totals", "errors"), 0))
        if total_errors > 0:
            reasons.append(f"totals.errors={total_errors}")

    elif action_id == "daily_asx_marketwide":
        discovered = _as_int(_get(primary, ("discovery", "found"), 0))
        inserted = _as_int(_get(primary, ("insert", "inserted"), 0))
        processed = _as_int(_get(primary, ("processing", "processed"), 0))
        request_fail = _as_int(_get(primary, ("discovery", "provider_metrics", "request_fail"), 0))
        if discovered <= 0 and inserted <= 0 and processed <= 0:
            reasons.append("no discovery/insert/process delta observed")
        if request_fail > 0 and inserted == 0:
            reasons.append("discovery request failures with zero inserts")

    elif action_id == "full_history":
        found = _as_int(_get(primary, ("backfill", "totals", "found"), 0))
        inserted = _as_int(_get(primary, ("backfill", "totals", "inserted"), 0))
        processed = _as_int(_get(primary, ("backfill", "totals", "processed"), 0))
        if found <= 0 and inserted <= 0 and processed <= 0:
            reasons.append("no backfill delta observed")

    elif action_id == "rebuild_ticker_financials":
        selected = _as_int(_get(primary, ("selected_count",), 0))
        processed = _as_int(_get(primary, ("processed_count",), 0))
        if selected <= 0:
            reasons.append("selected_count is 0")
        elif processed <= 0:
            reasons.append("processed_count is 0")

    elif action_id == "resume_pending":
        total_errors = _as_int(_get(primary, ("totals", "errors"), 0))
        if total_errors > 0:
            reasons.append(f"totals.errors={total_errors}")

    elif action_id == "recover_headed":
        selected = _as_int(_get(primary, ("selected_total",), 0))
        recovered = _as_int(_get(primary, ("recovered",), 0))
        failed = _as_int(_get(primary, ("failed",), 0))
        if selected <= 0:
            reasons.append("selected_total is 0")
        if recovered <= 0 and failed > 0:
            reasons.append("recovered is 0 with failures present")

    elif action_id == "sort_asx_docs":
        results = primary.get("results") if isinstance(primary.get("results"), list) else []
        classified_total = 0
        for item in results:
            if isinstance(item, dict):
                classified_total += _as_int(item.get("classified_count"), 0)
        if results and classified_total <= 0:
            reasons.append("classified_count total is 0")

    elif action_id == "audit_ticker_financials":
        low_confidence_count = _as_int(_get(primary, ("low_confidence_count",), 0))
        max_allowed = _as_int(_get(primary, ("settings", "max_low_confidence"), 1000000), 1000000)
        if low_confidence_count > max_allowed:
            reasons.append(f"low_confidence_count={low_confidence_count} exceeds max={max_allowed}")

    # Non-fatal sanity check for ratio-like fields when present.
    ratio = _get(primary, ("quality_gate", "min_success_ratio"))
    if ratio is not None:
        min_ratio = _as_float(ratio, default=0.0)
        if min_ratio < 0.0 or min_ratio > 1.0:
            reasons.append("quality gate min_success_ratio is outside [0,1]")

    return len(reasons) == 0, reasons
