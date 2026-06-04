# Merge Parking Registry

Last updated: 2026-06-04

This registry tracks evidence-backed Tenn work that should remain visible for
later merge review, validation, human decision, supersede/reject handling, or
data-missing follow-up.

This surface is inventory-first. An entry here is not merge approval.

## Status Legend

- `PARKED_READY_FOR_REVIEW`: task card, report, changed-files evidence,
  validation evidence, branch/head, and bounded status are present.
- `PARKED_NEEDS_VALIDATION`: bounded work exists, but validation or target-proof
  is incomplete.
- `PARKED_NEEDS_HUMAN_DECISION`: evidence exists, but risk or bundling is too
  high for an automatic merge-review recommendation.
- `PARKED_SUPERSEDED`: historical evidence worth retaining, but a newer review
  surface is preferred.
- `DATA_MISSING`: path or historical worktree evidence is missing; preserve the
  gap visibly.

## Active Registry Entries

| Status | Branch | Lane | Parked Entry | Reason |
| --- | --- | --- | --- | --- |
| `PARKED_READY_FOR_REVIEW` | `safe/extraction-broad-accuracy-push-v1-20260602` | Financial Truth | [extraction-broad-accuracy-push-v1-20260602.md](parked/extraction-broad-accuracy-push-v1-20260602.md) | Clean branch, report + validation present, bounded blocker-isolation evidence |
| `PARKED_READY_FOR_REVIEW` | `safe/appendix5b-report-gate-refresh-v1-20260531` | Evaluation | [appendix5b-report-gate-refresh-v1-20260531.md](parked/appendix5b-report-gate-refresh-v1-20260531.md) | Clean report-only Appendix 5B no-regression evidence with validation |
| `PARKED_NEEDS_VALIDATION` | `safe/extraction-appendix4d-profit-after-tax-alias-v1-20260602` | Financial Truth | [extraction-appendix4d-profit-after-tax-alias-v1-20260602.md](parked/extraction-appendix4d-profit-after-tax-alias-v1-20260602.md) | Unit-test evidence exists, but targeted GPT Appendix 4D proof is missing |
| `PARKED_NEEDS_HUMAN_DECISION` | `safe/extraction-live-contract-truth-gates-v1-20260603-nvme` | Financial Truth | [extraction-live-contract-truth-gates-v1-20260603-nvme.md](parked/extraction-live-contract-truth-gates-v1-20260603-nvme.md) | High-risk dirty parent batch with many staged reports and overlapping extraction code changes |
| `DATA_MISSING` | `multiple missing /tmp worktree paths` | Repo Hygiene | [extraction-data-missing-20260604.md](parked/extraction-data-missing-20260604.md) | Preserve missing Appendix 4D and extraction restore paths visibly |

## Not Parked Here

- `safe/extraction-broad-runtime-after-pls-evidence-v1-20260602`:
  preserved in the inventory as superseded by
  `safe/extraction-broad-accuracy-push-v1-20260602`.
- `safe/extraction-metric-ontology-prepersist-v1-20260531` and
  `safe/extraction-storage-metric-contract-gate-v1-20260531`:
  inventory classified them as already merged into
  `migration/clean-runtime-baseline-reconstruct-v1`.
- Narrow sub-slices inside the NVMe parent batch, such as AEG / Appendix 4E /
  BBN follow-ups:
  retained in the inventory report, but not parked individually here because
  they are still bundled inside the dirty parent worktree and need separation
  before independent review.
