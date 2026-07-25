"""Typed authority for Tenn's financial metric contract.

This module is declarative.  It owns metric names, ordering, persistence and
evaluation mappings, source requirements, and contract metadata, but performs
no extraction, normalization, derivation, evaluation, or persistence itself.
Evaluation aliases are intentionally not production source-matching rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StatementContext(str, Enum):
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW_STATEMENT = "cashflow_statement"
    NET_DEBT_NOTE = "net_debt_note"
    BALANCE_SHEET = "balance_sheet"
    SHARE_CAPITAL = "share_capital"
    HIGHLIGHTS = "highlights"


class MetricUnitKind(str, Enum):
    CURRENCY_ABSOLUTE = "currency_absolute"
    SHARE_COUNT_ABSOLUTE = "share_count_absolute"
    NOT_APPLICABLE = "not_applicable"


class AuthorizedDerivation(str, Enum):
    APPENDIX_5B_EXPLICIT_CAPEX_SUBITEM_SUM = (
        "appendix_5b_explicit_capex_subitem_sum"
    )


class ProvenanceRequirement(str, Enum):
    SOURCE_ROW_REF = "source_row_ref"
    SOURCE_ROW_REFS = "source_row_refs"
    NOT_CANONICAL = "not_canonical"


class MetricContractStatus(str, Enum):
    SUPPORTED = "supported"
    EXTRACTOR_SUPPORTED = "extractor_supported"
    EVALUATOR_SUPPORTED = "evaluator_supported"
    PERSISTED_ONLY = "persisted_only"
    GOLD_ONLY = "gold_only"
    PLANNED = "planned"
    INTERNAL_ONLY = "internal_only"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS_REQUIRES_POLICY = "ambiguous_requires_policy"


@dataclass(frozen=True)
class MetricContractFamily:
    """One financial metric family's complete declarative contract."""

    family: str
    canonical_field: str | None
    aliases: tuple[str, ...]
    planned: bool = False
    internal_only: bool = False
    ambiguous_requires_policy: bool = False
    notes: str = ""
    persistence_column: str | None = None
    statement_contexts: tuple[StatementContext, ...] = ()
    unit_kind: MetricUnitKind = MetricUnitKind.NOT_APPLICABLE
    direct_source_required: bool = False
    authorized_derivations: tuple[AuthorizedDerivation, ...] = ()
    provenance_requirement: ProvenanceRequirement = (
        ProvenanceRequirement.NOT_CANONICAL
    )
    declared_status: MetricContractStatus = MetricContractStatus.UNSUPPORTED
    evaluation_names: tuple[str, ...] = ()
    extractor_output_order: int | None = None
    persistence_order: int | None = None
    production_relevance_tier: str | None = None

REAL_GOLD_METRIC_ALIASES = {
    "operating_cash_flow": "operating_cf",
}

REVIEW_GOLD_METRIC_ALIASES = {
    "operating_cf": "operating_cash_flow",
    "operating_cash_flow": "operating_cf",
}

EVALUATION_ALIASES_ARE_PRODUCTION_MATCH_RULES = False

_SUPPORTED_CURRENCY = {
    "unit_kind": MetricUnitKind.CURRENCY_ABSOLUTE,
    "direct_source_required": True,
    "provenance_requirement": ProvenanceRequirement.SOURCE_ROW_REF,
    "declared_status": MetricContractStatus.SUPPORTED,
}


METRIC_CONTRACT_FAMILIES = (
    MetricContractFamily(
        family="revenue",
        canonical_field="revenue",
        aliases=("sales_revenue", "top_line_revenue"),
        notes="Top-line revenue family.",
        persistence_column="revenue",
        statement_contexts=(
            StatementContext.INCOME_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("revenue",),
        extractor_output_order=0,
        persistence_order=0,
        production_relevance_tier="core",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="operating_cash_flow",
        canonical_field="operating_cf",
        aliases=("operating_cf", "cash_flow_from_operations"),
        notes="Fixture/gold alias maps to the extractor field operating_cf.",
        persistence_column="operating_cf",
        statement_contexts=(
            StatementContext.CASH_FLOW_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("operating_cf", "operating_cash_flow"),
        extractor_output_order=3,
        persistence_order=3,
        production_relevance_tier="core",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="net_debt",
        canonical_field="net_debt",
        aliases=("net_borrowings", "net_cash"),
        notes="Canonical only when explicit net-debt evidence or approved derivation gates pass.",
        persistence_column="net_debt",
        statement_contexts=(
            StatementContext.NET_DEBT_NOTE,
            StatementContext.BALANCE_SHEET,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("net_debt",),
        extractor_output_order=8,
        persistence_order=8,
        production_relevance_tier="core",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="total_equity",
        canonical_field="total_equity",
        aliases=("shareholders_equity", "equity_attributable"),
        notes="Persisted field exists, but extractor/evaluator support is not approved.",
        persistence_column="total_equity",
        statement_contexts=(StatementContext.BALANCE_SHEET,),
        unit_kind=MetricUnitKind.CURRENCY_ABSOLUTE,
        direct_source_required=True,
        provenance_requirement=ProvenanceRequirement.SOURCE_ROW_REF,
        declared_status=MetricContractStatus.PERSISTED_ONLY,
        persistence_order=10,
    ),
    MetricContractFamily(
        family="interest_expense",
        canonical_field="interest_expense",
        aliases=("interest_cost", "interest_paid"),
        notes="Persisted field exists, but extractor/evaluator support is not approved.",
        persistence_column="interest_expense",
        statement_contexts=(StatementContext.INCOME_STATEMENT,),
        unit_kind=MetricUnitKind.CURRENCY_ABSOLUTE,
        direct_source_required=True,
        provenance_requirement=ProvenanceRequirement.SOURCE_ROW_REF,
        declared_status=MetricContractStatus.PERSISTED_ONLY,
        persistence_order=11,
    ),
    MetricContractFamily(
        family="finance_costs",
        canonical_field=None,
        aliases=("finance_cost", "finance_expense"),
        ambiguous_requires_policy=True,
        notes="Potential interest_expense alias, but finance costs can include non-interest items.",
        statement_contexts=(StatementContext.INCOME_STATEMENT,),
        declared_status=MetricContractStatus.AMBIGUOUS_REQUIRES_POLICY,
    ),
    MetricContractFamily(
        family="cash",
        canonical_field="cash_end",
        aliases=("cash_end", "cash_and_cash_equivalents", "closing_cash"),
        notes="Canonical family is period-end cash/cash equivalents.",
        persistence_column="cash_end",
        statement_contexts=(
            StatementContext.CASH_FLOW_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("cash_end",),
        extractor_output_order=7,
        persistence_order=7,
        production_relevance_tier="cash_flow",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="debt_borrowings",
        canonical_field="total_debt",
        aliases=("debt", "borrowings", "total_borrowings"),
        internal_only=True,
        notes="Internal balance-sheet capture used only for guarded net_debt derivation.",
        statement_contexts=(StatementContext.BALANCE_SHEET,),
        unit_kind=MetricUnitKind.CURRENCY_ABSOLUTE,
        direct_source_required=True,
        provenance_requirement=ProvenanceRequirement.SOURCE_ROW_REF,
        declared_status=MetricContractStatus.INTERNAL_ONLY,
    ),
    MetricContractFamily(
        family="capex",
        canonical_field="capex",
        aliases=("capital_expenditure", "payments_for_ppe"),
        notes="Supported with convention-specific source evidence requirements.",
        persistence_column="capex",
        statement_contexts=(
            StatementContext.CASH_FLOW_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        unit_kind=MetricUnitKind.CURRENCY_ABSOLUTE,
        direct_source_required=True,
        authorized_derivations=(
            AuthorizedDerivation.APPENDIX_5B_EXPLICIT_CAPEX_SUBITEM_SUM,
        ),
        provenance_requirement=ProvenanceRequirement.SOURCE_ROW_REFS,
        declared_status=MetricContractStatus.SUPPORTED,
        evaluation_names=("capex",),
        extractor_output_order=6,
        persistence_order=6,
        production_relevance_tier="cash_flow",
    ),
    MetricContractFamily(
        family="eps",
        canonical_field=None,
        aliases=("earnings_per_share", "basic_eps", "diluted_eps"),
        planned=True,
        notes="Broad metric catalogue candidate; not canonical extraction output.",
        declared_status=MetricContractStatus.PLANNED,
    ),
    MetricContractFamily(
        family="dividends",
        canonical_field=None,
        aliases=("dividend", "dividends_paid", "dividend_per_share"),
        planned=True,
        notes="Broad metric catalogue candidate; not canonical extraction output.",
        declared_status=MetricContractStatus.PLANNED,
    ),
    MetricContractFamily(
        family="np_attributable",
        canonical_field="np_attributable",
        aliases=("npat", "profit_attributable", "profit attributable"),
        notes="Profit attributable to ordinary/security holders family.",
        persistence_column="np_attributable",
        statement_contexts=(
            StatementContext.INCOME_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("np_attributable",),
        extractor_output_order=2,
        persistence_order=2,
        production_relevance_tier="core",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="ebit",
        canonical_field="ebit",
        aliases=("operating_profit", "profit_before_tax"),
        notes="Supported, but source label policy remains stricter than generic PBT.",
        persistence_column="ebit",
        statement_contexts=(
            StatementContext.INCOME_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("ebit",),
        extractor_output_order=1,
        persistence_order=1,
        production_relevance_tier="core",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="investing_cf",
        canonical_field="investing_cf",
        aliases=("investing_cash_flow",),
        notes="Extractor field for cash-flow statement support.",
        persistence_column="investing_cf",
        statement_contexts=(
            StatementContext.CASH_FLOW_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("investing_cf",),
        extractor_output_order=4,
        persistence_order=4,
        production_relevance_tier="cash_flow",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="financing_cf",
        canonical_field="financing_cf",
        aliases=("financing_cash_flow",),
        notes="Extractor field for cash-flow statement support.",
        persistence_column="financing_cf",
        statement_contexts=(
            StatementContext.CASH_FLOW_STATEMENT,
            StatementContext.HIGHLIGHTS,
        ),
        evaluation_names=("financing_cf",),
        extractor_output_order=5,
        persistence_order=5,
        production_relevance_tier="cash_flow",
        **_SUPPORTED_CURRENCY,
    ),
    MetricContractFamily(
        family="shares_outstanding",
        canonical_field="shares_outstanding",
        aliases=("shares_on_issue", "ordinary_shares_on_issue"),
        notes="Supported when the source reports period-end share count, not weighted-average EPS denominator.",
        persistence_column="shares_outstanding",
        statement_contexts=(
            StatementContext.BALANCE_SHEET,
            StatementContext.SHARE_CAPITAL,
            StatementContext.HIGHLIGHTS,
        ),
        unit_kind=MetricUnitKind.SHARE_COUNT_ABSOLUTE,
        direct_source_required=True,
        provenance_requirement=ProvenanceRequirement.SOURCE_ROW_REF,
        declared_status=MetricContractStatus.SUPPORTED,
        evaluation_names=("shares_outstanding",),
        extractor_output_order=9,
        persistence_order=9,
        production_relevance_tier="capital_structure",
    ),
    MetricContractFamily(
        family="total_assets",
        canonical_field=None,
        aliases=("assets",),
        notes="Unsupported in the current extraction/evaluation contract.",
        statement_contexts=(StatementContext.BALANCE_SHEET,),
        declared_status=MetricContractStatus.UNSUPPORTED,
    ),
)

METRIC_CONTRACT_BY_FAMILY = {
    definition.family: definition for definition in METRIC_CONTRACT_FAMILIES
}

METRIC_CONTRACT_BY_CANONICAL_FIELD = {
    definition.canonical_field: definition
    for definition in METRIC_CONTRACT_FAMILIES
    if definition.canonical_field is not None
}

CANONICAL_METRIC_FIELDS = tuple(
    definition.canonical_field
    for definition in sorted(
        (
            definition
            for definition in METRIC_CONTRACT_FAMILIES
            if definition.extractor_output_order is not None
        ),
        key=lambda definition: definition.extractor_output_order,
    )
)

PERSISTED_METRIC_COLUMNS = tuple(
    definition.persistence_column
    for definition in sorted(
        (
            definition
            for definition in METRIC_CONTRACT_FAMILIES
            if definition.persistence_order is not None
        ),
        key=lambda definition: definition.persistence_order,
    )
)

INTERNAL_METRIC_FIELDS = tuple(
    definition.canonical_field
    for definition in METRIC_CONTRACT_FAMILIES
    if definition.internal_only and definition.canonical_field is not None
)

METRIC_NAME_MAP = {
    evaluation_name: canonical_field
    for canonical_field in CANONICAL_METRIC_FIELDS
    for evaluation_name in METRIC_CONTRACT_BY_CANONICAL_FIELD[
        canonical_field
    ].evaluation_names
}

PRODUCTION_RELEVANCE_TIERS = {
    canonical_field: definition.production_relevance_tier
    for canonical_field in CANONICAL_METRIC_FIELDS
    if (
        definition := METRIC_CONTRACT_BY_CANONICAL_FIELD[canonical_field]
    ).production_relevance_tier
}
