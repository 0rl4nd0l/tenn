import uuid
from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base
class Document(Base):
    __tablename__ = "documents"
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    exchange: Mapped[str] = mapped_column(String(16), index=True)
    doc_class: Mapped[str] = mapped_column(String(16), index=True)
    doc_subtype: Mapped[str] = mapped_column(String(32), index=True)
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    period_end: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True, index=True)
    pdf_path: Mapped[str] = mapped_column(Text)
    pdf_sha256: Mapped[str] = mapped_column(String(64), index=True)
    announcement_type: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    ingested_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
