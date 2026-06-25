# Decisions

## Validator Shape

Decision: add a standalone standard-library script,
`scripts/check_board_decision.py`.

Reason: board decisions are authority artifacts for `tenn-fix`, merge, park,
supersede, and owner-boundary decisions. A separate script gives agents and
hooks a cheap command to reject malformed board outputs without adding another
visible skill.

## Strict Versus Template Mode

Decision: default CLI mode validates real board decisions strictly; `--template`
validates template structure without requiring concrete text.

Reason: `docs/dev_flow/templates/BOARD_DECISION.json` must remain a reusable
template with empty fill-in fields, while real board artifacts must not pass
with placeholders or missing minority-objection checks.

## Scope Boundaries

Decision: do not repair Git hooks, sync host skills, or archive legacy
`.codex/skills` in this task.

Reason: those are separate owner-boundary or host-global decisions. This task
only implements the board-decision validator slice approved by the current user
prompt.

## Runtime Proof

Decision: Runtime Functionality Proof is not applicable for this closeout.

Reason: this is control-plane validation code and documentation. It does not
claim daemon, runtime, extraction, ingestion, automation, scheduler, service, or
pipeline functionality.
