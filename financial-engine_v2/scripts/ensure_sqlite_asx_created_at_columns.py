#!/usr/bin/env python3
"""Idempotently add created_at to ASX structured tables on SQLite.

Alembic migrations target Postgres; runtime / dev SQLite DBs (e.g. fe_local.db)
need the same columns for monitoring queries. Safe to run multiple times.

Usage:
  python scripts/ensure_sqlite_asx_created_at_columns.py /path/to/fe_local.db
  # or
  FE_SQLITE_PATH=/path/to/fe_local.db python scripts/ensure_sqlite_asx_created_at_columns.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _ensure_table_column(
    conn: sqlite3.Connection, table: str, copy_from: str = "updated_at"
) -> None:
    cols = _column_names(conn, table)
    if "created_at" in cols:
        print(f"{table}: created_at already present — skip")
        return
    if copy_from not in cols:
        raise SystemExit(f"{table}: missing column {copy_from!r}, cannot backfill created_at")
    print(f"{table}: adding created_at, backfilling from {copy_from}")
    conn.execute(f"ALTER TABLE {table} ADD COLUMN created_at DATETIME")
    conn.execute(
        f"UPDATE {table} SET created_at = {copy_from} WHERE created_at IS NULL"
    )


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    os.chdir(repo)
    path = (
        (sys.argv[1] if len(sys.argv) > 1 else None)
        or os.environ.get("FE_SQLITE_PATH")
        or os.environ.get("SQLITE_PATH")
    )
    if not path:
        print(
            "Usage: ensure_sqlite_asx_created_at_columns.py <database.sqlite>\n"
            "   or: FE_SQLITE_PATH=... ensure_sqlite_asx_created_at_columns.py",
            file=sys.stderr,
        )
        return 2
    db_path = Path(path).expanduser().resolve()
    if not db_path.is_file():
        print(f"Not a file: {db_path}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_table_column(conn, "asx_periodic_financials")
        _ensure_table_column(conn, "asx_risk_notes")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
