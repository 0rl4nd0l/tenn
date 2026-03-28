from __future__ import annotations

from typing import Any

from cockpit.core.action_preview import normalize_action_preview


_CONFIRM_ALIASES = {"y", "yes", "ok", "okay"}
_CANCEL_ALIASES = {"n", "no", "cancel"}


def build_pending_action_payload(preview: dict[str, Any], original_message: str) -> dict[str, Any]:
    payload = normalize_action_preview(preview)
    if payload["action_id"] == "__access_request__":
        resume_message = str(original_message or "").strip()
        if resume_message:
            payload["resume_message"] = resume_message
    return payload


def access_scope_is_enabled(scope: str, state: dict[str, Any]) -> bool:
    normalized = str(scope or "").strip().lower()
    if normalized == "web":
        return bool(state.get("web_enabled", False))
    if normalized == "rag":
        return bool(state.get("rag_enabled", False))
    if normalized == "dbdiag":
        return bool(state.get("db_diagnostic_query_enabled", False))
    return False


def resolve_confirm_resume_message(action: dict[str, Any], state: dict[str, Any]) -> str | None:
    if action.get("action_id") != "__access_request__":
        return None
    args = dict(action.get("args") or {})
    if not bool(args.get("enable", True)):
        return None
    scope = str(args.get("scope") or "").strip().lower()
    if not scope or not access_scope_is_enabled(scope, state):
        return None
    resume_message = str(action.get("resume_message") or "").strip()
    return resume_message or None


def resolve_pending_action_alias(message: str, has_pending_action: bool) -> str:
    text = str(message or "").strip()
    if not has_pending_action:
        return text
    lowered = text.lower()
    if lowered in _CONFIRM_ALIASES:
        return "/confirm"
    if lowered in _CANCEL_ALIASES:
        return "/cancel"
    return text
