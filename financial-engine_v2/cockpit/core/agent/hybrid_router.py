"""HybridRouter — single insertion point between the orchestrator and LLM execution.

Routes every LLM call to either local (llama.cpp) or cloud API, normalises the
output into a ``RouterResponse``.

Policy (local-first, no surprise costs):
  - ``local_only``      — always use local; raise if no local client.
  - ``local_preferred`` — use local; fall back to API if local unavailable.
  - ``api_preferred``   — use API if an api_client is present; fall back to local.
  - ``api_only``        — always use API; raise if no api_client.

The default policy is ``local_only``.

The API client is never called without an explicit ``api_client`` being
supplied *and* either ``force_backend="api"`` or a policy that allows API.
This prevents accidental cloud cost.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cockpit.integrations.llamacpp_client import LlamaCppClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class RouterResponse:
    """Normalised response from a single LLM call."""

    text: str
    source: str          # "local" | "api"
    model: str
    latency_ms: int
    cost_usd: float      # 0.0 for local
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class _CostEntry:
    """Internal record of a single completed call."""

    source: str
    role: str
    model: str
    latency_ms: int
    cost_usd: float


# ---------------------------------------------------------------------------
# HybridRouter
# ---------------------------------------------------------------------------

_VALID_POLICIES = frozenset(
    {"local_only", "local_preferred", "api_preferred", "api_only"}
)
_ENV_POLICY_VAR = "HYBRID_ROUTER_POLICY"


class HybridRouter:
    """Route LLM calls to local or API backend with cost/latency tracking.

    Parameters
    ----------
    llm_client:
        A ``LlamaCppClient`` (or compatible) instance used for local calls.
        Must implement ``chat(prompt, timeout, prior_messages) -> str``.
    api_client:
        Optional cloud API client.  Must implement the same ``chat`` interface
        as ``llm_client``.  If ``None``, API routes are unavailable.
    policy:
        Routing policy string.  Falls back to the ``HYBRID_ROUTER_POLICY``
        environment variable; default is ``"local_only"``.
    llm_timeout:
        Per-call timeout in seconds passed through to the underlying client.
    """

    def __init__(
        self,
        llm_client: "LlamaCppClient | None" = None,
        api_client: Any = None,
        policy: str | None = None,
        llm_timeout: float = 120.0,
    ) -> None:
        self._local = llm_client
        self._api = api_client
        self._timeout = llm_timeout
        self._policy = self._resolve_policy(policy)
        self._log: list[_CostEntry] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict],
        *,
        role: str = "orchestrator",
        force_backend: str | None = None,
    ) -> RouterResponse:
        """Route ``messages`` to the selected backend and return a ``RouterResponse``.

        Parameters
        ----------
        messages:
            OpenAI-style list of ``{"role": ..., "content": ...}`` dicts.
        role:
            Caller role label used for cost tracking (e.g. ``"orchestrator"``).
        force_backend:
            ``"local"`` or ``"api"`` to override the configured policy for
            this call.
        """
        backend = self._select_backend(force_backend)

        start = time.monotonic()
        if backend == "local":
            response = self._call_local(messages)
        else:
            response = self._call_api(messages)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        result = RouterResponse(
            text=response["text"],
            source=backend,
            model=response["model"],
            latency_ms=elapsed_ms,
            cost_usd=response.get("cost_usd", 0.0),
            tool_calls=response.get("tool_calls", []),
        )

        self._log.append(
            _CostEntry(
                source=backend,
                role=role,
                model=result.model,
                latency_ms=elapsed_ms,
                cost_usd=result.cost_usd,
            )
        )
        return result

    def cost_log(self) -> list[dict]:
        """Return a copy of the cost log as plain dicts."""
        return [
            {
                "source": e.source,
                "role": e.role,
                "model": e.model,
                "latency_ms": e.latency_ms,
                "cost_usd": e.cost_usd,
            }
            for e in self._log
        ]

    def total_cost_usd(self) -> float:
        """Return cumulative API cost in USD (local calls contribute 0.0)."""
        return sum(e.cost_usd for e in self._log)

    # ------------------------------------------------------------------
    # Backend selection
    # ------------------------------------------------------------------

    def _select_backend(self, force_backend: str | None) -> str:
        """Determine which backend to use for this call."""
        if force_backend is not None:
            if force_backend not in ("local", "api"):
                raise ValueError(
                    f"force_backend must be 'local' or 'api', got {force_backend!r}"
                )
            return force_backend

        policy = self._policy

        if policy == "local_only":
            return "local"

        if policy == "local_preferred":
            if self._local is not None:
                return "local"
            if self._api is not None:
                return "api"
            return "local"  # will fail in _call_local with a clear message

        if policy == "api_preferred":
            if self._api is not None:
                return "api"
            return "local"

        if policy == "api_only":
            return "api"

        # Unreachable — _resolve_policy validates.
        return "local"

    # ------------------------------------------------------------------
    # Local backend
    # ------------------------------------------------------------------

    def _call_local(self, messages: list[dict]) -> dict:
        """Call the local llama.cpp backend, normalise to an internal dict."""
        if self._local is None:
            raise RuntimeError(
                "No local LLM client configured. "
                "Pass llm_client= to HybridRouter or change the policy."
            )

        model_name: str = getattr(self._local, "model", "local")

        # Split messages into prior history + final prompt (matching agent_loop.py pattern).
        if len(messages) >= 2:
            prior = messages[:-1]
            prompt = messages[-1]["content"]
        else:
            prior = None
            prompt = messages[-1]["content"] if messages else ""

        text = self._local.chat(
            prompt=prompt,
            timeout=self._timeout,
            prior_messages=prior,
        )
        return {"text": text, "model": model_name, "cost_usd": 0.0, "tool_calls": []}

    # ------------------------------------------------------------------
    # API backend
    # ------------------------------------------------------------------

    def _call_api(self, messages: list[dict]) -> dict:
        """Call the cloud API backend, normalise to an internal dict.

        Prefers the richer ``complete()`` interface (returns cost and
        tool-call data) when the client exposes it.  Falls back to the
        minimal ``chat()`` interface for backward compatibility.
        """
        if self._api is None:
            raise RuntimeError(
                "No API client configured. "
                "Pass api_client= to HybridRouter, or set policy='local_only'."
            )

        if len(messages) >= 2:
            prior = messages[:-1]
            prompt = messages[-1]["content"]
        else:
            prior = None
            prompt = messages[-1]["content"] if messages else ""

        # Prefer complete() for rich responses (cost, tool_calls, usage).
        if hasattr(self._api, "complete"):
            return self._api.complete(
                prompt=prompt,
                timeout=self._timeout,
                prior_messages=prior,
            )

        # Fallback: basic chat() interface (e.g. LlamaCppClient).
        model_name: str = getattr(self._api, "model", "api")
        text = self._api.chat(
            prompt=prompt,
            timeout=self._timeout,
            prior_messages=prior,
        )
        return {"text": text, "model": model_name, "cost_usd": 0.0, "tool_calls": []}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_policy(policy: str | None) -> str:
        """Resolve policy from argument → env var → default."""
        if policy is not None:
            resolved = policy.strip()
        else:
            resolved = (os.getenv(_ENV_POLICY_VAR) or "local_only").strip()

        if resolved not in _VALID_POLICIES:
            raise ValueError(
                f"Unknown HybridRouter policy {resolved!r}. "
                f"Valid options: {sorted(_VALID_POLICIES)}"
            )
        return resolved
