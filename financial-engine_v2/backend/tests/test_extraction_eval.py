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
import time
import warnings
from numbers import Real
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.services.extraction_eval import (
    ExtractionFixture,
    FixtureContext,
    MetricEvalStatus,
    evaluate_fixture,
)
from app.services.llamacpp_runtime import (
    _resolve_model_id,
    build_llm_headers,
    resolve_extraction_runtime_config,
    verify_llm_models,
)

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


def metric_matches(
    extracted: float | None, expected: float | None, tolerance: float
) -> bool:
    """Returns True if extracted is within tolerance of expected."""
    if not _is_real_number(tolerance):
        return False
    if expected is None:
        return extracted is None  # null expected → must be null
    if not _is_real_number(expected) or not _is_real_number(extracted):
        return False  # value expected → must not be null
    if expected == 0:
        return abs(extracted) < 1  # near-zero
    return abs((extracted - expected) / expected) <= tolerance


def _fixture_to_model(fixture: dict) -> ExtractionFixture:
    return ExtractionFixture(
        fixture_id=str(fixture.get("document_id") or fixture.get("ticker") or "?"),
        context=FixtureContext(
            period_end=fixture.get("period_end"),
            period_type=fixture.get("period_type"),
            currency=fixture.get("currency"),
            scale=fixture.get("scale"),
            accounting_basis=fixture.get("accounting_basis"),
        ),
        metrics=_coerce_fixture_numeric_map(fixture.get("metrics", {}), nulls=True),
        expected_nulls=[
            str(metric) for metric in fixture.get("expected_nulls", []) if metric
        ],
        optional_metrics=[],
        tolerances=_coerce_fixture_numeric_map(
            fixture.get("tolerances", {}),
            nulls=False,
        ),
    )


def _coerce_fixture_numeric_map(
    values: dict,
    *,
    nulls: bool,
) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for metric, value in values.items():
        if value is None and nulls:
            continue
        if not _is_real_number(value):
            raise ValueError(f"{metric} must be a finite real number")
        parsed[str(metric)] = float(value)
    return parsed


def _is_real_number(value: object) -> bool:
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _context_detail(
    fixture: dict,
    extracted_payload: dict[str, object],
) -> dict[str, dict[str, object]]:
    detail: dict[str, dict[str, object]] = {}
    fields = {
        "period_end": "period_end",
        "period_basis": "period_type",
        "currency": "currency",
        "scale": "scale",
        "accounting_basis": "accounting_basis",
    }
    for public_name, payload_name in fields.items():
        expected = fixture.get(payload_name)
        actual = extracted_payload.get(payload_name)
        detail[public_name] = {
            "expected": expected,
            "actual": actual,
            "matched": (
                expected is None
                or (
                    actual is not None
                    and str(expected).strip().lower() == str(actual).strip().lower()
                )
            ),
        }
    return detail


def _metric_outcome_class(status: MetricEvalStatus) -> str:
    if status in (MetricEvalStatus.ABSTAIN, MetricEvalStatus.QUARANTINE):
        return "abstained"
    return status.value


def _derive_trust_detail(
    metric_results: list[dict], context_mismatches: list[str]
) -> tuple[str, list[str]]:
    if context_mismatches:
        return "quarantine", [
            f"context_mismatch:{field}" for field in context_mismatches
        ]

    triggers = [
        f"{metric_result['metric_name']}:{metric_result['metric_status']}"
        for metric_result in metric_results
        if metric_result["metric_status"] != MetricEvalStatus.CORRECT.value
    ]
    if triggers:
        return "abstain", triggers
    return "trusted", []


def _serialize_metric_results(
    fixture_eval,
    extracted_payload: dict[str, object],
) -> list[dict[str, object]]:
    provenance = extracted_payload.get("provenance")
    provenance_map = provenance if isinstance(provenance, dict) else {}
    metric_results: list[dict[str, object]] = []
    for metric_eval in fixture_eval.metrics:
        metric_results.append(
            {
                "metric_name": metric_eval.metric,
                "metric_status": metric_eval.status.value,
                "expected_value_presence": metric_eval.expected is not None,
                "actual_value_presence": metric_eval.actual is not None,
                "expected_value": metric_eval.expected,
                "actual_value": metric_eval.actual,
                "outcome_class": _metric_outcome_class(metric_eval.status),
                "tolerance": metric_eval.tolerance,
                "reason": metric_eval.reason,
                "context_mismatch_flags": list(fixture_eval.context_mismatches),
                "provenance": provenance_map.get(metric_eval.metric),
            }
        )
    return metric_results


def _build_fixture_result_detail(
    fixture: dict,
    extracted_payload: dict[str, object],
) -> dict[str, object]:
    fixture_eval = evaluate_fixture(
        _fixture_to_model(fixture),
        extracted_payload.get("metrics", {})
        if isinstance(extracted_payload.get("metrics", {}), dict)
        else {},
        extracted_payload,
    )
    metric_results = _serialize_metric_results(fixture_eval, extracted_payload)
    trust_outcome, trust_triggers = _derive_trust_detail(
        metric_results,
        fixture_eval.context_mismatches,
    )
    failed_metrics = [
        metric_result["metric_name"]
        for metric_result in metric_results
        if metric_result["metric_status"] != MetricEvalStatus.CORRECT.value
    ]
    return {
        "context_ok": fixture_eval.context_ok,
        "context_mismatches": list(fixture_eval.context_mismatches),
        "context_detail": _context_detail(fixture, extracted_payload),
        "trust_outcome": trust_outcome,
        "trust_triggers": trust_triggers,
        "metric_results": metric_results,
        "failed_metrics": failed_metrics,
        "provenance_summary": fixture_eval.provenance_summary,
    }


def _select_seg_failure_debug_capture(
    *,
    extracted_payload: dict[str, object],
    pass3a_results: list[dict[str, object]] | None,
) -> dict[str, object]:
    selected_sources = {"balance_sheet", "share_capital"}
    selected_pass3a_outputs: dict[str, dict[str, object]] = {}
    for item in pass3a_results or []:
        source = str(item.get("_source") or "").strip()
        if source in selected_sources:
            selected_pass3a_outputs[source] = dict(item)

    provenance = extracted_payload.get("provenance")
    provenance_map = provenance if isinstance(provenance, dict) else {}
    selected_provenance = {
        metric: value
        for metric, value in provenance_map.items()
        if isinstance(value, str)
        and any(value.startswith(f"{source}:") for source in selected_sources)
    }

    return {
        "selected_pass3a_outputs": selected_pass3a_outputs,
        "selected_provenance": selected_provenance,
    }


def test_evaluate_fixture_uses_structured_field_provenance_summary() -> None:
    fixture = ExtractionFixture(
        fixture_id="BHP-2025",
        context=FixtureContext(
            period_end="2025-12-31",
            period_type="A",
            currency="AUD",
            scale="thousands",
        ),
        metrics={"revenue": 12_345_000.0},
        expected_nulls=[],
        optional_metrics=[],
        tolerances={},
    )
    payload = {
        "period_end": "2025-12-31",
        "period_type": "A",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {"revenue": 12_345_000.0},
        "field_provenance": {
            "revenue": {
                "metric": "revenue",
                "source": "income_statement",
                "table_label": "income_statement",
                "page_number": 7,
                "page_tag": "page_7",
                "row_ref": "Revenue from contracts with customers",
                "excerpt": "Revenue from contracts with customers",
                "scale": "thousands",
                "scale_source": "table",
                "currency": "AUD",
                "period_type": "A",
                "period_end": "2025-12-31",
            }
        },
    }

    result = evaluate_fixture(fixture, payload["metrics"], payload)

    assert result.provenance_summary["available"] is True
    assert result.provenance_summary["record_count"] == 1
    assert result.provenance_summary["status_counts"] == {"precise": 1}


def _validate_extraction_runtime_preflight(
    *, timeout: float = 30.0
) -> dict[str, object]:
    extraction_url, requested_model = resolve_extraction_runtime_config()
    headers = build_llm_headers(base_url=extraction_url)
    try:
        models_payload = verify_llm_models(
            extraction_url,
            headers=headers,
            timeout=timeout,
        )
    except Exception as exc:
        raise RuntimeError(
            "live eval preflight failed: could not verify extraction runtime "
            f"{extraction_url}/v1/models: {exc}"
        ) from exc

    data = models_payload.get("data")
    available_model_ids = sorted(
        str(row.get("id") or "").strip()
        for row in data
        if isinstance(data, list)
        and isinstance(row, dict)
        and str(row.get("id") or "").strip()
    )
    resolved_model = _resolve_model_id(models_payload, requested_model)
    if resolved_model not in available_model_ids:
        available_display = (
            ", ".join(available_model_ids) if available_model_ids else "<none>"
        )
        raise RuntimeError(
            "live eval preflight failed: extraction runtime "
            f"{extraction_url} does not expose requested extraction model "
            f"{requested_model!r}; available model ids: {available_display}. "
            "Likely wrong runtime on :8001; start the canonical router instead of a "
            "single-model llama-server."
        )

    return {
        "base_url": extraction_url,
        "requested_model": requested_model,
        "resolved_model": resolved_model,
        "headers": headers,
    }


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
            m: round(sum(v) / len(v), 4) for m, v in per_metric_results.items() if v
        },
        "thresholds": {
            "min_accuracy_overall": config["min_accuracy_overall"],
            "warn_threshold": config.get("warn_threshold"),
            "min_accuracy_per_metric": config.get("min_accuracy_per_metric", {}),
        },
    }
    path = results_dir / f"eval_{ts}.json"
    path.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _write_eval_progress(
    progress_path: Path,
    *,
    run_id: str,
    model_label: str,
    completed_fixtures: int,
    total_fixtures: int,
    fixture_statuses: dict[str, dict],
    current_fixture: str | None = None,
) -> None:
    progress_path.parent.mkdir(exist_ok=True)
    payload = {
        "run_id": run_id,
        "model": model_label,
        "completed_fixtures": completed_fixtures,
        "total_fixtures": total_fixtures,
        "current_fixture": current_fixture,
        "fixture_statuses": fixture_statuses,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    progress_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _emit_live_eval_progress(
    request: pytest.FixtureRequest | None, message: str
) -> None:
    reporter = None
    if request is not None:
        reporter = request.config.pluginmanager.getplugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(message)
    else:
        print(message, flush=True)


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
        MultipassResult,
        METRIC_FIELDS,
        _run_pass4_reconciler,
        _run_pass3b_narrative_extractor,
    )

    mock_pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 1_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": 500_000,
            "pass3_confidence": 0.9,
            "row_refs": {},
        }
    ]
    mock_pass3b = {
        "risk_summary": "Test risk",
        "risk_bullets": ["Risk 1"],
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.7,
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
    assert metric_matches(3_241_000, 3_241_000, 0.01)  # exact
    assert metric_matches(3_208_590, 3_241_000, 0.01)  # within 1%
    assert not metric_matches(2_900_000, 3_241_000, 0.01)  # outside 1%
    assert metric_matches(None, None, 0.01)  # both null OK
    assert not metric_matches(None, 3_241_000, 0.01)  # missing value
    assert not metric_matches(True, 1.0, 0.01)
    assert not metric_matches(1.0, True, 0.01)
    assert not metric_matches(1.0, 1.0, True)


@pytest.mark.parametrize(
    "fixture",
    [
        {"metrics": {"revenue": True}},
        {"metrics": {"revenue": 1.0}, "tolerances": {"revenue": False}},
    ],
)
def test_fixture_adapter_rejects_boolean_numbers(fixture):
    with pytest.raises(ValueError, match="finite real number"):
        _fixture_to_model(fixture)


def test_fixture_adapter_preserves_numeric_zero():
    fixture = _fixture_to_model(
        {"metrics": {"revenue": 0}, "tolerances": {"revenue": 0}}
    )

    assert fixture.metrics["revenue"] == 0.0
    assert fixture.tolerances["revenue"] == 0.0


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
        "revenue": None,
        "ebit": None,
        "np_attributable": None,
        "net_debt": None,
        "operating_cf": 500_000,
        "cash_end": 2_000_000,
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


def test_write_eval_progress_creates_incremental_status_file(tmp_path):
    progress_path = tmp_path / "eval_progress.json"
    fixture_statuses = {
        "QBE": {"status": "running"},
        "TLS": {"status": "pending"},
    }

    _write_eval_progress(
        progress_path,
        run_id="eval-test-run",
        model_label="llamacpp:http://127.0.0.1:8001",
        completed_fixtures=1,
        total_fixtures=2,
        fixture_statuses=fixture_statuses,
        current_fixture="TLS",
    )

    payload = json.loads(progress_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "eval-test-run"
    assert payload["completed_fixtures"] == 1
    assert payload["total_fixtures"] == 2
    assert payload["current_fixture"] == "TLS"
    assert payload["fixture_statuses"] == fixture_statuses


def test_fixture_result_detail_includes_metric_outcomes_and_context():
    fixture = {
        "document_id": "seg_h_fy2026_appendix4d",
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "accounting_basis": "statutory",
        "metrics": {
            "revenue": 73_671_000,
            "shares_outstanding": 280_874_770,
        },
        "expected_nulls": [],
        "tolerances": {
            "revenue": 0.01,
            "shares_outstanding": 0.001,
        },
    }
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "accounting_basis": "statutory",
        "metrics": {
            "revenue": 73_671_000,
            "shares_outstanding": 280_875,
        },
        "provenance": {
            "revenue": "income_statement:page_12:Revenue from continuing operations",
            "shares_outstanding": "share_capital:page_24:Balance at the end of the period",
        },
    }

    detail = _build_fixture_result_detail(fixture, payload)

    assert detail["context_ok"] is True
    assert detail["trust_outcome"] == "abstain"
    assert detail["trust_triggers"] == ["shares_outstanding:wrong"]
    assert detail["failed_metrics"] == ["shares_outstanding"]
    assert detail["context_detail"]["currency"]["matched"] is True
    assert detail["context_detail"]["period_basis"]["matched"] is True
    assert detail["context_detail"]["accounting_basis"]["matched"] is True
    assert set(detail["context_detail"]) == {
        "period_end",
        "period_basis",
        "currency",
        "scale",
        "accounting_basis",
    }

    by_metric = {item["metric_name"]: item for item in detail["metric_results"]}
    assert by_metric["revenue"]["outcome_class"] == "correct"
    assert by_metric["shares_outstanding"]["metric_status"] == "wrong"
    assert by_metric["shares_outstanding"]["expected_value_presence"] is True
    assert by_metric["shares_outstanding"]["actual_value_presence"] is True
    assert (
        by_metric["shares_outstanding"]["provenance"]
        == "share_capital:page_24:Balance at the end of the period"
    )


def test_seg_failure_debug_capture_filters_to_balance_sheet_and_share_capital():
    payload = {
        "provenance": {
            "shares_outstanding": "share_capital:page_24:Balance at the end of the period",
            "net_debt": "derived:balance_sheet:total_debt(13240)-cash_end(26716)",
            "revenue": "income_statement:page_12:Revenue from continuing operations",
        }
    }
    pass3a_results = [
        {
            "_source": "income_statement",
            "revenue": 73_671_000,
            "row_refs": {"revenue": "Revenue from continuing operations"},
        },
        {
            "_source": "share_capital",
            "shares_outstanding": 280_875,
            "row_refs": {"shares_outstanding": "Balance at the end of the period"},
        },
        {
            "_source": "balance_sheet",
            "total_debt": 13_240,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]

    capture = _select_seg_failure_debug_capture(
        extracted_payload=payload,
        pass3a_results=pass3a_results,
    )

    assert set(capture["selected_pass3a_outputs"]) == {
        "balance_sheet",
        "share_capital",
    }
    assert "income_statement" not in capture["selected_pass3a_outputs"]
    assert "shares_outstanding" in capture["selected_provenance"]
    assert "revenue" not in capture["selected_provenance"]


def test_extraction_runtime_preflight_accepts_router_extraction_model(monkeypatch):
    monkeypatch.setattr(
        "test_extraction_eval.resolve_extraction_runtime_config",
        lambda: ("http://127.0.0.1:8001", "qwen2.5-14b-instruct"),
    )
    monkeypatch.setattr(
        "test_extraction_eval.build_llm_headers",
        lambda *, base_url=None: {"Authorization": "Bearer local-openai-key"},
    )
    monkeypatch.setattr(
        "test_extraction_eval.verify_llm_models",
        lambda *args, **kwargs: {
            "data": [
                {
                    "id": "model:qwen2.5-14b-instruct",
                    "status": {
                        "value": "unloaded",
                        "args": [
                            "--model",
                            "/mnt/nvme/tenn/models/qwen2.5-14b-instruct.gguf",
                        ],
                    },
                }
            ]
        },
    )

    preflight = _validate_extraction_runtime_preflight()

    assert preflight["base_url"] == "http://127.0.0.1:8001"
    assert preflight["requested_model"] == "qwen2.5-14b-instruct"
    assert preflight["resolved_model"] == "model:qwen2.5-14b-instruct"
    assert preflight["headers"]["Authorization"] == "Bearer local-openai-key"


def test_extraction_runtime_preflight_fails_for_wrong_single_model_runtime(
    monkeypatch,
):
    monkeypatch.setattr(
        "test_extraction_eval.resolve_extraction_runtime_config",
        lambda: ("http://127.0.0.1:8001", "qwen2.5-14b-instruct"),
    )
    monkeypatch.setattr(
        "test_extraction_eval.build_llm_headers",
        lambda *, base_url=None: {"Authorization": "Bearer local-openai-key"},
    )
    monkeypatch.setattr(
        "test_extraction_eval.verify_llm_models",
        lambda *args, **kwargs: {
            "data": [
                {
                    "id": "model:gpt-oss-20b",
                    "status": {
                        "value": "loaded",
                        "args": [
                            "--model",
                            "/mnt/ssd/models/gpt-oss-20b-mxfp4.gguf",
                        ],
                    },
                }
            ]
        },
    )

    with pytest.raises(RuntimeError, match="Likely wrong runtime on :8001"):
        _validate_extraction_runtime_preflight()


# ---------------------------------------------------------------------------
# Live eval mode: accuracy regression gate (requires real LLM + fixtures)
# ---------------------------------------------------------------------------


@pytest.mark.live_eval
def test_live_eval_accuracy_against_fixtures(request: pytest.FixtureRequest):
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
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    progress_path = (
        Path(__file__).parent / "eval_results" / f"eval_progress_{run_id}.json"
    )
    fixture_statuses: dict[str, dict] = {}

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
        preflight = _validate_extraction_runtime_preflight()
        extraction_url = str(preflight["base_url"])
        headers = dict(preflight["headers"])
        base_url = extraction_url.rstrip("/") + "/v1"
        llm_client = httpx.Client(base_url=base_url, timeout=60.0, headers=headers)
        model_label = f"llamacpp:{extraction_url}"
        _emit_live_eval_progress(
            request,
            "[live-eval] preflight "
            f"runtime={extraction_url} "
            f"requested_model={preflight['requested_model']} "
            f"resolved_model={preflight['resolved_model']}",
        )

    _write_eval_progress(
        progress_path,
        run_id=run_id,
        model_label=model_label,
        completed_fixtures=0,
        total_fixtures=len(fixtures),
        fixture_statuses=fixture_statuses,
        current_fixture=None,
    )
    _emit_live_eval_progress(
        request,
        f"[live-eval] start run_id={run_id} fixtures={len(fixtures)} model={model_label} progress={progress_path.name}",
    )

    fixture_failures: list[str] = []

    for fixture_index, fixture in enumerate(fixtures, start=1):
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
        label = fixture.get("ticker", fixture.get("document_id", "?"))
        fixture_statuses[label] = {
            "status": "running",
            "index": fixture_index,
            "document_id": fixture["document_id"],
        }
        _write_eval_progress(
            progress_path,
            run_id=run_id,
            model_label=model_label,
            completed_fixtures=fixture_index - 1,
            total_fixtures=len(fixtures),
            fixture_statuses=fixture_statuses,
            current_fixture=label,
        )
        _emit_live_eval_progress(
            request,
            f"[live-eval] [{fixture_index}/{len(fixtures)}] start {label} ({fixture['document_id']})",
        )
        fixture_started_at = time.perf_counter()
        seg_debug_capture: dict[str, object] | None = {} if label == "SEG" else None
        result = run_multipass_extraction(
            pdf_path,
            doc_metadata,
            llm_client,
            debug_capture=seg_debug_capture,
        )

        # If extraction failed, mark all metrics as failures and skip comparison.
        if result.status == "failed":
            logger.error(
                "Extraction failed for %s: %s — marking all metrics as failures",
                label,
                result.error,
            )
            num_metrics = (
                len(fixture["metrics"])
                + len(
                    [
                        m
                        for m in fixture.get("expected_nulls", [])
                        if m not in fixture["metrics"]
                    ]
                )
                + (1 if "period_end" in fixture else 0)
            )
            fixture_min_acc = fixture.get("config", {}).get(
                "min_accuracy_overall", config["min_accuracy_overall"]
            )
            # Exclude structurally-limited fixtures from aggregate metrics
            if fixture_min_acc > 0.0:
                for metric in fixture["metrics"]:
                    per_metric_results.setdefault(metric, []).append(False)
                for null_metric in fixture.get("expected_nulls", []):
                    if null_metric not in fixture["metrics"]:
                        per_metric_results.setdefault(null_metric, []).append(False)
                fixture_results_failed = [False] * num_metrics
                overall_results.extend(fixture_results_failed)
            extracted_payload = (
                result.payload if isinstance(result.payload, dict) else {}
            )
            result_detail = _build_fixture_result_detail(fixture, extracted_payload)
            per_fixture_data[label] = {
                "accuracy": 0.0,
                "metric_count": num_metrics,
                **result_detail,
            }
            if label == "SEG":
                per_fixture_data[label]["seg_failure_debug"] = (
                    _select_seg_failure_debug_capture(
                        extracted_payload=extracted_payload,
                        pass3a_results=seg_debug_capture.get("pass3a_results")
                        if isinstance(seg_debug_capture, dict)
                        else None,
                    )
                )
            fixture_statuses[label] = {
                "status": "failed",
                "index": fixture_index,
                "document_id": fixture["document_id"],
                "elapsed_s": round(time.perf_counter() - fixture_started_at, 2),
                "accuracy": 0.0,
                "error": result.error,
                "evaluation": result_detail,
            }
            if label == "SEG":
                fixture_statuses[label]["seg_failure_debug"] = per_fixture_data[label][
                    "seg_failure_debug"
                ]
            _write_eval_progress(
                progress_path,
                run_id=run_id,
                model_label=model_label,
                completed_fixtures=fixture_index,
                total_fixtures=len(fixtures),
                fixture_statuses=fixture_statuses,
                current_fixture=None,
            )
            _emit_live_eval_progress(
                request,
                f"[live-eval] [{fixture_index}/{len(fixtures)}] done {label} status=failed elapsed={fixture_statuses[label]['elapsed_s']:.2f}s",
            )
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

        # Fixtures with min_accuracy_overall=0.0 are structurally limited (e.g.
        # garbled PDF fonts). Their per-metric results are excluded from the
        # aggregate per_metric_results and overall_results so they don't drag
        # down global accuracy with non-deterministic noise.
        exclude_from_aggregate = fixture_min_acc == 0.0

        for metric, expected_val in fixture["metrics"].items():
            tol = fixture_tolerances.get(metric, 0.01)
            extracted_val = result.payload.get("metrics", {}).get(metric)
            match = metric_matches(extracted_val, expected_val, tol)
            if not exclude_from_aggregate:
                per_metric_results.setdefault(metric, []).append(match)
                overall_results.append(match)
            fixture_results.append(match)

        # Check expected nulls (skip keys already counted in metrics loop)
        for null_metric in fixture.get("expected_nulls", []):
            if null_metric in fixture.get("metrics", {}):
                continue  # already counted in metrics loop
            val = result.payload.get("metrics", {}).get(null_metric)
            ok = val is None
            if not exclude_from_aggregate:
                per_metric_results.setdefault(null_metric, []).append(ok)
                overall_results.append(ok)
            fixture_results.append(ok)

        # Check period_end if fixture specifies it
        if "period_end" in fixture:
            expected_pe = fixture["period_end"]
            extracted_pe = str(result.payload.get("period_end", ""))
            pe_match = expected_pe == extracted_pe
            fixture_results.append(pe_match)
            if not exclude_from_aggregate:
                overall_results.append(pe_match)

        # Per-fixture accuracy gate
        fixture_acc = (
            sum(fixture_results) / len(fixture_results) if fixture_results else 0
        )
        result_detail = _build_fixture_result_detail(fixture, result.payload)
        per_fixture_data[label] = {
            "accuracy": round(fixture_acc, 4),
            "metric_count": len(fixture_results),
            **result_detail,
        }
        seg_failed = label == "SEG" and fixture_acc < fixture_min_acc
        if seg_failed:
            per_fixture_data[label]["seg_failure_debug"] = (
                _select_seg_failure_debug_capture(
                    extracted_payload=result.payload,
                    pass3a_results=seg_debug_capture.get("pass3a_results")
                    if isinstance(seg_debug_capture, dict)
                    else None,
                )
            )
        fixture_statuses[label] = {
            "status": result.status,
            "index": fixture_index,
            "document_id": fixture["document_id"],
            "elapsed_s": round(time.perf_counter() - fixture_started_at, 2),
            "accuracy": round(fixture_acc, 4),
            "evaluation": result_detail,
        }
        if seg_failed:
            fixture_statuses[label]["seg_failure_debug"] = per_fixture_data[label][
                "seg_failure_debug"
            ]
        _write_eval_progress(
            progress_path,
            run_id=run_id,
            model_label=model_label,
            completed_fixtures=fixture_index,
            total_fixtures=len(fixtures),
            fixture_statuses=fixture_statuses,
            current_fixture=None,
        )
        _emit_live_eval_progress(
            request,
            f"[live-eval] [{fixture_index}/{len(fixtures)}] done {label} status={result.status} accuracy={fixture_acc:.4f} elapsed={fixture_statuses[label]['elapsed_s']:.2f}s",
        )
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
    _write_eval_log(
        config,
        overall_acc,
        per_fixture_data,
        per_metric_results,
        model_label=model_label,
        llm_api_key_present=llm_api_key_present,
    )

    # Per-fixture failures reported first (most actionable)
    assert not fixture_failures, f"Per-fixture accuracy failures:\n" + "\n".join(
        f"  {f}" for f in fixture_failures
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
