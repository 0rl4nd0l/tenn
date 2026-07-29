import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class FinancialObservation(Base):
    __tablename__ = "financial_observations"
    __table_args__ = (
        CheckConstraint(
            "metric IN ('revenue', 'ebit', 'np_attributable', 'operating_cf', "
            "'investing_cf', 'financing_cf', 'capex', 'cash_end', 'net_debt', "
            "'shares_outstanding')",
            name="ck_financial_observation_metric",
        ),
        CheckConstraint(
            "period_basis IN ('Q', 'H', 'A', 'period_only', 'year_to_date')",
            name="ck_financial_observation_period_basis",
        ),
        CheckConstraint(
            "accounting_basis = 'statutory'",
            name="ck_financial_observation_accounting_basis",
        ),
        CheckConstraint(
            "(metric = 'shares_outstanding' AND currency = 'shares') OR "
            "(metric <> 'shares_outstanding' AND currency IN ('AUD', 'CAD', "
            "'CNY', 'EUR', 'GBP', 'HKD', 'IDR', 'JPY', 'NZD', 'SGD', 'USD'))",
            name="ck_financial_observation_currency",
        ),
        CheckConstraint("scale = 'units'", name="ck_financial_observation_scale"),
        CheckConstraint(
            "trust_state = 'accepted'",
            name="ck_financial_observation_trust_state",
        ),
        UniqueConstraint(
            "source_document_id",
            "extractor_version",
            "ticker",
            "metric",
            "period_end",
            "period_basis",
            "accounting_basis",
            "currency",
            "scale",
            name="uq_financial_observation_source_context",
        ),
    )

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    accounting_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    scale: Mapped[str] = mapped_column(String(16), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    trust_state: Mapped[str] = mapped_column(String(16), nullable=False)


class FinancialObservationSupersession(Base):
    """Immutable explicit evidence that one observation replaces another."""

    __tablename__ = "financial_observation_supersessions"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('amendment', 'restatement')",
            name="ck_financial_observation_supersession_type",
        ),
        CheckConstraint(
            "superseding_observation_id <> superseded_observation_id",
            name="ck_financial_observation_supersession_distinct",
        ),
        UniqueConstraint(
            "superseded_observation_id",
            name="uq_financial_observation_superseded_once",
        ),
        Index(
            "ix_financial_observation_supersessions_superseding",
            "superseding_observation_id",
        ),
    )

    supersession_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    superseding_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_observations.observation_id"),
        nullable=False,
    )
    superseded_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_observations.observation_id"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)


class FinancialObservationReview(Base):
    """Unresolved observation candidate retained with source evidence."""

    __tablename__ = "financial_observation_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_kind IN ('conflicting', 'ambiguous', 'abstained', "
            "'quarantined')",
            name="ck_financial_observation_review_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_financial_observation_review_status",
        ),
        CheckConstraint(
            "decision IS NULL OR decision IN ('approve', 'reject')",
            name="ck_financial_observation_review_decision",
        ),
        CheckConstraint(
            "(status = 'pending' AND decision IS NULL "
            "AND decision_actor IS NULL AND decided_at IS NULL "
            "AND decision_reason_codes IS NULL) OR "
            "(((status = 'approved' AND decision = 'approve') OR "
            "(status = 'rejected' AND decision = 'reject')) "
            "AND decision_actor IS NOT NULL "
            "AND btrim(decision_actor) <> '' AND decided_at IS NOT NULL "
            "AND decision_reason_codes IS NOT NULL "
            "AND jsonb_typeof(decision_reason_codes) = 'array' "
            "AND jsonb_array_length(decision_reason_codes) > 0 "
            "AND NOT jsonb_path_exists("
            "decision_reason_codes, "
            "'$[*] ? (@.type() != \"string\" || "
            "@ like_regex \"^\\\\s*$\")')))",
            name="ck_financial_observation_review_decision_audit",
        ),
        UniqueConstraint(
            "source_document_id",
            "extraction_run_id",
            "metric",
            "period_end",
            "period_basis",
            "review_kind",
            name="uq_financial_observation_review_candidate",
        ),
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    scale: Mapped[str] = mapped_column(String(16), nullable=False)
    review_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False)
    source_evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision_actor: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decision_reason_codes: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinancialResultDisclosure(Base):
    """Immutable non-statutory result kept outside canonical observations."""

    __tablename__ = "financial_result_disclosures"
    __table_args__ = (
        CheckConstraint(
            "metric IN ('revenue', 'ebit', 'np_attributable', 'operating_cf', "
            "'investing_cf', 'financing_cf', 'capex', 'cash_end', 'net_debt', "
            "'shares_outstanding')",
            name="ck_financial_result_disclosure_metric",
        ),
        CheckConstraint(
            "accounting_basis IN ('adjusted', 'underlying', 'normalized', "
            "'pro_forma')",
            name="ck_financial_result_disclosure_accounting_basis",
        ),
        CheckConstraint(
            "period_basis IN ('Q', 'H', 'A', 'period_only', 'year_to_date')",
            name="ck_financial_result_disclosure_period_basis",
        ),
        CheckConstraint(
            "(metric = 'shares_outstanding' AND currency = 'shares') OR "
            "(metric <> 'shares_outstanding' AND currency IN ('AUD', 'CAD', "
            "'CNY', 'EUR', 'GBP', 'HKD', 'IDR', 'JPY', 'NZD', 'SGD', 'USD'))",
            name="ck_financial_result_disclosure_currency",
        ),
        CheckConstraint(
            "scale = 'units'",
            name="ck_financial_result_disclosure_scale",
        ),
        CheckConstraint(
            "consolidation_scope = 'consolidated'",
            name="ck_financial_result_disclosure_scope",
        ),
        CheckConstraint(
            "trust_state = 'disclosed'",
            name="ck_financial_result_disclosure_trust_state",
        ),
        UniqueConstraint(
            "source_document_id",
            "extractor_version",
            "ticker",
            "metric",
            "period_end",
            "period_basis",
            "accounting_basis",
            "source_label",
            "currency",
            "scale",
            name="uq_financial_result_disclosure_source_context",
        ),
    )

    disclosure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    accounting_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    consolidation_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    source_label: Mapped[str] = mapped_column(String(256), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    scale: Mapped[str] = mapped_column(String(16), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    reconciliation_evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    trust_state: Mapped[str] = mapped_column(String(16), nullable=False)
