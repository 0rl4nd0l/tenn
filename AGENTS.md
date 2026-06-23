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
- Use `docs/README.md` as the documentation source map before browsing the
  wider docs tree or historical report archives.
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

## Agent Operating Constitution

### Truthfulness And Non-Sycophancy

- Do not lie, invent state, exaggerate progress, or mirror Orlando. Challenge
  the premise when repo evidence disagrees.
- Label important claims as `VERIFIED`, `USER_REPORTED`, `INFERRED`, `UNKNOWN`,
  `CONFLICT`, or `DATA_MISSING`; treat conflicts as stop-or-narrow conditions.

### Runtime Functionality Proof

For daemon, runtime, ingestion, extraction, automation, collector, scheduler,
service, or pipeline work, agents must not equate activity with functionality.

These are not proof that the system works:

- A running service is not proof.
- A timer is not proof.
- Fresh logs are not proof.
- Fresh artifacts are not proof.
- Passing unit tests are not proof.
- A report bundle is not proof.
- A merged PR is not proof.

Functionality requires proving that the intended live output changed after the
run began or was already fresh before the run. Before claiming `DONE`,
functional, working, complete, or equivalent status for this work class, include
a proof table with these exact fields:

| Field | Required evidence |
| --- | --- |
| intended output | The live output the system is meant to produce, not the activity around it. |
| live output location | DB table/query, API route, file path, queue, store, or external surface checked. |
| pre-run max timestamp or count | Baseline freshness/count captured before the run or `DATA_MISSING`. |
| post-run max timestamp or count | Freshness/count captured after the run or `DATA_MISSING`. |
| rows/files inserted or updated after run start | Delta attributable to the run, or explicit zero. |
| readiness/gate status | Current readiness gate, health gate, promotion gate, or blocker gate status. |
| exact command/query used | Reproducible command, SQL, API call, or script used for the proof. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | One of the four allowed functionality results. |
| remaining blocker | The unresolved blocker, or `none` only when the proof supports `WORKING`. |

If the intended output is stale, zero, missing, or unverified, the status must
be `PARTIAL`, `BROKEN`, or `DATA_MISSING`, never `DONE`.

### Branch And Worktree Preflight

- Before non-trivial implementation, check worktree, branch, HEAD, upstream,
  canonical base, related PRs, related branches/worktrees, dirty state, and
  owner-boundary paths.
- Do not start coding when requested work already exists elsewhere or the
  current branch is stale.

### Advanced-Code And Stale-Work Policy

- Search for more advanced existing work before implementing.
- Classify existing work as `ADOPT`, `CONTINUE`, `PRESERVE`, `SUPERSEDED`,
  `OWNER_BOUNDARY`, or `UNKNOWN`.
- Preserve valuable stale work through validated commit/PR paths when approved.

### Minimum Necessary Code

- Prefer the smallest readable, testable change. If one line is enough, use one
  line.
- Remove unnecessary related lines when safe and in scope, but do not code-golf
  or add obscure cleverness.
- Avoid opportunistic unrelated refactors.

### No Report-Only Loops

- Reports must end in implementation, PR/merge, issue closeout, cleanup
  approval, owner decision, or an exact next goal.
- Do not run report after report.

### Native Git Hygiene

- Git Hygiene is a backend guard for every workflow.
- It may classify and recommend, but must not clean, delete, reset, stash,
  rebase, merge, or push without approval.

### Review Board And Worker Discipline

- Review board must produce `BOARD_DECISION.json`, not just opinions.
- Review board must search for credible objections but never fabricate dissent.
- Workers require one lane, one worktree, one result file, and no invisible
  dirt.

### Explanation Obligation

- When Orlando asks, explain in plain language but enough depth: what it is,
  why it exists, what changed, what remains broken, risks, and next action.

### Surprising Numbers And Owner Challenges

- When reporting counts, scores, pass rates, daemon status, evaluation results,
  or surprisingly low/high numbers, explain denominator, filters, exclusions,
  freshness, and pipeline stage.
- Before closeout for daemon, runtime, extraction, or automation functionality
  claims, build evidence/counter-lineage for the intended output and current
  gate status even if Orlando has not challenged the result.
- If Orlando challenges a number with phrases like "why only", "shouldn't this
  be higher", "is the daemon doing it", or "that doesn't make sense", switch to
  evidence mode and build counter lineage: raw/captured -> candidate -> accepted
  -> evaluated -> reported.
- Distinguish `VERIFIED`, `INFERRED`, `UNKNOWN`, and `DATA_MISSING`.

## Task Ledger And Duplicate-Work Prevention

- Before non-trivial work, check the branch-independent Agent Task Ledger and
  related task cards, reports, branches, worktrees, PRs, and issues.
- Do not reimplement work that already exists. Classify similar work before
  coding as active, open-PR, merged-canonical, stale-preserve, superseded,
  owner-boundary, or unknown.
- Implementation-capable sessions must write or update a ledger entry for their
  claim, progress, wait/block state, PR, merge, done, parked, or superseded
  state.
- If the ledger is unavailable, record `DATA_MISSING` and perform a bounded
  fallback search before coding.

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

## Two-Shot Workstreams And Autonomy Envelopes

- Non-trivial Git Hygiene and control-plane remediation should default to a
  two-shot workstream.
- Shot 1 means investigate, classify, preserve safe evidence, create an
  approval manifest, create an execution plan, and stop.
- Shot 2 means execute approved manifest groups mechanically, skip drifted
  paths, stop before forbidden boundaries, and close out.
- Avoid micro-approval loops for safe report-local and preservation-only
  actions. Approval should be group-level and manifest-based where possible, not
  path-by-path chat back-and-forth.
- Still stop for destructive, source-state, canonical-history, GitHub,
  product, runtime, or data boundaries.
- Reserve `WAITING_ON_USER` for actual boundary crossings, ambiguity, missing
  approval, or unsafe drift; do not use it for every safe report, ledger,
  archive, patch bundle, or preservation artifact.

## Task Cards, Registry, And Merge Parking

- Run the portable guard before relying on repo-local Tenn scripts:
  `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json`.
  From a Tenn control-plane checkout, the repo-backed fallback is
  `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json`.
  Missing repo-local `scripts/agent_*` files in runtime/product repos is not
  itself repo corruption; record `DATA_MISSING` only for unavailable evidence.
- Implementation-capable work should have a task card before edits. Validate it
  with the Tenn-control-plane-local
  `python3 scripts/agent_job_contract.py validate <task_card>` when the script
  is available.
- Keep `allowed_files` exact. Include report artifacts explicitly because
  `reports/` is ignored and local `check-diff` is literal.
- Use the Tenn-control-plane-local
  `python3 scripts/agent_job_registry.py list-active --read-only` for focused
  registry inspection when the script is available. Do not use lock-writing
  registry commands for read-only audit. If safe read-only registry evidence is
  unavailable, record `DATA_MISSING`.
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
- For runtime, daemon, automation, extraction, ingestion, collector, scheduler,
  service, or pipeline work, `DONE` requires fresh intended-output proof from
  the `Runtime Functionality Proof` table.
- If only artifacts, tests, reports, logs, services, timers, or PR state changed,
  use `DONE_WITH_RISK` or `PARTIAL`, not `DONE`.
- If the task was report-only, explicitly say "report-only complete; system
  functionality not proven."
- Use `DONE_WITH_RISK` when useful work completed but evidence is incomplete,
  validation is skipped for a stated reason, or an external blocker remains.
- Use `DONE` only when the stated done criteria and validation/reporting
  requirements are met.

## Skill And Subagent Policy

- Repo-backed Codex skills live under `.agents/skills`.
- See `docs/agents/skill-registry.md` for active, legacy, tool-specific, and
  reference-only skill root labels.
- `.codex/config.toml` and `.codex/hooks.json` are Codex config/hooks surfaces.
  Treat `.codex/skills` references as legacy/custom unless local evidence proves
  compatibility is intentionally required.
- Generic engineering skills that need issue tracker, triage label, or
  domain-doc configuration should read `docs/agents/issue-tracker.md`,
  `docs/agents/triage-labels.md`, and `docs/agents/domain.md`.
- Do not mirror all host skills into Tenn. Repo skills should wrap Tenn-specific
  workflows.
- If a repo-backed skill is needed but not shown in the picker or autocomplete,
  read the skill file by path under `.agents/skills/<skill>/SKILL.md`.
- Autocomplete or picker absence is not evidence that the repo-backed skill does
  not exist.
- Host/global skills must not silently replace Tenn repo-backed skills. Use the
  repo skill, or state why it is unavailable and mark the gap explicitly.
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
