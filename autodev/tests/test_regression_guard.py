from __future__ import annotations

import json
from pathlib import Path
import subprocess

from autodev.runtime import autodev_loop
from autodev.runtime.config import AutoDevConfig
from autodev.runtime.gates import GateResult
from autodev.runtime.regression_guard import evaluate_regression
from autodev.runtime.sandbox_runner import CommandResult


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr}")


def _init_repo(repo: Path) -> None:
    _run(["git", "init"], repo)
    _run(["git", "add", "-A"], repo)
    _run(
        [
            "git",
            "-c",
            "user.name=autodev-test",
            "-c",
            "user.email=autodev-test@example.com",
            "commit",
            "-m",
            "init",
        ],
        repo,
    )


def _write_minimal_spec(repo: Path) -> None:
    (repo / "autodev/spec").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/evals").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/reports/runs").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/reports/daily").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/baselines").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/spec/TASKS.md").write_text(
        "- [ ] T1 | milestone:M1 | slug:regression-test | title:Regression test task\n",
        encoding="utf-8",
    )
    (repo / "autodev/spec/MILESTONES.md").write_text(
        "\n".join(
            [
                "## Milestone",
                "id: M1",
                "dod: test",
                "commands: ruff,pytest,eval",
                "required_artifacts: autodev/evals/results.json",
                "thresholds: demo_pass_rate=1.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "autodev/evals/results.json").write_text(
        json.dumps({"metrics": {"demo_pass_rate": 1.0}}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _config(repo: Path, allow_init: bool, allow_update: bool) -> AutoDevConfig:
    return AutoDevConfig(
        repo_path=repo,
        default_branch="main",
        max_retries=2,
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
        allow_baseline_init=allow_init,
        allow_baseline_update=allow_update,
        protected_metrics=("demo_pass_rate",),
        regression_tolerances={"demo_pass_rate": 0.0},
        enable_debate=False,
        debate_strictness="strict",
        debate_require_3_failure_modes=True,
        python_bin="python3",
    )


def _passing_gates() -> list[GateResult]:
    out: list[GateResult] = []
    for name in ("ruff", "pytest", "eval"):
        out.append(
            GateResult(
                name=name,
                command=[name],
                result=CommandResult(
                    command=[name],
                    exit_code=0,
                    stdout="ok",
                    stderr="",
                    started_at="n/a",
                    duration_seconds=0.0,
                    log_path=Path("/tmp/pass.json"),
                    used_docker=False,
                ),
                passed=True,
                log_path=Path("/tmp/pass.json"),
            )
        )
    return out


def test_baseline_missing_init_blocked() -> None:
    result = evaluate_regression(
        current_metrics={"demo_pass_rate": 1.0},
        baseline_path=Path("/tmp/nonexistent-baseline.json"),
        tolerances={"demo_pass_rate": 0.0},
        protected_metrics=("demo_pass_rate",),
        allow_baseline_init=False,
        allow_baseline_update=False,
        gates_passed=True,
        run_id="r1",
    )
    assert result.passed is False
    assert result.decision == "baseline_init_blocked"
    assert result.stop_retries is True


def test_baseline_init_allowed_creates_file(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    result = evaluate_regression(
        current_metrics={"demo_pass_rate": 1.0},
        baseline_path=baseline_path,
        tolerances={},
        protected_metrics=(),
        allow_baseline_init=True,
        allow_baseline_update=False,
        gates_passed=True,
        run_id="r2",
    )
    assert result.passed is True
    assert result.decision == "baseline_initialized"
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["source_run_id"] == "r2"
    assert payload["metrics"]["demo_pass_rate"] == 1.0


def test_regression_violation_triggers_fail(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at": "2026-03-04T00:00:00Z",
                "source_run_id": "seed",
                "metrics": {"demo_pass_rate": 1.0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = evaluate_regression(
        current_metrics={"demo_pass_rate": 0.95},
        baseline_path=baseline_path,
        tolerances={"demo_pass_rate": 0.0},
        protected_metrics=("demo_pass_rate",),
        allow_baseline_init=False,
        allow_baseline_update=False,
        gates_passed=True,
        run_id="r3",
    )
    assert result.passed is False
    assert result.decision == "fail"
    assert len(result.violations) == 1


def test_within_tolerance_passes(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at": "2026-03-04T00:00:00Z",
                "source_run_id": "seed",
                "metrics": {"demo_pass_rate": 1.0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = evaluate_regression(
        current_metrics={"demo_pass_rate": 0.99},
        baseline_path=baseline_path,
        tolerances={"demo_pass_rate": 0.02},
        protected_metrics=("demo_pass_rate",),
        allow_baseline_init=False,
        allow_baseline_update=False,
        gates_passed=True,
        run_id="r4",
    )
    assert result.passed is True
    assert result.decision == "pass"


def test_baseline_update_requires_allow_flag(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at": "2026-03-04T00:00:00Z",
                "source_run_id": "seed",
                "metrics": {"demo_pass_rate": 1.0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = evaluate_regression(
        current_metrics={"demo_pass_rate": 1.0},
        baseline_path=baseline_path,
        tolerances={"demo_pass_rate": 0.0},
        protected_metrics=("demo_pass_rate",),
        allow_baseline_init=False,
        allow_baseline_update=False,
        gates_passed=True,
        run_id="r5",
    )
    assert result.decision == "pass"
    assert json.loads(baseline_path.read_text(encoding="utf-8"))["source_run_id"] == "seed"

    updated = evaluate_regression(
        current_metrics={"demo_pass_rate": 1.0},
        baseline_path=baseline_path,
        tolerances={"demo_pass_rate": 0.0},
        protected_metrics=("demo_pass_rate",),
        allow_baseline_init=False,
        allow_baseline_update=True,
        gates_passed=True,
        run_id="r6",
    )
    assert updated.decision == "baseline_updated"
    assert json.loads(baseline_path.read_text(encoding="utf-8"))["source_run_id"] == "r6"


def test_loop_blocks_pr_when_baseline_init_not_allowed(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_minimal_spec(repo)
    _init_repo(repo)
    cfg = _config(repo, allow_init=False, allow_update=False)
    called: dict[str, int] = {"pr": 0}

    monkeypatch.setattr(autodev_loop, "run_gates", lambda **kwargs: _passing_gates())

    def _fake_pr(**kwargs):
        called["pr"] += 1
        raise AssertionError("PR stage should not be reached when regression blocks")

    monkeypatch.setattr(autodev_loop, "create_pr_or_fallback", _fake_pr)
    autodev_loop.run_once(cfg)
    assert called["pr"] == 0
    run_reports = sorted((repo / "autodev/reports/runs").glob("*/report.md"))
    assert run_reports
    run_dir = run_reports[-1].parent
    regression_path = run_dir / "regression.json"
    assert regression_path.exists()
    payload = json.loads(regression_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "baseline_init_blocked"
