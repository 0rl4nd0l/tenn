from __future__ import annotations

import base64
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes import thesis_audit as thesis_audit_route
from app.services.thesis_audit import (
    CLAIM_STATUSES,
    CLAIM_TYPES,
    ResearchReportInput,
    ThesisAuditService,
)


class FakeOrchestrator:
    def __init__(self, evidence: dict) -> None:
        self.evidence = evidence
        self.calls: list[dict] = []

    def orchestrate_query_with_context(self, query: str, *, context: dict | None = None):
        self.calls.append({"query": query, "context": context or {}})
        return SimpleNamespace(
            evidence=self.evidence,
            source_plan=(
                "financial_truth",
                "company_memory",
                "market_memory",
                "user_thesis_memory",
            ),
            sufficient_for_analysis=True,
            missing_categories_after_recovery=(),
        )


def _report_text(claim: str) -> str:
    return (
        f"{claim} The report thesis is that this evidence supports a better quality "
        "business profile and a more resilient medium-term setup. It also argues "
        "that management execution and market demand are the main risks to the view."
    )


def test_thesis_audit_keeps_report_noncanonical_and_uses_financial_truth_for_numbers() -> None:
    orchestrator = FakeOrchestrator(
        {
            "financial_truth": {
                "status": "ok",
                "financials": [
                    {
                        "ticker": "BHP",
                        "period_type": "annual",
                        "period_end": "2025-06-30",
                        "revenue": "100",
                        "source_document_id": "doc-1",
                    }
                ],
            },
            "company_memory": {"items": []},
            "market_memory": {"items": [], "sector_items": [], "macro_items": []},
            "user_thesis_memory": {"items": []},
        }
    )
    service = ThesisAuditService(orchestrator=orchestrator, use_llm=False)

    audit = service.audit(
        ResearchReportInput(
            ticker="bhp",
            report_text=_report_text("BHP revenue was 100 in FY2025."),
            filename="research-note.txt",
        )
    )
    payload = audit.to_dict()

    assert payload["ticker"] == "BHP"
    assert payload["report_source"]["source_role"] == "non_canonical_thesis_source"
    assert payload["guardrails"]["uploaded_report_is_canonical_truth"] is False
    assert payload["guardrails"]["company_memory_written"] is False
    assert payload["guardrails"]["market_memory_written"] is False
    assert payload["guardrails"]["user_thesis_memory_auto_saved"] is False
    assert payload["guardrails"]["numeric_truth_source"] == "canonical_financial_truth_only"
    assert orchestrator.calls[0]["context"]["analysis_mode"] == "thesis_audit"

    claim = payload["claims"][0]
    assert claim["claim_type"] in CLAIM_TYPES
    assert claim["report_span"]["text"]

    verification = payload["verification_matrix"][0]
    assert verification["status"] in CLAIM_STATUSES
    assert verification["status"] == "supported"
    assert verification["independent_evidence_spans"][0]["source_layer"] == "financial_truth"


def test_numeric_report_claim_is_contradicted_by_canonical_financial_truth() -> None:
    orchestrator = FakeOrchestrator(
        {
            "financial_truth": {
                "status": "ok",
                "financials": [
                    {
                        "ticker": "BHP",
                        "period_type": "annual",
                        "period_end": "2025-06-30",
                        "revenue": "100",
                    }
                ],
            },
            "company_memory": {"items": []},
            "market_memory": {"items": [], "sector_items": [], "macro_items": []},
            "user_thesis_memory": {"items": []},
        }
    )
    service = ThesisAuditService(orchestrator=orchestrator, use_llm=False)

    audit = service.audit(
        ResearchReportInput(
            ticker="BHP",
            report_text=_report_text("BHP revenue was 999 in FY2025."),
        )
    )

    verification = audit.to_dict()["verification_matrix"][0]
    assert verification["status"] == "contradicted"
    assert verification["contradicting_evidence_spans"][0]["source_layer"] == "financial_truth"


def test_missing_independent_evidence_preserves_data_missing() -> None:
    service = ThesisAuditService(
        orchestrator=FakeOrchestrator(
            {
                "financial_truth": {"status": "ok", "financials": []},
                "company_memory": {"items": []},
                "market_memory": {"items": [], "sector_items": [], "macro_items": []},
                "user_thesis_memory": {"items": []},
            }
        ),
        use_llm=False,
    )

    audit = service.audit(
        ResearchReportInput(
            ticker="BHP",
            report_text=_report_text("BHP has a dominant logistics advantage in its core basin."),
        )
    )

    statuses = {row["status"] for row in audit.to_dict()["verification_matrix"]}
    assert "DATA_MISSING" in statuses


def test_memory_proposals_are_payloads_not_applied_memory_writes() -> None:
    service = ThesisAuditService(
        orchestrator=FakeOrchestrator(
            {
                "financial_truth": {"status": "ok", "financials": []},
                "company_memory": {"items": []},
                "market_memory": {"items": [], "sector_items": [], "macro_items": []},
                "user_thesis_memory": {"items": []},
            }
        ),
        use_llm=False,
    )

    audit = service.audit(
        ResearchReportInput(
            ticker="BHP",
            report_text=_report_text("BHP has a dominant logistics advantage in its core basin."),
        )
    )
    proposals = audit.to_dict()["user_thesis_memory_proposals"]

    assert proposals
    assert proposals[0]["proposal_type"] == "create_thesis"
    assert proposals[0]["metadata"]["requires_confirmation"] is True
    assert proposals[0]["metadata"]["non_canonical_report_source"] is True


def test_thesis_audit_route_accepts_text_upload(monkeypatch) -> None:
    class FakeService:
        def audit(self, report: ResearchReportInput):
            assert report.ticker == "BHP"
            assert "BHP revenue" in report.report_text
            return SimpleNamespace(
                to_dict=lambda: {
                    "audit_id": "audit-1",
                    "ticker": "BHP",
                    "guardrails": {"user_thesis_memory_auto_saved": False},
                }
            )

    monkeypatch.setattr(thesis_audit_route, "_build_service", lambda: FakeService())
    app = FastAPI()
    app.include_router(thesis_audit_route.router, prefix="/api/cockpit")
    client = TestClient(app)
    content = base64.b64encode(_report_text("BHP revenue was 100 in FY2025.").encode()).decode()

    response = client.post(
        "/api/cockpit/thesis-audit",
        json={"ticker": "BHP", "filename": "note.txt", "content_base64": content},
    )

    assert response.status_code == 200
    assert response.json()["audit_id"] == "audit-1"
