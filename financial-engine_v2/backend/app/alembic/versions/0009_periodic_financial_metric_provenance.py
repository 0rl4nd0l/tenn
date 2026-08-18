"""Add per-metric provenance to ASX periodic financial rows."""

from alembic import op
import sqlalchemy as sa

revision = "0009_metric_provenance"
down_revision = "0008_asx_structured_created_at"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "asx_periodic_financials",
        sa.Column("metric_provenance", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("asx_periodic_financials", "metric_provenance")
