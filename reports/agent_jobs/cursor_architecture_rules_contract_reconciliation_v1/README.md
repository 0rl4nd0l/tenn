# Cursor Architecture Rules Contract Reconciliation V1

## Summary

Resolved GitHub issue #139 by retiring current command/documentation dependencies on missing `.cursor/rules` architecture rule files. The affected commands now point at `docs/architecture/SYSTEM_CONTRACT.md` and relevant `docs/architecture/*.md` files instead of requiring rule files that are not present in this checkout or tracked history.

## Scope

- Updated `/architecture-check` to use the authoritative system contract and architecture docs.
- Updated `/architecture-cleanup` to use the authoritative system contract and current architecture/process docs.
- Updated `/function-quality` consistency checks to reference the system contract.
- Updated `/repo-audit` preflight/inventory/output references so it no longer depends on missing Cursor agent/rule files.
- Updated `docs/claude/commands.md` command summary for Architecture Cleanup.

## DATA_MISSING

- `.cursor/rules/00_mandatory_index.md`
- `.cursor/rules/backend_architecture.md`
- `.cursor/rules/embedding_rules.md`
- `.cursor/rules/vector_store_invariants.md`
- `.cursor/rules/failure_policy.md`
- `graphify-out/GRAPH_REPORT.md`

No tracked restoration source was found for the missing architecture rule files, so this task retired the stale dependency rather than recreating content from inference.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `rg -n "\\.cursor/rules|\\.cursor/agents|backend_architecture.md|embedding_rules.md|vector_store_invariants.md|failure_policy.md" .claude/commands docs/claude/commands.md docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cursor_architecture_rules_contract_reconciliation_v1.md`

## Evidence

- Diff gate: `reports/agent_jobs/cursor_architecture_rules_contract_reconciliation_v1/diff-check.json`
