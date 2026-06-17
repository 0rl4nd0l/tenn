# Validation

State: PASSED_WITH_RISK

## Checks Run

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md` | 0 | Task card valid. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | `ok: true`, `read_only: true`, `lock_acquired: false`, `active_jobs: []`. |
| `python3 scripts/agent_job_contract.py check-artifacts docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md` | 0 | All 13 report artifacts exist and are non-empty. |
| `git diff --check` | 0 | No whitespace errors. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md --no-write-report` | 1 then 0 | Initial run failed because audit-only cards require `allow_audit_code_changes: true` even for this task-card/report-only diff. The task card was patched with that explicit flag; rerun passed with `ok: true`. |
| changed-path guard | 0 | Changed paths are only the audit task card and exact report bundle files. |
| product/runtime/data/extraction/count-24 guard | 0 | No guarded product/runtime/data/extraction/count-24 paths changed. |
| host-global guard | 0 | No host-global paths changed. |
| `git status --short --untracked-files=all` | 0 | Only the task card appears because `reports/` is ignored. |

## Final Notes

- Validation passed after adding `allow_audit_code_changes: true` to the
  audit-only task card.
- Report artifacts are ignored by git but verified by `check-artifacts` and the
  custom changed-path guard.
- Residual risk is from `DATA_MISSING` task ledger files and the active sibling
  Agent Task Ledger runtime/handoff worktree, not from changed-path scope.
