#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.analysis_report_schema import validate_analysis_report  # noqa: E402


FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures" / "analysis_report_schema"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class AnalysisReportSchemaTests(unittest.TestCase):
    def test_valid_report_and_evidence_pass(self) -> None:
        report = _load_json("report_valid.json")
        evidence = _load_json("evidence_bundle_valid.json")
        result = validate_analysis_report(report=report, evidence_bundle=evidence, min_citation_coverage=0.95)
        self.assertTrue(result["ok"], msg=result)
        self.assertGreaterEqual(result["metrics"]["citation_coverage"], 0.95)

    def test_low_coverage_fails_gate(self) -> None:
        report = _load_json("report_low_coverage.json")
        evidence = _load_json("evidence_bundle_valid.json")
        result = validate_analysis_report(report=report, evidence_bundle=evidence, min_citation_coverage=0.95)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Citation coverage gate failed" in msg for msg in result["errors"]))

    def test_unknown_evidence_ids_fail(self) -> None:
        report = _load_json("report_unknown_evidence_id.json")
        evidence = _load_json("evidence_bundle_valid.json")
        result = validate_analysis_report(report=report, evidence_bundle=evidence, min_citation_coverage=0.95)
        self.assertFalse(result["ok"])
        self.assertTrue(any("unknown evidence_ids" in msg for msg in result["errors"]))


if __name__ == "__main__":
    unittest.main()
