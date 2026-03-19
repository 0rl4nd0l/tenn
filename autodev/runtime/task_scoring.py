"""Task scoring and deterministic prioritization for discovery output."""

from __future__ import annotations


TASK_WEIGHTS = {
    "bug": 100,
    "slow_function": 90,
    "missing_tests": 80,
    "dead_import": 60,
    "refactor_large_file": 50,
    "refactor_large_function": 50,
    "todo": 40,
    "docstring": 20,
}

MODULE_WEIGHTS = {
    "autodev/runtime": 30,
    "autodev/runtime/workers": 25,
    "autodev/runtime/gates": 25,
    "autodev/runtime/autodev_loop": 30,
    "autodev/runtime/control": 20,
    "autodev/runtime/task_discovery": 20,
    "autodev/tests": 10,
    "docs": 0,
}


def score_task(task: dict[str, object]) -> int:
    """Return priority score for a discovered task record."""
    task_type = str(task.get("type", "")).strip()
    base = int(TASK_WEIGHTS.get(task_type, 10))
    file_path = str(task.get("file", ""))
    module_bonus = 0
    for module, weight in MODULE_WEIGHTS.items():
        if module in file_path:
            module_bonus = max(module_bonus, weight)
    return base + module_bonus


def rank_tasks(tasks: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return tasks sorted by priority, with deterministic tie-breaking."""
    return sorted(
        tasks,
        key=lambda task: (
            -score_task(task),
            str(task.get("file", "")),
            int(task.get("line", 0) or 0),
            str(task.get("type", "")),
            str(task.get("description", "")),
        ),
    )
