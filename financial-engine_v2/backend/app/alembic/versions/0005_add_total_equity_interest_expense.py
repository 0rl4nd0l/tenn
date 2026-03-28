"""Add total_equity and interest_expense to asx_periodic_financials.

total_equity: total shareholders' equity from the balance sheet. Required for
  ROIC calculation (invested capital = total_equity + net_debt).

interest_expense: interest/finance costs from the income statement. Required for
  NOPAT derivation and interest coverage ratio.

Both columns are nullable to allow the migration to run against existing rows that
have no source data to backfill from.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_equity_interest"
down_revision = "0004_financials_period_currency"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "asx_periodic_financials",
        sa.Column("total_equity", sa.Numeric(), nullable=True),
    )
    op.add_column(
        "asx_periodic_financials",
        sa.Column("interest_expense", sa.Numeric(), nullable=True),
    )


def downgrade():
    op.drop_column("asx_periodic_financials", "interest_expense")
    op.drop_column("asx_periodic_financials", "total_equity")
