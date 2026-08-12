"""Expand immutable observations to the ten canonical statutory metrics."""

from alembic import op
import sqlalchemy as sa


revision = "0011_statutory_metrics"
down_revision = "0010_financial_observations"
branch_labels = None
depends_on = None

_METRICS = (
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
)
_CURRENCIES = (
    "AUD",
    "CAD",
    "CNY",
    "EUR",
    "GBP",
    "HKD",
    "IDR",
    "JPY",
    "NZD",
    "SGD",
    "USD",
)


def _quoted(values):
    return ", ".join(f"'{value}'" for value in values)


def upgrade():
    op.drop_constraint(
        "ck_financial_observation_metric",
        "financial_observations",
        type_="check",
    )
    op.drop_constraint(
        "ck_financial_observation_currency",
        "financial_observations",
        type_="check",
    )
    op.alter_column(
        "financial_observations",
        "currency",
        existing_type=sa.String(length=3),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_financial_observation_metric",
        "financial_observations",
        f"metric IN ({_quoted(_METRICS)})",
    )
    op.create_check_constraint(
        "ck_financial_observation_currency",
        "financial_observations",
        (
            "(metric = 'shares_outstanding' AND currency = 'shares') OR "
            "(metric <> 'shares_outstanding' "
            f"AND currency IN ({_quoted(_CURRENCIES)}))"
        ),
    )


def downgrade():
    raise RuntimeError(
        "0011_statutory_metrics is forward-only; immutable observations "
        "cannot be narrowed safely"
    )
