#!/usr/bin/env python3
"""Entrypoint for the combined pre-boot + cockpit web app.

Runs CockpitWebApp — a single Textual app that shows the pre-boot setup
screen in the browser first, then transitions to the full cockpit UI after
the user clicks Launch.

Usage (direct):
    python financial-engine_v2/scripts/cockpit_web.py [--config PATH]

Usage (via cockpit CLI):
    cockpit start web
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.config import DEFAULT_BACKEND_URL, DEFAULT_LLAMACPP_URL, DEFAULT_OLLAMA_URL
from cockpit.ui.web import CockpitWebApp


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cockpit combined web app (pre-boot + cockpit)")
    p.add_argument(
        "--config",
        default=os.environ.get("COCKPIT_CONFIG", "config/cockpit.yaml"),
        help="Cockpit config path (relative to repo root, or absolute)",
    )
    p.add_argument(
        "--backend-url",
        default=os.environ.get("COCKPIT_BACKEND_URL", DEFAULT_BACKEND_URL),
    )
    p.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL),
    )
    p.add_argument(
        "--llamacpp-url",
        default=os.environ.get("COCKPIT_LLAMACPP_URL", os.environ.get("LLAMACPP_URL", DEFAULT_LLAMACPP_URL)),
    )
    args, _ = p.parse_known_args()
    return args


def _resolve_config(config_arg: str) -> str:
    p = Path(config_arg)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return str(p)


_args = _parse()
_config_path = _resolve_config(_args.config)

# Module-level app instance — consumed by `app.run()` below or by
# the cockpit CLI via the PTY wrapper.
app = CockpitWebApp(
    repo_root=REPO_ROOT,
    config_path=_config_path,
    backend_url=_args.backend_url,
    ollama_url=_args.ollama_url,
    llamacpp_url=_args.llamacpp_url,
)

if __name__ == "__main__":
    app.run()
