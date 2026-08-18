"""Expand immutable observation period bases for quarter and YTD views."""

from alembic import op

revision = "0012_observation_period_basis"
down_revision = "0011_statutory_metrics"
branch_labels = None
depends_on = None

_PERIOD_BASES = ("Q", "H", "A", "period_only", "year_to_date")


def _quoted(values):
    return ", ".join(f"'{value}'" for value in values)


def upgrade():
    op.drop_constraint(
        "ck_financial_observation_period_basis",
        "financial_observations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_financial_observation_period_basis",
        "financial_observations",
        f"period_basis IN ({_quoted(_PERIOD_BASES)})",
    )


def downgrade():
    raise RuntimeError(
        "0012_observation_period_basis is forward-only; immutable "
        "observations cannot be narrowed safely"
    )
