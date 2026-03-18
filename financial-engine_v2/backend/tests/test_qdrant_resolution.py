from __future__ import annotations

from types import SimpleNamespace
import uuid
from pathlib import Path

import pytest
import app.core.config as config
import app.main as main
import app.services.commentary_ingest as commentary_ingest


class StubMemoExtractor:
    def __init__(self, memos_path: Path) -> None:
        self.memos_path = memos_path

    def extract_and_store(self, **kwargs):
        raise AssertionError("memo extraction should be queued, not run inline")


def test_normalize_qdrant_url_rewrites_docker_hostname_for_host_runtime(monkeypatch):
    monkeypatch.setattr(config, "_running_in_docker", lambda: False)
    assert config._normalize_qdrant_url("http://qdrant:6333") == "http://127.0.0.1:6333"


def test_normalize_qdrant_url_keeps_docker_hostname_inside_container(monkeypatch):
    monkeypatch.setattr(config, "_running_in_docker", lambda: True)
    assert config._normalize_qdrant_url("http://qdrant:6333") == "http://qdrant:6333"


@pytest.mark.parametrize(
    ("runtime_in_docker", "url", "default_db", "expected"),
    [
        (False, "", 0, "redis://127.0.0.1:6379/0"),
        (False, "redis://redis:6379", 1, "redis://127.0.0.1:6379/1"),
        (True, "redis://127.0.0.1:6379/0", 0, "redis://redis:6379/0"),
    ],
)
def test_normalize_redis_url_aligns_with_runtime(monkeypatch, runtime_in_docker, url, default_db, expected):
    monkeypatch.setattr(config, "is_running_in_docker", lambda: runtime_in_docker)

    assert config._normalize_redis_url(url, default_db=default_db) == expected


def test_ingest_transcript_verifies_qdrant_before_embedding_and_upsert(monkeypatch, tmp_path, capsys):
    call_order: list[str] = []
    fake_client = object()
    queued_payloads: list[dict[str, str]] = []
    memos_path = tmp_path / "commentary_memos.jsonl"

    def fake_verify_qdrant(*, qdrant_url: str | None = None):
        assert qdrant_url == "http://qdrant:6333"
        call_order.append("verify_qdrant")
        return fake_client

    def fake_embed_batch(texts: list[str], *, llm_url: str | None, model: str | None):
        call_order.append("embed")
        return [[0.1, 0.2] for _ in texts]

    def fake_ensure_collection(client, collection: str, dim: int) -> str:
        assert client is fake_client
        assert collection == "commentary_chunks"
        assert dim == 2
        call_order.append("ensure_collection")
        return collection

    def fake_upsert_points(client, collection: str, points: list[dict]) -> None:
        assert client is fake_client
        assert collection == "commentary_chunks"
        assert len(points) == 1
        assert points[0]["payload"]["chunk_id"].endswith(":0")
        assert str(uuid.UUID(points[0]["id"])) == points[0]["id"]
        call_order.append("upsert_points")

    monkeypatch.setattr(commentary_ingest, "verify_qdrant", fake_verify_qdrant)
    monkeypatch.setattr(commentary_ingest, "ensure_collection", fake_ensure_collection)
    monkeypatch.setattr(commentary_ingest, "upsert_points", fake_upsert_points)
    monkeypatch.setattr(
        commentary_ingest,
        "extract_commentary_memo_task",
        type(
            "QueuedMemoTask",
            (),
            {
                "delay": staticmethod(
                    lambda payload: queued_payloads.append(dict(payload)) or call_order.append("queue_memo")
                )
            },
        )(),
    )

    result = commentary_ingest.ingest_transcript(
        transcript_text="A short transcript about a company update.",
        source_name="Example Channel",
        source_type="youtube_transcript",
        speaker="Example Speaker",
        published_at="2026-03-12T00:00:00Z",
        registry_path=tmp_path / "source_registry.jsonl",
        memos_path=memos_path,
        qdrant_url="http://qdrant:6333",
        embed_batch_fn=fake_embed_batch,
        memo_extractor=StubMemoExtractor(memos_path),
    )

    assert call_order == ["verify_qdrant", "embed", "ensure_collection", "upsert_points", "queue_memo"]
    assert queued_payloads == [
        {
            "source_id": result["source_id"],
            "transcript_text": "A short transcript about a company update.",
            "speaker": "Example Speaker",
            "source_type": "youtube_transcript",
            "published_at": "2026-03-12T00:00:00Z",
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-coder-14b",
            "memos_path": str(memos_path.resolve()),
        }
    ]
    assert result["ok"] is True
    assert result["chunks_indexed"] == 1
    assert result["memo"] is None
    assert result["memos_path"] == str(memos_path.resolve())
    assert "[INFO] memo extraction queued" in capsys.readouterr().out


def test_validate_qdrant_on_startup_skips_permission_error(monkeypatch, caplog):
    monkeypatch.setattr(main.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(main.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(main, "_validate_embedding_model_on_startup", lambda: None)
    monkeypatch.setattr(
        main,
        "verify_qdrant",
        lambda: (_ for _ in ()).throw(PermissionError("[Errno 1] Operation not permitted")),
    )

    with caplog.at_level("WARNING"):
        main._validate_qdrant_on_startup()

    assert "qdrant startup validation skipped" in caplog.text


def test_validate_qdrant_on_startup_keeps_non_permission_fail_fast(monkeypatch):
    monkeypatch.setattr(main.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(main.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(main, "_validate_embedding_model_on_startup", lambda: None)
    monkeypatch.setattr(
        main,
        "verify_qdrant",
        lambda: (_ for _ in ()).throw(RuntimeError("qdrant unavailable")),
    )

    with pytest.raises(RuntimeError, match="qdrant unavailable"):
        main._validate_qdrant_on_startup()


def test_validate_embedding_model_on_startup_allows_empty_collection_with_stale_marker(monkeypatch, tmp_path, caplog):
    marker = tmp_path / "runtime_embedding_model.txt"
    marker.write_text("old-model", encoding="utf-8")

    monkeypatch.setattr(main, "RUNTIME_EMBEDDING_MODEL_FILE", marker)
    monkeypatch.setattr(main.settings, "embed_model", "new-model", raising=False)
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": "old-model",
            "configured_model": "new-model",
            "document_count": 0,
            "extraction_count": 0,
            "qdrant_collection_exists": True,
            "qdrant_points_count": 0,
        },
    )

    with caplog.at_level("WARNING"):
        main._validate_embedding_model_on_startup()

    assert "empty qdrant collection" in caplog.text.lower()


def test_validate_embedding_model_on_startup_writes_marker_when_missing(monkeypatch, tmp_path):
    marker = tmp_path / "runtime_embedding_model.txt"

    monkeypatch.setattr(main, "RUNTIME_EMBEDDING_MODEL_FILE", marker)
    monkeypatch.setattr(main.settings, "embed_model", "sentence-transformers/all-MiniLM-L6-v2", raising=False)
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": None,
            "configured_model": "sentence-transformers/all-MiniLM-L6-v2",
            "document_count": 0,
            "extraction_count": 0,
            "qdrant_collection_exists": False,
            "qdrant_points_count": 0,
        },
    )

    main._validate_embedding_model_on_startup()

    assert marker.read_text(encoding="utf-8").strip() == "sentence-transformers/all-MiniLM-L6-v2"


def test_validate_embedding_model_on_startup_warns_when_db_has_rows_but_qdrant_empty(monkeypatch, caplog):
    monkeypatch.setattr(main.settings, "embed_model", "new-model", raising=False)
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": "old-model",
            "configured_model": "new-model",
            "document_count": 4,
            "extraction_count": 2,
            "qdrant_collection_exists": True,
            "qdrant_points_count": 0,
        },
    )

    with caplog.at_level("WARNING"):
        main._validate_embedding_model_on_startup()

    assert "database has embedding metadata but qdrant collection is empty" in caplog.text.lower()


def test_validate_embedding_model_on_startup_fails_only_when_db_and_vectors_exist_with_mismatch(monkeypatch):
    monkeypatch.setattr(main.settings, "embed_model", "new-model", raising=False)
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": "old-model",
            "configured_model": "new-model",
            "document_count": 4,
            "extraction_count": 2,
            "qdrant_collection_exists": True,
            "qdrant_points_count": 11,
        },
    )

    with pytest.raises(RuntimeError, match="Embedding model mismatch"):
        main._validate_embedding_model_on_startup()


def test_validate_qdrant_on_startup_allows_zero_vector_collection_and_logs_dims(monkeypatch, caplog):
    monkeypatch.setattr(main.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(main.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(main.settings, "qdrant_collection", "asx_docs", raising=False)
    monkeypatch.setattr(main, "_validate_embedding_model_on_startup", lambda client=None: None)
    monkeypatch.setattr(main, "verify_qdrant", lambda: object())
    monkeypatch.setattr(main, "_qdrant_collection_state", lambda client, collection: (True, 0))
    monkeypatch.setattr(
        main,
        "_get_embedding_state_snapshot",
        lambda client=None: {
            "stored_model": "sentence-transformers/all-MiniLM-L6-v2",
            "configured_model": "sentence-transformers/all-MiniLM-L6-v2",
            "document_count": 0,
            "extraction_count": 0,
            "qdrant_collection_exists": True,
            "qdrant_points_count": 0,
        },
    )
    monkeypatch.setattr(main, "embed_texts", lambda *args, **kwargs: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr(
        main,
        "get_qdrant_collection_vector_config",
        lambda client, collection: {"actual_dim": 384, "actual_distance": "Cosine", "points_count": 0},
    )

    with caplog.at_level("INFO"):
        main._validate_qdrant_on_startup()

    assert "expected_dim" in caplog.text
    assert "0 vectors" in caplog.text.lower()


def test_system_status_snapshot_reports_latest_ingestion_activity(monkeypatch):
    latest_document = main.datetime(2026, 3, 16, 10, 0, 0)
    latest_extraction = main.datetime(2026, 3, 17, 11, 30, 0)

    class DummyQuery:
        def __init__(self, scalar_value):
            self._scalar_value = scalar_value

        def scalar(self):
            return self._scalar_value

    class DummySession:
        def __init__(self):
            self.calls = 0

        def query(self, *args, **kwargs):
            self.calls += 1
            values = {
                1: 12,
                2: latest_document,
                3: latest_extraction,
            }
            return DummyQuery(values[self.calls])

        def close(self):
            pass

    monkeypatch.setattr(main, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(main, "_redis_connected", lambda: True)
    monkeypatch.setattr(
        main,
        "verify_qdrant",
        lambda: SimpleNamespace(
            get_collections=lambda: SimpleNamespace(
                collections=[SimpleNamespace(name="asx_docs"), SimpleNamespace(name="commentary_chunks")]
            )
        ),
    )

    payload = main._system_status_snapshot()

    assert payload["redis_connected"] is True
    assert payload["qdrant_connected"] is True
    assert payload["collections_present"] == ["asx_docs", "commentary_chunks"]
    assert payload["document_count_estimate"] == 12
    assert payload["last_ingestion_activity"] == latest_extraction.isoformat()
