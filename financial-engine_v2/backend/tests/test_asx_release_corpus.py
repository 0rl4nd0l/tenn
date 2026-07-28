from __future__ import annotations

from dataclasses import replace

import pytest
from app.services.asx_diagnostic_corpus import TICKET_02_BUCKETS
from app.services.asx_release_corpus import (
    CorpusValidationError,
    ProtectedCorpusEntry,
    ReviewMetadata,
    validate_release_corpus,
)

TYPE_BY_BUCKET = {
    "annual": "annual_report",
    "4E": "appendix_4e",
    "half-year": "half_year_report",
    "4D": "appendix_4d",
    "quarterly": "appendix_5b",
    "4C": "appendix_4c",
}


def valid_entries() -> list[ProtectedCorpusEntry]:
    entries = []
    for index in range(48):
        bucket = TICKET_02_BUCKETS[index % 6]
        entries.append(
            ProtectedCorpusEntry(
                document_id=f"synthetic-{index:02d}",
                issuer_id=f"issuer-{index % 12:02d}",
                sector=(
                    "energy",
                    "materials",
                    "industrials",
                    "financials",
                    "health",
                    "tech",
                )[index % 6],
                issuer_size="large" if index % 2 == 0 else "small",
                currency="NZD" if index == 0 else "AUD",
                ticket_02_bucket=bucket,
                document_type=TYPE_BY_BUCKET[bucket],
                scan_image_heavy=index < 6,
                source_sha256=f"{index + 1:064x}",
                label_sha256=f"{index + 101:064x}",
                review=ReviewMetadata(
                    reviewer_id=f"reviewer-{index % 2}",
                    reviewed_at="2026-07-01T00:00:00Z",
                    decision="approved",
                    review_version=1,
                ),
                partition="diagnostic" if index < 12 else "holdout",
            )
        )
    return entries


def test_valid_release_corpus_returns_only_aggregate_summary() -> None:
    summary = validate_release_corpus(valid_entries(), corpus_version="ticket-03-v1")

    assert summary.document_count == 48
    assert summary.partition_counts == {"diagnostic": 12, "holdout": 36}
    assert summary.bucket_counts == {bucket: 8 for bucket in TICKET_02_BUCKETS}
    assert summary.company_count == 12
    assert summary.sector_count == 6
    assert len(summary.corpus_digest) == 64
    assert "synthetic-" not in repr(summary)


def test_release_corpus_rejects_partition_counts_skewed_across_buckets() -> None:
    entries = valid_entries()
    annual_holdout = next(
        index
        for index, row in enumerate(entries)
        if row.ticket_02_bucket == "annual" and row.partition == "holdout"
    )
    half_year_diagnostic = next(
        index
        for index, row in enumerate(entries)
        if row.ticket_02_bucket == "half-year" and row.partition == "diagnostic"
    )
    entries[annual_holdout] = replace(entries[annual_holdout], partition="diagnostic")
    entries[half_year_diagnostic] = replace(
        entries[half_year_diagnostic], partition="holdout"
    )

    with pytest.raises(CorpusValidationError, match="per-class partition"):
        validate_release_corpus(entries, corpus_version="ticket-03-v1")


def test_release_corpus_allows_more_than_six_sectors() -> None:
    entries = valid_entries()
    entries[0] = replace(entries[0], sector="consumer")

    summary = validate_release_corpus(entries, corpus_version="ticket-03-v1")

    assert summary.sector_count == 7


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda rows: rows[:-1], "exactly 48"),
        (
            lambda rows: [replace(row, partition="holdout") for row in rows],
            "diagnostic",
        ),
        (
            lambda rows: [
                replace(row, ticket_02_bucket="annual", document_type="annual_report")
                if row.ticket_02_bucket == "4E"
                else row
                for row in rows
            ],
            "bucket",
        ),
        (
            lambda rows: [replace(row, issuer_id="one-issuer") for row in rows],
            "companies",
        ),
        (
            lambda rows: [replace(row, sector="energy") for row in rows],
            "sectors",
        ),
        (
            lambda rows: [replace(row, issuer_size="large") for row in rows],
            "issuer sizes",
        ),
        (
            lambda rows: [replace(row, currency="AUD") for row in rows],
            "non-AUD",
        ),
        (
            lambda rows: [replace(row, scan_image_heavy=False) for row in rows],
            "scan/image-heavy",
        ),
    ],
)
def test_release_boundaries_fail_closed(mutation, message: str) -> None:
    with pytest.raises(CorpusValidationError, match=message):
        validate_release_corpus(mutation(valid_entries()), corpus_version="v1")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows[:-1] + [replace(rows[-1], document_id=rows[0].document_id)],
        lambda rows: (
            rows[:-1] + [replace(rows[-1], source_sha256=rows[0].source_sha256)]
        ),
        lambda rows: rows[:-1] + [replace(rows[-1], label_sha256="BAD")],
        lambda rows: rows[:-1] + [replace(rows[-1], review=None)],
        lambda rows: (
            rows[:-1]
            + [
                replace(
                    rows[-1],
                    review=replace(rows[-1].review, reviewed_at="2026-02-30T00:00:00Z"),
                )
            ]
        ),
        lambda rows: (
            rows[:-1]
            + [replace(rows[-1], review=replace(rows[-1].review, decision="pending"))]
        ),
        lambda rows: rows[:-1] + [replace(rows[-1], document_type="appendix_4e")],
    ],
)
def test_duplicate_hash_review_and_consistency_fail_closed(mutation) -> None:
    with pytest.raises(CorpusValidationError):
        validate_release_corpus(mutation(valid_entries()), corpus_version="v1")


def test_invalid_entry_type_uses_the_corpus_validation_boundary() -> None:
    entries = valid_entries()
    entries[-1] = object()

    with pytest.raises(CorpusValidationError, match="ProtectedCorpusEntry"):
        validate_release_corpus(entries, corpus_version="v1")


def test_digest_is_deterministic_and_binds_protected_metadata() -> None:
    entries = valid_entries()
    first = validate_release_corpus(entries, corpus_version="v1")
    reordered = validate_release_corpus(list(reversed(entries)), corpus_version="v1")
    changed = validate_release_corpus(
        [replace(entries[0], label_sha256=f"{999:064x}"), *entries[1:]],
        corpus_version="v1",
    )

    assert first.corpus_digest == reordered.corpus_digest
    assert first.corpus_digest != changed.corpus_digest
