# Extraction Merge Parking Registry Setup

## Outcome

Created repo-side merge-parking registry surfaces and added evidence-backed
parked entries for the highest-priority extraction findings from the existing
inventory bundle.

## Registry Paths Created

- `docs/agent_registry/merge_parking/REGISTRY.md`
- `docs/agent_registry/merge_parking/parked/`

## Parked Items Added

- `safe/extraction-broad-accuracy-push-v1-20260602`
  - parked as `PARKED_READY_FOR_REVIEW`
- `safe/appendix5b-report-gate-refresh-v1-20260531`
  - parked as `PARKED_READY_FOR_REVIEW`
- `safe/extraction-appendix4d-profit-after-tax-alias-v1-20260602`
  - parked as `PARKED_NEEDS_VALIDATION`
- `safe/extraction-live-contract-truth-gates-v1-20260603-nvme`
  - parked as `PARKED_NEEDS_HUMAN_DECISION`
- DATA_MISSING preservation entry
  - parked as `DATA_MISSING`

## Intentionally Not Parked Here

- `safe/extraction-broad-runtime-after-pls-evidence-v1-20260602`
  - inventory already marks it as superseded by
    `safe/extraction-broad-accuracy-push-v1-20260602`
- merged branches such as:
  - `safe/extraction-metric-ontology-prepersist-v1-20260531`
  - `safe/extraction-storage-metric-contract-gate-v1-20260531`
  - not parked because the inventory found them already merged into the
    migration baseline
- narrow sub-slices inside the NVMe parent batch
  - not parked individually because they remain bundled inside the dirty parent
    worktree

## Recommended First Merge-Review Candidate

`safe/extraction-broad-accuracy-push-v1-20260602`

Reason:

- clean branch
- task/report/validation present
- bounded review surface
- inventory explicitly recommended it as the first merge-review candidate

## DATA_MISSING Preserved

Visible in:

- `docs/agent_registry/merge_parking/parked/extraction-data-missing-20260604.md`

## Explicit Non-Actions

- No merge
- No cherry-pick
- No prune/delete
- No clean/stash/reset/restore
- No extraction/backfill/sample run
- No extraction code modification

## Validation Notes

- `python3 -m json.tool reports/agent_jobs/extraction_merge_parking_registry_setup_v1_20260604/status.json`
  passed.
- `git diff --check` passed.
- `python3 scripts/agent_job_registry.py list-active` returned no active jobs.
- Source-PDF repo status check via `git status --short --untracked-files=all -- '*.pdf'`
  returned clean.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_merge_parking_registry_setup_v1_20260604.md`
  remained blocked by unrelated dirty worktree state and by the validator
  treating new `docs/agent_registry/merge_parking/parked/*.md` entries as
  outside `allowed_files` despite the task card using `parked/**`.
