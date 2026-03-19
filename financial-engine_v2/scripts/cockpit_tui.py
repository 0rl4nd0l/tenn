#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import venv
from pathlib import Path
from typing import Any

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


def _ensure_cockpit_venv(repo_root: Path) -> Path:
    """Ensure a venv exists with Cockpit's Python deps."""
    venv_dir = (repo_root / ".venv").resolve()
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.exists():
        _log(f"creating python venv: {venv_dir.relative_to(repo_root)}")
        venv.create(str(venv_dir), with_pip=True, clear=False)
    pip_bin = venv_dir / "bin" / "pip"
    _run(
        [
            str(pip_bin),
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            # Cockpit runtime deps (minimal set; backend deps are handled via Docker images).
            "textual>=0.80.0",
            "httpx>=0.27.0",
            "pyyaml>=6.0",
            "sqlalchemy>=2.0.0",
        ],
        cwd=repo_root,
        check=True,
    )
    return python_bin


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


def _argv_has_flag(argv: list[str], flag: str) -> bool:
    prefix = f"{flag}="
    return any(arg == flag or arg.startswith(prefix) for arg in argv)


def _apply_cockpit_logging_defaults(cockpit_argv: list[str]) -> None:
    """Enable verbose cockpit logging by default unless user already set overrides."""
    if "COCKPIT_VERBOSE_LOGGING" not in os.environ and not _argv_has_flag(cockpit_argv, "--verbose"):
        os.environ["COCKPIT_VERBOSE_LOGGING"] = "1"
        _log("defaulted COCKPIT_VERBOSE_LOGGING=1")
    if "COCKPIT_LOG_LEVEL" not in os.environ and not _argv_has_flag(cockpit_argv, "--log-level"):
        os.environ["COCKPIT_LOG_LEVEL"] = "DEBUG"
        _log("defaulted COCKPIT_LOG_LEVEL=DEBUG")


def _apply_full_functionality_defaults(cockpit_argv: list[str]) -> None:
    """Set safe full-feature defaults unless the operator already overrides them."""
    defaults = {
        # Keep Cockpit aligned with local backend entrypoint by default.
        "COCKPIT_BACKEND_API_URL": "http://localhost:8000",
        # Keep news context routing deterministic and permissive by default.
        "COCKPIT_NEWS_CORPUS_FILTER": "news",
        "COCKPIT_NEWS_TICKER_MATCH_MODE": "soft",
        # Prefer full operational + web-augmented path by default.
        "COCKPIT_FORCE_LOCAL_OPERATIONAL_BRIEF": "0",
    }
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
            _log(f"defaulted {key}={value}")

    # If the caller already set explicit runtime constraints, keep them.
    if "COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS" not in os.environ:
        os.environ["COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS"] = "60"
        _log("defaulted COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS=60")
    if "COCKPIT_MAX_USER_MESSAGE_CHARS" not in os.environ:
        os.environ["COCKPIT_MAX_USER_MESSAGE_CHARS"] = "8000"
        _log("defaulted COCKPIT_MAX_USER_MESSAGE_CHARS=8000")

    # Mirror chart launcher behavior unless caller passed through an explicit npx path.
    if "COCKPIT_NPX_PATH" not in os.environ and not _argv_has_flag(cockpit_argv, "--npx-path"):
        os.environ["COCKPIT_NPX_PATH"] = "npx"
        _log("defaulted COCKPIT_NPX_PATH=npx")


def _emit_startup_header(cockpit_argv: list[str]) -> None:
    """Print an operator-friendly startup header with effective defaults."""
    _log("=== cockpit_tui full functionality startup ===")
    _log(f"launch args: {' '.join(cockpit_argv) if cockpit_argv else '(none)'}")
    for key in (
        "COCKPIT_BACKEND_API_URL",
        "COCKPIT_OLLAMA_URL",
        "COCKPIT_NEWS_CORPUS_FILTER",
        "COCKPIT_NEWS_TICKER_MATCH_MODE",
        "COCKPIT_FORCE_LOCAL_OPERATIONAL_BRIEF",
        "COCKPIT_VERBOSE_LOGGING",
        "COCKPIT_LOG_LEVEL",
        "COCKPIT_LOG_TO_STDERR",
    ):
        value = str(os.environ.get(key, "")).strip()
        if value:
            _log(f"{key}={value}")
    _log("============================================")


def _resolve_effective_config_path(
    repo_root: Path,
    cockpit_argv: list[str],
    fallback_config: str,
) -> Path | None:
    """Resolve effective --config from argv (or fallback)."""
    config_value = ""
    for idx, arg in enumerate(cockpit_argv):
        if arg == "--config" and idx + 1 < len(cockpit_argv):
            config_value = str(cockpit_argv[idx + 1] or "").strip()
            break
        if arg.startswith("--config="):
            config_value = str(arg.split("=", 1)[1] or "").strip()
            break
    if not config_value:
        config_value = str(fallback_config or "").strip()
    if not config_value:
        return None
    p = Path(config_value).expanduser()
    if not p.is_absolute():
        p = (repo_root / p).resolve()
    return p


def _config_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _load_startup_feature_flags(config_path: Path | None) -> dict[str, Any]:
    """Best-effort runtime-ish flag summary from selected cockpit config + env overrides."""
    flags: dict[str, Any] = {
        "config_exists": False,
        "rag_enabled": False,
        "qualitative_context_enabled": False,
        "news_context_enabled": False,
    }
    if config_path is None or not config_path.exists():
        return flags
    flags["config_exists"] = True

    try:
        # Lazy import to keep startup resilient if YAML deps are unavailable.
        import yaml  # type: ignore
    except Exception:
        return flags

    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return flags
    if not isinstance(payload, dict):
        return flags

    rag_cfg = payload.get("rag")
    rag_cfg = rag_cfg if isinstance(rag_cfg, dict) else {}
    qual_cfg = rag_cfg.get("qualitative_context")
    qual_cfg = qual_cfg if isinstance(qual_cfg, dict) else {}
    news_cfg = rag_cfg.get("news_context")
    news_cfg = news_cfg if isinstance(news_cfg, dict) else {}

    flags["rag_enabled"] = _config_bool(rag_cfg.get("enabled"), default=False)
    flags["qualitative_context_enabled"] = _config_bool(qual_cfg.get("enabled"), default=False)
    flags["news_context_enabled"] = _config_bool(news_cfg.get("enabled"), default=False)

    # Environment can override select settings at runtime.
    news_corpus_override = str(os.getenv("COCKPIT_NEWS_CORPUS_FILTER") or "").strip()
    if news_corpus_override:
        flags["news_context_enabled"] = True

    return flags


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
    parser.add_argument(
        "--cockpit-config",
        default="config/cockpit.local.yaml",
        help=(
            "Default cockpit config path when no --config is passed through to cockpit.main. "
            "Use empty string to keep cockpit.main defaults."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args, cockpit_argv = parser.parse_known_args(argv)
    if cockpit_argv and cockpit_argv[0] == "--":
        cockpit_argv = cockpit_argv[1:]

    has_explicit_config = any(arg == "--config" for arg in cockpit_argv)
    default_cockpit_config = str(args.cockpit_config or "").strip()
    if not has_explicit_config and default_cockpit_config:
        config_path = (REPO_ROOT / default_cockpit_config).resolve()
        if config_path.exists():
            cockpit_argv = ["--config", default_cockpit_config, *cockpit_argv]
            _log(f"using default cockpit config: {default_cockpit_config}")
        else:
            _log(
                f"default cockpit config not found ({default_cockpit_config}); "
                "falling back to cockpit.main defaults"
            )

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

    _apply_cockpit_logging_defaults(cockpit_argv)
    _apply_full_functionality_defaults(cockpit_argv)

    # When running on the host, .env often has OLLAMA_URL=http://host.docker.internal:11434
    # for containers. That hostname does not resolve from the host, so force Cockpit to use
    # localhost unless the user explicitly set COCKPIT_OLLAMA_URL.
    if "COCKPIT_OLLAMA_URL" not in os.environ:
        ollama_from_env = (os.environ.get("OLLAMA_URL") or "").strip()
        if "host.docker.internal" in ollama_from_env.lower():
            os.environ["COCKPIT_OLLAMA_URL"] = "http://localhost:11434"
            _log("defaulted COCKPIT_OLLAMA_URL=http://localhost:11434")

    _emit_startup_header(cockpit_argv)
    effective_config_path = _resolve_effective_config_path(
        REPO_ROOT,
        cockpit_argv,
        default_cockpit_config,
    )
    feature_flags = _load_startup_feature_flags(effective_config_path)
    if effective_config_path is not None:
        _log(f"effective_config_path={effective_config_path}")
    _log(
        "effective_flags: "
        f"rag_enabled={feature_flags.get('rag_enabled')} "
        f"qualitative_context_enabled={feature_flags.get('qualitative_context_enabled')} "
        f"news_context_enabled={feature_flags.get('news_context_enabled')} "
        f"config_exists={feature_flags.get('config_exists')}"
    )

    launcher = str(_ensure_cockpit_venv(REPO_ROOT))
    cmd = [launcher, "-m", "cockpit.main", *cockpit_argv]
    _run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
