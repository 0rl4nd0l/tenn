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


def test_conflicting_annual_and_quarterly_report_anchors_abstain() -> None:
    result = classify_asx_document_type(
        {
            "first_page_title_text": "Annual Report and Quarterly Report",
            "headings": ["Directors' report", "Financial statements"],
            "relevant_line_anchors": [
                "For the year ended 30 June 2025",
                "For the quarter ended 31 March 2025",
            ],
        }
    ).to_dict()

    assert result["document_type"] == "unknown_or_abstain"
    assert result["abstain"] is True
    assert "conflicting" in " ".join(result["abstain_reasons"]).lower()


def test_page_aware_collection_preserves_first_page_conflict_abstention() -> None:
    result = classify_asx_document_type(
        {
            "document_pages": [
                {
                    "page": 1,
                    "text": (
                        "Annual Report. Directors' report. Financial statements. "
                        "Quarterly Report. Quarter ended 31 March 2025."
                    ),
                }
            ]
        }
    ).to_dict()

    assert result["document_type"] == "unknown_or_abstain"
    assert result["abstain"] is True
    assert "conflicting" in " ".join(result["abstain_reasons"]).lower()


def test_appendix_4c_on_page_2_takes_precedence_over_generic_quarterly_cover() -> None:
    result = classify_asx_document_type(
        {
            "first_page_title_text": "Quarterly activities report",
            "document_pages": [
                {"page": 1, "text": "Quarterly activities report"},
                {
                    "page": 2,
                    "text": "Appendix 4C. Quarterly cash flow report. Rule 4.7B.",
                },
            ],
        }
    ).to_dict()

    assert result["document_type"] == "appendix_4c"
    assert result["abstain"] is False
    assert any(
        item["anchor"] == "Appendix 4C" and item["page"] == 2
        for item in result["positive_evidence"]
    )


def test_authoritative_appendix_title_survives_bare_later_repeat() -> None:
    result = classify_asx_document_type(
        {
            "asx_announcement_title": "Appendix 4C",
            "document_pages": [
                {"page": 1, "text": "Company logo"},
                {"page": 2, "text": "Appendix 4C"},
            ],
        }
    ).to_dict()

    assert result["document_type"] == "appendix_4c"
    assert result["abstain"] is False
    assert any(
        item["anchor"] == "Appendix 4C" and item["page"] is None
        for item in result["positive_evidence"]
    )


def test_page_evidence_aggregates_sections_before_matching() -> None:
    result = classify_asx_document_type(
        {
            "document_pages": [
                {"page": 1, "text": "Quarterly activities report"},
                {"page": 2, "text": "Appendix"},
                {
                    "page": 2,
                    "text": "4C. Quarterly cash flow report. Rule 4.7B.",
                },
            ]
        }
    ).to_dict()

    assert result["document_type"] == "appendix_4c"
    assert any(
        item["anchor"] == "Appendix 4C" and item["page"] == 2
        for item in result["positive_evidence"]
    )


def test_appendix_5b_late_in_quarterly_activities_bundle_is_collected_by_page() -> None:
    for appendix_page in (9, 11):
        result = classify_asx_document_type(
            {
                "document_pages": [
                    {"page": 1, "text": "Quarterly activities report"},
                    {
                        "page": appendix_page,
                        "text": (
                            "Appendix 5B. Mining exploration entity quarterly "
                            "cash flow report. Rule 5.5."
                        ),
                    },
                ]
            }
        ).to_dict()

        assert result["document_type"] == "appendix_5b"
        assert any(
            item["anchor"] == "Appendix 5B" and item["page"] == appendix_page
            for item in result["positive_evidence"]
        )


def test_annual_report_can_use_title_metadata_when_cover_text_is_low_signal() -> None:
    result = classify_asx_document_type(
        {
            "asx_announcement_title": "2025 Annual Report",
            "document_pages": [{"page": 1, "text": "Company logo"}],
        }
    ).to_dict()

    assert result["document_type"] == "annual_report"
    assert result["abstain"] is False
    assert any(
        item["anchor"] == "Annual Report" and item["page"] is None
        for item in result["positive_evidence"]
    )


def test_half_year_report_takes_whole_document_precedence_over_4d_wrapper() -> None:
    result = classify_asx_document_type(
        {
            "document_pages": [
                {
                    "page": 1,
                    "text": "Appendix 4D. Results for announcement to the market.",
                },
                {
                    "page": 4,
                    "text": (
                        "Half-Year Report. Interim financial report. "
                        "Condensed consolidated financial statements."
                    ),
                },
            ]
        }
    ).to_dict()

    assert result["document_type"] == "half_year_report"
    assert result["abstain"] is False
    assert any(item["page"] == 4 for item in result["positive_evidence"])


def test_page_match_takes_precedence_over_duplicate_title_anchor() -> None:
    result = classify_asx_document_type(
        {
            "asx_announcement_title": "Appendix 4D and Half-Year Results",
            "document_pages": [
                {
                    "page": 1,
                    "text": "Appendix 4D. Results for announcement to the market.",
                },
                {
                    "page": 4,
                    "text": (
                        "Half-Year Report. Interim financial report. "
                        "Condensed consolidated financial statements."
                    ),
                },
            ],
        }
    ).to_dict()

    assert result["document_type"] == "half_year_report"
    assert result["abstain"] is False
    assert any(item["page"] == 4 for item in result["positive_evidence"])


def test_later_complete_half_year_report_outweighs_repeated_wrapper_anchor() -> None:
    result = classify_asx_document_type(
        {
            "document_pages": [
                {
                    "page": 1,
                    "text": (
                        "Appendix 4D. Results for announcement to the market. "
                        "Interim financial report."
                    ),
                },
                {
                    "page": 4,
                    "text": (
                        "Half-Year Report. Interim financial report. "
                        "Condensed consolidated financial statements."
                    ),
                },
            ]
        }
    ).to_dict()

    assert result["document_type"] == "half_year_report"
    assert result["abstain"] is False
    assert any(item["page"] == 4 for item in result["positive_evidence"])


def test_same_page_4d_and_half_year_report_bundle_abstains() -> None:
    result = classify_asx_document_type(
        {
            "document_pages": [
                {
                    "page": 1,
                    "text": (
                        "Appendix 4D. Half-Year Report. Interim financial report. "
                        "Condensed consolidated financial statements."
                    ),
                }
            ]
        }
    ).to_dict()

    assert result["document_type"] == "unknown_or_abstain"
    assert result["abstain"] is True
    assert "conflicting" in " ".join(result["abstain_reasons"]).lower()


def test_half_year_bundle_abstains_on_high_annual_report_conflict() -> None:
    result = classify_asx_document_type(
        {
            "asx_announcement_title": "2025 Annual Report",
            "document_pages": [
                {
                    "page": 1,
                    "text": (
                        "Annual Report. Directors' report. Financial statements. "
                        "Appendix 4D. Results for announcement to the market."
                    ),
                },
                {
                    "page": 4,
                    "text": (
                        "Half-Year Report. Interim financial report. "
                        "Condensed consolidated financial statements."
                    ),
                },
            ],
        }
    ).to_dict()

    assert result["document_type"] == "unknown_or_abstain"
    assert result["abstain"] is True
    assert "conflicting" in " ".join(result["abstain_reasons"]).lower()


def test_deep_quarterly_reference_does_not_conflict_with_annual_report() -> None:
    result = classify_asx_document_type(
        {
            "asx_announcement_title": "2025 Annual Report",
            "document_pages": [
                {
                    "page": 1,
                    "text": (
                        "Annual Report. Directors' report. Financial statements."
                    ),
                },
                {
                    "page": 37,
                    "text": (
                        "See the Quarterly activities report for the quarter "
                        "ended 31 March 2025."
                    ),
                },
            ],
        }
    ).to_dict()

    assert result["document_type"] == "annual_report"
    assert result["abstain"] is False


def test_deep_bare_appendix_reference_does_not_override_annual_report() -> None:
    result = classify_asx_document_type(
        {
            "asx_announcement_title": "2025 Annual Report",
            "document_pages": [
                {
                    "page": 1,
                    "text": (
                        "Annual Report. Directors' report. Financial statements."
                    ),
                },
                {
                    "page": 52,
                    "text": "For prior quarterly disclosures, see Appendix 4C.",
                },
            ],
        }
    ).to_dict()

    assert result["document_type"] == "annual_report"
    assert result["abstain"] is False


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
