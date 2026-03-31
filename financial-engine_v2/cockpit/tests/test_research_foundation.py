"""Comprehensive tests for research foundation modules: dossier, situation memory, alerts.

These are the persistence layer that everything else builds on.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from cockpit.core.research.dossier import CompanyDossierService
from cockpit.core.research.situation_memory import SituationMemory, _tokenize
from cockpit.core.research.alerts import AlertReader


# ============================================================
# CompanyDossierService
# ============================================================


class TestCompanyDossierSaveRecallRoundTrip:
    """Test 1: save() + recall() round-trip."""

    def test_save_and_recall_single_finding(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        result = svc.save(
            "BHP",
            "Revenue grew 15%",
            "annual report",
            confidence=0.8,
            category="financials",
        )
        assert result["ok"] is True
        assert result["ticker"] == "BHP"
        assert result["entries"] == 1

        recalled = svc.recall("BHP")
        assert recalled["ok"] is True
        assert recalled["total"] == 1
        assert len(recalled["findings"]) == 1

        f = recalled["findings"][0]
        assert f["ticker"] == "BHP"
        assert "Revenue grew 15%" in f["finding"]
        assert f["source"] == "annual report"
        assert f["confidence"] == 0.8
        assert f["category"] == "financials"
        assert "ts" in f


class TestCompanyDossierMultipleFindings:
    """Test 2: save() multiple findings, recall returns most recent first."""

    def test_most_recent_first_with_limit(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        # Save 3 findings; each gets a timestamp in order.
        svc.save("BHP", "Finding A", "src-a", category="a")
        svc.save("BHP", "Finding B", "src-b", category="b")
        svc.save("BHP", "Finding C", "src-c", category="c")

        recalled = svc.recall("BHP", limit=2)
        assert recalled["total"] == 3
        assert len(recalled["findings"]) == 2
        # Most recent first — C before B.
        assert "Finding C" in recalled["findings"][0]["finding"]
        assert "Finding B" in recalled["findings"][1]["finding"]


class TestCompanyDossierKeywordFilter:
    """Test 3: recall() keyword filter."""

    def test_keyword_filters_findings(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        svc.save("BHP", "Earnings grew 10%", "report", category="financials")
        svc.save("BHP", "New CEO appointed", "news", category="governance")
        svc.save("BHP", "Iron ore prices up", "market", category="commodities")

        # Filter by keyword in finding text.
        recalled = svc.recall("BHP", query="earnings")
        assert len(recalled["findings"]) == 1
        assert "Earnings grew 10%" in recalled["findings"][0]["finding"]

    def test_keyword_matches_category(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        svc.save("BHP", "Some finding", "src", category="earnings")

        recalled = svc.recall("BHP", query="earnings")
        assert len(recalled["findings"]) == 1


class TestCompanyDossierEmptyRecall:
    """Test 4: recall() empty dossier returns empty list."""

    def test_empty_dossier(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        recalled = svc.recall("NONEXISTENT")
        assert recalled["ok"] is True
        assert recalled["findings"] == []
        assert recalled["total"] == 0


class TestCompanyDossierInputValidation:
    """Test 5: save() validates inputs."""

    def test_empty_ticker(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        result = svc.save("", "Some finding", "src")
        assert result["ok"] is False
        assert "required" in result["error"]

    def test_empty_finding(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        result = svc.save("BHP", "  ", "src")
        assert result["ok"] is False
        assert "required" in result["error"]


class TestCompanyDossierListTickers:
    """Test 6: list_tickers() returns all tickers with data."""

    def test_lists_tickers(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        svc.save("BHP", "Finding 1", "src")
        svc.save("CSL", "Finding 2", "src")

        tickers = svc.list_tickers()
        assert "BHP" in tickers
        assert "CSL" in tickers
        assert len(tickers) == 2


class TestCompanyDossierSummary:
    """Test 7: summary() formats readable text."""

    def test_summary_includes_key_info(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        svc.save("BHP", "Revenue up", "annual report", category="financials", confidence=0.9)
        svc.save("BHP", "Dividend cut", "news", category="governance", confidence=0.7)
        svc.save("BHP", "New mine opened", "press release", category="operations", confidence=0.6)

        text = svc.summary("BHP")
        assert "BHP" in text
        assert "financials" in text or "governance" in text or "operations" in text
        # Includes entry count header.
        assert "3 total entries" in text

    def test_summary_empty_ticker(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        text = svc.summary("NOTHING")
        assert "No dossier entries" in text


class TestCompanyDossierAgeLabels:
    """Test 8: recall() age labels prepended to findings."""

    def test_today_label(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        svc.save("BHP", "Fresh finding", "src")

        recalled = svc.recall("BHP")
        assert recalled["findings"][0]["finding"].startswith("[today]")

    def test_old_finding_label(self, tmp_path: Path) -> None:
        svc = CompanyDossierService(root=tmp_path / "dossiers")
        # Write a record with an old timestamp directly.
        old_ts = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        record = {
            "ticker": "BHP",
            "finding": "Old finding",
            "source": "archive",
            "source_url": "",
            "confidence": 0.5,
            "category": "general",
            "ts": old_ts,
        }
        path = (tmp_path / "dossiers" / "BHP.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        recalled = svc.recall("BHP")
        # 45 days -> "~1 months ago"
        assert "[~1 months ago]" in recalled["findings"][0]["finding"]


# ============================================================
# SituationMemory
# ============================================================


class TestSituationMemoryRoundTrip:
    """Test 9: add() + recall() round-trip.

    BM25 requires multiple documents with varied vocabularies to produce
    positive IDF scores. A single-document corpus yields 0 or negative
    scores, so we add several entries to make the index meaningful.
    """

    def test_add_and_recall(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("BHP revenue surged after iron ore rally", "stock rose 8%")
        mem.add("CSL drug pipeline update", "pharma sector lifted")
        mem.add("RBA kept interest rates on hold", "banks flat")
        mem.add("Woolworths logistics disruption hit margins", "retail dipped")

        results = mem.recall("iron ore price increase")
        assert len(results) >= 1
        assert results[0]["score"] > 0
        assert "iron ore rally" in results[0]["situation"]
        assert "stock rose 8%" in results[0]["outcome"]


class TestSituationMemoryTopN:
    """Test 10: recall() returns top N matches.

    BM25 IDF needs vocabulary diversity across documents to produce
    positive scores. We add a few unrelated entries so the shared terms
    in the target entries become discriminative.
    """

    def test_limit_results(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        # Add unrelated entries so BM25 IDF has contrast.
        mem.add("completely unrelated banking sector news", "banks moved")
        mem.add("foreign exchange rate volatility increased", "AUD weakened")
        for i in range(5):
            mem.add(f"situation {i} with keyword alpha", f"outcome {i}")

        results = mem.recall("keyword alpha situation", n=2)
        assert len(results) == 2


class TestSituationMemoryBM25Ranking:
    """Test 11: BM25 ranks relevant matches higher."""

    def test_relevance_ranking(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("BHP revenue up 20% after iron ore price surge", "stock rallied")
        mem.add("CSL pipeline drug approval boosted shares", "pharma gains")
        mem.add("RIO iron ore production record quarter", "mining sector up")

        results = mem.recall("iron ore price mining", n=3)
        # BHP and RIO should be in the top results (both mention iron ore).
        situation_texts = [r["situation"] for r in results]
        top_two_text = " ".join(situation_texts[:2]).lower()
        assert "iron ore" in top_two_text


class TestSituationMemoryEmptyRecall:
    """Test 12: recall() empty memory returns empty list."""

    def test_empty_memory(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        results = mem.recall("anything at all")
        assert results == []


class TestSituationMemoryEmptyStrings:
    """Test 13: add() empty strings rejected."""

    def test_empty_situation_rejected(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("", "outcome")
        assert len(mem._entries) == 0

    def test_empty_outcome_rejected(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("situation", "")
        assert len(mem._entries) == 0

    def test_whitespace_only_rejected(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("   ", "   ")
        assert len(mem._entries) == 0


class TestSituationMemoryPersistence:
    """Test 14: persistence survives reload."""

    def test_reload_from_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "situations.jsonl"
        mem1 = SituationMemory(path=path)
        mem1.add("iron ore prices crashed sharply", "BHP stock dropped 12%")
        mem1.add("interest rates cut by RBA", "property stocks rallied")
        mem1.add("gold mining output fell in WA", "gold equities dipped")
        mem1.add("wheat exports surged on drought fears", "agri stocks up")

        # Create a new instance from the same file.
        mem2 = SituationMemory(path=path)
        assert len(mem2._entries) == 4
        results = mem2.recall("iron ore crash")
        assert len(results) >= 1
        assert "iron ore" in results[0]["situation"].lower()


class TestSituationMemoryKeywordFallback:
    """Test 15: keyword fallback works without rank_bm25."""

    def test_keyword_recall_directly(self, tmp_path: Path) -> None:
        mem = SituationMemory(path=tmp_path / "situations.jsonl")
        mem.add("gold prices surged dramatically", "miners rallied")
        mem.add("tech sector fell on rate hikes", "growth stocks down")

        # Call _keyword_recall directly to test the fallback path.
        results = mem._keyword_recall("gold prices mining surge")
        assert len(results) >= 1
        assert "gold" in results[0]["situation"].lower()
        assert results[0]["score"] > 0

    def test_tokenize_function(self) -> None:
        tokens = _tokenize("Iron Ore Prices  UP")
        assert tokens == ["iron", "ore", "prices", "up"]


# ============================================================
# AlertReader
# ============================================================


class TestAlertReaderRoundTrip:
    """Test 16: write_alert() + get() round-trip."""

    def test_write_and_get(self, tmp_path: Path) -> None:
        alert_path = tmp_path / "alerts" / "pending.jsonl"
        AlertReader.write_alert(
            path=alert_path,
            ticker="BHP",
            alert_type="price_move",
            message="BHP up 5% on earnings beat",
        )

        reader = AlertReader(path=alert_path)
        result = reader.get()
        assert result["ok"] is True
        assert result["total"] == 1

        alert = result["alerts"][0]
        assert alert["ticker"] == "BHP"
        assert alert["type"] == "price_move"
        assert alert["message"] == "BHP up 5% on earnings beat"
        assert alert["seen"] is False
        assert "id" in alert
        assert "ts" in alert


class TestAlertReaderTimeFiltering:
    """Test 17: get() time filtering."""

    def test_filters_by_time(self, tmp_path: Path) -> None:
        alert_path = tmp_path / "alerts" / "pending.jsonl"
        alert_path.parent.mkdir(parents=True, exist_ok=True)

        # Write a recent alert via the API.
        AlertReader.write_alert(
            path=alert_path,
            ticker="BHP",
            alert_type="price_move",
            message="Recent alert",
        )

        # Manually write an old alert (2 days ago).
        old_ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        old_alert = {
            "id": "old123",
            "ticker": "CSL",
            "type": "news",
            "message": "Old alert",
            "data": {},
            "ts": old_ts,
            "seen": False,
        }
        with alert_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(old_alert) + "\n")

        reader = AlertReader(path=alert_path)

        # since_hours=1 should include the recent one.
        recent = reader.get(since_hours=1)
        assert recent["total"] == 1
        assert recent["alerts"][0]["ticker"] == "BHP"

        # since_hours=24 should exclude the 2-day-old one.
        day_result = reader.get(since_hours=24)
        assert day_result["total"] == 1
        assert day_result["alerts"][0]["ticker"] == "BHP"

        # since_hours=72 should include both.
        wide = reader.get(since_hours=72)
        assert wide["total"] == 2


class TestAlertReaderTickerFiltering:
    """Test 18: get() ticker filtering."""

    def test_filters_by_ticker(self, tmp_path: Path) -> None:
        alert_path = tmp_path / "alerts" / "pending.jsonl"
        AlertReader.write_alert(
            path=alert_path, ticker="BHP", alert_type="price", message="BHP alert"
        )
        AlertReader.write_alert(
            path=alert_path, ticker="CSL", alert_type="news", message="CSL alert"
        )

        reader = AlertReader(path=alert_path)
        bhp_only = reader.get(ticker="BHP")
        assert bhp_only["total"] == 1
        assert bhp_only["alerts"][0]["ticker"] == "BHP"


class TestAlertReaderMarkSeen:
    """Test 19: mark_seen() marks alerts."""

    def test_mark_seen(self, tmp_path: Path) -> None:
        alert_path = tmp_path / "alerts" / "pending.jsonl"
        AlertReader.write_alert(
            path=alert_path, ticker="BHP", alert_type="price", message="Alert 1"
        )
        AlertReader.write_alert(
            path=alert_path, ticker="CSL", alert_type="news", message="Alert 2"
        )

        reader = AlertReader(path=alert_path)
        # Get alerts to find the IDs.
        alerts = reader.get()["alerts"]
        assert len(alerts) == 2

        # Mark the first one as seen.
        first_id = alerts[0]["id"]
        count = reader.mark_seen([first_id])
        assert count == 1

        # Re-read and verify.
        updated = reader.get()["alerts"]
        seen_map = {a["id"]: a["seen"] for a in updated}
        assert seen_map[first_id] is True
        # The other should remain unseen.
        other_id = [a["id"] for a in alerts if a["id"] != first_id][0]
        assert seen_map[other_id] is False


class TestAlertReaderEmptyFile:
    """Test 20: get() empty/nonexistent file."""

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        reader = AlertReader(path=tmp_path / "does_not_exist" / "alerts.jsonl")
        result = reader.get()
        assert result["ok"] is True
        assert result["alerts"] == []
        assert result["total"] == 0


class TestAlertReaderCreatesDirectory:
    """Test 21: write_alert() creates directory if needed."""

    def test_creates_dir(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "alerts.jsonl"
        assert not deep_path.parent.exists()

        AlertReader.write_alert(
            path=deep_path,
            ticker="BHP",
            alert_type="test",
            message="Test alert",
        )

        assert deep_path.parent.exists()
        assert deep_path.exists()

        # Verify it can be read back.
        reader = AlertReader(path=deep_path)
        result = reader.get()
        assert result["total"] == 1
