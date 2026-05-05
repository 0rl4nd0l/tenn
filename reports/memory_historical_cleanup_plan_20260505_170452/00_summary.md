# Summary

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn (shell pwd resolved to /home/l4nd0/tenn)
Execution mode: AUDIT MODE ONLY
Intended files: reports/memory_historical_cleanup_plan_20260505_170452/*
Contested surfaces touched: none
Collision risk: MEDIUM for report generation and copied-DB inspection; HIGH for any live cleanup, DB mutation, alias migration, or reindexing
Decision: audit only

## Contract Position

Target layer: Storage and Retrieval-adjacent Memory.
Relevant rules: SYSTEM_CONTRACT.md sections 1.1, 1.2, 2.2, 5.1, 5.4, 7, 8, 10.2, and 10.3.
Must not change: live memory rows, canonical financial truth, market/user/session memory boundaries, Qdrant, news/transcript ingestion, retrieval ranking, answer synthesis, source labels, or production routing.
Why safe: this lane created reports and CSV candidates only, and inspected copied SQLite files for deeper SQL analysis.

## Counts

| proposed_action | row_count | current_schema_support | future_gate_required |
|---|---:|---|---|
| `no_action_preserve` | 34 | yes | none |
| `manual_review` | 316 | yes | operator review |
| `status_quarantine_candidate` | 0 | no | schema migration adding quarantined status plus operator approval |
| `status_expire_candidate` | 1212 | yes | operator approval plus backup and max-row-count gate |
| `alias_merge_candidate_later` | 53 | no | ASX identity audit, source-preserving alias map, and separate prompt |
| `market_memory_rehome_candidate_later` | 69 | no | source review, rehome design, no-delete archival plan |
| `macro_memory_rehome_candidate_later` | 147 | no | source review, rehome design, no-delete archival plan |
| `do_not_touch_blocked` | 167 | yes | additional provenance or source evidence |

## Final Answers

- Is historical cleanup now safe to execute? no.
- Approvals or evidence still required: operator review of candidate CSVs, approved action types, max row count, backup/checksum approval, copied-DB dry run, and a separate explicit live cleanup prompt.
- Safest first action type: `status_expire_candidate` only, because current schema supports `expired` and row text/source fields remain present.
- Rows/cohorts blocked: raw dict-like rows, quarantine candidates until schema support exists, alias merge rows until identity audit, market/macro rehome rows until rehome design, and insufficient-provenance or low-signal rows.
- Alias canonicalization required before cleanup? no for high-confidence duplicate fanout expiry; yes before any alias merge/rewrite.
- Can cleanup be status-only and reversible? partially. Expiry is status-only and text-preserving, but full reversibility requires backup plus change-log entries because the existing API mutates status/timestamps. Quarantine is not supported today.
