from __future__ import annotations

import os
from typing import Any, Mapping
from urllib.parse import urlparse


def database_url_class(database_url: str) -> str:
    text = str(database_url or "").strip()
    if not text:
        return "missing"
    lowered = text.lower()
    if lowered.startswith("sqlite:"):
        return "sqlite"

    scheme = str(urlparse(text).scheme or "").strip().lower()
    if scheme.startswith("postgresql"):
        return "postgresql"
    return scheme or "unknown"


def _bool_setting(settings_obj: Any, name: str, default: bool) -> bool:
    return bool(getattr(settings_obj, name, default))


def _str_setting(settings_obj: Any, name: str, default: str = "") -> str:
    return str(getattr(settings_obj, name, default) or "").strip()


def _entrypoint_label(env: Mapping[str, str] | None = None) -> str:
    env_values = env if env is not None else os.environ
    marker = str(env_values.get("TENN_BACKEND_ENTRYPOINT") or "").strip()
    return marker or "direct_or_unknown"


def build_runtime_startup_summary(
    settings_obj: Any,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    celery_broker_url = _str_setting(settings_obj, "celery_broker_url")
    qdrant_url = _str_setting(settings_obj, "qdrant_url")
    return {
        "entrypoint": _entrypoint_label(env),
        "task_mode": _str_setting(settings_obj, "task_mode", "unknown") or "unknown",
        "database_url_class": database_url_class(
            _str_setting(settings_obj, "database_url")
        ),
        "auto_create_tables": _bool_setting(settings_obj, "auto_create_tables", False),
        "enable_embeddings": _bool_setting(settings_obj, "enable_embeddings", True),
        "enable_qdrant": _bool_setting(settings_obj, "enable_qdrant", True),
        "enable_extraction": _bool_setting(settings_obj, "enable_extraction", True),
        "qdrant_configured": bool(qdrant_url),
        "celery_broker_configured": bool(celery_broker_url),
    }


def should_warn_direct_startup(summary: Mapping[str, Any]) -> bool:
    if str(summary.get("entrypoint") or "") == "run_local_backend":
        return False
    return any(
        [
            str(summary.get("task_mode") or "") != "sync",
            str(summary.get("database_url_class") or "") != "sqlite",
            bool(summary.get("enable_embeddings")),
            bool(summary.get("enable_qdrant")),
            bool(summary.get("enable_extraction")),
        ]
    )
