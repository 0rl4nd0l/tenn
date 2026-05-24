#!/usr/bin/env python3
"""Run recurring extraction evaluation gates and write one aggregate report."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = Path(
    "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
    "recurring_eval_report.json"
)


@dataclass(frozen=True)
class GateSpec:
    name: str
    command: list[str]
    expected_output: Path | None = None


def default_gate_specs(*, python_bin: str = sys.executable) -> list[GateSpec]:
    return [
        GateSpec(
            name="appendix5b_prm_no_regression",
            command=[
                python_bin,
                "scripts/run_appendix5b_no_regression_gate.py",
                "--output",
                (
                    "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
                    "appendix5b_no_regression_report.json"
                ),
            ],
            expected_output=Path(
                "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
                "appendix5b_no_regression_report.json"
            ),
        )
    ]


def run_gate_specs(
    specs: Sequence[GateSpec],
    *,
    repo_root: Path,
    generated_at: str | None = None,
) -> dict[str, object]:
    gate_results = [_run_gate(spec, repo_root=repo_root) for spec in specs]
    failed = [result for result in gate_results if result["status"] != "PASS"]
    return {
        "artifact_type": "extraction_recurring_evaluation_gates_v1",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "canonical_write": False,
        "scope": "report_local_evaluation_gates",
        "gate_count": len(gate_results),
        "gate_pass": not failed,
        "failed_gates": [result["name"] for result in failed],
        "gates": gate_results,
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_gate(spec: GateSpec, *, repo_root: Path) -> dict[str, object]:
    completed = subprocess.run(
        spec.command,
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    expected_output = _read_expected_output(spec.expected_output, repo_root=repo_root)
    return {
        "name": spec.name,
        "command": spec.command,
        "returncode": completed.returncode,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
        "expected_output": str(spec.expected_output) if spec.expected_output else None,
        "expected_output_summary": expected_output,
    }


def _read_expected_output(path: Path | None, *, repo_root: Path) -> dict[str, object] | None:
    if path is None:
        return None
    resolved = path if path.is_absolute() else repo_root / path
    if not resolved.exists():
        return {"status": "DATA_MISSING", "path": str(path)}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "INVALID_JSON", "path": str(path), "error": str(exc)}
    if not isinstance(payload, dict):
        return {"status": "INVALID_JSON", "path": str(path), "error": "root is not object"}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "status": "OK",
        "path": str(path),
        "gate_pass": payload.get("gate_pass"),
        "canonical_write": payload.get("canonical_write"),
        "summary": summary,
    }


def _tail(text: str, *, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run recurring extraction evaluation gates without starting services."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    specs = default_gate_specs()
    report = run_gate_specs(specs, repo_root=args.repo_root)
    write_report(args.output, report)
    print(
        json.dumps(
            {
                "status": "PASS" if report["gate_pass"] else "FAIL",
                "output": str(args.output),
                "failed_gates": report["failed_gates"],
                "gate_count": report["gate_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
