"""Tests for CompanyDossierService (JSONL-backed per-ticker research memory)."""

from __future__ import annotations

import json

import pytest

from cockpit.core.research.dossier import CompanyDossierService


# ------------------------------------------------------------------
# Happy path: save() then recall() returns the saved finding
# ------------------------------------------------------------------


def test_save_then_recall(tmp_path):
    """Save a finding, then recall it for the same ticker."""
    svc = CompanyDossierService(root=tmp_path)
    save_result = svc.save("BHP", "Revenue up 10%", "annual_report", confidence=0.8)

    assert save_result["ok"] is True
    assert save_result["ticker"] == "BHP"
    assert save_result["entries"] == 1

    recall_result = svc.recall("BHP")
    assert recall_result["ok"] is True
    assert recall_result["total"] == 1
    assert len(recall_result["findings"]) == 1
    assert recall_result["findings"][0]["finding"] == "Revenue up 10%"
    assert recall_result["findings"][0]["confidence"] == 0.8


# ------------------------------------------------------------------
# Isolation: recall for ticker A does not return findings for ticker B
# ------------------------------------------------------------------


def test_ticker_isolation(tmp_path):
    """Findings for BHP do not appear when recalling CSL."""
    svc = CompanyDossierService(root=tmp_path)
    svc.save("BHP", "Iron ore production steady", "analyst_note")
    svc.save("CSL", "Plasma demand rising", "industry_report")

    bhp = svc.recall("BHP")
    csl = svc.recall("CSL")

    assert bhp["total"] == 1
    assert bhp["findings"][0]["finding"] == "Iron ore production steady"

    assert csl["total"] == 1
    assert csl["findings"][0]["finding"] == "Plasma demand rising"


# ------------------------------------------------------------------
# Corrupt JSONL: one malformed line is skipped, valid lines returned
# ------------------------------------------------------------------


def test_corrupt_jsonl_skipped(tmp_path):
    """Malformed JSONL line is skipped; valid lines returned."""
    svc = CompanyDossierService(root=tmp_path)
    svc.save("RIO", "Good finding", "source_a")

    # Inject a corrupt line into the JSONL file.
    ticker_path = tmp_path / "RIO.jsonl"
    with ticker_path.open("a", encoding="utf-8") as f:
        f.write("{this is not valid json\n")
        f.write(json.dumps({
            "ticker": "RIO",
            "finding": "Second good finding",
            "source": "source_b",
            "source_url": "",
            "confidence": 0.6,
            "category": "general",
            "ts": "2026-03-27T00:00:00+00:00",
        }) + "\n")

    result = svc.recall("RIO")
    assert result["ok"] is True
    assert result["total"] == 2  # 2 valid lines (corrupt skipped)
    findings_text = [f["finding"] for f in result["findings"]]
    assert "Good finding" in findings_text
    assert "Second good finding" in findings_text


def test_recall_nonexistent_ticker(tmp_path):
    """Recall for a ticker with no dossier returns empty list."""
    svc = CompanyDossierService(root=tmp_path)
    result = svc.recall("XYZ")

    assert result["ok"] is True
    assert result["findings"] == []
    assert result["total"] == 0


def test_save_empty_finding_rejected(tmp_path):
    """Save with empty ticker or finding returns error."""
    svc = CompanyDossierService(root=tmp_path)
    result = svc.save("", "something", "source")
    assert result["ok"] is False

    result = svc.save("BHP", "   ", "source")
    assert result["ok"] is False
