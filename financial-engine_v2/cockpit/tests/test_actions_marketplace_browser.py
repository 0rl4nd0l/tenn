from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cockpit.core.actions import ActionRegistry


def test_action_registry_builds_marketplace_browser_command_with_defaults(
    tmp_path: Path,
) -> None:
    registry = ActionRegistry(tmp_path)

    preview = registry.preview("launch_marketplace_browser", {})

    assert preview.action_id == "launch_marketplace_browser"
    assert preview.timeout_seconds == 30
    assert preview.estimated_impact == "read-only"
    assert preview.command[1] == "scripts/launch_marketplace_browser.py"
    assert preview.command[-1] == "https://www.facebook.com/marketplace/"
    assert "--browser" in preview.command
    assert "--port" in preview.command


def test_action_registry_adds_fresh_profile_flag_for_marketplace_browser(
    tmp_path: Path,
) -> None:
    registry = ActionRegistry(tmp_path)

    command = registry.build_command(
        "launch_marketplace_browser",
        {
            "url": "https://www.facebook.com/marketplace/item/1234567890",
            "browser": "chrome",
            "fresh_profile": True,
        },
    )

    assert command[-2:] == [
        "https://www.facebook.com/marketplace/item/1234567890",
        "--fresh-profile",
    ]
    assert "chrome" in command
