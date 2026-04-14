"""Parse structured LLM responses for the agentic chat protocol.

The cockpit LLM is instructed to respond with JSON in one of five formats:
  - "thinking":        deliberation step — information assessment and tool plan
  - "response":        plain text answer (no tool needed)
  - "tool_call":       single tool invocation request
  - "tool_calls":      multiple parallel tool invocations
  - "action_proposal": mutating action that requires user confirmation

When the LLM ignores the format instruction and returns bare text or
malformed JSON, the parser falls back gracefully to a plain-text response
and logs a warning so the caller can track format-compliance rates.

See docs/architecture/17_agentic_chat_architecture.md §4.2–4.4.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

VALID_TYPES = frozenset({"thinking", "response", "tool_call", "tool_calls", "action_proposal"})


@dataclass
class ParsedResponse:
    """Normalized representation of an LLM structured response."""

    type: str  # "thinking", "response", "tool_call", "tool_calls", "action_proposal"
    content: str | None = None  # For "response" / "thinking" type
    tool: str | None = None  # For "tool_call" / "action_proposal"
    arguments: dict | None = None  # For "tool_call" / "action_proposal"
    calls: list[dict] | None = None  # For "tool_calls" — [{id, tool, arguments}, …]
    explanation: str | None = None  # For "action_proposal"
    reasoning: str | None = None  # Optional reasoning (any type)
    assessment: str | None = None  # For "thinking" — what data is available/missing
    plan: str | None = None  # For "thinking" — which tools to call and why
    raw: str = ""  # Always preserved for debugging


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?\s*```",
    re.DOTALL,
)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text


def _repair_json(text: str) -> str:
    """Best-effort repair of common JSON issues.

    Handles:
    - Trailing commas before } or ]
    - Single quotes used instead of double quotes (simple cases)
    """
    # Strip trailing commas before closing braces/brackets
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    return repaired


def _try_split_multi_json(text: str) -> list[dict] | None:
    """Split a string containing multiple concatenated JSON objects.

    LLMs sometimes emit a thinking block followed by a response block as two
    separate JSON objects in a single completion::

        {"type":"thinking","assessment":"...","plan":"..."}

        {"type":"response","content":"actual answer"}

    ``json.loads`` rejects this because it is not a single valid JSON value.
    This function uses a simple brace-depth scanner to find object boundaries
    and returns a list of successfully parsed dicts, or None if fewer than 2
    objects are found (the single-object case is already handled by the caller).
    """
    objects: list[dict] = []
    depth = 0
    start: int | None = None
    in_string = False
    escape_next = False

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            if in_string:
                escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                parsed = _try_parse_json(candidate)
                if parsed is not None:
                    objects.append(parsed)
                start = None

    return objects if len(objects) >= 2 else None


def _try_parse_json(text: str) -> dict | None:
    """Attempt to parse *text* as JSON, returning None on failure."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _infer_type(obj: dict) -> str:
    """Infer response type from keys when "type" is absent."""
    if "assessment" in obj or "plan" in obj:
        return "thinking"
    if "calls" in obj:
        return "tool_calls"
    if "tool" in obj and "explanation" in obj:
        return "action_proposal"
    if "tool" in obj:
        return "tool_call"
    # Default: treat as a direct response
    return "response"


def _build_from_dict(obj: dict, raw: str) -> ParsedResponse:
    """Construct a ParsedResponse from a validated dict."""
    resp_type = obj.get("type")
    if resp_type not in VALID_TYPES:
        resp_type = _infer_type(obj)

    return ParsedResponse(
        type=resp_type,
        content=obj.get("content"),
        tool=obj.get("tool"),
        arguments=obj.get("arguments"),
        calls=obj.get("calls"),
        explanation=obj.get("explanation"),
        reasoning=obj.get("reasoning"),
        assessment=obj.get("assessment"),
        plan=obj.get("plan"),
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_llm_response(raw: str) -> ParsedResponse:
    """Parse an LLM response string into a structured ``ParsedResponse``.

    The function tries, in order:
    1. Strip whitespace and markdown fences, then parse as JSON.
    2. Apply light JSON repair (trailing commas) and retry.
    3. Fall back to plain-text response with a logged warning.
    """
    if not raw or not raw.strip():
        return ParsedResponse(type="response", content="", raw=raw or "")

    stripped = raw.strip()
    cleaned = _strip_fences(stripped)

    # Attempt 1: direct parse
    obj = _try_parse_json(cleaned)
    if obj is not None:
        return _build_from_dict(obj, raw)

    # Attempt 2: repair and retry
    repaired = _repair_json(cleaned)
    obj = _try_parse_json(repaired)
    if obj is not None:
        logger.debug("Parsed LLM response after JSON repair")
        return _build_from_dict(obj, raw)

    # Attempt 3: multi-object split (thinking + response in one completion)
    multi = _try_split_multi_json(cleaned)
    if multi is not None:
        # Prefer the last "response"-typed object; carry thinking metadata.
        thinking_obj: dict | None = None
        response_obj: dict | None = None
        for obj in multi:
            inferred = obj.get("type") or _infer_type(obj)
            if inferred == "thinking":
                thinking_obj = obj
            elif inferred == "response":
                response_obj = obj
        # If we found a response block, use it.
        if response_obj is not None:
            result = _build_from_dict(response_obj, raw)
            if thinking_obj is not None:
                result.assessment = thinking_obj.get("assessment")
                result.plan = thinking_obj.get("plan")
            logger.info(
                "Parsed multi-object LLM response (%d objects); "
                "extracted type=%s",
                len(multi),
                result.type,
            )
            return result
        # No response block — fall through to the last object.
        logger.info(
            "Parsed multi-object LLM response (%d objects); "
            "using last object",
            len(multi),
        )
        return _build_from_dict(multi[-1], raw)

    # Fallback: plain text
    logger.warning(
        "LLM response is not valid JSON; treating as plain text. "
        "First 120 chars: %s",
        stripped[:120],
    )
    return ParsedResponse(type="response", content=stripped, raw=raw)


def format_tool_result(
    tool_name: str,
    result: dict,
    max_chars: int = 2000,
) -> str:
    """Format a tool execution result for injection back into the conversation.

    Returns a string like::

        [Tool: query_ticker_data]
        {"ticker": "BHP", "documents": [...]}

    If the JSON serialization exceeds *max_chars* it is truncated with an
    ellipsis marker so the LLM knows data was clipped.
    """
    try:
        result_json = json.dumps(result, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        result_json = str(result)

    if len(result_json) > max_chars:
        result_json = result_json[: max_chars - 15] + "...[truncated]"

    return f"[Tool: {tool_name}]\n{result_json}"
