---
name: tenn-handoff
description: Produce a Tenn report-local handoff with git, ledger, session trace, validation, next milestones, and a short fresh-session /goal prompt.
---

# Tenn Handoff

Use `tenn-handoff` when Orlando asks to hand off work, close a long `/goal`,
stop before completion, or package context for a fresh session.

This is repo-native and report-local. Prefer it over the generic host `handoff`
skill for Tenn work because it is versioned with the repo and understands task
cards, ledger state, Git Hygiene, and owner-boundary rules.

## Required Inputs

- Current owner request or active goal.
- Active task card when one exists.
- Current report directory, preferably the task card `output_dir`.
- Current git state, validation state, and known PR/issue references.
- Agent Task Ledger state from `scripts/agent_task_ledger.py` when available.

## Workflow

1. Run `tenn-git-guard` preflight:
   - `pwd`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
   - `git status --short --untracked-files=all`
   - `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
   - `python3 scripts/agent_task_ledger.py resolve-path`
   - `python3 scripts/agent_task_ledger.py validate`
2. Investigate the session:
   - current task or goal
   - completed work
   - changed files
   - commits, branches, PRs, issues, reports, task cards, tests, validation
   - failed attempts, retries, uncertainty, and `DATA_MISSING`
3. Zoom out:
   - explain where this session fits in broader Tenn workflow
   - classify the work as product, extraction, control-plane, repo hygiene,
     reporting, or owner-boundary
   - identify product/control-plane state without inventing runtime evidence
4. Check git and ledger hygiene:
   - inspect staged, unstaged, untracked, and ignored/report artifacts relevant
     to the task
   - search ledger by task id, issue id, PR id, branch, worktree, touched paths,
     and text
   - write or update a ledger entry only when the task card or owner explicitly
     permits live ledger mutation
   - otherwise write `handoff/LEDGER_ENTRY.json` and record why live append was
     skipped
   - if relevant work is validated and commits are authorized, commit it;
     otherwise record exact uncommitted paths and next action
5. Optionally run architecture review for substantial sessions when it reduces
   risk and does not create another report-only loop.
6. Write the handoff artifacts.

## Required Artifacts

Under `reports/agent_jobs/<job_id>/handoff/` or the task card handoff path,
write:

- `HANDOFF.md`
- `NEXT_GOAL.md`
- optional `ARCHITECTURE_NOTES.md`
- optional `LEDGER_ENTRY.json`

Use `docs/dev_flow/templates/HANDOFF.md` as the section contract.

## Required HANDOFF.md Sections

- Executive summary
- Session ID / thread ID / goal ID
- Branch/worktree/base
- Completed work
- Commits
- PRs
- Issues
- Files changed
- Tests and validation
- Reports/task cards created
- Git status and dirt
- Ledger status
- Failed attempts / mistakes
- Open risks
- Owner decisions needed
- Next 10 milestones
- Short next `/goal`
- Do-not-touch boundaries
- Evidence grades

## Session Trace

Use explicit available sources only:

- `CODEX_THREAD_ID`
- `TENN_AGENT_SESSION_ID`
- `CODEX_SESSION_ID`
- `CODEX_GOAL_ID`
- read-only `~/.codex/goals_1.sqlite` lookup keyed by an explicit
  `CODEX_THREAD_ID`
- explicit hook or handoff payload fields

Do not scan broadly and guess the newest thread. Do not treat registry fallback
lease IDs such as `hostname:pid:job_id` as Codex session or thread IDs. If no
safe source exists, write `DATA_MISSING`.

## Short Fresh-Session Prompt

`NEXT_GOAL.md` must contain a short prompt, not a full recap. It must point at
`HANDOFF.md` and instruct the next orchestrator to read it first, run
`tenn-git-guard`, check ledger/PR/task/report duplicates, and use subagents
where useful.

## Completion Rule

A handoff is not complete unless:

- git state is reported honestly
- relevant work is committed or explicitly recorded as uncommitted or
  owner-boundary
- ledger entry exists, or `DATA_MISSING` plus fallback evidence is recorded
- `NEXT_GOAL.md` exists
- the short fresh-session prompt exists
- no product/runtime/data/extraction mutation occurred outside approved scope

## Host-Global Boundary

Do not edit `~/.codex/skills/handoff/SKILL.md` by default. If host-global
handoff behavior needs a change and the owner has not explicitly approved that
host mutation in the current run, write a report-local `HOST_HANDOFF_PATCH.md`
with exact proposed changes instead.
