from __future__ import annotations

import json
from pathlib import Path
import subprocess

from autodev.runtime import autodev_loop
from autodev.runtime.config import AutoDevConfig
from autodev.runtime.debate import DebateOutput
from autodev.runtime.gates import GateResult
from autodev.runtime.regression_guard import RegressionResult
from autodev.runtime.sandbox_runner import CommandResult
from autodev.runtime.task_queue import Milestone, Task
from autodev.runtime.worker_interface import WorkerResult


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
        "- [ ] T1 | milestone:M1 | slug:debate-test | title:Debate layer task\n",
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
    (repo / "autodev/baselines/baseline_metrics.json").write_text(
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


def _config(repo: Path, max_retries: int = 2) -> AutoDevConfig:
    return AutoDevConfig(
        repo_path=repo,
        default_branch="main",
        max_retries=max_retries,
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
        protected_metrics=("demo_pass_rate",),
        regression_tolerances={"demo_pass_rate": 0.0},
        enable_debate=True,
        debate_strictness="strict",
        debate_require_3_failure_modes=True,
        python_bin="python3",
    )


def test_build_debate_context_uses_config_allowed_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    cfg = AutoDevConfig(
        **{
            **_config(repo).__dict__,
            "allowed_paths": ("autodev/", "openclaw/", "scripts/"),
        }
    )
    task = Task(
        task_id="T1",
        milestone_id="M1",
        slug="debate-test",
        title="Debate layer task",
        completed=False,
        line_number=1,
    )
    milestone = Milestone(
        milestone_id="M1",
        dod="test",
        commands=["pytest"],
        required_artifacts=[],
        thresholds={},
    )

    context = autodev_loop._build_debate_context(
        config=cfg,
        task=task,
        milestone=milestone,
        branch_name="agent/2026-03-09/debate-test",
        changed_files=["openclaw/nl_router.py"],
        changed_lines=1,
        phase="post_change_attempt_1",
    )

    assert context.allowed_paths == ("autodev/", "openclaw/", "scripts/")


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


def _pre_veto_outputs():
    return {
        "proposer": DebateOutput(
            role="proposer",
            passed=True,
            veto=False,
            reasons=["plan ok"],
            required_changes=[],
            risk_level="medium",
            stop_retries=False,
        ),
        "skeptic": DebateOutput(
            role="skeptic",
            passed=False,
            veto=True,
            reasons=["safety violation"],
            required_changes=["reduce risk"],
            risk_level="high",
            stop_retries=True,
        ),
        "auditor": DebateOutput(
            role="auditor",
            passed=True,
            veto=False,
            reasons=["ok"],
            required_changes=[],
            risk_level="low",
            stop_retries=False,
        ),
    }


def _post_veto_outputs():
    return {
        "proposer": DebateOutput(
            role="proposer",
            passed=True,
            veto=False,
            reasons=["plan ok"],
            required_changes=[],
            risk_level="medium",
            stop_retries=False,
        ),
        "skeptic": DebateOutput(
            role="skeptic",
            passed=True,
            veto=False,
            reasons=["ok"],
            required_changes=[],
            risk_level="low",
            stop_retries=False,
        ),
        "auditor": DebateOutput(
            role="auditor",
            passed=False,
            veto=True,
            reasons=["policy violation"],
            required_changes=["revert change"],
            risk_level="high",
            stop_retries=True,
        ),
    }


def test_pre_debate_veto_blocks_worker(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_minimal_spec(repo)
    _init_repo(repo)
    cfg = _config(repo, max_retries=3)
    called = {"worker": 0}

    monkeypatch.setattr(autodev_loop, "run_pre_change_debate", lambda context: _pre_veto_outputs())
    monkeypatch.setattr(autodev_loop, "run_post_change_debate", lambda context: _post_veto_outputs())

    def _worker(*args, **kwargs):
        called["worker"] += 1
        return WorkerResult(
            status="changed",
            summary="changed",
            files_changed=[],
            lines_changed=1,
            commit_created=False,
        )

    monkeypatch.setattr(autodev_loop, "run_worker", _worker)
    autodev_loop.run_once(cfg)
    assert called["worker"] == 0
    run_reports = sorted((repo / "autodev/reports/runs").glob("*/report.md"))
    report = run_reports[-1].read_text(encoding="utf-8")
    assert "debate_pre" in report
    assert "retries used: `1`" in report


def test_post_debate_veto_resets_changes_and_blocks_pr(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_minimal_spec(repo)
    _init_repo(repo)
    cfg = _config(repo, max_retries=2)
    called = {"pr": 0}

    monkeypatch.setattr(
        autodev_loop,
        "run_pre_change_debate",
        lambda context: {
            "proposer": DebateOutput("proposer", True, False, ["ok"], [], "low", False),
            "skeptic": DebateOutput("skeptic", True, False, ["ok"], [], "low", False),
            "auditor": DebateOutput("auditor", True, False, ["ok"], [], "low", False),
        },
    )
    monkeypatch.setattr(autodev_loop, "run_post_change_debate", lambda context: _post_veto_outputs())

    def _worker(request, worker_name):
        target = repo / "autodev" / "worker_outputs" / "debate-test.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
        return WorkerResult(
            status="changed",
            summary="changed",
            files_changed=["autodev/worker_outputs/debate-test.md"],
            lines_changed=1,
            commit_created=False,
        )

    monkeypatch.setattr(autodev_loop, "run_worker", _worker)
    monkeypatch.setattr(autodev_loop, "run_gates", lambda **kwargs: _passing_gates())

    def _fake_pr(**kwargs):
        called["pr"] += 1
        raise AssertionError("PR stage should not run on post debate veto")

    monkeypatch.setattr(autodev_loop, "create_pr_or_fallback", _fake_pr)
    autodev_loop.run_once(cfg)
    assert called["pr"] == 0
    assert not (repo / "autodev" / "worker_outputs" / "debate-test.md").exists()


def test_debate_artifacts_are_written(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_minimal_spec(repo)
    _init_repo(repo)
    cfg = _config(repo)

    monkeypatch.setattr(autodev_loop, "run_pre_change_debate", lambda context: _pre_veto_outputs())
    monkeypatch.setattr(autodev_loop, "run_post_change_debate", lambda context: _post_veto_outputs())
    autodev_loop.run_once(cfg)
    run_dirs = sorted((repo / "autodev/reports/runs").glob("*"))
    latest = run_dirs[-1]
    assert (latest / "debate_pre.json").exists()
    assert (latest / "debate_post.json").exists()
    post_payload = json.loads((latest / "debate_post.json").read_text(encoding="utf-8"))
    assert post_payload["meta"]["reason"] == "pre_veto"


def test_debate_pass_does_not_override_regression_or_gates(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_minimal_spec(repo)
    _init_repo(repo)
    cfg = _config(repo)

    monkeypatch.setattr(
        autodev_loop,
        "run_pre_change_debate",
        lambda context: {
            "proposer": DebateOutput("proposer", True, False, ["ok"], [], "low", False),
            "skeptic": DebateOutput("skeptic", True, False, ["ok"], [], "low", False),
            "auditor": DebateOutput("auditor", True, False, ["ok"], [], "low", False),
        },
    )
    monkeypatch.setattr(
        autodev_loop,
        "run_post_change_debate",
        lambda context: {
            "proposer": DebateOutput("proposer", True, False, ["ok"], [], "low", False),
            "skeptic": DebateOutput("skeptic", True, False, ["ok"], [], "low", False),
            "auditor": DebateOutput("auditor", True, False, ["ok"], [], "low", False),
        },
    )
    monkeypatch.setattr(autodev_loop, "run_gates", lambda **kwargs: _passing_gates())
    monkeypatch.setattr(
        autodev_loop,
        "run_worker",
        lambda request, worker_name: WorkerResult(
            status="changed",
            summary="changed",
            files_changed=[],
            lines_changed=0,
            commit_created=False,
        ),
    )
    monkeypatch.setattr(
        autodev_loop,
        "evaluate_regression",
        lambda **kwargs: RegressionResult(
            passed=False,
            violations=[],
            decision="fail",
            stop_retries=False,
            baseline_path=str(cfg.baseline_path),
        ),
    )
    autodev_loop.run_once(cfg)
    run_reports = sorted((repo / "autodev/reports/runs").glob("*/report.md"))
    report = run_reports[-1].read_text(encoding="utf-8")
    assert "Blocked by regression guard" in report
