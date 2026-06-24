# State

State: DONE_WITH_RISK

Current Focus: Validate the handoff next-goal print-only contract change.

## Completed

- Created fresh canonical sibling worktree.
- Added narrow task card.
- Updated `tenn-handoff` to require terse final chat output.
- Updated `HANDOFF.md` to require actionable leftover git-dirt disclosure.
- Updated `HANDOFF_NEXT_GOAL.md` to show the final chat output shape.

## Blocked

- None.

## Decisions

- Keep the durable handoff content in `HANDOFF.md`.
- Keep `NEXT_GOAL.md` as the short prompt source.
- Final chat output should include only the handoff path, short goal, and a
  concise git-dirt summary.
- The next agent must see staged, unstaged, untracked, ignored/report, and
  owner-boundary dirt in `HANDOFF.md`, with a next action for each.

## Task Ledger

- Sources checked: live ledger and committed ledger.
- Duplicate-work classification: `NO_MATCHING_ACTIVE_WORK_FOUND`.
- Ledger update: not written live; report-local
  `reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/ledger_entry.json`
  records the intended ledger entry.

## Runtime Functionality Proof

- Required: no
- result: not_applicable
- remaining blocker: none

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md`: pass
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: pass
- `python3 scripts/agent_task_ledger.py --repo-root . validate`: pass
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md --repo-root .`: pass before report closeout
- `git diff --check`: pass
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort | wc -l`: `10`

## Next Safe Action

Review the local diff, then commit/open a PR only if desired. No GitHub write
was performed in this run.
