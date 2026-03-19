from __future__ import annotations

from autodev.runtime.task_scoring import rank_tasks, score_task


def test_score_task_applies_weight_and_runtime_bonus() -> None:
    assert score_task({"type": "docstring", "file": "autodev/runtime/x.py"}) == 50
    assert score_task({"type": "missing_tests", "file": "autodev/tests/x.py"}) == 90
    assert score_task({"type": "unknown", "file": "autodev/runtime/x.py"}) == 40


def test_rank_tasks_orders_by_priority_desc() -> None:
    tasks = [
        {"type": "docstring", "file": "autodev/runtime/a.py", "line": 3, "description": "a"},
        {"type": "missing_tests", "file": "autodev/runtime/b.py", "line": 1, "description": "b"},
        {"type": "todo", "file": "autodev/runtime/c.py", "line": 2, "description": "c"},
    ]
    ranked = rank_tasks(tasks)
    assert [item["type"] for item in ranked] == ["missing_tests", "todo", "docstring"]
