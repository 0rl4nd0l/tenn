from __future__ import annotations

from typing import Any

from cockpit.core.action_preview import normalize_action_preview


_CONFIRM_ALIASES = {"y", "yes", "ok", "okay"}
_CANCEL_ALIASES = {"n", "no", "cancel"}


def build_pending_action_payload(preview: dict[str, Any], original_message: str) -> dict[str, Any]:
    payload = normalize_action_preview(preview)
    if payload["action_id"] == "__backend_proposal__":
        args = dict(payload.get("args") or {})
        proposal_id = str(args.get("proposal_id") or "").strip()
        resume_message = str(original_message or "").strip()
        if proposal_id.startswith("enable_") and resume_message and "resume_message" not in args:
            args["resume_message"] = resume_message
            payload["args"] = args
    return payload


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
