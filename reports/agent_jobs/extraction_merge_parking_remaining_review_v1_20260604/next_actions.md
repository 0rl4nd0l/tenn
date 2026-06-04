# Next Actions

## First Integration/Rebase Target

Use the Appendix 4D wrapper-gate branch as a rebase/salvage source, not as a
direct merge branch.

```text
Create a clean Tenn extraction canonical worktree from origin/migration/clean-runtime-baseline-reconstruct-v1. Task-card first. Review local branch safe/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602 at 669d003026c68ce6ef667db7266f665f8a7dd7bd only as a source. Port only the Appendix 4D/4E wrapper metric-minimum gate logic, the focused tests, and the wrapper-gate report/task artifacts needed for review. Do not merge or cherry-pick the whole branch. Do not run extraction, backfill, random samples, canaries, or broad merges. Preserve source PDFs, prompts, gold labels, schema, runtime config, DB/Qdrant/news/memory, and unrelated dirt. Validate with task-card validate/check-diff, git diff --check, focused pytest for wrapper-gate and ordinary annual/half-year behavior, py_compile, JSON validation, no source PDFs staged, and final registry/list-active.
```

## Second Target

Mine the BPT income-tax NPAT truth guard from the dirty NVMe parent batch.

```text
Create a clean review branch from origin/migration/clean-runtime-baseline-reconstruct-v1 for exactly one slice: extraction_bpt_income_tax_npat_truth_guard_v1_20260604. Inspect /mnt/tenn-nvme2/tenn/tmp/tenn-extraction-contract-restore-v1-nvme read-only and port only the BPT income-tax NPAT mismatch guard plus focused tests and report/task artifacts. Do not copy unrelated parent-batch changes. Do not run extraction, backfill, random samples, canaries, or broad merges. Validate with RED-to-GREEN selector evidence if possible, focused pytest selectors, full touched test files already used by the slice, py_compile, task-card validate/check-diff, git diff --check, JSON validation, no source PDFs staged, and final registry/list-active.
```

## Third Target

Mine the COL adjusted-NPAT truth guard from the dirty NVMe parent batch.

```text
Create a clean review branch from origin/migration/clean-runtime-baseline-reconstruct-v1 for exactly one slice: extraction_col_adjusted_npat_truth_guard_v1_20260604. Inspect /mnt/tenn-nvme2/tenn/tmp/tenn-extraction-contract-restore-v1-nvme read-only and port only the adjusted/ex-significant-items NPAT mismatch guard plus focused tests and report/task artifacts. Do not copy unrelated parent-batch changes. Do not run extraction, backfill, random samples, canaries, or broad merges. Validate with RED-to-GREEN selector evidence if possible, focused pytest selectors, full touched test files already used by the slice, py_compile, task-card validate/check-diff, git diff --check, JSON validation, no source PDFs staged, and final registry/list-active.
```

## Explicit Non-Actions

- Do not merge `safe/extraction-live-contract-truth-gates-v1-20260603-nvme`.
- Do not merge `safe/extraction-appendix4d-profit-after-tax-alias-v1-20260602`.
- Do not merge `safe/extraction-broad-accuracy-push-v1-20260602`.
- Do not treat `extraction_post_col_random_count16_docling_cpu_v1_20260604` as
  implementation; it is evidence only.
- Do not run broad extraction until clean, narrow integration branches have
  been reviewed and current runtime readiness is separately authorized.
