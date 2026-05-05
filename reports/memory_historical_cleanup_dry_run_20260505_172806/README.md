# Memory Historical Cleanup Dry Run 20260505_172806

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn (shell `pwd` resolved through symlink as /home/l4nd0/tenn)
Execution mode: AUDIT MODE + DRY-RUN ONLY
Contested surfaces touched: none
Collision risk: MEDIUM for copied-DB analysis; HIGH for live mutation
Decision: copied-DB dry run completed; live mutation remains gated.

## Result

- Live DB changed: no. Live company DB checksum remained `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`.
- Copied DB dry run completed: yes.
- Candidate rows found: 1212.
- Rows expired in copied DB: 1212.
- Rows skipped: 0.
- Preserve/manual/blocked overlap: 0/0/0.
- Future live cleanup verdict: GO to request an operator-approved first-batch live cleanup lane; NO-GO for automatic live execution from this audit.

## Key Files

- Copied DB after git remediation: `/mnt/sdb2/home/l4nd0/tenn_runtime_backups/memory_cleanup_20260505_174752/dry_run_copied_db/company_memory.sqlite`
- Validation CSV: `csv/candidate_validation_results.csv`
- Expired rows CSV: `csv/dry_run_rows_expired.csv`
- First-batch CSV: `csv/operator_first_batch_candidates.csv`
- SQL templates: `sql_templates/DO_NOT_RUN_live_expire_candidates.sql`, `sql_templates/DO_NOT_RUN_rollback_expire_candidates.sql`

The raw copied SQLite files were preserved outside git and removed from tracking during backup artifact remediation. The tracked report keeps CSVs, markdown, SQL templates, and JSONL evidence only.
