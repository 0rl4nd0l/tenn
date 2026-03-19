from __future__ import annotations

import json
import re
from hashlib import sha1
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS_ROOT = REPO_ROOT / "reports"
PROPOSALS_LOG_PATH = REPORTS_ROOT / "strategy_proposals.jsonl"
ACTIVE_STATE_PATH = REPORTS_ROOT / "strategy_state.json"

_INCREASE_PATTERN = re.compile(
    r"^\s*(increase|raise|boost)\s+weight\s+of\s+(?P<target>.+?)\s*$",
    flags=re.IGNORECASE,
)
_DECREASE_PATTERN = re.compile(
    r"^\s*(decrease|lower|reduce)\s+weight\s+of\s+(?P<target>.+?)\s*$",
    flags=re.IGNORECASE,
)
_DECAY_PATTERN = re.compile(
    r"^\s*(increase|decrease|raise|lower|reduce)\s+decay(?:\s+rate)?\s+for\s+(?P<target>.+?)\s*$",
    flags=re.IGNORECASE,
)
_FILTER_PATTERN = re.compile(
    r"^\s*(exclude|include|filter)\s+(?P<target>.+?)\s*$",
    flags=re.IGNORECASE,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_proposal_id(user_input: str) -> str:
    seed = f"{_utc_now_iso()}::{str(user_input or '').strip()}"
    return f"proposal_{sha1(seed.encode('utf-8')).hexdigest()[:12]}"


def _load_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else dict(default)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_proposal_events(path: Path | None = None) -> list[dict[str, Any]]:
    resolved_path = path or PROPOSALS_LOG_PATH
    if not resolved_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with resolved_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _proposal_snapshot(proposal_id: str, *, path: Path | None = None) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in _load_proposal_events(path):
        if str(row.get("proposal_id") or "") == proposal_id:
            latest = dict(row)
    return latest


def _normalize_target(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _impact_for_change(change_type: str, action: str) -> str:
    if change_type == "source_weight":
        return "higher ranking in retrieval" if action == "increase" else "lower ranking in retrieval"
    if change_type == "decay_rate":
        if action == "increase":
            return "more recent commentary will be weighted more strongly"
        return "older commentary will retain influence longer"
    if change_type == "filter_rule":
        return "matching sources will be filtered during chat retrieval"
    return "chat-layer strategy behavior will change after apply"


def _build_strategy_change(user_input: str) -> dict[str, Any]:
    text = str(user_input or "").strip()
    if not text:
        raise ValueError("user_input is required")

    match = _INCREASE_PATTERN.match(text)
    if match:
        target = _normalize_target(match.group("target"))
        return {
            "change_type": "source_weight",
            "action": "increase",
            "change": "increase credibility_weight",
            "target": target,
            "parameters": {"delta": 0.1},
            "impact": _impact_for_change("source_weight", "increase"),
        }

    match = _DECREASE_PATTERN.match(text)
    if match:
        target = _normalize_target(match.group("target"))
        return {
            "change_type": "source_weight",
            "action": "decrease",
            "change": "decrease credibility_weight",
            "target": target,
            "parameters": {"delta": -0.1},
            "impact": _impact_for_change("source_weight", "decrease"),
        }

    match = _DECAY_PATTERN.match(text)
    if match:
        action = str(match.group(1) or "").strip().lower()
        normalized_action = "increase" if action in {"increase", "raise"} else "decrease"
        target = _normalize_target(match.group("target"))
        return {
            "change_type": "decay_rate",
            "action": normalized_action,
            "change": f"{normalized_action} decay rate",
            "target": target,
            "parameters": {"multiplier": 0.8 if normalized_action == "increase" else 1.25},
            "impact": _impact_for_change("decay_rate", normalized_action),
        }

    match = _FILTER_PATTERN.match(text)
    if match:
        action = str(match.group(1) or "").strip().lower()
        target = _normalize_target(match.group("target"))
        include = action == "include"
        return {
            "change_type": "filter_rule",
            "action": "include" if include else "exclude",
            "change": "allow source during chat retrieval" if include else "exclude source during chat retrieval",
            "target": target,
            "parameters": {"mode": "allow" if include else "deny"},
            "impact": _impact_for_change("filter_rule", action),
        }

    raise ValueError(
        "Unsupported strategy request. Try changing a source weight, decay rate, or filter rule."
    )


def _load_active_state(path: Path | None = None) -> dict[str, Any]:
    return _load_json(
        path or ACTIVE_STATE_PATH,
        default={
            "source_weights": {},
            "decay_rules": {},
            "filter_rules": {"allow": [], "deny": []},
            "applied_proposals": [],
            "updated_at": "",
        },
    )


def _clamp_weight(value: float) -> float:
    return max(0.1, min(3.0, round(float(value), 4)))


def _apply_to_state(state: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    updated = dict(state)
    updated.setdefault("source_weights", {})
    updated.setdefault("decay_rules", {})
    updated.setdefault("filter_rules", {"allow": [], "deny": []})
    updated.setdefault("applied_proposals", [])

    target = str(proposal.get("target") or "").strip()
    change_type = str(proposal.get("change_type") or "").strip()
    action = str(proposal.get("action") or "").strip()
    parameters = dict(proposal.get("parameters") or {})

    if change_type == "source_weight":
        source_weights = dict(updated.get("source_weights") or {})
        current = float(source_weights.get(target, 1.0))
        source_weights[target] = _clamp_weight(current + float(parameters.get("delta") or 0.0))
        updated["source_weights"] = source_weights
    elif change_type == "decay_rate":
        decay_rules = dict(updated.get("decay_rules") or {})
        current = float(decay_rules.get(target, 1.0))
        decay_rules[target] = round(
            max(0.1, min(5.0, current * float(parameters.get("multiplier") or 1.0))),
            4,
        )
        updated["decay_rules"] = decay_rules
    elif change_type == "filter_rule":
        filter_rules = dict(updated.get("filter_rules") or {})
        allow = [str(item) for item in list(filter_rules.get("allow") or []) if str(item).strip()]
        deny = [str(item) for item in list(filter_rules.get("deny") or []) if str(item).strip()]
        allow = [item for item in allow if item != target]
        deny = [item for item in deny if item != target]
        if action == "include":
            allow.append(target)
        else:
            deny.append(target)
        filter_rules["allow"] = sorted(dict.fromkeys(allow))
        filter_rules["deny"] = sorted(dict.fromkeys(deny))
        updated["filter_rules"] = filter_rules
    else:
        raise ValueError(f"Unsupported proposal change_type: {change_type}")

    applied = [str(item) for item in list(updated.get("applied_proposals") or []) if str(item).strip()]
    proposal_id = str(proposal.get("proposal_id") or "").strip()
    if proposal_id and proposal_id not in applied:
        applied.append(proposal_id)
    updated["applied_proposals"] = applied
    updated["updated_at"] = _utc_now_iso()
    return updated


def get_active_strategy_state() -> dict[str, Any]:
    return _load_active_state()


def propose_change(user_input: str) -> dict[str, Any]:
    proposal = _build_strategy_change(user_input)
    proposal_id = _build_proposal_id(user_input)
    payload = {
        "proposal_id": proposal_id,
        **proposal,
        "status": "proposed",
        "user_input": str(user_input or "").strip(),
        "created_at": _utc_now_iso(),
        "confirmation_required": True,
        "message": "Do you want to confirm this change before applying it?",
    }
    _append_jsonl(PROPOSALS_LOG_PATH, payload)
    return payload


def confirm_change(proposal_id: str) -> dict[str, Any]:
    proposal = _proposal_snapshot(proposal_id)
    if proposal is None:
        raise ValueError(f"Unknown proposal_id: {proposal_id}")
    if str(proposal.get("status") or "") == "applied":
        raise ValueError(f"Proposal already applied: {proposal_id}")

    confirmed = {
        **proposal,
        "status": "confirmed",
        "confirmed_at": _utc_now_iso(),
        "message": "Confirmation recorded. Call apply to make this chat-layer strategy change active.",
    }
    _append_jsonl(PROPOSALS_LOG_PATH, confirmed)
    return confirmed


def apply_change(proposal_id: str) -> dict[str, Any]:
    proposal = _proposal_snapshot(proposal_id)
    if proposal is None:
        raise ValueError(f"Unknown proposal_id: {proposal_id}")
    if str(proposal.get("status") or "") != "confirmed":
        raise ValueError(f"Proposal must be confirmed before apply: {proposal_id}")

    updated_state = _apply_to_state(_load_active_state(), proposal)
    _write_json(ACTIVE_STATE_PATH, updated_state)

    applied = {
        **proposal,
        "status": "applied",
        "applied_at": _utc_now_iso(),
        "message": "Strategy change applied to the chat layer.",
        "active_state_path": str(ACTIVE_STATE_PATH),
    }
    _append_jsonl(PROPOSALS_LOG_PATH, applied)
    return applied
