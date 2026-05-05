# Memory Contamination Root Cause Audit

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
Execution mode: AUDIT MODE, plus prompt-authorized Safe Extension for one isolated synthetic xfail test
Intended files: reports/memory_contamination_root_cause_20260505_161634/*; financial-engine_v2/backend/tests/test_memory_signal_router.py
Contested surfaces touched: none
Collision risk: MEDIUM for the isolated test; LOW for report generation
Decision: proceed with audit/report/test fixture only; cleanup remains blocked

## Scope

This folder investigates company-memory contamination/fanout reported in:

- reports/full_system_stocktake_20260505_152038/04A_memory_scope_classification.csv
- reports/full_system_stocktake_20260505_152038/04A_memory_duplicate_fanout_clusters.csv
- reports/full_system_stocktake_20260505_152038/04A_memory_alias_fragmentation_matrix.csv
- reports/full_system_stocktake_20260505_152038/04A_memory_write_path_trace.md
- reports/full_system_stocktake_20260505_152038/04A_memory_retrieval_risk_report.md

## System Contract

Target layer: Storage and Retrieval-adjacent Memory write/read paths.

Relevant rules: SYSTEM_CONTRACT.md sections 1.1, 2.2, 5.1, 7, 8, 10.3.

Must not change: live memory rows, canonical financial truth, Qdrant, ingestion, production routing, memory ranking, answer synthesis, or alias storage. This audit did not delete, expire, rewrite, normalize, ingest, reprocess, upsert, migrate, or tune retrieval.

Why safe: all root-cause proof came from repo code, stocktake artifacts, a temp-directory synthetic reproduction, and one strict xfail regression fixture that writes only to pytest tmp_path SQLite stores.

## Contents

- 00_summary.md
- 01_write_path_trace.md
- 02_fanout_root_cause.md
- 03_alias_fragmentation_root_cause.md
- 04_fixture_reproduction_plan.md
- 05_cleanup_blockers.md
- 06_safe_fix_options.md
- 07_tests_to_add.md
- 08_codex_next_prompt.md

## Validation

Focused validation run:

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_memory_signal_router.py -q
```

Result: 7 passed, 1 xfailed in 0.89s.

