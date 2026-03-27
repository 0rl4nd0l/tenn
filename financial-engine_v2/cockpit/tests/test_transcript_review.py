"""Tests for the transcript staging and review gate."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def staging_dir(tmp_path):
    """Override STAGED_CHUNKS_DIR to use a temp directory."""
    staged = tmp_path / "staged_chunks"
    staged.mkdir()
    index_path = staged / "index.json"
    with patch("app.services.commentary_ingest.STAGED_CHUNKS_DIR", staged), \
         patch("app.services.commentary_ingest.STAGED_CHUNKS_INDEX", index_path), \
         patch("cockpit.integrations.transcript_review.STAGED_CHUNKS_DIR", staged), \
         patch("cockpit.integrations.transcript_review.STAGED_CHUNKS_INDEX", index_path):
        yield staged, index_path


def _make_ingest_kwargs(**overrides):
    defaults = {
        "transcript_text": "Hello this is a test transcript about financial markets.",
        "source_name": "Test Video",
        "source_type": "youtube_transcript",
        "speaker": "Test Speaker",
        "published_at": "2026-03-27T00:00:00Z",
        "topic_tags": ["test"],
    }
    defaults.update(overrides)
    return defaults


class TestStagingGate:
    def test_stage_hot_source_writes_to_disk(self, staging_dir, tmp_path):
        staged, index_path = staging_dir
        registry_path = tmp_path / "registry.jsonl"

        mock_qdrant = MagicMock()
        mock_embed = MagicMock(return_value=[[0.1] * 768])

        from app.services.commentary_ingest import ingest_transcript

        result = ingest_transcript(
            **_make_ingest_kwargs(),
            qdrant_client=mock_qdrant,
            registry_path=str(registry_path),
            embed_batch_fn=mock_embed,
        )

        assert result["ok"] is True
        assert result["staged"] is True
        assert result["chunks_indexed"] == 0
        assert result["chunks_staged"] > 0

        # Qdrant upsert should NOT have been called
        mock_qdrant.upsert.assert_not_called()

        # Staged file should exist
        index = json.loads(index_path.read_text())
        assert len(index) == 1
        source_id = result["source_id"]
        assert source_id in index
        staged_file = Path(index[source_id]["path"])
        assert staged_file.exists()

    def test_dedup_skips_existing_source_id(self, staging_dir, tmp_path):
        staged, index_path = staging_dir
        registry_path = tmp_path / "registry.jsonl"

        mock_qdrant = MagicMock()
        mock_embed = MagicMock(return_value=[[0.1] * 768])

        from app.services.commentary_ingest import ingest_transcript

        # First ingest
        r1 = ingest_transcript(
            **_make_ingest_kwargs(),
            qdrant_client=mock_qdrant,
            registry_path=str(registry_path),
            embed_batch_fn=mock_embed,
        )
        # Second ingest with same content (same source_id)
        r2 = ingest_transcript(
            **_make_ingest_kwargs(),
            qdrant_client=mock_qdrant,
            registry_path=str(registry_path),
            embed_batch_fn=mock_embed,
        )

        assert r1["staged"] is True
        # Second should still report staged (dedup log warning, but same result shape)
        index = json.loads(index_path.read_text())
        assert len(index) == 1  # Only one entry, not two


class TestTranscriptReviewService:
    def test_list_pending_returns_staged_items(self, staging_dir):
        staged, index_path = staging_dir
        index_path.write_text(json.dumps({
            "src_1": {"source_type": "youtube_transcript", "title": "Test", "staged_at": "2026-03-27T00:00:00Z", "chunk_count": 5, "path": str(staged / "src_1.jsonl")},
        }))
        from cockpit.integrations.transcript_review import TranscriptReviewService
        svc = TranscriptReviewService()
        pending = svc.list_pending()
        assert len(pending) == 1
        assert pending[0]["source_id"] == "src_1"

    def test_approve_reads_staged_and_upserts(self, staging_dir):
        staged, index_path = staging_dir
        # Write a staged file with one point
        point = {"id": "abc", "vector": [0.1] * 768, "payload": {"text": "test"}}
        staged_file = staged / "src_1.jsonl"
        staged_file.write_text(json.dumps(point) + "\n")
        index_path.write_text(json.dumps({
            "src_1": {"path": str(staged_file), "source_type": "youtube_transcript", "collection_name": "commentary_chunks", "staged_at": "2026-03-27T00:00:00Z", "chunk_count": 1},
        }))

        with patch("cockpit.integrations.transcript_review.TranscriptReviewService.approve") as mock_approve:
            # Test the real approve method without Qdrant
            pass

        # Test with mocked Qdrant
        from cockpit.integrations.transcript_review import TranscriptReviewService
        with patch("app.services.embeddings.verify_qdrant") as mock_verify, \
             patch("app.services.embeddings.upsert_points") as mock_upsert, \
             patch("app.services.source_registry.SourceRegistry") as mock_registry:
            mock_verify.return_value = MagicMock()
            svc = TranscriptReviewService()
            result = svc.approve("src_1")

        assert result["ok"] is True
        assert result["chunks_indexed"] == 1
        mock_upsert.assert_called_once()
        assert not staged_file.exists()
        # Index should be cleared
        index = json.loads(index_path.read_text())
        assert "src_1" not in index

    def test_reject_deletes_staged_file(self, staging_dir):
        staged, index_path = staging_dir
        staged_file = staged / "src_1.jsonl"
        staged_file.write_text('{"id": "abc"}\n')
        index_path.write_text(json.dumps({
            "src_1": {"path": str(staged_file), "staged_at": "2026-03-27T00:00:00Z", "chunk_count": 1},
        }))

        from cockpit.integrations.transcript_review import TranscriptReviewService
        with patch("app.services.source_registry.SourceRegistry"):
            svc = TranscriptReviewService()
            result = svc.reject("src_1")

        assert result["ok"] is True
        assert not staged_file.exists()
        index = json.loads(index_path.read_text())
        assert "src_1" not in index

    def test_purge_expired_removes_old_entries(self, staging_dir):
        staged, index_path = staging_dir
        old_date = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        staged_file = staged / "old_src.jsonl"
        staged_file.write_text('{"id": "abc"}\n')
        index_path.write_text(json.dumps({
            "old_src": {"path": str(staged_file), "staged_at": old_date, "chunk_count": 1},
        }))

        from cockpit.integrations.transcript_review import TranscriptReviewService
        svc = TranscriptReviewService()
        purged = svc.purge_expired(max_age_days=7)

        assert "old_src" in purged
        assert not staged_file.exists()
        index = json.loads(index_path.read_text())
        assert "old_src" not in index
