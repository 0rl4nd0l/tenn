# Null Merge-Base Stale Path Guard State

- state: READY_TO_PR
- job_id: null_merge_base_stale_path_guard_v1_20260623
- branch: control-plane/null-merge-base-stale-path-guard-v1-20260623
- base: origin/migration/clean-runtime-baseline-reconstruct-v1
- base_head: 43df758d57280408f3d2c2567772ae2add90b36b
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
