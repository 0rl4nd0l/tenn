# Null Merge-Base Stale Path Guard State

- state: REFRESHED_ON_CANONICAL_VALIDATED_PENDING_PUSH
- job_id: null_merge_base_stale_path_guard_v1_20260623
- branch: control-plane/null-merge-base-stale-path-guard-v1-20260623
- base: origin/migration/clean-runtime-baseline-reconstruct-v1
- original_base_head: 43df758d57280408f3d2c2567772ae2add90b36b
- refreshed_base_head: a68553a7341ef5344626d37da196c9e390584cf8
- task_scope: control_plane_only
- mutation_mode: safe_extension
- product_runtime_data_extraction_count24_touched: no
- greyhound_runtime_touched: no
- host_global_mutation: no

## Summary

The host-global null-merge-base stale-path guard behavior was ported into the
repo-backed `tenn-git-guard` skill without broad formatting or unrelated
changes. The repo-backed guard now blocks a checked-out canonical local branch
when its HEAD differs from canonical, including the regression shape where
`merge_base_with_canonical` is `null`.

## Changed Repo Files

- `.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py`
- `.agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
- `docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md`
- `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/STATE.md`
- `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/DECISIONS.md`
- `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/VALIDATION.md`
- `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/CODE_REVIEW.md`

## Current Evidence

- Required first host-global preflight ran against `/home/l4nd0/tenn` before
  edits and blocked that stale/non-canonical start.
- Work continued in a clean sibling worktree created from current canonical:
  `/home/l4nd0/tenn-null-merge-base-stale-path-guard-v1-20260623`.
- Host-global files were read only for comparison.
- Repo-backed script and test are aligned with the host-global files for this
  fix after the port.
- PR #402 review on 2026-06-25 classified the patch as
  `REFRESH_THEN_READY`: valid, not superseded, but stale against canonical.
- Orlando's follow-up `proceed` approved the branch refresh/GitHub write lane.
- The PR branch was refreshed with a non-force merge of
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `a68553a7341ef5344626d37da196c9e390584cf8`.
- After refresh, `git merge-base HEAD origin/migration/clean-runtime-baseline-reconstruct-v1`
  equals the refreshed canonical head.
- Refreshed focused validation passed before push: task-card validation,
  `tenn-git-guard` regression tests, `git diff --check`, `check-diff`,
  `check-report-artifacts`, and visible skill count check.

## Docs Impact Check

- docs_impact: DOCS_UPDATED
- docs_checked: `AGENTS.md`, `docs/README.md`,
  `docs/dev_flow/SKILLS_SURFACE.md`,
  `docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md`,
  `.agents/skills/tenn-git-guard/SKILL.md`, `.agents/skills/tenn-fix/SKILL.md`
- docs_changed:
  `docs/agent_tasks/null_merge_base_stale_path_guard_v1_20260623.md`,
  `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/STATE.md`,
  `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/DECISIONS.md`,
  `reports/agent_jobs/null_merge_base_stale_path_guard_v1_20260623/VALIDATION.md`
- docs_followup: none
- reason: The PR branch refresh approval and validation evidence are recorded
  in the task/report artifacts; no operator-routing or runtime docs changed.

## Model And Worker Routing

- task_tier: medium
- recommended_model: standard coding model
- actual_model: GPT-5 Codex
- why_this_model: The run updates an existing control-plane PR branch, validates
  guard behavior, and performs GitHub branch-state work.
- worker_model_allowed: no
- worker_decision_limit: not_applicable
- escalation_needed: no
