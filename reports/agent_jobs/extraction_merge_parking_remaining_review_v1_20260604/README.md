# Extraction Merge Parking Remaining Review

## Summary

Audit-only merge-parking review completed for the remaining extraction parked
items. No extraction, backfill, random sample, canary, broad merge, source PDF
mutation, prompt/gold-label/schema change, or production DB/Qdrant/news/memory
mutation was run.

Extraction canonical for this review is
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`78b111f423ee86fd1fdfc214f1db551576ee14f5`. `origin/HEAD` currently points to
`origin/main`, but PR #293 is not on `origin/main`; it is present on the
extraction canonical branch.

## Preflight

- Current checkout branch: `tmp/sloppy-fix-demo`
- Current checkout HEAD: `8fc129668d2afcbc9d36b563ac05416149298579`
- `origin/main` HEAD: `c260942969309d7be00bafdd35dc4e6f769ffcbc`
- Extraction canonical HEAD: `78b111f423ee86fd1fdfc214f1db551576ee14f5`
- PR #293 merge commit: present on
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Registry active jobs: `[]`
- Worktree state: unrelated dirty/untracked files existed before this audit and
  were left untouched.

## Validation

- JSON validation: `status.json` and `parking_decision_table.json` passed
  `jq empty`.
- Task-card validation: passed for
  `docs/agent_tasks/extraction_merge_parking_remaining_review_v1_20260604.md`.
- `git diff --check`: passed.
- Task-card `check-diff --no-write-report`: failed because the shared checkout
  still has pre-existing unrelated dirt outside this job's exact allowlist,
  including `.gemini/`, `.playwright-mcp/`, `.tenn/`, `cockpit-ui/package.json`,
  `cockpit-ui/package-lock.json`, unrelated `docs/agent_tasks/*`,
  `outputs/*`, and untracked registry helper scripts. The allowlist was not
  broadened and unrelated files were not cleaned.
- Extraction implementation code check: no diffs found in the inspected
  extraction surfaces in this checkout.
- Source PDF check: no staged or unstaged PDF paths found.
- Final registry `list-active`: `[]`.
- Explicitly not run: extraction, backfill, random sample, canary, broad merge,
  production DB/Qdrant/news/memory mutation.

## Decisions

| Item | Classification | Decision |
| --- | --- | --- |
| `safe/appendix5b-report-gate-refresh-v1-20260531` | `STAY_PARKED` | Report-only evidence; do not integrate as extraction code. |
| `safe/extraction-appendix4d-profit-after-tax-alias-v1-20260602` | `SUPERSEDED` | Preserve as historical alias evidence only. Later wrapper-gate work is the preferred source. |
| `safe/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602` | `NEEDS_REBASE` | Correct source to mine, but local-only and stale against extraction canonical. |
| `safe/extraction-live-contract-truth-gates-v1-20260603-nvme` | `HIGH_RISK_PARENT_BATCH` | Do not merge whole. Mine narrow slices only. |
| `safe/extraction-broad-accuracy-push-v1-20260602` | `SUPERSEDED` | Historical blocker-isolation evidence; later Appendix 4D/NVMe work supersedes it as an integration surface. |

## Appendix 4D Wrapper Gate

The local branch
`safe/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602` exists at
`669d003026c68ce6ef667db7266f665f8a7dd7bd`; no `origin/` ref was found. A
detached inspection worktree was created at
`/tmp/tenn-merge-parking-review-wrapper-gate-20260604`.

Evidence is useful: the wrapper-gate reconcile report records focused pytest
`17 passed`, `py_compile` passed, `git diff --check` passed, task-card
validation/check-diff passed, and direct targeted GPT wrapper-gate simulation
returned `ok`.

The branch is not a direct integration candidate. It is stale relative to
extraction canonical, branch-level comparison includes large unrelated churn and
current registry deletion, and the earlier metric-minimum report had
`contract_check_diff=false` due to unrelated dirty files. Classification:
`NEEDS_REBASE`.

## NVMe Parent Batch

The parent batch at
`/mnt/tenn-nvme2/tenn/tmp/tenn-extraction-contract-restore-v1-nvme` is branch
`safe/extraction-live-contract-truth-gates-v1-20260603-nvme` at
`ab06d41ba534307dfbb4469b4ca12dcd12e1c8b1`.

It remains a high-risk parent container. Status showed hundreds of staged task
cards/report artifacts plus staged and unstaged edits to shared extraction
surfaces, including `multipass_extraction.py`,
`test_extraction_pre_canary_truth_gates.py`, `test_multipass_extraction.py`,
`broad_extraction_test.py`, and `test_broad_extraction_test.py`.

Recommended mining order:

1. `extraction_bpt_income_tax_npat_truth_guard_v1_20260604`
2. `extraction_col_adjusted_npat_truth_guard_v1_20260604`
3. `extraction_bbn_attributable_profit_row_recovery_v1_20260604`
4. `extraction_aeg_formal_units_statement_recovery_v1_20260604`
5. `extraction_appendix4e_full_dollar_scale_recovery_v1_20260603`

`extraction_post_col_random_count16_docling_cpu_v1_20260604` is evidence only;
do not integrate it as implementation. No RB6, PPT, or EVN slice was found in
the parent batch. BPT was found and should be mined first because it fixes a
false-success canonical NPAT risk.

## Can Implementation Resume?

Broad extraction implementation cannot resume from these parked branches as a
whole. The exact blocker is that no reviewed extraction implementation branch is
both current against extraction canonical and clean enough for direct
integration. Safe implementation can resume only through a new task-carded,
clean branch that ports one narrow slice at a time, starting with the Appendix
4D wrapper-gate rebase or the BPT/COL truth guards.

## DATA_MISSING

- Requested task card was absent from both the current checkout and extraction
  canonical before this report created it.
- Wrapper-gate branch is local-only; no remote ref found.
- Exact per-slice code diffs for NVMe child slices are not isolated because the
  parent has bundled staged and unstaged shared-code edits.
- No RB6, PPT, or EVN slice was found.
- This audit did not rerun historical validation artifacts; it read existing
  report evidence only.

## Validation

- JSON validation passed for `status.json` and `parking_decision_table.json`.
- `git diff --check` passed.
- Task-card validation passed.
- Task-card `check-diff` was attempted with `--no-write-report` and failed
  because the shared checkout contains pre-existing unrelated dirty/untracked
  files outside this task card's allowlist.
- Registry `list-active` passed with `active_jobs=[]`.
- No source PDFs were staged.
- No extraction-code changes were made in the current checkout.
- Final git status still shows unrelated pre-existing dirt; it was preserved.
- Required report files exist on disk. The report directory is ignored by Git,
  so it appears under `git status --ignored` as ignored.

## Project Memory Recommendation

Save a future memory note that extraction canonical for this merge-parking lane
is `origin/migration/clean-runtime-baseline-reconstruct-v1`, not `origin/main`,
and that the Appendix 4D wrapper branch is a rebase/salvage source rather than
a direct merge branch.
