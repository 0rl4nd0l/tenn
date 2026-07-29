"""Add immutable, evidence-backed financial observation supersessions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_observation_supersessions"
down_revision = "0013_result_disclosures"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_observation_supersessions",
        sa.Column(
            "supersession_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "superseding_observation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("financial_observations.observation_id"),
            nullable=False,
        ),
        sa.Column(
            "superseded_observation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("financial_observations.observation_id"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(16), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "relationship_type IN ('amendment', 'restatement')",
            name="ck_financial_observation_supersession_type",
        ),
        sa.CheckConstraint(
            "superseding_observation_id <> superseded_observation_id",
            name="ck_financial_observation_supersession_distinct",
        ),
        sa.UniqueConstraint(
            "superseded_observation_id",
            name="uq_financial_observation_superseded_once",
        ),
    )
    op.create_index(
        "ix_financial_observation_supersessions_superseding",
        "financial_observation_supersessions",
        ["superseding_observation_id"],
    )


def downgrade():
    raise RuntimeError(
        "0014_observation_supersessions is forward-only; immutable "
        "supersession evidence cannot be removed safely"
    )
