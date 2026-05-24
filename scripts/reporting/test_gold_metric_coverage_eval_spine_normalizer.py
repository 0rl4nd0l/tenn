from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.reporting import eval_spine_manifest
from scripts.reporting import gold_metric_coverage_eval_spine_normalizer as normalizer


def _write_task_card(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "job_id: gold_metric_coverage_eval_spine_normalizer_v1_20260524",
                "lane: Evaluation",
                "owner: Codex",
                "allowed_files:",
                "  - docs/agent_tasks/gold_metric_coverage_eval_spine_normalizer_v1_20260524.md",
                "approval_required: false",
                "allow_unapproved_safe_extension: true",
                "timeout_seconds: 300",
                "output_dir: reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524",
                "mutation_mode: safe_extension",
                "production_data_access: false",
                "---",
                "",
                "# Gold normalizer",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _inventory() -> dict[str, object]:
    return {
        "canonical_core": {
            "document_count": 10,
            "metric_check_count": 24,
            "metrics": ["revenue", "operating_cash_flow", "net_debt"],
        },
        "expanded_required": {
            "document_count": 15,
            "metric_check_count": 39,
            "metrics": ["revenue", "operating_cash_flow", "net_debt"],
        },
        "confirmed_metric_coverage": {
            "fixture_count": 15,
            "total_expectations": 146,
            "scorable_count": 73,
            "candidate_count": 70,
            "ambiguous_count": 3,
            "unsupported_count": 0,
        },
        "confirmed_unscored": ["ebit", "cash_end"],
        "ambiguous_or_derived": ["free_cash_flow"],
        "unsupported": ["ebitda"],
    }


def test_scorecards_preserve_profile_boundaries() -> None:
    rows = normalizer.build_scorecards(_inventory())

    by_profile = {row["scorecard_profile"]: row for row in rows}
    assert by_profile["canonical_core"]["document_count"] == 10
    assert by_profile["canonical_core"]["metric_check_count"] == 24
    assert "strict 10-document" in by_profile["canonical_core"]["overclaim_guard"]
    assert by_profile["expanded_required"]["metric_check_count"] == 39
    assert by_profile["confirmed_metric_coverage"]["status"] == "inventory_only_not_accuracy"
    assert by_profile["confirmed_metric_coverage"]["accuracy_claim"] == "none_inventory_only"


def test_metric_rows_do_not_turn_unscored_or_unsupported_into_accuracy_claims() -> None:
    rows = normalizer.build_metric_rows(_inventory())
    by_metric = {row["metric_name"]: row for row in rows}

    assert by_metric["revenue"]["accuracy_claim"] == "profile_scorecard_boundary_only"
    assert by_metric["cash_end"]["expectation_class"] == "confirmed_unscored"
    assert by_metric["cash_end"]["accuracy_claim"] == "none"
    assert by_metric["free_cash_flow"]["expectation_class"] == "ambiguous_or_derived"
    assert by_metric["ebitda"]["expectation_class"] == "unsupported"


def test_write_outputs_builds_valid_eval_spine_manifest_and_csvs(tmp_path: Path) -> None:
    repo = tmp_path
    inventory_path = repo / "reports" / "agent_jobs" / "gold" / "metric_inventory.json"
    inventory_path.parent.mkdir(parents=True)
    inventory_path.write_text(json.dumps(_inventory()) + "\n", encoding="utf-8")
    task_card = repo / "docs" / "agent_tasks" / "gold_metric_coverage_eval_spine_normalizer_v1_20260524.md"
    _write_task_card(task_card)
    out_dir = repo / "reports" / "agent_jobs" / "gold_metric_coverage_eval_spine_normalizer_v1_20260524"

    outputs = normalizer.write_outputs(
        inventory_path=inventory_path,
        output_dir=out_dir,
        task_card=task_card,
        job_id="gold_metric_coverage_eval_spine_normalizer_v1_20260524",
        repo_root=repo,
    )

    manifest = json.loads(Path(outputs["normalized_manifest"]).read_text(encoding="utf-8"))
    assert eval_spine_manifest.validate_manifest(manifest) == []
    assert any(
        item["code"] == "missing_confirmed_metric_coverage_current_accuracy"
        for item in manifest["data_missing"]
    )
    assert manifest["production_data_access"] is False
    assert manifest["scorecards"][2]["scorecard_profile"] == "confirmed_metric_coverage"

    with Path(outputs["metric_expectations_csv"]).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["metric_name"] for row in rows} >= {"revenue", "cash_end", "ebitda"}
