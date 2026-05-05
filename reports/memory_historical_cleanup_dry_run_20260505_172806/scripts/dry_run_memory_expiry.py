#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HIGH_RISK_TICKERS = [
    "BHP",
    "A2M",
    "A2 MILK",
    "COH",
    "WES",
    "ASX",
    "ACC",
    "ACCENT GROUP",
    "PET",
    "PETT",
    "PETTIMED",
    "GCM",
    "GCMC",
    "GCM CORPORATION",
    "MAR",
    "MARINO",
    "MARINO AND CO",
    "KEY",
    "KEYP",
    "KEY PETROLEUM",
    "WIN",
    "WIN MEDALS",
    "END",
    "EDV",
    "ENDV",
    "ENDEAVOR GROUP",
]

COHORT_FILES = {
    "preserve": "memory_rows_to_preserve.csv",
    "manual_review": "memory_rows_manual_review.csv",
    "blocked_uncertain": "memory_rows_blocked_uncertain.csv",
    "alias_merge_later": "memory_rows_alias_merge_candidates.csv",
    "rehome_later": "memory_rows_rehome_market_macro_candidates.csv",
}

PLAN_CLASSIFICATION_FILES = [
    "memory_rows_to_preserve.csv",
    "memory_rows_manual_review.csv",
    "memory_rows_quarantine_candidates.csv",
    "memory_rows_expire_candidates.csv",
    "memory_rows_alias_merge_candidates.csv",
    "memory_rows_rehome_market_macro_candidates.csv",
    "memory_rows_blocked_uncertain.csv",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def row_id(row: dict[str, str]) -> int | None:
    try:
        return int(str(row.get("row_id") or "").strip())
    except ValueError:
        return None


def normalize_entity(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def repo_root() -> Path:
    # script is reports/<report>/scripts/dry_run_memory_expiry.py
    return Path(__file__).resolve().parents[3]


def report_root() -> Path:
    return Path(__file__).resolve().parents[1]


def refuse_unsafe_paths(copied_db: Path, output_dir: Path) -> None:
    root = repo_root()
    report = report_root()
    resolved_db = copied_db.expanduser().resolve()
    resolved_output = output_dir.expanduser().resolve()
    live_like_roots = [
        root / "financial-engine_v2" / "data",
        root / "financial-engine_v2" / "reports",
        root / "reports" / "research_memory",
    ]
    for live_root in live_like_roots:
        if is_relative_to(resolved_db, live_root.resolve()):
            raise SystemExit(f"Refusing live-looking DB path: {resolved_db}")
    if not (is_relative_to(resolved_db, report.resolve()) or is_relative_to(resolved_db, Path("/tmp"))):
        raise SystemExit(
            "Refusing copied DB outside the report folder or /tmp: "
            f"{resolved_db}"
        )
    if not is_relative_to(resolved_output, report.resolve()):
        raise SystemExit(f"Refusing output outside report folder: {resolved_output}")
    if resolved_db.name != "company_memory.sqlite":
        raise SystemExit(f"Expected copied company_memory.sqlite, got: {resolved_db.name}")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def checkpoint_sqlite(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def fetch_rows(conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    rows = conn.execute("SELECT * FROM memory_entries ORDER BY entry_id ASC").fetchall()
    return {int(row["entry_id"]): row for row in rows}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {}
    for row in conn.execute(
        "SELECT status, COUNT(*) AS n FROM memory_entries GROUP BY status ORDER BY status"
    ):
        counts[str(row["status"])] = int(row["n"])
    return counts


def entity_counts(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "active": 0, "expired": 0, "other": 0}
    )
    for row in conn.execute(
        """
        SELECT company_id, status, COUNT(*) AS n
        FROM memory_entries
        GROUP BY company_id, status
        ORDER BY company_id, status
        """
    ):
        entity = normalize_entity(row["company_id"])
        status = str(row["status"] or "")
        n = int(row["n"])
        counts[entity]["total"] += n
        if status == "active":
            counts[entity]["active"] += n
        elif status == "expired":
            counts[entity]["expired"] += n
        else:
            counts[entity]["other"] += n
    return dict(counts)


def counts_by_column(conn: sqlite3.Connection, column: str) -> list[dict[str, Any]]:
    rows = []
    query = f"SELECT {column} AS value, status, COUNT(*) AS n FROM memory_entries GROUP BY {column}, status ORDER BY {column}, status"
    for row in conn.execute(query):
        rows.append(
            {
                "value": str(row["value"] or ""),
                "status": str(row["status"] or ""),
                "row_count": int(row["n"]),
            }
        )
    return rows


def load_cohort_sets(plan_csv_root: Path) -> dict[str, set[int]]:
    sets: dict[str, set[int]] = {}
    for key, filename in COHORT_FILES.items():
        path = plan_csv_root / filename
        ids: set[int] = set()
        if path.exists():
            for row in read_csv(path):
                rid = row_id(row)
                if rid is not None:
                    ids.add(rid)
        sets[key] = ids
    return sets


def load_all_classified_ids(plan_csv_root: Path) -> set[int]:
    ids: set[int] = set()
    for filename in PLAN_CLASSIFICATION_FILES:
        path = plan_csv_root / filename
        if not path.exists():
            raise SystemExit(f"Missing required candidate CSV: {path}")
        for row in read_csv(path):
            rid = row_id(row)
            if rid is not None:
                ids.add(rid)
    return ids


def load_cluster_rows(plan_csv_root: Path) -> dict[str, dict[str, str]]:
    path = plan_csv_root / "fanout_cluster_cleanup_candidates.csv"
    if not path.exists():
        return {}
    rows = read_csv(path)
    return {str(row.get("duplicate_cluster_id") or ""): row for row in rows}


def stable_provenance(db_row: sqlite3.Row | None, candidate: dict[str, str]) -> bool:
    if db_row is None:
        return False
    db_source_id = str(db_row["source_id"] or "").strip()
    db_source = str(db_row["source"] or "").strip()
    csv_source_id = str(candidate.get("source_id") or "").strip()
    return bool(db_source_id and db_source and csv_source_id and csv_source_id != "DATA_MISSING")


def build_validation_rows(
    candidates: list[dict[str, str]],
    db_rows: dict[int, sqlite3.Row],
    cohort_sets: dict[str, set[int]],
) -> tuple[list[dict[str, Any]], set[int]]:
    id_counts = Counter(row_id(row) for row in candidates)
    id_counts.pop(None, None)
    duplicate_ids = {int(rid) for rid, count in id_counts.items() if count > 1}
    validation_rows: list[dict[str, Any]] = []
    valid_ids: set[int] = set()
    for candidate in candidates:
        rid = row_id(candidate)
        db_row = db_rows.get(rid or -1)
        overlaps_preserve = rid in cohort_sets.get("preserve", set())
        overlaps_manual = rid in cohort_sets.get("manual_review", set())
        overlaps_blocked = rid in cohort_sets.get("blocked_uncertain", set())
        overlaps_any_nonexpire = any(
            rid in ids
            for key, ids in cohort_sets.items()
            if key != "expire"
        )
        exists = db_row is not None
        status_before = str(db_row["status"] or "") if db_row is not None else "DATA_MISSING"
        active_like = status_before == "active"
        candidate_action_ok = (
            str(candidate.get("proposed_action") or "") == "status_expire_candidate"
        )
        source_match = (
            db_row is not None
            and str(db_row["source_id"] or "") == str(candidate.get("source_id") or "")
        )
        statement_match = (
            db_row is not None
            and normalize_text(db_row["statement"])
            == normalize_text(candidate.get("statement/text"))
        )
        type_match = (
            db_row is not None
            and str(db_row["type"] or "") == str(candidate.get("memory_type") or "")
        )
        entity_match = (
            db_row is not None
            and normalize_entity(db_row["company_id"])
            == normalize_entity(candidate.get("ticker/entity"))
        )
        provenance_ok = stable_provenance(db_row, candidate)
        skip_reasons = []
        if rid is None:
            skip_reasons.append("invalid_row_id")
        if rid in duplicate_ids:
            skip_reasons.append("duplicate_candidate_row_id")
        if not exists:
            skip_reasons.append("missing_from_db")
        if exists and not active_like:
            skip_reasons.append("not_active")
        if not candidate_action_ok:
            skip_reasons.append("wrong_proposed_action")
        if not source_match:
            skip_reasons.append("source_id_mismatch")
        if not statement_match:
            skip_reasons.append("statement_mismatch")
        if not type_match:
            skip_reasons.append("memory_type_mismatch")
        if not entity_match:
            skip_reasons.append("entity_mismatch")
        if overlaps_preserve:
            skip_reasons.append("overlaps_preserve")
        if overlaps_manual:
            skip_reasons.append("overlaps_manual_review")
        if overlaps_blocked:
            skip_reasons.append("overlaps_blocked_uncertain")
        if not provenance_ok:
            skip_reasons.append("lacking_stable_provenance")
        status = "valid_for_copied_db_expiry" if not skip_reasons else "skip"
        if status == "valid_for_copied_db_expiry" and rid is not None:
            valid_ids.add(rid)
        validation_rows.append(
            {
                "row_id": rid if rid is not None else str(candidate.get("row_id") or ""),
                "ticker_entity": candidate.get("ticker/entity", ""),
                "db_entity": str(db_row["company_id"] or "") if db_row is not None else "DATA_MISSING",
                "memory_type": candidate.get("memory_type", ""),
                "status_before": status_before,
                "classification": candidate.get("classification", ""),
                "proposed_action": candidate.get("proposed_action", ""),
                "duplicate_cluster_id": candidate.get("duplicate_cluster_id", ""),
                "fanout_cluster_size": candidate.get("fanout_cluster_size", ""),
                "exists_in_copied_db": "yes" if exists else "no",
                "active_like": "yes" if active_like else "no",
                "source_id_match": "yes" if source_match else "no",
                "statement_match": "yes" if statement_match else "no",
                "memory_type_match": "yes" if type_match else "no",
                "entity_match": "yes" if entity_match else "no",
                "stable_provenance": "yes" if provenance_ok else "no",
                "overlaps_preserve": "yes" if overlaps_preserve else "no",
                "overlaps_manual_review": "yes" if overlaps_manual else "no",
                "overlaps_blocked_uncertain": "yes" if overlaps_blocked else "no",
                "overlaps_any_nonexpire": "yes" if overlaps_any_nonexpire else "no",
                "validation_status": status,
                "skip_reason": "|".join(skip_reasons),
            }
        )
    return validation_rows, valid_ids


def fanout_sample(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    by_cluster: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_cluster[str(row.get("duplicate_cluster_id") or "NO_CLUSTER")].append(row)
    selected: list[dict[str, str]] = []
    for cluster_id in sorted(by_cluster):
        if len(selected) >= count:
            break
        selected.append(sorted(by_cluster[cluster_id], key=lambda r: int(r.get("row_id") or 0))[0])
    if len(selected) < count:
        selected_ids = {str(row.get("row_id") or "") for row in selected}
        for row in sorted(rows, key=lambda r: int(r.get("row_id") or 0)):
            if len(selected) >= count:
                break
            if str(row.get("row_id") or "") not in selected_ids:
                selected.append(row)
    return selected


def sample_rows(rows: list[dict[str, str]], count: int, label: str) -> list[dict[str, Any]]:
    sampled = fanout_sample(rows, count)
    output = []
    for row in sampled:
        entity = normalize_entity(row.get("ticker/entity"))
        statement = normalize_text(row.get("statement/text"))
        entity_text_present = bool(entity and len(entity) > 2 and entity.lower() in statement)
        if label == "expire":
            review_note = (
                "operator_spot_check_entity_text_present"
                if entity_text_present
                else "no_obvious_preserve_conflict_by_csv_mapping"
            )
        elif label == "blocked_uncertain":
            review_note = (
                "possible_future_manual_expiry_review"
                if str(row.get("duplicate_cluster_id") or "").startswith("fanout_")
                else "blocked_without_cluster"
            )
        else:
            review_note = "sampled_for_operator_review"
        output.append(
            {
                **row,
                "sample_review_label": label,
                "entity_text_present_in_statement": "yes" if entity_text_present else "no",
                "review_note": review_note,
            }
        )
    return output


def select_first_batch(
    candidates: list[dict[str, str]],
    valid_ids: set[int],
    clusters: dict[str, dict[str, str]],
    max_rows: int = 250,
) -> list[dict[str, Any]]:
    candidate_by_cluster: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        rid = row_id(row)
        if rid in valid_ids:
            candidate_by_cluster[str(row.get("duplicate_cluster_id") or "")].append(row)
    eligible_clusters = []
    for cluster_id, cluster in clusters.items():
        try:
            preserve = int(cluster.get("preserve_count") or 0)
            manual = int(cluster.get("manual_review_count") or 0)
            quarantine = int(cluster.get("quarantine_count") or 0)
            blocked = int(cluster.get("blocked_count") or 0)
            alias = int(cluster.get("alias_merge_count") or 0)
            expire = int(cluster.get("expire_count") or 0)
        except ValueError:
            continue
        if expire <= 0:
            continue
        if preserve <= 0 or manual or quarantine or blocked or alias:
            continue
        if cluster_id not in candidate_by_cluster:
            continue
        eligible_clusters.append((cluster_id, expire, preserve))
    eligible_clusters.sort(key=lambda item: (-item[1], item[0]))
    chosen_clusters: set[str] = set()
    total = 0
    for cluster_id, expire_count, _preserve in eligible_clusters:
        rows_in_cluster = len(candidate_by_cluster[cluster_id])
        next_count = rows_in_cluster or expire_count
        if total + next_count > max_rows:
            continue
        chosen_clusters.add(cluster_id)
        total += next_count
    output = []
    for cluster_id in sorted(chosen_clusters):
        for row in sorted(candidate_by_cluster[cluster_id], key=lambda r: int(r.get("row_id") or 0)):
            output.append(
                {
                    **row,
                    "first_batch_reason": (
                        "cluster_has_preserved_target_no_alias_manual_or_blocked_rows"
                    ),
                    "recommended_batch": "first",
                }
            )
    return output


def run(args: argparse.Namespace) -> int:
    copied_db = Path(args.copied_db)
    candidates_path = Path(args.candidates)
    output_dir = Path(args.output)
    refuse_unsafe_paths(copied_db, output_dir)
    plan_csv_root = candidates_path.expanduser().resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    checksum_before = sha256_file(copied_db)
    print(f"copied_db_sha256_before {checksum_before}")

    candidates = read_csv(candidates_path)
    candidate_ids = [rid for rid in (row_id(row) for row in candidates) if rid is not None]
    clusters = load_cluster_rows(plan_csv_root)
    cohort_sets = load_cohort_sets(plan_csv_root)
    all_classified_ids = load_all_classified_ids(plan_csv_root)

    with connect(copied_db) as conn:
        if not table_exists(conn, "memory_entries"):
            raise SystemExit("Copied DB missing memory_entries table")
        if not table_exists(conn, "change_log"):
            raise SystemExit("Copied DB missing change_log table")
        total_rows = conn.execute("SELECT COUNT(*) AS n FROM memory_entries").fetchone()["n"]
        if int(total_rows) != len(all_classified_ids):
            raise SystemExit(
                f"Classified row total {len(all_classified_ids)} does not equal DB row count {total_rows}"
            )
        before_status = status_counts(conn)
        before_entity = entity_counts(conn)
        before_by_type = counts_by_column(conn, "type")
        before_by_source = counts_by_column(conn, "source")
        db_rows = fetch_rows(conn)
        validation_rows, valid_ids = build_validation_rows(candidates, db_rows, cohort_sets)

        overlap_failures = [
            row
            for row in validation_rows
            if row["overlaps_preserve"] == "yes"
            or row["overlaps_manual_review"] == "yes"
            or row["overlaps_blocked_uncertain"] == "yes"
        ]
        if overlap_failures:
            write_csv(
                output_dir / "candidate_validation_results.csv",
                validation_rows,
                list(validation_rows[0].keys()),
            )
            raise SystemExit(
                "Hard stop: expiry candidates overlap preserve/manual/blocked cohorts"
            )

        now = utc_now()
        expired_rows: list[dict[str, Any]] = []
        skipped_rows: list[dict[str, Any]] = []
        for candidate in candidates:
            rid = row_id(candidate)
            db_row = db_rows.get(rid or -1)
            validation = next(
                row for row in validation_rows if str(row["row_id"]) == str(candidate.get("row_id"))
            )
            if rid not in valid_ids or db_row is None:
                skipped_rows.append(
                    {
                        **candidate,
                        "skip_reason": validation["skip_reason"],
                        "status_before": validation["status_before"],
                    }
                )
                continue
            conn.execute(
                "UPDATE memory_entries SET status = 'expired' WHERE entry_id = ?",
                (rid,),
            )
            conn.execute(
                """
                INSERT INTO change_log (company_id, entry_id, event_type, details_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(db_row["company_id"]),
                    rid,
                    "dry_run_expire",
                    json.dumps(
                        {
                            "dry_run": True,
                            "original_status": str(db_row["status"]),
                            "candidate_source": str(candidates_path),
                            "duplicate_cluster_id": candidate.get("duplicate_cluster_id", ""),
                            "reason": candidate.get("reason", ""),
                        },
                        sort_keys=True,
                    ),
                    now,
                ),
            )
            expired_rows.append(
                {
                    "row_id": rid,
                    "company_id": str(db_row["company_id"]),
                    "memory_type": str(db_row["type"]),
                    "statement": str(db_row["statement"]),
                    "original_status": str(db_row["status"]),
                    "new_status": "expired",
                    "source": str(db_row["source"]),
                    "source_id": str(db_row["source_id"]),
                    "confidence": db_row["confidence"],
                    "materiality": db_row["materiality"],
                    "persistence": str(db_row["persistence"]),
                    "first_seen_at": str(db_row["first_seen_at"]),
                    "last_seen_at": str(db_row["last_seen_at"]),
                    "closed_at": str(db_row["closed_at"] or ""),
                    "duplicate_cluster_id": candidate.get("duplicate_cluster_id", ""),
                    "fanout_cluster_size": candidate.get("fanout_cluster_size", ""),
                    "classification": candidate.get("classification", ""),
                    "dry_run_change_log_event": "dry_run_expire",
                }
            )
        after_status = status_counts(conn)
        after_entity = entity_counts(conn)
        after_change_log_count = conn.execute("SELECT COUNT(*) AS n FROM change_log").fetchone()["n"]

    checkpoint_sqlite(copied_db)
    checksum_after = sha256_file(copied_db)
    print(f"copied_db_sha256_after {checksum_after}")
    print(f"candidate_rows {len(candidates)}")
    print(f"rows_expired_in_copy {len(expired_rows)}")
    print(f"rows_skipped {len(skipped_rows)}")

    field_validation = list(validation_rows[0].keys()) if validation_rows else ["row_id"]
    write_csv(output_dir / "candidate_validation_results.csv", validation_rows, field_validation)
    write_csv(
        output_dir / "dry_run_rows_expired.csv",
        expired_rows,
        [
            "row_id",
            "company_id",
            "memory_type",
            "statement",
            "original_status",
            "new_status",
            "source",
            "source_id",
            "confidence",
            "materiality",
            "persistence",
            "first_seen_at",
            "last_seen_at",
            "closed_at",
            "duplicate_cluster_id",
            "fanout_cluster_size",
            "classification",
            "dry_run_change_log_event",
        ],
    )
    write_csv(
        output_dir / "dry_run_rows_skipped.csv",
        skipped_rows,
        list(skipped_rows[0].keys()) if skipped_rows else ["row_id", "skip_reason"],
    )

    candidate_counts_by_entity = Counter(
        normalize_entity(row.get("ticker/entity"))
        for row in candidates
        if row_id(row) in valid_ids
    )
    count_rows: list[dict[str, Any]] = []
    entities = sorted(set(before_entity) | set(after_entity))
    for entity in entities:
        before = before_entity.get(entity, {"total": 0, "active": 0, "expired": 0, "other": 0})
        after = after_entity.get(entity, {"total": 0, "active": 0, "expired": 0, "other": 0})
        active_before = int(before["active"])
        active_after = int(after["active"])
        reduction = active_before - active_after
        pct = round((reduction / active_before * 100.0), 2) if active_before else 0.0
        count_rows.append(
            {
                "entity": entity,
                "total_rows_before": before["total"],
                "active_before": active_before,
                "expired_before": before["expired"],
                "expire_candidate_count": candidate_counts_by_entity.get(entity, 0),
                "total_rows_after": after["total"],
                "active_after": active_after,
                "expired_after": after["expired"],
                "active_delta": active_after - active_before,
                "active_reduction_pct": pct,
                "nearly_emptied": "yes" if active_before >= 1 and active_after <= 2 and reduction > 0 else "no",
                "below_floor_after": "yes" if active_after < 3 else "no",
            }
        )
    count_fields = [
        "entity",
        "total_rows_before",
        "active_before",
        "expired_before",
        "expire_candidate_count",
        "total_rows_after",
        "active_after",
        "expired_after",
        "active_delta",
        "active_reduction_pct",
        "nearly_emptied",
        "below_floor_after",
    ]
    write_csv(output_dir / "pre_dry_run_counts_by_entity.csv", count_rows, count_fields)
    write_csv(output_dir / "post_dry_run_counts_by_entity.csv", count_rows, count_fields)

    high_risk_rows = [row for row in count_rows if row["entity"] in set(HIGH_RISK_TICKERS)]
    write_csv(output_dir / "high_risk_ticker_before_after.csv", high_risk_rows, count_fields)

    expire_sample = sample_rows(candidates, 50, "expire")
    manual_rows = read_csv(plan_csv_root / "memory_rows_manual_review.csv")
    blocked_rows = read_csv(plan_csv_root / "memory_rows_blocked_uncertain.csv")
    preserve_rows = read_csv(plan_csv_root / "memory_rows_to_preserve.csv")
    write_csv(output_dir / "sample_expire_candidates.csv", expire_sample, list(expire_sample[0].keys()))
    manual_sample = sample_rows(manual_rows, 30, "manual_review")
    blocked_sample = sample_rows(blocked_rows, 30, "blocked_uncertain")
    preserve_sample = sample_rows(preserve_rows, 20, "preserve")
    write_csv(output_dir / "sample_manual_review.csv", manual_sample, list(manual_sample[0].keys()))
    write_csv(output_dir / "sample_blocked_uncertain.csv", blocked_sample, list(blocked_sample[0].keys()))
    write_csv(output_dir / "sample_preserve.csv", preserve_sample, list(preserve_sample[0].keys()))

    first_batch = select_first_batch(candidates, valid_ids, clusters, max_rows=250)
    write_csv(
        output_dir / "operator_first_batch_candidates.csv",
        first_batch,
        list(first_batch[0].keys()) if first_batch else ["row_id"],
    )

    metadata = {
        "copied_db": str(copied_db.expanduser().resolve()),
        "checksum_before": checksum_before,
        "checksum_after": checksum_after,
        "candidate_rows": len(candidates),
        "rows_expired_in_copy": len(expired_rows),
        "rows_skipped": len(skipped_rows),
        "status_counts_before": before_status,
        "status_counts_after": after_status,
        "before_by_type": before_by_type,
        "before_by_source": before_by_source,
        "change_log_rows_after": after_change_log_count,
        "first_batch_count": len(first_batch),
        "excluded_from_first_batch_count": len(candidates) - len(first_batch),
        "entities_nearly_emptied_count": sum(1 for row in count_rows if row["nearly_emptied"] == "yes"),
        "entities_below_floor_after_count": sum(1 for row in count_rows if row["below_floor_after"] == "yes"),
    }
    (output_dir / "dry_run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate company-memory status expiry on a copied SQLite DB only. "
            "The script refuses live-looking Tenn DB paths and writes CSVs only under its report folder."
        )
    )
    parser.add_argument("--copied-db", required=True, help="Path to copied company_memory.sqlite")
    parser.add_argument("--candidates", required=True, help="memory_rows_expire_candidates.csv")
    parser.add_argument("--output", required=True, help="Report csv output directory")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
