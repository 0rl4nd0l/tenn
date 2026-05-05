# Next Codex Prompts

## Dry Run Prompt

```text
You are Codex working on Tenn.

Task: Dry-run historical company-memory cleanup against copied SQLite DBs only.

Lane: Memory.
Execution mode: AUDIT MODE ONLY.
Use report folder `reports/memory_historical_cleanup_plan_20260505_170452` as the candidate source. Copy live `company_memory.sqlite`, `market_memory.sqlite`, source registry, and memo JSONL files to a new temporary directory. Do not open live DBs for write. Do not update, delete, insert, migrate, vacuum, reindex Qdrant, reprocess news/transcripts, tune retrieval/ranking, or change answer synthesis.

Required dry run:
1. Verify candidate CSV checksums from `csv_checksums.sha256`.
2. Verify row ids still exist in the copied company-memory DB and current statuses match the CSV.
3. Simulate allowed action types only on a throwaway copied DB: first `status_expire_candidate` rows only, capped by an operator-provided max row count.
4. Produce before/after row counts, active counts by company_id, change-log simulation counts, and a sample verification table.
5. Do not touch live DBs.

Stop if any candidate row is missing, row status changed unexpectedly, checksum mismatches, or the operator has not supplied a max dry-run row count.

```

## Live Cleanup Prompt

```text
You are Codex working on Tenn.

Task: Live historical company-memory cleanup execution after explicit operator approval.

Lane: Memory.
Execution mode: SAFE EXTENSION MODE for live DB status-only mutation, but only if this prompt includes explicit approvals for action types, max row count, backup path/checksum, and candidate CSV checksum.

Allowed first live action: `status_expire_candidate` only. Do not quarantine, delete, rewrite statements, normalize aliases, rehome rows, migrate DBs, reindex Qdrant, reprocess news/transcripts, tune retrieval/ranking, change answer synthesis, or change source labels.

Required sequence:
1. Re-read SYSTEM_CONTRACT.md and `reports/memory_historical_cleanup_plan_20260505_170452`.
2. Verify live DB path, backup path, backup checksum, candidate CSV checksum, and operator max row count.
3. Start a SQLite transaction on the live company-memory DB only after all gates pass.
4. For approved row ids, update status to `expired`, set `closed_at`/`last_seen_at`, and insert one `change_log` row per mutation with the cleanup report id and reason.
5. Commit only if affected row count equals expected row count; otherwise roll back.
6. Run post-cleanup row-count diff and sample verification.
7. Commit a milestone report only after validation.

Stop unless the user prompt explicitly says: I approve live status-expire cleanup for N rows from candidate CSV checksum <sha256> against backup checksum <sha256>.

```
