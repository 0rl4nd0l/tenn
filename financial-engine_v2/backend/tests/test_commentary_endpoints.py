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
    _validate_source_id,
    approve_transcript,
    get_pending_transcripts,
    purge_expired_transcripts,
    reject_transcript,
)


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

    def test_staged_path_outside_allowed_root_rejected(self):
        """source_id with path traversal chars is rejected at validation."""
        with pytest.raises(HTTPException) as exc_info:
            approve_transcript("../../etc/passwd")
        assert exc_info.value.status_code == 400


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
    IngestMarketplaceSnapshotRequest,
    InspectMarketplaceRequest,
    ingest_marketplace_snapshot,
    ingest_url,
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

    def test_successful_ingest_returns_staging_result(self, monkeypatch):
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
        result = ingest_url(IngestUrlRequest(url="https://youtu.be/abc123abcde"))
        assert result["ok"] is True
        assert result["source_id"] == "youtube_transcript:test-video:abc123"
        assert result["staged"] is True
        assert result["video_title"] == "Test Video"
        assert result["channel"] == "Test Channel"

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
