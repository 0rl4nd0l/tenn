"""Sandboxed command execution with allowlists and logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import time


DISALLOWED_TOKENS = {
    "curl",
    "wget",
    "ssh",
    "scp",
    "pip",
    "pip3",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "brew",
}

DISALLOWED_PATTERNS = {
    ("rm", "-rf"),
    ("rm", "-fr"),
}

# Keep this strict. Expand only with explicit human approval.
ALLOWLIST: dict[str, set[str]] = {
    "python": {"-m"},
    "python3": {"-m"},
    "pytest": {"-q", "-k", "-m", "--maxfail", "--disable-warnings"},
    "ruff": {"check"},
    "git": {
        "status",
        "rev-parse",
        "branch",
        "checkout",
        "diff",
        "format-patch",
        "add",
        "commit",
        "log",
    },
}


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    started_at: str
    duration_seconds: float
    log_path: Path | None
    used_docker: bool


class CommandRejectedError(RuntimeError):
    """Raised when a command violates allowlist restrictions."""


def _is_flag(token: str) -> bool:
    return token.startswith("-")


def _validate_command(command: list[str], allow_network: bool) -> None:
    if not command:
        raise CommandRejectedError("Empty command is not allowed.")
    executable = command[0]
    if executable not in ALLOWLIST:
        raise CommandRejectedError(f"Executable '{executable}' is not allowlisted.")

    for token in command:
        if token in DISALLOWED_TOKENS and not allow_network:
            raise CommandRejectedError(f"Token '{token}' blocked by network/default policy.")

    if len(command) >= 2:
        pair = (command[0], command[1])
        if pair in DISALLOWED_PATTERNS:
            raise CommandRejectedError(f"Pattern '{pair[0]} {pair[1]}' is forbidden.")

    if executable == "ruff":
        if command == ["ruff", "--version"]:
            return
        if len(command) < 3 or command[1] != "check":
            raise CommandRejectedError(
                "ruff must be invoked as: ruff check [--no-cache|--cache-dir /tmp/<dir>] <path> or ruff --version"
            )
        idx = 2
        while idx < len(command) and command[idx].startswith("-"):
            token = command[idx]
            if token == "--no-cache":
                idx += 1
                continue
            if token == "--cache-dir":
                if idx + 1 >= len(command):
                    raise CommandRejectedError("ruff --cache-dir requires a directory argument.")
                cache_dir = command[idx + 1]
                if cache_dir != "/tmp/ruff_cache" and not cache_dir.startswith("/tmp/"):
                    raise CommandRejectedError("ruff --cache-dir must point to /tmp.")
                idx += 2
                continue
            raise CommandRejectedError(f"Unsupported ruff option: {token}")
        if idx >= len(command):
            raise CommandRejectedError("ruff check requires at least one target path.")
        return

    if executable == "pytest":
        if len(command) >= 2 and command[1] == "--version":
            return
        return

    if executable in {"python", "python3"}:
        if len(command) < 2:
            raise CommandRejectedError("python commands require a module or script argument.")
        if command[1] == "-m":
            if len(command) < 3:
                raise CommandRejectedError("python -m requires a module name.")
            return
        if command[1].endswith(".py") or "/" in command[1]:
            return
        raise CommandRejectedError("python command must use -m <module> or a script path.")

    allowed_subcommands = ALLOWLIST[executable]
    for token in command[1:]:
        if _is_flag(token):
            continue
        if token not in allowed_subcommands:
            raise CommandRejectedError(
                f"Token '{token}' is not an allowed subcommand/argument for '{executable}'."
            )


def _format_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def _write_log(log_path: Path, payload: dict[str, object]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run_subprocess(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    allow_network: bool,
    log_path: Path | None,
) -> CommandResult:
    started = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    env = os.environ.copy()
    if not allow_network:
        env["AUTODEV_NETWORK_DISABLED"] = "1"
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except FileNotFoundError as exc:
        exit_code = 127
        stdout = ""
        stderr = str(exc)
    duration = time.time() - started
    result = CommandResult(
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        started_at=started_at,
        duration_seconds=duration,
        log_path=log_path,
        used_docker=False,
    )
    if log_path:
        _write_log(
            log_path,
            {
                "started_at": started_at,
                "duration_seconds": duration,
                "allow_network": allow_network,
                "used_docker": False,
                "command": command,
                "command_str": _format_command(command),
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            },
        )
    return result


def _run_docker(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    allow_network: bool,
    docker_image: str,
    log_path: Path | None,
) -> CommandResult:
    started = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    work_dir = "/workspace"
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--cpus",
        "2.0",
        "--memory",
        "2g",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-v",
        f"{str(cwd)}:{work_dir}:ro",
        "-v",
        f"{str(cwd / 'autodev_work')}:{work_dir}/autodev_work:rw",
        "-v",
        f"{str(cwd / 'autodev' / 'reports')}:{work_dir}/autodev/reports:rw",
        "-v",
        f"{str(cwd / 'autodev' / 'evals' / 'results.json')}:{work_dir}/autodev/evals/results.json:rw",
        "-w",
        work_dir,
        "-e",
        "XDG_CACHE_HOME=/tmp/cache",
        "-e",
        "PYTHONPATH=/workspace",
    ]
    if not allow_network:
        docker_cmd.extend(["--network", "none"])
    docker_cmd.extend([docker_image, *command])
    proc = subprocess.run(
        docker_cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    duration = time.time() - started
    result = CommandResult(
        command=command,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        started_at=started_at,
        duration_seconds=duration,
        log_path=log_path,
        used_docker=True,
    )
    if log_path:
        _write_log(
            log_path,
            {
                "started_at": started_at,
                "duration_seconds": duration,
                "allow_network": allow_network,
                "used_docker": True,
                "docker_command": docker_cmd,
                "command": command,
                "command_str": _format_command(command),
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            },
        )
    return result


def _ensure_docker_image(
    cwd: Path,
    docker_image: str,
    dockerfile_path: str,
    auto_build: bool,
) -> None:
    inspect = subprocess.run(
        ["docker", "image", "inspect", docker_image],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if inspect.returncode == 0:
        return
    if not auto_build:
        raise RuntimeError(
            f"Docker image '{docker_image}' not found. Build it with "
            f"'docker build -t {docker_image} -f {dockerfile_path} .'."
        )
    dockerfile_abs = cwd / dockerfile_path
    if not dockerfile_abs.exists():
        raise RuntimeError(
            f"Docker image '{docker_image}' is missing and Dockerfile '{dockerfile_path}' was not found."
        )
    build = subprocess.run(
        ["docker", "build", "-t", docker_image, "-f", dockerfile_path, "."],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(
            f"Failed to build Docker image '{docker_image}'. "
            f"stderr: {build.stderr.strip() or 'n/a'}"
        )


def run_command(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    allow_network: bool = False,
    prefer_docker: bool = True,
    docker_image: str = "autodev-gates:latest",
    dockerfile_path: str = "autodev/docker/Dockerfile",
    docker_auto_build: bool = True,
    log_path: Path | None = None,
) -> CommandResult:
    _validate_command(command, allow_network=allow_network)
    has_docker = shutil.which("docker") is not None
    eval_results_path = cwd / "autodev" / "evals" / "results.json"
    eval_results_path.parent.mkdir(parents=True, exist_ok=True)
    if not eval_results_path.exists():
        eval_results_path.write_text("{}\n", encoding="utf-8")
    if prefer_docker and has_docker:
        (cwd / "autodev_work").mkdir(exist_ok=True)
        (cwd / "autodev" / "reports").mkdir(parents=True, exist_ok=True)
        try:
            _ensure_docker_image(
                cwd=cwd,
                docker_image=docker_image,
                dockerfile_path=dockerfile_path,
                auto_build=docker_auto_build,
            )
            return _run_docker(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
                allow_network=allow_network,
                docker_image=docker_image,
                log_path=log_path,
            )
        except Exception as exc:
            warning = f"[autodev] Docker run failed, falling back to restricted runner: {exc}\n"
            fallback = _run_subprocess(
                command=command,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
                allow_network=allow_network,
                log_path=log_path,
            )
            fallback_stderr = warning + fallback.stderr
            return CommandResult(
                command=fallback.command,
                exit_code=fallback.exit_code,
                stdout=fallback.stdout,
                stderr=fallback_stderr,
                started_at=fallback.started_at,
                duration_seconds=fallback.duration_seconds,
                log_path=fallback.log_path,
                used_docker=False,
            )
    return _run_subprocess(
        command=command,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        allow_network=allow_network,
        log_path=log_path,
    )
