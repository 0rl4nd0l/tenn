"""Add an immutable lane for explicitly labelled non-statutory results."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_result_disclosures"
down_revision = "0012_observation_period_basis"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_result_disclosures",
        sa.Column("disclosure_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extraction_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extractor_version", sa.String(64), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_basis", sa.String(16), nullable=False),
        sa.Column("accounting_basis", sa.String(32), nullable=False),
        sa.Column("consolidation_scope", sa.String(32), nullable=False),
        sa.Column("source_label", sa.String(256), nullable=False),
        sa.Column("currency", sa.String(16), nullable=False),
        sa.Column("scale", sa.String(16), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("reconciliation_evidence", sa.JSON(), nullable=False),
        sa.Column("trust_state", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "metric IN ('revenue', 'ebit', 'np_attributable', 'operating_cf', "
            "'investing_cf', 'financing_cf', 'capex', 'cash_end', 'net_debt', "
            "'shares_outstanding')",
            name="ck_financial_result_disclosure_metric",
        ),
        sa.CheckConstraint(
            "accounting_basis IN ('adjusted', 'underlying', 'normalized', "
            "'pro_forma')",
            name="ck_financial_result_disclosure_accounting_basis",
        ),
        sa.CheckConstraint(
            "period_basis IN ('Q', 'H', 'A', 'period_only', 'year_to_date')",
            name="ck_financial_result_disclosure_period_basis",
        ),
        sa.CheckConstraint(
            "(metric = 'shares_outstanding' AND currency = 'shares') OR "
            "(metric <> 'shares_outstanding' AND currency IN ('AUD', 'CAD', "
            "'CNY', 'EUR', 'GBP', 'HKD', 'IDR', 'JPY', 'NZD', 'SGD', 'USD'))",
            name="ck_financial_result_disclosure_currency",
        ),
        sa.CheckConstraint(
            "scale = 'units'",
            name="ck_financial_result_disclosure_scale",
        ),
        sa.CheckConstraint(
            "consolidation_scope = 'consolidated'",
            name="ck_financial_result_disclosure_scope",
        ),
        sa.CheckConstraint(
            "trust_state = 'disclosed'",
            name="ck_financial_result_disclosure_trust_state",
        ),
        sa.UniqueConstraint(
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
    for column in ("source_document_id", "extraction_run_id", "ticker"):
        op.create_index(
            f"ix_financial_result_disclosures_{column}",
            "financial_result_disclosures",
            [column],
        )


def downgrade():
    raise RuntimeError(
        "0013_result_disclosures is forward-only; immutable disclosures "
        "cannot be removed safely"
    )
