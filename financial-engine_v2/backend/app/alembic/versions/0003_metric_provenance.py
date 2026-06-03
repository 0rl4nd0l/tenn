"""add metric provenance to periodic financials

Revision ID: 0003_metric_provenance
Revises: 0002_documents_source_url_unique
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_metric_provenance"
down_revision = "0002_documents_source_url_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asx_periodic_financials", sa.Column("metric_provenance", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("asx_periodic_financials", "metric_provenance")
