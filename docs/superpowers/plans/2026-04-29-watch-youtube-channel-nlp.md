# Watch YouTube Channel via Natural Language — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the user to say "watch YouTube videos from Kneppy Invests" in Tenn chat and have the channel automatically registered in the watch list.

**Architecture:** Add a `resolve_channel_id()` function to the YouTube fetcher service (resolves name/URL/handle → channel_id via yt-dlp), expose a new `POST /api/commentary/channels` backend endpoint that writes to `ChannelRegistry`, wire a `watch_youtube_channel` read-only tool into `ToolExecutor` (calls `BackendApiClient.add_watched_channel()`), and add a `CommandRouter` regex so explicit imperative phrases bypass the LLM entirely.

**Tech Stack:** Python, FastAPI, yt-dlp, existing `ChannelRegistry`, `BackendApiClient`, `ToolExecutor`, `tool_definitions.py`, `command_router.py`

---

## File Map

| File | Change |
|------|--------|
| `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py` | Add `resolve_channel_id(name_or_url)` |
| `financial-engine_v2/backend/app/api/commentary.py` | Add `POST /api/commentary/channels` endpoint |
| `financial-engine_v2/cockpit/integrations/backend_api.py` | Add `add_watched_channel()` and `list_watched_channels()` |
| `financial-engine_v2/cockpit/core/tool_definitions.py` | Add `watch_youtube_channel` tool definition |
| `financial-engine_v2/cockpit/core/tool_executor.py` | Add `_exec_watch_youtube_channel` + `_READ_ONLY_DISPATCH` entry |
| `financial-engine_v2/cockpit/core/command_router.py` | Add `_WATCH_CHANNEL_RE` regex + route |
| `financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py` | Add `resolve_channel_id` tests |
| `financial-engine_v2/backend/tests/test_commentary_channel_endpoint.py` | New — backend endpoint tests |

---

## Task 1: `resolve_channel_id()` in youtube_transcript_fetcher.py

**Files:**
- Modify: `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py`
- Test: `financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py`

Resolves a channel name, @handle, URL, or raw channel ID to a `(channel_id, canonical_name)` tuple using yt-dlp.

- [ ] **Step 1: Write failing tests**

Add to `financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py`:

```python
from unittest.mock import patch, MagicMock
from app.services.youtube_transcript_fetcher import resolve_channel_id


class TestResolveChannelId:
    def _mock_ydl(self, channel_id: str, uploader: str):
        """Build a fake yt-dlp info dict."""
        return {
            "channel_id": channel_id,
            "uploader": uploader,
            "channel": uploader,
            "uploader_id": f"@{uploader.replace(' ', '')}",
        }

    def test_resolves_at_handle(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id("@KneppyInvests")
        assert channel_id == "UCabc123"
        assert name == "Kneppy Invests"

    def test_resolves_plain_name_via_at_handle(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id("Kneppy Invests")
        assert channel_id == "UCabc123"

    def test_passthrough_raw_channel_id(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id("UCabc123")
        assert channel_id == "UCabc123"

    def test_resolves_channel_url(self):
        info = self._mock_ydl("UCabc123", "Kneppy Invests")
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = info
            channel_id, name = resolve_channel_id(
                "https://www.youtube.com/@KneppyInvests"
            )
        assert channel_id == "UCabc123"

    def test_raises_on_missing_channel_id(self):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.return_value = {"uploader": "Someone"}
            import pytest
            with pytest.raises(RuntimeError, match="could not resolve channel_id"):
                resolve_channel_id("some channel")

    def test_raises_runtime_error_on_yt_dlp_failure(self):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            instance = MockYDL.return_value.__enter__.return_value
            instance.extract_info.side_effect = Exception("network error")
            import pytest
            with pytest.raises(RuntimeError, match="channel lookup failed"):
                resolve_channel_id("Kneppy Invests")
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/backend
python -m pytest tests/test_youtube_transcript_fetcher.py::TestResolveChannelId -v 2>&1 | tail -20
```

Expected: `ImportError: cannot import name 'resolve_channel_id'`

- [ ] **Step 3: Implement `resolve_channel_id`**

Open `financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py` and add after the existing imports/helpers (before `YoutubeVideo`):

```python
def _slugify_as_handle(name: str) -> str:
    """Convert 'Kneppy Invests' → 'KneppyInvests' for @handle attempt."""
    return re.sub(r"[^A-Za-z0-9_]", "", name.title().replace(" ", ""))


def resolve_channel_id(name_or_url: str) -> tuple[str, str]:
    """Resolve a channel name, @handle, URL, or raw ID to (channel_id, canonical_name).

    Tries in order:
    1. If input starts with 'UC' (raw channel ID) → validate via yt-dlp
    2. If input is a URL or @handle → pass directly to yt-dlp
    3. Plain name → try https://www.youtube.com/@{slugified} via yt-dlp

    Raises RuntimeError if channel_id cannot be resolved.
    """
    import re as _re
    raw = str(name_or_url or "").strip()
    if not raw:
        raise ValueError("channel name or URL is required")

    # Build the lookup URL
    if raw.startswith("http://") or raw.startswith("https://"):
        lookup_url = raw
    elif raw.startswith("@"):
        lookup_url = f"https://www.youtube.com/{raw}/videos"
    elif _re.match(r"^UC[A-Za-z0-9_-]{10,}$", raw):
        lookup_url = f"https://www.youtube.com/channel/{raw}/videos"
    else:
        handle = _slugify_as_handle(raw)
        lookup_url = f"https://www.youtube.com/@{handle}/videos"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlist_items": "1",
    }
    try:
        import yt_dlp  # type: ignore
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(lookup_url, download=False)
    except Exception as exc:
        raise RuntimeError(f"channel lookup failed for {raw!r}: {exc}") from exc

    channel_id = str((info or {}).get("channel_id") or "").strip()
    if not channel_id:
        raise RuntimeError(
            f"could not resolve channel_id from {raw!r} — "
            "try providing a YouTube channel URL or @handle instead"
        )
    canonical_name = str(
        (info or {}).get("channel")
        or (info or {}).get("uploader")
        or raw
    ).strip()
    return channel_id, canonical_name
```

Also add `import re` at the top of the file if not already present (check first).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/backend
python -m pytest tests/test_youtube_transcript_fetcher.py::TestResolveChannelId -v 2>&1 | tail -20
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py \
        financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py
git commit -m "feat(youtube): add resolve_channel_id() for name/handle/URL lookup via yt-dlp"
```

---

## Task 2: Backend endpoint `POST /api/commentary/channels`

**Files:**
- Modify: `financial-engine_v2/backend/app/api/commentary.py`
- Create: `financial-engine_v2/backend/tests/test_commentary_channel_endpoint.py`

- [ ] **Step 1: Write failing tests**

Create `financial-engine_v2/backend/tests/test_commentary_channel_endpoint.py`:

```python
"""Tests for POST /api/commentary/channels endpoint."""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


def _make_client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=True)


def _auth_headers():
    import os
    key = os.environ.get("LOCAL_API_KEY", "test-key")
    return {"X-API-Key": key}


class TestAddChannelEndpoint:
    def test_add_new_channel_by_channel_id(self):
        client = _make_client()
        fake_registry_channels = []

        with (
            patch(
                "app.api.commentary.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.api.commentary.ChannelRegistry") as MockReg,
        ):
            instance = MockReg.return_value
            instance.channels.return_value = fake_registry_channels
            instance.save.return_value = None

            resp = client.post(
                "/api/commentary/channels",
                json={"name_or_id": "Kneppy Invests", "credibility_weight": 0.6},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["channel_id"] == "UCabc123"
        assert body["name"] == "Kneppy Invests"
        assert body["enabled"] is True
        assert body["already_existed"] is False

    def test_add_already_existing_channel_returns_already_existed(self):
        from app.services.channel_registry import ChannelConfig
        client = _make_client()
        existing = [ChannelConfig(name="Kneppy Invests", channel_id="UCabc123")]

        with (
            patch(
                "app.api.commentary.resolve_channel_id",
                return_value=("UCabc123", "Kneppy Invests"),
            ),
            patch("app.api.commentary.ChannelRegistry") as MockReg,
        ):
            instance = MockReg.return_value
            instance.channels.return_value = existing
            instance.save.return_value = None

            resp = client.post(
                "/api/commentary/channels",
                json={"name_or_id": "UCabc123"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        assert resp.json()["already_existed"] is True

    def test_missing_name_returns_422(self):
        client = _make_client()
        resp = client.post(
            "/api/commentary/channels",
            json={},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_resolve_failure_returns_502(self):
        client = _make_client()
        with patch(
            "app.api.commentary.resolve_channel_id",
            side_effect=RuntimeError("channel lookup failed"),
        ):
            resp = client.post(
                "/api/commentary/channels",
                json={"name_or_id": "nonexistent xyz channel 99999"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 502

    def test_list_channels(self):
        from app.services.channel_registry import ChannelConfig
        client = _make_client()
        channels = [
            ChannelConfig(name="Kneppy Invests", channel_id="UCabc123", enabled=True),
            ChannelConfig(name="Other Channel", channel_id="UCdef456", enabled=False),
        ]
        with patch("app.api.commentary.ChannelRegistry") as MockReg:
            MockReg.return_value.channels.return_value = channels
            resp = client.get("/api/commentary/channels", headers=_auth_headers())

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["channels"]) == 2
        assert body["channels"][0]["channel_id"] == "UCabc123"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/backend
python -m pytest tests/test_commentary_channel_endpoint.py -v 2>&1 | tail -20
```

Expected: `404 Not Found` or route-not-found errors.

- [ ] **Step 3: Implement the endpoint in commentary.py**

Open `financial-engine_v2/backend/app/api/commentary.py`.

Add this import near the top with the other service imports:

```python
from app.services.youtube_transcript_fetcher import resolve_channel_id
```

Add these models and routes after the existing `IngestUrlRequest` model section:

```python
class AddChannelRequest(BaseModel):
    name_or_id: str
    credibility_weight: float = 0.55
    enabled: bool = True


@router.post(
    "/channels",
    dependencies=[Depends(require_api_key)],
)
def add_watched_channel(body: AddChannelRequest) -> dict[str, Any]:
    name_or_id = str(body.name_or_id or "").strip()
    if not name_or_id:
        raise HTTPException(status_code=422, detail="name_or_id is required")

    try:
        channel_id, canonical_name = resolve_channel_id(name_or_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    registry = ChannelRegistry()
    existing = registry.channels()
    already_existed = any(c.channel_id == channel_id for c in existing)

    if not already_existed:
        new_channel = ChannelConfig(
            name=canonical_name,
            channel_id=channel_id,
            credibility_weight=float(body.credibility_weight),
            enabled=body.enabled,
        )
        registry.save([*existing, new_channel])

    return {
        "channel_id": channel_id,
        "name": canonical_name,
        "enabled": body.enabled,
        "credibility_weight": body.credibility_weight,
        "already_existed": already_existed,
    }


@router.get(
    "/channels",
    dependencies=[Depends(require_api_key)],
)
def list_watched_channels() -> dict[str, Any]:
    registry = ChannelRegistry()
    channels = registry.channels()
    return {
        "channels": [c.to_dict() for c in channels],
        "count": len(channels),
    }
```

Also ensure `ChannelRegistry` and `ChannelConfig` are imported. Add near the top of commentary.py:

```python
from app.services.channel_registry import ChannelConfig, ChannelRegistry
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/backend
python -m pytest tests/test_commentary_channel_endpoint.py -v 2>&1 | tail -20
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/backend/app/api/commentary.py \
        financial-engine_v2/backend/tests/test_commentary_channel_endpoint.py
git commit -m "feat(commentary): add POST/GET /api/commentary/channels endpoints"
```

---

## Task 3: `BackendApiClient.add_watched_channel()` and `list_watched_channels()`

**Files:**
- Modify: `financial-engine_v2/cockpit/integrations/backend_api.py`

No new test file — this file's integration is covered by endpoint tests in Task 2 and tool tests in Task 5.

- [ ] **Step 1: Add methods to BackendApiClient**

Open `financial-engine_v2/cockpit/integrations/backend_api.py`.

Append before `_normalize_base_url`:

```python
def add_watched_channel(
    self,
    name_or_id: str,
    *,
    credibility_weight: float = 0.55,
    enabled: bool = True,
    timeout: float = 30.0,
) -> dict[str, Any]:
    url = f"{self.base_url}/api/commentary/channels"
    headers: dict[str, str] = {}
    if self.api_key:
        headers["X-API-Key"] = self.api_key
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.post(
            url,
            json={
                "name_or_id": name_or_id,
                "credibility_weight": credibility_weight,
                "enabled": enabled,
            },
            headers=headers,
        )
        response.raise_for_status()
        return response.json() if response.content else {}

def list_watched_channels(self, *, timeout: float = 10.0) -> dict[str, Any]:
    url = f"{self.base_url}/api/commentary/channels"
    headers: dict[str, str] = {}
    if self.api_key:
        headers["X-API-Key"] = self.api_key
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.json() if response.content else {"channels": [], "count": 0}
```

- [ ] **Step 2: Verify no import errors**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -c "from cockpit.integrations.backend_api import BackendApiClient; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add financial-engine_v2/cockpit/integrations/backend_api.py
git commit -m "feat(backend-client): add add_watched_channel() and list_watched_channels()"
```

---

## Task 4: Tool definition `watch_youtube_channel`

**Files:**
- Modify: `financial-engine_v2/cockpit/core/tool_definitions.py`

- [ ] **Step 1: Add tool definition**

Open `financial-engine_v2/cockpit/core/tool_definitions.py`.

Find the end of the `TOOL_DEFINITIONS` list (just before `MUTATING_TOOL_NAMES`). Add the new entry:

```python
    {
        "name": "watch_youtube_channel",
        "description": (
            "Add a YouTube channel to the watch list so its transcripts are "
            "automatically fetched and staged for ingestion. "
            "Accepts a channel name (e.g. 'Kneppy Invests'), a @handle "
            "(e.g. '@KneppyInvests'), a channel URL, or a raw UC... channel ID. "
            "Returns the resolved channel_id, canonical name, and whether it "
            "was already being watched."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "channel_name": {
                    "type": "string",
                    "description": (
                        "Channel name, @handle, URL, or channel ID. "
                        "Examples: 'Kneppy Invests', '@KneppyInvests', "
                        "'https://youtube.com/@KneppyInvests', 'UCabc123'"
                    ),
                },
                "credibility_weight": {
                    "type": "number",
                    "description": (
                        "How much to trust this source (0.0–1.0). "
                        "Default 0.55 is standard for YouTube commentary."
                    ),
                    "default": 0.55,
                },
            },
            "required": ["channel_name"],
        },
        "mutating": False,
    },
```

- [ ] **Step 2: Verify it's importable and `watch_youtube_channel` is not in MUTATING_TOOL_NAMES**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -c "
from cockpit.core.tool_definitions import TOOL_DEFINITIONS, MUTATING_TOOL_NAMES
names = [t['name'] for t in TOOL_DEFINITIONS]
assert 'watch_youtube_channel' in names, 'tool not found'
assert 'watch_youtube_channel' not in MUTATING_TOOL_NAMES, 'should not be mutating'
print('ok — tool count:', len(names))
"
```

Expected: `ok — tool count: <N+1>`

- [ ] **Step 3: Commit**

```bash
git add financial-engine_v2/cockpit/core/tool_definitions.py
git commit -m "feat(tool-defs): add watch_youtube_channel tool definition"
```

---

## Task 5: ToolExecutor wiring + tests

**Files:**
- Modify: `financial-engine_v2/cockpit/core/tool_executor.py`
- Create: `financial-engine_v2/cockpit/tests/test_watch_youtube_channel_tool.py`

- [ ] **Step 1: Write failing tests**

Create `financial-engine_v2/cockpit/tests/test_watch_youtube_channel_tool.py`:

```python
"""Tests for watch_youtube_channel tool execution."""
from unittest.mock import MagicMock
import pytest
from cockpit.core.tool_executor import ToolExecutor


def _make_executor(backend_response: dict | None = None, raises: Exception | None = None):
    router = MagicMock()
    router.backend_api_client = MagicMock()
    if raises:
        router.backend_api_client.add_watched_channel.side_effect = raises
    else:
        router.backend_api_client.add_watched_channel.return_value = (
            backend_response
            or {
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "enabled": True,
                "credibility_weight": 0.55,
                "already_existed": False,
            }
        )
    action_registry = MagicMock()
    return ToolExecutor(tool_router=router, action_registry=action_registry)


class TestWatchYoutubeChannelTool:
    def test_successful_add(self):
        executor = _make_executor()
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        assert result["ok"] is True
        assert result["channel_id"] == "UCabc123"
        assert result["name"] == "Kneppy Invests"
        assert result["already_existed"] is False

    def test_with_credibility_weight(self):
        executor = _make_executor()
        executor.execute(
            "watch_youtube_channel",
            {"channel_name": "@KneppyInvests", "credibility_weight": 0.7},
        )
        executor._router.backend_api_client.add_watched_channel.assert_called_once_with(
            "@KneppyInvests", credibility_weight=0.7
        )

    def test_missing_channel_name_returns_error(self):
        executor = _make_executor()
        result = executor.execute("watch_youtube_channel", {})
        assert result["ok"] is False
        assert "channel_name" in result["error"]

    def test_backend_unavailable_returns_error(self):
        router = MagicMock()
        router.backend_api_client = None
        executor = ToolExecutor(tool_router=router, action_registry=MagicMock())
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        assert result["ok"] is False
        assert "backend" in result["error"].lower()

    def test_backend_api_error_returns_error(self):
        executor = _make_executor(raises=RuntimeError("channel lookup failed"))
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "nonexistent xyz 99999"}
        )
        assert result["ok"] is False
        assert "channel lookup failed" in result["error"]

    def test_already_existed_true(self):
        executor = _make_executor(
            backend_response={
                "channel_id": "UCabc123",
                "name": "Kneppy Invests",
                "enabled": True,
                "credibility_weight": 0.55,
                "already_existed": True,
            }
        )
        result = executor.execute(
            "watch_youtube_channel", {"channel_name": "Kneppy Invests"}
        )
        assert result["ok"] is True
        assert result["already_existed"] is True
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -m pytest cockpit/tests/test_watch_youtube_channel_tool.py -v 2>&1 | tail -20
```

Expected: `KeyError: 'watch_youtube_channel'` (tool not in dispatch table yet).

- [ ] **Step 3: Implement `_exec_watch_youtube_channel` in tool_executor.py**

Open `financial-engine_v2/cockpit/core/tool_executor.py`.

Add the handler method to the `ToolExecutor` class (add near the end of the read-only handler methods, before `_READ_ONLY_DISPATCH`):

```python
def _exec_watch_youtube_channel(self, args: dict[str, Any]) -> dict[str, Any]:
    channel_name = str(args.get("channel_name", "")).strip()
    if not channel_name:
        return {"ok": False, "error": "channel_name is required"}
    client = self._router.backend_api_client
    if client is None:
        return {"ok": False, "error": "backend API client not configured"}
    credibility_weight = float(args.get("credibility_weight", 0.55))
    try:
        result = client.add_watched_channel(
            channel_name, credibility_weight=credibility_weight
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, **result}
```

Add to `_READ_ONLY_DISPATCH` dict:

```python
"watch_youtube_channel": _exec_watch_youtube_channel,
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -m pytest cockpit/tests/test_watch_youtube_channel_tool.py -v 2>&1 | tail -20
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/cockpit/core/tool_executor.py \
        financial-engine_v2/cockpit/tests/test_watch_youtube_channel_tool.py
git commit -m "feat(tool-executor): add watch_youtube_channel read-only tool dispatch"
```

---

## Task 6: CommandRouter regex for imperative phrases

**Files:**
- Modify: `financial-engine_v2/cockpit/core/command_router.py`

Adds a regex so "watch youtube videos from X", "monitor channel X", "add channel X" etc. bypass the LLM and go straight to the tool — faster and more reliable than waiting for the model to recognise the intent.

- [ ] **Step 1: Write failing test**

Open `financial-engine_v2/cockpit/core/command_router.py` test file (check if it exists):

```bash
ls /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/cockpit/tests/test_command_router.py 2>/dev/null || echo "missing"
```

If it exists, add to it. If missing, create it:

```python
"""Tests for command_router watch_youtube_channel patterns."""
from cockpit.core.command_router import route_command


class TestWatchYoutubeChannelCommandRoute:
    def test_watch_youtube_from(self):
        r = route_command("watch youtube videos from Kneppy Invests")
        assert r.matched is True
        assert r.tool == "watch_youtube_channel"
        assert r.arguments["channel_name"] == "Kneppy Invests"

    def test_monitor_channel(self):
        r = route_command("monitor channel Kneppy Invests")
        assert r.matched is True
        assert r.tool == "watch_youtube_channel"
        assert r.arguments["channel_name"] == "Kneppy Invests"

    def test_add_youtube_channel(self):
        r = route_command("add youtube channel @KneppyInvests")
        assert r.matched is True
        assert r.arguments["channel_name"] == "@KneppyInvests"

    def test_subscribe_to(self):
        r = route_command("subscribe to KneppyInvests")
        assert r.matched is True
        assert r.arguments["channel_name"] == "KneppyInvests"

    def test_follow_channel(self):
        r = route_command("follow channel https://youtube.com/@KneppyInvests")
        assert r.matched is True
        assert r.arguments["channel_name"] == "https://youtube.com/@KneppyInvests"

    def test_unrelated_does_not_match(self):
        r = route_command("what do you think about BHP")
        assert r.matched is False

    def test_ingest_ticker_still_works(self):
        r = route_command("ingest BHP news")
        assert r.matched is True
        assert r.tool == "run_news_ingest"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -m pytest cockpit/tests/test_command_router.py::TestWatchYoutubeChannelCommandRoute -v 2>&1 | tail -20
```

Expected: All `TestWatchYoutubeChannelCommandRoute` tests fail with `assert r.matched is False`.

- [ ] **Step 3: Add regex and route to command_router.py**

Open `financial-engine_v2/cockpit/core/command_router.py`.

Add near the other regex constants:

```python
_WATCH_CHANNEL_RE = re.compile(
    r"""
    ^\s*
    (?:
        watch\s+(?:youtube\s+)?(?:videos?\s+from\s+|channel\s+)?  # watch [youtube] [videos from | channel]
      | monitor\s+(?:youtube\s+)?(?:channel\s+)?                  # monitor [youtube] [channel]
      | add\s+(?:youtube\s+)?channel\s+                           # add [youtube] channel
      | subscribe\s+to\s+                                         # subscribe to
      | follow\s+(?:youtube\s+)?(?:channel\s+)?                   # follow [youtube] [channel]
    )
    (.+)$
    """,
    re.IGNORECASE | re.VERBOSE,
)
```

Add the route case inside `route_command`, before the final `return CommandRoute(matched=False)`:

```python
# watch/monitor/add/subscribe/follow youtube channel
m = _WATCH_CHANNEL_RE.match(text)
if m:
    channel_name = m.group(1).strip()
    if channel_name:
        return CommandRoute(
            matched=True,
            action_type=None,
            tool="watch_youtube_channel",
            arguments={"channel_name": channel_name},
            explanation=f"Add YouTube channel {channel_name!r} to the watch list.",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -m pytest cockpit/tests/test_command_router.py::TestWatchYoutubeChannelCommandRoute -v 2>&1 | tail -20
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Verify existing command_router tests still pass**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -m pytest cockpit/tests/test_command_router.py -v 2>&1 | tail -20
```

Expected: ALL pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/core/command_router.py \
        financial-engine_v2/cockpit/tests/test_command_router.py
git commit -m "feat(command-router): add watch_youtube_channel intent routing for natural language"
```

---

## Task 7: Full integration smoke test

Verifies the end-to-end path works with the running backend.

- [ ] **Step 1: Run all new tests together**

```bash
cd /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2
python -m pytest \
  backend/tests/test_youtube_transcript_fetcher.py::TestResolveChannelId \
  backend/tests/test_commentary_channel_endpoint.py \
  cockpit/tests/test_watch_youtube_channel_tool.py \
  cockpit/tests/test_command_router.py::TestWatchYoutubeChannelCommandRoute \
  -v 2>&1 | tail -30
```

Expected: All tests PASS, 0 failures.

- [ ] **Step 2: Lint**

```bash
cd /mnt/sdb2/home/l4nd0/tenn
python -m ruff check \
  financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py \
  financial-engine_v2/backend/app/api/commentary.py \
  financial-engine_v2/cockpit/integrations/backend_api.py \
  financial-engine_v2/cockpit/core/tool_definitions.py \
  financial-engine_v2/cockpit/core/tool_executor.py \
  financial-engine_v2/cockpit/core/command_router.py
```

Expected: No errors.

- [ ] **Step 3: Manual API smoke test (requires running backend)**

```bash
curl -sS -X POST http://127.0.0.1:8000/api/commentary/channels \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(cat ~/.tenn/local_api_key 2>/dev/null || echo '')" \
  -d '{"name_or_id": "@mkbhd", "credibility_weight": 0.55}' | python -m json.tool
```

Expected response shape:
```json
{
  "channel_id": "UCBcRF18a7Qf58cMAttxpOtA",
  "name": "Marques Brownlee",
  "enabled": true,
  "credibility_weight": 0.55,
  "already_existed": false
}
```

- [ ] **Step 4: Verify channel appears in registry**

```bash
curl -sS http://127.0.0.1:8000/api/commentary/channels \
  -H "X-API-Key: $(cat ~/.tenn/local_api_key 2>/dev/null || echo '')" | python -m json.tool
```

Expected: `channels` array includes the newly added channel.

- [ ] **Step 5: Final milestone commit**

```bash
git add -p  # review any remaining unstaged changes
git commit -m "milestone(youtube-channel-nlp): watch channel via natural language end-to-end

Working: User can say 'watch youtube videos from X' in Tenn chat and have
the channel registered in channel_registry.json automatically.
Tested: Unit tests for resolver, endpoint, tool executor, command router all pass."
```

---

## What the user experience looks like after this

```
User: watch youtube videos from Kneppy Invests

CommandRouter matches → watch_youtube_channel{channel_name: "Kneppy Invests"}
  → ToolExecutor._exec_watch_youtube_channel()
  → BackendApiClient.add_watched_channel("Kneppy Invests")
  → POST /api/commentary/channels
  → resolve_channel_id("Kneppy Invests") via yt-dlp → (UC_xyz, "Kneppy Invests")
  → ChannelRegistry.save()

Tenn replies: "Added 'Kneppy Invests' (UC_xyz) to the watch list. 
New videos will be ingested automatically on the next daemon cycle."
```

Once the channel is in the registry, `run_transcript_daemon.py` picks it up on the next poll and ingests transcripts automatically.
