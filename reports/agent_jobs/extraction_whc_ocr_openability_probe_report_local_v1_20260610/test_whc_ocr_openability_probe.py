#!/usr/bin/env python3
"""Focused mocked tests for whc_ocr_openability_probe.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("whc_ocr_openability_probe.py")
SPEC = importlib.util.spec_from_file_location("whc_ocr_openability_probe", MODULE_PATH)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class FakeRunner:
    def __init__(self, fail_render: bool = False, fail_ocr: bool = False):
        self.fail_render = fail_render
        self.fail_ocr = fail_ocr
        self.calls = []

    def run(self, args, *, timeout=120):
        self.calls.append(args)
        if args[0] == "pdftoppm":
            if self.fail_render:
                return probe.CommandResult(args, 1, "", "render failed")
            prefix = Path(args[-1])
            page = args[2]
            (prefix.parent / f"{prefix.name}-{page}.png").write_text("fake image", encoding="utf-8")
            return probe.CommandResult(args, 0, "", "")
        if args[0] == "tesseract":
            if self.fail_ocr:
                return probe.CommandResult(args, 1, "", "ocr failed")
            return probe.CommandResult(
                args,
                0,
                "Consolidated statement of cash flows\n"
                "For the year ended 30 June 2022\n"
                "$000 $000\n"
                "Net cash from operating activities 2,529,823\n",
                "",
            )
        raise AssertionError(f"unexpected command: {args}")


def test_parse_whc_statement_ocr_rows_preserves_source_page_period_and_scale_text():
    text = (
        "Consolidated statement of comprehensive income\n"
        "For the year ended 30 June 2022\n"
        "$000 $000\n"
        "Revenue 4,920,102\n"
        "Finance expense (56,825)\n"
    )
    parsed = probe.parse_ocr_text(57, text, source="test")
    assert parsed["statement_label"] == "income_statement"
    assert parsed["period_phrases"] == ["For the year ended 30 June 2022"]
    assert parsed["scale_phrases"] == ["$000"]
    assert any("Revenue 4,920,102" in row["source_text"] for row in parsed["row_candidates"])
    assert "normalized_value" not in json.dumps(parsed)


def test_compare_saved_cache_flags_empty_statement_cells():
    cache_doc = {
        "extraction_method": "pymupdf",
        "page_count": 116,
        "source_pdf_page_count": 0,
        "sections": [{"page": 57, "text": "For personal use only"}],
        "tables": [
            {
                "page_number": 57,
                "caption": "For personal use only",
                "headers": ["", ""],
                "rows": [["", ""], ["", ""]],
            }
        ],
    }
    summary = probe.page_cache_summary(cache_doc, [57])
    assert summary["tables_present_on_statement_pages"] is True
    assert summary["statement_cells_preserved"] is False
    assert summary["gap_classification"] == "parser_openability_or_ocr_gap"


def test_sidecar_contract_has_no_canonical_metrics():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cache_path = root / "cache.json"
        source_diag_path = root / "source_diag.json"
        cache_path.write_text(
            json.dumps(
                {
                    "tables": [
                        {
                            "page_number": 57,
                            "caption": "",
                            "headers": ["", ""],
                            "rows": [["", ""], ["", ""]],
                        }
                    ],
                    "sections": [],
                }
            ),
            encoding="utf-8",
        )
        source_diag_path.write_text(
            json.dumps(
                {
                    "source_statement_evidence": [
                        {
                            "pdf_page": 57,
                            "statement": "Consolidated statement of comprehensive income",
                            "period": "For the year ended 30 June 2022",
                            "scale_evidence": "$000 $000",
                            "rows": ["Revenue 4,920,102"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        payload = probe.build_probe_payload(
            source_pdf=root / "source.pdf",
            cache_json=cache_path,
            source_diagnostic=source_diag_path,
            pages=[57],
            mode="saved-evidence",
        )
    payload_text = json.dumps(payload)
    assert payload["provenance_only"] is True
    assert payload["canonical_output_changed"] is False
    assert payload["parser_cache_written"] is False
    assert "accepted_metrics" not in payload
    assert "normalized_value" not in payload_text
    assert payload["summary"]["canonical_repair_ready"] is False


def test_missing_ocr_text_stays_data_missing():
    parsed = probe.parse_ocr_text(57, "For personal use only", source="test")
    assert parsed["verdict"] == "DATA_MISSING"
    assert parsed["statement_evidence_found"] is False
    assert parsed["row_candidates"] == []


def test_unbounded_page_request_rejected():
    try:
        probe.parse_pages("57,62")
    except ValueError as exc:
        assert "unapproved" in str(exc)
    else:
        raise AssertionError("expected unapproved page rejection")


def test_command_runner_failure_is_reported_not_promoted():
    records = probe.run_ocr_for_pages(
        Path("/tmp/nonexistent.pdf"),
        [56],
        runner=FakeRunner(fail_render=True),
    )
    assert records[0]["verdict"] == "DATA_MISSING"
    assert records[0]["error"] == "pdftoppm_failed"
    assert records[0]["statement_evidence_found"] is False


def test_mocked_ocr_path_extracts_provenance_only_record():
    records = probe.run_ocr_for_pages(
        Path("/tmp/nonexistent.pdf"),
        [60],
        runner=FakeRunner(),
    )
    assert records[0]["statement_label"] == "cashflow_statement"
    assert records[0]["scale_phrases"] == ["$000"]
    assert records[0]["row_candidate_count"] == 1


def test_report_local_write_rejects_non_report_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "report"
        root.mkdir()
        outside = Path(tmp) / "parser-cache.json"
        try:
            probe.write_report_local_json(outside, {"provenance_only": True}, report_root=root)
        except ValueError:
            pass
        else:
            raise AssertionError("expected non-report-local write rejection")


def run_all():
    tests = [
        test_parse_whc_statement_ocr_rows_preserves_source_page_period_and_scale_text,
        test_compare_saved_cache_flags_empty_statement_cells,
        test_sidecar_contract_has_no_canonical_metrics,
        test_missing_ocr_text_stays_data_missing,
        test_unbounded_page_request_rejected,
        test_command_runner_failure_is_reported_not_promoted,
        test_mocked_ocr_path_extracts_provenance_only_record,
        test_report_local_write_rejects_non_report_path,
    ]
    for test in tests:
        test()
    print(json.dumps({"ok": True, "tests": len(tests)}, sort_keys=True))


if __name__ == "__main__":
    run_all()
