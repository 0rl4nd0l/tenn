from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "cockpit_flag_investigator.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cockpit_flag_investigator", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_codex_exec_command_uses_current_noninteractive_approval_config(tmp_path: Path) -> None:
    module = _load_module()
    args = argparse.Namespace(
        apply=True,
        codex_bin="codex",
        sandbox="read-only",
    )

    command = module._build_codex_command(
        args=args,
        repo_root=ROOT,
        output_path=tmp_path / "last-message.md",
    )

    assert "--ask-for-approval" not in command
    assert command[:3] == ["codex", "exec", "--json"]
    assert command[command.index("-c") + 1] == 'approval_policy="never"'
    assert command[command.index("--sandbox") + 1] == "workspace-write"
