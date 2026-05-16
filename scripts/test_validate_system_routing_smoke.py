from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_system.sh"
MEMORY_SCRIPT = ROOT / "scripts" / "validate_memory_integrity.sh"


def test_validate_system_has_opt_in_routing_smoke_gate() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "COCKPIT_VALIDATE_ROUTING_SMOKE" in text
    assert 'scripts/cockpit smoke routing "${routing_args[@]}"' in text
    assert "set COCKPIT_VALIDATE_ROUTING_SMOKE=1 to enable" in text


def test_validate_system_calls_dedicated_memory_gate() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'MEMORY_VALIDATE="scripts/validate_memory_integrity.sh"' in text
    assert 'bash "${MEMORY_VALIDATE}"' in text


def test_validate_system_shell_syntax_is_valid() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], cwd=ROOT, check=True)


def test_validate_memory_integrity_shell_syntax_is_valid() -> None:
    subprocess.run(["bash", "-n", str(MEMORY_SCRIPT)], cwd=ROOT, check=True)
