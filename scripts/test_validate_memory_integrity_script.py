from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_memory_integrity.sh"


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


def _run_memory_gate(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    fallback_root = tmp_path / "fallback"
    fallback_root.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "TENN_MEMORY_MARKET_DB": str(tmp_path / "market_memory.sqlite"),
            "TENN_TICKER_IDENTITY_MAP": str(tmp_path / "ticker_identity_map.json"),
            "TENN_MEMORY_FALLBACK_ROOT": str(fallback_root),
            "TENN_MEMORY_COMPANY_DB": str(tmp_path / "missing_company_memory.sqlite"),
            "TENN_MEMORY_MANUAL_REVIEW_CSV": str(tmp_path / "missing_manual_review.csv"),
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_memory_gate_passes_without_backend_runtime(tmp_path: Path) -> None:
    _write_identity_map(tmp_path / "ticker_identity_map.json", ["BHP"])
    _write_market_memory(tmp_path / "market_memory.sqlite", [(1, "active", ["BHP"])])

    result = _run_memory_gate(tmp_path)

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_memory_gate_fails_on_unsupported_ticker_without_backend_runtime(
    tmp_path: Path,
) -> None:
    _write_identity_map(tmp_path / "ticker_identity_map.json", ["BHP"])
    _write_market_memory(
        tmp_path / "market_memory.sqlite",
        [(1, "active", ["BHP", "UNSUPPORTED"])],
    )

    result = _run_memory_gate(tmp_path)

    assert result.returncode == 1
    assert "unsupported_linked_ticker" in result.stdout


def test_memory_gate_fails_on_fallback_sqlite_without_backend_runtime(
    tmp_path: Path,
) -> None:
    _write_identity_map(tmp_path / "ticker_identity_map.json", ["BHP"])
    _write_market_memory(tmp_path / "market_memory.sqlite", [(1, "active", ["BHP"])])
    fallback_root = tmp_path / "fallback"
    fallback_root.mkdir()
    (fallback_root / "legacy.sqlite").write_bytes(b"legacy")

    result = _run_memory_gate(tmp_path)

    assert result.returncode == 1
    assert "fallback_sqlite_present" in result.stdout
