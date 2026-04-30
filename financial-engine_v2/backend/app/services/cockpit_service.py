from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import re
import threading
import uuid
import time
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx
from sqlalchemy import func
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.asx_financials import ASXPeriodicFinancial
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.models.companies import Company
from app.services.cockpit_auto_flagger import (
    build_auto_flag_fingerprint,
    build_auto_flag_note,
    detect_auto_flag_findings,
)
from app.services.query_orchestrator import QueryOrchestrator

# Import cockpit core logic
from cockpit.core.actions import ActionRegistry
from cockpit.core.agent_loop import parse_backend_prefix
from cockpit.core.chat import ChatController, ChatResponse
from cockpit.core.config import (
    RuntimeFlags,
    apply_runtime_flags,
    effective_anthropic_api_key,
    load_config,
    load_env,
)
from cockpit.core.tools import ToolRouter
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.integrations.qual_context_bootstrap import (
    build_qual_context_reader,
    context_enabled,
)
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.storage.state import StateStore
from cockpit.storage.artifacts import ArtifactStore

logger = logging.getLogger(__name__)

_FLAG_REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_FLAG_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$", re.IGNORECASE)

_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|auth|authorization|token|secret|cookie|password|private[_-]?key)",
    re.IGNORECASE,
)
_BEARER_TOKEN_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]+", re.IGNORECASE)
_ANTHROPIC_BILLING_ERROR_RE = re.compile(
    r"(credit balance is too low|plans\s*&\s*billing|purchase credits)",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_flag_report_operator_writable(
    report_dir: Path,
    *,
    owner_reference: Path,
) -> None:
    """Make a flagged-report packet writable by the local workspace operator."""
    try:
        owner_stat = owner_reference.stat()
    except OSError:
        logger.warning(
            "Could not stat flagged-report owner reference",
            extra={"owner_reference": str(owner_reference)},
        )
        return

    try:
        paths = [report_dir, *report_dir.rglob("*")]
    except OSError:
        logger.warning(
            "Could not enumerate flagged-report packet for permission repair",
            extra={"report_dir": str(report_dir)},
        )
        return

    for path in paths:
        try:
            if path.is_symlink():
                continue
            if os.geteuid() == 0:
                os.chown(path, owner_stat.st_uid, owner_stat.st_gid)
            path.chmod(0o775 if path.is_dir() else 0o664)
        except OSError as exc:
            logger.warning(
                "Could not make flagged-report artifact operator-writable",
                extra={"path": str(path), "error": str(exc)},
            )


def _detect_api_provider_error(
    text: str,
    routing_metadata: dict[str, Any] | None,
) -> dict[str, str] | None:
    content = str(text or "")
    if not content or not _ANTHROPIC_BILLING_ERROR_RE.search(content):
        return None

    source = str((routing_metadata or {}).get("source") or "").strip().lower()
    if source not in {"api", "anthropic"} and "anthropic" not in content.lower():
        return None

    return {
        "provider": "anthropic",
        "code": "billing_insufficient_credit",
        "severity": "action_required",
        "title": "Anthropic credits are exhausted",
        "message": (
            "Claude API rejected the request because the Anthropic credit balance "
            "is too low. Top up Anthropic credits in Plans & Billing."
        ),
        "action_label": "Top up Anthropic credits",
    }


# Recent ASXPeriodicFinancial rows used for population / trust metrics (not total table size).
_PULSE_FINANCIAL_SAMPLE_LIMIT = 24


def _diluted_eps_value(row: ASXPeriodicFinancial) -> float | None:
    """EPS proxy: np_attributable / shares_outstanding when both are present."""
    np_ = row.np_attributable
    sh = row.shares_outstanding
    if np_ is None or sh is None:
        return None
    try:
        denom = float(sh)
        if denom == 0:
            return None
        return float(np_) / denom
    except (TypeError, ValueError):
        return None


def _matrix_cell_state(
    financial_rows: list[ASXPeriodicFinancial],
    field: str,
    stage: str,
    failed_doc_ids: set[UUID],
) -> str:
    """Classify one matrix cell: populated | abstain | failed | sparse."""
    if field == "__eps__":
        populated_rows = [r for r in financial_rows if _diluted_eps_value(r) is not None]

        def is_null(r: ASXPeriodicFinancial) -> bool:
            return _diluted_eps_value(r) is None

    else:
        populated_rows = [
            r for r in financial_rows if getattr(r, field, None) is not None
        ]

        def is_null(r: ASXPeriodicFinancial) -> bool:
            return getattr(r, field, None) is None

    if populated_rows:
        if stage == "evaluation":
            high_confidence_rows = [
                r
                for r in populated_rows
                if float(r.confidence_metrics or 0.0) >= 0.85
            ]
            return "populated" if high_confidence_rows else "abstain"
        return "populated"

    if not financial_rows:
        return "sparse"

    null_rows = [r for r in financial_rows if is_null(r)]
    if any(r.source_document_id in failed_doc_ids for r in null_rows):
        return "failed"
    return "sparse"


def _clip_text(value: Any, limit: int = 4000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _normalize_feedback_type(raw: Any) -> str:
    return "good" if str(raw or "").strip().lower() == "good" else "poor"


def _normalize_capture_kind(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in {"chat_feedback", "ui_issue", "auto_diagnostic"}:
        return value
    return "chat_feedback"


def _normalize_flag_resolution_status(raw: Any) -> str:
    return "resolved" if str(raw or "").strip().lower() == "resolved" else "open"


def _default_flag_resolution() -> dict[str, Any]:
    return {
        "status": "open",
        "resolved_at": None,
        "resolved_by": None,
        "commit_sha": None,
        "note": None,
    }


def _extract_flag_resolution(bundle: dict[str, Any] | None) -> dict[str, Any]:
    resolution_raw = (
        bundle.get("resolution") if isinstance(bundle, dict) else None
    )
    resolution = (
        dict(resolution_raw)
        if isinstance(resolution_raw, dict)
        else _default_flag_resolution()
    )
    status = _normalize_flag_resolution_status(resolution.get("status"))
    if status != "resolved":
        return _default_flag_resolution()

    commit_sha = str(resolution.get("commit_sha") or "").strip().lower() or None
    return {
        "status": "resolved",
        "resolved_at": str(resolution.get("resolved_at") or "").strip() or None,
        "resolved_by": str(resolution.get("resolved_by") or "").strip() or None,
        "commit_sha": commit_sha,
        "note": str(resolution.get("note") or "").strip() or None,
    }


def _validated_commit_sha(raw: Any) -> str:
    commit_sha = str(raw or "").strip().lower()
    if not _FLAG_COMMIT_SHA_RE.fullmatch(commit_sha):
        raise ValueError("commit_sha must be a 7-64 char git SHA")
    return commit_sha


def _sanitize_payload(value: Any, *, key: str | None = None) -> Any:
    if key and _SENSITIVE_KEY_RE.search(key):
        return "***REDACTED***"

    if isinstance(value, dict):
        return {
            str(item_key): _sanitize_payload(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return _BEARER_TOKEN_RE.sub("Bearer ***REDACTED***", value)
    return value


def _json_object_or_none(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_tool_calls(evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    passthrough_keys = (
        "id",
        "status",
        "ok",
        "error",
        "iteration",
        "duration_ms",
        "latency_ms",
        "hint",
        "reasoning",
    )
    for item in evidence or []:
        if not isinstance(item, dict) or not item.get("tool"):
            continue
        call: dict[str, Any] = {
            "tool": str(item.get("tool") or ""),
            "arguments": item.get("arguments")
            if isinstance(item.get("arguments"), dict)
            else {},
            "result": item.get("result"),
        }
        for key in passthrough_keys:
            value = item.get(key)
            if value is not None:
                call[key] = value
        calls.append(call)
    return calls


def _merge_tool_trace_metadata(
    calls: list[dict[str, Any]], tool_traces: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    if not calls:
        return calls
    trace_items = [item for item in (tool_traces or []) if isinstance(item, dict)]
    if not trace_items:
        return calls

    trace_keys = (
        "iteration",
        "ok",
        "error",
        "duration_ms",
        "hint",
        "arguments_summary",
    )
    for idx, call in enumerate(calls):
        if idx >= len(trace_items):
            break
        trace = trace_items[idx]
        for key in trace_keys:
            if call.get(key) is None and trace.get(key) is not None:
                call[key] = trace.get(key)
    return calls


def _render_flagged_summary(
    bundle: dict[str, Any], analysis: dict[str, Any] | None
) -> str:
    feedback_type = _normalize_feedback_type(bundle.get("feedback_type"))
    capture_kind = _normalize_capture_kind(bundle.get("capture_kind"))
    flagged = bundle.get("flagged_message") or {}
    request = (bundle.get("backend_turn") or {}).get("request") or {}
    routing = (bundle.get("backend_turn") or {}).get("routing_metadata") or {}
    frontend_context = (bundle.get("frontend_snapshot") or {}).get("context") or {}
    attachments = bundle.get("attachments") if isinstance(bundle.get("attachments"), list) else []
    resolution = _extract_flag_resolution(bundle)
    if capture_kind == "ui_issue":
        title = "# Cockpit UI Issue"
        response_heading = "Issue Description"
    elif capture_kind == "auto_diagnostic":
        title = "# Auto Cockpit Diagnostic"
        response_heading = "Flagged Response"
    else:
        title = (
            "# Positive Cockpit Feedback"
            if feedback_type == "good"
            else "# Flagged Cockpit Chat"
        )
        response_heading = (
            "Saved Response" if feedback_type == "good" else "Flagged Response"
        )
    lines = [title, ""]
    lines.append(f"- Report ID: `{bundle.get('report_id')}`")
    lines.append(f"- Saved At: `{bundle.get('saved_at')}`")
    lines.append(f"- Capture Kind: `{capture_kind}`")
    lines.append(f"- Feedback Type: `{feedback_type}`")
    lines.append(f"- Status: `{resolution['status']}`")
    if resolution["status"] == "resolved":
        if resolution.get("resolved_at"):
            lines.append(f"- Resolved At: `{resolution['resolved_at']}`")
        if resolution.get("resolved_by"):
            lines.append(f"- Resolved By: `{resolution['resolved_by']}`")
        if resolution.get("commit_sha"):
            lines.append(f"- Fix Commit: `{resolution['commit_sha']}`")
        if resolution.get("note"):
            lines.append(f"- Resolution Note: {resolution['note']}")
    lines.append(f"- Session ID: `{bundle.get('session_id') or 'global-main'}`")
    if bundle.get("ticker"):
        lines.append(f"- Ticker: `{bundle.get('ticker')}`")
    auto_findings = bundle.get("auto_findings")
    if isinstance(auto_findings, list) and auto_findings:
        lines.append(f"- Auto Findings: `{len(auto_findings)}`")
    route_path = str(frontend_context.get("pathname") or "").strip()
    if route_path:
        lines.append(f"- Route: `{route_path}`")
    page_title = str(frontend_context.get("page_title") or "").strip()
    if page_title:
        lines.append(f"- Page Title: `{page_title}`")
    note = str(bundle.get("note") or "").strip()
    if note:
        lines.append(f"- Note: {note}")
    model_name = str(routing.get("model") or "").strip()
    if model_name:
        lines.append(f"- Model: `{model_name}`")
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get("kind") or "") != "screenshot":
            continue
        relative_path = str(attachment.get("relative_path") or "").strip()
        absolute_path = str(attachment.get("absolute_path") or "").strip()
        screenshot_label = relative_path or absolute_path
        if screenshot_label:
            lines.append(f"- Screenshot: `{screenshot_label}`")
        break
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get("kind") or "") != "browser_debug":
            continue
        debug_label = str(
            attachment.get("relative_path") or attachment.get("absolute_path") or ""
        ).strip()
        if debug_label:
            lines.append(f"- Browser Debug: `{debug_label}`")
        break
    lines.extend(["", "## Request", "", _clip_text(request.get("message"), 1200), ""])
    lines.extend(
        [
            f"## {response_heading}",
            "",
            _clip_text(flagged.get("content"), 2400),
            "",
        ]
    )
    if analysis:
        summary = str(analysis.get("summary") or "").strip()
        if summary:
            lines.extend(["## Analysis", "", summary, ""])
        failure_modes = analysis.get("likely_failure_modes")
        if isinstance(failure_modes, list) and failure_modes:
            lines.append("## Likely Failure Modes")
            lines.append("")
            for item in failure_modes[:8]:
                lines.append(f"- {item}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _display_report_path(path: Path | str) -> str:
    raw = str(path or "").strip()
    if not raw:
        return ""
    candidate = Path(raw)
    for index, part in enumerate(candidate.parts):
        if part == "reports":
            return str(Path(*candidate.parts[index:]))
    return raw


def _build_codex_flag_prompt(
    *,
    bundle: dict[str, Any],
    analysis: dict[str, Any] | None,
    report_dir: Path,
    bundle_path: Path,
    summary_path: Path,
    read_api_path: str,
) -> str:
    feedback_type = _normalize_feedback_type(bundle.get("feedback_type"))
    capture_kind = _normalize_capture_kind(bundle.get("capture_kind"))
    flagged = bundle.get("flagged_message") or {}
    note = str(bundle.get("note") or "").strip()
    flagged_text = _clip_text(flagged.get("content"), 1200).strip()
    analysis_summary = str((analysis or {}).get("summary") or "").strip()
    attachments = bundle.get("attachments") if isinstance(bundle.get("attachments"), list) else []
    screenshot_path = ""
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get("kind") or "") != "screenshot":
            continue
        absolute_path = str(attachment.get("absolute_path") or "").strip()
        relative_path = str(attachment.get("relative_path") or "").strip()
        if absolute_path:
            screenshot_path = absolute_path
        elif relative_path:
            screenshot_path = str((report_dir / relative_path).resolve())
        break
    debug_path = ""
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get("kind") or "") != "browser_debug":
            continue
        absolute_path = str(attachment.get("absolute_path") or "").strip()
        relative_path = str(attachment.get("relative_path") or "").strip()
        if absolute_path:
            debug_path = absolute_path
        elif relative_path:
            debug_path = str((report_dir / relative_path).resolve())
        break

    report_dir_label = _display_report_path(report_dir)
    bundle_path_label = _display_report_path(bundle_path)
    summary_path_label = _display_report_path(summary_path)
    screenshot_path_label = _display_report_path(screenshot_path) if screenshot_path else ""
    debug_path_label = _display_report_path(debug_path) if debug_path else ""
    resolve_api_path = f"{read_api_path}/resolve"

    if capture_kind == "ui_issue":
        prompt_lines = [
            "Investigate this cockpit UI issue and implement the minimal safe fix.",
            "",
            f"Issue ID: {bundle.get('report_id')}",
            f"Issue directory: {report_dir_label}",
            f"Read API: {read_api_path}",
            f"Bundle: {bundle_path_label}",
            f"Summary: {summary_path_label}",
        ]
    elif capture_kind == "auto_diagnostic":
        prompt_lines = [
            "Investigate this automatically flagged cockpit diagnostic and fix the underlying issue if confirmed.",
            "",
            f"Diagnostic ID: {bundle.get('report_id')}",
            f"Diagnostic directory: {report_dir_label}",
            f"Read API: {read_api_path}",
            f"Bundle: {bundle_path_label}",
            f"Summary: {summary_path_label}",
        ]
    elif feedback_type == "good":
        prompt_lines = [
            "Review this positively rated cockpit response and capture what worked well.",
            "",
            f"Feedback ID: {bundle.get('report_id')}",
            f"Feedback directory: {report_dir_label}",
            f"Read API: {read_api_path}",
            f"Bundle: {bundle_path_label}",
            f"Summary: {summary_path_label}",
        ]
    else:
        prompt_lines = [
            "Investigate this flagged cockpit response and fix the underlying bug.",
            "",
            f"Flag ID: {bundle.get('report_id')}",
            f"Flag directory: {report_dir_label}",
            f"Read API: {read_api_path}",
            f"Bundle: {bundle_path_label}",
            f"Summary: {summary_path_label}",
        ]
    if note:
        prompt_lines.extend(["", f"User note: {note}"])
    if flagged_text:
        prompt_lines.extend(["", "Saved response:", flagged_text])
    if screenshot_path_label:
        prompt_lines.extend(["", f"Screenshot: {screenshot_path_label}"])
    if debug_path_label:
        prompt_lines.extend(["", f"Browser debug: {debug_path_label}"])
    if analysis_summary:
        prompt_lines.extend(["", f"Saved analysis summary: {analysis_summary}"])
    if capture_kind == "ui_issue":
        prompt_lines.extend(
            [
                "",
                "Check the saved screenshot, frontend context, backend runtime snapshot, and summary.",
                "Use the artifact directory on disk as the source of truth for reproduction details.",
            ]
        )
    elif capture_kind == "auto_diagnostic":
        prompt_lines.extend(
            [
                "",
                "Check the saved auto_findings, backend_turn, tool traces, routing metadata, and summary.",
                "Confirm whether the diagnostic points to a real bug or operational inefficiency before changing code.",
            ]
        )
    elif feedback_type == "good":
        prompt_lines.extend(
            [
                "",
                "Check the saved message, transcript, backend_turn, and analysis output.",
                "Identify the routing, prompting, or evidence patterns worth preserving for future training or tuning.",
            ]
        )
    else:
        prompt_lines.extend(
            [
                "",
                "Check the flagged message, transcript, backend_turn, and analysis output.",
                "Identify the root cause in code, implement the minimal safe fix, and verify it.",
            ]
        )
    if feedback_type != "good":
        prompt_lines.extend(
            [
                "",
                "After you commit the fix, mark this flag resolved with the commit SHA:",
                (
                    "curl -sS -X POST "
                    f"http://127.0.0.1:8000{resolve_api_path} "
                    "-H 'Content-Type: application/json' "
                    "-d '{\"commit_sha\":\"<git-commit-sha>\",\"resolved_by\":\"codex\","
                    "\"note\":\"<one-line-fix-summary>\"}'"
                ),
            ]
        )
    return "\n".join(prompt_lines).strip()


def _write_codex_investigation_artifacts(
    *,
    report_id: str,
    feedback_type: str,
    capture_kind: str,
    report_dir: Path,
    read_api_path: str,
    codex_prompt: str,
    created_at: str | None,
) -> dict[str, Any]:
    prompt_path = report_dir / "codex_prompt.md"
    investigation_path = report_dir / "investigation.json"
    normalized_feedback_type = _normalize_feedback_type(feedback_type)
    should_queue = normalized_feedback_type != "good"
    updated_at = _now_iso()
    deploy_command = (
        f"python scripts/cockpit_flag_investigator.py --report-id {report_id} --once --apply"
        if should_queue
        else None
    )

    prompt_path.write_text(codex_prompt.strip() + "\n", encoding="utf-8")
    investigation = {
        "schema_version": 1,
        "report_id": report_id,
        "capture_kind": _normalize_capture_kind(capture_kind),
        "feedback_type": normalized_feedback_type,
        "status": "queued" if should_queue else "not_requested",
        "mode": "operator_gated_codex_cli",
        "created_at": created_at or updated_at,
        "updated_at": updated_at,
        "read_api_path": read_api_path,
        "codex_prompt_path": str(prompt_path),
        "codex_prompt_relative_path": _display_report_path(prompt_path),
        "runner": "scripts/cockpit_flag_investigator.py",
        "suggested_command": deploy_command,
        "note": (
            "A flag queues an operator-gated Codex CLI investigation. "
            "The backend writes this packet but does not launch Codex directly."
            if should_queue
            else "Positive feedback is stored for review and does not queue a Codex investigation."
        ),
    }
    investigation_path.write_text(
        json.dumps(_sanitize_payload(investigation), indent=2, default=str),
        encoding="utf-8",
    )
    return {
        "codex_prompt_path": str(prompt_path),
        "investigation_path": str(investigation_path),
        "investigation_status": investigation["status"],
        "codex_cli_command": deploy_command,
    }


def _persist_feedback_screenshot(
    *,
    report_dir: Path,
    screenshot: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(screenshot, dict):
        return None

    data_url = str(screenshot.get("data_url") or "").strip()
    if not data_url:
        return None

    match = re.match(
        r"^data:(image/(?:png|jpeg));base64,(?P<data>[A-Za-z0-9+/=\s]+)$",
        data_url,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValueError("Screenshot must be a base64 data URL (png or jpeg)")

    mime_type = str(match.group(1) or "").strip().lower()
    encoded = re.sub(r"\s+", "", str(match.group("data") or ""))
    try:
        blob = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Screenshot payload is not valid base64") from exc

    if not blob:
        raise ValueError("Screenshot payload is empty")
    if len(blob) > 10 * 1024 * 1024:
        raise ValueError("Screenshot payload exceeds 10MB limit")

    suffix = ".jpg" if mime_type == "image/jpeg" else ".png"
    filename = str(screenshot.get("filename") or "").strip() or f"ui-screenshot{suffix}"
    filename = Path(filename).name
    if not filename.lower().endswith(suffix):
        filename = f"{Path(filename).stem}{suffix}"

    output_path = (report_dir / filename).resolve()
    output_path.write_bytes(blob)

    width = screenshot.get("width")
    height = screenshot.get("height")
    return {
        "kind": "screenshot",
        "filename": filename,
        "mime_type": mime_type,
        "relative_path": filename,
        "absolute_path": str(output_path),
        "byte_size": len(blob),
        "width": int(width) if isinstance(width, (int, float)) else None,
        "height": int(height) if isinstance(height, (int, float)) else None,
        "captured_at": str(screenshot.get("captured_at") or "").strip() or None,
    }


def _persist_browser_debug_bundle(
    *,
    report_dir: Path,
    frontend_context: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    context_payload = dict(frontend_context) if isinstance(frontend_context, dict) else {}
    debug_bundle = context_payload.pop("debug_bundle", None)
    if debug_bundle is None:
        return context_payload, None

    sanitized_debug_bundle = _sanitize_payload(debug_bundle)
    debug_path = (report_dir / "browser-debug.json").resolve()
    debug_path.write_text(
        json.dumps(sanitized_debug_bundle, indent=2, default=str),
        encoding="utf-8",
    )
    return (
        context_payload,
        {
            "kind": "browser_debug",
            "filename": "browser-debug.json",
            "mime_type": "application/json",
            "relative_path": "browser-debug.json",
            "absolute_path": str(debug_path),
        },
    )


def _write_flagged_report_files(
    *,
    bundle_path: Path,
    summary_path: Path,
    analysis_path: Path,
    bundle: dict[str, Any],
    analysis: dict[str, Any] | None,
) -> None:
    bundle_path.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    summary_path.write_text(
        _render_flagged_summary(bundle, analysis),
        encoding="utf-8",
    )
    if analysis is not None:
        analysis_path.write_text(
            json.dumps(analysis, indent=2, default=str),
            encoding="utf-8",
        )


class _BackendFinancialTruthProvider:
    def __init__(self, backend_api_client: BackendApiClient) -> None:
        self._client = backend_api_client

    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]:
        ticker = str(entities.get("primary_ticker") or "").strip().upper()
        if not ticker:
            return {
                "source": "financial_truth",
                "status": "no_entity",
                "items": [],
                "query": query,
                "intent": intent,
            }
        recovery_level = str(entities.get("recovery_level") or "").strip().lower()
        deep_recovery = recovery_level == "deep"
        docs_limit = 24 if deep_recovery else 8
        financials_limit = 24 if deep_recovery else 8
        announcements_limit = 24 if deep_recovery else 8
        failures_limit = 20 if deep_recovery else 8
        low_confidence_limit = 20 if deep_recovery else 8
        try:
            payload = self._client.get_ticker_context(
                ticker,
                docs_limit=docs_limit,
                financials_limit=financials_limit,
                announcements_limit=announcements_limit,
                failures_limit=failures_limit,
                low_confidence_limit=low_confidence_limit,
            )
        except Exception as exc:
            return {
                "source": "financial_truth",
                "status": "error",
                "items": [],
                "ticker": ticker,
                "error": str(exc),
                "query": query,
                "intent": intent,
            }

        errors = payload.get("errors") or []
        status = "partial_error" if errors else "ok"
        return {
            "source": "financial_truth",
            "status": status,
            "ticker": ticker,
            "items": payload.get("financials") or [],
            "docs": payload.get("docs") or [],
            "financials": payload.get("financials") or [],
            "latest_financial_snapshot": payload.get("latest_financial_snapshot") or {},
            "announcement_context": payload.get("announcement_context") or [],
            "extraction_failures": payload.get("extraction_failures") or [],
            "low_confidence_financials": payload.get("low_confidence_financials") or [],
            "errors": errors,
            "query": query,
            "intent": intent,
        }


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y"}


def _resolve_repo_root() -> Path:
    override = str(os.getenv("COCKPIT_REPO_ROOT") or "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())

    backend_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            backend_root.parent,
            Path("/workspace/financial-engine_v2"),
        ]
    )

    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if (
            (resolved / "config" / "cockpit.yaml").is_file()
            or (resolved / ".env").is_file()
            or str(resolved) == "/"
        ):
            return resolved

    return backend_root.parent.resolve()


def _resolve_config_path(config_path_value: str, repo_root: Path) -> Path:
    configured = Path(str(config_path_value or "").strip() or "config/cockpit.yaml")
    if configured.is_absolute():
        return configured.resolve()

    candidates = [
        (repo_root / configured).resolve(),
        (Path("/") / configured).resolve(),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return candidates[0]


def _normalize_cockpit_artifact_dirs(
    cfg: dict[str, Any], *, data_root: str | Path | None = None
) -> None:
    reports_cfg = cfg.setdefault("reports", {})
    exports_cfg = cfg.setdefault("exports", {})

    raw_reports = str(reports_cfg.get("dir") or "reports").strip() or "reports"
    raw_exports = str(exports_cfg.get("dir") or "reports/analysis").strip() or "reports/analysis"

    reports_path = Path(raw_reports).expanduser()
    exports_path = Path(raw_exports).expanduser()

    canonical_reports_root = (
        Path(str(data_root or getattr(settings, "data_root", "/data"))).expanduser().resolve()
        / "reports"
    )

    if reports_path.is_absolute():
        resolved_reports_dir = reports_path.resolve()
    else:
        if reports_path.parts and reports_path.parts[0] == "reports":
            reports_suffix = Path(*reports_path.parts[1:])
        else:
            reports_suffix = reports_path
        resolved_reports_dir = (canonical_reports_root / reports_suffix).resolve()

    if exports_path.is_absolute():
        resolved_exports_dir = exports_path.resolve()
    else:
        if exports_path.parts and exports_path.parts[0] == "reports":
            exports_suffix = Path(*exports_path.parts[1:])
        else:
            exports_suffix = exports_path
        resolved_exports_dir = (resolved_reports_dir / exports_suffix).resolve()

    reports_cfg["dir"] = str(resolved_reports_dir)
    exports_cfg["dir"] = str(resolved_exports_dir)


def _normalize_database_url(repo_root: Path, database_url: str) -> str:
    value = (database_url or "").strip()
    if not value:
        value = "sqlite:///./data/fe_local.db"

    if value.startswith("sqlite:///"):
        path_part = value[len("sqlite:///") :]
        if path_part.startswith("./") or not path_part.startswith("/"):
            resolved = (repo_root / path_part).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{resolved}"

        abs_path = Path(path_part)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return value

    return value


class CockpitService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        repo_root = _resolve_repo_root()
        load_env(repo_root)

        config_path_value = str(
            os.getenv("COCKPIT_CONFIG") or "config/cockpit.yaml"
        ).strip()
        config_path = _resolve_config_path(config_path_value, repo_root)
        runtime_profile = str(os.getenv("COCKPIT_PROFILE") or "default").strip() or "default"
        runtime_read_only = _env_flag("COCKPIT_READ_ONLY", False)
        runtime_no_web = _env_flag("COCKPIT_NO_WEB", False)

        cfg = load_config(str(config_path))
        cfg = apply_runtime_flags(
            cfg,
            RuntimeFlags(
                config_path=str(config_path),
                profile=runtime_profile,
                read_only=runtime_read_only,
                no_web=runtime_no_web,
                repo_root=repo_root,
            ),
        )
        _normalize_cockpit_artifact_dirs(cfg)

        db_cfg = cfg.get("db") if isinstance(cfg.get("db"), dict) else {}
        db_url = _normalize_database_url(
            repo_root, str(db_cfg.get("database_url") or "")
        )
        cfg.setdefault("db", {})
        cfg["db"]["database_url"] = db_url

        llm_cfg = cfg.get("llm") if isinstance(cfg.get("llm"), dict) else {}
        llm_provider = str(llm_cfg.get("provider") or "llamacpp").strip().lower()
        llm_model = str(llm_cfg.get("model") or "").strip()
        if llm_provider == "llamacpp":
            llm_url = str(llm_cfg.get("llamacpp_url") or "").strip()
        else:
            llm_url = str(
                llm_cfg.get("llamacpp_url") or llm_cfg.get("ollama_url") or ""
            ).strip()

        backend_cfg = cfg.get("backend") if isinstance(cfg.get("backend"), dict) else {}
        backend_api_url = str(backend_cfg.get("api_base_url") or "").strip()

        self.repo_root = repo_root
        self._config_path = config_path
        self._runtime_profile = runtime_profile
        self._runtime_read_only = runtime_read_only
        self._runtime_no_web = runtime_no_web
        self.config = cfg
        self.llm_timeout_seconds = float(llm_cfg.get("timeout_seconds", 300))
        self.artifact_store = ArtifactStore(
            repo_root=repo_root,
            exports_dir=cfg["exports"]["dir"],
            reports_dir=cfg["reports"]["dir"],
        )
        self.state_store = StateStore(cfg["memory"]["state_db"])
        self.db_reader = DbReader(db_url)
        self.file_indexer = FileIndexer(cfg["paths"]["allow_roots"])
        self.web_fetcher = WebFetcher()

        self.llm_client = LlamaCppClient(
            llm_url,
            llm_model,
            api_key=str(llm_cfg.get("llamacpp_api_key") or ""),
        )
        self._preload_preferred_model_async(
            preferred_model=llm_model,
            api_key=str(llm_cfg.get("llamacpp_api_key") or ""),
            llm_provider=llm_provider,
        )

        self.action_registry = ActionRegistry(
            repo_root=repo_root,
            confirm_required=cfg["actions"].get("confirm_required", True),
        )

        self.backend_api_client = None
        self.query_orchestrator = None
        if backend_api_url:
            self.backend_api_client = BackendApiClient(
                base_url=backend_api_url,
                api_key=str(backend_cfg.get("api_key") or "").strip(),
            )
            self.query_orchestrator = QueryOrchestrator(
                financial_truth_provider=_BackendFinancialTruthProvider(
                    self.backend_api_client
                )
            )

        rag_cfg = cfg.get("rag") if isinstance(cfg.get("rag"), dict) else {}
        qual_company = None
        qual_news = None
        if self.backend_api_client is not None:
            qc_cfg = (
                rag_cfg.get("qualitative_context")
                if isinstance(rag_cfg.get("qualitative_context"), dict)
                else None
            )
            if context_enabled(qc_cfg, default=False):
                try:
                    qual_company = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=qc_cfg,
                        backend_api_client=self.backend_api_client,
                        context_name="qualitative_context",
                    )
                except Exception as exc:
                    logger.warning(
                        "CockpitService: qual_context (company) disabled: %s", exc
                    )

            news_cfg = (
                rag_cfg.get("news_context")
                if isinstance(rag_cfg.get("news_context"), dict)
                else None
            )
            if context_enabled(news_cfg, default=False):
                try:
                    qual_news = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=news_cfg,
                        backend_api_client=self.backend_api_client,
                        context_name="news_context",
                    )
                except Exception as exc:
                    logger.warning(
                        "CockpitService: qual_context (news) disabled: %s", exc
                    )

        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            repo_root=repo_root,
            web_default_enabled=cfg["web"].get("enabled_default", False),
            backend_api_client=self.backend_api_client,
            qual_context_company_reader=qual_company,
            qual_context_news_reader=qual_news,
            state_store=self.state_store,
        )
        self.chat_controller = ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=self.llm_timeout_seconds,
            state_store=self.state_store,
            thread_id="global-main",
            cockpit_llm=cfg.get("cockpit_llm"),
            repo_root=self.repo_root,
            query_orchestrator=self.query_orchestrator,
        )
        self._feedback_lock = threading.Lock()
        self._recent_turn_diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._recent_auto_flag_fingerprints: set[str] = set()
        self._verification_runs_lock = threading.Lock()

        logger.info("CockpitService initialized successfully (config=%s)", config_path)

    def _preload_preferred_model_async(
        self,
        *,
        preferred_model: str,
        api_key: str,
        llm_provider: str,
    ) -> None:
        model_id = str(preferred_model or "").strip()
        if llm_provider != "llamacpp" or not model_id:
            return

        thread = threading.Thread(
            target=self._preload_preferred_model,
            kwargs={"preferred_model": model_id, "api_key": api_key},
            daemon=True,
            name="cockpit-model-preload",
        )
        thread.start()

    def _preload_preferred_model(self, *, preferred_model: str, api_key: str) -> None:
        base_url = str(getattr(self.llm_client, "base_url", "") or "").strip()
        if not base_url:
            return

        try:
            from app.services.router_state import is_extraction_active

            if is_extraction_active():
                logger.info(
                    "Skipping preferred model preload during active extraction: %s",
                    preferred_model,
                )
                return
        except Exception:
            pass

        parsed = urlparse(base_url)
        host = str(parsed.hostname or "127.0.0.1")
        if parsed.port is not None:
            port = parsed.port
        else:
            port = 443 if parsed.scheme == "https" else 80

        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = httpx.get(
                f"{base_url}/v1/models",
                headers=headers,
                timeout=5.0,
            )
            response.raise_for_status()
            payload = response.json() if response.content else {}
        except Exception as exc:
            logger.debug("Model preload skipped: llama.cpp unavailable (%s)", exc)
            return

        model_rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(model_rows, list):
            return

        # Only router mode exposes rich status dicts and supports /models/load.
        if not any(isinstance(row.get("status"), dict) for row in model_rows):
            return

        loaded_model = ""
        for row in model_rows:
            status = row.get("status")
            if isinstance(status, dict) and str(status.get("value") or "") == "loaded":
                loaded_model = str(row.get("id") or "").strip()
                break

        if loaded_model == preferred_model:
            return

        try:
            from cockpit.integrations.llamacpp_manager import load_model_api

            logger.info(
                "Preloading preferred model at startup: %s (current=%s)",
                preferred_model,
                loaded_model or "none",
            )
            ok = load_model_api(
                host=host,
                port=str(port),
                model_name=preferred_model,
                api_key=api_key,
                timeout=300.0,
                on_status=lambda msg: logger.info("model preload: %s", msg),
            )
            if ok:
                llm_client = getattr(self, "llm_client", None)
                if llm_client is not None and hasattr(llm_client, "switch_model"):
                    llm_client.switch_model(preferred_model)
                elif llm_client is not None:
                    llm_client.model = preferred_model
            else:
                logger.info(
                    "Preferred model preload did not complete (best effort): %s",
                    preferred_model,
                )
        except Exception:
            logger.exception(
                "Failed preloading preferred model",
                extra={"preferred_model": preferred_model, "host": host, "port": port},
            )

    @classmethod
    def get_instance(cls) -> CockpitService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def _resolve_thread_id(session_id: str | None) -> str:
        candidate = str(session_id or "").strip()
        return candidate[:128] if candidate else "global-main"

    def _build_chat_controller(self, thread_id: str) -> ChatController:
        if thread_id == "global-main":
            self._refresh_global_chat_controller_if_needed()
            return self.chat_controller
        return ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=self.llm_timeout_seconds,
            state_store=self.state_store,
            thread_id=thread_id,
            cockpit_llm=self.config.get("cockpit_llm"),
            repo_root=self.repo_root,
            query_orchestrator=self.query_orchestrator,
        )

    def _refresh_global_chat_controller_if_needed(self) -> None:
        """Hot-refresh routing-sensitive chat config without full backend restart.

        CockpitService is a process singleton, so runtime config edits would
        otherwise require backend restart before HybridRouter picks them up.
        We keep this narrow: only rebuild the global ChatController when
        routing policy or API availability changed.
        """
        config_path = getattr(self, "_config_path", None)
        if config_path is None:
            return

        try:
            cfg = load_config(str(config_path))
            cfg = apply_runtime_flags(
                cfg,
                RuntimeFlags(
                    config_path=str(config_path),
                    profile=str(getattr(self, "_runtime_profile", "default") or "default"),
                    read_only=bool(getattr(self, "_runtime_read_only", False)),
                    no_web=bool(getattr(self, "_runtime_no_web", False)),
                    repo_root=self.repo_root,
                ),
            )
        except Exception as exc:
            logger.warning("Skipping chat controller config refresh: %s", exc)
            return

        cockpit_llm = (
            cfg.get("cockpit_llm")
            if isinstance(cfg.get("cockpit_llm"), dict)
            else {}
        )
        desired_policy = str(cockpit_llm.get("hybrid_router_policy") or "").strip()
        desired_api_available = bool(effective_anthropic_api_key(cockpit_llm))

        hybrid_router = getattr(self.chat_controller, "_hybrid_router", None)
        current_policy = str(getattr(hybrid_router, "_policy", "") or "").strip()
        current_api_available = bool(getattr(hybrid_router, "_api", None))

        if (
            desired_policy == current_policy
            and desired_api_available == current_api_available
        ):
            return

        llm_cfg = cfg.get("llm") if isinstance(cfg.get("llm"), dict) else {}
        self.config = cfg
        self.llm_timeout_seconds = float(llm_cfg.get("timeout_seconds", 300))
        self.chat_controller = ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=self.llm_timeout_seconds,
            state_store=self.state_store,
            thread_id="global-main",
            cockpit_llm=self.config.get("cockpit_llm"),
            repo_root=self.repo_root,
            query_orchestrator=self.query_orchestrator,
        )
        logger.info(
            "Reloaded global ChatController (policy=%s api=%s)",
            desired_policy or "unknown",
            "available" if desired_api_available else "none",
        )

    def _persist_chat_message(self, thread_id: str, role: str, content: str) -> None:
        text = str(content or "").strip()
        if not text:
            return
        try:
            self.state_store.add_chat_message(
                thread_id,
                role,
                text,
                datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception(
                "Failed to persist chat message",
                extra={"thread_id": thread_id, "role": role},
            )

    def _remember_turn_diagnostics(
        self, thread_id: str, payload: dict[str, Any]
    ) -> None:
        with self._feedback_lock:
            items = self._recent_turn_diagnostics.setdefault(thread_id, [])
            items.append(payload)
            if len(items) > 20:
                del items[:-20]

    def _resolve_turn_diagnostics(
        self, thread_id: str, flagged_message: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        flagged_text = str((flagged_message or {}).get("content") or "").strip()
        with self._feedback_lock:
            items = list(self._recent_turn_diagnostics.get(thread_id) or [])
        if not items:
            return None
        if flagged_text:
            for item in reversed(items):
                if str(item.get("response_text") or "").strip() == flagged_text:
                    return item
        return items[-1]

    def auto_flag_chat_response(
        self,
        *,
        session_id: str | None,
        ticker: str | None,
        response: Any,
    ) -> dict[str, Any] | None:
        """Persist an automatic diagnostic report when a turn exposes clear issues."""

        thread_id = self._resolve_thread_id(session_id)
        response_text = str(getattr(response, "text", "") or "").strip()
        latest = self._resolve_turn_diagnostics(
            thread_id,
            {"content": response_text} if response_text else None,
        )
        turn = dict(latest or {})
        turn["response_text"] = response_text or str(turn.get("response_text") or "")
        turn["routing_metadata"] = dict(
            getattr(response, "routing_metadata", None)
            or turn.get("routing_metadata")
            or {}
        )
        turn["evidence"] = list(
            getattr(response, "evidence", None) or turn.get("evidence") or []
        )
        turn["tool_traces"] = list(
            getattr(response, "tool_traces", None) or turn.get("tool_traces") or []
        )

        findings = detect_auto_flag_findings(turn)
        if not findings:
            return None

        fingerprint = build_auto_flag_fingerprint(
            thread_id=thread_id,
            response_text=turn["response_text"],
            findings=findings,
        )
        with self._feedback_lock:
            seen = getattr(self, "_recent_auto_flag_fingerprints", set())
            if fingerprint in seen:
                return None
            seen.add(fingerprint)
            if len(seen) > 200:
                seen = set(list(seen)[-100:])
            self._recent_auto_flag_fingerprints = seen

        request = turn.get("request") if isinstance(turn.get("request"), dict) else {}
        return self.flag_chat_feedback(
            session_id=thread_id,
            ticker=ticker or request.get("ticker"),
            feedback_type="poor",
            capture_kind="auto_diagnostic",
            note=build_auto_flag_note(findings),
            flagged_message={
                "id": f"auto-diagnostic-{uuid.uuid4().hex[:8]}",
                "role": "assistant",
                "content": turn["response_text"],
            },
            transcript=[],
            frontend_context={
                "source": "cockpit-auto-flagger",
                "auto_flag": True,
                "auto_findings": findings,
            },
            auto_findings=findings,
        )

    @staticmethod
    def _fallback_flagged_analysis(
        review_input: dict[str, Any],
        *,
        error: Exception | None = None,
    ) -> dict[str, Any]:
        failure_modes: list[str] = []
        evidence_notes: list[str] = []
        follow_up: list[str] = []

        status_events = [
            item for item in review_input.get("status_events", []) if isinstance(item, dict)
        ]
        tool_traces = [
            item for item in review_input.get("tool_traces", []) if isinstance(item, dict)
        ]
        tool_calls = [
            item for item in review_input.get("tool_calls", []) if isinstance(item, dict)
        ]
        request_text = str(review_input.get("request") or "").strip()
        flagged_response = str(review_input.get("flagged_response") or "").strip()

        if request_text:
            evidence_notes.append(f"Request: {request_text[:280]}")
        if flagged_response:
            evidence_notes.append(f"Flagged response: {flagged_response[:280]}")

        timeout_like = False
        error_like = False
        for event in status_events:
            stage = str(event.get("stage") or "").strip()
            if not stage:
                continue
            lowered = stage.lower()
            evidence_notes.append(f"Status event: {stage[:180]}")
            timeout_like = timeout_like or ("timeout" in lowered or "timed out" in lowered)
            error_like = error_like or ("error" in lowered or "failed" in lowered)

        failed_tools: list[str] = []
        for trace in tool_traces:
            ok = trace.get("ok")
            tool_name = str(trace.get("tool_name") or trace.get("tool") or "").strip()
            error_text = str(trace.get("error") or "").strip()
            if ok is False or error_text:
                failed_tools.append(tool_name or "unknown_tool")
                if error_text:
                    evidence_notes.append(
                        f"Tool failure ({tool_name or 'unknown_tool'}): {error_text[:180]}"
                    )
        if failed_tools:
            failure_modes.append(
                f"Tool execution failure(s) observed: {', '.join(sorted(set(failed_tools)))}."
            )
            follow_up.append(
                "Replay the turn with tool tracing enabled and inspect failing tool parameters/results."
            )

        if timeout_like:
            failure_modes.append(
                "Execution timeout observed in status events before a reliable final answer."
            )
            follow_up.append(
                "Re-run with narrower scope or adjusted timeout to confirm whether latency is the root cause."
            )
        elif error_like:
            failure_modes.append(
                "Execution/status events include an explicit error or failure transition."
            )

        if not tool_calls and not tool_traces:
            failure_modes.append(
                "No tool activity was recorded, suggesting an ungrounded or skipped-retrieval response path."
            )
            follow_up.append(
                "Confirm routing intent and require at least one relevant read-only tool call before final synthesis."
            )

        if not failure_modes:
            failure_modes.append(
                "Root cause is inconclusive from deterministic traces; manual replay is required."
            )
            follow_up.append(
                "Reproduce the session with verbose status + tool tracing and compare request/response routing metadata."
            )

        if error is not None:
            evidence_notes.append(f"Fallback trigger: {type(error).__name__}: {str(error)[:200]}")

        summary = (
            "Deterministic fallback analysis generated because automated LLM review was unavailable. "
            "Findings are trace-derived and may require manual confirmation."
        )
        return {
            "status": "fallback",
            "summary": summary,
            "likely_failure_modes": failure_modes[:6],
            "evidence": evidence_notes[:10],
            "recommended_follow_up": follow_up[:6],
        }

    def _analyze_flagged_bundle(self, bundle: dict[str, Any]) -> dict[str, Any] | None:
        if _normalize_feedback_type(bundle.get("feedback_type")) == "good":
            return None
        review_input = {
            "session_id": bundle.get("session_id"),
            "ticker": bundle.get("ticker"),
            "frontend_note": bundle.get("note"),
            "request": ((bundle.get("backend_turn") or {}).get("request") or {}).get(
                "message"
            ),
            "flagged_response": ((bundle.get("flagged_message") or {}).get("content")),
            "response_mode": (bundle.get("backend_turn") or {}).get("response_mode"),
            "response_prompt": (bundle.get("backend_turn") or {}).get("prompt"),
            "thinking": (
                (bundle.get("backend_turn") or {}).get("thinking_events") or []
            )[:4],
            "status_events": (
                (bundle.get("backend_turn") or {}).get("status_events") or []
            )[:12],
            "tool_traces": (
                (bundle.get("backend_turn") or {}).get("tool_traces") or []
            )[:12],
            "tool_calls": ((bundle.get("backend_turn") or {}).get("tool_calls") or [])[
                :6
            ],
            "routing_metadata": (bundle.get("backend_turn") or {}).get(
                "routing_metadata"
            )
            or {},
            "recent_transcript": (bundle.get("frontend_snapshot") or {}).get(
                "transcript"
            )
            or [],
        }
        review_input = _sanitize_payload(review_input)
        prompt = (
            "You are reviewing a flagged cockpit chat turn. Return JSON only with keys "
            '"summary", "likely_failure_modes", "evidence", and "recommended_follow_up". '
            "Keep lists concise, factual, and grounded in the provided traces. If the cause is unclear, say so explicitly.\n\n"
            f"Context:\n{json.dumps(review_input, indent=2, default=str)}"
        )
        try:
            raw = self.llm_client.chat(
                prompt,
                timeout=min(max(self.llm_timeout_seconds, 10.0), 30.0),
            )
        except Exception as exc:
            logger.warning("Flagged chat analysis unavailable: %s", exc)
            return self._fallback_flagged_analysis(review_input, error=exc)

        parsed = _json_object_or_none(raw)
        if parsed is not None:
            parsed.setdefault("status", "ok")
            return parsed
        return {
            "status": "unparsed",
            "raw": _clip_text(raw, 3000),
        }

    def _finalize_flagged_report_async(
        self,
        *,
        report_id: str,
        bundle: dict[str, Any],
        bundle_path: Path,
        summary_path: Path,
        analysis_path: Path,
    ) -> None:
        try:
            analysis = self._analyze_flagged_bundle(bundle)
            sanitized_analysis = (
                _sanitize_payload(analysis) if analysis is not None else None
            )
            _write_flagged_report_files(
                bundle_path=bundle_path,
                summary_path=summary_path,
                analysis_path=analysis_path,
                bundle=bundle,
                analysis=sanitized_analysis,
            )
            self._make_flag_report_operator_writable(analysis_path.parent)
        except Exception:
            logger.exception(
                "Background flagged chat analysis failed",
                extra={"report_id": report_id},
            )

    def _schedule_flagged_report_analysis(
        self,
        *,
        report_id: str,
        bundle: dict[str, Any],
        bundle_path: Path,
        summary_path: Path,
        analysis_path: Path,
    ) -> None:
        worker = threading.Thread(
            target=self._finalize_flagged_report_async,
            kwargs={
                "report_id": report_id,
                "bundle": bundle,
                "bundle_path": bundle_path,
                "summary_path": summary_path,
                "analysis_path": analysis_path,
            },
            name=f"flagged-chat-analysis-{report_id}",
            daemon=True,
        )
        worker.start()

    def _flagged_reports_root(self) -> Path:
        workspace = os.getenv("COCKPIT_WORKSPACE_ROOT", "").strip()
        base = Path(workspace) if workspace else self.repo_root
        return (base / "reports" / "cockpit" / "flagged_sessions").resolve()

    def _flagged_reports_owner_reference(self) -> Path:
        workspace = os.getenv("COCKPIT_WORKSPACE_ROOT", "").strip()
        base = Path(workspace) if workspace else self.repo_root
        return base.resolve()

    def _make_flag_report_operator_writable(self, report_dir: Path) -> None:
        _make_flag_report_operator_writable(
            report_dir,
            owner_reference=self._flagged_reports_owner_reference(),
        )

    def _build_flag_read_api_path(self, report_id: str) -> str:
        return f"/api/cockpit/feedback/flags/{report_id}"

    def _resolve_flag_report_dir(self, report_id: str) -> Path:
        normalized = str(report_id or "").strip()
        if not _FLAG_REPORT_ID_RE.match(normalized):
            raise ValueError("Invalid report_id")
        root = self._flagged_reports_root()
        for candidate in root.glob(f"*/{normalized}"):
            if candidate.is_dir():
                return candidate.resolve()
        raise FileNotFoundError(normalized)

    @staticmethod
    def _load_flag_bundle(
        report_dir: Path,
        *,
        report_id: str | None = None,
    ) -> tuple[dict[str, Any], Path, Path, Path]:
        bundle_path = report_dir / "bundle.json"
        summary_path = report_dir / "summary.md"
        analysis_path = report_dir / "analysis.json"
        if not bundle_path.exists():
            raise FileNotFoundError(
                f"Missing bundle.json for {report_id or report_dir.name}"
            )
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Unreadable bundle.json for {report_id or report_dir.name}"
            ) from exc
        if not isinstance(bundle, dict):
            raise ValueError(f"Invalid bundle payload for {report_id or report_dir.name}")
        bundle["resolution"] = _extract_flag_resolution(bundle)
        return bundle, bundle_path, summary_path, analysis_path

    @staticmethod
    def _load_flag_analysis(analysis_path: Path) -> dict[str, Any] | None:
        if not analysis_path.exists():
            return None
        try:
            raw = json.loads(analysis_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Unreadable flagged analysis: %s", analysis_path)
            return None
        return raw if isinstance(raw, dict) else None

    @staticmethod
    def _load_flag_investigation(investigation_path: Path) -> dict[str, Any] | None:
        if not investigation_path.exists():
            return None
        try:
            raw = json.loads(investigation_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Unreadable flagged investigation: %s", investigation_path)
            return None
        return raw if isinstance(raw, dict) else None

    def list_flagged_reports(
        self,
        limit: int = 25,
        status: str = "open",
    ) -> list[dict[str, Any]]:
        root = self._flagged_reports_root()
        if not root.exists():
            return []

        normalized_status = str(status or "").strip().lower() or "open"
        if normalized_status not in {"open", "resolved", "all"}:
            raise ValueError("Invalid status filter")
        rows: list[tuple[float, dict[str, Any]]] = []
        max_items = max(1, min(int(limit or 25), 100))
        for session_dir in root.iterdir():
            if not session_dir.is_dir():
                continue
            for report_dir in session_dir.iterdir():
                if not report_dir.is_dir():
                    continue
                try:
                    bundle, _, _, _ = self._load_flag_bundle(report_dir)
                except FileNotFoundError:
                    continue
                except ValueError:
                    logger.warning("Unreadable flagged bundle: %s", report_dir / "bundle.json")
                    continue
                resolution = _extract_flag_resolution(bundle)
                if (
                    normalized_status != "all"
                    and resolution["status"] != normalized_status
                ):
                    continue
                saved_at = str(bundle.get("saved_at") or "")
                flagged_message = bundle.get("flagged_message") or {}
                report_id_value = str(bundle.get("report_id") or report_dir.name)
                rows.append(
                    (
                        report_dir.stat().st_mtime,
                        {
                            "report_id": report_id_value,
                            "feedback_type": _normalize_feedback_type(
                                bundle.get("feedback_type")
                            ),
                            "capture_kind": _normalize_capture_kind(
                                bundle.get("capture_kind")
                            ),
                            "session_id": str(
                                bundle.get("session_id") or session_dir.name
                            ),
                            "ticker": bundle.get("ticker"),
                            "saved_at": saved_at or None,
                            "note": bundle.get("note"),
                            "flagged_response_excerpt": _clip_text(
                                flagged_message.get("content"), 280
                            ).strip()
                            or None,
                            "read_api_path": self._build_flag_read_api_path(
                                report_id_value
                            ),
                            "resolution_status": resolution["status"],
                            "resolved_at": resolution.get("resolved_at"),
                            "resolution_commit_sha": resolution.get("commit_sha"),
                        },
                    )
                )
        rows.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in rows[:max_items]]

    def get_flagged_report(self, report_id: str) -> dict[str, Any]:
        report_dir = self._resolve_flag_report_dir(report_id)
        self._make_flag_report_operator_writable(report_dir)
        bundle, bundle_path, summary_path, analysis_path = self._load_flag_bundle(
            report_dir, report_id=report_id
        )
        summary_markdown = (
            summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        )
        analysis = self._load_flag_analysis(analysis_path)
        investigation_path = report_dir / "investigation.json"
        investigation = self._load_flag_investigation(investigation_path)
        resolution = _extract_flag_resolution(bundle)
        report_id_value = str(bundle.get("report_id") or report_id)

        return {
            "report_id": report_id_value,
            "feedback_type": _normalize_feedback_type(bundle.get("feedback_type")),
            "capture_kind": _normalize_capture_kind(bundle.get("capture_kind")),
            "report_dir": str(report_dir),
            "bundle_path": str(bundle_path),
            "summary_path": str(summary_path),
            "analysis_path": str(analysis_path) if analysis_path.exists() else None,
            "investigation_path": str(investigation_path)
            if investigation_path.exists()
            else None,
            "codex_prompt_path": str(report_dir / "codex_prompt.md")
            if (report_dir / "codex_prompt.md").exists()
            else None,
            "read_api_path": self._build_flag_read_api_path(report_id_value),
            "bundle": bundle,
            "summary_markdown": summary_markdown,
            "analysis": analysis,
            "investigation": investigation,
            "resolution_status": resolution["status"],
            "resolved_at": resolution.get("resolved_at"),
            "resolution_commit_sha": resolution.get("commit_sha"),
            "resolved_by": resolution.get("resolved_by"),
        }

    def resolve_flagged_report(
        self,
        report_id: str,
        *,
        commit_sha: str,
        resolved_by: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        report_dir = self._resolve_flag_report_dir(report_id)
        normalized_commit_sha = _validated_commit_sha(commit_sha)
        normalized_resolved_by = str(resolved_by or "").strip() or "codex"
        normalized_note = str(note or "").strip() or None

        with self._feedback_lock:
            bundle, bundle_path, summary_path, analysis_path = self._load_flag_bundle(
                report_dir, report_id=report_id
            )
            resolution = {
                "status": "resolved",
                "resolved_at": _now_iso(),
                "resolved_by": normalized_resolved_by,
                "commit_sha": normalized_commit_sha,
                "note": normalized_note,
            }
            bundle["resolution"] = resolution
            sanitized_bundle = _sanitize_payload(bundle)
            analysis = self._load_flag_analysis(analysis_path)
            bundle_path.write_text(
                json.dumps(sanitized_bundle, indent=2, default=str),
                encoding="utf-8",
            )
            summary_path.write_text(
                _render_flagged_summary(sanitized_bundle, analysis),
                encoding="utf-8",
            )

        report_id_value = str(bundle.get("report_id") or report_id)
        return {
            "ok": True,
            "report_id": report_id_value,
            "resolution_status": "resolved",
            "resolved_at": resolution["resolved_at"],
            "resolution_commit_sha": normalized_commit_sha,
            "resolved_by": normalized_resolved_by,
            "summary_path": str(summary_path),
            "read_api_path": self._build_flag_read_api_path(report_id_value),
        }

    def flag_chat_feedback(
        self,
        *,
        session_id: str | None,
        ticker: str | None,
        feedback_type: str = "poor",
        capture_kind: str = "chat_feedback",
        flagged_message: dict[str, Any],
        transcript: list[dict[str, Any]] | None = None,
        frontend_context: dict[str, Any] | None = None,
        screenshot: dict[str, Any] | None = None,
        auto_findings: list[dict[str, Any]] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        normalized_feedback_type = _normalize_feedback_type(feedback_type)
        normalized_capture_kind = _normalize_capture_kind(capture_kind)
        thread_id = self._resolve_thread_id(session_id)
        resolved_turn = self._resolve_turn_diagnostics(thread_id, flagged_message) or {}
        matched_turn = resolved_turn if isinstance(resolved_turn, dict) else {}
        evidence = (
            matched_turn.get("evidence")
            if isinstance(matched_turn.get("evidence"), list)
            else []
        )
        tool_traces = (
            matched_turn.get("tool_traces")
            if isinstance(matched_turn.get("tool_traces"), list)
            else []
        )
        tool_calls = _merge_tool_trace_metadata(
            _extract_tool_calls(evidence),
            tool_traces,
        )
        persisted_history: list[dict[str, Any]] = []
        if self.state_store is not None:
            try:
                persisted_history = self.state_store.get_chat_messages(
                    thread_id, limit=200
                )
            except Exception:
                logger.exception(
                    "Failed to read persisted chat history",
                    extra={"thread_id": thread_id},
                )

        if normalized_capture_kind == "ui_issue":
            report_prefix = "ui_issue"
        elif normalized_capture_kind == "auto_diagnostic":
            report_prefix = "auto"
        else:
            report_prefix = "good" if normalized_feedback_type == "good" else "flag"
        report_id = f"{report_prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        report_dir = (self._flagged_reports_root() / thread_id / report_id).resolve()
        report_dir.mkdir(parents=True, exist_ok=True)
        screenshot_attachment = _persist_feedback_screenshot(
            report_dir=report_dir,
            screenshot=screenshot,
        )
        frontend_context_payload, debug_attachment = _persist_browser_debug_bundle(
            report_dir=report_dir,
            frontend_context=frontend_context,
        )
        attachments = [
            attachment
            for attachment in (screenshot_attachment, debug_attachment)
            if attachment is not None
        ]

        bundle = {
            "report_id": report_id,
            "saved_at": _now_iso(),
            "session_id": thread_id,
            "ticker": str(ticker or "").strip().upper() or None,
            "feedback_type": normalized_feedback_type,
            "capture_kind": normalized_capture_kind,
            "note": str(note or "").strip() or None,
            "auto_findings": [
                item for item in (auto_findings or []) if isinstance(item, dict)
            ][:10],
            "flagged_message": flagged_message
            if isinstance(flagged_message, dict)
            else {},
            "attachments": attachments,
            "frontend_snapshot": {
                "transcript": [
                    item for item in (transcript or []) if isinstance(item, dict)
                ][-200:],
                "context": frontend_context_payload,
            },
            "persisted_history": persisted_history,
            "backend_turn": {
                **matched_turn,
                "response_mode": matched_turn.get("response_mode"),
                "response_prompt": matched_turn.get("prompt"),
                "tool_calls": tool_calls,
            },
            "backend_runtime": {
                "thread_id": thread_id,
                "llm_model": str(getattr(self.llm_client, "model", "") or ""),
                "llm_base_url": str(getattr(self.llm_client, "base_url", "") or ""),
                "backend_api_configured": self.backend_api_client is not None,
                "query_orchestrator_enabled": self.query_orchestrator is not None,
            },
            "resolution": _default_flag_resolution(),
        }
        sanitized_bundle = _sanitize_payload(bundle)

        bundle_path = report_dir / "bundle.json"
        summary_path = report_dir / "summary.md"
        analysis_path = report_dir / "analysis.json"

        _write_flagged_report_files(
            bundle_path=bundle_path,
            summary_path=summary_path,
            analysis_path=analysis_path,
            bundle=sanitized_bundle,
            analysis=None,
        )
        read_api_path = self._build_flag_read_api_path(report_id)
        codex_prompt = _build_codex_flag_prompt(
            bundle=sanitized_bundle,
            analysis=None,
            report_dir=report_dir,
            bundle_path=bundle_path,
            summary_path=summary_path,
            read_api_path=read_api_path,
        )
        investigation_artifacts = _write_codex_investigation_artifacts(
            report_id=report_id,
            feedback_type=normalized_feedback_type,
            capture_kind=normalized_capture_kind,
            report_dir=report_dir,
            read_api_path=read_api_path,
            codex_prompt=codex_prompt,
            created_at=str(sanitized_bundle.get("saved_at") or ""),
        )
        self._make_flag_report_operator_writable(report_dir)
        if (
            normalized_capture_kind in {"chat_feedback", "auto_diagnostic"}
            and normalized_feedback_type != "good"
        ):
            self._schedule_flagged_report_analysis(
                report_id=report_id,
                bundle=sanitized_bundle,
                bundle_path=bundle_path,
                summary_path=summary_path,
                analysis_path=analysis_path,
            )

        return {
            "ok": True,
            "report_id": report_id,
            "feedback_type": normalized_feedback_type,
            "capture_kind": normalized_capture_kind,
            "report_dir": str(report_dir),
            "bundle_path": str(bundle_path),
            "summary_path": str(summary_path),
            "analysis_path": str(analysis_path),
            "read_api_path": read_api_path,
            "codex_prompt": codex_prompt,
            **investigation_artifacts,
            "analysis_summary": None,
            "resolution_status": "open",
            "resolved_at": None,
            "resolution_commit_sha": None,
        }

    def get_intel_pulse_stats(self, ticker: str | None = None) -> dict[str, Any]:
        """Fetch Intel Pulse summary stats from canonical backend stores."""
        normalized_ticker = ticker.strip().upper() if ticker and ticker.strip() else None
        db = SessionLocal()
        try:
            doc_query = db.query(func.count(Document.document_id))
            financial_query = db.query(ASXPeriodicFinancial)
            failure_query = db.query(ExtractionRun).filter(ExtractionRun.status == "failed")
            runs_total_query = db.query(func.count(ExtractionRun.run_id))
            periodic_total_query = db.query(func.count(ASXPeriodicFinancial.ticker))

            if normalized_ticker:
                doc_query = doc_query.filter(Document.ticker == normalized_ticker)
                financial_query = financial_query.filter(
                    ASXPeriodicFinancial.ticker == normalized_ticker
                )
                failure_query = failure_query.join(
                    Document, ExtractionRun.document_id == Document.document_id
                ).filter(Document.ticker == normalized_ticker)
                runs_total_query = runs_total_query.join(
                    Document, ExtractionRun.document_id == Document.document_id
                ).filter(Document.ticker == normalized_ticker)
                periodic_total_query = periodic_total_query.filter(
                    ASXPeriodicFinancial.ticker == normalized_ticker
                )

            doc_count = int(doc_query.scalar() or 0)
            periodic_financial_rows_total = int(periodic_total_query.scalar() or 0)
            extraction_runs_total = int(runs_total_query.scalar() or 0)

            financial_rows = financial_query.order_by(
                ASXPeriodicFinancial.period_end.desc()
            ).limit(_PULSE_FINANCIAL_SAMPLE_LIMIT).all()
            financial_count = len(financial_rows)
            failed_count = int(failure_query.count() or 0)

            # signal_count / memory_count stay 0 until a single canonical counter is wired
            # (Qdrant commentary/asx_docs vs cockpit memory). See IntelPulseStats field docs.
            signal_count = 0
            memory_count = 0

            confidence_values = [
                float(row.confidence_metrics or 0.0)
                for row in financial_rows
                if row.confidence_metrics is not None
            ]
            avg_confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else 0.0
            )

            metric_fields = [
                "revenue",
                "ebit",
                "np_attributable",
                "operating_cf",
                "investing_cf",
                "financing_cf",
                "capex",
                "cash_end",
                "net_debt",
                "shares_outstanding",
                "total_equity",
                "interest_expense",
            ]
            populated_metrics = sum(
                1
                for row in financial_rows
                for field in metric_fields
                if getattr(row, field, None) is not None
            )
            total_metric_slots = len(financial_rows) * len(metric_fields)
            population_index = (
                (populated_metrics / total_metric_slots) * 100
                if total_metric_slots > 0
                else 0.0
            )
            extraction_failure_rate_pct = (
                (failed_count / doc_count) * 100 if doc_count > 0 else 0.0
            )
            quarantine_rate = extraction_failure_rate_pct

            overview_health = round((population_index + avg_confidence * 100) / 2, 1)
            overview_status = (
                "nominal"
                if extraction_failure_rate_pct <= 10.0 and overview_health >= 50.0
                else "degraded"
            )
            failure_stage_health = round(max(0.0, 100.0 - extraction_failure_rate_pct), 1)

            return {
                "stats": {
                    "document_count": doc_count,
                    "extraction_count": financial_count,
                    "recent_financial_rows_sampled": financial_count,
                    "periodic_financial_rows_total": periodic_financial_rows_total,
                    "extraction_runs_total": extraction_runs_total,
                    "signal_count": signal_count,
                    "memory_count": memory_count,
                    "population_index": round(population_index, 1),
                    "trust_score_avg": round(avg_confidence, 2),
                    "quarantine_rate": round(quarantine_rate, 1),
                    "extraction_failure_rate_pct": round(extraction_failure_rate_pct, 1),
                },
                "pipeline": [
                    {
                        "id": "overview",
                        "label": "PULSE_HOME",
                        "health": overview_health,
                        "status": overview_status,
                    },
                    {
                        "id": "extraction",
                        "label": "EXTRACTION",
                        "health": round(population_index, 1),
                        "status": "nominal" if population_index >= 60 else "degraded",
                    },
                    {
                        "id": "evaluation",
                        "label": "EVALUATION",
                        "health": round(avg_confidence * 100, 1),
                        "status": "nominal" if avg_confidence > 0.8 else "degraded",
                    },
                    {
                        "id": "signals",
                        "label": "SIGNALS",
                        "health": 0,
                        "status": "unavailable",
                    },
                    {
                        "id": "memory",
                        "label": "MEMORY",
                        "health": 0,
                        "status": "unavailable",
                    },
                    {
                        "id": "failures",
                        "label": "FAILURES",
                        "health": failure_stage_health,
                        "status": (
                            "critical" if extraction_failure_rate_pct > 10 else "nominal"
                        ),
                    },
                ],
                "failures": self._get_recent_failures(db, normalized_ticker),
                "generated_at": _now_iso(),
            }
        finally:
            db.close()

    def _get_recent_failures(
        self, db, ticker: str | None = None
    ) -> list[dict[str, Any]]:
        normalized_ticker = ticker.strip().upper() if ticker and ticker.strip() else None
        query = (
            db.query(ExtractionRun, Document.ticker)
            .join(Document, ExtractionRun.document_id == Document.document_id)
            .filter(ExtractionRun.status == "failed")
        )
        if normalized_ticker:
            query = query.filter(Document.ticker == normalized_ticker)

        rows = query.order_by(ExtractionRun.created_at.desc()).limit(10).all()
        out: list[dict[str, Any]] = []
        for run, tick in rows:
            ts = "--"
            if run.created_at is not None:
                ts = run.created_at.isoformat()
            out.append(
                {
                    "id": str(run.run_id)[:8],
                    "entity": str(tick or "UNKNOWN").strip().upper() or "UNKNOWN",
                    "type": "EXTRACTION_FAIL",
                    "message": run.error or "Unknown extraction error",
                    "confidence": float(run.confidence_overall or 0.0),
                    "timestamp": ts,
                }
            )
        return out

    def get_diagnostic_matrix(
        self, stage: str, ticker: str | None = None
    ) -> dict[str, Any]:
        """Build the density matrix from canonical financial rows."""
        db = SessionLocal()
        try:
            if ticker:
                companies = [ticker.strip().upper()]
            else:
                companies = [
                    row.ticker
                    for row in db.query(Company.ticker)
                    .order_by(Company.ticker.asc())
                    .limit(10)
                    .all()
                ]

            # Canonical columns only (EBIT from `ebit`; EPS derived from NP / shares).
            metric_specs: list[tuple[str, str]] = [
                ("REVENUE", "revenue"),
                ("EBIT", "ebit"),
                ("NET_DEBT", "net_debt"),
                ("EPS", "__eps__"),
                ("CAPEX", "capex"),
            ]

            stage_l = stage.lower()
            entities: list[dict[str, Any]] = []
            for comp in companies:
                financial_rows = (
                    db.query(ASXPeriodicFinancial)
                    .filter(ASXPeriodicFinancial.ticker == comp)
                    .order_by(ASXPeriodicFinancial.period_end.desc())
                    .limit(12)
                    .all()
                )
                doc_ids = {r.source_document_id for r in financial_rows}
                failed_doc_ids: set[UUID] = set()
                if doc_ids:
                    failed_doc_ids = {
                        row[0]
                        for row in db.query(ExtractionRun.document_id)
                        .filter(
                            ExtractionRun.document_id.in_(doc_ids),
                            ExtractionRun.status == "failed",
                        )
                        .distinct()
                        .all()
                    }

                entity_metrics: dict[str, str] = {}
                for label, field in metric_specs:
                    entity_metrics[label] = _matrix_cell_state(
                        financial_rows, field, stage_l, failed_doc_ids
                    )
                entities.append({"entity": comp, "metrics": entity_metrics})

            return {"stage": stage, "entities": entities}
        finally:
            db.close()

    def chat_stream(
        self,
        message: str,
        ticker: str | None = None,
        session_id: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_thinking: Callable[[str, str], None] | None = None,
        enable_web: bool | None = None,
        model: str | None = None,
        rag: bool | None = None,
        db_diagnostics: bool | None = None,
        ui_mode: str | None = None,
        attached_sources: list[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        """Run a chat turn and return the full response, while optionally streaming chunks."""
        requested_model = str(model or "").strip()
        llm_client = getattr(self, "llm_client", None)
        current_model = str(getattr(llm_client, "model", "") or "").strip()

        status_events: list[dict[str, Any]] = []
        thinking_events: list[dict[str, Any]] = []

        def _capture_status(stage: str) -> None:
            status_events.append({"stage": str(stage or ""), "at": _now_iso()})
            if on_status is not None:
                on_status(stage)

        thread_id = self._resolve_thread_id(session_id)
        controller = self._build_chat_controller(thread_id)

        forced_backend, _effective_message = parse_backend_prefix(message)
        route_preview: dict[str, Any] | None = None
        hybrid_router = getattr(controller, "_hybrid_router", None)
        if hybrid_router is not None and hasattr(hybrid_router, "preview_route"):
            try:
                route_preview = hybrid_router.preview_route(
                    force_backend=forced_backend
                )
            except RuntimeError as exc:
                _capture_status(str(exc))
                raise
            except Exception:
                logger.exception("Failed to preview HybridRouter route before model switch")

        route_preview_source = (
            str(route_preview.get("source") or "").strip()
            if isinstance(route_preview, dict)
            else ""
        )
        route_preview_model = (
            str(route_preview.get("model") or "").strip()
            if isinstance(route_preview, dict)
            else ""
        )
        route_preview_reason = (
            str(route_preview.get("routing_reason") or "").strip()
            if isinstance(route_preview, dict)
            else ""
        )
        should_switch_local_model = (
            requested_model
            and llm_client is not None
            and requested_model != current_model
            and (route_preview is None or route_preview_source == "local")
        )

        if requested_model and route_preview_source == "api":
            route_label = "API" if route_preview_source == "api" else route_preview_source
            suffix = f" ({route_preview_reason})" if route_preview_reason else ""
            model_label = f": {route_preview_model}" if route_preview_model else ""
            _capture_status(
                f"Routing to {route_label or 'configured backend'}{model_label}{suffix}"
            )
        elif should_switch_local_model:
            if requested_model != current_model:
                _capture_status(
                    f"Switching model: {current_model or 'unknown'} -> {requested_model}"
                )
                logger.info(
                    "Switching LLM model: %s -> %s",
                    current_model or "unknown",
                    requested_model,
                )
                try:
                    llm_client.switch_model(requested_model)
                except Exception as exc:
                    _capture_status(f"Model switch failed: {exc}")
                    raise

                resolved_model = str(getattr(llm_client, "model", "") or "").strip()
                if resolved_model and resolved_model != requested_model:
                    _capture_status(
                        f"Model alias resolved: {requested_model} -> {resolved_model}"
                    )
                _capture_status(f"Model ready: {resolved_model or requested_model}")
            else:
                _capture_status(f"Using selected model: {current_model}")
        elif requested_model:
            _capture_status(f"Requested model: {requested_model}")
        elif current_model:
            _capture_status(f"Using active model: {current_model}")

        def _capture_chunk(chunk: str) -> None:
            if on_chunk is not None:
                on_chunk(chunk)

        def _capture_thinking(assessment: str, plan: str) -> None:
            thinking_events.append(
                {
                    "assessment": str(assessment or ""),
                    "plan": str(plan or ""),
                    "at": _now_iso(),
                }
            )
            if on_thinking is not None:
                on_thinking(assessment, plan)

        self._persist_chat_message(thread_id, "user", message)
        response_started = time.monotonic()
        response = controller.build_chat_response(
            message=message,
            enable_web=bool(enable_web) if enable_web is not None else False,
            enable_rag=bool(rag) if rag is not None else True,
            enable_db_diagnostics=bool(db_diagnostics)
            if db_diagnostics is not None
            else False,
            prior_ticker=ticker,
            on_chunk=_capture_chunk,
            on_status=_capture_status,
            on_thinking=_capture_thinking,
            ui_mode=ui_mode,
            attached_sources=attached_sources or [],
        )
        elapsed_ms = int((time.monotonic() - response_started) * 1000)
        meta = dict(getattr(response, "routing_metadata", None) or {})
        if not str(meta.get("source") or "").strip():
            hybrid_router = getattr(controller, "_hybrid_router", None)
            last_attempt = (
                hybrid_router.last_attempt_metadata()
                if hybrid_router is not None
                and hasattr(hybrid_router, "last_attempt_metadata")
                else None
            )
            if isinstance(last_attempt, dict):
                meta.update(last_attempt)
        if not str(meta.get("source") or "").strip() and isinstance(route_preview, dict):
            meta.update(
                {
                    key: value
                    for key, value in route_preview.items()
                    if key in {"source", "model", "cost_usd", "routing_reason"}
                    and value is not None
                }
            )
        llm_client = getattr(self, "llm_client", None)
        current_model = str(getattr(llm_client, "model", "") or "").strip()
        source = str(meta.get("source") or "").strip()
        if (
            current_model
            and not str(meta.get("model") or "").strip()
            and (
                source in {"local", "api"}
                or getattr(response, "prompt", None)
                or requested_model
            )
        ):
            meta["model"] = current_model
        if not source:
            meta["source"] = (
                "local"
                if getattr(response, "prompt", None) or requested_model
                else "cockpit"
            )
        if int(meta.get("latency_ms") or 0) <= 0:
            meta["latency_ms"] = max(1, elapsed_ms)
        meta.setdefault("cost_usd", 0.0)
        provider_error = _detect_api_provider_error(response.text, meta)
        if provider_error:
            meta["provider_error"] = provider_error
            _capture_status("Claude API billing action required: top up Anthropic credits.")
        response.routing_metadata = meta
        self._persist_chat_message(thread_id, "assistant", response.text)
        self._remember_turn_diagnostics(
            thread_id,
            {
                "created_at": _now_iso(),
                "thread_id": thread_id,
                "session_id": thread_id,
                "ticker": str(ticker or "").strip().upper() or None,
                "request": {
                    "message": message,
                    "ticker": ticker,
                    "enable_web": bool(enable_web) if enable_web is not None else False,
                    "requested_model": str(model or "").strip() or None,
                    "rag": bool(rag) if rag is not None else True,
                    "db_diagnostics": bool(db_diagnostics)
                    if db_diagnostics is not None
                    else False,
                    "ui_mode": ui_mode,
                },
                "status_events": status_events,
                "thinking_events": thinking_events,
                "response_mode": str(getattr(response, "mode", "") or "") or None,
                "response_text": response.text,
                "prompt": getattr(response, "prompt", None),
                "action_preview": response.action_preview,
                "tool_traces": list(getattr(response, "tool_traces", None) or []),
                "evidence": list(response.evidence or []),
                "routing_metadata": meta,
            },
        )
        return response

    # ------------------------------------------------------------------
    # Verification run history
    # ------------------------------------------------------------------

    def record_verification_run(
        self,
        ticker: str,
        outcome_summary: str,
        passed: bool,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a completed verification run."""
        import time

        run: dict[str, Any] = {
            "run_id": run_id or str(uuid.uuid4())[:8],
            "ticker": ticker.upper().strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": time.time(),
            "passed": passed,
            "outcome_summary": outcome_summary[:500],
        }
        with self._verification_runs_lock:
            runs = self._load_verification_runs()
            runs.insert(0, run)
            runs = runs[:50]
            self._save_verification_runs(runs)
        return run

    def get_verification_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent verification runs, newest first."""
        runs = self._load_verification_runs()
        return runs[: max(1, min(int(limit), 50))]

    def _verification_runs_path(self) -> Path:
        data_root = os.environ.get("DATA_ROOT", "/tmp")
        return Path(data_root) / "cockpit_verification_runs.json"

    def _load_verification_runs(self) -> list[dict[str, Any]]:
        path = self._verification_runs_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_verification_runs(self, runs: list[dict[str, Any]]) -> None:
        path = self._verification_runs_path()
        try:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(runs, default=str))
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Failed to save verification runs: %s", exc)
