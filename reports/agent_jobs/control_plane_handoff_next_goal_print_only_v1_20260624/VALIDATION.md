# Validation

## Commands Run

- `pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all`: pass
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "handoff next goal print only" --json`: pass
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md`: pass
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: pass
- `python3 scripts/agent_task_ledger.py --repo-root . validate`: pass
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md --repo-root .`: pass
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md --repo-root .`: pass
- `git diff --check`: pass
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort | wc -l`: pass, count `10`
- `git push -u origin control-plane/handoff-next-goal-print-only-v1-20260624`:
  blocked by pre-push hook because
  `financial-engine_v2/.venv/bin/ruff` and
  `financial-engine_v2/.venv/bin/pytest` are missing.
- Push resolution: use `TENN_ALLOW_MISSING_HOOK_TOOLS=1` for this docs-only
  control-plane change instead of mutating the product venv or installing
  dependencies.

## Git Dirt Disclosure Check

- `HANDOFF.md` template now requires `tracked_dirt`, `staged_dirt`,
  `unstaged_dirt`, `untracked_dirt`, `ignored_or_report_artifacts`,
  `session_created_dirt`, `pre_existing_or_owner_boundary_dirt`,
  `git_dirt_summary`, and `next_agent_dirt_action`.
- `HANDOFF_NEXT_GOAL.md` final chat output now includes
  `Git dirt left behind: <...>`.

## Final Checks

- Final `check-diff` after report files: pass.
- Final `check-report-artifacts`: pass.
- Final `git diff --check`: pass.
- Final visible skill count: `10`.

## Validation Scope

Control-plane docs/skill-template validation only. Runtime functionality proof
is not applicable.
