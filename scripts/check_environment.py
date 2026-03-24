#!/usr/bin/env python
from __future__ import annotations

import os
import socket
import sys
import tempfile
import errno
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
BACKEND_ROOT = ENGINE_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _mask_secret(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "<empty>"
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}***{text[-2:]}"


def _print_header(title: str) -> None:
    print(f"\n[{title}]")


def _print_ok(message: str) -> None:
    print(f"OK   {message}")


def _print_warn(message: str) -> None:
    print(f"WARN {message}")


def _print_error(message: str) -> None:
    print(f"ERR  {message}")


def _source_label(name: str) -> str:
    return "env" if name in os.environ else "default"


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"


def _parse_host_port(url: str) -> tuple[str, int]:
    parsed = urlparse(str(url or "").strip())
    scheme = str(parsed.scheme or "").lower()
    if scheme in {"http", "https", "redis", "rediss"}:
        hostname = str(parsed.hostname or "").strip()
        port = parsed.port
        if port is None:
            if scheme == "https":
                port = 443
            elif scheme in {"redis", "rediss"}:
                port = 6379
            else:
                port = 80
        if hostname:
            return hostname, int(port)
    raise ValueError(f"Unsupported URL for socket probe: {url}")


def _probe_socket(label: str, url: str, *, required: bool) -> list[str]:
    messages: list[str] = []
    try:
        host, port = _parse_host_port(url)
    except ValueError as exc:
        prefix = _print_error if required else _print_warn
        prefix(f"{label}: {exc}")
        return [str(exc)] if required else []

    try:
        with socket.create_connection((host, port), timeout=1.5):
            _print_ok(f"{label} reachable at {host}:{port}")
            return []
    except OSError as exc:
        permission_blocked = isinstance(exc, PermissionError) or (
            isinstance(exc, OSError) and exc.errno in {getattr(errno, "EPERM", 1), getattr(errno, "EACCES", 13)}
        )
        if permission_blocked or "Operation not permitted" in str(exc):
            _print_warn(
                f"{label} check UNVERIFIED at {host}:{port} due restricted environment ({exc})."
            )
            return []
        prefix = _print_error if required else _print_warn
        prefix(f"{label} not reachable at {host}:{port} ({exc}).")
        if required:
            return [f"{label} unreachable"]
        return []


def _check_data_root(settings: object) -> list[str]:
    data_root = Path(settings.data_root)
    try:
        data_root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=data_root, prefix=".env-check-", delete=True):
            pass
        _print_ok(f"DATA_ROOT writable: {data_root}")
        return []
    except OSError as exc:
        _print_error(f"DATA_ROOT not writable: {data_root} ({exc}). Set DATA_ROOT to a writable directory.")
        return ["DATA_ROOT not writable"]


def main() -> int:
    errors: list[str] = []
    try:
        from app.core.config import settings  # noqa: WPS433
    except ModuleNotFoundError as exc:
        _print_error(f"Missing Python dependency: {exc}. Activate the backend venv and retry.")
        print("Suggested fix: python -m pip install -r financial-engine_v2/backend/requirements.txt")
        return 1

    _print_header("Environment")
    env_rows = [
        ("DATA_ROOT", settings.data_root),
        ("QDRANT_URL", settings.qdrant_url),
        ("OLLAMA_URL", settings.ollama_url),
        ("LLM_URL", os.getenv("LLM_URL", "http://127.0.0.1:8001")),
        ("LLAMACPP_URL", settings.llamacpp_url),
        ("LLM_API_KEY", _mask_secret(os.getenv("LLM_API_KEY", "local-openai-key"))),
        ("EMBEDDING_BATCH_SIZE", str(getattr(settings, "embedding_batch_size", 32))),
        ("ROUTER_FEEDBACK_ENABLED", _bool_text(getattr(settings, "router_feedback_enabled", True))),
        ("ANALYZER_MAX_AGE_SECONDS", str(getattr(settings, "analyzer_max_age_seconds", 600))),
        ("REDIS_URL", str(getattr(settings, "redis_url", "redis://127.0.0.1:6379/0"))),
        ("CELERY_BROKER_URL", str(getattr(settings, "celery_broker_url", "redis://127.0.0.1:6379/0"))),
    ]
    for name, value in env_rows:
        _print_ok(f"{name}={value} ({_source_label(name)})")

    _print_header("Filesystem")
    errors.extend(_check_data_root(settings))

    _print_header("Ports")
    errors.extend(
        _probe_socket(
            "primary LLM",
            os.getenv("LLM_URL", "http://127.0.0.1:8001"),
            required=bool(getattr(settings, "enable_extraction", True)),
        )
    )
    errors.extend(_probe_socket("llama.cpp", settings.llamacpp_url, required=False))
    errors.extend(
        _probe_socket(
            "Qdrant",
            settings.qdrant_url,
            required=bool(getattr(settings, "enable_qdrant", True)),
        )
    )
    errors.extend(_probe_socket("Ollama", settings.ollama_url, required=False))
    broker_url = str(getattr(settings, "celery_broker_url", "") or getattr(settings, "redis_url", ""))
    errors.extend(
        _probe_socket(
            "Redis/Celery broker",
            broker_url,
            required=str(getattr(settings, "task_mode", "celery")).strip().lower() != "sync",
        )
    )

    _print_header("Actions")
    if errors:
        _print_error("Environment check failed.")
        print("Suggested fixes:")
        print("- Copy financial-engine_v2/.env.example to financial-engine_v2/.env and adjust only the values you need.")
        print("- Start the missing services on ports 8001, 6333, 6379, and 11434 as needed.")
        print("- Re-run with: python scripts/check_environment.py")
        return 1

    _print_ok("Environment check passed.")
    print("Suggested next step: python financial-engine_v2/run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
