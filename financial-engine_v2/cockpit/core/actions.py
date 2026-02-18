from __future__ import annotations

import shlex
import uuid
from dataclasses import dataclass
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
        if action_id == "daily_marketindex" and normalized.get("overwrite_pdfs"):
            command.append("--overwrite-pdfs")
        if action_id == "daily_marketindex" and normalized.get("skip_download"):
            command.append("--skip-download")
        if action_id == "resume_pending" and normalized.get("process_documents"):
            command.append("--process-documents")

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

        out.setdefault("report_path", f"reports/cockpit_{spec.id}_{ts}.json")
        out.setdefault("daily_report", f"reports/marketindex/daily_marketindex_action_report_{ts}.json")
        out.setdefault("download_report", f"reports/marketindex/pdf_download_report_{ts}.json")

        return out
