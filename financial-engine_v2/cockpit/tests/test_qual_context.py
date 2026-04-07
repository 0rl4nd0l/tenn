from __future__ import annotations

from pathlib import Path

from cockpit.integrations.qual_context import QualContextReader


class _FakeBackendClient:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self._should_fail = should_fail

    def rag_query(self, **kwargs):
        self.calls.append(dict(kwargs))
        if self._should_fail:
            raise RuntimeError("backend exploded")
        return {
            "results": [
                {
                    "score": 0.91,
                    "payload": {"title": "Example hit", "corpus": "news"},
                }
            ]
        }


def test_query_forwards_explicit_date_filters():
    backend = _FakeBackendClient()
    reader = QualContextReader(repo_root=Path("."), backend_api_client=backend)

    result = reader.query(
        query="latest company update",
        ticker_filter="abc",
        date_from="2026-01-01",
        date_to="2026-01-31",
    )

    assert result["ok"] is True
    assert backend.calls[0]["ticker"] == "ABC"
    assert backend.calls[0]["date_from"] == "2026-01-01"
    assert backend.calls[0]["date_to"] == "2026-01-31"


def test_query_normalizes_blank_date_filters_to_none():
    backend = _FakeBackendClient()
    reader = QualContextReader(repo_root=Path("."), backend_api_client=backend)

    result = reader.query(
        query="latest company update",
        date_from="   ",
        date_to="",
    )

    assert result["ok"] is True
    assert backend.calls[0]["date_from"] is None
    assert backend.calls[0]["date_to"] is None


def test_query_returns_backend_error_when_backend_call_fails():
    backend = _FakeBackendClient(should_fail=True)
    reader = QualContextReader(repo_root=Path("."), backend_api_client=backend)

    result = reader.query(query="latest company update", date_from="2026-01-01")

    assert result["ok"] is False
    assert result["hits"] == []
    assert "backend exploded" in result["error"]
