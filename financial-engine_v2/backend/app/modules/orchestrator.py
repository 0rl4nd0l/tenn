"""orchestrator.py — Run all analysis modules for a ticker.

Instantiates the 7-module registry, executes them in dependency order,
writes artifacts, and returns results. A failing module does not block
others.

Dependency order:
  1. balance_sheet (first — no upstream deps)
  2. roic, risk, valuation, catalysts, sentiment (independent of each other)
  3. moat (last — benefits from upstream context)
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.modules.artifacts import write_artifact
from app.modules.balance_sheet import BalanceSheetModule
from app.modules.base import AnalysisModule, ArtifactSet, Completeness
from app.modules.catalysts import CatalystsModule
from app.modules.moat import MoatModule
from app.modules.risk import RiskModule
from app.modules.roic import ROICModule
from app.modules.sentiment import SentimentModule
from app.modules.ticker_context import ContextRequest, RAGQuerySpec, TickerContext
from app.modules.valuation import ValuationModule

logger = logging.getLogger(__name__)

# Dependency tiers — executed in order; modules within a tier are independent.
_TIERS: tuple[tuple[str, ...], ...] = (
    ("balance_sheet",),
    ("roic", "risk", "valuation", "catalysts", "sentiment"),
    ("moat",),
)


class AnalysisOrchestrator:
    """Instantiates and runs all analysis modules for a single ticker."""

    def __init__(
        self,
        *,
        llm_base_url: str | None = None,
        llm_model: str = "",
        reports_root: str | None = None,
    ) -> None:
        self._llm_base_url = llm_base_url
        self._llm_model = llm_model
        self._reports_root = reports_root
        self._registry = self._build_registry()

    def _build_registry(self) -> dict[str, AnalysisModule]:
        """Instantiate all 7 modules. Hybrid modules receive LLM config."""
        llm_kwargs: dict[str, Any] = {
            "llm_base_url": self._llm_base_url,
            "llm_model": self._llm_model,
        }
        return {
            "balance_sheet": BalanceSheetModule(),
            "roic": ROICModule(),
            "valuation": ValuationModule(),
            "risk": RiskModule(**llm_kwargs),
            "catalysts": CatalystsModule(**llm_kwargs),
            "sentiment": SentimentModule(),
            "moat": MoatModule(**llm_kwargs),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(
        self, ticker: str, context: TickerContext,
    ) -> list[ArtifactSet]:
        """Run all modules in dependency order, write artifacts, return results."""
        results: list[ArtifactSet] = []
        for tier in _TIERS:
            for module_name in tier:
                result = self._run_one(module_name, context)
                results.append(result)
        return results

    def run_module(
        self, module_name: str, context: TickerContext,
    ) -> ArtifactSet:
        """Run a single module by name."""
        return self._run_one(module_name, context)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run_one(
        self, module_name: str, context: TickerContext,
    ) -> ArtifactSet:
        """Execute a single module, catch exceptions, write artifact."""
        module = self._registry.get(module_name)
        if module is None:
            logger.error("Unknown module: %s", module_name)
            return ArtifactSet(
                ticker=context.ticker,
                module_name=module_name,
                completeness=Completeness.FAILED,
                structured={"error": f"unknown module: {module_name}"},
            )

        logger.info("Running module %s for %s", module_name, context.ticker)
        try:
            result = module.run(context)
        except Exception:
            logger.exception(
                "Module %s failed for %s", module_name, context.ticker,
            )
            result = ArtifactSet(
                ticker=context.ticker,
                module_name=module_name,
                completeness=Completeness.FAILED,
                structured={"error": "unhandled exception"},
                warnings=("module_raised_exception",),
            )

        # Write artifact to disk
        try:
            path = write_artifact(result, reports_root=self._reports_root)
            logger.info("Wrote artifact: %s", path)
        except Exception:
            logger.exception(
                "Failed to write artifact for %s/%s",
                context.ticker, module_name,
            )

        return result


# ------------------------------------------------------------------
# Merged context request
# ------------------------------------------------------------------


def _merge_context_requests(
    modules: dict[str, AnalysisModule],
) -> ContextRequest:
    """Build a single ContextRequest that satisfies all modules."""
    needs_financials = False
    needs_risk_notes = False
    needs_documents = False
    needs_price = False
    rag_queries: list[RAGQuerySpec] = []
    seen_labels: set[str] = set()

    for module in modules.values():
        reqs = module.requires
        if "financials" in reqs:
            needs_financials = True
        if "risk_notes" in reqs:
            needs_risk_notes = True
        if "documents" in reqs:
            needs_documents = True
        if "price" in reqs:
            needs_price = True
        # Collect RAG queries from modules that declare them
        module_rag = getattr(module, "rag_queries", ())
        for spec in module_rag:
            if spec.label not in seen_labels:
                rag_queries.append(spec)
                seen_labels.add(spec.label)

    return ContextRequest(
        needs_financials=needs_financials,
        needs_risk_notes=needs_risk_notes,
        needs_documents=needs_documents,
        needs_price=needs_price,
        rag_queries=tuple(rag_queries),
    )


# ------------------------------------------------------------------
# High-level entry point
# ------------------------------------------------------------------


def analyse_ticker(
    ticker: str,
    *,
    db: Session,
    llm_base_url: str | None = None,
    llm_model: str = "",
    reports_root: str | None = None,
) -> list[ArtifactSet]:
    """Load context + run all modules. Returns list of ArtifactSet results."""
    orchestrator = AnalysisOrchestrator(
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        reports_root=reports_root,
    )

    # Build merged context request from all module requirements
    request = _merge_context_requests(orchestrator._registry)

    # Load context (context_loader may not exist yet)
    try:
        from app.modules.context_loader import TickerContextLoader
        from app.services.analysis_rag_adapter import analysis_rag_query
    except ImportError:
        logger.error(
            "analysis context dependencies not available — cannot load "
            "TickerContext for %s. Implement app.modules.context_loader."
            "TickerContextLoader and app.services.analysis_rag_adapter."
            "analysis_rag_query.",
            ticker,
        )
        raise ImportError(
            "app.modules.context_loader.TickerContextLoader and "
            "app.services.analysis_rag_adapter.analysis_rag_query are required "
            "but not yet implemented."
        )

    loader = TickerContextLoader(rag_fn=analysis_rag_query)
    context = loader.load(ticker=ticker, db=db, request=request)
    return orchestrator.run_all(ticker, context)
