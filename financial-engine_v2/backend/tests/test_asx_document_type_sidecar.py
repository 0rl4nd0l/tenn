import ast
import json
import subprocess
import sys
from pathlib import Path

from app.services.asx_document_type_sidecar import (
    ARTIFACT_TYPE,
    build_asx_document_type_sidecar,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "asx_document_type_classifier"
FIXTURE_PATHS = sorted(path for path in FIXTURE_DIR.glob("*.json") if path.name != "manifest.json")
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_asx_document_type_sidecars.py"
SIDECAR_PATH = BACKEND_ROOT / "app" / "services" / "asx_document_type_sidecar.py"
PRODUCTION_ROUTING_PATHS = [
    BACKEND_ROOT / "app" / "routes" / "chat.py",
    BACKEND_ROOT / "app" / "routes" / "cockpit_api.py",
    BACKEND_ROOT / "app" / "routes" / "ops_api.py",
    BACKEND_ROOT / "app" / "services" / "docling_extract.py",
    BACKEND_ROOT / "app" / "services" / "method_isolated_extraction.py",
    BACKEND_ROOT / "app" / "services" / "multipass_extraction.py",
    BACKEND_ROOT / "app" / "services" / "pipeline.py",
    BACKEND_ROOT / "app" / "services" / "pipeline_service.py",
    BACKEND_ROOT / "app" / "services" / "pipeline_stages.py",
    BACKEND_ROOT / "app" / "worker_tasks.py",
]
ALLOWED_SIDECAR_IMPORT_ROOTS = {
    "__future__",
    "app",
    "collections",
    "datetime",
    "hashlib",
    "json",
    "pathlib",
    "typing",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    assert isinstance(loaded, dict)
    return loaded


def _fixtures() -> list[dict]:
    return [_load_json(path) for path in FIXTURE_PATHS]


def _sidecar(fixture: dict) -> dict:
    return build_asx_document_type_sidecar(fixture, generated_at="2026-05-20T00:00:00Z")


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_walk_strings(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_walk_strings(item))
        return values
    return []


def test_sidecar_artifact_can_be_generated_for_every_fixture() -> None:
    assert FIXTURE_PATHS
    for fixture in _fixtures():
        artifact = _sidecar(fixture)
        assert artifact["artifact_type"] == ARTIFACT_TYPE, fixture["fixture_id"]
        assert artifact["document_id"] == fixture["document_id"], fixture["fixture_id"]
        assert artifact["fixture_id"] == fixture["fixture_id"], fixture["fixture_id"]
        assert artifact["ticker"] == fixture["ticker"], fixture["fixture_id"]
        assert artifact["source"] == "synthetic_fixture", fixture["fixture_id"]
        assert artifact["schema_version"] == 1, fixture["fixture_id"]


def test_sidecar_results_match_fixture_expectations_and_never_write_canonically() -> None:
    for fixture in _fixtures():
        artifact = _sidecar(fixture)
        assert artifact["canonical_write"] is False, fixture["fixture_id"]
        assert artifact["document_type"] == fixture["expected_document_type"], (
            fixture["fixture_id"]
        )
        assert artifact["abstain"] is fixture["expected_abstain"], (
            fixture["fixture_id"]
        )
        if fixture["expected_document_type"] in {
            "annual_report",
            "half_year_report",
            "quarterly_report",
            "appendix_4c",
            "appendix_4d",
            "appendix_4e",
            "appendix_5b",
        }:
            assert artifact["extraction_contract_id"], fixture["fixture_id"]
            assert artifact["extraction_contract_abstain"] is False
        else:
            assert artifact["extraction_contract_id"] is None
            assert artifact["extraction_contract_abstain"] is True


def test_abstain_and_positive_evidence_contract() -> None:
    for fixture in _fixtures():
        artifact = _sidecar(fixture)
        if fixture["expected_abstain"]:
            assert artifact["abstain_reasons"], fixture["fixture_id"]
        else:
            assert artifact["positive_evidence"], fixture["fixture_id"]
            assert not artifact["abstain_reasons"], fixture["fixture_id"]


def test_sidecars_include_deterministic_input_checksum() -> None:
    for fixture in _fixtures():
        first = _sidecar(fixture)
        second = build_asx_document_type_sidecar(
            fixture,
            generated_at="2026-05-20T01:02:03Z",
        )
        assert first["input_checksum"] == second["input_checksum"], fixture["fixture_id"]
        assert len(first["input_checksum"]) == 64, fixture["fixture_id"]
        int(first["input_checksum"], 16)


def test_sidecar_accepts_explicit_surrogate_payload_without_fixture_fields() -> None:
    fixture = _load_json(FIXTURE_DIR / "annual_report_basic.json")
    artifact = build_asx_document_type_sidecar(
        fixture["source_text_surrogate"],
        document_id="SURROGATE-ASX-001",
        ticker="SRG",
        source="explicit_surrogate",
        generated_at="2026-05-20T00:00:00Z",
    )
    assert artifact["artifact_type"] == ARTIFACT_TYPE
    assert artifact["document_id"] == "SURROGATE-ASX-001"
    assert artifact["ticker"] == "SRG"
    assert artifact["source"] == "explicit_surrogate"
    assert artifact["document_type"] == fixture["expected_document_type"]
    assert artifact["canonical_write"] is False
    assert "fixture_id" not in artifact


def test_sidecar_does_not_include_large_source_text_blobs() -> None:
    forbidden_keys = {"source_text_surrogate", "full_text", "pdf_text", "page_text"}
    for fixture in _fixtures():
        artifact = _sidecar(fixture)
        serialized = json.dumps(artifact, sort_keys=True)
        assert not (forbidden_keys & set(artifact)), fixture["fixture_id"]
        assert json.dumps(fixture["source_text_surrogate"], sort_keys=True) not in serialized
        for text in _walk_strings(artifact):
            assert len(text) <= 220, (fixture["fixture_id"], text)


def test_script_can_generate_sidecars_into_temp_directory(tmp_path: Path) -> None:
    out_dir = tmp_path / "sidecars"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--fixtures-dir",
            str(FIXTURE_DIR),
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    summary = json.loads(completed.stdout)
    assert summary["ok"] is True
    paths = sorted(out_dir.glob("*.json"))
    assert len(paths) == len(FIXTURE_PATHS)
    for path in paths:
        artifact = _load_json(path)
        assert artifact["artifact_type"] == ARTIFACT_TYPE
        assert artifact["canonical_write"] is False


def test_script_refuses_missing_or_unsafe_fixture_dirs_gracefully(tmp_path: Path) -> None:
    missing = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--fixtures-dir",
            str(tmp_path / "missing"),
            "--out-dir",
            str(tmp_path / "out"),
        ],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert missing.returncode == 2
    assert "does not exist" in missing.stderr
    assert "Traceback" not in missing.stderr

    unsafe = tmp_path / "not_a_fixture_contract"
    unsafe.mkdir()
    (unsafe / "random.json").write_text("{}", encoding="utf-8")
    refused = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--fixtures-dir",
            str(unsafe),
            "--out-dir",
            str(tmp_path / "out2"),
        ],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert refused.returncode == 2
    assert "missing manifest.json" in refused.stderr
    assert "Traceback" not in refused.stderr


def test_sidecar_module_imports_only_standard_library_and_pure_classifier() -> None:
    tree = ast.parse(SIDECAR_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
            imported_modules.add(node.module)

    assert imported_roots <= ALLOWED_SIDECAR_IMPORT_ROOTS
    assert imported_modules <= {
        "__future__",
        "app.services.asx_document_type_classifier",
        "app.services.asx_extraction_contracts",
        "collections.abc",
        "datetime",
        "hashlib",
        "json",
        "pathlib",
        "typing",
    }


def test_cli_script_imports_only_sidecar_not_backend_startup_or_routes() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "app.main" not in imported_modules
    assert not any(module.startswith("app.routes") for module in imported_modules)
    assert "app.services.asx_document_type_sidecar" in imported_modules


def test_production_routing_files_do_not_import_sidecar() -> None:
    for path in PRODUCTION_ROUTING_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "asx_document_type_sidecar" not in source, path
