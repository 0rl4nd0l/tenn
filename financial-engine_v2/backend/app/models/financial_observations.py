import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
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
