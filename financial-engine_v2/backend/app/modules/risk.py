"""risk.py — Hybrid D1+D2 risk analysis module.

D1 (deterministic): Extracts risk items from TickerContext.risk_notes and
computes financial stress signals from financials. Always runs.

D2 (LLM synthesis, optional): Passes D1 output + RAG evidence to llama.cpp
for risk prioritization, interaction analysis, and narrative generation.
Only runs when llm_base_url is provided.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.base import (
    ArtifactSet, Completeness, EvidenceItem, ModuleHelpers, Narrative,
)
from app.modules.math_utils import ratio, round_or_none
from app.modules.ticker_context import FinancialSummary, RiskNote, TickerContext

logger = logging.getLogger(__name__)

# -- D2 prompt template --

_D2_PROMPT = """\
You are a financial risk analyst.

Given the D1 risk assessment and RAG evidence below, produce a JSON object with:
- "risk_items": array of 3-7 objects, each with:
    "category": one of "operational", "financial", "regulatory", "macro", "strategic"
    "severity": one of "critical", "high", "medium", "low"
    "description": concise risk description (1-2 sentences)
- "risk_interactions": array of 0-3 objects, each with:
    "risks": array of 2 category strings that interact
    "description": how these risks compound or reinforce each other
- "risk_summary": 2-4 sentence narrative summarizing the overall risk profile

D1 RISK ITEMS:
{d1_risk_items}

FINANCIAL STRESS SIGNALS:
{stress_signals}

RAG EVIDENCE:
{rag_evidence}

Output ONLY valid JSON matching the schema above.
"""

# -- Stress signal thresholds --

_CASH_CONVERSION_LOW = 0.5
_REVENUE_DECLINE_THRESHOLD = -0.10
_LEVERAGE_HIGH = 3.0
_CASH_RUNWAY_LOW_QUARTERS = 4.0


# -- D1 helpers --


def _extract_risk_items_from_notes(
    risk_notes: tuple[RiskNote, ...],
) -> list[dict[str, str]]:
    """Extract individual risk text items from risk notes."""
    items: list[dict[str, str]] = []
    for note in risk_notes:
        if note.risk_summary:
            items.append({
                "text": note.risk_summary,
                "source_type": "risk_summary",
                "document_id": note.document_id,
            })
        for bullet in note.risk_bullets:
            text = str(bullet).strip()
            if text:
                items.append({
                    "text": text,
                    "source_type": "risk_bullet",
                    "document_id": note.document_id,
                })
    return items


def _compute_stress_signals(fin: FinancialSummary) -> list[dict[str, Any]]:
    """Compute financial stress signals from the latest period + trends."""
    signals: list[dict[str, Any]] = []
    latest = fin.latest
    if latest is None:
        return signals

    if latest.cash_conversion is not None and latest.cash_conversion < _CASH_CONVERSION_LOW:
        signals.append({
            "signal": "low_cash_conversion", "severity": "medium",
            "value": round_or_none(latest.cash_conversion),
            "threshold": _CASH_CONVERSION_LOW,
            "detail": f"Cash conversion {latest.cash_conversion:.2f} below {_CASH_CONVERSION_LOW}",
        })

    trends = fin.trends
    if trends.available and trends.revenue_yoy is not None and trends.revenue_yoy < _REVENUE_DECLINE_THRESHOLD:
        signals.append({
            "signal": "revenue_declining", "severity": "high",
            "value": round_or_none(trends.revenue_yoy),
            "threshold": _REVENUE_DECLINE_THRESHOLD,
            "detail": f"Revenue declined {trends.revenue_yoy:.1%} YoY",
        })

    if latest.ebit is not None and latest.ebit > 0:
        leverage = ratio(latest.net_debt, latest.ebit)
        if leverage is not None and leverage > _LEVERAGE_HIGH:
            signals.append({
                "signal": "high_leverage", "severity": "high",
                "value": round_or_none(leverage),
                "threshold": _LEVERAGE_HIGH,
                "detail": f"Net debt/EBIT ratio {leverage:.1f}x exceeds {_LEVERAGE_HIGH}x",
            })

    if latest.fcf is not None and latest.fcf < 0:
        signals.append({
            "signal": "negative_fcf", "severity": "medium",
            "value": round_or_none(latest.fcf), "threshold": 0,
            "detail": f"Free cash flow is negative: {latest.fcf:,.0f}",
        })

    if (
        latest.operating_cf is not None and latest.operating_cf < 0
        and latest.cash_end is not None and latest.cash_end > 0
    ):
        runway = latest.cash_end / abs(latest.operating_cf)
        if runway < _CASH_RUNWAY_LOW_QUARTERS:
            signals.append({
                "signal": "low_cash_runway", "severity": "critical",
                "value": round_or_none(runway, 1),
                "threshold": _CASH_RUNWAY_LOW_QUARTERS,
                "detail": f"Cash runway ~{runway:.1f} quarters at current burn rate",
            })
    return signals


def _compute_risk_score(
    risk_items: list[dict[str, str]], stress_signals: list[dict[str, Any]],
) -> int:
    """Aggregate risk score 0-100 from item counts + signal severities."""
    score = min(len(risk_items) * 5, 50)
    weights = {"critical": 20, "high": 12, "medium": 6, "low": 3}
    for sig in stress_signals:
        score += weights.get(sig.get("severity", "low"), 3)
    return min(score, 100)


def _compute_trajectory(fin: FinancialSummary) -> str:
    """Risk trajectory from financial trends (improving/stable/deteriorating)."""
    trends = fin.trends
    if not trends.available:
        return "insufficient_data"
    deltas = [trends.revenue_yoy, trends.ebit_yoy, trends.fcf_yoy]
    improving = sum(1 for d in deltas if d is not None and d > 0.05)
    deteriorating = sum(1 for d in deltas if d is not None and d < -0.05)
    if improving > deteriorating:
        return "improving"
    if deteriorating > improving:
        return "deteriorating"
    return "stable"


# -- D2 LLM synthesis --


def _build_d2_prompt(
    risk_items: list[dict[str, str]],
    stress_signals: list[dict[str, Any]],
    rag_evidence: str,
) -> str:
    """Format the D2 prompt with D1 outputs."""
    item_lines = "\n".join(
        f"- [{item.get('source_type', 'unknown')}] {item['text']}"
        for item in risk_items
    ) or "(none)"
    signal_lines = "\n".join(
        f"- {sig['signal']}: {sig['detail']}" for sig in stress_signals
    ) or "(none detected)"
    return _D2_PROMPT.format(
        d1_risk_items=item_lines,
        stress_signals=signal_lines,
        rag_evidence=rag_evidence or "(no RAG evidence available)",
    )


def _collect_rag_evidence(ctx: TickerContext) -> str:
    """Gather RAG hit texts from context for D2 prompt (capped at 15)."""
    lines: list[str] = []
    for result in ctx.rag_results:
        for hit in result.hits:
            text = hit.text.strip()
            if text:
                lines.append(f"- [{result.label}] {text[:500]}")
    return "\n".join(lines[:15])


def _run_d2_synthesis(
    risk_items: list[dict[str, str]],
    stress_signals: list[dict[str, Any]],
    ctx: TickerContext,
    llm_base_url: str,
    llm_model: str,
) -> Narrative | None:
    """Run LLM synthesis and return a Narrative, or None on failure."""
    from app.services.llamacpp_runtime import generate_json_llamacpp

    rag_evidence = _collect_rag_evidence(ctx)
    prompt = _build_d2_prompt(risk_items, stress_signals, rag_evidence)
    try:
        result = generate_json_llamacpp(
            base_url=llm_base_url, model=llm_model,
            prompt=prompt, timeout=120.0,
        )
    except Exception as exc:
        logger.warning("Risk D2 synthesis failed: %s", exc)
        return None
    if not isinstance(result, dict):
        logger.warning("Risk D2 returned non-dict: %s", type(result))
        return None
    return Narrative(
        summary=str(result.get("risk_summary") or ""),
        detail={
            "risk_items": result.get("risk_items", []),
            "risk_interactions": result.get("risk_interactions", []),
        },
        model_id=llm_model,
        prompt_hash=Narrative.hash_prompt(prompt),
    )


# -- Module class --


class RiskModule(ModuleHelpers):
    """Hybrid D1+D2 risk analysis module.

    D1 always runs (deterministic). D2 runs only when llm_base_url is provided.
    """

    def __init__(
        self, *, llm_base_url: str | None = None, llm_model: str = "",
    ) -> None:
        self._llm_base_url = llm_base_url
        self._llm_model = llm_model

    @property
    def name(self) -> str:
        return "risk"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"financials", "risk_notes"})

    def run(self, context: TickerContext) -> ArtifactSet:
        ticker = context.ticker
        warnings: list[str] = []

        # Minimum viability — financials missing is FAILED
        missing = self._check_minimum_viability(
            context, frozenset({"financials", "risk_notes"}),
        )
        if "financials" in missing:
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no financial data available"},
                warnings=("no_financials",),
            )

        # D1: Extract risk items
        risk_items = _extract_risk_items_from_notes(context.risk_notes)
        if not risk_items:
            warnings.append("no_risk_notes")

        # D1: Compute stress signals
        stress_signals: list[dict[str, Any]] = []
        if context.financials is not None:
            stress_signals = _compute_stress_signals(context.financials)

        # D1: Aggregate score and trajectory
        risk_score = _compute_risk_score(risk_items, stress_signals)
        trajectory = (
            _compute_trajectory(context.financials)
            if context.financials is not None else "insufficient_data"
        )

        structured: dict[str, Any] = {
            "risk_items": risk_items,
            "stress_signals": stress_signals,
            "risk_score": risk_score,
            "trajectory": trajectory,
            "d2_available": self._llm_base_url is not None,
        }

        # D2: Optional LLM synthesis
        narrative: Narrative | None = None
        if self._llm_base_url is not None:
            narrative = _run_d2_synthesis(
                risk_items, stress_signals, context,
                self._llm_base_url, self._llm_model,
            )
            if narrative is None:
                warnings.append("d2_synthesis_failed")

        # Completeness
        completeness = (
            Completeness.PARTIAL if not risk_items and not stress_signals
            else Completeness.COMPLETE
        )

        # Evidence chain
        evidence_items: list[EvidenceItem] = []
        for item in risk_items:
            evidence_items.append(EvidenceItem(
                evidence_id=f"risk_{ticker}_{item.get('document_id', 'unknown')}",
                source_type="financial_statement",
                content=item["text"][:200],
                source_id=item.get("document_id", ""),
            ))
        for sig in stress_signals:
            evidence_items.append(EvidenceItem(
                evidence_id=f"stress_{ticker}_{sig['signal']}",
                source_type="computed",
                content=sig["detail"],
            ))

        return self._build_artifact(
            ticker=ticker, module_name=self.name,
            completeness=completeness, structured=structured,
            narrative=narrative, evidence=tuple(evidence_items),
            warnings=tuple(warnings),
        )
