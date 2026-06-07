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
        "model": "llama3:latest",
        "timeout_seconds": 300,
    },
    "paths": {
        "allow_roots": ["."],
        "default_workspace": str(Path.cwd()),
    },
    "memory": {
        "mode": "global_persisted",
        "state_db": str(Path.home() / ".financial_engine_cockpit" / "state.db"),
    },
    "actions": {
        "confirm_required": True,
    },
    "db": {
        "diagnostic_query_enabled": False,
    },
    "backend": {
        "api_base_url": "http://localhost:8000",
        "auto_start": True,
        "start_command": ["./scripts/run_local_backend.sh"],
        "startup_timeout_seconds": 25,
    },
    "web": {
        "enabled_default": False,
    },
    "exports": {
        "dir": "reports/analysis",
        "chat_window_messages": 40,
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

    # Cockpit-specific env vars override config, then fall back to shared stack vars.
    cfg.setdefault("llm", {})
    cfg["llm"]["ollama_url"] = os.getenv(
        "COCKPIT_OLLAMA_URL",
        os.getenv("OLLAMA_URL", cfg["llm"].get("ollama_url", "http://localhost:11434")),
    )
    cockpit_model = (os.getenv("COCKPIT_LLM_MODEL") or "").strip()
    if cockpit_model:
        cfg["llm"]["model"] = cockpit_model
    else:
        configured_model = str(cfg["llm"].get("model") or "").strip()
        if configured_model:
            cfg["llm"]["model"] = configured_model
        else:
            cfg["llm"]["model"] = os.getenv("EXTRACT_MODEL", "llama3.1:8b")
    cfg.setdefault("db", {})
    cfg["db"]["database_url"] = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")
    cfg.setdefault("backend", {})
    cfg["backend"]["api_base_url"] = os.getenv(
        "COCKPIT_BACKEND_API_URL",
        cfg["backend"].get("api_base_url", "http://localhost:8000"),
    )

    rag_cfg = cfg.setdefault("rag", {})
    if not isinstance(rag_cfg, dict):
        rag_cfg = {}
        cfg["rag"] = rag_cfg
    qc_cfg = rag_cfg.setdefault("qualitative_context", {})
    if not isinstance(qc_cfg, dict):
        qc_cfg = {}
        rag_cfg["qualitative_context"] = qc_cfg
    news_cfg = rag_cfg.setdefault("news_context", {})
    if not isinstance(news_cfg, dict):
        news_cfg = {}
        rag_cfg["news_context"] = news_cfg

    company_db_override = (os.getenv("COCKPIT_COMPANY_DB_PATH") or "").strip()
    if not company_db_override:
        company_db_override = (os.getenv("TENN_COMPANY_CONTEXT_DB") or "").strip()
    if not company_db_override:
        qual_artifact_root = (os.getenv("TENN_QUAL_CONTEXT_ARTIFACT_ROOT") or "").strip()
        if qual_artifact_root:
            company_db_override = str(Path(qual_artifact_root).expanduser() / "company.sqlite")
    if company_db_override:
        qc_cfg["db_path"] = company_db_override

    news_db_override = (os.getenv("COCKPIT_NEWS_DB_PATH") or "").strip()
    if not news_db_override:
        news_db_override = (os.getenv("TENN_NEWS_CONTEXT_DB") or "").strip()
    if not news_db_override:
        news_artifact_root = (os.getenv("TENN_NEWS_ARTIFACT_ROOT") or "").strip()
        if news_artifact_root:
            news_db_override = str(Path(news_artifact_root).expanduser() / "news.sqlite")
    if news_db_override:
        news_cfg["db_path"] = news_db_override

    news_corpus_override = (os.getenv("COCKPIT_NEWS_CORPUS_FILTER") or "").strip()
    if news_corpus_override:
        news_cfg["corpus_filter"] = news_corpus_override

    ticker_mode_override = (os.getenv("COCKPIT_NEWS_TICKER_MATCH_MODE") or "").strip().lower()
    if ticker_mode_override:
        if ticker_mode_override not in {"soft", "strict"}:
            raise ValueError(
                "Invalid COCKPIT_NEWS_TICKER_MATCH_MODE value "
                f"'{ticker_mode_override}'. Expected 'soft' or 'strict'."
            )
        news_cfg["ticker_match_mode"] = ticker_mode_override
    return cfg
