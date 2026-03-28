"""base.py — Analysis module contract.

Defines the Protocol that all analysis modules implement, the data structures
they consume and produce, and the completeness/evidence types that enable
audit-ready artifact output.

Design decisions (from architecture debate):
  - Protocol (not ABC): existing code is function-oriented; structural subtyping
    lets adapters satisfy the interface by shape alone.
  - ArtifactSet carries D1 (structured) + optional D2 (narrative) + evidence chain.
  - Completeness enum reconciles fail-fast contract with real-world data sparsity.
  - ModuleHelpers mixin is optional; orchestrator depends only on the Protocol.
"""
from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Completeness(enum.Enum):
    """Outcome status for a module run.

    COMPLETE -- all expected fields populated, no data gaps.
    PARTIAL  -- module ran but some metrics are None due to missing data.
    FAILED   -- minimum-viability check failed; no meaningful output.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Evidence and narrative types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of evidence supporting an artifact claim."""

    evidence_id: str
    source_type: str  # "financial_statement" | "rag_hit" | "news" | "computed"
    content: str
    source_id: str = ""
    confidence: float = 1.0


@dataclass(frozen=True)
class Narrative:
    """LLM-generated qualitative analysis (D2 layer).

    Only produced by hybrid modules (risk, moat, catalysts).
    Pure-computation modules return narrative=None.
    """

    summary: str
    detail: dict[str, Any]
    model_id: str
    prompt_hash: str
    cached: bool = False

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# ArtifactSet — the universal return type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactSet:
    """The output of a single module run.

    Every module returns exactly one ArtifactSet. The orchestrator collects
    these, writes them as artifacts, and optionally feeds them to downstream
    consumers (report generator, portfolio module).
    """

    ticker: str
    module_name: str
    completeness: Completeness
    structured: dict[str, Any]
    evidence: tuple[EvidenceItem, ...] = ()
    narrative: Narrative | None = None
    warnings: tuple[str, ...] = ()
    computed_at: str = ""
    artifact_path: str | None = None

    def __post_init__(self) -> None:
        if not self.computed_at:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            object.__setattr__(self, "computed_at", ts)


# ---------------------------------------------------------------------------
# Module Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AnalysisModule(Protocol):
    """The contract that every analysis module must satisfy.

    Modules are stateless. All state flows through TickerContext (input)
    and ArtifactSet (output). No side effects beyond logging.
    """

    @property
    def name(self) -> str:
        """Unique module identifier (e.g., 'balance_sheet', 'risk')."""
        ...

    @property
    def requires(self) -> frozenset[str]:
        """Data dependencies from TickerContext.

        Valid: 'financials', 'risk_notes', 'documents', 'price',
               'rag_results'.
        """
        ...

    def run(self, context: Any) -> ArtifactSet:
        """Execute the analysis. Context is a TickerContext (imported separately
        to avoid circular imports)."""
        ...


# ---------------------------------------------------------------------------
# Module helpers mixin (optional)
# ---------------------------------------------------------------------------


class ModuleHelpers:
    """Optional mixin providing shared utility methods.

    The orchestrator does NOT depend on this — it depends only on
    AnalysisModule (Protocol).
    """

    def _build_artifact(
        self,
        *,
        ticker: str,
        module_name: str,
        completeness: Completeness,
        structured: dict[str, Any],
        narrative: Narrative | None = None,
        evidence: tuple[EvidenceItem, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> ArtifactSet:
        return ArtifactSet(
            ticker=ticker,
            module_name=module_name,
            completeness=completeness,
            structured=structured,
            narrative=narrative,
            evidence=evidence,
            warnings=warnings,
        )

    def _check_minimum_viability(
        self,
        context: Any,
        required_fields: frozenset[str],
    ) -> list[str]:
        """Check required TickerContext fields are non-empty.

        Returns list of missing field names. Empty = all present.
        """
        missing = []
        for f in required_fields:
            val = getattr(context, f, None)
            if val is None:
                missing.append(f)
            elif isinstance(val, (list, tuple)) and len(val) == 0:
                missing.append(f)
        return missing
