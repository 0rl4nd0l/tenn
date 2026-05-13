from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.services.tenn_chat import _build_prompt as build_backend_json_chat_prompt
from cockpit.core.agent_loop import _STRUCTURED_OUTPUT_INSTRUCTIONS
from cockpit.core.chat import ResponseMode
from cockpit.core.request_standards import (
    REQUEST_STANDARD_REGISTRY,
    request_standard_prompt_guidance,
)
from cockpit.core.tool_definitions import TOOL_DEFINITIONS_PROMPT


PromptBlockKind = Literal[
    "base",
    "safety",
    "route_modifier",
    "tool_definitions",
    "output_contract",
    "runtime_context",
    "user_message",
    "operator_draft",
    "no_llm",
]


@dataclass(frozen=True)
class PromptRoute:
    route_id: str
    label: str
    kind: str
    description: str
    editable: bool
    supports_dry_run: bool
    warning: str | None = None


PROMPT_ROUTES: tuple[PromptRoute, ...] = (
    PromptRoute(
        route_id="structured_agent",
        label="Structured agent loop",
        kind="Agent",
        description="Default tool-capable Cockpit chat path for general analysis.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="keyword_synthesis",
        label="Keyword synthesis",
        kind="Keyword",
        description="Legacy direct synthesis path after local context is gathered.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="marketplace_assistant",
        label="Marketplace assistant",
        kind="Mode",
        description="Marketplace mission drafting mode that bypasses ticker heuristics.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="backend_json_rag",
        label="Backend /chat JSON RAG",
        kind="JSON",
        description="Backend evidence-only JSON chat prompt used by /chat.",
        editable=True,
        supports_dry_run=True,
        warning="Strict JSON output contract.",
    ),
    PromptRoute(
        route_id="request_company_analysis",
        label="Company analysis standard",
        kind="Overlay",
        description="Request-standard overlay for deep company analysis.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="request_daily_market_update",
        label="Daily market update standard",
        kind="Overlay",
        description="Request-standard overlay for market-wide daily updates.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="request_sector_analysis",
        label="Sector analysis standard",
        kind="Overlay",
        description="Request-standard overlay for sector and industry analysis.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="request_watchlist_triage",
        label="Watchlist triage standard",
        kind="Overlay",
        description="Request-standard overlay for watchlist prioritization.",
        editable=True,
        supports_dry_run=True,
    ),
    PromptRoute(
        route_id="slash_control",
        label="Slash/control commands",
        kind="No LLM",
        description="Deterministic slash and control paths dispatch without an LLM prompt.",
        editable=False,
        supports_dry_run=False,
        warning="No LLM prompt is sent for deterministic command routes.",
    ),
)


_ROUTES_BY_ID = {route.route_id: route for route in PROMPT_ROUTES}


def prompt_route_inventory() -> list[dict[str, Any]]:
    return [
        {
            "route_id": route.route_id,
            "label": route.label,
            "kind": route.kind,
            "description": route.description,
            "editable": route.editable,
            "supports_dry_run": route.supports_dry_run,
            "warning": route.warning,
        }
        for route in PROMPT_ROUTES
    ]


def _trim_draft(draft_override: str | None) -> str:
    return str(draft_override or "").strip()[:8000]


def _block(
    block_id: str,
    label: str,
    kind: PromptBlockKind,
    content: str,
    *,
    locked: bool,
    source: str,
    warning: str | None = None,
) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "label": label,
        "kind": kind,
        "content": str(content or ""),
        "locked": locked,
        "source": source,
        "warning": warning,
    }


def _system_instruction(controller: Any, *, mode: str, ticker: str | None) -> str:
    return controller._build_system_instruction(  # noqa: SLF001
        mode,
        str(ticker or "").strip().upper() or None,
        {},
    )


def _marketplace_system_instruction() -> str:
    return (
        "You are Tenn in Marketplace assistant mode.\n"
        "- Treat the user message as an application instruction packet for Marketplace mission drafting.\n"
        "- Do not interpret uppercase words as ASX tickers, company identifiers, or command aliases.\n"
        "- Do not trigger finance/news/announcement/backfill workflows unless the user explicitly requests those workflows.\n"
        "- If the user message requests strict JSON only, return strict JSON only.\n"
        "- Return plain text otherwise.\n"
    )


def _split_backend_json_prompt(prompt: str) -> tuple[str, str]:
    first_period = prompt.find(".")
    if first_period > 0 and prompt[:first_period].startswith("You are"):
        return prompt[: first_period + 1].strip(), prompt[first_period + 1 :].strip()
    return "Output ONLY valid JSON.", prompt


def _request_standard_from_route(route_id: str) -> str | None:
    prefix = "request_"
    if route_id.startswith(prefix):
        candidate = route_id[len(prefix) :]
        if candidate in REQUEST_STANDARD_REGISTRY:
            return candidate
    return None


def _messages_from_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    system_parts = [
        block["content"]
        for block in blocks
        if block["kind"]
        in {"base", "safety", "route_modifier", "tool_definitions", "output_contract", "operator_draft"}
        and str(block.get("content") or "").strip()
    ]
    user_parts = [
        block["content"]
        for block in blocks
        if block["kind"] in {"runtime_context", "user_message"}
        and str(block.get("content") or "").strip()
    ]
    messages: list[dict[str, str]] = []
    if system_parts:
        messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    if user_parts:
        messages.append({"role": "user", "content": "\n\n".join(user_parts)})
    return messages


def build_prompt_preview(
    service: Any,
    *,
    route_id: str,
    message: str,
    ticker: str | None = None,
    mode: str = "analysis",
    draft_override: str | None = None,
) -> dict[str, Any]:
    route = _ROUTES_BY_ID.get(route_id)
    if route is None:
        raise ValueError(f"Unknown prompt route: {route_id}")

    normalized_message = str(message or "").strip() or "Summarise BHP using current evidence."
    normalized_ticker = str(ticker or "").strip().upper() or None
    draft = _trim_draft(draft_override)
    controller = getattr(service, "chat_controller", None)
    if controller is None and route.route_id != "backend_json_rag":
        raise RuntimeError("Cockpit chat controller is unavailable")

    blocks: list[dict[str, Any]]
    if route.route_id == "slash_control":
        blocks = [
            _block(
                "no_llm",
                "No LLM prompt",
                "no_llm",
                "This route is handled by deterministic slash/control command dispatch.",
                locked=True,
                source="cockpit.core.chat.ChatController._handle_slash_command",
                warning=route.warning,
            )
        ]
        messages: list[dict[str, str]] = []
    elif route.route_id == "structured_agent":
        system_content = (
            controller._agent_loop._build_system_prompt()  # noqa: SLF001
            if getattr(controller, "_agent_loop", None) is not None
            else "\n".join(
                [
                    _system_instruction(controller, mode=ResponseMode.FAST, ticker=None),
                    f"\nTOOLS:\n{TOOL_DEFINITIONS_PROMPT}",
                    f"\n{_STRUCTURED_OUTPUT_INSTRUCTIONS}",
                ]
            )
        )
        user_content = normalized_message
        if normalized_ticker:
            user_content = f"Current ticker context: {normalized_ticker}\n\n{normalized_message}"
        blocks = [
            _block(
                "agent_system",
                "System + tool contract",
                "base",
                system_content,
                locked=True,
                source="cockpit.core.agent_loop.AgentLoop._build_system_prompt",
            ),
            _block(
                "agent_runtime_context",
                "Runtime context preview",
                "runtime_context",
                "Conversation history, attached sources, strategy context, and request-standard guidance may be prepended at runtime.",
                locked=True,
                source="cockpit.core.chat.ChatController._run_agent_loop",
            ),
            _block(
                "agent_user",
                "User message preview",
                "user_message",
                user_content,
                locked=True,
                source="preview input",
            ),
        ]
    elif route.route_id == "keyword_synthesis":
        response_mode = ResponseMode.DEEP_ANALYSIS if mode == "strategy" else ResponseMode.FAST
        blocks = [
            _block(
                "keyword_system",
                "System instruction",
                "base",
                _system_instruction(controller, mode=response_mode, ticker=normalized_ticker),
                locked=True,
                source="cockpit.core.chat.ChatController._build_system_instruction",
            ),
            _block(
                "keyword_runtime_context",
                "Runtime context preview",
                "runtime_context",
                "Local context, excerpts, financial metrics, prices, qualitative context, data quality notes, recent turns, and attached sources are appended at runtime.",
                locked=True,
                source="cockpit.core.chat.ChatController.build_chat_response",
            ),
            _block(
                "keyword_user",
                "User message preview",
                "user_message",
                normalized_message,
                locked=True,
                source="preview input",
            ),
        ]
    elif route.route_id == "marketplace_assistant":
        blocks = [
            _block(
                "marketplace_system",
                "Marketplace system instruction",
                "route_modifier",
                _marketplace_system_instruction(),
                locked=True,
                source="cockpit.core.chat.ChatController._run_marketplace_chat_mode",
            ),
            _block(
                "marketplace_user",
                "Instruction packet preview",
                "user_message",
                normalized_message,
                locked=True,
                source="preview input",
            ),
        ]
    elif route.route_id == "backend_json_rag":
        sample_rows = [
            {
                "source_name": "Prompt Lab sample context",
                "published_at": datetime.utcnow().date().isoformat(),
                "text": "Dry-run preview context only. Replace with live retrieved context in normal /chat analysis.",
            }
        ]
        prompt = build_backend_json_chat_prompt(normalized_message, sample_rows)
        system_msg, user_msg = _split_backend_json_prompt(prompt)
        blocks = [
            _block(
                "backend_json_system",
                "JSON system instruction",
                "base",
                system_msg,
                locked=True,
                source="app.services.tenn_chat._build_prompt",
                warning=route.warning,
            ),
            _block(
                "backend_json_user",
                "Question + context JSON preview",
                "user_message",
                user_msg,
                locked=True,
                source="app.services.tenn_chat._build_prompt",
            ),
        ]
    else:
        standard_type = _request_standard_from_route(route.route_id)
        if standard_type is None:
            raise ValueError(f"Unsupported prompt route: {route.route_id}")
        blocks = [
            _block(
                "request_standard_base",
                "Base Cockpit instruction",
                "base",
                _system_instruction(controller, mode=ResponseMode.DEEP_ANALYSIS, ticker=normalized_ticker),
                locked=True,
                source="cockpit.core.chat.ChatController._build_system_instruction",
            ),
            _block(
                "request_standard_overlay",
                route.label,
                "route_modifier",
                request_standard_prompt_guidance(standard_type),
                locked=True,
                source="cockpit.core.request_standards.request_standard_prompt_guidance",
            ),
            _block(
                "request_standard_user",
                "User message preview",
                "user_message",
                normalized_message,
                locked=True,
                source="preview input",
            ),
        ]

    if draft and route.editable:
        blocks.append(
            _block(
                "operator_draft",
                "Operator draft override",
                "operator_draft",
                draft,
                locked=False,
                source="unsaved UI draft",
                warning="Draft only. Not active in normal chat routing.",
            )
        )

    messages = _messages_from_blocks(blocks) if route.route_id != "slash_control" else []
    char_count = sum(len(item.get("content", "")) for item in messages)
    return {
        "route": {
            "route_id": route.route_id,
            "label": route.label,
            "kind": route.kind,
            "description": route.description,
            "editable": route.editable,
            "supports_dry_run": route.supports_dry_run,
            "warning": route.warning,
        },
        "blocks": blocks,
        "messages": messages,
        "estimated_tokens": max(char_count // 4, 1) if char_count else 0,
        "warnings": [item for item in (route.warning,) if item],
    }


def dry_run_prompt_preview(service: Any, preview: dict[str, Any]) -> dict[str, Any]:
    route = preview.get("route") if isinstance(preview.get("route"), dict) else {}
    if not bool(route.get("supports_dry_run")):
        raise ValueError("Selected route does not support LLM dry-run")

    messages = preview.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("Prompt preview has no LLM messages")

    controller = getattr(service, "chat_controller", None)
    if controller is None:
        raise RuntimeError("Cockpit chat controller is unavailable")

    last = messages[-1]
    prompt = str(last.get("content") or "")
    prior_messages = [
        {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")}
        for item in messages[:-1]
        if isinstance(item, dict)
    ]
    timeout = min(float(getattr(controller, "llm_timeout_seconds", 120.0) or 120.0), 120.0)

    hybrid_router = getattr(controller, "_hybrid_router", None)
    routing_metadata: dict[str, Any] = {"source": "dry_run"}
    if hybrid_router is not None:
        text = hybrid_router.chat(
            prompt,
            timeout=timeout,
            prior_messages=prior_messages,
        )
        if hasattr(hybrid_router, "last_attempt_metadata"):
            metadata = hybrid_router.last_attempt_metadata()
            if isinstance(metadata, dict):
                routing_metadata.update(metadata)
    else:
        llm_client = getattr(controller, "ollama_client", None)
        if llm_client is None:
            raise RuntimeError("No LLM client is available for dry-run")
        text = llm_client.chat(
            prompt,
            timeout=timeout,
            prior_messages=prior_messages,
        )
        routing_metadata.update(
            {
                "source": "local",
                "model": str(getattr(llm_client, "model", "") or "local"),
            }
        )

    return {
        "text": str(text or "").strip(),
        "routing_metadata": routing_metadata,
    }
