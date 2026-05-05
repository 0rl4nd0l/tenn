-- DO_NOT_RUN_cleanup_candidates.sql
-- Historical company-memory cleanup candidate templates only.
-- Do not execute this file against a live DB.
-- This template is for operator review and copied-DB dry runs.

-- 1. Inspect current row state by stable row id.
-- Replace the row ids with an approved, checksum-verified candidate set.
SELECT entry_id, company_id, type, statement, status, source, source_id, first_seen_at, last_seen_at
FROM memory_entries
WHERE entry_id IN (/* APPROVED_ROW_IDS */)
ORDER BY entry_id;

-- 2. Copied-DB dry-run only: preview active rows that would be expired.
SELECT count(*) AS active_candidate_count
FROM memory_entries
WHERE entry_id IN (/* APPROVED_ROW_IDS */)
  AND status = 'active';

-- 3. DO NOT RUN LIVE. Future live cleanup must be transaction-wrapped by reviewed code
-- that verifies expected row counts and writes change_log rows.
-- UPDATE memory_entries
-- SET status = 'expired', closed_at = :cleanup_timestamp, last_seen_at = :cleanup_timestamp
-- WHERE entry_id IN (/* APPROVED_ROW_IDS */)
--   AND status = 'active';

-- 4. DO NOT RUN LIVE. Example change-log insert shape only.
-- INSERT INTO change_log (company_id, entry_id, event_type, details_json, created_at)
-- SELECT company_id,
--        entry_id,
--        'expire',
--        json_object(
--          'source', 'memory_historical_cleanup_plan_20260505_170452',
--          'reason', 'operator-approved duplicate fanout cleanup',
--          'candidate_csv_checksum', :candidate_csv_checksum
--        ),
--        :cleanup_timestamp
-- FROM memory_entries
-- WHERE entry_id IN (/* APPROVED_ROW_IDS */);
