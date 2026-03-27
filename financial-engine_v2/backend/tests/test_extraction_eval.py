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
import logging
import math
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

logger = logging.getLogger(__name__)

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
    model_label: str = "",
    llm_api_key_present: bool = False,
) -> None:
    """Write a machine-readable eval result JSON to tests/eval_results/.

    Written before assertions so the log is available even when the test fails.
    """
    results_dir = Path(__file__).parent / "eval_results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    log = {
        "timestamp": ts,
        "model": model_label,
        "llm_api_key_present": llm_api_key_present,
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


def test_expected_nulls_counted_in_accuracy():
    """expected_nulls assertions must be included in the accuracy calculation.

    A structural-only fixture (empty metrics, only expected_nulls) must produce
    accuracy == 1.0 when all expected-null metrics are actually null in the result,
    and accuracy == 0.0 when none of them are null.

    This test exercises the eval harness logic directly, without a real LLM or PDF.
    """
    null_metrics = ["revenue", "ebit", "np_attributable"]

    # Simulate result where all expected-null metrics are actually null
    def _run_harness(extracted_metrics: dict, expected_nulls: list[str]) -> float:
        """Run the expected_nulls evaluation loop from test_live_eval_accuracy_against_fixtures."""
        per_metric_results: dict[str, list[bool]] = {}
        overall_results: list[bool] = []
        for null_metric in expected_nulls:
            val = extracted_metrics.get(null_metric)
            ok = val is None
            per_metric_results.setdefault(null_metric, []).append(ok)
            overall_results.append(ok)
        return sum(overall_results) / len(overall_results) if overall_results else 0.0

    # All correctly null → accuracy 1.0
    all_null = {m: None for m in null_metrics}
    assert _run_harness(all_null, null_metrics) == 1.0, (
        "expected_nulls accuracy must be 1.0 when all expected-null metrics are null"
    )

    # All incorrectly populated → accuracy 0.0
    all_present = {m: 100_000 for m in null_metrics}
    assert _run_harness(all_present, null_metrics) == 0.0, (
        "expected_nulls accuracy must be 0.0 when all expected-null metrics have values"
    )

    # Partial: 2 of 3 null → accuracy 0.666…
    partial = {"revenue": None, "ebit": None, "np_attributable": 50_000}
    acc = _run_harness(partial, null_metrics)
    assert abs(acc - 2 / 3) < 1e-9, f"Expected 0.667, got {acc:.4f}"


def test_structural_fixture_with_only_expected_nulls_produces_valid_accuracy():
    """A fixture with empty metrics and only expected_nulls (GRE/EQR quarterly pattern)
    must produce a valid accuracy score that contributes to overall accuracy.

    Validates that the quarterly structural coverage path is correctly measured.
    """
    # Simulate a quarterly structural fixture (no asserted numeric values)
    fixture = {
        "metrics": {},
        "expected_nulls": ["revenue", "ebit", "np_attributable", "net_debt"],
        "config": {"min_accuracy_overall": 0.80},
    }
    # Simulated extraction result with income statement metrics correctly absent
    extracted_metrics = {
        "revenue": None, "ebit": None, "np_attributable": None, "net_debt": None,
        "operating_cf": 500_000, "cash_end": 2_000_000,
    }

    fixture_results: list[bool] = []

    # Metrics loop (empty for structural fixture)
    for metric, expected_val in fixture["metrics"].items():
        tol = 0.01
        extracted_val = extracted_metrics.get(metric)
        fixture_results.append(metric_matches(extracted_val, expected_val, tol))

    # Expected nulls loop (skip keys already counted in metrics loop)
    for null_metric in fixture.get("expected_nulls", []):
        if null_metric in fixture.get("metrics", {}):
            continue  # already counted in metrics loop
        val = extracted_metrics.get(null_metric)
        fixture_results.append(val is None)

    assert len(fixture_results) == 4, (
        f"Structural fixture must produce 4 accuracy data points (one per expected_null); "
        f"got {len(fixture_results)}"
    )
    assert all(fixture_results), (
        "All expected_null assertions must pass when income statement metrics are correctly null"
    )
    acc = sum(fixture_results) / len(fixture_results)
    assert acc >= fixture["config"]["min_accuracy_overall"], (
        f"Structural fixture accuracy {acc:.1%} must meet per-fixture threshold"
    )


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
    force_llamacpp = os.getenv("EVAL_FORCE_LLAMACPP", "").lower() in ("1", "true")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    llm_api_key_present = bool(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    if anthropic_key and not force_llamacpp:
        import anthropic
        llm_client = anthropic.Anthropic(api_key=anthropic_key)
        eval_model = os.getenv("EVAL_CLAUDE_MODEL", "claude-opus-4-6")
        llm_client._extraction_model = eval_model
        model_label = f"anthropic:{eval_model}"
    else:
        headers = {}
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        extraction_url = os.getenv("EXTRACTION_LLAMACPP_URL") or os.getenv("LLAMACPP_URL") or "http://127.0.0.1:8001"
        base_url = extraction_url.rstrip("/") + "/v1"
        llm_client = httpx.Client(base_url=base_url, timeout=60.0, headers=headers)
        model_label = f"llamacpp:{extraction_url}"

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

        # If extraction failed, mark all metrics as failures and skip comparison.
        if result.status == "failed":
            label = fixture.get("ticker", fixture.get("document_id", "?"))
            logger.error(
                "Extraction failed for %s: %s — marking all metrics as failures",
                label,
                result.error,
            )
            num_metrics = len(fixture["metrics"]) + len(
                [m for m in fixture.get("expected_nulls", []) if m not in fixture["metrics"]]
            ) + (1 if "period_end" in fixture else 0)
            for metric in fixture["metrics"]:
                per_metric_results.setdefault(metric, []).append(False)
            for null_metric in fixture.get("expected_nulls", []):
                if null_metric not in fixture["metrics"]:
                    per_metric_results.setdefault(null_metric, []).append(False)
            fixture_results_failed = [False] * num_metrics
            overall_results.extend(fixture_results_failed)
            fixture_min_acc = fixture.get("config", {}).get(
                "min_accuracy_overall", config["min_accuracy_overall"]
            )
            per_fixture_data[label] = {
                "accuracy": 0.0,
                "metric_count": num_metrics,
            }
            if fixture_min_acc > 0.0:
                fixture_failures.append(
                    f"{label}: FAILED (extraction error) < {fixture_min_acc:.1%}"
                )
            else:
                logger.info(
                    "Extraction failed for %s but min_accuracy is 0.0 — not a failure",
                    label,
                )
            continue

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

        # Check expected nulls (skip keys already counted in metrics loop)
        for null_metric in fixture.get("expected_nulls", []):
            if null_metric in fixture.get("metrics", {}):
                continue  # already counted in metrics loop
            val = result.payload.get("metrics", {}).get(null_metric)
            ok = val is None
            per_metric_results.setdefault(null_metric, []).append(ok)
            overall_results.append(ok)
            fixture_results.append(ok)

        # Check period_end if fixture specifies it
        if "period_end" in fixture:
            expected_pe = fixture["period_end"]
            extracted_pe = str(result.payload.get("period_end", ""))
            pe_match = expected_pe == extracted_pe
            fixture_results.append(pe_match)
            overall_results.append(pe_match)

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
    _write_eval_log(config, overall_acc, per_fixture_data, per_metric_results,
                    model_label=model_label, llm_api_key_present=llm_api_key_present)

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
