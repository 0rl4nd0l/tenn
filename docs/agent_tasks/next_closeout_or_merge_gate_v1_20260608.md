---
job_id: next_closeout_or_merge_gate_v1_20260608
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/next_closeout_or_merge_gate_v1_20260608.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/README.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/status.json
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/pr149_review.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/pr164_review.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/validation.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
requested_primary_lane: Repo Hygiene
requested_mutation_mode: result_review
github_mutation_allowed: blocker_comment_only
---

# Next Closeout Or Merge Gate v1 - 2026-06-08

## Objective

Run a bounded result-review / merge-readiness gate for the next safe Tenn
repo-hygiene parking PRs:

- PR #149: `safe/repo-hygiene-park-stale-query-audit-v1-20260531`
- PR #164: `safe/repo-prunable-worktree-metadata-review-v1-20260531`

This card supersedes any further closures under
`issue_closeout_sweep_v1_20260608`. Do not close more issues under that prior
card.

## Scope

- Read live GitHub PR metadata, files, checks, and related issue state.
- Use a clean sibling worktree from
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Run local merge probes against the target baseline.
- Produce a report-only reviewer gate with merge-readiness decisions.
- Keep #73 open as the Financial Truth parent tracker.
- Leave #329 open unless a separate cleanup task card explicitly approves
  actual `git worktree prune`.

## Allowed GitHub mutations

- Blocker/status comment only if a PR is not merge-ready and the blocker must
  be visible on GitHub.
- No issue closure.
- No PR merge.
- No label, milestone, project, or branch mutation.

## Forbidden surfaces

- Product/backend/frontend/runtime code.
- Production DB, Qdrant, news, memory, source PDFs, or canonical financial
  truth stores.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Runtime/model/GPU/service config.
- Actual `git worktree prune`.
- Branch delete, reset, stash, rebase, cherry-pick, or pushed merge.
- Unrelated dirty files in any checkout.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/next_closeout_or_merge_gate_v1_20260608.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root . --read-only`
- Fresh `gh pr view` / `gh issue view` readback.
- Local merge probe for PR #149.
- Local merge probe for PR #164.
- `python3 -m json.tool reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/status.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/next_closeout_or_merge_gate_v1_20260608.md --no-write-report`

## Hard stops

- Task-card validation fails.
- Registry read-only shows an active overlapping job.
- Merge probe conflicts or requires product/runtime/data edits to validate.
- GitHub evidence is unavailable or points at the wrong repository.
- Merge-readiness claim depends on actual branch merge, prune, reset, or
  cleanup approval.
