from pathlib import Path
from types import SimpleNamespace
import os
import inspect
import importlib.util
import json
import sys
import threading
import time

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import main as main_app
from app.services.confirmed_metric_coverage_review import (
    resolve_confirmed_metric_coverage_source_path,
)
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
REQUIRE_REAL_GOLD_SOURCE_ASSETS = "TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS"


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
            "metrics": {
                "revenue": 187_743,
                "np_attributable": 1_100_860,
                "operating_cf": -854_114,
                "investing_cf": 301_155,
                "financing_cf": 4_103_422,
                "cash_end": 3_956_993,
            },
        },
        "am5_h_2025-12-31_canary_regression": {
            "period_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "units",
            "source_document_id": "aacc4c29-3089-48cf-8b82-8004134f9387",
            "provenance": {
                "np_attributable": "income_statement:page_10:Loss after income tax expense for the half-year attributable to the owners of Antares Metals Limited",
                "operating_cf": "cashflow_statement:page_13:Net cash used in operating activities",
                "investing_cf": "cashflow_statement:page_13:Net cash from/(used in) investing activities",
                "financing_cf": "cashflow_statement:page_13:Net cash from financing activities",
                "cash_end": "cashflow_statement:page_13:Cash and cash equivalents at the end of the financial half-year",
            },
            "metrics": {
                "revenue": None,
                "ebit": None,
                "np_attributable": -1_359_665,
                "operating_cf": -1_180_006,
                "investing_cf": -87_689,
                "financing_cf": 956_516,
                "cash_end": 1_055_036,
            },
        },
        "aqx_h_2025-12-31_canary_regression": {
            "period_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "units",
            "source_document_id": "0ed0104f-f29a-4068-8ff7-370f14fead98",
            "provenance": {
                "revenue": "income_statement:page_21:Revenue from continuing operations",
                "np_attributable": "income_statement:page_21:Net loss attributable to owners of the Parent Entity",
                "operating_cf": "cashflow_statement:page_24:Net cash used in operating activities",
                "investing_cf": "cashflow_statement:page_24:Net cash flow (used in)/from investing activities",
                "financing_cf": "cashflow_statement:page_24:Net cash from financing activities",
                "cash_end": "cashflow_statement:page_24:Cash and cash equivalents at the end of the period",
            },
            "metrics": {
                "revenue": 13_552,
                "ebit": None,
                "np_attributable": -1_158_426,
                "operating_cf": -1_462_291,
                "investing_cf": 32_031,
                "financing_cf": 1_866_935,
                "cash_end": 802_985,
            },
        },
        "atm_a_2025-12-31_canary_regression": {
            "period_type": "A",
            "period_end": "2025-12-31",
            "currency": "IDR",
            "scale": "millions",
            "source_document_id": "96e9aabd-44dc-4c2c-be8c-74248a0a9025",
            "provenance": {
                "revenue": "income_statement:page_27:Pendapatan dari kontrak dengan pelanggan",
                "ebit": "income_statement:page_27:LABA USAHA",
                "np_attributable": "income_statement:page_28:Profit for the year attributable to owners of the parent",
                "operating_cf": "cashflow_statement:page_30:Net cash provided by operating activities",
                "investing_cf": "cashflow_statement:page_30:Net cash used in investing activities",
                "financing_cf": "cashflow_statement:page_31:Net cash provided by financing activities",
                "capex": "cashflow_statement:page_30:Additions to fixed assets",
                "cash_end": "cashflow_statement:page_31:Cash and cash equivalents at end of the year",
            },
            "metrics": {
                "revenue": 84_642_439_000_000,
                "ebit": 8_395_030_000_000,
                "np_attributable": 7_208_834_000_000,
                "operating_cf": 4_853_256_000_000,
                "investing_cf": -1_506_766_000_000,
                "financing_cf": 299_870_000_000,
                "capex": -430_528_000_000,
                "cash_end": 8_433_610_000_000,
            },
        },
        "crs_h_2025-12-31_canary_regression": {
            "period_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "units",
            "source_document_id": "b43a16fb-7660-4bf7-96ab-0db641cd4032",
            "provenance": {
                "np_attributable": "income_statement:page_4:Loss after income tax expense for the half year",
                "operating_cf": "cashflow_statement:page_7:Net cash used in operating activities",
                "investing_cf": "cashflow_statement:page_7:Net cash used in investing activities",
                "financing_cf": "cashflow_statement:page_7:Net cash generated from financing activities",
                "cash_end": "cashflow_statement:page_7:Cash and cash equivalents at end of half year",
            },
            "metrics": {
                "revenue": None,
                "ebit": None,
                "np_attributable": -1_937_589,
                "operating_cf": -588_790,
                "investing_cf": -3_429_257,
                "financing_cf": 997_240,
                "cash_end": 4_756_183,
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
        "viva_fy2025_regression",
        "bhp_a_2025-06-30_canary_regression",
        "clv_h_2026-01-31_canary_regression",
        "ctm_a_2025-12-31_canary_regression",
        "aau_a_2025-12-31_canary_regression",
        "am5_h_2025-12-31_canary_regression",
        "aqx_h_2025-12-31_canary_regression",
        "atm_a_2025-12-31_canary_regression",
        "crs_h_2025-12-31_canary_regression",
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
        fixture_by_id["am5_h_2025-12-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["aqx_h_2025-12-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["atm_a_2025-12-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )
    assert (
        fixture_by_id["crs_h_2025-12-31_canary_regression"].expected_trust
        == RealTrustOutcome.TRUSTED
    )


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
    assert all(metric.status == MetricEvalStatus.CORRECT for metric in evaluation.metrics)


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
    assert all(metric.status == MetricEvalStatus.CORRECT for metric in evaluation.metrics)


def test_new_canary_source_review_fixtures_trust_source_backed_payloads():
    for document_id in (
        "am5_h_2025-12-31_canary_regression",
        "aqx_h_2025-12-31_canary_regression",
        "atm_a_2025-12-31_canary_regression",
        "crs_h_2025-12-31_canary_regression",
    ):
        evaluation = evaluate_real_gold_fixture(
            _load_real_fixture(document_id),
            _real_payloads()[document_id],
        )

        assert evaluation.context_ok is True
        assert evaluation.trust == RealTrustOutcome.TRUSTED
        assert evaluation.trust_matches_expected is True
        assert evaluation.trust_triggers == []
        assert all(
            metric.status == MetricEvalStatus.CORRECT for metric in evaluation.metrics
        )


def test_real_gold_scorecard_can_filter_document_ids():
    scorecard = build_real_gold_scorecard(
        REAL_FIXTURES_DIR,
        _real_payloads(),
        document_ids=[
            "atm_a_2025-12-31_canary_regression",
            "crs_h_2025-12-31_canary_regression",
        ],
    )

    assert scorecard["total_fixture_count"] == 2
    assert scorecard["trusted_count"] == 2
    assert scorecard["abstained_count"] == 0
    assert scorecard["quarantined_count"] == 0
    assert {
        entry["document_id"] for entry in scorecard["fixture_summaries"]
    } == {
        "atm_a_2025-12-31_canary_regression",
        "crs_h_2025-12-31_canary_regression",
    }


def test_real_gold_scorecard_stays_separate_from_synthetic_flow():
    scorecard = build_real_gold_scorecard(REAL_FIXTURES_DIR, _real_payloads())
    synthetic_scorecard = build_fixture_scorecard(SYNTHETIC_FIXTURES_DIR, {})

    assert scorecard["trusted_count"] == 10
    assert scorecard["abstained_count"] == 1
    assert scorecard["quarantined_count"] == 1
    assert all("document_id" in entry for entry in scorecard["fixture_summaries"])
    assert all("fixture_id" not in entry for entry in scorecard["fixture_summaries"])
    assert all("trust_triggers" in entry for entry in scorecard["fixture_summaries"])

    expected_triggers = {
        "real_trusted_match": [],
        "real_abstain_missing_metric": ["net_debt:missing"],
        "real_quarantine_currency_mismatch": ["context_mismatch:currency"],
        "viva_fy2025_regression": [],
        "bhp_a_2025-06-30_canary_regression": [],
        "clv_h_2026-01-31_canary_regression": [],
        "ctm_a_2025-12-31_canary_regression": [],
        "aau_a_2025-12-31_canary_regression": [],
        "am5_h_2025-12-31_canary_regression": [],
        "aqx_h_2025-12-31_canary_regression": [],
        "atm_a_2025-12-31_canary_regression": [],
        "crs_h_2025-12-31_canary_regression": [],
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

    assert scorecard["trusted_count"] == 10
    assert scorecard["abstained_count"] == 1
    assert scorecard["quarantined_count"] == 1
    assert scorecard["provenance_summary"]["available_fixture_count"] == 12
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
        main_app.RealGoldEvalRequest(method="docling", strict_method=True)
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

    result = main_app._run_real_gold_eval_sync(main_app.RealGoldEvalRequest())

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
        main_app.RealGoldEvalRequest(method="docling", strict_method=True)
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
        main_app.RealGoldEvalRequest(method="docling", strict_method=True)
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


def test_real_gold_eval_route_preserves_blocking_response_by_default(monkeypatch):
    """Existing non-background callers must keep getting a 200 + full body."""
    captured: dict[str, object] = {}

    def fake_sync(body):
        captured["body"] = body
        return _stub_sync_payload()

    monkeypatch.setattr(main_app, "_run_real_gold_eval_sync", fake_sync)

    client = TestClient(main_app.app)
    response = client.post("/api/extraction-eval/real-gold", json={})

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
            "/api/extraction-eval/real-gold?background=true", json={}
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
    schedule = client.post("/api/extraction-eval/real-gold?background=true", json={})
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
        event.get("message") == "Real-Gold summary ready"
        for event in last["progress"]
    )


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
    schedule = client.post("/api/extraction-eval/real-gold?background=true", json={})
    task_id = schedule.json()["task_id"]

    deadline = time.monotonic() + 3.0
    last: dict = {}
    while time.monotonic() < deadline:
        last = client.get(
            f"/api/extraction-eval/real-gold/tasks/{task_id}"
        ).json()
        if last.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert last.get("status") == "failed", last
    assert "extraction crashed" in (last.get("error") or "")
    assert last["result"] is None


def test_real_gold_eval_task_endpoint_returns_404_for_unknown_id():
    client = TestClient(main_app.app)
    response = client.get(
        "/api/extraction-eval/real-gold/tasks/does-not-exist"
    )
    assert response.status_code == 404
