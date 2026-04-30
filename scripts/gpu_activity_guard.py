#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
for _path in (BACKEND_ROOT, ENGINE_ROOT):
    text = str(_path)
    if text not in sys.path:
        sys.path.insert(0, text)


def _parse_metadata(values: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                f"metadata entry must be KEY=VALUE, got {value!r}"
            )
        key, item = value.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError("metadata key cannot be empty")
        metadata[key] = item.strip()
    return metadata


def _load_router_state() -> Any:
    from app.services import router_state

    return router_state


def _fallback_file_snapshot() -> dict[str, Any]:
    """Read the shared activity file when backend dependencies are unavailable."""

    now_ts = time.time()
    state_path = Path(
        os.getenv("TENN_EXTRACTION_ACTIVE_FILE")
        or (Path(tempfile.gettempdir()) / "tenn_extraction_active.json")
    ).expanduser()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "active": False,
            "source": "none",
            "token_count": 0,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [],
            "kind": "gpu_exclusive_activity",
        }

    raw_tokens = payload.get("tokens") if isinstance(payload, dict) else {}
    raw_metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    if not isinstance(raw_tokens, dict):
        raw_tokens = {}
    if not isinstance(raw_metadata, dict):
        raw_metadata = {}

    active_runs: list[dict[str, Any]] = []
    for token, raw_expiry in raw_tokens.items():
        try:
            expiry = float(raw_expiry)
        except (TypeError, ValueError):
            continue
        if expiry <= now_ts:
            continue
        token_text = str(token)
        run = {
            "token": token_text,
            "expires_at": expiry,
            "expires_in_seconds": max(int(expiry - now_ts), 0),
        }
        metadata = raw_metadata.get(token_text)
        if isinstance(metadata, dict):
            for key in ("activity_type", "reason", "owner", "mode"):
                value = metadata.get(key)
                if value is not None and str(value).strip():
                    run[key] = str(value).strip()
        active_runs.append(run)

    if not active_runs:
        return {
            "active": False,
            "source": "none",
            "token_count": 0,
            "expires_at": None,
            "expires_in_seconds": 0,
            "active_runs": [],
            "kind": "gpu_exclusive_activity",
        }

    latest_expiry = max(float(run["expires_at"]) for run in active_runs)
    return {
        "active": True,
        "source": "file",
        "token_count": len(active_runs),
        "expires_at": latest_expiry,
        "expires_in_seconds": max(int(latest_expiry - now_ts), 0),
        "active_runs": sorted(
            active_runs,
            key=lambda run: float(run.get("expires_at") or 0.0),
            reverse=True,
        ),
        "kind": "gpu_exclusive_activity",
    }


def _status_snapshot(redis_url: str | None) -> dict[str, Any]:
    try:
        router_state = _load_router_state()
    except Exception:
        return _fallback_file_snapshot()
    return router_state.get_gpu_exclusive_activity_snapshot(redis_url=redis_url)


def _print_status(snapshot: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(snapshot, sort_keys=True))
        return
    if not bool(snapshot.get("active")):
        print("GPU-exclusive activity: inactive")
        return
    expires_in = int(snapshot.get("expires_in_seconds") or 0)
    source = str(snapshot.get("source") or "unknown")
    token_count = int(snapshot.get("token_count") or 0)
    print(
        "GPU-exclusive activity: "
        f"active source={source} tokens={token_count} expires_in={expires_in}s"
    )
    for run in snapshot.get("active_runs") or []:
        token = str(run.get("token") or "")
        activity_type = str(run.get("activity_type") or "unknown")
        reason = str(run.get("reason") or "").strip()
        owner = str(run.get("owner") or "").strip()
        pieces = [f"token={token}", f"type={activity_type}"]
        if reason:
            pieces.append(f"reason={reason}")
        if owner:
            pieces.append(f"owner={owner}")
        print("  " + " ".join(pieces))


def cmd_status(args: argparse.Namespace) -> int:
    snapshot = _status_snapshot(args.redis_url)
    active = bool(snapshot.get("active"))
    if args.quiet_active:
        return 0 if active else 1
    _print_status(snapshot, as_json=args.json)
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    router_state = _load_router_state()
    metadata = _parse_metadata(args.metadata or [])
    token = router_state.register_gpu_exclusive_activity(
        redis_url=args.redis_url,
        ttl_seconds=args.ttl_seconds,
        metadata=metadata,
        reason=args.reason,
        owner=args.owner,
        track_process=args.track_process,
    )
    if args.json:
        snapshot = router_state.get_gpu_exclusive_activity_snapshot(
            redis_url=args.redis_url
        )
        print(json.dumps({"token": token, "snapshot": snapshot}, sort_keys=True))
    else:
        print(token)
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    router_state = _load_router_state()
    router_state.clear_gpu_exclusive_activity(args.token, redis_url=args.redis_url)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Register or inspect Tenn GPU-exclusive activity. While active, "
            "Cockpit chat routes to API and shared local llama startup is blocked."
        )
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("CELERY_BROKER_URL"),
        help="Redis URL for shared state; defaults to CELERY_BROKER_URL.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show guard state.")
    status.add_argument("--json", action="store_true", help="Emit JSON.")
    status.add_argument(
        "--quiet-active",
        action="store_true",
        help="Print nothing; exit 0 when active, 1 when inactive.",
    )
    status.set_defaults(func=cmd_status)

    start = subparsers.add_parser("start", help="Register a GPU-exclusive token.")
    start.add_argument("--json", action="store_true", help="Emit token and snapshot.")
    start.add_argument(
        "--ttl-seconds",
        type=int,
        default=1800,
        help="Safety TTL for the token. Defaults to 1800 seconds.",
    )
    start.add_argument("--reason", default=None, help="Short reason for diagnostics.")
    start.add_argument("--owner", default=None, help="Owner label for diagnostics.")
    start.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra metadata. May be repeated.",
    )
    start.add_argument(
        "--track-process",
        action="store_true",
        help=(
            "Tie token lifetime to this process PID. Intended for in-process "
            "contexts, not one-shot shell guards."
        ),
    )
    start.set_defaults(func=cmd_start)

    clear = subparsers.add_parser("clear", help="Clear a token returned by start.")
    clear.add_argument("token")
    clear.set_defaults(func=cmd_clear)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
