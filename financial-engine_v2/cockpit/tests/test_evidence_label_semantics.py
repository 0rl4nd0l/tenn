from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cockpit.core.agent_loop import (  # noqa: E402
    _coverage_from_evidence_labels,
    _normalize_evidence_state_labels,
)
from shared.evidence_labels import EVIDENCE_STATE_LABELS  # noqa: E402


def test_agent_loop_state_labels_use_shared_taxonomy_subset() -> None:
    assert "degraded_runtime" in EVIDENCE_STATE_LABELS
    assert "claim_verified" not in EVIDENCE_STATE_LABELS

    labels = _normalize_evidence_state_labels(
        ["degraded_runtime", "claim_verified", "unknown_label"]
    )

    assert labels == {"degraded_runtime"}
    assert _coverage_from_evidence_labels({"context_only", "financial_truth"}) == (
        "financial_truth"
    )
