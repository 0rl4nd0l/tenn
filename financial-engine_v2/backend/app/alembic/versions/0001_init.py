from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0001_init'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('documents',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(16), nullable=False),
        sa.Column('exchange', sa.String(16), nullable=False),
        sa.Column('doc_class', sa.String(16), nullable=False),
        sa.Column('doc_subtype', sa.String(32), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('period_end', sa.DateTime(timezone=True)),
        sa.Column('title', sa.Text()),
        sa.Column('source_url', sa.Text()),
        sa.Column('pdf_path', sa.Text(), nullable=False),
        sa.Column('pdf_sha256', sa.String(64), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_documents_ticker','documents',['ticker'])
    op.create_index('ix_documents_pdf_sha256','documents',['pdf_sha256'])

    op.create_table('extraction_runs',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('extractor_version', sa.String(64)),
        sa.Column('model_name', sa.String(64)),
        sa.Column('prompt_hash', sa.String(64)),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('confidence_overall', sa.Float()),
        sa.Column('error', sa.Text()),
        sa.Column('structured_json', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_extraction_runs_document_id','extraction_runs',['document_id'])

    op.create_table('asx_periodic_financials',
        sa.Column('ticker', sa.String(16), primary_key=True),
        sa.Column('period_end', sa.Date(), primary_key=True),
        sa.Column('period_type', sa.String(1), primary_key=True),
        sa.Column('revenue', sa.Numeric()),
        sa.Column('ebit', sa.Numeric()),
        sa.Column('np_attributable', sa.Numeric()),
        sa.Column('operating_cf', sa.Numeric()),
        sa.Column('investing_cf', sa.Numeric()),
        sa.Column('financing_cf', sa.Numeric()),
        sa.Column('capex', sa.Numeric()),
        sa.Column('cash_end', sa.Numeric()),
        sa.Column('net_debt', sa.Numeric()),
        sa.Column('shares_outstanding', sa.Numeric()),
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('confidence_metrics', sa.Float()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table('asx_risk_notes',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('risk_summary', sa.Text()),
        sa.Column('risk_bullets', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('guidance_summary', sa.Text()),
        sa.Column('material_changes', sa.Text()),
        sa.Column('confidence_narrative', sa.Float()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

def downgrade():
    op.drop_table('asx_risk_notes')
    op.drop_table('asx_periodic_financials')
    op.drop_index('ix_extraction_runs_document_id', table_name='extraction_runs')
    op.drop_table('extraction_runs')
    op.drop_index('ix_documents_pdf_sha256', table_name='documents')
    op.drop_index('ix_documents_ticker', table_name='documents')
    op.drop_table('documents')
