from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ActionSpec:
    id: str
    label: str
    command_template: list[str]
    arg_schema: dict[str, type]
    is_mutating: bool
    requires_confirmation: bool
    expected_outputs: list[str]
    timeout_seconds: int = 3600


@dataclass
class JobRun:
    job_id: str
    action_id: str
    args: dict[str, Any]
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "queued"
    exit_code: int | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    artifacts: list[str] = field(default_factory=list)


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: datetime


@dataclass
class ToolResult:
    ok: bool
    title: str
    payload: dict[str, Any]
