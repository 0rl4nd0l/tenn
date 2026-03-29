"""Map high-level cockpit LLM profiles to HybridRouter policy strings.

Debate-informed defaults:
  - *ops* (default): local-first to minimise Anthropic token use for tool-heavy work.
  - *advisor*: API-first when a key is present (richer synthesis).
  - Explicit HYBRID_ROUTER_POLICY always wins if set.

See cockpit.core.agent.hybrid_router.HybridRouter for policy semantics.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Valid ``COCKPIT_LLM_PROFILE`` values surfaced in Cockpit (pre-boot + Ops).
LLM_PROFILE_IDS: tuple[str, ...] = ("ops", "advisor", "local_only", "api_only")

# Short titles for Select widgets (long body text lives in LLM_PROFILE_DESCRIPTIONS).
LLM_PROFILE_TITLES: dict[str, str] = {
    "ops": "Ops — local-first (default)",
    "advisor": "Advisor — prefer API when key is set",
    "local_only": "Local only — never cloud LLM",
    "api_only": "API only — require cloud LLM when possible",
}

# Plain-language help: one paragraph per profile (UI: under each option in help blocks).
LLM_PROFILE_DESCRIPTIONS: dict[str, str] = {
    "ops": (
        "Day-to-day default. Uses your local llama.cpp first for chat and tool calls so routine "
        "work stays on-box and API cost stays low. Cloud (Anthropic) is only used when your routing "
        "rules allow it and local is not the right fit—not silent auto-cloud."
    ),
    "advisor": (
        "When an Anthropic API key is configured, prefers the cloud model for judgment and "
        "synthesis-heavy turns; falls back to local if the key is missing or the API fails. "
        "Good when you want stronger prose or reasoning and accept token cost."
    ),
    "local_only": (
        "Never sends chat completions to Anthropic—all LLM traffic goes through local llama.cpp. "
        "Use for offline sensitivity, cost caps, or policy that forbids cloud LLM."
    ),
    "api_only": (
        "Requires cloud LLM (Anthropic) for completions when a key is present. If no key is "
        "available, routing falls back to local so the app keeps working—fix the key for strict "
        "API-only behaviour."
    ),
}


def describe_llm_profile(profile_id: str) -> str:
    """Return the help paragraph for a profile id, or a generic fallback."""
    key = (profile_id or "ops").strip().lower()
    return LLM_PROFILE_DESCRIPTIONS.get(key, LLM_PROFILE_DESCRIPTIONS["ops"])


def format_all_profile_descriptions() -> str:
    """Multi-line block listing every profile with its description (pre-boot / Ops help)."""
    lines: list[str] = []
    for pid in LLM_PROFILE_IDS:
        title = LLM_PROFILE_TITLES.get(pid, pid)
        body = LLM_PROFILE_DESCRIPTIONS.get(pid, "")
        lines.append(f"• {title}")
        lines.append(f"  {body}")
        lines.append("")
    return "\n".join(lines).rstrip()


_VALID_POLICIES = frozenset(
    {"local_only", "local_preferred", "api_preferred", "api_only"}
)


def resolve_hybrid_router_policy(
    *,
    api_available: bool,
    cockpit_llm: dict[str, Any] | None = None,
) -> str:
    """Return a HybridRouter policy string.

    When ``cockpit_llm`` is loaded from ``config/cockpit_llm.yaml`` and
    ``allow_env_override`` is false, ``hybrid_router_policy`` in that file is
    authoritative (env vars are ignored).

    When ``cockpit_llm`` is None (tests) or ``allow_env_override`` is true, legacy
    precedence applies:

      1. ``HYBRID_ROUTER_POLICY`` (if set to a valid value)
      2. ``COCKPIT_LLM_PROFILE`` (see mapping below)
      3. ``local_preferred`` (ops default)
    """
    cm = cockpit_llm if cockpit_llm is not None else {}
    use_env = cockpit_llm is None or bool(cm.get("allow_env_override", False))

    if not use_env:
        explicit = (cm.get("hybrid_router_policy") or "").strip()
        if explicit in _VALID_POLICIES:
            return explicit
        if explicit:
            logger.warning(
                "Ignoring invalid hybrid_router_policy in cockpit_llm.yaml: %r — using local_preferred.",
                explicit,
            )
        return "local_preferred"

    explicit = (os.environ.get("HYBRID_ROUTER_POLICY") or "").strip()
    if explicit in _VALID_POLICIES:
        return explicit
    if explicit:
        logger.warning(
            "Ignoring invalid HYBRID_ROUTER_POLICY=%r — falling through to COCKPIT_LLM_PROFILE.",
            explicit,
        )

    profile = (os.environ.get("COCKPIT_LLM_PROFILE") or "ops").strip().lower()

    if profile in {"ops", "local_first"}:
        return "local_preferred"
    if profile in {"advisor", "cloud", "cloud_first", "balanced"}:
        return "api_preferred" if api_available else "local_preferred"
    if profile == "local_only":
        return "local_only"
    if profile == "api_only":
        return "api_only" if api_available else "local_preferred"

    logger.warning("Unknown COCKPIT_LLM_PROFILE=%r — using local_preferred.", profile)
    return "local_preferred"


def cockpit_llm_profile_label(cockpit_llm: dict[str, Any] | None = None) -> str:
    """Human-readable profile for diagnostics (not necessarily equal to policy)."""
    cm = cockpit_llm if cockpit_llm is not None else {}
    use_env = cockpit_llm is None or bool(cm.get("allow_env_override", False))
    if not use_env:
        return str(cm.get("llm_profile_label") or "ops").strip() or "ops"
    if (os.environ.get("HYBRID_ROUTER_POLICY") or "").strip() in _VALID_POLICIES:
        return f"override:{os.environ['HYBRID_ROUTER_POLICY'].strip()}"
    return (os.environ.get("COCKPIT_LLM_PROFILE") or "ops").strip() or "ops"


def preview_effective_policy(
    *,
    profile: str,
    explicit_override: str | None,
    api_available: bool,
) -> str:
    """Show which HybridRouter policy would apply for a session (pre-boot / Ops preview).

    Temporarily adjusts only ``COCKPIT_LLM_PROFILE`` / ``HYBRID_ROUTER_POLICY`` and restores them.
    """
    old_h = os.environ.get("HYBRID_ROUTER_POLICY")
    old_p = os.environ.get("COCKPIT_LLM_PROFILE")
    try:
        ex = (explicit_override or "").strip()
        if ex in _VALID_POLICIES:
            os.environ["HYBRID_ROUTER_POLICY"] = ex
        else:
            os.environ.pop("HYBRID_ROUTER_POLICY", None)
        os.environ["COCKPIT_LLM_PROFILE"] = (profile or "ops").strip().lower()
        return resolve_hybrid_router_policy(api_available=api_available)
    finally:
        if old_h is None:
            os.environ.pop("HYBRID_ROUTER_POLICY", None)
        else:
            os.environ["HYBRID_ROUTER_POLICY"] = old_h
        if old_p is None:
            os.environ.pop("COCKPIT_LLM_PROFILE", None)
        else:
            os.environ["COCKPIT_LLM_PROFILE"] = old_p
