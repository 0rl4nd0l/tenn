# Issue 234 Phase 3 Dry-Run Review

Current state: DONE_WITH_RISK

## Objective

Classify issue #234,
`[Repo Hygiene] Classify stale extraction contract parity diff-check dirt`,
under `REPORT_AUTONOMY` only.

## Classification

`SUPERSEDED_CURRENT_BASE_CLEAN`

The stale dirty rewrite described in issue #234 is not present on current
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`107adb03852558d42795b28c3a5ec887e7cd0c64`. A 2026-06-25 current-base refresh
rechecked the same artifact on `b3b3a154590f36e61d297c1ac79fe623526f0b28` and
found the same clean artifact hash. The historical parity artifact is tracked
clean and still contains the original #98 changed-file list rather than the
later empty `changed_files: []` rewrite reported on 2026-06-02.

## Exact Next Action

Recommended next action: preserve this report-only packet through a separate
control-plane PR, then, after that report is durable, request approval for a
GitHub-only issue #234 closeout comment marking the issue superseded by current
base evidence.

Do not restore, clean, commit the old artifact, or rerun extraction work from
this packet.

## Files Touched

- `docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/README.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/ISSUE_REFRESH.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/EVIDENCE.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/CLASSIFICATION.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/APPROVAL_PACKET.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/DATA_MISSING.md`
- `reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/VALIDATION.md`

## Files Intentionally Not Touched

- `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`
- `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`
- Product, runtime, data, extraction, prompt, source-PDF, gold-label, DB, Qdrant,
  news, memory, service, model/GPU, and production-data files.

## Unsafe Actions Avoided

In the original report-only review, no restore, cleanup, delete, stash, reset,
commit, push, GitHub mutation, service start, extraction run, broad validation,
branch deletion, or worktree deletion was performed.

After owner approval to commit the packet, the report-only files were prepared
on local branch `control-plane/issue234-diff-check-dirt-classification-v1-20260615`
from current origin base `107adb03852558d42795b28c3a5ec887e7cd0c64`.

On 2026-06-25, the packet was replayed onto fresh current base
`b3b3a154590f36e61d297c1ac79fe623526f0b28` for a draft preservation PR. This
refresh still does not permit issue closeout, branch/worktree deletion, cleanup,
extraction work, or modification of the historical parity artifact.
The refresh records both the Git blob hash and raw file `sha1sum` for the
historical parity artifact so hash evidence is not ambiguous.

## Remaining Risk

The original 2026-06-02 dirty rewrite session was not identified from safe
current-base evidence. The current base is clean, so this packet does not prove
the historical rewrite cause; it proves the stale dirty state no longer applies
to current canonical base.
