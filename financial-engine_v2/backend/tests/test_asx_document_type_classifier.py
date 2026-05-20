import ast
import json
from pathlib import Path

from app.services.asx_document_type_classifier import classify_asx_document_type


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "asx_document_type_classifier"
FIXTURE_PATHS = sorted(path for path in FIXTURE_DIR.glob("*.json") if path.name != "manifest.json")
CLASSIFIER_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "services"
    / "asx_document_type_classifier.py"
)
ROUTING_OWNER_PATHS = [
    Path(__file__).resolve().parent.parent / "app" / "services" / "multipass_extraction.py",
    Path(__file__).resolve().parent.parent / "app" / "services" / "method_isolated_extraction.py",
    Path(__file__).resolve().parent.parent / "app" / "services" / "pipeline.py",
]

ALLOWED_CLASSIFIER_IMPORT_ROOTS = {
    "__future__",
    "collections",
    "dataclasses",
    "re",
    "typing",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    assert isinstance(loaded, dict)
    return loaded


def _fixtures() -> list[dict]:
    return [_load_json(path) for path in FIXTURE_PATHS]


def _classify_fixture(fixture: dict) -> dict:
    return classify_asx_document_type(fixture["source_text_surrogate"]).to_dict()


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_walk_strings(item))
        return strings
    return []


def test_all_fixtures_classify_to_expected_document_type_and_abstain_contract() -> None:
    for fixture in _fixtures():
        result = _classify_fixture(fixture)
        assert result["document_type"] == fixture["expected_document_type"], fixture["fixture_id"]
        assert result["confidence_band"] == fixture["expected_confidence_band"], fixture["fixture_id"]
        assert result["abstain"] is fixture["expected_abstain"], fixture["fixture_id"]
        assert result["expected_abstain"] is fixture["expected_abstain"], fixture["fixture_id"]


def test_non_abstain_fixtures_have_positive_evidence_and_abstain_fixtures_have_reasons() -> None:
    for fixture in _fixtures():
        result = _classify_fixture(fixture)
        if fixture["expected_abstain"]:
            assert result["abstain_reasons"], fixture["fixture_id"]
            assert not result["positive_evidence"], fixture["fixture_id"]
        else:
            assert result["positive_evidence"], fixture["fixture_id"]
            assert not result["abstain_reasons"], fixture["fixture_id"]


def test_every_classifier_result_has_canonical_write_false() -> None:
    for fixture in _fixtures():
        result = _classify_fixture(fixture)
        assert result["canonical_write"] is False, fixture["fixture_id"]


def test_cashflow_appendix_results_warn_against_income_statement_metric_inference() -> None:
    for fixture in _fixtures():
        if fixture["expected_document_type"] not in {"appendix_4c", "appendix_5b"}:
            continue

        result = _classify_fixture(fixture)
        warning_text = " ".join(result["warnings"]).lower()
        assert "cash-flow appendix" in warning_text, fixture["fixture_id"]
        assert "income-statement metric inference" in warning_text, fixture["fixture_id"]
        assert "revenue" in warning_text, fixture["fixture_id"]
        assert "npat" in warning_text, fixture["fixture_id"]
        assert "net debt" in warning_text, fixture["fixture_id"]


def test_appendix_4d_4e_review_only_metric_warnings_are_preserved() -> None:
    for fixture in _fixtures():
        if fixture["expected_document_type"] not in {"appendix_4d", "appendix_4e"}:
            continue

        source_text = " ".join(_walk_strings(fixture["source_text_surrogate"])).lower()
        assert any(term in source_text for term in ("eps", "nta", "dividend", "dividends"))

        result = _classify_fixture(fixture)
        warning_text = " ".join(result["warnings"]).lower()
        assert "review-only unsupported context" in warning_text, fixture["fixture_id"]
        assert "not canonical" in warning_text, fixture["fixture_id"]


def test_ambiguous_4d_4e_fixture_abstains() -> None:
    fixture = _load_json(FIXTURE_DIR / "ambiguous_appendix_4d_4e_abstain.json")
    result = _classify_fixture(fixture)
    assert result["document_type"] == "unknown_or_abstain"
    assert result["abstain"] is True
    assert result["abstain_reasons"]
    negative_text = " ".join(item["anchor"] for item in result["negative_evidence"])
    assert "Appendix 4D" in negative_text
    assert "Appendix 4E" in negative_text


def test_unknown_low_signal_fixture_abstains() -> None:
    fixture = _load_json(FIXTURE_DIR / "unknown_low_signal.json")
    result = _classify_fixture(fixture)
    assert result["document_type"] == "unknown_or_abstain"
    assert result["abstain"] is True
    assert "low signal" in " ".join(result["abstain_reasons"]).lower()


def test_classifier_module_imports_only_allowed_standard_library_modules() -> None:
    tree = ast.parse(CLASSIFIER_PATH.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots <= ALLOWED_CLASSIFIER_IMPORT_ROOTS


def test_classifier_is_not_imported_by_production_extraction_routing_files() -> None:
    for path in ROUTING_OWNER_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "asx_document_type_classifier" not in source, path
