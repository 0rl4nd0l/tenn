from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_env_loaded = False


def load_env(repo_root: Path | None = None) -> None:
    """Load .env from the financial-engine_v2 root (same file the backend uses).

    Shell env vars take precedence — dotenv only fills in missing keys.
    Safe to call multiple times; only loads once.
    """
    global _env_loaded  # noqa: PLW0603
    if _env_loaded:
        return
    _env_loaded = True

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        # Fallback: parse KEY=VALUE lines manually (no interpolation).
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_LLAMACPP_URL = "http://localhost:8001"
DEFAULT_LLAMACPP_MODEL = "qwen2.5-coder-14b"


DEFAULT_CONFIG = {
    "llm": {
        "provider": "llamacpp",
        "ollama_url": "",
        "llamacpp_url": DEFAULT_LLAMACPP_URL,
        "llamacpp_api_key": "local-openai-key",
        "model": DEFAULT_LLAMACPP_MODEL,
        "router_mode_opt_in": False,
        "timeout_seconds": 120,
    },
    "paths": {
        "allow_roots": [str(Path.home())],
        "default_workspace": str(Path.cwd()),
    },
    "memory": {
        "mode": "global_persisted",
        "state_db": str(Path.home() / ".financial_engine_cockpit" / "state.db"),
    },
    "actions": {
        "confirm_required": True,
    },
    "backend": {
        "api_base_url": DEFAULT_BACKEND_URL,
    },
    "web": {
        "enabled_default": False,
    },
    "exports": {
        "dir": "reports/analysis",
    },
    "reports": {
        "dir": "reports",
    },
}

VALID_LLM_PROVIDERS = {"llamacpp", "ollama"}


@dataclass
class RuntimeFlags:
    config_path: str
    profile: str
    read_only: bool
    no_web: bool


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(config_path: str | None) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if not config_path:
        return cfg

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("cockpit config must be a mapping")
    return _deep_merge(cfg, payload)


def apply_runtime_flags(config: dict[str, Any], flags: RuntimeFlags) -> dict[str, Any]:
    cfg = dict(config)
    cfg["runtime"] = {
        "profile": flags.profile,
        "read_only": flags.read_only,
        "no_web": flags.no_web,
    }
    if flags.no_web:
        cfg.setdefault("web", {})
        cfg["web"]["enabled_default"] = False

    # Environment override keeps Cockpit aligned with existing stack.
    cfg.setdefault("llm", {})
    provider = str(os.getenv("COCKPIT_LLM_PROVIDER", cfg["llm"].get("provider", "llamacpp")) or "").strip().lower()
    if provider not in VALID_LLM_PROVIDERS:
        raise ValueError(f"Unsupported Cockpit LLM provider: {provider}")
    cfg["llm"]["provider"] = provider
    cfg["llm"]["ollama_url"] = os.getenv(
        "COCKPIT_OLLAMA_URL",
        os.getenv("OLLAMA_URL", cfg["llm"].get("ollama_url", DEFAULT_OLLAMA_URL)),
    )
    cfg["llm"]["llamacpp_url"] = os.getenv(
        "COCKPIT_LLAMACPP_URL",
        os.getenv("LLAMACPP_URL", cfg["llm"].get("llamacpp_url", DEFAULT_LLAMACPP_URL)),
    )
    cfg["llm"]["model"] = os.getenv(
        "COCKPIT_LLM_MODEL",
        os.getenv("EXTRACT_MODEL", cfg["llm"].get("model", DEFAULT_LLAMACPP_MODEL)),
    )
    cfg["llm"]["llamacpp_api_key"] = os.getenv("LLAMACPP_API_KEY") or os.getenv("LLM_API_KEY") or cfg["llm"].get("llamacpp_api_key", "")
    router_mode_value = os.getenv(
        "COCKPIT_ROUTER_MODE",
        str(cfg["llm"].get("router_mode_opt_in", False)),
    )
    cfg["llm"]["router_mode_opt_in"] = str(router_mode_value).strip().lower() in {"1", "true", "yes", "on"}
    cfg.setdefault("backend", {})
    cfg["backend"]["api_base_url"] = os.getenv(
        "COCKPIT_BACKEND_URL",
        cfg["backend"].get("api_base_url", DEFAULT_BACKEND_URL),
    )
    cfg.setdefault("db", {})
    cfg["db"]["database_url"] = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")
    return cfg
