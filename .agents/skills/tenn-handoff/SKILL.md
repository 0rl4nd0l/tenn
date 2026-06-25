---
name: tenn-handoff
description: Produce a Tenn report-local handoff with git, ledger, session trace, linked artifacts, next milestones, and a short fresh-session orchestrator /goal prompt.
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
- Agent Task Ledger state from the portable guard preflight, plus
  Tenn-control-plane-local `scripts/agent_task_ledger.py` output when
  available.
- Relevant report bundles, review-board reports, worker results, task cards,
  validation artifacts, failed attempts, known risks, and do-not-touch
  boundaries.

## Workflow

1. Run `tenn-git-guard` preflight:
   - `pwd`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
   - `git status --short --untracked-files=all`
   - `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json`
   - from a Tenn control-plane checkout, if the installed host skill path is
     unavailable: `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json`
   - Tenn-control-plane-local follow-up checks when the scripts are available:
     `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`,
     `python3 scripts/agent_task_ledger.py resolve-path`, and
     `python3 scripts/agent_task_ledger.py validate`
2. Investigate the session:
   - current task or goal
   - completed work
   - changed files
   - commits, branches, PRs, issues, reports, task cards, tests, validation
   - review-board packets, worker briefs/results, prior handoffs, and failed
     attempts that affect the next session
   - failed attempts, retries, uncertainty, and `DATA_MISSING`
3. Zoom out:
   - explain where this session fits in broader Tenn workflow
   - classify the work as product, extraction, control-plane, repo hygiene,
     reporting, or owner-boundary
   - identify product/control-plane state without inventing runtime evidence
   - for daemon, runtime, ingestion, extraction, automation, collector,
     scheduler, service, or pipeline work, state whether functionality was
     proven through intended live output or whether only activity, reports,
     tests, or artifacts were proven
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
6. Write the handoff artifacts, then print only the short fresh-session goal,
   the `HANDOFF.md` path, and a concise git-dirt summary for Orlando. Do not
   paste the full handoff, artifact map, validation history, or a long recap
   into chat when the handoff docs contain that context.

## Fresh-Session Continuation Contract

Handoff owns fresh-session continuation. A handoff must make the next session
usable without chat archaeology.

Include explicit links or repo-relative paths for every relevant artifact:

- report bundles and handoff directories
- review-board `BOARD.md`, `BOARD_DECISION.json`, and `NEXT_GOAL.md`
- worker briefs and `WORKER_RESULT.md` files
- task cards and task-ledger entries
- PRs, issues, branches, worktrees, and commits
- validation artifacts, raw logs, failed attempts, and known risks
- source problem statement or owner decision when available

Also include:

- what the next session should do first
- what the next session must not touch
- the next 5-10 key milestones when the session is part of a larger repair
- stop conditions and owner decisions needed
- leftover git dirt, separated into staged, unstaged, untracked,
  ignored/report artifacts, and owner-boundary or pre-existing dirt. For each
  dirt item, state whether it is session-created, intentionally preserved, safe
  to commit, should be ignored, or needs owner approval. If no dirt remains,
  say `git_dirt: clean`.

When continuation requires orchestration, `NEXT_GOAL.md` must instruct the
fresh session to read `HANDOFF.md` first, run `tenn-git-guard` and ledger/task
duplicate checks, then act as an orchestrator through `tenn-fix`: split
independent lanes, delegate only bounded workers, review worker outputs before
integration, integrate one coherent change at a time, validate, and report
honestly.

The operator-facing closeout after writing a handoff should be terse. Print the
short goal from `NEXT_GOAL.md`, the repo-relative `HANDOFF.md` path, and a
one-line git-dirt summary. Do not summarize the full handoff in chat unless
Orlando explicitly asks for the summary.

## Required Artifacts

Under `reports/agent_jobs/<job_id>/handoff/` or the task card handoff path,
write:

- `HANDOFF.md`
- `NEXT_GOAL.md` using the handoff-only prompt contract in
  `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md`
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
- Runtime functionality proof, or `not_applicable`
- Reports/task cards created
- Git status and dirt
- Leftover git dirt and next action
- Ledger status
- Failed attempts / mistakes
- Open risks
- Owner decisions needed
- Relevant artifact map
- What the next session should do first
- What not to touch
- Next 5-10 key milestones
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
`HANDOFF.md` and instruct the next session to read it first, run
`tenn-git-guard`, check ledger/PR/task/report duplicates, then act as an
orchestrator when work remains. The prompt must name the first action, the main
do-not-touch boundaries, and the stop state.

After creating `NEXT_GOAL.md`, print that short prompt as the final answer for
the current session, preceded or followed only by the `HANDOFF.md` path and a
concise git-dirt summary. The handoff file is the durable context; chat output
is just the new-session goal plus whether any dirt was left behind.

Use `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md` for this handoff-specific
prompt. Do not make the shared `docs/dev_flow/templates/NEXT_GOAL.md`
handoff-specific; `tenn-issue`, `tenn-review-board`, and other non-handoff
producers need that shared template to remain generic and directly executable.

## Completion Rule

A handoff is not complete unless:

- git state is reported honestly
- relevant work is committed or explicitly recorded as uncommitted or
  owner-boundary
- ledger entry exists, or `DATA_MISSING` plus fallback evidence is recorded
- runtime-like work explicitly says whether functionality was proven, and uses
  `PARTIAL`, `BROKEN`, or `DATA_MISSING` when intended live output was not
  verified
- `NEXT_GOAL.md` exists
- the short fresh-session prompt exists
- `HANDOFF.md` records leftover git dirt using current `git status --short
  --untracked-files=all` evidence and, when relevant, ignored/report artifact
  evidence
- the final chat closeout prints only the short fresh-session goal,
  `HANDOFF.md` path, and concise git-dirt summary, not a full handoff recap
- relevant artifacts and failed attempts are linked by path or URL
- the first next action and do-not-touch boundaries are explicit
- no product/runtime/data/extraction mutation occurred outside approved scope

## Host-Global Boundary

Do not edit `~/.codex/skills/handoff/SKILL.md` by default. If host-global
handoff behavior needs a change and the owner has not explicitly approved that
host mutation in the current run, write a report-local `HOST_HANDOFF_PATCH.md`
with exact proposed changes instead.
