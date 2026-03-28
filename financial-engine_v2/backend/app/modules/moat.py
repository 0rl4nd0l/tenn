"""moat.py — Hybrid D1+D2 moat analysis module.

Quantitative moat signals (D1) from financial periods, plus optional
LLM-driven qualitative assessment (D2) using the Morningstar 5-source
moat framework.  D1 always runs.  D2 requires an LLM endpoint.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.modules.base import (
    ArtifactSet, Completeness, EvidenceItem, ModuleHelpers, Narrative,
)
from app.modules.math_utils import (
    mean, pct_change, ratio, round_or_none, safe_abs, safe_sub, stdev,
)
from app.modules.ticker_context import PeriodMetrics, TickerContext

logger = logging.getLogger(__name__)

_STRENGTH_SCORES: dict[str, int] = {"strong": 20, "moderate": 12, "weak": 5, "absent": 0}
_SOURCE_KEYS = (
    "network_effects", "switching_costs", "cost_advantages",
    "intangible_assets", "efficient_scale",
)

_MOAT_PROMPT_TEMPLATE = """\
You are a financial analyst specialising in competitive moat assessment.\
 Assess the company's economic moat using the Morningstar 5-source framework.

## Quantitative signals
{quantitative_signals}

## Documentary evidence (from filings)
{rag_evidence}

## Instructions
For each source (network_effects, switching_costs, cost_advantages,\
 intangible_assets, efficient_scale) assess present (bool), strength\
 (strong/moderate/weak/absent), evidence_summary (1-2 sentences).

Overall: moat_classification (none/narrow/wide — wide: 2+ strong or\
 1 strong + 2 moderate; narrow: 1 strong or 2+ moderate),\
 moat_score 0-100 (each source: strong=20, moderate=12, weak=5, absent=0),\
 moat_confidence (high/medium/low), moat_trend (strengthening/stable/eroding),\
 moat_summary (3-4 sentences).

Return ONLY valid JSON:
{{"sources": {{"network_effects": {{"present": bool, "strength": str,\
 "evidence_summary": str}}, ...}},\
 "moat_classification": str, "moat_score": int,\
 "moat_confidence": str, "moat_trend": str, "moat_summary": str}}
"""

# ---------------------------------------------------------------------------
# D1: Quantitative moat signals
# ---------------------------------------------------------------------------

def _assess_margin_stability(margins: list[float | None]) -> dict[str, Any]:
    sd, avg = stdev(margins), mean(margins)
    if sd is None or avg is None:
        return {"stdev": None, "mean": None, "assessment": "insufficient_data"}
    if sd < 0.03 and avg > 0.10:
        a = "stable"
    elif sd >= 0.03:
        a = "volatile"
    else:
        a = "low"
    return {"stdev": round_or_none(sd), "mean": round_or_none(avg), "assessment": a}


def _assess_roic_proxy(periods: tuple[PeriodMetrics, ...]) -> dict[str, Any]:
    val = ratio(periods[-1].ebit, periods[-1].revenue)
    if val is None:
        return {"value": None, "assessment": "insufficient_data"}
    a = "high" if val > 0.15 else ("low" if val < 0.05 else "stable")
    return {"value": round_or_none(val), "assessment": a}


def _assess_capex_intensity(periods: tuple[PeriodMetrics, ...]) -> dict[str, Any]:
    val = ratio(safe_abs(periods[-1].capex), periods[-1].revenue)
    if val is None:
        return {"value": None, "assessment": "insufficient_data"}
    a = "low" if val < 0.05 else ("high" if val > 0.15 else "stable")
    return {"value": round_or_none(val), "assessment": a}


def _assess_revenue_persistence(periods: tuple[PeriodMetrics, ...]) -> dict[str, Any]:
    if len(periods) < 2:
        return {"value": None, "assessment": "insufficient_data"}
    yoys = [y for i in range(1, len(periods))
            if (y := pct_change(periods[i].revenue, periods[i - 1].revenue)) is not None]
    if not yoys:
        return {"value": None, "assessment": "insufficient_data"}
    worst = min(yoys)
    a = "stable" if worst > -0.05 else ("volatile" if worst < -0.15 else "low")
    return {"value": round_or_none(worst), "assessment": a}


def _assess_cash_conversion_consistency(conversions: list[float | None]) -> dict[str, Any]:
    sd = stdev(conversions)
    if sd is None:
        return {"stdev": None, "assessment": "insufficient_data"}
    return {"stdev": round_or_none(sd), "assessment": "stable" if sd < 0.15 else "volatile"}


def _assess_fcf_margin_trend(periods: tuple[PeriodMetrics, ...]) -> dict[str, Any]:
    fm = [p.fcf_margin for p in periods if p.fcf_margin is not None]
    if len(fm) < 2:
        return {"value": None, "assessment": "insufficient_data"}
    delta = safe_sub(fm[-1], fm[0])
    if delta is None:
        return {"value": None, "assessment": "insufficient_data"}
    a = "high" if delta > 0.02 else ("low" if delta < -0.02 else "stable")
    return {"value": round_or_none(delta), "assessment": a}


def _compute_d1_signals(periods: tuple[PeriodMetrics, ...]) -> dict[str, Any]:
    return {
        "margin_stability": _assess_margin_stability([p.ebit_margin for p in periods]),
        "roic_proxy": _assess_roic_proxy(periods),
        "capex_intensity": _assess_capex_intensity(periods),
        "revenue_persistence": _assess_revenue_persistence(periods),
        "cash_conversion_consistency": _assess_cash_conversion_consistency(
            [p.cash_conversion for p in periods]),
        "fcf_margin_trend": _assess_fcf_margin_trend(periods),
    }

# ---------------------------------------------------------------------------
# D2: LLM-driven moat assessment
# ---------------------------------------------------------------------------

def _format_rag_evidence(context: TickerContext) -> str:
    rag = context.rag_by_label("competitive_position")
    if rag is None or not rag.hits:
        return "No documentary evidence available."
    return "\n".join(f"- [{h.score:.2f}] {h.text[:500]}" for h in rag.hits[:6])


def _classify_moat(sources: dict[str, Any]) -> str:
    strengths = [s.get("strength", "absent") for s in sources.values() if isinstance(s, dict)]
    sc, mc = strengths.count("strong"), strengths.count("moderate")
    if sc >= 2 or (sc >= 1 and mc >= 2):
        return "wide"
    if sc >= 1 or mc >= 2:
        return "narrow"
    return "none"


def _compute_moat_score(sources: dict[str, Any]) -> int:
    return sum(
        _STRENGTH_SCORES.get(str(sources.get(k, {}).get("strength", "absent")).lower(), 0)
        for k in _SOURCE_KEYS if isinstance(sources.get(k), dict)
    )


def _validate_llm_response(raw: dict[str, Any]) -> dict[str, Any]:
    sources = raw.get("sources", {})
    if not isinstance(sources, dict):
        sources = {}
    for key in _SOURCE_KEYS:
        if key not in sources or not isinstance(sources[key], dict):
            sources[key] = {"present": False, "strength": "absent", "evidence_summary": "Not assessed."}
        else:
            src = sources[key]
            src.setdefault("present", False)
            strength = str(src.get("strength", "absent")).lower()
            src["strength"] = strength if strength in _STRENGTH_SCORES else "absent"
            src.setdefault("evidence_summary", "")
    # Deterministic overrides — do not trust LLM arithmetic
    confidence = str(raw.get("moat_confidence", "low")).lower()
    trend = str(raw.get("moat_trend", "stable")).lower()
    return {
        "sources": sources,
        "moat_classification": _classify_moat(sources),
        "moat_score": _compute_moat_score(sources),
        "moat_confidence": confidence if confidence in ("high", "medium", "low") else "low",
        "moat_trend": trend if trend in ("strengthening", "stable", "eroding") else "stable",
        "moat_summary": str(raw.get("moat_summary", "")),
    }


def _run_d2_synthesis(
    *, ticker: str, d1_signals: dict[str, Any], context: TickerContext,
    llm_base_url: str, llm_model: str,
) -> tuple[dict[str, Any], Narrative]:
    from app.services.llamacpp_runtime import generate_json_llamacpp
    prompt = _MOAT_PROMPT_TEMPLATE.format(
        quantitative_signals=json.dumps(d1_signals, indent=2, default=str),
        rag_evidence=_format_rag_evidence(context),
    )
    prompt_hash = Narrative.hash_prompt(prompt)
    raw = generate_json_llamacpp(
        base_url=llm_base_url, model=llm_model, prompt=prompt, timeout=120.0,
    )
    if not isinstance(raw, dict):
        raise ValueError(f"LLM returned non-dict for moat assessment: {type(raw)}")
    validated = _validate_llm_response(raw)
    narrative = Narrative(
        summary=validated.get("moat_summary", ""),
        detail=validated, model_id=llm_model, prompt_hash=prompt_hash,
    )
    return validated, narrative

# ---------------------------------------------------------------------------
# Module class
# ---------------------------------------------------------------------------

class MoatModule(ModuleHelpers):
    """Hybrid D1+D2 moat analysis using Morningstar 5-source framework."""

    def __init__(self, llm_base_url: str | None = None, llm_model: str = "") -> None:
        self._llm_base_url = llm_base_url
        self._llm_model = llm_model

    @property
    def name(self) -> str:
        return "moat"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"financials"})

    def run(self, context: TickerContext) -> ArtifactSet:
        ticker = context.ticker
        warnings: list[str] = []

        if not context.has_financials:
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no financial periods available"},
                warnings=("no_financials",),
            )
        assert context.financials is not None
        periods = context.financials.periods
        if not periods:
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no financial periods available"},
                warnings=("no_periods",),
            )

        d1_signals = _compute_d1_signals(periods)
        insufficient = sum(
            1 for v in d1_signals.values()
            if isinstance(v, dict) and v.get("assessment") == "insufficient_data"
        )
        if insufficient >= 4:
            warnings.append("most_signals_insufficient_data")

        evidence = (EvidenceItem(
            evidence_id=f"moat_d1_{ticker}_{periods[-1].period_end}",
            source_type="computed",
            content=f"Moat D1 signals from {len(periods)} periods ending {periods[-1].period_end}",
        ),)

        structured: dict[str, Any] = {
            "d1_signals": d1_signals,
            "moat_classification": None, "moat_score": None,
            "moat_confidence": None, "moat_trend": None,
            "moat_summary": None, "sources": None,
        }
        narrative: Narrative | None = None

        if self._llm_base_url:
            try:
                d2, narrative = _run_d2_synthesis(
                    ticker=ticker, d1_signals=d1_signals, context=context,
                    llm_base_url=self._llm_base_url, llm_model=self._llm_model,
                )
                for k in ("moat_classification", "moat_score", "moat_confidence",
                          "moat_trend", "moat_summary", "sources"):
                    structured[k] = d2[k]
            except Exception:
                logger.exception("Moat D2 synthesis failed for %s", ticker)
                warnings.append("d2_synthesis_failed")
        else:
            warnings.append("no_llm_configured")

        completeness = (
            Completeness.COMPLETE if structured["moat_classification"] is not None
            else Completeness.PARTIAL
        )
        return self._build_artifact(
            ticker=ticker, module_name=self.name, completeness=completeness,
            structured=structured, narrative=narrative,
            evidence=evidence, warnings=tuple(warnings),
        )
