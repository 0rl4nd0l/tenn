from __future__ import annotations

import pytest

from scripts import load_news_to_qdrant as loader



def test_resolve_ollama_url_prefers_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://env.local:11434")
    url, source = loader.resolve_ollama_url(
        cli_url="http://cli.local:11434",
        settings_url="http://settings.local:11434",
    )
    assert url == "http://cli.local:11434"
    assert source == loader.OLLAMA_URL_SOURCE_CLI



def test_resolve_ollama_url_uses_env_when_cli_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://env.local:11434")
    url, source = loader.resolve_ollama_url(
        cli_url=None,
        settings_url="http://settings.local:11434",
    )
    assert url == "http://env.local:11434"
    assert source == loader.OLLAMA_URL_SOURCE_ENV



def test_resolve_ollama_url_defaults_when_settings_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    url, source = loader.resolve_ollama_url(
        cli_url=None,
        settings_url="   ",
    )
    assert url == loader.DEFAULT_OLLAMA_URL
    assert source == loader.OLLAMA_URL_SOURCE_DEFAULT



def test_resolve_ollama_url_rejects_invalid_url() -> None:
    with pytest.raises(ValueError, match="Invalid --ollama-url"):
        loader.resolve_ollama_url(
            cli_url="ftp://bad.example",
            settings_url="http://settings.local:11434",
        )



def test_sync_news_to_qdrant_records_ollama_url_source_in_stats(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://env.local:11434")

    monkeypatch.setattr(
        loader,
        "build_news_projection_target",
        lambda db_path, *, since_hours=None: {
            "articles": [],
            "points": [],
            "report": {},
        },
    )

    stats = loader.sync_news_to_qdrant(
        db_path=str(tmp_path / "news.sqlite"),
        dispatch_memos=False,
        embed_model="nomic-embed-text",
        embed_texts_fn=lambda texts: [[0.0]],
    )

    assert stats["ollama_url"] == "http://env.local:11434"
    assert stats["ollama_url_source"] == loader.OLLAMA_URL_SOURCE_ENV
    assert "articles" in stats
