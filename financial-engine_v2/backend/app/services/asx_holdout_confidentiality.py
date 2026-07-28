"""Fail-closed confidentiality boundary for the Ticket 03 holdout corpus."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Generic, TypeVar

from app.services.asx_diagnostic_corpus import TICKET_02_BUCKETS

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_T = TypeVar("_T")


class ConfidentialityError(ValueError):
    """Raised when data crosses the wrong corpus access boundary."""


class ProtectedAccessMode(str, Enum):
    DEVELOPMENT = "development"
    PROTECTED = "protected"


class CorpusClassification(str, Enum):
    """Classification used by evaluation output boundaries."""

    NON_HOLDOUT = "non_holdout"
    HOLDOUT = "holdout"


class ProtectedAccess(Generic[_T]):
    """Container whose contents require an explicit protected access mode."""

    def __init__(self, entries: tuple[_T, ...]) -> None:
        self._entries = tuple(entries)

    def entries(self, mode: ProtectedAccessMode) -> tuple[_T, ...]:
        if mode is not ProtectedAccessMode.PROTECTED:
            raise ConfidentialityError("protected corpus access mode required")
        return self._entries


@dataclass(frozen=True)
class DevelopmentAggregateResult:
    """The complete allowlist for a development/public corpus response."""

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

    ALLOWED_FIELDS = frozenset(
        {
            "corpus_version",
            "corpus_digest",
            "document_count",
            "partition_counts",
            "bucket_counts",
            "company_count",
            "sector_count",
            "scan_image_heavy_count",
            "non_aud_count",
            "issuer_size_counts",
        }
    )
    _COUNT_FIELDS = frozenset(
        {
            "document_count",
            "company_count",
            "sector_count",
            "scan_image_heavy_count",
            "non_aud_count",
        }
    )
    _MAPPING_FIELDS = frozenset(
        {"partition_counts", "bucket_counts", "issuer_size_counts"}
    )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DevelopmentAggregateResult:
        if not isinstance(payload, Mapping):
            raise ConfidentialityError("development result must be an object")
        if set(payload) != cls.ALLOWED_FIELDS:
            raise ConfidentialityError(
                "development result violates aggregate allowlist"
            )
        version = payload["corpus_version"]
        digest = payload["corpus_digest"]
        if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
            raise ConfidentialityError("corpus_version must be an opaque identifier")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ConfidentialityError("corpus_digest must be a SHA-256 digest")
        for field in cls._COUNT_FIELDS:
            _require_count(payload[field], field)
        counts = {
            field: _aggregate_counts(payload[field], field)
            for field in cls._MAPPING_FIELDS
        }
        if set(counts["partition_counts"]) != {"diagnostic", "holdout"}:
            raise ConfidentialityError("partition_counts violates aggregate allowlist")
        if set(counts["bucket_counts"]) != set(TICKET_02_BUCKETS):
            raise ConfidentialityError("bucket_counts violates aggregate allowlist")
        if set(counts["issuer_size_counts"]) != {"large", "small"}:
            raise ConfidentialityError(
                "issuer_size_counts violates aggregate allowlist"
            )
        if payload["document_count"] != 48:
            raise ConfidentialityError("document_count must be 48")
        if counts["partition_counts"] != {"diagnostic": 12, "holdout": 36}:
            raise ConfidentialityError(
                "partition_counts must be diagnostic 12 and holdout 36"
            )
        if any(count != 8 for count in counts["bucket_counts"].values()):
            raise ConfidentialityError("bucket_counts must contain eight per bucket")
        if sum(counts["issuer_size_counts"].values()) != payload["document_count"]:
            raise ConfidentialityError("issuer_size_counts must sum to document_count")
        if payload["company_count"] < 12:
            raise ConfidentialityError("company_count must be at least 12")
        if payload["sector_count"] < 6:
            raise ConfidentialityError("sector_count must be at least 6")
        if payload["scan_image_heavy_count"] < 6:
            raise ConfidentialityError("scan_image_heavy_count must be at least 6")
        if payload["non_aud_count"] < 1:
            raise ConfidentialityError("non_aud_count must be at least 1")
        for field in (
            "company_count",
            "sector_count",
            "scan_image_heavy_count",
            "non_aud_count",
        ):
            if payload[field] > payload["document_count"]:
                raise ConfidentialityError(f"{field} cannot exceed document_count")
        return cls(
            corpus_version=version,
            corpus_digest=digest,
            document_count=payload["document_count"],
            partition_counts=counts["partition_counts"],
            bucket_counts=counts["bucket_counts"],
            company_count=payload["company_count"],
            sector_count=payload["sector_count"],
            scan_image_heavy_count=payload["scan_image_heavy_count"],
            non_aud_count=payload["non_aud_count"],
            issuer_size_counts=counts["issuer_size_counts"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus_version": self.corpus_version,
            "corpus_digest": self.corpus_digest,
            "document_count": self.document_count,
            "partition_counts": dict(self.partition_counts),
            "bucket_counts": dict(self.bucket_counts),
            "company_count": self.company_count,
            "sector_count": self.sector_count,
            "scan_image_heavy_count": self.scan_image_heavy_count,
            "non_aud_count": self.non_aud_count,
            "issuer_size_counts": dict(self.issuer_size_counts),
        }


def serialize_evaluation_output(
    payload: Mapping[str, Any],
    *,
    corpus_classification: CorpusClassification | str | None,
    access_mode: ProtectedAccessMode | str | None,
    development_aggregate: DevelopmentAggregateResult | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the single fail-closed boundary for evaluator and report outputs.

    Non-holdout callers retain their legacy payload.  A holdout payload is
    detailed only when protected mode is explicitly supplied; every other
    mode, including omitted or unknown values, is reduced to the authoritative
    development aggregate.
    """

    try:
        classification = CorpusClassification(corpus_classification)
    except (TypeError, ValueError):
        if corpus_classification is None:
            return dict(payload)
        raise ConfidentialityError("unknown corpus classification") from None

    if classification is CorpusClassification.NON_HOLDOUT:
        return dict(payload)

    try:
        mode = ProtectedAccessMode(access_mode)
    except (TypeError, ValueError):
        mode = ProtectedAccessMode.DEVELOPMENT
    if mode is ProtectedAccessMode.PROTECTED:
        return dict(payload)

    if development_aggregate is None:
        raise ConfidentialityError(
            "holdout development aggregate required for non-protected output"
        )
    aggregate = (
        development_aggregate
        if isinstance(development_aggregate, DevelopmentAggregateResult)
        else DevelopmentAggregateResult.from_mapping(development_aggregate)
    )
    result = aggregate.to_dict()
    if set(result) != DevelopmentAggregateResult.ALLOWED_FIELDS:
        raise ConfidentialityError("development result violates aggregate allowlist")
    return result


def _require_count(value: Any, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfidentialityError(f"{field} must be a non-negative integer")


def _aggregate_counts(value: Any, field: str) -> Mapping[str, int]:
    if not isinstance(value, Mapping):
        raise ConfidentialityError(f"{field} must be an aggregate count object")
    result: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not key:
            raise ConfidentialityError(f"{field} keys must be strings")
        _require_count(count, f"{field}.{key}")
        result[key] = count
    return MappingProxyType(result)
