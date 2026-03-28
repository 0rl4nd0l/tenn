"""analysis.py — API routes for the 6-module analysis system.

POST /api/analysis/{ticker}  — run analysis modules, return results.
GET  /api/analysis/{ticker}  — read latest artifacts from disk.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes import require_api_key
from app.core.config import settings
from app.core.db import get_db
from app.modules.artifacts import read_artifact
from app.modules.base import ArtifactSet, Completeness
from app.modules.context_loader import TickerContextLoader
from app.modules.orchestrator import AnalysisOrchestrator, _merge_context_requests

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

ALL_MODULES = ("balance_sheet", "roic", "risk", "valuation", "catalysts", "moat")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ModuleResult(BaseModel):
    module: str
    completeness: str
    structured: dict[str, Any]
    warnings: list[str] = []


class AnalysisRunResponse(BaseModel):
    ticker: str
    modules_run: int
    results: list[ModuleResult]


class AnalysisReadResponse(BaseModel):
    ticker: str
    modules_found: int
    artifacts: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _artifact_to_result(a: ArtifactSet) -> ModuleResult:
    return ModuleResult(
        module=a.module_name,
        completeness=a.completeness.value,
        structured=a.structured,
        warnings=list(a.warnings),
    )


# ---------------------------------------------------------------------------
# POST — run analysis
# ---------------------------------------------------------------------------


@router.post(
    "/analysis/{ticker}",
    response_model=AnalysisRunResponse,
    dependencies=[Depends(require_api_key)],
)
def run_analysis(
    ticker: str,
    modules: str | None = Query(
        default=None,
        description="Comma-separated module names to run (default: all)",
    ),
    db: Session = Depends(get_db),
) -> AnalysisRunResponse:
    """Run analysis modules for *ticker* and return per-module results."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")

    requested = _parse_modules(modules)

    llm_url = str(settings.llamacpp_url or "").strip() or None
    llm_model = str(settings.extract_model or "").strip()

    orchestrator = AnalysisOrchestrator(
        llm_base_url=llm_url,
        llm_model=llm_model,
    )

    # Build context request from whichever modules we intend to run.
    registry = orchestrator._registry
    if requested:
        registry = {k: v for k, v in registry.items() if k in requested}
    request = _merge_context_requests(registry)

    loader = TickerContextLoader()
    try:
        context = loader.load(ticker=ticker, request=request, db=db)
    except Exception as exc:
        logger.exception("Failed to load context for %s", ticker)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if requested:
        results = [orchestrator.run_module(m, context) for m in requested]
    else:
        results = orchestrator.run_all(ticker, context)

    return AnalysisRunResponse(
        ticker=ticker,
        modules_run=len(results),
        results=[_artifact_to_result(r) for r in results],
    )


# ---------------------------------------------------------------------------
# GET — read latest artifacts
# ---------------------------------------------------------------------------


@router.get(
    "/analysis/{ticker}",
    response_model=AnalysisReadResponse,
    dependencies=[Depends(require_api_key)],
)
def read_analysis(ticker: str) -> AnalysisReadResponse:
    """Read the latest on-disk artifacts for *ticker*."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")

    artifacts: dict[str, Any] = {}
    for module_name in ALL_MODULES:
        data = read_artifact(ticker, module_name)
        if data is not None:
            artifacts[module_name] = data

    return AnalysisReadResponse(
        ticker=ticker,
        modules_found=len(artifacts),
        artifacts=artifacts,
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _parse_modules(raw: str | None) -> list[str]:
    """Parse comma-separated module list; validate names. Empty = run all."""
    if not raw:
        return []
    names = [n.strip().lower() for n in raw.split(",") if n.strip()]
    unknown = [n for n in names if n not in ALL_MODULES]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown modules: {', '.join(unknown)}. "
            f"Valid: {', '.join(ALL_MODULES)}",
        )
    return names
