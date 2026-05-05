# Operator Approval Pack

## Recommended First Live Batch

- First live batch candidates: 249 rows.
- Rows excluded from first live batch: 963 rows.
- Maximum safe batch size recommendation: 250 rows.
- First-batch selection rule: complete fanout clusters with preserved target rows, no alias-merge rows, no manual-review rows, no blocked rows, no quarantine rows, and valid copied-DB mappings.
- First-batch clusters: fanout_0007=49, fanout_0018=40, fanout_0020=33, fanout_0023=26, fanout_0024=26, fanout_0026=26, fanout_0044=7, fanout_0045=7, fanout_0046=7, fanout_0047=7, fanout_0048=7, fanout_0049=7, fanout_0050=7

## Operator Checklist

1. Confirm live DB path: `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`.
2. Stop or gate memory writers during the live cleanup window.
3. Create a timestamped backup of company memory DB plus any WAL/SHM files.
4. Record pre-cleanup checksums and row counts.
5. Confirm first batch row ids from `csv/operator_first_batch_candidates.csv`.
6. Execute only the approved status-expiry transaction, not alias/rehome/quarantine actions.
7. Insert one audit row per expired row.
8. Recount active/expired rows and compare to the dry-run expected delta.
9. Keep rollback SQL and the backup snapshot until operator signoff.

## Evidence Files

- `csv/candidate_validation_results.csv`
- `csv/dry_run_rows_expired.csv`
- `csv/dry_run_rows_skipped.csv`
- `csv/high_risk_ticker_before_after.csv`
- `csv/operator_first_batch_candidates.csv`
- `sql_templates/DO_NOT_RUN_live_expire_candidates.sql`
- `sql_templates/DO_NOT_RUN_rollback_expire_candidates.sql`
