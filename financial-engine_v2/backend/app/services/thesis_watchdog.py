from __future__ import annotations

import json
import logging
from typing import Any, Callable

from app.services.user_thesis_memory import UserThesisMemoryStore
from app.services.llm import generate_json

logger = logging.getLogger(__name__)

WATCHDOG_PROMPT = """You are a senior investment analyst watchdog. Your task is to compare a user's saved thesis claim against new evidence from a recent company announcement.

Claim to monitor:
"{{claim_statement}}"

New Evidence ({{doc_title}}):
{{evidence_summary}}

Evaluate if this new evidence significantly contradicts, strongly supports, or presents a meaningful divergence from the saved claim. Be objective and focus on factual contradictions or major narrative shifts.

Return a JSON object:
{
  "outcome": "contradict" | "support" | "diverge" | "neutral",
  "severity": 0.0 to 1.0,  // 0.0 is neutral, 1.0 is a critical contradiction/support
  "finding": "A brief summary of why the evidence impacts the claim.",
  "relevant_excerpt": "The specific quote or metric from the evidence that justifies this finding."
}
"""

class ThesisWatchdogService:
    def __init__(
        self,
        store: UserThesisMemoryStore | None = None,
        llm_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.store = store or UserThesisMemoryStore()
        self.llm_fn = llm_fn or generate_json

    def check_document(self, ticker: str, document_id: str, new_data: dict[str, Any], doc_title: str) -> list[dict[str, Any]]:
        """Check all active monitored thesis claims for a ticker against new document data."""
        active_entries = self.store.list_entries(ticker, status="active", auto_monitor_only=True)
        if not active_entries:
            return []

        alerts = []
        # We summarize the new data to stay within context limits
        evidence_summary = self._summarize_new_data(new_data)

        for entry in active_entries:
            try:
                result = self._evaluate_claim(entry["statement"], evidence_summary, doc_title)
                if result and result.get("outcome") in ("contradict", "diverge", "support"):
                    severity = float(result.get("severity") or 0.0)
                    if severity >= 0.4:  # Threshold for creating an alert
                        alert = self.store.create_alert(
                            entry_id=entry["entry_id"],
                            ticker=ticker,
                            severity=result["outcome"],
                            finding=result["finding"],
                            evidence_source_id=document_id,
                            metadata={
                                "excerpt": result.get("relevant_excerpt"),
                                "severity_score": severity,
                            }
                        )
                        alerts.append(alert)
                        logger.info(f"Thesis Watchdog Alert created: {alert['alert_id']} for ticker {ticker}")
            except Exception as exc:
                logger.error(f"Failed to evaluate thesis claim {entry['entry_id']}: {exc}")

        return alerts

    def _evaluate_claim(self, claim: str, evidence: str, title: str) -> dict[str, Any] | None:
        prompt = WATCHDOG_PROMPT.replace("{{claim_statement}}", claim)
        prompt = prompt.replace("{{doc_title}}", title)
        prompt = prompt.replace("{{evidence_summary}}", evidence)

        try:
            return self.llm_fn(
                prompt=prompt,
                metadata={
                    "component": "thesis_watchdog",
                    "task_type": "reasoning",
                },
                timeout=25.0,
            )
        except Exception as exc:
            logger.warning(f"Watchdog LLM call failed: {exc}")
            return None

    def _summarize_new_data(self, data: dict[str, Any]) -> str:
        """Create a concise summary of the extraction result for the watchdog prompt."""
        parts = []
        
        # Add key metrics if available
        metrics = data.get("metrics") or {}
        if metrics:
            metric_lines = []
            for k, v in metrics.items():
                if v is not None:
                    metric_lines.append(f"- {k}: {v}")
            if metric_lines:
                parts.append("Key Metrics:\n" + "\n".join(metric_lines))

        # Add risk summary or guidance if available
        for key in ("risk_summary", "guidance_summary", "material_changes"):
            val = data.get(key)
            if val:
                parts.append(f"{key.replace('_', ' ').title()}: {val}")

        # Add risk bullets
        bullets = data.get("risk_bullets")
        if bullets and isinstance(bullets, list):
            parts.append("Risk Highlights:\n" + "\n".join([f"- {b}" for b in bullets[:5]]))

        return "\n\n".join(parts)
