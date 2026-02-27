from __future__ import annotations

from typing import Any


def access_scope_is_enabled(scope: str, state: dict[str, Any]) -> bool:
    key = str(scope or "").strip().lower()
    if key == "web":
        return bool(state.get("web_enabled"))
    if key == "rag":
        return bool(state.get("rag_enabled"))
    if key == "dbdiag":
        return bool(state.get("db_diagnostic_query_enabled"))
    return False


def build_pending_action_payload(action_preview: dict[str, Any], message: str) -> dict[str, Any]:
    payload = {
        "action_id": action_preview.get("action_id"),
        "args": action_preview.get("args"),
    }
    if str(action_preview.get("action_id") or "").strip() == "__access_request__":
        resume_message = str(message or "").strip()
        if resume_message:
            payload["resume_message"] = resume_message
    return payload


def resolve_confirm_resume_message(
    action: dict[str, Any],
    state_after: dict[str, Any],
) -> str | None:
    action_id = str(action.get("action_id") or "").strip()
    if action_id != "__access_request__":
        return None
    action_args = action.get("args") if isinstance(action.get("args"), dict) else {}
    if not bool(action_args.get("enable", True)):
        return None
    scope = str(action_args.get("scope") or "").strip().lower()
    if not access_scope_is_enabled(scope, state_after):
        return None
    resume_message = str(action.get("resume_message") or "").strip()
    return resume_message or None


def resolve_pending_action_alias(message: str, has_pending_action: bool) -> str:
    text = str(message or "")
    if not has_pending_action:
        return text
    normalized = text.strip().lower()
    if normalized in {"yes", "y", "ok", "okay"}:
        return "/confirm"
    if normalized in {"no", "n", "cancel"}:
        return "/cancel"
    return text
