"""Risk gate — bull/bear/judge LLM debate before strategy decisions.

Adapted from TradingAgents' 3-persona risk debate pattern. Synthesis is
routed through the backend POST /research/synthesize endpoint (service
role invariant — cockpit never calls LLM directly).

Pipeline: Bull argues FOR → Bear argues AGAINST → Judge synthesizes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_BULL_SYSTEM = (
    "You are a bull-case investment analyst for ASX equities. Argue FOR the proposed "
    "investment signal. Emphasize growth potential, competitive advantages, positive "
    "catalysts, and upside scenarios. Be specific — cite the data provided. "
    "Keep your argument concise (3-5 key points, ~200 words)."
)

_BEAR_SYSTEM = (
    "You are a bear-case investment analyst for ASX equities. Argue AGAINST the proposed "
    "investment signal. Emphasize risks, negative catalysts, competitive threats, valuation "
    "concerns, and downside scenarios. Be specific — cite the data provided. "
    "Keep your argument concise (3-5 key points, ~200 words)."
)

_JUDGE_PROMPT = (
    "You are a senior portfolio manager reviewing a bull/bear debate on an ASX equity. "
    "Synthesize both arguments and produce a final recommendation.\n"
    "Output ONLY valid JSON: "
    '{"adjusted_signal":"BUY|OVERWEIGHT|HOLD|UNDERWEIGHT|SELL",'
    '"risk_level":"low|medium|high",'
    '"key_risks":["risk 1","risk 2"],'
    '"synthesis":"2-3 sentence summary",'
    '"confidence":0.0-1.0}'
)


class RiskGate:
    """Runs a structured bull/bear/judge debate on a proposed signal."""

    def __init__(
        self,
        *,
        backend_client: Any,
        dossier_service: Any | None = None,
        situation_memory: Any | None = None,
    ) -> None:
        self._backend = backend_client
        self._dossier = dossier_service
        self._situation_memory = situation_memory

    def assess(
        self,
        ticker: str,
        proposed_signal: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the bull/bear/judge debate."""
        ticker = ticker.strip().upper()
        logger.info("risk_gate: assessing %s signal for %s", proposed_signal, ticker)

        ctx_text = self._format_context(ticker, proposed_signal, context)

        # 1. Bull case.
        bull_case = self._run_persona(
            _BULL_SYSTEM,
            f"Argue FOR a {proposed_signal} signal on {ticker}.\n\n{ctx_text}",
        )

        # 2. Bear case.
        bear_case = self._run_persona(
            _BEAR_SYSTEM,
            f"Argue AGAINST a {proposed_signal} signal on {ticker}.\n\n{ctx_text}",
        )

        # 3. Judge synthesis.
        judge_input = (
            f"Ticker: {ticker}\nProposed signal: {proposed_signal}\n\n"
            f"BULL CASE:\n{bull_case}\n\nBEAR CASE:\n{bear_case}\n\nDATA:\n{ctx_text}"
        )
        judge_result = self._run_judge(judge_input)

        # 4. Recall similar past situations.
        past_situations: list[dict[str, Any]] = []
        if self._situation_memory is not None:
            try:
                situation_desc = f"{ticker} {proposed_signal} — {context.get('thesis', '')}"
                past_situations = self._situation_memory.recall(situation_desc, n=3)
            except Exception as exc:
                logger.debug("risk_gate: situation recall failed: %s", exc)

        return {
            "ok": True,
            "ticker": ticker,
            "proposed_signal": proposed_signal,
            "bull_case": bull_case,
            "bear_case": bear_case,
            "judge_synthesis": judge_result.get("synthesis", ""),
            "adjusted_signal": judge_result.get("adjusted_signal", proposed_signal),
            "risk_level": judge_result.get("risk_level", "medium"),
            "key_risks": judge_result.get("key_risks", []),
            "confidence": judge_result.get("confidence", 0.5),
            "similar_past_situations": past_situations,
        }

    # ------------------------------------------------------------------
    # Internals — routed via backend POST /research/synthesize
    # ------------------------------------------------------------------

    def _run_persona(self, system_prompt: str, user_msg: str) -> str:
        """Run a single persona call via the backend synthesis endpoint."""
        if self._backend is None:
            return "(backend client not available)"
        try:
            result = self._backend.synthesize_research(
                system_prompt=system_prompt,
                data={"user_message": user_msg[:6000]},
            )
            return result.get("raw_text", result.get("summary", str(result)))
        except Exception as exc:
            logger.warning("risk_gate: persona call failed: %s", exc)
            return f"(LLM call failed: {exc})"

    def _run_judge(self, user_msg: str) -> dict[str, Any]:
        """Run the judge synthesis call, parse JSON output."""
        if self._backend is None:
            return self._fallback_judge()
        try:
            result = self._backend.synthesize_research(
                system_prompt=_JUDGE_PROMPT,
                data={"user_message": user_msg[:8000]},
            )
            raw = result.get("raw_text", result.get("summary", ""))
            return self._parse_judge(raw)
        except Exception as exc:
            logger.warning("risk_gate: judge call failed: %s", exc)
            return self._fallback_judge()

    @staticmethod
    def _fallback_judge() -> dict[str, Any]:
        return {
            "adjusted_signal": "HOLD",
            "risk_level": "high",
            "key_risks": ["Risk assessment unavailable"],
            "synthesis": "Could not run risk assessment — defaulting to HOLD.",
            "confidence": 0.2,
        }

    @staticmethod
    def _parse_judge(raw: str) -> dict[str, Any]:
        """Parse judge JSON output with fallback."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                sig = result.get("adjusted_signal", "HOLD").upper()
                if sig not in ("BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL"):
                    sig = "HOLD"
                result["adjusted_signal"] = sig
                return result
        except json.JSONDecodeError:
            pass
        return {
            "adjusted_signal": "HOLD",
            "risk_level": "medium",
            "key_risks": ["Could not parse judge output"],
            "synthesis": text[:500],
            "confidence": 0.3,
        }

    def _format_context(self, ticker: str, signal: str, context: dict[str, Any]) -> str:
        """Format context data for LLM consumption."""
        parts: list[str] = []
        if context.get("thesis"):
            parts.append(f"Thesis: {context['thesis']}")
        if context.get("score_data"):
            sd = context["score_data"]
            parts.append(
                f"Composite score: {sd.get('composite_score', '?')}/100 "
                f"(health={sd.get('financial_health', '?')}, "
                f"momentum={sd.get('momentum_score', '?')}, "
                f"valuation={sd.get('valuation_score', '?')}, "
                f"technical={sd.get('technical_score', '?')})"
            )
        if context.get("valuation"):
            v = context["valuation"]
            parts.append(f"Valuation: PE={v.get('pe_ratio', '?')}, FCF yield={v.get('fcf_yield_pct', '?')}%")
        if context.get("technicals"):
            t = context["technicals"]
            parts.append(f"Technicals: RSI={t.get('rsi_14', '?')}, trend={t.get('trend_regime', '?')}")
        if self._dossier is not None:
            try:
                dossier = self._dossier.recall(ticker, limit=3)
                for f in dossier.get("findings", [])[:3]:
                    parts.append(f"  - {f.get('finding', '')[:200]}")
            except Exception:
                pass
        return "\n".join(parts) if parts else f"No context available for {ticker}."
