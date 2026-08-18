---
name: tenn-issue-finder
description: Full-system Tenn issue discovery and triage skill. Use when Codex should audit Tenn read-only across reports, repo state, GitHub issues, PRs, task cards, and current artifacts, de-duplicate findings, and draft or create only high-confidence actionable GitHub issues with lanes, evidence, validation paths, and hard stops.
---

# Tenn Issue Finder

Audit Tenn for confirmed or high-confidence actionable problems. Prefer precise, lane-owned issue candidates over vague backlog growth.

## Core Rule

Do not fix anything. Do not mutate product code, runtime, data stores, production DB, Qdrant, news, memory stores, canonical financial truth, parser routing, extraction prompts, gold labels, model/runtime/GPU/service config, or unrelated dirty files.

Default to report-only issue discovery unless the user explicitly asks to create GitHub issues and the task card or current permission contract allows GitHub issue creation. Never create vague issues such as "improve UX" or "make Tenn smarter."

## Supervisor Operating Model

Use this skill as a discovery supervisor, not a giant backlog generator. Dispatch bounded child discovery passes by lane or artifact set, then reconcile them into one compact finding matrix.

Child passes use one primary lane, one evidence source group, one duplicate-check plan, one report output, and one create-or-defer decision set. They do not fix anything.

If Codex supports actual subagents, use read-only subagents for lane triage, duplicate search, regression/security review, and final arbitration. If actual subagents are unavailable, emulate them as named passes with compact outputs.

Durable state belongs in reports, issue matrices, GitHub issue/PR links, and parking references, not in growing chat context.

## Evidence Order

Use current evidence in this order:

1. Current reports, task cards, status JSON, validation output, and generated artifacts.
2. Current repo state, diffs, tests, scripts, docs, and config.
3. Current GitHub issues and PRs, open and closed.
4. Project Memory only as a search hint; do not treat it as current truth.

Record `DATA_MISSING` when evidence is unavailable rather than guessing.

## Context Hygiene

After each candidate issue or lane pass, write a compact outcome row and discard detailed issue-specific context.

Carry forward only finding title, lane, classification, evidence pointer, duplicate-check result, create/defer decision, follow-up or parking link, remaining `DATA_MISSING`, and next recommended candidate.

Do not carry forward detailed logs, file excerpts, speculative hypotheses, issue-specific workaround assumptions, failed experiments, or unvalidated fix patterns.

## Batch Limit / Review Gate

After every 5 candidate issues reviewed, stop and run a bounded reviewer pass over the matrix before creating more issue drafts.

Stop earlier and review when a finding touches Financial Truth, Memory, Query Orchestration, Provenance, runtime/model/GPU/service config, CI, security/auth, seed-regression behavior, cross-ticker behavior, or cross-route behavior.

## Preflight

Run read-only orientation commands:

```bash
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git worktree list --porcelain
git branch --all --verbose --no-abbrev
git for-each-ref --format="%(refname:short) %(objectname) %(committerdate:iso8601) %(upstream:short)" refs/heads refs/remotes
rg -n "DATA_MISSING|FOLLOWUP_REQUIRED|BLOCKED|FAIL|REGRESSION|FIXME" docs reports .github scripts tests backend frontend
```

Use read-only GitHub checks before proposing any new issue:

```bash
gh issue list --repo 0rl4nd0l/tenn --state open --limit 200
gh issue list --repo 0rl4nd0l/tenn --state closed --limit 200
gh pr list --repo 0rl4nd0l/tenn --state open --limit 100
gh issue list --repo 0rl4nd0l/tenn --state all --search "<finding terms>"
gh pr list --repo 0rl4nd0l/tenn --state all --search "<finding terms>"
```

If GitHub auth is unavailable, continue repo/report audit and mark duplicate checks as `DATA_MISSING`.

## Audit Lanes

Audit by lane and stop at actionable evidence:

- `Financial Truth`: canonical metrics, ASX/filing source truth, metric definitions, restatement risk, ticker cross-contamination.
- `Evaluation`: seeds, eval harnesses, gold labels, regressions, false pass/fail signals, missing validation.
- `Provenance`: source labels, source pages, citations, report traceability, evidence envelope, PDF/page access.
- `Query Orchestration`: routing, retrieval, query plans, fallback visibility, chat/Cockpit path consistency.
- `Memory`: company memory boundaries, stale facts, interticker contamination, cleanup evidence.
- `Reporting/Cockpit/Usability`: user-visible workflows, report completeness, closeout/report UX, dashboard truth.
- `Repo/GitHub/Dev-agent workflow`: task-card enforcement, registry overlap, CI, branch hygiene, issue/PR traceability.
- `Performance/local-first runtime`: local LLM routing, GPU/runtime diagnostics, throughput, startup safety, resource exhaustion.

## Per-Issue Child Context Contract

For each proposed issue, keep one finding, one primary lane, one duplicate-check plan, one validation path, one issue body or defer reason, one reviewer verdict when high risk, and one create/defer decision.

Do not allow child discovery passes to write concurrently to shared report files. If issue creation is authorized, use one writer at a time and re-check duplicates immediately before creating each issue.

## Finding Classification

Classify each candidate:

```text
CONFIRMED_BUG
CONFIRMED_GAP
SEED_REGRESSION
TRUST_RISK
USABILITY_FRICTION
REPO_CONTROL_RISK
DATA_MISSING
DEFER
REJECT
```

Use `CONFIRMED_BUG` only when current evidence shows broken behavior.

Use `CONFIRMED_GAP` when a required control, report, validation, or workflow is missing and its absence is actionable.

Use `SEED_REGRESSION` only when a seed, fixture, eval, or expected behavior regressed or can mask real product failure. Require blast-radius and root-cause framing.

Use `TRUST_RISK` for provenance, financial truth, memory, or source traceability failures that can mislead users even if the UI still functions.

Use `DEFER` for real but low-value or premature ideas that should stay in a report, not GitHub.

Use `REJECT` for duplicates, unsupported guesses, broad wishlist items, or findings without a validation path.

## Root-Cause And Blast-Radius Gate

For candidate issues involving tickers, documents, news, retrieval, source labels, memory, extraction, or UI/backend contracts:

- Prove whether the issue is isolated or class-wide before creating a remediation issue.
- Check other likely affected tickers, docs, routes, or classes where feasible.
- Require the issue body to ask for regression coverage or a follow-up if broader proof is missing.
- Reject one-off aliases, hidden fallbacks, label relaxation, and test-only coverups as proposed final fixes.

For seed regressions, require blast-radius and root-cause analysis in the issue body.

## De-Duplication Gate

Before creating or recommending a GitHub issue:

1. Search open issues.
2. Search closed issues.
3. Search open PRs.
4. Search reports, task cards, and parking entries.
5. Decide whether the candidate is already tracked, superseded, parked, stale, or new.

Treat a finding as duplicate only when the existing tracker covers the same root cause, lane, validation path, and hard stops. Similar symptoms are not enough.

## Branch Hygiene / Merge Visibility Discovery

Use branch discovery to find useful untracked branch work, not to generate a stale-branch issue for every old ref. Branch review is read-only unless the user and task card explicitly permit GitHub mutation. Do not delete, prune, reset, stash, merge, rebase, or cherry-pick branches during issue discovery.

Discover branch candidates with current local and remote-tracking refs. If a remote refresh would be needed to know current PR/branch truth and the task does not approve ref or GitHub mutation, record `DATA_MISSING` instead of fetching.

For each candidate branch, collect only bounded evidence:

- branch name, worktree path if present, base ref, and branch HEAD;
- unique commits using a read-only command such as `git log --left-right --cherry-pick --oneline <base>...<branch>`;
- changed files using a read-only command such as `git diff --name-status <base>...<branch>`;
- existing issue, PR, task-card, report, and parking links;
- validation or CI evidence when already available;
- duplicate or supersession evidence.

Classify each branch:

```text
ACTIVE_LINKED
PARKED_READY_FOR_REVIEW
PARKED_NEEDS_REBASE
BLOCKED_BY_CI
BLOCKED_BY_DEPENDENCY
SUPERSEDED
STALE_UNKNOWN_NEEDS_AUDIT
SAFE_TO_ARCHIVE_CANDIDATE
```

Create or draft a branch review issue only when the branch has at least one of:

- unique commits not reachable from the target base;
- meaningful changed files or report/task artifacts;
- unclear merge state, ownership, or validation status;
- validation evidence that may be useful later;
- possible Tenn product, evaluation, reporting, repo-hygiene, or control-plane value.

Do not create branch issues for low-evidence stale refs whose only signal is age. Use `SAFE_TO_ARCHIVE_CANDIDATE` only when current evidence shows no unique commits, no meaningful unmerged changed files, or full coverage by a linked replacement; this classification is not cleanup approval.

Recommended tracking for branch review drafts:

- Labels: `lane:repo-hygiene`, `type:control-plane`, `state:needs-review` / `state:parked` / `state:blocked` / `state:data-missing`, `risk:medium` or `risk:high`, and `mode:audit` or `mode:result-review`.
- Milestone: `M0 — Control Plane Hardening`.
- Classification maps to the issue state: `PARKED_*` uses `state:parked`, `BLOCKED_*` uses `state:blocked`, `STALE_UNKNOWN_NEEDS_AUDIT` uses `state:data-missing`, and reviewable active work uses `state:needs-review`.

## GitHub-Native Issue System

Treat GitHub Issues as Tenn's live actionable backlog. Findings that require action should become linked GitHub issues, PR references, task cards, or merge-parking entries when creation/linking is approved. Reports are evidence; they are not the final tracker for actionable remediation.

Recommend these labels for every issue draft and apply them only when the task card or user explicitly permits GitHub mutation:

- `lane:*`
- `mode:*`
- `priority:*`
- `risk:*`
- `state:*`
- `type:*`

Recommend one milestone when useful:

- `M0 Control Plane Hardening`
- `M1 Trust / Provenance Foundation`
- `M2 Evaluation Spine`
- `M3 Query + Memory Integrity`
- `M4 Financial Truth Expansion`
- `M5 Cockpit Analyst Workflow`
- `M6 Runtime / Local Automation`

When Projects are available, recommend field values for Lane, Mode, Risk, Priority, Status, Task Card, Report Path, Blocked By, Root Cause Fixed, Follow-up Required, and Production Data Access. If Project access or schema is unavailable, record `DATA_MISSING`.

Use `fixes #X` only in PR guidance when product remediation actually landed and validation passed. Use `refs #X`, `audit for #X`, or normal references for audit-only, report-only, exploratory, parked, or partial work so remediation issues do not auto-close incorrectly.

Automated discovery reports must create or draft issue-ready findings, update existing issue references when approved, or mark low-value/unsupported items as `DEFER` or `NO_FOLLOWUP`. Do not maintain disconnected bug, opportunity, or remediation registries that never reach GitHub Issues, a linked PR, task card, or merge parking.

## Issue Creation Gate

Create or recommend a GitHub issue only when all gates pass:

- Actionable: one bounded objective.
- Scoped: small enough for a task card.
- Lane-owned: primary lane and supporting lanes are clear.
- Evidence-backed: current file, report, command, or GitHub evidence exists.
- Not already tracked: duplicate check is complete.
- Validation path: clear commands, report checks, or acceptance criteria exist.
- Boundaries: forbidden surfaces and hard stops are explicit.

If any gate fails, put the candidate in the report matrix with `issue created: NO` and the reason.

## Plain-Language Summary Rule

Every issue body, issue draft, and high-confidence finding must include a `## Summary` heading.

Write the summary in plain language and explain:

- What the issue is or was.
- What it impacted.
- How it restricted Tenn or blocked user/system value.
- Why fixing it would be a meaningful step forward rather than cosmetic cleanup.

## Throttle And Noise Rule

Prioritize P0/P1 findings first unless the user explicitly asks for broad issue generation. Low-value suggestions, polish ideas, vague UX preferences, and speculative improvements go to the report only.

Do not open more issues than the user requested. If no count is requested, stop after the highest-confidence P0/P1 candidates and report the rest as deferred.

## Issue Body Template

Use this body for authorized GitHub issue creation or for drafts:

```markdown
## Task
`<job_id>`

## Lane
Primary lane: <lane>
Supporting lanes: <lanes>
Mode: audit_only / safe_extension / implementation / result_review

## GitHub Tracking
Recommended labels: lane:<lane>, mode:<mode>, priority:<P0/P1/P2/P3>, risk:<risk>, state:<state>, type:<type>
Recommended milestone: <M0/M1/M2/M3/M4/M5/M6 or none>
Project fields: Lane=<lane>; Mode=<mode>; Risk=<risk>; Priority=<priority>; Status=<status>; Task Card=<task_card_path>; Report Path=<report_path>; Blocked By=<issue/none>; Root Cause Fixed=<YES/NO>; Follow-up Required=<YES/NO>; Production Data Access=<YES/NO>

## Finding
<one bounded problem statement>

## Summary
In plain language:
- What the issue is or was:
- What it impacted:
- How it restricted Tenn:
- Why fixing it is a meaningful step forward:

## Evidence
- `<path or command>`: <summary>
- GitHub duplicate check: <open/closed issue and PR search summary>

## Why this matters
<trust risk, user workflow breakage, regression risk, or repo-control gap>

## Required task card
`docs/agent_tasks/<job_id>.md`

## Required output
`reports/agent_jobs/<job_id>/`

## Allowed files / surfaces
- <exact files/dirs or report-only>

## Forbidden files / surfaces
- production DB/Qdrant/news/memory
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- runtime/model/GPU/service config
- unrelated dirty work
- <finding-specific forbidden surfaces>

## Acceptance criteria
- <evidence-backed completion criteria>
- <blast-radius/root-cause criteria where relevant>
- <no broad claims without validation>

## Definition of done
- The root cause or documented gap is resolved according to the issue mode.
- Validation passes or blockers are explicitly documented.
- Required follow-ups are linked, created, parked, `NO_FOLLOWUP`, or `DATA_MISSING`.
- PR link text uses `fixes #X` only for validated product remediation; otherwise use `refs #X` or `audit for #X`.
- No forbidden surfaces are changed.

## Validation
- task-card validate/check-diff
- registry list/check-overlap/claim/release if available
- focused tests/checks
- JSON/schema validation if artifacts are produced
- git diff --check

## Hard stops
- duplicate tracker found
- HIGH collision risk
- forbidden surface required
- production data access required without approval
- validation cannot run or fails without explanation
```

## Branch Review Issue Body Template

Use this body for authorized branch review issue creation or for drafts:

```markdown
## Task
`<job_id>`

## Lane
Primary lane: Repo Hygiene
Supporting lanes: Reporting, Evaluation
Mode: audit / result-review

## GitHub Tracking
Recommended labels: lane:repo-hygiene, type:control-plane, mode:<audit/result-review>, risk:<medium/high>, state:<needs-review/parked/blocked/data-missing>
Recommended milestone: M0 — Control Plane Hardening
Project fields: Lane=Repo Hygiene; Mode=<audit/result-review>; Risk=<medium/high>; Priority=<P1/P2/P3>; Status=<Needs Review/Parked/Blocked/Data Missing>; Task Card=<task_card_path>; Report Path=<report_path>; Blocked By=<issue/PR/branch/none>; Root Cause Fixed=NO; Follow-up Required=YES; Production Data Access=NO

## Branch
- Branch: `<branch>`
- Worktree: `<path or DATA_MISSING>`
- Base ref / commit: `<base>`
- Branch HEAD: `<head>`
- Classification: ACTIVE_LINKED / PARKED_READY_FOR_REVIEW / PARKED_NEEDS_REBASE / BLOCKED_BY_CI / BLOCKED_BY_DEPENDENCY / SUPERSEDED / STALE_UNKNOWN_NEEDS_AUDIT / SAFE_TO_ARCHIVE_CANDIDATE

## Summary
In plain language:
- What the branch appears to contain:
- What it may impact:
- Why review or parking matters:
- What evidence is missing, if any:

## Evidence
- Unique commits: `<command/result or DATA_MISSING>`
- Changed files: `<summary or DATA_MISSING>`
- Existing issue/PR/task/report links: `<links or DATA_MISSING>`
- Validation evidence: `<commands/reports or DATA_MISSING>`
- Supersession/duplicate check: `<replacement link or DATA_MISSING>`

## Required task card
`docs/agent_tasks/<job_id>.md`

## Required output
`reports/agent_jobs/<job_id>/`

## Allowed files / surfaces
- Branch review report artifacts.
- Issue/PR comments or labels only if explicitly approved.

## Forbidden files / surfaces
- product/backend/frontend/runtime code unless a later implementation task allows it
- production DB/Qdrant/news/memory
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- runtime/model/GPU/service config
- branch delete/prune/reset/stash/merge/rebase/cherry-pick without separate explicit approval
- unrelated dirty work

## Acceptance criteria
- Branch classification is evidence-backed or marked `DATA_MISSING`.
- Useful work is linked to an issue, PR, task card, report, or parking entry.
- Superseded or archive-candidate status links the replacement or evidence.
- No destructive branch cleanup occurs in this task.

## Validation
- `git branch --contains` / `git branch --no-merged` or equivalent read-only checks.
- `git log --left-right --cherry-pick --oneline <base>...<branch>` where safe.
- `git diff --name-status <base>...<branch>` where safe.
- Existing report/test/CI evidence, or `DATA_MISSING`.
```

## Finding Matrix

Always produce:

| Finding | Evidence | Severity | Lane | Labels | Milestone | Duplicate check | Issue created | Reason |
| ------- | -------- | -------- | ---- | ------ | --------- | --------------- | ------------- | ------ |
| `<finding>` | `<path/command/URL>` | `P0/P1/P2/P3` | `<lane>` | `<labels>` | `<milestone>` | `<result>` | `YES #... / NO / DRAFT` | `<gate result>` |

## Stop / Split Context

Stop with a checkpoint report and recommend a fresh continuation goal using only matrix and report paths when the matrix gets large or the run has handled 10 candidate issue reviews, 2 high-risk findings, or any contested integration/merge decision.

## Final Output

Finish with:

```markdown
## Issue discovery summary

Branch:
HEAD:

Audited lanes:
- ...

Finding matrix:
| Finding | Evidence | Severity | Lane | Labels | Milestone | Duplicate check | Issue created | Reason |
| ------- | -------- | -------- | ---- | ------ | --------- | --------------- | ------------- | ------ |

Issues created:
- #... or none

Issue drafts:
- <title> - <reason not created>

Rejected/deferred:
- <finding> - <reason>

DATA_MISSING:
- ...

Forbidden mutations:
- none / <explain>

Verdict:
PASS / PASS_REPORT_ONLY / BLOCKED_DATA_MISSING / FAIL_SCOPE_VIOLATION
```
