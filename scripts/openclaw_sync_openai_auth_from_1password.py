#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_auth_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "profiles": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Could not parse auth file: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Auth file is not a JSON object: {path}")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        payload["profiles"] = {}
    if "version" not in payload:
        payload["version"] = 1
    return payload


def _read_secret_from_op(op_bin: str, secret_ref: str) -> str:
    if not shutil.which(op_bin):
        raise RuntimeError(
            f"1Password CLI '{op_bin}' is not installed or not in PATH. "
            "Install/sign in first, then re-run."
        )
    proc = subprocess.run(
        [op_bin, "read", secret_ref],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"Failed to read secret via 1Password CLI: {stderr or 'unknown error'}")
    token = (proc.stdout or "").strip()
    if not token:
        raise RuntimeError("1Password returned an empty secret.")
    return token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync OpenAI API key from 1Password CLI into OpenClaw auth profiles."
    )
    parser.add_argument(
        "--secret-ref",
        required=True,
        help="1Password secret reference, for example: op://Vault/Item/field",
    )
    parser.add_argument(
        "--auth-file",
        default=str(Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"),
        help="Target OpenClaw auth profile file.",
    )
    parser.add_argument(
        "--profile-id",
        default="openai:manual",
        help="Profile key to update in auth-profiles.json.",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        help="Provider id for this token (default: openai).",
    )
    parser.add_argument(
        "--op-bin",
        default="op",
        help="1Password CLI binary name/path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    auth_file = Path(args.auth_file).expanduser().resolve()

    try:
        token = _read_secret_from_op(args.op_bin, args.secret_ref)
        payload = _load_auth_payload(auth_file)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
        payload["profiles"] = profiles

    profile_id = str(args.profile_id).strip()
    provider = str(args.provider).strip()
    if not profile_id:
        print("error: --profile-id cannot be empty", file=sys.stderr)
        return 1
    if not provider:
        print("error: --provider cannot be empty", file=sys.stderr)
        return 1

    profiles[profile_id] = {
        "provider": provider,
        "token": token,
        # OpenClaw auth-profiles schema expects token credentials as type=token.
        "type": "token",
    }

    if args.dry_run:
        print("dry_run=true")
        print(f"auth_file={auth_file}")
        print(f"profile_id={profile_id}")
        print(f"provider={provider}")
        print("result=would_update")
        return 0

    auth_file.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None
    if auth_file.exists():
        backup_path = auth_file.with_name(f"{auth_file.name}.bak.{_timestamp()}")
        shutil.copy2(auth_file, backup_path)

    auth_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    auth_file.chmod(0o600)

    print(f"auth_file={auth_file}")
    if backup_path:
        print(f"backup_file={backup_path}")
    print(f"profile_id={profile_id}")
    print(f"provider={provider}")
    print("result=updated")
    print("note=restart openclaw-gateway.service after updating credentials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
