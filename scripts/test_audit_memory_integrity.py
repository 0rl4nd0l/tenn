from __future__ import annotations

import importlib.util
import json
import sqlite3
from argparse import Namespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_memory_integrity.py"

spec = importlib.util.spec_from_file_location("audit_memory_integrity", SCRIPT_PATH)
assert spec is not None
audit_memory_integrity = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit_memory_integrity)


def _write_identity_map(path: Path, tickers: list[str]) -> None:
    payload = {
        ticker: {"canonical_names": [f"{ticker} Limited"], "aliases": []}
        for ticker in tickers
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_market_memory(path: Path, rows: list[tuple[int, str, list[str]]]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE sector_states (
            entry_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,
            linked_tickers_json TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO sector_states (entry_id, status, linked_tickers_json) VALUES (?, ?, ?)",
        [(entry_id, status, json.dumps(tickers)) for entry_id, status, tickers in rows],
    )
    conn.commit()
    conn.close()


def _args(tmp_path: Path, *, fallback_root: Path | None = None) -> Namespace:
    return Namespace(
        market_memory=tmp_path / "market_memory.sqlite",
        identity_map=tmp_path / "ticker_identity_map.json",
        fallback_root=fallback_root,
        forbidden_token=["BE"],
        require_no_fallback_sqlite=fallback_root is not None,
        no_immutable=False,
    )


def test_audit_passes_when_active_linked_tickers_are_supported(tmp_path: Path) -> None:
    _write_identity_map(tmp_path / "ticker_identity_map.json", ["BHP", "COH"])
    _write_market_memory(
        tmp_path / "market_memory.sqlite",
        [
            (1, "active", ["BHP", "COH"]),
            (2, "expired", ["BE"]),
        ],
    )

    result = audit_memory_integrity.run_audit(_args(tmp_path))

    assert result["ok"] is True
    assert result["market_memory"]["active_distinct_linked_tickers"] == ["BHP", "COH"]


def test_audit_fails_for_unsupported_and_forbidden_tokens(tmp_path: Path) -> None:
    _write_identity_map(tmp_path / "ticker_identity_map.json", ["BHP"])
    _write_market_memory(
        tmp_path / "market_memory.sqlite",
        [
            (1, "active", ["BHP", "BE"]),
            (2, "active", ["NOT A TICKER"]),
        ],
    )

    result = audit_memory_integrity.run_audit(_args(tmp_path))

    assert result["ok"] is False
    issue_types = {issue["type"] for issue in result["issues"]}
    assert "forbidden_linked_ticker" in issue_types
    assert "unsupported_linked_ticker" in issue_types
    assert "invalid_linked_ticker_shape" in issue_types


def test_audit_fails_when_fallback_sqlite_files_exist(tmp_path: Path) -> None:
    fallback_root = tmp_path / "fallback"
    fallback_root.mkdir()
    (fallback_root / "market_memory.sqlite").write_bytes(b"not a real db")
    _write_identity_map(tmp_path / "ticker_identity_map.json", ["BHP"])
    _write_market_memory(tmp_path / "market_memory.sqlite", [(1, "active", ["BHP"])])

    result = audit_memory_integrity.run_audit(_args(tmp_path, fallback_root=fallback_root))

    assert result["ok"] is False
    assert result["fallback_root"]["sqlite_files"] == [
        str(fallback_root / "market_memory.sqlite")
    ]
