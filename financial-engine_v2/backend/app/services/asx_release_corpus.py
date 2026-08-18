"""Pure metadata contract for the combined Ticket 03 ASX release corpus."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from types import MappingProxyType

from app.services.asx_diagnostic_corpus import DOCUMENT_TYPES, TICKET_02_BUCKETS
from app.services.asx_holdout_confidentiality import DevelopmentAggregateResult

DOCUMENT_COUNT = 48
DIAGNOSTIC_COUNT = 12
HOLDOUT_COUNT = 36
DOCUMENTS_PER_BUCKET = 8
DIAGNOSTIC_PER_BUCKET = 2
HOLDOUT_PER_BUCKET = 6
MIN_COMPANIES = 12
REQUIRED_SECTORS = 6
MIN_SCAN_IMAGE_HEAVY = 6

_TYPE_BY_BUCKET = {
    "annual": "annual_report",
    "4E": "appendix_4e",
    "half-year": "half_year_report",
    "4D": "appendix_4d",
    "quarterly": "appendix_5b",
    "4C": "appendix_4c",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SECTOR_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_REVIEWED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class CorpusValidationError(ValueError):
    """Raised when protected corpus metadata fails any Ticket 03 invariant."""


@dataclass(frozen=True)
class ReviewMetadata:
    reviewer_id: str
    reviewed_at: str
    decision: str
    review_version: int


@dataclass(frozen=True)
class ProtectedCorpusEntry:
    document_id: str
    issuer_id: str
    sector: str
    issuer_size: str
    currency: str
    ticket_02_bucket: str
    document_type: str
    scan_image_heavy: bool
    source_sha256: str
    label_sha256: str
    review: ReviewMetadata | None
    partition: str


@dataclass(frozen=True)
class ReleaseCorpusSummary:
    corpus_version: str
    corpus_digest: str
    document_count: int
    partition_counts: Mapping[str, int]
    bucket_counts: Mapping[str, int]
    company_count: int
    sector_count: int
    scan_image_heavy_count: int
    non_aud_count: int
    issuer_size_counts: Mapping[str, int]

    def development_result(self) -> DevelopmentAggregateResult:
        return DevelopmentAggregateResult.from_mapping(
            {
                "corpus_version": self.corpus_version,
                "corpus_digest": self.corpus_digest,
                "document_count": self.document_count,
                "partition_counts": self.partition_counts,
                "bucket_counts": self.bucket_counts,
                "company_count": self.company_count,
                "sector_count": self.sector_count,
                "scan_image_heavy_count": self.scan_image_heavy_count,
                "non_aud_count": self.non_aud_count,
                "issuer_size_counts": self.issuer_size_counts,
            }
        )


def validate_release_corpus(
    entries: Iterable[ProtectedCorpusEntry], *, corpus_version: str
) -> ReleaseCorpusSummary:
    """Validate protected metadata and return an aggregate-only summary."""

    rows: tuple[ProtectedCorpusEntry, ...] = tuple(entries)
    errors: list[str] = []
    if len(rows) != DOCUMENT_COUNT:
        errors.append(
            f"combined corpus must contain exactly {DOCUMENT_COUNT} documents"
        )
    if not isinstance(corpus_version, str) or not _ID_RE.fullmatch(corpus_version):
        errors.append("corpus version must be a non-empty opaque identifier")

    valid_rows: list[ProtectedCorpusEntry] = []
    ids: list[str] = []
    source_hashes: list[str] = []
    label_hashes: list[str] = []
    for index, row in enumerate(rows):
        where = f"entries[{index}]"
        if not isinstance(row, ProtectedCorpusEntry):
            errors.append(f"{where}: expected ProtectedCorpusEntry")
            continue
        valid_rows.append(row)
        _validate_entry(row, where, errors)
        ids.append(row.document_id)
        source_hashes.append(row.source_sha256)
        label_hashes.append(row.label_sha256)

    _reject_duplicates(ids, "document IDs", errors)
    _reject_duplicates(source_hashes, "source SHA-256 hashes", errors)
    _reject_duplicates(label_hashes, "label SHA-256 hashes", errors)

    partitions = Counter(row.partition for row in valid_rows)
    buckets = Counter(row.ticket_02_bucket for row in valid_rows)
    bucket_partitions = Counter(
        (row.ticket_02_bucket, row.partition) for row in valid_rows
    )
    sizes = Counter(row.issuer_size for row in valid_rows)
    if partitions != {"diagnostic": DIAGNOSTIC_COUNT, "holdout": HOLDOUT_COUNT}:
        errors.append("partition counts must be diagnostic 12 and holdout 36")
    for bucket in TICKET_02_BUCKETS:
        if buckets[bucket] != DOCUMENTS_PER_BUCKET:
            errors.append(f"bucket {bucket!r} must contain exactly 8 documents")
        if (
            bucket_partitions[(bucket, "diagnostic")] != DIAGNOSTIC_PER_BUCKET
            or bucket_partitions[(bucket, "holdout")] != HOLDOUT_PER_BUCKET
        ):
            errors.append(
                f"bucket {bucket!r} violates per-class partition counts: "
                "expected diagnostic 2 and holdout 6"
            )
    companies = {row.issuer_id for row in valid_rows}
    sectors = {row.sector for row in valid_rows}
    if len(companies) < MIN_COMPANIES:
        errors.append("corpus must contain at least 12 distinct companies")
    if len(sectors) < REQUIRED_SECTORS:
        errors.append("corpus must contain at least six normalized sectors")
    if not {"large", "small"}.issubset(sizes):
        errors.append("corpus must include both large and small issuer sizes")
    non_aud_count = sum(row.currency != "AUD" for row in valid_rows)
    if non_aud_count < 1:
        errors.append("corpus must include at least one non-AUD document")
    scan_count = sum(row.scan_image_heavy is True for row in valid_rows)
    if scan_count < MIN_SCAN_IMAGE_HEAVY:
        errors.append("corpus must include at least six scan/image-heavy documents")
    if errors:
        raise CorpusValidationError("; ".join(sorted(set(errors))))

    digest_payload = [
        asdict(row) for row in sorted(valid_rows, key=lambda item: item.document_id)
    ]
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ReleaseCorpusSummary(
        corpus_version=corpus_version,
        corpus_digest=digest,
        document_count=len(valid_rows),
        partition_counts=MappingProxyType(dict(partitions)),
        bucket_counts=MappingProxyType(
            {bucket: buckets[bucket] for bucket in TICKET_02_BUCKETS}
        ),
        company_count=len(companies),
        sector_count=len(sectors),
        scan_image_heavy_count=scan_count,
        non_aud_count=non_aud_count,
        issuer_size_counts=MappingProxyType(dict(sizes)),
    )


def _validate_entry(row: ProtectedCorpusEntry, where: str, errors: list[str]) -> None:
    for field in ("document_id", "issuer_id"):
        value = getattr(row, field)
        if not isinstance(value, str) or not _ID_RE.fullmatch(value):
            errors.append(f"{where}.{field}: invalid identifier")
    if not isinstance(row.sector, str) or not _SECTOR_RE.fullmatch(row.sector):
        errors.append(f"{where}.sector: expected normalized sector")
    if row.issuer_size not in {"large", "small"}:
        errors.append(f"{where}.issuer_size: unsupported issuer size")
    if not isinstance(row.currency, str) or not _CURRENCY_RE.fullmatch(row.currency):
        errors.append(f"{where}.currency: expected ISO 4217 code")
    if row.ticket_02_bucket not in TICKET_02_BUCKETS:
        errors.append(f"{where}.ticket_02_bucket: unsupported Ticket 02 bucket")
    if row.document_type not in DOCUMENT_TYPES:
        errors.append(f"{where}.document_type: unsupported canonical document type")
    if _TYPE_BY_BUCKET.get(row.ticket_02_bucket) != row.document_type:
        errors.append(f"{where}: inconsistent bucket and document type")
    if type(row.scan_image_heavy) is not bool:
        errors.append(f"{where}.scan_image_heavy: expected boolean")
    for field in ("source_sha256", "label_sha256"):
        value = getattr(row, field)
        if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
            errors.append(f"{where}.{field}: expected lowercase SHA-256")
    if row.partition not in {"diagnostic", "holdout"}:
        errors.append(f"{where}.partition: unsupported partition")
    review = row.review
    if not isinstance(review, ReviewMetadata):
        errors.append(f"{where}.review: immutable review metadata required")
    elif (
        not isinstance(review.reviewer_id, str)
        or not _ID_RE.fullmatch(review.reviewer_id)
        or not _valid_reviewed_at(review.reviewed_at)
        or review.decision != "approved"
        or isinstance(review.review_version, bool)
        or not isinstance(review.review_version, int)
        or review.review_version < 1
    ):
        errors.append(f"{where}.review: incomplete or unapproved review metadata")


def _valid_reviewed_at(value: object) -> bool:
    if not isinstance(value, str) or not _REVIEWED_AT_RE.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc


def _reject_duplicates(values: list[str], label: str, errors: list[str]) -> None:
    if len(values) != len(set(values)):
        errors.append(f"duplicate {label}")
