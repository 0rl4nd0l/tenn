from __future__ import annotations

from typing import Any


class ResearchContextBuilder:
    def __init__(self, *, commentary_weight_max: float = 0.25) -> None:
        self.commentary_weight_max = float(max(0.0, commentary_weight_max))

    @staticmethod
    def _supporting_chunks_for_framework(
        framework: dict[str, Any],
        methodology_chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        family = str(framework.get("framework_family") or "").strip()
        matches = [
            dict(chunk)
            for chunk in methodology_chunks
            if str(chunk.get("framework_family") or "").strip() == family
        ]
        if matches:
            return matches[:3]
        return [dict(chunk) for chunk in methodology_chunks[:2]]

    def _cap_commentary_chunks(
        self,
        commentary_chunks: list[dict[str, Any]],
        evidence_chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        evidence_reference = max(
            [float(chunk.get("score") or 0.0) for chunk in evidence_chunks] or [1.0]
        )
        cap = evidence_reference * self.commentary_weight_max
        capped: list[dict[str, Any]] = []
        for chunk in commentary_chunks:
            normalized = dict(chunk)
            current_score = float(normalized.get("final_score") or 0.0)
            normalized["final_score"] = min(current_score, cap)
            capped.append(normalized)
        capped.sort(
            key=lambda chunk: (
                -float(chunk.get("final_score") or 0.0),
                -float(chunk.get("relevance_score") or 0.0),
                str(chunk.get("chunk_id") or ""),
            )
        )
        return capped

    def build(
        self,
        *,
        frameworks: list[dict[str, Any]],
        methodology_chunks: list[dict[str, Any]],
        evidence_chunks: list[dict[str, Any]],
        commentary_chunks: list[dict[str, Any]],
        commentary_memos: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ordered_frameworks = []
        for framework in frameworks:
            normalized = dict(framework)
            normalized["supporting_chunks"] = self._supporting_chunks_for_framework(
                normalized,
                methodology_chunks,
            )
            ordered_frameworks.append(normalized)

        ordered_evidence = sorted(
            (dict(chunk) for chunk in evidence_chunks),
            key=lambda chunk: (
                -float(chunk.get("score") or 0.0),
                str(chunk.get("document_id") or ""),
                int(chunk.get("chunk_index") or 0),
            ),
        )
        ordered_commentary = self._cap_commentary_chunks(commentary_chunks, ordered_evidence)
        commentary_source_ids = {
            str(chunk.get("source_id") or "").strip()
            for chunk in ordered_commentary
            if str(chunk.get("source_id") or "").strip()
        }
        ordered_memos = [
            dict(memo)
            for memo in commentary_memos
            if str(memo.get("source_id") or "").strip() in commentary_source_ids
        ]
        ordered_memos.sort(key=lambda memo: str(memo.get("source_id") or ""))

        return {
            "frameworks": ordered_frameworks,
            "evidence_chunks": ordered_evidence,
            "commentary_chunks": ordered_commentary,
            "commentary_memos": ordered_memos,
        }
