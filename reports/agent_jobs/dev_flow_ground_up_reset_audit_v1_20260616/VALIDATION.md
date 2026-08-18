# Validation

## Commands Run

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md` | 0 | Passed. |
| `python3 scripts/agent_job_registry.py list-active --read-only` | 0 | Passed; `active_jobs: []`, `read_only: true`, `lock_acquired: false`. |
| `git ls-remote origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Remote base resolved to `227e1ce0d4e99c4a13ece8012a44adeba4585cdf`. |
| `git worktree list --porcelain` | 0 | 479 Tenn worktree entries found. |
| Worktree classifier | 0 | 82 dev-flow/control-plane, 331 product/runtime/extraction, 5 prunable metadata, 61 unknown/review-needed. |
| `gh auth status` | 0 | Authenticated read-only inspection available. |
| Focused `gh issue` and `gh pr` reads | 0 | Read-only context gathered for issues #78/#291/#234 and PRs #320/#344. |
| `git diff --check` with explicit `GIT_DIR`/`GIT_WORK_TREE` | 0 | Passed. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md --no-write-report` | 0 | Passed; changed non-ignored file is only the audit task card. |
| `python3 scripts/agent_job_contract.py check-artifacts docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md` | 0 | Passed; all 15 report files exist and are non-empty. |
| Final changed-path guard | 0 | Non-ignored changes: only `docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md`; report files appear under ignored `reports/`. |

## Known Validation Risks

- A mid-run normal `git status` failed with
  `fatal: this operation must be run in a work tree`; later normal status and
  explicit `GIT_DIR`/`GIT_WORK_TREE` status succeeded. Treat this as transient
  checkout fragility, not repaired by this audit.
- A mid-run explicit status probe showed unrelated dirty hook/report paths, but
  final status did not. This audit did not modify those paths.

## No-Mutation Confirmations

- No product/runtime/data/extraction files were intentionally edited.
- No host-global Codex files were edited.
- No GitHub mutation was performed.
- No branch/worktree deletion, prune, clean, reset, stash, merge, rebase,
  cherry-pick, push, or force-push was performed.
- No product/runtime/data/extraction path appeared in the final non-ignored
  changed-path guard.
