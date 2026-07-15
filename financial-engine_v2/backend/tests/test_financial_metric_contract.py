from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path


def _contract_module():
    return importlib.import_module("app.services.financial_metric_contract")


def test_financial_metric_contract_module_exposes_exact_field_authorities() -> None:
    contract = _contract_module()

    assert contract.CANONICAL_METRIC_FIELDS == (
        "revenue",
        "ebit",
        "np_attributable",
        "operating_cf",
        "investing_cf",
        "financing_cf",
        "capex",
        "cash_end",
        "net_debt",
        "shares_outstanding",
    )
    assert contract.PERSISTED_METRIC_COLUMNS == (
        *contract.CANONICAL_METRIC_FIELDS,
        "total_equity",
        "interest_expense",
    )
    assert contract.INTERNAL_METRIC_FIELDS == ("total_debt",)
    assert sorted(
        definition.extractor_output_order
        for definition in contract.METRIC_CONTRACT_FAMILIES
        if definition.extractor_output_order is not None
    ) == list(range(len(contract.CANONICAL_METRIC_FIELDS)))
    assert sorted(
        definition.persistence_order
        for definition in contract.METRIC_CONTRACT_FAMILIES
        if definition.persistence_order is not None
    ) == list(range(len(contract.PERSISTED_METRIC_COLUMNS)))


def test_financial_metric_contract_registry_is_unique_and_complete() -> None:
    contract = _contract_module()
    definitions = contract.METRIC_CONTRACT_FAMILIES

    assert len({definition.family for definition in definitions}) == len(definitions)
    assert contract.METRIC_CONTRACT_BY_FAMILY == {
        definition.family: definition for definition in definitions
    }

    by_canonical = {
        definition.canonical_field: definition
        for definition in definitions
        if definition.canonical_field is not None
    }
    for field in contract.CANONICAL_METRIC_FIELDS:
        definition = by_canonical[field]
        assert definition.persistence_column == field
        assert definition.statement_contexts
        assert definition.unit_kind != contract.MetricUnitKind.NOT_APPLICABLE
        assert definition.direct_source_required is True
        assert definition.provenance_requirement != (
            contract.ProvenanceRequirement.NOT_CANONICAL
        )
        assert definition.declared_status == contract.MetricContractStatus.SUPPORTED

    assert by_canonical["total_equity"].declared_status == (
        contract.MetricContractStatus.PERSISTED_ONLY
    )
    assert by_canonical["interest_expense"].declared_status == (
        contract.MetricContractStatus.PERSISTED_ONLY
    )
    assert by_canonical["total_debt"].declared_status == (
        contract.MetricContractStatus.INTERNAL_ONLY
    )


def test_financial_metric_contract_authorizes_only_appendix_5b_capex_sum() -> None:
    contract = _contract_module()
    authorized = [
        (definition.canonical_field, derivation)
        for definition in contract.METRIC_CONTRACT_FAMILIES
        for derivation in definition.authorized_derivations
    ]

    assert authorized == [
        (
            "capex",
            contract.AuthorizedDerivation.APPENDIX_5B_EXPLICIT_CAPEX_SUBITEM_SUM,
        )
    ]


def test_financial_metric_contract_owns_evaluation_only_aliases() -> None:
    contract = _contract_module()

    assert contract.METRIC_NAME_MAP == {
        "revenue": "revenue",
        "ebit": "ebit",
        "np_attributable": "np_attributable",
        "operating_cf": "operating_cf",
        "operating_cash_flow": "operating_cf",
        "investing_cf": "investing_cf",
        "financing_cf": "financing_cf",
        "capex": "capex",
        "cash_end": "cash_end",
        "net_debt": "net_debt",
        "shares_outstanding": "shares_outstanding",
    }
    assert contract.REAL_GOLD_METRIC_ALIASES == {
        "operating_cash_flow": "operating_cf"
    }
    assert contract.REVIEW_GOLD_METRIC_ALIASES == {
        "operating_cf": "operating_cash_flow",
        "operating_cash_flow": "operating_cf",
    }
    assert contract.EVALUATION_ALIASES_ARE_PRODUCTION_MATCH_RULES is False


def test_existing_callers_export_registry_compatibility_names() -> None:
    contract = _contract_module()
    from app.services import extraction_gold_eval
    from app.services import extraction_gold_eval_scorecard
    from app.services import extraction_review
    from app.services import multipass_extraction
    from app.services import pipeline

    assert multipass_extraction.METRIC_FIELDS == list(
        contract.CANONICAL_METRIC_FIELDS
    )
    assert extraction_gold_eval.REAL_GOLD_METRIC_ALIASES is (
        contract.REAL_GOLD_METRIC_ALIASES
    )
    assert extraction_review._GOLD_METRIC_ALIASES is (
        contract.REVIEW_GOLD_METRIC_ALIASES
    )
    assert extraction_gold_eval_scorecard.METRIC_NAME_MAP is contract.METRIC_NAME_MAP
    assert extraction_gold_eval_scorecard.PRODUCTION_RELEVANCE_TIERS is (
        contract.PRODUCTION_RELEVANCE_TIERS
    )
    assert extraction_gold_eval_scorecard.METRIC_CONTRACT_FAMILIES is (
        contract.METRIC_CONTRACT_FAMILIES
    )
    assert extraction_gold_eval_scorecard.MetricContractStatus is (
        contract.MetricContractStatus
    )
    assert extraction_gold_eval_scorecard.MetricContractFamily is (
        contract.MetricContractFamily
    )
    assert pipeline.PERSISTED_METRIC_COLUMNS is contract.PERSISTED_METRIC_COLUMNS


def test_metric_contract_parity_semantics_remain_unchanged(tmp_path: Path) -> None:
    from app.services.extraction_gold_eval_scorecard import (
        build_metric_contract_parity_matrix,
    )

    confirmed = tmp_path / "confirmed"
    real_gold = tmp_path / "real_gold"
    confirmed.mkdir()
    real_gold.mkdir()
    matrix = build_metric_contract_parity_matrix(
        confirmed_fixtures_dir=confirmed,
        real_gold_fixtures_dir=real_gold,
    )
    stable = {
        "artifact_type": matrix["artifact_type"],
        "metric_ontology_version": matrix["metric_ontology_version"],
        "summary": matrix["summary"],
        "policy_assertions": matrix["policy_assertions"],
        "metric_rows": matrix["metric_rows"],
        "promotion_policy": matrix["promotion_policy"],
    }
    digest = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    assert digest == "cc042df11e1743d9cf3085020991bd6dd8f73da835a7ece2efb48edf1c9f51ce"
