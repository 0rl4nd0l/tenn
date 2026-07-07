# Decisions

## Decision 1: Use Fresh Sibling Worktree

- decision: use
  `/home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707`
- reason: `/home/l4nd0/tenn` had visible task-card dirt and portable guard
  blocked implementation there as `DIRTY_RELATED_WORKTREE`.
- result: no launch-checkout edits.

## Decision 2: Keep Helper Advisory

- decision: parser returns report-review marker status only.
- reason: the marker is not proof of runtime functionality, GitHub state, PR
  readiness, financial truth, or issue closeout.
- result: helper rejects unsupported runtime/GitHub claims instead of promoting
  them.

## Decision 3: Missing Marker Is DATA_MISSING

- decision: missing `REPORT_REVIEW_STATUS.json` is valid optional absence and
  returns `review_status=DATA_MISSING`.
- reason: missing marker must not be conflated with "unreviewed" or "invalid".
- result: scans can distinguish unknown review state from malformed markers.

## Decision 4: No Automation Adoption Yet

- decision: do not wire `scripts/codex_automation_runner.py` in this slice.
- reason: the prior audit explicitly scoped this follow-up to parser/helper and
  tests only.
- result: adoption remains a separate task card.

## Decision 5: Docs Follow-Up, Not Docs Expansion Here

- decision: record `DOCS_FOLLOWUP` instead of editing durable docs.
- reason: this slice validates the helper shape first; operator-facing adoption
  docs should be updated with the automation integration task.
- result: durable docs remain unchanged in this lane.
