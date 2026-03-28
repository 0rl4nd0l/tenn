from __future__ import annotations

import os
import shlex
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cockpit.core.types import ActionSpec


VISIBLE_ACTION_IDS: tuple[str, ...] = (
    "daily_news_ingest",
    "historical_news_ingest",
    "load_news_to_qdrant",
    "daily_announcement_ingest",
    "single_ticker_announcement_backfill",
    "universe_announcement_enrichment_backfill",
    "metric_extraction",
)

# Streamlined UI surface — subset of VISIBLE_ACTION_IDS that appears in list_actions().
# load_news_to_qdrant is intentionally excluded: it is accessible via intent routing
# but not surfaced as a first-class action in the cockpit action panel.
_STREAMLINED_ACTION_IDS: tuple[str, ...] = (
    "daily_news_ingest",
    "historical_news_ingest",
    "daily_announcement_ingest",
    "single_ticker_announcement_backfill",
    "universe_announcement_enrichment_backfill",
    "metric_extraction",
)

# Actions that operate on a specific ticker and MUST have one provided.
# Market-wide actions (daily_news_ingest, etc.) are intentionally excluded.
TICKER_REQUIRED_ACTION_IDS: frozenset[str] = frozenset({
    "full_history",
    "update_ticker_financials",
    "rebuild_ticker_financials",
    "audit_ticker_financials",
    "single_ticker_announcement_backfill",
    "metric_extraction",
    "show_candlestick",
    "resume_pending",
    "recover_headed",
})


@dataclass
class ActionPreview:
    action_id: str
    command: list[str]
    summary: str
    estimated_impact: str
    timeout_seconds: int
    guard_message: str | None = None


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
            "asx_enrichment_chunked": ActionSpec(
                id="asx_enrichment_chunked",
                label="ASX enrichment chunked (legacy)",
                command_template=[
                    py,
                    "scripts/run_asx_enrichment_chunked.py",
                    "--end-date",
                    "{date}",
                    "--total-days-back",
                    "{total_days_back}",
                    "--chunk-days",
                    "{chunk_days}",
                    "--fallback-max-tickers",
                    "{fallback_max_tickers}",
                    "--ticker-universe-file",
                    "{ticker_universe_file}",
                    "--request-delay-ms",
                    "{request_delay_ms}",
                    "--request-jitter-ms",
                    "{request_jitter_ms}",
                    "--failure-backoff-ms",
                    "{failure_backoff_ms}",
                    "--max-consecutive-failures",
                    "{max_consecutive_failures}",
                    "--max-errors",
                    "{max_errors}",
                    "--stop-after-empty-days",
                    "{stop_after_empty_days}",
                    "--reports-dir",
                    "{asx_chunk_reports_dir}",
                    "--rollup-report",
                    "{asx_chunk_rollup_report}",
                ],
                arg_schema={
                    "date": str,
                    "total_days_back": int,
                    "chunk_days": int,
                    "fallback_max_tickers": int,
                    "ticker_universe_file": str,
                    "request_delay_ms": int,
                    "request_jitter_ms": int,
                    "failure_backoff_ms": int,
                    "max_consecutive_failures": int,
                    "max_errors": int,
                    "stop_after_empty_days": int,
                    "asx_chunk_reports_dir": str,
                    "asx_chunk_rollup_report": str,
                    "download_existing_missing": bool,
                    "process_documents": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/asx/asx_enrichment_chunked_rollup*.json"],
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
            "daily_news_ingest": ActionSpec(
                id="daily_news_ingest",
                label="Daily news ingest",
                command_template=[
                    py,
                    "../scripts/fetch_daily_news.py",
                    "--providers",
                    "{providers}",
                    "--since-hours",
                    "{since_hours}",
                    "--lane",
                    "{lane}",
                    "--max-tickers",
                    "{max_tickers}",
                    "--news-runs-root",
                    "{news_runs_root}",
                ],
                arg_schema={
                    "providers": str,
                    "since_hours": int,
                    "lane": str,
                    "max_tickers": int,
                    "news_runs_root": str,
                    "asx_wide": bool,
                    "tickers": str,
                    "auto_live_when_capture_missing": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["../reports/qual_context/news_runs/*/report_summary.json"],
                timeout_seconds=5400,
            ),
            "historical_news_ingest": ActionSpec(
                id="historical_news_ingest",
                label="Historical news ingest",
                command_template=[
                    py,
                    "../scripts/backfill_news.py",
                    "--provider",
                    "{provider}",
                    "--from",
                    "{from_day}",
                    "--to",
                    "{to_day}",
                    "--lane",
                    "{lane}",
                    "--run-id",
                    "{run_id}",
                    "--max-days",
                    "{max_days}",
                    "--max-tickers",
                    "{max_tickers}",
                    "--news-runs-root",
                    "{news_runs_root}",
                ],
                arg_schema={
                    "provider": str,
                    "from_day": str,
                    "to_day": str,
                    "lane": str,
                    "run_id": str,
                    "max_days": int,
                    "max_tickers": int,
                    "news_runs_root": str,
                    "no_resume": bool,
                    "asx_wide": bool,
                    "tickers": str,
                    "auto_live_when_capture_missing": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["../reports/qual_context/news_runs/*/report_summary.json"],
                timeout_seconds=14400,
            ),
            "load_news_to_qdrant": ActionSpec(
                id="load_news_to_qdrant",
                label="Load news chunks to Qdrant",
                command_template=[
                    py,
                    "../scripts/load_news_to_qdrant.py",
                    "--db-path",
                    "{db_path}",
                    "--qdrant-url",
                    "{qdrant_url}",
                    "--collection",
                    "{collection}",
                    "--batch-size",
                    "{batch_size}",
                    "--since-hours",
                    "{since_hours}",
                ],
                arg_schema={
                    "db_path": str,
                    "qdrant_url": str,
                    "collection": str,
                    "batch_size": int,
                    "since_hours": int,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=[],
                timeout_seconds=1800,
            ),
            "daily_announcement_ingest": ActionSpec(
                id="daily_announcement_ingest",
                label="Daily announcement ingest",
                command_template=[
                    py,
                    "scripts/daily_asx_all_announcements_action.py",
                    "--date",
                    "{date}",
                    "--report",
                    "{daily_announcement_report}",
                ],
                arg_schema={
                    "date": str,
                    "daily_announcement_report": str,
                    "process_documents": bool,
                    "skip_download": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/asx/daily_asx_all_announcements_report*.json"],
                timeout_seconds=7200,
            ),
            "single_ticker_announcement_backfill": ActionSpec(
                id="single_ticker_announcement_backfill",
                label="Single ticker backfill",
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
                    "{single_ticker_backfill_report}",
                ],
                arg_schema={
                    "ticker": str,
                    "years": float,
                    "max_backfill_retries": int,
                    "resume_max_retries": int,
                    "resume_retry_delay_seconds": float,
                    "single_ticker_backfill_report": str,
                    "process_documents": bool,
                    "no_resume_pending": bool,
                    "allow_warning": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/ticker_full_history_report*.json"],
                timeout_seconds=14400,
            ),
            "universe_announcement_enrichment_backfill": ActionSpec(
                id="universe_announcement_enrichment_backfill",
                label="Universe announcement backfill",
                command_template=[
                    py,
                    "scripts/run_asx_enrichment_chunked.py",
                    "--end-date",
                    "{date}",
                    "--total-days-back",
                    "{total_days_back}",
                    "--chunk-days",
                    "{chunk_days}",
                    "--fallback-max-tickers",
                    "{fallback_max_tickers}",
                    "--ticker-universe-file",
                    "{ticker_universe_file}",
                    "--request-delay-ms",
                    "{request_delay_ms}",
                    "--request-jitter-ms",
                    "{request_jitter_ms}",
                    "--failure-backoff-ms",
                    "{failure_backoff_ms}",
                    "--max-consecutive-failures",
                    "{max_consecutive_failures}",
                    "--max-errors",
                    "{max_errors}",
                    "--stop-after-empty-days",
                    "{stop_after_empty_days}",
                    "--reports-dir",
                    "{asx_chunk_reports_dir}",
                    "--rollup-report",
                    "{universe_backfill_rollup_report}",
                ],
                arg_schema={
                    "date": str,
                    "total_days_back": int,
                    "chunk_days": int,
                    "fallback_max_tickers": int,
                    "ticker_universe_file": str,
                    "request_delay_ms": int,
                    "request_jitter_ms": int,
                    "failure_backoff_ms": int,
                    "max_consecutive_failures": int,
                    "max_errors": int,
                    "stop_after_empty_days": int,
                    "asx_chunk_reports_dir": str,
                    "universe_backfill_rollup_report": str,
                    "download_existing_missing": bool,
                    "process_documents": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/asx/asx_enrichment_chunked_rollup*.json"],
                timeout_seconds=21600,
            ),
            "metric_extraction": ActionSpec(
                id="metric_extraction",
                label="Metric extraction",
                command_template=[
                    py,
                    "scripts/rebuild_ticker_financials_from_docs.py",
                    "--ticker",
                    "{ticker}",
                    "--report",
                    "{metric_extraction_report}",
                ],
                arg_schema={
                    "ticker": str,
                    "limit": int,
                    "since": str,
                    "include_non_financial_candidates": bool,
                    "force": bool,
                    "with_embeddings": bool,
                    "metric_extraction_report": str,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/rebuild_ticker_financials_from_docs_*.json"],
                timeout_seconds=10800,
            ),
            "show_candlestick": ActionSpec(
                id="show_candlestick",
                label="Generate candlestick / price chart",
                command_template=[
                    py,
                    "scripts/noop_chart.py",
                    "--ticker",
                    "{ticker}",
                ],
                arg_schema={
                    "ticker": str,
                    "mode_flag": str,
                    "mode_value": str,
                    "timeframe": str,
                },
                is_mutating=False,
                requires_confirmation=False,
                expected_outputs=["reports/cockpit/*candle*.html"],
                timeout_seconds=60,
            ),
        }

    def list_actions(self) -> list[ActionSpec]:
        return [self._actions[action_id] for action_id in _STREAMLINED_ACTION_IDS if action_id in self._actions]

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

        if action_id == "full_history" and normalized.get("process_documents"):
            command.append("--process-documents")
        if action_id == "update_ticker_financials" and normalized.get("process_documents", True):
            command.append("--process-documents")
        if action_id == "update_ticker_financials" and not normalized.get("process_documents", True):
            command.append("--no-process-documents")
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
        if action_id in {"asx_enrichment_chunked", "universe_announcement_enrichment_backfill"}:
            if normalized.get("download_existing_missing", True):
                command.append("--download-existing-missing")
            else:
                command.append("--no-download-existing-missing")
            if normalized.get("process_documents"):
                command.append("--process-documents")
        if action_id == "daily_news_ingest":
            if normalized.get("asx_wide"):
                command.append("--asx-wide")
            tickers_raw = str(normalized.get("tickers", "")).strip()
            if tickers_raw:
                command.extend(["--tickers", tickers_raw])
            if normalized.get("auto_live_when_capture_missing"):
                command.append("--auto-live-when-capture-missing")
        if action_id == "historical_news_ingest":
            if normalized.get("no_resume"):
                command.append("--no-resume")
            if normalized.get("asx_wide"):
                command.append("--asx-wide")
            tickers_raw = str(normalized.get("tickers", "")).strip()
            if tickers_raw:
                command.extend(["--tickers", tickers_raw])
            if normalized.get("auto_live_when_capture_missing"):
                command.append("--auto-live-when-capture-missing")
        if action_id == "daily_announcement_ingest":
            if normalized.get("process_documents"):
                command.append("--process-documents")
            if normalized.get("skip_download"):
                command.append("--skip-download")
        if action_id == "single_ticker_announcement_backfill":
            if normalized.get("process_documents"):
                command.append("--process-documents")
            if normalized.get("no_resume_pending"):
                command.append("--no-resume-pending")
            if normalized.get("allow_warning", True):
                command.append("--allow-warning")
        if action_id == "metric_extraction":
            if int(normalized.get("limit", 0)) > 0:
                command.extend(["--limit", str(normalized["limit"])])
            since = str(normalized.get("since", "")).strip()
            if since:
                command.extend(["--since", since])
            if normalized.get("include_non_financial_candidates"):
                command.append("--include-non-financial-candidates")
            if normalized.get("force"):
                command.append("--force")
            if normalized.get("with_embeddings"):
                command.append("--with-embeddings")
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

        # Pre-flight: extraction endpoint guard.
        from cockpit.core.action_runtime_guards import check_extraction_endpoint
        ok, guard_msg = check_extraction_endpoint(action_id, args)
        if not ok:
            raise ValueError(guard_msg)

        impact = "mutates local data and reports" if spec.is_mutating else "read-only"
        return ActionPreview(
            action_id=action_id,
            command=command,
            summary=f"Run {spec.label}",
            estimated_impact=impact,
            timeout_seconds=spec.timeout_seconds,
            guard_message=guard_msg if guard_msg else None,
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

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "y"}:
            return True
        if text in {"0", "false", "no", "off", "n"}:
            return False
        return default

    @classmethod
    def extract_control_args(cls, args: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
        src = dict(args or {})
        dry_run = False
        for key in (
            "dry_run",
            "dry-run",
            "dryrun",
            "preview_only",
            "preview-only",
            "noop",
            "no-op",
        ):
            if key in src:
                raw_value = src.pop(key)
                dry_run = dry_run or cls._to_bool(raw_value, default=False)
        return src, {"dry_run": dry_run}

    def doctor(self, check_help: bool = True, action_id: str | None = None) -> dict[str, Any]:
        specs = [self.get(action_id)] if action_id else self.list_actions()
        preflight = self._run_preflight(specs)

        checks: list[dict[str, Any]] = []
        ok_count = 0
        for spec in specs:
            row: dict[str, Any] = {
                "action_id": spec.id,
                "label": spec.label,
                "is_mutating": bool(spec.is_mutating),
                "requires_confirmation": bool(spec.requires_confirmation),
                "timeout_seconds": int(spec.timeout_seconds),
            }
            try:
                command = self.build_command(spec.id, {})
                row["command"] = command
            except Exception as exc:
                row["ok"] = False
                row["error"] = f"build_command failed: {exc}"
                checks.append(row)
                continue

            python_path = str(command[0]) if command else ""
            row["python"] = python_path
            row["python_exists"] = bool(python_path) and Path(python_path).exists()

            script_rel = str(command[1]) if len(command) > 1 else ""
            script_path = (self.repo_root / script_rel).resolve() if script_rel else self.repo_root
            row["script"] = script_rel
            row["script_exists"] = bool(script_rel) and script_path.exists()

            if check_help and row["python_exists"] and row["script_exists"]:
                try:
                    proc = subprocess.run(
                        [python_path, script_rel, "--help"],
                        cwd=str(self.repo_root),
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    row["help_returncode"] = int(proc.returncode)
                    stderr = str(proc.stderr or "").strip()
                    if stderr:
                        row["help_stderr"] = stderr.splitlines()[:3]
                except Exception as exc:
                    row["help_error"] = str(exc)

            row_ok = bool(row.get("python_exists")) and bool(row.get("script_exists"))
            if check_help:
                row_ok = row_ok and int(row.get("help_returncode", 1)) == 0 and not row.get("help_error")
            row["ok"] = row_ok
            if row_ok:
                ok_count += 1
            checks.append(row)

        return {
            "ok": ok_count == len(checks) and bool(preflight.get("ok", True)),
            "preflight": preflight,
            "counts": {
                "total": len(checks),
                "ok": ok_count,
                "failed": max(0, len(checks) - ok_count),
            },
            "checks": checks,
        }

    def _run_preflight(self, specs: list[ActionSpec]) -> dict[str, Any]:
        output_dirs: set[Path] = set()
        for spec in specs:
            for pattern in spec.expected_outputs:
                parent = Path(pattern).parent
                output_dirs.add((self.repo_root / parent).resolve())

        output_rows = [self._check_writable_dir(path) for path in sorted(output_dirs, key=str)]
        outputs_ok = all(bool(row.get("ok")) for row in output_rows)
        return {
            "ok": outputs_ok,
            "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "warnings": [],
            "checks": [
                {
                    "id": "write_permissions",
                    "ok": outputs_ok,
                    "output_dirs_checked": len(output_rows),
                    "output_dirs": output_rows,
                }
            ],
        }

    @staticmethod
    def _first_existing_parent(path: Path) -> Path:
        current = path
        while not current.exists() and current != current.parent:
            current = current.parent
        return current

    @classmethod
    def _check_writable_dir(cls, dir_path: Path) -> dict[str, Any]:
        exists = dir_path.exists()
        is_dir = dir_path.is_dir() if exists else False
        writable = os.access(str(dir_path), os.W_OK) if exists else False
        parent = cls._first_existing_parent(dir_path)
        parent_exists = parent.exists()
        parent_writable = os.access(str(parent), os.W_OK) if parent_exists else False
        ok = (exists and is_dir and writable) or (not exists and parent_exists and parent_writable)
        return {
            "path": str(dir_path),
            "exists": exists,
            "is_dir": is_dir,
            "writable": writable,
            "parent": str(parent),
            "parent_exists": parent_exists,
            "parent_writable": parent_writable,
            "ok": ok,
        }

    def _normalize_args(self, spec: ActionSpec, args: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value_type in spec.arg_schema.items():
            value = args.get(key)
            if value is None:
                continue
            if value_type is bool:
                out[key] = self._to_bool(value, default=False)
            elif value_type is int:
                try:
                    out[key] = int(value)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Arg '{key}' must be an integer, got {value!r}") from exc
            elif value_type is float:
                try:
                    out[key] = float(value)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Arg '{key}' must be a number, got {value!r}") from exc
            else:
                out[key] = str(value)

        ts = uuid.uuid4().hex[:8]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if not out.get("ticker") and spec.id in TICKER_REQUIRED_ACTION_IDS:
            raise ValueError(
                f"Action '{spec.id}' requires a ticker. "
                f"Provide one via the input field (e.g. ticker=CSL) or specify it in your message."
            )
        out.setdefault("ticker", "")
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
        out.setdefault("date", today)
        out.setdefault("days_back", 30)
        out.setdefault("total_days_back", 1825)
        out.setdefault("chunk_days", 14)
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
        out.setdefault("max_tickers", 0)
        out.setdefault("ticker_universe_file", str(self.repo_root / "data" / "raw" / "asx_ticker_universe.txt"))
        out.setdefault("process_documents", False)
        out.setdefault("allow_warning", True)
        out.setdefault("no_resume_pending", False)
        out.setdefault("include_non_financial_candidates", False)
        out.setdefault("force", False)
        out.setdefault("with_embeddings", False)

        if spec.id in {
            "update_ticker_financials",
            "daily_announcement_ingest",
            "single_ticker_announcement_backfill",
            "universe_announcement_enrichment_backfill",
            "asx_enrichment_chunked",
        }:
            out["process_documents"] = self._to_bool(args.get("process_documents"), default=True)

        out.setdefault("report_path", f"reports/cockpit_{spec.id}_{ts}.json")
        if spec.id == "update_ticker_financials":
            out.setdefault("report_path", f"reports/financial_update_{out.get('ticker', 'UNKNOWN')}_{ts}.json")
        if spec.id == "sort_asx_docs" and "ticker" not in args:
            out["ticker"] = ""
        if spec.id == "sort_asx_docs" and "limit" not in args:
            out["limit"] = 0

        out.setdefault("daily_report", f"reports/marketindex/daily_marketindex_action_report_{ts}.json")
        out.setdefault("download_report", f"reports/marketindex/pdf_download_report_{ts}.json")
        out.setdefault("daily_asx_report", f"reports/asx/daily_asx_all_announcements_report_{ts}.json")
        out.setdefault("asx_sweep_report", f"reports/asx/asx_enrichment_sweep_report_{ts}.json")
        out.setdefault("asx_chunk_reports_dir", "reports/asx")
        out.setdefault("asx_chunk_rollup_report", f"reports/asx/asx_enrichment_chunked_rollup_{ts}.json")
        out.setdefault("daily_announcement_report", f"reports/asx/daily_asx_all_announcements_report_{ts}.json")
        out.setdefault("single_ticker_backfill_report", f"reports/ticker_full_history_report_{ts}.json")
        out.setdefault("universe_backfill_rollup_report", f"reports/asx/asx_enrichment_chunked_rollup_{ts}.json")
        out.setdefault("metric_extraction_report", f"reports/rebuild_ticker_financials_from_docs_{out.get('ticker', 'UNKNOWN')}_{ts}.json")
        out.setdefault("db_path", str(self.repo_root.parent / "reports" / "qual_context" / "news_articles.sqlite"))
        out.setdefault("qdrant_url", "http://localhost:6333")
        out.setdefault("collection", "news_chunks")
        out.setdefault("batch_size", 64)
        out.setdefault("providers", "eodhd,gdelt")
        if spec.id == "load_news_to_qdrant":
            out.setdefault("since_hours", 0)
        out.setdefault("since_hours", 36)
        out.setdefault("news_runs_root", str(self.repo_root.parent / "reports" / "qual_context" / "news_runs"))
        out.setdefault("provider", "gdelt")
        out.setdefault("from_day", "2026-01-01")
        out.setdefault("to_day", today)
        out.setdefault("run_id", "")
        out.setdefault("max_days", 0)
        out.setdefault("lane", "high_precision")
        out.setdefault("tickers", "")
        out.setdefault("no_resume", False)
        out.setdefault("importance_report", f"reports/importance/announcement_importance_report_{ts}.json")
        out.setdefault("rebuild_report", f"reports/rebuild_ticker_financials_from_docs_{out.get('ticker', 'UNKNOWN')}_{ts}.json")
        out.setdefault("audit_report", f"reports/audit_ticker_financials_{out.get('ticker', 'UNKNOWN')}_{ts}.json")

        return out
