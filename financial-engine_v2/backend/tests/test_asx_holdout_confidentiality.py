from __future__ import annotations

import pytest
from app.services.asx_holdout_confidentiality import (
    ConfidentialityError,
    CorpusClassification,
    DevelopmentAggregateResult,
    ProtectedAccess,
    ProtectedAccessMode,
    serialize_evaluation_output,
)


def test_development_result_has_an_allowlisted_aggregate_schema() -> None:
    result = DevelopmentAggregateResult.from_mapping(
        {
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
    )

    payload = result.to_dict()
    assert payload["document_count"] == 48
    assert set(payload) == DevelopmentAggregateResult.ALLOWED_FIELDS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("document_count", 47),
        ("partition_counts", {"diagnostic": 11, "holdout": 37}),
        (
            "bucket_counts",
            {
                "annual": 7,
                "4E": 9,
                "half-year": 8,
                "4D": 8,
                "quarterly": 8,
                "4C": 8,
            },
        ),
        ("company_count", 11),
        ("sector_count", 5),
        ("scan_image_heavy_count", 5),
        ("non_aud_count", 0),
        ("company_count", 49),
        ("sector_count", 49),
        ("scan_image_heavy_count", 49),
        ("non_aud_count", 49),
        ("issuer_size_counts", {"large": 23, "small": 24}),
    ],
)
def test_development_result_rejects_inconsistent_aggregates(field, value) -> None:
    payload = valid_aggregate_payload()
    payload[field] = value

    with pytest.raises(ConfidentialityError):
        DevelopmentAggregateResult.from_mapping(payload)


@pytest.mark.parametrize(
    "extra",
    [
        {"document_ids": ["secret"]},
        {"ticker": "SYN"},
        {"details": {"filename": "secret.pdf"}},
        {"errors": [{"document_id": "secret", "message": "bad"}]},
        {"scores": {"secret": 0.99}},
        {"bucket_counts": {"annual": {"count": 8, "paths": ["/protected"]}}},
    ],
)
def test_development_result_rejects_nested_and_adversarial_disclosure(extra) -> None:
    payload = valid_aggregate_payload()
    payload.update(extra)

    with pytest.raises(ConfidentialityError):
        DevelopmentAggregateResult.from_mapping(payload)


def valid_aggregate_payload() -> dict:
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


def test_protected_entries_require_explicit_protected_mode() -> None:
    access = ProtectedAccess(("protected-entry",))

    with pytest.raises(ConfidentialityError):
        access.entries(ProtectedAccessMode.DEVELOPMENT)
    assert access.entries(ProtectedAccessMode.PROTECTED) == ("protected-entry",)


@pytest.mark.parametrize("mode", [None, "unknown", ProtectedAccessMode.DEVELOPMENT])
def test_holdout_output_fails_closed_to_exact_aggregate(mode) -> None:
    payload = serialize_evaluation_output(
        {"documents": [{"document_id": "secret", "expected": 1, "actual": 2}]},
        corpus_classification=CorpusClassification.HOLDOUT,
        access_mode=mode,
        development_aggregate=valid_aggregate_payload(),
    )

    assert payload == valid_aggregate_payload()
    assert set(payload) == DevelopmentAggregateResult.ALLOWED_FIELDS


def test_holdout_detail_requires_explicit_protected_mode() -> None:
    detailed = {"documents": [{"document_id": "secret"}]}

    assert (
        serialize_evaluation_output(
            detailed,
            corpus_classification="holdout",
            access_mode=ProtectedAccessMode.PROTECTED,
        )
        == detailed
    )


def test_non_holdout_output_remains_compatible() -> None:
    detailed = {"fixture_summaries": [{"document_id": "synthetic"}]}

    assert (
        serialize_evaluation_output(
            detailed,
            corpus_classification=CorpusClassification.NON_HOLDOUT,
            access_mode=ProtectedAccessMode.DEVELOPMENT,
        )
        == detailed
    )


@pytest.mark.parametrize(
    ("classification", "mode"),
    [
        (None, ProtectedAccessMode.PROTECTED),
        (CorpusClassification.NON_HOLDOUT, None),
    ],
)
def test_output_requires_explicit_classification_and_non_holdout_mode(
    classification, mode
) -> None:
    with pytest.raises(ConfidentialityError):
        serialize_evaluation_output(
            {"documents": [{"document_id": "must-not-escape"}]},
            corpus_classification=classification,
            access_mode=mode,
        )
