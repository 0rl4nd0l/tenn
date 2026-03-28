"""catalysts.py — Hybrid D1+D2 catalyst identification module.

D1 (always runs): extracts guidance from risk_notes, computes financial
momentum signals from period metrics, collects RAG evidence.

D2 (optional, when llm_base_url provided): LLM identifies 2-6 catalysts
with category, timeframe, probability, impact direction, and evidence links.
Produces catalyst_summary narrative and upcoming_events.
"""
from __future__ import annotations

import logging
from typing import Any

from app.modules.base import (
    ArtifactSet,
    Completeness,
    EvidenceItem,
    ModuleHelpers,
    Narrative,
)
from app.modules.math_utils import pct_change, round_or_none
from app.modules.ticker_context import TickerContext

logger = logging.getLogger(__name__)

CATALYST_RAG_LABELS = (
    "catalyst_guidance",
    "catalyst_strategy",
    "catalyst_outlook",
    "catalyst_regulatory",
    "catalyst_corporate_action",
)

_CATALYST_PROMPT = """\
You are a financial analyst identifying catalysts for {ticker}.

Given the following evidence, identify 2-6 catalysts that could materially
move the share price. For each catalyst provide:
- title: short name
- category: one of earnings|corporate_action|regulatory|macro|operational|market
- timeframe: one of near_term|medium_term|long_term
- probability: one of high|medium|low
- impact_direction: one of positive|negative|ambiguous
- description: 1-2 sentence explanation
- evidence_ids: list of evidence_id strings that support this catalyst

Also provide:
- catalyst_summary: 2-3 sentence overall catalyst outlook
- upcoming_events: list of objects with "event" and "expected_timeframe" fields

GUIDANCE:
{guidance}

MOMENTUM SIGNALS:
{momentum}

RAG EVIDENCE:
{rag_evidence}

Return ONLY valid JSON matching this schema:
{{
  "catalysts": [{{
    "title": "...", "category": "...", "timeframe": "...",
    "probability": "...", "impact_direction": "...",
    "description": "...", "evidence_ids": ["..."]
  }}],
  "catalyst_summary": "...",
  "upcoming_events": [{{"event": "...", "expected_timeframe": "..."}}]
}}
"""


# -- D1 helpers --------------------------------------------------------------

def _extract_guidance(context: TickerContext) -> list[dict[str, Any]]:
    """Extract guidance and material change items from risk notes."""
    items: list[dict[str, Any]] = []
    for rn in context.risk_notes:
        if rn.guidance_summary:
            items.append({
                "type": "guidance",
                "document_id": rn.document_id,
                "content": rn.guidance_summary,
            })
        if rn.material_changes:
            items.append({
                "type": "material_change",
                "document_id": rn.document_id,
                "content": rn.material_changes,
            })
    return items


def _compute_momentum(context: TickerContext) -> list[dict[str, Any]]:
    """Derive momentum signals from financial trends."""
    signals: list[dict[str, Any]] = []
    if context.financials is None or context.financials.period_count < 2:
        return signals
    latest = context.financials.latest
    prior = context.financials.prior
    if latest is None or prior is None:
        return signals

    rev_g = pct_change(latest.revenue, prior.revenue)
    if rev_g is not None and rev_g > 0.10:
        signals.append({
            "signal": "potential_earnings_beat",
            "metric": "revenue_yoy",
            "value": round_or_none(rev_g),
            "description": "Revenue growth >10% YoY suggests potential earnings beat",
        })

    ebit_g = pct_change(latest.ebit, prior.ebit)
    if ebit_g is not None and ebit_g > 0.15:
        signals.append({
            "signal": "margin_expansion",
            "metric": "ebit_yoy",
            "value": round_or_none(ebit_g),
            "description": "EBIT growth >15% YoY indicates margin expansion",
        })

    fcf_g = pct_change(latest.fcf, prior.fcf)
    if fcf_g is not None and fcf_g > 0.20:
        signals.append({
            "signal": "possible_capital_return",
            "metric": "fcf_yoy",
            "value": round_or_none(fcf_g),
            "description": "FCF acceleration >20% YoY signals possible capital return",
        })

    if latest.net_debt is not None and latest.net_debt < 0:
        signals.append({
            "signal": "ma_or_buyback_capacity",
            "metric": "net_cash",
            "value": round_or_none(latest.net_debt),
            "description": "Net cash position provides M&A or buyback capacity",
        })
    return signals


def _collect_rag_evidence(
    context: TickerContext,
) -> tuple[list[dict[str, str]], list[EvidenceItem]]:
    """Collect RAG hits as text snippets and EvidenceItems."""
    snippets: list[dict[str, str]] = []
    evidence: list[EvidenceItem] = []
    for label in CATALYST_RAG_LABELS:
        result = context.rag_by_label(label)
        if result is None:
            continue
        for i, hit in enumerate(result.hits):
            eid = f"rag_{label}_{i}"
            snippets.append({"evidence_id": eid, "label": label, "text": hit.text[:500]})
            evidence.append(EvidenceItem(
                evidence_id=eid, source_type="rag_hit",
                content=hit.text[:300], source_id=hit.document_id,
                confidence=hit.score,
            ))
    return snippets, evidence


# -- D2 LLM synthesis --------------------------------------------------------

def _build_prompt(
    ticker: str,
    guidance: list[dict[str, Any]],
    momentum: list[dict[str, Any]],
    rag_snippets: list[dict[str, str]],
) -> str:
    """Format the catalyst prompt with collected evidence."""
    g_text = "\n".join(f"- [{g['type']}] {g['content']}" for g in guidance) or "No guidance available."
    m_text = "\n".join(f"- {s['signal']}: {s['description']} ({s['value']})" for s in momentum) or "No momentum signals detected."
    r_text = "\n".join(f"- [{s['evidence_id']}] {s['text']}" for s in rag_snippets) or "No RAG evidence available."
    return _CATALYST_PROMPT.format(ticker=ticker, guidance=g_text, momentum=m_text, rag_evidence=r_text)


def _run_d2(
    ticker: str, prompt: str, llm_base_url: str, llm_model: str,
) -> dict[str, Any] | None:
    """Call LLM for catalyst synthesis. Returns parsed JSON or None on failure."""
    from app.services.llamacpp_runtime import generate_json_llamacpp

    try:
        result = generate_json_llamacpp(
            base_url=llm_base_url, model=llm_model,
            prompt=prompt, timeout=120.0,
        )
        if isinstance(result, dict):
            return result
        logger.warning("catalysts D2 %s: unexpected result type %s", ticker, type(result))
        return None
    except Exception:
        logger.exception("catalysts D2 %s: LLM call failed", ticker)
        return None


# -- Module class -------------------------------------------------------------

class CatalystsModule(ModuleHelpers):
    """Hybrid D1+D2 catalyst identification module."""

    def __init__(self, llm_base_url: str | None = None, llm_model: str = "") -> None:
        self._llm_base_url = llm_base_url
        self._llm_model = llm_model

    @property
    def name(self) -> str:
        return "catalysts"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"financials", "risk_notes"})

    def run(self, context: TickerContext) -> ArtifactSet:
        ticker = context.ticker
        warnings: list[str] = []

        # Minimum viability — need at least one of financials or risk_notes
        missing = self._check_minimum_viability(context, frozenset({"financials", "risk_notes"}))
        if "financials" in missing and "risk_notes" in missing:
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no financials or risk_notes available"},
                warnings=("no_financials", "no_risk_notes"),
            )
        if "financials" in missing:
            warnings.append("no_financials")
        if "risk_notes" in missing:
            warnings.append("no_risk_notes")

        # D1: extract guidance, momentum, RAG evidence
        guidance = _extract_guidance(context)
        momentum = _compute_momentum(context)
        rag_snippets, rag_evidence = _collect_rag_evidence(context)

        # Build evidence chain
        evidence_items: list[EvidenceItem] = list(rag_evidence)
        for sig in momentum:
            evidence_items.append(EvidenceItem(
                evidence_id=f"momentum_{sig['signal']}",
                source_type="computed", content=sig["description"],
            ))
        for g in guidance:
            evidence_items.append(EvidenceItem(
                evidence_id=f"guidance_{g['document_id']}_{g['type']}",
                source_type="financial_statement",
                content=g["content"][:300], source_id=g["document_id"],
            ))

        structured: dict[str, Any] = {
            "guidance": guidance,
            "momentum_signals": momentum,
            "rag_snippet_count": len(rag_snippets),
        }

        # D2: LLM synthesis (optional)
        narrative: Narrative | None = None
        if self._llm_base_url:
            prompt = _build_prompt(ticker, guidance, momentum, rag_snippets)
            prompt_hash = Narrative.hash_prompt(prompt)
            llm_result = _run_d2(ticker, prompt, self._llm_base_url, self._llm_model)
            if llm_result is not None:
                catalysts = llm_result.get("catalysts", [])
                structured["catalysts"] = catalysts
                structured["upcoming_events"] = llm_result.get("upcoming_events", [])
                narrative = Narrative(
                    summary=llm_result.get("catalyst_summary", ""),
                    detail={"catalysts": catalysts},
                    model_id=self._llm_model, prompt_hash=prompt_hash,
                )
            else:
                warnings.append("llm_synthesis_failed")

        completeness = Completeness.COMPLETE if guidance or momentum else Completeness.PARTIAL

        return self._build_artifact(
            ticker=ticker, module_name=self.name,
            completeness=completeness, structured=structured,
            narrative=narrative, evidence=tuple(evidence_items),
            warnings=tuple(warnings),
        )
