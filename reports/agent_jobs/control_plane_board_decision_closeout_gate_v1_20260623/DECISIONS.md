# Decisions

## Decision: Validate Listed Board Decisions In Closeout

`check-closeout` now validates `BOARD_DECISION.json` artifacts listed under the
task card `output_dir` in `allowed_files`.

Rationale: the board-decision validator already existed, but relying on agents
to remember a separate command left a gap at final report closeout. The closeout
gate is the existing report-readiness surface.

## Decision: Keep Non-Runtime Closeout Lightweight

For non-runtime task cards, `check-closeout` still does not force every report
artifact to exist. It only checks listed `BOARD_DECISION.json` artifacts.

Rationale: existing docs/report-only cards depend on `check-closeout` being
lightweight unless runtime functionality proof is required. Full artifact
presence remains the job of `check-report-artifacts`.

## Decision: Lazy Import The Board Validator

`agent_job_contract.py` imports `check_board_decision.py` only when a board
decision artifact is actually present.

Rationale: hook tests and minimal temp repos copy only the contract and
registry scripts. A top-level import made unrelated hook checks fail in those
minimal fixtures.

## Decision: No Schema Expansion

This slice did not change `BOARD_DECISION.json` schema requirements.

Rationale: schema changes are a separate owner-visible decision. This slice
only enforces the existing validator at closeout.
