from alembic import op
import sqlalchemy as sa


revision = "0003_openbb_staging_snapshots"
down_revision = "0002_documents_source_url_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "openbb_price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=True),
        sa.Column("symbol", sa.String(32), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("dataset_type", sa.String(32), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_openbb_price_snapshots_ticker", "openbb_price_snapshots", ["ticker"])
    op.create_index("ix_openbb_price_snapshots_request_hash", "openbb_price_snapshots", ["request_hash"])
    op.create_index("ix_openbb_price_snapshots_captured_at", "openbb_price_snapshots", ["captured_at"])
    op.create_index(
        "ix_openbb_price_snapshots_lookup",
        "openbb_price_snapshots",
        ["ticker", "dataset_type", "captured_at"],
    )

    op.create_table(
        "openbb_fundamental_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=True),
        sa.Column("symbol", sa.String(32), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("dataset_type", sa.String(64), nullable=False),
        sa.Column("statement_type", sa.String(16), nullable=True),
        sa.Column("period", sa.String(16), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_openbb_fundamental_snapshots_ticker", "openbb_fundamental_snapshots", ["ticker"])
    op.create_index("ix_openbb_fundamental_snapshots_request_hash", "openbb_fundamental_snapshots", ["request_hash"])
    op.create_index("ix_openbb_fundamental_snapshots_captured_at", "openbb_fundamental_snapshots", ["captured_at"])
    op.create_index(
        "ix_openbb_fundamental_snapshots_lookup",
        "openbb_fundamental_snapshots",
        ["ticker", "dataset_type", "captured_at"],
    )


def downgrade():
    op.drop_index("ix_openbb_fundamental_snapshots_lookup", table_name="openbb_fundamental_snapshots")
    op.drop_index("ix_openbb_fundamental_snapshots_captured_at", table_name="openbb_fundamental_snapshots")
    op.drop_index("ix_openbb_fundamental_snapshots_request_hash", table_name="openbb_fundamental_snapshots")
    op.drop_index("ix_openbb_fundamental_snapshots_ticker", table_name="openbb_fundamental_snapshots")
    op.drop_table("openbb_fundamental_snapshots")

    op.drop_index("ix_openbb_price_snapshots_lookup", table_name="openbb_price_snapshots")
    op.drop_index("ix_openbb_price_snapshots_captured_at", table_name="openbb_price_snapshots")
    op.drop_index("ix_openbb_price_snapshots_request_hash", table_name="openbb_price_snapshots")
    op.drop_index("ix_openbb_price_snapshots_ticker", table_name="openbb_price_snapshots")
    op.drop_table("openbb_price_snapshots")
