from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import system_analyzer


def test_build_artifact_paths_enforces_data_root():
    paths = system_analyzer.build_artifact_paths("run-123")

    assert set(paths) >= {"latest_report", "history_report", "patch_candidate"}
    for value in paths.values():
        assert value.startswith("/data/")


def test_validate_artifact_path_rejects_non_data_paths():
    with pytest.raises(ValueError, match="/data"):
        system_analyzer.validate_artifact_path("/app/reports/system_analyzer/latest.json")


def test_detect_write_path_drifts_flags_repo_report_writes():
    drifts = system_analyzer.detect_write_path_drifts(
        {
            "financial-engine_v2/backend/app/main.py": 'RUNTIME_EMBEDDING_MODEL_FILE = PROJECT_ROOT / "reports" / "runtime_embedding_model.txt"',
            "financial-engine_v2/backend/app/services/router_metrics.py": '_REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"',
            "financial-engine_v2/scripts/benchmark_models.py": 'default=str(ROOT / "reports" / "model_benchmark.json")',
        }
    )

    kinds = {drift["kind"] for drift in drifts}
    assert "write_path_violation" in kinds
    assert any("runtime_embedding_model.txt" in drift["details"] for drift in drifts)


def test_detect_router_chain_drifts_flags_reasoning_mismatch():
    config = SimpleNamespace(
        router=SimpleNamespace(model_name="router-model", provider="llamacpp", base_url="http://router"),
        coding=SimpleNamespace(model_name="coding-model", provider="llamacpp", base_url="http://coding"),
    )
    reasoning_fallback = SimpleNamespace(
        model_name="wrong-model",
        provider="llamacpp",
        base_url="http://wrong",
        execution_queue="llm_cpu",
    )
    coding_fallback = SimpleNamespace(
        model_name="coding-model",
        provider="llamacpp",
        base_url="http://coding",
        execution_queue="llm_gpu",
    )

    drifts = system_analyzer.detect_router_chain_drifts(
        config,
        reasoning_fallback=reasoning_fallback,
        coding_fallback=coding_fallback,
    )

    assert any(drift["kind"] == "router_chain_mismatch" for drift in drifts)


def test_compute_scorecard_marks_missing_metrics_without_fabrication():
    scorecard = system_analyzer.compute_scorecard(
        checks=[
            {"name": "backend_health", "result": "passed", "severity": "high"},
            {"name": "router_chain", "result": "passed", "severity": "high"},
        ],
        drifts=[],
        metrics_snapshot={},
        benchmark_report={},
    )

    signal_map = {signal["name"]: signal["value"] for signal in scorecard["signals"]}
    assert signal_map["latency"] == system_analyzer.DATA_MISSING
    assert signal_map["throughput"] == system_analyzer.DATA_MISSING
    assert signal_map["fallback_frequency"] == system_analyzer.DATA_MISSING
    assert signal_map["timeout_error_rate"] == system_analyzer.DATA_MISSING
    assert 0.0 <= scorecard["overall_score"] <= 1.0


def test_run_analyzer_loop_defaults_to_recommend_only():
    report = system_analyzer.run_analyzer_loop(
        write_report=False,
        snapshot_collector=lambda: {"backend": {"status": "ok"}},
        drift_detector=lambda snapshot: [],
        scoring_engine=lambda checks, drifts, metrics_snapshot, benchmark_report: {
            "overall_score": 1.0,
            "signals": [],
        },
        planner=lambda report: [{"class": "no_op", "summary": "stable"}],
    )

    assert report["loop_mode"] == "recommend"
    assert report["safe_state"] == "recommend"
    assert report["optimizer"]["auto_apply"] is False


def test_run_analyzer_loop_returns_partial_report_on_failure():
    report = system_analyzer.run_analyzer_loop(
        write_report=False,
        snapshot_collector=lambda: (_ for _ in ()).throw(TimeoutError("backend timeout")),
    )

    assert report["status"] == "partial"
    assert report["safe_state"] == "recommend"
    assert any(check["result"] == "failed" for check in report["checks"])
