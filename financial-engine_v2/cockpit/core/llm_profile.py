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

logger = logging.getLogger(__name__)

_VALID_POLICIES = frozenset(
    {"local_only", "local_preferred", "api_preferred", "api_only"}
)


def resolve_hybrid_router_policy(*, api_available: bool) -> str:
    """Return a HybridRouter policy string.

    Precedence:
      1. ``HYBRID_ROUTER_POLICY`` (if set to a valid value)
      2. ``COCKPIT_LLM_PROFILE`` (see mapping below)
      3. ``local_preferred`` (ops default)
    """
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


def cockpit_llm_profile_label() -> str:
    """Human-readable profile for diagnostics (not necessarily equal to policy)."""
    if (os.environ.get("HYBRID_ROUTER_POLICY") or "").strip() in _VALID_POLICIES:
        return f"override:{os.environ['HYBRID_ROUTER_POLICY'].strip()}"
    return (os.environ.get("COCKPIT_LLM_PROFILE") or "ops").strip() or "ops"
