from __future__ import annotations

import shlex
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cockpit.core.types import ActionSpec


@dataclass
class ActionPreview:
    action_id: str
    command: list[str]
    summary: str
    estimated_impact: str
    timeout_seconds: int


class ActionRegistry:
    def __init__(self, repo_root: Path, confirm_required: bool = True) -> None:
        self.repo_root = repo_root
        py = str(repo_root / ".venv" / "bin" / "python")
        self._actions: dict[str, ActionSpec] = {
            "full_history": ActionSpec(
                id="full_history",
                label="Full history ticker sync",
                command_template=[
                    py,
                    "scripts/full_history_ticker_sync.py",
                    "--ticker",
                    "{ticker}",
                    "--years",
                    "{years}",
                    "--max-backfill-retries",
                    "{max_backfill_retries}",
                    "--resume-max-retries",
                    "{resume_max_retries}",
                    "--resume-retry-delay-seconds",
                    "{resume_retry_delay_seconds}",
                    "--report",
                    "{report_path}",
                ],
                arg_schema={
                    "ticker": str,
                    "years": int,
                    "max_backfill_retries": int,
                    "resume_max_retries": int,
                    "resume_retry_delay_seconds": float,
                    "report_path": str,
                    "process_documents": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/full_history_run_*.json"],
                timeout_seconds=7200,
            ),
            "update_ticker_financials": ActionSpec(
                id="update_ticker_financials",
                label="Update ticker financial data",
                command_template=[
                    py,
                    "scripts/update_ticker_financials.py",
                    "--ticker",
                    "{ticker}",
                    "--years",
                    "{years}",
                    "--max-backfill-retries",
                    "{max_backfill_retries}",
                    "--resume-max-retries",
                    "{resume_max_retries}",
                    "--resume-retry-delay-seconds",
                    "{resume_retry_delay_seconds}",
                    "--report",
                    "{report_path}",
                ],
                arg_schema={
                    "ticker": str,
                    "years": int,
                    "max_backfill_retries": int,
                    "resume_max_retries": int,
                    "resume_retry_delay_seconds": float,
                    "report_path": str,
                    "process_documents": bool,
                    "skip_resume_pending": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/financial_update_*.json"],
                timeout_seconds=7200,
            ),
            "rebuild_ticker_financials": ActionSpec(
                id="rebuild_ticker_financials",
                label="Rebuild ticker financials from docs",
                command_template=[
                    py,
                    "scripts/rebuild_ticker_financials_from_docs.py",
                    "--ticker",
                    "{ticker}",
                    "--report",
                    "{rebuild_report}",
                ],
                arg_schema={
                    "ticker": str,
                    "limit": int,
                    "since": str,
                    "include_non_financial_candidates": bool,
                    "force": bool,
                    "rebuild_report": str,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/rebuild_ticker_financials_from_docs_*.json"],
                timeout_seconds=7200,
            ),
            "audit_ticker_financials": ActionSpec(
                id="audit_ticker_financials",
                label="Audit ticker financials quality",
                command_template=[
                    py,
                    "scripts/audit_ticker_financials.py",
                    "--ticker",
                    "{ticker}",
                    "--low-confidence-threshold",
                    "{low_confidence_threshold}",
                    "--report",
                    "{audit_report}",
                ],
                arg_schema={
                    "ticker": str,
                    "low_confidence_threshold": float,
                    "audit_report": str,
                },
                is_mutating=False,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/audit_ticker_financials_*.json"],
                timeout_seconds=1800,
            ),
            "daily_marketindex": ActionSpec(
                id="daily_marketindex",
                label="Daily MarketIndex action",
                command_template=[
                    py,
                    "scripts/daily_marketindex_action.py",
                    "--download-limit",
                    "{download_limit}",
                    "--min-download-count",
                    "{min_download_count}",
                    "--min-success-ratio",
                    "{min_success_ratio}",
                    "--null-retry-delay-seconds",
                    "{null_retry_delay_seconds}",
                    "--daily-report",
                    "{daily_report}",
                    "--download-report",
                    "{download_report}",
                ],
                arg_schema={
                    "download_limit": int,
                    "min_download_count": int,
                    "min_success_ratio": float,
                    "null_retry_delay_seconds": int,
                    "daily_report": str,
                    "download_report": str,
                    "overwrite_pdfs": bool,
                    "skip_download": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/marketindex/daily_marketindex_action_report_*.json"],
                timeout_seconds=3600,
            ),
            "daily_asx_marketwide": ActionSpec(
                id="daily_asx_marketwide",
                label="Daily ASX all-announcements action",
                command_template=[
                    py,
                    "scripts/daily_asx_all_announcements_action.py",
                    "--date",
                    "{date}",
                    "--report",
                    "{daily_asx_report}",
                ],
                arg_schema={
                    "date": str,
                    "daily_asx_report": str,
                    "process_documents": bool,
                    "skip_download": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/asx/daily_asx_all_announcements_report*.json"],
                timeout_seconds=7200,
            ),
            "asx_enrichment_sweep": ActionSpec(
                id="asx_enrichment_sweep",
                label="ASX enrichment sweep (bulk ingest + classify)",
                command_template=[
                    py,
                    "scripts/asx_enrichment_sweep_action.py",
                    "--end-date",
                    "{date}",
                    "--days-back",
                    "{days_back}",
                    "--max-new-docs",
                    "{max_new_docs}",
                    "--max-errors",
                    "{max_errors}",
                    "--stop-after-empty-days",
                    "{stop_after_empty_days}",
                    "--fallback-max-tickers",
                    "{fallback_max_tickers}",
                    "--request-delay-ms",
                    "{request_delay_ms}",
                    "--request-jitter-ms",
                    "{request_jitter_ms}",
                    "--failure-backoff-ms",
                    "{failure_backoff_ms}",
                    "--max-consecutive-failures",
                    "{max_consecutive_failures}",
                    "--report",
                    "{asx_sweep_report}",
                ],
                arg_schema={
                    "date": str,
                    "days_back": int,
                    "max_new_docs": int,
                    "max_errors": int,
                    "stop_after_empty_days": int,
                    "fallback_max_tickers": int,
                    "request_delay_ms": int,
                    "request_jitter_ms": int,
                    "failure_backoff_ms": int,
                    "max_consecutive_failures": int,
                    "asx_sweep_report": str,
                    "process_documents": bool,
                    "skip_download": bool,
                    "download_existing_missing": bool,
                    "no_historical_fallback": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/asx/asx_enrichment_sweep_report*.json"],
                timeout_seconds=14400,
            ),
            "sort_asx_docs": ActionSpec(
                id="sort_asx_docs",
                label="Sort all ASX docs into announcement-type folders",
                command_template=[
                    py,
                    "scripts/classify_announcement_importance.py",
                    "--report",
                    "{importance_report}",
                ],
                arg_schema={
                    "ticker": str,
                    "limit": int,
                    "importance_report": str,
                    "only_unsorted": bool,
                    "no_pdf_text": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/importance/announcement_importance_report*.json"],
                timeout_seconds=7200,
            ),
            "resume_pending": ActionSpec(
                id="resume_pending",
                label="Resume pending downloads",
                command_template=[
                    py,
                    "scripts/resume_pending_downloads.py",
                    "--ticker",
                    "{ticker}",
                    "--max-retries",
                    "{max_retries}",
                    "--retry-delay-seconds",
                    "{retry_delay_seconds}",
                    "--report",
                    "{report_path}",
                ],
                arg_schema={
                    "ticker": str,
                    "max_retries": int,
                    "retry_delay_seconds": float,
                    "report_path": str,
                    "process_documents": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/*resume*.json"],
                timeout_seconds=3600,
            ),
            "recover_headed": ActionSpec(
                id="recover_headed",
                label="Recover headed MarketIndex docs",
                command_template=[
                    py,
                    "scripts/recover_marketindex_headed.py",
                    "--ticker",
                    "{ticker}",
                    "--limit",
                    "{limit}",
                ],
                arg_schema={
                    "ticker": str,
                    "limit": int,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/marketindex_headed_recovery_report.json"],
                timeout_seconds=7200,
            ),
        }

    def list_actions(self) -> list[ActionSpec]:
        return list(self._actions.values())

    def get(self, action_id: str) -> ActionSpec:
        if action_id not in self._actions:
            raise KeyError(f"Unknown action: {action_id}")
        return self._actions[action_id]

    def build_command(self, action_id: str, args: dict[str, Any]) -> list[str]:
        spec = self.get(action_id)
        normalized = self._normalize_args(spec, args)
        command: list[str] = []
        for token in spec.command_template:
            if token.startswith("{") and token.endswith("}"):
                key = token[1:-1]
                if key not in normalized:
                    raise ValueError(f"Missing required arg: {key}")
                command.append(str(normalized[key]))
            else:
                command.append(token)

        # Optional flags toggles.
        if action_id == "full_history" and normalized.get("process_documents"):
            command.append("--process-documents")
        if action_id == "update_ticker_financials" and normalized.get("process_documents", True):
            command.append("--process-documents")
        if action_id == "update_ticker_financials" and normalized.get("skip_resume_pending"):
            command.append("--skip-resume-pending")
        if action_id == "daily_marketindex" and normalized.get("overwrite_pdfs"):
            command.append("--overwrite-pdfs")
        if action_id == "daily_marketindex" and normalized.get("skip_download"):
            command.append("--skip-download")
        if action_id == "resume_pending" and normalized.get("process_documents"):
            command.append("--process-documents")
        if action_id == "daily_asx_marketwide" and normalized.get("process_documents"):
            command.append("--process-documents")
        if action_id == "daily_asx_marketwide" and normalized.get("skip_download"):
            command.append("--skip-download")
        if action_id == "asx_enrichment_sweep" and normalized.get("process_documents"):
            command.append("--process-documents")
        if action_id == "asx_enrichment_sweep" and normalized.get("skip_download"):
            command.append("--skip-download")
        if action_id == "asx_enrichment_sweep" and normalized.get("download_existing_missing", True):
            command.append("--download-existing-missing")
        if action_id == "asx_enrichment_sweep" and normalized.get("no_historical_fallback"):
            command.append("--no-historical-fallback")
        if action_id == "sort_asx_docs":
            if str(normalized.get("ticker", "")).strip():
                command.extend(["--ticker", str(normalized["ticker"]).strip().upper()])
            if int(normalized.get("limit", 0)) > 0:
                command.extend(["--limit", str(normalized["limit"])])
            if normalized.get("only_unsorted", True):
                command.append("--only-unsorted")
            if normalized.get("no_pdf_text"):
                command.append("--no-pdf-text")
        if action_id == "rebuild_ticker_financials":
            if int(normalized.get("limit", 0)) > 0:
                command.extend(["--limit", str(normalized["limit"])])
            since = str(normalized.get("since", "")).strip()
            if since:
                command.extend(["--since", since])
            if normalized.get("include_non_financial_candidates"):
                command.append("--include-non-financial-candidates")
            if normalized.get("force"):
                command.append("--force")

        return command

    def preview(self, action_id: str, args: dict[str, Any]) -> ActionPreview:
        spec = self.get(action_id)
        command = self.build_command(action_id, args)
        impact = "mutates local data and reports" if spec.is_mutating else "read-only"
        return ActionPreview(
            action_id=action_id,
            command=command,
            summary=f"Run {spec.label}",
            estimated_impact=impact,
            timeout_seconds=spec.timeout_seconds,
        )

    @staticmethod
    def parse_kv_args(raw: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if not raw.strip():
            return result
        for part in shlex.split(raw):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            result[key.strip()] = value.strip()
        return result

    def _normalize_args(self, spec: ActionSpec, args: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value_type in spec.arg_schema.items():
            value = args.get(key)
            if value is None:
                continue
            if value_type is bool:
                if isinstance(value, bool):
                    out[key] = value
                else:
                    out[key] = str(value).lower() in {"1", "true", "yes", "on"}
            elif value_type is int:
                out[key] = int(value)
            elif value_type is float:
                out[key] = float(value)
            else:
                out[key] = str(value)

        # Runtime defaults.
        ts = uuid.uuid4().hex[:8]
        out.setdefault("ticker", "BHP")
        out.setdefault("years", 5)
        out.setdefault("max_backfill_retries", 3)
        out.setdefault("resume_max_retries", 5)
        out.setdefault("resume_retry_delay_seconds", 2.0)
        out.setdefault("download_limit", 0)
        out.setdefault("min_download_count", 5)
        out.setdefault("min_success_ratio", 0.35)
        out.setdefault("null_retry_delay_seconds", 15)
        out.setdefault("max_retries", 4)
        out.setdefault("retry_delay_seconds", 2.0)
        out.setdefault("limit", 50)
        out.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
        out.setdefault("days_back", 30)
        out.setdefault("max_new_docs", 0)
        out.setdefault("max_errors", 100)
        out.setdefault("stop_after_empty_days", 10)
        out.setdefault("fallback_max_tickers", 1000)
        out.setdefault("request_delay_ms", 700)
        out.setdefault("request_jitter_ms", 900)
        out.setdefault("failure_backoff_ms", 2500)
        out.setdefault("max_consecutive_failures", 50)
        out.setdefault("download_existing_missing", True)
        out.setdefault("low_confidence_threshold", 0.40)
        out.setdefault("only_unsorted", True)

        out.setdefault("report_path", f"reports/cockpit_{spec.id}_{ts}.json")
        if spec.id == "update_ticker_financials":
            out.setdefault("report_path", f"reports/financial_update_{out.get('ticker', 'BHP')}_{ts}.json")
            out.setdefault("process_documents", True)
        if spec.id == "sort_asx_docs" and "ticker" not in args:
            out["ticker"] = ""
        if spec.id == "sort_asx_docs" and "limit" not in args:
            out["limit"] = 0
        out.setdefault("daily_report", f"reports/marketindex/daily_marketindex_action_report_{ts}.json")
        out.setdefault("download_report", f"reports/marketindex/pdf_download_report_{ts}.json")
        out.setdefault("daily_asx_report", f"reports/asx/daily_asx_all_announcements_report_{ts}.json")
        out.setdefault("asx_sweep_report", f"reports/asx/asx_enrichment_sweep_report_{ts}.json")
        out.setdefault("importance_report", f"reports/importance/announcement_importance_report_{ts}.json")
        out.setdefault("rebuild_report", f"reports/rebuild_ticker_financials_from_docs_{out.get('ticker', 'BHP')}_{ts}.json")
        out.setdefault("audit_report", f"reports/audit_ticker_financials_{out.get('ticker', 'BHP')}_{ts}.json")

        return out
