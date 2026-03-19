from __future__ import annotations

from pathlib import Path

from autodev.runtime.task_queue import get_next_incomplete_task, load_tasks


def test_load_tasks_supports_user_task_format(tmp_path: Path) -> None:
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text(
        "\n".join(
            [
                "# TASKS",
                "- [ ] T_auto_foo | milestone:M1 | slug:auto-foo | title:Legacy task",
                "- [ ] T_user_20260305120000_optimize_pdf_parser Optimize PDF parser performance",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    tasks = load_tasks(tasks_path)
    assert len(tasks) == 2
    user_task = tasks[1]
    assert user_task.task_id == "T_user_20260305120000_optimize_pdf_parser"
    assert user_task.milestone_id == "M1"
    assert user_task.title == "Optimize PDF parser performance"
    assert user_task.slug.startswith("t-user-20260305120000-optimize-pdf-parser")


def test_get_next_incomplete_task_prioritizes_latest_user_task(tmp_path: Path) -> None:
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text(
        "\n".join(
            [
                "# TASKS",
                "- [ ] T_auto_foo | milestone:M1 | slug:auto-foo | title:Legacy task",
                "- [ ] T_user_20260305120000_first First user task",
                "- [ ] T_user_20260305123000_second Second user task",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    tasks = load_tasks(tasks_path)
    next_task = get_next_incomplete_task(tasks)
    assert next_task is not None
    assert next_task.task_id == "T_user_20260305123000_second"
