from __future__ import annotations

from pathlib import Path

from cockpit.core.config import RuntimeFlags, apply_runtime_flags


def test_apply_runtime_flags_respects_router_mode_opt_in_env(
    monkeypatch, tmp_path: Path
):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "cockpit_llm.yaml").write_text(
        "allow_env_override: true\n"
        "hybrid_router_policy: local_preferred\n"
        "llm_profile_label: ops\n"
        "tool_debug: failures\n"
        "llm:\n"
        "  provider: llamacpp\n"
        "  model: qwen2.5-coder-14b\n"
        "  router_mode_opt_in: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("COCKPIT_ROUTER_MODE", "1")

    cfg = apply_runtime_flags(
        {"llm": {"provider": "llamacpp", "router_mode_opt_in": False}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["llm"]["router_mode_opt_in"] is True


def test_apply_runtime_flags_prefers_backend_api_url_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("COCKPIT_BACKEND_URL", "http://localhost:8000")
    monkeypatch.setenv("COCKPIT_BACKEND_API_URL", "http://127.0.0.1:9000")

    cfg = apply_runtime_flags(
        {"backend": {"api_base_url": "http://fallback:8000"}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["backend"]["api_base_url"] == "http://127.0.0.1:9000"


def test_apply_runtime_flags_uses_backend_url_when_api_url_unset(
    monkeypatch, tmp_path: Path
):
    monkeypatch.delenv("COCKPIT_BACKEND_API_URL", raising=False)
    monkeypatch.setenv("COCKPIT_BACKEND_URL", "http://localhost:8100")

    cfg = apply_runtime_flags(
        {"backend": {"api_base_url": "http://fallback:8000"}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["backend"]["api_base_url"] == "http://localhost:8100"


def test_apply_runtime_flags_prefers_cockpit_state_db_env(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("COCKPIT_STATE_DB", "/shared/cockpit/state.db")

    cfg = apply_runtime_flags(
        {"memory": {"state_db": str(tmp_path / "fallback-state.db")}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["memory"]["state_db"] == "/shared/cockpit/state.db"


def test_apply_runtime_flags_prefers_cockpit_news_db_path_env(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("COCKPIT_NEWS_DB_PATH", "/cockpit/news.sqlite")
    monkeypatch.setenv("TENN_NEWS_CONTEXT_DB", "/shared/news.sqlite")
    monkeypatch.setenv("TENN_NEWS_ARTIFACT_ROOT", "/shared/qual_context")

    cfg = apply_runtime_flags(
        {"rag": {"news_context": {"db_path": "reports/qual_context/news.sqlite"}}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["rag"]["news_context"]["db_path"] == "/cockpit/news.sqlite"


def test_apply_runtime_flags_uses_tenn_news_context_db_env(
    monkeypatch, tmp_path: Path
):
    monkeypatch.delenv("COCKPIT_NEWS_DB_PATH", raising=False)
    monkeypatch.setenv("TENN_NEWS_CONTEXT_DB", "/shared/news.sqlite")
    monkeypatch.setenv("TENN_NEWS_ARTIFACT_ROOT", "/shared/qual_context")

    cfg = apply_runtime_flags(
        {"rag": {"news_context": {"db_path": "reports/qual_context/news.sqlite"}}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["rag"]["news_context"]["db_path"] == "/shared/news.sqlite"


def test_apply_runtime_flags_derives_news_db_from_artifact_root_env(
    monkeypatch, tmp_path: Path
):
    artifact_root = tmp_path / "qual_context"
    monkeypatch.delenv("COCKPIT_NEWS_DB_PATH", raising=False)
    monkeypatch.delenv("TENN_NEWS_CONTEXT_DB", raising=False)
    monkeypatch.setenv("TENN_NEWS_ARTIFACT_ROOT", str(artifact_root))

    cfg = apply_runtime_flags(
        {"rag": {"news_context": {"db_path": "reports/qual_context/news.sqlite"}}},
        RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="default",
            read_only=False,
            no_web=False,
            repo_root=tmp_path,
        ),
    )

    assert cfg["rag"]["news_context"]["db_path"] == str(
        artifact_root / "news.sqlite"
    )
