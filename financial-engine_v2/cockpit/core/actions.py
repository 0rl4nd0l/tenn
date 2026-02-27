from __future__ import annotations

import os
import re
import shlex
import sqlite3
import subprocess
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
            "probe_all_system_tickers": ActionSpec(
                id="probe_all_system_tickers",
                label="Probe all system tickers (default 5y)",
                command_template=[
                    py,
                    "scripts/probe_all_system_tickers.py",
                    "--years",
                    "{years}",
                    "--max-tickers",
                    "{max_tickers}",
                    "--max-backfill-retries",
                    "{max_backfill_retries}",
                    "--resume-max-retries",
                    "{resume_max_retries}",
                    "--resume-retry-delay-seconds",
                    "{resume_retry_delay_seconds}",
                    "--report",
                    "{probe_report}",
                ],
                arg_schema={
                    "years": int,
                    "max_tickers": int,
                    "max_backfill_retries": int,
                    "resume_max_retries": int,
                    "resume_retry_delay_seconds": float,
                    "probe_report": str,
                    "ticker": str,
                    "process_documents": bool,
                    "no_resume_pending": bool,
                },
                is_mutating=True,
                requires_confirmation=confirm_required,
                expected_outputs=["reports/all_system_tickers_probe_report*.json"],
                timeout_seconds=14400,
            ),
            "asx_enrichment_chunked": ActionSpec(
                id="asx_enrichment_chunked",
                label="ASX enrichment chunked (default 5y)",
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
        if action_id == "probe_all_system_tickers":
            if str(normalized.get("ticker", "")).strip():
                command.extend(["--ticker", str(normalized["ticker"]).strip().upper()])
            if normalized.get("process_documents"):
                command.append("--process-documents")
            if normalized.get("no_resume_pending"):
                command.append("--no-resume-pending")
        if action_id == "asx_enrichment_chunked":
            if normalized.get("download_existing_missing", True):
                command.append("--download-existing-missing")
            else:
                command.append("--no-download-existing-missing")
            if normalized.get("process_documents"):
                command.append("--process-documents")
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

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "y", "ok"}:
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

    @staticmethod
    def _sanitize_command_for_compare(command: list[str]) -> list[str]:
        out: list[str] = []
        for token in command:
            normalized = str(token)
            normalized = normalized.replace("\\", "/")
            normalized = normalized.strip()
            normalized = normalized.lower()
            # Collapse generated run suffixes so command diffs are meaningful.
            normalized = re.sub(r"[0-9a-f]{8}", "<ts>", normalized)
            out.append(normalized)
        return out

    def doctor(self, check_help: bool = True, action_id: str | None = None) -> dict[str, Any]:
        specs: list[ActionSpec]
        if action_id:
            specs = [self.get(str(action_id).strip())]
        else:
            specs = self.list_actions()

        preflight = self._run_preflight(specs)
        script_to_actions: dict[str, list[str]] = {}
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

            command0 = str(command[0]) if command else ""
            py_exists = Path(command0).exists() if command0 else False
            row["python"] = command0
            row["python_exists"] = bool(py_exists)

            script_rel = str(command[1]) if len(command) > 1 else ""
            script_path = (self.repo_root / script_rel).resolve() if script_rel else self.repo_root
            script_exists = bool(script_rel) and script_path.exists()
            row["script"] = script_rel
            row["script_exists"] = script_exists
            if script_rel:
                script_to_actions.setdefault(script_rel, []).append(spec.id)

            bool_no_effect: list[str] = []
            for key, value_type in spec.arg_schema.items():
                if value_type is not bool:
                    continue
                try:
                    cmd_true = self.build_command(spec.id, {key: True})
                    cmd_false = self.build_command(spec.id, {key: False})
                    if self._sanitize_command_for_compare(cmd_true) == self._sanitize_command_for_compare(cmd_false):
                        bool_no_effect.append(key)
                except Exception:
                    # Keep doctor resilient; other checks still provide value.
                    continue
            if bool_no_effect:
                row["bool_args_no_effect"] = sorted(bool_no_effect)

            if check_help and py_exists and script_exists:
                help_cmd = [command[0], command[1], "--help"]
                try:
                    proc = subprocess.run(
                        help_cmd,
                        cwd=str(self.repo_root),
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=25,
                    )
                    row["help_returncode"] = int(proc.returncode)
                    if spec.is_mutating:
                        row["supports_dry_run"] = "--dry-run" in str(proc.stdout or "")
                    stderr = str(proc.stderr or "").strip()
                    if stderr:
                        row["help_stderr"] = stderr.splitlines()[:3]
                except Exception as exc:
                    row["help_error"] = str(exc)

            row_ok = bool(row.get("python_exists")) and bool(row.get("script_exists"))
            if check_help:
                row_ok = row_ok and int(row.get("help_returncode", 1)) == 0 and not row.get("help_error")
            row["ok"] = bool(row_ok)
            if row_ok:
                ok_count += 1
            checks.append(row)

        overlaps = [
            {"script": script, "actions": sorted(action_ids)}
            for script, action_ids in script_to_actions.items()
            if len(action_ids) > 1
        ]
        warnings: list[str] = []
        if overlaps:
            warnings.append("multiple action IDs map to the same script")
        if any(isinstance(item.get("bool_args_no_effect"), list) and item.get("bool_args_no_effect") for item in checks):
            warnings.append("one or more bool args do not change command output")
        if not bool(preflight.get("ok", True)):
            warnings.append("preflight checks reported one or more failures")

        ok_actions = ok_count == len(checks) and not overlaps
        ok_preflight = bool(preflight.get("ok", True))
        return {
            "ok": ok_actions and ok_preflight,
            "ok_actions": bool(ok_actions),
            "ok_preflight": bool(ok_preflight),
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "check_help": bool(check_help),
            "action_filter": str(action_id or "").strip() or None,
            "preflight": preflight,
            "counts": {
                "total": len(checks),
                "ok": ok_count,
                "failed": max(0, len(checks) - ok_count),
            },
            "overlaps": overlaps,
            "warnings": warnings,
            "checks": checks,
        }

    def _run_preflight(self, specs: list[ActionSpec]) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        warnings: list[str] = []

        output_dirs: set[Path] = set()
        for spec in specs:
            for pattern in spec.expected_outputs:
                try:
                    output_dirs.add((self.repo_root / Path(pattern).parent).resolve())
                except Exception:
                    continue

        outputs_rows: list[dict[str, Any]] = []
        outputs_ok = True
        for dir_path in sorted(output_dirs, key=lambda p: str(p)):
            row = self._check_writable_dir(dir_path)
            outputs_rows.append(row)
            outputs_ok = outputs_ok and bool(row.get("ok"))

        checks.append(
            {
                "id": "write_permissions",
                "ok": outputs_ok,
                "output_dirs_checked": len(outputs_rows),
                "output_dirs": outputs_rows,
            }
        )

        db_check = self._check_database()
        checks.append(db_check)
        if not bool(db_check.get("ok")):
            warnings.append("database check failed")

        ollama_check = self._check_ollama_models()
        checks.append(ollama_check)
        if not bool(ollama_check.get("ok", True)):
            warnings.append("ollama check failed")

        ok = all(bool(item.get("ok")) for item in checks)
        return {
            "ok": ok,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "warnings": warnings,
            "checks": checks,
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

    def _check_database(self) -> dict[str, Any]:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")
        row: dict[str, Any] = {"id": "database", "ok": True, "database_url": database_url}
        if not str(database_url).lower().startswith("sqlite:///"):
            row["kind"] = "non_sqlite"
            row["note"] = "Skipping path/table checks for non-sqlite DATABASE_URL."
            return row

        raw_path = str(database_url)[len("sqlite:///") :]
        row["kind"] = "sqlite"
        row["sqlite_path_raw"] = raw_path
        if raw_path in {"", ":memory:"} or raw_path.startswith("file:"):
            row["ok"] = False
            row["error"] = "Unsupported sqlite path for doctor check (expected file path)."
            return row

        p = Path(raw_path).expanduser()
        if not p.is_absolute():
            p = (self.repo_root / p).resolve()
        row["sqlite_path"] = str(p)
        row["exists"] = p.exists()
        row["readable"] = os.access(str(p), os.R_OK) if p.exists() else False
        row["writable"] = os.access(str(p), os.W_OK) if p.exists() else False
        row["parent"] = str(p.parent)
        row["parent_exists"] = p.parent.exists()
        row["parent_writable"] = os.access(str(p.parent), os.W_OK) if p.parent.exists() else False
        if p.exists():
            try:
                row["bytes"] = p.stat().st_size
            except Exception:
                pass

        if not p.exists():
            row["ok"] = False
            row["error"] = "sqlite database file does not exist"
            return row

        required_tables = ["documents", "asx_periodic_financials"]
        try:
            conn = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=2)
            try:
                cur = conn.cursor()
                cur.execute("select name from sqlite_master where type='table'")
                tables = sorted({str(r[0]) for r in cur.fetchall() if r and r[0]})
            finally:
                conn.close()
            row["table_count"] = len(tables)
            row["tables_sample"] = tables[:25]
            missing = [t for t in required_tables if t not in set(tables)]
            row["missing_required_tables"] = missing
            if missing:
                row["ok"] = False
                row["error"] = f"missing required tables: {', '.join(missing)}"
        except Exception as exc:
            row["ok"] = False
            row["error"] = str(exc)
        return row

    def _check_ollama_models(self) -> dict[str, Any]:
        base_url = (os.getenv("COCKPIT_OLLAMA_URL") or os.getenv("OLLAMA_URL") or "http://localhost:11434").strip()
        required = [
            str(os.getenv("COCKPIT_LLM_MODEL") or "").strip(),
            str(os.getenv("EXTRACT_MODEL") or "llama3:latest").strip(),
            str(os.getenv("EMBED_MODEL") or "nomic-embed-text").strip(),
        ]
        required_models = sorted({m for m in required if m})
        row: dict[str, Any] = {
            "id": "ollama",
            "ok": True,
            "ollama_url": base_url,
            "required_models": required_models,
        }

        try:
            from cockpit.integrations.ollama_client import OllamaClient

            client = OllamaClient(base_url, required_models[0] if required_models else "")
            health = client.health(timeout=2.5)
            row["health"] = health
            if not bool(health.get("ok")):
                row["ok"] = False
                row["error"] = str(health.get("error") or "ollama health failed")
                return row

            installed = set(str(m) for m in (health.get("models") or []) if m)
            missing = [m for m in required_models if m not in installed]
            row["missing_models"] = missing
            if missing:
                row["ok"] = False
                row["error"] = f"missing required ollama model(s): {', '.join(missing)}"
        except Exception as exc:
            row["ok"] = False
            row["error"] = str(exc)
        return row

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
        out.setdefault("probe_report", f"reports/all_system_tickers_probe_report_{ts}.json")
        out.setdefault("asx_chunk_reports_dir", "reports/asx")
        out.setdefault("asx_chunk_rollup_report", f"reports/asx/asx_enrichment_chunked_rollup_{ts}.json")
        out.setdefault("importance_report", f"reports/importance/announcement_importance_report_{ts}.json")
        out.setdefault("rebuild_report", f"reports/rebuild_ticker_financials_from_docs_{out.get('ticker', 'BHP')}_{ts}.json")
        out.setdefault("audit_report", f"reports/audit_ticker_financials_{out.get('ticker', 'BHP')}_{ts}.json")

        return out
