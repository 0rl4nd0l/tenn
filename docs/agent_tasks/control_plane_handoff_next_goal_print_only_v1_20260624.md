---
job_id: control_plane_handoff_next_goal_print_only_v1_20260624
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624
mutation_mode: safe_extension
task_scope: control_plane_only
production_data_access: false
allowed_files:
  - docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md
  - .agents/skills/tenn-handoff/SKILL.md
  - docs/dev_flow/templates/HANDOFF.md
  - docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/README.md
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/STATE.md
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/DECISIONS.md
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/VALIDATION.md
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/PR_REVIEW.md
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/git_guard.json
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/diff-check.json
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/report-artifacts.json
  - reports/agent_jobs/control_plane_handoff_next_goal_print_only_v1_20260624/ledger_entry.json
---

# Control Plane Handoff Next Goal Print Only V1

## Objective

Update the repo-native `tenn-handoff` contract so closeout emphasizes printing
only the short fresh-session `/goal` after the handoff artifacts are written.
The printed goal must point the next session at the handoff docs rather than
recapping the full handoff in chat. It must also tell Orlando whether the
session left git dirt and make that dirt visible in the handoff for the next
agent.

## Scope

- Clarify `.agents/skills/tenn-handoff/SKILL.md` so the final operator-facing
  output is only the short next-session goal and the relevant handoff doc path.
- Clarify `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md` so generated
  `NEXT_GOAL.md` stays compact and points at `HANDOFF.md`.
- Clarify `docs/dev_flow/templates/HANDOFF.md` so leftover staged, unstaged,
  untracked, ignored/report, and owner-boundary dirt is explicit and actionable.
- Produce a small report bundle with validation and review evidence.

## Hard Boundaries

- Do not touch Tenn product, backend, frontend, runtime, data, extraction,
  source-PDF, gold-label, prompt, schema, service, model, GPU, DB, Qdrant,
  Redis, news, memory, or count-24 paths.
- Do not mutate host-global Codex files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or home-directory skill
  roots.
- Do not add a new visible skill.
- Do not edit the shared generic `docs/dev_flow/templates/NEXT_GOAL.md`.
- Do not merge, rebase, cherry-pick, reset, stash, prune, force-push, or delete
  branches or worktrees.
- Do not create, edit, comment on, close, or label GitHub issues.
- GitHub PR creation and merge are allowed only for this exact branch after
  focused validation, final diff review, live PR checks, and clean mergeability
  evidence from GitHub.
- Do not start services, install project dependencies, or run product/runtime
  validation.

## Required Preflight

- Fresh task worktree from `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Branch, HEAD, remote, upstream, dirty state, selected base, and merge base.
- `tenn-git-guard` preflight with ledger and registry status.
- Task-card validation before edits.
- Current `tenn-handoff` skill and `HANDOFF_NEXT_GOAL.md` template.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_handoff_next_goal_print_only_v1_20260624.md --repo-root .`
- `git diff --check`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort | wc -l`
- Live GitHub PR checks must be green before merge.
- Final `git status --short --untracked-files=all`

## Definition Of Done

- `tenn-handoff` says to print only the short fresh-session goal after writing
  handoff artifacts, plus a concise git-dirt summary.
- The printed goal points at the generated `HANDOFF.md` and avoids full chat
  recap.
- `HANDOFF.md` requires a concrete leftover-dirt section so the next agent
  knows what is dirty, why, and what to do first.
- `HANDOFF_NEXT_GOAL.md` reinforces the compact, file-linked prompt contract.
- No product/runtime/data/extraction/host-global files are changed.
- Validation and report artifacts are recorded.
- Report-local ledger intent is recorded when live ledger mutation is skipped.
