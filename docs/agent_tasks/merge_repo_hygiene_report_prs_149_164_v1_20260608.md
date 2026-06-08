---
job_id: merge_repo_hygiene_report_prs_149_164_v1_20260608
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/next_closeout_or_merge_gate_v1_20260608.md
  - docs/agent_tasks/merge_repo_hygiene_report_prs_149_164_v1_20260608.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/README.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/status.json
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/pr149_review.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/pr164_review.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/validation.md
  - reports/agent_jobs/next_closeout_or_merge_gate_v1_20260608/diff-check.json
  - reports/agent_jobs/merge_repo_hygiene_report_prs_149_164_v1_20260608/README.md
  - reports/agent_jobs/merge_repo_hygiene_report_prs_149_164_v1_20260608/status.json
  - reports/agent_jobs/merge_repo_hygiene_report_prs_149_164_v1_20260608/validation.md
  - reports/agent_jobs/merge_repo_hygiene_report_prs_149_164_v1_20260608/diff-check.json
approval_required: true
approval_reference: "User said proceed after plan: fresh-readback and merge #149 then #164; no prune."
timeout_seconds: 3600
output_dir: reports/agent_jobs/merge_repo_hygiene_report_prs_149_164_v1_20260608
mutation_mode: safe_extension
production_data_access: false
requested_primary_lane: Repo Hygiene
requested_mutation_mode: pr_merge_only
github_mutation_allowed: merge_pr_149_164_only
---

# Merge Repo Hygiene Report PRs #149 and #164

## Objective

After the validated result-review gate in
`next_closeout_or_merge_gate_v1_20260608`, merge only:

- PR #149: `safe/repo-hygiene-park-stale-query-audit-v1-20260531`
- PR #164: `safe/repo-prunable-worktree-metadata-review-v1-20260531`

## Required Order

1. Fresh-readback PR #149 and PR #164.
2. Merge PR #149.
3. Fresh-readback PR #164 after #149 lands.
4. Merge PR #164 if still clean/mergeable.
5. Fresh-readback both PRs plus #329 and #73.

## Allowed GitHub Mutations

- Merge PR #149.
- Merge PR #164.

## Forbidden

- Actual `git worktree prune`.
- Branch deletion.
- Issue closure.
- Product/backend/frontend/runtime code mutation.
- Production DB, Qdrant, news, memory, source PDFs, or canonical financial
  truth stores.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service
  config.
- Reset, stash, rebase, cherry-pick, or unrelated cleanup.

## Validation

- Task-card validate.
- Registry read-only check.
- Fresh PR readback before each merge.
- Fresh PR/issue readback after merge.
- `python3 -m json.tool` for report status.
- `git diff --check`.
- Task-card `check-diff`.

## Hard Stops

- Either PR is not open, not mergeable, draft, has non-success checks, or no
  longer targets `migration/clean-runtime-baseline-reconstruct-v1`.
- Registry read-only shows an active overlapping job.
- Merging would require branch deletion, cleanup, prune, or local code changes.
