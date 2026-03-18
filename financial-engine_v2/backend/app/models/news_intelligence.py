from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    article_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    primary_ticker: Mapped[str] = mapped_column(String(16), index=True)
    tickers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    mapping_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")

    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ingested_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    headline_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    canonical_story_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_method_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    headline_vector_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    text_vector_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CanonicalStory(Base):
    __tablename__ = "canonical_stories"

    canonical_story_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    primary_article_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    related_articles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_seen_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    story_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sentiment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_method_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    story_vector_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class NewsNarrative(Base):
    __tablename__ = "news_narratives"

    narrative_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    story_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_seen: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    story_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sentiment_profile: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SourceCheckpoint(Base):
    __tablename__ = "source_checkpoints"

    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="incremental")
    last_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_ingested_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
