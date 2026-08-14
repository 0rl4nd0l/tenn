"""Add immutable financial observations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_financial_observations"
down_revision = "0009_metric_provenance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_observations",
        sa.Column(
            "observation_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "extraction_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("extractor_version", sa.String(64), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_basis", sa.String(16), nullable=False),
        sa.Column("accounting_basis", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("scale", sa.String(16), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("trust_state", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "metric = 'revenue'", name="ck_financial_observation_metric"
        ),
        sa.CheckConstraint(
            "period_basis IN ('Q', 'H', 'A')",
            name="ck_financial_observation_period_basis",
        ),
        sa.CheckConstraint(
            "accounting_basis = 'statutory'",
            name="ck_financial_observation_accounting_basis",
        ),
        sa.CheckConstraint(
            "currency IN ('AUD', 'CAD', 'CNY', 'EUR', 'GBP', 'HKD', 'IDR', "
            "'JPY', 'NZD', 'SGD', 'USD')",
            name="ck_financial_observation_currency",
        ),
        sa.CheckConstraint(
            "scale = 'units'", name="ck_financial_observation_scale"
        ),
        sa.CheckConstraint(
            "trust_state = 'accepted'",
            name="ck_financial_observation_trust_state",
        ),
        sa.UniqueConstraint(
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
    op.create_index(
        "ix_financial_observations_source_document_id",
        "financial_observations",
        ["source_document_id"],
    )
    op.create_index(
        "ix_financial_observations_extraction_run_id",
        "financial_observations",
        ["extraction_run_id"],
    )
    op.create_index(
        "ix_financial_observations_ticker",
        "financial_observations",
        ["ticker"],
    )


def downgrade():
    op.drop_index(
        "ix_financial_observations_ticker",
        table_name="financial_observations",
    )
    op.drop_index(
        "ix_financial_observations_extraction_run_id",
        table_name="financial_observations",
    )
    op.drop_index(
        "ix_financial_observations_source_document_id",
        table_name="financial_observations",
    )
    op.drop_table("financial_observations")
