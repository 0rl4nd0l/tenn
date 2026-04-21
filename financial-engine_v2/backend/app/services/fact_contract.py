from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CanonicalFact:
    metric_key: str
    value: float
    unit: str
    scale: str
    basis: str  # e.g., "RC" (Replacement Cost), "HC" (Historical Cost), "Statutory"
    period_type: str
    period_end: str
    source_doc_id: str
    source_page: str
    source_span: str
    validation_status: str = "unvalidated"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "value": self.value,
            "unit": self.unit,
            "scale": self.scale,
            "basis": self.basis,
            "period_type": self.period_type,
            "period_end": self.period_end,
            "source_doc_id": self.source_doc_id,
            "source_page": self.source_page,
            "source_span": self.source_span,
            "validation_status": self.validation_status,
            "metadata": self.metadata,
        }


# Failure Taxonomy Codes
FAILURE_CODES = {
    "WRONG_NUMBER": "wrong_number",
    "UNSUPPORTED_NUMERIC_CLAIM": "unsupported_numeric_claim",
    "BASIS_MISMATCH": "basis_mismatch",
    "SCALE_MISMATCH": "scale_mismatch",
    "DATA_MISSING": "data_missing",
}
