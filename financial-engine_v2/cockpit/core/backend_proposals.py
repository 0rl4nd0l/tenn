from __future__ import annotations

from typing import Any


def build_backend_runtime_remediation_request(
    backend_api_client: Any,
    *,
    action_id: str,
    args: dict[str, Any],
    error_message: str,
) -> dict[str, Any] | None:
    if backend_api_client is None or not hasattr(backend_api_client, "capabilities"):
        return None

    lowered = str(error_message or "").strip().lower()
    if "extraction endpoint unreachable" not in lowered and "start llama-server" not in lowered:
        return None

    try:
        capabilities = backend_api_client.capabilities(timeout=5.0)
    except Exception:
        return None
    if not capabilities.get("ok"):
        return None

    payload = capabilities.get("payload") if isinstance(capabilities, dict) else {}
    proposals = payload.get("proposals") if isinstance(payload, dict) else []
    if not isinstance(proposals, list):
        return None

    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        if str(proposal.get("id") or "").strip() != "start_extraction_runtime":
            continue
        return {
            "action_id": "__backend_proposal__",
            "args": {
                "proposal_id": "start_extraction_runtime",
                "resume_action_id": action_id,
                "resume_args": dict(args or {}),
                "error": str(error_message or "").strip(),
            },
        }
    return None
