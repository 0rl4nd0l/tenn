"""Comprehensive tests for the strategy decision pipeline:
ThesisService, RiskGate, and ReflectionService.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from cockpit.core.research.reflection import ReflectionService, _assess_outcome
from cockpit.core.research.risk_gate import RiskGate
from cockpit.core.research.thesis import VALID_SIGNALS, ThesisService


# =====================================================================
# ThesisService tests
# =====================================================================


class TestThesisServiceCreate:
    """Tests for ThesisService.create()."""

    def test_create_happy_path(self, tmp_path: object) -> None:
        """Create a BUY thesis for BHP — verify structure and JSONL file."""
        svc = ThesisService(root=tmp_path)
        result = svc.create("BHP", "Strong iron ore demand", signal="BUY")

        assert result["ok"] is True
        thesis = result["thesis"]
        assert thesis["ticker"] == "BHP"
        assert thesis["signal"] == "BUY"
        assert thesis["status"] == "active"
        assert thesis["supporting_evidence"] == []
        assert thesis["disconfirming_evidence"] == []
        assert thesis["thesis_statement"] == "Strong iron ore demand"
        assert thesis["risk_assessment"] is None
        assert 0.0 <= thesis["confidence"] <= 1.0

        # Verify JSONL file was created.
        jsonl_path = tmp_path / "BHP.jsonl"
        assert jsonl_path.exists()
        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 1
        stored = json.loads(lines[0])
        assert stored["id"] == thesis["id"]

    def test_create_invalid_signal(self, tmp_path: object) -> None:
        """Invalid signal returns ok=False with error message."""
        svc = ThesisService(root=tmp_path)
        result = svc.create("BHP", "Some thesis", signal="INVALID")

        assert result["ok"] is False
        assert "Invalid signal" in result["error"]
        assert "INVALID" in result["error"]

    def test_create_normalizes_ticker_case(self, tmp_path: object) -> None:
        """Ticker is uppercased regardless of input."""
        svc = ThesisService(root=tmp_path)
        result = svc.create("bhp", "Thesis", signal="HOLD")
        assert result["thesis"]["ticker"] == "BHP"

    def test_create_invalid_thesis_type_defaults_neutral(
        self, tmp_path: object
    ) -> None:
        """Invalid thesis_type silently defaults to neutral."""
        svc = ThesisService(root=tmp_path)
        result = svc.create("BHP", "Thesis", thesis_type="garbage")
        assert result["thesis"]["thesis_type"] == "neutral"


class TestThesisServiceEvidence:
    """Tests for ThesisService.add_evidence() and auto_evaluate()."""

    def test_add_supporting_evidence(self, tmp_path: object) -> None:
        """Add supporting evidence — verify count increases."""
        svc = ThesisService(root=tmp_path)
        svc.create("BHP", "Strong demand", signal="BUY")

        result = svc.add_evidence("BHP", "Iron ore prices rising", is_supporting=True)
        assert result["ok"] is True
        assert result["evidence_type"] == "supporting"
        assert result["total_supporting"] == 1
        assert result["total_disconfirming"] == 0

    def test_disconfirming_evidence_triggers_auto_evaluate(
        self, tmp_path: object
    ) -> None:
        """3 disconfirming with 0 supporting triggers auto-invalidation."""
        svc = ThesisService(root=tmp_path)
        svc.create("BHP", "Strong demand", signal="BUY")

        svc.add_evidence("BHP", "Risk 1", is_supporting=False)
        svc.add_evidence("BHP", "Risk 2", is_supporting=False)
        result = svc.add_evidence("BHP", "Risk 3", is_supporting=False)

        assert result["ok"] is True
        assert result.get("auto_invalidated") is True

        # Verify thesis status is now invalidated.
        active = svc.get_active("BHP")
        assert len(active) == 0

    def test_auto_evaluate_below_threshold(self, tmp_path: object) -> None:
        """1 disconfirming + 2 supporting stays active (ratio < 2:1)."""
        svc = ThesisService(root=tmp_path)
        svc.create("BHP", "Strong demand", signal="BUY")

        svc.add_evidence("BHP", "Pro 1", is_supporting=True)
        svc.add_evidence("BHP", "Pro 2", is_supporting=True)
        svc.add_evidence("BHP", "Con 1", is_supporting=False)

        result = svc.auto_evaluate("BHP")
        assert result["ok"] is True
        assert result["status_changed"] is False

        active = svc.get_active("BHP")
        assert len(active) == 1

    def test_auto_evaluate_ratio_trigger(self, tmp_path: object) -> None:
        """1 supporting + 3 disconfirming triggers invalidation (3 >= 2*1)."""
        svc = ThesisService(root=tmp_path)
        svc.create("BHP", "Strong demand", signal="BUY")

        svc.add_evidence("BHP", "Pro 1", is_supporting=True)
        svc.add_evidence("BHP", "Con 1", is_supporting=False)
        svc.add_evidence("BHP", "Con 2", is_supporting=False)
        # Third disconfirming triggers via add_evidence's auto_evaluate call.
        svc.add_evidence("BHP", "Con 3", is_supporting=False)

        result = svc.auto_evaluate("BHP")
        # Thesis already invalidated by now, so no active thesis.
        assert result["ok"] is False  # No active thesis to evaluate.

        active = svc.get_active("BHP")
        assert len(active) == 0

    def test_add_evidence_no_active_thesis(self, tmp_path: object) -> None:
        """Adding evidence with no active thesis returns ok=False."""
        svc = ThesisService(root=tmp_path)
        result = svc.add_evidence("BHP", "Some finding")
        assert result["ok"] is False
        assert "No active thesis" in result["error"]


class TestThesisServiceGetActive:
    """Tests for ThesisService.get_active()."""

    def test_filters_correctly(self, tmp_path: object) -> None:
        """Only active theses are returned."""
        svc = ThesisService(root=tmp_path)
        r1 = svc.create("BHP", "Thesis 1", signal="BUY")
        r2 = svc.create("BHP", "Thesis 2", signal="HOLD")

        # Invalidate the first.
        svc.invalidate("BHP", r1["thesis"]["id"], reason="test")

        active = svc.get_active("BHP")
        assert len(active) == 1
        assert active[0]["id"] == r2["thesis"]["id"]


class TestThesisServiceExpireStale:
    """Tests for ThesisService.expire_stale()."""

    def test_expires_old_theses(self, tmp_path: object) -> None:
        """Thesis older than threshold gets expired."""
        svc = ThesisService(root=tmp_path)
        svc.create("BHP", "Old thesis", signal="BUY")

        # Backdate the thesis to 100 days ago.
        path = tmp_path / "BHP.jsonl"
        theses = []
        for line in path.read_text().strip().split("\n"):
            t = json.loads(line)
            old_dt = datetime.now(timezone.utc) - timedelta(days=100)
            t["created_at"] = old_dt.isoformat()
            theses.append(t)
        with path.open("w") as f:
            for t in theses:
                f.write(json.dumps(t) + "\n")

        result = svc.expire_stale(days=90)
        assert result["ok"] is True
        assert result["expired_count"] == 1
        assert "BHP" in result["tickers_affected"]

        active = svc.get_active("BHP")
        assert len(active) == 0

    def test_does_not_expire_recent_theses(self, tmp_path: object) -> None:
        """Recent thesis is not expired."""
        svc = ThesisService(root=tmp_path)
        svc.create("BHP", "Fresh thesis", signal="BUY")

        result = svc.expire_stale(days=90)
        assert result["ok"] is True
        assert result["expired_count"] == 0

        active = svc.get_active("BHP")
        assert len(active) == 1


# =====================================================================
# RiskGate tests
# =====================================================================


class TestRiskGateAssess:
    """Tests for RiskGate.assess()."""

    def _make_backend(
        self,
        bull_text: str = "Strong growth outlook",
        bear_text: str = "Valuation concerns",
        judge_json: str | None = None,
    ) -> Mock:
        """Create a mock backend that returns persona responses."""
        if judge_json is None:
            judge_json = json.dumps(
                {
                    "adjusted_signal": "BUY",
                    "risk_level": "medium",
                    "key_risks": ["commodity price risk"],
                    "synthesis": "Bull case prevails.",
                    "confidence": 0.7,
                }
            )

        backend = Mock()
        # synthesize_research is called 3 times: bull, bear, judge.
        backend.synthesize_research.side_effect = [
            {"raw_text": bull_text},
            {"raw_text": bear_text},
            {"raw_text": judge_json},
        ]
        return backend

    def test_assess_happy_path(self) -> None:
        """Full bull/bear/judge pipeline with mock backend."""
        backend = self._make_backend()
        gate = RiskGate(backend_client=backend)

        result = gate.assess("BHP", "BUY", context={"thesis": "Strong demand"})

        assert result["ok"] is True
        assert result["ticker"] == "BHP"
        assert result["bull_case"] == "Strong growth outlook"
        assert result["bear_case"] == "Valuation concerns"
        assert result["judge_synthesis"] == "Bull case prevails."
        assert result["adjusted_signal"] in VALID_SIGNALS
        assert result["risk_level"] in ("low", "medium", "high")
        assert backend.synthesize_research.call_count == 3

    def test_assess_backend_unavailable(self) -> None:
        """No backend — returns HOLD fallback with high risk."""
        gate = RiskGate(backend_client=None)
        result = gate.assess("BHP", "BUY", context={})

        assert result["ok"] is True
        assert result["adjusted_signal"] == "HOLD"
        assert result["risk_level"] == "high"

    def test_assess_calls_backend_with_supported_contract_shape(self) -> None:
        """RiskGate sends ticker+gathered_sources+focus to BackendApiClient."""

        class StrictBackend:
            def __init__(self) -> None:
                self.calls: list[tuple[str, dict[str, Any], str | None]] = []

            def synthesize_research(
                self,
                *,
                ticker: str,
                gathered_sources: dict[str, Any],
                focus: str | None = None,
            ) -> dict[str, Any]:
                self.calls.append((ticker, gathered_sources, focus))
                if focus == "risk_gate_judge":
                    return {
                        "summary": "Bear case outweighs upside in the near term.",
                        "sentiment": "bearish",
                        "confidence": 0.4,
                        "risks": ["Execution risk", "Commodity downside"],
                    }
                return {"summary": f"{focus} response"}

        backend = StrictBackend()
        gate = RiskGate(backend_client=backend)

        result = gate.assess("BHP", "BUY", context={"thesis": "Cycle turning"})

        assert len(backend.calls) == 3
        assert {call[2] for call in backend.calls} == {
            "risk_gate_bull",
            "risk_gate_bear",
            "risk_gate_judge",
        }
        for ticker, gathered, _focus in backend.calls:
            assert ticker == "BHP"
            assert "risk_gate" in gathered
            assert isinstance(gathered["risk_gate"], dict)
        assert result["adjusted_signal"] in VALID_SIGNALS
        assert result["risk_level"] in ("low", "medium", "high")

    def test_assess_judge_returns_invalid_json(self) -> None:
        """Garbled judge output falls back to HOLD with confidence=0.3."""
        backend = Mock()
        backend.synthesize_research.side_effect = [
            {"raw_text": "bull argument"},
            {"raw_text": "bear argument"},
            {"raw_text": "this is not valid json at all!!!"},
        ]
        gate = RiskGate(backend_client=backend)

        result = gate.assess("BHP", "BUY", context={})

        assert result["adjusted_signal"] == "HOLD"
        assert result["confidence"] == 0.3

    def test_assess_with_situation_memory(self) -> None:
        """Past situations are populated when situation_memory is provided."""
        backend = self._make_backend()
        memory = Mock()
        memory.recall.return_value = [
            {"situation": "BHP BUY — strong Q2", "outcome": "price +8%"},
        ]
        gate = RiskGate(backend_client=backend, situation_memory=memory)

        result = gate.assess("BHP", "BUY", context={"thesis": "Strong demand"})

        assert len(result["similar_past_situations"]) == 1
        memory.recall.assert_called_once()


class TestRiskGateParseJudge:
    """Tests for RiskGate._parse_judge() static method."""

    def test_valid_json(self) -> None:
        """Valid JSON is parsed correctly."""
        raw = json.dumps(
            {
                "adjusted_signal": "BUY",
                "risk_level": "low",
                "key_risks": ["risk1"],
                "synthesis": "Looks good.",
                "confidence": 0.8,
            }
        )
        result = RiskGate._parse_judge(raw)
        assert result["adjusted_signal"] == "BUY"
        assert result["risk_level"] == "low"
        assert result["key_risks"] == ["risk1"]

    def test_markdown_fenced_json(self) -> None:
        """JSON wrapped in ```json ... ``` fences is parsed."""
        inner = json.dumps(
            {
                "adjusted_signal": "SELL",
                "risk_level": "high",
                "key_risks": ["downtrend"],
                "synthesis": "Bearish.",
                "confidence": 0.6,
            }
        )
        raw = f"```json\n{inner}\n```"
        result = RiskGate._parse_judge(raw)
        assert result["adjusted_signal"] == "SELL"
        assert result["risk_level"] == "high"

    def test_invalid_signal_defaults_hold(self) -> None:
        """Invalid signal in judge output defaults to HOLD."""
        raw = json.dumps(
            {
                "adjusted_signal": "YOLO",
                "risk_level": "medium",
                "key_risks": [],
                "synthesis": "Confused.",
                "confidence": 0.5,
            }
        )
        result = RiskGate._parse_judge(raw)
        assert result["adjusted_signal"] == "HOLD"

    def test_unparseable_text_fallback(self) -> None:
        """Non-JSON text returns fallback dict."""
        result = RiskGate._parse_judge("I think you should buy it.")
        assert result["adjusted_signal"] == "HOLD"
        assert result["confidence"] == 0.3
        assert "Could not parse" in result["key_risks"][0]


class TestRiskGateFormatContext:
    """Tests for RiskGate._format_context()."""

    def test_builds_readable_context(self) -> None:
        """Context with thesis, score_data, technicals produces expected text."""
        gate = RiskGate(backend_client=None)
        ctx = {
            "thesis": "Strong iron ore demand",
            "score_data": {
                "composite_score": 75,
                "financial_health": 80,
                "momentum_score": 70,
                "valuation_score": 65,
                "technical_score": 72,
            },
            "technicals": {
                "rsi_14": 55,
                "trend_regime": "uptrend",
            },
        }
        text = gate._format_context("BHP", "BUY", ctx)
        assert "Thesis: Strong iron ore demand" in text
        assert "Composite score: 75/100" in text
        assert "RSI=55" in text
        assert "trend=uptrend" in text

    def test_empty_context(self) -> None:
        """Empty context returns fallback message."""
        gate = RiskGate(backend_client=None)
        text = gate._format_context("BHP", "BUY", {})
        assert "No context available" in text


# =====================================================================
# ReflectionService tests
# =====================================================================


class TestReflectionRecordDecision:
    """Tests for ReflectionService.record_decision_context()."""

    def test_creates_snapshot_file(self, tmp_path: object) -> None:
        """Decision snapshot is written as JSON at the expected path."""
        svc = ReflectionService(root=tmp_path)
        score_data = {"composite_score": 72, "financial_health": 80}

        decision_id = svc.record_decision_context(
            "BHP",
            "BUY",
            thesis="Strong demand",
            score_data=score_data,
        )

        assert decision_id.startswith("BHP_")
        snapshot_path = tmp_path / f"{decision_id}.json"
        assert snapshot_path.exists()

        data = json.loads(snapshot_path.read_text())
        assert data["ticker"] == "BHP"
        assert data["signal"] == "BUY"
        assert data["thesis"] == "Strong demand"
        assert data["composite_score"] == 72
        assert data["financial_health"] == 80
        assert data["reflected"] is False


class TestReflectionCheckOutcome:
    """Tests for ReflectionService.check_outcome()."""

    def test_with_price_change(self, tmp_path: object) -> None:
        """Price went up — verify price_change_pct is positive for BUY."""
        mock_router = Mock()
        # First call: record_decision_context price lookup.
        # Second call: check_outcome price lookup.
        mock_router.get_price_context_for_window.side_effect = [
            {"price_state": {"last_close": 40.0}},
            {"price_state": {"last_close": 50.0}},
        ]
        svc = ReflectionService(root=tmp_path, tool_router=mock_router)
        svc.record_decision_context("BHP", "BUY", thesis="Test")

        result = svc.check_outcome("BHP")
        assert result["ok"] is True
        assert result["price_change_pct"] == 25.0
        assert result["outcome_quality"] == "good"  # BUY + price up 25%

    def test_no_snapshot_found(self, tmp_path: object) -> None:
        """No decision for ticker returns ok=False."""
        svc = ReflectionService(root=tmp_path)
        result = svc.check_outcome("XYZ")
        assert result["ok"] is False
        assert "No decision snapshot" in result["error"]


class TestReflectionReflectAndLearn:
    """Tests for ReflectionService.reflect_and_learn()."""

    def test_records_to_situation_memory(self, tmp_path: object) -> None:
        """Reflect records (situation, outcome) to SituationMemory."""
        mock_router = Mock()
        mock_router.get_price_context_for_window.side_effect = [
            {"price_state": {"last_close": 40.0}},
            {"price_state": {"last_close": 44.0}},
        ]
        mock_memory = Mock()
        svc = ReflectionService(
            root=tmp_path,
            situation_memory=mock_memory,
            tool_router=mock_router,
        )
        svc.record_decision_context("BHP", "BUY", thesis="Iron ore thesis")

        result = svc.reflect_and_learn("BHP")
        assert result["ok"] is True
        assert result["recorded_to_memory"] is True
        mock_memory.add.assert_called_once()

        # Verify snapshot marked as reflected.
        snapshot_files = list(tmp_path.glob("BHP_*.json"))
        assert len(snapshot_files) == 1
        data = json.loads(snapshot_files[0].read_text())
        assert data["reflected"] is True


class TestReflectionReviewOpenDecisions:
    """Tests for ReflectionService.review_open_decisions()."""

    def test_finds_old_unreflected_decisions(self, tmp_path: object) -> None:
        """Snapshot older than 30 days with reflected=False is returned."""
        svc = ReflectionService(root=tmp_path)

        # Create a backdated snapshot manually.
        old_dt = datetime.now(timezone.utc) - timedelta(days=35)
        decision_id = f"BHP_{old_dt.strftime('%Y%m%dT%H%M%S')}"
        snapshot = {
            "decision_id": decision_id,
            "ticker": "BHP",
            "signal": "BUY",
            "thesis": "Old thesis",
            "composite_score": 60,
            "price_at_decision": 40.0,
            "ts": old_dt.isoformat(),
            "reflected": False,
        }
        (tmp_path / f"{decision_id}.json").write_text(json.dumps(snapshot))

        results = svc.review_open_decisions()
        assert len(results) == 1
        assert results[0]["ticker"] == "BHP"
        assert results[0]["days_elapsed"] >= 35

    def test_excludes_reflected_decisions(self, tmp_path: object) -> None:
        """Reflected snapshot is excluded from review."""
        svc = ReflectionService(root=tmp_path)

        old_dt = datetime.now(timezone.utc) - timedelta(days=35)
        decision_id = f"BHP_{old_dt.strftime('%Y%m%dT%H%M%S')}"
        snapshot = {
            "decision_id": decision_id,
            "ticker": "BHP",
            "signal": "BUY",
            "thesis": "Old thesis",
            "ts": old_dt.isoformat(),
            "reflected": True,  # Already reflected.
        }
        (tmp_path / f"{decision_id}.json").write_text(json.dumps(snapshot))

        results = svc.review_open_decisions()
        assert len(results) == 0


class TestAssessOutcome:
    """Tests for the module-level _assess_outcome() function."""

    @pytest.mark.parametrize(
        ("signal", "price_pct", "expected"),
        [
            # BUY + price up 10% = good.
            ("BUY", 10.0, "good"),
            # BUY + price down 5% = bad.
            ("BUY", -5.0, "bad"),
            # BUY + price down 1% = neutral (within -3 threshold).
            ("BUY", -1.0, "neutral"),
            # OVERWEIGHT + price up 8% = good.
            ("OVERWEIGHT", 8.0, "good"),
            # SELL + price down 10% = good.
            ("SELL", -10.0, "good"),
            # SELL + price up 5% = bad.
            ("SELL", 5.0, "bad"),
            # UNDERWEIGHT + price down 8% = good.
            ("UNDERWEIGHT", -8.0, "good"),
            # HOLD + price flat = good (abs < 10).
            ("HOLD", 0.0, "good"),
            # HOLD + price flat 5% = good.
            ("HOLD", 5.0, "good"),
            # HOLD + price swing 15% = neutral.
            ("HOLD", 15.0, "neutral"),
            # None price = unknown.
            ("BUY", None, "unknown"),
        ],
    )
    def test_signal_direction_logic(
        self, signal: str, price_pct: float | None, expected: str
    ) -> None:
        assert _assess_outcome(signal, price_pct) == expected
