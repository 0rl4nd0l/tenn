# Control Plane Sloppy Fix Scan JSON Handoff V1

## Status

DONE_WITH_RISK

## Purpose

Patch the Sloppy Scan -> Sloppy Fix handoff so automatic fix mode consumes the
issues found by the triggering scan run instead of relying only on an independent
fix-mode rescan.

## Background Evidence

- Disposable proof PR: `https://github.com/0rl4nd0l/tenn/pull/307`
- Sloppy Scan run `27084576956` succeeded and reported score `95/100` with one
  stub issue and two lint issues.
- Downstream Sloppy Fix run `27084580866` triggered successfully, checked out
  the proof branch, loaded `PLAN.md`, detected `npm run test:ci`, but found
  `0` issues and fixed `0`.
- Sloppy action source in `/tmp/sloppy-action` supports `output-file`: scan mode
  writes issues JSON, and fix mode seeds pass 1 from preexisting issues with
  `status === "found"`.

## Implementation

- `.github/workflows/sloppy-scan.yml` now passes
  `output-file: /tmp/sloppy-scan-issues.json` to Sloppy scan mode.
- `.github/workflows/sloppy-scan.yml` uploads that JSON as required artifact
  `sloppy-scan-issues` after successful scans.
- `.github/workflows/sloppy-fix.yml` grants the fix job `actions: read` so it
  can read artifacts from the triggering workflow run.
- `.github/workflows/sloppy-fix.yml` downloads artifact `sloppy-scan-issues`
  from `github.event.workflow_run.id` on automatic runs.
- `.github/workflows/sloppy-fix.yml` checks out the triggering scan `head_sha`
  on automatic runs.
- `.github/workflows/sloppy-fix.yml` validates the downloaded scan JSON before
  invoking fix mode.
- `.github/workflows/sloppy-fix.yml` selects the downloaded scan JSON for
  automatic runs and falls back to `/tmp/sloppy-fix-issues.json` only for manual
  `workflow_dispatch`.
- `.github/workflows/sloppy-fix.yml` skips fix mode on automatic runs when the
  triggering scan artifact contains zero found issues.
- Sloppy Fix still uses Claude auth/provider/model and remains unscheduled.

## Validation

- Task-card validation: passed.
- YAML parse for both workflows: passed.
- Selector script syntax/sample test: passed for automatic and manual paths.
- Static handoff checks: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed with no disallowed files.
- `actionlint`: `DATA_MISSING`; not installed in this environment.

## Pending Live Verification

- Push branch and open PR: `DATA_MISSING`
- Merge handoff workflow to `main`: `DATA_MISSING`
- Rerun Sloppy Scan on proof PR #307: `DATA_MISSING`
- Confirm Sloppy Fix downloads `sloppy-scan-issues` and logs preexisting seeded
  issues: `DATA_MISSING`
- Confirm Sloppy produces a fix branch/commit or records a concrete skipped
  issue reason: `DATA_MISSING`

## Safety Notes

- No runtime services, DBs, Qdrant, Redis, news stores, production data,
  extraction prompts, parser routing, model/GPU config, or backfills were
  touched.
- Disposable proof PR #307 remains open and must not be merged.
