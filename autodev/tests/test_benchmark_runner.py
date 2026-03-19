from __future__ import annotations

from pathlib import Path
import subprocess

from autodev.runtime import benchmark_runner
from autodev.runtime.sandbox_runner import CommandResult


def test_benchmark_patch_success_returns_negative_duration(tmp_path: Path, monkeypatch) -> None:
    def fake_run_command(**kwargs) -> CommandResult:
        _ = kwargs
        return CommandResult(
            command=["pytest", "-q"],
            exit_code=0,
            stdout="ok",
            stderr="",
            started_at="n/a",
            duration_seconds=1.25,
            log_path=None,
            used_docker=False,
        )

    monkeypatch.setattr(benchmark_runner, "run_command", fake_run_command)
    score, passed, duration, exit_code = benchmark_runner.benchmark_patch(
        command=["pytest", "-q"],
        cwd=tmp_path,
        timeout_seconds=60,
        allow_network=False,
        prefer_docker=False,
        docker_image="autodev-gates:latest",
        dockerfile_path="autodev/docker/Dockerfile",
        docker_auto_build=False,
    )
    assert score == -1.25
    assert passed is True
    assert duration == 1.25
    assert exit_code == 0


def test_benchmark_patch_nonzero_returns_failure(tmp_path: Path, monkeypatch) -> None:
    def fake_run_command(**kwargs) -> CommandResult:
        _ = kwargs
        return CommandResult(
            command=["pytest", "-q"],
            exit_code=2,
            stdout="",
            stderr="failed",
            started_at="n/a",
            duration_seconds=0.4,
            log_path=None,
            used_docker=False,
        )

    monkeypatch.setattr(benchmark_runner, "run_command", fake_run_command)
    score, passed, duration, exit_code = benchmark_runner.benchmark_patch(
        command=["pytest", "-q"],
        cwd=tmp_path,
        timeout_seconds=60,
        allow_network=False,
        prefer_docker=False,
        docker_image="autodev-gates:latest",
        dockerfile_path="autodev/docker/Dockerfile",
        docker_auto_build=False,
    )
    assert score <= -1e9
    assert passed is False
    assert duration == 0.4
    assert exit_code == 2


def test_benchmark_patch_timeout_returns_failure(tmp_path: Path, monkeypatch) -> None:
    def fake_run_command(**kwargs) -> CommandResult:
        _ = kwargs
        raise subprocess.TimeoutExpired(cmd=["pytest", "-q"], timeout=60)

    monkeypatch.setattr(benchmark_runner, "run_command", fake_run_command)
    score, passed, duration, exit_code = benchmark_runner.benchmark_patch(
        command=["pytest", "-q"],
        cwd=tmp_path,
        timeout_seconds=60,
        allow_network=False,
        prefer_docker=False,
        docker_image="autodev-gates:latest",
        dockerfile_path="autodev/docker/Dockerfile",
        docker_auto_build=False,
    )
    assert score <= -1e9
    assert passed is False
    assert duration >= 0.0
    assert exit_code == 124
