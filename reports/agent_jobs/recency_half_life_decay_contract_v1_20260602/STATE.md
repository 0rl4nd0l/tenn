# State

## Current State

VERIFIED: Work is running from clean task worktree
`/home/l4nd0/tenn-issue260-recency-half-life-decay-v1-20260626`, branch
`safe/issue260-recency-half-life-decay-v1-20260626`, based on
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`857e76c3180cb0b1fb9fc360652d6a9b64543c86`.

VERIFIED: Issue #260 is open, has no comments, and no open PR covers issue
260, `commentary_decay`, or `half_life_days`.

VERIFIED: Guard preflight passed for this task worktree and found no matching
active implementation work.

## Task Ledger

- Live ledger availability: VERIFIED.
- Committed ledger availability: VERIFIED.
- Duplicate-work classification: no matching active implementation lane found.
- Ledger update result: VERIFIED claim entry appended for
  `recency_half_life_decay_contract_v1_20260602`.
- Implementation ledger update: VERIFIED `implementation_started` entry
  appended after source edit.
- Final ledger update: VERIFIED `done` entry appended with
  `owner_boundary=true` and verdict
  `LOCAL_FIX_VALIDATED_READY_FOR_PR_LEFT_OPEN`.

## Implementation Summary

- Changed the centralized recency formula from `exp(-age / half_life)` to
  `exp(-ln(2) * age / half_life)`.
- Added fixed-timestamp tests proving one `half_life_days` interval decays to
  `0.5` and two intervals decay to `0.25`.
- Added source-weighting coverage for `news_article` and `market_commentary`.
- Updated the marketplace observation weighting comment to describe a true
  20-day half-life instead of the old time-constant formula.
- Preserved the existing behavior for missing, zero, or negative half-life
  inputs.

## Issue Closeout Decision

- issue_state: OPEN
- close_decision: LEFT_OPEN
- github_comment:
  `https://github.com/0rl4nd0l/tenn/issues/260#issuecomment-4807424121`
- reason: Local acceptance criteria are validated, but the fix is unpublished.
  No branch push, PR, or merge was performed in this lane.
- next_action: publish/open PR for
  `safe/issue260-recency-half-life-decay-v1-20260626`, then close #260 after
  the fix is accepted into canonical.

## Docs Impact

- docs_impact: DOCS_NOT_REQUIRED
- docs_checked: `AGENTS.md`, `docs/README.md`,
  `.agents/skills/tenn-fix/SKILL.md`, `.agents/skills/tenn-git-guard/SKILL.md`.
- docs_changed: task card and report artifacts only.
- docs_followup: none for this source fix.
- reason: implementation now matches existing half-life naming and issue
  acceptance criteria; durable docs did not need a contract change.

## Model And Worker Routing

- task_tier: medium
- recommended_model: standard coding model
- actual_model: Codex
- why_this_model: small helper-level behavior fix, but it affects ranking
  weights through shared recency decay.
- worker_model_allowed: false
- worker_decision_limit: not_applicable
- escalation_needed: false unless validation reveals broader ranking or source
  registry behavior changes.

## Runtime Functionality Proof

This task does not claim live runtime/service functionality. It is a source and
test fix for recency score semantics.

| Field | Required evidence |
| --- | --- |
| intended output | `compute_recency_decay()` implements true half-life semantics. |
| live output location | Source helper and focused unit tests; no live runtime output claimed. |
| pre-run max timestamp or count | `DATA_MISSING`; no live runtime baseline captured because this is a no-runtime helper fix. |
| post-run max timestamp or count | `DATA_MISSING`; no live runtime output checked. |
| rows/files inserted or updated after run start | Three source/test files updated plus task/report artifacts. |
| readiness/gate status | Focused tests, ruff format/check, py_compile, and contract gates pass; GitHub issue remains open because fix is unpublished. |
| exact command/query used | `uv run --with-requirements ... pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`; `uv run --with ruff ruff format --check ...`; `uv run --with ruff ruff check ...`; `python3 -m py_compile ...`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Fix is local only; not pushed, PR'd, or merged. |

result: PARTIAL

## Code Review

```json
{
  "status": "SUCCESS",
  "work_log": {
    "assumptions": [
      "Review scope is the current git diff for issue #260 only.",
      "Publishing, PR creation, and merge are outside this task card."
    ],
    "sources_used": [
      "git diff -- financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py",
      "focused pytest and ruff validation results"
    ],
    "files_read": [
      "financial-engine_v2/backend/app/services/commentary_decay.py",
      "financial-engine_v2/backend/app/services/source_weighting.py",
      "financial-engine_v2/backend/app/services/marketplace_price_intelligence.py",
      "financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py"
    ],
    "files_modified": [
      "financial-engine_v2/backend/app/services/commentary_decay.py",
      "financial-engine_v2/backend/app/services/marketplace_price_intelligence.py",
      "financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py"
    ],
    "validation_checks": [
      "red fixed-timestamp half-life tests: failed with 0.367879 before fix",
      "focused source-weighting pytest: 29 passed",
      "ruff format --check: pass",
      "ruff check: pass",
      "py_compile: pass"
    ]
  },
  "result": {
    "critical": [],
    "warnings": [],
    "suggestions": []
  }
}
```
