"""
Eval harness for multipass extraction accuracy.

TWO MODES:
  Unit mode (default, no marker): loads fixtures + cached docling JSON.
      LLM calls mocked. Tests pipeline structure and schema only.
      Does NOT assert accuracy thresholds.

  Live eval mode (pytest -m live_eval): runs full pipeline against real LLM.
      Asserts per-metric accuracy >= thresholds in eval_config.json.
      Run manually before merging any extraction changes.
      Requires: llamacpp running on port 8001, eval_fixtures/*.json present.
"""
import json
import math
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "eval_fixtures"
CONFIG_PATH = Path(__file__).parent / "eval_config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def load_fixtures() -> list[dict]:
    if not FIXTURES_DIR.exists():
        return []
    return [
        json.loads(f.read_text())
        for f in sorted(FIXTURES_DIR.glob("*.json"))
        if f.name != ".gitkeep"
    ]


def metric_matches(extracted: float | None, expected: float | None,
                   tolerance: float) -> bool:
    """Returns True if extracted is within tolerance of expected."""
    if expected is None:
        return extracted is None  # null expected → must be null
    if extracted is None:
        return False  # value expected → must not be null
    if expected == 0:
        return abs(extracted) < 1  # near-zero
    return abs((extracted - expected) / expected) <= tolerance


# ---------------------------------------------------------------------------
# Unit mode: schema and structure tests (no real LLM)
# ---------------------------------------------------------------------------

def test_eval_config_exists_and_valid():
    """eval_config.json must exist and contain required keys."""
    config = load_config()
    assert "min_accuracy_overall" in config
    assert "min_accuracy_per_metric" in config
    assert "tolerances" in config
    assert config["min_accuracy_overall"] >= 0.5


def test_multipass_result_has_expected_keys():
    """MultipassResult payload must contain all METRIC_FIELDS + narrative fields."""
    from app.services.multipass_extraction import (
        MultipassResult, METRIC_FIELDS, _run_pass4_reconciler, _run_pass3b_narrative_extractor
    )

    mock_pass3a = [
        {"_source": "cashflow_statement", "operating_cf": 1_000_000, "investing_cf": None,
         "financing_cf": None, "cash_end": 500_000, "pass3_confidence": 0.9, "row_refs": {}}
    ]
    mock_pass3b = {
        "risk_summary": "Test risk", "risk_bullets": ["Risk 1"],
        "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.7
    }
    mock_pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(mock_pass3a, mock_pass3b, mock_pass1)

    assert "period_type" in payload
    assert "period_end" in payload
    assert "confidence_metrics" in payload
    assert "metrics" in payload
    assert all(m in payload["metrics"] for m in METRIC_FIELDS)
    assert "risk_summary" in payload
    assert "guidance_summary" in payload


def test_metric_match_within_tolerance():
    """Tolerance function must correctly identify acceptable values."""
    assert metric_matches(3_241_000, 3_241_000, 0.01)       # exact
    assert metric_matches(3_208_590, 3_241_000, 0.01)        # within 1%
    assert not metric_matches(2_900_000, 3_241_000, 0.01)    # outside 1%
    assert metric_matches(None, None, 0.01)                   # both null OK
    assert not metric_matches(None, 3_241_000, 0.01)          # missing value


# ---------------------------------------------------------------------------
# Live eval mode: accuracy regression gate (requires real LLM + fixtures)
# ---------------------------------------------------------------------------

@pytest.mark.live_eval
def test_live_eval_accuracy_against_fixtures():
    """
    Run the full pipeline against each fixture and assert accuracy >= thresholds.
    Requires: llamacpp on port 8001, eval_fixtures/*.json with pdf_filename present.
    """
    import httpx
    from app.services.multipass_extraction import run_multipass_extraction

    config = load_config()
    fixtures = load_fixtures()

    if not fixtures:
        pytest.skip("No eval fixtures found in eval_fixtures/. Add fixtures first.")

    tolerances = config["tolerances"]
    per_metric_results: dict[str, list[bool]] = {}
    overall_results: list[bool] = []

    import os
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        import anthropic
        llm_client = anthropic.Anthropic(api_key=anthropic_key)
        llm_client._extraction_model = os.getenv("EVAL_CLAUDE_MODEL", "claude-opus-4-6")
    else:
        headers = {}
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        llm_client = httpx.Client(base_url="http://127.0.0.1:8001/v1", timeout=60.0, headers=headers)

    for fixture in fixtures:
        root = Path(__file__).parent.parent.parent
        if "pdf_path" in fixture:
            pdf_path = str(root / fixture["pdf_path"])
        else:
            pdf_path = str(root / "data" / fixture["ticker"] / fixture["pdf_filename"])
        if not Path(pdf_path).exists():
            pytest.skip(f"PDF not found: {pdf_path}")

        doc_metadata = {
            "document_id": fixture["document_id"],
            "ticker": fixture["ticker"],
            "title": fixture.get("pdf_filename", ""),
        }
        result = run_multipass_extraction(pdf_path, doc_metadata, llm_client)

        for metric, expected_val in fixture["metrics"].items():
            tol = tolerances.get(metric, 0.01)
            extracted_val = result.payload.get("metrics", {}).get(metric)
            match = metric_matches(extracted_val, expected_val, tol)
            per_metric_results.setdefault(metric, []).append(match)
            overall_results.append(match)

        # Check expected nulls
        for null_metric in fixture.get("expected_nulls", []):
            val = result.payload.get("metrics", {}).get(null_metric)
            per_metric_results.setdefault(null_metric, []).append(val is None)
            overall_results.append(val is None)

    # Assert overall accuracy
    overall_acc = sum(overall_results) / len(overall_results) if overall_results else 0
    assert overall_acc >= config["min_accuracy_overall"], (
        f"Overall accuracy {overall_acc:.1%} below threshold {config['min_accuracy_overall']:.1%}"
    )

    # Assert per-metric accuracy
    for metric, min_acc in config["min_accuracy_per_metric"].items():
        if metric not in per_metric_results:
            continue
        acc = sum(per_metric_results[metric]) / len(per_metric_results[metric])
        assert acc >= min_acc, (
            f"{metric} accuracy {acc:.1%} below threshold {min_acc:.1%}"
        )
