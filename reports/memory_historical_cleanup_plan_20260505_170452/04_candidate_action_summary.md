# Candidate Action Summary

## Row Counts

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

## How To Read The CSVs

Each row-level CSV uses stable `entry_id` as `row_id`, includes source and timestamp fields where available, and writes `DATA_MISSING` where the copied DB or stocktake did not contain a field.

`status_expire_candidate` is the only action type that maps to the current company-memory schema. All other non-preserve actions require manual review or a later design/migration prompt.
