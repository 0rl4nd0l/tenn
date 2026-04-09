from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import _normalize_action_command


def test_normalize_action_command_repairs_missing_absolute_shared_script(
    monkeypatch, tmp_path
) -> None:
    shared_root = tmp_path / "workspace" / "scripts"
    shared_root.mkdir(parents=True)
    script_path = shared_root / "fetch_daily_news.py"
    script_path.write_text("# stub\n", encoding="utf-8")

    monkeypatch.setenv("COCKPIT_SHARED_SCRIPTS_ROOT", str(shared_root))

    command = [sys.executable, "/scripts/fetch_daily_news.py"]
    normalized = _normalize_action_command(command, tmp_path)

    assert normalized[1] == str(script_path)
