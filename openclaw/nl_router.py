"""Natural-language router for OpenClaw commands with strict LLM gating."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Final, TypedDict
from urllib.parse import urlparse

ALLOWED_COMMANDS: Final[set[str]] = {
    "run",
    "status",
    "latest",
    "runs",
    "report",
    "gates",
    "start",
    "stop",
    "help",
}
ROUTER_ACTIONS: Final[set[str]] = set(ALLOWED_COMMANDS) | {"task", "unknown"}

_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[a-z0-9]+")
_CODE_FENCE_RE: Final[re.Pattern[str]] = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_LOCAL_OPENAI_HOSTS: Final[set[str]] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "host.docker.internal",
}

# Ordered rules: earlier rules win when phrases overlap.
_RULES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("help", ("what can you do",)),
    ("stop", ("stop daemon", "stop autonomous", "stop autonomous mode")),
    ("start", ("start daemon", "run continuously", "start autonomous mode", "start autonomous")),
    (
        "latest",
        (
            "latest report",
            "show latest report",
            "last run",
            "last report",
            "show the last report",
        ),
    ),
    ("runs", ("list runs", "recent runs", "show runs")),
    ("report", ("show report", "run report", "tail report")),
    (
        "gates",
        (
            "show gates",
            "gates",
            "test results",
            "why did it fail",
            "why failed",
            "gate logs",
        ),
    ),
    (
        "status",
        (
            "system status",
            "what is the system status",
            "what is running",
            "what is the system doing",
        ),
    ),
    (
        "task",
        (
            "analyze",
            "analyse",
            "edit",
            "fix",
            "implement",
            "modify",
            "refactor",
            "debug",
            "write",
            "create",
            "build",
            "update",
        ),
    ),
    ("run", ("run next task", "next task", "execute", "continue")),
)

_MANIFEST_PATH: Final[Path] = Path(__file__).with_name("tenn_operations_manifest.json")

_SYSTEM_TASK_RULES: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    (
        ("daily news ingestion", "run daily news ingestion", "run news ingestion", "news ingestion"),
        "daily_news_ingestion|Run daily news ingestion via script/fetch_daily_news.py, then save and report summary.",
    ),
    (
        ("historical news ingestion", "run historical news ingestion", "run news backfill"),
        "historical_news_ingestion|Run historical news backfill via backfill_news.py, then save and report summary.",
    ),
    (
        ("run announcement ingestion", "daily announcement ingestion", "announcement ingest"),
        "announcement_ingestion|Run daily announcement ingestion action and report results.",
    ),
    (
        ("run pipeline", "run ingestion pipeline", "backfill", "run backfill"),
        "pipeline_run|Trigger an ingestion pipeline run, then report completion status and key outputs.",
    ),
    (
        (
            "news pipeline tests",
            "test news ingestion",
            "run news tests",
            "verify news ingestion",
        ),
        "news_pipeline_tests|Run the relevant news ingestion tests/checks and report pass/fail and artefacts.",
    ),
    (
        ("run full system check", "system health check", "test system"),
        "system_health_check|Run the current health checks and report failures and mitigation steps.",
    ),
)


def _extract_operation(task_text: str) -> str:
    for segment in task_text.split(" | "):
        prefix = "operation="
        if segment.startswith(prefix):
            return segment[len(prefix):].strip()
    return ""


def _legacy_rule_to_schema(raw_rule_text: str) -> str:
    if raw_rule_text.startswith("operation="):
        return raw_rule_text
    if "|" not in raw_rule_text:
        return f"operation=legacy | goal={raw_rule_text}"

    operation_id, _, goal = raw_rule_text.partition("|")
    operation_id = operation_id.strip()
    goal = goal.strip()
    if not goal:
        goal = raw_rule_text.strip()
        operation_id = "legacy"
    return f"operation={operation_id} | goal={goal} | checks=[] | outputs=[] | constraints=[]"


def _normalize(text: str) -> str:
    tokens = _TOKEN_RE.findall(text.lower())
    return " ".join(tokens)


def _normalize_rule(text: str) -> str:
    return _normalize(text)


def _format_task_text_from_manifest(item: dict[str, object]) -> str:
    goal = str(item.get("goal", "")).strip()
    checks = [str(entry).strip() for entry in item.get("checks", []) if str(entry).strip()]
    outputs = [str(entry).strip() for entry in item.get("outputs", []) if str(entry).strip()]
    constraints = [str(entry).strip() for entry in item.get("constraints", []) if str(entry).strip()]
    operation_id = str(item.get("id", "system_operation")).strip() or "system_operation"

    def _join(items: list[str]) -> str:
        return "; ".join(items)

    if not goal:
        goal = "Execute requested system operation and report results."

    return " | ".join(
        (
            f"operation={operation_id}",
            f"goal={goal}",
            f"checks=[{_join(checks)}]",
            f"outputs=[{_join(outputs)}]",
            f"constraints=[{_join(constraints)}]",
        )
    )


def _load_system_task_rules() -> tuple[tuple[tuple[str, ...], str], ...]:
    if not _MANIFEST_PATH.exists():
        return tuple((phrases, _legacy_rule_to_schema(task_text)) for phrases, task_text in _SYSTEM_TASK_RULES)

    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError, ValueError):
        return _SYSTEM_TASK_RULES

    raw_operations = payload.get("operations") if isinstance(payload, dict) else payload
    if not isinstance(raw_operations, list):
        return _SYSTEM_TASK_RULES

    loaded: list[tuple[tuple[str, ...], str]] = []
    for raw_op in raw_operations:
        if not isinstance(raw_op, dict):
            continue
        triggers = raw_op.get("triggers", [])
        if not isinstance(triggers, list):
            continue

        normalized_triggers = tuple(
            _normalize_rule(trigger)
            for trigger in triggers
            if isinstance(trigger, str) and _normalize_rule(trigger)
        )
        if not normalized_triggers:
            continue

        loaded.append((normalized_triggers, _format_task_text_from_manifest(raw_op)))

    return tuple(loaded) if loaded else _SYSTEM_TASK_RULES


_LOADED_SYSTEM_TASK_RULES: Final[tuple[tuple[tuple[str, ...], str], ...]] = _load_system_task_rules()
_KNOWN_SYSTEM_OPERATIONS: Final[set[str]] = {
    _extract_operation(task_text) for _, task_text in _LOADED_SYSTEM_TASK_RULES if task_text.startswith("operation=")
}


def _system_operations_context() -> str:
    if not _LOADED_SYSTEM_TASK_RULES:
        return "- No TENN operation patterns loaded."

    lines = ["TENN action context:"]
    for task_text in (item[1] for item in _LOADED_SYSTEM_TASK_RULES):
        operation = _extract_operation(task_text)
        goal = ""
        for segment in task_text.split(" | "):
            if segment.startswith("goal="):
                goal = segment[len("goal=") :]
                break
        if operation:
            if goal:
                lines.append(f"- {operation}: {goal}")
            else:
                lines.append(f"- {operation}")
    return "\n".join(lines)


def _coerce_task_text(task_text: str) -> str:
    clean = _sanitize_task_text(task_text)
    if not clean:
        return clean

    if clean.startswith("operation="):
        operation_id = _extract_operation(clean)
        if operation_id in _KNOWN_SYSTEM_OPERATIONS or operation_id == "user_task":
            return clean
        if operation_id and operation_id != "user_task":
            return ""
        return clean

    if clean:
        return f"operation=user_task | goal={clean} | checks=[] | outputs=[] | constraints=[safe code path only]"
    return ""


class RouteDecision(TypedDict):
    action: str
    task_text: str | None
    source: str


def _sanitize_task_text(text: str) -> str:
    compact = " ".join(text.split()).strip().replace("|", "/")
    return compact[:240].rstrip()

def _contains_phrase(normalized: str, phrase: str) -> bool:
    # Match whole-token phrases only, avoiding partial-word hits.
    return f" {phrase} " in f" {normalized} "


if any(command not in ROUTER_ACTIONS for command, _ in _RULES):
    raise ValueError("NL router rules include a non-allowed command")


def _decision(action: str, task_text: str | None, source: str) -> RouteDecision:
    safe_action = action if action in ROUTER_ACTIONS else "unknown"
    return {
        "action": safe_action,
        "task_text": task_text if task_text else None,
        "source": source,
    }


def _route_with_rules(normalized: str) -> str:
    for command, phrases in _RULES:
        if any(_contains_phrase(normalized, phrase) for phrase in phrases):
            return command
    return "unknown"


def _route_with_system_tasks(normalized: str) -> str | None:
    for phrases, task_text in _LOADED_SYSTEM_TASK_RULES:
        if any(_contains_phrase(normalized, phrase) for phrase in phrases):
            return task_text
    return None


def _router_prompt(text: str) -> str:
    actions = ", ".join(sorted(ROUTER_ACTIONS))
    return (
        "Classify this OpenClaw user message into one action.\n"
        f"Allowed actions: {actions}.\n"
        "Return strict JSON only with this schema:\n"
        '{"action":"<one allowed action>","task_text":"<short task description or empty>"}\n'
        "Rules:\n"
        "- Use task for coding work requests, implementation asks, or test/refactor asks.\n"
        "- Use unknown for greetings/chitchat/ambiguous requests.\n"
        "- Never output anything except JSON.\n"
        "- Keep task_text concise.\n\n"
        f"{_system_operations_context()}\n\n"
        f"User message: {text}"
    )


def _strip_code_fences(text: str) -> str:
    raw = text.strip()
    if not raw.startswith("```"):
        return raw
    return _CODE_FENCE_RE.sub("", raw).strip()


def _extract_json_payload(text: str) -> dict[str, object]:
    raw = _strip_code_fences(text)
    if raw.startswith("{") and raw.endswith("}"):
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in LLM output.")
    payload = json.loads(raw[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("LLM JSON payload is not an object.")
    return payload


def _timeout_seconds() -> int:
    raw = os.getenv("OPENCLAW_ROUTER_TIMEOUT_SECONDS", "12").strip()
    try:
        return max(2, min(60, int(raw)))
    except ValueError:
        return 12


def _openai_base_url() -> str | None:
    for env_name in ("OPENCLAW_ROUTER_OPENAI_BASE_URL", "OPENAI_BASE_URL"):
        raw = os.getenv(env_name, "").strip()
        if raw:
            return raw.rstrip("/")
    return None


def _is_local_openai_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    host = (parsed.hostname or "").lower()
    return host in _LOCAL_OPENAI_HOSTS


def _openai_api_key(base_url: str | None) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        return api_key
    if _is_local_openai_base_url(base_url):
        # llama.cpp/open-source local endpoints generally ignore API keys.
        return "local-openai-key"
    return ""


def _run_ollama(prompt: str) -> str:
    model = os.getenv("OPENCLAW_ROUTER_OLLAMA_MODEL", "deepseek-coder:6.7b").strip()
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
        timeout=_timeout_seconds(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ollama command failed")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("ollama returned empty output")
    return output


def _run_openai(prompt: str) -> str:
    from openai import OpenAI

    model = os.getenv("OPENCLAW_ROUTER_OPENAI_MODEL", "gpt-4.1-mini").strip()
    base_url = _openai_base_url()
    api_key = _openai_api_key(base_url)
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")

    client_kwargs: dict[str, str] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise RuntimeError("OpenAI returned no choices.")
    message = getattr(choices[0], "message", None)
    output = getattr(message, "content", "")
    if isinstance(output, list):
        output = "".join(str(part.get("text", "")) for part in output if isinstance(part, dict))
    output = str(output).strip()
    if not output:
        raise RuntimeError("OpenAI returned an empty response.")
    return output


def _run_model_prompt(prompt: str) -> str:
    provider = os.getenv("OPENCLAW_ROUTER_PROVIDER", "auto").strip().lower()
    if provider in {"none", "off", "disabled"}:
        raise RuntimeError("LLM router disabled")

    errors: list[str] = []
    if provider in {"auto", "ollama"}:
        try:
            return _run_ollama(prompt)
        except Exception as exc:  # pragma: no cover - depends on local model tooling
            errors.append(f"ollama: {exc}")

    if provider in {"auto", "openai", "llamacpp", "llama.cpp"}:
        try:
            return _run_openai(prompt)
        except Exception as exc:  # pragma: no cover - depends on network/model availability
            errors.append(f"openai: {exc}")

    raise RuntimeError("; ".join(errors) if errors else "No supported LLM provider configured")


def _route_with_llm(text: str) -> RouteDecision | None:
    try:
        raw = _run_model_prompt(_router_prompt(text))
        payload = _extract_json_payload(raw)
    except Exception:
        return None

    action_raw = str(payload.get("action", "")).strip().lower()
    if action_raw not in ROUTER_ACTIONS:
        return None

    task_text_raw = payload.get("task_text")
    task_text = _sanitize_task_text(str(task_text_raw)) if task_text_raw else ""
    if action_raw == "task" and not task_text:
        task_text = _sanitize_task_text(text)

    if action_raw == "task":
        task_text = _coerce_task_text(task_text)
        if not task_text:
            return None

    return _decision(action_raw, task_text or None, source="llm")


def route_user_message(text: str) -> RouteDecision:
    """Route a user message to a command action, task action, or unknown."""
    normalized = _normalize(text)
    if not normalized:
        return _decision("unknown", None, source="empty")

    if normalized in ALLOWED_COMMANDS:
        return _decision(normalized, None, source="exact")

    system_task = _route_with_system_tasks(normalized)
    if system_task is not None:
        return _decision("task", system_task, source="rules")

    command = _route_with_rules(normalized)
    if command != "unknown":
        return _decision(command, None, source="rules")

    llm_result = _route_with_llm(text)
    if llm_result is not None:
        return llm_result

    return _decision("unknown", None, source="rules")


def parse_user_message(text: str) -> str:
    """Map user input to an approved command, or 'unknown'."""
    routed = route_user_message(text)
    action = routed["action"]
    return action if action in ALLOWED_COMMANDS else "unknown"
