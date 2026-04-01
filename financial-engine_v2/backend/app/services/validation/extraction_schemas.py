"""
Extraction output validation schemas.
Defined here, NOT YET ACTIVATED in the live pipeline.
Schema is the intended contract — activation is a separate step.

These schemas mirror the payload structure produced by
multipass_extraction.run_multipass_extraction() after Pass 4 reconciliation
and flattening. The payload dict is the input to _upsert_financial_rows.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series


class ExtractionOutputSchema(pa.DataFrameModel):
    """Schema for a batch of extraction outputs (one row per document)."""

    ticker: Series[str] = pa.Field(nullable=False)
    document_id: Series[str] = pa.Field(nullable=False)
    extraction_status: Series[str] = pa.Field(
        nullable=False,
        isin=["ok", "ok_low_confidence", "failed"],
    )

    # Period metadata — required when status == "ok"
    period_end: Series[str] = pa.Field(nullable=True)
    period_type: Series[str] = pa.Field(nullable=True, isin=["A", "H", "Q"])
    period_start: Series[str] = pa.Field(nullable=True)
    scale: Series[str] = pa.Field(
        nullable=True,
        isin=["thousands", "millions", "billions", "units", "unknown"],
    )
    currency: Series[str] = pa.Field(nullable=True)
    scale_validation: Series[str] = pa.Field(nullable=True)

    # Confidence — float [0.0, 1.0]
    confidence_metrics: Series[float] = pa.Field(
        nullable=True, ge=0.0, le=1.0,
    )

    # 10 financial metric fields (all nullable — absent metrics are None)
    revenue: Optional[Series[float]] = pa.Field(nullable=True)
    ebit: Optional[Series[float]] = pa.Field(nullable=True)
    np_attributable: Optional[Series[float]] = pa.Field(nullable=True)
    operating_cf: Optional[Series[float]] = pa.Field(nullable=True)
    investing_cf: Optional[Series[float]] = pa.Field(nullable=True)
    financing_cf: Optional[Series[float]] = pa.Field(nullable=True)
    capex: Optional[Series[float]] = pa.Field(nullable=True)
    cash_end: Optional[Series[float]] = pa.Field(nullable=True)
    net_debt: Optional[Series[float]] = pa.Field(nullable=True)
    shares_outstanding: Optional[Series[float]] = pa.Field(nullable=True)

    # Narrative fields from Pass 3b (all nullable)
    risk_summary: Optional[Series[str]] = pa.Field(nullable=True)
    risk_bullets: Optional[Series[str]] = pa.Field(nullable=True)
    guidance_summary: Optional[Series[str]] = pa.Field(nullable=True)
    material_changes: Optional[Series[str]] = pa.Field(nullable=True)
    confidence_narrative: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0.0, le=1.0,
    )

    class Config:
        strict = "filter"
        coerce = False  # Never coerce — fail loudly on type mismatch
