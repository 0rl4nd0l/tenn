from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_extraction_evaluation_gates.py"

spec = importlib.util.spec_from_file_location("run_extraction_evaluation_gates", str(SCRIPT_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _write_gate_script(path: Path, *, returncode: int) -> None:
    path.write_text(
        "import sys\n"
        f"print('gate returncode {returncode}')\n"
        f"raise SystemExit({returncode})\n",
        encoding="utf-8",
    )


def test_recurring_gate_report_passes_when_all_gates_pass(tmp_path: Path) -> None:
    gate_script = tmp_path / "gate.py"
    output = tmp_path / "gate-output.json"
    _write_gate_script(gate_script, returncode=0)
    output.write_text(
        json.dumps(
            {
                "gate_pass": True,
                "canonical_write": False,
                "summary": {"exact_match_rate": 1.0},
            }
        ),
        encoding="utf-8",
    )

    report = mod.run_gate_specs(
        [
            mod.GateSpec(
                name="sample_gate",
                command=[sys.executable, str(gate_script)],
                expected_output=output,
            )
        ],
        repo_root=tmp_path,
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert report["gate_pass"]
    assert report["failed_gates"] == []
    assert report["canonical_write"] is False
    assert report["gates"][0]["expected_output_summary"]["summary"]["exact_match_rate"] == 1.0


def test_default_gate_spec_names_prm_floor() -> None:
    specs = mod.default_gate_specs(python_bin=sys.executable)

    assert [spec.name for spec in specs] == ["appendix5b_prm_no_regression"]


def test_recurring_gate_report_fails_when_any_gate_fails(tmp_path: Path) -> None:
    gate_script = tmp_path / "gate.py"
    _write_gate_script(gate_script, returncode=2)

    report = mod.run_gate_specs(
        [
            mod.GateSpec(
                name="sample_gate",
                command=[sys.executable, str(gate_script)],
            )
        ],
        repo_root=tmp_path,
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert not report["gate_pass"]
    assert report["failed_gates"] == ["sample_gate"]
    assert report["gates"][0]["status"] == "FAIL"


def test_recurring_gate_report_marks_missing_expected_output(tmp_path: Path) -> None:
    gate_script = tmp_path / "gate.py"
    _write_gate_script(gate_script, returncode=0)

    report = mod.run_gate_specs(
        [
            mod.GateSpec(
                name="sample_gate",
                command=[sys.executable, str(gate_script)],
                expected_output=Path("missing.json"),
            )
        ],
        repo_root=tmp_path,
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert report["gate_pass"]
    assert report["gates"][0]["expected_output_summary"]["status"] == "DATA_MISSING"
