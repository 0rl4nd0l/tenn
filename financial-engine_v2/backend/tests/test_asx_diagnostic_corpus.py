import hashlib
import json
import os
import random
from copy import deepcopy
from pathlib import Path

import pytest
from app.services.asx_diagnostic_corpus import (
    TICKET_02_BUCKETS,
    CorpusContractError,
    build_manifest,
    canonical_json_bytes,
    lint_corpus,
    main,
)
from app.services.financial_metric_contract import (
    METRIC_CONTRACT_BY_CANONICAL_FIELD,
    MetricContractStatus,
)

_SEMANTICS = {
    "annual": ("annual", "annual_report", "A"),
    "4E": ("annual", "appendix_4e", "A"),
    "half-year": ("half_year", "half_year_report", "H"),
    "4D": ("half_year", "appendix_4d", "H"),
    "quarterly": ("quarterly", "appendix_5b", "Q"),
    "4C": ("quarterly", "appendix_4c", "Q"),
}


def _label(document_id: str, bucket: str) -> dict:
    document_class, document_type, period_type = _SEMANTICS[bucket]
    return {
        "schema_version": 1,
        "document_id": document_id,
        "ticket_02_bucket": bucket,
        "document_class": document_class,
        "document_type": document_type,
        "period_type": period_type,
        "period_end": "2025-12-31",
        "accounting_basis": "statutory",
        "currency": "AUD",
        "consolidation_scope": "consolidated",
        "accounting_standards": "australian_accounting_standards",
        "supported_metrics": ["cash_end", "operating_cf"],
        "provenance_expectations": [
            {
                "metric": metric,
                "page_required": True,
                "statement_required": True,
            }
            for metric in ("cash_end", "operating_cf")
        ],
        "scan_image_status": {
            "kind": "born_digital",
            "has_text_layer": True,
            "has_page_images": False,
        },
        "labeler_id": "synthetic-labeler",
        "independent_verification": {
            "verifier_id": "synthetic-verifier",
            "status": "verified",
            "verified_at": "2026-07-28T09:00:00+10:00",
        },
    }


def _valid_corpus(root: Path) -> tuple[list[dict], Path]:
    documents = []
    for bucket in TICKET_02_BUCKETS:
        document_class, document_type, _ = _SEMANTICS[bucket]
        for ordinal in (1, 2):
            document_id = f"{bucket.lower()}-{ordinal}"
            source_path = f"sources/{document_id}.pdf"
            label_path = f"labels/{document_id}.json"
            source = root / source_path
            label = root / label_path
            source.parent.mkdir(parents=True, exist_ok=True)
            label.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(f"synthetic PDF {document_id}".encode())
            label.write_bytes(canonical_json_bytes(_label(document_id, bucket)))
            documents.append(
                {
                    "document_id": document_id,
                    "ticket_02_bucket": bucket,
                    "document_class": document_class,
                    "document_type": document_type,
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


def test_valid_corpus_is_deterministic_and_cli_interoperates(
    tmp_path: Path, capsys
) -> None:
    documents, manifest_path = _valid_corpus(tmp_path)
    shuffled = documents[:]
    random.Random(42).shuffle(shuffled)

    assert lint_corpus(tmp_path, Path("manifest.json")) == []
    assert build_manifest(tmp_path, shuffled) == build_manifest(tmp_path, documents)
    assert main(["--corpus-root", str(tmp_path), "--manifest", manifest_path.name]) == 0
    assert capsys.readouterr().out == "OK: valid 12-document ASX diagnostic corpus\n"


def test_document_classes_interoperate_with_asx_document_class_authority(
    tmp_path: Path,
) -> None:
    from app.services.extraction_gold_eval import ASXDocumentClass

    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)

    assert {entry["document_class"] for entry in manifest["documents"]} == {
        item.value for item in ASXDocumentClass
    }


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda m: m.pop("schema_version"), "missing fields"),
        (lambda m: m.update(extra=True), "unknown fields"),
        (lambda m: m.update(schema_version=True), "expected integer"),
        (lambda m: m["documents"].pop(), "expected exactly 12 entries"),
        (
            lambda m: m["documents"][0].update(ticket_02_bucket="unsupported"),
            "unsupported Ticket 02 bucket",
        ),
        (
            lambda m: m["documents"][0].update(ticket_02_bucket="annual"),
            "bucket '4C' must have exactly 2 entries",
        ),
        (
            lambda m: m["documents"][0].update(document_class="half-year"),
            "unsupported canonical document class",
        ),
        (
            lambda m: m["documents"][0].update(document_type="quarterly"),
            "unsupported canonical document type",
        ),
        (
            lambda m: m["documents"][0].update(document_class="annual"),
            "class/type combination is inconsistent",
        ),
        (
            lambda m: m["documents"][0].update(
                document_id=m["documents"][1]["document_id"]
            ),
            "duplicate document_id",
        ),
        (
            lambda m: m["documents"][0].update(source_sha256="ABC"),
            "expected lowercase SHA-256",
        ),
        (
            lambda m: m["documents"][0].update(source_sha256="0" * 64),
            "hash mismatch",
        ),
        (
            lambda m: m["documents"][0].update(source_path="../escape.pdf"),
            "non-canonical or unsafe relative path",
        ),
        (
            lambda m: m["documents"][0].update(source_path="/absolute.pdf"),
            "non-canonical or unsafe relative path",
        ),
        (
            lambda m: m["documents"][0].update(source_path="sources//4c-1.pdf"),
            "non-canonical or unsafe relative path",
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
            lambda label: label.update(document_type="annual_report"),
            "does not match manifest",
        ),
        (
            lambda label: label.update(period_type="FY"),
            "expected canonical A, H, or Q",
        ),
        (
            lambda label: label.update(period_type="A"),
            "inconsistent with document semantics",
        ),
        (
            lambda label: label.update(period_end="not-a-date"),
            "expected source-bound ISO date",
        ),
        (
            lambda label: label.update(accounting_basis="reported"),
            "expected 'statutory' or 'underlying'",
        ),
        (lambda label: label.update(currency="aud"), "expected ISO 4217"),
        (
            lambda label: label.update(consolidation_scope="group"),
            "unsupported scope",
        ),
        (
            lambda label: label.update(accounting_standards="unknown"),
            "unsupported standards",
        ),
        (lambda label: label.update(supported_metrics=[]), "expected non-empty array"),
        (
            lambda label: label.update(supported_metrics=["cash_end", "cash_end"]),
            "duplicate metric",
        ),
        (
            lambda label: label.update(supported_metrics=["operating_cash_flow"]),
            "not a canonical financial metric field",
        ),
        (
            lambda label: label.update(supported_metrics=["total_equity"]),
            "metric is not canonically supported",
        ),
        (
            lambda label: label.update(supported_metrics=["eps"]),
            "not a canonical financial metric field",
        ),
        (
            lambda label: label.update(supported_metrics=["total_debt"]),
            "metric is not canonically supported",
        ),
        (
            lambda label: label.update(supported_metrics=["unknown_metric"]),
            "not a canonical financial metric field",
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
            lambda label: label["scan_image_status"].update(has_text_layer=False),
            "inconsistent born_digital",
        ),
        (lambda label: label.update(labeler_id=""), "invalid stable identifier"),
        (
            lambda label: label["independent_verification"].update(
                verifier_id=label["labeler_id"]
            ),
            "must differ from labeler_id",
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


def test_metric_authority_interoperability_and_document_applicability(
    tmp_path: Path,
) -> None:
    assert METRIC_CONTRACT_BY_CANONICAL_FIELD["operating_cf"].declared_status == (
        MetricContractStatus.SUPPORTED
    )
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    quarterly = next(
        entry
        for entry in manifest["documents"]
        if entry["document_type"] == "appendix_4c"
    )
    manifest["documents"].remove(quarterly)
    manifest["documents"].insert(0, quarterly)
    _rewrite_label(
        tmp_path,
        manifest,
        lambda label: (
            label.update(supported_metrics=["revenue"]),
            label.update(
                provenance_expectations=[
                    {
                        "metric": "revenue",
                        "page_required": True,
                        "statement_required": True,
                    }
                ]
            ),
        ),
    )
    _write_manifest(tmp_path, manifest)

    assert any(
        "metric is not supported for appendix_4c" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


@pytest.mark.parametrize("path_field", ["source_path", "label_path"])
def test_symlink_in_any_path_component_is_rejected(
    tmp_path: Path, path_field: str
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    entry = manifest["documents"][0]
    original = tmp_path / entry[path_field]
    real_parent = tmp_path / f"real-{path_field}"
    real_parent.mkdir()
    moved = real_parent / original.name
    original.replace(moved)
    link = original.parent / "linked-component"
    link.symlink_to(real_parent, target_is_directory=True)
    entry[path_field] = f"{original.parent.name}/{link.name}/{original.name}"
    _write_manifest(tmp_path, manifest)

    assert any(
        f".{path_field}: symlinks are not allowed in any path component" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


@pytest.mark.parametrize("path_field", ["source_path", "label_path"])
def test_hard_link_alias_is_rejected_by_file_identity(
    tmp_path: Path, path_field: str
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    first, second = manifest["documents"][:2]
    second_path = tmp_path / second[path_field]
    second_path.unlink()
    os.link(tmp_path / first[path_field], second_path)
    second[path_field.removesuffix("_path") + "_sha256"] = first[
        path_field.removesuffix("_path") + "_sha256"
    ]
    _write_manifest(tmp_path, manifest)

    assert any(
        "duplicate file identity" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


def test_source_and_label_paths_share_one_uniqueness_domain(tmp_path: Path) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    first, second = manifest["documents"][:2]
    second_label = tmp_path / second["label_path"]
    second_label.unlink()
    os.link(tmp_path / first["source_path"], second_label)
    second["label_sha256"] = first["source_sha256"]
    _write_manifest(tmp_path, manifest)

    assert any(
        "duplicate file identity" in error
        for error in lint_corpus(tmp_path, Path("manifest.json"))
    )


def test_builder_translates_hash_io_failure_to_field_scoped_error(
    tmp_path: Path, monkeypatch
) -> None:
    documents, _ = _valid_corpus(tmp_path)

    def fail_hash(_path):
        raise PermissionError("synthetic denial")

    monkeypatch.setattr("app.services.asx_diagnostic_corpus.sha256_file", fail_hash)
    with pytest.raises(
        CorpusContractError, match=r"documents\[0\]\.source_path: unavailable"
    ):
        build_manifest(tmp_path, documents)


def test_malformed_label_json_and_hash_mismatch_are_diagnostic(
    tmp_path: Path,
) -> None:
    _valid_corpus(tmp_path)
    manifest = _manifest(tmp_path)
    entry = manifest["documents"][0]
    label = tmp_path / entry["label_path"]
    label.write_bytes(b"{not-json")
    entry["label_sha256"] = hashlib.sha256(label.read_bytes()).hexdigest()
    (tmp_path / entry["source_path"]).write_bytes(b"changed")
    _write_manifest(tmp_path, manifest)

    errors = lint_corpus(tmp_path, Path("manifest.json"))
    assert any("label: invalid JSON" in error for error in errors)
    assert any("source_sha256: hash mismatch" in error for error in errors)


def test_builder_rejects_incomplete_inputs(tmp_path: Path) -> None:
    documents, _ = _valid_corpus(tmp_path)
    documents[0]["unknown"] = "closed"

    with pytest.raises(CorpusContractError, match="unknown fields"):
        build_manifest(tmp_path, documents)


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
