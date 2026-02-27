from alembic import op


revision = "0002_documents_source_url_unique"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        # Partial unique index avoids NULL/empty rows while enforcing strict dedupe for real URLs.
        op.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_url_nonempty
            ON documents(source_url)
            WHERE source_url IS NOT NULL AND trim(source_url) <> ''
            """
        )
        return

    # Postgres and others.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_source_url_nonempty
        ON documents(source_url)
        WHERE source_url IS NOT NULL AND btrim(source_url) <> ''
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_documents_source_url_nonempty")
