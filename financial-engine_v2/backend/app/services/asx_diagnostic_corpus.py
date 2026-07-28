"""Deterministic, fail-closed contract for the Ticket 02 ASX corpus.

The corpus is deliberately separate from classifier fixtures and production
extraction data. This module performs local filesystem and JSON validation only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from app.services.financial_metric_contract import (
    METRIC_CONTRACT_BY_CANONICAL_FIELD,
    MetricContractStatus,
    StatementContext,
)

SCHEMA_VERSION = 1
TICKET_02_BUCKETS = ("annual", "4E", "half-year", "4D", "quarterly", "4C")
# Backwards-compatible public name: these are coverage buckets, not document classes.
DOCUMENT_CLASSES = TICKET_02_BUCKETS
DOCUMENTS_PER_CLASS = 2
DOCUMENT_COUNT = len(TICKET_02_BUCKETS) * DOCUMENTS_PER_CLASS
# Exact values owned by extraction_gold_eval.ASXDocumentClass. Keeping this
# dependency value-based avoids importing the production extraction graph.
_DOCUMENT_CLASS_VALUES = frozenset({"annual", "half_year", "quarterly"})

_BUCKET_SEMANTICS = {
    "annual": ("annual", "annual_report", "A"),
    "4E": ("annual", "appendix_4e", "A"),
    "half-year": ("half_year", "half_year_report", "H"),
    "4D": ("half_year", "appendix_4d", "H"),
    "quarterly": ("quarterly", "appendix_5b", "Q"),
    "4C": ("quarterly", "appendix_4c", "Q"),
}
DOCUMENT_TYPES = frozenset(values[1] for values in _BUCKET_SEMANTICS.values())

_MANIFEST_KEYS = {"schema_version", "documents"}
_ENTRY_KEYS = {
    "document_id",
    "ticket_02_bucket",
    "document_class",
    "document_type",
    "source_path",
    "label_path",
    "source_sha256",
    "label_sha256",
}
_BUILD_ENTRY_KEYS = _ENTRY_KEYS - {"source_sha256", "label_sha256"}
_LABEL_KEYS = {
    "schema_version",
    "document_id",
    "ticket_02_bucket",
    "document_class",
    "document_type",
    "period_type",
    "period_end",
    "accounting_basis",
    "currency",
    "consolidation_scope",
    "accounting_standards",
    "supported_metrics",
    "provenance_expectations",
    "scan_image_status",
    "labeler_id",
    "independent_verification",
}
_PROVENANCE_KEYS = {"metric", "page_required", "statement_required"}
_SCAN_KEYS = {"kind", "has_text_layer", "has_page_images"}
_VERIFICATION_KEYS = {"verifier_id", "status", "verified_at"}
_PERIOD_TYPES = {"A", "H", "Q"}
_ACCOUNTING_BASES = {"statutory", "underlying"}
_STANDARDS = {"australian_accounting_standards", "ifrs"}
_SCOPES = {"consolidated", "standalone"}
_SCAN_KINDS = {"born_digital", "image_only", "mixed"}
_CASH_FLOW_DOCUMENT_TYPES = {"appendix_4c", "appendix_5b"}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_METRIC_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CorpusContractError(ValueError):
    """Raised when corpus construction inputs do not satisfy the contract."""


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the one canonical JSON representation used by this contract."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def sha256_file(path: Path) -> str:
    """Hash a file while translating field-scoped I/O errors at call sites."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(corpus_root: Path, documents: Iterable[Mapping[str, Any]]) -> bytes:
    """Build canonical manifest bytes and reject an invalid complete corpus."""

    root = _resolved_root(corpus_root)
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(documents):
        where = f"documents[{index}]"
        if not isinstance(raw, Mapping):
            raise CorpusContractError(f"{where}: expected object")
        _exact_keys(raw, _BUILD_ENTRY_KEYS, where)
        entry = dict(raw)
        for field in ("source_path", "label_path"):
            path = _safe_regular_file(root, entry[field], f"{where}.{field}")
            try:
                entry[field.removesuffix("_path") + "_sha256"] = sha256_file(path)
            except OSError as exc:
                raise CorpusContractError(
                    f"{where}.{field}: unavailable: {exc}"
                ) from exc
        entries.append(entry)

    manifest = {"schema_version": SCHEMA_VERSION, "documents": entries}
    errors = lint_manifest_data(root, manifest)
    if errors:
        raise CorpusContractError("\n".join(sorted(errors)))
    entries.sort(key=lambda item: item["document_id"])
    return canonical_json_bytes(manifest)


def lint_corpus(corpus_root: Path, manifest_path: Path) -> list[str]:
    """Lint an explicitly selected root and manifest; return sorted errors."""

    try:
        root = _resolved_root(corpus_root)
        manifest = _safe_regular_file(root, str(manifest_path), "manifest")
    except CorpusContractError as exc:
        return [str(exc)]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"manifest: invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return ["manifest: expected object"]
    return sorted(lint_manifest_data(root, data))


def lint_manifest_data(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Validate parsed manifest data and every referenced file and label."""

    errors: list[str] = []
    _collect_exact_keys(manifest, _MANIFEST_KEYS, "manifest", errors)
    _require_integer(manifest.get("schema_version"), "manifest.schema_version", errors)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"manifest.schema_version: expected {SCHEMA_VERSION}")

    documents = manifest.get("documents")
    if not isinstance(documents, list):
        errors.append("manifest.documents: expected array")
        return errors
    if len(documents) != DOCUMENT_COUNT:
        errors.append(f"manifest.documents: expected exactly {DOCUMENT_COUNT} entries")

    ids: list[str] = []
    buckets: list[str] = []
    lexical_paths: list[tuple[str, str]] = []
    resolved_paths: list[tuple[str, str]] = []
    file_ids: list[tuple[tuple[int, int], str]] = []
    for index, entry in enumerate(documents):
        where = f"manifest.documents[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected object")
            continue
        _collect_exact_keys(entry, _ENTRY_KEYS, where, errors)
        document_id = entry.get("document_id")
        if not _valid_id(document_id):
            errors.append(f"{where}.document_id: invalid stable identifier")
        else:
            ids.append(document_id)

        bucket = entry.get("ticket_02_bucket")
        document_class = entry.get("document_class")
        document_type = entry.get("document_type")
        if bucket not in TICKET_02_BUCKETS:
            errors.append(f"{where}.ticket_02_bucket: unsupported Ticket 02 bucket")
        else:
            buckets.append(bucket)
        if document_class not in _DOCUMENT_CLASS_VALUES:
            errors.append(
                f"{where}.document_class: unsupported canonical document class"
            )
        if document_type not in DOCUMENT_TYPES:
            errors.append(f"{where}.document_type: unsupported canonical document type")
        _check_bucket_semantics(bucket, document_class, document_type, where, errors)

        resolved: dict[str, Path] = {}
        for field in ("source_path", "label_path"):
            value = entry.get(field)
            if isinstance(value, str):
                lexical_paths.append((value, f"{where}.{field}"))
            try:
                path = _safe_regular_file(root, value, f"{where}.{field}")
                resolved[field] = path
                resolved_paths.append((os.fspath(path), f"{where}.{field}"))
                file_ids.append(
                    (_file_identity(path, f"{where}.{field}"), f"{where}.{field}")
                )
            except CorpusContractError as exc:
                errors.append(str(exc))

        for hash_field in ("source_sha256", "label_sha256"):
            value = entry.get(hash_field)
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                errors.append(f"{where}.{hash_field}: expected lowercase SHA-256")
                continue
            path_field = hash_field.removesuffix("_sha256") + "_path"
            if path_field in resolved:
                try:
                    actual = sha256_file(resolved[path_field])
                except OSError as exc:
                    errors.append(f"{where}.{path_field}: unavailable: {exc}")
                else:
                    if actual != value:
                        errors.append(f"{where}.{hash_field}: hash mismatch")

        if (label_path := resolved.get("label_path")) is not None:
            _lint_label(label_path, entry, where, errors)

    _duplicates(ids, "manifest.documents: duplicate document_id", errors)
    _path_duplicates(lexical_paths, "duplicate path spelling", errors)
    _path_duplicates(resolved_paths, "duplicate resolved path", errors)
    _file_identity_duplicates(file_ids, errors)
    counts = Counter(buckets)
    for bucket in TICKET_02_BUCKETS:
        if counts[bucket] != DOCUMENTS_PER_CLASS:
            errors.append(
                f"manifest.documents: Ticket 02 bucket {bucket!r} must have "
                f"exactly {DOCUMENTS_PER_CLASS} entries"
            )
    return errors


def _lint_label(
    path: Path,
    manifest_entry: Mapping[str, Any],
    manifest_where: str,
    errors: list[str],
) -> None:
    where = f"{manifest_where}.label"
    try:
        label = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{where}: invalid JSON: {exc}")
        return
    if not isinstance(label, dict):
        errors.append(f"{where}: expected object")
        return
    _collect_exact_keys(label, _LABEL_KEYS, where, errors)
    _require_integer(label.get("schema_version"), f"{where}.schema_version", errors)
    if label.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{where}.schema_version: expected {SCHEMA_VERSION}")
    for field in (
        "document_id",
        "ticket_02_bucket",
        "document_class",
        "document_type",
    ):
        if label.get(field) != manifest_entry.get(field):
            errors.append(f"{where}.{field}: does not match manifest")

    bucket = label.get("ticket_02_bucket")
    document_class = label.get("document_class")
    document_type = label.get("document_type")
    _check_bucket_semantics(bucket, document_class, document_type, where, errors)
    expected_period = (
        _BUCKET_SEMANTICS[bucket][2] if bucket in _BUCKET_SEMANTICS else None
    )
    period_type = label.get("period_type")
    if period_type not in _PERIOD_TYPES:
        errors.append(f"{where}.period_type: expected canonical A, H, or Q")
    elif expected_period is not None and period_type != expected_period:
        errors.append(f"{where}.period_type: inconsistent with document semantics")
    _iso_date(label.get("period_end"), f"{where}.period_end", errors)

    if label.get("accounting_basis") not in _ACCOUNTING_BASES:
        errors.append(f"{where}.accounting_basis: expected 'statutory' or 'underlying'")
    if not isinstance(label.get("currency"), str) or not _CURRENCY_RE.fullmatch(
        label.get("currency", "")
    ):
        errors.append(f"{where}.currency: expected ISO 4217 code")
    if label.get("consolidation_scope") not in _SCOPES:
        errors.append(f"{where}.consolidation_scope: unsupported scope")
    if label.get("accounting_standards") not in _STANDARDS:
        errors.append(f"{where}.accounting_standards: unsupported standards")

    metrics = label.get("supported_metrics")
    valid_metrics: list[str] = []
    if not isinstance(metrics, list) or not metrics:
        errors.append(f"{where}.supported_metrics: expected non-empty array")
    else:
        for index, metric in enumerate(metrics):
            metric_where = f"{where}.supported_metrics[{index}]"
            if not isinstance(metric, str) or not _METRIC_RE.fullmatch(metric):
                errors.append(f"{metric_where}: invalid metric")
                continue
            valid_metrics.append(metric)
            contract = METRIC_CONTRACT_BY_CANONICAL_FIELD.get(metric)
            if contract is None:
                errors.append(f"{metric_where}: not a canonical financial metric field")
            elif contract.declared_status != MetricContractStatus.SUPPORTED:
                errors.append(f"{metric_where}: metric is not canonically supported")
            elif (
                document_type in _CASH_FLOW_DOCUMENT_TYPES
                and StatementContext.CASH_FLOW_STATEMENT
                not in contract.statement_contexts
            ):
                errors.append(
                    f"{metric_where}: metric is not supported for {document_type}"
                )
        _duplicates(
            valid_metrics, f"{where}.supported_metrics: duplicate metric", errors
        )

    provenance = label.get("provenance_expectations")
    provenance_metrics: list[str] = []
    if not isinstance(provenance, list) or not provenance:
        errors.append(f"{where}.provenance_expectations: expected non-empty array")
    else:
        for index, item in enumerate(provenance):
            item_where = f"{where}.provenance_expectations[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_where}: expected object")
                continue
            _collect_exact_keys(item, _PROVENANCE_KEYS, item_where, errors)
            metric = item.get("metric")
            if not isinstance(metric, str) or not _METRIC_RE.fullmatch(metric):
                errors.append(f"{item_where}.metric: invalid metric")
            else:
                provenance_metrics.append(metric)
            for field in ("page_required", "statement_required"):
                if not isinstance(item.get(field), bool):
                    errors.append(f"{item_where}.{field}: expected boolean")
        _duplicates(
            provenance_metrics,
            f"{where}.provenance_expectations: duplicate metric",
            errors,
        )
        if sorted(provenance_metrics) != sorted(valid_metrics):
            errors.append(
                f"{where}.provenance_expectations: metrics must exactly match "
                "supported_metrics"
            )

    _lint_scan(label.get("scan_image_status"), where, errors)
    labeler = label.get("labeler_id")
    if not _valid_id(labeler):
        errors.append(f"{where}.labeler_id: invalid stable identifier")
    verification = label.get("independent_verification")
    if not isinstance(verification, dict):
        errors.append(f"{where}.independent_verification: expected object")
        return
    verification_where = f"{where}.independent_verification"
    _collect_exact_keys(verification, _VERIFICATION_KEYS, verification_where, errors)
    verifier = verification.get("verifier_id")
    if not _valid_id(verifier):
        errors.append(f"{verification_where}.verifier_id: invalid stable identifier")
    if _valid_id(labeler) and verifier == labeler:
        errors.append(f"{verification_where}.verifier_id: must differ from labeler_id")
    if verification.get("status") != "verified":
        errors.append(f"{verification_where}.status: expected 'verified'")
    timestamp = verification.get("verified_at")
    try:
        parsed = (
            datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else None
        )
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(
            f"{verification_where}.verified_at: "
            "expected timezone-aware ISO 8601 timestamp"
        )


def _lint_scan(value: Any, label_where: str, errors: list[str]) -> None:
    where = f"{label_where}.scan_image_status"
    if not isinstance(value, dict):
        errors.append(f"{where}: expected object")
        return
    _collect_exact_keys(value, _SCAN_KEYS, where, errors)
    kind = value.get("kind")
    text_layer = value.get("has_text_layer")
    page_images = value.get("has_page_images")
    if kind not in _SCAN_KINDS:
        errors.append(f"{where}.kind: unsupported status")
    for field, item in (
        ("has_text_layer", text_layer),
        ("has_page_images", page_images),
    ):
        if not isinstance(item, bool):
            errors.append(f"{where}.{field}: expected boolean")
    expected = {
        "born_digital": (True, False),
        "image_only": (False, True),
        "mixed": (True, True),
    }.get(kind)
    if expected is not None and (text_layer, page_images) != expected:
        errors.append(f"{where}: inconsistent {kind} status")


def _check_bucket_semantics(
    bucket: Any,
    document_class: Any,
    document_type: Any,
    where: str,
    errors: list[str],
) -> None:
    expected = _BUCKET_SEMANTICS.get(bucket)
    if expected is not None and (document_class, document_type) != expected[:2]:
        errors.append(
            f"{where}: document class/type combination is inconsistent with "
            f"Ticket 02 bucket {bucket!r}"
        )


def _resolved_root(root: Path) -> Path:
    try:
        root_path = root if isinstance(root, Path) else Path(root)
        resolved = root_path.resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise CorpusContractError(f"corpus root: unavailable: {exc}") from exc
    if not resolved.is_dir():
        raise CorpusContractError("corpus root: expected directory")
    return resolved


def _safe_regular_file(root: Path, value: Any, where: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CorpusContractError(f"{where}: expected non-empty relative POSIX path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or "\\" in value
        or value != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise CorpusContractError(f"{where}: non-canonical or unsafe relative path")
    candidate = root.joinpath(*pure.parts)
    current = root
    try:
        for part in pure.parts:
            current = current / part
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise CorpusContractError(
                    f"{where}: symlinks are not allowed in any path component"
                )
        resolved = candidate.resolve(strict=True)
    except CorpusContractError:
        raise
    except OSError as exc:
        raise CorpusContractError(f"{where}: unavailable: {exc}") from exc
    if not resolved.is_relative_to(root):
        raise CorpusContractError(f"{where}: path escapes corpus root")
    try:
        if not stat.S_ISREG(candidate.lstat().st_mode):
            raise CorpusContractError(f"{where}: expected regular file")
    except OSError as exc:
        raise CorpusContractError(f"{where}: unavailable: {exc}") from exc
    return resolved


def _file_identity(path: Path, where: str) -> tuple[int, int]:
    try:
        info = path.stat()
    except OSError as exc:
        raise CorpusContractError(f"{where}: unavailable: {exc}") from exc
    return info.st_dev, info.st_ino


def _collect_exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    where: str,
    errors: list[str],
) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        errors.append(f"{where}: missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{where}: unknown fields: {', '.join(unknown)}")


def _exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    errors: list[str] = []
    _collect_exact_keys(value, expected, where, errors)
    if errors:
        raise CorpusContractError("\n".join(errors))


def _require_integer(value: Any, where: str, errors: list[str]) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{where}: expected integer")


def _iso_date(value: Any, where: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{where}: expected source-bound ISO date")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{where}: expected source-bound ISO date")
        return None


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and _ID_RE.fullmatch(value) is not None


def _duplicates(values: Sequence[str], message: str, errors: list[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        errors.append(f"{message}: {', '.join(duplicates)}")


def _path_duplicates(
    values: Sequence[tuple[str, str]], message: str, errors: list[str]
) -> None:
    grouped: dict[str, list[str]] = {}
    for value, where in values:
        grouped.setdefault(value, []).append(where)
    for value in sorted(grouped):
        if len(grouped[value]) > 1:
            errors.append(
                f"manifest.documents: {message} {value!r}: {', '.join(grouped[value])}"
            )


def _file_identity_duplicates(
    values: Sequence[tuple[tuple[int, int], str]], errors: list[str]
) -> None:
    grouped: dict[tuple[int, int], list[str]] = {}
    for identity, where in values:
        grouped.setdefault(identity, []).append(where)
    for identity in sorted(grouped):
        if len(grouped[identity]) > 1:
            errors.append(
                "manifest.documents: duplicate file identity "
                f"{identity[0]}:{identity[1]}: {', '.join(grouped[identity])}"
            )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint an ASX diagnostic corpus")
    parser.add_argument("--corpus-root", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="manifest path relative to --corpus-root",
    )
    args = parser.parse_args(argv)
    errors = lint_corpus(args.corpus_root, args.manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: valid {DOCUMENT_COUNT}-document ASX diagnostic corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
