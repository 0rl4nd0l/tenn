# Merge Parking Registry

Last updated: 2026-06-04

This registry tracks evidence-backed Tenn work that should remain visible for
later merge review, validation, human decision, supersede/reject handling, or
data-missing follow-up.

This surface is inventory-first. An entry here is not merge approval.

## Status Legend

- `PARKED_READY_FOR_REVIEW`: task card, report, changed-files evidence,
  validation evidence, branch/head, and bounded status are present.
- `STAY_PARKED`: evidence is useful, but the item is not a current integration
  target.
- `NEEDS_REBASE`: evidence is useful, but the branch is stale or not safe to
  merge against current extraction canonical.
- `PARKED_NEEDS_VALIDATION`: bounded work exists, but validation or target-proof
  is incomplete.
- `PARKED_NEEDS_HUMAN_DECISION`: evidence exists, but risk or bundling is too
  high for an automatic merge-review recommendation.
- `HIGH_RISK_PARENT_BATCH`: dirty or bundled parent worktree retained only as a
  source for mining narrow review slices.
- `PARKED_SUPERSEDED`: historical evidence worth retaining, but a newer review
  surface is preferred.
- `DATA_MISSING`: path or historical worktree evidence is missing; preserve the
  gap visibly.

## Active Registry Entries

| Status | Branch | Lane | Parked Entry | Reason |
| --- | --- | --- | --- | --- |
| `PARKED_SUPERSEDED` | `safe/extraction-broad-accuracy-push-v1-20260602` | Financial Truth | [extraction-broad-accuracy-push-v1-20260602.md](parked/extraction-broad-accuracy-push-v1-20260602.md) | Historical broad blocker-isolation evidence; later Appendix 4D wrapper and NVMe slices supersede it as an integration surface |
| `STAY_PARKED` | `safe/appendix5b-report-gate-refresh-v1-20260531` | Evaluation | [appendix5b-report-gate-refresh-v1-20260531.md](parked/appendix5b-report-gate-refresh-v1-20260531.md) | Report-only Appendix 5B no-regression evidence; not merge-authorized extraction code |
| `PARKED_SUPERSEDED` | `safe/extraction-appendix4d-profit-after-tax-alias-v1-20260602` | Financial Truth | [extraction-appendix4d-profit-after-tax-alias-v1-20260602.md](parked/extraction-appendix4d-profit-after-tax-alias-v1-20260602.md) | Superseded by later Appendix 4D wrapper-gate work; preserve as historical evidence only |
| `NEEDS_REBASE` | `safe/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602` | Financial Truth | [extraction-appendix4d-wrapper-gate-reconciled-v1-20260602.md](parked/extraction-appendix4d-wrapper-gate-reconciled-v1-20260602.md) | Local-only wrapper-gate evidence exists, but branch is stale against extraction canonical and must be salvaged into a clean review branch |
| `HIGH_RISK_PARENT_BATCH` | `safe/extraction-live-contract-truth-gates-v1-20260603-nvme` | Financial Truth | [extraction-live-contract-truth-gates-v1-20260603-nvme.md](parked/extraction-live-contract-truth-gates-v1-20260603-nvme.md) | Dirty parent batch; mine narrow slices only, never merge as one unit |
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
  retained in the remaining-review report, but not parked individually here
  because they are still bundled inside the dirty parent worktree and need
  separation before independent review.
