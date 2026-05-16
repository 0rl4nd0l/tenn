#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


TICKER_RE = re.compile(r"^[A-Z0-9]{1,10}$")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sqlite_uri(path: Path, *, immutable: bool) -> str:
    suffix = "?mode=ro"
    if immutable:
        suffix += "&immutable=1"
    return path.resolve().as_uri() + suffix


def _safe_json_list(raw: str) -> list[Any]:
    try:
        parsed = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return [{"__invalid_json__": raw}]
    return parsed if isinstance(parsed, list) else [{"__not_list__": parsed}]


def _audit_market_memory(
    *,
    market_memory_path: Path,
    identity_map_path: Path,
    forbidden_tokens: set[str],
    immutable: bool,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    identity_map = _read_json(identity_map_path)
    if not isinstance(identity_map, dict):
        raise ValueError("identity map must be a JSON object")

    token_occurrences: dict[str, list[int]] = {}
    invalid_tickers: list[dict[str, Any]] = []
    invalid_json_rows: list[int] = []
    active_row_count = 0

    with sqlite3.connect(_sqlite_uri(market_memory_path, immutable=immutable), uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT entry_id, linked_tickers_json
            FROM sector_states
            WHERE status = 'active'
            ORDER BY entry_id
            """
        ).fetchall()

    for row in rows:
        active_row_count += 1
        entry_id = int(row["entry_id"])
        linked_tickers = _safe_json_list(row["linked_tickers_json"])
        if linked_tickers and isinstance(linked_tickers[0], dict):
            invalid_json_rows.append(entry_id)
            continue
        for raw_token in linked_tickers:
            token = str(raw_token or "").strip().upper()
            token_occurrences.setdefault(token, []).append(entry_id)
            if not TICKER_RE.fullmatch(token):
                invalid_tickers.append({"entry_id": entry_id, "token": raw_token})

    active_tokens = sorted(token_occurrences)
    unsupported_tokens = [
        {"token": token, "entry_ids": token_occurrences[token]}
        for token in active_tokens
        if token not in identity_map
    ]
    forbidden_hits = [
        {"token": token, "entry_ids": token_occurrences[token]}
        for token in sorted(forbidden_tokens)
        if token in token_occurrences
    ]

    if invalid_json_rows:
        issues.append({"type": "invalid_linked_tickers_json", "rows": invalid_json_rows})
    if invalid_tickers:
        issues.append({"type": "invalid_linked_ticker_shape", "tokens": invalid_tickers})
    if unsupported_tokens:
        issues.append({"type": "unsupported_linked_ticker", "tokens": unsupported_tokens})
    if forbidden_hits:
        issues.append({"type": "forbidden_linked_ticker", "tokens": forbidden_hits})

    return {
        "market_memory_path": str(market_memory_path),
        "identity_map_path": str(identity_map_path),
        "active_sector_row_count": active_row_count,
        "active_distinct_linked_ticker_count": len(active_tokens),
        "active_distinct_linked_tickers": active_tokens,
        "forbidden_tokens": sorted(forbidden_tokens),
        "issues": issues,
        "ok": not issues,
    }


def _audit_fallback_root(
    *,
    fallback_root: Path | None,
    require_no_sqlite: bool,
) -> dict[str, Any]:
    if fallback_root is None:
        return {
            "checked": False,
            "issues": [],
            "ok": True,
        }
    sqlite_files = sorted(str(path) for path in fallback_root.glob("*.sqlite"))
    issues = []
    if require_no_sqlite and sqlite_files:
        issues.append({"type": "fallback_sqlite_present", "paths": sqlite_files})
    return {
        "checked": True,
        "fallback_root": str(fallback_root),
        "sqlite_files": sqlite_files,
        "require_no_sqlite": require_no_sqlite,
        "issues": issues,
        "ok": not issues,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    market = _audit_market_memory(
        market_memory_path=args.market_memory,
        identity_map_path=args.identity_map,
        forbidden_tokens={token.upper() for token in args.forbidden_token},
        immutable=not args.no_immutable,
    )
    fallback = _audit_fallback_root(
        fallback_root=args.fallback_root,
        require_no_sqlite=args.require_no_fallback_sqlite,
    )
    issues = []
    issues.extend({"scope": "market_memory", **issue} for issue in market["issues"])
    issues.extend({"scope": "fallback_root", **issue} for issue in fallback["issues"])
    return {
        "ok": not issues,
        "issues": issues,
        "market_memory": market,
        "fallback_root": fallback,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only audit for memory linked-ticker integrity."
    )
    parser.add_argument("--market-memory", type=Path, required=True)
    parser.add_argument("--identity-map", type=Path, required=True)
    parser.add_argument("--fallback-root", type=Path)
    parser.add_argument(
        "--forbidden-token",
        action="append",
        default=[],
        help="Linked ticker token that must not appear in active market memory.",
    )
    parser.add_argument(
        "--require-no-fallback-sqlite",
        action="store_true",
        help="Fail if fallback-root contains any .sqlite files.",
    )
    parser.add_argument(
        "--no-immutable",
        action="store_true",
        help="Open SQLite read-only without immutable=1.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = run_audit(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
