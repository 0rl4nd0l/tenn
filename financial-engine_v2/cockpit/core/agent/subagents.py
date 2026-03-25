"""SubAgentSpawner — background asyncio agents with lifecycle management.

Design constraints
------------------
- Max concurrent local: 1 (single GPU, ``--models-max 1``)
- Max spawn depth: 1 (no recursive sub-spawning)
- Timeout: configurable, default 300 s
- Tool access: same as orchestrator minus ``spawn_agent``
- Memory: if ``memory_store`` and ``ticker`` provided, appends findings to
  ``research/<TICKER>.md`` via MemoryStore.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cockpit.core.agent.memory.store import MemoryStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

MAX_SPAWN_DEPTH = 1  # depth >= MAX_SPAWN_DEPTH is rejected


class SubAgentType(str, Enum):
    """Recognised sub-agent roles."""

    RESEARCHER = "researcher"
    AUDITOR = "auditor"
    COMPARATOR = "comparator"
    PIPELINE_RUNNER = "pipeline_runner"


@dataclass
class SubAgentResult:
    """Result returned by a completed sub-agent run."""

    agent_type: str
    success: bool
    result: str
    error: str | None = None
    tool_calls_made: int = 0
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# System-prompt templates (role-specific)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "researcher": (
        "You are a financial research analyst specialising in ASX-listed companies. "
        "Your goal is to retrieve, synthesise, and summarise financial data with precision. "
        "Focus on quantitative findings: revenue, EBITDA, net profit, cashflow, and guidance. "
        "Be concise and cite the source document where possible."
    ),
    "auditor": (
        "You are a financial auditor. Your goal is to verify the accuracy and consistency "
        "of reported financial figures. Check for discrepancies between headline numbers and "
        "detailed breakdowns. Flag any anomalies, restatements, or qualification notes. "
        "Produce a structured verification report."
    ),
    "comparator": (
        "You are a comparative financial analyst. Your goal is to compare financial metrics "
        "across multiple companies or reporting periods. Identify material differences, "
        "highlight relative strengths and weaknesses, and provide context where applicable. "
        "Use tables where clarity is improved."
    ),
    "pipeline_runner": (
        "You are a data pipeline orchestrator. Your goal is to describe the steps required "
        "to run or validate a data extraction pipeline, diagnose failures, and summarise "
        "pipeline output. Be precise about configuration, inputs, and expected outputs."
    ),
}

_FALLBACK_SYSTEM_PROMPT = (
    "You are a specialised financial sub-agent. Complete the assigned task accurately "
    "and concisely, citing relevant evidence."
)


# ---------------------------------------------------------------------------
# SubAgentSpawner
# ---------------------------------------------------------------------------


class SubAgentSpawner:
    """Spawn background asyncio agents with GPU concurrency control.

    Parameters
    ----------
    llm_client:
        A ``LlamaCppClient`` (or compatible) instance.
        Must implement ``chat(prompt, timeout, prior_messages) -> str``.
    tool_executor:
        Optional tool executor (same as orchestrator, minus ``spawn_agent``).
        Reserved for future use — not yet invoked inside agents.
    memory_store:
        Optional ``MemoryStore`` instance.  When provided *and* a ``ticker``
        is passed to ``spawn()``, findings are appended to
        ``research/<TICKER>.md``.
    max_concurrent_local:
        Semaphore size for local GPU calls.  Default 1 (single GPU).
    timeout_seconds:
        Per-agent wall-clock timeout.  Default 300 s.
    """

    def __init__(
        self,
        llm_client: Any,
        tool_executor: Any = None,
        memory_store: "MemoryStore | None" = None,
        max_concurrent_local: int = 1,
        timeout_seconds: float = 300.0,
    ) -> None:
        self._llm = llm_client
        self._tool_executor = tool_executor
        self._memory = memory_store
        self._timeout = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent_local)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def spawn(
        self,
        agent_type: "SubAgentType | str",
        task: str,
        ticker: str | None = None,
        spawn_depth: int = 0,
    ) -> SubAgentResult:
        """Spawn a sub-agent and await its result.

        Parameters
        ----------
        agent_type:
            One of ``SubAgentType`` (or equivalent string).
        task:
            Natural-language task description passed to the agent.
        ticker:
            Optional ASX ticker; used for memory storage key.
        spawn_depth:
            Recursion depth.  Set by the orchestrator; end-users pass 0.
            Depth >= 1 is rejected to prevent recursive spawning.
        """
        agent_type_str = agent_type.value if isinstance(agent_type, SubAgentType) else str(agent_type)

        # Depth guard — no recursive sub-spawning
        if spawn_depth >= MAX_SPAWN_DEPTH:
            return SubAgentResult(
                agent_type=agent_type_str,
                success=False,
                result="",
                error=f"spawn depth {spawn_depth} exceeds maximum ({MAX_SPAWN_DEPTH - 1}); recursive spawning is not allowed",
            )

        start = time.monotonic()
        try:
            async with self._semaphore:
                result_text = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self._run_sync, agent_type_str, task
                    ),
                    timeout=self._timeout,
                )
        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.warning("sub-agent %s timed out after %.1fs", agent_type_str, self._timeout)
            return SubAgentResult(
                agent_type=agent_type_str,
                success=False,
                result="",
                error=f"timeout: agent did not complete within {self._timeout:.1f}s",
                duration_ms=elapsed,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error("sub-agent %s failed: %s", agent_type_str, exc)
            return SubAgentResult(
                agent_type=agent_type_str,
                success=False,
                result="",
                error=str(exc),
                duration_ms=elapsed,
            )

        elapsed = int((time.monotonic() - start) * 1000)

        # Persist findings to memory when store + ticker are available
        if self._memory is not None and ticker:
            try:
                heading = f"\n## [{agent_type_str.upper()}] {task}\n"
                self._memory.append_research(ticker, heading + result_text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("failed to write research memory for %s: %s", ticker, exc)

        return SubAgentResult(
            agent_type=agent_type_str,
            success=True,
            result=result_text,
            error=None,
            duration_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _run_sync(self, agent_type: str, task: str) -> str:
        """Synchronous LLM call executed inside a thread-pool executor."""
        system_prompt = self._build_system_prompt(agent_type)
        prior = [{"role": "system", "content": system_prompt}]
        response: str = self._llm.chat(
            prompt=task,
            timeout=self._timeout,
            prior_messages=prior,
        )
        return response

    def _build_system_prompt(self, agent_type: str) -> str:
        """Return a role-specific system prompt for *agent_type*."""
        key = agent_type.lower() if isinstance(agent_type, str) else str(agent_type)
        return _SYSTEM_PROMPTS.get(key, _FALLBACK_SYSTEM_PROMPT)
