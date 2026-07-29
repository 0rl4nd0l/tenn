import json
import re
from pathlib import Path


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "asx_document_type_classifier"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
FIXTURE_PATHS = sorted(path for path in FIXTURE_DIR.glob("*.json") if path.name != "manifest.json")

APPROVED_DOCUMENT_TYPES = {
    "annual_report",
    "half_year_report",
    "appendix_4c",
    "appendix_4d",
    "appendix_4e",
    "appendix_5b",
    "quarterly_report",
    "other_asx_announcement",
    "unknown_or_abstain",
}
CONFIDENCE_BANDS = {"high", "medium", "low", "abstain"}
REQUIRED_FIELDS = {
    "fixture_id",
    "document_id",
    "ticker",
    "expected_document_type",
    "expected_confidence_band",
    "expected_abstain",
    "source_text_surrogate",
    "positive_anchors",
    "negative_anchors",
    "required_evidence",
    "abstain_reasons",
    "must_not_infer_metrics",
    "canonical_write",
    "notes",
}
SOURCE_TEXT_KEYS = {
    "first_page_title_text",
    "asx_announcement_title",
    "headings",
    "table_captions",
    "relevant_line_anchors",
    "footer_form_labels",
}
SOURCE_TEXT_MAX_STRING_LENGTH = 180
SOURCE_TEXT_MAX_TOTAL_LENGTH = 900
CASHFLOW_TYPES = {"appendix_4c", "appendix_5b"}
CASHFLOW_FORBIDDEN_METRICS = ("revenue", "npat", "net debt")
UNSUPPORTED_REVIEW_RE = re.compile(r"\b(?:eps|nta|dividend|dividends)\b")
REVIEW_ONLY_MARKERS = ("review-only", "unsupported", "not canonical")


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    assert isinstance(loaded, dict), f"{path.name} must contain a JSON object"
    return loaded


def _fixtures() -> list[dict]:
    return [_load_json(path) for path in FIXTURE_PATHS]


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


def _lower_join(values: object) -> str:
    return " ".join(_walk_strings(values)).lower()


def test_all_fixture_json_files_parse_and_manifest_lists_them() -> None:
    assert FIXTURE_PATHS, "expected ASX document-type fixture files"
    manifest = _load_json(MANIFEST_PATH)
    manifest_files = manifest["fixture_files"]
    assert sorted(manifest_files) == sorted(path.name for path in FIXTURE_PATHS)
    for path in FIXTURE_PATHS:
        _load_json(path)


def test_every_fixture_has_required_fields_and_approved_enums() -> None:
    seen_ids: set[str] = set()
    for fixture in _fixtures():
        missing = REQUIRED_FIELDS - set(fixture)
        assert not missing, f"{fixture.get('fixture_id', '<unknown>')} missing {sorted(missing)}"
        assert fixture["fixture_id"] not in seen_ids
        seen_ids.add(fixture["fixture_id"])
        assert fixture["expected_document_type"] in APPROVED_DOCUMENT_TYPES
        assert fixture["expected_confidence_band"] in CONFIDENCE_BANDS
        assert isinstance(fixture["expected_abstain"], bool)
        assert isinstance(fixture["must_not_infer_metrics"], list)
        assert fixture["must_not_infer_metrics"]


def test_canonical_write_is_false_for_every_fixture_and_manifest() -> None:
    assert _load_json(MANIFEST_PATH)["canonical_write"] is False
    for fixture in _fixtures():
        assert fixture["canonical_write"] is False, fixture["fixture_id"]


def test_positive_anchor_and_abstain_contract() -> None:
    for fixture in _fixtures():
        positive_anchors = fixture["positive_anchors"]
        abstain_reasons = fixture["abstain_reasons"]
        if fixture["expected_abstain"]:
            assert abstain_reasons, fixture["fixture_id"]
            assert fixture["expected_confidence_band"] == "abstain"
        else:
            assert positive_anchors, fixture["fixture_id"]
            assert not abstain_reasons, fixture["fixture_id"]

    abstain_ids = {
        fixture["fixture_id"]
        for fixture in _fixtures()
        if fixture["expected_document_type"] == "unknown_or_abstain"
    }
    assert abstain_ids == {"unknown_low_signal", "ambiguous_appendix_4d_4e_abstain"}


def test_source_text_surrogates_are_small_and_structured() -> None:
    for fixture in _fixtures():
        surrogate = fixture["source_text_surrogate"]
        assert isinstance(surrogate, dict), fixture["fixture_id"]
        assert set(surrogate) == SOURCE_TEXT_KEYS
        strings = _walk_strings(surrogate)
        assert sum(len(text) for text in strings) <= SOURCE_TEXT_MAX_TOTAL_LENGTH
        for text in strings:
            assert len(text) <= SOURCE_TEXT_MAX_STRING_LENGTH, (
                fixture["fixture_id"],
                text,
            )
        for key in SOURCE_TEXT_KEYS - {"first_page_title_text", "asx_announcement_title"}:
            assert isinstance(surrogate[key], list), (fixture["fixture_id"], key)


def test_document_type_coverage_matches_approved_contract() -> None:
    covered_types = {fixture["expected_document_type"] for fixture in _fixtures()}
    assert APPROVED_DOCUMENT_TYPES <= covered_types


def test_cashflow_appendix_fixtures_do_not_imply_income_statement_metrics() -> None:
    for fixture in _fixtures():
        if fixture["expected_document_type"] not in CASHFLOW_TYPES:
            continue

        must_not = _lower_join(fixture["must_not_infer_metrics"])
        for metric in CASHFLOW_FORBIDDEN_METRICS:
            assert metric in must_not, (fixture["fixture_id"], metric)

        classifier_evidence = _lower_join(
            {
                "positive_anchors": fixture["positive_anchors"],
                "required_evidence": fixture["required_evidence"],
            }
        )
        for metric in CASHFLOW_FORBIDDEN_METRICS:
            assert metric not in classifier_evidence, (fixture["fixture_id"], metric)


def test_appendix_4d_4e_unsupported_metrics_are_review_only() -> None:
    for fixture in _fixtures():
        if fixture["expected_document_type"] not in {"appendix_4d", "appendix_4e", "unknown_or_abstain"}:
            continue

        for text in _walk_strings(fixture):
            lowered = text.lower()
            if UNSUPPORTED_REVIEW_RE.search(lowered):
                assert any(marker in lowered for marker in REVIEW_ONLY_MARKERS), (
                    fixture["fixture_id"],
                    text,
                )


def test_unknown_and_ambiguous_fixtures_abstain() -> None:
    fixtures_by_id = {fixture["fixture_id"]: fixture for fixture in _fixtures()}
    for fixture_id in {"unknown_low_signal", "ambiguous_appendix_4d_4e_abstain"}:
        fixture = fixtures_by_id[fixture_id]
        assert fixture["expected_document_type"] == "unknown_or_abstain"
        assert fixture["expected_abstain"] is True
        assert fixture["abstain_reasons"]
