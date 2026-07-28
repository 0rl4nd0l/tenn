"""Contract, deterministic manifest builder, and linter for the ASX corpus.

The diagnostic corpus is deliberately separate from classifier fixtures and
production extraction data.  This module performs local filesystem and JSON
validation only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
DOCUMENT_CLASSES = ("annual", "4E", "half-year", "4D", "quarterly", "4C")
DOCUMENTS_PER_CLASS = 2
DOCUMENT_COUNT = len(DOCUMENT_CLASSES) * DOCUMENTS_PER_CLASS

_MANIFEST_KEYS = {"schema_version", "documents"}
_ENTRY_KEYS = {
    "document_id",
    "document_class",
    "source_path",
    "label_path",
    "source_sha256",
    "label_sha256",
}
_LABEL_KEYS = {
    "schema_version",
    "document_id",
    "document_class",
    "period_basis",
    "accounting_basis",
    "supported_metrics",
    "provenance_expectations",
    "scan_image_status",
    "independent_verification",
}
_PERIOD_KEYS = {"basis", "start_date", "end_date"}
_ACCOUNTING_KEYS = {"standards", "scope", "currency"}
_PROVENANCE_KEYS = {"metric", "page_required", "statement_required"}
_SCAN_KEYS = {"kind", "has_text_layer", "has_page_images"}
_VERIFICATION_KEYS = {"reviewer_id", "status", "verified_at"}
_PERIOD_BASES = {"full_year", "half_year", "quarter"}
_CLASS_PERIODS = {
    "annual": "full_year",
    "4E": "full_year",
    "half-year": "half_year",
    "4D": "half_year",
    "quarterly": "quarter",
    "4C": "quarter",
}
_STANDARDS = {"australian_accounting_standards", "ifrs"}
_SCOPES = {"consolidated", "standalone"}
_SCAN_KINDS = {"born_digital", "image_only", "mixed"}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_METRIC_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CorpusContractError(ValueError):
    """Raised when corpus construction inputs do not satisfy the contract."""


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the one canonical JSON representation used by this contract."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(corpus_root: Path, documents: Iterable[Mapping[str, Any]]) -> bytes:
    """Build canonical manifest bytes, hashing source and label files.

    Each input item must contain exactly document identity, class, and paths.
    The returned bytes are independent of input order.  Full corpus validation
    is intentionally performed so invalid manifests cannot be built.
    """

    root = _resolved_root(corpus_root)
    entries: list[dict[str, Any]] = []
    input_keys = {"document_id", "document_class", "source_path", "label_path"}
    for index, raw in enumerate(documents):
        if not isinstance(raw, Mapping):
            raise CorpusContractError(f"documents[{index}]: expected object")
        _exact_keys(raw, input_keys, f"documents[{index}]")
        entry = dict(raw)
        source = _safe_regular_file(
            root, entry["source_path"], f"documents[{index}].source_path"
        )
        label = _safe_regular_file(
            root, entry["label_path"], f"documents[{index}].label_path"
        )
        entry["source_sha256"] = sha256_file(source)
        entry["label_sha256"] = sha256_file(label)
        entries.append(entry)

    manifest = {"schema_version": SCHEMA_VERSION, "documents": entries}
    errors = lint_manifest_data(root, manifest)
    if errors:
        raise CorpusContractError("\n".join(errors))
    entries.sort(key=lambda item: item["document_id"])
    return canonical_json_bytes(manifest)


def lint_corpus(corpus_root: Path, manifest_path: Path) -> list[str]:
    """Lint an explicitly selected root and manifest; return sorted errors."""

    errors: list[str] = []
    try:
        root = _resolved_root(corpus_root)
    except CorpusContractError as exc:
        return [str(exc)]

    try:
        manifest = _safe_regular_file(root, str(manifest_path), "manifest")
    except CorpusContractError as exc:
        return [str(exc)]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"manifest: invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return ["manifest: expected object"]
    errors.extend(lint_manifest_data(root, data))
    return sorted(errors)


def lint_manifest_data(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Validate parsed manifest data and all referenced labels and files."""

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
    sources: list[str] = []
    labels: list[str] = []
    classes: list[str] = []
    for index, entry in enumerate(documents):
        where = f"manifest.documents[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected object")
            continue
        _collect_exact_keys(entry, _ENTRY_KEYS, where, errors)
        document_id = entry.get("document_id")
        document_class = entry.get("document_class")
        if not isinstance(document_id, str) or not _ID_RE.fullmatch(document_id):
            errors.append(f"{where}.document_id: invalid stable identifier")
        else:
            ids.append(document_id)
        if document_class not in DOCUMENT_CLASSES:
            errors.append(f"{where}.document_class: unsupported document class")
        else:
            classes.append(document_class)

        resolved: dict[str, Path] = {}
        for field, seen in (("source_path", sources), ("label_path", labels)):
            value = entry.get(field)
            if isinstance(value, str):
                seen.append(value)
            try:
                resolved[field] = _safe_regular_file(root, value, f"{where}.{field}")
            except CorpusContractError as exc:
                errors.append(str(exc))
        for field in ("source_sha256", "label_sha256"):
            value = entry.get(field)
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                errors.append(f"{where}.{field}: expected lowercase SHA-256")
                continue
            path_field = field.removesuffix("_sha256") + "_path"
            if path_field in resolved and sha256_file(resolved[path_field]) != value:
                errors.append(f"{where}.{field}: hash mismatch")

        label_path = resolved.get("label_path")
        if label_path is not None:
            _lint_label(label_path, document_id, document_class, where, errors)

    _duplicates(ids, "manifest.documents: duplicate document_id", errors)
    _duplicates(sources, "manifest.documents: duplicate source_path", errors)
    _duplicates(labels, "manifest.documents: duplicate label_path", errors)
    counts = Counter(classes)
    for document_class in DOCUMENT_CLASSES:
        if counts[document_class] != DOCUMENTS_PER_CLASS:
            errors.append(
                f"manifest.documents: class {document_class!r} must have "
                f"exactly {DOCUMENTS_PER_CLASS} entries"
            )
    return errors


def _lint_label(
    path: Path,
    manifest_id: Any,
    manifest_class: Any,
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
    if label.get("document_id") != manifest_id:
        errors.append(f"{where}.document_id: does not match manifest")
    if label.get("document_class") != manifest_class:
        errors.append(f"{where}.document_class: does not match manifest")

    period = label.get("period_basis")
    if not isinstance(period, dict):
        errors.append(f"{where}.period_basis: expected object")
    else:
        _collect_exact_keys(period, _PERIOD_KEYS, f"{where}.period_basis", errors)
        basis = period.get("basis")
        if not isinstance(basis, str) or basis not in _PERIOD_BASES:
            errors.append(f"{where}.period_basis.basis: unsupported basis")
        elif (
            isinstance(manifest_class, str)
            and manifest_class in _CLASS_PERIODS
            and basis != _CLASS_PERIODS[manifest_class]
        ):
            errors.append(
                f"{where}.period_basis.basis: inconsistent with document class"
            )
        start = _iso_date(
            period.get("start_date"), f"{where}.period_basis.start_date", errors
        )
        end = _iso_date(
            period.get("end_date"), f"{where}.period_basis.end_date", errors
        )
        if start is not None and end is not None and start > end:
            errors.append(f"{where}.period_basis: start_date is after end_date")

    accounting = label.get("accounting_basis")
    if not isinstance(accounting, dict):
        errors.append(f"{where}.accounting_basis: expected object")
    else:
        _collect_exact_keys(
            accounting, _ACCOUNTING_KEYS, f"{where}.accounting_basis", errors
        )
        standards = accounting.get("standards")
        scope = accounting.get("scope")
        if not isinstance(standards, str) or standards not in _STANDARDS:
            errors.append(f"{where}.accounting_basis.standards: unsupported standards")
        if not isinstance(scope, str) or scope not in _SCOPES:
            errors.append(f"{where}.accounting_basis.scope: unsupported scope")
        if not isinstance(
            accounting.get("currency"), str
        ) or not _CURRENCY_RE.fullmatch(accounting.get("currency", "")):
            errors.append(f"{where}.accounting_basis.currency: expected ISO 4217 code")

    metrics = label.get("supported_metrics")
    valid_metrics: list[str] = []
    if not isinstance(metrics, list) or not metrics:
        errors.append(f"{where}.supported_metrics: expected non-empty array")
    else:
        for index, metric in enumerate(metrics):
            if not isinstance(metric, str) or not _METRIC_RE.fullmatch(metric):
                errors.append(f"{where}.supported_metrics[{index}]: invalid metric")
            else:
                valid_metrics.append(metric)
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
                f"{where}.provenance_expectations: metrics must exactly match supported_metrics"
            )

    scan = label.get("scan_image_status")
    if not isinstance(scan, dict):
        errors.append(f"{where}.scan_image_status: expected object")
    else:
        _collect_exact_keys(scan, _SCAN_KEYS, f"{where}.scan_image_status", errors)
        kind = scan.get("kind")
        text_layer = scan.get("has_text_layer")
        page_images = scan.get("has_page_images")
        if not isinstance(kind, str) or kind not in _SCAN_KINDS:
            errors.append(f"{where}.scan_image_status.kind: unsupported status")
        for field, value in (
            ("has_text_layer", text_layer),
            ("has_page_images", page_images),
        ):
            if not isinstance(value, bool):
                errors.append(f"{where}.scan_image_status.{field}: expected boolean")
        if kind == "born_digital" and (
            text_layer is not True or page_images is not False
        ):
            errors.append(
                f"{where}.scan_image_status: inconsistent born_digital status"
            )
        if kind == "image_only" and (
            text_layer is not False or page_images is not True
        ):
            errors.append(f"{where}.scan_image_status: inconsistent image_only status")
        if kind == "mixed" and (text_layer is not True or page_images is not True):
            errors.append(f"{where}.scan_image_status: inconsistent mixed status")

    verification = label.get("independent_verification")
    if not isinstance(verification, dict):
        errors.append(f"{where}.independent_verification: expected object")
    else:
        _collect_exact_keys(
            verification,
            _VERIFICATION_KEYS,
            f"{where}.independent_verification",
            errors,
        )
        reviewer = verification.get("reviewer_id")
        if not isinstance(reviewer, str) or not _ID_RE.fullmatch(reviewer):
            errors.append(
                f"{where}.independent_verification.reviewer_id: invalid stable identifier"
            )
        if verification.get("status") != "verified":
            errors.append(
                f"{where}.independent_verification.status: expected 'verified'"
            )
        timestamp = verification.get("verified_at")
        try:
            parsed = (
                datetime.fromisoformat(timestamp)
                if isinstance(timestamp, str)
                else None
            )
        except ValueError:
            parsed = None
        if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
            errors.append(
                f"{where}.independent_verification.verified_at: "
                "expected timezone-aware ISO 8601 timestamp"
            )


def _resolved_root(root: Path) -> Path:
    if not isinstance(root, Path):
        root = Path(root)
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
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
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise CorpusContractError(f"{where}: invalid or unsafe relative path")
    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CorpusContractError(f"{where}: unavailable: {exc}") from exc
    if not resolved.is_relative_to(root):
        raise CorpusContractError(f"{where}: path escapes corpus root")
    try:
        mode = candidate.lstat().st_mode
    except OSError as exc:
        raise CorpusContractError(f"{where}: unavailable: {exc}") from exc
    if stat.S_ISLNK(mode):
        raise CorpusContractError(f"{where}: symlinks are not allowed")
    if not stat.S_ISREG(mode):
        raise CorpusContractError(f"{where}: expected regular file")
    return resolved


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
        errors.append(f"{where}: expected ISO date")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{where}: expected ISO date")
        return None


def _duplicates(values: Sequence[str], message: str, errors: list[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        errors.append(f"{message}: {', '.join(duplicates)}")


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
