# AGENTS.md - Tenn Repo Constitution

This file is the stable instruction layer for agents working in Tenn. Keep it
short enough to load every turn. Put repeatable procedures in `.agents/skills`
instead of expanding this file.

## Repo Map And Target Selection

- Tenn is an ASX financial data ingestion, extraction, and cockpit workflow
  repository. The active runtime code is mainly under `financial-engine_v2/`;
  repository-level scripts and evaluation helpers also exist under `scripts/`.
- Verify the actual target before acting: `pwd`, `git branch --show-current`,
  `git rev-parse HEAD`, `git remote -v`, and
  `git status --short --untracked-files=all`.
- Runtime paths are environment-specific. Do not assume `/workspace`,
  `/home/l4nd0`, NVMe, venv, Docker, or service availability without checking.
- Use `docs/entrypoints.md` for runtime entrypoint context only when the task
  needs runtime work. Most repo-hygiene tasks should not start services.

## Current Evidence And Truthfulness

- Ground substantive claims in current-turn evidence. Prior memory, reports, and
  older summaries are background until re-checked.
- Mark missing or stale evidence as `DATA_MISSING`; do not invent repo state,
  validation results, issue status, branch ownership, or active agent ownership.
- Prefer exact file paths, command outputs, issue numbers, and report artifacts
  over qualitative status claims.

## Source Of Truth Hierarchy

1. Current user instructions and explicit safety boundaries.
2. The active task card, if one is provided or created.
3. Live repo state, current files, branch/HEAD/origin, and safe GitHub reads.
4. Current reports under `reports/agent_jobs/...` and registry evidence.
5. Durable docs such as `AGENTS.md`, `docs/entrypoints.md`, and issue bodies.
6. Memory or prior session context, as background only.

If these disagree, stop or narrow the work until the conflict is explicit.

## Safety Boundaries

- Do not mutate DB, Qdrant, Redis, news stores, memory, backfills, source PDFs,
  gold labels, extraction prompts, runtime state, model/GPU/service config, or
  production data unless the user explicitly approves that exact action.
- Do not run broad rewrites, dependency installs, service starts, branch
  deletion/pruning, merge/rebase/reset/stash/clean, or GitHub write actions
  unless the task explicitly requires and permits them.
- Preserve unrelated dirty or untracked files. Work with existing dirt instead
  of cleaning it.

## Financial Truth Priority

- Financial metric extraction is currently the highest-priority Tenn blocker
  only when live issue/registry evidence confirms it for the task.
- Canonical financial numbers must be source-bound, deterministic, auditable,
  and provenance-linked. Do not let LLM outputs define canonical numbers or
  promote disclosure text into canonical truth silently.
- Favor audit-first work and one narrow safe extension at a time.

## Multi-Agent Live Repo Control

- Assume other agents or worktrees may be active. Check branch, dirty state,
  task cards, and registry evidence before edits.
- Use exactly one primary lane accepted by local tooling. If doing Repo Hygiene,
  use an accepted primary lane such as `Evaluation` or `Reporting` and list
  `Repo Hygiene` as a supporting lane until the validator changes.
- Stop on unresolved high collision risk or ambiguous target branch/worktree.
- Prefer a clean sibling worktree when shared-checkout dirt overlaps the task;
  otherwise keep the diff strictly inside the task-card allowlist.

## Task Cards, Registry, And Merge Parking

- Implementation-capable work should have a task card before edits. Validate it
  with `python3 scripts/agent_job_contract.py validate <task_card>` when the
  script is available.
- Keep `allowed_files` exact. Include report artifacts explicitly because
  `reports/` is ignored and local `check-diff` is literal.
- The audited registry script lacks `list-active --read-only`. Do not rely on
  lock-writing registry commands for read-only audit. If safe read-only
  registry evidence is unavailable, record `DATA_MISSING`.
- Use `docs/agent_registry/merge_parking/REGISTRY.md` for parked merge state.
  Do not merge, rebase, cherry-pick, unpark, or delete parked work without
  explicit approval.

## Command Output Discipline

- Scope unknown or potentially large output before reading it into context.
  Prefer `rg`, `rg --files`, `git status --short`, `git diff --name-only`, and
  targeted ranges before full reads.
- For noisy commands, cap bytes, not just lines:
  - `COMMAND 2>&1 | head -c 4000`
  - `COMMAND 2>&1 | tail -c 4000`
- Line caps alone are unsafe because one giant line can flood context.
- Preserve exit codes when validation matters. Use `set -o pipefail`, capture
  status explicitly, or rerun a focused command if a pipe hides the status.
- Read these fully when relevant: instruction files, policy files, skill files,
  task cards, small config files, and intentionally selected small source
  sections.
- For noisy tests or builds, write raw logs to a report artifact and show only
  the summary plus raw-log path.

## Blocked, Waiting, And Approval States

Never silently continue low-value work when the next meaningful step requires
approval, a flag, permission, credential, service, or decision.

Declare `WAITING_ON_USER` when work cannot safely continue because it needs user
approval, permission flags, sandbox/network/runtime capability, secrets/env
vars, live services, DB/backfill approval, GitHub write/auth, merge/rebase/
branch/parking decisions, or product/design/architecture decisions.

```text
WAITING_ON_USER
Needed: <exact approval/flag/input>
Why: <what this unlocks>
Current safe state: <what has been done>
Options: <A/B/C>
Recommended: <one option>
```

For `/goal`, write the same wait state into the goal report or handoff before
stopping. If approval is optional, continue only with clearly labeled useful
read-only work. If approval is required for the next meaningful step, stop.

## Risk-Based Validation

- Tiny docs, comments, report-only artifacts, or prompt text: no runtime
  validation required; explain why.
- Narrow code change: run the cheapest focused check that exercises the change.
- Shared extraction, parser, runtime, RAG, registry, hook, or orchestration
  change: run a targeted regression or smoke check.
- Broad, cross-layer, release, or merge-candidate change: run broader suites
  only when justified.
- Never claim validation passed without the command, exit status, and relevant
  output.

## Done Criteria And Reporting

- Final reports should list files touched, files intentionally not touched,
  commands run, validation status, unsafe actions avoided, blocked items,
  ignored/untracked artifacts, and the next recommended prompt.
- Use `DONE_WITH_RISK` when useful work completed but evidence is incomplete,
  validation is skipped for a stated reason, or an external blocker remains.
- Use `DONE` only when the stated done criteria and validation/reporting
  requirements are met.

## Skill And Subagent Policy

- Repo-backed Codex skills live under `.agents/skills`.
- `.codex/config.toml` and `.codex/hooks.json` are Codex config/hooks surfaces.
  Treat `.codex/skills` references as legacy/custom unless local evidence proves
  compatibility is intentionally required.
- Do not mirror all host skills into Tenn. Repo skills should wrap Tenn-specific
  workflows.
- Use subagents only when they save context, increase independent verification,
  or allow parallel read-only specialist review. Do not use subagents for
  trivial tasks or parallel writes on contested surfaces.
- Each subagent report must include files inspected, findings, uncertainty,
  commands run, files changed if any, and recommended next action.

## GitHub Issue Workflow

- GitHub issues are the coordination backlog; task cards are execution
  contracts; reports are evidence and closeout.
- Search open and closed issues before proposing new issue mutations. Do not
  create, edit, label, comment on, close, or reopen issues without explicit
  approval.
- Use issue #78 for agent markdown and Codex repo documentation refresh work
  unless live evidence shows a narrower tracker supersedes it.
