# Next Goal

## Recommended Prompt

```text
Use tenn-review-board or tenn-fix as appropriate.
Before acting on any future review-board packet, run:
python3 scripts/check_board_decision.py <report-dir>/BOARD_DECISION.json
Treat a validator failure as a board artifact defect and fix the board packet
before using it as authority for implementation, merge, park, or supersede.
```

## Remaining Separate Work

- Git hook path repair/verification remains separate.
- Legacy `.codex/skills/cockpit-flag-orchestrator` warning/archive remains
  separate.
- Host skill sync remains owner-boundary and requires explicit approval.
- Docs-impact standalone validation remains a separate optional hardening task.
