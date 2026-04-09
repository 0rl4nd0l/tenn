"""Evidence sourcing formatter — compact footer showing provenance for analysis responses.

Appended to analysis responses when the ``show_sources`` user preference is ON.
Display-only — does not affect LLM prompt content.
"""

from __future__ import annotations

from typing import Any

_SEPARATOR = "─" * 40
_MAX_TITLE_LEN = 50
_MAX_RAG_HITS = 3


def _safe_int(value: object, default: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return parsed if parsed > 0 else max(parsed, default)


def _as_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


class SourcesFormatter:
    """Build a compact sources footer from a context payload ``sources`` dict."""

    @staticmethod
    def collect_sources_payloads(
        evidence: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Collect normalized source payloads from all evidence entries."""
        source_keys = {
            "rag_hits",
            "financial_periods",
            "dossier_count",
            "strategy_criteria_count",
            "web_sources",
        }

        def _looks_like_source_payload(candidate: dict[str, Any]) -> bool:
            return any(key in candidate for key in source_keys)

        payloads: list[dict[str, Any]] = []
        for entry in evidence or []:
            if not isinstance(entry, dict):
                continue
            details = entry.get("details")
            if not isinstance(details, dict):
                details = None

            sources: object = None
            if isinstance(details, dict):
                nested = details.get("sources")
                if isinstance(nested, dict):
                    sources = nested
                elif _looks_like_source_payload(details):
                    sources = details

            if sources is None:
                result = entry.get("result")
                if isinstance(result, dict) and _looks_like_source_payload(result):
                    sources = result

            if not isinstance(sources, dict) or not sources:
                continue

            payloads.append(sources)
        return payloads

    @staticmethod
    def _merge_source_entries(payloads: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple source payloads into one combined view for display."""
        merged: dict[str, object] = {
            "rag_hits": [],
            "financial_periods": [],
            "dossier_count": 0,
            "strategy_criteria_count": 0,
            "web_sources": [],
        }

        rag_hits: list[dict[str, Any]] = []
        seen_hit_ids: set[str] = set()

        financial_periods: list[tuple[str, str, str]] = []
        seen_periods: set[tuple[str, str, str]] = set()

        for payload in payloads or []:
            if not isinstance(payload, dict):
                continue

            merged_hits = payload.get("rag_hits") or []
            for hit in merged_hits:
                if not isinstance(hit, dict):
                    continue
                source_id = str(hit.get("source_id") or "").strip()
                if not source_id:
                    source_id = f"{str(hit.get('document_id') or '').strip()}:{str(hit.get('chunk_index') or '')}".strip(
                        ":"
                    )
                if source_id and source_id in seen_hit_ids:
                    continue
                if source_id:
                    seen_hit_ids.add(source_id)
                rag_hits.append(dict(hit))

            for period in payload.get("financial_periods") or []:
                period_tuple: tuple[str, str, str]
                if isinstance(period, (tuple, list)) and period:
                    left = [str(item or "") for item in period]
                    while len(left) < 3:
                        left.append("")
                    period_tuple = (left[0], left[1], left[2])
                elif isinstance(period, dict):
                    period_tuple = (
                        str(period.get("ticker") or ""),
                        str(period.get("period_end") or period.get("period") or ""),
                        str(period.get("period_type") or ""),
                    )
                else:
                    continue
                if period_tuple in seen_periods:
                    continue
                seen_periods.add(period_tuple)
                financial_periods.append(period_tuple)

            merged["dossier_count"] = _safe_int(
                payload.get("dossier_count", 0), 0
            ) + _safe_int(merged["dossier_count"], 0)
            merged["strategy_criteria_count"] = _safe_int(
                payload.get("strategy_criteria_count", 0), 0
            ) + _safe_int(merged["strategy_criteria_count"], 0)

            merged_web_sources = payload.get("web_sources")
            if isinstance(merged_web_sources, list):
                for web_source in merged_web_sources:
                    if isinstance(web_source, dict):
                        merged.setdefault("web_sources", []).append(web_source)
                    else:
                        merged.setdefault("web_sources", []).append(str(web_source))

        merged["rag_hits"] = rag_hits
        merged["financial_periods"] = financial_periods
        return merged

    @staticmethod
    def format_list(payloads: list[dict[str, Any]], max_hits: int = 20) -> str:
        """Format all aggregated source hits in an inspectable numbered list."""
        merged = SourcesFormatter._merge_source_entries(payloads)
        rag_hits: list[dict[str, Any]] = merged.get("rag_hits") or []
        if not rag_hits:
            return ""

        lines = [
            _SEPARATOR,
            "Sources list (use `/sources show <n>` to inspect a specific hit):",
        ]
        for index, hit in enumerate(rag_hits[:max_hits], start=1):
            title = str(hit.get("title") or "untitled")
            if len(title) > _MAX_TITLE_LEN:
                title = title[: _MAX_TITLE_LEN - 1] + "…"
            source_id = str(hit.get("source_id") or f"{index}").strip()
            score = _as_float(hit.get("score"))
            doc_type = str(hit.get("doc_type") or hit.get("corpus") or "")
            lines.append(
                f"  {index:>2}. {title} [{source_id}] (score: {score:.2f}{', ' + doc_type if doc_type else ''})"
            )

        if not lines:
            return ""
        lines.append(_SEPARATOR)
        return "\n".join(lines)

    @staticmethod
    def format_show(payloads: list[dict[str, Any]], index: int) -> str:
        """Format a specific source hit by 1-based index for interactive inspection."""
        merged = SourcesFormatter._merge_source_entries(payloads)
        rag_hits: list[dict[str, Any]] = merged.get("rag_hits") or []
        if not rag_hits:
            return "No sources available."
        if index <= 0 or index > len(rag_hits):
            return f"Source index out of range. Use 1..{len(rag_hits)}."

        hit = rag_hits[index - 1]
        title = str(hit.get("title") or "untitled")
        doc_type = str(hit.get("doc_type") or hit.get("corpus") or "")
        score = _as_float(hit.get("score"))
        source_id = str(hit.get("source_id") or "")
        document_id = str(hit.get("document_id") or "")
        chunk_index = hit.get("chunk_index")
        url = str(hit.get("url") or "")
        published_at = str(hit.get("published_at") or "")
        ticker = str(hit.get("ticker") or "")
        text = str(hit.get("text") or "")

        lines = [
            _SEPARATOR,
            f"Source {index}: {title}",
            f"  id: {source_id}" if source_id else "",
        ]
        meta = [
            f"  score: {score:.2f}",
            f"  doc_type: {doc_type}" if doc_type else "",
            f"  document_id: {document_id}" if document_id else "",
            f"  chunk_index: {chunk_index}" if chunk_index not in (None, "") else "",
            f"  ticker: {ticker}" if ticker else "",
            f"  published_at: {published_at}" if published_at else "",
            f"  url: {url}" if url else "",
        ]
        for item in meta:
            if item:
                lines.append(item)

        if text:
            lines.append("  text:")
            lines.append("  " + text.replace("\n", "\n  "))

        lines.append(_SEPARATOR)
        return "\n".join(line for line in lines if line)

    @staticmethod
    def format_footer(
        sources: list[dict[str, Any]] | dict[str, Any],
        show_sources: bool = True,
    ) -> str:
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

        normalized = None
        if isinstance(sources, dict):
            normalized = SourcesFormatter._merge_source_entries([sources])
        elif isinstance(sources, list):
            normalized = SourcesFormatter._merge_source_entries(sources)
        if not isinstance(normalized, dict):
            return ""

        rag_hits: list[dict[str, Any]] = normalized.get("rag_hits") or []
        financial_periods: list = normalized.get("financial_periods") or []
        dossier_count: int = int(normalized.get("dossier_count", 0) or 0)
        strategy_count: int = int(normalized.get("strategy_criteria_count", 0) or 0)
        web_sources: list = normalized.get("web_sources") or []

        # Nothing to show?
        if (
            not rag_hits
            and not financial_periods
            and dossier_count == 0
            and strategy_count == 0
            and not web_sources
        ):
            return ""

        # Summary line
        parts: list[str] = []
        if rag_hits:
            parts.append(f"RAG: {len(rag_hits)} doc{'s' if len(rag_hits) != 1 else ''}")
        if financial_periods:
            parts.append(
                f"Financial: {len(financial_periods)} period{'s' if len(financial_periods) != 1 else ''}"
            )
        if dossier_count:
            parts.append(
                f"Dossier: {dossier_count} finding{'s' if dossier_count != 1 else ''}"
            )
        if strategy_count:
            parts.append(
                f"Strategy: {strategy_count} criteri{'a' if strategy_count != 1 else 'on'}"
            )
        if web_sources:
            parts.append(
                f"Web: {len(web_sources)} source{'s' if len(web_sources) != 1 else ''}"
            )

        summary = "Sources  " + "  |  ".join(parts)

        lines = [_SEPARATOR, summary]

        # RAG hit details (top 3)
        for hit in rag_hits[:_MAX_RAG_HITS]:
            title = str(hit.get("title") or "untitled")
            if len(title) > _MAX_TITLE_LEN:
                title = title[: _MAX_TITLE_LEN - 1] + "…"
            score = hit.get("score", 0.0)
            doc_type = hit.get("doc_type") or hit.get("corpus") or ""
            detail = f"  • {title} (score: {score:.2f}"
            if doc_type:
                detail += f", {doc_type}"
            detail += ")"
            lines.append(detail)

        lines.append(_SEPARATOR)
        return "\n".join(lines)
