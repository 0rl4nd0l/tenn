"""Deep research meta-tool — multi-source research in a single call.

Bypasses the 6-iteration agent loop limit by running a deterministic
gather → synthesize → persist pipeline. Uses its own LLM context
(separate from the agent loop) for synthesis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_RESEARCH_SYSTEM_PROMPT = """\
You are an ASX equity research analyst. You have been given data from multiple
sources about a company. Synthesize this into a concise research brief.

Output ONLY valid JSON with these fields:
{
  "summary": "2-3 sentence overview of the company's current situation",
  "key_metrics": {"revenue": "...", "ebit": "...", "cash_flow": "...", "net_debt": "..."},
  "recent_developments": ["development 1", "development 2"],
  "sentiment": "bullish|neutral|bearish",
  "confidence": 0.0-1.0,
  "risks": ["risk 1", "risk 2"],
  "catalysts": ["catalyst 1", "catalyst 2"],
  "data_gaps": ["what data is missing or uncertain"]
}

Be concise. Cite specific numbers from the data. Flag low-confidence claims.
"""


class DeepResearchRunner:
    """Runs a complete multi-source research pipeline in one call."""

    def __init__(
        self,
        *,
        tool_router: Any,
        hybrid_router: Any,
        dossier_service: Any | None = None,
        brave_client: Any | None = None,
        hn_client: Any | None = None,
    ) -> None:
        self._router = tool_router
        self._llm = hybrid_router
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

        # 2. Synthesize via LLM.
        synthesis = self._synthesize(ticker, gathered, focus=focus)

        # 3. Persist to dossier.
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
    # Synthesize
    # ------------------------------------------------------------------

    def _synthesize(
        self,
        ticker: str,
        gathered: dict[str, Any],
        *,
        focus: str | None = None,
    ) -> dict[str, Any]:
        """Call LLM to synthesize gathered data into a research brief."""
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

        # Build user message with gathered data.
        focus_instruction = f"\nFocus your analysis on: {focus}" if focus else ""
        data_text = json.dumps(gathered, default=str, ensure_ascii=False)
        # Truncate data to avoid context overflow (~8K chars max).
        if len(data_text) > 8000:
            data_text = data_text[:8000] + "\n... (truncated)"

        user_msg = f"Research {ticker} on the ASX.{focus_instruction}\n\nDATA:\n{data_text}"

        messages = [
            {"role": "system", "content": _RESEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            response = self._llm.complete(messages, role="deep_research")
            raw = response.text if hasattr(response, "text") else str(response)
            return self._parse_synthesis(raw, ticker)
        except Exception as exc:
            logger.warning("deep_research: LLM synthesis failed: %s", exc)
            return {
                "summary": f"LLM synthesis failed for {ticker}: {str(exc)[:200]}",
                "key_metrics": {},
                "recent_developments": [],
                "sentiment": "neutral",
                "confidence": 0.0,
                "risks": ["Synthesis failed"],
                "catalysts": [],
                "data_gaps": ["LLM call failed"],
            }

    def _parse_synthesis(self, raw: str, ticker: str) -> dict[str, Any]:
        """Parse LLM JSON output with fallback to plain text."""
        # Strip markdown fences if present.
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
                return result
        except json.JSONDecodeError:
            pass

        # Fallback: treat raw text as summary.
        return {
            "summary": text[:500],
            "key_metrics": {},
            "recent_developments": [],
            "sentiment": "neutral",
            "confidence": 0.3,
            "risks": [],
            "catalysts": [],
            "data_gaps": ["LLM returned non-JSON response"],
        }
