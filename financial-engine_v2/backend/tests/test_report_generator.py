from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_MODULE_PATH = (
    Path(__file__).parents[1] / "app/services/analysis/report_generator.py"
)
_SPEC = importlib.util.spec_from_file_location("report_generator", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
report_generator = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(report_generator)


class _StubLlmClient:
    def chat(self, prompt: str, *, timeout: float) -> str:
        return "{}"


def test_financial_evidence_uses_accepted_observation_projection(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def capture_validation(
        report: dict[str, Any],
        *,
        evidence_bundle: dict[str, Any],
        min_citation_coverage: float,
    ) -> dict[str, Any]:
        captured["evidence_bundle"] = evidence_bundle
        return {"ok": True, "errors": []}

    monkeypatch.setattr(
        report_generator,
        "validate_analysis_report",
        capture_validation,
    )

    report_generator.generate({"ticker": "BHP"}, _StubLlmClient())

    financial_evidence = captured["evidence_bundle"]["evidence"][0]
    assert financial_evidence["source_id"] == (
        "BHP_accepted_financial_observation_projection"
    )
    assert financial_evidence["content"] == (
        "Financial data from accepted_financial_observation_projection."
    )
