from __future__ import annotations

from types import SimpleNamespace

from app.core.startup_diagnostics import (
    build_runtime_startup_summary,
    database_url_class,
    should_warn_direct_startup,
)


def _settings(**overrides: object) -> SimpleNamespace:
    values = {
        "task_mode": "celery",
        "database_url": "postgresql+psycopg://user:pass@127.0.0.1:5432/tenn",
        "auto_create_tables": False,
        "enable_embeddings": True,
        "enable_qdrant": True,
        "enable_extraction": True,
        "qdrant_url": "http://127.0.0.1:6333",
        "celery_broker_url": "redis://127.0.0.1:6379/0",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_database_url_class_reports_scheme_without_credentials() -> None:
    assert database_url_class("sqlite:////tmp/tenn.db") == "sqlite"
    assert (
        database_url_class("postgresql+psycopg://user:secret@db:5432/tenn")
        == "postgresql"
    )
    assert database_url_class("") == "missing"


def test_direct_or_unknown_production_like_startup_warns() -> None:
    summary = build_runtime_startup_summary(
        _settings(),
        env={},
    )

    assert summary["entrypoint"] == "direct_or_unknown"
    assert summary["database_url_class"] == "postgresql"
    assert summary["task_mode"] == "celery"
    assert should_warn_direct_startup(summary) is True


def test_canonical_local_backend_marker_suppresses_direct_startup_warning() -> None:
    summary = build_runtime_startup_summary(
        _settings(
            task_mode="sync",
            database_url="sqlite:////tmp/financial-engine_v2-fe_local_runtime.db",
            auto_create_tables=True,
            enable_embeddings=False,
            enable_qdrant=False,
            enable_extraction=False,
        ),
        env={"TENN_BACKEND_ENTRYPOINT": "run_local_backend"},
    )

    assert summary["entrypoint"] == "run_local_backend"
    assert summary["database_url_class"] == "sqlite"
    assert should_warn_direct_startup(summary) is False
