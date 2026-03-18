from alembic import op
import sqlalchemy as sa


revision = "0003_news_intelligence"
down_revision = "0002_documents_source_url_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_articles",
        sa.Column("article_id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("primary_ticker", sa.String(16), nullable=False),
        sa.Column("tickers", sa.JSON(), nullable=False),
        sa.Column("mapping_confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default=sa.text("'en'")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("headline_hash", sa.String(64), nullable=False),
        sa.Column("canonical_story_id", sa.String(64), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_label", sa.String(16), nullable=True),
        sa.Column("sentiment_confidence", sa.Float(), nullable=True),
        sa.Column("sentiment_method_version", sa.String(32), nullable=True),
        sa.Column("headline_vector_id", sa.String(36), nullable=True),
        sa.Column("text_vector_id", sa.String(36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_news_articles_document_id", "news_articles", ["document_id"])
    op.create_index("ix_news_articles_primary_ticker", "news_articles", ["primary_ticker"])
    op.create_index("ix_news_articles_source", "news_articles", ["source"])
    op.create_index("ix_news_articles_canonical_url", "news_articles", ["canonical_url"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])
    op.create_index("ix_news_articles_content_hash", "news_articles", ["content_hash"])
    op.create_index("ix_news_articles_headline_hash", "news_articles", ["headline_hash"])
    op.create_index("ix_news_articles_canonical_story_id", "news_articles", ["canonical_story_id"])
    op.create_index("ix_news_articles_headline_vector_id", "news_articles", ["headline_vector_id"])
    op.create_index("ix_news_articles_text_vector_id", "news_articles", ["text_vector_id"])

    op.create_table(
        "canonical_stories",
        sa.Column("canonical_story_id", sa.String(64), primary_key=True),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("primary_article_id", sa.String(64), nullable=False),
        sa.Column("related_articles", sa.JSON(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("story_text", sa.Text(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_label", sa.String(16), nullable=True),
        sa.Column("sentiment_confidence", sa.Float(), nullable=True),
        sa.Column("sentiment_method_version", sa.String(32), nullable=True),
        sa.Column("story_vector_id", sa.String(36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_canonical_stories_ticker", "canonical_stories", ["ticker"])
    op.create_index("ix_canonical_stories_primary_article_id", "canonical_stories", ["primary_article_id"])
    op.create_index("ix_canonical_stories_first_published_at", "canonical_stories", ["first_published_at"])
    op.create_index("ix_canonical_stories_last_seen_at", "canonical_stories", ["last_seen_at"])
    op.create_index("ix_canonical_stories_story_vector_id", "canonical_stories", ["story_vector_id"])

    op.create_table(
        "news_narratives",
        sa.Column("narrative_id", sa.String(64), primary_key=True),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("story_ids", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("story_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sentiment_profile", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_news_narratives_ticker", "news_narratives", ["ticker"])
    op.create_index("ix_news_narratives_start_date", "news_narratives", ["start_date"])
    op.create_index("ix_news_narratives_last_seen", "news_narratives", ["last_seen"])

    op.create_table(
        "source_checkpoints",
        sa.Column("source", sa.String(64), primary_key=True),
        sa.Column("run_mode", sa.String(16), nullable=False, server_default=sa.text("'incremental'")),
        sa.Column("last_cursor", sa.Text(), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_article_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade():
    op.drop_table("source_checkpoints")
    op.drop_index("ix_news_narratives_last_seen", table_name="news_narratives")
    op.drop_index("ix_news_narratives_start_date", table_name="news_narratives")
    op.drop_index("ix_news_narratives_ticker", table_name="news_narratives")
    op.drop_table("news_narratives")

    op.drop_index("ix_canonical_stories_story_vector_id", table_name="canonical_stories")
    op.drop_index("ix_canonical_stories_last_seen_at", table_name="canonical_stories")
    op.drop_index("ix_canonical_stories_first_published_at", table_name="canonical_stories")
    op.drop_index("ix_canonical_stories_primary_article_id", table_name="canonical_stories")
    op.drop_index("ix_canonical_stories_ticker", table_name="canonical_stories")
    op.drop_table("canonical_stories")

    op.drop_index("ix_news_articles_text_vector_id", table_name="news_articles")
    op.drop_index("ix_news_articles_headline_vector_id", table_name="news_articles")
    op.drop_index("ix_news_articles_canonical_story_id", table_name="news_articles")
    op.drop_index("ix_news_articles_headline_hash", table_name="news_articles")
    op.drop_index("ix_news_articles_content_hash", table_name="news_articles")
    op.drop_index("ix_news_articles_published_at", table_name="news_articles")
    op.drop_index("ix_news_articles_canonical_url", table_name="news_articles")
    op.drop_index("ix_news_articles_source", table_name="news_articles")
    op.drop_index("ix_news_articles_primary_ticker", table_name="news_articles")
    op.drop_index("ix_news_articles_document_id", table_name="news_articles")
    op.drop_table("news_articles")
