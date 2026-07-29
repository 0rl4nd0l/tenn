from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import os
import inspect
import importlib.util
import json
import sys
import threading
import time

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import main as main_app
from app.services.confirmed_metric_coverage_review import (
    resolve_confirmed_metric_coverage_source_path,
)
from app.services.extraction_eval import (
    FixtureContext,
    MetricEvalStatus,
    build_fixture_scorecard,
)
from app.services.extraction_gold_eval import (
    ASXDocumentClass,
    RealGoldFixture,
    RealTrustOutcome,
    build_real_gold_scorecard,
    classify_real_gold_fixtures,
    evaluate_real_gold_fixture,
    load_real_gold_fixtures,
    summarize_real_gold_evaluations,
)


REAL_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction_gold"
SYNTHETIC_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction_eval"
REAL_CORPUS_DIR = PROJECT_ROOT / "data" / "extraction_gold_real"
REQUIRE_REAL_GOLD_SOURCE_ASSETS = "TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS"


def _structured_provenance(
    metric: str,
    *,
    source_document_id: str,
    source: str,
    value: float = 100.0,
    period_type: str = "A",
    period_end: str = "2025-06-30",
    currency: str = "AUD",
    scale: str = "millions",
) -> dict[str, dict]:
    multiplier = {
        "units": 1,
        "thousands": 1_000,
        "millions": 1_000_000,
        "billions": 1_000_000_000,
        "trillions": 1_000_000_000_000,
    }[scale]
    raw_value = f"{value / multiplier:.15g}"
    table_label = source.removeprefix("derived:")
    return {
        metric: {
            "metric": metric,
            "source": source,
            "table_label": table_label,
            "page_number": 1,
            "page_tag": "page_1",
            "row_ref": metric,
            "source_cell": {
                "source_document_id": source_document_id,
                "page_number": 1,
                "table_label": table_label,
                "row_index": 1,
                "column_index": 2,
                "row_label": metric,
                "raw_value": raw_value,
                "header_cell": period_end,
                "requested_period_end": period_end,
            },
            "scale": scale,
            "currency": currency,
            "period_type": period_type,
            "period_end": period_end,
            "source_document_id": source_document_id,
        }
    }


def _structured_provenance_for_metrics(
    metric_sources: dict[str, str],
    *,
    source_document_id: str,
    metric_values: dict[str, float],
    period_type: str = "A",
    period_end: str = "2025-06-30",
    currency: str = "AUD",
    scale: str = "millions",
) -> dict[str, dict]:
    output: dict[str, dict] = {}
    for metric, source in metric_sources.items():
        output.update(
            _structured_provenance(
                metric,
                source_document_id=source_document_id,
                source=source,
                value=metric_values[metric],
                period_type=period_type,
                period_end=period_end,
                currency=currency,
                scale=scale,
            )
        )
    return output


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
        "viva_fy2025_regression": {
            "period_type": "A",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "millions",
            "source_document_id": "viva_fy2025",
            "provenance": {
                "ebit": "presentation:page_2:RC EBIT $437.0m",
                "np_attributable": "presentation:page_2:Statutory Net Loss ($421.1m)",
                "operating_cf": "presentation:page_5:Operating Cash Flow $541.8m",
                "capex": "presentation:page_5:Net capital expenditure $494.4m",
            },
            "metrics": {
                "ebit": 437.0,
                "np_attributable": -421.1,
                "operating_cf": 541.8,
                "capex": 494.4,
            },
        },
        "bhp_a_2025-06-30_canary_regression": {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "USD",
            "scale": "millions",
            "source_document_id": "2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7",
            "provenance": {
                "revenue": "income_statement:page_1:Revenue 51,262",
                "operating_cf": "cashflow_statement:page_1:Net operating cash flows 18,692",
                "net_debt": "ofr:page_1:Net debt 12,924",
            },
            "field_provenance": _structured_provenance_for_metrics(
                {
                    "revenue": "income_statement",
                    "operating_cf": "cashflow_statement",
                    "net_debt": "net_debt_note",
                },
                source_document_id="2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7",
                metric_values={
                    "revenue": 51_262_000_000,
                    "operating_cf": 18_692_000_000,
                    "net_debt": 12_924_000_000,
                },
                period_end="2025-06-30",
                currency="USD",
                scale="millions",
            ),
            "metrics": {
                "revenue": 51_262_000_000,
                "operating_cf": 18_692_000_000,
                "net_debt": 12_924_000_000,
            },
        },
        "clv_h_2026-01-31_canary_regression": {
            "period_type": "H",
            "period_end": "2026-01-31",
            "currency": "AUD",
            "scale": "millions",
            "source_document_id": "da9f9ea5-6596-464f-af14-5acf12f9b050",
            "provenance": {
                "revenue": "income_statement:page_1:1H revenue of $44.1 million",
                "np_attributable": "income_statement:page_1:NPAT $4.2 million",
            },
            "metrics": {
                "revenue": 44_100_000,
                "ebit": None,
                "np_attributable": 4_200_000,
            },
        },
        "ctm_a_2025-12-31_canary_regression": {
            "period_type": "A",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "units",
            "source_document_id": "035c6758-7aed-41a6-9e84-ad154125d431",
            "provenance": {
                "operating_cf": "cashflow_statement:page_27:Net cash used in operating activities",
                "investing_cf": "cashflow_statement:page_27:Net cash used in investing activities",
                "financing_cf": "cashflow_statement:page_27:Net cash from financing activities",
                "cash_end": "cashflow_statement:page_27:Cash and cash equivalents at 31 December",
            },
            "metrics": {
                "operating_cf": -13_225_929,
                "investing_cf": -2_167_611,
                "financing_cf": 22_024_529,
                "cash_end": 24_577_181,
            },
        },
        "aau_a_2025-12-31_canary_regression": {
            "period_type": "A",
            "period_end": "2025-12-31",
            "currency": "USD",
            "scale": "units",
            "source_document_id": "508fc892-ae88-45ec-981f-cd9e124c8375",
            "provenance": {
                "revenue": "income_statement:page_23:Revenue",
                "np_attributable": "income_statement:page_23:Profit/(loss) after income tax expense for the year",
                "operating_cf": "cashflow_statement:page_26:Net cash used in operating activities",
                "investing_cf": "cashflow_statement:page_26:Net cash provided by/(used in) investing activities",
                "financing_cf": "cashflow_statement:page_26:Net cash provided by financing activities",
                "cash_end": "cashflow_statement:page_26:Cash at the end of financial year",
            },
            "field_provenance": _structured_provenance_for_metrics(
                {
                    "revenue": "income_statement",
                    "np_attributable": "income_statement",
                    "operating_cf": "cashflow_statement",
                    "investing_cf": "cashflow_statement",
                    "financing_cf": "cashflow_statement",
                    "cash_end": "cashflow_statement",
                },
                source_document_id="508fc892-ae88-45ec-981f-cd9e124c8375",
                metric_values={
                    "revenue": 187_743,
                    "np_attributable": 1_100_860,
                    "operating_cf": -854_114,
                    "investing_cf": 301_155,
                    "financing_cf": 4_103_422,
                    "cash_end": 3_956_993,
                },
                period_end="2025-12-31",
                currency="USD",
                scale="units",
            ),
            "metrics": {
                "revenue": 187_743,
                "np_attributable": 1_100_860,
                "operating_cf": -854_114,
                "investing_cf": 301_155,
                "financing_cf": 4_103_422,
                "cash_end": 3_956_993,
            },
        },
    }


def _in_memory_fixture(
    document_id: str,
    document_class: ASXDocumentClass,
    metrics: dict[str, float | None],
) -> RealGoldFixture:
    period_type = {
        ASXDocumentClass.ANNUAL: "A",
        ASXDocumentClass.HALF_YEAR: "H",
        ASXDocumentClass.QUARTERLY: "Q",
    }[document_class]
    return RealGoldFixture(
        document_id=document_id,
        context=FixtureContext(
            period_type=period_type,
            period_end="2025-06-30",
            currency="AUD",
            scale="millions",
            accounting_basis="statutory",
        ),
        metrics=metrics,
        tolerances={},
        expected_trust=None,
        document_class=document_class,
        source_document_id=document_id,
    )


def test_load_real_gold_fixtures_and_expected_trust_labels():
    fixtures = load_real_gold_fixtures(REAL_FIXTURES_DIR)
    fixture_by_id = {fixture.document_id: fixture for fixture in fixtures}

    assert set(fixture_by_id) == {
        "real_trusted_match",
        "real_abstain_missing_metric",
        "real_quarantine_currency_mismatch",
        "viva_fy2025_regression",
        "bhp_a_2025-06-30_canary_regression",
        "clv_h_2026-01-31_canary_regression",
        "ctm_a_2025-12-31_canary_regression",
        "aau_a_2025-12-31_canary_regression",
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
    assert (
        fixture_by_id["clv_h_2026-01-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["ctm_a_2025-12-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["aau_a_2025-12-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["bhp_a_2025-06-30_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["bhp_a_2025-06-30_canary_regression"].source_document_id
        == "2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7"
    )
    assert fixture_by_id["real_trusted_match"].source_document_id is None
    assert all(fixture.document_class is None for fixture in fixtures)


@pytest.mark.parametrize("numeric_field", ["metrics", "tolerances"])
@pytest.mark.parametrize("boolean_value", [False, True])
def test_load_real_gold_fixtures_rejects_boolean_numbers(
    tmp_path,
    numeric_field,
    boolean_value,
):
    fixture = {
        "document_id": "boolean-fixture",
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "units",
        "metrics": {"revenue": 0},
        "tolerances": {"revenue": 0},
    }
    fixture[numeric_field]["revenue"] = boolean_value
    (tmp_path / "boolean.json").write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(ValueError, match="must be numeric"):
        load_real_gold_fixtures(tmp_path)


@pytest.mark.parametrize(
    "field_name",
    [
        "document_id",
        "source_document_id",
        "period_type",
        "period_end",
        "currency",
        "scale",
        "accounting_basis",
    ],
)
def test_load_real_gold_fixtures_rejects_boolean_identity_and_context_fields(
    tmp_path,
    field_name,
):
    fixture = {
        "document_id": "boolean-identity",
        "source_document_id": "boolean-identity",
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "units",
        "accounting_basis": "statutory",
        "metrics": {"revenue": 0},
        "tolerances": {"revenue": 0},
    }
    fixture[field_name] = True
    (tmp_path / "boolean.json").write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(ValueError, match=rf"{field_name}.*must be a string"):
        load_real_gold_fixtures(tmp_path)


def test_real_gold_rejects_impossible_fixture_and_payload_dates(tmp_path):
    fixture_payload = {
        "document_id": "impossible-date",
        "source_document_id": "impossible-date",
        "period_type": "A",
        "period_end": "2025-02-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
        "metrics": {"revenue": None},
        "tolerances": {},
    }
    (tmp_path / "impossible.json").write_text(
        json.dumps(fixture_payload),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="period_end must be a valid ISO date"):
        load_real_gold_fixtures(tmp_path)

    fixture = RealGoldFixture(
        document_id="impossible-date",
        context=FixtureContext(
            period_type="A",
            period_end="2025-02-30",
            currency="AUD",
            scale="millions",
            accounting_basis="statutory",
        ),
        metrics={"revenue": None},
        tolerances={},
        expected_trust=None,
        source_document_id="impossible-date",
    )
    with pytest.raises(ValueError, match="period_end must be a valid ISO date"):
        evaluate_real_gold_fixture(
            fixture,
            {
                "period_type": "A",
                "period_end": "2025-02-30",
                "currency": "AUD",
                "scale": "millions",
                "accounting_basis": "statutory",
                "source_document_id": "impossible-date",
                "metrics": {"revenue": None},
            },
        )


def test_real_gold_rejects_boolean_in_memory_fixture_source_identity():
    fixture = RealGoldFixture(
        document_id="boolean-fixture-source",
        context=FixtureContext(
            period_type="A",
            period_end="2025-06-30",
            currency="AUD",
            scale="millions",
            accounting_basis="statutory",
        ),
        metrics={"revenue": 100.0},
        tolerances={},
        expected_trust=None,
        source_document_id=True,
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id="True",
        source="income_statement",
    )

    with pytest.raises(ValueError, match="source_document_id must be a string"):
        evaluate_real_gold_fixture(
            fixture,
            {
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
                "scale": "millions",
                "accounting_basis": "statutory",
                "source_document_id": "True",
                "metrics": {"revenue": 100.0},
                "field_provenance": field_provenance,
            },
        )


def test_load_real_gold_fixtures_preserves_numeric_zero(tmp_path):
    fixture = {
        "document_id": "zero-fixture",
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "units",
        "metrics": {"revenue": 0},
        "tolerances": {"revenue": 0},
    }
    (tmp_path / "zero.json").write_text(json.dumps(fixture), encoding="utf-8")

    loaded = load_real_gold_fixtures(tmp_path)

    assert loaded[0].metrics["revenue"] == 0.0
    assert loaded[0].tolerances["revenue"] == 0.0


def test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_source_paths():
    fixtures = load_real_gold_fixtures(REAL_CORPUS_DIR)
    fixture_by_id = {fixture.document_id: fixture for fixture in fixtures}

    assert len(fixtures) == 15
    assert fixture_by_id["qbe_h_2025-06-30"].metrics["operating_cf"] == 1_756_000_000.0
    assert "operating_cash_flow" not in fixture_by_id["qbe_h_2025-06-30"].metrics

    missing_source_files = []
    for corpus_file in sorted(REAL_CORPUS_DIR.glob("*.json")):
        payload = json.loads(corpus_file.read_text(encoding="utf-8"))
        source_file = payload["source_file"]
        try:
            resolved_source = resolve_confirmed_metric_coverage_source_path(source_file)
        except FileNotFoundError:
            missing_source_files.append(source_file)
            continue
        assert resolved_source.is_file(), source_file

    if os.getenv(REQUIRE_REAL_GOLD_SOURCE_ASSETS) == "1":
        assert missing_source_files == []


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


def test_real_gold_scorecard_distinguishes_legacy_none_from_explicit_empty_payloads():
    legacy_scorecard = build_real_gold_scorecard(REAL_FIXTURES_DIR)

    assert legacy_scorecard["evaluation_lane"] == "real_document"
    assert legacy_scorecard["total_fixture_count"] == 8

    with pytest.raises(
        ValueError,
        match="fixture/payload document ID sets differ",
    ):
        build_real_gold_scorecard(REAL_FIXTURES_DIR, {})


def test_real_gold_holdout_scorecard_is_aggregate_only():
    aggregate = {
        "corpus_version": "opaque-v1",
        "corpus_digest": "a" * 64,
        "document_count": 48,
        "partition_counts": {"diagnostic": 12, "holdout": 36},
        "bucket_counts": {
            "annual": 8,
            "4E": 8,
            "half-year": 8,
            "4D": 8,
            "quarterly": 8,
            "4C": 8,
        },
        "company_count": 12,
        "sector_count": 6,
        "scan_image_heavy_count": 6,
        "non_aud_count": 1,
        "issuer_size_counts": {"large": 24, "small": 24},
    }

    assert (
        build_real_gold_scorecard(
            REAL_FIXTURES_DIR,
            corpus_classification="holdout",
            development_aggregate=aggregate,
        )
        == aggregate
    )


def test_real_gold_fixture_evaluates_trust_outcomes():
    payloads = _real_payloads()

    trusted = evaluate_real_gold_fixture(
        _load_real_fixture("real_trusted_match"),
        payloads["real_trusted_match"],
    )
    assert trusted.context_ok is True
    assert trusted.trust == RealTrustOutcome.ABSTAIN
    assert trusted.trust_matches_expected is False
    assert all(metric.status.value == "correct" for metric in trusted.metrics)
    assert trusted.provenance_summary["status"] == "clean"
    assert trusted.provenance_summary["issue_count"] == 0
    assert trusted.provenance_trust_failures == [
        "revenue:provenance_invalid:fixture_source_document_id_missing",
        "ebit:provenance_invalid:fixture_source_document_id_missing",
    ]

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


def test_real_gold_required_provenance_is_a_fail_closed_trust_gate():
    direct_fixture = _in_memory_fixture(
        "direct-source",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    base_payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
        "metrics": {"revenue": 100.0},
    }

    missing = evaluate_real_gold_fixture(direct_fixture, base_payload)
    assert missing.trust == RealTrustOutcome.ABSTAIN
    assert missing.trust_triggers == ["revenue:provenance_missing"]
    assert missing.provenance_trust_failures == ["revenue:provenance_missing"]

    unbound = evaluate_real_gold_fixture(
        direct_fixture,
        {
            **base_payload,
            "provenance": {
                "revenue": "income_statement:page_1:Revenue",
            },
        },
    )
    assert unbound.trust == RealTrustOutcome.ABSTAIN
    assert unbound.trust_triggers == [
        "revenue:provenance_invalid:source_document_id_missing"
    ]

    bound = evaluate_real_gold_fixture(
        direct_fixture,
        {
            **base_payload,
            "source_document_id": "direct-source",
            "field_provenance": _structured_provenance(
                "revenue",
                source_document_id="direct-source",
                source="income_statement",
            ),
        },
    )
    assert bound.trust == RealTrustOutcome.TRUSTED
    assert bound.provenance_trust_failures == []

    generic_bound = evaluate_real_gold_fixture(
        direct_fixture,
        {
            **base_payload,
            "source_document_id": "direct-source",
            "provenance": {
                "revenue": "income_statement:page_1:Revenue",
            },
        },
    )
    assert generic_bound.trust == RealTrustOutcome.ABSTAIN
    assert generic_bound.provenance_trust_failures == [
        "revenue:provenance_invalid:structured_provenance_missing"
    ]

    wrong_unbound = evaluate_real_gold_fixture(
        direct_fixture,
        {
            **base_payload,
            "metrics": {"revenue": 90.0},
            "provenance": {
                "revenue": "income_statement:page_1:Revenue",
            },
        },
    )
    assert wrong_unbound.trust == RealTrustOutcome.ABSTAIN
    assert wrong_unbound.trust_triggers == ["revenue:wrong"]
    assert wrong_unbound.provenance_trust_failures == [
        "revenue:provenance_invalid:source_document_id_missing"
    ]


@pytest.mark.parametrize(
    ("scope", "field_name"),
    [
        ("payload", "source_document_id"),
        ("payload", "period_type"),
        ("payload", "period_end"),
        ("payload", "currency"),
        ("payload", "scale"),
        ("payload", "accounting_basis"),
        ("provenance", "source_document_id"),
        ("provenance", "source"),
        ("provenance", "statement_context"),
        ("provenance", "period_type"),
        ("provenance", "period_end"),
        ("provenance", "currency"),
        ("provenance", "scale"),
        ("provenance", "page_number"),
        ("provenance", "page_tag"),
        ("provenance", "table_label"),
        ("provenance", "row_ref"),
        ("cell", "source_document_id"),
        ("cell", "page_number"),
        ("cell", "page_tag"),
        ("cell", "row_index"),
        ("cell", "column_index"),
        ("cell", "row_label"),
        ("cell", "row_ref"),
        ("cell", "header_cell"),
        ("cell", "requested_period_end"),
        ("cell", "raw_value"),
    ],
)
def test_real_gold_rejects_boolean_payload_and_provenance_fields(
    scope,
    field_name,
):
    fixture = _in_memory_fixture(
        "boolean-payload-field",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"]["statement_context"] = "income_statement"
    payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
        "source_document_id": fixture.document_id,
        "metrics": {"revenue": 100.0},
        "field_provenance": field_provenance,
    }
    target = {
        "payload": payload,
        "provenance": field_provenance["revenue"],
        "cell": field_provenance["revenue"]["source_cell"],
    }[scope]
    target[field_name] = True

    with pytest.raises(ValueError, match=rf"{field_name}.*must"):
        evaluate_real_gold_fixture(fixture, payload)


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        (
            {"source_document_id": "wrong-source"},
            "source_document_id_mismatch",
        ),
        (
            {"period_end": "2024-06-30"},
            "period_end_mismatch",
        ),
        (
            {"currency": "USD"},
            "currency_mismatch",
        ),
        (
            {"scale": "thousands"},
            "scale_mismatch",
        ),
        (
            {"source": "cashflow_statement", "table_label": "cashflow_statement"},
            "statement_context_not_allowed",
        ),
    ],
)
def test_real_gold_rejects_provenance_outside_fixture_and_contract_context(
    mutation,
    expected_reason,
):
    fixture = _in_memory_fixture(
        "strict-revenue",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.source_document_id,
        source="income_statement",
    )
    field_provenance["revenue"].update(mutation)
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "strict-revenue",
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        f"revenue:provenance_invalid:{expected_reason}"
    ]


def test_real_gold_rejects_top_level_source_mismatch_and_page_row_only_evidence():
    fixture = _in_memory_fixture(
        "strict-revenue",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    complete = _structured_provenance(
        "revenue",
        source_document_id="strict-revenue",
        source="income_statement",
    )
    wrong_top_level = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "wrong-source",
            "metrics": {"revenue": 100.0},
            "field_provenance": complete,
        },
    )
    page_row_only = complete["revenue"].copy()
    page_row_only.pop("table_label")
    page_row_only.pop("source_cell")
    incomplete = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "strict-revenue",
            "metrics": {"revenue": 100.0},
            "field_provenance": {"revenue": page_row_only},
        },
    )

    assert wrong_top_level.provenance_trust_failures == [
        "revenue:provenance_invalid:source_document_id_mismatch"
    ]
    assert incomplete.provenance_trust_failures == [
        "revenue:provenance_invalid:table_or_region_binding_missing"
    ]


@pytest.mark.parametrize(
    ("page_tag", "expected_reason"),
    [
        ("page_999", "page_binding_mismatch"),
        ("page_1x", "page_binding_invalid"),
    ],
)
def test_real_gold_rejects_contradictory_parent_page_bindings(
    page_tag,
    expected_reason,
):
    fixture = _in_memory_fixture(
        "contradictory-page-bindings",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"]["page_tag"] = page_tag

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        f"revenue:provenance_invalid:{expected_reason}"
    ]


@pytest.mark.parametrize(
    ("provenance_mutation", "cell_mutation", "expected_reason"),
    [
        (
            {"table_label": "cashflow_statement"},
            {"table_label": "cashflow_statement"},
            "statement_table_context_mismatch",
        ),
        (
            {"statement_context": "cashflow_statement"},
            {},
            "statement_context_mismatch",
        ),
        (
            {"region_ref": "cashflow_statement"},
            {},
            "table_or_region_binding_mismatch",
        ),
    ],
)
def test_real_gold_rejects_conflicting_source_coordinate_representations(
    provenance_mutation,
    cell_mutation,
    expected_reason,
):
    fixture = _in_memory_fixture(
        "conflicting-source-coordinate",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"].update(provenance_mutation)
    field_provenance["revenue"]["source_cell"].update(cell_mutation)

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        f"revenue:provenance_invalid:{expected_reason}"
    ]


def test_real_gold_rejects_prior_period_source_cell_binding():
    fixture = _in_memory_fixture(
        "strict-revenue",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id="strict-revenue",
        source="income_statement",
    )
    field_provenance["revenue"]["source_cell"]["requested_period_end"] = "2024-06-30"
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "strict-revenue",
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        "revenue:provenance_invalid:cell_period_mismatch"
    ]


@pytest.mark.parametrize(
    ("cell_mutation", "expected_reason"),
    [
        (
            {"source_document_id": "wrong-source"},
            "cell_source_document_id_mismatch",
        ),
        ({"page_number": 2}, "cell_page_mismatch"),
        (
            {"table_label": "different_table"},
            "cell_table_or_region_mismatch",
        ),
        ({"row_label": "Not revenue"}, "cell_row_mismatch"),
        ({"header_cell": "30 June 2024"}, "cell_header_period_mismatch"),
        ({"header_cell": "30 June 20250"}, "cell_header_period_mismatch"),
        ({"raw_value": "0.0002"}, "cell_value_mismatch"),
    ],
)
def test_real_gold_rejects_incoherent_direct_source_cells(
    cell_mutation,
    expected_reason,
):
    fixture = _in_memory_fixture(
        "coherent-revenue",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id="coherent-revenue",
        source="income_statement",
    )
    field_provenance["revenue"]["source_cell"].update(cell_mutation)
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "coherent-revenue",
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        f"revenue:provenance_invalid:{expected_reason}"
    ]


@pytest.mark.parametrize(
    ("cell_mutation", "expected_reason"),
    [
        ({"row_ref": "Not revenue"}, "cell_row_mismatch"),
        ({"page_tag": "page_999"}, "cell_page_mismatch"),
    ],
)
def test_real_gold_rejects_conflicting_source_cell_siblings(
    cell_mutation,
    expected_reason,
):
    fixture = _in_memory_fixture(
        "conflicting-source-cell-siblings",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"]["source_cell"].update(cell_mutation)

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        f"revenue:provenance_invalid:{expected_reason}"
    ]


def test_real_gold_rejects_conflicting_single_and_plural_source_cells():
    fixture = _in_memory_fixture(
        "conflicting-cell-representations",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    conflicting_cell = deepcopy(field_provenance["revenue"]["source_cell"])
    conflicting_cell["raw_value"] = "999"
    field_provenance["revenue"]["source_cells"] = [conflicting_cell]

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        "revenue:provenance_invalid:cell_representation_mismatch"
    ]


def test_real_gold_accepts_matching_single_and_plural_source_cells():
    fixture = _in_memory_fixture(
        "matching-cell-representations",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"]["source_cells"] = [
        deepcopy(field_provenance["revenue"]["source_cell"])
    ]

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.TRUSTED
    assert result.provenance_trust_failures == []


@pytest.mark.parametrize(
    ("missing_field", "expected_reason"),
    [
        ("source_document_id", "cell_source_document_id_missing"),
        ("table_label", "cell_table_or_region_missing"),
    ],
)
def test_real_gold_rejects_incomplete_direct_source_cell_identity(
    missing_field,
    expected_reason,
):
    fixture = _in_memory_fixture(
        "complete-cell-identity",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"]["source_cell"].pop(missing_field)

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        f"revenue:provenance_invalid:{expected_reason}"
    ]


def test_real_gold_accepts_human_readable_exact_period_header():
    fixture = _in_memory_fixture(
        "human-period-header",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id="human-period-header",
        source="income_statement",
    )
    field_provenance["revenue"]["source_cell"]["header_cell"] = "30 June 2025 AUDm"
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "human-period-header",
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.TRUSTED
    assert result.provenance_trust_failures == []


@pytest.mark.parametrize("header_cell", ["30 June 2025x", "x30 June 2025"])
def test_real_gold_rejects_period_header_prefix_and_suffix_impersonation(header_cell):
    fixture = _in_memory_fixture(
        "period-header-impersonation",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    field_provenance["revenue"]["source_cell"]["header_cell"] = header_cell

    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "field_provenance": field_provenance,
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        "revenue:provenance_invalid:cell_header_period_mismatch"
    ]


def test_real_gold_rejects_direct_net_debt_from_disallowed_income_statement():
    fixture = _in_memory_fixture(
        "strict-net-debt",
        ASXDocumentClass.ANNUAL,
        {"net_debt": 70.0},
    )
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "strict-net-debt",
            "metrics": {"net_debt": 70.0},
            "field_provenance": _structured_provenance(
                "net_debt",
                source_document_id="strict-net-debt",
                source="income_statement",
            ),
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        "net_debt:provenance_invalid:statement_context_not_allowed"
    ]


def test_real_gold_extra_derived_net_debt_fails_trust_without_inflating_quality():
    fixture = _in_memory_fixture(
        "extra-derived-net-debt",
        ASXDocumentClass.ANNUAL,
        {"revenue": 100.0},
    )
    field_provenance = _structured_provenance(
        "revenue",
        source_document_id=fixture.document_id,
        source="income_statement",
    )
    derived_net_debt = _structured_provenance(
        "net_debt",
        source_document_id=fixture.document_id,
        source="derived:balance_sheet",
        value=70.0,
    )
    derived_net_debt["net_debt"]["derivation_identity"] = "total_debt_minus_cash_end"
    field_provenance.update(derived_net_debt)
    payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
        "source_document_id": fixture.document_id,
        "metrics": {"revenue": 100.0, "net_debt": 70.0},
        "field_provenance": field_provenance,
    }

    evaluation = evaluate_real_gold_fixture(fixture, payload)
    scorecard = summarize_real_gold_evaluations(
        [fixture],
        [evaluation],
        {fixture.document_id: payload},
    )

    assert [metric.metric for metric in evaluation.metrics] == ["revenue"]
    assert evaluation.trust == RealTrustOutcome.ABSTAIN
    assert evaluation.trust_triggers == [
        "net_debt:provenance_invalid:unauthorized_derivation"
    ]
    assert evaluation.provenance_trust_failures == [
        "net_debt:provenance_invalid:unauthorized_derivation"
    ]
    assert scorecard["accepted_numeric_precision"] == {
        "correct_count": 1,
        "accepted_count": 1,
        "value": 1.0,
    }
    assert scorecard["supported_metric_recall"] == {
        "correct_count": 1,
        "expected_count": 1,
        "value": 1.0,
    }


def test_real_gold_quarantine_still_reports_present_metric_provenance_failure():
    fixture = _in_memory_fixture(
        "quarantined-provenance",
        ASXDocumentClass.HALF_YEAR,
        {"revenue": 100.0},
    )
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "H",
            "period_end": "2025-06-30",
            "currency": "USD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "quarantined-provenance",
            "metrics": {"revenue": 100.0},
        },
    )

    assert result.trust == RealTrustOutcome.QUARANTINE
    assert result.trust_triggers == ["context_mismatch:currency"]
    assert result.provenance_trust_failures == ["revenue:provenance_missing"]


def test_real_gold_missing_fixture_source_identity_fails_explicitly():
    fixture = RealGoldFixture(
        document_id="missing-fixture-source",
        context=FixtureContext(
            period_type="A",
            period_end="2025-06-30",
            currency="AUD",
            scale="millions",
            accounting_basis="statutory",
        ),
        metrics={"revenue": 100.0},
        tolerances={},
        expected_trust=None,
        document_class=None,
        source_document_id=None,
    )
    result = evaluate_real_gold_fixture(
        fixture,
        {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": "payload-source",
            "metrics": {"revenue": 100.0},
            "field_provenance": _structured_provenance(
                "revenue",
                source_document_id="payload-source",
                source="income_statement",
            ),
        },
    )

    assert result.trust == RealTrustOutcome.ABSTAIN
    assert result.provenance_trust_failures == [
        "revenue:provenance_invalid:fixture_source_document_id_missing"
    ]


def test_real_gold_missing_document_class_is_not_inferred_from_period_type():
    fixture = RealGoldFixture(
        document_id="unclassified-annual-period",
        context=FixtureContext(
            period_type="A",
            period_end="2025-06-30",
            currency="AUD",
            scale="millions",
            accounting_basis="statutory",
        ),
        metrics={"revenue": 100.0},
        tolerances={},
        expected_trust=None,
        document_class=None,
        source_document_id="unclassified-source",
    )
    payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
        "source_document_id": "unclassified-source",
        "metrics": {"revenue": 100.0},
        "field_provenance": _structured_provenance(
            "revenue",
            source_document_id="unclassified-source",
            source="income_statement",
        ),
    }
    evaluation = evaluate_real_gold_fixture(fixture, payload)
    scorecard = summarize_real_gold_evaluations(
        [fixture],
        [evaluation],
        {fixture.document_id: payload},
    )

    assert scorecard["fixture_summaries"][0]["document_class"] == "unclassified"
    assert scorecard["document_class_groups"]["unclassified"]["document_count"] == 1
    assert scorecard["document_class_groups"]["annual"]["document_count"] == 0


def test_real_gold_provenance_preserves_authorized_derivation_boundary():
    capex_fixture = _in_memory_fixture(
        "authorized-capex",
        ASXDocumentClass.QUARTERLY,
        {"capex": 30_000_000.0},
    )
    net_debt_fixture = _in_memory_fixture(
        "unauthorized-net-debt",
        ASXDocumentClass.ANNUAL,
        {"net_debt": 70.0},
    )
    common = {
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
    }

    authorized_capex_provenance = _structured_provenance(
        "capex",
        source_document_id="authorized-capex",
        source="derived:cashflow_statement",
        value=30_000_000.0,
        period_type="Q",
    )
    authorized_capex_provenance["capex"].update(
        {
            "derivation_identity": "appendix_5b_explicit_capex_subitem_sum",
            "source_row_refs": ["1.2(a)", "1.2(b)"],
            "source_cells": [
                {
                    "source_document_id": "authorized-capex",
                    "page_number": 1,
                    "table_label": "cashflow_statement",
                    "row_index": 2,
                    "column_index": 2,
                    "row_label": "1.2(a)",
                    "raw_value": "10",
                    "header_cell": "2025-06-30",
                    "requested_period_end": "2025-06-30",
                },
                {
                    "source_document_id": "authorized-capex",
                    "page_number": 1,
                    "table_label": "cashflow_statement",
                    "row_index": 3,
                    "column_index": 2,
                    "row_label": "1.2(b)",
                    "raw_value": "20",
                    "header_cell": "2025-06-30",
                    "requested_period_end": "2025-06-30",
                },
            ],
        }
    )
    capex = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": authorized_capex_provenance,
        },
    )
    missing_source_row_refs = {"capex": dict(authorized_capex_provenance["capex"])}
    missing_source_row_refs["capex"].pop("source_row_refs")
    capex_without_source_rows = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": missing_source_row_refs,
        },
    )
    embedded_provenance = {
        "capex": {
            **authorized_capex_provenance["capex"],
            "derivation_identity": (
                "prefix_appendix_5b_explicit_capex_subitem_sum_suffix"
            ),
        }
    }
    embedded_capex = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": embedded_provenance,
        },
    )
    misaligned_source_rows = deepcopy(authorized_capex_provenance)
    misaligned_source_rows["capex"]["source_cells"][1]["row_label"] = "1.2(c)"
    capex_with_misaligned_rows = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": misaligned_source_rows,
        },
    )
    mismatched_source_count = deepcopy(authorized_capex_provenance)
    mismatched_source_count["capex"]["source_cells"].pop()
    capex_with_mismatched_source_count = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": mismatched_source_count,
        },
    )
    wrong_derived_value = deepcopy(authorized_capex_provenance)
    wrong_derived_value["capex"]["source_cells"][1]["raw_value"] = "21"
    capex_with_wrong_derived_value = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": wrong_derived_value,
        },
    )
    conflicting_source_row_siblings = deepcopy(authorized_capex_provenance)
    conflicting_source_row_siblings["capex"]["source_cells"][0]["row_ref"] = (
        "conflicting-row"
    )
    capex_with_conflicting_source_row_siblings = evaluate_real_gold_fixture(
        capex_fixture,
        {
            **common,
            "period_type": "Q",
            "source_document_id": "authorized-capex",
            "metrics": {"capex": 30_000_000.0},
            "field_provenance": conflicting_source_row_siblings,
        },
    )
    derived_net_debt_provenance = _structured_provenance(
        "net_debt",
        source_document_id="unauthorized-net-debt",
        source="derived:balance_sheet",
        value=70.0,
    )
    derived_net_debt_provenance["net_debt"]["derivation_identity"] = (
        "total_debt_minus_cash_end"
    )
    net_debt = evaluate_real_gold_fixture(
        net_debt_fixture,
        {
            **common,
            "period_type": "A",
            "source_document_id": "unauthorized-net-debt",
            "metrics": {"net_debt": 70.0},
            "field_provenance": derived_net_debt_provenance,
        },
    )

    assert capex.trust == RealTrustOutcome.TRUSTED
    assert capex.provenance_trust_failures == []
    assert capex_without_source_rows.trust == RealTrustOutcome.ABSTAIN
    assert capex_without_source_rows.provenance_trust_failures == [
        "capex:provenance_invalid:source_row_refs_missing"
    ]
    assert embedded_capex.trust == RealTrustOutcome.ABSTAIN
    assert embedded_capex.provenance_trust_failures == [
        "capex:provenance_invalid:unauthorized_derivation"
    ]
    assert capex_with_misaligned_rows.provenance_trust_failures == [
        "capex:provenance_invalid:source_row_cell_mismatch"
    ]
    assert capex_with_mismatched_source_count.provenance_trust_failures == [
        "capex:provenance_invalid:source_row_cell_count_mismatch"
    ]
    assert capex_with_wrong_derived_value.provenance_trust_failures == [
        "capex:provenance_invalid:derived_value_mismatch"
    ]
    assert capex_with_conflicting_source_row_siblings.provenance_trust_failures == [
        "capex:provenance_invalid:cell_row_mismatch"
    ]
    assert net_debt.trust == RealTrustOutcome.ABSTAIN
    assert net_debt.trust_triggers == [
        "net_debt:provenance_invalid:unauthorized_derivation"
    ]


def test_real_scorecard_reports_context_dimensions_independently_in_memory():
    fields = {
        "period-end": ("period_end", "2024-06-30"),
        "period-basis": ("period_type", "H"),
        "currency": ("currency", "USD"),
        "scale": ("scale", "thousands"),
        "accounting-basis": ("accounting_basis", "underlying"),
    }
    fixtures = [
        _in_memory_fixture(
            document_id,
            ASXDocumentClass.ANNUAL,
            {"revenue": 100.0},
        )
        for document_id in fields
    ]
    payloads: dict[str, dict] = {}
    for fixture in fixtures:
        payload = {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": {"revenue": 100.0},
            "provenance": {
                "revenue": "income_statement:page_1:Revenue",
            },
        }
        field, value = fields[fixture.document_id]
        payload[field] = value
        payloads[fixture.document_id] = payload

    evaluations = classify_real_gold_fixtures(fixtures, payloads)
    scorecard = summarize_real_gold_evaluations(
        fixtures,
        evaluations,
        payloads,
    )

    for field in (
        "period_end",
        "period_basis",
        "currency",
        "scale",
        "accounting_basis",
    ):
        assert scorecard[f"{field}_correctness_summary"] == {
            "expected_count": 5,
            "matched_count": 4,
            "mismatched_count": 1,
            "missing_count": 0,
        }


def test_real_scorecard_separates_quality_trust_class_and_lane_in_memory():
    fixtures = [
        _in_memory_fixture(
            "annual",
            ASXDocumentClass.ANNUAL,
            {"revenue": 100.0, "ebit": 20.0},
        ),
        _in_memory_fixture(
            "half-year",
            ASXDocumentClass.HALF_YEAR,
            {"revenue": 200.0},
        ),
        _in_memory_fixture(
            "quarterly-direct",
            ASXDocumentClass.QUARTERLY,
            {"operating_cf": 300.0},
        ),
        _in_memory_fixture(
            "quarterly-unbound",
            ASXDocumentClass.QUARTERLY,
            {"net_debt": 70.0},
        ),
    ]
    common = {
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "millions",
        "accounting_basis": "statutory",
    }
    payloads = {
        "annual": {
            **common,
            "period_type": "A",
            "source_document_id": "annual",
            "metrics": {"revenue": 100.0},
            "field_provenance": _structured_provenance(
                "revenue",
                source_document_id="annual",
                source="income_statement",
            ),
        },
        "half-year": {
            **common,
            "period_type": "H",
            "source_document_id": "half-year",
            "metrics": {"revenue": 250.0},
            "field_provenance": _structured_provenance(
                "revenue",
                source_document_id="half-year",
                source="income_statement",
                value=250.0,
                period_type="H",
            ),
        },
        "quarterly-direct": {
            **common,
            "period_type": "Q",
            "source_document_id": "quarterly-direct",
            "metrics": {"operating_cf": 300.0},
            "field_provenance": _structured_provenance(
                "operating_cf",
                source_document_id="quarterly-direct",
                source="cashflow_statement",
                value=300.0,
                period_type="Q",
            ),
        },
        "quarterly-unbound": {
            **common,
            "period_type": "Q",
            "metrics": {"net_debt": 70.0},
            "provenance": {
                "net_debt": "balance_sheet:page_1:Net debt",
            },
        },
    }
    evaluations = classify_real_gold_fixtures(fixtures, payloads)

    scorecard = summarize_real_gold_evaluations(
        fixtures,
        evaluations,
        payloads,
    )

    assert scorecard["evaluation_lane"] == "real_document"
    assert scorecard["accepted_numeric_precision"] == {
        "correct_count": 3,
        "accepted_count": 4,
        "value": 0.75,
    }
    assert scorecard["supported_metric_recall"] == {
        "correct_count": 3,
        "expected_count": 5,
        "value": 0.6,
    }
    assert scorecard["provenance_trust_failure_count"] == 1
    assert scorecard["trusted_count"] == 1
    assert scorecard["abstained_count"] == 3
    assert list(scorecard["document_class_groups"]) == [
        "annual",
        "half_year",
        "quarterly",
    ]
    assert (
        scorecard["document_class_groups"]["annual"]["supported_metric_recall"]["value"]
        == 0.5
    )
    assert (
        scorecard["document_class_groups"]["quarterly"][
            "provenance_trust_failure_count"
        ]
        == 1
    )
    assert scorecard["document_class_grouping"] == {
        "supported_classes": ["annual", "half_year", "quarterly"],
        "classification_is_metric_evidence": False,
        "classification_is_metric_authority": False,
    }
    assert {entry["evaluation_lane"] for entry in scorecard["fixture_summaries"]} == {
        "real_document"
    }


def test_real_scorecard_rejects_duplicate_and_mismatched_document_ids():
    fixtures = [
        _in_memory_fixture(
            "annual",
            ASXDocumentClass.ANNUAL,
            {"revenue": 100.0},
        ),
        _in_memory_fixture(
            "half-year",
            ASXDocumentClass.HALF_YEAR,
            {"revenue": 200.0},
        ),
    ]
    payloads = {
        fixture.document_id: {
            "period_type": fixture.context.period_type,
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "accounting_basis": "statutory",
            "source_document_id": fixture.document_id,
            "metrics": fixture.metrics,
            "provenance": {
                "revenue": "income_statement:page_1:Revenue",
            },
        }
        for fixture in fixtures
    }
    evaluations = classify_real_gold_fixtures(fixtures, payloads)

    with pytest.raises(ValueError) as duplicate_fixture_error:
        summarize_real_gold_evaluations(
            [fixtures[0], fixtures[0]],
            [evaluations[0]],
            payloads,
        )
    assert (
        str(duplicate_fixture_error.value) == "duplicate fixture document IDs: annual"
    )

    with pytest.raises(ValueError) as duplicate_evaluation_error:
        summarize_real_gold_evaluations(
            [fixtures[0]],
            [evaluations[0], evaluations[0]],
            payloads,
        )
    assert (
        str(duplicate_evaluation_error.value)
        == "duplicate evaluation document IDs: annual"
    )

    with pytest.raises(ValueError) as mismatched_ids_error:
        summarize_real_gold_evaluations(
            fixtures,
            [evaluations[0]],
            payloads,
        )
    assert str(mismatched_ids_error.value) == (
        "fixture/evaluation document ID sets differ: "
        "missing evaluations=['half-year']; unexpected evaluations=[]"
    )

    with pytest.raises(ValueError) as missing_payload_error:
        summarize_real_gold_evaluations(
            fixtures,
            evaluations,
            {"annual": payloads["annual"]},
        )
    assert str(missing_payload_error.value) == (
        "fixture/payload document ID sets differ: "
        "missing payloads=['half-year']; unexpected payloads=[]"
    )

    boolean_key_payloads = {
        True: payloads["annual"],
        "half-year": payloads["half-year"],
    }
    with pytest.raises(ValueError, match="payload keys must be strings"):
        summarize_real_gold_evaluations(
            fixtures,
            evaluations,
            boolean_key_payloads,
        )

    unexpected_payloads = {
        **payloads,
        "unexpected": payloads["annual"],
    }
    with pytest.raises(ValueError) as unexpected_payload_error:
        summarize_real_gold_evaluations(
            fixtures,
            evaluations,
            unexpected_payloads,
        )
    assert str(unexpected_payload_error.value) == (
        "fixture/payload document ID sets differ: "
        "missing payloads=[]; unexpected payloads=['unexpected']"
    )

    mismatched_embedded_payloads = deepcopy(payloads)
    mismatched_embedded_payloads["annual"]["document_id"] = "different-document"
    with pytest.raises(ValueError) as mismatched_payload_identity_error:
        summarize_real_gold_evaluations(
            fixtures,
            evaluations,
            mismatched_embedded_payloads,
        )
    assert str(mismatched_payload_identity_error.value) == (
        "payload document ID mismatches: annual='different-document'"
    )

    duplicate_embedded_payloads = deepcopy(payloads)
    duplicate_embedded_payloads["annual"]["document_id"] = "duplicate-document"
    duplicate_embedded_payloads["half-year"]["document_id"] = "duplicate-document"
    with pytest.raises(ValueError) as duplicate_payload_identity_error:
        summarize_real_gold_evaluations(
            fixtures,
            evaluations,
            duplicate_embedded_payloads,
        )
    assert str(duplicate_payload_identity_error.value) == (
        "duplicate payload document IDs: duplicate-document"
    )


def test_canary_failure_regression_payloads_are_not_trusted():
    clv_bad_payload = {
        "period_type": "H",
        "period_end": "2026-01-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "revenue": 44_100_000_000,
            "ebit": 6_900_000_000,
            "np_attributable": 4_200_000_000,
        },
    }
    clv_eval = evaluate_real_gold_fixture(
        _load_real_fixture("clv_h_2026-01-31_canary_regression"),
        clv_bad_payload,
    )
    assert clv_eval.trust == RealTrustOutcome.ABSTAIN
    assert set(clv_eval.trust_triggers) == {
        "revenue:wrong",
        "ebit:wrong",
        "np_attributable:wrong",
    }

    ctm_bad_payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "operating_cf": -13_225_929,
            "investing_cf": -2_167_611,
            "financing_cf": 22_024_529,
            "cash_end": 24_577_181,
        },
    }
    ctm_eval = evaluate_real_gold_fixture(
        _load_real_fixture("ctm_a_2025-12-31_canary_regression"),
        ctm_bad_payload,
    )
    assert ctm_eval.trust == RealTrustOutcome.QUARANTINE
    assert ctm_eval.trust_triggers == [
        "context_mismatch:period_type",
        "context_mismatch:scale",
    ]

    aau_missing_period_payload = {
        "period_type": "A",
        "period_end": None,
        "currency": "USD",
        "scale": "units",
        "metrics": {
            "revenue": 187_743,
            "np_attributable": 1_100_860,
            "operating_cf": -854_114,
            "investing_cf": 301_155,
            "financing_cf": 4_103_422,
            "cash_end": 3_956_993,
        },
    }
    aau_eval = evaluate_real_gold_fixture(
        _load_real_fixture("aau_a_2025-12-31_canary_regression"),
        aau_missing_period_payload,
    )
    assert aau_eval.trust == RealTrustOutcome.QUARANTINE
    assert aau_eval.trust_triggers == ["context_mismatch:period_end"]

    bhp_bad_payload = {
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {
            "revenue": 55_658_000_000,
            "ebit": 17_537_000_000,
            "np_attributable": 7_897_000_000,
            "operating_cf": 18_692_000_000,
            "investing_cf": -13_350_000_000,
            "financing_cf": -5_971_000_000,
            "capex": -9_398_000_000,
            "cash_end": 11_893_000_000,
            "net_debt": 12_924_000_000,
        },
    }
    bhp_eval = evaluate_real_gold_fixture(
        _load_real_fixture("bhp_a_2025-06-30_canary_regression"),
        bhp_bad_payload,
    )
    assert bhp_eval.trust == RealTrustOutcome.ABSTAIN
    assert bhp_eval.trust_triggers == ["revenue:wrong"]


def test_aau_canary_regression_fixture_trusts_source_backed_payload():
    evaluation = evaluate_real_gold_fixture(
        _load_real_fixture("aau_a_2025-12-31_canary_regression"),
        _real_payloads()["aau_a_2025-12-31_canary_regression"],
    )

    assert evaluation.context_ok is True
    assert evaluation.trust == RealTrustOutcome.TRUSTED
    assert evaluation.trust_matches_expected is True
    assert evaluation.trust_triggers == []
    assert {metric.metric for metric in evaluation.metrics} == {
        "revenue",
        "np_attributable",
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "cash_end",
    }
    assert all(
        metric.status == MetricEvalStatus.CORRECT for metric in evaluation.metrics
    )


def test_bhp_canary_regression_fixture_trusts_source_backed_payload():
    evaluation = evaluate_real_gold_fixture(
        _load_real_fixture("bhp_a_2025-06-30_canary_regression"),
        _real_payloads()["bhp_a_2025-06-30_canary_regression"],
    )

    assert evaluation.context_ok is True
    assert evaluation.trust == RealTrustOutcome.TRUSTED
    assert evaluation.trust_matches_expected is True
    assert evaluation.trust_triggers == []
    assert {metric.metric for metric in evaluation.metrics} == {
        "revenue",
        "operating_cf",
        "net_debt",
    }
    assert all(
        metric.status == MetricEvalStatus.CORRECT for metric in evaluation.metrics
    )


def test_real_gold_scorecard_stays_separate_from_synthetic_flow():
    scorecard = build_real_gold_scorecard(REAL_FIXTURES_DIR, _real_payloads())
    synthetic_scorecard = build_fixture_scorecard(SYNTHETIC_FIXTURES_DIR, {})

    assert scorecard["evaluation_lane"] == "real_document"
    assert synthetic_scorecard["evaluation_lane"] == "synthetic"
    assert scorecard["trusted_count"] == 2
    assert scorecard["abstained_count"] == 5
    assert scorecard["quarantined_count"] == 1
    assert all("document_id" in entry for entry in scorecard["fixture_summaries"])
    assert all("fixture_id" not in entry for entry in scorecard["fixture_summaries"])
    assert all("trust_triggers" in entry for entry in scorecard["fixture_summaries"])

    expected_triggers = {
        "real_trusted_match": [
            "revenue:provenance_invalid:fixture_source_document_id_missing",
            "ebit:provenance_invalid:fixture_source_document_id_missing",
        ],
        "real_abstain_missing_metric": ["net_debt:missing"],
        "real_quarantine_currency_mismatch": ["context_mismatch:currency"],
        "viva_fy2025_regression": [
            "ebit:provenance_invalid:fixture_source_document_id_missing",
            "np_attributable:provenance_invalid:fixture_source_document_id_missing",
            "operating_cf:provenance_invalid:fixture_source_document_id_missing",
            "capex:provenance_invalid:fixture_source_document_id_missing",
        ],
        "bhp_a_2025-06-30_canary_regression": [],
        "clv_h_2026-01-31_canary_regression": [
            "revenue:provenance_invalid:fixture_source_document_id_missing",
            "np_attributable:provenance_invalid:fixture_source_document_id_missing",
        ],
        "ctm_a_2025-12-31_canary_regression": [
            "operating_cf:provenance_invalid:fixture_source_document_id_missing",
            "investing_cf:provenance_invalid:fixture_source_document_id_missing",
            "financing_cf:provenance_invalid:fixture_source_document_id_missing",
            "cash_end:provenance_invalid:fixture_source_document_id_missing",
        ],
        "aau_a_2025-12-31_canary_regression": [],
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


def test_real_gold_scorecard_reports_provenance_diagnostics_and_fail_closed_trust():
    scorecard = build_real_gold_scorecard(REAL_FIXTURES_DIR, _real_payloads())
    by_document = {
        entry["document_id"]: entry for entry in scorecard["fixture_summaries"]
    }

    assert scorecard["trusted_count"] == 2
    assert scorecard["abstained_count"] == 5
    assert scorecard["quarantined_count"] == 1
    assert scorecard["provenance_summary"]["available_fixture_count"] == 8
    assert scorecard["provenance_summary"]["fixture_with_issues_count"] == 1
    assert scorecard["provenance_summary"]["status"] == "issues_detected"

    assert by_document["real_trusted_match"]["provenance_status"] == "clean"
    assert by_document["real_trusted_match"]["trust"] == "abstain"
    assert by_document["real_trusted_match"]["provenance_trust_failures"] == [
        "revenue:provenance_invalid:fixture_source_document_id_missing",
        "ebit:provenance_invalid:fixture_source_document_id_missing",
    ]
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
                "source_document_id": "bhp_a_2025-06-30",
                "provenance": {
                    "revenue": "income_statement:page_1:Revenue",
                    "operating_cf": (
                        "cashflow_statement:page_1:Net operating cash flows"
                    ),
                    "net_debt": "net_debt_note:page_1:Net debt",
                },
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

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    assert result["summary"]["total_documents"] == 1
    assert result["summary"]["failed_documents"] == 0
    assert result["summary"]["total_accuracy"] == 1.0
    assert result["summary"]["trust_distribution"]["trusted"] == 0
    assert result["summary"]["trust_distribution"]["abstain"] == 1
    assert result["documents"][0]["extraction_status"] == "ok_low_confidence"
    assert result["documents"][0]["ticker"] == "UNKNOWN"
    assert result["documents"][0]["correct_metric_count"] == 3
    assert result["documents"][0]["failed_metric_count"] == 0
    assert result["documents"][0]["trust_outcome"] == "abstain"
    assert result["documents"][0]["mismatch_reasons"] == [
        "trust: expected=trusted actual=abstain"
    ]


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

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(
            limit=1,
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

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
        prompt_bundle_id=None,
        model_override=None,
    ):
        captured.update(
            {
                "pdf_path": pdf_path_arg,
                "metadata": metadata_arg,
                "requested_method": requested_method,
                "strict_method": strict_method,
                "skip_narrative": skip_narrative,
                "prompt_bundle_id": prompt_bundle_id,
                "model_override": model_override,
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
        main_app.RealGoldEvalRequest(
            method="docling",
            strict_method=True,
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    assert result["requested_method"] == "docling"
    assert result["strict_method"] is True
    assert captured["requested_method"] == "docling"
    assert captured["strict_method"] is True
    assert result["documents"][0]["method_provenance"]["actual_method"] == "docling"


def test_real_gold_eval_policy_defaults_to_non_canonical(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="doc_default_noncanonical",
        source_file="sample.pdf",
        period_type="A",
        period_end="2025-06-30",
        currency="AUD",
        scale="millions",
        metrics={"revenue": 100.0},
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
        "_build_real_gold_fixture_manifest",
        lambda _path: {
            "dataset_dir": str(main_app.REAL_GOLD_DATASET_DIR),
            "fixture_file_count": 1,
            "fixture_content_sha256": "fixture-hash",
            "fixture_git_commit": "fixture-commit",
            "fixture_git_dirty": False,
        },
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

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    assert result["eval_policy"]["mode"] == "non_canonical"
    assert result["eval_policy"]["kpi_eligible"] is False
    assert "strict_method" in " ".join(result["eval_policy"]["non_canonical_reasons"])
    assert result["fixture_manifest"]["fixture_content_sha256"] == "fixture-hash"


def test_real_gold_eval_policy_marks_docling_strict_run_canonical(
    monkeypatch, tmp_path
):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="doc_canonical",
        source_file="sample.pdf",
        period_type="A",
        period_end="2025-06-30",
        currency="AUD",
        scale="millions",
        metrics={"revenue": 100.0},
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
        "_build_real_gold_fixture_manifest",
        lambda _path: {
            "dataset_dir": str(main_app.REAL_GOLD_DATASET_DIR),
            "fixture_file_count": 1,
            "fixture_content_sha256": "fixture-hash",
            "fixture_git_commit": "fixture-commit",
            "fixture_git_dirty": False,
        },
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
                    "requested_method": "docling",
                    "actual_method": "docling",
                    "strict_method": True,
                },
            },
        ),
    )

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(
            method="docling",
            strict_method=True,
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    assert result["eval_policy"]["mode"] == "canonical"
    assert result["eval_policy"]["kpi_eligible"] is True
    assert result["eval_policy"]["non_canonical_reasons"] == []
    assert result["fixture_manifest"]["fixture_git_dirty"] is False


def test_real_gold_eval_policy_demotes_kpi_when_fixture_provenance_missing(
    monkeypatch, tmp_path
):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    gold_doc = main_app.RealGoldDocument(
        document_id="doc_provenance_missing",
        source_file="sample.pdf",
        period_type="A",
        period_end="2025-06-30",
        currency="AUD",
        scale="millions",
        metrics={"revenue": 100.0},
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
        "_build_real_gold_fixture_manifest",
        lambda _path: {
            "dataset_dir": str(main_app.REAL_GOLD_DATASET_DIR),
            "fixture_file_count": 1,
            "fixture_content_sha256": "fixture-hash",
            "fixture_git_commit": None,
            "fixture_git_dirty": None,
        },
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
                    "requested_method": "docling",
                    "actual_method": "docling",
                    "strict_method": True,
                },
            },
        ),
    )

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(
            method="docling",
            strict_method=True,
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    assert result["eval_policy"]["mode"] == "non_canonical"
    assert result["eval_policy"]["kpi_eligible"] is False
    assert (
        "fixture_provenance:fixture_git_commit_missing"
        in result["eval_policy"]["non_canonical_reasons"]
    )
    assert (
        "fixture_provenance:fixture_git_dirty_not_false:None"
        in result["eval_policy"]["non_canonical_reasons"]
    )


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
        main_app.RealGoldEvalRequest(
            method="docling",
            strict_method=True,
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    document = result["documents"][0]
    assert document["failed_metric_count"] == 1
    assert document["review_session_id"] == "real-gold-review-123"
    assert document["review_item_count"] == 1
    assert document["review_reason"] == "reviewable"
    assert captured["document_id"] == "qbe_h_2025-06-30"
    assert captured["status"] == "ok_low_confidence"
    assert captured["payload"]["metrics"] == {"revenue": 10875.0}


def test_real_gold_holdout_development_does_not_persist_review_session(
    monkeypatch, tmp_path
):
    pdf_path = tmp_path / "protected.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    gold_doc = main_app.RealGoldDocument(
        document_id="protected-holdout-document",
        source_file="protected.pdf",
        period_type="H",
        period_end="2025-06-30",
        currency="AUD",
        scale="millions",
        metrics={"revenue": 100.0, "net_debt": 25.0},
        expected_trust="abstain",
    )
    review_calls: list[dict] = []

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
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0},
            },
        ),
    )
    monkeypatch.setattr(
        main_app,
        "create_review_session_from_payload",
        lambda **kwargs: review_calls.append(kwargs) or {},
    )
    aggregate = _stub_development_aggregate()

    result = main_app._run_real_gold_eval_sync(
        main_app.RealGoldEvalRequest(
            corpus_classification="holdout",
            access_mode="development",
            development_aggregate=aggregate,
        )
    )

    assert result == aggregate
    assert review_calls == []


def test_real_gold_eval_endpoint_reports_review_session_failures(monkeypatch, tmp_path):
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
        main_app.RealGoldEvalRequest(
            method="docling",
            strict_method=True,
            corpus_classification="non_holdout",
            access_mode="development",
        )
    )

    document = result["documents"][0]
    assert document["failed_metric_count"] == 1
    assert document["review_session_id"] is None
    assert document["review_item_count"] == 0
    assert (
        document["review_reason"] == "review_session_failed:unable to persist session"
    )
    assert document["trust_outcome"] == "abstain"
    assert any(
        reason.startswith("metric:net_debt:") for reason in document["mismatch_reasons"]
    )


def test_real_gold_eval_route_is_sync():
    """Handler must be sync so FastAPI runs it in the anyio threadpool.

    A coroutine would execute on the event loop and block /api/health during
    full-corpus evals. Docling timeouts are enforced by a spawn ProcessPoolExecutor,
    not SIGALRM, so no main-thread context is required.
    """
    assert not inspect.iscoroutinefunction(main_app.run_real_gold_eval)


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


# ---------------------------------------------------------------------------
# Background-task polling path (Phase B)
#
# Default behavior (no ?background flag) must still return the full blocking
# result synchronously so existing non-background callers (scripts,
# direct tests, and ad hoc API users) do not break.
#
# ?background=true returns 202 + task_id and runs the eval on a daemon thread.
# GET /api/extraction-eval/real-gold/tasks/{task_id} returns the current state.
# ---------------------------------------------------------------------------


def _stub_sync_payload() -> dict:
    return {
        "summary": {
            "total_documents": 0,
            "total_accuracy": 0.0,
            "trust_distribution": {"trusted": 0, "abstain": 0, "quarantine": 0},
            "metric_status_counts": {},
            "total_metric_checks": 0,
        },
        "documents": [],
        "dataset_dir": "stub",
        "requested_method": "auto",
        "strict_method": False,
        "prompt_variant_id": None,
        "model_override": None,
    }


def _stub_development_aggregate() -> dict:
    return {
        "corpus_version": "opaque-v1",
        "corpus_digest": "a" * 64,
        "document_count": 48,
        "partition_counts": {"diagnostic": 12, "holdout": 36},
        "bucket_counts": {
            "annual": 8,
            "4E": 8,
            "half-year": 8,
            "4D": 8,
            "quarterly": 8,
            "4C": 8,
        },
        "company_count": 12,
        "sector_count": 6,
        "scan_image_heavy_count": 6,
        "non_aud_count": 1,
        "issuer_size_counts": {"large": 24, "small": 24},
    }


def test_real_gold_eval_route_fails_closed_for_holdout(monkeypatch):
    monkeypatch.setattr(
        main_app, "_run_real_gold_eval_sync", lambda _body: _stub_sync_payload()
    )
    aggregate = _stub_development_aggregate()
    client = TestClient(main_app.app)

    response = client.post(
        "/api/extraction-eval/real-gold",
        json={
            "corpus_classification": "holdout",
            "access_mode": "development",
            "development_aggregate": aggregate,
        },
    )

    assert response.status_code == 200
    assert response.json() == aggregate


@pytest.mark.parametrize(
    ("failure", "status_code"),
    [
        (FileNotFoundError("protected/path/secret.pdf"), 400),
        (RuntimeError("secret expected=1 actual=2"), 500),
    ],
)
def test_real_gold_holdout_sync_masks_failure_details(
    monkeypatch, failure, status_code
):
    monkeypatch.setattr(
        main_app,
        "_build_real_gold_fixture_manifest",
        lambda _path: (_ for _ in ()).throw(failure),
    )

    with pytest.raises(main_app.HTTPException) as captured:
        main_app._run_real_gold_eval_sync(
            main_app.RealGoldEvalRequest(
                corpus_classification="holdout",
                access_mode="development",
                development_aggregate=_stub_development_aggregate(),
            )
        )

    assert captured.value.status_code == status_code
    assert captured.value.detail == "holdout evaluation failed"


def test_real_gold_eval_route_rejects_holdout_without_aggregate():
    client = TestClient(main_app.app)

    response = client.post(
        "/api/extraction-eval/real-gold",
        json={
            "corpus_classification": "holdout",
            "access_mode": "development",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid evaluation confidentiality contract"


def test_real_gold_eval_route_requires_explicit_confidentiality_contract():
    client = TestClient(main_app.app)

    response = client.post("/api/extraction-eval/real-gold", json={})

    assert response.status_code == 422
    missing_fields = {
        detail["loc"][-1]
        for detail in response.json()["detail"]
        if detail["type"] == "missing"
    }
    assert missing_fields == {"corpus_classification", "access_mode"}


def test_real_gold_eval_route_preserves_blocking_response_by_default(monkeypatch):
    """Existing non-background callers must keep getting a 200 + full body."""
    captured: dict[str, object] = {}

    def fake_sync(body):
        captured["body"] = body
        return _stub_sync_payload()

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", fake_sync)

    client = TestClient(main_app.app)
    response = client.post(
        "/api/extraction-eval/real-gold",
        json={
            "corpus_classification": "non_holdout",
            "access_mode": "development",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_documents"] == 0
    assert "task_id" not in body
    assert "status" not in body
    assert captured["body"] is not None


def test_real_gold_eval_route_returns_202_task_id_when_background_true(monkeypatch):
    """background=true must return 202 and a task_id without waiting for the job."""
    started = threading.Event()
    finish = threading.Event()

    def slow_sync(_body, progress_callback=None):
        if progress_callback:
            progress_callback(
                {
                    "stage": "evaluate_document",
                    "status": "running",
                    "message": "Evaluating stub document",
                }
            )
        started.set()
        finish.wait(timeout=5.0)
        return _stub_sync_payload()

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", slow_sync)

    client = TestClient(main_app.app)
    try:
        response = client.post(
            "/api/extraction-eval/real-gold?background=true",
            json={
                "corpus_classification": "non_holdout",
                "access_mode": "development",
            },
        )
        assert response.status_code == 202
        body = response.json()
        assert body["status"] in {"pending", "running"}
        assert isinstance(body.get("task_id"), str) and body["task_id"]
        # Handler must return before the eval finishes.
        assert started.wait(timeout=2.0), "background thread never started"
    finally:
        finish.set()


def test_real_gold_eval_task_endpoint_reports_completed_result(monkeypatch):
    def fake_sync(_body, progress_callback=None):
        if progress_callback:
            progress_callback(
                {
                    "stage": "summarize",
                    "status": "succeeded",
                    "message": "Real-Gold summary ready",
                    "completed": 0,
                    "total": 0,
                }
            )
        return _stub_sync_payload()

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", fake_sync)
    client = TestClient(main_app.app)
    schedule = client.post(
        "/api/extraction-eval/real-gold?background=true",
        json={
            "corpus_classification": "non_holdout",
            "access_mode": "development",
        },
    )
    assert schedule.status_code == 202
    task_id = schedule.json()["task_id"]

    deadline = time.monotonic() + 3.0
    last: dict = {}
    while time.monotonic() < deadline:
        poll = client.get(f"/api/extraction-eval/real-gold/tasks/{task_id}")
        assert poll.status_code == 200
        last = poll.json()
        if last.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert last.get("status") == "completed", last
    assert last["result"]["summary"]["total_documents"] == 0
    assert last["error"] is None
    assert any(
        event.get("message") == "Real-Gold summary ready" for event in last["progress"]
    )


def test_real_gold_holdout_background_result_and_progress_are_aggregate(monkeypatch):
    def fake_sync(_body, progress_callback=None):
        if progress_callback:
            progress_callback({"document_id": "secret", "expected": 1, "actual": 2})
        return _stub_sync_payload()

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", fake_sync)
    aggregate = _stub_development_aggregate()
    client = TestClient(main_app.app)
    schedule = client.post(
        "/api/extraction-eval/real-gold?background=true",
        json={
            "corpus_classification": "holdout",
            "access_mode": "development",
            "development_aggregate": aggregate,
        },
    )
    task_id = schedule.json()["task_id"]
    deadline = time.monotonic() + 3.0
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/extraction-eval/real-gold/tasks/{task_id}").json()
        if last.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert last["status"] == "completed"
    assert last["result"] == aggregate
    assert last["progress"]
    assert all(event == aggregate for event in last["progress"])


def test_real_gold_holdout_background_masks_failure_details(monkeypatch):
    def fake_sync(_body, progress_callback=None):
        if progress_callback:
            progress_callback({"document_id": "secret-before-failure"})
        raise RuntimeError("secret.pdf expected=1 actual=2")

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", fake_sync)
    aggregate = _stub_development_aggregate()
    client = TestClient(main_app.app)
    schedule = client.post(
        "/api/extraction-eval/real-gold?background=true",
        json={
            "corpus_classification": "holdout",
            "access_mode": "development",
            "development_aggregate": aggregate,
        },
    )
    task_id = schedule.json()["task_id"]
    deadline = time.monotonic() + 3.0
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/extraction-eval/real-gold/tasks/{task_id}").json()
        if last.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert last["status"] == "failed"
    assert last["error"] == "holdout evaluation failed"
    assert last["progress"]
    assert all(event == aggregate for event in last["progress"])


def test_real_gold_eval_task_endpoint_reports_failed_error(monkeypatch):
    def raising_sync(_body, progress_callback=None):
        if progress_callback:
            progress_callback(
                {
                    "stage": "evaluate_document",
                    "status": "running",
                    "message": "Evaluating stub document",
                }
            )
        raise RuntimeError("extraction crashed")

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", raising_sync)
    client = TestClient(main_app.app)
    schedule = client.post(
        "/api/extraction-eval/real-gold?background=true",
        json={
            "corpus_classification": "non_holdout",
            "access_mode": "development",
        },
    )
    task_id = schedule.json()["task_id"]

    deadline = time.monotonic() + 3.0
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/extraction-eval/real-gold/tasks/{task_id}").json()
        if last.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert last.get("status") == "failed", last
    assert "extraction crashed" in (last.get("error") or "")
    assert last["result"] is None


def test_real_gold_eval_task_endpoint_returns_404_for_unknown_id():
    client = TestClient(main_app.app)
    response = client.get("/api/extraction-eval/real-gold/tasks/does-not-exist")
    assert response.status_code == 404
