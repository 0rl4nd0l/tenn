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
import datetime
import json
import math
import warnings
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


def _write_eval_log(
    config: dict,
    overall_acc: float,
    per_fixture_data: dict,
    per_metric_results: dict,
) -> None:
    """Write a machine-readable eval result JSON to tests/eval_results/.

    Written before assertions so the log is available even when the test fails.
    """
    results_dir = Path(__file__).parent / "eval_results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    log = {
        "timestamp": ts,
        "overall_accuracy": round(overall_acc, 4),
        "per_fixture": per_fixture_data,
        "per_metric": {
            m: round(sum(v) / len(v), 4)
            for m, v in per_metric_results.items()
            if v
        },
        "thresholds": {
            "min_accuracy_overall": config["min_accuracy_overall"],
            "warn_threshold": config.get("warn_threshold"),
            "min_accuracy_per_metric": config.get("min_accuracy_per_metric", {}),
        },
    }
    path = results_dir / f"eval_{ts}.json"
    path.write_text(json.dumps(log, indent=2), encoding="utf-8")


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
    per_fixture_data: dict[str, dict] = {}

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

    fixture_failures: list[str] = []

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

        # Per-fixture tolerances override global; per-fixture min_accuracy if set.
        fixture_tolerances = {**tolerances, **fixture.get("tolerances", {})}
        fixture_min_acc = fixture.get("config", {}).get(
            "min_accuracy_overall", config["min_accuracy_overall"]
        )
        fixture_results: list[bool] = []

        for metric, expected_val in fixture["metrics"].items():
            tol = fixture_tolerances.get(metric, 0.01)
            extracted_val = result.payload.get("metrics", {}).get(metric)
            match = metric_matches(extracted_val, expected_val, tol)
            per_metric_results.setdefault(metric, []).append(match)
            overall_results.append(match)
            fixture_results.append(match)

        # Check expected nulls
        for null_metric in fixture.get("expected_nulls", []):
            val = result.payload.get("metrics", {}).get(null_metric)
            ok = val is None
            per_metric_results.setdefault(null_metric, []).append(ok)
            overall_results.append(ok)
            fixture_results.append(ok)

        # Per-fixture accuracy gate
        fixture_acc = sum(fixture_results) / len(fixture_results) if fixture_results else 0
        label = fixture.get("ticker", fixture.get("document_id", "?"))
        per_fixture_data[label] = {
            "accuracy": round(fixture_acc, 4),
            "metric_count": len(fixture_results),
        }
        if fixture_acc < fixture_min_acc:
            fixture_failures.append(
                f"{label}: {fixture_acc:.1%} < {fixture_min_acc:.1%}"
            )

    # Emit warnings for metrics approaching the failure threshold.
    # warn_threshold is a soft floor — fires before the hard gate to give early notice.
    warn_threshold = config.get("warn_threshold", 0.0)
    if warn_threshold > 0:
        for metric, results in sorted(per_metric_results.items()):
            metric_acc = sum(results) / len(results) if results else 0.0
            if metric_acc < warn_threshold:
                warnings.warn(
                    f"eval warn: '{metric}' accuracy {metric_acc:.1%} below "
                    f"warn_threshold {warn_threshold:.1%}",
                    UserWarning,
                    stacklevel=2,
                )

    overall_acc = sum(overall_results) / len(overall_results) if overall_results else 0

    # Structured eval log written before assertions so it exists even on failure.
    _write_eval_log(config, overall_acc, per_fixture_data, per_metric_results)

    # Per-fixture failures reported first (most actionable)
    assert not fixture_failures, (
        f"Per-fixture accuracy failures:\n" + "\n".join(f"  {f}" for f in fixture_failures)
    )

    # Overall accuracy across all fixtures
    assert overall_acc >= config["min_accuracy_overall"], (
        f"Overall accuracy {overall_acc:.1%} below threshold {config['min_accuracy_overall']:.1%}"
    )

    # Per-metric accuracy across all fixtures
    for metric, min_acc in config["min_accuracy_per_metric"].items():
        if metric not in per_metric_results:
            continue
        acc = sum(per_metric_results[metric]) / len(per_metric_results[metric])
        assert acc >= min_acc, (
            f"{metric} accuracy {acc:.1%} below threshold {min_acc:.1%}"
        )
