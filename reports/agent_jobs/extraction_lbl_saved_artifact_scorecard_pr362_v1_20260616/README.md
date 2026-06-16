# LBL Saved-Artifact Scorecard For PR 362

Status: `DONE`

## Objective

Run a report-only current saved-artifact scorecard for PR #362 after the LBL
row-ref repair and decide whether the PR can move from draft to
ready-for-review/merge, needs one more focused repair, or needs a count-24
approval packet refresh.

## Current State

- Worktree: `/home/l4nd0/tenn-lbl-income-row-ref-repair-v1-20260616`
- Branch: `safe/extraction-lbl-income-row-ref-repair-v1-20260616`
- HEAD: `1ef230f0133a53ad50e8613ba8dbb3e2338912db`
- PR: `https://github.com/0rl4nd0l/tenn/pull/362`
- PR state: open draft, mergeable, `CLEAN`
- CI at current snapshot: `lint-and-test` success, `scan` success
- Registry read-only state: no active jobs

## Decision

Primary decision: `READY_FOR_REVIEW_MERGE`.

PR #362 can move from draft to ready-for-review and merge consideration. The
current saved-artifact scorecard does not indicate one more focused repair, and
it does not require a count-24 approval packet refresh for this bounded PR gate.

## Saved-Artifact Scorecard Result

- Prior saved-artifact LBL guard status: failed, zero accepted metrics.
- Current repaired LBL replay status: `ok`.
- Current LBL period: `H`, ending `2025-12-31`.
- Current LBL scale/currency: `thousands` / `AUD`.
- Current LBL non-null metrics: `7`.
- Current LBL repaired income row refs:
  - `revenue`: `Sales Revenue`
  - `ebit`: `EBIT`
  - `np_attributable`: `NPAT For`
- Prior guard contextual cases remain preserved from saved artifacts:
  - WHC: pass, 8 accepted metrics.
  - CTN: pass, 6 accepted metrics.
  - HUB: pass, 9 accepted metrics.
  - AZJ: scale-table path closed from saved evidence.
  - NSR: clean thousands-scale control.

Current observed saved-artifact delta versus the earlier LBL fail-closed guard:
`+1` accepted document and `+7` non-null metrics for LBL. Combined with the
previous guard packet's saved-artifact repair deltas, the current guard packet
represents `+4` documents and `+30` non-null metrics across saved-artifact guard
cases. This is not a broad extraction scorecard claim.

## What This Proves

- The previous LBL saved-artifact fail-closed guard is no longer the current
  saved-artifact state on PR #362.
- The repaired LBL replay is source-bound for period, scale, currency, and
  row-ref provenance on the target income metrics.
- The PR branch is cleanly mergeable in GitHub and CI is green at the current
  snapshot.
- The branch diff does not touch forbidden source-PDF, DB, backfill,
  canonical-truth, prompt, gold-label, runtime, model, or GPU surfaces.

## What This Does Not Prove

- It does not prove count-24 or count-32 sample performance.
- It does not prove random-sample or broad extraction accuracy.
- It does not prove production canonical-write safety.
- It does not replace reviewer judgment on the code diff.

## Files Touched

- `docs/agent_tasks/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616.md`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/README.md`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/status.json`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/pr_snapshot.json`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/saved_artifact_scorecard.json`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/readiness_decision.json`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/diff-check.json`

## Unsafe Actions Avoided

No count-24, count-32, random samples, broad extraction, backfills, canonical
writes, GitHub mutation, merge, PR #318 use, or mutation of DB/Qdrant/Redis/news
/memory/source PDFs/prompts/gold/schema/runtime/model/GPU config.

## Next Recommended Step

Move PR #362 from draft to ready-for-review, then review and merge through the
normal PR process if the reviewer accepts the bounded repair. Keep count-24
approval refresh as a later gate, not a prerequisite for this PR.
