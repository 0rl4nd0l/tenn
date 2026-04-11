"""Add created_at to asx_periodic_financials and asx_risk_notes.

Aligns structured ASX tables with extraction_runs timing semantics: monitoring
and ad-hoc SQL can filter on created_at for first-persist time while
updated_at continues to move on upserts.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0008_asx_structured_created_at"
down_revision = "0007_add_companies"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("asx_periodic_financials", "asx_risk_notes"):
        op.add_column(
            table,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.execute(
            text(f"UPDATE {table} SET created_at = updated_at WHERE created_at IS NULL")
        )
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        )


def downgrade():
    for table in ("asx_risk_notes", "asx_periodic_financials"):
        op.drop_column(table, "created_at")
