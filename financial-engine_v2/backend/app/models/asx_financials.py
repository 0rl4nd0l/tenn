import uuid
from sqlalchemy import String, Date, Numeric, Float, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base
class ASXPeriodicFinancial(Base):
    __tablename__ = "asx_periodic_financials"
    ticker: Mapped[str] = mapped_column(String(16), primary_key=True)
    period_end: Mapped[Date] = mapped_column(Date, primary_key=True)
    period_type: Mapped[str] = mapped_column(String(1), primary_key=True)  # Q|H|A
    revenue: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    ebit: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    np_attributable: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    operating_cf: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    investing_cf: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    financing_cf: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    capex: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    cash_end: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    net_debt: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    shares_outstanding: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    total_equity: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    interest_expense: Mapped[Numeric | None] = mapped_column(Numeric, nullable=True)
    period_start: Mapped[Date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    confidence_metrics: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
class ASXRiskNote(Base):
    __tablename__ = "asx_risk_notes"
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    risk_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_bullets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    guidance_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_narrative: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
