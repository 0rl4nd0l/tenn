from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import cockpit_api
from app.routes.cockpit_api import _suppress_unverified_data_missing_claims
from app.services.chat_evidence_guard import apply_visible_evidence_gap_labels
from app.services.chat_readiness import build_chat_readiness_status


CAPABILITY_IDS = {
    "financial_fact",
    "filing_document_summary",
    "local_news_rag",
    "portfolio_holdings_context",
    "memory_context",
    "strategy_action_preview",
    "model_route_runtime",
}


class FakeSqlProbe:
    def __init__(self, counts: dict[tuple[str, str | None], dict[str, object]]) -> None:
        self.counts = counts
        self.calls: list[tuple[str, str | None, str]] = []

    def count_rows(
        self,
        table: str,
        *,
        ticker: str | None = None,
        ticker_column: str = "ticker",
    ) -> dict[str, object]:
        self.calls.append((table, ticker, ticker_column))
        return dict(
            self.counts.get(
                (table, ticker),
                self.counts.get((table, None), {"available": False, "count": 0, "error": "missing"}),
            )
        )


def _settings(**overrides: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "database_url": "sqlite:////tmp/missing-fe-local.db",
        "data_root": "/tmp/missing-tenn-data",
        "docs_root": "/tmp/missing-tenn-docs",
        "enable_embeddings": False,
        "enable_qdrant": False,
        "enable_extraction": False,
        "enable_session_memory": True,
        "qdrant_url": "http://127.0.0.1:6333",
        "qdrant_collection": "asx_docs",
        "llamacpp_url": "http://127.0.0.1:8001",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_chat_readiness_reports_capability_blockers_without_promoting_health() -> None:
    readiness = build_chat_readiness_status(
        ticker="BHP",
        settings_obj=_settings(),
        sql_probe=FakeSqlProbe({}),
        http_probe=lambda url, path: (False, 0.0, "connection refused"),
        state_db_path="/tmp/missing-cockpit-state.db",
        memory_root="/tmp/missing-research-memory",
    )

    assert readiness["schema_version"] == 1
    assert readiness["ticker"] == "BHP"
    assert readiness["answer_ready"] is False
    assert readiness["normal_analysis_allowed"] is False
    assert set(readiness["capabilities"]) == CAPABILITY_IDS
    assert readiness["capabilities"]["financial_fact"]["status"] == "DATA_MISSING"
    assert readiness["capabilities"]["filing_document_summary"]["status"] == "DATA_MISSING"
    assert readiness["capabilities"]["local_news_rag"]["status"] == "DATA_MISSING"
    assert "ENABLE_QDRANT=false" in readiness["capabilities"]["local_news_rag"]["blockers"]
    assert readiness["capabilities"]["model_route_runtime"]["status"] == "DEGRADED"
    assert "financial_fact" in readiness["summary"]["primary_blockers"]
    assert readiness["reporting_contract"]["forbidden_actions_performed"] == []


def test_chat_readiness_allows_normal_analysis_only_when_core_substrates_are_ready(tmp_path) -> None:
    memory_root = tmp_path / "research_memory"
    memory_root.mkdir()
    state_db = tmp_path / "state.db"

    import sqlite3

    with sqlite3.connect(state_db) as conn:
        conn.execute("CREATE TABLE holdings_items (ticker TEXT, status TEXT)")
        conn.execute("INSERT INTO holdings_items (ticker, status) VALUES ('BHP', 'active')")
    with sqlite3.connect(memory_root / "company_memory.sqlite") as conn:
        conn.execute("CREATE TABLE memory_entries (company_id TEXT, status TEXT)")
        conn.execute("INSERT INTO memory_entries (company_id, status) VALUES ('BHP', 'active')")

    readiness = build_chat_readiness_status(
        ticker="BHP",
        settings_obj=_settings(enable_embeddings=True, enable_qdrant=True),
        sql_probe=FakeSqlProbe(
            {
                ("asx_periodic_financials", "BHP"): {"available": True, "count": 2, "error": None},
                ("documents", "BHP"): {"available": True, "count": 3, "error": None},
            }
        ),
        http_probe=lambda url, path: (True, 12.5, None),
        state_db_path=str(state_db),
        memory_root=str(memory_root),
    )

    assert readiness["answer_ready"] is True
    assert readiness["normal_analysis_allowed"] is True
    assert readiness["capabilities"]["financial_fact"]["ready"] is True
    assert readiness["capabilities"]["local_news_rag"]["ready"] is True
    assert readiness["capabilities"]["memory_context"]["answer_scope"] == "context_only"
    assert readiness["capabilities"]["memory_context"]["ready"] is True


def test_readiness_route_exposes_read_only_capability_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "schema_version": 1,
            "ticker": kwargs.get("ticker"),
            "answer_ready": False,
            "normal_analysis_allowed": False,
            "capabilities": {
                "financial_fact": {"status": "DATA_MISSING", "ready": False, "blockers": ["missing"]},
                "filing_document_summary": {"status": "DATA_MISSING", "ready": False, "blockers": ["missing"]},
                "local_news_rag": {"status": "DATA_MISSING", "ready": False, "blockers": ["disabled"]},
                "portfolio_holdings_context": {"status": "DATA_MISSING", "ready": False, "blockers": ["missing"]},
                "memory_context": {"status": "DATA_MISSING", "ready": False, "blockers": ["missing"]},
                "strategy_action_preview": {"status": "READY", "ready": True, "blockers": []},
                "model_route_runtime": {"status": "DEGRADED", "ready": False, "blockers": ["down"]},
            },
            "summary": {"primary_blockers": ["financial_fact"]},
            "reporting_contract": {"forbidden_actions_performed": []},
        }

    monkeypatch.setattr(cockpit_api, "build_chat_readiness_status", fake_build)

    app = FastAPI()
    app.include_router(cockpit_api.router, prefix="/api/cockpit")
    response = TestClient(app).get("/api/cockpit/chat/readiness?ticker=bhp")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "BHP"
    assert payload["capabilities"]["financial_fact"]["status"] == "DATA_MISSING"
    assert captured["ticker"] == "BHP"
    assert "http_probe" in captured


def test_data_missing_numeric_claims_are_suppressed_without_claim_verified_sources() -> None:
    text = (
        "DATA_MISSING / evidence gaps:\n"
        "- missing_required_evidence: required evidence is absent.\n\n"
        "Answer below is context-only.\n"
        "BHP reported revenue of $27,902 million for FY25."
    )
    metadata = {
        "claim_verified_source_count": 0,
        "source_coverage_status": "financial_truth",
        "evidence_labels": ["financial_truth", "financial_truth_numeric"],
        "missing_categories_after_recovery": ["stale_evidence"],
        "sufficient_for_analysis": True,
    }

    sanitized, updated_metadata = _suppress_unverified_data_missing_claims(text, metadata)

    assert "BHP reported revenue" not in sanitized
    assert "unverified_numeric_claims_suppressed" in sanitized
    assert updated_metadata["unsafe_numeric_claims_suppressed"] is True
    assert updated_metadata["sufficient_for_analysis"] is False
    assert updated_metadata["source_coverage_status"] == "missing_required_evidence"
    assert "unverified_numeric_claims" in updated_metadata["missing_categories_after_recovery"]


def test_gap_labeled_numeric_claims_are_suppressed_after_visible_gap_prefix() -> None:
    metadata = {
        "claim_verified_source_count": 0,
        "source_coverage_status": "context_only",
        "evidence_labels": ["missing_required_evidence", "financial_truth", "financial_truth_numeric"],
        "sufficient_for_analysis": True,
    }
    labeled = apply_visible_evidence_gap_labels(
        "BHP reported revenue of $27,902 million for the half-year ended December 31, 2025.",
        metadata,
    )

    sanitized, updated_metadata = _suppress_unverified_data_missing_claims(labeled, metadata)

    assert labeled.startswith("DATA_MISSING / evidence gaps:")
    assert "BHP reported revenue" not in sanitized
    assert "unverified_numeric_claims_suppressed" in sanitized
    assert updated_metadata["unsafe_numeric_claims_suppressed"] is True
