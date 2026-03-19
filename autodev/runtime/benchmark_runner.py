"""Sandbox-safe benchmark execution helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess
import time

from autodev.runtime.experiment_engine import FAILED_BENCHMARK_SCORE
from autodev.runtime.sandbox_runner import run_command


def benchmark_patch(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    allow_network: bool,
    prefer_docker: bool,
    docker_image: str,
    dockerfile_path: str,
    docker_auto_build: bool,
) -> tuple[float, bool, float, int]:
    """Run one benchmark command and return (score, passed, duration, exit_code)."""
    started = time.monotonic()
    try:
        result = run_command(
            command=command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            allow_network=allow_network,
            prefer_docker=prefer_docker,
            docker_image=docker_image,
            dockerfile_path=dockerfile_path,
            docker_auto_build=docker_auto_build,
        )
        duration = float(result.duration_seconds)
        if result.exit_code != 0:
            return FAILED_BENCHMARK_SCORE, False, duration, result.exit_code
        return -duration, True, duration, 0
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - started
        return FAILED_BENCHMARK_SCORE, False, duration, 124
    except Exception:
        duration = time.monotonic() - started
        return FAILED_BENCHMARK_SCORE, False, duration, 1
