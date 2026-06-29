"""Tests for /api/commentary/transcripts/* endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.commentary import (
    TranscriptReviewUpdateRequest,
    _chunk_takeaways,
    _commentary_takeaways_payload,
    _validate_source_id,
    approve_transcript,
    get_pending_transcripts,
    purge_expired_transcripts,
    reject_transcript,
    update_transcript_review,
)


# ---------------------------------------------------------------------------
# _chunk_takeaways — per-chunk fallback regression
# ---------------------------------------------------------------------------

def _make_point(index: int, text: str, source_id: str = "test:src:abc") -> dict:
    return {
        "payload": {
            "chunk_index": index,
            "text": text,
            "source_id": source_id,
        }
    }


class TestChunkTakeaways:
    def test_single_chunk_with_no_punctuation_returns_fallback(self):
        """Short caption phrases produce no sentences >= 45 chars — fallback should fire."""
        text = "\n".join(["XJO sitting flat"] * 10)  # all phrases < 45 chars
        points = [_make_point(0, text)]
        result = _chunk_takeaways(points, "test:src:abc", limit=5)
        assert len(result) == 1
        assert result[0]["text"]  # fallback text included

    def test_multiple_chunks_with_no_punctuation_all_represented(self):
        """Each chunk should contribute at least one candidate via per-chunk fallback.
        Regression for bug where only chunk 0 got the fallback."""
        chunks = [
            "\n".join([f"chunk {i} short phrase here"] * 8)  # all < 45 chars
            for i in range(5)
        ]
        points = [_make_point(i, text) for i, text in enumerate(chunks)]
        result = _chunk_takeaways(points, "test:src:abc", limit=5)
        assert len(result) == 5, (
            f"Expected 5 takeaways (one per chunk via fallback), got {len(result)}"
        )
        # Each result should come from a different chunk
        chunk_ids = {r["citations"][0]["chunk_id"] for r in result}
        assert len(chunk_ids) == 5

    def test_chunks_with_sentences_score_above_fallback(self):
        """Chunks with real sentences should produce multiple takeaways ranked by score."""
        good_text = (
            "The XJO showed strong earnings growth and solid dividend yield. "
            "Market sentiment improved on positive guidance from major sectors. "
            "Growth margins expanded significantly across the board."
        )
        points = [_make_point(0, good_text)]
        result = _chunk_takeaways(points, "test:src:abc", limit=5)
        assert len(result) >= 2
        # Higher-scoring sentences should rank first
        assert result[0]["score"] >= result[-1]["score"]

    def test_limit_respected_across_many_chunks(self):
        """With 10 chunks via fallback, limit=3 should return exactly 3."""
        chunks = ["\n".join([f"chunk {i} phrase"] * 5) for i in range(10)]
        points = [_make_point(i, text) for i, text in enumerate(chunks)]
        result = _chunk_takeaways(points, "test:src:abc", limit=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# source_id validation
# ---------------------------------------------------------------------------

class TestValidateSourceId:
    def test_valid_source_ids(self):
        assert _validate_source_id("abc-123") == "abc-123"
        assert _validate_source_id("my_source_001") == "my_source_001"

    def test_valid_colon_source_id(self):
        # build_source_id produces "type:slug:hex16" — colons must be accepted
        sid = "youtube_transcript:my-video-title:a3f9bc12ef34cd56"
        assert _validate_source_id(sid) == sid

    def test_empty_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_source_id("")
        assert exc_info.value.status_code == 400

    def test_invalid_chars_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_source_id("../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_too_long_raises_400(self):
        # 192 is the current max — 193 must fail, 200 must also fail
        with pytest.raises(HTTPException) as exc_info:
            _validate_source_id("a" * 193)
        assert exc_info.value.status_code == 400

        with pytest.raises(HTTPException) as exc_info:
            _validate_source_id("a" * 200)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/commentary/transcripts/pending
# ---------------------------------------------------------------------------

class TestGetPendingTranscripts:
    def test_empty_staging_dir(self):
        with patch("app.api.commentary._load_index", return_value={}):
            result = get_pending_transcripts()
        assert result == {"pending": [], "count": 0}

    def test_non_empty_staging_dir(self):
        index = {
            "src-001": {"staged_at": "2026-03-20T10:00:00Z", "path": "/tmp/src-001.jsonl"},
            "src-002": {"staged_at": "2026-03-21T10:00:00Z", "path": "/tmp/src-002.jsonl"},
        }
        with patch("app.api.commentary._load_index", return_value=index):
            result = get_pending_transcripts()
        assert result["count"] == 2
        assert result["pending"][0]["source_id"] == "src-001"
        assert result["pending"][1]["source_id"] == "src-002"

    def test_include_takeaways_enriches_pending_item(self):
        index = {
            "src-001": {"staged_at": "2026-03-20T10:00:00Z", "path": "/tmp/src-001.jsonl"},
        }
        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch(
                "app.api.commentary._takeaway_enrichment",
                return_value={
                    "takeaway_status": "ready",
                    "takeaways": [{"text": "Transcript takeaway"}],
                    "watchlist_suggestions": [],
                    "outline": [{"summary": "Section summary"}],
                    "takeaway_payload": {"ok": True},
                },
            ) as enrichment,
        ):
            result = get_pending_transcripts(include_takeaways=True, takeaway_limit=3)

        enrichment.assert_called_once_with("src-001", 3)
        assert result["pending"][0]["takeaway_status"] == "ready"
        assert result["pending"][0]["outline"][0]["summary"] == "Section summary"


# ---------------------------------------------------------------------------
# POST /api/commentary/transcripts/{source_id}/approve
# ---------------------------------------------------------------------------

class TestApproveTranscript:
    def test_source_not_found_raises_404(self):
        with patch("app.api.commentary._load_index", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                approve_transcript("unknown-source")
            assert exc_info.value.status_code == 404

    def test_staged_file_missing_raises_404(self):
        index = {"src-001": {"path": "/tmp/nonexistent-file.jsonl"}}
        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                approve_transcript("src-001")
            assert exc_info.value.status_code == 404

    def test_empty_staged_file_raises_422(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text("")
        index = {"src-001": {"path": str(staged_file)}}
        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                approve_transcript("src-001")
            assert exc_info.value.status_code == 422

    def test_qdrant_unavailable_raises_503(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text('{"id": "pt-1", "vector": [0.1], "payload": {"text": "hello"}}\n')
        index = {"src-001": {"path": str(staged_file), "collection_name": "commentary_chunks"}}
        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index"),
            patch("app.api.commentary.verify_qdrant", side_effect=RuntimeError("connection refused")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                approve_transcript("src-001")
            assert exc_info.value.status_code == 503

    def test_successful_approve(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text(
            '{"id": "pt-1", "vector": [0.1, 0.2], "payload": {"text": "hello"}}\n'
            '{"id": "pt-2", "vector": [0.3, 0.4], "payload": {"text": "world"}}\n'
        )
        index = {"src-001": {"path": str(staged_file), "collection_name": "commentary_chunks"}}
        mock_client = MagicMock()
        saved_indices = []

        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index", side_effect=lambda idx: saved_indices.append(idx)),
            patch("app.api.commentary.verify_qdrant", return_value=mock_client),
            patch("app.api.commentary.upsert_points", return_value={"written_points": 2, "rejected_payloads": 0}),
            patch("app.api.commentary._update_source_registry"),
        ):
            result = approve_transcript("src-001")

        assert result["ok"] is True
        assert result["source_id"] == "src-001"
        assert result["points_upserted"] == 2
        assert result["collection"] == "commentary_chunks"
        # Index should have src-001 removed
        assert "src-001" not in saved_indices[-1]

    def test_successful_approve_applies_review_metadata(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text(
            json.dumps(
                {
                    "id": "pt-1",
                    "vector": [0.1, 0.2],
                    "payload": {
                        "source_id": "src-001",
                        "text": "hello",
                        "video_id": "abc123",
                        "webpage_url": "https://www.youtube.com/watch?v=abc123",
                        "segment_start_seconds": 12.0,
                        "segment_end_seconds": 15.5,
                    },
                }
            )
            + "\n"
        )
        index = {
            "src-001": {
                "path": str(staged_file),
                "collection_name": "commentary_chunks",
                "credibility_weight": 0.72,
                "review_takeaways": [{"text": "Operator-edited takeaway"}],
            }
        }
        captured_points: list[dict[str, Any]] = []

        def fake_upsert(_client, _collection, points):
            captured_points.extend(points)
            return {"written_points": len(points)}

        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index"),
            patch("app.api.commentary.verify_qdrant", return_value=MagicMock()),
            patch("app.api.commentary.upsert_points", side_effect=fake_upsert),
            patch("app.api.commentary._update_source_registry") as update_registry,
        ):
            result = approve_transcript("src-001")

        payload = captured_points[0]["payload"]
        assert payload["credibility_weight"] == 0.72
        assert payload["review_takeaways"] == ["Operator-edited takeaway"]
        assert payload["video_id"] == "abc123"
        assert payload["webpage_url"] == "https://www.youtube.com/watch?v=abc123"
        assert payload["segment_start_seconds"] == 12.0
        assert payload["segment_end_seconds"] == 15.5
        assert result["credibility_weight"] == 0.72
        assert result["takeaways"][0]["text"] == "Operator-edited takeaway"
        update_registry.assert_called_once_with(
            "src-001",
            "approved",
            credibility_weight=0.72,
        )

    def test_staged_path_outside_allowed_root_rejected(self):
        """source_id with path traversal chars is rejected at validation."""
        with pytest.raises(HTTPException) as exc_info:
            approve_transcript("../../etc/passwd")
        assert exc_info.value.status_code == 400


class TestUpdateTranscriptReview:
    def test_weight_updates_index_and_staged_payloads(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text(
            json.dumps(
                {
                    "id": "pt-1",
                    "vector": [0.1],
                    "payload": {"source_id": "src-001", "text": "hello"},
                }
            )
            + "\n"
        )
        index = {"src-001": {"path": str(staged_file), "collection_name": "commentary"}}
        saved_indices: list[dict[str, Any]] = []

        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index", side_effect=lambda idx: saved_indices.append(idx)),
            patch("app.api.commentary._update_source_registry") as update_registry,
        ):
            result = update_transcript_review(
                "src-001",
                TranscriptReviewUpdateRequest(credibility_weight=0.68),
            )

        assert result["ok"] is True
        assert result["credibility_weight"] == 0.68
        assert saved_indices[-1]["src-001"]["credibility_weight"] == 0.68
        rewritten = json.loads(staged_file.read_text("utf-8").strip())
        assert rewritten["payload"]["credibility_weight"] == 0.68
        update_registry.assert_called_once_with("src-001", credibility_weight=0.68)

    def test_takeaway_edits_are_used_by_takeaway_payload(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text(
            json.dumps(
                {
                    "id": "pt-1",
                    "vector": [0.1],
                    "payload": {
                        "source_id": "src-001",
                        "text": "Original transcript sentence with market growth.",
                    },
                }
            )
            + "\n"
        )
        index = {"src-001": {"path": str(staged_file), "collection_name": "commentary"}}
        saved_indices: list[dict[str, Any]] = []

        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index", side_effect=lambda idx: saved_indices.append(idx)),
            patch("app.api.commentary._update_source_registry"),
        ):
            result = update_transcript_review(
                "src-001",
                TranscriptReviewUpdateRequest(takeaways=["Edited operator takeaway"]),
            )

        assert result["takeaways"][0]["text"] == "Edited operator takeaway"
        assert saved_indices[-1]["src-001"]["review_takeaways"][0]["text"] == (
            "Edited operator takeaway"
        )
        rewritten = json.loads(staged_file.read_text("utf-8").strip())
        assert rewritten["payload"]["review_takeaways"] == ["Edited operator takeaway"]

        with (
            patch("app.api.commentary._load_index", return_value=saved_indices[-1]),
            patch("app.api.commentary.load_commentary_memos", return_value=[]),
        ):
            payload = _commentary_takeaways_payload("src-001", 5)

        assert payload["takeaway_source"] == "operator_review"
        assert payload["takeaways"][0]["text"] == "Edited operator takeaway"


# ---------------------------------------------------------------------------
# POST /api/commentary/transcripts/{source_id}/reject
# ---------------------------------------------------------------------------

class TestRejectTranscript:
    def test_success(self, tmp_path):
        staged_file = tmp_path / "src-001.jsonl"
        staged_file.write_text("some data\n")
        index = {"src-001": {"path": str(staged_file)}}
        saved_indices = []
        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index", side_effect=lambda idx: saved_indices.append(idx)),
            patch("app.api.commentary._update_source_registry"),
        ):
            result = reject_transcript("src-001")
        assert result["ok"] is True
        assert result["source_id"] == "src-001"
        assert "src-001" not in saved_indices[-1]

    def test_unknown_source_id_raises_404(self):
        with patch("app.api.commentary._load_index", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                reject_transcript("unknown")
            assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/commentary/transcripts/purge-expired
# ---------------------------------------------------------------------------

class TestPurgeExpiredTranscripts:
    def test_success_with_expired(self, tmp_path):
        staged_file = tmp_path / "old-src.jsonl"
        staged_file.write_text("data\n")
        index = {
            "old-src": {
                "staged_at": "2020-01-01T00:00:00Z",
                "path": str(staged_file),
            },
            "new-src": {
                "staged_at": "2099-01-01T00:00:00Z",
                "path": str(tmp_path / "new-src.jsonl"),
            },
        }
        saved_indices = []
        with (
            patch("app.api.commentary._load_index", return_value=index),
            patch("app.api.commentary._save_index", side_effect=lambda idx: saved_indices.append(idx)),
        ):
            result = purge_expired_transcripts(max_age_days=7)
        assert result["count"] == 1
        assert "old-src" in result["purged"]
        assert "new-src" not in result["purged"]
        # new-src should remain in index
        assert "new-src" in saved_indices[-1]

    def test_no_expired(self):
        index = {
            "new-src": {
                "staged_at": "2099-01-01T00:00:00Z",
                "path": "/tmp/new.jsonl",
            },
        }
        with (
            patch("app.api.commentary._load_index", return_value=index),
        ):
            result = purge_expired_transcripts(max_age_days=7)
        assert result["count"] == 0
        assert result["purged"] == []


# ---------------------------------------------------------------------------
# POST /api/commentary/ingest-url
# ---------------------------------------------------------------------------

from app.api.commentary import (  # noqa: E402
    IngestUrlRequest,
    IngestUrlsRequest,
    IngestMarketplaceSnapshotRequest,
    InspectMarketplaceRequest,
    ingest_marketplace_snapshot,
    ingest_url,
    ingest_urls,
    inspect_marketplace,
)


class TestIngestUrl:
    def _make_video(self):
        from app.services.youtube_transcript_fetcher import YoutubeVideo

        return YoutubeVideo(
            video_id="abc123",
            title="Test Video",
            channel_name="Test Channel",
            published_at="2026-04-12T00:00:00Z",
            webpage_url="https://www.youtube.com/watch?v=abc123",
        )

    def test_missing_url_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url=""))
        assert exc_info.value.status_code == 422

    def test_non_youtube_url_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url="https://example.com/not-youtube"))
        assert exc_info.value.status_code == 422

    def test_metadata_fetch_failure_raises_502(self, monkeypatch):
        import app.api.commentary as mod

        monkeypatch.setattr(
            mod,
            "fetch_video_metadata",
            lambda url: (_ for _ in ()).throw(RuntimeError("yt-dlp failed")),
        )
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert exc_info.value.status_code == 502

    def test_members_only_video_raises_403(self, monkeypatch):
        import app.api.commentary as mod
        from app.services.youtube_transcript_fetcher import MembersOnlyVideoError

        monkeypatch.setattr(
            mod,
            "fetch_video_metadata",
            lambda url: (_ for _ in ()).throw(MembersOnlyVideoError("members-only video")),
        )
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert exc_info.value.status_code == 403
        assert "members-only" in str(exc_info.value.detail)

    def test_transcript_unavailable_raises_422(self, monkeypatch):
        import app.api.commentary as mod
        from app.services.youtube_transcript_fetcher import TranscriptUnavailableError

        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(
            mod,
            "_default_fetch_transcript",
            lambda v: (_ for _ in ()).throw(TranscriptUnavailableError("no transcript")),
        )
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert exc_info.value.status_code == 422

    def test_transcript_fetch_runtime_failure_raises_502(self, monkeypatch):
        import app.api.commentary as mod

        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(
            mod,
            "_default_fetch_transcript",
            lambda v: (_ for _ in ()).throw(RuntimeError("transcript service failed")),
        )
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert exc_info.value.status_code == 502

    def test_successful_ingest_returns_staging_result(self, monkeypatch):
        import app.api.commentary as mod

        captured: dict = {}
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(
            mod, "_default_fetch_transcript", lambda v: "This is the transcript text."
        )

        def fake_ingest_transcript(**kwargs):
            captured.update(kwargs)
            return {
                "ok": True,
                "source_id": "youtube_transcript:test-video:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            }

        monkeypatch.setattr(mod, "ingest_transcript", fake_ingest_transcript)
        result = ingest_url(
            IngestUrlRequest(url="https://youtu.be/abc123abcde", credibility_weight=0.7)
        )
        assert result["ok"] is True
        assert result["source_id"] == "youtube_transcript:test-video:abc123"
        assert result["staged"] is True
        assert result["video_title"] == "Test Video"
        assert result["channel"] == "Test Channel"
        assert captured["credibility_weight"] == 0.7
        assert captured["video_id"] == "abc123"
        assert captured["webpage_url"] == "https://www.youtube.com/watch?v=abc123"
        assert captured["transcript_segments"] == []
        assert "transcript_chars" in result
        assert "duration_seconds" in result
        assert result["review_status"] == "staged"
        assert result["commit_path"] == "/api/commentary/transcripts/{source_id}/approve"

    def test_ingest_url_passes_transcript_segment_timing(self, monkeypatch):
        import app.api.commentary as mod
        from app.services.youtube_transcript_fetcher import YoutubeTranscriptText

        captured: dict = {}
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(
            mod,
            "_default_fetch_transcript",
            lambda v: YoutubeTranscriptText(
                "00:00:12 This is the transcript text.",
                segment_timing=[
                    {
                        "text": "This is the transcript text.",
                        "segment_start_seconds": 12.0,
                        "segment_end_seconds": 15.5,
                    }
                ],
            ),
        )

        def fake_ingest_transcript(**kwargs):
            captured.update(kwargs)
            return {
                "ok": True,
                "source_id": "youtube_transcript:test-video:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            }

        monkeypatch.setattr(mod, "ingest_transcript", fake_ingest_transcript)

        result = ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))

        assert result["ok"] is True
        assert captured["transcript_segments"] == [
            {
                "text": "This is the transcript text.",
                "segment_start_seconds": 12.0,
                "segment_end_seconds": 15.5,
            }
        ]

    def test_single_url_ingest_returns_takeaways(self, monkeypatch):
        import app.api.commentary as mod

        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(
            mod, "_default_fetch_transcript", lambda v: "This is the transcript text."
        )
        monkeypatch.setattr(
            mod,
            "ingest_transcript",
            lambda **kwargs: {
                "ok": True,
                "source_id": "youtube_transcript:test-video:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            },
        )
        monkeypatch.setattr(
            mod,
            "_commentary_takeaways_payload",
            lambda source_id, limit: {
                "ok": True,
                "source_id": source_id,
                "takeaways": [{"text": "Key takeaway", "citations": []}],
                "watchlist_suggestions": [],
                "outline": [{"summary": "Opening section"}],
            },
        )

        result = ingest_url(
            IngestUrlRequest(url="https://youtu.be/abc123abcde", takeaway_limit=3)
        )

        assert result["takeaway_status"] == "ready"
        assert result["takeaways"] == [{"text": "Key takeaway", "citations": []}]
        assert result["outline"] == [{"summary": "Opening section"}]
        assert result["takeaway_payload"]["source_id"] == "youtube_transcript:test-video:abc123"

    def test_short_transcript_for_long_video_includes_quality_warning(self, monkeypatch):
        import app.api.commentary as mod
        from app.services.youtube_transcript_fetcher import YoutubeVideo

        # 26-minute video (1560 seconds); threshold = 1560 * 2 = 3120 chars minimum
        long_video = YoutubeVideo(
            video_id="abc123",
            title="Test Video",
            channel_name="Test Channel",
            published_at="2026-05-03T06:41:57Z",
            webpage_url="https://www.youtube.com/watch?v=abc123",
            duration_seconds=1560,
        )
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: long_video)
        # Short transcript — just an intro, 400 chars (well below 3120 minimum)
        short_transcript = "Hi there, welcome to the channel. " * 12  # ~408 chars
        monkeypatch.setattr(mod, "_default_fetch_transcript", lambda v: short_transcript)
        monkeypatch.setattr(
            mod,
            "ingest_transcript",
            lambda **kwargs: {
                "ok": True,
                "source_id": "youtube_transcript:test-video:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            },
        )
        result = ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert result["ok"] is True
        assert "transcript_quality_warning" in result
        assert "incomplete" in result["transcript_quality_warning"]
        assert "26-minute" in result["transcript_quality_warning"]

    def test_adequate_transcript_has_no_quality_warning(self, monkeypatch):
        import app.api.commentary as mod
        from app.services.youtube_transcript_fetcher import YoutubeVideo

        # 2-minute video; minimum = 120 * 2 = 240 chars
        short_video = YoutubeVideo(
            video_id="abc123",
            title="Test Video",
            channel_name="Test Channel",
            published_at="2026-05-03T06:41:57Z",
            webpage_url="https://www.youtube.com/watch?v=abc123",
            duration_seconds=120,
        )
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: short_video)
        adequate_transcript = "A" * 300  # 300 chars > 240 minimum
        monkeypatch.setattr(mod, "_default_fetch_transcript", lambda v: adequate_transcript)
        monkeypatch.setattr(
            mod,
            "ingest_transcript",
            lambda **kwargs: {
                "ok": True,
                "source_id": "youtube_transcript:test-video:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            },
        )
        result = ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert result["ok"] is True
        assert "transcript_quality_warning" not in result

    def test_batch_ingest_urls_returns_takeaways(self, monkeypatch):
        import app.api.commentary as mod

        captured: dict = {}
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(
            mod, "_default_fetch_transcript", lambda v: "This is the transcript text."
        )

        def fake_ingest_transcript(**kwargs):
            captured.update(kwargs)
            return {
                "ok": True,
                "source_id": "youtube_transcript:test-video:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            }

        monkeypatch.setattr(mod, "ingest_transcript", fake_ingest_transcript)
        monkeypatch.setattr(
            mod,
            "_commentary_takeaways_payload",
            lambda source_id, limit: {
                "ok": True,
                "source_id": source_id,
                "takeaways": [{"text": "Key takeaway", "citations": []}],
                "watchlist_suggestions": [],
            },
        )

        result = ingest_urls(
            IngestUrlsRequest(
                urls=["https://youtu.be/abc123abcde"],
                credibility_weight=0.65,
                takeaway_limit=3,
            )
        )

        assert result["ok"] is True
        assert result["count"] == 1
        assert result["requires_review"] is True
        assert result["results"][0]["takeaways"][0]["text"] == "Key takeaway"
        assert result["results"][0]["source_id"] == "youtube_transcript:test-video:abc123"
        assert captured["credibility_weight"] == 0.65
        assert captured["video_id"] == "abc123"
        assert captured["webpage_url"] == "https://www.youtube.com/watch?v=abc123"

    def test_empty_transcript_raises_422(self, monkeypatch):
        import app.api.commentary as mod

        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(mod, "_default_fetch_transcript", lambda v: "This is the transcript text.")
        monkeypatch.setattr(
            mod,
            "ingest_transcript",
            lambda **kwargs: (_ for _ in ()).throw(ValueError("transcript_text is required")),
        )
        with pytest.raises(HTTPException) as exc_info:
            ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert exc_info.value.status_code == 422


class TestInspectMarketplace:
    def test_missing_url_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            inspect_marketplace(InspectMarketplaceRequest(url=""))
        assert exc_info.value.status_code == 422

    def test_non_marketplace_url_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            inspect_marketplace(
                InspectMarketplaceRequest(url="https://example.com/not-marketplace")
            )
        assert exc_info.value.status_code == 422

    def test_browser_unavailable_maps_to_503(self, monkeypatch):
        import app.api.commentary as mod

        monkeypatch.setattr(
            mod,
            "inspect_facebook_marketplace_listing",
            lambda url: (_ for _ in ()).throw(
                RuntimeError("marketplace_browser_unavailable: no debugger")
            ),
        )
        with pytest.raises(HTTPException) as exc_info:
            inspect_marketplace(
                InspectMarketplaceRequest(
                    url="https://www.facebook.com/marketplace/item/1234567890"
                )
            )
        assert exc_info.value.status_code == 503

    def test_legacy_login_required_prefix_is_not_special_cased(self, monkeypatch):
        import app.api.commentary as mod

        monkeypatch.setattr(
            mod,
            "inspect_facebook_marketplace_listing",
            lambda url: (_ for _ in ()).throw(
                RuntimeError("marketplace_login_required: log in first")
            ),
        )
        with pytest.raises(HTTPException) as exc_info:
            inspect_marketplace(
                InspectMarketplaceRequest(
                    url="https://www.facebook.com/marketplace/item/1234567890"
                )
            )
        assert exc_info.value.status_code == 502

    def test_successful_marketplace_inspect_stages_market_commentary(self, monkeypatch):
        import app.api.commentary as mod

        captured: dict[str, Any] = {}
        monkeypatch.setattr(
            mod,
            "inspect_facebook_marketplace_listing",
            lambda url: SimpleNamespace(
                url=url,
                captured_at="2026-04-18T10:00:00Z",
                title="2018 Excavator",
                price="$28,000",
                seller_name="Seller A",
                location="Melbourne VIC",
                description="Low hours, serviced.",
                screenshot_path="/tmp/marketplace.png",
                transcript_text="Facebook Marketplace listing snapshot",
            ),
        )

        def _fake_ingest_transcript(**kwargs):
            captured.update(kwargs)
            return {
                "ok": True,
                "source_id": "market_commentary:2018-excavator:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            }

        monkeypatch.setattr(mod, "ingest_transcript", _fake_ingest_transcript)

        result = inspect_marketplace(
            InspectMarketplaceRequest(
                url="https://www.facebook.com/marketplace/item/1234567890"
            )
        )

        assert captured["source_type"] == "market_commentary"
        assert captured["speaker"] == "Seller A"
        assert captured["topic_tags"] == ["facebook_marketplace", "marketplace_listing"]
        assert result["source_id"] == "market_commentary:2018-excavator:abc123"
        assert result["listing_title"] == "2018 Excavator"
        assert result["price"] == "$28,000"
        assert result["source_kind"] == "concat"

    def test_marketplace_snapshot_ingest_stages_market_commentary(self, monkeypatch):
        import app.api.commentary as mod

        captured: dict[str, Any] = {}

        def _fake_ingest_transcript(**kwargs):
            captured.update(kwargs)
            return {
                "ok": True,
                "source_id": "market_commentary:portable-saw:abc123",
                "staged": True,
                "chunks_staged": 1,
                "chunks_indexed": 0,
                "collection": "commentary_chunks",
            }

        monkeypatch.setattr(mod, "ingest_transcript", _fake_ingest_transcript)

        result = ingest_marketplace_snapshot(
            IngestMarketplaceSnapshotRequest(
                url="https://www.facebook.com/marketplace/item/1234567890",
                title="Portable Saw",
                price="$180",
                seller_name="Seller B",
                location="Geelong VIC",
                description="Works well, pickup only.",
                raw_text_lines=["Portable Saw", "$180", "Works well, pickup only."],
            )
        )

        assert captured["source_type"] == "market_commentary"
        assert captured["speaker"] == "Seller B"
        assert captured["topic_tags"] == ["facebook_marketplace", "marketplace_listing"]
        assert result["source_id"] == "market_commentary:portable-saw:abc123"
        assert result["listing_title"] == "Portable Saw"
        assert result["price"] == "$180"
        assert result["webpage_url"] == "https://www.facebook.com/marketplace/item/1234567890"
