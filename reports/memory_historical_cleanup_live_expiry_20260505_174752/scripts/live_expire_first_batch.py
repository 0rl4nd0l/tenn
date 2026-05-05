#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVED_DB_PATH = Path("/data/reports/research_memory/company_memory.sqlite")
APPROVED_ROW_COUNT = 249
EXPECTED_PRE_ACTIVE = 1997
EXPECTED_PRE_EXPIRED = 1
EXPECTED_POST_ACTIVE = 1748
EXPECTED_POST_EXPIRED = 250


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def row_id(row: dict[str, str]) -> int:
    return int(str(row.get("row_id") or "").strip())


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        str(row["status"]): int(row["n"])
        for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM memory_entries GROUP BY status"
        ).fetchall()
    }


def entity_counts(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"active": 0, "expired": 0})
    for row in conn.execute(
        """
        SELECT company_id, status, COUNT(*) AS n
        FROM memory_entries
        GROUP BY company_id, status
        ORDER BY company_id, status
        """
    ):
        entity = str(row["company_id"] or "").strip().upper()
        status = str(row["status"] or "")
        if status in {"active", "expired"}:
            counts[entity][status] = int(row["n"])
    return dict(counts)


def validate_manifest(rows: list[dict[str, str]]) -> list[int]:
    if len(rows) != APPROVED_ROW_COUNT:
        raise SystemExit(f"Expected {APPROVED_ROW_COUNT} approved rows, got {len(rows)}")
    ids = [row_id(row) for row in rows]
    if len(set(ids)) != APPROVED_ROW_COUNT:
        duplicates = [rid for rid, count in Counter(ids).items() if count > 1]
        raise SystemExit(f"Duplicate approved row ids: {duplicates}")
    for row in rows:
        if row.get("proposed_action") != "status_expire_candidate":
            raise SystemExit(f"Unexpected proposed_action for row {row.get('row_id')}")
        if row.get("recommended_batch") != "first":
            raise SystemExit(f"Unexpected recommended_batch for row {row.get('row_id')}")
        if not row.get("first_batch_reason"):
            raise SystemExit(f"Missing first_batch_reason for row {row.get('row_id')}")
    return ids


def backup_database(db_path: Path, backup_path: Path) -> str:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    wal_path = Path(f"{db_path}-wal")
    shm_path = Path(f"{db_path}-shm")
    if not wal_path.exists() and not shm_path.exists():
        shutil.copy2(db_path, backup_path)
        return "raw_file_copy"
    with sqlite3.connect(db_path) as src:
        with sqlite3.connect(backup_path) as dst:
            src.backup(dst)
    return "sqlite_backup_api"


def fetch_approved_rows(
    conn: sqlite3.Connection, ids: list[int]
) -> dict[int, sqlite3.Row]:
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM memory_entries WHERE entry_id IN ({placeholders})",
        ids,
    ).fetchall()
    return {int(row["entry_id"]): row for row in rows}


def write_sql_templates(
    output_dir: Path,
    ids: list[int],
    approval_id: str,
    timestamp: str,
) -> None:
    values = ",\n".join(f"  ({rid})" for rid in ids)
    live_sql = f"""-- DO_NOT_RUN_executed_live_expire_first_batch.sql
-- DO_NOT_RUN. Historical record of the approved live cleanup already executed by this report.
-- Approval id: {approval_id}
-- Executed at: {timestamp}

BEGIN IMMEDIATE;
CREATE TEMP TABLE cleanup_expire_candidate_ids(entry_id INTEGER PRIMARY KEY);
INSERT INTO cleanup_expire_candidate_ids(entry_id) VALUES
{values};

UPDATE memory_entries
SET status = 'expired'
WHERE entry_id IN (SELECT entry_id FROM cleanup_expire_candidate_ids)
  AND status = 'active';

INSERT INTO change_log (company_id, entry_id, event_type, details_json, created_at)
SELECT
  e.company_id,
  e.entry_id,
  'expire',
  json_object(
    'source', 'historical_memory_cleanup',
    'approval_id', '{approval_id}',
    'dry_run_report', 'reports/memory_historical_cleanup_dry_run_20260505_172806',
    'live_report', 'reports/memory_historical_cleanup_live_expiry_20260505_174752',
    'status_only', 1
  ),
  '{timestamp}'
FROM memory_entries e
JOIN cleanup_expire_candidate_ids c ON c.entry_id = e.entry_id;

UPDATE company_memory
SET active_entry_count = (
      SELECT COUNT(*)
      FROM memory_entries e
      WHERE e.company_id = company_memory.company_id
        AND e.status = 'active'
    ),
    updated_at = '{timestamp}'
WHERE company_id IN (
  SELECT DISTINCT company_id
  FROM memory_entries
  WHERE entry_id IN (SELECT entry_id FROM cleanup_expire_candidate_ids)
);

COMMIT;
"""
    rollback_sql = f"""-- DO_NOT_RUN_rollback_live_expire_first_batch.sql
-- DO_NOT_RUN. Prefer restoring backup/company_memory.sqlite.pre_live_expiry_20260505_174752 for full rollback.
-- This row-id rollback restores only approved entry statuses and summary counts.

BEGIN IMMEDIATE;
CREATE TEMP TABLE cleanup_expire_candidate_ids(entry_id INTEGER PRIMARY KEY);
INSERT INTO cleanup_expire_candidate_ids(entry_id) VALUES
{values};

UPDATE memory_entries
SET status = 'active'
WHERE entry_id IN (SELECT entry_id FROM cleanup_expire_candidate_ids)
  AND status = 'expired';

INSERT INTO change_log (company_id, entry_id, event_type, details_json, created_at)
SELECT
  e.company_id,
  e.entry_id,
  'rollback_expire',
  json_object(
    'source', 'historical_memory_cleanup_rollback',
    'approval_id', '{approval_id}',
    'live_report', 'reports/memory_historical_cleanup_live_expiry_20260505_174752'
  ),
  'OPERATOR_TIMESTAMP_UTC'
FROM memory_entries e
JOIN cleanup_expire_candidate_ids c ON c.entry_id = e.entry_id;

UPDATE company_memory
SET active_entry_count = (
      SELECT COUNT(*)
      FROM memory_entries e
      WHERE e.company_id = company_memory.company_id
        AND e.status = 'active'
    ),
    updated_at = 'OPERATOR_TIMESTAMP_UTC'
WHERE company_id IN (
  SELECT DISTINCT company_id
  FROM memory_entries
  WHERE entry_id IN (SELECT entry_id FROM cleanup_expire_candidate_ids)
);

COMMIT;
"""
    sql_dir = output_dir / "sql_templates"
    sql_dir.mkdir(parents=True, exist_ok=True)
    (sql_dir / "DO_NOT_RUN_executed_live_expire_first_batch.sql").write_text(
        live_sql, encoding="utf-8"
    )
    (sql_dir / "DO_NOT_RUN_rollback_live_expire_first_batch.sql").write_text(
        rollback_sql, encoding="utf-8"
    )


def chown_tree(path: Path, uid: int | None, gid: int | None) -> None:
    if uid is None or gid is None:
        return
    for root, dirs, files in os.walk(path):
        os.chown(root, uid, gid)
        for name in dirs:
            os.chown(Path(root) / name, uid, gid)
        for name in files:
            os.chown(Path(root) / name, uid, gid)


def run(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    if db_path != APPROVED_DB_PATH:
        raise SystemExit(f"Refusing DB path outside approval: {db_path}")
    output_dir = Path(args.output).resolve()
    candidates_path = Path(args.candidates).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    approved_rows = read_csv(candidates_path)
    approved_ids = validate_manifest(approved_rows)
    approval_id = args.approval_id
    timestamp = utc_now()

    pre_live_checksum = sha256_file(db_path)
    backup_path = output_dir / "backup" / "company_memory.sqlite.pre_live_expiry_20260505_174752"
    backup_method = backup_database(db_path, backup_path)
    backup_checksum = sha256_file(backup_path)
    if backup_method == "raw_file_copy" and backup_checksum != pre_live_checksum:
        raise SystemExit(
            f"Backup checksum mismatch: live={pre_live_checksum} backup={backup_checksum}"
        )
    with connect(backup_path) as backup_conn:
        backup_status = status_counts(backup_conn)
    if backup_status.get("active") != EXPECTED_PRE_ACTIVE:
        raise SystemExit(f"Unexpected backup active count: {backup_status}")
    if backup_status.get("expired") != EXPECTED_PRE_EXPIRED:
        raise SystemExit(f"Unexpected backup expired count: {backup_status}")

    validation_rows: list[dict[str, Any]] = []
    expired_rows: list[dict[str, Any]] = []
    before_entity: dict[str, dict[str, int]]
    after_entity: dict[str, dict[str, int]]

    with connect(db_path) as conn:
        before_status = status_counts(conn)
        if before_status.get("active") != EXPECTED_PRE_ACTIVE:
            raise SystemExit(f"Unexpected pre active count: {before_status}")
        if before_status.get("expired") != EXPECTED_PRE_EXPIRED:
            raise SystemExit(f"Unexpected pre expired count: {before_status}")
        before_entity = entity_counts(conn)
        approved_db_rows = fetch_approved_rows(conn, approved_ids)
        if len(approved_db_rows) != APPROVED_ROW_COUNT:
            missing = sorted(set(approved_ids) - set(approved_db_rows))
            raise SystemExit(f"Approved row ids missing from live DB: {missing[:20]}")

        bad_status = [
            rid
            for rid, row in approved_db_rows.items()
            if str(row["status"] or "") != "active"
        ]
        if bad_status:
            raise SystemExit(f"Approved rows not active before cleanup: {bad_status[:20]}")

        row_by_id = {row_id(row): row for row in approved_rows}
        for rid in approved_ids:
            db_row = approved_db_rows[rid]
            csv_row = row_by_id[rid]
            source_match = str(db_row["source_id"]) == str(csv_row["source_id"])
            statement_match = " ".join(str(db_row["statement"]).lower().split()) == " ".join(
                str(csv_row["statement/text"]).lower().split()
            )
            entity_match = str(db_row["company_id"]).upper() == str(
                csv_row["ticker/entity"]
            ).upper()
            type_match = str(db_row["type"]) == str(csv_row["memory_type"])
            status = (
                "valid"
                if source_match and statement_match and entity_match and type_match
                else "invalid"
            )
            validation_rows.append(
                {
                    "row_id": rid,
                    "company_id": str(db_row["company_id"]),
                    "memory_type": str(db_row["type"]),
                    "status_before": str(db_row["status"]),
                    "source_id_match": "yes" if source_match else "no",
                    "statement_match": "yes" if statement_match else "no",
                    "entity_match": "yes" if entity_match else "no",
                    "memory_type_match": "yes" if type_match else "no",
                    "validation_status": status,
                }
            )
        invalid = [row for row in validation_rows if row["validation_status"] != "valid"]
        if invalid:
            write_csv(
                output_dir / "csv" / "live_candidate_validation_results.csv",
                validation_rows,
                list(validation_rows[0].keys()),
            )
            raise SystemExit(f"Approved row validation failed: {invalid[:3]}")

        conn.execute("BEGIN IMMEDIATE")
        for rid in approved_ids:
            db_row = approved_db_rows[rid]
            conn.execute(
                """
                UPDATE memory_entries
                SET status = 'expired'
                WHERE entry_id = ? AND status = 'active'
                """,
                (rid,),
            )
            conn.execute(
                """
                INSERT INTO change_log (
                    company_id, entry_id, event_type, details_json, created_at
                )
                VALUES (?, ?, 'expire', ?, ?)
                """,
                (
                    str(db_row["company_id"]),
                    rid,
                    json.dumps(
                        {
                            "source": "historical_memory_cleanup",
                            "approval_id": approval_id,
                            "dry_run_report": "reports/memory_historical_cleanup_dry_run_20260505_172806",
                            "live_report": "reports/memory_historical_cleanup_live_expiry_20260505_174752",
                            "status_only": True,
                        },
                        sort_keys=True,
                    ),
                    timestamp,
                ),
            )
            expired_rows.append(
                {
                    "row_id": rid,
                    "company_id": str(db_row["company_id"]),
                    "memory_type": str(db_row["type"]),
                    "statement": str(db_row["statement"]),
                    "source": str(db_row["source"]),
                    "source_id": str(db_row["source_id"]),
                    "status_before": "active",
                    "status_after": "expired",
                    "first_seen_at": str(db_row["first_seen_at"]),
                    "last_seen_at": str(db_row["last_seen_at"]),
                    "closed_at": str(db_row["closed_at"] or ""),
                    "cleanup_timestamp": timestamp,
                    "approval_id": approval_id,
                }
            )
        affected_companies = sorted(
            {str(approved_db_rows[rid]["company_id"]) for rid in approved_ids}
        )
        for company_id in affected_companies:
            conn.execute(
                """
                UPDATE company_memory
                SET active_entry_count = (
                    SELECT COUNT(*)
                    FROM memory_entries
                    WHERE company_id = ? AND status = 'active'
                ),
                    updated_at = ?
                WHERE company_id = ?
                """,
                (company_id, timestamp, company_id),
            )
        after_status = status_counts(conn)
        if after_status.get("active") != EXPECTED_POST_ACTIVE:
            raise SystemExit(f"Unexpected post active count in transaction: {after_status}")
        if after_status.get("expired") != EXPECTED_POST_EXPIRED:
            raise SystemExit(f"Unexpected post expired count in transaction: {after_status}")
        remaining_active = [
            row["entry_id"]
            for row in conn.execute(
                f"SELECT entry_id FROM memory_entries WHERE entry_id IN ({','.join('?' for _ in approved_ids)}) AND status = 'active'",
                approved_ids,
            ).fetchall()
        ]
        if remaining_active:
            raise SystemExit(f"Approved rows still active in transaction: {remaining_active[:20]}")
        conn.commit()

    with connect(db_path) as conn:
        final_status = status_counts(conn)
        after_entity = entity_counts(conn)
        audit_count = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM change_log
            WHERE event_type = 'expire'
              AND json_extract(details_json, '$.approval_id') = ?
            """,
            (approval_id,),
        ).fetchone()["n"]
        if int(audit_count) != APPROVED_ROW_COUNT:
            raise SystemExit(f"Unexpected audit count after commit: {audit_count}")
        changed_active = conn.execute(
            f"SELECT COUNT(*) AS n FROM memory_entries WHERE entry_id IN ({','.join('?' for _ in approved_ids)}) AND status = 'expired'",
            approved_ids,
        ).fetchone()["n"]
        if int(changed_active) != APPROVED_ROW_COUNT:
            raise SystemExit(f"Unexpected approved expired count: {changed_active}")

    with sqlite3.connect(db_path) as checkpoint_conn:
        checkpoint_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    post_live_checksum = sha256_file(db_path)
    write_csv(
        output_dir / "csv" / "live_candidate_validation_results.csv",
        validation_rows,
        list(validation_rows[0].keys()),
    )
    write_csv(
        output_dir / "csv" / "live_rows_expired.csv",
        expired_rows,
        list(expired_rows[0].keys()),
    )

    before_after_rows: list[dict[str, Any]] = []
    for entity in sorted(set(before_entity) | set(after_entity)):
        before = before_entity.get(entity, {"active": 0, "expired": 0})
        after = after_entity.get(entity, {"active": 0, "expired": 0})
        before_after_rows.append(
            {
                "entity": entity,
                "active_before": before["active"],
                "expired_before": before["expired"],
                "active_after": after["active"],
                "expired_after": after["expired"],
                "active_delta": after["active"] - before["active"],
                "expired_delta": after["expired"] - before["expired"],
            }
        )
    write_csv(
        output_dir / "csv" / "live_before_after_counts_by_entity.csv",
        before_after_rows,
        [
            "entity",
            "active_before",
            "expired_before",
            "active_after",
            "expired_after",
            "active_delta",
            "expired_delta",
        ],
    )

    metadata = {
        "approval_id": approval_id,
        "approved_manifest": str(candidates_path),
        "approved_rows": APPROVED_ROW_COUNT,
        "db_path": str(db_path),
        "backup_path": str(backup_path),
        "pre_live_checksum": pre_live_checksum,
        "backup_checksum": backup_checksum,
        "backup_method": backup_method,
        "post_live_checksum": post_live_checksum,
        "before_status_counts": before_status,
        "after_status_counts": final_status,
        "audit_rows_inserted": APPROVED_ROW_COUNT,
        "company_summary_rows_touched": len(
            {str(row["company_id"]) for row in expired_rows}
        ),
        "executed_at": timestamp,
        "executor": "codex",
        "mutation_scope": "memory_entries.status plus change_log audit rows and company_memory summary counts",
    }
    (output_dir / "live_cleanup_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = f"""# Live Memory Expiry First Batch

Lane: Memory
Execution mode: SAFE EXTENSION MODE
Approval: {approval_id}
Approved manifest: `{candidates_path}`
Live DB: `{db_path}`

## Result

- Approved rows: {APPROVED_ROW_COUNT}
- Rows expired: {APPROVED_ROW_COUNT}
- Rows skipped: 0
- Audit rows inserted: {APPROVED_ROW_COUNT}
- Status counts before: {before_status}
- Status counts after: {final_status}
- Backup path: `{backup_path}`
- Backup checksum: `{backup_checksum}`
- Backup method: `{backup_method}`
- Live checksum before: `{pre_live_checksum}`
- Live checksum after: `{post_live_checksum}`

## Scope

The live mutation changed only approved `memory_entries.status` values, inserted `change_log` audit rows, and refreshed `company_memory.active_entry_count` summaries for affected companies. It did not delete rows, rewrite text, canonicalize aliases, rehome market/macro rows, touch market/thesis/session stores, reindex Qdrant, run ingestion, change retrieval/ranking, or change financial truth.
"""
    (output_dir / "README.md").write_text(summary, encoding="utf-8")
    write_sql_templates(output_dir, approved_ids, approval_id, timestamp)

    checksums = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256":
            checksums.append(f"{sha256_file(path)}  {path}")
    (output_dir / "checksums.sha256").write_text("\n".join(checksums) + "\n")
    chown_tree(output_dir, args.chown_uid, args.chown_gid)
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--chown-uid", type=int)
    parser.add_argument("--chown-gid", type=int)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
