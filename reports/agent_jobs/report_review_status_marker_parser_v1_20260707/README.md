# Report Review Status Marker Parser V1

## Objective

Implement the narrow control-plane helper recommended by the prior
report-review marker audit:

```text
report_review_status_marker_parser_v1_20260707
```

The helper parses optional report-local `REPORT_REVIEW_STATUS.json` sidecars
under `reports/agent_jobs/<job_id>/`.

## Current State

DONE

## Local Commit

- local commit created for the allowlisted task card, helper, tests, and report
  artifacts.
- branch: `control-plane/report-review-status-marker-parser-v1-20260707`
- push/PR: not performed; GitHub writes were outside the task-card scope.
- exact current HEAD: verify with `git rev-parse HEAD` after any amend.

## What Changed

- Added `scripts/report_review_status.py`.
- Added `scripts/test_report_review_status.py`.
- Added the exact task card:
  `docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md`.
- Added this report bundle.

## Helper Semantics

- Missing marker means `DATA_MISSING`, not failure.
- Marker `job_id` must match the containing report directory.
- `review_status` and `next_action` must use the approved vocabularies from the
  audit design.
- `source_report_paths` must remain inside the covered report directory.
- Non-`DATA_MISSING` review statuses require at least one concrete source
  report path.
- `runtime_functionality_proven=true` is rejected unless a covered report
  includes the Runtime Functionality Proof fields with `result: WORKING`.
- `github_state_checked=true` requires current-turn GitHub evidence in
  `review_evidence`.
- JSON scalar validation is strict enough to reject boolean `schema_version`,
  integer stand-ins for booleans, and non-string enum values.

The helper is advisory review evidence only. It does not prove runtime
functionality, GitHub state, PR readiness, financial-truth approval, or
issue-closeout permission.

## Files Touched

- `docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md`
- `scripts/report_review_status.py`
- `scripts/test_report_review_status.py`
- `reports/agent_jobs/report_review_status_marker_parser_v1_20260707/README.md`
- `reports/agent_jobs/report_review_status_marker_parser_v1_20260707/STATE.md`
- `reports/agent_jobs/report_review_status_marker_parser_v1_20260707/VALIDATION.md`
- `reports/agent_jobs/report_review_status_marker_parser_v1_20260707/DECISIONS.md`

## Files Intentionally Not Touched

- `/home/l4nd0/tenn/docs/agent_tasks/opencode_deepseek_scout_delegation_v1_20260707.md`
- `scripts/codex_automation_runner.py`
- historical report bundles
- durable docs, templates, hooks, and skills
- runtime/data/extraction/parser-output/source-PDF/gold-label/prompt surfaces
- DB, Qdrant, Redis, news stores, memory stores, production data
- GitHub, timers, systemd, Docker volumes, model/GPU config, services
- live registry and live task ledger
- preserved task-card branches or worktrees

## Docs Impact

- docs_impact: `DOCS_FOLLOWUP`
- docs_checked:
  - `scripts/codex_automation_runner.py`
  - prior report-local design under
    `/home/l4nd0/tenn-report-review-status-marker-audit-v1-20260707/reports/agent_jobs/report_review_status_marker_audit_v1_20260707/`
  - `docs/dev_flow/templates/`
- docs_changed:
  - none
- docs_followup:
  - before automation adoption, update durable operator/developer docs to name
    `REPORT_REVIEW_STATUS.json` and `scripts/report_review_status.py`
- reason:
  - this task intentionally implemented only the helper and tests; automation
    prompt behavior and historical report policy were out of scope.

## Validation Status

See `VALIDATION.md`.

## Ignored Or Untracked Artifacts

- Visible untracked files in the sibling worktree are the task card and two
  allowed script files.
- The report bundle is ignored by repo rules:
  `!! reports/agent_jobs/report_review_status_marker_parser_v1_20260707/`.
- `python3 -m py_compile` created ignored validation cache files under
  `scripts/__pycache__/`.
- The launch checkout still has only the prior visible untracked OpenCode task
  card.

## Runtime Functionality Proof

- Required: no.
- intended output: control-plane helper and tests.
- live output location: repository files listed above.
- pre-run max timestamp or count: not applicable.
- post-run max timestamp or count: not applicable.
- rows/files inserted or updated after run start: none; code/report files only.
- readiness/gate status: focused unit tests and task-card gates pass.
- exact command/query used: see `VALIDATION.md`.
- result: DATA_MISSING for runtime functionality, by design.
- remaining blocker: none for helper implementation; durable docs and
  automation adoption remain follow-up work.

## Remaining Risk

- No historical report bundles were backfilled.
- Automation prompts still ask for "unreviewed reports" without consuming the
  helper yet.
- Durable docs were not changed in this narrow slice; see docs follow-up above.

## Next Recommended Prompt

```text
/goal Adopt REPORT_REVIEW_STATUS.json in Tenn automation only after fresh Tenn preflight and exact task card. Use scripts/report_review_status.py as the parser, update the repo-hygiene automation prompt/report logic and durable docs, add focused tests, and do not backfill historical reports or infer runtime/GitHub state from review markers.
```
