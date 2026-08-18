from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as main_app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main_app.settings, "local_api_key", "", raising=False)
    return TestClient(main_app.app)


def test_rag_query_accepts_asx_docs_source(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call: dict[str, Any] = {}

    def fake_query_rag(**kwargs: Any) -> dict[str, Any]:
        call.update(kwargs)
        return {"source": "asx_docs", "results": []}

    monkeypatch.setattr(main_app, "query_rag", fake_query_rag)

    response = client.post(
        "/rag/query",
        json={
            "query": "capital management",
            "source": "asx_docs",
            "ticker": "BHP",
            "top_k": 3,
            "debug": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"source": "asx_docs", "results": []}
    assert call == {
        "query": "capital management",
        "ticker": "BHP",
        "top_k": 3,
        "debug": True,
    }


def test_rag_query_accepts_news_source(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call: dict[str, Any] = {}

    def fake_query_news_chunks(**kwargs: Any) -> dict[str, Any]:
        call.update(kwargs)
        return {"source": "news", "results": []}

    monkeypatch.setattr(main_app, "query_news_chunks", fake_query_news_chunks)

    response = client.post(
        "/rag/query",
        json={
            "query": "iron ore",
            "source": "news",
            "ticker": "BHP",
            "provider": "a2m",
            "language": "fr",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "top_k": 4,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"source": "news", "results": []}
    assert call == {
        "query": "iron ore",
        "ticker": "BHP",
        "provider": "a2m",
        "language": "fr",
        "date_from": "2026-01-01",
        "date_to": "2026-01-31",
        "top_k": 4,
    }


@pytest.mark.parametrize("source", ["commentary", "hybrid"])
def test_rag_query_rejects_unsupported_sources_before_retrieval(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    def retrieval_must_not_run(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("unsupported /rag/query sources must not run retrieval")

    monkeypatch.setattr(main_app, "query_rag", retrieval_must_not_run)
    monkeypatch.setattr(main_app, "query_news_chunks", retrieval_must_not_run)

    response = client.post(
        "/rag/query",
        json={"query": "market commentary", "source": source},
    )

    assert response.status_code == 422
    assert "source" in str(response.json())
