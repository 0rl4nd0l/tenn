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
    def __init__(
        self,
        evidence: dict,
        *,
        sufficient_for_analysis: bool = True,
        missing_categories_after_recovery: tuple[str, ...] = (),
    ) -> None:
        self.evidence = evidence
        self.sufficient_for_analysis = sufficient_for_analysis
        self.missing_categories_after_recovery = missing_categories_after_recovery
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
            sufficient_for_analysis=self.sufficient_for_analysis,
            missing_categories_after_recovery=self.missing_categories_after_recovery,
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
    assert "BHP revenue was 100 in FY2025." in orchestrator.calls[0]["query"]

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

    payload = audit.to_dict()
    verification = payload["verification_matrix"][0]
    assert verification["status"] == "contradicted"
    assert verification["contradicting_evidence_spans"][0]["source_layer"] == "financial_truth"
    assert payload["contrarian_findings"]
    assert payload["contrarian_findings"][0]["evidence_spans"]


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

    payload = audit.to_dict()
    statuses = {row["status"] for row in payload["verification_matrix"]}
    assert "DATA_MISSING" in statuses
    # Fix 1: contrarian findings are now emitted even when no independent evidence
    # spans are available; the finding text reflects the unverified status instead
    # of silently dropping the pack.
    assert len(payload["contrarian_findings"]) > 0
    finding_statuses = {f["status"] for f in payload["contrarian_findings"]}
    assert "DATA_MISSING" in finding_statuses or "assumption" in finding_statuses


def test_memory_proposals_are_payloads_not_applied_memory_writes() -> None:
    service = ThesisAuditService(
        orchestrator=FakeOrchestrator(
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


def test_evidence_limited_audit_blocks_memory_proposals() -> None:
    service = ThesisAuditService(
        orchestrator=FakeOrchestrator(
            {
                "financial_truth": {"status": "ok", "financials": []},
                "company_memory": {"items": []},
                "market_memory": {"items": [], "sector_items": [], "macro_items": []},
                "user_thesis_memory": {"items": []},
            },
            sufficient_for_analysis=False,
            missing_categories_after_recovery=("financials", "announcements_news_context"),
        ),
        use_llm=False,
    )

    audit = service.audit(
        ResearchReportInput(
            ticker="BHP",
            report_text=_report_text("BHP has a dominant logistics advantage in its core basin."),
        )
    )
    payload = audit.to_dict()

    assert payload["user_thesis_memory_proposals"] == []
    assert payload["evidence_summary"]["coverage_status"] == "no_backend_evidence"
    assert payload["evidence_summary"]["proposal_gate"]["allowed"] is False
    assert payload["guardrails"]["user_thesis_memory_proposals_allowed"] is False
    assert payload["guardrails"]["user_thesis_memory_proposal_gate"] == "no_backend_evidence"


def test_thesis_audit_coverage_reports_evidence_gate() -> None:
    service = ThesisAuditService(
        orchestrator=FakeOrchestrator(
            {
                "financial_truth": {"status": "ok", "financials": []},
                "company_memory": {"items": []},
                "market_memory": {"items": [], "sector_items": [], "macro_items": []},
                "user_thesis_memory": {"items": []},
            },
            sufficient_for_analysis=False,
            missing_categories_after_recovery=("financials",),
        ),
        use_llm=False,
    )

    payload = service.coverage("bhp").to_dict()

    assert payload["ticker"] == "BHP"
    assert payload["evidence_summary"]["coverage_status"] == "no_backend_evidence"
    assert payload["evidence_summary"]["proposal_gate"]["allowed"] is False
    assert payload["guardrails"]["memory_read_only"] is True
    assert payload["guardrails"]["qdrant_written"] is False


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

    monkeypatch.setattr(thesis_audit_route, "_get_service", lambda: FakeService())
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


def test_thesis_audit_route_reports_coverage(monkeypatch) -> None:
    class FakeService:
        def coverage(self, ticker: str):
            assert ticker == "BHP"
            return SimpleNamespace(
                to_dict=lambda: {
                    "ticker": "BHP",
                    "evidence_summary": {
                        "coverage_status": "ready",
                        "evidence_span_count": 2,
                    },
                    "guardrails": {"memory_read_only": True},
                }
            )

    monkeypatch.setattr(thesis_audit_route, "_get_service", lambda: FakeService())
    app = FastAPI()
    app.include_router(thesis_audit_route.router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/thesis-audit/coverage?ticker=BHP")

    assert response.status_code == 200
    assert response.json()["evidence_summary"]["coverage_status"] == "ready"


def test_context_financial_truth_provider_passes_scalar_defaults(monkeypatch) -> None:
    captured: dict[str, object] = {}
    closed = {"value": False}

    class FakeDb:
        def close(self) -> None:
            closed["value"] = True

    def fake_get_ticker_context(**kwargs):
        captured.update(kwargs)
        return {
            "errors": [],
            "financials": [],
            "docs": [],
            "latest_financial_snapshot": {},
            "announcement_context": [],
            "extraction_failures": [],
            "low_confidence_financials": [],
        }

    import app.api.context as context_api
    import app.core.db as db_module

    monkeypatch.setattr(context_api, "get_ticker_context", fake_get_ticker_context)
    monkeypatch.setattr(db_module, "SessionLocal", lambda: FakeDb())

    provider = thesis_audit_route._ContextFinancialTruthProvider()
    payload = provider.retrieve(
        query="verify claims",
        entities={"primary_ticker": "BHP"},
        intent="mixed",
    )

    assert payload["status"] == "ok"
    assert isinstance(captured["low_confidence_threshold"], float)
    assert captured["low_confidence_threshold"] == 0.4
    assert captured["low_confidence_limit"] == 12
    assert closed["value"] is True
