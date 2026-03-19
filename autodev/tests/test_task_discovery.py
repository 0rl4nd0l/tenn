from __future__ import annotations

import json
from pathlib import Path
import re
import time

from autodev.runtime import control
from autodev.runtime.config import AutoDevConfig
from autodev.runtime.task_discovery import (
    append_tasks_to_queue,
    mark_discovery_run,
    scan_repo,
    should_run_discovery,
)


PRIORITY_RE = re.compile(r"\(priority=(\d+)\)\s*$")


def _config(repo: Path) -> AutoDevConfig:
    return AutoDevConfig(
        repo_path=repo,
        default_branch="main",
        max_retries=1,
        allow_network=False,
        pr_mode="local_patch",
        notification_mode="stdout",
        notification_webhook_file=None,
        daemon_interval_seconds=1,
        gate_timeout_seconds=5,
        use_docker_if_available=False,
        docker_image="autodev-gates:latest",
        dockerfile_path="autodev/docker/Dockerfile",
        docker_auto_build=False,
        max_changed_lines_per_attempt=300,
        max_changed_files_per_attempt=20,
        worker_name="local_patch",
        llm_routing_mode="simple",
        llm_provider_balanced="ollama",
        llm_provider_heavy="ollama",
        llama_cpp_base_url="http://127.0.0.1:8080",
        llama_cpp_api_key="",
        llama_cpp_model_balanced="qwen2.5-coder-14b",
        llama_cpp_model_heavy="qwen2.5-coder-14b",
        ollama_host="http://127.0.0.1:11434",
        ollama_model_balanced="qwen2.5-coder:7b",
        ollama_model_heavy="qwen2.5:32b",
        ollama_timeout_seconds=120,
        openai_model="gpt-4.1-mini",
        llm_max_generation_attempts=3,
        allowed_paths=("autodev/",),
        protected_paths=(".github/", "financial-engine_v2/", "scripts/", "docs/"),
        baseline_path=repo / "autodev/baselines/baseline_metrics.json",
        allow_baseline_init=False,
        allow_baseline_update=False,
        protected_metrics=(),
        regression_tolerances={},
        enable_debate=False,
        debate_strictness="strict",
        debate_require_3_failure_modes=True,
        python_bin="python3",
    )


def _write_fixture_repo(repo: Path) -> None:
    (repo / "autodev/runtime").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/spec").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/tests").mkdir(parents=True, exist_ok=True)

    long_body = "\n".join(f"    total += {idx}" for idx in range(170))
    (repo / "autodev/runtime/module_no_test.py").write_text(
        "\n".join(
            [
                "import os",
                "",
                "def huge_fn():",
                "    total = 0",
                long_body,
                "    # TODO: split this function",
                "    return total",
                "",
                "def slow_fn(items):",
                "    total = 0",
                "    for left in items:",
                "        for right in items:",
                "            total += left * right",
                "    return total",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "autodev/runtime/huge_file.py").write_text(
        "\n".join(["value = 1"] * 1001) + "\n",
        encoding="utf-8",
    )
    (repo / "autodev/spec/MILESTONES.md").write_text(
        "\n".join(
            [
                "# MILESTONES",
                "",
                "## Milestone",
                "id: M1",
                "dod: x",
                "commands: ruff,pytest,eval",
                "required_artifacts: autodev/evals/results.json",
                "thresholds: demo_pass_rate=1.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "autodev/spec/TASKS.md").write_text("# TASKS\n\n", encoding="utf-8")


def test_scan_repo_emits_expected_task_types(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_fixture_repo(repo)

    tasks = scan_repo(repo)

    assert tasks
    assert len(tasks) <= 20
    assert any("Refactor large function" in task for task in tasks)
    assert any("Modularize large Python file" in task for task in tasks)
    assert any("Resolve TODO/FIXME" in task for task in tasks)
    assert any("Add tests for module autodev/runtime/module_no_test.py" in task for task in tasks)
    assert any("Optimize potentially slow function slow_fn" in task for task in tasks)
    assert any("Remove unused import os" in task for task in tasks)
    assert any("Add docstring to function" in task for task in tasks)
    priorities: list[int] = []
    for task in tasks:
        assert task.startswith("- [ ] ")
        assert " | milestone:" in task
        assert " | slug:" in task
        assert " | title:" in task
        match = PRIORITY_RE.search(task)
        assert match is not None
        priorities.append(int(match.group(1)))
    assert priorities == sorted(priorities, reverse=True)


def test_append_tasks_to_queue_and_control_discover(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    _write_fixture_repo(repo)
    tasks_path = repo / "autodev/spec/TASKS.md"

    added_first = append_tasks_to_queue(repo, ["- [ ] T1 | milestone:M1 | slug:x | title:X"])
    assert added_first == 1
    added_second = append_tasks_to_queue(repo, ["- [ ] T1 | milestone:M1 | slug:x | title:X"])
    assert added_second == 0

    cfg = _config(repo)
    rc = control.cmd_discover(cfg)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Discovered " in out
    assert "Added to TASKS.md" in out
    content = tasks_path.read_text(encoding="utf-8")
    assert "T_auto_" in content


def test_discovery_interval_state_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_fixture_repo(repo)

    assert should_run_discovery(900, repo_path=repo)
    mark_discovery_run(repo_path=repo)
    assert not should_run_discovery(900, repo_path=repo)

    state_path = repo / "autodev/state/discovery_state.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert "last_run" in payload

    state_path.write_text(json.dumps({"last_run": time.time() - 901}), encoding="utf-8")
    assert should_run_discovery(900, repo_path=repo)
