from pathlib import Path
from types import SimpleNamespace
import inspect
import importlib.util
import json
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import main as main_app
from app.services.extraction_eval import MetricEvalStatus
from app.services.extraction_eval import build_fixture_scorecard
from app.services.extraction_gold_eval import (
    RealTrustOutcome,
    build_real_gold_scorecard,
    evaluate_real_gold_fixture,
    load_real_gold_fixtures,
)


REAL_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction_gold"
SYNTHETIC_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction_eval"
REAL_CORPUS_DIR = PROJECT_ROOT / "data" / "extraction_gold_real"


def _load_real_fixture(document_id: str):
    fixtures = {f.document_id: f for f in load_real_gold_fixtures(REAL_FIXTURES_DIR)}
    return fixtures[document_id]


def _real_payloads() -> dict[str, dict]:
    return {
        "real_trusted_match": {
            "period_type": "A",
            "period_end": "2024-12-31",
            "currency": "AUD",
            "scale": "thousands",
            "source_document_id": "123e4567-e89b-12d3-a456-426614174000",
            "provenance": {
                "revenue": "income_statement:page_7:Revenue from contracts with customers",
                "ebit": "income_statement:page_8:Earnings before interest and tax",
            },
            "metrics": {
                "revenue": 1500000,
                "ebit": 120000,
            },
        },
        "real_abstain_missing_metric": {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "thousands",
            "source_document_id": "123e4567-e89b-12d3-a456-426614174001",
            "provenance": {
                "net_debt": "placeholder provenance not_configured for this fixture",
            },
            "metrics": {},
        },
        "real_quarantine_currency_mismatch": {
            "period_type": "H",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "thousands",
            "source_document_id": "123e4567-e89b-12d3-a456-426614174002",
            "provenance": {
                "revenue": "income_statement:page_5:Revenue",
            },
            "metrics": {
                "revenue": 750000,
            },
        },
    }


def test_load_real_gold_fixtures_and_expected_trust_labels():
    fixtures = load_real_gold_fixtures(REAL_FIXTURES_DIR)
    fixture_by_id = {fixture.document_id: fixture for fixture in fixtures}

    assert set(fixture_by_id) == {
        "real_trusted_match",
        "real_abstain_missing_metric",
        "real_quarantine_currency_mismatch",
    }

    assert (
        fixture_by_id["real_trusted_match"].expected_trust == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["real_abstain_missing_metric"].expected_trust
        == RealTrustOutcome.ABSTAIN
    )
    assert (
        fixture_by_id["real_quarantine_currency_mismatch"].expected_trust
        == RealTrustOutcome.QUARANTINE
    )


def test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist():
    fixtures = load_real_gold_fixtures(REAL_CORPUS_DIR)
    fixture_by_id = {fixture.document_id: fixture for fixture in fixtures}

    assert len(fixtures) == 10
    assert fixture_by_id["qbe_h_2025-06-30"].metrics["operating_cf"] == 1_756_000_000.0
    assert "operating_cash_flow" not in fixture_by_id["qbe_h_2025-06-30"].metrics

    for corpus_file in sorted(REAL_CORPUS_DIR.glob("*.json")):
        payload = json.loads(corpus_file.read_text(encoding="utf-8"))
        source_file = payload["source_file"]
        assert (PROJECT_ROOT / source_file).exists(), source_file


def test_scorecard_script_defaults_to_real_gold_corpus():
    script_path = PROJECT_ROOT / "scripts" / "extraction_gold_eval_scorecard.py"
    spec = importlib.util.spec_from_file_location(
        "extraction_gold_eval_scorecard", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.DEFAULT_FIXTURES_DIR == PROJECT_ROOT / "data" / "extraction_gold_real"


def test_real_gold_fixture_evaluates_trust_outcomes():
    payloads = _real_payloads()

    trusted = evaluate_real_gold_fixture(
        _load_real_fixture("real_trusted_match"),
        payloads["real_trusted_match"],
    )
    assert trusted.context_ok is True
    assert trusted.trust == RealTrustOutcome.TRUSTED
    assert trusted.trust_matches_expected is True
    assert all(metric.status.value == "correct" for metric in trusted.metrics)
    assert trusted.provenance_summary["status"] == "clean"
    assert trusted.provenance_summary["issue_count"] == 0

    abstain = evaluate_real_gold_fixture(
        _load_real_fixture("real_abstain_missing_metric"),
        payloads["real_abstain_missing_metric"],
    )
    assert abstain.trust == RealTrustOutcome.ABSTAIN
    assert abstain.trust_triggers == ["net_debt:missing"]
    assert abstain.trust_matches_expected is True
    assert abstain.metrics[0].status == MetricEvalStatus.MISSING
    assert abstain.provenance_summary["status"] == "issues_detected"
    abstain_issue_codes = {
        issue["code"] for issue in abstain.provenance_summary["issues"]
    }
    assert "synthetic_evidence" in abstain_issue_codes

    quarantine = evaluate_real_gold_fixture(
        _load_real_fixture("real_quarantine_currency_mismatch"),
        payloads["real_quarantine_currency_mismatch"],
    )
    assert quarantine.context_ok is False
    assert "currency" in quarantine.context_mismatches
    assert quarantine.trust == RealTrustOutcome.QUARANTINE
    assert quarantine.trust_triggers == ["context_mismatch:currency"]
    assert all(metric.status.value == "quarantine" for metric in quarantine.metrics)
    assert quarantine.provenance_summary["status"] == "clean"


def test_real_gold_abstain_documents_can_be_wrong_or_missing_noncontradictory():
    fixture = _load_real_fixture("real_abstain_missing_metric")

    missing_payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {},
    }
    missing_eval = evaluate_real_gold_fixture(fixture, missing_payload)
    assert missing_eval.trust == RealTrustOutcome.ABSTAIN
    assert missing_eval.trust_triggers == ["net_debt:missing"]
    assert missing_eval.trust_matches_expected is True
    assert missing_eval.metrics[0].status == MetricEvalStatus.MISSING

    wrong_payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {"net_debt": 20000},
    }
    wrong_eval = evaluate_real_gold_fixture(fixture, wrong_payload)
    assert wrong_eval.trust == RealTrustOutcome.ABSTAIN
    assert wrong_eval.trust_triggers == ["net_debt:wrong"]
    assert wrong_eval.trust_matches_expected is True
    assert wrong_eval.metrics[0].status == MetricEvalStatus.WRONG


def test_real_gold_scorecard_stays_separate_from_synthetic_flow():
    scorecard = build_real_gold_scorecard(REAL_FIXTURES_DIR, _real_payloads())
    synthetic_scorecard = build_fixture_scorecard(SYNTHETIC_FIXTURES_DIR, {})

    assert scorecard["trusted_count"] == 1
    assert scorecard["abstained_count"] == 1
    assert scorecard["quarantined_count"] == 1
    assert all("document_id" in entry for entry in scorecard["fixture_summaries"])
    assert all("fixture_id" not in entry for entry in scorecard["fixture_summaries"])
    assert all("trust_triggers" in entry for entry in scorecard["fixture_summaries"])

    expected_triggers = {
        "real_trusted_match": [],
        "real_abstain_missing_metric": ["net_debt:missing"],
        "real_quarantine_currency_mismatch": ["context_mismatch:currency"],
    }
    for entry in scorecard["fixture_summaries"]:
        assert entry["trust_triggers"] == expected_triggers[entry["document_id"]]

    synthetic_fixture_ids = {
        entry["fixture_id"] for entry in synthetic_scorecard["fixture_summaries"]
    }
    real_ids = {entry["document_id"] for entry in scorecard["fixture_summaries"]}
    assert real_ids.isdisjoint(synthetic_fixture_ids)
    expected_synthetic_ids = {
        "currency_mismatch",
        "correct_ok",
        "wrong_value",
        "missing_metric",
        "optional_abstain",
        "context_mismatch",
        "scoring_mix",
        "period_mismatch",
        "scale_mismatch",
        "mixed_status",
        "shares_fallback_disagreement",
        "statutory_underlying_wrong_value",
        "wrong_current_period_column",
        # Phase 02 regression fixtures
        "quarterly_cashflow_only",
        "net_debt_derived_row_abstain",
    }
    assert expected_synthetic_ids.issubset(synthetic_fixture_ids)
    assert "trusted_count" not in synthetic_scorecard


def test_real_gold_scorecard_reports_provenance_diagnostics_without_changing_trust():
    scorecard = build_real_gold_scorecard(REAL_FIXTURES_DIR, _real_payloads())
    by_document = {
        entry["document_id"]: entry for entry in scorecard["fixture_summaries"]
    }

    assert scorecard["trusted_count"] == 1
    assert scorecard["abstained_count"] == 1
    assert scorecard["quarantined_count"] == 1
    assert scorecard["provenance_summary"]["available_fixture_count"] == 3
    assert scorecard["provenance_summary"]["fixture_with_issues_count"] == 1
    assert scorecard["provenance_summary"]["status"] == "issues_detected"

    assert by_document["real_trusted_match"]["provenance_status"] == "clean"
    assert by_document["real_trusted_match"]["trust"] == "trusted"
    assert (
        by_document["real_abstain_missing_metric"]["provenance_status"]
        == "issues_detected"
    )
    assert by_document["real_abstain_missing_metric"]["trust"] == "abstain"


def test_real_gold_eval_endpoint_runs_current_multipass_logic(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="bhp_a_2025-06-30",
        source_file="sample.pdf",
        period_type="A",
        period_end="2025-06-30",
        currency="USD",
        scale="millions",
        metrics={
            "revenue": 51_262_000_000.0,
            "operating_cash_flow": 18_692_000_000.0,
            "net_debt": 12_924_000_000.0,
        },
        expected_trust="trusted",
    )

    monkeypatch.setattr(main_app, "_load_real_gold_dataset", lambda _path: [gold_doc])
    monkeypatch.setattr(
        main_app, "_resolve_real_gold_source_path", lambda _path: pdf_path
    )
    monkeypatch.setattr(
        main_app, "_persist_local_llm_api_key", lambda: "local-openai-key"
    )
    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="ok_low_confidence",
            error=None,
            payload={
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "USD",
                "scale": "millions",
                "metrics": {
                    "revenue": 51_262_000_000.0,
                    "operating_cf": 18_692_000_000.0,
                    "net_debt": 12_924_000_000.0,
                },
                "_method_provenance": {
                    "requested_method": "auto",
                    "actual_method": "docling",
                    "strict_method": False,
                },
            },
        ),
    )

    result = main_app._run_real_gold_eval_sync(main_app.RealGoldEvalRequest())

    assert result["summary"]["total_documents"] == 1
    assert result["summary"]["failed_documents"] == 0
    assert result["summary"]["total_accuracy"] == 1.0
    assert result["summary"]["trust_distribution"]["trusted"] == 1
    assert result["documents"][0]["extraction_status"] == "ok_low_confidence"
    assert result["documents"][0]["ticker"] == "UNKNOWN"
    assert result["documents"][0]["correct_metric_count"] == 3
    assert result["documents"][0]["failed_metric_count"] == 0
    assert result["documents"][0]["trust_outcome"] == "trusted"
    assert result["documents"][0]["mismatch_reasons"] == []


def test_real_gold_eval_endpoint_respects_limit(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    docs = [
        main_app.RealGoldDocument(
            document_id=f"doc_{index}",
            source_file="sample.pdf",
            period_type="A",
            period_end="2025-06-30",
            currency="AUD",
            scale="millions",
            metrics={"revenue": 100.0},
            expected_trust="trusted",
        )
        for index in range(2)
    ]

    monkeypatch.setattr(main_app, "_load_real_gold_dataset", lambda _path: docs)
    monkeypatch.setattr(
        main_app, "_resolve_real_gold_source_path", lambda _path: pdf_path
    )
    monkeypatch.setattr(
        main_app, "_persist_local_llm_api_key", lambda: "local-openai-key"
    )
    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="ok",
            error=None,
            payload={
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
                "_method_provenance": {
                    "requested_method": "auto",
                    "actual_method": "docling",
                    "strict_method": False,
                },
            },
        ),
    )

    result = main_app._run_real_gold_eval_sync(main_app.RealGoldEvalRequest(limit=1))

    assert result["summary"]["total_documents"] == 1
    assert [doc["document_id"] for doc in result["documents"]] == ["doc_0"]


def test_real_gold_eval_endpoint_passes_method_selection(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="bhp_a_2025-06-30",
        source_file="sample.pdf",
        period_type="A",
        period_end="2025-06-30",
        currency="USD",
        scale="millions",
        metrics={"revenue": 51_262_000_000.0},
        expected_trust="trusted",
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(main_app, "_load_real_gold_dataset", lambda _path: [gold_doc])
    monkeypatch.setattr(
        main_app, "_resolve_real_gold_source_path", lambda _path: pdf_path
    )
    monkeypatch.setattr(
        main_app, "_persist_local_llm_api_key", lambda: "local-openai-key"
    )

    def fake_run_method_isolated_extraction(
        pdf_path_arg,
        metadata_arg,
        llm_client_arg,
        *,
        requested_method,
        strict_method,
        skip_narrative,
    ):
        captured.update(
            {
                "pdf_path": pdf_path_arg,
                "metadata": metadata_arg,
                "requested_method": requested_method,
                "strict_method": strict_method,
                "skip_narrative": skip_narrative,
            }
        )
        return SimpleNamespace(
            status="ok",
            error=None,
            payload={
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "USD",
                "scale": "millions",
                "metrics": {"revenue": 51_262_000_000.0},
                "_method_provenance": {
                    "requested_method": requested_method,
                    "actual_method": requested_method,
                    "strict_method": strict_method,
                },
            },
        )

    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        fake_run_method_isolated_extraction,
    )

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(method="docling", strict_method=True)
    )

    assert result["requested_method"] == "docling"
    assert result["strict_method"] is True
    assert captured["requested_method"] == "docling"
    assert captured["strict_method"] is True
    assert result["documents"][0]["method_provenance"]["actual_method"] == "docling"


def test_real_gold_eval_endpoint_attaches_backend_review_session_for_flagged_metrics(
    monkeypatch, tmp_path
):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="qbe_h_2025-06-30",
        source_file="sample.pdf",
        period_type="H",
        period_end="2025-06-30",
        currency="USD",
        scale="millions",
        metrics={"revenue": 10875.0, "net_debt": 123.0},
        expected_trust="abstain",
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(main_app, "_load_real_gold_dataset", lambda _path: [gold_doc])
    monkeypatch.setattr(
        main_app, "_resolve_real_gold_source_path", lambda _path: pdf_path
    )
    monkeypatch.setattr(
        main_app, "_persist_local_llm_api_key", lambda: "local-openai-key"
    )
    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="ok_low_confidence",
            error=None,
            payload={
                "period_type": "H",
                "period_end": "2025-06-30",
                "currency": "USD",
                "scale": "millions",
                "metrics": {"revenue": 10875.0},
                "_method_provenance": {
                    "requested_method": "docling",
                    "actual_method": "docling",
                    "strict_method": True,
                },
            },
        ),
    )

    def fake_create_review_session_from_payload(**kwargs):
        captured.update(kwargs)
        return {
            "session_id": "real-gold-review-123",
            "documents": [{"reason": "reviewable"}],
            "items": [{"item_id": "item-1"}],
        }

    monkeypatch.setattr(
        main_app,
        "create_review_session_from_payload",
        fake_create_review_session_from_payload,
    )

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(method="docling", strict_method=True)
    )

    document = result["documents"][0]
    assert document["failed_metric_count"] == 1
    assert document["review_session_id"] == "real-gold-review-123"
    assert document["review_item_count"] == 1
    assert document["review_reason"] == "reviewable"
    assert captured["document_id"] == "qbe_h_2025-06-30"
    assert captured["status"] == "ok_low_confidence"
    assert captured["payload"]["metrics"] == {"revenue": 10875.0}


def test_real_gold_eval_endpoint_reports_review_session_failures(
    monkeypatch, tmp_path
):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="qbe_h_2025-06-30",
        source_file="sample.pdf",
        period_type="H",
        period_end="2025-06-30",
        currency="USD",
        scale="millions",
        metrics={"revenue": 10875.0, "net_debt": 123.0},
        expected_trust="abstain",
    )

    monkeypatch.setattr(main_app, "_load_real_gold_dataset", lambda _path: [gold_doc])
    monkeypatch.setattr(
        main_app, "_resolve_real_gold_source_path", lambda _path: pdf_path
    )
    monkeypatch.setattr(
        main_app, "_persist_local_llm_api_key", lambda: "local-openai-key"
    )
    monkeypatch.setattr(
        main_app,
        "run_method_isolated_extraction",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="ok_low_confidence",
            error=None,
            payload={
                "period_type": "H",
                "period_end": "2025-06-30",
                "currency": "USD",
                "scale": "millions",
                "metrics": {"revenue": 10875.0},
                "_method_provenance": {
                    "requested_method": "docling",
                    "actual_method": "docling",
                    "strict_method": True,
                },
            },
        ),
    )
    monkeypatch.setattr(
        main_app,
        "create_review_session_from_payload",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("unable to persist session")
        ),
    )

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(method="docling", strict_method=True)
    )

    document = result["documents"][0]
    assert document["failed_metric_count"] == 1
    assert document["review_session_id"] is None
    assert document["review_item_count"] == 0
    assert document["review_reason"] == "review_session_failed:unable to persist session"
    assert document["trust_outcome"] == "abstain"
    assert any(
        reason.startswith("metric:net_debt:") for reason in document["mismatch_reasons"]
    )


def test_real_gold_eval_route_is_async():
    assert inspect.iscoroutinefunction(main_app.run_real_gold_eval)


def test_real_gold_eval_summary_rolls_up_failure_and_trigger_fields():
    summary = main_app._summarize_real_gold_results(
        [
            {
                "context_correct": True,
                "context_mismatches": [],
                "failed_metric_count": 1,
                "trust_matches_expected": False,
                "trust_outcome": "abstain",
                "trust_triggers": ["net_debt:missing"],
                "metric_results": {
                    "net_debt": {"status": "missing"},
                    "revenue": {"status": "correct"},
                },
            },
            {
                "context_correct": False,
                "context_mismatches": ["currency"],
                "failed_metric_count": 0,
                "trust_matches_expected": True,
                "trust_outcome": "quarantine",
                "trust_triggers": ["context_mismatch:currency"],
                "metric_results": {
                    "revenue": {"status": "correct"},
                },
            },
        ]
    )

    assert summary["failed_documents"] == 2
    assert summary["context_mismatch_documents"] == 1
    assert summary["context_mismatch_fields"] == 1
    assert summary["missing_count"] == 1
    assert summary["correct_count"] == 2
    assert summary["trust_matches_expected"] == 1
    assert summary["trust_mismatches_expected"] == 1
    assert summary["trust_trigger_counts"] == {
        "context_mismatch:currency": 1,
        "net_debt:missing": 1,
    }
