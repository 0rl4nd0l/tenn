from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE_MODES = load_module(ROOT / "scripts" / "report_financial_metrics_source_modes.py", "report_source_modes")


def _sample_rows() -> list[dict[str, object]]:
    return [
        {
            "file": "/tmp/docs/AAA/report.pdf",
            "metric": "revenue",
            "statement_period_end": "2025-06-30",
            "value_type": "amount",
            "value": 100.0,
            "currency": "AUD",
            "source_mode": "docling_table",
            "primary_metric_value": True,
            "canonical_confidence_score": 3,
            "integrity_score": 3,
            "integrity_checks_evaluated": 0,
        }
    ]


def test_source_mode_report_embeds_authority_metadata(tmp_path: Path) -> None:
    source = tmp_path / "canonical.json"
    out = tmp_path / "source_modes.json"
    source.write_text(json.dumps(_sample_rows()) + "\n", encoding="utf-8")

    report = SOURCE_MODES.attach_authority_metadata(
        SOURCE_MODES.build_source_mode_report(_sample_rows()),
        canonical_path=source,
        out_path=out,
    )

    authority = report["authority"]
    assert authority["lane"] == "Evaluation"
    assert authority["canonical_financial_truth"] is False
    assert authority["canonical_write_allowed"] is False
    assert authority["source_artifacts"]
    assert authority["do_not_overclaim"]


def test_query_financial_metrics_json_envelope_and_sidecar(tmp_path: Path) -> None:
    source = tmp_path / "canonical.json"
    authority_path = tmp_path / "query.authority.json"
    source.write_text(json.dumps(_sample_rows()) + "\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/query_financial_metrics.py",
            "--ticker",
            "AAA",
            "--json-path",
            str(source),
            "--format",
            "json",
            "--json-envelope",
            "--authority-json",
            str(authority_path),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    payload = json.loads(completed.stdout)
    sidecar = json.loads(authority_path.read_text(encoding="utf-8"))
    assert len(payload["rows"]) == 1
    assert payload["authority"]["canonical_financial_truth"] is False
    assert sidecar["canonical_write_allowed"] is False
    assert sidecar["source_artifacts"]


def test_derived_metrics_writes_authority_sidecar(tmp_path: Path) -> None:
    source = tmp_path / "canonical.json"
    out_json = tmp_path / "derived.json"
    out_csv = tmp_path / "derived.csv"
    out_sqlite = tmp_path / "derived.sqlite"
    authority_path = tmp_path / "derived.authority.json"
    source.write_text(json.dumps(_sample_rows()) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/derived_metrics.py",
            "--canonical-json",
            str(source),
            "--out-json",
            str(out_json),
            "--out-csv",
            str(out_csv),
            "--out-sqlite",
            str(out_sqlite),
            "--authority-json",
            str(authority_path),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    metadata = json.loads(authority_path.read_text(encoding="utf-8"))
    assert metadata["lane"] == "Analysis"
    assert metadata["canonical_financial_truth"] is False
    assert metadata["canonical_write_allowed"] is False
    assert metadata["source_artifacts"]
    assert metadata["output_artifacts"]
    assert metadata["do_not_overclaim"]
