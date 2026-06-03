"""split document download status from pdf hash

Revision ID: 0004_document_download_status
Revises: 0003_metric_provenance
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_document_download_status"
down_revision = "0003_metric_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("download_status", sa.String(32), nullable=False, server_default="pending"))
    op.add_column("documents", sa.Column("download_error_code", sa.String(128), nullable=True))
    op.add_column("documents", sa.Column("download_error_detail", sa.Text(), nullable=True))
    op.create_index("ix_documents_download_status", "documents", ["download_status"])

    bind = op.get_bind()
    dialect = bind.dialect.name
    trim_fn = "trim" if dialect == "sqlite" else "btrim"
    op.execute(
        f"""
        UPDATE documents
        SET download_status = CASE
                WHEN pdf_sha256 LIKE 'blocked_%' THEN 'blocked'
                WHEN pdf_sha256 IS NOT NULL AND {trim_fn}(pdf_sha256) <> '' THEN 'downloaded'
                ELSE 'pending'
            END,
            download_error_code = CASE
                WHEN pdf_sha256 LIKE 'blocked_%' THEN pdf_sha256
                ELSE NULL
            END,
            pdf_sha256 = CASE
                WHEN pdf_sha256 LIKE 'blocked_%' THEN ''
                ELSE pdf_sha256
            END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE documents
        SET pdf_sha256 = download_error_code
        WHERE download_status = 'blocked'
          AND COALESCE(pdf_sha256, '') = ''
          AND download_error_code IS NOT NULL
        """
    )
    op.drop_index("ix_documents_download_status", table_name="documents")
    op.drop_column("documents", "download_error_detail")
    op.drop_column("documents", "download_error_code")
    op.drop_column("documents", "download_status")
