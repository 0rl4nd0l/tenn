---
job_id: null_merge_base_stale_path_guard_v1_20260623
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: pr
allowed_files:
  - docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md
  - .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py
  - .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py
  - reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/STATE.md
  - reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/DECISIONS.md
  - reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/VALIDATION.md
  - reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/CODE_REVIEW.md
  - reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/diff-check.json
---

# Null Merge-Base Stale Path Guard

## Objective

Persist the host-global `tenn-git-guard` null-merge-base stale-path fix into
the repo-backed skill so canonical Tenn carries the same guard behavior.

## Scope

Allowed:

- Compare the approved host-global guard script and test file to the
  repo-backed skill files.
- Port only the null-merge-base stale-path guard fix and its focused regression
  test into `.agents/skills/tenn-git-guard/`.
- Write report-local closeout artifacts for this lane.
- Open a focused draft PR.

Forbidden:

- Tenn product, runtime, data, extraction, count-24, source-PDF, gold-label,
  prompt, DB, Qdrant, Redis, news, memory, service, model/GPU, production-data,
  or Greyhound runtime mutation.
- Host-global file mutation. Reading the approved host-global guard files for
  comparison is allowed.
- Visible skill additions.
- Broad formatting or unrelated guard rewrites.
- Branch deletion, worktree removal, `git clean`, `git reset --hard`, stash,
  rebase, cherry-pick, merge, pruning, or unrelated dirty worktree inspection.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md`
- Compare host-global and repo-backed guard script/test files before and after
  the port.
- `python3 .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "null merge-base stale path regression" --json`
- Visible repo-backed skill count is exactly 10.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md --repo-root .`
- Forbidden product/runtime/data/extraction/count-24 path guard.
- Greyhound path guard.
- Host-global path guard, except approved read-only host-global comparison.

## Definition Of Done

- Repo-backed guard code includes the null-merge-base stale canonical branch
  classification.
- Repo-backed tests cover a local canonical branch whose remote canonical ref
  has no merge-base with local HEAD.
- Validation proves the known stale worktree
  `/home/l4nd0/tenn-merge-parking-registry-integrate-v1-20260604` is covered by
  repo-backed guard behavior.
- A focused draft PR is open against
  `migration/clean-runtime-baseline-reconstruct-v1`.
