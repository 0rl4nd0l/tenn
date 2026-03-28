#!/usr/bin/env python3
"""Thin serve wrapper for CockpitApp.

Bypasses the interactive TTY guard in cockpit/main.py so that
`textual serve` can host the app over WebSocket for browser access.

Usage (from financial-engine_v2/, after `pip install textual`):
    .venv/bin/textual serve scripts/cockpit_serve.py [-- --read-only --no-web]

Do not use `python -m textual serve` — that runs Textual's demo app, not `serve`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.config import RuntimeFlags, apply_runtime_flags, load_config, load_env
from cockpit.ui.app import CockpitApp

# Load .env BEFORE arg parsing — arg defaults read from os.environ.
load_env(REPO_ROOT)


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cockpit serve wrapper (no TTY required)")
    p.add_argument("--config", default="config/cockpit.yaml", help="Cockpit config path (relative to repo root)")
    p.add_argument("--profile", default=os.environ.get("COCKPIT_PREBOOT_PROFILE", "default"))
    p.add_argument("--read-only", action="store_true", default=os.environ.get("COCKPIT_PREBOOT_READ_ONLY", "") in {"1", "true"})
    p.add_argument("--no-web", action="store_true", default=os.environ.get("COCKPIT_PREBOOT_NO_WEB", "") in {"1", "true"})
    args, _ = p.parse_known_args()
    return args


_args = _parse()
_cfg = load_config(_args.config)
_cfg = apply_runtime_flags(
    _cfg,
    RuntimeFlags(
        config_path=_args.config,
        profile=_args.profile,
        read_only=_args.read_only,
        no_web=_args.no_web,
    ),
)

# Module-level app instance — textual serve detects this.
app = CockpitApp(repo_root=REPO_ROOT, config=_cfg, read_only=_args.read_only)

if __name__ == "__main__":
    app.run()
