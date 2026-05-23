# Phase 3G Consolidation Execution Task-Card Draft

Job: `strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521`

Mode: draft-only, audit/report only.

## Result

The Phase 3G future consolidation execution task card was drafted in
`draft_task_card.md`.

No consolidation mutation was performed.

## Current Evidence

- Repo root: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `2bff733e2d7f8fadfde6d492a5ff48212b710f59`
- Phase 3F recommendation:
  `GO_PHASE3G_CONSOLIDATION_EXECUTION_TASK_CARD_DRAFT_ONLY`

## Draft Summary

The draft future task card:

- requires explicit approval before mutation;
- preserves Tenn as the research brain and provenance authority;
- keeps QuantDinger as a replaceable external sidecar/comparator;
- keeps `strategy_lab_artifact_v1` authoritative;
- keeps Phase 2B helper material pending-review and out of runtime/backend
  wiring;
- enumerates future candidate task cards, Strategy Lab docs, fixtures, tests,
  and report bundles;
- excludes generated pycache;
- keeps runtime/backend/Cockpit/stores/dependencies/services/tokens/production
  data/trading paths forbidden.

## Environmental Warnings

Current ordinary git status includes untracked Phase 3D, Phase 3E, and Phase 3F
task cards outside this draft task's allowlist. Registry overlap/check-diff may
therefore report expected dirty-file warnings.

## Validation Summary

- Task-card validation: passed.
- `jq empty` on `status.json`: passed.
- Markdown hygiene: passed.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- Registry `list-active`: final result `active_jobs=[]`.
- Registry `check-overlap`: failed only on pre-existing Phase 3D, Phase 3E, and
  Phase 3F task cards outside this draft task allowlist.
- `agent_job_contract.py check-diff`: failed only on the same pre-existing
  Phase 3D, Phase 3E, and Phase 3F task cards outside this draft task
  allowlist.
- Targeted status for `docs/strategy_lab`, `tests/strategy_lab`,
  `financial-engine_v2`, `cockpit-ui`, `scripts`, dependency files, Docker
  files, and env files had no entries.
- QuantDinger process scan found no `quantdinger` or `tenn_quantdinger`
  process.

## Files Written

- `docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/preflight.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/draft_task_card.md`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/status.json`
- `reports/agent_jobs/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521/diff-check.json` if generated

## Next Gate

Actual consolidation execution still requires explicit user approval. The next
mutation-capable task should use the drafted card, convert report globs to exact
report-child paths if needed by the validator, and re-check source worktree
state before copying or force-adding anything.
