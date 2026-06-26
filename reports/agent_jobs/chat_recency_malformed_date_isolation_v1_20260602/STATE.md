# State

## Current State

VERIFIED: Work is running from clean task worktree
`/home/l4nd0/tenn-issue261-malformed-date-isolation-v1-20260626`, branch
`safe/issue261-malformed-date-isolation-v1-20260626`, based on
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`857e76c3180cb0b1fb9fc360652d6a9b64543c86`.

VERIFIED: Issue #261 is open, has no comments, and no ledger match for issue
261. Guard preflight passed and found no matching active implementation work.

VERIFIED: This lane may overlap unpublished local branches for #259/#260 on
source weighting/recency surfaces. It remains isolated in its own worktree and
must be integrated deliberately if these branches are published later.

## Task Ledger

- Live ledger availability: VERIFIED.
- Committed ledger availability: VERIFIED.
- Duplicate-work classification: no matching active implementation lane found.
- Ledger update result: VERIFIED claimed and implementation_started entries
  appended.

## Implementation Summary

VERIFIED: `financial-engine_v2/backend/app/services/source_weighting.py`
now catches malformed `published_at` recency parsing errors inside
`apply_weighting_to_chunk()`, applies neutral `recency_decay = 1.0`, and
preserves visible metadata:

- `recency_status = "malformed_published_at"`
- `recency_warning = "invalid_published_at"`
- `published_at_parse_error` with the invalid value and exception detail

VERIFIED: `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
now covers direct malformed-date source weighting and `_apply_chat_strategy()`
with one malformed-date chunk plus one valid neighboring chunk.

VERIFIED: The new regressions failed before the source fix with `ValueError`
from `dateutil.parser.isoparse("not-a-date")`.

VERIFIED: GitHub issue evidence comment posted:
`https://github.com/0rl4nd0l/tenn/issues/261#issuecomment-4807663121`.

## Docs Impact

- docs_impact: DOCS_NOT_REQUIRED.
- docs_checked: `AGENTS.md`, `docs/README.md`,
  `.agents/skills/tenn-fix/SKILL.md`, `.agents/skills/tenn-git-guard/SKILL.md`.
- docs_changed: task card and report artifacts only.
- docs_followup: no durable docs update required for this narrow defensive
  metadata behavior; issue/report record the visible status fields.

## Model And Worker Routing

- task_tier: medium
- recommended_model: standard coding model
- actual_model: Codex
- why_this_model: narrow malformed-metadata isolation fix with focused tests.
- worker_model_allowed: false
- worker_decision_limit: not_applicable
- escalation_needed: false unless validation reveals broader retrieval-stack
  behavior outside the allowed surface.

## Runtime Functionality Proof

This task does not claim live runtime/service functionality. It is a source and
test fix for deterministic malformed metadata handling.

| Field | Required evidence |
| --- | --- |
| intended output | Malformed `published_at` does not crash source weighting or chat strategy weighting, and visible malformed-date metadata is preserved. |
| live output location | Source helpers and focused unit tests; no live runtime output claimed. |
| pre-run max timestamp or count | `DATA_MISSING`; no live runtime baseline captured because this is a no-runtime helper fix. |
| post-run max timestamp or count | `DATA_MISSING`; no live runtime output checked. |
| rows/files inserted or updated after run start | Two source/test files plus task-card/report artifacts updated locally. |
| readiness/gate status | Focused malformed-date regressions pass; chat/source-weighting tests pass; news retrieval eval tests pass; lint, compile, task-card validate, allowed-file diff check, report-artifact check, JSON check, and task-ledger validate pass. `ruff format --check` fails because the legacy selected files would be broadly reformatted. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Local fix is unpublished/unmerged; no PR or merge performed. |

result: PARTIAL
