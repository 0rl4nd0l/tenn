"""Add the evidence-backed financial observation review queue."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_observation_reviews"
down_revision = "0014_observation_supersessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_observation_reviews",
        sa.Column("review_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extraction_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extractor_version", sa.String(64), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("proposed_value", sa.Numeric(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_basis", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(16), nullable=False),
        sa.Column("scale", sa.String(16), nullable=False),
        sa.Column("review_kind", sa.String(16), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("source_evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decision", sa.String(16), nullable=True),
        sa.Column("decision_actor", sa.String(128), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "decision_reason_codes", postgresql.JSONB(), nullable=True
        ),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "review_kind IN ('conflicting', 'ambiguous', 'abstained', 'quarantined')",
            name="ck_financial_observation_review_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_financial_observation_review_status",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('approve', 'reject')",
            name="ck_financial_observation_review_decision",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND decision IS NULL "
            "AND decision_actor IS NULL AND decided_at IS NULL "
            "AND decision_reason_codes IS NULL) OR "
            "(((status = 'approved' AND decision = 'approve') OR "
            "(status = 'rejected' AND decision = 'reject')) "
            "AND decision_actor IS NOT NULL "
            "AND btrim(decision_actor) <> '' AND decided_at IS NOT NULL "
            "AND decision_reason_codes IS NOT NULL "
            "AND jsonb_typeof(decision_reason_codes) = 'array' "
            "AND jsonb_array_length(decision_reason_codes) > 0 "
            "AND NOT jsonb_path_exists("
            "decision_reason_codes, "
            "'$[*] ? (@.type() != \"string\" || "
            "@ like_regex \"^\\\\s*$\")')))",
            name="ck_financial_observation_review_decision_audit",
        ),
        sa.UniqueConstraint(
            "source_document_id",
            "extraction_run_id",
            "metric",
            "period_end",
            "period_basis",
            "review_kind",
            name="uq_financial_observation_review_candidate",
        ),
    )
    for column in ("source_document_id", "extraction_run_id", "ticker"):
        op.create_index(
            f"ix_financial_observation_reviews_{column}",
            "financial_observation_reviews",
            [column],
        )


def downgrade():
    raise RuntimeError(
        "0015_observation_reviews is forward-only; review evidence and decisions "
        "cannot be removed safely"
    )
