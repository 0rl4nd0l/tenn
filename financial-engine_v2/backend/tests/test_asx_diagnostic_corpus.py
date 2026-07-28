import hashlib
import json
import random
from copy import deepcopy
from pathlib import Path

import pytest
from app.services.asx_diagnostic_corpus import (
    DOCUMENT_CLASSES,
    CorpusContractError,
    build_manifest,
    canonical_json_bytes,
    lint_corpus,
    main,
)


def _label(document_id: str, document_class: str) -> dict:
    period = {
        "annual": "full_year",
        "4E": "full_year",
        "half-year": "half_year",
        "4D": "half_year",
        "quarterly": "quarter",
        "4C": "quarter",
    }[document_class]
    return {
        "schema_version": 1,
        "document_id": document_id,
        "document_class": document_class,
        "period_basis": {
            "basis": period,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        },
        "accounting_basis": {
            "standards": "australian_accounting_standards",
            "scope": "consolidated",
            "currency": "AUD",
        },
        "supported_metrics": ["cash_end", "operating_cf"],
        "provenance_expectations": [
            {
                "metric": "cash_end",
                "page_required": True,
                "statement_required": True,
            },
            {
                "metric": "operating_cf",
                "page_required": True,
                "statement_required": True,
            },
        ],
        "scan_image_status": {
            "kind": "born_digital",
            "has_text_layer": True,
            "has_page_images": False,
        },
        "independent_verification": {
            "reviewer_id": "synthetic-reviewer",
            "status": "verified",
            "verified_at": "2026-07-28T09:00:00+10:00",
        },
    }


def _valid_corpus(root: Path) -> tuple[list[dict], Path]:
    documents = []
    for document_class in DOCUMENT_CLASSES:
        for ordinal in (1, 2):
            document_id = f"{document_class.lower()}-{ordinal}"
            source_path = f"sources/{document_id}.pdf"
            label_path = f"labels/{document_id}.json"
            source = root / source_path
            label = root / label_path
            source.parent.mkdir(parents=True, exist_ok=True)
            label.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(f"synthetic PDF {document_id}".encode())
            label.write_bytes(canonical_json_bytes(_label(document_id, document_class)))
            documents.append(
                {
                    "document_id": document_id,
                    "document_class": document_class,
                    "source_path": source_path,
                    "label_path": label_path,
                }
            )
    manifest_path = root / "manifest.json"
    manifest_path.write_bytes(build_manifest(root, documents))
    return documents, manifest_path


def _manifest(root: Path) -> dict:
    return json.loads((root / "manifest.json").read_text())


def _write_manifest(root: Path, manifest: dict) -> None:
    (root / "manifest.json").write_bytes(canonical_json_bytes(manifest))


def _rewrite_label(root: Path, manifest: dict, mutate) -> None:
    entry = manifest["documents"][0]
    path = root / entry["label_path"]
    label = json.loads(path.read_text())
    mutate(label)
    path.write_bytes(canonical_json_bytes(label))
    entry["label_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_full_twelve_entry_corpus_and_cli(tmp_path: Path, capsys) -> None:
    _, manifest_path = _valid_corpus(tmp_path)

    assert lint_corpus(tmp_path, Path("manifest.json")) == []
    assert main(["--corpus-root", str(tmp_path), "--manifest", manifest_path.name]) == 0
    assert capsys.readouterr().out == "OK: valid 12-document ASX diagnostic corpus\n"


def test_manifest_build_is_deterministic_across_input_order(tmp_path: Path) -> None:
    documents, _ = _valid_corpus(tmp_path)
    shuffled = documents[:]
    random.Random(42).shuffle(shuffled)

    assert build_manifest(tmp_path, documents) == build_manifest(tmp_path, shuffled)
    parsed = json.loads(build_manifest(tmp_path, shuffled))
    assert [item["document_id"] for item in parsed["documents"]] == sorted(
        item["document_id"] for item in parsed["documents"]
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda m: m.pop("schema_version"), "missing fields"),
        (lambda m: m.update(extra=True), "unknown fields"),
        (lambda m: m.update(schema_version=True), "expected integer"),
        (lambda m: m["documents"].pop(), "expected exactly 12 entries"),
        (
            lambda m: m["documents"][0].update(document_class="unsupported"),
            "unsupported document class",
        ),
        (
            lambda m: m["documents"][0].update(document_class="annual"),
            "class '4C' must have exactly 2 entries",
        ),
        (
            lambda m: m["documents"][0].update(
                document_id=m["documents"][1]["document_id"]
            ),
            "duplicate document_id",
        ),
        (
            lambda m: m["documents"][0].update(
                source_path=m["documents"][1]["source_path"]
            ),
            "duplicate source_path",
        ),
        (
            lambda m: m["documents"][0].update(
                label_path=m["documents"][1]["label_path"]
            ),
            "duplicate label_path",
        ),
        (
            lambda m: m["documents"][0].update(source_sha256="ABC"),
            "expected lowercase SHA-256",
        ),
        (
            lambda m: m["documents"][0].update(label_sha256="ABC"),
            "expected lowercase SHA-256",
        ),
        (
            lambda m: m["documents"][0].update(source_sha256="0" * 64),
            "hash mismatch",
        ),
        (
            lambda m: m["documents"][0].update(source_path="../escape.pdf"),
            "invalid or unsafe relative path",
        ),
        (
            lambda m: m["documents"][0].update(source_path="/absolute.pdf"),
            "invalid or unsafe relative path",
        ),
        (
            lambda m: m["documents"][0].update(source_path="missing.pdf"),
            "unavailable",
        ),
    ],
)
def test_manifest_fail_closed_boundaries(
    tmp_path: Path, mutation, expected: str
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    mutation(manifest)
    _write_manifest(tmp_path, manifest)

    assert any(
        expected in error for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda label: label.pop("accounting_basis"), "missing fields"),
        (lambda label: label.update(unexpected=True), "unknown fields"),
        (lambda label: label.update(schema_version=False), "expected integer"),
        (lambda label: label.update(document_id="other"), "does not match manifest"),
        (
            lambda label: label.update(document_class="annual"),
            "does not match manifest",
        ),
        (
            lambda label: label["period_basis"].update(basis="full_year"),
            "inconsistent with document class",
        ),
        (
            lambda label: label["period_basis"].update(start_date="not-a-date"),
            "expected ISO date",
        ),
        (
            lambda label: label["period_basis"].update(
                start_date="2026-01-01", end_date="2025-01-01"
            ),
            "start_date is after end_date",
        ),
        (
            lambda label: label["accounting_basis"].update(standards="unknown"),
            "unsupported standards",
        ),
        (
            lambda label: label["accounting_basis"].update(scope="unknown"),
            "unsupported scope",
        ),
        (
            lambda label: label["accounting_basis"].update(currency="aud"),
            "expected ISO 4217",
        ),
        (lambda label: label.update(supported_metrics=[]), "expected non-empty array"),
        (
            lambda label: label.update(supported_metrics=["cash_end", "cash_end"]),
            "duplicate metric",
        ),
        (
            lambda label: label["provenance_expectations"][0].pop("page_required"),
            "missing fields",
        ),
        (
            lambda label: label["provenance_expectations"].append(
                deepcopy(label["provenance_expectations"][0])
            ),
            "duplicate metric",
        ),
        (
            lambda label: label["provenance_expectations"].pop(),
            "must exactly match supported_metrics",
        ),
        (
            lambda label: label["provenance_expectations"][0].update(page_required=1),
            "expected boolean",
        ),
        (
            lambda label: label["scan_image_status"].update(kind="unknown"),
            "unsupported status",
        ),
        (
            lambda label: label["scan_image_status"].update(has_text_layer=False),
            "inconsistent born_digital",
        ),
        (
            lambda label: label["independent_verification"].pop("reviewer_id"),
            "missing fields",
        ),
        (
            lambda label: label["independent_verification"].update(reviewer_id=""),
            "invalid stable identifier",
        ),
        (
            lambda label: label["independent_verification"].update(status="pending"),
            "expected 'verified'",
        ),
        (
            lambda label: label["independent_verification"].update(
                verified_at="2026-07-28T09:00:00"
            ),
            "timezone-aware",
        ),
    ],
)
def test_label_fail_closed_boundaries(tmp_path: Path, mutation, expected: str) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    _rewrite_label(tmp_path, manifest, mutation)
    _write_manifest(tmp_path, manifest)

    assert any(
        expected in error for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


def test_source_and_label_hash_mismatch_are_both_rejected(tmp_path: Path) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    entry = manifest["documents"][0]
    (tmp_path / entry["source_path"]).write_bytes(b"changed")
    (tmp_path / entry["label_path"]).write_bytes(b"{}")

    errors = lint_corpus(tmp_path, Path("manifest.json"))
    assert any("source_sha256: hash mismatch" in error for error in errors)
    assert any("label_sha256: hash mismatch" in error for error in errors)


def test_malformed_label_json_is_rejected_after_hash_verification(
    tmp_path: Path,
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    entry = manifest["documents"][0]
    label = tmp_path / entry["label_path"]
    label.write_bytes(b"{not-json")
    entry["label_sha256"] = hashlib.sha256(label.read_bytes()).hexdigest()
    _write_manifest(tmp_path, manifest)

    assert any(
        "label: invalid JSON" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


@pytest.mark.parametrize("path_field", ["source_path", "label_path"])
def test_absent_source_or_label_file_is_rejected(
    tmp_path: Path, path_field: str
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    (tmp_path / manifest["documents"][0][path_field]).unlink()

    assert any(
        f".{path_field}: unavailable" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


def test_non_regular_and_symlink_escape_are_rejected(tmp_path: Path) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    entry = manifest["documents"][0]
    source = tmp_path / entry["source_path"]
    source.unlink()
    source.mkdir()
    _write_manifest(tmp_path, manifest)
    assert any(
        "expected regular file" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )

    source.rmdir()
    outside = tmp_path.parent / f"{tmp_path.name}-outside.pdf"
    outside.write_bytes(b"outside")
    source.symlink_to(outside)
    assert any(
        "path escapes corpus root" in error or "symlinks are not allowed" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


def test_builder_rejects_incomplete_inputs(tmp_path: Path) -> None:
    documents, _ = _valid_corpus(tmp_path)
    documents[0]["unknown"] = "closed"

    with pytest.raises(CorpusContractError, match="unknown fields"):
        build_manifest(tmp_path, documents)


@pytest.mark.parametrize("malformed_id", [None, True, 7, [], {}])
def test_builder_reports_malformed_document_id_as_contract_error(
    tmp_path: Path, malformed_id
) -> None:
    documents, _ = _valid_corpus(tmp_path)
    documents[0]["document_id"] = malformed_id

    with pytest.raises(CorpusContractError, match="invalid stable identifier"):
        build_manifest(tmp_path, documents)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda label: label["period_basis"].update(basis=[]), "unsupported basis"),
        (
            lambda label: label["accounting_basis"].update(standards=[]),
            "unsupported standards",
        ),
        (
            lambda label: label["accounting_basis"].update(scope={}),
            "unsupported scope",
        ),
        (
            lambda label: label["scan_image_status"].update(kind=[]),
            "unsupported status",
        ),
    ],
)
def test_unhashable_label_values_produce_diagnostics(
    tmp_path: Path, mutation, expected: str
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    _rewrite_label(tmp_path, manifest, mutation)
    _write_manifest(tmp_path, manifest)

    assert any(
        expected in error for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


def test_cli_diagnostics_are_deterministic_and_nonzero(tmp_path: Path, capsys) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    manifest["documents"][0]["source_sha256"] = "bad"
    _write_manifest(tmp_path, manifest)

    assert main(["--corpus-root", str(tmp_path), "--manifest", "manifest.json"]) == 1
    first = capsys.readouterr().err
    assert main(["--corpus-root", str(tmp_path), "--manifest", "manifest.json"]) == 1
    assert capsys.readouterr().err == first
    assert first.startswith("ERROR: ")
