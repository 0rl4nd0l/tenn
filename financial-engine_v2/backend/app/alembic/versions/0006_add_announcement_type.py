"""Add announcement_type to documents table.

Stores the 8-way classification from announcement_importance.py so that
downstream consumers (RAG filtering, analysis modules, cockpit search) can
filter by document type without re-classifying on each query.
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_announcement_type"
down_revision = "0005_add_equity_interest"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # Make the migration idempotent for Postgres – avoid failing if the column/index
        # were already created in a previous run or via manual changes.
        bind.execute(
            sa.text(
                "ALTER TABLE documents "
                "ADD COLUMN IF NOT EXISTS announcement_type VARCHAR(32)"
            )
        )
        bind.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_documents_announcement_type "
                "ON documents (announcement_type)"
            )
        )
    else:
        op.add_column(
            "documents",
            sa.Column("announcement_type", sa.String(32), nullable=True),
        )
        op.create_index(
            "ix_documents_announcement_type",
            "documents",
            ["announcement_type"],
        )


def downgrade():
    op.drop_index("ix_documents_announcement_type", table_name="documents")
    op.drop_column("documents", "announcement_type")
