from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = {
    "llm": {
        "provider": "ollama",
        "ollama_url": "http://localhost:11434",
        "llamacpp_url": "http://localhost:8001",
        "model": "llama3:latest",
        "timeout_seconds": 300,
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
    cfg["llm"]["ollama_url"] = os.getenv("OLLAMA_URL", cfg["llm"].get("ollama_url", "http://localhost:11434"))
    cfg["llm"]["llamacpp_url"] = os.getenv("LLAMACPP_URL", cfg["llm"].get("llamacpp_url", "http://localhost:8001"))
    cfg["llm"]["model"] = os.getenv("EXTRACT_MODEL", cfg["llm"].get("model", "llama3.1:8b"))
    cfg.setdefault("db", {})
    cfg["db"]["database_url"] = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")
    return cfg
