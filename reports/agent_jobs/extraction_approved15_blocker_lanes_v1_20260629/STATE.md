# State

## Verified Target

- Worktree:
  `/home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629`
- Branch: `safe/extraction-approved15-blocker-lanes-v1-20260629`
- Start HEAD: `265a0d5a8125254c099e391087724097d6200517`
- PR #461 merge commit: `265a0d5a8125254c099e391087724097d6200517`
- Current origin later advanced to
  `b2adf891096f41d4ddef260b1c47fd9b5a8417a4` with control-plane/docs
  changes only for the inspected extraction allowlist.

## Current Worktree Dirt

Expected task dirt:

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `docs/agent_tasks/extraction_approved15_blocker_lanes_v1_20260629.md`
- Report-local artifacts under
  `reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/`

Unrelated dirt in `/home/l4nd0/tenn` was not touched:

- `transcript_promnpt`

## Scorecard State

Before RMS fix:

- `ambiguous_quarantined=73`
- `missing_expected_metric=4`
- `not_evaluated_no_actual_payload=18`
- `present_correct=49`
- `present_wrong_value=2`

After RMS fix:

- `ambiguous_quarantined=73`
- `missing_expected_metric=0`
- `not_evaluated_no_actual_payload=18`
- `present_correct=53`
- `present_wrong_value=2`

Gate state: `fail`, decision `blocked`.

## No-Write Boundary

No DB, Qdrant, Redis, news, runtime/backfill, production data, source PDF,
gold-label, prompt, model, service, count-24/count-32, or GitHub issue mutation
was performed. The replay used loopback LLM only and report-local outputs.

## Publish State

Local branch is PR-ready after validation, but GitHub publishing is blocked in
this environment until authentication is refreshed. `gh auth status` reports
that the saved `github.com` token is no longer valid.
