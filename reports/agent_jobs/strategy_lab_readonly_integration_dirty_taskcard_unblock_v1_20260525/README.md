# Strategy Lab Readonly Integration Dirty Task-Card Unblock

## Required Preflight Template

Lane: Reporting
Primary scope: Repo Hygiene
Branch: `migration/clean-runtime-baseline-reconstruct-v1`
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Execution mode: SAFE EXTENSION / AUDIT
Intended files: this task card/report bundle plus the two named dirty task cards
Contested surfaces touched: none
Collision risk: MEDIUM
Decision: proceed narrowly, preserve/archive-classify only the two named cards

## Decision

`PRESERVE_ARCHIVE_CLASSIFY_TWO_CARDS`

The two named dirty task-card blockers should be committed unchanged as
historical task-card evidence. They should not be treated as active work,
current system proof, or authorization for implementation.

No Strategy Lab source commit was cherry-picked or merged.

## Classification

### `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`

- Lane: Evaluation.
- Mutation mode: audit_only.
- Lifecycle classification: completed historical audit evidence.
- Active state: not active in current registry evidence.
- Staleness: stale for current HEAD. The report status records branch HEAD
  `6eb30d3f098849c501d2239a188374bd822d6000`; current HEAD at this unblock
  started from `3a18475b91a325baccd22a3daf07237dc1d3d18b`.
- Use classification: archive/reference only; useful as a May 25 audit packet,
  not current proof.
- Preservation action: preserve the task card unchanged.
- Report evidence inspected:
  `reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/`.
- Do not do from this evidence: do not rely on it for current runtime truth,
  branch cleanliness, graphify state, merge-parking support, or production
  readiness without rerunning.

### `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`

- Lane: Reporting.
- Supporting lanes: Evaluation, Provenance.
- Mutation mode: audit_only.
- Lifecycle classification: blocked preflight audit, needs later review/rerun.
- Active state: not active in current registry evidence.
- Staleness: stale and incomplete. The report status records branch HEAD
  `84a17f10dc1e6a491fd1fb70088c84502494bd39`; current HEAD at this unblock
  started from `3a18475b91a325baccd22a3daf07237dc1d3d18b`.
- Use classification: archive-only blocked preflight evidence; not substantive
  worker/runtime provenance evidence.
- Preservation action: preserve the task card unchanged.
- Report evidence inspected:
  `reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/`.
- Do not do from this evidence: do not implement runtime/provenance changes or
  claim worker/GPU parity from this blocked report.

## Current Blocker Outside This Task

Current `git status --short --untracked-files=all` also shows:

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`

That file is outside this task's allowlist and was not touched. It is now the
remaining dirty task-card blocker for a clean Strategy Lab integration rerun.

## Validation Summary

- Task-card validation: passed.
- Registry `list-active`: passed; active jobs were empty.
- Registry `check-overlap` for this unblock card: failed because the unrelated
  A2M task card is dirty outside this task's allowlist.
- Existing report JSON for the two classified cards parsed with
  `python3 -m json.tool`.
- No worker provenance, full-system implementation, Strategy Lab source, runtime,
  backend, parser, model, GPU, DB, Qdrant, news, memory, or canonical-truth
  surfaces were modified.

## Target Cleanliness For Strategy Lab Rerun

Not yet clean enough to rerun the Strategy Lab `e5e12fe990d1` integration review
from this same checkout because the unrelated A2M task card remains untracked.

The two Strategy Lab-unblock blockers named in this task are cleared once this
report and the two cards are committed.

## Files Changed

- `docs/agent_tasks/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525.md`
- `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
- `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`
- `reports/agent_jobs/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525/README.md`
- `reports/agent_jobs/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525/status.json`
- `reports/agent_jobs/strategy_lab_readonly_integration_dirty_taskcard_unblock_v1_20260525/validation.json`

## DATA_MISSING

- Whether the unrelated A2M dirty task card should be preserved, deleted,
  archived, or handled by a separate task.
- Whether the ignored report bundles for the two preserved cards should later be
  committed; they were inspected but are outside this task's allowed files.
- Whether a clean Strategy Lab single-commit integration review will pass after
  the A2M dirt is handled.

## Save Recommendation

Project Memory save recommended after review: the two named dirty task-card
blockers were classified and preserved unchanged, but a new unrelated A2M task
card remains the current checkout cleanliness blocker for rerunning Strategy Lab
integration review.
