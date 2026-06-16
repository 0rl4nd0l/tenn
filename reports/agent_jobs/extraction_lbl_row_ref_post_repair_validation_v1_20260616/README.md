# LBL Row Ref Post Repair Validation

Status: `DONE_WITH_RISK`

## Objective

Report-only readiness packet after preserving, pushing, and opening PR #362 for
the bounded LBL income-statement row-ref repair.

## Current State

- Worktree: `/home/l4nd0/tenn-lbl-income-row-ref-repair-v1-20260616`
- Branch: `safe/extraction-lbl-income-row-ref-repair-v1-20260616`
- Base: `migration/clean-runtime-baseline-reconstruct-v1`
- Repair commit: `d16c630af158ce3e5bcb3d7180adb7d3cb23273c`
- PR: `https://github.com/0rl4nd0l/tenn/pull/362`
- PR status at snapshot: draft, mergeable, `UNSTABLE` because
  `lint-and-test` was still in progress; `scan` passed.

## Decision

Primary decision: `C` - need current saved-artifact scorecard after this repair.

The PR is suitable for focused review of the bounded repair, but broad readiness
is not proven by the single-document replay. Count-24 is not justified yet.

## Evidence Used

- Repair task card:
  `docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md`
- Repair report:
  `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/`
- PR snapshot:
  `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/pr_snapshot.json`
- Replay summary:
  `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json`
- Forbidden-path audit:
  `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/forbidden_path_audit.json`

## Validation Status

- Post task-card validation: passed.
- Registry read-only inspection: passed, no active jobs.
- PR snapshot: passed on supported `gh` fields.
- Repair report JSON validation: passed.
- Replay assertions: passed.
- Forbidden-path audit: passed.

## Replay Result

- Runtime status: `ok`
- Runtime error: `None`
- Period: `H`
- Period end: `2025-12-31`
- Scale/currency: `thousands` / `AUD`
- Non-null metrics: `7`
- Target row refs:
  - `revenue`: `Sales Revenue`
  - `ebit`: `EBIT`
  - `np_attributable`: `NPAT For`

## What This Proves

- The branch preserves the bounded LBL row-ref repair and focused regression.
- The single-document LBL replay now has source-bound row refs and structured
  field provenance row refs for the target income metrics.
- The branch diff does not include forbidden data/runtime/source-PDF/canonical
  mutation surfaces.

## What This Does Not Prove

- Current saved-artifact scorecard results after this repair.
- Count-24/count-32 readiness.
- Broad extraction accuracy.
- Production canonical-write safety.
- Final PR merge readiness while CI is still in progress and the PR is draft.

## Files Touched

- `docs/agent_tasks/extraction_lbl_row_ref_post_repair_validation_v1_20260616.md`
- `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/README.md`
- `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/status.json`
- `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/pr_snapshot.json`
- `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/readiness_decision.json`
- `reports/agent_jobs/extraction_lbl_row_ref_post_repair_validation_v1_20260616/forbidden_path_audit.json`

## Files Intentionally Not Touched

No code, source PDFs, DB, Qdrant, Redis, news, memory, prompts, gold labels,
schema, runtime/model/GPU config, canonical truth, broad extraction outputs, or
count sample artifacts were touched by this post-repair packet.

## Unsafe Actions Avoided

No count-24, count-32, random samples, broad extraction, backfill, canonical
writes, GitHub merge, DB/Qdrant/Redis/news/memory/source-PDF/prompt/gold/schema
/runtime/model/GPU mutation, or PR #318 use.

## Remaining Risk

- PR #362 was draft at snapshot time.
- `lint-and-test` was still in progress at snapshot time.
- Task ledger files were `DATA_MISSING`.

## Next Recommended Prompt

Run a current saved-artifact scorecard against PR #362 after CI finishes, using
report-only mode and no count-24/count-32. Use that scorecard to decide whether
the PR can move from draft to review/merge readiness or needs one more focused
repair.
