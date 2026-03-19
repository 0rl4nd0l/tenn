"""Create and append safe user-authored tasks for AutoDev."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re


TASKS_PATH = Path(__file__).resolve().parents[1] / "autodev" / "spec" / "TASKS.md"
EXPERIMENT_MARKER = "[experiment:pytest -q]"
EXPERIMENT_KEYWORDS = ("optimize", "speed", "performance", "faster", "latency")
DANGEROUS_TERMS = ("delete", "rm", "shutdown")
DANGEROUS_PHRASES = (
    "format disk",
    "shutdown -h",
    "shutdown -r",
    "rm -rf",
    "poweroff",
    "reboot now",
    "delete all",
)
TOKEN_RE = re.compile(r"[a-z0-9]+")
EXPLICIT_TASK_PREFIXES = (
    "task ",
    "todo ",
    "new task ",
    "create task ",
    "add task ",
    "autodev task ",
)
TASK_INTENT_KEYWORDS = (
    "optimize",
    "improve",
    "refactor",
    "fix",
    "implement",
    "add",
    "write",
    "create",
    "build",
    "update",
    "debug",
    "test",
    "document",
    "harden",
    "stabilize",
)
TASK_INTENT_PHRASES = (
    "add tests",
    "write tests",
    "create tests",
    "speed up",
    "make faster",
    "reduce latency",
)
SMALL_TALK_TOKENS = {
    "hi",
    "hello",
    "hey",
    "yo",
    "thanks",
    "thank",
    "ok",
    "okay",
    "cool",
}


def _clean_text(text: str) -> str:
    compact = " ".join(text.split()).strip()
    compact = compact.replace("|", "/")
    return compact


def _slug_fragment(text: str) -> str:
    tokens = TOKEN_RE.findall(text.lower())
    fragment = "_".join(tokens[:8]).strip("_")
    return fragment or "task"


def _description_from_text(user_text: str) -> str:
    cleaned = _clean_text(user_text)
    if not cleaned:
        return "User requested task"
    return cleaned[0].upper() + cleaned[1:]


def extract_task_request_text(user_text: str) -> str:
    """Return user text with explicit task prefixes removed."""
    cleaned = _clean_text(user_text)
    lowered = cleaned.lower()
    for prefix in EXPLICIT_TASK_PREFIXES:
        if lowered.startswith(prefix):
            remainder = cleaned[len(prefix) :].strip()
            return remainder or "User requested task"
    return cleaned


def _needs_experiment_marker(user_text: str) -> bool:
    lowered = user_text.lower()
    return any(keyword in lowered for keyword in EXPERIMENT_KEYWORDS)


def is_dangerous_task_request(user_text: str) -> bool:
    """Return True when user text includes forbidden terms."""
    lowered = _clean_text(user_text).lower()
    if not lowered:
        return False

    tokens = set(TOKEN_RE.findall(lowered))
    if any(term in tokens for term in DANGEROUS_TERMS):
        return True
    if any(phrase in lowered for phrase in DANGEROUS_PHRASES):
        return True
    return False


def is_task_request(user_text: str) -> bool:
    """Return True when text appears to be an actionable coding task."""
    cleaned = _clean_text(user_text)
    if not cleaned:
        return False

    lowered = cleaned.lower()
    if any(lowered.startswith(prefix) for prefix in EXPLICIT_TASK_PREFIXES):
        return True

    tokens = TOKEN_RE.findall(lowered)
    if len(tokens) < 2:
        return False
    if all(token in SMALL_TALK_TOKENS for token in tokens):
        return False
    if any(phrase in lowered for phrase in TASK_INTENT_PHRASES):
        return True
    if any(keyword in tokens for keyword in TASK_INTENT_KEYWORDS):
        return True
    return False


def generate_task_from_text(user_text: str) -> str:
    """Return a single TASKS.md line in user-task format."""
    description = _description_from_text(user_text)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    task_id = f"T_user_{timestamp}_{_slug_fragment(description)}"
    marker = f"{EXPERIMENT_MARKER} " if _needs_experiment_marker(user_text) else ""
    return f"- [ ] {task_id} {marker}{description}"


def append_task(task_line: str, tasks_path: Path | None = None) -> Path:
    """Append a task line to TASKS.md and return the target path."""
    target = tasks_path or TASKS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    needs_newline = False
    if target.exists() and target.stat().st_size > 0:
        with target.open("rb") as handle:
            handle.seek(-1, 2)
            needs_newline = handle.read(1) != b"\n"

    with target.open("a", encoding="utf-8") as handle:
        if needs_newline:
            handle.write("\n")
        handle.write(task_line.strip() + "\n")

    return target
