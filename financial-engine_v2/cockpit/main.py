from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cockpit.core.backend_restart import restart_backend
from cockpit.core.config import RuntimeFlags, apply_runtime_flags, load_config, load_env
from cockpit.ui.app import CockpitApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Financial Engine Cockpit TUI")
    parser.add_argument("--config", default="config/cockpit.yaml", help="Path to cockpit config")
    parser.add_argument("--profile", default="default", help="Runtime profile label")
    parser.add_argument("--read-only", action="store_true", help="Disable mutating actions")
    parser.add_argument("--no-web", action="store_true", help="Disable web fetch tools")

    subparsers = parser.add_subparsers(dest="command")
    restart_p = subparsers.add_parser("restart", help="Restart a cockpit service")
    restart_p.add_argument(
        "service",
        choices=["backend"],
        help="Service to restart (currently: backend)",
    )

    return parser


def main() -> None:
    load_env()
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    # --- CLI subcommands (non-TUI) ---
    if args.command == "restart":
        restart_backend(repo_root)
        return

    # --- TUI mode ---
    # Textual requires an interactive TTY; fail fast with a clear message.
    if not sys.stdout.isatty():
        raise SystemExit(
            "Cockpit TUI requires an interactive stdout TTY. "
            "Run from a normal terminal tab/pane, not a non-interactive output pane."
        )
    if (os.getenv("TERM") or "").lower() in {"", "dumb", "unknown"}:
        raise SystemExit(
            "Cockpit TUI requires a valid TERM. "
            "Try: export TERM=xterm-256color"
        )

    cfg = load_config(args.config)
    cfg = apply_runtime_flags(
        cfg,
        RuntimeFlags(
            config_path=args.config,
            profile=args.profile,
            read_only=args.read_only,
            no_web=args.no_web,
            repo_root=repo_root,
        ),
    )

    app = CockpitApp(repo_root=repo_root, config=cfg, read_only=args.read_only)
    app.run()


if __name__ == "__main__":
    main()
