# Approval Packet

## Current Decision

Classification: `SUPERSEDED_CURRENT_BASE_CLEAN`

The current base is clean for the historical #98 parity `diff-check.json`
artifact. No artifact restoration, cleanup, commit, or parking is recommended
from this run.

## Recommended Group A: Preserve Report Packet

Approve a separate control-plane preservation PR containing only:

- `docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/**`

Purpose: make the #234 classification durable before mutating the GitHub issue.

## Recommended Group B: GitHub Issue Closeout After Preservation

After Group A is merged or otherwise accepted, approve a GitHub-only issue #234
comment and close action:

- Summarize that current base has the artifact tracked clean.
- Link the durable classification report.
- Close #234 as superseded/current-base-clean.

## Explicitly Not Approved

- Do not restore or rewrite
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`.
- Do not run extraction jobs.
- Do not mutate product/runtime/data/extraction files.
- Do not clean, delete, stash, reset, commit, push, or mutate GitHub from this
  dry-run review.
- Do not close #234 before the classification packet is durable unless the owner
  explicitly accepts chat-only evidence.

## If Disputed

If an operator believes the stale empty `changed_files: []` artifact still
exists in another worktree, run a new read-only current-state packet against
that exact worktree path and treat this report as current-base-only evidence.
