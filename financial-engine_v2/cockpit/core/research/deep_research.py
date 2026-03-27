"""Deep research meta-tool — multi-source research in a single call.

Bypasses the 6-iteration agent loop limit by running a deterministic
gather → synthesize → persist pipeline. Synthesis is performed by the
backend via POST /research/synthesize (service role invariant — cockpit
never calls LLM directly).
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class DeepResearchRunner:
    """Runs a complete multi-source research pipeline in one call."""

    def __init__(
        self,
        *,
        tool_router: Any,
        backend_client: Any,
        dossier_service: Any | None = None,
        brave_client: Any | None = None,
        hn_client: Any | None = None,
    ) -> None:
        self._router = tool_router
        self._backend = backend_client
        self._dossier = dossier_service
        self._brave = brave_client
        self._hn = hn_client

    def run(self, ticker: str, *, focus: str | None = None) -> dict[str, Any]:
        """Execute deep research on a ticker.

        Returns a dict suitable for the agent loop (truncated to ~4000 chars).
        """
        ticker = ticker.strip().upper()
        if not ticker:
            return {"ok": False, "error": "ticker is required"}

        logger.info("deep_research: starting for %s (focus=%s)", ticker, focus)

        # 1. Gather from all sources.
        gathered = self._gather(ticker, focus=focus)

        # 2. Synthesize via backend endpoint.
        synthesis = self._synthesize(ticker, gathered, focus=focus)

        # 3. Persist to dossier (auto-save to agent scratch memory).
        if self._dossier is not None and synthesis.get("summary"):
            self._dossier.save(
                ticker,
                synthesis["summary"],
                source="deep_research",
                confidence=synthesis.get("confidence", 0.5),
                category="financial",
            )

        # 4. Return result (capped for context window).
        result_text = json.dumps(synthesis, default=str, ensure_ascii=False)
        if len(result_text) > 4000:
            result_text = result_text[:4000]

        return {
            "ok": True,
            "ticker": ticker,
            "research": synthesis,
            "sources_used": list(gathered.keys()),
        }

    # ------------------------------------------------------------------
    # Gather
    # ------------------------------------------------------------------

    def _gather(self, ticker: str, *, focus: str | None = None) -> dict[str, Any]:
        """Collect data from all available sources."""
        data: dict[str, Any] = {}

        # Financials from local DB.
        try:
            financials = self._router.db_reader.get_financials(ticker, limit=6)
            if financials:
                data["financials"] = financials[:3]  # Trim for context
        except Exception as exc:
            logger.warning("deep_research: financials failed for %s: %s", ticker, exc)

        # Price data.
        try:
            price = self._router.get_price_context_for_window(
                ticker=ticker, range_="6mo", interval="1d", max_history_rows=30,
            )
            if price:
                data["price"] = price
        except Exception as exc:
            logger.warning("deep_research: price failed for %s: %s", ticker, exc)

        # Web search.
        if self._brave is not None:
            try:
                focus_q = f" {focus}" if focus else ""
                web = self._brave.search(f"{ticker} ASX{focus_q} news", count=5)
                if web.get("ok") and web.get("results"):
                    data["web_search"] = web["results"][:5]
            except Exception as exc:
                logger.warning("deep_research: web search failed: %s", exc)

        # HN / social.
        if self._hn is not None:
            try:
                hn = self._hn.search(f"{ticker}", limit=5)
                if hn.get("ok") and hn.get("stories"):
                    data["hn_social"] = hn["stories"][:3]
            except Exception as exc:
                logger.warning("deep_research: HN search failed: %s", exc)

        # Announcements.
        try:
            docs = self._router.db_reader.get_docs(ticker, limit=5)
            context = self._router.db_reader.get_announcement_context(ticker, limit=5)
            if docs or context:
                data["announcements"] = {
                    "documents": docs[:3] if docs else [],
                    "context": context[:3] if context else [],
                }
        except Exception as exc:
            logger.warning("deep_research: announcements failed: %s", exc)

        # Prior dossier.
        if self._dossier is not None:
            try:
                prior = self._dossier.recall(ticker, limit=3)
                if prior.get("findings"):
                    data["prior_dossier"] = prior["findings"]
            except Exception as exc:
                logger.warning("deep_research: dossier recall failed: %s", exc)

        logger.info(
            "deep_research: gathered %d sources for %s: %s",
            len(data), ticker, list(data.keys()),
        )
        return data

    # ------------------------------------------------------------------
    # Synthesize (via backend HTTP endpoint)
    # ------------------------------------------------------------------

    def _synthesize(
        self,
        ticker: str,
        gathered: dict[str, Any],
        *,
        focus: str | None = None,
    ) -> dict[str, Any]:
        """Call backend POST /research/synthesize for LLM synthesis."""
        if not gathered:
            return {
                "summary": f"No data available for {ticker}.",
                "key_metrics": {},
                "recent_developments": [],
                "sentiment": "neutral",
                "confidence": 0.0,
                "risks": ["No data gathered"],
                "catalysts": [],
                "data_gaps": ["All sources returned empty"],
            }

        if self._backend is None:
            return {
                "summary": f"Backend client not available for {ticker}.",
                "key_metrics": {},
                "recent_developments": [],
                "sentiment": "neutral",
                "confidence": 0.0,
                "risks": ["Backend client not configured"],
                "catalysts": [],
                "data_gaps": ["Synthesis unavailable"],
            }

        try:
            return self._backend.synthesize_research(
                ticker=ticker,
                gathered_sources=gathered,
                focus=focus,
            )
        except Exception as exc:
            logger.warning("deep_research: backend synthesis failed: %s", exc)
            return {
                "summary": f"LLM synthesis failed for {ticker}: {str(exc)[:200]}",
                "key_metrics": {},
                "recent_developments": [],
                "sentiment": "neutral",
                "confidence": 0.0,
                "risks": ["Synthesis failed"],
                "catalysts": [],
                "data_gaps": ["Backend synthesis call failed"],
            }
