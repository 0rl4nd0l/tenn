"""HybridRouter — single insertion point between the orchestrator and LLM execution.

Routes every LLM call to either local (llama.cpp) or cloud API, normalises the
output into a ``RouterResponse``.

Policy (local-first, no surprise costs):
  - ``local_only``      — always use local; raise if no local client.
  - ``local_preferred`` — use local; fall back to API if local unavailable.
  - ``api_preferred``   — use API if an api_client is present; fall back to local.
  - ``api_only``        — always use API; raise if no api_client.

The default policy is ``api_preferred``.

The API client is never called unless an explicit ``api_client`` is supplied.
Normal routing follows ``force_backend`` or the configured policy, except for
GPU-exclusive activity: when extraction or another registered GPU-heavy task
owns the local llama.cpp router, chat is forced to API when available and
otherwise fails fast instead of contending for VRAM.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
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
    source: str  # "local" | "api"
    model: str
    latency_ms: int
    cost_usd: float  # 0.0 for local
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class _CostEntry:
    """Internal record of a single completed call."""

    source: str
    role: str
    model: str
    latency_ms: int
    cost_usd: float
    routing_reason: str


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
        environment variable; default is ``"api_preferred"``.
    llm_timeout:
        Per-call timeout in seconds passed through to the underlying client.
    extraction_active_fn:
        Optional callable returning ``True`` when a GPU-bound extraction is
        running on the shared llama.cpp server. When active, chat is routed to
        the cloud API when available; otherwise local chat is blocked fail-fast
        to avoid VRAM contention on the shared router.
    gpu_exclusive_active_fn:
        Optional callable returning ``True`` when any registered GPU-heavy
        activity requires local chat to yield to API routing.
    """

    def __init__(
        self,
        llm_client: "LlamaCppClient | None" = None,
        api_client: Any = None,
        policy: str | None = None,
        llm_timeout: float = 120.0,
        extraction_active_fn: Callable[[], bool] | None = None,
        gpu_exclusive_active_fn: Callable[[], bool] | None = None,
        gpu_preemption_fn: Callable[[], str | None] | None = None,
    ) -> None:
        self._local = llm_client
        self._api = api_client
        self._timeout = llm_timeout
        self._policy = self._resolve_policy(policy)
        self._extraction_active_fn = extraction_active_fn
        self._gpu_exclusive_active_fn = gpu_exclusive_active_fn
        self._gpu_preemption_fn = gpu_preemption_fn
        self._log: list[_CostEntry] = []
        self._last_attempt: dict[str, Any] | None = None

        if self._policy == "api_preferred" and self._api is None:
            logger.warning(
                "HybridRouter policy is 'api_preferred' but no api_client configured — "
                "all calls will fall back to local. Set ANTHROPIC_API_KEY to enable API routing."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict],
        *,
        role: str = "orchestrator",
        force_backend: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
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
        backend, routing_reason = self._select_backend(
            force_backend,
            on_status=on_status,
        )

        model_name = self._resolve_backend_model_name(backend)
        self._last_attempt = {
            "source": backend,
            "model": model_name,
            "latency_ms": 0,
            "cost_usd": 0.0,
            "routing_reason": routing_reason,
        }

        start = time.monotonic()
        if backend == "local":
            response = self._call_local(messages, on_chunk=on_chunk)
        else:
            response = self._call_api(messages, on_chunk=on_chunk)
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
                routing_reason=routing_reason,
            )
        )
        self._last_attempt = {
            "source": backend,
            "model": result.model,
            "latency_ms": elapsed_ms,
            "cost_usd": result.cost_usd,
            "routing_reason": routing_reason,
        }
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
                "routing_reason": e.routing_reason,
            }
            for e in self._log
        ]

    def total_cost_usd(self) -> float:
        """Return cumulative API cost in USD (local calls contribute 0.0)."""
        return sum(e.cost_usd for e in self._log)

    def last_attempt_metadata(self) -> dict[str, Any] | None:
        """Return metadata for the most recent routing attempt, including failures."""
        return dict(self._last_attempt) if self._last_attempt is not None else None

    def preview_route(
        self,
        *,
        force_backend: str | None = None,
    ) -> dict[str, Any]:
        """Return the backend that would be selected for the next call.

        This is used by callers that need to avoid mutating the local llama.cpp
        runtime before the extraction/GPU safety checks have had a chance to
        redirect the turn to the API backend.
        """
        backend, routing_reason = self._select_backend(force_backend, on_status=None)
        return {
            "source": backend,
            "model": self._resolve_backend_model_name(backend),
            "routing_reason": routing_reason,
        }

    # ------------------------------------------------------------------
    # Backend selection
    # ------------------------------------------------------------------

    def _select_backend(
        self,
        force_backend: str | None,
        *,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[str, str]:
        """Determine which backend to use for this call."""
        if force_backend is not None and force_backend not in ("local", "api"):
            raise ValueError(
                f"force_backend must be 'local' or 'api', got {force_backend!r}"
            )

        if force_backend == "api":
            return "api", "force:api"

        if force_backend == "local" and self._gpu_exclusive_active_fn is None:
            return "local", "force:local"

        # GPU-exclusive override: when a registered GPU-heavy task owns the
        # shared llama.cpp server, route chat to the cloud API to avoid VRAM
        # contention. This deliberately beats local_only and force:local because
        # the contract requires local chat to fail fast rather than compete for
        # the GPU.
        if self._gpu_exclusive_active_fn is not None:
            try:
                if self._gpu_exclusive_active_fn():
                    logger.info("GPU-exclusive activity active on shared llama.cpp")
                    if self._api is not None:
                        if on_status is not None:
                            on_status(
                                "GPU-exclusive activity active - routing chat to API"
                            )
                        return "api", "gpu_exclusive_active"
                    if on_status is not None:
                        on_status(
                            "GPU-exclusive activity active - local chat blocked"
                        )
                    raise RuntimeError(
                        "GPU-exclusive activity active and no API client is configured"
                    )
            except RuntimeError:
                raise
            except Exception:
                pass  # Best-effort check; fall through to normal policy

        if force_backend is not None:
            return force_backend, f"force:{force_backend}"

        # Backward-compatible extraction-aware override for callers that still
        # pass only the extraction checker.
        if self._extraction_active_fn is not None:
            try:
                if self._extraction_active_fn():
                    logger.info("Extraction active on shared llama.cpp")
                    if self._api is not None:
                        if on_status is not None:
                            on_status(
                                "Extraction active on shared llama.cpp - routing chat to API"
                            )
                        return "api", "extraction_active"
                    if on_status is not None:
                        on_status(
                            "Extraction active on shared llama.cpp - local chat blocked until extraction finishes"
                        )
                    raise RuntimeError(
                        "Extraction active on shared llama.cpp and no API client is configured"
                    )
            except RuntimeError:
                raise
            except Exception:
                pass  # Best-effort check; fall through to normal policy

        if (
            self._gpu_preemption_fn is not None
            and self._api is not None
            and self._policy != "local_only"
        ):
            try:
                reason = str(self._gpu_preemption_fn() or "").strip()
                if reason:
                    logger.info(
                        "Higher-priority GPU claimant detected (%s) — routing chat to API",
                        reason,
                    )
                    if on_status is not None:
                        on_status(
                            "Higher-priority GPU work detected - routing chat to API"
                        )
                    return "api", "gpu_preempted"
            except Exception:
                pass  # Best-effort check; fall through to normal policy

        policy = self._policy

        if policy == "local_only":
            return "local", "policy:local_only"

        if policy == "local_preferred":
            if self._local is not None:
                return "local", "policy:local_preferred"
            if self._api is not None:
                return "api", "policy:local_preferred_fallback_api"
            return "local", "policy:local_preferred"  # clear fail in _call_local

        if policy == "api_preferred":
            if self._api is not None:
                return "api", "policy:api_preferred"
            return "local", "policy:api_preferred_fallback_local"

        if policy == "api_only":
            return "api", "policy:api_only"

        # Unreachable — _resolve_policy validates.
        return "local", "policy:local_preferred"

    # ------------------------------------------------------------------
    # Local backend
    # ------------------------------------------------------------------

    def _call_local(
        self,
        messages: list[dict],
        *,
        on_chunk: Callable[[str], None] | None = None,
    ) -> dict:
        """Call the local llama.cpp backend, normalise to an internal dict."""
        if self._local is None:
            raise RuntimeError(
                "No local LLM client configured. "
                "Pass llm_client= to HybridRouter or change the policy."
            )

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
            on_chunk=on_chunk,
        )
        model_name: str = getattr(self._local, "model", "local")
        return {"text": text, "model": model_name, "cost_usd": 0.0, "tool_calls": []}

    # ------------------------------------------------------------------
    # API backend
    # ------------------------------------------------------------------

    def _call_api(
        self,
        messages: list[dict],
        *,
        on_chunk: Callable[[str], None] | None = None,
    ) -> dict:
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

        # Prefer complete() for rich responses (cost, tool_calls, usage) when
        # streaming is not required. During final-answer synthesis we need the
        # chat interface so chunks can pass through safely.
        if on_chunk is None and hasattr(self._api, "complete"):
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
            on_chunk=on_chunk,
        )
        return {"text": text, "model": model_name, "cost_usd": 0.0, "tool_calls": []}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_backend_model_name(self, backend: str) -> str:
        if backend == "api":
            return str(getattr(self._api, "model", "api") or "api")
        return str(getattr(self._local, "model", "local") or "local")

    def _wrap_chunk_progress(
        self,
        on_chunk: Callable[[str], None] | None,
        on_status: Callable[[str], None] | None,
        backend: str,
    ) -> tuple[Callable[[str], None] | None, float]:
        """Wrap on_chunk with periodic on_status ticks so the UI sees progress.

        Emits a status update every ~3 s once token generation has started, so a
        silent JSON-generation pass (iteration 0, which intentionally swallows
        chunks from the caller) still produces user-visible "generating" ticks.

        Only applied to the ``local`` backend — wrapping ``on_chunk`` for the
        API backend would defeat the ``complete()``-vs-``chat()`` preference in
        ``_call_api`` (complete() is only called when ``on_chunk is None``).

        Returns the wrapped callback and the monotonic start timestamp so the
        caller can measure fallback latency against the same clock.
        """
        start = time.monotonic()
        if backend != "local":
            return on_chunk, start
        if on_status is None and on_chunk is None:
            return None, start

        state = {"tokens": 0, "last_emit": start}

        def _wrapped(chunk: str) -> None:
            state["tokens"] += 1
            if on_chunk is not None:
                on_chunk(chunk)
            if on_status is None:
                return
            now = time.monotonic()
            if now - state["last_emit"] >= 3.0:
                state["last_emit"] = now
                elapsed = now - start
                on_status(
                    f"Local model generating: "
                    f"{state['tokens']} token chunks / {elapsed:.0f}s"
                )

        return _wrapped, start

    def _should_fallback_to_api(
        self,
        exc: Exception,
        *,
        backend: str,
        force_backend: str | None,
    ) -> bool:
        """Return True when a failed local call should be retried via API.

        Triggered on TimeoutError or RuntimeError from the local backend when an
        API client is configured and the caller did not explicitly force local.
        Guards against infinite recursion (API-only path never enters here).
        """
        if backend != "local":
            return False
        if force_backend == "local":
            return False
        if self._api is None:
            return False
        if self._policy in ("local_only",):
            return False
        return isinstance(exc, (TimeoutError, RuntimeError))

    # ------------------------------------------------------------------
    # chat() adapter — allows HybridRouter to be used as llm_client
    # in AgentLoop without a separate wrapper class.
    # ------------------------------------------------------------------

    def chat(
        self,
        prompt: str,
        timeout: float = 120.0,
        prior_messages: list[dict] | None = None,
        on_chunk: Any = None,
        force_backend: str | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> str:
        """LlamaCppClient-compatible chat interface.

        Builds an OpenAI-style message list and delegates to :meth:`complete`.
        Returns the plain-text response. ``on_chunk`` is passed through to
        backend clients that support token callbacks.

        ``force_backend`` (``\"local\"`` | ``\"api\"``) overrides policy for this call only
        when HybridRouter is used from :class:`cockpit.core.agent_loop.AgentLoop`
        (e.g. ``/advisor`` / ``/local`` message prefixes).  Ignored by plain
        :class:`cockpit.integrations.llamacpp_client.LlamaCppClient`.
        """
        messages: list[dict] = []
        if prior_messages:
            messages.extend(prior_messages)
        messages.append({"role": "user", "content": prompt})

        result = self._complete_with_timeout(
            messages,
            timeout=timeout,
            role="orchestrator",
            force_backend=force_backend,
            on_chunk=on_chunk,
            on_status=on_status,
        )
        return result.text

    def _run_with_wall_clock_watchdog(
        self,
        call: Callable[[], dict],
        *,
        timeout: float,
        label: str,
        on_status: Callable[[str], None] | None = None,
    ) -> dict:
        """Run *call* in a daemon thread with an absolute wall-clock deadline.

        The inner httpx clients already have per-read timeouts, but those reset
        on every chunk. If the backend blocks before the first byte arrives, or
        dribbles tokens just fast enough to keep resetting the read timeout,
        those per-read timeouts never fire and the caller hangs indefinitely.

        This watchdog enforces a hard *timeout*-second budget from the outside.
        When the deadline expires we raise :class:`TimeoutError` and let the
        orphaned daemon thread unwind on its own — its httpx session will
        eventually raise on its own connect/read timeout, and as a daemon it
        cannot block process exit.
        """
        box: dict[str, Any] = {"value": None, "error": None}

        def _runner() -> None:
            try:
                box["value"] = call()
            except BaseException as exc:  # noqa: BLE001 — surface every failure
                box["error"] = exc

        thread = threading.Thread(
            target=_runner,
            daemon=True,
            name=f"hybrid-router-{label}-watchdog",
        )
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            msg = (
                f"{label} wall-clock watchdog expired after {timeout:.1f}s "
                "(request is still running but we stopped waiting)"
            )
            if on_status is not None:
                try:
                    on_status(msg)
                except Exception:
                    pass
            raise TimeoutError(msg)

        err = box["error"]
        if err is not None:
            raise err
        value = box["value"]
        if value is None:
            raise RuntimeError(
                f"{label} backend returned no result without raising — this is a bug"
            )
        return value

    def _complete_with_timeout(
        self,
        messages: list[dict],
        *,
        timeout: float,
        role: str = "orchestrator",
        force_backend: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> "RouterResponse":
        """Like :meth:`complete` but with a per-call timeout override (thread-safe)."""
        backend, routing_reason = self._select_backend(
            force_backend,
            on_status=on_status,
        )

        wrapped_on_chunk, progress_start = self._wrap_chunk_progress(
            on_chunk, on_status, backend
        )

        start = time.monotonic()
        try:
            if backend == "local":
                saved = self._timeout
                self._timeout = timeout
                try:
                    response = self._run_with_wall_clock_watchdog(
                        lambda: self._call_local(
                            messages, on_chunk=wrapped_on_chunk
                        ),
                        timeout=timeout,
                        label="local",
                        on_status=on_status,
                    )
                finally:
                    self._timeout = saved
            else:
                saved = self._timeout
                self._timeout = timeout
                try:
                    response = self._run_with_wall_clock_watchdog(
                        lambda: self._call_api(
                            messages, on_chunk=wrapped_on_chunk
                        ),
                        timeout=timeout,
                        label="api",
                        on_status=on_status,
                    )
                finally:
                    self._timeout = saved
        except Exception as exc:  # noqa: BLE001 — we re-raise after fallback attempt
            if self._should_fallback_to_api(
                exc, backend=backend, force_backend=force_backend
            ):
                elapsed_local = time.monotonic() - progress_start
                reason = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
                logger.warning(
                    "Local backend failed (%s) after %.1fs; retrying on API backend",
                    reason,
                    elapsed_local,
                )
                if on_status is not None:
                    on_status(
                        f"Local model failed after {elapsed_local:.0f}s ({reason}) — retrying on API backend"
                    )
                backend = "api"
                routing_reason = f"fallback_api_after_local_failure:{type(exc).__name__}"
                wrapped_on_chunk, progress_start = self._wrap_chunk_progress(
                    on_chunk, on_status, backend
                )
                start = time.monotonic()
                saved = self._timeout
                self._timeout = timeout
                try:
                    response = self._run_with_wall_clock_watchdog(
                        lambda: self._call_api(
                            messages, on_chunk=wrapped_on_chunk
                        ),
                        timeout=timeout,
                        label="api",
                        on_status=on_status,
                    )
                finally:
                    self._timeout = saved
            else:
                raise
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
                routing_reason=routing_reason,
            )
        )
        return result

    @staticmethod
    def _resolve_policy(policy: str | None) -> str:
        """Resolve policy from argument → env var → default."""
        if policy is not None:
            resolved = policy.strip()
        else:
            resolved = (os.getenv(_ENV_POLICY_VAR) or "api_preferred").strip()

        if resolved not in _VALID_POLICIES:
            raise ValueError(
                f"Unknown HybridRouter policy {resolved!r}. "
                f"Valid options: {sorted(_VALID_POLICIES)}"
            )
        return resolved
