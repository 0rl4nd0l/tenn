"""Add companies master table for listed company metadata.

Introduces a canonical company master table to replace the distributed company
identity that was previously scattered across documents.ticker / documents.exchange
with no name, listing status, sector, ISIN, or FIGI anywhere in the schema.

Note: No FK constraint from documents.ticker → companies.ticker is added here.
A backfill of the companies table must be completed before that constraint can be
applied safely. The FK migration will follow as a separate step.
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_add_companies"
down_revision = "0006_add_announcement_type"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "companies",
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=False, server_default="ASX"),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("isin", sa.String(12), nullable=True),
        sa.Column("figi", sa.String(12), nullable=True),
        sa.Column("listing_date", sa.Date(), nullable=True),
        sa.Column("delisting_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("sector", sa.String(64), nullable=True),
        sa.Column("industry", sa.String(64), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("ticker", "exchange", name="pk_companies"),
        sa.UniqueConstraint("isin", name="uq_companies_isin"),
        sa.UniqueConstraint("figi", name="uq_companies_figi"),
    )
    op.create_index(
        "ix_companies_exchange_status",
        "companies",
        ["exchange", "status"],
    )


def downgrade():
    op.drop_index("ix_companies_exchange_status", table_name="companies")
    op.drop_table("companies")
