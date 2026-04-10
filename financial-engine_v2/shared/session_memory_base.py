from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

_MAX_CONTENT_CHARS = 400

_FALLBACK_PATHS = (
    Path("~/.openviking/ov.conf").expanduser(),
    Path("/etc/openviking/ov.conf"),
)


class SessionMemoryClient:
    """Shared OpenViking session memory client.

    Parameterised per component so that cockpit and backend each hold their
    own singleton without sharing global mutable state.

    All methods fail open — session memory is best-effort augmentation and
    callers must not depend on any method succeeding.
    """

    def __init__(
        self,
        component_name: str,
        config_path: Path,
        operator_action: str,
    ) -> None:
        self._component_name = component_name
        self._config_path = config_path
        self._operator_action = operator_action
        self._logger = logging.getLogger(__name__)

        # Initialised lazily on first call to _get_ov().
        self._ov_instance: Any = None
        self._ov_init_attempted: bool = False
        self._ov_init_error: str = ""
        self._status_logged: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_config_path(self) -> Path | None:
        """Return the config file path that should be used, or None."""
        env_path = os.environ.get("OPENVIKING_CONFIG_FILE")
        if env_path:
            p = Path(env_path).expanduser()
            return p if p.exists() else None
        if self._config_path.exists():
            return self._config_path
        for fallback in _FALLBACK_PATHS:
            if fallback.exists():
                return fallback
        return None

    def _get_ov(self) -> Any | None:
        """Attempt OpenViking init once; capture error.

        Does not log — call log_startup_status() for the one-time message.
        """
        if self._ov_init_attempted:
            return self._ov_instance
        self._ov_init_attempted = True

        config = self._resolve_config_path()
        if config is None:
            self._ov_init_error = "no config file found"
            return None

        # Ensure OpenViking discovers the component-specific config.
        os.environ.setdefault("OPENVIKING_CONFIG_FILE", str(config))

        try:
            from openviking import SyncOpenViking  # type: ignore[import]

            ov = SyncOpenViking()
            ov.initialize()
            self._ov_instance = ov
        except Exception as exc:
            self._ov_init_error = f"{type(exc).__name__}: {exc}"
        return self._ov_instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_startup_status(self) -> None:
        """Emit exactly one startup log per process: enabled or degraded."""
        if self._status_logged:
            return
        self._status_logged = True
        ov = self._get_ov()
        prefix = self._component_name
        if ov is not None:
            config_used = os.environ.get("OPENVIKING_CONFIG_FILE") or str(self._config_path)
            self._logger.info(
                "%s.session_memory: OpenViking enabled (config: %s)",
                prefix,
                config_used,
            )
        elif self._resolve_config_path() is not None:
            self._logger.warning(
                "%s.session_memory: OpenViking init failed — running stateless. Root cause: %s",
                prefix,
                self._ov_init_error,
            )
        else:
            self._logger.warning(
                "%s.session_memory: OpenViking config not found — running stateless. %s",
                prefix,
                self._operator_action,
            )

    def get_relevant_session_context(
        self,
        session_id: str,
        query: str,
        *,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Return up to *limit* structured prior-turn records relevant to *query*.

        Queries the OpenViking vector index.  When no resources are indexed
        (the common case) this will return [].  Use get_recent_turns() as a
        complementary retrieval path that reads messages directly from the
        in-memory JSONL store.

        Returns an empty list on any failure — callers must treat this as
        best-effort augmentation only.
        """
        ov = self._get_ov()
        if not ov:
            return []
        try:
            raw_results = ov.search(query, session_id=session_id, limit=limit)
            items: list[dict[str, Any]] = []
            for r in raw_results or []:
                content: str = ""
                if isinstance(r, dict):
                    content = str(r.get("content") or r.get("text") or "").strip()
                elif isinstance(r, str):
                    content = r.strip()
                if not content:
                    continue
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        items.append(parsed)
                        continue
                except (json.JSONDecodeError, ValueError):
                    pass
                items.append({"text": content[:_MAX_CONTENT_CHARS]})
            return items[:limit]
        except Exception as exc:
            self._logger.warning(
                "%s.session_memory.get_relevant_session_context failed — returning empty context. "
                "%s: %s",
                self._component_name,
                type(exc).__name__,
                exc,
            )
            return []

    def get_recent_turns(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return up to *limit* most-recent turns directly from the session store.

        This bypasses the vector search pipeline and reads the raw in-memory
        message list that OpenViking loads from its JSONL store.  It is the
        correct retrieval path when get_relevant_session_context() returns []
        because no resources have been indexed yet.

        The assistant messages are expected to be JSON-encoded turn payloads
        written by record_turn().  Plain-text assistant messages are returned
        as {"text": <content>}.

        Returns an empty list on any failure.
        """
        ov = self._get_ov()
        if not ov:
            return []
        try:
            # Try the most common session-load APIs across OpenViking versions.
            session_obj = None
            if hasattr(ov, "get_session"):
                session_obj = ov.get_session(session_id)
            elif hasattr(ov, "session"):
                raw = ov.session(session_id)
                session_obj = raw.load() if hasattr(raw, "load") else raw

            if session_obj is None:
                return []

            # Retrieve the message list.  Different versions use different
            # attribute names; try them in order.
            messages: list[Any] = []
            for attr in ("messages", "_messages", "history"):
                candidate = getattr(session_obj, attr, None)
                if candidate is not None:
                    messages = list(candidate)
                    break

            # Keep only assistant messages (the ones written by record_turn).
            assistant_msgs = [
                m for m in messages if _message_role(m) == "assistant"
            ]
            recent = assistant_msgs[-limit:]

            items: list[dict[str, Any]] = []
            for msg in recent:
                content = _message_content(msg)
                if not content:
                    continue
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        items.append(parsed)
                        continue
                except (json.JSONDecodeError, ValueError):
                    pass
                items.append({"text": content[:_MAX_CONTENT_CHARS]})
            return items
        except Exception as exc:
            self._logger.warning(
                "%s.session_memory.get_recent_turns failed — returning empty list. %s: %s",
                self._component_name,
                type(exc).__name__,
                exc,
            )
            return []

    def record_turn(self, session_id: str, payload: dict[str, Any]) -> None:
        """Persist a structured turn record to the session.

        Fails open — callers must not depend on this succeeding.
        """
        ov = self._get_ov()
        if not ov:
            return
        try:
            query = str(payload.get("query") or "").strip()
            if query:
                ov.add_message(session_id, "user", content=query)
            answer_json = json.dumps(payload, ensure_ascii=False, default=str)
            ov.add_message(session_id, "assistant", content=answer_json)
        except Exception as exc:
            self._logger.warning(
                "%s.session_memory.record_turn failed — turn not persisted. %s: %s",
                self._component_name,
                type(exc).__name__,
                exc,
            )


# ------------------------------------------------------------------
# Internal helpers for get_recent_turns
# ------------------------------------------------------------------


def _message_role(msg: Any) -> str:
    """Extract the role string from a message object or dict."""
    if isinstance(msg, dict):
        return str(msg.get("role") or "")
    return str(getattr(msg, "role", ""))


def _message_content(msg: Any) -> str:
    """Extract the content string from a message object or dict."""
    if isinstance(msg, dict):
        return str(msg.get("content") or msg.get("text") or "").strip()
    return str(getattr(msg, "content", "") or "").strip()
