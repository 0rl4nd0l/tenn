from __future__ import annotations

import app.tasks.news_tasks as news_tasks


def test_extract_news_memo_task_uses_news_memo_extractor(monkeypatch):
    extractor_inits: list[dict[str, str | None]] = []
    extractor_calls: list[dict[str, str]] = []

    class StubExtractor:
        def __init__(
            self, *, llm_url=None, llm_model=None, memos_path=None, max_article_chars=None
        ):
            extractor_inits.append(
                {
                    "llm_url": llm_url,
                    "llm_model": llm_model,
                    "memos_path": memos_path,
                    "max_article_chars": max_article_chars,
                }
            )

        def extract_and_store(self, **kwargs):
            extractor_calls.append(dict(kwargs))
            return {"ok": True, "source_id": kwargs["source_id"]}

    monkeypatch.setattr(news_tasks, "NewsMemoExtractor", StubExtractor)

    payload = {
        "source_id": "news:12345",
        "article_text": "BHP announces record iron ore production.",
        "provider": "newspaper4k",
        "published_at": "2026-03-30T10:00:00Z",
        "llm_url": "http://127.0.0.1:8001",
        "llm_model": "qwen2.5-14b-instruct",
        "memos_path": "/tmp/news_memos.jsonl",
        "max_article_chars": 5000,
    }

    result = news_tasks.extract_news_memo_task.run(payload)

    assert extractor_inits == [
        {
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-14b-instruct",
            "memos_path": "/tmp/news_memos.jsonl",
            "max_article_chars": 5000,
        }
    ]
    assert extractor_calls == [
        {
            "source_id": "news:12345",
            "article_text": "BHP announces record iron ore production.",
            "provider": "newspaper4k",
            "published_at": "2026-03-30T10:00:00Z",
        }
    ]
    assert result == {"ok": True, "source_id": "news:12345"}
