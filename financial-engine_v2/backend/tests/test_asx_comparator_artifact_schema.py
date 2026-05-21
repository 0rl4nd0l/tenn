import ast
from pathlib import Path

from app.services.asx_comparator_artifact_schema import (
    ARTIFACT_TYPE,
    build_comparator_artifact,
    stable_artifact_checksum,
    validate_comparator_artifact,
    validate_metric_candidate,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
SCHEMA_PATH = BACKEND_ROOT / "app" / "services" / "asx_comparator_artifact_schema.py"
EXISTING_ASX_TEST_PATHS = [
    BACKEND_ROOT / "tests" / "test_asx_document_type_fixture_contract.py",
    BACKEND_ROOT / "tests" / "test_asx_document_type_classifier.py",
    BACKEND_ROOT / "tests" / "test_asx_document_type_sidecar.py",
]
PRODUCTION_ROUTING_PATHS = [
    BACKEND_ROOT / "app" / "services" / "multipass_extraction.py",
    BACKEND_ROOT / "app" / "services" / "method_isolated_extraction.py",
    BACKEND_ROOT / "app" / "services" / "pipeline.py",
    BACKEND_ROOT / "app" / "services" / "docling_extract.py",
]
ALLOWED_SCHEMA_IMPORT_MODULES = {
    "__future__",
    "collections.abc",
    "datetime",
    "hashlib",
    "json",
    "re",
    "typing",
}
ALLOWED_SCHEMA_IMPORT_ROOTS = {
    "__future__",
    "collections",
    "datetime",
    "hashlib",
    "json",
    "re",
    "typing",
}


def _table() -> dict:
    return {
        "table_id": "table-1",
        "page": 4,
        "bbox": [0.1, 0.2, 0.8, 0.9],
        "caption": "Consolidated statement of profit or loss",
        "headers": ["Line item", "Current period"],
        "rows": [["Revenue", "$1.2m"]],
        "source_anchor": "statement of profit or loss",
        "parser_confidence": 0.92,
        "warnings": [],
    }


def _metric(name: str = "cash receipts", status: str = "candidate") -> dict:
    return {
        "metric_name": name,
        "candidate_value": "1200000",
        "raw_value": "$1.2m",
        "normalized_value": 1200000,
        "unit": "currency",
        "currency": "AUD",
        "scale": "ones",
        "period": "quarter",
        "source_table_id": "table-1",
        "page": 4,
        "row_label": "Receipts from customers",
        "column_label": "Current quarter",
        "line_item_id": "appendix_4c_1_1",
        "evidence_text": "Receipts from customers $1.2m",
        "confidence": 0.91,
        "status": status,
        "canonical_write": False,
        "abstain_reasons": [],
        "warnings": [],
    }


def _artifact(document_type: str = "appendix_4e", metric: dict | None = None) -> dict:
    return build_comparator_artifact(
        document_id="ASX-ABC-2026-0001",
        ticker="ABC",
        document_type=document_type,
        source_reference="synthetic://asx/abc/2026/0001.pdf",
        source_sha256="a" * 64,
        parser_id="deterministic-parser-prototype",
        parser_version="0.0.0-test",
        generated_at="2026-05-21T00:00:00Z",
        period_end="2026-03-31",
        reporting_period="quarter",
        currency="AUD",
        scale="ones",
        tables=[_table()],
        metric_candidates=[metric or _metric()],
        unsupported_metric_candidates=[],
        abstain_reasons=[],
        warnings=["report-only comparator artifact"],
        provenance={"source": "unit-test", "canonical_write": False},
        validation_summary={"schema_validation": "not_run"},
    )


def test_valid_minimal_comparator_artifact_passes_validation() -> None:
    artifact = _artifact()

    assert artifact["artifact_type"] == ARTIFACT_TYPE
    assert validate_comparator_artifact(artifact) == []


def test_missing_required_artifact_fields_fail_validation() -> None:
    artifact = _artifact()
    del artifact["document_id"]
    del artifact["parser_id"]

    issues = validate_comparator_artifact(artifact)

    assert "artifact missing required field: document_id" in issues
    assert "artifact missing required field: parser_id" in issues


def test_artifact_level_canonical_write_true_fails_validation() -> None:
    artifact = _artifact()
    artifact["canonical_write"] = True

    issues = validate_comparator_artifact(artifact)

    assert "artifact canonical_write must be false" in issues


def test_metric_candidate_with_canonical_write_true_fails_validation() -> None:
    artifact = _artifact()
    artifact["metric_candidates"][0]["canonical_write"] = True

    issues = validate_comparator_artifact(artifact)

    assert "metric_candidates[0] canonical_write must be false" in issues


def test_metric_candidate_without_evidence_fails_unless_status_is_abstain() -> None:
    candidate = _metric()
    candidate["source_table_id"] = ""
    candidate["page"] = None
    candidate["row_label"] = ""
    candidate["column_label"] = ""

    issues = validate_metric_candidate(candidate)

    assert any("source_table_id" in issue for issue in issues)
    assert any("page" in issue for issue in issues)
    assert any("row_label" in issue for issue in issues)
    assert any("column_label" in issue for issue in issues)

    abstain_candidate = dict(candidate)
    abstain_candidate["status"] = "abstain"
    abstain_candidate["abstain_reasons"] = ["table evidence missing"]
    assert validate_metric_candidate(abstain_candidate) == []

    abstain_candidate["abstain_reasons"] = []
    assert "metric_candidate abstain status requires abstain_reasons" in validate_metric_candidate(
        abstain_candidate
    )


def test_unsupported_metric_candidates_validate_only_as_review_only_or_unsupported() -> None:
    artifact = _artifact()
    artifact["metric_candidates"] = []
    artifact["unsupported_metric_candidates"] = [_metric("EBITDA", "candidate")]

    issues = validate_comparator_artifact(artifact)

    assert "unsupported_metric_candidates[0] unsupported metric status must be review_only or unsupported" in issues
    assert "unsupported_metric_candidates[0] ebitda must be review_only or unsupported" in issues

    artifact["unsupported_metric_candidates"][0]["status"] = "review_only"
    assert validate_comparator_artifact(artifact) == []

    artifact["unsupported_metric_candidates"][0]["status"] = "unsupported"
    assert validate_comparator_artifact(artifact) == []


def test_appendix_5b_artifact_rejects_revenue_npat_net_debt_canonical_candidates() -> None:
    for metric_name in ("revenue", "NPAT", "net debt"):
        artifact = _artifact("appendix_5b", _metric(metric_name, "candidate"))

        issues = validate_comparator_artifact(artifact)

        assert any("cannot be a candidate for appendix_5b artifacts" in issue for issue in issues)


def test_appendix_4c_artifact_rejects_revenue_npat_net_debt_canonical_candidates() -> None:
    for metric_name in ("revenue", "NPAT", "net debt"):
        artifact = _artifact("appendix_4c", _metric(metric_name, "candidate"))

        issues = validate_comparator_artifact(artifact)

        assert any("cannot be a candidate for appendix_4c artifacts" in issue for issue in issues)


def test_appendix_4d_4e_artifacts_allow_eps_nta_dividends_only_as_review_or_unsupported() -> None:
    for document_type in ("appendix_4d", "appendix_4e"):
        for metric_name in ("EPS", "NTA", "dividends"):
            candidate_artifact = _artifact(document_type, _metric(metric_name, "candidate"))
            assert any(
                "must be review_only or unsupported" in issue
                for issue in validate_comparator_artifact(candidate_artifact)
            )

            review_artifact = _artifact(document_type, _metric(metric_name, "review_only"))
            assert validate_comparator_artifact(review_artifact) == []

            unsupported_artifact = _artifact(document_type, _metric(metric_name, "unsupported"))
            assert validate_comparator_artifact(unsupported_artifact) == []


def test_stable_checksum_is_deterministic() -> None:
    artifact = _artifact()

    first = stable_artifact_checksum(artifact)
    second = stable_artifact_checksum(dict(reversed(list(artifact.items()))))

    assert first == second
    assert len(first) == 64
    int(first, 16)


def test_module_imports_no_forbidden_backend_or_runtime_packages() -> None:
    tree = ast.parse(SCHEMA_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
            imported_modules.add(node.module)

    assert imported_roots <= ALLOWED_SCHEMA_IMPORT_ROOTS
    assert imported_modules <= ALLOWED_SCHEMA_IMPORT_MODULES
    assert "app" not in imported_roots
    assert "qdrant_client" not in imported_roots
    assert "sqlalchemy" not in imported_roots


def test_production_routing_files_do_not_import_comparator_schema() -> None:
    for path in PRODUCTION_ROUTING_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "asx_comparator_artifact_schema" not in source, path


def test_existing_asx_fixture_classifier_sidecar_test_files_remain_present() -> None:
    for path in EXISTING_ASX_TEST_PATHS:
        assert path.exists(), path
