"""Task and milestone parsing for autodev."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


LEGACY_TASK_RE = re.compile(
    r"^- \[(?P<status>[ xX])\] (?P<task_id>[^|]+)\| milestone:(?P<milestone>[^|]+)\| slug:(?P<slug>[^|]+)\| title:(?P<title>.+)$"
)
USER_TASK_RE = re.compile(
    r"^- \[(?P<status>[ xX])\] (?P<task_id>T_user_[^\s|]+)\s+(?P<title>.+)$"
)


def _safe_slug(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    slug = "-".join(tokens[:10]).strip("-")
    return slug or "user-task"


@dataclass(frozen=True)
class Task:
    task_id: str
    milestone_id: str
    slug: str
    title: str
    completed: bool
    line_number: int


@dataclass(frozen=True)
class Milestone:
    milestone_id: str
    dod: str
    commands: list[str]
    required_artifacts: list[str]
    thresholds: dict[str, float]


def load_tasks(tasks_path: Path) -> list[Task]:
    if not tasks_path.exists():
        return []
    tasks: list[Task] = []
    for line_number, raw_line in enumerate(tasks_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        legacy = LEGACY_TASK_RE.match(line)
        if legacy:
            task_id = legacy.group("task_id").strip()
            milestone = legacy.group("milestone").strip()
            slug = legacy.group("slug").strip()
            title = legacy.group("title").strip()
            completed = legacy.group("status").lower() == "x"
        else:
            user_task = USER_TASK_RE.match(line)
            if not user_task:
                continue
            task_id = user_task.group("task_id").strip()
            title = user_task.group("title").strip()
            completed = user_task.group("status").lower() == "x"
            milestone = "M1"
            slug = _safe_slug(f"{task_id} {title}")

        tasks.append(
            Task(
                task_id=task_id,
                milestone_id=milestone,
                slug=slug,
                title=title,
                completed=completed,
                line_number=line_number,
            )
        )
    return tasks


def get_next_incomplete_task(tasks: list[Task]) -> Task | None:
    pending = [task for task in tasks if not task.completed]
    if not pending:
        return None
    user_pending = [task for task in pending if task.task_id.startswith("T_user_")]
    if user_pending:
        return user_pending[-1]
    return pending[0]


def load_milestones(milestones_path: Path) -> dict[str, Milestone]:
    if not milestones_path.exists():
        return {}
    lines = milestones_path.read_text(encoding="utf-8").splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current:
                blocks.append(current)
            current = []
            continue
        if stripped:
            current.append(stripped)
    if current:
        blocks.append(current)

    milestones: dict[str, Milestone] = {}
    for block in blocks:
        kv: dict[str, str] = {}
        for line in block:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            kv[key.strip()] = value.strip()
        if "id" not in kv:
            continue
        milestone_id = kv["id"]
        commands = [c.strip() for c in kv.get("commands", "").split(",") if c.strip()]
        required_artifacts = [
            item.strip() for item in kv.get("required_artifacts", "").split(",") if item.strip()
        ]
        thresholds: dict[str, float] = {}
        for item in kv.get("thresholds", "").split(","):
            if "=" not in item:
                continue
            metric, raw_value = item.split("=", 1)
            metric = metric.strip()
            try:
                thresholds[metric] = float(raw_value.strip())
            except ValueError:
                continue
        milestones[milestone_id] = Milestone(
            milestone_id=milestone_id,
            dod=kv.get("dod", ""),
            commands=commands,
            required_artifacts=required_artifacts,
            thresholds=thresholds,
        )
    return milestones
