from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.services.memory_events import emit_memory_read_event


class EvidenceProvider(Protocol):
    def retrieve(
        self,
        *,
        query: str,
        entities: dict[str, Any],
        intent: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class MemoryBundle:
    evidence: dict[str, dict[str, Any]]
    raw_evidence: dict[str, dict[str, Any]]
    considered_counts: dict[str, int]
    selected_counts: dict[str, int]
    filtered_counts: dict[str, int]


class MemoryAssembler:
    """Deterministic memory assembly contract for orchestrator read paths."""

    def __init__(
        self,
        *,
        financial_truth_provider: EvidenceProvider,
        company_memory_provider: EvidenceProvider,
        market_memory_provider: EvidenceProvider,
        user_thesis_memory_provider: EvidenceProvider,
    ) -> None:
        self._providers = {
            "financial_truth": financial_truth_provider,
            "company_memory": company_memory_provider,
            "market_memory": market_memory_provider,
            "user_thesis_memory": user_thesis_memory_provider,
        }

    def assemble(
        self,
        *,
        mode: str,
        query: str,
        intent: str,
        entities: dict[str, Any],
        source_plan: tuple[str, ...],
    ) -> MemoryBundle:
        evidence: dict[str, dict[str, Any]] = {}
        raw_evidence: dict[str, dict[str, Any]] = {}
        considered_counts: dict[str, int] = {}
        selected_counts: dict[str, int] = {}
        filtered_counts: dict[str, int] = {}

        for source in source_plan:
            provider = self._providers[source]
            payload = provider.retrieve(query=query, entities=entities, intent=intent)
            normalized = payload if isinstance(payload, dict) else {"items": payload}
            raw_evidence[source] = normalized

            filtered_payload, considered, selected = self._filter_payload(
                source=source,
                payload=normalized,
            )
            evidence[source] = filtered_payload
            considered_counts[source] = considered
            selected_counts[source] = selected
            filtered_counts[source] = max(0, considered - selected)

        emit_memory_read_event(
            mode=mode,
            query_type=intent,
            query=query,
            entities=entities,
            source_plan=list(source_plan),
            considered_counts=considered_counts,
            selected_counts=selected_counts,
            filtered_counts=filtered_counts,
        )

        return MemoryBundle(
            evidence=evidence,
            raw_evidence=raw_evidence,
            considered_counts=considered_counts,
            selected_counts=selected_counts,
            filtered_counts=filtered_counts,
        )

    def _filter_payload(
        self,
        *,
        source: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], int, int]:
        if source == "financial_truth":
            items = payload.get("items")
            considered = len(items) if isinstance(items, list) else 0
            selected = considered
            return payload, considered, selected

        if source == "company_memory":
            items = payload.get("items") if isinstance(payload.get("items"), list) else []
            selected_items = [
                item
                for item in items
                if isinstance(item, dict)
                and float(item.get("active_score") or 0.0) >= 0.55
                and str(item.get("status") or "active").strip().lower() == "active"
            ]
            return {
                **payload,
                "items": selected_items,
            }, len(items), len(selected_items)

        if source == "market_memory":
            sector_items = (
                payload.get("sector_items")
                if isinstance(payload.get("sector_items"), list)
                else []
            )
            macro_items = (
                payload.get("macro_items")
                if isinstance(payload.get("macro_items"), list)
                else []
            )
            considered = len(sector_items) + len(macro_items)
            filtered_sector = [
                item
                for item in sector_items
                if isinstance(item, dict)
                and float(item.get("active_score") or 0.0) >= 0.55
                and str(item.get("status") or "active").strip().lower() == "active"
            ]
            filtered_macro = [
                item
                for item in macro_items
                if isinstance(item, dict)
                and float(item.get("active_score") or 0.0) >= 0.55
                and str(item.get("status") or "active").strip().lower() == "active"
            ]
            selected = len(filtered_sector) + len(filtered_macro)
            return {
                **payload,
                "sector_items": filtered_sector,
                "macro_items": filtered_macro,
                "items": filtered_sector + filtered_macro,
            }, considered, selected

        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        selected_items = [
            item
            for item in items
            if isinstance(item, dict)
            and str(item.get("status") or "active").strip().lower() == "active"
        ]
        return {
            **payload,
            "items": selected_items,
        }, len(items), len(selected_items)
