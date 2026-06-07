# Control Plane Sloppy Fix Missing Artifact Skip V1

## Status

DONE_WITH_RISK

## Purpose

Repair the post-#308 Sloppy Fix behavior for triggering Sloppy Scan runs that do
not upload the `sloppy-scan-issues` artifact.

## Live Evidence

- PR #308 merged the scan JSON handoff at
  `94194de0e1b005ae5b00087645900a953b06c1de`.
- Disposable proof PR #307 rerun:
  - Sloppy Scan `27084910196` found three issues and uploaded artifact
    `sloppy-scan-issues`.
  - Sloppy Fix `27084915118` downloaded the artifact, loaded three preexisting
    issues, skipped the independent first-pass rescan, and completed.
  - Sloppy Fix did not produce a fix commit: it skipped all three issues with
    `Could not parse agent output`.
- Unrelated Sloppy Scan `27084924894` on
  `safe/extraction-count24-approval-packet-v1-20260607` did not upload
  `sloppy-scan-issues`.
- Downstream Sloppy Fix `27084928612` failed while downloading the missing
  artifact. This patch prevents that failure mode.

## Implementation

- Keep artifact handoff unchanged when `sloppy-scan-issues` exists.
- Make artifact download best-effort.
- In automatic `workflow_run` mode, missing scan artifact now emits
  `found_count=missing_artifact`.
- Sloppy fix mode does not run for `found_count=missing_artifact`, so it cannot
  fall back to an independent rescan.
- Missing-artifact skips are visible in the PR comment.
- Malformed artifact JSON still fails in the selector step.

## Validation

- Task-card validation: passed.
- YAML parse for `.github/workflows/sloppy-fix.yml`: passed.
- Selector script syntax/sample test: passed for missing artifact, zero found
  issues, one found issue, malformed artifact JSON, and manual dispatch.
- Static checks: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed with no disallowed files.
- `actionlint`: `DATA_MISSING`; not installed in this environment.

## Pending Live Verification

- Merge this patch to `main`: `DATA_MISSING`
- Rerun or naturally observe a no-artifact Sloppy Scan followed by Sloppy Fix
  skip-success: `DATA_MISSING`

## Safety Notes

- No runtime services, DBs, Qdrant, Redis, news stores, production data,
  extraction prompts, parser routing, model/GPU config, or backfills were
  touched.
- Disposable proof PR #307 remains open and must not be merged.
