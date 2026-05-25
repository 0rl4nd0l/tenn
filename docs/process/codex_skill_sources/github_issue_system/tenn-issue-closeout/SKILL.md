---
name: tenn-issue-closeout
description: Safely triage, close, park, supersede, or leave open Tenn GitHub issues using task-card permission contracts, registry/lane checks, fresh GitHub/repo evidence, follow-up issue creation, merge parking, and report artifacts. Use when Codex is asked to close out Tenn issues, run an issue closeout sweep, review open or recently closed Tenn GitHub issues, create or link follow-up issues for audit findings, or decide whether an audit issue can close without mutating product, runtime, data, parser, prompt, gold-label, or config surfaces.
---

# Tenn Issue Closeout

Safely triage, complete, close, park, supersede, or leave open Tenn GitHub issues without losing findings, hiding unfinished work, mutating forbidden surfaces, or creating false "fixed" signals.

## Core Rule

Do not close an issue merely because an audit ran.

Close only when one close gate is satisfied:

- `COMPLETED_WITH_EVIDENCE`: acceptance criteria are met, validation passed, and evidence is linked.
- `COMPLETED_AUDIT_ONLY_WITH_FOLLOWUPS`: the audit/report is complete, and every actionable unresolved finding links to an open issue, new follow-up issue, or merge-parking entry.
- `DUPLICATE_COVERED_BY_EXISTING`: another issue, PR, report, task, or parking entry fully covers it, and the closeout links the replacement.
- `SUPERSEDED`: a newer task/PR/report makes the issue obsolete, and the comment explains why.
- `PARKED_FOR_REVIEW`: work is complete, validated, and frozen but cannot safely merge; a visible parking entry or review issue exists.

If no gate is true, leave the issue open and add a blocker/status comment.

## Supervisor Operating Model

Use this skill as the dispatcher, safety gate, and final arbiter for issue closeout. Do not run it as one giant issue fixer.

Child worker passes handle one bounded unit at a time:

- One issue.
- One primary lane.
- One task card.
- One branch or worktree when mutation is required.
- One report directory.
- One validation plan.
- One reviewer verdict.
- One closeout decision.

Reviewer passes decide root cause, regression, security/boundary, financial-truth/provenance, user value, skeptic/opposition, and final arbitration.

If Codex supports actual subagents, use them for triage, implementation, regression/security review, and final arbitration. If actual subagents are unavailable, emulate them as named passes with compact outputs.

Durable state belongs in reports, GitHub issues/comments, merge parking, and issue matrices, not in growing chat context. The main agent keeps only compact rolling state and re-reads durable artifacts when needed.

## Resolution Review Hook

Use `tenn-issue-resolution-reviewer` before closing high-risk or batch-close issues. The reviewer decides whether the work is root-cause fixed, only a narrow workaround, audit-only, unsafe, regressive, or ready to close.

Reviewer required when:

- The issue touches Financial Truth, Memory, Query Orchestration, Provenance, runtime, security, CI, or repo-control surfaces.
- The issue is a seed regression.
- The issue was audit-only but has remediation findings.
- The issue affects multiple tickers, docs, routes, or workflows.
- The closeout would close more than 5 issues in one batch.
- The issue has failed or blocked validation.
- The closeout depends on a narrow ticker-specific fix.
- The closeout claims product remediation landed.

Reviewer optional when:

- The issue is a pure duplicate.
- The issue is stale or superseded and docs-only.
- The issue is a typo or low-risk cosmetic issue with direct validation.

Do not close when the reviewer returns `KEEP_OPEN`, `BLOCKED_DATA_MISSING`, or `FAIL_UNSAFE_OR_REGRESSIVE`. If the reviewer returns `PASS_WITH_FOLLOWUPS`, close only when every required follow-up is linked, created under the current permission contract, or parked visibly.

## Context Hygiene

After each issue, write one compact outcome row to the closeout matrix and discard detailed issue-specific context.

Carry forward only:

- Issue number.
- Decision.
- Branch, commit, and report.
- Validation result.
- Follow-up issue or parking link.
- Remaining `DATA_MISSING`.
- Next recommended issue.

Do not carry forward:

- Detailed logs.
- File excerpts.
- Speculative hypotheses.
- Issue-specific workaround assumptions.
- Failed experiments.
- Unvalidated fix patterns.

## Batch Limit / Review Gate

Stop and run `tenn-issue-resolution-reviewer` after every 5 issues reviewed.

Stop and run `tenn-issue-resolution-reviewer` after every 2 issues fixed.

Stop earlier and run the reviewer when any issue touches Financial Truth, Memory, Query Orchestration, Provenance, runtime/model/GPU/service config, CI, security/auth, seed-regression behavior, cross-ticker behavior, or cross-route behavior.

## Per-Issue Child Context Contract

Each child worker must use one issue, one primary lane, one task card, one branch/worktree if mutation is required, one report dir, one validation plan, one reviewer verdict, and one closeout decision.

Do not allow child workers to share mutable files unless registry and task-card checks say it is safe. Do not let multiple child workers write concurrently to overlapping files. Prefer read-only subagents for exploration and review, with one writer at a time for implementation.

## Root-Cause Over Workaround Gate

Before closing an issue as fixed, require the reviewer to classify the solution:

```text
ROOT_CAUSE_FIXED
NARROW_WORKAROUND
TEST_ONLY_COVERUP
PARTIAL_FIX
AUDIT_ONLY_NO_REMEDIATION
REGRESSION_RISK
NEEDS_FOLLOWUP
READY_TO_CLOSE
```

If the classification is `NARROW_WORKAROUND`, `TEST_ONLY_COVERUP`, `PARTIAL_FIX`, `REGRESSION_RISK`, or `AUDIT_ONLY_NO_REMEDIATION`, do not close as fixed. Create or link a follow-up issue, park completed-but-unmerged work, or leave the issue open with a blocker comment. Close only as audit complete when all remediation is tracked elsewhere.

## Blast Radius Gate

For bugs involving tickers, documents, news, retrieval, source labels, memory, extraction, or UI/backend contracts:

- Prove whether the issue is isolated or class-wide.
- Check other likely affected tickers, docs, routes, or classes where feasible.
- Add regression coverage or a follow-up issue when broader proof is missing.
- Reject one-off aliases, hidden fallbacks, label relaxation, and test-only coverups as final fixes.

## Hard Boundaries

Do not use this skill to mass-close issues, mark audits as product-remediated, clean worktrees, force-release registry locks, mutate production data, mutate DB/Qdrant/news/memory stores, change canonical financial truth, change parser routing, change extraction prompts, change gold labels, change model/runtime/GPU/service config, or merge/rebase/cherry-pick/reset/stash/prune/delete branches or worktrees unless the current task card and registry checks explicitly allow it.

Before acting, classify:

- Primary lane: `Financial Truth`, `Evaluation`, `Provenance`, `Query Orchestration`, `Memory`, `Reporting`, or `Repo Hygiene / Ops`.
- Mode: `audit_only`, `safe_extension`, `implementation`, `result_review`, or `issue_closeout_only`.
- Collision risk: `LOW`, `MEDIUM`, or `HIGH`.

If collision risk is `HIGH`, do not mutate code or close issues unless closure is purely duplicate/superseded with evidence. Prefer report-only or leave open with a blocker comment.

## Preflight

Run and record:

```bash
pwd
date -Iseconds
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git remote -v
git worktree list --porcelain
```

Run these when available; record `DATA_MISSING` instead of guessing if unavailable:

```bash
python3 scripts/agent_job_registry.py list-active
python3 scripts/agent_job_registry.py check-overlap --help
python3 scripts/agent_job_contract.py --help
gh repo view 0rl4nd0l/tenn
gh issue list --repo 0rl4nd0l/tenn --state open --limit 100
gh issue list --repo 0rl4nd0l/tenn --state closed --limit 100
gh pr list --repo 0rl4nd0l/tenn --state open --limit 50
gh run list --repo 0rl4nd0l/tenn --limit 20
```

## Task Card Gate

If the current `/goal` asks for repo writes, report generation, GitHub issue creation, issue closing, labels, or closeout comments, create or validate a task card before changes.

Default card:

```text
docs/agent_tasks/issue_closeout_sweep_v1_<date>.md
```

Minimum card fields:

```yaml
job_id: issue_closeout_sweep_v1_<date>
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/issue_closeout_sweep_v1_<date>.md
  - reports/agent_jobs/issue_closeout_sweep_v1_<date>/README.md
  - reports/agent_jobs/issue_closeout_sweep_v1_<date>/status.json
  - reports/agent_jobs/issue_closeout_sweep_v1_<date>/issue_closeout_matrix.md
  - reports/agent_jobs/issue_closeout_sweep_v1_<date>/followup_issue_map.md
  - reports/agent_jobs/issue_closeout_sweep_v1_<date>/data_missing.md
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/issue_closeout_sweep_v1_<date>
mutation_mode: issue_closeout_only
production_data_access: false
```

Allowed writes are the task card, report artifacts, GitHub issue comments, safe labels, GitHub follow-up issues, and GitHub issue close actions that pass a close gate. Forbidden writes are product/backend/frontend/runtime code, production DB/Qdrant/news/memory, canonical financial truth, parser/extraction/gold-label/model/runtime/service surfaces, and unrelated dirty files.

## Issue Inputs

Use user-provided issue numbers or label queries when present.

If no issue list is provided, default to:

1. Open issues labelled `task:codex-ready`.
2. Recently closed issues with task-card labels, to verify no findings were lost.
3. Open PR-linked issues that may be stale, superseded, duplicated, or blocked.

Do not close arbitrary product/UI bugs unless the task explicitly includes them.

## Classification

Classify each issue:

```text
ISSUE_STATUS:
- OPEN_ACTIONABLE
- OPEN_BLOCKED
- READY_TO_CLOSE_COMPLETED
- READY_TO_CLOSE_AUDIT_WITH_FOLLOWUPS
- READY_TO_CLOSE_DUPLICATE
- READY_TO_CLOSE_SUPERSEDED
- PARKED_FOR_REVIEW
- KEEP_OPEN_DATA_MISSING
- KEEP_OPEN_NEEDS_USER_DECISION
```

Classify each finding:

```text
FINDING_CLASS:
- FOLLOWUP_REQUIRED
- FOLLOWUP_RECOMMENDED
- COVERED_BY_EXISTING
- NO_FOLLOWUP
- DATA_MISSING
```

Treat confirmed blockers, remediation tasks, validation gaps, regression seeds, unsafe ambiguities, and missing control-plane surfaces as `FOLLOWUP_REQUIRED`. Treat useful bounded non-blockers as `FOLLOWUP_RECOMMENDED`. Use `COVERED_BY_EXISTING` only when an issue, PR, report, task card, or parking entry actually tracks it. Use `DATA_MISSING` when evidence is needed before tasking.

## Follow-Up Rule

Before closing any audit-mode issue, every `FOLLOWUP_REQUIRED` item must be linked to an existing open issue, converted into a new issue, converted into a merge-parking entry for completed-but-unmerged work, or explicitly marked `DATA_MISSING` with the evidence needed. Do not leave required follow-ups only inside a closed issue comment or report.

## GitHub-Native Backlog Policy

Treat GitHub Issues as Tenn's live actionable backlog. Reports provide evidence, task cards provide permission contracts, milestones group execution batches, Projects provide dashboards, Project Memory provides coordination hints, and merge parking tracks completed-but-unmerged work. Do not let required findings live only in reports, closed comments, local registries, or chat context.

Recommend these labels for every closeout, follow-up, or status comment, and apply them only when the task card or user explicitly allows GitHub mutation:

- `lane:*`
- `mode:*`
- `priority:*`
- `risk:*`
- `state:*`
- `type:*`

Recommend one milestone when applicable:

- `M0 Control Plane Hardening`
- `M1 Trust / Provenance Foundation`
- `M2 Evaluation Spine`
- `M3 Query + Memory Integrity`
- `M4 Financial Truth Expansion`
- `M5 Cockpit Analyst Workflow`
- `M6 Runtime / Local Automation`

When Projects are available, recommend field values for Lane, Mode, Risk, Priority, Status, Task Card, Report Path, Blocked By, Root Cause Fixed, Follow-up Required, and Production Data Access. If Project access or schema is unavailable, record `DATA_MISSING` and keep the issue body backfillable.

Use `fixes #X` only when product remediation landed, validation passed, and the issue should auto-close on merge. Use `refs #X`, `audit for #X`, or normal references for audit-only, report-only, partial, parked, or evidence work. Never let an audit-only PR auto-close a remediation issue.

Before creating or linking a follow-up, de-duplicate against open issues, closed issues, open and closed PRs, recent reports, task cards, and merge parking entries. A duplicate must cover the same root cause, lane, validation path, and hard stops; similar symptoms are not enough.

Audit issues can close only when every unresolved actionable finding is linked to an existing issue or PR, converted into a new issue under approval, parked for merge/review, marked `NO_FOLLOWUP` with reason, or marked `DATA_MISSING` with required evidence. Otherwise leave the issue open with a blocker/status comment.

Automated reports must create or draft issue-ready findings, update existing issue references when approved, or mark items `DEFER` / `NO_FOLLOWUP`. Do not maintain disconnected bug or opportunity registries that never reach GitHub Issues, a linked PR, task card, or merge parking.

## Plain-Language Summary Rule

Every created issue, follow-up issue, fix report, parking entry, and closeout comment must include a `## Summary` heading.

For issues, write the summary in plain language and explain:

- What the issue is or was.
- What it impacted.
- How it restricted Tenn or blocked user/system value.

For fixes, write the summary in plain language and explain:

- What the issue was.
- How it was fixed or why it was not fixed.
- How the result improves Tenn.
- Why the result is a meaningful step forward rather than a narrow workaround.

New follow-up issue body:

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

## Source
Created from closeout of:
- Issue: #<source_issue>
- Report: `<report_path>`
- Commit/branch if applicable: `<branch>` / `<commit>`

## Summary
In plain language:
- What the issue is or was:
- What it impacted:
- How it restricted Tenn:

## Goal
<one bounded objective>

## Why this matters
<blocker, trust risk, workflow value, or control-plane gap>

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
- <issue-specific forbidden surfaces>

## Acceptance criteria
- <evidence/validation criteria>
- <no broad claims without evidence>
- <follow-up report required>

## Definition of done
- Root cause or audit scope is resolved according to the task mode.
- Validation passes or blockers are documented.
- Required follow-ups are linked, created, parked, `NO_FOLLOWUP`, or `DATA_MISSING`.
- No forbidden surfaces are changed.

## Validation
- task-card validate/check-diff
- registry list/check-overlap/claim/release if available
- focused tests/checks
- JSON/schema validation if artifacts are produced
- git diff --check

## Hard stops
- HIGH collision risk
- forbidden surface required
- production data access required without approval
- validation cannot run or fails without explanation
```

## Closeout Comments

Add a closeout comment before or during every closure:

```markdown
## Closeout

Status: COMPLETED_WITH_EVIDENCE / COMPLETED_AUDIT_ONLY_WITH_FOLLOWUPS / DUPLICATE / SUPERSEDED / PARKED_FOR_REVIEW

## Summary
In plain language:
- What the issue was:
- How it was fixed, or why this is audit/parking/duplicate closeout rather than a fix:
- How the result improves Tenn:
- Why this is a meaningful step forward:

Branch:
`<branch>`

HEAD / commit:
`<commit>`

Task card:
`<task_card_path>`

Report:
`<report_path>`

Changed files / surfaces:
- `<file or surface>`
- Or: report-only / GitHub-only

Validation:
- `<command>` - PASS / FAIL / BLOCKED
- `<command>` - PASS / FAIL / BLOCKED

Boundary compliance:
- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing / extraction prompt / gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No unrelated dirty work touched.
- Any exceptions: `<none or explain>`

Finding classification:
| Finding | Class | Follow-up |
|---|---|---|
| `<finding>` | FOLLOWUP_REQUIRED / FOLLOWUP_RECOMMENDED / COVERED_BY_EXISTING / NO_FOLLOWUP / DATA_MISSING | `#<issue>` / `<reason>` |

GitHub tracking:
- Labels recommended/applied:
- Milestone recommended/applied:
- Project fields recommended/applied:
- PR link mode: fixes / refs / audit for / none

Remaining DATA_MISSING:
- `<item or none>`

Product remediation landed?
- YES / NO
- If NO: audit/report complete only; remediation tracked in `#<issue>`.

Close reason:
- `<why closing is safe>`
```

If the issue must stay open, comment:

```markdown
## Status update - left open

This issue remains open.

## Summary
In plain language:
- What the issue is:
- What it impacts:
- How it restricts Tenn:
- Why it is not fixed yet:

Reason:
- <blocker / missing validation / unresolved follow-up / DATA_MISSING>

Current evidence:
- Branch: `<branch>`
- HEAD: `<head>`
- Report: `<report_path or DATA_MISSING>`

Next safe step:
- <exact task or evidence needed>

Hard boundaries preserved:
- No forbidden surfaces mutated.
```

## Do Not Close

Leave the issue open if acceptance criteria are unmet, validation failed and no follow-up exists, the report is missing, a required follow-up was not created or linked, the task was blocked without a blocker comment, production remediation is implied but only an audit occurred, the issue is still the best tracker, central `DATA_MISSING` remains, or the close reason would mislead future agents.

## Merge Parking

If work is completed and validated but cannot merge safely:

1. Do not close as merged.
2. Create or update a merge-parking entry if repo merge-parking surfaces exist.
3. If no parking surface exists, create a follow-up issue or blocker comment.
4. Close only if the parked entry is visible and linked.

Parking is not merge approval. Parking closeout must include task card, report, branch, base commit, HEAD commit, changed files, validation, parking status, merge/review blockers, and next review action.

## Sweep Priority

Use this order:

1. Issues whose reports say remediation remains but no follow-up exists.
2. Audit issues closed recently; verify follow-ups were created.
3. Open `task:codex-ready` issues with high trust/control-plane value.
4. PR/CI blocker issues.
5. Duplicate/superseded cleanup.
6. Low-value stale issues.

Never prioritize cosmetic closure over traceability.

## Main Skill Final Matrix

Maintain this rolling matrix during every closeout run:

| Issue | Lane | Worker decision | Reviewer verdict | Closed? | Follow-up/Parking | DATA_MISSING | Next action |
| ----- | ---- | --------------- | ---------------- | ------- | ----------------- | ------------ | ----------- |

This matrix is the handoff artifact for fresh continuations. Do not rely on accumulated chat context as the source of truth.

## Stop / Split Context

Stop with a checkpoint report and recommend a fresh continuation goal using only matrix and report paths when the matrix gets large or the run has handled:

- 10 issue reviews.
- 4 issue fixes.
- 2 high-risk issues.
- Any contested integration or merge decision.

The continuation should start from durable artifacts, not the whole accumulated context.

## Required Reports

Write:

```text
reports/agent_jobs/<job_id>/README.md
reports/agent_jobs/<job_id>/status.json
reports/agent_jobs/<job_id>/issue_closeout_matrix.md
reports/agent_jobs/<job_id>/followup_issue_map.md
reports/agent_jobs/<job_id>/data_missing.md
```

`issue_closeout_matrix.md`:

| Issue | Lane | Worker decision | Reviewer verdict | Closed? | Follow-up/Parking | DATA_MISSING | Next action |
| ----- | ---- | --------------- | ---------------- | ------- | ----------------- | ------------ | ----------- |

`followup_issue_map.md`:

| Source issue | Finding | Follow-up issue | Lane | Mode | Labels | Milestone | Project fields | Status |
| ------------ | ------- | --------------- | ---- | ---- | ------ | --------- | -------------- | ------ |

`status.json`:

```json
{
  "job_id": "<job_id>",
  "mode": "issue_closeout_only",
  "primary_lane": "Reporting",
  "issues_reviewed": 0,
  "issues_closed": 0,
  "issues_left_open": 0,
  "followup_issues_created": 0,
  "followup_issues_linked": 0,
  "parked_items_created": 0,
  "duplicates_closed": 0,
  "superseded_closed": 0,
  "data_missing": [],
  "forbidden_mutations": false,
  "production_data_access": false,
  "validation_summary": [],
  "verdict": "PASS"
}
```

Allowed verdicts: `PASS`, `PARTIAL_FOLLOWUPS_CREATED`, `PARTIAL_LEFT_OPEN`, `BLOCKED_HIGH_COLLISION`, `BLOCKED_DATA_MISSING`, `FAIL_SCOPE_VIOLATION`.

## Validation

Run where safe:

```bash
git diff --check
python3 -m json.tool <any_status_json>
python3 scripts/agent_job_contract.py validate <task_card>
python3 scripts/agent_job_contract.py check-diff <task_card>
```

If GitHub issue comments, creation, closure, or labels were done through `gh`, record exact issue numbers.

## Final Response

Return only:

```markdown
## Issue closeout summary

Branch:
HEAD:

Reviewed:
Closed:
Left open:
Follow-ups created:
Follow-ups linked:
Parked items:

Validation:
- ...

High-risk notes:
- ...

Issues closed:
- #...

Issues left open:
- #... - reason

Follow-up issues:
- #... from #...

Reports:
- `<path>`

DATA_MISSING:
- ...

Verdict:
PASS / PARTIAL_FOLLOWUPS_CREATED / PARTIAL_LEFT_OPEN / BLOCKED_HIGH_COLLISION / BLOCKED_DATA_MISSING / FAIL_SCOPE_VIOLATION
```

## Hard Stop

Stop immediately and write a blocker report if the task requires forbidden mutations, task-card validation fails and cannot be corrected within allowed files, registry overlap is `HIGH` and safe isolation is not possible, GitHub authentication is unavailable and issue updates are required, `gh` would affect the wrong repository, closeout would hide unresolved `FOLLOWUP_REQUIRED` work, or validation cannot be performed and the issue is not clearly duplicate/superseded.
