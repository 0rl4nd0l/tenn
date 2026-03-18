from __future__ import annotations

import app.tasks.commentary_tasks as commentary_tasks


def test_extract_commentary_memo_task_uses_commentary_memo_extractor(monkeypatch):
    extractor_inits: list[dict[str, str | None]] = []
    extractor_calls: list[dict[str, str]] = []

    class StubExtractor:
        def __init__(self, *, llm_url=None, llm_model=None, memos_path=None):
            extractor_inits.append(
                {
                    "llm_url": llm_url,
                    "llm_model": llm_model,
                    "memos_path": memos_path,
                }
            )

        def extract_and_store(self, **kwargs):
            extractor_calls.append(dict(kwargs))
            return {"ok": True, "source_id": kwargs["source_id"]}

    monkeypatch.setattr(commentary_tasks, "CommentaryMemoExtractor", StubExtractor)

    payload = {
        "source_id": "youtube_transcript:test",
        "transcript_text": "A short transcript",
        "speaker": "Example Speaker",
        "source_type": "youtube_transcript",
        "published_at": "2026-03-12T00:00:00Z",
        "llm_url": "http://127.0.0.1:8001",
        "llm_model": "qwen2.5-coder-14b",
        "memos_path": "/tmp/commentary_memos.jsonl",
    }

    result = commentary_tasks.extract_commentary_memo_task.run(payload)

    assert extractor_inits == [
        {
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-coder-14b",
            "memos_path": "/tmp/commentary_memos.jsonl",
        }
    ]
    assert extractor_calls == [
        {
            "source_id": "youtube_transcript:test",
            "transcript_text": "A short transcript",
            "speaker": "Example Speaker",
            "source_type": "youtube_transcript",
            "published_at": "2026-03-12T00:00:00Z",
        }
    ]
    assert result == {"ok": True, "source_id": "youtube_transcript:test"}
