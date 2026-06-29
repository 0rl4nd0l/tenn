# AGENTS.md - Tenn Repo Constitution

This is the stable instruction layer for agents working in Tenn. Keep it short
enough to load every turn. Put repeatable procedures in repo-backed skills and
`docs/dev_flow`, not in this file.

## Repo And Target Verification

- Tenn is an ASX financial data ingestion, extraction, and cockpit workflow
  repository. Active runtime code is mainly under `financial-engine_v2/`;
  repo-level scripts and evaluation helpers also exist under `scripts/`.
- Verify the actual target before acting:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git status --short --untracked-files=all
```

- Runtime paths are environment-specific. Do not assume `/workspace`,
  `/home/l4nd0`, NVMe, venv, Docker, services, GPUs, or DB access without
  checking.
- Use `docs/README.md` as the documentation source map before browsing wider
  docs or historical reports.
- Use `docs/entrypoints.md` only when runtime entrypoint context is needed.
  Most repo-hygiene and docs tasks should not start services.

## Procedure Routing

`AGENTS.md` states the non-negotiables. Read the relevant procedure only when
the task needs it:

| Task type | Procedure source |
| --- | --- |
| Implementation, docs edits, validation, closeout | `.agents/skills/tenn-fix/SKILL.md` |
| Branch, worktree, dirty state, ledger, registry, duplicate work | `.agents/skills/tenn-git-guard/SKILL.md` |
| Operator prompts and exact command patterns | `docs/dev_flow/CODEX_OPERATOR_GUIDE.md` |
| Skill selection and visible-surface policy | `docs/dev_flow/SKILLS_SURFACE.md` |
| Handoff or fresh-session continuation | `.agents/skills/tenn-handoff/SKILL.md` |
| Long `/goal` reports and wait states | `.agents/skills/tenn-goal-report/SKILL.md` |
| Risky decisions or merge/readiness calls | `.agents/skills/tenn-review-board/SKILL.md` |
| Plain-language explanations | `.agents/skills/tenn-explain/SKILL.md` |
| Financial metric extraction | `.agents/skills/tenn-financial-metric-extraction/SKILL.md` |
| Path ownership and stale-work preservation | `docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md` |

Host/global skills must not silently replace Tenn repo-backed skills. If a
repo skill is needed but absent from autocomplete, read it by path.

## Source Of Truth

Use this order when evidence conflicts:

1. Current user instructions and explicit safety boundaries.
2. Active task card, if one is provided or created.
3. Live repo state, current files, branch/HEAD/origin, and safe GitHub reads.
4. Current reports under `reports/agent_jobs/...` and registry evidence.
5. Durable docs such as this file, `docs/README.md`, `docs/entrypoints.md`,
   repo-backed skills, and issue bodies.
6. Memory, prior reports, and older summaries as background only.

If these disagree, stop or narrow the work until the conflict is explicit.

## Evidence And Truthfulness

- Ground substantive claims in current-turn evidence.
- Label important claims as `VERIFIED`, `USER_REPORTED`, `INFERRED`,
  `UNKNOWN`, `CONFLICT`, or `DATA_MISSING`.
- Do not invent repo state, validation results, issue status, branch ownership,
  runtime behavior, active agent ownership, or dissent.
- Challenge the premise when evidence disagrees. Do not mirror Orlando when the
  repo says otherwise.
- Prefer exact paths, commands, issue/PR numbers, report artifacts, timestamps,
  counts, and query outputs over qualitative status.
- For surprising counts, scores, pass rates, daemon status, or evaluation
  results, explain denominator, filters, exclusions, freshness, and pipeline
  stage.

## Safety Boundaries

Do not mutate any of these without explicit approval for that exact action:

- DB, Qdrant, Redis, news stores, memory stores, production data, source PDFs,
  gold labels, extraction prompts, backfills, runtime state, service config,
  model/GPU config, Docker volumes, or secrets.
- Broad rewrites, dependency installs, service starts, merge/rebase/reset/stash,
  branch deletion, worktree deletion, pruning, force operations, GitHub writes,
  or parked-work changes.

Preserve unrelated dirty or untracked files. Work with existing dirt instead of
cleaning it.

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

## Worktree, Task Card, And Ledger Discipline

- Before non-trivial implementation, run the portable guard and inspect
  `path_ownership`, `canonical_head`, `duplicate_work_status`, and
  `stop_reimplementation`:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
```

- For `FULL_GUARD` audits, merge/parking decisions, high-risk duplicate-work
  searches, or broad hygiene work, add `--fallback-detail full` when the runner
  supports it. Keep small `FAST_PROGRESS` work on summarized guard output.

- If the portable guard is unavailable inside a Tenn control-plane checkout,
  use `.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py`.
- Do not start coding when requested work already exists elsewhere, the current
  branch is stale, the path is not a valid Tenn git worktree, or owner
  boundaries are ambiguous.
- Create or validate a task card before implementation-capable edits. Keep
  `allowed_files` exact, including report artifacts.
- Check the branch-independent Agent Task Ledger, task cards, reports,
  branches, worktrees, PRs, and issues for duplicate work before coding.
- Update ledger/report state for claim, progress, wait/block, PR, merge, done,
  parked, or superseded status as required by `tenn-fix`.
- Classify similar work as active, open-PR, merged-canonical, stale-preserve,
  superseded, owner-boundary, or unknown before replacing it.

## Execution Lanes

- `FAST_PROGRESS`: small docs/control-plane fixes or narrow code fixes with
  exact files, no runtime/data/extraction/GitHub/destructive boundary, and no
  stale/dirty/duplicate-work blocker. Use summarized guard output, focused
  validation, and direct closeout.
- `STANDARD_FIX`: normal bounded implementation with task card, guard,
  allowed-files check, validation, docs impact, and final diff review.
- `FULL_GUARD`: stale path, dirty overlap, duplicate-work risk, merge/parking,
  owner-boundary, architecture, broad cleanup, or high-collision work. Use full
  fallback detail and stop on unresolved risk.
- `RUNTIME_PROOF`: runtime-like work may be called working, functional,
  complete, or `DONE` only after the Runtime Functionality Proof table passes.
- If lane eligibility is uncertain, escalate to `FULL_GUARD`.

## Implementation Discipline

- Prefer the smallest readable, testable change. Avoid opportunistic refactors.
- Use one primary lane accepted by local tooling. If doing Repo Hygiene, use an
  accepted primary lane such as `Evaluation` or `Reporting` and list
  `Repo Hygiene` as supporting.
- Use subagents only when they save context, increase independent verification,
  or support parallel read-only specialist review. Each worker needs one lane,
  one worktree, one result file, and no invisible dirt.
- Review board output must include `BOARD_DECISION.json`, not just opinions. It
  should search for credible objections but never fabricate dissent.
- Reports must end in implementation, PR/merge, issue closeout, cleanup
  approval, owner decision, blocked state, or an exact next goal.
- Financial metric extraction is highest priority only when live issue or
  registry evidence confirms it for the task. Canonical financial numbers must
  be source-bound, deterministic, auditable, and provenance-linked.

## Waiting And Approval

Stop with `WAITING_ON_USER` when the next meaningful step requires approval,
permission flags, credentials, services, DB/backfill access, runtime/data
mutation, GitHub writes, merge/rebase/branch/parking decisions, cleanup, or an
owner product/design/architecture decision.

Write the wait state into the report or handoff with: needed input, why it
matters, current safe state, options, and recommendation. If approval is
optional, continue only with clearly labeled useful read-only work.

## Command Output Discipline

- Scope unknown or potentially large output before reading it into context.
  Prefer `rg`, `rg --files`, `git status --short`, `git diff --name-only`, and
  targeted ranges.
- For noisy commands, cap bytes, not just lines:
  `COMMAND 2>&1 | head -c 4000` or `COMMAND 2>&1 | tail -c 4000`.
- Preserve exit codes when validation matters. Use `set -o pipefail`, capture
  status explicitly, or rerun a focused command if a pipe hides the status.
- For noisy tests or builds, write raw logs to a report artifact and show only
  the summary plus raw-log path.

## Validation And Done

- Tiny docs, comments, report-only artifacts, or prompt text: no runtime
  validation required; explain why.
- Narrow code change: run the cheapest focused check that exercises the change.
- Shared extraction, parser, runtime, RAG, registry, hook, or orchestration
  change: run a targeted regression or smoke check.
- Broad, cross-layer, release, or merge-candidate change: run broader suites
  only when justified.
- Never claim validation passed without the command, exit status, and relevant
  output.
- Final reports should list files touched, files intentionally not touched,
  commands run, validation status, unsafe actions avoided, blocked items,
  ignored/untracked artifacts, and the next recommended prompt.
- If the task was report-only or docs-only, explicitly say system
  functionality was not proven.
- Use `DONE_WITH_RISK` when useful work completed but evidence is incomplete,
  validation was skipped for a stated reason, or an external blocker remains.
  Use `DONE` only when the stated done criteria and proof requirements are met.

## GitHub Issue Workflow

- GitHub issues are the coordination backlog; task cards are execution
  contracts; reports are evidence and closeout.
- Search open and closed issues before proposing issue mutations.
- Do not create, edit, label, comment on, close, or reopen issues without
  explicit approval.
- Use issue #78 for agent markdown and Codex repo documentation refresh work
  unless live evidence shows a narrower tracker supersedes it.
