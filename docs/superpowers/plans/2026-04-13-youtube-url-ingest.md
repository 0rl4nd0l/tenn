# YouTube URL Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow a YouTube URL pasted into cockpit chat to be ingested as a transcript into the commentary RAG pipeline via `/ingest <url>`.

**Architecture:** A new `fetch_video_metadata()` helper in `youtube_transcript_fetcher.py` resolves a single URL to a `YoutubeVideo` dataclass using yt-dlp. A new `POST /api/commentary/ingest-url` backend endpoint calls that helper + the existing `ingest_transcript()` pipeline. `BackendApiClient` gains an `ingest_url()` method. The cockpit chat dispatcher gains a `/ingest` command that calls the backend (or a local fallback). A conversation-command NL rule fires when a YouTube URL is pasted bare.

**Tech Stack:** FastAPI, yt-dlp (library + CLI fallback), youtube-transcript-api, existing `ingest_transcript()` + staging gate, httpx (cockpit client), pytest + monkeypatch.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/services/youtube_transcript_fetcher.py` | Add `fetch_video_metadata(url)` — single-URL → `YoutubeVideo` |
| Modify | `backend/app/api/commentary.py` | Add `POST /api/commentary/ingest-url` endpoint |
| Modify | `cockpit/integrations/backend_api.py` | Add `ingest_url(url)` method |
| Modify | `cockpit/ui/app.py` | Add `/ingest` command handler block |
| Modify | `cockpit/core/conversation_commands.py` | Add NL rules for YouTube URL paste |
| Modify | `backend/tests/test_commentary_endpoints.py` | Tests for new endpoint |
| Modify | `backend/tests/test_youtube_transcript_fetcher.py` (new) | Tests for `fetch_video_metadata` |
| Modify | `cockpit/tests/test_backend_api_client_ingest_url.py` (new) | Tests for `BackendApiClient.ingest_url` |
| Modify | `cockpit/tests/test_conversation_commands.py` | Tests for new NL rules |

---

## Task 1: `fetch_video_metadata` — single URL → YoutubeVideo

**Files:**
- Modify: `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py`
- Create: `financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py`

- [ ] **Step 1: Write the failing test**

Create `financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py`:

```python
from __future__ import annotations

import pytest
from app.services.youtube_transcript_fetcher import YoutubeVideo, fetch_video_metadata


def _make_ydl_info(
    video_id="abc123",
    title="My Video",
    channel="My Channel",
    upload_date="20260412",
    webpage_url="https://www.youtube.com/watch?v=abc123",
):
    return {
        "id": video_id,
        "title": title,
        "channel": channel,
        "upload_date": upload_date,
        "webpage_url": webpage_url,
        "release_timestamp": None,
        "timestamp": None,
    }


class TestFetchVideoMetadata:
    def test_returns_youtube_video_from_watch_url(self, monkeypatch):
        info = _make_ydl_info()

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        video = fetch_video_metadata("https://www.youtube.com/watch?v=abc123")

        assert isinstance(video, YoutubeVideo)
        assert video.video_id == "abc123"
        assert video.title == "My Video"
        assert video.channel_name == "My Channel"
        assert video.published_at == "2026-04-12T00:00:00Z"
        assert "abc123" in video.webpage_url

    def test_returns_youtube_video_from_short_url(self, monkeypatch):
        info = _make_ydl_info(video_id="UNJwgi0aW6s", title="Short URL Title")

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        video = fetch_video_metadata("https://youtu.be/UNJwgi0aW6s")
        assert video.video_id == "UNJwgi0aW6s"
        assert video.title == "Short URL Title"

    def test_yt_dlp_unavailable_raises_runtime_error(self, monkeypatch):
        monkeypatch.setitem(__import__("sys").modules, "yt_dlp", None)
        with pytest.raises(RuntimeError, match="yt-dlp is required"):
            fetch_video_metadata("https://youtu.be/abc123")

    def test_yt_dlp_returns_none_raises_runtime_error(self, monkeypatch):
        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return None

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        with pytest.raises(RuntimeError, match="no metadata"):
            fetch_video_metadata("https://youtu.be/abc123")

    def test_missing_video_id_raises_runtime_error(self, monkeypatch):
        info = _make_ydl_info(video_id="")

        class StubYDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def extract_info(self, url, download=False): return info

        import yt_dlp
        monkeypatch.setattr("yt_dlp.YoutubeDL", StubYDL)

        with pytest.raises(RuntimeError, match="could not resolve video_id"):
            fetch_video_metadata("https://youtu.be/abc123")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest backend/tests/test_youtube_transcript_fetcher.py -v
```

Expected: `ImportError` or `AttributeError` — `fetch_video_metadata` does not exist yet.

- [ ] **Step 3: Implement `fetch_video_metadata`**

Add to the bottom of `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py` (before the `YoutubeTranscriptFetcher` class):

```python
def fetch_video_metadata(url: str) -> YoutubeVideo:
    """Resolve a single YouTube URL to a YoutubeVideo using yt-dlp.

    Raises RuntimeError if yt-dlp is unavailable, returns no info,
    or the video_id cannot be resolved.
    """
    try:
        import yt_dlp  # type: ignore
    except Exception as exc:
        raise RuntimeError("yt-dlp is required for single-URL ingestion") from exc

    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(str(url or "").strip(), download=False)

    if not info:
        raise RuntimeError(f"yt-dlp returned no metadata for URL: {url}")

    video_id = str(info.get("id") or "").strip()
    if not video_id:
        raise RuntimeError(f"yt-dlp could not resolve video_id from URL: {url}")

    title = str(info.get("title") or video_id).strip() or video_id
    channel = str(info.get("channel") or info.get("uploader") or "").strip()
    webpage_url = str(info.get("webpage_url") or url).strip()
    published_at = _iso_from_timestamp(
        info.get("release_timestamp") or info.get("timestamp") or info.get("upload_date")
    )

    return YoutubeVideo(
        video_id=video_id,
        title=title,
        channel_name=channel,
        published_at=published_at,
        webpage_url=webpage_url,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest backend/tests/test_youtube_transcript_fetcher.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py \
        financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py
git commit -m "feat(commentary): add fetch_video_metadata for single-URL yt-dlp resolution"
```

---

## Task 2: `POST /api/commentary/ingest-url` backend endpoint

**Files:**
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Modify: `financial-engine_v2/backend/tests/test_commentary_endpoints.py`

- [ ] **Step 1: Write the failing tests**

Append to `financial-engine_v2/backend/tests/test_commentary_endpoints.py`:

```python
# ---------------------------------------------------------------------------
# POST /api/commentary/ingest-url
# ---------------------------------------------------------------------------

from app.api.commentary import ingest_url


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
            ingest_url({"url": ""})
        assert exc_info.value.status_code == 422

    def test_non_youtube_url_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            ingest_url({"url": "https://example.com/not-youtube"})
        assert exc_info.value.status_code == 422

    def test_metadata_fetch_failure_raises_502(self, monkeypatch):
        import app.api.commentary as mod
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: (_ for _ in ()).throw(RuntimeError("yt-dlp failed")))
        with pytest.raises(HTTPException) as exc_info:
            ingest_url({"url": "https://youtu.be/abc123"})
        assert exc_info.value.status_code == 502

    def test_transcript_unavailable_raises_422(self, monkeypatch):
        import app.api.commentary as mod
        from app.services.youtube_transcript_fetcher import TranscriptUnavailableError
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(mod, "_default_fetch_transcript", lambda v: (_ for _ in ()).throw(TranscriptUnavailableError("no transcript")))
        with pytest.raises(HTTPException) as exc_info:
            ingest_url({"url": "https://youtu.be/abc123"})
        assert exc_info.value.status_code == 422

    def test_successful_ingest_returns_staging_result(self, monkeypatch):
        import app.api.commentary as mod
        monkeypatch.setattr(mod, "fetch_video_metadata", lambda url: self._make_video())
        monkeypatch.setattr(mod, "_default_fetch_transcript", lambda v: "This is the transcript text.")
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
        result = ingest_url({"url": "https://youtu.be/abc123"})
        assert result["ok"] is True
        assert result["source_id"] == "youtube_transcript:test-video:abc123"
        assert result["staged"] is True
        assert result["video_title"] == "Test Video"
        assert result["channel"] == "Test Channel"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest backend/tests/test_commentary_endpoints.py::TestIngestUrl -v
```

Expected: `ImportError` — `ingest_url` does not exist yet.

- [ ] **Step 3: Implement the endpoint**

Add to `financial-engine_v2/backend/app/api/commentary.py`.

First, extend the imports at the top of the file:

```python
# Add to existing imports
from app.services.youtube_transcript_fetcher import (
    TranscriptUnavailableError,
    YoutubeVideo,
    _default_fetch_transcript,
    fetch_video_metadata,
)
from app.services.commentary_ingest import ingest_transcript
```

Then add a request model and the endpoint (place after the `purge_expired_transcripts` endpoint):

```python
# ---------------------------------------------------------------------------
# POST /api/commentary/ingest-url
# ---------------------------------------------------------------------------

_YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/watch\?.*v=|youtu\.be/)([A-Za-z0-9_\-]{11})"
)


class IngestUrlRequest(BaseModel):
    url: str


@router.post(
    "/ingest-url",
    dependencies=[Depends(require_api_key)],
)
def ingest_url(body: IngestUrlRequest) -> dict[str, Any]:
    url = str(body.url or "").strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")
    if not _YOUTUBE_URL_RE.search(url):
        raise HTTPException(status_code=422, detail="url must be a YouTube watch or short URL")

    try:
        video = fetch_video_metadata(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"metadata fetch failed: {exc}") from exc

    try:
        transcript_text = _default_fetch_transcript(video)
    except TranscriptUnavailableError as exc:
        raise HTTPException(status_code=422, detail=f"transcript unavailable: {exc}") from exc

    result = ingest_transcript(
        transcript_text=transcript_text,
        source_name=video.title,
        source_type="youtube_transcript",
        speaker=video.channel_name,
        published_at=video.published_at,
    )

    return {
        **result,
        "video_title": video.title,
        "channel": video.channel_name,
        "published_at": video.published_at,
        "webpage_url": video.webpage_url,
    }
```

Also add `BaseModel` to the FastAPI/pydantic imports at the top of `commentary.py`:

```python
from pydantic import BaseModel
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest backend/tests/test_commentary_endpoints.py::TestIngestUrl -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full commentary test suite to confirm no regressions**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest backend/tests/test_commentary_endpoints.py -v
```

Expected: all 22 passed.

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_commentary_endpoints.py
git commit -m "feat(commentary): add POST /api/commentary/ingest-url endpoint"
```

---

## Task 3: `BackendApiClient.ingest_url` cockpit method

**Files:**
- Modify: `financial-engine_v2/cockpit/integrations/backend_api.py`
- Create: `financial-engine_v2/cockpit/tests/test_backend_api_client_ingest_url.py`

- [ ] **Step 1: Write the failing test**

Create `financial-engine_v2/cockpit/tests/test_backend_api_client_ingest_url.py`:

```python
from __future__ import annotations

import pytest
import httpx
import respx

from cockpit.integrations.backend_api import BackendApiClient


BASE = "http://127.0.0.1:8000"


@respx.mock
def test_ingest_url_success():
    respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "source_id": "youtube_transcript:my-video:abc123",
                "staged": True,
                "chunks_staged": 18,
                "chunks_indexed": 0,
                "video_title": "My Video",
                "channel": "My Channel",
            },
        )
    )
    client = BackendApiClient(BASE, api_key="test-key")
    result = client.ingest_url("https://youtu.be/abc123")
    assert result["ok"] is True
    assert result["chunks_staged"] == 18
    assert result["video_title"] == "My Video"


@respx.mock
def test_ingest_url_422_raises():
    respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(422, json={"detail": "transcript unavailable"})
    )
    client = BackendApiClient(BASE, api_key="test-key")
    with pytest.raises(httpx.HTTPStatusError):
        client.ingest_url("https://youtu.be/abc123")


@respx.mock
def test_ingest_url_sends_api_key():
    route = respx.post(f"{BASE}/api/commentary/ingest-url").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client = BackendApiClient(BASE, api_key="secret")
    client.ingest_url("https://youtu.be/abc123")
    assert route.calls[0].request.headers.get("x-api-key") == "secret"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_backend_api_client_ingest_url.py -v
```

Expected: `AttributeError` — `ingest_url` method does not exist.

- [ ] **Step 3: Implement `BackendApiClient.ingest_url`**

Add to `financial-engine_v2/cockpit/integrations/backend_api.py`, after `purge_expired_transcripts`:

```python
def ingest_url(
    self,
    url: str,
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    endpoint = f"{self.base_url}/api/commentary/ingest-url"
    headers: dict[str, str] = {}
    if self.api_key:
        headers["X-API-Key"] = self.api_key
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.post(endpoint, json={"url": url}, headers=headers)
        response.raise_for_status()
        return response.json() if response.content else {}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_backend_api_client_ingest_url.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/cockpit/integrations/backend_api.py \
        financial-engine_v2/cockpit/tests/test_backend_api_client_ingest_url.py
git commit -m "feat(cockpit): add BackendApiClient.ingest_url method"
```

---

## Task 4: `/ingest` command in cockpit chat dispatcher

**Files:**
- Modify: `financial-engine_v2/cockpit/ui/app.py`

- [ ] **Step 1: Write the failing test**

Search for the existing `/review` command test in `cockpit/tests/test_slash_commands.py` to find the test pattern, then add:

```bash
cd financial-engine_v2
grep -n "review" cockpit/tests/test_slash_commands.py | head -20
```

Then append to `cockpit/tests/test_slash_commands.py`:

```python
class TestIngestCommand:
    """Tests for /ingest <url> command dispatch."""

    def _make_app(self, monkeypatch, backend_result=None, backend_raises=None):
        """Return a minimal CockpitApp stub with _handle_ingest_command exposed."""
        # Import here to avoid circular issues at module level
        import types, sys
        # We test _handle_ingest_command directly since it's a pure method
        from cockpit.ui.app import CockpitApp

        app = object.__new__(CockpitApp)

        class StubClient:
            def ingest_url(self, url):
                if backend_raises:
                    raise backend_raises
                return backend_result or {
                    "ok": True,
                    "source_id": "youtube_transcript:test:abc123",
                    "staged": True,
                    "chunks_staged": 5,
                    "video_title": "Test Video",
                    "channel": "Test Channel",
                }

        app._backend_client = StubClient()
        return app

    def test_ingest_url_success_returns_staged_message(self, monkeypatch):
        app = self._make_app(monkeypatch)
        result = app._handle_ingest_command("https://youtu.be/abc123", log=None)
        assert "Test Video" in result
        assert "5 chunks staged" in result
        assert "/review approve" in result

    def test_ingest_url_empty_returns_usage(self, monkeypatch):
        app = self._make_app(monkeypatch)
        result = app._handle_ingest_command("", log=None)
        assert "Usage" in result

    def test_ingest_url_backend_error_returns_error_message(self, monkeypatch):
        app = self._make_app(monkeypatch, backend_raises=Exception("502 upstream"))
        result = app._handle_ingest_command("https://youtu.be/abc123", log=None)
        assert "failed" in result.lower()

    def test_ingest_no_backend_returns_not_available(self, monkeypatch):
        from cockpit.ui.app import CockpitApp
        app = object.__new__(CockpitApp)
        app._backend_client = None
        result = app._handle_ingest_command("https://youtu.be/abc123", log=None)
        assert "backend" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_slash_commands.py::TestIngestCommand -v
```

Expected: `AttributeError` — `_handle_ingest_command` does not exist.

- [ ] **Step 3: Add `_handle_ingest_command` method to `CockpitApp`**

In `financial-engine_v2/cockpit/ui/app.py`, add the method alongside `_handle_review_command` (around line 2151):

```python
def _handle_ingest_command(self, url: str, log) -> str:
    """Handle /ingest <url> — fetch and stage a YouTube transcript by URL."""
    url = str(url or "").strip()
    if not url:
        return "Usage: /ingest <youtube-url>"
    if not self._backend_client:
        return "Ingest requires the backend to be running. Start it and reconnect."
    try:
        result = self._backend_client.ingest_url(url)
    except Exception as exc:
        return f"Ingest failed: {exc}"
    title = result.get("video_title") or result.get("source_id") or url
    channel = result.get("channel", "")
    chunks = result.get("chunks_staged", result.get("chunks_indexed", 0))
    source_id = result.get("source_id", "")
    staged = result.get("staged", False)
    if staged:
        return (
            f'Staged "{title}" ({channel}) — {chunks} chunks pending review.\n'
            f"Run: /review approve {source_id}"
        )
    return f'Ingested "{title}" ({channel}) — {chunks} chunks indexed directly.'
```

- [ ] **Step 4: Wire `/ingest` into the chat command dispatcher**

In `financial-engine_v2/cockpit/ui/app.py`, add the dispatch block immediately after the `/review` block (around line 1181). Find the line:

```python
        # Handle /strategy commands
        if stripped.startswith("/strategy"):
```

Insert before it:

```python
        # Handle /ingest <url> — single YouTube URL transcript ingest
        if stripped.startswith("/ingest"):
            url = stripped[len("/ingest"):].strip()
            now_iso = datetime.now(timezone.utc).isoformat()
            reply = self._handle_ingest_command(url, log)
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(self.thread_id, "assistant", reply, now_iso)
            return
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_slash_commands.py::TestIngestCommand -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/ui/app.py \
        financial-engine_v2/cockpit/tests/test_slash_commands.py
git commit -m "feat(cockpit): add /ingest <url> command for YouTube transcript staging"
```

---

## Task 5: Natural-language rules for YouTube URL paste

**Files:**
- Modify: `financial-engine_v2/cockpit/core/conversation_commands.py`
- Modify: `financial-engine_v2/cockpit/tests/test_conversation_commands.py`

- [ ] **Step 1: Write the failing tests**

Append to `financial-engine_v2/cockpit/tests/test_conversation_commands.py`:

```python
class TestYouTubeIngestRules:
    def test_bare_youtube_watch_url_maps_to_ingest(self):
        url = "https://www.youtube.com/watch?v=UNJwgi0aW6s"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_bare_youtu_be_url_maps_to_ingest(self):
        url = "https://youtu.be/UNJwgi0aW6s"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_youtu_be_with_si_param_maps_to_ingest(self):
        url = "https://youtu.be/UNJwgi0aW6s?si=jeB30d8VCY8xjnbR"
        result = derive_conversational_command(url)
        assert result == f"/ingest {url}"

    def test_ingest_this_video_phrase_maps_to_ingest(self):
        url = "https://youtu.be/abc123"
        result = derive_conversational_command(f"ingest this video {url}")
        assert result == f"/ingest {url}"

    def test_non_youtube_url_does_not_match(self):
        result = derive_conversational_command("https://example.com/page")
        assert result is None

    def test_slash_command_passthrough_not_matched(self):
        result = derive_conversational_command("/ingest https://youtu.be/abc123")
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_conversation_commands.py::TestYouTubeIngestRules -v
```

Expected: all fail — rules do not exist yet.

- [ ] **Step 3: Add NL rules to `conversation_commands.py`**

In `financial-engine_v2/cockpit/core/conversation_commands.py`, add after the existing `/review` rules (around line 147):

```python
_YOUTUBE_URL_PATTERN = re.compile(
    r"(https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]*v=[A-Za-z0-9_\-]{11}[^\s]*|youtu\.be/[A-Za-z0-9_\-]{11}[^\s]*))"
)


@_rule(_YOUTUBE_URL_PATTERN)
def _(m, _msg):
    return f"/ingest {m.group(1)}"
```

Also add `import re` at the top of the file if it is not already present (check first with `grep "^import re" cockpit/core/conversation_commands.py`).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_conversation_commands.py::TestYouTubeIngestRules -v
```

Expected: 6 passed.

- [ ] **Step 5: Run full conversation commands test suite**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest cockpit/tests/test_conversation_commands.py -v
```

Expected: all pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/core/conversation_commands.py \
        financial-engine_v2/cockpit/tests/test_conversation_commands.py
git commit -m "feat(cockpit): map pasted YouTube URLs to /ingest command"
```

---

## Task 6: Full regression sweep

- [ ] **Step 1: Run all affected test suites**

```bash
cd financial-engine_v2
.venv/bin/python -m pytest \
    backend/tests/test_youtube_transcript_fetcher.py \
    backend/tests/test_commentary_endpoints.py \
    cockpit/tests/test_backend_api_client_ingest_url.py \
    cockpit/tests/test_slash_commands.py \
    cockpit/tests/test_conversation_commands.py \
    -v
```

Expected: all pass.

- [ ] **Step 2: Smoke-test the live endpoint (optional, requires backend running)**

```bash
curl -s -X POST http://127.0.0.1:8000/api/commentary/ingest-url \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TENN_API_KEY" \
  -d '{"url": "https://youtu.be/UNJwgi0aW6s"}' | python3 -m json.tool
```

Expected: `{"ok": true, "staged": true, "chunks_staged": 18, "video_title": "A Significant Pivot Point in Markets: We're Buying", ...}`

- [ ] **Step 3: Final milestone commit**

```bash
git add -p  # review any remaining unstaged changes
git commit -m "milestone(commentary): YouTube URL paste-to-ingest end-to-end wired"
```

---

## Self-Review

**Spec coverage:**
- ✅ Single URL → metadata resolve via yt-dlp (`fetch_video_metadata`)
- ✅ Transcript fetch via existing `_default_fetch_transcript`
- ✅ Clean → chunk → embed → stage via existing `ingest_transcript()`
- ✅ Backend endpoint `POST /api/commentary/ingest-url`
- ✅ Cockpit `BackendApiClient.ingest_url()`
- ✅ `/ingest <url>` slash command with staged/indexed feedback and approve hint
- ✅ Bare YouTube URL paste auto-maps to `/ingest`
- ✅ Graceful no-backend message when backend not configured
- ✅ TDD throughout with full test coverage

**Placeholder scan:** No TBDs, no "add appropriate error handling", all code blocks are complete.

**Type consistency:** `YoutubeVideo` dataclass used consistently across Task 1 and Task 2. `fetch_video_metadata` signature `(url: str) -> YoutubeVideo` matches usage in endpoint. `ingest_url` in `BackendApiClient` returns `dict[str, Any]` matching endpoint response shape. `_handle_ingest_command(url: str, log) -> str` matches dispatcher call site.
