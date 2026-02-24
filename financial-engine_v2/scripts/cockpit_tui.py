#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_SERVICES = ["postgres", "redis", "qdrant", "worker", "backend"]


def _run(cmd: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            check=check,
            text=True,
            capture_output=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required executable: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Command failed ({exc.returncode}): {' '.join(cmd)}") from exc


def _log(msg: str) -> None:
    print(f"[cockpit-bootstrap] {msg}", flush=True)


def _ensure_env_file(repo_root: Path, env_file: str) -> Path:
    env_path = (repo_root / env_file).resolve()
    if env_path.exists():
        return env_path
    example_path = (repo_root / ".env.example").resolve()
    if not example_path.exists():
        raise SystemExit(f"Missing required env file: {env_path} (and no .env.example found).")
    env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
    _log(f"created {env_path.relative_to(repo_root)} from .env.example")
    return env_path


def _ensure_env_key(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    if any(line.startswith(prefix) for line in lines):
        return
    lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _log(f"set default {key}={value} in {env_path.name}")


def _ensure_uid_gid_defaults(env_path: Path) -> None:
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        _ensure_env_key(env_path, "HOST_UID", str(os.getuid()))
        _ensure_env_key(env_path, "HOST_GID", str(os.getgid()))


def _load_env_file(env_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _split_services(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_SERVICES)
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def _wait_for_postgres_ready(
    repo_root: Path,
    *,
    compose_cmd: list[str],
    postgres_user: str,
    postgres_db: str,
    timeout_seconds: int,
) -> None:
    deadline = time.time() + max(1, timeout_seconds)
    while time.time() < deadline:
        probe = subprocess.run(
            compose_cmd + ["exec", "-T", "postgres", "pg_isready", "-U", postgres_user, "-d", postgres_db],
            cwd=str(repo_root),
            check=False,
            text=True,
            capture_output=True,
        )
        if probe.returncode == 0:
            return
        time.sleep(1.0)
    raise SystemExit("Timed out waiting for postgres to become ready.")


def bootstrap_stack(
    repo_root: Path,
    *,
    env_file: str,
    services: list[str],
    build: bool,
    migrate: bool,
    wait_seconds: int,
) -> None:
    env_path = _ensure_env_file(repo_root, env_file)
    _ensure_uid_gid_defaults(env_path)
    env_map = _load_env_file(env_path)
    postgres_user = env_map.get("POSTGRES_USER", "fe")
    postgres_db = env_map.get("POSTGRES_DB", "fe")

    compose_cmd = ["docker", "compose", "--env-file", str(env_path)]

    _run(["docker", "ps"], cwd=repo_root, check=True)

    up_cmd = compose_cmd + ["up", "-d"]
    if build:
        up_cmd.append("--build")
    up_cmd.extend(services)
    _log(f"starting services: {', '.join(services)}")
    _run(up_cmd, cwd=repo_root, check=True)

    if migrate:
        if "backend" not in services:
            _log("skipping migration because backend service is not in --services")
            return
        _log("waiting for postgres health before migration")
        _wait_for_postgres_ready(
            repo_root,
            compose_cmd=compose_cmd,
            postgres_user=postgres_user,
            postgres_db=postgres_db,
            timeout_seconds=wait_seconds,
        )
        _log("running alembic upgrade head")
        _run(compose_cmd + ["exec", "-T", "backend", "alembic", "upgrade", "head"], cwd=repo_root, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Launch Cockpit TUI with optional stack bootstrap "
            "(env init + docker compose up + migration)."
        )
    )
    parser.add_argument("--no-boot", action="store_true", help="Skip bootstrap and launch cockpit only.")
    parser.add_argument(
        "--services",
        default=",".join(DEFAULT_SERVICES),
        help=f"Comma-separated compose services to start (default: {','.join(DEFAULT_SERVICES)}).",
    )
    parser.add_argument("--no-build", action="store_true", help="Skip docker compose build during bootstrap.")
    parser.add_argument("--no-migrate", action="store_true", help="Skip alembic migration after startup.")
    parser.add_argument("--env-file", default=".env", help="Compose env file path relative to repo root.")
    parser.add_argument("--wait-seconds", type=int, default=90, help="Postgres readiness timeout for migration.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args, cockpit_argv = parser.parse_known_args(argv)
    if cockpit_argv and cockpit_argv[0] == "--":
        cockpit_argv = cockpit_argv[1:]

    if not args.no_boot:
        services = _split_services(args.services)
        bootstrap_stack(
            REPO_ROOT,
            env_file=args.env_file,
            services=services,
            build=not args.no_build,
            migrate=not args.no_migrate,
            wait_seconds=args.wait_seconds,
        )

    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    launcher = str(venv_python if venv_python.exists() else Path(sys.executable))
    cmd = [launcher, "-m", "cockpit.main", *cockpit_argv]
    _run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
