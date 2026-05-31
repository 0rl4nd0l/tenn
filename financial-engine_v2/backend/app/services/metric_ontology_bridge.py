"""Eval-only ontology projection for exhaustive real-gold datapoints.

Pure function. Maps a raw exhaustive datapoint (one row from the exhaustive
real-gold artifact) to a canonical metric family with explicit unit-type
awareness and confidence grading. The projection is *advisory* — it is a
precondition for the future exhaustive matcher, and is intentionally kept
separate from canonical extraction and release-gate scoring.

Contract (from docs/ops/extraction-truth/phase-04-exhaustive-matcher-contract.md §2.D):

    project(datapoint) -> OntologyProjection:
        canonical_family:   str | None       # canonical metric family, if any
        unit_type:          UnitType         # re-derived, never trusts input blindly
        mapping_confidence: MappingConfidence
        mapping_basis:      str              # machine-readable reason category
        auto_collapse_safe: bool             # safe for a matcher to treat as canonical
        normalized_label:   str              # whitespace/punct-normalized row_label
        notes:              tuple[str, ...]  # optional advisory flags

Key invariants enforced here (see tests for verification):
    - Raw-value percentages are never silently treated as scaled currency.
    - Share-count rows are never silently treated as currency.
    - Non-canonical per-share rows (EPS/DPS) stay supplemental-only.
    - "Underlying" / "Statutory" / "Adjusted" qualifiers block auto-collapse.
    - Period-qualified labels (e.g., "net debt at the beginning of the period")
      keep the family but drop auto_collapse_safe so the matcher must pick
      an explicit period instance.
    - A family match is REJECTED when the derived unit_type contradicts the
      family's expected unit_type (e.g., "Net debt" with a percentage value).
    - Supplemental families (ebitda, total_assets, ...) never auto-collapse,
      because the extractor does not target them.

The bridge does not write to disk, does not touch DB, and is not imported
by canonical extraction or scoring paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class UnitType(str, Enum):
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    PER_SHARE = "per_share"
    COUNT = "count"
    RATIO = "ratio"
    UNKNOWN = "unknown"


class MappingConfidence(str, Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    SUPPLEMENTAL = "supplemental"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class OntologyProjection:
    canonical_family: str | None
    unit_type: UnitType
    mapping_confidence: MappingConfidence
    mapping_basis: str
    auto_collapse_safe: bool
    normalized_label: str
    notes: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Family tables
# ---------------------------------------------------------------------------

# Fields the extractor directly targets. A strong match on these is the only
# configuration that can become auto_collapse_safe.
EXTRACTOR_TARGET_FAMILIES: frozenset[str] = frozenset(
    {
        "revenue",
        "ebit",
        "np_attributable",
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "capex",
        "cash_end",
        "net_debt",
        "shares_outstanding",
    }
)

# Known canonical families outside the extractor target set. Matches here
# surface as `supplemental` — legitimate canonical semantics, but outside the
# current extractor's remit so the matcher must not count them as FPs.
SUPPLEMENTAL_FAMILIES: frozenset[str] = frozenset(
    {
        "ebitda",
        "depreciation_and_amortisation",
        "free_cash_flow",
        "interest_expense",
        "net_income",
        "total_assets",
        "total_equity",
        "total_liabilities",
    }
)

_ALL_FAMILIES: frozenset[str] = EXTRACTOR_TARGET_FAMILIES | SUPPLEMENTAL_FAMILIES


# Core phrases per family. The normalizer is permissive, so canonical phrases
# are stored in their natural english form and normalized before comparison.
_FAMILY_CORE_PHRASES: dict[str, tuple[str, ...]] = {
    "revenue": (
        "revenue",
        "total revenue",
        "sales revenue",
        "sales",
        "turnover",
    ),
    "ebit": (
        "ebit",
        "operating profit",
    ),
    "ebitda": ("ebitda",),
    "np_attributable": (
        "profit attributable to members",
        "profit attributable to owners",
        "profit attributable to shareholders",
        "profit attributable to equity holders",
        "net profit attributable to members",
        "net profit attributable to shareholders",
    ),
    "operating_cf": (
        "net cash from operating activities",
        "net cash generated from operating activities",
        "cash flow from operating activities",
        "net cash from operations",
        "cash from operating activities",
        "net cash inflow from operating activities",
        "operating cash flow",
        "cash flows from operating activities",
        "cash flows from operating activities subtotal",
        "net cash from used in operating activities",
    ),
    "investing_cf": (
        "net cash used in investing activities",
        "net cash from investing activities",
        "cash flow from investing activities",
        "net cash outflow from investing activities",
        "investing cash flow",
        "cash flows from investing activities",
        "net cash from used in investing activities",
    ),
    "financing_cf": (
        "net cash used in financing activities",
        "net cash from financing activities",
        "cash flow from financing activities",
        "net cash outflow from financing activities",
        "financing cash flow",
        "cash flows from financing activities",
        "net cash from used in financing activities",
    ),
    "capex": (
        "capex",
        "capital expenditure",
        "purchase of property plant and equipment",
        "payments for property plant and equipment",
        "additions to property plant and equipment",
    ),
    "cash_end": (
        "cash and cash equivalents at end of period",
        "cash and cash equivalents at end of financial year",
        "cash and cash equivalents at end of the period",
        "cash and cash equivalents at the end of the period",
        "cash and cash equivalents at end of half year",
        "cash and cash equivalents at end of the year",
        "cash and cash equivalents at end of quarter",
    ),
    "net_debt": ("net debt",),
    "shares_outstanding": (
        "ordinary shares issued and fully paid",
        "ordinary shares on issue",
        "number of ordinary shares on issue",
        "ordinary shares issued",
        "shares on issue",
    ),
    "depreciation_and_amortisation": (
        "depreciation and amortisation",
        "depreciation and amortization",
        "d and a",
    ),
    "free_cash_flow": (
        "free cash flow",
        "fcf",
    ),
    "interest_expense": (
        "interest expense",
        "interest paid",
        "interest cost",
    ),
    "net_income": (
        "net income",
        "profit after tax",
        "pat",
    ),
    "total_assets": ("total assets",),
    "total_equity": (
        "total equity",
        "shareholders equity",
    ),
    "total_liabilities": ("total liabilities",),
}


# Expected unit_type per family. Used to reject family matches whose
# derived unit_type contradicts the family's canonical unit.
_FAMILY_EXPECTED_UNIT: dict[str, UnitType] = {
    "revenue": UnitType.CURRENCY,
    "ebit": UnitType.CURRENCY,
    "ebitda": UnitType.CURRENCY,
    "np_attributable": UnitType.CURRENCY,
    "operating_cf": UnitType.CURRENCY,
    "investing_cf": UnitType.CURRENCY,
    "financing_cf": UnitType.CURRENCY,
    "capex": UnitType.CURRENCY,
    "cash_end": UnitType.CURRENCY,
    "net_debt": UnitType.CURRENCY,
    "shares_outstanding": UnitType.COUNT,
    "depreciation_and_amortisation": UnitType.CURRENCY,
    "free_cash_flow": UnitType.CURRENCY,
    "interest_expense": UnitType.CURRENCY,
    "net_income": UnitType.CURRENCY,
    "total_assets": UnitType.CURRENCY,
    "total_equity": UnitType.CURRENCY,
    "total_liabilities": UnitType.CURRENCY,
}


# Collapse blockers: qualifiers that change accounting semantics. Their
# presence forces confidence to MEDIUM and disables auto_collapse_safe.
_COLLAPSE_BLOCKERS = re.compile(
    r"\b(underlying|statutory|adjusted|normalised|normalized|"
    r"continuing|discontinued|pro[- ]?forma|segment|excluding|"
    r"including|from continuing operations)\b",
    re.IGNORECASE,
)


# Period disambiguation suffixes (e.g., "net debt at the beginning of the period").
# These keep the family but disable auto_collapse_safe.
_PERIOD_SUFFIX = re.compile(
    r"\b(at (the )?(beginning|end) of (the )?(period|financial year|year|half[- ]?year))\b",
    re.IGNORECASE,
)


# Unit-type detection patterns
_PERCENT_STRING_RE = re.compile(r"%\s*$")
_BASIS_POINTS_RE = re.compile(r"\b(bps|basis\s*points?)\b", re.IGNORECASE)

# Per-share pattern: "per ordinary share", "per share", "EPS", "DPS", plus
# scale hints like "cents" combined with share-context.
_PER_SHARE_LABEL_RE = re.compile(
    r"\b(per (ordinary )?share|per security|earnings per share|"
    r"dividend per share|eps|dps)\b",
    re.IGNORECASE,
)

# Share-count pattern: unambiguous references to share counts / holdings.
_SHARES_COUNT_RE = re.compile(
    r"\b(ordinary shares (issued|on issue)|"
    r"number of (ordinary )?shares|"
    r"shares on issue|"
    r"shares issued and fully paid|"
    r"total shares)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_label(text: Any) -> str:
    """Lowercase, collapse whitespace, strip punctuation except alphanumerics and spaces."""
    s = str(text or "").strip().lower()
    if not s:
        return ""
    # preserve alphanumerics and spaces; drop everything else
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _leading_section(context_text: Any) -> str:
    """Extract the leading section of a ' | '-separated context breadcrumb."""
    ctx = str(context_text or "")
    if " | " not in ctx:
        return _normalize_label(ctx)
    head = ctx.split(" | ", 1)[0]
    return _normalize_label(head)


# ---------------------------------------------------------------------------
# Unit type detection
# ---------------------------------------------------------------------------


def _derive_unit_type(
    *,
    row_label: str,
    context_text: str,
    raw_value: str,
    raw_scale: str | None,
    unit_type_src: str | None,
) -> tuple[UnitType, str]:
    """Return (UnitType, basis-tag). Raw-value hints win over generator hints."""

    rv = str(raw_value or "").strip()

    # 1. Hard signals from raw_value
    if _PERCENT_STRING_RE.search(rv):
        return UnitType.PERCENTAGE, "raw_value_percent_suffix"
    if _BASIS_POINTS_RE.search(rv):
        return UnitType.PERCENTAGE, "raw_value_bps"

    # Normalized label/context — punctuation (including em/en-dashes) collapsed
    # to spaces so regex word-boundary matches work on real-world labels like
    # "Ordinary shares – issued and fully paid".
    label_norm = _normalize_label(row_label)
    ctx_norm = _normalize_label(context_text)
    combined_norm = f"{label_norm} {ctx_norm}".strip()

    # 2. Share-count patterns (ordered before per-share: share-count labels
    #    like "Number of ordinary shares on issue" would also weakly match
    #    per-share; share-count check is more specific).
    if _SHARES_COUNT_RE.search(combined_norm):
        return UnitType.COUNT, "label_shares_count_pattern"

    # 3. Per-share patterns
    if _PER_SHARE_LABEL_RE.search(combined_norm):
        return UnitType.PER_SHARE, "label_per_share_pattern"

    # 4. Scale hint: "cents" only makes sense for per-share metrics in this
    #    corpus. Guard behind a share-related context to avoid misfiring.
    scale_l = str(raw_scale or "").lower().strip()
    if scale_l == "cents" and "share" in combined_norm:
        return UnitType.PER_SHARE, "scale_cents_with_share_context"

    # 5. Incoming generator hint (as fallback, never overriding raw_value)
    src_l = str(unit_type_src or "").lower().strip()
    if src_l in {"percent_or_ratio", "percent", "percentage"}:
        # Disambiguate percent vs ratio via labels (e.g. "gearing ratio").
        # Single-letter `x` excluded to avoid spurious matches in running text.
        if re.search(r"\b(ratio|gearing|times)\b", combined_norm):
            return UnitType.RATIO, "src_percent_or_ratio_with_ratio_label"
        return UnitType.PERCENTAGE, "src_percent_or_ratio"
    if src_l == "per_share":
        return UnitType.PER_SHARE, "src_per_share"
    if src_l in {"shares", "volume"}:
        return UnitType.COUNT, "src_shares_or_volume"
    if src_l == "currency":
        return UnitType.CURRENCY, "src_currency"
    if src_l == "plain_number":
        return UnitType.UNKNOWN, "src_plain_number"

    return UnitType.UNKNOWN, "no_signal"


# ---------------------------------------------------------------------------
# Family detection
# ---------------------------------------------------------------------------


def _match_family_exact(normalized: str) -> str | None:
    for family, phrases in _FAMILY_CORE_PHRASES.items():
        for phrase in phrases:
            if normalized == _normalize_label(phrase):
                return family
    return None


def _match_family_contains(normalized: str) -> tuple[str | None, str | None]:
    """Substring-match a family core phrase; returns (family, matched_phrase)."""
    best: tuple[str, str] | None = None
    for family, phrases in _FAMILY_CORE_PHRASES.items():
        for phrase in phrases:
            norm_phrase = _normalize_label(phrase)
            if norm_phrase and norm_phrase in normalized:
                # prefer longer phrases (more specific)
                if best is None or len(norm_phrase) > len(best[1]):
                    best = (family, norm_phrase)
    if best is None:
        return None, None
    return best


def _match_quarterly_fragment(
    *,
    normalized_label: str,
    normalized_context: str,
) -> tuple[str | None, str | None]:
    """Recognize split 5B labels that rely on local context.

    Keep this narrow and eval-only: it only covers fragment rows that clearly
    point to operating / investing / financing totals or end-cash totals in
    ASX Appendix 5B-style cash flow statements.
    """

    fragment_map = (
        (
            "operating_cf",
            (
                "activities",
                "activities item 1 9 above",
                "item 1 9 above",
            ),
            (
                "net cash from used in operating",
                "net cash from operating activities",
            ),
        ),
        (
            "investing_cf",
            (
                "activities",
                "item 2 6 above",
            ),
            (
                "net cash from used in investing",
                "net cash from investing activities",
            ),
        ),
        (
            "financing_cf",
            (
                "activities",
                "item 3 10 above",
            ),
            (
                "net cash from used in financing",
                "net cash from financing activities",
            ),
        ),
        (
            "cash_end",
            (
                "period",
                "period should equal item 4 6 above",
                "quarter should equal item 4 6 above",
            ),
            (
                "cash and cash equivalents at end of",
            ),
        ),
    )

    for family, label_fragments, context_fragments in fragment_map:
        if normalized_label not in label_fragments:
            continue
        if any(fragment in normalized_context for fragment in context_fragments):
            return family, "quarterly_fragment_context"
    return None, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def project(datapoint: Mapping[str, Any]) -> OntologyProjection:
    """Pure function — project one exhaustive datapoint onto the ontology."""

    row_label = datapoint.get("row_label")
    context_text = datapoint.get("context_text")
    raw_value = datapoint.get("raw_value")
    # Accept both `*_src` (canonical upstream schema) and bare `unit_type` /
    # `raw_scale` aliases (used by some test helpers); *_src wins when present.
    raw_scale = datapoint.get("raw_scale_src", datapoint.get("raw_scale"))
    unit_type_src = datapoint.get("unit_type_src", datapoint.get("unit_type"))

    normalized = _normalize_label(row_label)
    normalized_context = _normalize_label(context_text)

    unit_type, unit_basis = _derive_unit_type(
        row_label=str(row_label or ""),
        context_text=str(context_text or ""),
        raw_value=str(raw_value or ""),
        raw_scale=raw_scale,
        unit_type_src=unit_type_src,
    )

    notes: list[str] = []

    # --- Family matching ---------------------------------------------------
    family: str | None = None
    basis: str = "no_match"
    confidence = MappingConfidence.UNSUPPORTED

    if normalized:
        fam_exact = _match_family_exact(normalized)
        if fam_exact is not None:
            family = fam_exact
            basis = "exact_alias"
            confidence = (
                MappingConfidence.SUPPLEMENTAL
                if family in SUPPLEMENTAL_FAMILIES
                else MappingConfidence.STRONG
            )
        else:
            fam_contains, matched_phrase = _match_family_contains(normalized)
            if fam_contains is not None:
                family = fam_contains
                basis = f"contains_phrase:{matched_phrase}"
                confidence = (
                    MappingConfidence.SUPPLEMENTAL
                    if family in SUPPLEMENTAL_FAMILIES
                    else MappingConfidence.MEDIUM
                )
            elif normalized_context:
                fam_fragment, basis_fragment = _match_quarterly_fragment(
                    normalized_label=normalized,
                    normalized_context=normalized_context,
                )
                if fam_fragment is not None:
                    family = fam_fragment
                    basis = basis_fragment or "quarterly_fragment_context"
                    confidence = MappingConfidence.MEDIUM

    if (
        family is None
        and normalized
        and normalized_context
        and _COLLAPSE_BLOCKERS.search(str(row_label or "")) is None
    ):
        # Last-resort: weak context-only lookup on the leading section of the
        # context breadcrumb. Kept after the narrow 5B fragment matcher so
        # obvious quarterly total rows resolve as medium fragment matches
        # instead of generic weak context borrowing.
        section = _leading_section(context_text)
        if section:
            fam_ctx = _match_family_exact(section)
            if fam_ctx is None:
                fam_ctx, _ = _match_family_contains(section)
            if fam_ctx is not None:
                family = fam_ctx
                basis = "context_leading_section"
                confidence = MappingConfidence.WEAK

    if (
        family is None
        and unit_type == UnitType.PER_SHARE
        and normalized
        and confidence == MappingConfidence.UNSUPPORTED
    ):
        # EPS/DPS rows are legitimate financial datapoints but outside the
        # extractor's canonical target families, so keep them supplemental-only.
        basis = "per_share_noncanonical"
        confidence = MappingConfidence.SUPPLEMENTAL

    # --- Qualifier / period modifiers --------------------------------------
    label_has_blocker = bool(_COLLAPSE_BLOCKERS.search(str(row_label or "")))
    label_has_period_suffix = bool(_PERIOD_SUFFIX.search(str(row_label or "")))

    if family is not None:
        if label_has_blocker:
            notes.append("collapse_blocker_qualifier")
            if confidence == MappingConfidence.STRONG:
                confidence = MappingConfidence.MEDIUM
        if label_has_period_suffix and family != "cash_end":
            # cash_end is DEFINED by "at end of period" — the suffix is canonical,
            # not disambiguating. For all other families (e.g. net_debt, cash_start)
            # the suffix is a secondary modifier so demote to MEDIUM.
            notes.append("period_disambiguation_suffix")
            if confidence == MappingConfidence.STRONG:
                confidence = MappingConfidence.MEDIUM

    # --- Unit/family coherence check ---------------------------------------
    # If a family was found but the derived unit_type contradicts the family's
    # expected unit_type, REJECT the family and downgrade to unsupported.
    # This is what catches "Net debt" rows whose value is actually a percentage
    # change column, and share-count rows mislabelled as currency.
    if family is not None:
        expected_unit = _FAMILY_EXPECTED_UNIT.get(family)
        if (
            expected_unit is not None
            and unit_type not in (UnitType.UNKNOWN,)
            and unit_type != expected_unit
        ):
            # For shares_outstanding, tolerate UNKNOWN → COUNT promotion upstream
            # (already handled in _derive_unit_type), so this branch only fires
            # on real contradictions.
            notes.append(
                f"unit_type_conflict:{unit_type.value}_vs_expected_{expected_unit.value}"
            )
            family = None
            basis = "rejected_unit_type_conflict"
            confidence = MappingConfidence.UNSUPPORTED

    # --- auto_collapse_safe gate -------------------------------------------
    # Period suffix is canonical for cash_end (the phrase *is* the definition),
    # so do not treat it as a collapse blocker for that family.
    period_suffix_blocks_collapse = label_has_period_suffix and family != "cash_end"
    auto_collapse_safe = (
        confidence == MappingConfidence.STRONG
        and family in EXTRACTOR_TARGET_FAMILIES
        and not label_has_blocker
        and not period_suffix_blocks_collapse
    )

    return OntologyProjection(
        canonical_family=family,
        unit_type=unit_type,
        mapping_confidence=confidence,
        mapping_basis=f"{basis}|unit:{unit_basis}",
        auto_collapse_safe=auto_collapse_safe,
        normalized_label=normalized,
        notes=tuple(notes),
    )


__all__ = [
    "EXTRACTOR_TARGET_FAMILIES",
    "MappingConfidence",
    "OntologyProjection",
    "SUPPLEMENTAL_FAMILIES",
    "UnitType",
    "project",
]
