from __future__ import annotations

from typing import Any


def extract_ticker_from_payload(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None

    def _normalize(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().upper()
        return cleaned or None

    direct = _normalize(payload.get("ticker"))
    if direct:
        return direct

    evidence = payload.get("evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            details = item.get("details") if isinstance(item.get("details"), dict) else {}
            arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
            result = item.get("result") if isinstance(item.get("result"), dict) else {}
            result_arguments = result.get("arguments") if isinstance(result.get("arguments"), dict) else {}
            for candidate in (
                item.get("ticker"),
                details.get("ticker"),
                arguments.get("ticker"),
                result.get("ticker"),
                result_arguments.get("ticker"),
            ):
                normalized = _normalize(candidate)
                if normalized:
                    return normalized

    actions = payload.get("actions_taken")
    if isinstance(actions, list):
        for item in actions:
            if not isinstance(item, dict):
                continue
            args = item.get("args") if isinstance(item.get("args"), dict) else item.get("arguments")
            normalized = _normalize(args.get("ticker") if isinstance(args, dict) else None)
            if normalized:
                return normalized

    action_preview = payload.get("action_preview")
    if isinstance(action_preview, dict):
        args = action_preview.get("args")
        normalized = _normalize(args.get("ticker") if isinstance(args, dict) else None)
        if normalized:
            return normalized

    return None
