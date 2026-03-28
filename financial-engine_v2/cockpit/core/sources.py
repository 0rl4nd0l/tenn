"""Evidence sourcing formatter — compact footer showing provenance for analysis responses.

Appended to analysis responses when the ``show_sources`` user preference is ON.
Display-only — does not affect LLM prompt content.
"""

from __future__ import annotations

_SEPARATOR = "─" * 40
_MAX_TITLE_LEN = 50
_MAX_RAG_HITS = 3


class SourcesFormatter:
    """Build a compact sources footer from a context payload ``sources`` dict."""

    @staticmethod
    def format_footer(sources: dict, show_sources: bool = True) -> str:
        """Return a formatted footer string, or empty string if disabled/empty.

        Parameters
        ----------
        sources:
            Dict with optional keys: ``rag_hits``, ``financial_periods``,
            ``dossier_count``, ``strategy_criteria_count``, ``web_sources``.
        show_sources:
            If False, always returns empty string.
        """
        if not show_sources or not sources:
            return ""

        rag_hits: list[dict] = sources.get("rag_hits") or []
        financial_periods: list = sources.get("financial_periods") or []
        dossier_count: int = sources.get("dossier_count", 0)
        strategy_count: int = sources.get("strategy_criteria_count", 0)
        web_sources: list = sources.get("web_sources") or []

        # Nothing to show?
        if not rag_hits and not financial_periods and dossier_count == 0 and strategy_count == 0 and not web_sources:
            return ""

        # Summary line
        parts: list[str] = []
        if rag_hits:
            parts.append(f"RAG: {len(rag_hits)} doc{'s' if len(rag_hits) != 1 else ''}")
        if financial_periods:
            parts.append(f"Financial: {len(financial_periods)} period{'s' if len(financial_periods) != 1 else ''}")
        if dossier_count:
            parts.append(f"Dossier: {dossier_count} finding{'s' if dossier_count != 1 else ''}")
        if strategy_count:
            parts.append(f"Strategy: {strategy_count} criteri{'a' if strategy_count != 1 else 'on'}")
        if web_sources:
            parts.append(f"Web: {len(web_sources)} source{'s' if len(web_sources) != 1 else ''}")

        summary = "Sources  " + "  |  ".join(parts)

        lines = [_SEPARATOR, summary]

        # RAG hit details (top 3)
        for hit in rag_hits[:_MAX_RAG_HITS]:
            title = str(hit.get("title") or "untitled")
            if len(title) > _MAX_TITLE_LEN:
                title = title[:_MAX_TITLE_LEN - 1] + "…"
            score = hit.get("score", 0.0)
            doc_type = hit.get("doc_type") or hit.get("corpus") or ""
            detail = f"  • {title} (score: {score:.2f}"
            if doc_type:
                detail += f", {doc_type}"
            detail += ")"
            lines.append(detail)

        lines.append(_SEPARATOR)
        return "\n".join(lines)
