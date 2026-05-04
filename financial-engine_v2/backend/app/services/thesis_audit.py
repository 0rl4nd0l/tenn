from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from app.services.claim_verification import split_atomic_claims
from app.services.query_orchestrator import QueryOrchestrator

logger = logging.getLogger(__name__)

ClaimType = Literal[
    "numeric_fact",
    "company_narrative",
    "causal_claim",
    "catalyst_timing",
    "valuation_assumption",
    "market_sector_claim",
]
ClaimStatus = Literal[
    "supported",
    "partially_supported",
    "contradicted",
    "stale",
    "assumption",
    "DATA_MISSING",
]
ConfidenceLabel = Literal["Confirmed", "Inferred", "Speculative"]

CLAIM_TYPES: tuple[str, ...] = (
    "numeric_fact",
    "company_narrative",
    "causal_claim",
    "catalyst_timing",
    "valuation_assumption",
    "market_sector_claim",
)
CLAIM_STATUSES: tuple[str, ...] = (
    "supported",
    "partially_supported",
    "contradicted",
    "stale",
    "assumption",
    "DATA_MISSING",
)
CONFIDENCE_LABELS: tuple[str, ...] = ("Confirmed", "Inferred", "Speculative")
CONTRARIAN_PACKS: tuple[str, ...] = (
    "factual_break",
    "causal_break",
    "timing_break",
    "financing_break",
    "peer_base_rate_break",
    "valuation_break",
)

_MAX_REPORT_CHARS = 300_000
_MAX_PROMPT_CHARS = 28_000
_MAX_CLAIMS = 14
_MAX_ASSUMPTIONS = 10
_MAX_EVIDENCE = 80

_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9&.'-]{2,}\b")
_NUMBER_RE = re.compile(
    r"(?<!\w)(?:[$€£])?\(?-?\d[\d,]*(?:\.\d+)?\)?\s*(?:%|[mbk]|million|billion|bn|mn)?",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9$])")
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,10}$")
_YEAR_RE = re.compile(r"\b(?:FY)?((?:19|20)\d{2})\b", re.IGNORECASE)

_STOPWORDS = {
    "about",
    "above",
    "after",
    "against",
    "also",
    "because",
    "before",
    "being",
    "between",
    "cannot",
    "could",
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
_METRIC_WORDS = {
    "revenue",
    "sales",
    "ebit",
    "ebitda",
    "npata",
    "npat",
    "profit",
    "loss",
    "cash",
    "debt",
    "capex",
    "shares",
    "margin",
    "dividend",
    "production",
    "cost",
    "costs",
    "guidance",
    "earnings",
}
_VALUATION_RE = re.compile(
    r"\b(?:valuation|valued|rerat(?:e|ing)|multiple|p/e|ev/ebitda|dcf|"
    r"discount|target price|fair value|upside|downside|cheap|expensive)\b",
    re.IGNORECASE,
)
_TIMING_RE = re.compile(
    r"\b(?:catalyst|by\s+(?:q[1-4]|fy)?\d{2,4}|next quarter|next year|"
    r"near[- ]term|medium[- ]term|long[- ]term|within|after|before|when|"
    r"approval|commissioning|ramp[- ]?up)\b",
    re.IGNORECASE,
)
_MARKET_RE = re.compile(
    r"\b(?:sector|market|commodity|commodities|peer|peers|china|macro|"
    r"cycle|demand|supply|iron ore|copper|lithium|gold|coal|oil|gas)\b",
    re.IGNORECASE,
)
_CAUSAL_RE = re.compile(
    r"\b(?:because|due to|driven by|drives|supports|leads? to|therefore|"
    r"as a result|caused by|benefits? from|depends on)\b",
    re.IGNORECASE,
)
_MODAL_RE = re.compile(
    r"\b(?:assume|assumes|assuming|should|could|might|may|likely|expects?|"
    r"forecast|target|will|would|if)\b",
    re.IGNORECASE,
)
_NEGATIVE_RE = re.compile(
    r"\b(?:decline|fall|fell|falling|weak|weaker|negative|risk|pressure|"
    r"miss|below|deteriorat|worse|loss)\b",
    re.IGNORECASE,
)
_POSITIVE_RE = re.compile(
    r"\b(?:increase|rise|rising|improve|improved|strong|stronger|positive|"
    r"beat|above|growth|expand|benefit)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResearchReportInput:
    ticker: str
    report_text: str
    filename: str | None = None
    report_id: str | None = None
    focus: str | None = None


@dataclass(frozen=True)
class ReportSpan:
    span_id: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class EvidenceSpan:
    evidence_id: str
    source_layer: str
    source_type: str
    text: str
    title: str | None = None
    published_at: str | None = None
    document_id: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ThesisClaim:
    claim_id: str
    text: str
    claim_type: ClaimType
    report_span: ReportSpan
    confidence_label: ConfidenceLabel
    load_bearing_score: float
    load_bearing_rank: int


@dataclass(frozen=True)
class ThesisAssumption:
    assumption_id: str
    text: str
    report_span: ReportSpan | None
    confidence_label: ConfidenceLabel
    related_claim_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClaimVerification:
    claim_id: str
    status: ClaimStatus
    confidence_label: ConfidenceLabel
    rationale: str
    report_span: ReportSpan
    independent_evidence_spans: list[EvidenceSpan] = field(default_factory=list)
    contradicting_evidence_spans: list[EvidenceSpan] = field(default_factory=list)
    evidence_gap: str | None = None


@dataclass(frozen=True)
class ContrarianFinding:
    break_pack: str
    finding: str
    claim_ids: list[str]
    status: ClaimStatus
    confidence_label: ConfidenceLabel
    evidence_spans: list[EvidenceSpan] = field(default_factory=list)


@dataclass(frozen=True)
class UserThesisMemoryProposal:
    proposal_type: Literal["create_thesis", "add_evidence", "invalidate"]
    statement: str
    signal: str | None
    confidence: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ThesisAuditReport:
    audit_id: str
    ticker: str
    generated_at: str
    report_source: dict[str, Any]
    thesis_summary: str
    claims: list[ThesisClaim]
    hidden_assumptions: list[ThesisAssumption]
    verification_matrix: list[ClaimVerification]
    contrarian_findings: list[ContrarianFinding]
    strongest_disconfirming_evidence: list[ContrarianFinding]
    report_to_reality_delta: str | None
    change_my_mind_triggers: list[str]
    next_diligence_questions: list[str]
    user_thesis_memory_proposals: list[UserThesisMemoryProposal]
    evidence_summary: dict[str, Any]
    guardrails: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThesisAuditCoverageReport:
    ticker: str
    generated_at: str
    evidence_summary: dict[str, Any]
    guardrails: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_ticker(value: str) -> str:
    ticker = str(value or "").strip().upper()
    if not ticker or not _TICKER_RE.fullmatch(ticker):
        raise ValueError("ticker must be 1-10 ASX ticker characters")
    return ticker


def _clean_text(value: Any, *, limit: int | None = None) -> str:
    text = re.sub(r"[ \t]+", " ", str(value or "")).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if limit is not None and len(text) > limit:
        return text[:limit].rstrip()
    return text


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
        raw = (
            match.lower()
            .replace(",", "")
            .replace("$", "")
            .replace("€", "")
            .replace("£", "")
            .strip()
            .replace(" ", "")
        )
        if raw.startswith("(") and raw.endswith(")"):
            raw = f"-{raw[1:-1]}"
        if raw:
            tokens.add(raw)
        number_match = re.search(r"-?\d+(?:\.\d+)?", raw)
        if number_match:
            tokens.add(number_match.group(0))
    return tokens


def _non_year_numeric_tokens(tokens: set[str]) -> set[str]:
    non_year = {
        token
        for token in tokens
        if not re.fullmatch(r"(?:19|20)\d{2}", token)
    }
    return non_year or tokens


def _extract_report_spans(report_text: str, *, max_spans: int = 160) -> list[ReportSpan]:
    spans: list[ReportSpan] = []
    seen: set[str] = set()

    for match in re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", report_text):
        block = _clean_text(match.group(0))
        if len(block) < 35:
            continue
        parts = _SENTENCE_RE.split(block)
        offset = match.start()
        for part in parts:
            text = _clean_text(part)
            if len(text) < 35:
                continue
            normalized = text.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            local_start = report_text.find(part, offset)
            start = local_start if local_start >= 0 else match.start()
            end = min(start + len(part), len(report_text))
            spans.append(
                ReportSpan(
                    span_id=f"report_span_{len(spans) + 1}",
                    start=start,
                    end=end,
                    text=text[:800].rstrip(),
                )
            )
            if len(spans) >= max_spans:
                return spans

    if not spans and report_text.strip():
        snippet = _clean_text(report_text, limit=800)
        spans.append(ReportSpan("report_span_1", 0, min(len(report_text), len(snippet)), snippet))
    return spans


def _span_for_text(text: str, spans: list[ReportSpan]) -> ReportSpan:
    if not spans:
        return ReportSpan("report_span_1", 0, len(text), _clean_text(text, limit=800))
    normalized = _clean_text(text).lower()
    best = spans[0]
    best_score = 0.0
    claim_terms = _terms(normalized)
    for span in spans:
        span_text = span.text.lower()
        if normalized and normalized in span_text:
            return span
        span_terms = _terms(span_text)
        if not claim_terms:
            score = 0.0
        else:
            score = len(claim_terms & span_terms) / max(len(claim_terms), 1)
        if score > best_score:
            best = span
            best_score = score
    return best


def _classify_claim_type(text: str) -> ClaimType:
    lowered = text.lower()
    term_set = _terms(lowered)
    has_number = bool(_numeric_tokens(text))
    if has_number and (term_set & _METRIC_WORDS):
        return "numeric_fact"
    if _VALUATION_RE.search(text):
        return "valuation_assumption"
    if _TIMING_RE.search(text):
        return "catalyst_timing"
    if _MARKET_RE.search(text):
        return "market_sector_claim"
    if _CAUSAL_RE.search(text):
        return "causal_claim"
    return "company_narrative"


def _confidence_label(raw: Any, *, default: ConfidenceLabel = "Inferred") -> ConfidenceLabel:
    value = str(raw or "").strip()
    if value in CONFIDENCE_LABELS:
        return value  # type: ignore[return-value]
    lowered = value.lower()
    if lowered in {"confirmed", "high"}:
        return "Confirmed"
    if lowered in {"speculative", "low"}:
        return "Speculative"
    return default


def _bounded_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def _load_bearing_score(text: str, claim_type: ClaimType, index: int) -> float:
    score = 0.35
    if claim_type in {"numeric_fact", "valuation_assumption"}:
        score += 0.22
    if claim_type in {"causal_claim", "catalyst_timing"}:
        score += 0.18
    if _MODAL_RE.search(text):
        score += 0.08
    if _numeric_tokens(text):
        score += 0.08
    if index <= 3:
        score += 0.08
    return _bounded_score(score)


def _build_extraction_prompt(
    report: ResearchReportInput,
    spans: list[ReportSpan],
) -> str:
    span_payload = [
        {"span_id": span.span_id, "text": span.text}
        for span in spans[:45]
    ]
    data = json.dumps(span_payload, ensure_ascii=False)
    focus = f"\nFocus: {report.focus}" if report.focus else ""
    return (
        "You are extracting a thesis audit input from a non-canonical company research report. "
        "The report is not financial truth. Reconstruct the author's thesis faithfully before critique.\n"
        "Output ONLY valid JSON with this shape:\n"
        "{"
        '"thesis_summary":"2-4 sentences faithful to the report",'
        '"claims":[{"text":"atomic claim","claim_type":"numeric_fact|company_narrative|causal_claim|catalyst_timing|valuation_assumption|market_sector_claim","report_span_id":"report_span_1","confidence_label":"Confirmed|Inferred|Speculative"}],'
        '"hidden_assumptions":[{"text":"hidden assumption","report_span_id":"report_span_1","related_claim_text":"claim text","confidence_label":"Confirmed|Inferred|Speculative"}]'
        "}\n"
        "Rules: keep claims atomic; do not invent facts not present in spans; numeric report claims remain report-derived only; "
        f"return at most {_MAX_CLAIMS} claims and {_MAX_ASSUMPTIONS} assumptions.\n"
        f"Ticker: {report.ticker}.{focus}\n"
        f"Report spans:\n{data[:_MAX_PROMPT_CHARS]}"
    )


def _build_evidence_query(
    *,
    ticker: str,
    claims: list[ThesisClaim] | None = None,
    focus: str | None = None,
) -> str:
    claim_lines = []
    for claim in (claims or [])[:_MAX_CLAIMS]:
        claim_lines.append(f"- {claim.claim_id} [{claim.claim_type}]: {claim.text}")
    focus_text = f"\nFocus: {_clean_text(focus, limit=300)}" if focus else ""
    claims_text = "\nClaims to verify:\n" + "\n".join(claim_lines) if claim_lines else ""
    return (
        f"Research report thesis audit for {ticker}: verify report claims against Tenn evidence."
        f"{focus_text}{claims_text}"
    )[:10_000]


def _call_extractor(
    report: ResearchReportInput,
    spans: list[ReportSpan],
    llm_fn: Callable[..., Any] | None,
) -> dict[str, Any] | None:
    if llm_fn is None:
        try:
            from app.services.llm import generate_json
        except Exception as exc:
            logger.debug("thesis_audit: LLM unavailable during import: %s", exc)
            return None
        llm_fn = generate_json
    try:
        return llm_fn(
            prompt=_build_extraction_prompt(report, spans),
            metadata={
                "component": "thesis_audit",
                "task_type": "reasoning",
                "ticker": report.ticker,
            },
            timeout=18.0,
        )
    except TypeError:
        try:
            return llm_fn(_build_extraction_prompt(report, spans))
        except Exception as exc:
            logger.warning("thesis_audit: extractor failed: %s", exc)
            return None
    except Exception as exc:
        logger.warning("thesis_audit: extractor failed: %s", exc)
        return None


def _fallback_summary(report_text: str, claims: list[str]) -> str:
    if claims:
        return " ".join(claims[:3])[:900].rstrip()
    sentences = split_atomic_claims(report_text)
    return " ".join(sentences[:3])[:900].rstrip() or "No clear thesis could be reconstructed from the supplied report."


def _normalize_claims(
    raw_payload: dict[str, Any] | None,
    spans: list[ReportSpan],
    report_text: str,
) -> list[ThesisClaim]:
    raw_claims = raw_payload.get("claims") if isinstance(raw_payload, dict) else None
    candidates: list[dict[str, Any]] = []
    if isinstance(raw_claims, list):
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            text = _clean_text(item.get("text"), limit=500)
            if len(text) < 12:
                continue
            candidates.append(dict(item, text=text))

    if not candidates:
        for claim in split_atomic_claims(report_text)[:_MAX_CLAIMS]:
            candidates.append({"text": claim})

    normalized: list[ThesisClaim] = []
    seen: set[str] = set()
    for index, item in enumerate(candidates[:_MAX_CLAIMS], start=1):
        text = _clean_text(item.get("text"), limit=500)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        raw_type = str(item.get("claim_type") or "").strip()
        claim_type = raw_type if raw_type in CLAIM_TYPES else _classify_claim_type(text)
        span_id = str(item.get("report_span_id") or "").strip()
        span = next((candidate for candidate in spans if candidate.span_id == span_id), None)
        if span is None:
            span = _span_for_text(text, spans)
        normalized.append(
            ThesisClaim(
                claim_id=f"claim_{len(normalized) + 1}",
                text=text,
                claim_type=claim_type,  # type: ignore[arg-type]
                report_span=span,
                confidence_label=_confidence_label(item.get("confidence_label")),
                load_bearing_score=_load_bearing_score(text, claim_type, index),  # type: ignore[arg-type]
                load_bearing_rank=0,
            )
        )

    ranked = sorted(
        normalized,
        key=lambda claim: (claim.load_bearing_score, -int(claim.claim_id.split("_")[-1])),
        reverse=True,
    )
    ranks = {claim.claim_id: idx for idx, claim in enumerate(ranked, start=1)}
    return [
        ThesisClaim(
            claim_id=claim.claim_id,
            text=claim.text,
            claim_type=claim.claim_type,
            report_span=claim.report_span,
            confidence_label=claim.confidence_label,
            load_bearing_score=claim.load_bearing_score,
            load_bearing_rank=ranks[claim.claim_id],
        )
        for claim in normalized
    ]


def _normalize_assumptions(
    raw_payload: dict[str, Any] | None,
    claims: list[ThesisClaim],
    spans: list[ReportSpan],
) -> list[ThesisAssumption]:
    raw_assumptions = raw_payload.get("hidden_assumptions") if isinstance(raw_payload, dict) else None
    assumptions: list[ThesisAssumption] = []
    seen: set[str] = set()

    if isinstance(raw_assumptions, list):
        for item in raw_assumptions:
            if not isinstance(item, dict):
                continue
            text = _clean_text(item.get("text"), limit=500)
            if len(text) < 12:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            span = None
            span_id = str(item.get("report_span_id") or "").strip()
            if span_id:
                span = next((candidate for candidate in spans if candidate.span_id == span_id), None)
            if span is None:
                span = _span_for_text(text, spans)
            related_text = _clean_text(item.get("related_claim_text"), limit=300)
            related = [
                claim.claim_id
                for claim in claims
                if related_text and (_terms(related_text) & _terms(claim.text))
            ][:3]
            assumptions.append(
                ThesisAssumption(
                    assumption_id=f"assumption_{len(assumptions) + 1}",
                    text=text,
                    report_span=span,
                    confidence_label=_confidence_label(item.get("confidence_label"), default="Speculative"),
                    related_claim_ids=related,
                )
            )
            if len(assumptions) >= _MAX_ASSUMPTIONS:
                return assumptions

    for claim in claims:
        if len(assumptions) >= _MAX_ASSUMPTIONS:
            break
        if claim.claim_type not in {"causal_claim", "catalyst_timing", "valuation_assumption"} and not _MODAL_RE.search(claim.text):
            continue
        text = f"The report depends on this claim remaining true: {claim.text}"
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        assumptions.append(
            ThesisAssumption(
                assumption_id=f"assumption_{len(assumptions) + 1}",
                text=text,
                report_span=claim.report_span,
                confidence_label="Speculative",
                related_claim_ids=[claim.claim_id],
            )
        )
    return assumptions


def _safe_get_text(item: dict[str, Any]) -> str:
    for key in ("text", "statement", "summary", "snippet", "content", "narrative", "title"):
        value = item.get(key)
        if value not in (None, "", [], {}):
            return _clean_text(value, limit=1200)
    return ""


def _financial_row_text(row: dict[str, Any]) -> str:
    parts = []
    period = " ".join(
        str(row.get(key) or "").strip()
        for key in ("period_type", "period_end")
        if str(row.get(key) or "").strip()
    )
    if period:
        parts.append(period)
    for key in (
        "revenue",
        "ebit",
        "ebitda",
        "np_attributable",
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "capex",
        "cash_end",
        "net_debt",
        "shares_outstanding",
    ):
        value = row.get(key)
        if value not in (None, "", [], {}):
            parts.append(f"{key}={value}")
    return "; ".join(parts)


def _flatten_evidence(evidence: dict[str, Any]) -> list[EvidenceSpan]:
    spans: list[EvidenceSpan] = []
    seen: set[str] = set()

    def add(
        *,
        layer: str,
        source_type: str,
        text: str,
        title: str | None = None,
        item: dict[str, Any] | None = None,
    ) -> None:
        if len(spans) >= _MAX_EVIDENCE:
            return
        cleaned = _clean_text(text, limit=1200)
        if len(cleaned) < 8:
            return
        item = item or {}
        key = f"{layer}|{source_type}|{cleaned}".lower()
        if key in seen:
            return
        seen.add(key)
        evidence_id = f"evidence_{len(spans) + 1}"
        spans.append(
            EvidenceSpan(
                evidence_id=evidence_id,
                source_layer=layer,
                source_type=source_type,
                text=cleaned,
                title=_clean_text(title or item.get("title") or item.get("source_name"), limit=180) or None,
                published_at=_clean_text(item.get("published_at") or item.get("date"), limit=80) or None,
                document_id=_clean_text(
                    item.get("document_id")
                    or item.get("source_document_id")
                    or item.get("source_id")
                    or item.get("entry_id"),
                    limit=180,
                )
                or None,
                url=_clean_text(item.get("url") or item.get("source_url"), limit=500) or None,
                metadata={
                    key: value
                    for key, value in item.items()
                    if key
                    in {
                        "ticker",
                        "period_end",
                        "period_type",
                        "type",
                        "signal",
                        "status",
                        "confidence",
                        "active_score",
                    }
                },
            )
        )

    financial_truth = evidence.get("financial_truth") if isinstance(evidence.get("financial_truth"), dict) else {}
    snapshot = financial_truth.get("latest_financial_snapshot")
    if isinstance(snapshot, dict):
        add(
            layer="financial_truth",
            source_type="latest_financial_snapshot",
            text=_financial_row_text(snapshot),
            title="Latest financial snapshot",
            item=snapshot,
        )
    for row in financial_truth.get("financials") or financial_truth.get("items") or []:
        if isinstance(row, dict):
            add(
                layer="financial_truth",
                source_type="financial_period",
                text=_financial_row_text(row),
                title="Canonical financial period",
                item=row,
            )
    for row in financial_truth.get("announcement_context") or []:
        if isinstance(row, dict):
            add(layer="financial_truth", source_type="announcement_context", text=_safe_get_text(row), item=row)
    for row in financial_truth.get("docs") or []:
        if isinstance(row, dict):
            text = _safe_get_text(row)
            if text:
                add(layer="financial_truth", source_type="document_metadata", text=text, item=row)

    for layer in ("company_memory", "market_memory", "user_thesis_memory"):
        payload = evidence.get(layer) if isinstance(evidence.get(layer), dict) else {}
        items: list[Any] = []
        if layer == "market_memory":
            items.extend(payload.get("sector_items") or [])
            items.extend(payload.get("macro_items") or [])
            items.extend(payload.get("items") or [])
        else:
            items.extend(payload.get("items") or [])
        for row in items:
            if isinstance(row, dict):
                add(
                    layer=layer,
                    source_type=_clean_text(row.get("type") or row.get("entry_type") or "memory", limit=80),
                    text=_safe_get_text(row),
                    item=row,
                )
    return spans


def _coverage_status(
    *,
    evidence_span_count: int,
    sufficient_for_analysis: bool,
    missing_categories: list[str],
) -> tuple[str, str]:
    if evidence_span_count <= 0:
        return (
            "no_backend_evidence",
            "No backend evidence is available for this ticker; treat the audit as extraction-only until Tenn has filings, financials, or memory context.",
        )
    if not sufficient_for_analysis:
        if missing_categories:
            missing = ", ".join(missing_categories)
            return (
                "limited",
                f"Backend evidence is incomplete after recovery; missing categories: {missing}.",
            )
        return (
            "limited",
            "Backend evidence is incomplete after recovery.",
        )
    if missing_categories:
        missing = ", ".join(missing_categories)
        return (
            "partial",
            f"Backend evidence is usable but still missing: {missing}.",
        )
    return (
        "ready",
        "Backend evidence coverage is sufficient for a thesis audit.",
    )


def _proposal_gate(evidence_summary: dict[str, Any]) -> dict[str, Any]:
    evidence_span_count = int(evidence_summary.get("evidence_span_count") or 0)
    sufficient = evidence_summary.get("sufficient_for_analysis") is True
    if evidence_span_count <= 0:
        return {
            "allowed": False,
            "reason": "no_backend_evidence",
            "message": "Thesis memory proposals are blocked until backend evidence exists for this ticker.",
        }
    if not sufficient:
        return {
            "allowed": False,
            "reason": "insufficient_backend_evidence",
            "message": "Thesis memory proposals are blocked until backend evidence is sufficient for analysis.",
        }
    return {
        "allowed": True,
        "reason": "evidence_sufficient",
        "message": "Backend evidence is sufficient for staged thesis memory proposals.",
    }


def _build_evidence_summary(orchestrated: Any, evidence_spans: list[EvidenceSpan]) -> dict[str, Any]:
    missing_categories = list(orchestrated.missing_categories_after_recovery)
    evidence_span_count = len(evidence_spans)
    sufficient_for_analysis = bool(orchestrated.sufficient_for_analysis)
    coverage_status, coverage_message = _coverage_status(
        evidence_span_count=evidence_span_count,
        sufficient_for_analysis=sufficient_for_analysis,
        missing_categories=missing_categories,
    )
    summary = {
        "source_plan": list(orchestrated.source_plan),
        "evidence_span_count": evidence_span_count,
        "memory_read_only": True,
        "sufficient_for_analysis": sufficient_for_analysis,
        "missing_categories_after_recovery": missing_categories,
        "coverage_status": coverage_status,
        "coverage_message": coverage_message,
    }
    summary["proposal_gate"] = _proposal_gate(summary)
    return summary


def _score_evidence(claim: ThesisClaim, evidence: EvidenceSpan) -> tuple[float, bool, bool]:
    claim_terms = _terms(claim.text)
    evidence_terms = _terms(f"{evidence.title or ''} {evidence.text}")
    if not claim_terms:
        return 0.0, False, False
    overlap_ratio = len(claim_terms & evidence_terms) / max(len(claim_terms), 1)
    claim_numbers = _numeric_tokens(claim.text)
    evidence_numbers = _numeric_tokens(evidence.text)
    claim_metric_numbers = _non_year_numeric_tokens(claim_numbers)
    evidence_metric_numbers = _non_year_numeric_tokens(evidence_numbers)
    numeric_ok = not claim_numbers or claim_metric_numbers.issubset(evidence_metric_numbers)
    claim_metric_terms = claim_terms & _METRIC_WORDS
    evidence_metric_terms = evidence_terms & _METRIC_WORDS
    metric_overlap = bool(claim_metric_terms & evidence_metric_terms)
    numeric_conflict = bool(
        claim_numbers
        and evidence_numbers
        and metric_overlap
        and claim_metric_numbers.isdisjoint(evidence_metric_numbers)
    )
    polarity_conflict = bool(
        overlap_ratio >= 0.48
        and ((_POSITIVE_RE.search(claim.text) and _NEGATIVE_RE.search(evidence.text))
             or (_NEGATIVE_RE.search(claim.text) and _POSITIVE_RE.search(evidence.text)))
    )
    exactish = claim.text.lower().rstrip(".") in evidence.text.lower()
    score = 1.0 if exactish else overlap_ratio
    if claim_numbers and numeric_ok:
        score += 0.2
        if metric_overlap:
            score += 0.3
    return _bounded_score(score), numeric_ok, numeric_conflict or polarity_conflict


def _is_stale_without_current_support(claim: ThesisClaim, best_score: float) -> bool:
    years = [int(match.group(1)) for match in _YEAR_RE.finditer(claim.text)]
    if not years:
        return False
    current_year = datetime.now(timezone.utc).year
    return max(years) <= current_year - 3 and best_score < 0.45


def _verify_claims(
    claims: list[ThesisClaim],
    evidence_spans: list[EvidenceSpan],
) -> list[ClaimVerification]:
    verifications: list[ClaimVerification] = []
    for claim in claims:
        candidate_evidence = (
            [span for span in evidence_spans if span.source_layer == "financial_truth"]
            if claim.claim_type == "numeric_fact"
            else evidence_spans
        )
        scored = [
            (span, *_score_evidence(claim, span))
            for span in candidate_evidence
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        best_score = scored[0][1] if scored else 0.0
        contradictions = [span for span, _score, _numeric_ok, conflict in scored if conflict][:3]
        supported = [
            span
            for span, score, numeric_ok, _conflict in scored
            if numeric_ok and score >= (0.58 if claim.claim_type == "numeric_fact" else 0.7)
        ][:3]
        partial = [
            span
            for span, score, numeric_ok, _conflict in scored
            if numeric_ok and score >= 0.42
        ][:3]

        if contradictions:
            status: ClaimStatus = "contradicted"
            confidence: ConfidenceLabel = "Confirmed"
            rationale = "Independent evidence conflicts with the claim on overlapping terms or numeric values."
            evidence = []
            contradicting = contradictions
            gap = None
        elif supported:
            status = "supported"
            confidence = "Confirmed"
            rationale = "Independent evidence supports the claim's key terms and any numeric values."
            evidence = supported
            contradicting = []
            gap = None
        elif partial:
            status = "partially_supported"
            confidence = "Inferred"
            rationale = "Independent evidence overlaps with the claim, but does not fully verify it."
            evidence = partial
            contradicting = []
            gap = "Evidence is directionally relevant but incomplete."
        elif _is_stale_without_current_support(claim, best_score):
            status = "stale"
            confidence = "Speculative"
            rationale = "The claim appears anchored to older dated context and current support was not found."
            evidence = []
            contradicting = []
            gap = "Current-period evidence is missing."
        elif claim.claim_type in {"valuation_assumption", "causal_claim", "catalyst_timing"} or _MODAL_RE.search(claim.text):
            status = "assumption"
            confidence = "Speculative"
            rationale = "The claim is forward-looking or inferential and should remain an assumption unless independently verified."
            evidence = []
            contradicting = []
            gap = "No decisive independent evidence was available."
        else:
            status = "DATA_MISSING"
            confidence = "Speculative"
            rationale = "No independent evidence in Tenn's current evidence layers was sufficient to verify the claim."
            evidence = []
            contradicting = []
            gap = "Independent evidence missing."

        verifications.append(
            ClaimVerification(
                claim_id=claim.claim_id,
                status=status,
                confidence_label=confidence,
                rationale=rationale,
                report_span=claim.report_span,
                independent_evidence_spans=evidence,
                contradicting_evidence_spans=contradicting,
                evidence_gap=gap,
            )
        )
    return verifications


def _contrarian_findings(
    claims: list[ThesisClaim],
    verifications: list[ClaimVerification],
) -> list[ContrarianFinding]:
    claim_by_id = {claim.claim_id: claim for claim in claims}
    verification_by_id = {verification.claim_id: verification for verification in verifications}
    findings: list[ContrarianFinding] = []

    pack_claim_types = {
        "factual_break": {"numeric_fact", "company_narrative"},
        "causal_break": {"causal_claim"},
        "timing_break": {"catalyst_timing"},
        "financing_break": {"numeric_fact", "valuation_assumption"},
        "peer_base_rate_break": {"market_sector_claim", "company_narrative"},
        "valuation_break": {"valuation_assumption", "numeric_fact"},
    }

    for pack in CONTRARIAN_PACKS:
        relevant = [
            claim
            for claim in claims
            if claim.claim_type in pack_claim_types[pack]
        ]
        weak = [
            claim
            for claim in relevant
            if verification_by_id[claim.claim_id].status
            in {"contradicted", "partially_supported", "assumption", "DATA_MISSING", "stale"}
        ]
        if not weak:
            continue
        selected = sorted(weak, key=lambda claim: claim.load_bearing_score, reverse=True)[:2]
        verifs = [verification_by_id[claim.claim_id] for claim in selected]
        strongest = next((verification for verification in verifs if verification.status == "contradicted"), verifs[0])
        evidence = [
            *strongest.contradicting_evidence_spans,
            *strongest.independent_evidence_spans,
        ][:3]
        if strongest.status == "contradicted":
            finding = f"{pack.replace('_', ' ')}: independent evidence contradicts a load-bearing report claim."
            confidence: ConfidenceLabel = "Confirmed"
        elif strongest.status in {"DATA_MISSING", "assumption"}:
            finding = f"{pack.replace('_', ' ')}: a load-bearing report claim is not independently verified."
            confidence = "Speculative"
        else:
            finding = f"{pack.replace('_', ' ')}: support is incomplete for a load-bearing report claim."
            confidence = "Inferred"
        findings.append(
            ContrarianFinding(
                break_pack=pack,
                finding=finding,
                claim_ids=[claim.claim_id for claim in selected],
                status=strongest.status,
                confidence_label=confidence,
                evidence_spans=evidence,
            )
        )
    return findings


def _change_my_mind_triggers(
    claims: list[ThesisClaim],
    verifications: list[ClaimVerification],
) -> list[str]:
    claim_by_id = {claim.claim_id: claim for claim in claims}
    triggers: list[str] = []
    for verification in verifications:
        if verification.status not in {"contradicted", "DATA_MISSING", "assumption", "stale"}:
            continue
        claim = claim_by_id[verification.claim_id]
        if verification.status == "contradicted":
            triggers.append(f"Resolve contradiction for {verification.claim_id}: {claim.text}")
        elif verification.status == "stale":
            triggers.append(f"Find current evidence for stale claim {verification.claim_id}: {claim.text}")
        elif verification.status == "DATA_MISSING":
            triggers.append(f"Do not rely on {verification.claim_id} until independent evidence exists: {claim.text}")
        else:
            triggers.append(f"Track explicit evidence that would turn assumption {verification.claim_id} into a verified claim.")
        if len(triggers) >= 8:
            break
    return triggers


def _diligence_questions(
    claims: list[ThesisClaim],
    verifications: list[ClaimVerification],
    assumptions: list[ThesisAssumption],
) -> list[str]:
    claim_by_id = {claim.claim_id: claim for claim in claims}
    questions: list[str] = []
    for verification in verifications:
        if verification.status in {"supported", "partially_supported"}:
            continue
        claim = claim_by_id[verification.claim_id]
        if claim.claim_type == "numeric_fact":
            questions.append(f"Which canonical filing line verifies or refutes {claim.text}?")
        elif claim.claim_type == "valuation_assumption":
            questions.append(f"What valuation sensitivity breaks {claim.text}?")
        elif claim.claim_type == "catalyst_timing":
            questions.append(f"What dated milestone evidence confirms the timing in {claim.text}?")
        elif claim.claim_type == "market_sector_claim":
            questions.append(f"Which peer or sector data independently supports {claim.text}?")
        else:
            questions.append(f"What independent company evidence supports or breaks {claim.text}?")
        if len(questions) >= 8:
            break
    for assumption in assumptions[:3]:
        if len(questions) >= 10:
            break
        questions.append(f"What evidence would falsify this hidden assumption: {assumption.text}?")
    return questions


def _memory_proposals(
    *,
    audit_id: str,
    ticker: str,
    thesis_summary: str,
    claims: list[ThesisClaim],
    verifications: list[ClaimVerification],
    evidence_summary: dict[str, Any],
) -> list[UserThesisMemoryProposal]:
    proposal_gate = evidence_summary.get("proposal_gate") if isinstance(evidence_summary, dict) else None
    if isinstance(proposal_gate, dict) and proposal_gate.get("allowed") is False:
        return []

    proposals: list[UserThesisMemoryProposal] = []
    if thesis_summary:
        proposals.append(
            UserThesisMemoryProposal(
                proposal_type="create_thesis",
                statement=thesis_summary[:900].rstrip(),
                signal=None,
                confidence=0.55,
                metadata={
                    "source": "research_report_thesis_audit",
                    "audit_id": audit_id,
                    "requires_confirmation": True,
                    "non_canonical_report_source": True,
                },
            )
        )
    claim_by_id = {claim.claim_id: claim for claim in claims}
    for verification in verifications:
        if len(proposals) >= 5:
            break
        if verification.status not in {"supported", "partially_supported", "contradicted"}:
            continue
        claim = claim_by_id[verification.claim_id]
        proposals.append(
            UserThesisMemoryProposal(
                proposal_type="add_evidence",
                statement=claim.text,
                signal=None,
                confidence=0.72 if verification.status == "supported" else 0.6,
                metadata={
                    "source": "research_report_thesis_audit",
                    "audit_id": audit_id,
                    "claim_id": claim.claim_id,
                    "claim_type": claim.claim_type,
                    "verification_status": verification.status,
                    "is_supporting": verification.status != "contradicted",
                    "report_span": asdict(claim.report_span),
                    "evidence_span_ids": [
                        span.evidence_id
                        for span in (
                            verification.independent_evidence_spans
                            + verification.contradicting_evidence_spans
                        )
                    ],
                    "requires_confirmation": True,
                    "non_canonical_report_source": True,
                },
            )
        )
    return proposals


def _synthesize_delta(
    claims: list[ThesisClaim],
    verifications: list[ClaimVerification],
) -> str:
    contradicted = [v for v in verifications if v.status == "contradicted"]
    stale = [v for v in verifications if v.status == "stale"]
    supported = [v for v in verifications if v.status == "supported"]

    if not verifications:
        return "No claims were available for comparison."

    parts = []
    if contradicted:
        parts.append(
            f"The report contains {len(contradicted)} claim(s) contradicted by independent evidence, "
            f"primarily regarding: {', '.join(v.claim_id for v in contradicted[:3])}."
        )
    if stale:
        parts.append(
            f"There are {len(stale)} stale claim(s) that appear anchored to older data context."
        )

    support_pct = (len(supported) / len(verifications)) * 100
    if support_pct > 75:
        parts.append("Overall, the thesis is strongly supported by current backend evidence.")
    elif support_pct > 40:
        parts.append("The thesis is partially supported, but with notable gaps or assumptions.")
    else:
        parts.append("The thesis has significant verification gaps or contradictions against current evidence.")

    return " ".join(parts)


class ThesisAuditService:
    def __init__(
        self,
        *,
        orchestrator: QueryOrchestrator | None = None,
        llm_fn: Callable[..., Any] | None = None,
        use_llm: bool = True,
    ) -> None:
        self._orchestrator = orchestrator or QueryOrchestrator()
        self._llm_fn = llm_fn
        self._use_llm = use_llm

    def _orchestrate_evidence(
        self,
        *,
        ticker: str,
        claims: list[ThesisClaim] | None = None,
        focus: str | None = None,
        analysis_mode: str = "thesis_audit",
    ) -> Any:
        return self._orchestrator.orchestrate_query_with_context(
            _build_evidence_query(ticker=ticker, claims=claims, focus=focus),
            context={
                "prior_ticker": ticker,
                "request_standard": "company_analysis",
                "analysis_mode": analysis_mode,
            },
        )

    def coverage(self, ticker: str) -> ThesisAuditCoverageReport:
        normalized_ticker = _normalize_ticker(ticker)
        orchestrated = self._orchestrate_evidence(
            ticker=normalized_ticker,
            analysis_mode="thesis_audit_coverage",
        )
        evidence_spans = _flatten_evidence(orchestrated.evidence)
        evidence_summary = _build_evidence_summary(orchestrated, evidence_spans)
        proposal_gate = evidence_summary["proposal_gate"]
        return ThesisAuditCoverageReport(
            ticker=normalized_ticker,
            generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            evidence_summary=evidence_summary,
            guardrails={
                "memory_read_only": True,
                "user_thesis_memory_proposals_allowed": bool(proposal_gate.get("allowed")),
                "user_thesis_memory_proposal_gate": proposal_gate.get("reason"),
                "company_memory_written": False,
                "market_memory_written": False,
                "user_thesis_memory_auto_saved": False,
                "qdrant_written": False,
            },
        )

    def audit(self, report: ResearchReportInput) -> ThesisAuditReport:
        ticker = _normalize_ticker(report.ticker)
        report_text = _clean_text(report.report_text, limit=_MAX_REPORT_CHARS)
        if len(report_text) < 80:
            raise ValueError("report_text must contain at least 80 characters")
        normalized_report = ResearchReportInput(
            ticker=ticker,
            report_text=report_text,
            filename=report.filename,
            report_id=report.report_id,
            focus=report.focus,
        )
        spans = _extract_report_spans(report_text)
        audit_id = hashlib.sha256(f"{ticker}|{report_text}".encode("utf-8")).hexdigest()[:16]
        raw_payload = (
            _call_extractor(normalized_report, spans, self._llm_fn)
            if self._use_llm
            else None
        )
        if raw_payload is not None and not isinstance(raw_payload, dict):
            raw_payload = None

        claims = _normalize_claims(raw_payload, spans, report_text)
        thesis_summary = _clean_text(
            raw_payload.get("thesis_summary") if isinstance(raw_payload, dict) else "",
            limit=900,
        )
        if not thesis_summary:
            thesis_summary = _fallback_summary(report_text, [claim.text for claim in claims])
        assumptions = _normalize_assumptions(raw_payload, claims, spans)

        orchestrated = self._orchestrate_evidence(
            ticker=ticker,
            claims=claims,
            focus=report.focus,
        )
        evidence_spans = _flatten_evidence(orchestrated.evidence)
        evidence_summary = _build_evidence_summary(orchestrated, evidence_spans)
        verifications = _verify_claims(claims, evidence_spans)
        findings = _contrarian_findings(claims, verifications)
        strongest = sorted(
            [finding for finding in findings if finding.status in {"contradicted", "partially_supported"}],
            key=lambda finding: 0 if finding.status == "contradicted" else 1,
        )[:5]

        return ThesisAuditReport(
            audit_id=audit_id,
            ticker=ticker,
            generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            report_source={
                "filename": report.filename,
                "report_id": report.report_id or f"uploaded_report:{audit_id}",
                "source_role": "non_canonical_thesis_source",
                "span_count": len(spans),
                "text_chars": len(report_text),
            },
            thesis_summary=thesis_summary,
            claims=claims,
            hidden_assumptions=assumptions,
            verification_matrix=verifications,
            contrarian_findings=findings,
            strongest_disconfirming_evidence=strongest,
            report_to_reality_delta=_synthesize_delta(claims, verifications),
            change_my_mind_triggers=_change_my_mind_triggers(claims, verifications),
            next_diligence_questions=_diligence_questions(claims, verifications, assumptions),
            user_thesis_memory_proposals=_memory_proposals(
                audit_id=audit_id,
                ticker=ticker,
                thesis_summary=thesis_summary,
                claims=claims,
                verifications=verifications,
                evidence_summary=evidence_summary,
            ),
            evidence_summary=evidence_summary,
            guardrails={
                "uploaded_report_is_canonical_truth": False,
                "numeric_truth_source": "canonical_financial_truth_only",
                "company_memory_written": False,
                "market_memory_written": False,
                "user_thesis_memory_auto_saved": False,
                "user_thesis_memory_proposals_allowed": bool(
                    evidence_summary["proposal_gate"].get("allowed")
                ),
                "user_thesis_memory_proposal_gate": evidence_summary["proposal_gate"].get("reason"),
                "qdrant_written": False,
            },
        )
