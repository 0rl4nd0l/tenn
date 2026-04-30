from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

ClaimVerdict = Literal[
    "supported",
    "contradicted",
    "insufficient_evidence",
    "not_checkable",
]

_MAX_CLAIMS = 12
_MAX_EVIDENCE_REFS = 40
_MAX_TEXT_LEN = 1200

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9$])")
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9&.'-]{2,}\b")
_NUMBER_RE = re.compile(
    r"(?<!\w)(?:[$€£])?\(?-?\d[\d,]*(?:\.\d+)?\)?\s*(?:%|[mbk]|million|billion)?",
    re.IGNORECASE,
)
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

_STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "also",
    "because",
    "before",
    "being",
    "below",
    "between",
    "cannot",
    "could",
    "does",
    "from",
    "have",
    "into",
    "more",
    "only",
    "over",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "through",
    "under",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "without",
    "would",
}
_SUBJECTIVE_OR_FORWARD_RE = re.compile(
    r"\b(?:should|could|might|likely|possibly|probably|potentially|"
    r"attractive|cheap|expensive|good|bad|best|worst|undervalued|overvalued|"
    r"outperform|underperform|will|future)\b",
    re.IGNORECASE,
)
_MODAL_MAY_RE = re.compile(
    r"\bmay\s+(?:be|have|not|need|rise|fall|increase|decrease|outperform|"
    r"underperform|deliver|report|generate|face|benefit|reflect|indicate|suggest)\b",
    re.IGNORECASE,
)
_METRIC_RE = re.compile(
    r"\b(?:revenue|profit|loss|cash|debt|shares?|price|margin|growth|dividend|"
    r"capex|ebit|ebitda|npata|earnings|guidance|production|costs?)\b",
    re.IGNORECASE,
)

_TEXT_KEYS = (
    "text",
    "snippet",
    "excerpt",
    "content",
    "claim",
    "summary",
    "narrative",
    "message",
)
_SOURCE_HINT_KEYS = (
    "source_id",
    "document_id",
    "url",
    "source_url",
    "title",
    "source_name",
    "path",
    "pdf_path",
)


@dataclass(frozen=True)
class EvidenceRef:
    source_id: str | None
    title: str
    text: str
    url: str | None = None
    document_id: str | None = None

    @property
    def ref_id(self) -> str:
        for value in (self.source_id, self.document_id, self.url, self.title):
            cleaned = str(value or "").strip()
            if cleaned:
                return cleaned
        return "evidence"


def split_atomic_claims(answer_text: str) -> list[str]:
    """Return a bounded list of sentence-like factual claim candidates."""
    cleaned = _CODE_FENCE_RE.sub(" ", str(answer_text or "")).strip()
    if not cleaned:
        return []

    claims: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if set(line) <= {"-", "|", ":", " "}:
            continue
        if line.startswith("|") and line.endswith("|"):
            continue
        line = _BULLET_PREFIX_RE.sub("", line).strip()
        line = line.strip("#*> ")
        if not line:
            continue
        for part in _SENTENCE_SPLIT_RE.split(line):
            claim = part.strip().strip("-* ")
            claim = re.sub(r"\s+", " ", claim)
            if len(claim) < 8:
                continue
            if claim not in claims:
                claims.append(claim[:500])
            if len(claims) >= _MAX_CLAIMS:
                return claims
    return claims


def _clean_text(value: Any, limit: int = _MAX_TEXT_LEN) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip()


def _source_text(raw: dict[str, Any]) -> str:
    for key in _TEXT_KEYS:
        value = raw.get(key)
        if value not in (None, "", [], {}):
            return _clean_text(value)
    return ""


def _source_from_mapping(raw: dict[str, Any]) -> EvidenceRef | None:
    text = _source_text(raw)
    title = _clean_text(
        raw.get("title")
        or raw.get("source_name")
        or raw.get("source")
        or raw.get("document_id")
        or raw.get("source_id")
        or "Source",
        180,
    )
    if not text:
        text = title
    if not text:
        return None
    return EvidenceRef(
        source_id=_clean_text(raw.get("source_id") or raw.get("chunk_id"), 180) or None,
        title=title or "Source",
        text=text,
        url=_clean_text(raw.get("url") or raw.get("source_url"), 500) or None,
        document_id=_clean_text(
            raw.get("document_id") or raw.get("source_document_id"), 180
        )
        or None,
    )


def _iter_candidate_dicts(value: Any, *, depth: int = 0):
    if depth > 5:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_candidate_dicts(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value[:50]:
            yield from _iter_candidate_dicts(child, depth=depth + 1)


def build_evidence_refs(
    *,
    visible_sources: list[dict[str, Any]] | None = None,
    turn_evidence: list[dict[str, Any]] | None = None,
) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    seen: set[str] = set()

    def add_ref(raw: dict[str, Any]) -> None:
        if len(refs) >= _MAX_EVIDENCE_REFS:
            return
        ref = _source_from_mapping(raw)
        if ref is None:
            return
        key = (ref.source_id or ref.document_id or ref.url or ref.text).lower()
        if key in seen:
            return
        seen.add(key)
        refs.append(ref)

    for raw in visible_sources or []:
        if isinstance(raw, dict):
            add_ref(raw)

    for raw in turn_evidence or []:
        for candidate in _iter_candidate_dicts(raw):
            if len(refs) >= _MAX_EVIDENCE_REFS:
                break
            has_text = any(candidate.get(key) not in (None, "", [], {}) for key in _TEXT_KEYS)
            has_source = any(
                candidate.get(key) not in (None, "", [], {}) for key in _SOURCE_HINT_KEYS
            )
            if has_text or has_source:
                add_ref(candidate)

    return refs


def _terms(text: str) -> set[str]:
    terms: set[str] = set()
    for word in _WORD_RE.findall(text):
        lowered = word.lower().strip("'-.")
        if len(lowered) < 3 or lowered in _STOPWORDS:
            continue
        terms.add(lowered)
    return terms


def _numeric_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in _NUMBER_RE.findall(text):
        raw = match.lower().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
        raw = raw.strip().replace(" ", "")
        if raw.startswith("(") and raw.endswith(")"):
            raw = f"-{raw[1:-1]}"
        if not raw:
            continue
        tokens.add(raw)
        number_match = re.search(r"-?\d+(?:\.\d+)?", raw)
        if number_match:
            tokens.add(number_match.group(0))
    return tokens


def _measurement_tokens(text: str) -> set[str]:
    return {
        token
        for token in _numeric_tokens(text)
        if not re.fullmatch(r"(?:19|20)\d{2}", token)
    }


def _is_not_checkable(claim: str) -> str | None:
    text = claim.strip()
    if not text:
        return "empty_claim"
    if text.endswith("?"):
        return "question"
    if _SUBJECTIVE_OR_FORWARD_RE.search(text) or _MODAL_MAY_RE.search(text):
        return "subjective_or_forward_looking"
    terms = _terms(text)
    if len(terms) < 2 and not _numeric_tokens(text):
        return "not_enough_factual_content"
    return None


def _score_evidence(claim: str, ref: EvidenceRef) -> tuple[float, bool, bool]:
    claim_terms = _terms(claim)
    evidence_text = f"{ref.title} {ref.text}"
    evidence_terms = _terms(evidence_text)
    if not claim_terms:
        return 0.0, False, False

    overlap = claim_terms & evidence_terms
    overlap_ratio = len(overlap) / max(len(claim_terms), 1)
    claim_nums = _numeric_tokens(claim)
    evidence_nums = _numeric_tokens(evidence_text)
    claim_measurements = _measurement_tokens(claim)
    evidence_measurements = _measurement_tokens(evidence_text)
    numeric_supported = not claim_nums or claim_nums.issubset(evidence_nums)
    numeric_conflict = bool(
        claim_measurements
        and evidence_measurements
        and claim_measurements.isdisjoint(evidence_measurements)
        and overlap_ratio >= 0.45
        and _METRIC_RE.search(claim)
        and _METRIC_RE.search(evidence_text)
    )
    exactish = claim.lower().rstrip(".") in evidence_text.lower()
    score = 1.0 if exactish else overlap_ratio
    if numeric_supported and claim_nums:
        score += 0.2
    return min(score, 1.0), numeric_supported, numeric_conflict


def verify_claims_against_evidence(
    *,
    answer_text: str,
    visible_sources: list[dict[str, Any]] | None = None,
    turn_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    claims = split_atomic_claims(answer_text)
    if not claims and str(answer_text or "").strip():
        claims = [str(answer_text).strip()[:500]]

    evidence_refs = build_evidence_refs(
        visible_sources=visible_sources,
        turn_evidence=turn_evidence,
    )

    verdicts: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        uncheckable_reason = _is_not_checkable(claim)
        if uncheckable_reason is not None:
            verdicts.append(
                {
                    "claim_id": f"claim_{index}",
                    "claim_text": claim,
                    "verdict": "not_checkable",
                    "short_reason": "The claim is subjective, forward-looking, or not a factual assertion.",
                    "supporting_source_ids": [],
                    "contradicting_source_ids": [],
                    "uncheckable_reason": uncheckable_reason,
                    "confidence": "low",
                }
            )
            continue

        if not evidence_refs:
            verdicts.append(
                {
                    "claim_id": f"claim_{index}",
                    "claim_text": claim,
                    "verdict": "insufficient_evidence",
                    "short_reason": "No evidence was supplied for this assistant message.",
                    "supporting_source_ids": [],
                    "contradicting_source_ids": [],
                    "uncheckable_reason": None,
                    "confidence": "low",
                }
            )
            continue

        scored = [
            (ref, *_score_evidence(claim, ref))
            for ref in evidence_refs
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        contradictions = [ref for ref, _score, _numeric_ok, conflict in scored if conflict]
        supported = [
            ref
            for ref, score, numeric_ok, _conflict in scored
            if numeric_ok and score >= (0.6 if _numeric_tokens(claim) else 0.72)
        ]

        if supported:
            verdict: ClaimVerdict = "supported"
            selected = supported[:3]
            reason = "The claim matches supplied evidence for the key terms and numeric values."
            confidence = "medium"
            contradicting: list[EvidenceRef] = []
        elif contradictions:
            verdict = "contradicted"
            selected = []
            contradicting = contradictions[:3]
            reason = "Supplied evidence discusses the same metric but contains conflicting numeric values."
            confidence = "medium"
        else:
            verdict = "insufficient_evidence"
            selected = []
            contradicting = []
            reason = "Supplied evidence was too weak or incomplete to verify the claim."
            confidence = "low"

        verdicts.append(
            {
                "claim_id": f"claim_{index}",
                "claim_text": claim,
                "verdict": verdict,
                "short_reason": reason,
                "supporting_source_ids": [ref.ref_id for ref in selected],
                "contradicting_source_ids": [ref.ref_id for ref in contradicting],
                "uncheckable_reason": None,
                "confidence": confidence,
            }
        )

    return {
        "verdicts": verdicts,
        "evidence_count": len(evidence_refs),
    }
