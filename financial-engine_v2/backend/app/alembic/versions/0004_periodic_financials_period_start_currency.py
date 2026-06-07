"""Add period_start and currency to asx_periodic_financials.

period_start: allows unambiguous reconstruction of the reporting window (H1 vs H2
  that share the same period_end year), and enables duration-aware annualisation.

currency: ISO 4217 code (AUD, USD, GBP, etc.) reported by the filing. Required for
  cross-company comparison — BHP reports USD, most ASX companies report AUD.

Both columns are nullable to allow the migration to run against existing rows that
have no source data to backfill from.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_financials_period_currency"
down_revision = "0002_documents_source_url_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "asx_periodic_financials",
        sa.Column("period_start", sa.Date(), nullable=True),
    )
    op.add_column(
        "asx_periodic_financials",
        sa.Column("currency", sa.String(3), nullable=True),
    )


def downgrade():
    op.drop_column("asx_periodic_financials", "currency")
    op.drop_column("asx_periodic_financials", "period_start")
