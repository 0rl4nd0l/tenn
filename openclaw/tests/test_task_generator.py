from __future__ import annotations

import re
from pathlib import Path

from openclaw.task_generator import (
    append_task,
    extract_task_request_text,
    generate_task_from_text,
    is_dangerous_task_request,
    is_task_request,
)


def test_generate_task_from_text_experiment_marker() -> None:
    line = generate_task_from_text("optimize pdf parser speed")
    assert line.startswith("- [ ] T_user_")
    assert re.search(r"^- \[ \] T_user_\d{14}_[a-z0-9_]+ ", line)
    assert "[experiment:pytest -q]" in line
    assert line.endswith("Optimize pdf parser speed")


def test_generate_task_from_text_no_experiment_marker() -> None:
    line = generate_task_from_text("add tests for financial engine")
    assert line.startswith("- [ ] T_user_")
    assert "[experiment:pytest -q]" not in line
    assert line.endswith("Add tests for financial engine")


def test_is_dangerous_task_request() -> None:
    assert is_dangerous_task_request("shutdown system")
    assert is_dangerous_task_request("please rm this file")
    assert is_dangerous_task_request("format disk now")
    assert not is_dangerous_task_request("refactor the news ingestion pipeline")


def test_is_task_request_detection() -> None:
    assert is_task_request("optimize pdf parser")
    assert is_task_request("add tests for financial engine")
    assert is_task_request("task improve parser reliability")
    assert not is_task_request("hi")
    assert not is_task_request("hello there")
    assert not is_task_request("thanks")


def test_extract_task_request_text() -> None:
    assert extract_task_request_text("task optimize pdf parser") == "optimize pdf parser"
    assert extract_task_request_text("create task add tests") == "add tests"
    assert extract_task_request_text("improve pipeline") == "improve pipeline"


def test_append_task(tmp_path: Path) -> None:
    tasks_path = tmp_path / "TASKS.md"
    tasks_path.write_text("# TASKS\n", encoding="utf-8")
    line = "- [ ] T_user_20260305123456_add_tests Add tests for financial engine"
    append_task(line, tasks_path=tasks_path)
    assert tasks_path.read_text(encoding="utf-8").endswith(line + "\n")
